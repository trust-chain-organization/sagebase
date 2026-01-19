"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.exceptions import LLMServiceException, ResponseParsingException
from src.infrastructure.external.llm_service import GeminiLLMService


class TestGeminiLLMService:
    """Test cases for GeminiLLMService."""

    @pytest.fixture
    def service(self):
        """Create LLM service instance."""
        with patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        ) as mock_llm:
            mock_llm.return_value = MagicMock()
            return GeminiLLMService(api_key="test-key", model_name="gemini-2.0-flash")

    @pytest.mark.asyncio
    async def test_extract_party_members(self, service):
        """Test party member extraction from HTML."""
        # Setup
        html_content = """
        <div class="member-list">
            <div class="member">
                <h3>山田太郎</h3>
                <p>やまだ たろう</p>
                <p>衆議院議員・東京1区</p>
            </div>
            <div class="member">
                <h3>鈴木花子</h3>
                <p>すずき はなこ</p>
                <p>参議院議員・比例区</p>
            </div>
        </div>
        """

        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = """
        {
            "success": true,
            "extracted_data": [
                {
                    "name": "山田太郎",
                    "furigana": "ヤマダ タロウ",
                    "position": "衆議院議員",
                    "district": "東京1区"
                },
                {
                    "name": "鈴木花子",
                    "furigana": "スズキ ハナコ",
                    "position": "参議院議員",
                    "district": "比例区"
                }
            ],
            "error": null
        }
        """

        # Mock the chain.ainvoke call
        with patch.object(service._llm, "ainvoke"):
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)

            with patch(
                "langchain_core.prompts.ChatPromptTemplate.from_template"
            ) as mock_template:
                mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

                # Execute
                result = await service.extract_party_members(html_content, party_id=1)

        # Verify
        assert result["success"] is True
        assert result["error"] is None
        assert result["extracted_data"] is not None
        assert len(result["extracted_data"]) > 0

        # Check first extracted member
        first_member = result["extracted_data"][0]
        assert "name" in first_member
        assert first_member["name"] is not None

        # Check metadata
        assert result["metadata"] is not None
        assert result["metadata"].get("party_id") == "1"

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test service initialization with different parameters."""
        with patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        ) as mock_llm:
            mock_llm.return_value = MagicMock()

            # Test with default model
            service1 = GeminiLLMService(api_key="key1")
            assert service1.api_key == "key1"
            assert service1.model_name == "gemini-2.0-flash"

            # Test with custom model
            service2 = GeminiLLMService(api_key="key2", model_name="gemini-1.5-pro")
            assert service2.api_key == "key2"
            assert service2.model_name == "gemini-1.5-pro"

            # Test with another model variant
            service3 = GeminiLLMService(api_key="key3", model_name="gemini-1.5-flash")
            assert service3.api_key == "key3"
            assert service3.model_name == "gemini-1.5-flash"


class TestGeminiLLMServiceErrorHandling:
    """Issue #965: エラーハンドリングのテスト"""

    @pytest.fixture
    def service(self):
        """Create LLM service instance."""
        with patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        ) as mock_llm:
            mock_llm.return_value = MagicMock()
            return GeminiLLMService(api_key="test-key", model_name="gemini-2.0-flash")

    @pytest.mark.asyncio
    async def test_extract_party_members_json_parse_error(self, service):
        """JSONパースエラー時にLLMExtractResult.success=Falseが返される"""
        mock_response = MagicMock()
        mock_response.content = "invalid json {"  # 不正なJSON

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            result = await service.extract_party_members("<html></html>", party_id=1)

        assert result["success"] is False
        assert "JSONパースエラー" in result["error"]
        assert result["extracted_data"] == []

    @pytest.mark.asyncio
    async def test_extract_party_members_general_error(self, service):
        """一般的なエラー時にLLMExtractResult.success=Falseが返される"""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=Exception("API error"))

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            result = await service.extract_party_members("<html></html>", party_id=1)

        assert result["success"] is False
        assert "LLM呼び出しエラー" in result["error"]

    @pytest.mark.asyncio
    async def test_match_conference_member_json_parse_error(self, service):
        """マッチング時のJSONパースエラーでNoneが返される"""
        mock_response = MagicMock()
        mock_response.content = "not valid json"

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            result = await service.match_conference_member(
                member_name="田中太郎",
                party_name="自民党",
                candidates=[],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_match_conference_member_general_error(self, service):
        """マッチング時の一般エラーでNoneが返される"""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=Exception("Connection error"))

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            result = await service.match_conference_member(
                member_name="田中太郎",
                party_name=None,
                candidates=[],
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_speeches_json_parse_error_raises_response_parsing_exception(
        self, service
    ):
        """発言抽出のJSONパースエラー時にResponseParsingExceptionがスローされる"""
        mock_response = MagicMock()
        mock_response.content = "invalid json {"

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            with pytest.raises(ResponseParsingException) as exc_info:
                await service.extract_speeches_from_text("議事録テキスト")

            assert "JSONパースエラー" in str(exc_info.value)
            assert exc_info.value.details["response_sample"] is not None

    @pytest.mark.asyncio
    async def test_extract_speeches_non_list_raises_response_parsing_exception(
        self, service
    ):
        """発言抽出でリスト以外が返された時にResponseParsingExceptionがスローされる"""
        mock_response = MagicMock()
        mock_response.content = '{"not": "a list"}'  # リストではなくdict

        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            with pytest.raises(ResponseParsingException) as exc_info:
                await service.extract_speeches_from_text("議事録テキスト")

            assert "リストを期待しました" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_speeches_general_error_raises_llm_service_exception(
        self, service
    ):
        """発言抽出の一般エラー時にLLMServiceExceptionがスローされる"""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=Exception("API error"))

        with patch(
            "langchain_core.prompts.ChatPromptTemplate.from_template"
        ) as mock_template:
            mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

            with pytest.raises(LLMServiceException) as exc_info:
                await service.extract_speeches_from_text("議事録テキスト")

            assert exc_info.value.details["operation"] == "extract_speeches"
            # エラーチェーンが保持されていることを確認
            assert exc_info.value.__cause__ is not None

    def test_invoke_with_retry_raises_llm_service_exception(self, service):
        """invoke_with_retryエラー時にLLMServiceExceptionがスローされる"""
        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = Exception("Chain error")

        with pytest.raises(LLMServiceException) as exc_info:
            service.invoke_with_retry(mock_chain, {"input": "test"})

        assert exc_info.value.details["operation"] == "chain_invoke"
        # エラーチェーンが保持されていることを確認
        assert exc_info.value.__cause__ is not None

    def test_invoke_llm_raises_llm_service_exception(self, service):
        """invoke_llmエラー時にLLMServiceExceptionがスローされる"""
        service._llm.invoke.side_effect = Exception("Invocation error")

        with pytest.raises(LLMServiceException) as exc_info:
            service.invoke_llm([{"role": "user", "content": "test"}])

        assert exc_info.value.details["operation"] == "invoke_llm"
        # エラーチェーンが保持されていることを確認
        assert exc_info.value.__cause__ is not None
