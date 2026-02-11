"""Heat News Extraction Pipeline -- complete end-to-end orchestration.

Collects heat-related news articles from across all Indian states, union
territories, and districts in 14+ local languages using free-tier news
APIs and RSS feeds.

Pipeline stages:
    1. **Query collection** -- generate and execute search queries via
       Google News RSS, NewsData.io, and GNews APIs with per-source
       circuit breakers, rate limiting, and checkpoint/resume.
    2. **Article extraction** -- fetch HTML and extract full text via
       trafilatura for each collected article reference.
    3. **Deduplication and filtering** -- URL dedup, title similarity
       dedup, relevance scoring, and exclusion filtering.
    4. **Output** -- write per-state JSON/CSV files and collection
       metadata to a date-organized output directory.

Usage:
    python main.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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

    # API keys from environment (None if not set -- sources degrade gracefully)
    # The `or None` converts empty strings to None (GitHub Actions sets undefined
    # secrets to "" rather than leaving them unset in the environment).
    newsdata_key = os.environ.get("NEWSDATA_API_KEY") or None
    gnews_key = os.environ.get("GNEWS_API_KEY") or None

    # Time budget: stop collecting 10 minutes before the GitHub Actions step
    # timeout so extraction, dedup, and output stages always complete.
    # Default 170 min (step timeout is 180 min). Override with env var.
    pipeline_start = time.monotonic()
    collection_budget_sec = int(os.environ.get("COLLECTION_BUDGET_MINUTES", "170")) * 60
    deadline = pipeline_start + collection_budget_sec
    logger.info("Collection deadline: %d minutes from now", collection_budget_sec // 60)

    # Output directory: output/<YYYY-MM-DD> in IST
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
        deadline=deadline,
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
        refs = await executor.run_collection()
        logger.info("Stage 1 complete: %d article refs collected", len(refs))

        # Stage 2 -- Article extraction
        logger.info("Stage 2: Article extraction")
        articles = await extract_articles(refs)
        logger.info("Stage 2 complete: %d articles extracted", len(articles))

        # Stage 3 -- Deduplication and filtering
        logger.info("Stage 3: Deduplication and filtering")
        filtered = deduplicate_and_filter(articles)
        logger.info("Stage 3 complete: %d articles after dedup+filter", len(filtered))

        # Stage 4 -- Output
        logger.info("Stage 4: Writing output to %s", output_dir)
        metadata = CollectionMetadata(
            collection_timestamp=datetime.now(ist),
            sources_queried=["google_news", "newsdata", "gnews"],
            query_terms_used=sorted({ref.search_term for ref in refs}),
            counts={
                "articles_found": len(refs),
                "articles_extracted": sum(
                    1 for a in articles if a.full_text is not None
                ),
                "articles_filtered": len(filtered),
            },
        )
        result = await write_collection_output(filtered, output_dir, metadata)
        logger.info(
            "Stage 4 complete: wrote %d JSON, %d CSV, %d metadata files",
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
