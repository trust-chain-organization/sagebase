"""Tests for speech extraction tools.

このモジュールは、speech_extraction_toolsの各ツールをテストします。
外部サービス（BAML/LLM）はモックを使用してテストします。
"""

from unittest.mock import patch

import pytest

from src.infrastructure.external.langgraph_tools.speech_extraction_tools import (
    create_speech_extraction_tools,
)


class MockMinutesBoundary:
    """Mock for BAML MinutesBoundary result."""

    def __init__(
        self,
        boundary_found: bool,
        boundary_text: str | None,
        boundary_type: str,
        confidence: float,
        reason: str,
    ):
        self.boundary_found = boundary_found
        self.boundary_text = boundary_text
        self.boundary_type = boundary_type
        self.confidence = confidence
        self.reason = reason


@pytest.fixture
def tools():
    """Create speech extraction tools fixture."""
    return create_speech_extraction_tools()


@pytest.fixture
def sample_minutes_text():
    """Sample minutes text for testing."""
    return """出席者：
議長　山田太郎
委員　佐藤花子
委員　鈴木一郎

｜境界｜

○議長（山田太郎）それでは、会議を開催いたします。
○委員（佐藤花子）質問があります。
○委員（鈴木一郎）私も意見を述べたいと思います。
"""


class TestValidateBoundaryCandidate:
    """Tests for validate_boundary_candidate tool."""

    @pytest.mark.asyncio
    async def test_valid_boundary_high_confidence(self, tools, sample_minutes_text):
        """Test with a valid boundary candidate with high confidence."""
        validate_tool = tools[0]

        # Mock BAML DetectBoundary
        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=True,
                boundary_text="出席者リスト｜境界｜発言開始",
                boundary_type="separator_line",
                confidence=0.95,
                reason="区切り線と発言マーカーが検出されました",
            )

            result = await validate_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": 50,
                    "context_window": 100,
                }
            )

            assert result["is_valid"] is True
            assert result["confidence"] == 0.95
            assert result["boundary_type"] == "separator_line"
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_invalid_boundary_low_confidence(self, tools, sample_minutes_text):
        """Test with an invalid boundary candidate with low confidence."""
        validate_tool = tools[0]

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.2,
                reason="境界が見つかりませんでした",
            )

            result = await validate_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": 10,
                }
            )

            assert result["is_valid"] is False
            assert result["confidence"] == 0.2
            assert result["boundary_type"] == "none"

    @pytest.mark.asyncio
    async def test_empty_minutes_text(self, tools):
        """Test with empty minutes text."""
        validate_tool = tools[0]

        result = await validate_tool.ainvoke(
            {
                "minutes_text": "",
                "boundary_position": 0,
            }
        )

        assert result["is_valid"] is False
        assert result["confidence"] == 0.0
        assert result["reason"] == "議事録テキストが空です"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_boundary_position_out_of_range(self, tools, sample_minutes_text):
        """Test with boundary position out of range."""
        validate_tool = tools[0]

        # Position too large
        result = await validate_tool.ainvoke(
            {
                "minutes_text": sample_minutes_text,
                "boundary_position": 10000,
            }
        )

        assert result["is_valid"] is False
        assert "範囲外" in result["reason"]

        # Negative position
        result = await validate_tool.ainvoke(
            {
                "minutes_text": sample_minutes_text,
                "boundary_position": -1,
            }
        )

        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_baml_error_handling(self, tools, sample_minutes_text):
        """Test error handling when BAML raises an exception."""
        validate_tool = tools[0]

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.side_effect = Exception("BAML API error")

            result = await validate_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": 50,
                }
            )

            assert result["is_valid"] is False
            assert result["confidence"] == 0.0
            assert "error" in result


class TestAnalyzeContext:
    """Tests for analyze_context tool."""

    @pytest.mark.asyncio
    async def test_detect_all_patterns(self, tools):
        """Test detection of all boundary indicator patterns."""
        analyze_tool = tools[1]

        # Create text with all patterns
        text_with_patterns = """
出席者：山田太郎、佐藤花子
議員：鈴木一郎

---
○議長（山田太郎）午前10時開会いたします。
◆委員（佐藤花子）質問があります。
"""

        # Use boundary position right before the speech markers
        # so that time marker appears in context_after
        result = await analyze_tool.ainvoke(
            {
                "minutes_text": text_with_patterns,
                "boundary_position": 35,  # Position after "---\n"
                "window_size": 200,
            }
        )

        assert result["has_attendee_list"] is True
        assert result["has_speech_markers"] is True
        assert result["has_separator_line"] is True
        assert result["has_time_markers"] is True
        assert len(result["boundary_indicators"]) >= 3
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_no_patterns_detected(self, tools):
        """Test when no boundary patterns are detected."""
        analyze_tool = tools[1]

        plain_text = "これは普通のテキストです。特別なパターンはありません。"

        result = await analyze_tool.ainvoke(
            {
                "minutes_text": plain_text,
                "boundary_position": 15,
            }
        )

        assert result["has_attendee_list"] is False
        assert result["has_speech_markers"] is False
        assert result["has_separator_line"] is False
        assert result["has_time_markers"] is False
        assert len(result["boundary_indicators"]) == 0

    @pytest.mark.asyncio
    async def test_speech_markers_only(self, tools):
        """Test detection of speech markers only."""
        analyze_tool = tools[1]

        text_with_markers = """前のテキスト

○議長（山田太郎）発言内容
◆委員（佐藤花子）発言内容
"""

        result = await analyze_tool.ainvoke(
            {
                "minutes_text": text_with_markers,
                "boundary_position": 10,
            }
        )

        assert result["has_speech_markers"] is True
        assert "speech_marker" in result["boundary_indicators"]

    @pytest.mark.asyncio
    async def test_empty_text(self, tools):
        """Test with empty text."""
        analyze_tool = tools[1]

        result = await analyze_tool.ainvoke(
            {
                "minutes_text": "",
                "boundary_position": 0,
            }
        )

        assert "error" in result
        assert result["has_attendee_list"] is False

    @pytest.mark.asyncio
    async def test_position_at_text_edges(self, tools):
        """Test with boundary position at text edges."""
        analyze_tool = tools[1]

        text = "○議長（山田太郎）発言内容です。"

        # Beginning of text
        result = await analyze_tool.ainvoke(
            {
                "minutes_text": text,
                "boundary_position": 0,
                "window_size": 50,
            }
        )

        assert result["context_before"] == ""
        assert len(result["context_after"]) > 0

        # End of text
        result = await analyze_tool.ainvoke(
            {
                "minutes_text": text,
                "boundary_position": len(text) - 1,
                "window_size": 50,
            }
        )

        assert len(result["context_before"]) > 0
        assert len(result["context_after"]) == 1


class TestVerifyBoundary:
    """Tests for verify_boundary tool."""

    @pytest.mark.asyncio
    async def test_high_confidence_boundary(self, tools, sample_minutes_text):
        """Test verification of a high confidence boundary."""
        verify_tool = tools[2]

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=True,
                boundary_text="出席者｜境界｜発言",
                boundary_type="speech_start",
                confidence=0.85,
                reason="発言開始マーカーが検出されました",
            )

            result = await verify_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": 50,
                }
            )

            assert result["is_boundary"] is True
            assert result["final_confidence"] >= 0.7
            assert (
                "高信頼度" in result["recommendation"]
                or "使用可能" in result["recommendation"]
            )
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_low_confidence_boundary(self, tools, sample_minutes_text):
        """Test verification of a low confidence boundary."""
        verify_tool = tools[2]

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.3,
                reason="明確な境界が見つかりませんでした",
            )

            result = await verify_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": 10,
                }
            )

            assert result["is_boundary"] is False
            assert result["final_confidence"] < 0.7
            assert (
                "別の" in result["recommendation"]
                or "不適切" in result["recommendation"]
            )

    @pytest.mark.asyncio
    async def test_with_provided_validation_result(self, tools, sample_minutes_text):
        """Test verification with pre-provided validation result."""
        verify_tool = tools[2]

        validation_result = {
            "is_valid": True,
            "confidence": 0.8,
            "boundary_type": "separator_line",
            "reason": "区切り線が検出されました",
            "context_before": "出席者リスト",
            "context_after": "発言開始",
        }

        context_analysis = {
            "context_before": "出席者リスト",
            "context_after": "発言開始",
            "has_attendee_list": True,
            "has_speech_markers": True,
            "has_separator_line": True,
            "has_time_markers": False,
            "boundary_indicators": [
                "attendee_list",
                "speech_marker",
                "separator_line",
            ],
        }

        result = await verify_tool.ainvoke(
            {
                "minutes_text": sample_minutes_text,
                "boundary_position": 50,
                "validation_result": validation_result,
                "context_analysis": context_analysis,
            }
        )

        assert result["is_boundary"] is True
        # Base 0.8 + attendee_list 0.15 + speech_marker 0.1 +
        # separator 0.05 = 1.1 -> capped at 1.0
        assert result["final_confidence"] >= 0.9
        assert result["verification_details"]["indicators_detected"] == 3

    @pytest.mark.asyncio
    async def test_confidence_boost_calculation(self, tools, sample_minutes_text):
        """Test that confidence boost is calculated correctly."""
        verify_tool = tools[2]

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=True,
                boundary_text="test",
                boundary_type="speech_start",
                confidence=0.6,
                reason="test",
            )

            # Create text with multiple indicators to test boost
            text_with_indicators = """
出席者：山田太郎
---
○議長（山田太郎）午前10時
"""

            result = await verify_tool.ainvoke(
                {
                    "minutes_text": text_with_indicators,
                    "boundary_position": 20,
                }
            )

            # Base confidence 0.6 + various boosts
            # Should have attendee_list, separator_line, speech_marker, time_marker
            details = result["verification_details"]
            assert details["base_confidence"] == 0.6
            assert details["confidence_boost"] > 0
            assert result["final_confidence"] > 0.6

    @pytest.mark.asyncio
    async def test_error_in_validation(self, tools, sample_minutes_text):
        """Test handling of validation error."""
        verify_tool = tools[2]

        validation_result_with_error = {
            "is_valid": False,
            "confidence": 0.0,
            "boundary_type": "none",
            "reason": "",
            "context_before": "",
            "context_after": "",
            "error": "Validation failed",
        }

        result = await verify_tool.ainvoke(
            {
                "minutes_text": sample_minutes_text,
                "boundary_position": 50,
                "validation_result": validation_result_with_error,
            }
        )

        assert result["is_boundary"] is False
        assert "error" in result


class TestToolsIntegration:
    """Integration tests for all three tools working together."""

    @pytest.mark.asyncio
    async def test_complete_boundary_verification_workflow(
        self, tools, sample_minutes_text
    ):
        """Test the complete workflow using all three tools."""
        validate_tool = tools[0]
        analyze_tool = tools[1]
        verify_tool = tools[2]

        boundary_position = 50

        with patch(
            "src.infrastructure.external.langgraph_tools.speech_extraction_tools.b.DetectBoundary"
        ) as mock_detect:
            mock_detect.return_value = MockMinutesBoundary(
                boundary_found=True,
                boundary_text="出席者｜境界｜発言",
                boundary_type="separator_line",
                confidence=0.8,
                reason="区切りが検出されました",
            )

            # Step 1: Validate boundary candidate
            validation_result = await validate_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": boundary_position,
                }
            )

            assert validation_result["is_valid"] is True

            # Step 2: Analyze context
            context_analysis = await analyze_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": boundary_position,
                }
            )

            assert len(context_analysis["boundary_indicators"]) > 0

            # Step 3: Verify boundary
            final_result = await verify_tool.ainvoke(
                {
                    "minutes_text": sample_minutes_text,
                    "boundary_position": boundary_position,
                    "validation_result": validation_result,
                    "context_analysis": context_analysis,
                }
            )

            assert final_result["is_boundary"] is True
            assert final_result["final_confidence"] >= 0.7
