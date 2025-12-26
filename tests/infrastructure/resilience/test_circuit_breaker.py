"""Tests for Circuit Breaker implementation."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerStats,
    CircuitState,
    circuit_breaker,
)


@pytest.fixture
def breaker_config():
    """Create circuit breaker configuration."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=1.0,
        failure_rate_threshold=0.5,
        minimum_requests=5,
        window_size=60.0,
    )


@pytest.fixture
def circuit_breaker_instance(breaker_config):
    """Create circuit breaker instance."""
    return CircuitBreaker("test_breaker", breaker_config)


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.success_threshold == 2
        assert config.timeout == 60
        assert config.failure_rate_threshold == 0.5
        assert config.minimum_requests == 10
        assert config.window_size == 60

    def test_custom_config(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=3,
            timeout=120,
            failure_rate_threshold=0.7,
            minimum_requests=20,
            window_size=120,
        )

        assert config.failure_threshold == 10
        assert config.success_threshold == 3
        assert config.timeout == 120
        assert config.failure_rate_threshold == 0.7
        assert config.minimum_requests == 20
        assert config.window_size == 120


class TestCircuitBreakerStats:
    """Test CircuitBreakerStats dataclass."""

    def test_default_stats(self):
        """Test default stats values."""
        stats = CircuitBreakerStats()

        assert stats.total_requests == 0
        assert stats.total_failures == 0
        assert stats.total_successes == 0
        assert stats.consecutive_failures == 0
        assert stats.consecutive_successes == 0
        assert stats.last_failure_time is None
        assert stats.last_success_time is None
        assert isinstance(stats.state_changed_at, datetime)
        assert stats.recent_requests == []


class TestCircuitBreakerError:
    """Test CircuitBreakerError exception."""

    def test_error_default_message(self):
        """Test error with default message."""
        error = CircuitBreakerError()

        assert str(error) == "Circuit breaker is OPEN"

    def test_error_custom_message(self):
        """Test error with custom message."""
        error = CircuitBreakerError("Custom error message")

        assert str(error) == "Custom error message"


class TestCircuitBreakerInit:
    """Test CircuitBreaker initialization."""

    def test_init_with_name(self):
        """Test initialization with name."""
        breaker = CircuitBreaker("test")

        assert breaker.name == "test"
        assert breaker.state == CircuitState.CLOSED
        assert isinstance(breaker.stats, CircuitBreakerStats)
        assert isinstance(breaker.config, CircuitBreakerConfig)

    def test_init_with_config(self, breaker_config):
        """Test initialization with custom config."""
        breaker = CircuitBreaker("test", breaker_config)

        assert breaker.config == breaker_config


class TestCircuitBreakerCall:
    """Test CircuitBreaker.call method."""

    def test_call_success_in_closed_state(self, circuit_breaker_instance):
        """Test successful call in CLOSED state."""
        mock_func = Mock(return_value="success")

        result = circuit_breaker_instance.call(mock_func)

        assert result == "success"
        mock_func.assert_called_once()
        assert circuit_breaker_instance.stats.total_successes == 1
        assert circuit_breaker_instance.stats.consecutive_successes == 1

    def test_call_with_arguments(self, circuit_breaker_instance):
        """Test call with function arguments."""
        mock_func = Mock(return_value="result")

        result = circuit_breaker_instance.call(mock_func, "arg1", "arg2", kwarg="value")

        mock_func.assert_called_once_with("arg1", "arg2", kwarg="value")
        assert result == "result"

    def test_call_failure_increments_stats(self, circuit_breaker_instance):
        """Test failed call increments failure stats."""
        mock_func = Mock(side_effect=ValueError("Test error"))

        with pytest.raises(ValueError):
            circuit_breaker_instance.call(mock_func)

        assert circuit_breaker_instance.stats.total_failures == 1
        assert circuit_breaker_instance.stats.consecutive_failures == 1

    def test_call_opens_on_threshold(self, circuit_breaker_instance):
        """Test circuit opens after failure threshold."""
        mock_func = Mock(side_effect=ValueError("Error"))

        # Fail enough times to open circuit
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_func)

        # Circuit should be OPEN
        assert circuit_breaker_instance.state == CircuitState.OPEN

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            circuit_breaker_instance.call(mock_func)

    def test_call_in_open_state_raises_error(self, circuit_breaker_instance):
        """Test call in OPEN state raises CircuitBreakerError."""
        circuit_breaker_instance.state = CircuitState.OPEN
        mock_func = Mock()

        with pytest.raises(CircuitBreakerError, match="Circuit breaker.*is OPEN"):
            circuit_breaker_instance.call(mock_func)

        mock_func.assert_not_called()

    def test_call_transitions_to_half_open_after_timeout(
        self, circuit_breaker_instance
    ):
        """Test circuit transitions to HALF_OPEN after timeout."""
        # Open the circuit
        circuit_breaker_instance.state = CircuitState.OPEN
        circuit_breaker_instance.stats.state_changed_at = datetime.now() - timedelta(
            seconds=circuit_breaker_instance.config.timeout + 1
        )

        mock_func = Mock(return_value="success")

        # Should transition to HALF_OPEN and allow call
        result = circuit_breaker_instance.call(mock_func)

        assert result == "success"
        assert circuit_breaker_instance.state in [
            CircuitState.HALF_OPEN,
            CircuitState.CLOSED,
        ]

    def test_call_in_half_open_limits_concurrency(self, circuit_breaker_instance):
        """Test HALF_OPEN state limits concurrent calls."""
        circuit_breaker_instance.state = CircuitState.HALF_OPEN

        # Acquire the lock
        circuit_breaker_instance._half_open_lock.acquire()

        mock_func = Mock()

        try:
            with pytest.raises(CircuitBreakerError, match="HALF_OPEN and busy"):
                circuit_breaker_instance.call(mock_func)

            mock_func.assert_not_called()
        finally:
            circuit_breaker_instance._half_open_lock.release()

    def test_call_half_open_to_closed_on_success(self, circuit_breaker_instance):
        """Test HALF_OPEN transitions to CLOSED after success threshold."""
        circuit_breaker_instance.state = CircuitState.HALF_OPEN
        mock_func = Mock(return_value="success")

        # Succeed enough times to close circuit
        for _ in range(circuit_breaker_instance.config.success_threshold):
            circuit_breaker_instance.call(mock_func)

        assert circuit_breaker_instance.state == CircuitState.CLOSED

    def test_call_half_open_to_open_on_failure(self, circuit_breaker_instance):
        """Test HALF_OPEN transitions back to OPEN on failure threshold."""
        circuit_breaker_instance.state = CircuitState.HALF_OPEN
        mock_func = Mock(side_effect=ValueError("Error"))

        # Need to hit failure threshold to transition to OPEN
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            try:
                circuit_breaker_instance.call(mock_func)
            except ValueError:
                pass

        # Should open again after hitting failure threshold
        assert circuit_breaker_instance.state == CircuitState.OPEN


class TestCircuitBreakerAsyncCall:
    """Test CircuitBreaker.async_call method."""

    @pytest.mark.asyncio
    async def test_async_call_success(self, circuit_breaker_instance):
        """Test successful async call."""

        async def async_func():
            await asyncio.sleep(0.01)
            return "async_result"

        result = await circuit_breaker_instance.async_call(async_func)

        assert result == "async_result"
        assert circuit_breaker_instance.stats.total_successes == 1

    @pytest.mark.asyncio
    async def test_async_call_failure(self, circuit_breaker_instance):
        """Test failed async call."""

        async def async_func():
            await asyncio.sleep(0.01)
            raise ValueError("Async error")

        with pytest.raises(ValueError):
            await circuit_breaker_instance.async_call(async_func)

        assert circuit_breaker_instance.stats.total_failures == 1

    @pytest.mark.asyncio
    async def test_async_call_with_arguments(self, circuit_breaker_instance):
        """Test async call with arguments."""

        async def async_func(x, y, z=None):
            await asyncio.sleep(0.01)
            return x + y + (z or 0)

        result = await circuit_breaker_instance.async_call(async_func, 1, 2, z=3)

        assert result == 6

    @pytest.mark.asyncio
    async def test_async_call_opens_on_threshold(self, circuit_breaker_instance):
        """Test async call opens circuit on threshold."""

        async def async_func():
            raise ValueError("Error")

        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                await circuit_breaker_instance.async_call(async_func)

        assert circuit_breaker_instance.state == CircuitState.OPEN


class TestCircuitBreakerStatsRecording:
    """Test stats recording methods."""

    def test_record_success(self, circuit_breaker_instance):
        """Test recording success."""
        mock_func = Mock(return_value="success")

        circuit_breaker_instance.call(mock_func)

        stats = circuit_breaker_instance.stats
        assert stats.total_requests == 1
        assert stats.total_successes == 1
        assert stats.consecutive_successes == 1
        assert stats.consecutive_failures == 0
        assert stats.last_success_time is not None

    def test_record_failure(self, circuit_breaker_instance):
        """Test recording failure."""
        mock_func = Mock(side_effect=ValueError("Error"))

        with pytest.raises(ValueError):
            circuit_breaker_instance.call(mock_func)

        stats = circuit_breaker_instance.stats
        assert stats.total_requests == 1
        assert stats.total_failures == 1
        assert stats.consecutive_failures == 1
        assert stats.consecutive_successes == 0
        assert stats.last_failure_time is not None

    def test_record_recent_requests(self, circuit_breaker_instance):
        """Test recent requests are recorded."""
        mock_success = Mock(return_value="success")
        mock_failure = Mock(side_effect=ValueError("Error"))

        circuit_breaker_instance.call(mock_success)
        with pytest.raises(ValueError):
            circuit_breaker_instance.call(mock_failure)

        assert len(circuit_breaker_instance.stats.recent_requests) == 2

    def test_record_recent_requests_cleanup(self, circuit_breaker_instance):
        """Test old recent requests are cleaned up."""
        # Create an old request
        old_time = datetime.now() - timedelta(
            seconds=circuit_breaker_instance.config.window_size + 1
        )
        circuit_breaker_instance.stats.recent_requests.append((old_time, True))

        # Add new request
        mock_func = Mock(return_value="success")
        circuit_breaker_instance.call(mock_func)

        # Old request should be removed
        assert all(
            ts
            > datetime.now()
            - timedelta(seconds=circuit_breaker_instance.config.window_size)
            for ts, _ in circuit_breaker_instance.stats.recent_requests
        )


class TestCircuitBreakerFailureRateDetection:
    """Test failure rate based circuit opening."""

    def test_opens_on_failure_rate(self):
        """Test circuit opens based on failure rate."""
        config = CircuitBreakerConfig(
            failure_threshold=100,  # High threshold
            failure_rate_threshold=0.5,
            minimum_requests=10,
        )
        breaker = CircuitBreaker("test", config)

        mock_success = Mock(return_value="success")
        mock_failure = Mock(side_effect=ValueError("Error"))

        # Success: 5, Failure: 6 = 54.5% failure rate
        for _ in range(5):
            breaker.call(mock_success)

        # Add failures - circuit may open during this loop
        for _ in range(6):
            try:
                breaker.call(mock_failure)
            except (ValueError, CircuitBreakerError):
                # Circuit may open during the loop, which is expected
                pass

        # Should be OPEN due to failure rate
        assert breaker.state == CircuitState.OPEN

    def test_does_not_open_below_minimum_requests(self):
        """Test circuit doesn't open below minimum requests."""
        config = CircuitBreakerConfig(
            failure_threshold=100,
            failure_rate_threshold=0.5,
            minimum_requests=10,
        )
        breaker = CircuitBreaker("test", config)

        mock_failure = Mock(side_effect=ValueError("Error"))

        # Only 5 requests (below minimum)
        for _ in range(5):
            with pytest.raises(ValueError):
                breaker.call(mock_failure)

        # Should still be CLOSED
        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerReset:
    """Test reset method."""

    def test_reset(self, circuit_breaker_instance):
        """Test reset restores initial state."""
        # Trigger some failures
        mock_failure = Mock(side_effect=ValueError("Error"))
        for _ in range(2):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_failure)

        # Reset
        circuit_breaker_instance.reset()

        # Should be back to initial state
        assert circuit_breaker_instance.state == CircuitState.CLOSED
        assert circuit_breaker_instance.stats.total_requests == 0
        assert circuit_breaker_instance.stats.total_failures == 0
        assert circuit_breaker_instance.stats.consecutive_failures == 0


class TestCircuitBreakerGetStatus:
    """Test get_status method."""

    def test_get_status(self, circuit_breaker_instance):
        """Test getting circuit breaker status."""
        status = circuit_breaker_instance.get_status()

        assert status["name"] == "test_breaker"
        assert status["state"] == "closed"
        assert status["total_requests"] == 0
        assert status["total_failures"] == 0
        assert status["total_successes"] == 0
        assert status["success_rate"] == 1.0
        assert "state_changed_at" in status

    def test_get_status_with_activity(self, circuit_breaker_instance):
        """Test status after some activity."""
        mock_success = Mock(return_value="success")
        mock_failure = Mock(side_effect=ValueError("Error"))

        circuit_breaker_instance.call(mock_success)
        with pytest.raises(ValueError):
            circuit_breaker_instance.call(mock_failure)

        status = circuit_breaker_instance.get_status()

        assert status["total_requests"] == 2
        assert status["total_successes"] == 1
        assert status["total_failures"] == 1
        assert status["success_rate"] == 0.5


class TestCircuitBreakerStateChangeCallbacks:
    """Test state change callbacks."""

    def test_add_state_change_callback(self, circuit_breaker_instance):
        """Test adding state change callback."""
        callback = Mock()

        circuit_breaker_instance.add_state_change_callback(callback)

        # Trigger state change
        mock_failure = Mock(side_effect=ValueError("Error"))
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_failure)

        # Callback should be called
        callback.assert_called()

    def test_multiple_callbacks(self, circuit_breaker_instance):
        """Test multiple callbacks are all called."""
        callback1 = Mock()
        callback2 = Mock()

        circuit_breaker_instance.add_state_change_callback(callback1)
        circuit_breaker_instance.add_state_change_callback(callback2)

        # Trigger state change
        mock_failure = Mock(side_effect=ValueError("Error"))
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_failure)

        callback1.assert_called()
        callback2.assert_called()

    def test_callback_error_does_not_break_circuit(self, circuit_breaker_instance):
        """Test callback error doesn't break circuit breaker."""
        callback = Mock(side_effect=Exception("Callback error"))

        circuit_breaker_instance.add_state_change_callback(callback)

        # Trigger state change
        mock_failure = Mock(side_effect=ValueError("Error"))
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_failure)

        # Circuit should still change state despite callback error
        assert circuit_breaker_instance.state == CircuitState.OPEN


class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator."""

    def test_decorator_sync_function(self):
        """Test decorator with synchronous function."""
        call_count = 0

        @circuit_breaker(name="test_sync")
        def sync_function():
            nonlocal call_count
            call_count += 1
            return "result"

        result = sync_function()

        assert result == "result"
        assert call_count == 1

    def test_decorator_with_config(self):
        """Test decorator with custom config."""
        config = CircuitBreakerConfig(failure_threshold=2)

        @circuit_breaker(name="test_config", config=config)
        def function():
            raise ValueError("Error")

        # Should open after 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                function()

        # Third call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            function()

    @pytest.mark.asyncio
    async def test_decorator_async_function(self):
        """Test decorator with async function."""
        call_count = 0

        @circuit_breaker(name="test_async")
        async def async_function():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "async_result"

        result = await async_function()

        assert result == "async_result"
        assert call_count == 1

    def test_decorator_preserves_function_name(self):
        """Test decorator preserves function metadata."""

        @circuit_breaker()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_decorator_with_arguments(self):
        """Test decorator with function arguments."""

        @circuit_breaker()
        def function_with_args(x, y, z=None):
            return x + y + (z or 0)

        result = function_with_args(1, 2, z=3)

        assert result == 6

    def test_decorator_opens_circuit_on_failures(self):
        """Test decorator opens circuit on repeated failures."""
        config = CircuitBreakerConfig(failure_threshold=3)

        @circuit_breaker(config=config)
        def failing_function():
            raise ValueError("Always fails")

        for _ in range(3):
            with pytest.raises(ValueError):
                failing_function()

        # Next call should raise CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_function()


class TestCircuitBreakerLogging:
    """Test circuit breaker logging."""

    @patch("src.infrastructure.resilience.circuit_breaker.logger")
    def test_logs_state_transitions(self, mock_logger, circuit_breaker_instance):
        """Test state transitions are logged."""
        mock_failure = Mock(side_effect=ValueError("Error"))

        # Trigger state change to OPEN
        for _ in range(circuit_breaker_instance.config.failure_threshold):
            with pytest.raises(ValueError):
                circuit_breaker_instance.call(mock_failure)

        # Verify warning log for OPEN
        mock_logger.warning.assert_called()

    @patch("src.infrastructure.resilience.circuit_breaker.logger")
    def test_logs_success_and_failure(self, mock_logger, circuit_breaker_instance):
        """Test success and failure are logged."""
        mock_success = Mock(return_value="success")
        mock_failure = Mock(side_effect=ValueError("Error"))

        circuit_breaker_instance.call(mock_success)
        with pytest.raises(ValueError):
            circuit_breaker_instance.call(mock_failure)

        # Verify debug logs
        assert mock_logger.debug.call_count >= 2


class TestCircuitBreakerEdgeCases:
    """Test edge cases."""

    def test_success_rate_with_no_requests(self, circuit_breaker_instance):
        """Test success rate with no requests."""
        status = circuit_breaker_instance.get_status()

        assert status["success_rate"] == 1.0

    def test_concurrent_calls_in_half_open(self, circuit_breaker_instance):
        """Test concurrent calls in HALF_OPEN state."""
        circuit_breaker_instance.state = CircuitState.HALF_OPEN

        # First call should succeed
        circuit_breaker_instance._half_open_lock.acquire()

        # Second concurrent call should fail
        with pytest.raises(CircuitBreakerError, match="HALF_OPEN and busy"):
            circuit_breaker_instance.call(Mock())

        circuit_breaker_instance._half_open_lock.release()

    def test_transition_to_half_open_resets_counters(self, circuit_breaker_instance):
        """Test transition to HALF_OPEN resets counters."""
        circuit_breaker_instance.stats.consecutive_failures = 5
        circuit_breaker_instance.stats.consecutive_successes = 3

        circuit_breaker_instance._transition_to_half_open()

        assert circuit_breaker_instance.stats.consecutive_failures == 0
        assert circuit_breaker_instance.stats.consecutive_successes == 0

    def test_transition_to_closed_resets_counters(self, circuit_breaker_instance):
        """Test transition to CLOSED resets counters."""
        circuit_breaker_instance.stats.consecutive_failures = 5
        circuit_breaker_instance.stats.consecutive_successes = 3

        circuit_breaker_instance._transition_to_closed()

        assert circuit_breaker_instance.stats.consecutive_failures == 0
        assert circuit_breaker_instance.stats.consecutive_successes == 0

    def test_transition_to_open_resets_counters(self, circuit_breaker_instance):
        """Test transition to OPEN resets counters."""
        circuit_breaker_instance.stats.consecutive_failures = 5
        circuit_breaker_instance.stats.consecutive_successes = 3

        circuit_breaker_instance._transition_to_open()

        assert circuit_breaker_instance.stats.consecutive_failures == 0
        assert circuit_breaker_instance.stats.consecutive_successes == 0
