"""QueryExecutor -- orchestrates hierarchical state-then-district query execution.

Ties together the QueryGenerator (what to search) with SourceSchedulers
(how to search safely) into a two-phase hierarchical execution flow:

1. **Phase 1 -- State-level queries:** Execute across all sources in parallel.
2. **Phase 2 -- District-level queries:** Only for states that returned results,
   only through sources that still have remaining budget.

All three sources execute concurrently via ``asyncio.TaskGroup``.  Errors are
caught and logged -- ``run_collection`` never raises.

Checkpoint integration: the executor optionally accepts a
:class:`~src.reliability.CheckpointStore` for crash recovery.  When present,
already-completed queries are skipped and checkpoints are saved after each
individual query completion (maximum recovery granularity).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from src.data.geo_loader import StateUT, get_all_regions
from src.models.article import ArticleRef

from ._generator import QueryGenerator
from ._models import Query, QueryResult
from ._scheduler import SourceScheduler

if TYPE_CHECKING:
    from src.relevance._base import RelevanceChecker
    from src.reliability._checkpoint import CheckpointStore

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Orchestrates hierarchical query execution across multiple news sources.

    Constructor:
        schedulers: dict keyed by source name ("google", "newsdata", "gnews"),
            each value a SourceScheduler wrapping a NewsSource.
        generator: QueryGenerator that produces Query objects from geographic
            data and heat terms.
        checkpoint: Optional CheckpointStore for crash recovery.  When
            provided, completed queries are skipped and checkpoint is
            saved after each individual query completion.
        deadline: Optional monotonic time deadline.  When set, the executor
            stops collecting and returns whatever was gathered so far,
            leaving time for downstream stages (extraction, dedup, output).
    """

    def __init__(
        self,
        schedulers: dict[str, SourceScheduler],
        generator: QueryGenerator,
        checkpoint: CheckpointStore | None = None,
        deadline: float | None = None,
    ) -> None:
        self._schedulers = schedulers
        self._generator = generator
        self._checkpoint = checkpoint
        self._deadline = deadline

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def checkpoint(self) -> CheckpointStore | None:
        """Return the checkpoint store, if any."""
        return self._checkpoint

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_collection(
        self, regions: list[StateUT] | None = None
    ) -> list[ArticleRef]:
        """Run hierarchical state-then-district collection.

        Args:
            regions: List of states/UTs to query.  If ``None``, loads all
                regions via :func:`get_all_regions`.

        Returns:
            Flat list of all :class:`ArticleRef` objects collected across
            both phases and all sources.
        """
        if regions is None:
            regions = get_all_regions()

        all_articles: list[ArticleRef] = []

        # ----------------------------------------------------------
        # Phase 1 -- State-level queries
        # ----------------------------------------------------------
        logger.info("Phase 1: generating state-level queries for %d regions", len(regions))
        queries_by_source = self._generator.generate_state_queries(regions)

        for source_key, queries in queries_by_source.items():
            logger.info("  %s: %d state queries", source_key, len(queries))

        state_results = await self._execute_queries_parallel(queries_by_source)

        # Collect articles from state results
        for result in state_results:
            all_articles.extend(result.articles)

        state_article_count = len(all_articles)
        logger.info(
            "Phase 1 complete: %d articles from %d query results",
            state_article_count,
            len(state_results),
        )

        # ----------------------------------------------------------
        # Determine active states (states that returned articles)
        # ----------------------------------------------------------
        active_slugs: set[str] = set()
        for result in state_results:
            if result.articles:
                active_slugs.add(result.query.state_slug)

        logger.info(
            "%d / %d states have active heat news",
            len(active_slugs),
            len(regions),
        )

        # ----------------------------------------------------------
        # Phase 2 -- District-level queries (active states only)
        # ----------------------------------------------------------
        active_regions = [r for r in regions if r.slug in active_slugs]

        if self._deadline is not None and time.monotonic() >= self._deadline:
            logger.warning(
                "Deadline reached after state queries -- skipping district queries"
            )
        elif not active_regions:
            logger.info("Phase 2: skipping district queries -- no active states")
        else:
            logger.info(
                "Phase 2: generating district queries for %d active states",
                len(active_regions),
            )

            district_queries_by_source: dict[str, list[Query]] = {}

            for hint, scheduler in self._schedulers.items():
                budget = scheduler.remaining_budget
                if budget is not None and budget <= 0:
                    logger.info("  %s: budget exhausted, skipping district queries", hint)
                    continue
                district_qs = self._generator.generate_district_queries(
                    active_regions, source_hint=hint  # type: ignore[arg-type]
                )
                if district_qs:
                    district_queries_by_source[hint] = district_qs
                    logger.info("  %s: %d district queries", hint, len(district_qs))

            if district_queries_by_source:
                district_results = await self._execute_queries_parallel(
                    district_queries_by_source
                )
                for result in district_results:
                    all_articles.extend(
                        _tag_districts(result.articles, result.query.districts)
                    )

        total = len(all_articles)
        logger.info(
            "Collection complete: %d total articles from %d state + %d district",
            total,
            state_article_count,
            total - state_article_count,
        )

        return all_articles

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_queries_parallel(
        self, queries_by_source: dict[str, list[Query]]
    ) -> list[QueryResult]:
        """Execute queries for each source in parallel via ``asyncio.TaskGroup``.

        Each source processes its queries sequentially through
        :meth:`_execute_query_list` (the scheduler handles internal rate
        limiting and concurrency).  Sources run concurrently.

        Wraps the TaskGroup in ``try/except*`` to handle ExceptionGroups
        without crashing -- logs all exceptions and returns whatever
        results were collected.
        """
        results: list[QueryResult] = []

        async def _run_source(source_key: str, source_queries: list[Query]) -> None:
            scheduler = self._schedulers.get(source_key)
            if scheduler is None:
                logger.warning(
                    "No scheduler registered for source '%s', skipping %d queries",
                    source_key,
                    len(source_queries),
                )
                return
            source_results = await self._execute_query_list(scheduler, source_queries)
            results.extend(source_results)

        try:
            async with asyncio.TaskGroup() as tg:
                for source_key, source_queries in queries_by_source.items():
                    tg.create_task(_run_source(source_key, source_queries))
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error(
                    "Error during parallel query execution: %s",
                    exc,
                    exc_info=exc,
                )

        return results

    async def _execute_query_list(
        self, scheduler: SourceScheduler, queries: list[Query]
    ) -> list[QueryResult]:
        """Run a list of queries through a single scheduler sequentially.

        Integrates checkpoint skip/save when a CheckpointStore is present:
        - Skips queries already completed in a previous run.
        - Marks each query as completed and saves checkpoint after execution.

        Checks remaining budget after each query and breaks early if
        the scheduler's budget is exhausted.

        Returns:
            List of QueryResult objects from executing the queries.
        """
        results: list[QueryResult] = []
        skipped_checkpoint = 0

        for query in queries:
            # Stop if deadline approaching -- leave time for extraction/dedup/output
            if self._deadline is not None and time.monotonic() >= self._deadline:
                logger.warning(
                    "%s: deadline reached after %d/%d queries, stopping to allow output",
                    scheduler.name,
                    len(results),
                    len(queries),
                )
                break

            # Skip if already completed in a previous run
            if self._checkpoint is not None and self._checkpoint.is_completed(query):
                skipped_checkpoint += 1
                continue

            result = await scheduler.execute(query)
            results.append(result)

            # Mark completed and save checkpoint after each query
            if self._checkpoint is not None:
                await self._checkpoint.mark_completed(query)
                await self._checkpoint.save()

            # Break early if budget exhausted
            budget = scheduler.remaining_budget
            if budget is not None and budget <= 0:
                logger.info(
                    "%s: budget exhausted after %d/%d queries, stopping",
                    scheduler.name,
                    len(results),
                    len(queries),
                )
                break

        if skipped_checkpoint > 0:
            logger.info(
                "%s: skipped %d queries from checkpoint",
                scheduler.name,
                skipped_checkpoint,
            )

        return results


def _tag_districts(
    articles: list[ArticleRef], districts: tuple[str, ...]
) -> list[ArticleRef]:
    """Tag articles with a district name from the query batch.

    Strategy:
    1. Single-district batch: assign all articles to that district
       (they were returned by a query targeting exactly that district).
    2. Multi-district batch: match by checking if the article title
       contains an English district name (case-insensitive substring).
    3. Unmatched articles keep district=None (post-extraction tagging
       in main.py will retry using full_text).

    Uses Pydantic's model_copy to create new frozen instances.
    """
    if not districts:
        return articles

    # Single-district batch: assign all articles directly
    if len(districts) == 1:
        return [
            article.model_copy(update={"district": districts[0]})
            for article in articles
        ]

    # Multi-district batch: match by English title
    tagged: list[ArticleRef] = []
    for article in articles:
        title_lower = article.title.lower()
        matched = None
        for d in districts:
            if d.lower() in title_lower:
                matched = d
                break
        if matched:
            tagged.append(article.model_copy(update={"district": matched}))
        else:
            tagged.append(article)
    return tagged


def tag_districts_from_text(
    articles: list[ArticleRef],
    regions: list[StateUT],
) -> list[ArticleRef]:
    """Post-extraction district tagging using title + full_text.

    For articles that still have ``district=None``, scans the combined
    title and full_text for English district names belonging to the
    article's state. This catches district mentions in regional-language
    articles where the body often includes English proper nouns.

    Articles that already have a district assigned are returned as-is.

    Args:
        articles: Articles (typically ``Article`` instances with full_text).
        regions: List of StateUT objects for district name lookup.

    Returns:
        New list with district fields populated where a match was found.
    """
    # Build state name → list of (district_name,) lookup
    state_districts: dict[str, list[str]] = {}
    for region in regions:
        if region.districts:
            state_districts[region.name] = [d.name for d in region.districts]

    tagged: list[ArticleRef] = []
    matched_count = 0

    for article in articles:
        # Already tagged -- keep as-is
        if article.district is not None:
            tagged.append(article)
            continue

        districts = state_districts.get(article.state, [])
        if not districts:
            tagged.append(article)
            continue

        # Build search text: title + full_text (if available)
        search_text = article.title.lower()
        full_text = getattr(article, "full_text", None)
        if full_text:
            search_text += " " + full_text.lower()

        # Find the first matching district name
        matched = None
        for d in districts:
            if d.lower() in search_text:
                matched = d
                break

        if matched:
            tagged.append(article.model_copy(update={"district": matched}))
            matched_count += 1
        else:
            tagged.append(article)

    if matched_count:
        logger.info(
            "Post-extraction district tagging: matched %d/%d untagged articles",
            matched_count,
            sum(1 for a in articles if a.district is None),
        )

    return tagged


async def tag_districts_with_llm(
    articles: list[ArticleRef],
    regions: list[StateUT],
    checker: RelevanceChecker,
) -> list[ArticleRef]:
    """Use LLM to identify districts for articles still untagged.

    Only processes articles with ``district=None``.  Sends each article's
    title + text to the LLM along with the state's district list.  The LLM
    identifies which single district the article is primarily about (or
    ``None`` if it covers multiple districts / the whole state).

    This is the final district tagging pass, run after the cheaper English
    text matching in :func:`tag_districts_from_text`.

    Args:
        articles: Articles (typically ``Article`` with full_text).
        regions: StateUT list for district name lookup.
        checker: An active RelevanceChecker instance.

    Returns:
        New list with district fields populated where the LLM found a match.
    """
    state_districts: dict[str, list[str]] = {}
    for region in regions:
        if region.districts:
            state_districts[region.name] = [d.name for d in region.districts]

    # Identify articles needing LLM tagging
    needs_llm: list[tuple[int, ArticleRef]] = []
    for i, article in enumerate(articles):
        if article.district is None and article.state in state_districts:
            needs_llm.append((i, article))

    if not needs_llm:
        return articles

    logger.info(
        "LLM district extraction: %d articles to check", len(needs_llm),
    )

    # Run LLM extraction concurrently
    async def _extract(article: ArticleRef) -> str | None:
        full_text = getattr(article, "full_text", None)
        return await checker.extract_district(
            article.title,
            full_text,
            article.state,
            state_districts[article.state],
        )

    tasks = [_extract(article) for _, article in needs_llm]
    results = await asyncio.gather(*tasks)

    # Build new list with LLM-tagged articles
    tagged = list(articles)  # shallow copy
    matched_count = 0
    for (idx, _article), district in zip(needs_llm, results):
        if district is not None:
            tagged[idx] = tagged[idx].model_copy(update={"district": district})
            matched_count += 1

    logger.info(
        "LLM district extraction: tagged %d/%d articles",
        matched_count,
        len(needs_llm),
    )

    return tagged
