"""Tests for Conversation entity."""

from src.domain.entities.conversation import Conversation


class TestConversation:
    """Test cases for Conversation entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        conversation = Conversation(
            comment="これはテスト発言です。",
            sequence_number=1,
        )

        assert conversation.comment == "これはテスト発言です。"
        assert conversation.sequence_number == 1
        assert conversation.minutes_id is None
        assert conversation.speaker_id is None
        assert conversation.speaker_name is None
        assert conversation.chapter_number is None
        assert conversation.sub_chapter_number is None
        assert conversation.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        conversation = Conversation(
            id=10,
            comment="予算案について質問します。",
            sequence_number=5,
            minutes_id=3,
            speaker_id=7,
            speaker_name="山田太郎",
            chapter_number=2,
            sub_chapter_number=1,
        )

        assert conversation.id == 10
        assert conversation.comment == "予算案について質問します。"
        assert conversation.sequence_number == 5
        assert conversation.minutes_id == 3
        assert conversation.speaker_id == 7
        assert conversation.speaker_name == "山田太郎"
        assert conversation.chapter_number == 2
        assert conversation.sub_chapter_number == 1

    def test_str_representation_with_speaker_name(self) -> None:
        """Test string representation with speaker name and ID."""
        conversation = Conversation(
            comment="短い発言",
            sequence_number=1,
            speaker_id=1,
            speaker_name="田中花子",
        )
        assert str(conversation) == "田中花子: 短い発言"

    def test_str_representation_with_speaker_id_only(self) -> None:
        """Test string representation with speaker ID but no name."""
        conversation = Conversation(
            comment="発言内容",
            sequence_number=1,
            speaker_id=42,
        )
        assert str(conversation) == "Speaker #42: 発言内容"

    def test_str_representation_without_speaker(self) -> None:
        """Test string representation without speaker information."""
        conversation = Conversation(
            comment="発言内容",
            sequence_number=1,
        )
        assert str(conversation) == "Unknown: 発言内容"

    def test_str_representation_long_comment(self) -> None:
        """Test string representation with long comment (truncated)."""
        long_comment = "これは非常に長い発言内容です。" * 10
        conversation = Conversation(
            comment=long_comment,
            sequence_number=1,
            speaker_id=1,
            speaker_name="佐藤一郎",
        )
        result = str(conversation)
        assert result.startswith("佐藤一郎: ")
        assert result.endswith("...")
        assert len(result) <= len("佐藤一郎: ") + 50 + 3  # name + 50 chars + "..."

    def test_str_representation_exactly_50_chars(self) -> None:
        """Test string representation with exactly 50 character comment."""
        # Create exactly 50 character comment
        comment_50 = "あ" * 50
        conversation = Conversation(
            comment=comment_50,
            sequence_number=1,
            speaker_id=1,
            speaker_name="テスト",
        )
        result = str(conversation)
        assert result == f"テスト: {comment_50}"
        assert not result.endswith("...")

    def test_various_sequence_numbers(self) -> None:
        """Test various sequence numbers."""
        sequence_numbers = [1, 10, 100, 1000, 9999]

        for seq_num in sequence_numbers:
            conversation = Conversation(
                comment="発言",
                sequence_number=seq_num,
            )
            assert conversation.sequence_number == seq_num

    def test_various_chapter_numbers(self) -> None:
        """Test various chapter and sub-chapter numbers."""
        test_cases = [
            (1, None),
            (1, 1),
            (5, 3),
            (10, 10),
            (None, None),
        ]

        for chapter, sub_chapter in test_cases:
            conversation = Conversation(
                comment="発言",
                sequence_number=1,
                chapter_number=chapter,
                sub_chapter_number=sub_chapter,
            )
            assert conversation.chapter_number == chapter
            assert conversation.sub_chapter_number == sub_chapter

    def test_inheritance_from_base_entity(self) -> None:
        """Test that Conversation properly inherits from BaseEntity."""
        conversation = Conversation(
            id=42,
            comment="発言",
            sequence_number=1,
        )

        # Check that id is properly set through BaseEntity
        assert conversation.id == 42

        # Create without id
        conversation_no_id = Conversation(
            comment="発言",
            sequence_number=1,
        )
        assert conversation_no_id.id is None

    def test_complex_conversation_scenarios(self) -> None:
        """Test complex real-world conversation scenarios."""
        # Question from politician
        question = Conversation(
            id=1,
            comment="議長、予算案の内訳について質問します。教育費の増額について、具体的な使途を教えてください。",
            sequence_number=10,
            minutes_id=1,
            speaker_id=5,
            speaker_name="山田太郎",
            chapter_number=3,
            sub_chapter_number=1,
        )
        assert question.speaker_name == "山田太郎"
        assert "山田太郎: " in str(question)

        # Answer from executive
        answer = Conversation(
            id=2,
            comment="お答えします。教育費の増額分は主に教員の増員と設備の改善に充てられます。",
            sequence_number=11,
            minutes_id=1,
            speaker_id=15,
            speaker_name="市長",
            chapter_number=3,
            sub_chapter_number=1,
        )
        assert answer.speaker_name == "市長"

        # Unidentified speaker
        unidentified = Conversation(
            id=3,
            comment="（発言する者あり）",
            sequence_number=12,
            minutes_id=1,
            chapter_number=3,
            sub_chapter_number=1,
        )
        assert unidentified.speaker_name is None
        assert "Unknown: " in str(unidentified)

    def test_edge_cases(self) -> None:
        """Test edge cases for Conversation entity."""
        # Empty comment
        conversation_empty = Conversation(
            comment="",
            sequence_number=1,
        )
        assert conversation_empty.comment == ""

        # Very long comment
        long_comment = "発言内容" * 1000
        conversation_long = Conversation(
            comment=long_comment,
            sequence_number=1,
        )
        assert conversation_long.comment == long_comment

        # Comment with special characters
        special_comment = "発言：（笑）、「質問」です！"
        conversation_special = Conversation(
            comment=special_comment,
            sequence_number=1,
            speaker_name="特殊文字テスト",
        )
        assert conversation_special.comment == special_comment

        # Large sequence number
        conversation_large_seq = Conversation(
            comment="発言",
            sequence_number=999999,
        )
        assert conversation_large_seq.sequence_number == 999999

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        conversation = Conversation(
            comment="発言",
            sequence_number=1,
            minutes_id=None,
            speaker_id=None,
            speaker_name=None,
            chapter_number=None,
            sub_chapter_number=None,
        )

        assert conversation.minutes_id is None
        assert conversation.speaker_id is None
        assert conversation.speaker_name is None
        assert conversation.chapter_number is None
        assert conversation.sub_chapter_number is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        conversation1 = Conversation(comment="発言1", sequence_number=1)
        assert conversation1.id is None

        # With ID
        conversation2 = Conversation(comment="発言2", sequence_number=2, id=100)
        assert conversation2.id == 100

        # ID can be any integer
        conversation3 = Conversation(comment="発言3", sequence_number=3, id=999999)
        assert conversation3.id == 999999

    def test_speaker_name_priority_over_id(self) -> None:
        """Test speaker_name priority over speaker_id in string."""
        conversation = Conversation(
            comment="発言",
            sequence_number=1,
            speaker_id=42,
            speaker_name="優先される名前",
        )
        result = str(conversation)
        assert result.startswith("優先される名前: ")
        assert "Speaker #42" not in result

    def test_comment_with_newlines(self) -> None:
        """Test comments with newline characters."""
        comment_with_newlines = "発言の1行目\n発言の2行目\n発言の3行目"
        conversation = Conversation(
            comment=comment_with_newlines,
            sequence_number=1,
            speaker_name="改行テスト",
        )
        assert conversation.comment == comment_with_newlines

    def test_zero_sequence_number(self) -> None:
        """Test conversation with sequence number 0."""
        conversation = Conversation(
            comment="発言",
            sequence_number=0,
        )
        assert conversation.sequence_number == 0

    def test_speaker_name_empty_string(self) -> None:
        """Test behavior with empty string speaker name."""
        conversation = Conversation(
            comment="発言",
            sequence_number=1,
            speaker_id=42,
            speaker_name="",
        )
        # Empty string is falsy, so should fall back to speaker_id
        result = str(conversation)
        assert "Speaker #42" in result
