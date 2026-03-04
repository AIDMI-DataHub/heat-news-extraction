"""Fallback relevance checker that switches providers on persistent failure."""

from __future__ import annotations

import logging

from src.relevance._base import RelevanceChecker

logger = logging.getLogger(__name__)

# Switch to fallback after this many consecutive failures on the primary.
_FAILURE_THRESHOLD = 5


class FallbackChecker(RelevanceChecker):
    """Wraps a primary and fallback checker.

    Uses the primary checker by default.  If the primary fails
    ``_FAILURE_THRESHOLD`` times consecutively, switches all subsequent
    calls to the fallback for the rest of the pipeline run.

    Parameters
    ----------
    primary:
        First-choice checker (e.g. OpenAI).
    fallback:
        Backup checker used when primary is unavailable (e.g. Gemini).
    """

    def __init__(self, primary: RelevanceChecker, fallback: RelevanceChecker) -> None:
        # Inherit concurrency settings from the active checker
        super().__init__(
            max_concurrent=primary._semaphore._value,
            min_interval=primary._min_interval,
        )
        self._primary = primary
        self._fallback = fallback
        self._consecutive_failures = 0
        self._using_fallback = False

    @property
    def active_checker(self) -> RelevanceChecker:
        return self._fallback if self._using_fallback else self._primary

    async def _call_llm(self, system: str, user: str) -> str:
        if self._using_fallback:
            return await self._fallback._call_llm(system, user)

        try:
            result = await self._primary._call_llm(system, user)
            self._consecutive_failures = 0
            return result
        except Exception:
            self._consecutive_failures += 1
            if self._consecutive_failures >= _FAILURE_THRESHOLD:
                logger.warning(
                    "Primary LLM failed %d times consecutively, "
                    "switching to fallback for remaining calls",
                    self._consecutive_failures,
                )
                self._using_fallback = True
                # Re-apply fallback's concurrency settings
                self._semaphore = self._fallback._semaphore
                self._min_interval = self._fallback._min_interval
            raise

    async def close(self) -> None:
        await self._primary.close()
        await self._fallback.close()
