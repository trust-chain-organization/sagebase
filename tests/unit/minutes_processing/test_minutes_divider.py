import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import Mock, patch

from src.infrastructure.external.minutes_divider.pydantic_minutes_divider import (
    MinutesDivider,
)
from src.minutes_divide_processor.models import (
    SectionInfo,
    SectionInfoList,
    SectionString,
    SectionStringList,
)


class TestMinutesDivider(unittest.TestCase):
    @patch(
        "src.infrastructure.external.minutes_divider.pydantic_minutes_divider.LLMServiceFactory"
    )
    def setUp(self, mock_factory):
        # Create a mock LLM service
        mock_service = Mock()
        mock_factory.return_value.create_advanced.return_value = mock_service

        # MinutesDivider will use the mocked service
        self.divider = MinutesDivider()
        self.mock_service = mock_service

    def test_do_divide_normal(self):
        processed_minutes = (
            "◎高速鉄道部長(塩見康裕)今御紹介がありました。"
            "高速鉄道部長の塩見康弘です。◎次のセクション"
        )
        section_info_list = SectionInfoList(
            section_info_list=[
                SectionInfo(chapter_number=1, keyword="◎高速鉄道部長(塩見康裕)"),
                SectionInfo(chapter_number=2, keyword="◎次のセクション"),
            ]
        )
        expected_output = SectionStringList(
            section_string_list=[
                SectionString(
                    chapter_number=1,
                    sub_chapter_number=1,
                    section_string=(
                        "◎高速鉄道部長(塩見康裕)今御紹介がありました。"
                        "高速鉄道部長の塩見康弘です。"
                    ),
                ),
                SectionString(
                    chapter_number=2,
                    sub_chapter_number=1,
                    section_string="◎次のセクション",
                ),
            ]
        )
        result = self.divider.do_divide(processed_minutes, section_info_list)
        self.assertEqual(result, expected_output)

    def test_do_divide_missing_keyword(self):
        processed_minutes = (
            "◎高速鉄道部長(塩見康裕)今御紹介がありました。高速鉄道部長の塩見康弘です。"
        )
        section_info_list = SectionInfoList(
            section_info_list=[
                SectionInfo(chapter_number=1, keyword="◎高速鉄道部長(塩見康裕)"),
                SectionInfo(chapter_number=2, keyword="◎次のセクション"),
            ]
        )
        expected_output = SectionStringList(
            section_string_list=[
                SectionString(
                    section_string=(
                        "◎高速鉄道部長(塩見康裕)今御紹介がありました。"
                        "高速鉄道部長の塩見康弘です。"
                    )
                )
            ]
        )
        result = self.divider.do_divide(processed_minutes, section_info_list)
        self.assertEqual(result, expected_output)

    def test_do_divide_empty_minutes(self):
        processed_minutes = ""
        section_info_list = SectionInfoList(
            section_info_list=[
                SectionInfo(chapter_number=1, keyword="◎高速鉄道部長(塩見康裕)")
            ]
        )
        expected_output = SectionStringList(section_string_list=[])
        result = self.divider.do_divide(processed_minutes, section_info_list)
        self.assertEqual(
            result.section_string_list, expected_output.section_string_list
        )


if __name__ == "__main__":
    unittest.main()
