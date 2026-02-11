"""Reliability primitives for the heat news extraction pipeline.

Re-exports the core reliability components:

- :class:`CircuitBreaker` -- per-source circuit breaker (closed/open/half_open)
- :class:`RateLimitError` -- exception for HTTP 429 rate-limit responses
- :func:`with_rate_limit_retry` -- tenacity decorator factory for rate-limit backoff
- :class:`CheckpointStore` -- query completion tracking with JSON persistence
"""

from ._checkpoint import CheckpointStore
from ._circuit_breaker import CircuitBreaker
from ._retry import RateLimitError, with_rate_limit_retry

__all__ = [
    "CheckpointStore",
    "CircuitBreaker",
    "RateLimitError",
    "with_rate_limit_retry",
]
