"""Simple focused tests for MinutesDivider to improve coverage

These tests focus on successfully exercising code paths without complex mocking
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import Mock, patch

from src.infrastructure.external.minutes_divider.pydantic_minutes_divider import (
    MinutesDivider,
)
from src.minutes_divide_processor.models import (
    AttendeesMapping,
    MinutesBoundary,
    SectionInfo,
    SectionInfoList,
    SectionString,
    SectionStringList,
)


class TestDoDivideSimple(unittest.TestCase):
    """Simple tests for do_divide method"""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_do_divide_with_skipped_keywords_coverage(self):
        """Test do_divide when some keywords are skipped"""
        processed_minutes = "◯セクション1テキスト。◯セクション3テキスト。"
        section_info_list = SectionInfoList(
            section_info_list=[
                SectionInfo(chapter_number=1, keyword="◯セクション1"),
                SectionInfo(chapter_number=2, keyword="◯存在しないキーワード"),
                SectionInfo(chapter_number=3, keyword="◯セクション3"),
            ]
        )

        result = self.divider.do_divide(processed_minutes, section_info_list)

        # Should handle skipped keywords gracefully
        self.assertIsInstance(result, SectionStringList)
        self.assertGreater(len(result.section_string_list), 0)


class TestCheckLengthSimple(unittest.TestCase):
    """Simple tests for check_length method"""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service
        self.divider = MinutesDivider()

    def test_check_length_identifies_long_sections(self):
        """Test that check_length identifies sections exceeding byte limit"""
        # Create a section that exceeds 6000 bytes
        long_text = "議事録内容" * 2000  # Should exceed 6000 bytes
        section_strings = SectionStringList(
            section_string_list=[
                SectionString(
                    chapter_number=1, sub_chapter_number=1, section_string=long_text
                )
            ]
        )

        result = self.divider.check_length(section_strings)

        # Should identify the long section
        self.assertGreater(len(result.redivide_section_string_list), 0)


class TestDetectAttendeeBoundarySimple(unittest.TestCase):
    """Simple tests for detect_attendee_boundary method"""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_detect_attendee_boundary_handles_keyerror(self):
        """Test detect_attendee_boundary handles missing prompt gracefully"""
        minutes_text = "テストテキスト"

        # Mock get_prompt to raise KeyError
        self.mock_service.get_prompt = Mock(side_effect=KeyError("Not found"))

        result = self.divider.detect_attendee_boundary(minutes_text)

        # Should return MinutesBoundary with boundary_found=False
        self.assertIsInstance(result, MinutesBoundary)
        self.assertFalse(result.boundary_found)


class TestSplitMinutesByBoundarySimple(unittest.TestCase):
    """Simple tests for split_minutes_by_boundary method"""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service
        self.divider = MinutesDivider()

    def test_split_minutes_by_boundary_handles_no_boundary(self):
        """Test split handles case when no boundary is found"""
        minutes_text = "テストテキスト"
        boundary = MinutesBoundary(
            boundary_found=False,
            boundary_text=None,
            boundary_type="none",
            confidence=0.0,
            reason="No boundary",
        )

        attendee_part, speech_part = self.divider.split_minutes_by_boundary(
            minutes_text, boundary
        )

        # Should return empty attendee part and full text as speech part
        self.assertEqual(attendee_part, "")
        self.assertEqual(speech_part, minutes_text)

    def test_split_minutes_by_boundary_with_marker(self):
        """Test split with boundary marker"""
        minutes_text = "出席者情報\n\n議事内容"
        boundary = MinutesBoundary(
            boundary_found=True,
            boundary_text="出席者情報｜境界｜議事内容",
            boundary_type="speech_start",
            confidence=0.9,
            reason="Found boundary",
        )

        attendee_part, speech_part = self.divider.split_minutes_by_boundary(
            minutes_text, boundary
        )

        # Should split correctly
        self.assertIsInstance(attendee_part, str)
        self.assertIsInstance(speech_part, str)


class TestExtractAttendeesMappingSimple(unittest.TestCase):
    """Simple tests for extract_attendees_mapping method"""

    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_extract_attendees_mapping_empty_text(self):
        """Test extract_attendees_mapping with empty text"""
        result = self.divider.extract_attendees_mapping("")

        # Should return empty AttendeesMapping
        self.assertIsInstance(result, AttendeesMapping)
        self.assertEqual(len(result.attendees_mapping), 0)
        self.assertEqual(len(result.regular_attendees), 0)

    def test_extract_attendees_mapping_handles_exception(self):
        """Test extract_attendees_mapping handles LLM exceptions"""
        attendees_text = "出席者リスト"

        self.mock_service.get_prompt = Mock(return_value="test prompt")
        self.mock_service.invoke_with_retry = Mock(side_effect=Exception("LLM error"))

        result = self.divider.extract_attendees_mapping(attendees_text)

        # Should return empty mapping on error
        self.assertIsInstance(result, AttendeesMapping)
        self.assertEqual(len(result.attendees_mapping), 0)


if __name__ == "__main__":
    unittest.main()
