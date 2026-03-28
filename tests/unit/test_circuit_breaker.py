"""Unit tests for CircuitBreaker (P2-2 — state transitions & resilience)."""
from __future__ import annotations

import time

import pytest

from backend.app.resilience.circuit_breaker import CircuitBreaker


@pytest.fixture
def breaker():
    """Fresh circuit breaker instance."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=1)


def test_circuit_breaker_init_closed(breaker):
    """Test circular breaker initializes in CLOSED state."""
    assert breaker.get_state("test_provider") == "closed"
    assert breaker.failure_count.get("test_provider", 0) == 0


def test_circuit_breaker_success_keeps_closed(breaker):
    """Test successful operation keeps breaker CLOSED."""
    breaker.record_success("test_provider")
    assert breaker.get_state("test_provider") == "closed"
    assert breaker.failure_count.get("test_provider", 0) == 0


def test_circuit_breaker_failure_increments_count(breaker):
    """Test failures increment counter."""
    breaker.record_failure("test_provider")
    assert breaker.failure_count.get("test_provider", 0) == 1
    assert breaker.get_state("test_provider") == "closed"

    breaker.record_failure("test_provider")
    assert breaker.failure_count.get("test_provider", 0) == 2
    assert breaker.get_state("test_provider") == "closed"


def test_circuit_breaker_opens_after_threshold(breaker):
    """Test breaker OPENS after failure threshold exceeded."""
    # Trigger 2 failures
    breaker.record_failure("test_provider")
    breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "closed"

    # Third failure should OPEN the breaker
    breaker.record_failure("test_provider")
    assert breaker.failure_count.get("test_provider", 0) == 3
    assert breaker.get_state("test_provider") == "open"


def test_circuit_breaker_open_blocks_requests(breaker):
    """Test is_open() returns True when OPEN."""
    # Open the breaker
    for _ in range(3):
        breaker.record_failure("test_provider")

    assert breaker.is_open("test_provider") is True


def test_circuit_breaker_success_resets_in_closed(breaker):
    """Test success in CLOSED state resets failure count."""
    breaker.record_failure("test_provider")
    breaker.record_failure("test_provider")
    assert breaker.failure_count.get("test_provider", 0) == 2

    # Success should reset counter
    breaker.record_success("test_provider")
    assert breaker.failure_count.get("test_provider", 0) == 0
    assert breaker.get_state("test_provider") == "closed"


def test_circuit_breaker_transitions_to_half_open_after_timeout(breaker):
    """Test breaker transitions to HALF_OPEN after recovery timeout."""
    # Open the breaker
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "open"

    # Wait for recovery timeout
    time.sleep(1.1)  # Slightly longer than recovery_timeout=1

    # Breaker should allow one test request (HALF_OPEN)
    assert breaker.get_state("test_provider") == "half_open"


def test_circuit_breaker_closes_on_half_open_success(breaker):
    """Test breaker CLOSES after successful request in HALF_OPEN state."""
    # Open and wait for timeout
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "open"

    time.sleep(1.1)
    assert breaker.get_state("test_provider") == "half_open"

    # Success in HALF_OPEN should close breaker
    breaker.record_success("test_provider")
    assert breaker.get_state("test_provider") == "closed"
    assert breaker.failure_count.get("test_provider", 0) == 0


def test_circuit_breaker_reopens_on_half_open_failure(breaker):
    """Test breaker OPENS again if failure during HALF_OPEN."""
    # Open and wait
    for _ in range(3):
        breaker.record_failure("test_provider")
    time.sleep(1.1)
    assert breaker.get_state("test_provider") == "half_open"

    # Failure in HALF_OPEN should reopen
    breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "open"


def test_circuit_breaker_multiple_cycles(breaker):
    """Test multiple open/close cycles."""
    # Cycle 1: CLOSED → OPEN
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "open"

    # Wait and transition to HALF_OPEN
    time.sleep(1.1)
    assert breaker.get_state("test_provider") == "half_open"

    # Success → CLOSED
    breaker.record_success("test_provider")
    assert breaker.get_state("test_provider") == "closed"

    # Cycle 2: CLOSED → OPEN again
    for _ in range(3):
        breaker.record_failure("test_provider")
    assert breaker.get_state("test_provider") == "open"

    # Wait and transition to HALF_OPEN
    time.sleep(1.1)
    assert breaker.get_state("test_provider") == "half_open"

    # Success → CLOSED
    breaker.record_success("test_provider")
    assert breaker.get_state("test_provider") == "closed"


def test_circuit_breaker_custom_threshold(breaker):
    """Test custom failure threshold."""
    custom_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=1)

    # Should remain CLOSED until 5 failures
    for i in range(1, 5):
        custom_breaker.record_failure("test_provider")
        assert custom_breaker.get_state("test_provider") == "closed", f"Failed at iteration {i}"

    # 5th failure should open
    custom_breaker.record_failure("test_provider")
    assert custom_breaker.get_state("test_provider") == "open"


def test_circuit_breaker_per_provider_isolation(breaker):
    """Test that circuit breaker tracks state per provider separately."""
    # Provider A fails 3 times → OPEN
    for _ in range(3):
        breaker.record_failure("provider_a")
    assert breaker.get_state("provider_a") == "open"

    # Provider B should be CLOSED independently
    assert breaker.get_state("provider_b") == "closed"

    # Success on provider B should have no effect on provider A
    breaker.record_success("provider_b")
    assert breaker.get_state("provider_a") == "open"
    assert breaker.get_state("provider_b") == "closed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
