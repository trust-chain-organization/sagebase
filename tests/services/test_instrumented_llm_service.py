"""Tests for InstrumentedLLMService - metrics wrapper for LLMService."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain.schema import HumanMessage

from src.services.instrumented_llm_service import InstrumentedLLMService
from src.services.llm_service import LLMService


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    mock = MagicMock(spec=LLMService)
    mock.model_name = "gemini-2.0-flash"
    mock.temperature = 0.1
    # Mock create_simple_chain to return a mock chain
    mock_chain = Mock()
    mock_chain.content = "Mocked LLM response"
    mock.create_simple_chain.return_value = mock_chain
    mock.invoke_with_retry.return_value = mock_chain
    # Mock invoke_prompt
    mock_response = Mock()
    mock_response.content = "Mocked template response"
    mock.invoke_prompt.return_value = mock_response
    return mock


@pytest.fixture
def instrumented_service(mock_llm_service):
    """Create instrumented LLM service."""
    return InstrumentedLLMService(mock_llm_service)


class TestInstrumentedLLMServiceInit:
    """Test InstrumentedLLMService initialization."""

    def test_init_with_llm_service(self, mock_llm_service):
        """Test initialization with LLM service."""
        service = InstrumentedLLMService(mock_llm_service)

        assert service._llm_service == mock_llm_service
        assert service.api_calls is not None
        assert service.api_duration is not None
        assert service.tokens_used is not None
        assert service.model_latency is not None
        assert service.token_histogram is not None

    def test_setup_metrics(self, mock_llm_service):
        """Test metrics are properly initialized."""
        service = InstrumentedLLMService(mock_llm_service)

        # Verify all metrics are created
        assert hasattr(service, "api_calls")
        assert hasattr(service, "api_duration")
        assert hasattr(service, "tokens_used")
        assert hasattr(service, "model_latency")
        assert hasattr(service, "token_histogram")


class TestInstrumentedLLMServiceInvoke:
    """Test invoke method with instrumentation."""

    def test_invoke_success(self, instrumented_service, mock_llm_service):
        """Test successful invoke records metrics."""
        messages = [HumanMessage(content="Test prompt")]

        result = instrumented_service.invoke(messages)

        # Verify result
        assert result == "Mocked LLM response"

        # Verify LLM service was called
        mock_llm_service.create_simple_chain.assert_called_once()
        mock_llm_service.invoke_with_retry.assert_called_once()

    def test_invoke_with_string_content(self, instrumented_service):
        """Test invoke handles string message content."""
        messages = [HumanMessage(content="Simple text")]

        result = instrumented_service.invoke(messages)

        assert result == "Mocked LLM response"

    def test_invoke_with_non_string_content(self, instrumented_service):
        """Test invoke handles non-string message content."""
        mock_message = Mock()
        mock_message.content = ["Part1", "Part2"]

        result = instrumented_service.invoke([mock_message])

        assert result == "Mocked LLM response"

    def test_invoke_with_message_without_content(self, instrumented_service):
        """Test invoke handles messages without content attribute."""
        mock_message = Mock(spec=[])  # No content attribute
        del mock_message.content

        result = instrumented_service.invoke([mock_message])

        assert result == "Mocked LLM response"

    def test_invoke_with_temperature(self, instrumented_service):
        """Test invoke with custom temperature."""
        messages = [HumanMessage(content="Test")]

        result = instrumented_service.invoke(messages, temperature=0.5)

        assert result == "Mocked LLM response"

    def test_invoke_with_max_tokens(self, instrumented_service):
        """Test invoke with max_tokens parameter."""
        messages = [HumanMessage(content="Test")]

        result = instrumented_service.invoke(messages, max_tokens=100)

        assert result == "Mocked LLM response"

    def test_invoke_with_kwargs(self, instrumented_service):
        """Test invoke with additional kwargs."""
        messages = [HumanMessage(content="Test")]

        result = instrumented_service.invoke(
            messages, temperature=0.7, max_tokens=500, custom_param="value"
        )

        assert result == "Mocked LLM response"

    def test_invoke_records_success_metrics(self, instrumented_service):
        """Test invoke records metrics on success."""
        messages = [HumanMessage(content="Test prompt")]

        with (
            patch.object(instrumented_service.api_calls, "add") as mock_add,
            patch.object(instrumented_service.api_duration, "record") as mock_duration,
            patch.object(instrumented_service.tokens_used, "add") as mock_tokens,
        ):
            instrumented_service.invoke(messages)

            # Verify metrics were recorded
            mock_add.assert_called_once()
            mock_duration.assert_called_once()
            mock_tokens.assert_called_once()

            # Verify success status in duration metric
            duration_call_kwargs = mock_duration.call_args[1]
            assert duration_call_kwargs["attributes"]["status"] == "success"

    def test_invoke_handles_exception(self, instrumented_service, mock_llm_service):
        """Test invoke handles and records exceptions."""
        messages = [HumanMessage(content="Test")]
        mock_llm_service.invoke_with_retry.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError, match="Test error"):
            instrumented_service.invoke(messages)

    def test_invoke_records_error_metrics(self, instrumented_service, mock_llm_service):
        """Test invoke records metrics on error."""
        messages = [HumanMessage(content="Test")]
        mock_llm_service.invoke_with_retry.side_effect = ValueError("API error")

        with patch.object(instrumented_service.api_duration, "record") as mock_duration:
            with pytest.raises(ValueError):
                instrumented_service.invoke(messages)

            # Verify error metrics were recorded
            mock_duration.assert_called_once()
            duration_call = mock_duration.call_args[1]
            assert duration_call["attributes"]["status"] == "error"
            assert duration_call["attributes"]["error_type"] == "ValueError"

    def test_invoke_estimates_tokens(self, instrumented_service):
        """Test invoke estimates token usage."""
        messages = [HumanMessage(content="A" * 100)]  # 100 chars

        with (
            patch.object(instrumented_service.tokens_used, "add") as mock_tokens,
            patch.object(
                instrumented_service.token_histogram, "record"
            ) as mock_histogram,
        ):
            instrumented_service.invoke(messages)

            # Verify token estimation was recorded
            mock_tokens.assert_called_once()
            mock_histogram.assert_called_once()

            # Check estimated tokens (chars/4 + response_chars/4)
            estimated_tokens = mock_tokens.call_args[0][0]
            assert estimated_tokens > 0


class TestInstrumentedLLMServiceGenerateFromTemplate:
    """Test generate_from_template method."""

    def test_generate_from_template_success(
        self, instrumented_service, mock_llm_service
    ):
        """Test successful template generation."""
        template_name = "test_template"
        context = {"key": "value"}

        result = instrumented_service.generate_from_template(template_name, context)

        # Verify result
        assert result == "Mocked template response"

        # Verify LLM service was called
        mock_llm_service.invoke_prompt.assert_called_once_with(
            prompt_key=template_name, variables=context
        )

    def test_generate_from_template_with_temperature(self, instrumented_service):
        """Test template generation with custom temperature."""
        result = instrumented_service.generate_from_template(
            "template", {}, temperature=0.8
        )

        assert result == "Mocked template response"

    def test_generate_from_template_with_max_tokens(self, instrumented_service):
        """Test template generation with max tokens."""
        result = instrumented_service.generate_from_template(
            "template", {}, max_tokens=200
        )

        assert result == "Mocked template response"

    def test_generate_from_template_records_metrics(self, instrumented_service):
        """Test template generation records metrics."""
        with patch.object(instrumented_service.api_calls, "add") as mock_add:
            instrumented_service.generate_from_template("template", {})

            # Verify API call was counted
            mock_add.assert_called_once()
            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["attributes"]["operation"] == "generate_from_template"
            assert call_kwargs["attributes"]["template"] == "template"

    def test_generate_from_template_with_non_string_result(
        self, instrumented_service, mock_llm_service
    ):
        """Test template generation with non-string result."""
        mock_response = Mock()
        mock_response.content = 12345
        mock_llm_service.invoke_prompt.return_value = mock_response

        result = instrumented_service.generate_from_template("template", {})

        assert result == "12345"


class TestInstrumentedLLMServiceDelegation:
    """Test delegation to underlying LLM service."""

    def test_getattr_delegates_to_llm_service(
        self, instrumented_service, mock_llm_service
    ):
        """Test __getattr__ delegates unknown attributes to LLM service."""
        mock_llm_service.some_custom_method = Mock(return_value="custom result")

        result = instrumented_service.some_custom_method()

        assert result == "custom result"
        mock_llm_service.some_custom_method.assert_called_once()

    def test_access_underlying_service_attributes(
        self, instrumented_service, mock_llm_service
    ):
        """Test access to underlying service attributes."""
        # Access attributes that exist on LLM service
        assert instrumented_service.model_name == "gemini-2.0-flash"
        assert instrumented_service.temperature == 0.1


class TestInstrumentedLLMServiceMetricsContext:
    """Test metrics context management."""

    @patch("src.services.instrumented_llm_service.MetricsContext")
    def test_invoke_uses_metrics_context(
        self, mock_metrics_context, instrumented_service
    ):
        """Test invoke uses MetricsContext."""
        messages = [HumanMessage(content="Test")]

        instrumented_service.invoke(messages)

        # Verify MetricsContext was used
        mock_metrics_context.assert_called()
        call_kwargs = mock_metrics_context.call_args[1]
        assert call_kwargs["operation"] == "llm_invoke"
        assert "model" in call_kwargs["labels"]

    @patch("src.services.instrumented_llm_service.MetricsContext")
    def test_generate_from_template_uses_metrics_context(
        self, mock_metrics_context, instrumented_service
    ):
        """Test generate_from_template uses MetricsContext."""
        instrumented_service.generate_from_template("template", {})

        # Verify MetricsContext was used
        mock_metrics_context.assert_called()
        call_kwargs = mock_metrics_context.call_args[1]
        assert call_kwargs["operation"] == "llm_generate_from_template"
        assert "template" in call_kwargs["labels"]


class TestInstrumentedLLMServiceModelName:
    """Test handling of model name."""

    def test_invoke_with_model_without_name(self, mock_llm_service):
        """Test invoke handles LLM service without model_name attribute."""
        # Remove model_name attribute
        del mock_llm_service.model_name
        service = InstrumentedLLMService(mock_llm_service)

        messages = [HumanMessage(content="Test")]

        # Should use "unknown" as fallback
        with patch.object(service.api_calls, "add") as mock_add:
            service.invoke(messages)

            call_kwargs = mock_add.call_args[1]
            assert call_kwargs["attributes"]["model"] == "unknown"


class TestInstrumentedLLMServiceLogging:
    """Test logging behavior."""

    @patch("src.services.instrumented_llm_service.logger")
    def test_invoke_logs_success(self, mock_logger, instrumented_service):
        """Test invoke logs success."""
        messages = [HumanMessage(content="Test")]

        instrumented_service.invoke(messages)

        # Verify success log
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args
        assert "LLM API call completed" in log_call[0][0]

    @patch("src.services.instrumented_llm_service.logger")
    def test_invoke_logs_error(
        self, mock_logger, instrumented_service, mock_llm_service
    ):
        """Test invoke logs errors."""
        messages = [HumanMessage(content="Test")]
        mock_llm_service.invoke_with_retry.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError):
            instrumented_service.invoke(messages)

        # Verify error log
        mock_logger.error.assert_called()
        log_call = mock_logger.error.call_args
        assert "LLM API call failed" in log_call[0][0]


class TestInstrumentedLLMServiceIntegration:
    """Integration tests for InstrumentedLLMService."""

    def test_multiple_invocations_accumulate_metrics(self, instrumented_service):
        """Test multiple invocations accumulate metrics correctly."""
        messages = [HumanMessage(content="Test")]

        with patch.object(instrumented_service.api_calls, "add") as mock_add:
            # Make multiple calls
            instrumented_service.invoke(messages)
            instrumented_service.invoke(messages)
            instrumented_service.invoke(messages)

            # Verify metrics were recorded for each call
            assert mock_add.call_count == 3

    def test_mixed_success_and_failure(self, instrumented_service, mock_llm_service):
        """Test metrics are recorded for both success and failure."""
        messages = [HumanMessage(content="Test")]

        with patch.object(instrumented_service.api_duration, "record") as mock_duration:
            # Success
            instrumented_service.invoke(messages)

            # Failure
            mock_llm_service.invoke_with_retry.side_effect = ValueError("Error")
            with pytest.raises(ValueError):
                instrumented_service.invoke(messages)

            # Reset side effect
            mock_llm_service.invoke_with_retry.side_effect = None

            # Verify both success and error were recorded
            assert mock_duration.call_count == 2
            calls = mock_duration.call_args_list
            assert calls[0][1]["attributes"]["status"] == "success"
            assert calls[1][1]["attributes"]["status"] == "error"
