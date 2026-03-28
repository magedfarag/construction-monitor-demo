"""In-process circuit breaker for external provider calls.

States: CLOSED (normal) → OPEN (after N failures) → HALF-OPEN (probe) → CLOSED

Thread-safe via threading.Lock.  State is per-process; in a multi-worker
deployment each worker tracks its own state independently.  For shared state
across workers, replace _State with Redis-backed storage.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

log = logging.getLogger(__name__)


class CBState(str, Enum):
    CLOSED    = "closed"    # normal operation
    OPEN      = "open"      # blocking calls after too many failures
    HALF_OPEN = "half_open" # allowing one probe request


@dataclass
class _ProviderState:
    state:          CBState = CBState.CLOSED
    failure_count:  int     = 0
    last_failure_ts: float  = 0.0
    lock: threading.Lock    = field(default_factory=threading.Lock, repr=False)


class CircuitBreaker:
    """Circuit breaker registry, one entry per provider name."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout  = recovery_timeout
        self._states: Dict[str, _ProviderState] = {}

    def _get(self, provider: str) -> _ProviderState:
        if provider not in self._states:
            self._states[provider] = _ProviderState()
        return self._states[provider]

    def is_open(self, provider: str) -> bool:
        """Return True if calls to *provider* should be blocked."""
        ps = self._get(provider)
        with ps.lock:
            if ps.state == CBState.OPEN:
                if time.monotonic() - ps.last_failure_ts >= self._recovery_timeout:
                    ps.state = CBState.HALF_OPEN
                    log.info("Circuit breaker HALF-OPEN for %s", provider)
                    return False   # allow probe
                return True
            return False

    def record_success(self, provider: str) -> None:
        ps = self._get(provider)
        with ps.lock:
            if ps.state != CBState.CLOSED:
                log.info("Circuit breaker CLOSED for %s after success", provider)
            ps.state         = CBState.CLOSED
            ps.failure_count = 0

    def record_failure(self, provider: str) -> None:
        ps = self._get(provider)
        with ps.lock:
            ps.failure_count  += 1
            ps.last_failure_ts = time.monotonic()
            if ps.state == CBState.HALF_OPEN or ps.failure_count >= self._failure_threshold:
                ps.state = CBState.OPEN
                log.warning(
                    "Circuit breaker OPEN for %s (%d failures)", provider, ps.failure_count
                )

    def status(self, provider: str) -> CBState:
        return self._get(provider).state
