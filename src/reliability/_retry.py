"""Rate-limit retry primitives for the heat news extraction pipeline.

Provides a ``RateLimitError`` exception for HTTP 429 responses and a
``with_rate_limit_retry`` decorator factory that wraps async functions
with tenacity exponential backoff + jitter.

Sources re-raise HTTP 429 as ``RateLimitError`` instead of returning
empty lists, enabling tenacity to catch and retry at the scheduler level.
All other HTTP errors continue to be handled by the source's existing
"never raises" contract.
"""

from __future__ import annotations

import logging

import tenacity

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when a news source receives an HTTP 429 rate-limit response.

    Attributes:
        status_code: The HTTP status code (always 429).
        source: Name of the source that was rate-limited.
    """

    def __init__(
        self,
        status_code: int,
        source: str,
        message: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.source = source
        super().__init__(message or f"HTTP {status_code} rate limit from {source}")


def is_rate_limit_error(exc: BaseException) -> bool:
    """Return True only for :class:`RateLimitError` exceptions."""
    return isinstance(exc, RateLimitError)


def with_rate_limit_retry(max_attempts: int = 5) -> tenacity.retry:
    """Return a tenacity retry decorator for rate-limit backoff.

    Uses exponential backoff with jitter:
    - Initial wait: 1 second
    - Maximum wait: 60 seconds
    - Jitter: up to 5 seconds
    - Retries only on :class:`RateLimitError`
    - Logs each retry attempt at WARNING level
    - Re-raises after *max_attempts* exhausted

    Usage::

        @with_rate_limit_retry()
        async def fetch_with_retry():
            ...
    """
    return tenacity.retry(
        wait=tenacity.wait_exponential_jitter(initial=1, max=60, jitter=5),
        stop=tenacity.stop_after_attempt(max_attempts),
        retry=tenacity.retry_if_exception(is_rate_limit_error),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
