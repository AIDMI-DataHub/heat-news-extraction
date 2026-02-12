"""Multi-LLM consensus relevance checker.

Runs multiple LLM checkers in parallel and uses majority vote
to determine relevance. An article is relevant only if the
majority of checkers agree it is relevant.
"""

from __future__ import annotations

import asyncio
import logging

from src.models.article import ArticleRef
from src.relevance._base import RelevanceChecker

logger = logging.getLogger(__name__)


class ConsensusChecker(RelevanceChecker):
    """Combines multiple LLM checkers with majority-vote consensus.

    Each article title is checked by all checkers concurrently.
    An article is kept only if more than half the checkers say "Yes".

    Parameters
    ----------
    checkers:
        List of RelevanceChecker instances to use for voting.
    """

    def __init__(self, checkers: list[RelevanceChecker]) -> None:
        # Don't use base class rate limiting -- each sub-checker has its own
        super().__init__(max_concurrent=100, min_interval=0.0)
        self._checkers = checkers

    async def _call_llm(self, system: str, user: str) -> str:
        # Not used directly -- consensus overrides filter_refs
        raise NotImplementedError

    async def _check_with_consensus(
        self, title: str, state: str = "", district: str | None = None,
    ) -> bool:
        """Check a single title against all checkers, return majority vote."""
        tasks = [checker.check_relevance(title, state=state, district=district) for checker in self._checkers]
        results = await asyncio.gather(*tasks)
        yes_count = sum(1 for r in results if r)
        majority = len(self._checkers) / 2
        is_relevant = yes_count > majority
        logger.debug(
            "Consensus: '%s' -> %d/%d yes (%s)",
            title[:50],
            yes_count,
            len(self._checkers),
            "keep" if is_relevant else "drop",
        )
        return is_relevant

    async def filter_refs(self, refs: list[ArticleRef]) -> list[ArticleRef]:
        """Filter refs using multi-LLM consensus voting."""
        if not refs:
            return refs

        logger.info(
            "Multi-LLM consensus check: %d refs, %d checkers",
            len(refs),
            len(self._checkers),
        )

        tasks = [self._check_with_consensus(r.title, state=r.state, district=r.district) for r in refs]
        results = await asyncio.gather(*tasks)

        relevant = [r for r, is_relevant in zip(refs, results) if is_relevant]
        dropped = len(refs) - len(relevant)

        logger.info(
            "Consensus filter: %d -> %d refs (dropped %d by majority vote)",
            len(refs),
            len(relevant),
            dropped,
        )

        return relevant

    async def close(self) -> None:
        """Close all sub-checkers."""
        for checker in self._checkers:
            await checker.close()
