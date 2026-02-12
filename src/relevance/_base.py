"""Abstract base for LLM relevance checkers."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

from src.models.article import ArticleRef
from src.relevance._prompt import build_prompt

logger = logging.getLogger(__name__)


class RelevanceChecker(ABC):
    """Base class for LLM-based relevance checking.

    Subclasses implement :meth:`_call_llm` for their specific API.
    This base handles batching, rate limiting, and error recovery.

    The primary entry point is :meth:`filter_refs` which checks article
    titles BEFORE extraction to avoid wasting time extracting irrelevant
    articles.

    Parameters
    ----------
    max_concurrent:
        Maximum parallel API requests.
    min_interval:
        Minimum seconds between requests (for rate limiting).
    """

    def __init__(self, max_concurrent: int = 5, min_interval: float = 0.1) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._min_interval = min_interval
        self._last_call = 0.0

    @abstractmethod
    async def _call_llm(self, system: str, user: str) -> str:
        """Send a prompt to the LLM and return the raw response text.

        Must be implemented by each provider subclass.
        Should raise on transient errors (will be caught by the caller).
        """

    async def check_relevance(
        self,
        title: str,
        text: str | None = None,
        state: str = "",
        district: str | None = None,
    ) -> bool:
        """Check if an article with this title (and optional text) is relevant."""
        from src.relevance._prompt import SYSTEM_PROMPT

        prompt = build_prompt(title, text, state=state, district=district)

        async with self._semaphore:
            # Rate limiting
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

            try:
                response = await self._call_llm(SYSTEM_PROMPT, prompt)
                answer = response.strip().lower()
                return answer.startswith("yes")
            except Exception:
                logger.warning(
                    "LLM relevance check failed for '%s', keeping article",
                    title[:60],
                    exc_info=True,
                )
                # On failure, keep the article (fail-open)
                return True

    async def filter_refs(self, refs: list[ArticleRef]) -> list[ArticleRef]:
        """Filter article refs by LLM relevance check on titles.

        This runs BEFORE extraction -- only titles are checked.
        Articles that pass this filter proceed to full extraction.
        On any LLM error, the ref is kept (fail-open policy).
        """
        if not refs:
            return refs

        logger.info("LLM relevance check: %d refs to check (title-only)", len(refs))

        # Run checks concurrently
        tasks = [self.check_relevance(r.title, state=r.state, district=r.district) for r in refs]
        results = await asyncio.gather(*tasks)

        relevant = [r for r, is_relevant in zip(refs, results) if is_relevant]
        dropped = len(refs) - len(relevant)

        logger.info(
            "LLM relevance filter: %d -> %d refs (dropped %d irrelevant)",
            len(refs),
            len(relevant),
            dropped,
        )

        return relevant

    async def extract_district(
        self,
        title: str,
        text: str | None,
        state: str,
        districts: list[str],
    ) -> str | None:
        """Use LLM to identify which district an article is primarily about.

        Sends the article title, text preview, state, and district list to the
        LLM.  Returns the matched district name or None if the article is about
        the state generally (mentions multiple districts or none).

        On any LLM error, returns None (fail-safe: article stays at state level).
        """
        district_list = ", ".join(districts)
        system = (
            "You extract geographic information from Indian news articles. "
            "You can read all Indian languages and scripts."
        )
        user = (
            f"Which single district in {state} is this article PRIMARILY about?\n"
            f"Districts: {district_list}\n\n"
            f"Title: {title}\n"
            f"Text: {(text or '')[:500]}\n\n"
            "Rules:\n"
            "- Reply with ONLY the district name from the list above.\n"
            "- If the article mentions multiple districts or is about the "
            "state as a whole, reply ONLY \"None\".\n"
            "- If you cannot determine the district, reply ONLY \"None\"."
        )

        async with self._semaphore:
            now = time.monotonic()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

            try:
                response = await self._call_llm(system, user)
                answer = response.strip().strip('"').strip("'")
                if answer.lower() == "none":
                    return None
                # Match response to a known district name (case-insensitive)
                for d in districts:
                    if d.lower() == answer.lower():
                        return d
                # Partial match (LLM might return slightly different form)
                for d in districts:
                    if d.lower() in answer.lower() or answer.lower() in d.lower():
                        return d
                return None
            except Exception:
                logger.warning(
                    "LLM district extraction failed for '%s'",
                    title[:60],
                    exc_info=True,
                )
                return None

    async def close(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
