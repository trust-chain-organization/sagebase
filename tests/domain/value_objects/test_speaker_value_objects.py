"""Tests for Speaker-related value objects."""

from dataclasses import FrozenInstanceError

import pytest

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.domain.value_objects.speaker_with_politician import SpeakerWithPolitician


class TestSpeakerWithPolitician:
    """SpeakerWithPolitician Value Objectのテスト"""

    def test_create_with_politician(self) -> None:
        """政治家情報ありでValue Objectを作成できることを確認"""
        speaker = Speaker(id=1, name="Test Speaker")
        politician = Politician(
            id=1, name="Test Politician", prefecture="東京都", district="東京1区"
        )
        vo = SpeakerWithPolitician(speaker=speaker, politician=politician)

        assert vo.speaker == speaker
        assert vo.politician == politician

    def test_create_without_politician(self) -> None:
        """政治家情報なしでValue Objectを作成できることを確認"""
        speaker = Speaker(id=1, name="Test Speaker")
        vo = SpeakerWithPolitician(speaker=speaker, politician=None)

        assert vo.speaker == speaker
        assert vo.politician is None

    def test_immutability(self) -> None:
        """イミュータビリティのテスト（frozen dataclass）"""
        speaker = Speaker(id=1, name="Test Speaker")
        politician = Politician(
            id=1, name="Test Politician", prefecture="東京都", district="東京1区"
        )
        vo = SpeakerWithPolitician(speaker=speaker, politician=politician)

        with pytest.raises(FrozenInstanceError):
            vo.speaker = Speaker(id=2, name="Other Speaker")  # type: ignore

    def test_equality_with_same_values(self) -> None:
        """同じ値を持つインスタンスの等価性テスト"""
        speaker = Speaker(id=1, name="Test Speaker")
        politician = Politician(
            id=1, name="Test Politician", prefecture="東京都", district="東京1区"
        )
        vo1 = SpeakerWithPolitician(speaker=speaker, politician=politician)
        vo2 = SpeakerWithPolitician(speaker=speaker, politician=politician)

        assert vo1 == vo2

    def test_inequality_with_different_values(self) -> None:
        """異なる値を持つインスタンスが等価でないことを確認"""
        speaker1 = Speaker(id=1, name="Speaker 1")
        speaker2 = Speaker(id=2, name="Speaker 2")
        politician = Politician(
            id=1, name="Test Politician", prefecture="東京都", district="東京1区"
        )

        vo1 = SpeakerWithPolitician(speaker=speaker1, politician=politician)
        vo2 = SpeakerWithPolitician(speaker=speaker2, politician=politician)

        assert vo1 != vo2

    def test_hashable(self) -> None:
        """ハッシュ可能性のテスト（setやdictのキーとして使用可能）"""
        speaker = Speaker(id=1, name="Test Speaker")
        vo = SpeakerWithPolitician(speaker=speaker, politician=None)

        # setに追加可能
        vo_set = {vo}
        assert vo in vo_set

        # dictのキーとして使用可能
        vo_dict = {vo: "test"}
        assert vo_dict[vo] == "test"


class TestSpeakerWithConversationCount:
    """SpeakerWithConversationCount Value Objectのテスト"""

    def test_create_value_object(self) -> None:
        """Value Objectを作成できることを確認"""
        vo = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type="議員",
            political_party_name="テスト党",
            position="委員",
            is_politician=True,
            conversation_count=10,
        )

        assert vo.id == 1
        assert vo.name == "Test Speaker"
        assert vo.type == "議員"
        assert vo.political_party_name == "テスト党"
        assert vo.position == "委員"
        assert vo.is_politician is True
        assert vo.conversation_count == 10

    def test_create_with_none_fields(self) -> None:
        """None値を持つフィールドでValue Objectを作成できることを確認"""
        vo = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=0,
        )

        assert vo.type is None
        assert vo.political_party_name is None
        assert vo.position is None
        assert vo.is_politician is False
        assert vo.conversation_count == 0

    def test_immutability(self) -> None:
        """イミュータビリティのテスト（frozen dataclass）"""
        vo = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
        )

        with pytest.raises(FrozenInstanceError):
            vo.conversation_count = 10  # type: ignore

    def test_equality_with_same_values(self) -> None:
        """同じ値を持つインスタンスの等価性テスト"""
        vo1 = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type="議員",
            political_party_name="テスト党",
            position="委員",
            is_politician=True,
            conversation_count=10,
        )
        vo2 = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type="議員",
            political_party_name="テスト党",
            position="委員",
            is_politician=True,
            conversation_count=10,
        )

        assert vo1 == vo2

    def test_inequality_with_different_conversation_count(self) -> None:
        """発言回数が異なる場合に等価でないことを確認"""
        vo1 = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
        )
        vo2 = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=10,
        )

        assert vo1 != vo2

    def test_hashable(self) -> None:
        """ハッシュ可能性のテスト"""
        vo = SpeakerWithConversationCount(
            id=1,
            name="Test Speaker",
            type=None,
            political_party_name=None,
            position=None,
            is_politician=False,
            conversation_count=5,
        )

        # setに追加可能
        vo_set = {vo}
        assert vo in vo_set

        # dictのキーとして使用可能
        vo_dict = {vo: "test"}
        assert vo_dict[vo] == "test"
