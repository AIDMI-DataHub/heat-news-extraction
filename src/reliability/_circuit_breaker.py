"""Per-source circuit breaker for the heat news extraction pipeline.

Implements a three-state circuit breaker (closed -> open -> half_open -> closed)
that tracks consecutive failures per news source and temporarily halts queries
to a source when failures exceed a configurable threshold.

State transitions:
- **closed** (normal): All requests pass through.  Failures increment counter.
- **open** (tripped): All requests are short-circuited.  After *reset_timeout*
  elapses, transitions to half_open.
- **half_open** (testing): One request is allowed through.  Success -> closed;
  failure -> open again.

Uses ``time.monotonic()`` for all timing (project convention from Phase 6).
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Per-source circuit breaker (closed -> open -> half_open -> closed).

    Args:
        name: Human-readable name for logging (e.g. ``"google_news"``).
        failure_threshold: Number of consecutive failures before opening.
        reset_timeout: Seconds to wait in *open* state before trying half_open.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: str = "closed"

    # -- Properties -----------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """Return True if the circuit is open (requests should be skipped).

        If the circuit is open and the reset timeout has elapsed, transition
        to half_open and return False (allow one test request through).
        """
        if self._state == "open":
            if time.monotonic() - self._last_failure_time >= self._reset_timeout:
                self._state = "half_open"
                logger.info(
                    "%s circuit breaker: open -> half_open (testing)",
                    self._name,
                )
                return False
            return True
        return False

    @property
    def state(self) -> str:
        """Return the current circuit breaker state (for logging/debugging)."""
        return self._state

    # -- Recording ------------------------------------------------------------

    def record_success(self) -> None:
        """Record a successful request.  Resets failure counter and closes."""
        if self._state == "half_open":
            logger.info(
                "%s circuit breaker: half_open -> closed (recovered)",
                self._name,
            )
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed request.  Opens the circuit after threshold."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = "open"
            logger.warning(
                "%s circuit breaker OPEN after %d consecutive failures",
                self._name,
                self._failure_count,
            )
