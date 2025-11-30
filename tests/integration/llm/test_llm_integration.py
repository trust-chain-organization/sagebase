"""Integration tests for LLMService and its usage across the system"""

import pytest
from pydantic import BaseModel
from pytest import MonkeyPatch  # Add the import for type annotation

from src.party_member_extractor.models import PartyMemberInfo, PartyMemberList
from src.services.llm_service import LLMService
from tests.utils.llm_mock import LLMServiceMock, mock_llm_service


class TestLLMServiceIntegration:
    """Test LLMService integration with other components"""

    @mock_llm_service(
        [
            PartyMemberList(
                members=[
                    PartyMemberInfo(
                        name="田中太郎",
                        position="衆議院議員",
                        electoral_district="東京1区",
                    )
                ],
                total_count=1,
                party_name="テスト党",
            )
        ]
    )
    def test_party_member_extractor_integration(self) -> None:
        """Test PartyMemberExtractor with LLMService"""
        from src.party_member_extractor.extractor import PartyMemberExtractor
        from src.party_member_extractor.models import WebPageContent

        extractor = PartyMemberExtractor()

        # Test extraction
        page = WebPageContent(
            url="https://example.com",
            html_content="<html><body>田中太郎 衆議院議員</body></html>",
            page_number=1,
        )

        result = extractor._extract_from_single_page(page, "テスト党")  # type: ignore[reportPrivateUsage]
        assert result is not None
        assert len(result.members) == 1
        assert result.members[0].name == "田中太郎"

    def test_minutes_divider_integration(self, monkeypatch: MonkeyPatch) -> None:
        """Test MinutesDivider with LLMService"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        with LLMServiceMock(
            [
                {
                    "section_info_list": [
                        {"chapter_number": 1, "keyword": "開会"},
                        {"chapter_number": 2, "keyword": "議事"},
                    ]
                }
            ]
        ):
            from src.infrastructure.external.minutes_divider.pydantic_minutes_divider import (  # noqa: E501
                MinutesDivider,
            )

            divider = MinutesDivider()

            # Test section divide
            result = divider.section_divide_run("議事録テキスト")
            assert result is not None
            assert len(result.section_info_list) == 2


class TestMockFramework:
    """Test the LLM mock framework itself"""

    def test_mock_llm_basic(self) -> None:
        """Test basic mock LLM functionality"""
        from tests.utils.llm_mock import MockLLM

        mock = MockLLM(["Response 1", "Response 2"])

        # Test first response
        result = mock.invoke("test input")
        assert isinstance(result.content, str)  # type: ignore[reportUnknownMemberType]
        assert "Response 1" in result.content

        # Test second response
        result = mock.invoke("another input")
        assert isinstance(result.content, str)  # type: ignore[reportUnknownMemberType]
        assert "Response 2" in result.content

        # Test call history
        assert len(mock.call_history) == 2
        assert mock.call_history[0]["input"] == "test input"

    def test_mock_structured_llm(self) -> None:
        """Test mock structured LLM"""
        from tests.utils.llm_mock import MockLLM

        class TestModel(BaseModel):
            name: str
            value: int

        mock = MockLLM([{"name": "test", "value": 42}])
        structured = mock.with_structured_output(TestModel)

        result = structured.invoke("test")
        assert isinstance(result, TestModel)
        assert result.name == "test"
        assert result.value == 42

    def test_llm_service_mock_context(self) -> None:
        """Test LLMServiceMock context manager"""
        with LLMServiceMock(["mocked response"]) as mock:
            service = LLMService()
            chain = service.create_simple_chain("Test prompt: {input}")
            result = chain.invoke({"input": "test"})

            assert mock.call_count == 1
            assert "mocked response" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
