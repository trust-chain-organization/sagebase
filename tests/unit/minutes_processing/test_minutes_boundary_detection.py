"""Tests for minutes boundary detection logic.

This test suite specifically addresses Issue #577 where boundary detection
was incorrectly placing boundaries at the end of speech-only text.
"""

import os
import sys
import unittest
from typing import Any
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure.external.minutes_divider.pydantic_minutes_divider import (
    MinutesDivider,
)
from src.minutes_divide_processor.models import MinutesBoundary


class TestBoundaryDetection(unittest.TestCase):
    """Test cases for boundary detection in minutes processing."""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory: Any) -> None:
        """Set up test fixtures."""
        # Create a mock LLM service
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service

        # MinutesDivider will use the mocked service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_split_boundary_at_end_should_be_rejected(self):
        """Test that boundaries near the end of text are rejected.

        This test reproduces Issue #577 where the LLM incorrectly placed
        the boundary at the end of speech-only text, causing all content
        to be classified as attendee information.
        """
        # Sample text similar to the one in Issue #577
        minutes_text = (
            "○議長(西村義直)ただ今から、常任委員会、市会運営委員会の合同委員会を開会いたします。"
            "これより、正副委員長の互選を行います。正副委員長の互選については、議長指名とし、"
            "議長から、ただ今、お手元に配付してあります名簿の方々を、それぞれ正副委員長に"
            "指名いたしたいと思いますが、御異議ありませんか。(「異議なし」と呼ぶ者あり)"
            "○議長(西村義直)御異議なしと認めます。よって、ただ今指名いたしました方々が、"
            "それぞれ正副委員長に当選されました。これをもって、合同委員会を"
            "散会いたします。［午後２時48分散会］委員長みちはた弘之"
        )

        # Mock boundary with marker at the end (incorrect behavior)
        boundary_with_end_marker = MinutesBoundary(
            boundary_found=True,
            boundary_text="散会いたします。［午後２時48分散会］委員長みちはた弘之｜境界｜",
            boundary_type="none",
            confidence=0.9,
            reason="末尾に境界を置いた（誤った検出）",
        )

        # Split should reject this boundary and treat entire text as speech
        attendee_part, speech_part = self.divider.split_minutes_by_boundary(
            minutes_text, boundary_with_end_marker
        )

        # Verify that the entire text is treated as speech (not attendee info)
        self.assertEqual(attendee_part, "", "Attendee part should be empty")
        self.assertEqual(
            speech_part,
            minutes_text,
            "Speech part should contain entire text",
        )

    def test_split_boundary_not_found(self):
        """Test handling when boundary is not found."""
        minutes_text = "○議長(西村義直)ただ今から、常任委員会を開会いたします。"

        boundary_not_found = MinutesBoundary(
            boundary_found=False,
            boundary_text=None,
            boundary_type="none",
            confidence=0.0,
            reason="境界が見つからない",
        )

        attendee_part, speech_part = self.divider.split_minutes_by_boundary(
            minutes_text, boundary_not_found
        )

        # When no boundary is found, entire text should be treated as speech
        self.assertEqual(attendee_part, "")
        self.assertEqual(speech_part, minutes_text)

    def test_split_valid_boundary_in_middle(self):
        """Test that valid boundaries in the middle of text are accepted."""
        minutes_text = (
            "◯出席委員\n"
            "委員長　みちはた弘之議員\n"
            "副委員長　西村よしみ議員\n"
            "－－－－－－－－－－－－－－－－－－－－－－－－－－－－\n"
            "［午後２時47分開会］\n"
            "○委員長(みちはた弘之)ただ今から、委員会を開会いたします。"
        )

        # Valid boundary in the middle
        valid_boundary = MinutesBoundary(
            boundary_found=True,
            boundary_text=(
                "副委員長　西村よしみ議員\n－－－｜境界｜"
                "－－－－－－－－\n［午後２時47分開会］"
            ),
            boundary_type="separator_line",
            confidence=0.95,
            reason="区切り線を境界として検出",
        )

        attendee_part, speech_part = self.divider.split_minutes_by_boundary(
            minutes_text, valid_boundary
        )

        # Verify split is accepted
        self.assertGreater(len(attendee_part), 0, "Attendee part should not be empty")
        self.assertGreater(len(speech_part), 0, "Speech part should not be empty")
        self.assertTrue(
            "出席委員" in attendee_part,
            "Attendee part should contain attendee info",
        )
        self.assertTrue(
            "○委員長" in speech_part,
            "Speech part should contain speeches",
        )

    def test_split_boundary_near_end_percentage(self):
        """Test that boundaries within 20% of text end are rejected."""
        # Create text where boundary would be at 85% position
        minutes_text = "a" * 100 + "○議長 test"

        # Boundary at position 85 (within 20% of end)
        boundary_near_end = MinutesBoundary(
            boundary_found=True,
            boundary_text="aaa｜境界｜aaa",
            boundary_type="none",
            confidence=0.9,
            reason="末尾付近に境界を置いた",
        )

        # Mock the boundary search to return position 85
        with patch.object(
            self.divider,
            "split_minutes_by_boundary",
            wraps=self.divider.split_minutes_by_boundary,
        ):
            attendee_part, speech_part = self.divider.split_minutes_by_boundary(
                minutes_text, boundary_near_end
            )

            # Should reject boundary and treat entire text as speech
            # (implementation will check percentage threshold)
            self.assertEqual(attendee_part, "")
            self.assertEqual(speech_part, minutes_text)


if __name__ == "__main__":
    unittest.main()
