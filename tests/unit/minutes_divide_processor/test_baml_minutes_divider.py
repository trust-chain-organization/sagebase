"""Tests for BAML MinutesDivider"""

from unittest.mock import patch

import pytest

from src.infrastructure.external.minutes_divider.baml_minutes_divider import (
    BAMLMinutesDivider,
)
from src.minutes_divide_processor.models import (
    RedivideSectionString,
    RedivideSectionStringList,
    SectionString,
)


class TestBAMLMinutesDivider:
    """Test cases for BAMLMinutesDivider"""

    @pytest.fixture
    def divider(self):
        """Create a BAMLMinutesDivider instance"""
        return BAMLMinutesDivider(k=5)

    # ========================================
    # section_divide_run tests
    # ========================================

    @pytest.mark.asyncio
    async def test_section_divide_run_success(self, divider):
        """Test successful section division with BAML"""

        # Mock BAML result
        class MockSectionInfo:
            def __init__(self, chapter_number, keyword):
                self.chapter_number = chapter_number
                self.keyword = keyword

        mock_result = [
            MockSectionInfo(1, "◎高速鉄道部長(塩見康裕)"),
            MockSectionInfo(2, "◎次のセクション"),
            MockSectionInfo(3, "◎最後のセクション"),
        ]

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DivideMinutesToKeywords"
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = await divider.section_divide_run("議事録テキスト")

            # Assert
            assert len(result.section_info_list) == 3
            assert result.section_info_list[0].chapter_number == 1
            assert result.section_info_list[0].keyword == "◎高速鉄道部長(塩見康裕)"
            assert result.section_info_list[1].chapter_number == 2
            assert result.section_info_list[2].chapter_number == 3

            # Verify BAML was called
            mock_baml.assert_called_once_with("議事録テキスト")

    @pytest.mark.asyncio
    async def test_section_divide_run_empty_result(self, divider):
        """Test section division with empty result"""
        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DivideMinutesToKeywords"
        ) as mock_baml:
            mock_baml.return_value = []

            # Execute
            result = await divider.section_divide_run("議事録テキスト")

            # Assert
            assert result.section_info_list == []

    @pytest.mark.asyncio
    async def test_section_divide_run_error_handling(self, divider):
        """Test error handling in section division"""
        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DivideMinutesToKeywords"
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = await divider.section_divide_run("議事録テキスト")

            # Assert - should return empty list on error
            assert result.section_info_list == []

    # ========================================
    # do_redivide tests
    # ========================================

    @pytest.mark.asyncio
    async def test_do_redivide_success(self, divider):
        """Test successful section redivision with BAML"""

        # Mock BAML result
        class MockSectionInfo:
            def __init__(self, chapter_number, keyword):
                self.chapter_number = chapter_number
                self.keyword = keyword

        mock_result = [
            MockSectionInfo(1, "再分割セクション1"),
            MockSectionInfo(2, "再分割セクション2"),
        ]

        # Create redivide input
        redivide_list = RedivideSectionStringList(
            redivide_section_string_list=[
                RedivideSectionString(
                    original_index=0,
                    redivide_section_string_bytes=7000,
                    redivide_section_string=SectionString(
                        chapter_number=1,
                        sub_chapter_number=1,
                        section_string="長いセクション" * 1000,
                    ),
                )
            ]
        )

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.RedivideSection"
        ) as mock_baml:
            mock_baml.return_value = mock_result

            # Execute
            result = await divider.do_redivide(redivide_list)

            # Assert
            assert len(result.redivided_section_info_list) == 2
            mock_baml.assert_called_once()

    @pytest.mark.asyncio
    async def test_do_redivide_error_handling(self, divider):
        """Test error handling in section redivision"""

        # Create redivide input
        redivide_list = RedivideSectionStringList(
            redivide_section_string_list=[
                RedivideSectionString(
                    original_index=0,
                    redivide_section_string_bytes=7000,
                    redivide_section_string=SectionString(
                        chapter_number=1,
                        sub_chapter_number=1,
                        section_string="長いセクション" * 1000,
                    ),
                )
            ]
        )

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.RedivideSection"
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = await divider.do_redivide(redivide_list)

            # Assert - should return empty list on error
            assert result.redivided_section_info_list == []

    # ========================================
    # detect_attendee_boundary tests
    # ========================================

    @pytest.mark.asyncio
    async def test_detect_attendee_boundary_success(self, divider):
        """Test successful boundary detection with BAML"""

        # Mock BAML result
        class MockBoundary:
            def __init__(self):
                self.boundary_found = True
                self.boundary_text = "出席者リスト｜境界｜発言開始"
                self.boundary_type = "separator_line"
                self.confidence = 0.9
                self.reason = "区切り線で明確に分離されている"

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_baml:
            mock_baml.return_value = MockBoundary()

            # Execute
            result = await divider.detect_attendee_boundary("議事録テキスト")

            # Assert
            assert result.boundary_found is True
            assert result.boundary_text == "出席者リスト｜境界｜発言開始"
            assert result.boundary_type == "separator_line"
            assert result.confidence == 0.9
            mock_baml.assert_called_once_with("議事録テキスト")

    @pytest.mark.asyncio
    async def test_detect_attendee_boundary_not_found(self, divider):
        """Test boundary detection when no boundary found"""

        # Mock BAML result
        class MockBoundary:
            def __init__(self):
                self.boundary_found = False
                self.boundary_text = None
                self.boundary_type = "none"
                self.confidence = 0.0
                self.reason = "境界が見つかりませんでした"

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_baml:
            mock_baml.return_value = MockBoundary()

            # Execute
            result = await divider.detect_attendee_boundary("議事録テキスト")

            # Assert
            assert result.boundary_found is False
            assert result.boundary_type == "none"

    @pytest.mark.asyncio
    async def test_detect_attendee_boundary_error_handling(self, divider):
        """Test error handling in boundary detection"""
        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = await divider.detect_attendee_boundary("議事録テキスト")

            # Assert - should return no boundary on error
            assert result.boundary_found is False
            assert result.boundary_type == "none"
            assert "エラーが発生しました" in result.reason

    # ========================================
    # extract_attendees_mapping tests
    # ========================================

    @pytest.mark.asyncio
    async def test_extract_attendees_mapping_success(self, divider):
        """Test successful attendees extraction with BAML"""

        # Mock BAML result
        class MockAttendees:
            def __init__(self):
                self.attendees_mapping = {"議長": "山田太郎", "副議長": "田中花子"}
                self.regular_attendees = ["山田太郎", "田中花子", "佐藤次郎"]
                self.confidence = 0.95

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.ExtractAttendees"
        ) as mock_baml:
            mock_baml.return_value = MockAttendees()

            # Execute
            result = await divider.extract_attendees_mapping("出席者情報テキスト")

            # Assert
            assert len(result.attendees_mapping) == 2  # type: ignore[arg-type]
            assert result.attendees_mapping["議長"] == "山田太郎"  # type: ignore[index]
            assert len(result.regular_attendees) == 3
            assert result.confidence == 0.95
            mock_baml.assert_called_once_with("出席者情報テキスト")

    @pytest.mark.asyncio
    async def test_extract_attendees_mapping_empty_text(self, divider):
        """Test attendees extraction with empty text"""
        # Execute
        result = await divider.extract_attendees_mapping("")

        # Assert
        assert result.attendees_mapping == {}
        assert result.regular_attendees == []
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_extract_attendees_mapping_error_handling(self, divider):
        """Test error handling in attendees extraction"""
        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.ExtractAttendees"
        ) as mock_baml:
            mock_baml.side_effect = Exception("BAML error")

            # Execute
            result = await divider.extract_attendees_mapping("出席者情報テキスト")

            # Assert - should return empty on error
            assert result.attendees_mapping == {}
            assert result.regular_attendees == []

    # ========================================
    # speech_divide_run tests
    # ========================================

    @pytest.mark.asyncio
    async def test_speech_divide_run_success(self, divider):
        """Test successful speech division with BAML"""

        # Mock BAML results for boundary detection and speech division
        class MockBoundary:
            def __init__(self):
                self.boundary_found = False
                self.boundary_text = None
                self.boundary_type = "none"
                self.confidence = 0.0
                self.reason = "境界なし"

        class MockSpeech:
            def __init__(self, speaker, content, order):
                self.speaker = speaker
                self.speech_content = content
                self.chapter_number = 1
                self.sub_chapter_number = 1
                self.speech_order = order

        mock_speeches = [
            MockSpeech("山田議長", "会議を開きます", 1),
            MockSpeech("田中議員", "質問があります", 2),
        ]

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_boundary:
            mock_boundary.return_value = MockBoundary()

            with patch(
                "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DivideSpeech"
            ) as mock_speech:
                mock_speech.return_value = mock_speeches

                # Execute
                section = SectionString(
                    chapter_number=1,
                    sub_chapter_number=1,
                    section_string=(
                        "○山田議長 会議を開きます。◆田中議員 質問があります。"
                    ),
                )
                result = await divider.speech_divide_run(section)

                # Assert
                assert len(result.speaker_and_speech_content_list) == 2
                assert result.speaker_and_speech_content_list[0].speaker == "山田議長"
                assert (
                    result.speaker_and_speech_content_list[0].speech_content
                    == "会議を開きます"
                )
                assert result.speaker_and_speech_content_list[1].speaker == "田中議員"

    @pytest.mark.asyncio
    async def test_speech_divide_run_empty_section(self, divider):
        """Test speech division with empty section"""

        # Mock boundary detection
        class MockBoundary:
            def __init__(self):
                self.boundary_found = False
                self.boundary_text = None
                self.boundary_type = "none"
                self.confidence = 0.0
                self.reason = "境界なし"

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_boundary:
            mock_boundary.return_value = MockBoundary()

            # Execute
            section = SectionString(
                chapter_number=1, sub_chapter_number=1, section_string=""
            )
            result = await divider.speech_divide_run(section)

            # Assert
            assert result.speaker_and_speech_content_list == []

    @pytest.mark.asyncio
    async def test_speech_divide_run_error_handling(self, divider):
        """Test error handling in speech division"""

        # Mock boundary detection (success)
        class MockBoundary:
            def __init__(self):
                self.boundary_found = False
                self.boundary_text = None
                self.boundary_type = "none"
                self.confidence = 0.0
                self.reason = "境界なし"

        with patch(
            "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DetectBoundary"
        ) as mock_boundary:
            mock_boundary.return_value = MockBoundary()

            with patch(
                "src.infrastructure.external.minutes_divider.baml_minutes_divider.b.DivideSpeech"
            ) as mock_speech:
                mock_speech.side_effect = Exception("BAML error")

                # Execute
                section = SectionString(
                    chapter_number=1,
                    sub_chapter_number=1,
                    section_string="○山田議長 会議を開きます。",
                )
                result = await divider.speech_divide_run(section)

                # Assert - should return empty list on error
                assert result.speaker_and_speech_content_list == []

    # ========================================
    # Non-LLM methods tests (sanity checks)
    # ========================================

    def test_pre_process(self, divider):
        """Test pre-processing of minutes text"""
        original = "（全角）　　スペース\r\nWindows改行"
        result = divider.pre_process(original)

        # Assert - should normalize text
        assert "（" not in result
        assert "）" not in result
        assert "\r\n" not in result

    def test_do_divide(self, divider):
        """Test division of processed minutes"""
        from src.minutes_divide_processor.models import SectionInfo, SectionInfoList

        processed_minutes = "◎高速鉄道部長(塩見康裕)テキスト◎次のセクション"
        section_info_list = SectionInfoList(
            section_info_list=[
                SectionInfo(chapter_number=1, keyword="◎高速鉄道部長(塩見康裕)"),
                SectionInfo(chapter_number=2, keyword="◎次のセクション"),
            ]
        )

        result = divider.do_divide(processed_minutes, section_info_list)

        # Assert
        assert len(result.section_string_list) == 2
        assert result.section_string_list[0].chapter_number == 1

    def test_check_length(self, divider):
        """Test length checking of sections"""
        from src.minutes_divide_processor.models import SectionStringList

        # Create a section with long text (>6000 bytes)
        long_text = "あ" * 3000  # 日本語文字は複数バイト
        section_list = SectionStringList(
            section_string_list=[
                SectionString(
                    chapter_number=1, sub_chapter_number=1, section_string=long_text
                )
            ]
        )

        result = divider.check_length(section_list)

        # Assert - should detect long section
        assert len(result.redivide_section_string_list) > 0
