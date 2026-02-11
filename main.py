"""Heat News Extraction Pipeline -- complete end-to-end orchestration.

Collects heat-related news articles from across Indian states, union
territories, and districts in 14+ local languages using free-tier news
APIs and RSS feeds.

Pipeline stages:
    1. **Query collection** -- generate and execute search queries via
       Google News RSS, NewsData.io, and GNews APIs with per-source
       circuit breakers, rate limiting, and checkpoint/resume.
    2. **Date filtering** -- discard articles older than DATE_RANGE_HOURS.
    3. **Article extraction** -- fetch HTML and extract full text via
       trafilatura for each collected article reference.
    4. **Deduplication and filtering** -- URL dedup, title similarity
       dedup, relevance scoring, and exclusion filtering.
    5. **Output** -- write per-state JSON/CSV files and collection
       metadata to a date-organized output directory.

Configuration (all via environment variables):
    TIMEOUT_MINUTES   Hard deadline for the entire pipeline (default: 0 = no
                      limit, runs to completion). Set by CI for time-bounded runs.
    STATES            Comma-separated state slugs (default: all 36).
                      Example: STATES=delhi,maharashtra,tamil-nadu
    DATE_RANGE_HOURS  Only keep articles from the last N hours (default: 48).
    MAX_ARTICLES      Cap articles sent to extraction (default: 5000).

Usage:
    python main.py                                      # all states, no time limit
    STATES=delhi,bihar python main.py                   # specific states
    TIMEOUT_MINUTES=30 STATES=delhi python main.py      # with deadline
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.data.geo_loader import get_all_regions, get_region_by_slug
from src.dedup import deduplicate_and_filter
from src.extraction import extract_articles
from src.output import CollectionMetadata, write_collection_output
from src.query import (
    QueryExecutor,
    QueryGenerator,
    create_gnews_scheduler,
    create_google_scheduler,
    create_newsdata_scheduler,
)
from src.reliability import CheckpointStore, CircuitBreaker
from src.sources import GNewsSource, GoogleNewsSource, NewsDataSource

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the heat news extraction pipeline end-to-end."""
    # ------------------------------------------------------------------
    # Setup and configuration
    # ------------------------------------------------------------------
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # --- Configuration from environment ---
    timeout_min = int(os.environ.get("TIMEOUT_MINUTES", "0"))
    states_csv = os.environ.get("STATES", "").strip()
    date_range_hours = int(os.environ.get("DATE_RANGE_HOURS", "48"))
    max_articles = int(os.environ.get("MAX_ARTICLES", "5000"))

    # API keys (None if not set -- sources degrade gracefully).
    # The `or None` converts empty strings to None (GitHub Actions sets
    # undefined secrets to "" rather than leaving them unset).
    newsdata_key = os.environ.get("NEWSDATA_API_KEY") or None
    gnews_key = os.environ.get("GNEWS_API_KEY") or None

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

    logger.info(
        "Config: timeout=%s, states=%s, date_range=%dh, max_articles=%d",
        f"{timeout_min} min" if timeout_min > 0 else "none (run to completion)",
        states_csv or "all",
        date_range_hours,
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
    output_dir = Path("output") / now.strftime("%Y-%m-%d")

    # Checkpoint for crash recovery
    checkpoint_path = output_dir / ".checkpoint.json"
    checkpoint = CheckpointStore(checkpoint_path)

    # ------------------------------------------------------------------
    # Source and scheduler construction
    # ------------------------------------------------------------------
    google_source = GoogleNewsSource()
    newsdata_source = NewsDataSource(api_key=newsdata_key)
    gnews_source = GNewsSource(api_key=gnews_key)

    google_cb = CircuitBreaker(name="google_news")
    newsdata_cb = CircuitBreaker(name="newsdata")
    gnews_cb = CircuitBreaker(name="gnews")

    google_scheduler = create_google_scheduler(google_source, circuit_breaker=google_cb)
    newsdata_scheduler = create_newsdata_scheduler(newsdata_source, circuit_breaker=newsdata_cb)
    gnews_scheduler = create_gnews_scheduler(gnews_source, circuit_breaker=gnews_cb)

    generator = QueryGenerator()
    executor = QueryExecutor(
        schedulers={
            "google": google_scheduler,
            "newsdata": newsdata_scheduler,
            "gnews": gnews_scheduler,
        },
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
        cutoff = now - timedelta(hours=date_range_hours)
        before_filter = len(refs)
        refs = [r for r in refs if r.date >= cutoff]
        logger.info(
            "Date filter: %d -> %d refs (discarded %d older than %dh)",
            before_filter, len(refs), before_filter - len(refs), date_range_hours,
        )

        # Cap articles to avoid unbounded extraction
        if len(refs) > max_articles:
            logger.info(
                "Capping refs at MAX_ARTICLES=%d (had %d)", max_articles, len(refs),
            )
            refs = refs[:max_articles]

        # Stage 3 -- Article extraction
        # When running with a deadline, give extraction all remaining time
        # minus a 2-min buffer.  Without a deadline, just extract everything.
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

        # Stage 4 -- Deduplication and filtering
        logger.info("Stage 4: Deduplication and filtering")
        filtered = deduplicate_and_filter(articles)
        logger.info("Stage 4 complete: %d articles after dedup+filter", len(filtered))

        # Stage 5 -- Output
        logger.info("Stage 5: Writing output to %s", output_dir)
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
        result = await write_collection_output(filtered, output_dir, metadata)
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
        await google_source.close()
        await newsdata_source.close()
        await gnews_source.close()
        logger.info("All source connections closed")


if __name__ == "__main__":
    asyncio.run(main())
