"""Heat News Extraction Pipeline -- complete end-to-end orchestration.

Collects heat-related news articles from across Indian states, union
territories, and districts in 14+ local languages using free-tier news
APIs and RSS feeds.

Pipeline stages:
    1. **Query collection** -- generate and execute search queries via
       Google News RSS, NewsData.io, and GNews APIs with per-source
       circuit breakers, rate limiting, and checkpoint/resume.
    2. **Filtering** -- date filter, then LLM relevance check on
       titles (before extraction to avoid wasting time on irrelevant articles).
    3. **Article extraction** -- fetch HTML and extract full text via
       trafilatura only for articles that passed relevance checks.
    4. **Deduplication and filtering** -- URL dedup, title similarity
       dedup, relevance scoring, and exclusion filtering.
    5. **Output** -- write per-state JSON/CSV files and collection
       metadata to a date-organized output directory.

Configuration via CLI arguments, environment variables, or .env file.
Precedence: CLI > env var > .env > code default.

Usage:
    python main.py                                          # today, all states
    python main.py --states delhi,bihar                     # specific states
    python main.py -s delhi --sources google --llm gemini   # full control
    python main.py --date-range 2026-02-10:2026-02-12       # date range
    STATES=delhi python main.py                             # env vars still work
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Load .env BEFORE any os.environ.get() calls.
# Does NOT override existing env vars, so shell exports and CI secrets win.
load_dotenv()

from src.data.geo_loader import get_all_regions, get_region_by_slug
from src.dedup import deduplicate_and_filter
from src.extraction import extract_articles
from src.output import CollectionMetadata, create_output_directories, write_collection_output
from src.query import (
    QueryExecutor,
    QueryGenerator,
    SourceScheduler,
    create_gnews_scheduler,
    create_google_scheduler,
    create_newsdata_scheduler,
    tag_districts_from_text,
    tag_districts_with_llm,
)
from src.relevance import create_relevance_checker
from src.reliability import CheckpointStore, CircuitBreaker
from src.sources import GNewsSource, GoogleNewsSource, NewsDataSource

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments. All are optional; env vars / .env fill the gaps."""
    parser = argparse.ArgumentParser(
        description="Heat News Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Precedence: CLI > env var > .env > code default.\n"
            "API keys are read from env vars / .env only (not CLI)."
        ),
    )
    parser.add_argument(
        "--states", "-s", default=None,
        help="Comma-separated state slugs (default: all)",
    )
    parser.add_argument(
        "--districts", "-d", default=None,
        help="Comma-separated district slugs (default: all)",
    )
    parser.add_argument(
        "--sources", default=None,
        help="News sources: google, newsdata, gnews (comma-separated)",
    )
    parser.add_argument(
        "--date-range", default=None,
        help="YYYY-MM-DD:YYYY-MM-DD date range",
    )
    parser.add_argument(
        "--date-range-hours", default=None, type=int,
        help="Hours lookback (default: today only)",
    )
    parser.add_argument(
        "--llm", default=None,
        help="LLM provider: openai, gemini, claude, none, or combined (e.g. openai+gemini)",
    )
    parser.add_argument(
        "--max-articles", default=None, type=int,
        help="Extraction cap (default: 5000)",
    )
    parser.add_argument(
        "--timeout", default=None, type=int,
        help="Pipeline timeout in minutes (default: 0 = no limit)",
    )
    return parser.parse_args()


async def main() -> None:
    """Run the heat news extraction pipeline end-to-end."""
    # ------------------------------------------------------------------
    # Setup and configuration
    # ------------------------------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    args = parse_args()

    # --- Configuration: CLI > env var > .env > code default ---
    timeout_min = args.timeout if args.timeout is not None else int(os.environ.get("TIMEOUT_MINUTES", "0"))
    states_csv = args.states if args.states is not None else os.environ.get("STATES", "").strip()
    districts_csv = args.districts if args.districts is not None else os.environ.get("DISTRICTS", "").strip()
    sources_csv = args.sources if args.sources is not None else os.environ.get("SOURCES", "").strip()
    max_articles = args.max_articles if args.max_articles is not None else int(os.environ.get("MAX_ARTICLES", "5000"))

    # Date params -- CLI overrides env vars; both override the "today" default
    date_range_str = args.date_range if args.date_range is not None else os.environ.get("DATE_RANGE", "").strip()
    date_range_hours_str = os.environ.get("DATE_RANGE_HOURS", "").strip()
    if args.date_range_hours is not None:
        date_range_hours: int | None = args.date_range_hours
    elif date_range_hours_str:
        date_range_hours = int(date_range_hours_str)
    else:
        # Neither CLI nor env var set -- will use "today" default below
        date_range_hours = None

    # LLM provider -- write to env so src/relevance picks it up
    if args.llm is not None:
        os.environ["LLM_PROVIDER"] = args.llm

    # API keys (None if not set -- sources degrade gracefully).
    # The `or None` converts empty strings to None (GitHub Actions sets
    # undefined secrets to "" rather than leaving them unset).
    newsdata_key = os.environ.get("NEWSDATA_API_KEY") or None
    gnews_key = os.environ.get("GNEWS_API_KEY") or None

    # Parse source selection (default: all three)
    enabled_sources: set[str] = {"google", "newsdata", "gnews"}
    if sources_csv:
        enabled_sources = {s.strip().lower() for s in sources_csv.split(",") if s.strip()}
        logger.info("Sources enabled: %s", sorted(enabled_sources))

    # Parse district filter
    district_slugs: set[str] | None = None
    if districts_csv:
        district_slugs = {d.strip().lower() for d in districts_csv.split(",") if d.strip()}

    # --- Deadlines (optional -- only for CI time constraints) ---
    # TIMEOUT_MINUTES=0 means no deadline: the pipeline runs to completion.
    # When set, collection gets 80% and extraction gets the remainder.
    pipeline_start = time.monotonic()
    if timeout_min > 0:
        pipeline_deadline = pipeline_start + timeout_min * 60
        collection_deadline = pipeline_start + timeout_min * 60 * 0.80
    else:
        pipeline_deadline = None
        collection_deadline = None

    date_desc = f"{date_range_hours}h" if date_range_hours is not None else "today"
    if date_range_str:
        date_desc = date_range_str
    logger.info(
        "Config: timeout=%s, states=%s, date_range=%s, max_articles=%d",
        f"{timeout_min} min" if timeout_min > 0 else "none (run to completion)",
        states_csv or "all",
        date_desc,
        max_articles,
    )

    # --- State filtering ---
    regions = None
    if states_csv:
        slugs = [s.strip() for s in states_csv.split(",") if s.strip()]
        regions = [r for slug in slugs if (r := get_region_by_slug(slug)) is not None]
        not_found = set(slugs) - {r.slug for r in regions}
        if not_found:
            logger.warning("Unknown state slugs (skipped): %s", sorted(not_found))
        if not regions:
            logger.error("No valid states found for STATES=%s", states_csv)
            return
        logger.info("Filtering to %d states: %s", len(regions), [r.slug for r in regions])

    # --- Time zone and output directory ---
    ist = ZoneInfo("Asia/Kolkata")
    now = datetime.now(ist)
    output_root = Path("output")

    # Create output directory skeleton from geo data
    all_regions = regions if regions else get_all_regions()
    create_output_directories(output_root, all_regions)
    logger.info("Output directories created for %d regions", len(all_regions))

    # Checkpoint for crash recovery
    checkpoint_path = output_root / ".checkpoint.json"
    checkpoint = CheckpointStore(checkpoint_path)

    # ------------------------------------------------------------------
    # Source and scheduler construction (only enabled sources)
    # ------------------------------------------------------------------
    sources_to_close: list = []
    schedulers: dict[str, SourceScheduler] = {}

    if "google" in enabled_sources:
        google_source = GoogleNewsSource()
        sources_to_close.append(google_source)
        google_cb = CircuitBreaker(name="google_news")
        schedulers["google"] = create_google_scheduler(google_source, circuit_breaker=google_cb)

    if "newsdata" in enabled_sources:
        if newsdata_key:
            newsdata_source = NewsDataSource(api_key=newsdata_key)
            sources_to_close.append(newsdata_source)
            newsdata_cb = CircuitBreaker(name="newsdata")
            schedulers["newsdata"] = create_newsdata_scheduler(newsdata_source, circuit_breaker=newsdata_cb)
        else:
            logger.warning("NewsData enabled but NEWSDATA_API_KEY not set -- skipping")

    if "gnews" in enabled_sources:
        if gnews_key:
            gnews_source = GNewsSource(api_key=gnews_key)
            sources_to_close.append(gnews_source)
            gnews_cb = CircuitBreaker(name="gnews")
            schedulers["gnews"] = create_gnews_scheduler(gnews_source, circuit_breaker=gnews_cb)
        else:
            logger.warning("GNews enabled but GNEWS_API_KEY not set -- skipping")

    logger.info("Active sources: %s", sorted(schedulers.keys()))

    generator = QueryGenerator()
    executor = QueryExecutor(
        schedulers=schedulers,
        generator=generator,
        checkpoint=checkpoint,
        deadline=collection_deadline,
    )

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------
    try:
        # Load checkpoint (resumes from previous run if any)
        await checkpoint.load()
        logger.info(
            "Checkpoint loaded: %d queries already completed",
            checkpoint.completed_count,
        )

        # Stage 1 -- Query collection
        logger.info("Stage 1: Query collection")
        refs = await executor.run_collection(regions=regions)
        logger.info("Stage 1 complete: %d article refs collected", len(refs))

        # Stage 2 -- Date filtering
        before_filter = len(refs)
        if date_range_str:
            # Explicit date range: --date-range 2026-02-01:2026-02-11
            parts = date_range_str.split(":")
            start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d").replace(tzinfo=ist)
            end_date = datetime.strptime(parts[-1].strip(), "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=ist
            )
            refs = [r for r in refs if start_date <= r.date <= end_date]
            logger.info(
                "Date range filter: %d -> %d refs (range %s to %s)",
                before_filter, len(refs), parts[0].strip(), parts[-1].strip(),
            )
        elif date_range_hours is not None:
            # Explicit hours lookback: --date-range-hours N
            cutoff = now - timedelta(hours=date_range_hours)
            refs = [r for r in refs if r.date >= cutoff]
            logger.info(
                "Date filter: %d -> %d refs (discarded %d older than %dh)",
                before_filter, len(refs), before_filter - len(refs), date_range_hours,
            )
        else:
            # Default: today only (midnight IST to now)
            today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            refs = [r for r in refs if r.date >= today_midnight]
            logger.info(
                "Date filter (today): %d -> %d refs (keeping %s onward)",
                before_filter, len(refs), today_midnight.strftime("%Y-%m-%d 00:00 IST"),
            )

        # District filtering (if DISTRICTS is set)
        if district_slugs:
            before_district = len(refs)
            refs = [
                r for r in refs
                if r.district and r.district.lower().replace(" ", "-") in district_slugs
            ]
            logger.info(
                "District filter: %d -> %d refs (keeping only %s)",
                before_district, len(refs), sorted(district_slugs),
            )

        # Stage 2b -- LLM relevance check on titles (BEFORE extraction)
        # Checker is kept alive until after district tagging (Stage 3c).
        relevance_checker = create_relevance_checker()
        if relevance_checker is not None:
            logger.info("Stage 2b: LLM relevance check (%d refs)", len(refs))
            refs = await relevance_checker.filter_refs(refs)
            logger.info("Stage 2b complete: %d refs after LLM filter", len(refs))
        else:
            logger.info("Stage 2b: LLM relevance check skipped (no provider configured)")

        # Cap articles to avoid unbounded extraction
        if len(refs) > max_articles:
            logger.info(
                "Capping refs at MAX_ARTICLES=%d (had %d)", max_articles, len(refs),
            )
            refs = refs[:max_articles]

        # Stage 3 -- Article extraction (only for LLM-approved refs)
        extraction_deadline = None
        if pipeline_deadline is not None:
            remaining_sec = pipeline_deadline - time.monotonic()
            extraction_deadline = time.monotonic() + max(remaining_sec - 120, 60)
        logger.info(
            "Stage 3: Article extraction (%d refs, %s)",
            len(refs),
            f"{max(remaining_sec - 120, 60) / 60:.0f} min available"
            if pipeline_deadline is not None
            else "no deadline",
        )
        articles = await extract_articles(refs, deadline=extraction_deadline)
        extracted_count = sum(1 for a in articles if a.full_text is not None)
        logger.info(
            "Stage 3 complete: %d/%d articles with full text",
            extracted_count, len(articles),
        )

        # Stage 3b -- Post-extraction district tagging (English text matching)
        before_tag = sum(1 for a in articles if a.district is not None)
        articles = tag_districts_from_text(articles, all_regions)
        after_text = sum(1 for a in articles if a.district is not None)
        logger.info(
            "Stage 3b: English text district tagging: %d -> %d articles with district",
            before_tag, after_text,
        )

        # Stage 3c -- LLM district extraction (for remaining untagged articles)
        if relevance_checker is not None:
            try:
                untagged = sum(1 for a in articles if a.district is None)
                if untagged > 0:
                    logger.info("Stage 3c: LLM district extraction (%d untagged)", untagged)
                    articles = await tag_districts_with_llm(
                        articles, all_regions, relevance_checker,
                    )
                    after_llm = sum(1 for a in articles if a.district is not None)
                    logger.info(
                        "Stage 3c complete: %d -> %d articles with district",
                        after_text, after_llm,
                    )
            finally:
                await relevance_checker.close()

        # Stage 4 -- Deduplication and filtering
        logger.info("Stage 4: Deduplication and filtering")
        filtered = deduplicate_and_filter(articles)
        logger.info("Stage 4 complete: %d articles after dedup+filter", len(filtered))

        # Stage 5 -- Output
        logger.info("Stage 5: Writing output to %s", output_root)
        metadata = CollectionMetadata(
            collection_timestamp=datetime.now(ist),
            sources_queried=["google_news", "newsdata", "gnews"],
            query_terms_used=sorted({ref.search_term for ref in refs}),
            counts={
                "articles_found": len(refs),
                "articles_extracted": extracted_count,
                "articles_filtered": len(filtered),
            },
        )
        result = await write_collection_output(filtered, output_root, metadata)
        logger.info(
            "Stage 5 complete: wrote %d JSON, %d CSV, %d metadata files",
            len(result["json"]),
            len(result["csv"]),
            len(result["metadata"]),
        )

        # Cleanup: delete checkpoint on successful completion
        checkpoint_path.unlink(missing_ok=True)
        logger.info("Pipeline complete -- checkpoint removed")

    except Exception:
        logger.error("Pipeline failed -- checkpoint preserved for resume", exc_info=True)
        raise

    finally:
        # Always close source instances
        for source in sources_to_close:
            await source.close()
        logger.info("All source connections closed")


if __name__ == "__main__":
    asyncio.run(main())
