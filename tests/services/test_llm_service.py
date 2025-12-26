"""Unit tests for LLMService"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.infrastructure.external.llm_errors import (
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.services.llm_service import LLMService


class SampleSchema(BaseModel):
    """Sample schema for structured output testing"""

    name: str
    value: int


class TestLLMService:
    """Test cases for LLMService"""

    @pytest.fixture
    def mock_api_key(self, monkeypatch):
        """Mock API key environment variable"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")

    def test_init_with_api_key(self, mock_api_key):
        """Test initialization with API key"""
        service = LLMService()
        assert service.api_key == "test-api-key"
        assert service.model_name == LLMService.DEFAULT_MODELS["fast"]
        assert service.temperature == 0.1
        assert service.max_tokens is None

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization without API key raises error"""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(LLMAuthenticationError) as exc_info:
            LLMService()

        assert "Google API key not found" in str(exc_info.value)

    def test_init_with_custom_parameters(self, mock_api_key):
        """Test initialization with custom parameters"""
        service = LLMService(
            model_name="custom-model",
            temperature=0.7,
            max_tokens=1000,
            api_key="custom-key",
            use_prompt_manager=False,
        )

        assert service.model_name == "custom-model"
        assert service.temperature == 0.7
        assert service.max_tokens == 1000
        assert service.api_key == "custom-key"
        assert service.prompt_manager is None

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_llm_lazy_initialization(self, mock_llm_class, mock_api_key):
        """Test lazy initialization of LLM"""
        service = LLMService()

        # LLM should not be created yet
        assert service._llm is None

        # Access LLM property
        llm = service.llm

        # LLM should be created
        assert llm is not None
        mock_llm_class.assert_called_once_with(
            model=service.model_name,
            temperature=service.temperature,
            google_api_key=service.api_key,
            timeout=60,
            max_retries=2,
        )

        # Subsequent access should return same instance
        llm2 = service.llm
        assert llm is llm2

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_get_structured_llm(self, mock_llm_class, mock_api_key):
        """Test getting structured LLM"""
        # Setup
        mock_llm_instance = MagicMock()
        mock_structured_llm = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm
        mock_llm_class.return_value = mock_llm_instance

        service = LLMService()

        # Execute
        structured_llm = service.get_structured_llm(SampleSchema)

        # Verify
        assert structured_llm == mock_structured_llm
        mock_llm_instance.with_structured_output.assert_called_once_with(SampleSchema)

        # Test caching
        structured_llm2 = service.get_structured_llm(SampleSchema)
        assert structured_llm2 == mock_structured_llm
        # Should not call with_structured_output again
        assert mock_llm_instance.with_structured_output.call_count == 1

    def test_convert_exception(self, mock_api_key):
        """Test exception conversion"""
        service = LLMService()

        # Test rate limit error
        rate_limit_error = Exception("Rate limit exceeded")
        converted = service._convert_exception(rate_limit_error)
        assert isinstance(converted, LLMRateLimitError)

        # Test timeout error
        timeout_error = Exception("Request timeout")
        converted = service._convert_exception(timeout_error)
        assert isinstance(converted, LLMTimeoutError)

        # Test authentication error
        auth_error = Exception("Invalid API key")
        converted = service._convert_exception(auth_error)
        assert isinstance(converted, LLMAuthenticationError)

        # Test generic error
        generic_error = Exception("Something went wrong")
        converted = service._convert_exception(generic_error)
        assert isinstance(converted, LLMError)

    @patch("src.services.llm_service.time")
    def test_handle_rate_limit(self, mock_time, mock_api_key):
        """Test rate limit handling"""
        service = LLMService()

        # Setup mock times
        mock_time.time.side_effect = [
            100.0,  # First request - current_time
            100.0,  # First request - _last_request_time update
            100.5,  # Second request - current_time
            101.0,  # Second request - _last_request_time update after sleep
        ]

        # First request
        service._handle_rate_limit()
        assert service._request_count == 1
        assert service._last_request_time == 100.0

        # Second request too soon - should sleep
        service._handle_rate_limit()
        mock_time.sleep.assert_called_once_with(0.5)  # 1.0 - 0.5 = 0.5s sleep
        assert service._request_count == 2
        assert service._last_request_time == 101.0

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_invoke_with_prompt(self, mock_llm_class, mock_api_key):
        """Test invoke_prompt method"""
        # Setup
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Test response"

        # Mock chain creation
        with patch.object(LLMService, "create_simple_chain", return_value=mock_chain):
            with patch.object(
                LLMService, "invoke_with_retry", return_value="Test response"
            ) as mock_invoke:
                service = LLMService()

                # Execute
                result = service.invoke_prompt("test_key", {"param": "value"})

                # Verify
                assert result == "Test response"
                mock_invoke.assert_called_once_with(mock_chain, {"param": "value"})

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    @patch("src.services.llm_service.time.sleep")  # Mock sleep to speed up test
    def test_invoke_with_retry(self, mock_sleep, mock_llm_class, mock_api_key):
        """Test invoke_with_retry method"""
        # Setup
        mock_chain = MagicMock()

        # Test successful invocation
        mock_chain.invoke.return_value = "Success"
        service = LLMService()

        # Execute
        result = service.invoke_with_retry(mock_chain, {"param": "value"})

        # Verify
        assert result == "Success"
        mock_chain.invoke.assert_called_once_with({"param": "value"})

        # Test with rate limit error - tenacity will wrap in RetryError
        from tenacity import RetryError

        mock_chain.reset_mock()
        mock_chain.invoke.side_effect = Exception("Rate limit exceeded")

        # This should raise RetryError after retries
        with pytest.raises(RetryError):
            service.invoke_with_retry(mock_chain, {"param": "value"})

        # Verify it was called 3 times (original + 2 retries)
        assert mock_chain.invoke.call_count == 3

    def test_create_chain(self, mock_api_key):
        """Test chain creation methods"""
        service = LLMService()

        # Test simple chain creation
        chain = service.create_simple_chain(prompt_template="Test prompt: {input}")
        assert chain is not None

        # Test chain with structured output
        chain_structured = service.create_simple_chain(
            prompt_template="Test prompt: {input}", output_schema=SampleSchema
        )
        assert chain_structured is not None

        # Test JSON output chain
        json_chain = service.create_json_output_chain(
            prompt_template="Test prompt: {input}", output_schema=SampleSchema
        )
        assert json_chain is not None

    def test_get_legacy_prompt(self, mock_api_key):
        """Test getting prompt with prompt manager"""
        service = LLMService()

        # Mock prompt manager
        mock_prompt_template = MagicMock()
        service.prompt_manager = MagicMock()
        service.prompt_manager.get_prompt.return_value = mock_prompt_template

        # Execute
        result = service.get_prompt("test_key")

        # Verify
        assert result == mock_prompt_template
        service.prompt_manager.get_prompt.assert_called_once_with("test_key")

    def test_get_legacy_prompt_no_manager(self, mock_api_key):
        """Test getting prompt without prompt manager"""
        service = LLMService(use_prompt_manager=False)

        # Mock prompt loader
        mock_prompt_template = MagicMock()
        service.prompt_loader = MagicMock()
        service.prompt_loader.get_prompt.return_value = mock_prompt_template

        # Execute
        result = service.get_prompt("test_key")

        # Verify
        assert result == mock_prompt_template
        service.prompt_loader.get_prompt.assert_called_once_with("test_key")
