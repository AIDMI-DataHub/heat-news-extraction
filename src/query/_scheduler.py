"""Rate-limit-aware source scheduling for the heat news extraction pipeline.

Provides per-source rate limiting (PerSecondLimiter, WindowLimiter) and a
SourceScheduler wrapper that enforces daily budgets, rolling windows, and
per-request delays.  Factory functions create pre-configured schedulers for
Google News, NewsData.io, and GNews.

The SourceScheduler.execute() method **never raises** -- it always returns a
QueryResult, using ``success=False`` for transport/parse errors and
``success=True`` with a descriptive ``error`` field for expected skip
conditions (budget exhaustion, unsupported language).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

from ._models import Query, QueryResult

if TYPE_CHECKING:
    from src.reliability._circuit_breaker import CircuitBreaker
    from src.sources._protocol import NewsSource

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-second rate limiter
# ---------------------------------------------------------------------------
class PerSecondLimiter:
    """Simple per-second rate limiter using an asyncio lock.

    Enforces a minimum interval between successive ``acquire()`` calls,
    with optional random jitter to avoid thundering-herd effects when
    multiple schedulers start simultaneously.

    Args:
        max_per_second: Maximum requests per second (e.g. 1.5 means one
            request every ~0.67 s).
        jitter: Maximum additional random delay in seconds added after
            each wait (uniform distribution ``[0, jitter]``).
    """

    def __init__(self, max_per_second: float, jitter: float = 0.0) -> None:
        self._interval: float = 1.0 / max_per_second
        self._jitter: float = jitter
        self._lock: asyncio.Lock = asyncio.Lock()
        self._last: float = 0.0  # monotonic timestamp of last acquire

    async def acquire(self) -> None:
        """Wait until the next request slot is available."""
        async with self._lock:
            now = time.monotonic()
            wait = self._last + self._interval - now
            if wait > 0:
                await asyncio.sleep(wait + random.uniform(0, self._jitter))
            self._last = time.monotonic()


# ---------------------------------------------------------------------------
# Rolling window rate limiter
# ---------------------------------------------------------------------------
class WindowLimiter:
    """Rolling-window rate limiter (e.g. 30 requests per 15 minutes).

    Tracks request timestamps and blocks ``acquire()`` until the oldest
    request in the window has expired when the window is full.

    Args:
        max_requests: Maximum number of requests allowed within the window.
        window_seconds: Length of the rolling window in seconds.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max: int = max_requests
        self._window: int = window_seconds
        self._timestamps: list[float] = []

    def _prune(self) -> None:
        """Remove timestamps that have fallen outside the window."""
        cutoff = time.monotonic() - self._window
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    async def acquire(self) -> None:
        """Wait until a request slot is available in the current window."""
        self._prune()
        if len(self._timestamps) >= self._max:
            # Wait until the oldest request falls outside the window
            oldest = self._timestamps[0]
            wait = oldest + self._window - time.monotonic() + 0.1
            if wait > 0:
                logger.debug(
                    "WindowLimiter: window full (%d/%d), sleeping %.1fs",
                    len(self._timestamps),
                    self._max,
                    wait,
                )
                await asyncio.sleep(wait)
            self._prune()
        self._timestamps.append(time.monotonic())

    @property
    def exhausted_in_window(self) -> bool:
        """Return True if the rolling window is currently full."""
        self._prune()
        return len(self._timestamps) >= self._max


# ---------------------------------------------------------------------------
# Source scheduler
# ---------------------------------------------------------------------------
class SourceScheduler:
    """Rate-limit-aware wrapper around a :class:`NewsSource`.

    Combines daily budget tracking, per-second delay, rolling-window
    enforcement, concurrency limiting, language filtering, and circuit
    breaker protection into a single ``execute()`` call that **never raises**.

    Args:
        source: The underlying NewsSource to wrap.
        name: Human-readable source name (used in logs and QueryResult).
        daily_limit: Maximum requests per day, or ``None`` for unlimited.
        per_second_limiter: Optional per-request delay limiter.
        window_limiter: Optional rolling-window limiter.
        supported_languages: Frozenset of supported language codes, or
            ``None`` to accept all languages.
        concurrency: Maximum number of concurrent requests (semaphore size).
        circuit_breaker: Optional per-source circuit breaker.  When open,
            queries are skipped immediately (fail fast, before budget check).
    """

    def __init__(
        self,
        source: NewsSource,
        name: str,
        daily_limit: int | None,
        per_second_limiter: PerSecondLimiter | None = None,
        window_limiter: WindowLimiter | None = None,
        supported_languages: frozenset[str] | None = None,
        concurrency: int = 1,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._source = source
        self._name = name
        self._daily_limit = daily_limit
        self._per_second_limiter = per_second_limiter
        self._window_limiter = window_limiter
        self._supported_languages = supported_languages
        self._daily_count: int = 0
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(concurrency)
        self._circuit_breaker = circuit_breaker

    # -- Public API --------------------------------------------------------

    async def execute(self, query: Query) -> QueryResult:
        """Execute *query* against the wrapped source with rate limiting.

        Returns a :class:`QueryResult` in all cases.  On transport or parse
        errors, ``success`` is ``False`` and ``error`` contains a description.
        Budget exhaustion, unsupported-language, and circuit-breaker-open
        skips are reported with ``success=True`` and a descriptive ``error``
        field (these are expected conditions, not failures).

        This method **never raises**.
        """
        # 0. Circuit breaker check (before budget, before rate limiter -- fail fast)
        if self._circuit_breaker is not None and self._circuit_breaker.is_open:
            logger.debug("%s: circuit breaker open, skipping query", self._name)
            return QueryResult(
                query=query,
                source_name=self._name,
                articles=[],
                success=True,
                error="circuit_breaker_open",
            )

        # 1. Budget check -- no HTTP request if exhausted
        if self._is_budget_exhausted():
            logger.debug("%s: budget exhausted, skipping query", self._name)
            return QueryResult(
                query=query,
                source_name=self._name,
                articles=[],
                success=True,
                error="budget_exhausted",
            )

        # 2. Language check
        if not self.supports_language(query.language):
            logger.debug(
                "%s: language %s not supported, skipping",
                self._name,
                query.language,
            )
            return QueryResult(
                query=query,
                source_name=self._name,
                articles=[],
                success=True,
                error="unsupported_language",
            )

        # 3-5. Rate-limited execution under semaphore
        try:
            async with self._semaphore:
                if self._per_second_limiter:
                    await self._per_second_limiter.acquire()
                if self._window_limiter:
                    await self._window_limiter.acquire()

                # 6. Call underlying source with tenacity retry for rate limits
                from src.reliability._retry import RateLimitError, with_rate_limit_retry

                @with_rate_limit_retry()
                async def _call_source() -> list:
                    return await self._source.search(
                        query.query_string,
                        query.language,
                        state=query.state,
                        search_term=query.query_string,
                    )

                articles = await _call_source()

            # 7. Increment daily count (after request, before result processing)
            self._daily_count += 1

            # 8. Record circuit breaker success
            if self._circuit_breaker is not None:
                self._circuit_breaker.record_success()

            # 9. Return successful result
            return QueryResult(
                query=query,
                source_name=self._name,
                articles=articles,
                success=True,
            )

        except Exception as exc:
            # 10. Record circuit breaker failure
            if self._circuit_breaker is not None:
                self._circuit_breaker.record_failure()

            # 11. Never raise -- return error result
            logger.warning(
                "%s: query failed: %s",
                self._name,
                exc,
                exc_info=True,
            )
            return QueryResult(
                query=query,
                source_name=self._name,
                articles=[],
                success=False,
                error=str(exc),
            )

    # -- Budget & language helpers -----------------------------------------

    def _is_budget_exhausted(self) -> bool:
        """Return True if the daily request budget has been used up."""
        return (
            self._daily_limit is not None
            and self._daily_count >= self._daily_limit
        )

    def supports_language(self, lang: str) -> bool:
        """Return True if *lang* is supported (or all languages accepted)."""
        return self._supported_languages is None or lang in self._supported_languages

    @property
    def remaining_budget(self) -> int | None:
        """Remaining daily budget, or ``None`` if unlimited."""
        if self._daily_limit is None:
            return None
        return max(0, self._daily_limit - self._daily_count)

    @property
    def name(self) -> str:
        """Human-readable source name."""
        return self._name


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------
def create_google_scheduler(
    source: NewsSource,
    circuit_breaker: CircuitBreaker | None = None,
) -> SourceScheduler:
    """Pre-configured scheduler for Google News RSS (unlimited, 5 concurrent, ~1.5/s with jitter)."""
    return SourceScheduler(
        source=source,
        name="google_news",
        daily_limit=None,
        per_second_limiter=PerSecondLimiter(max_per_second=1.5, jitter=0.3),
        concurrency=5,
        circuit_breaker=circuit_breaker,
    )


def create_newsdata_scheduler(
    source: NewsSource,
    circuit_breaker: CircuitBreaker | None = None,
) -> SourceScheduler:
    """Pre-configured scheduler for NewsData.io (200/day, 30/15min window, 10/s)."""
    return SourceScheduler(
        source=source,
        name="newsdata",
        daily_limit=200,
        per_second_limiter=PerSecondLimiter(max_per_second=10.0),
        window_limiter=WindowLimiter(max_requests=30, window_seconds=900),
        supported_languages=frozenset(
            {"en", "hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "or", "pa", "as", "ur", "ne"}
        ),
        circuit_breaker=circuit_breaker,
    )


def create_gnews_scheduler(
    source: NewsSource,
    circuit_breaker: CircuitBreaker | None = None,
) -> SourceScheduler:
    """Pre-configured scheduler for GNews (100/day, 1/s)."""
    return SourceScheduler(
        source=source,
        name="gnews",
        daily_limit=100,
        per_second_limiter=PerSecondLimiter(max_per_second=1.0),
        supported_languages=frozenset(
            {"en", "hi", "bn", "ta", "te", "mr", "ml", "pa"}
        ),
        circuit_breaker=circuit_breaker,
    )
