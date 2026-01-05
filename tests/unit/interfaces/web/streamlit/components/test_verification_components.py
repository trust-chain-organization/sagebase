"""検証コンポーネントの単体テスト。"""

import pytest

from src.interfaces.web.streamlit.components.verification_badge import (
    get_verification_badge_html,
    get_verification_badge_text,
)
from src.interfaces.web.streamlit.components.verification_filter import (
    filter_by_verification_status,
)


class TestVerificationBadge:
    """verification_badgeコンポーネントのテスト。"""

    def test_get_verification_badge_text_verified(self) -> None:
        """手動検証済みの場合のテキストテスト。"""
        result = get_verification_badge_text(True)
        assert result == "✅ 手動検証済み"

    def test_get_verification_badge_text_unverified(self) -> None:
        """未検証の場合のテキストテスト。"""
        result = get_verification_badge_text(False)
        assert result == "🤖 AI抽出"

    def test_get_verification_badge_html_verified(self) -> None:
        """手動検証済みの場合のHTMLテスト。"""
        result = get_verification_badge_html(True)
        assert "手動検証済み" in result
        assert "#e8f5e9" in result  # 薄緑背景

    def test_get_verification_badge_html_unverified(self) -> None:
        """未検証の場合のHTMLテスト。"""
        result = get_verification_badge_html(False)
        assert "AI抽出" in result
        assert "#e3f2fd" in result  # 薄青背景


class MockEntity:
    """テスト用のモックエンティティ。"""

    def __init__(self, id: int, is_manually_verified: bool):
        self.id = id
        self.is_manually_verified = is_manually_verified


class TestVerificationFilter:
    """verification_filterコンポーネントのテスト。"""

    @pytest.fixture
    def sample_entities(self) -> list[MockEntity]:
        """テスト用エンティティリスト。"""
        return [
            MockEntity(1, True),
            MockEntity(2, False),
            MockEntity(3, True),
            MockEntity(4, False),
            MockEntity(5, False),
        ]

    def test_filter_all_entities(self, sample_entities: list[MockEntity]) -> None:
        """フィルタなし（全件）のテスト。"""
        result = filter_by_verification_status(sample_entities, None)
        assert len(result) == 5

    def test_filter_verified_only(self, sample_entities: list[MockEntity]) -> None:
        """手動検証済みのみフィルタのテスト。"""
        result = filter_by_verification_status(sample_entities, True)
        assert len(result) == 2
        assert all(e.is_manually_verified for e in result)

    def test_filter_unverified_only(self, sample_entities: list[MockEntity]) -> None:
        """未検証のみフィルタのテスト。"""
        result = filter_by_verification_status(sample_entities, False)
        assert len(result) == 3
        assert all(not e.is_manually_verified for e in result)

    def test_filter_empty_list(self) -> None:
        """空リストのフィルタテスト。"""
        result = filter_by_verification_status([], True)
        assert len(result) == 0

    def test_filter_all_verified(self) -> None:
        """全件検証済みの場合のテスト。"""
        entities = [
            MockEntity(1, True),
            MockEntity(2, True),
        ]
        result = filter_by_verification_status(entities, True)
        assert len(result) == 2

        result = filter_by_verification_status(entities, False)
        assert len(result) == 0

    def test_filter_all_unverified(self) -> None:
        """全件未検証の場合のテスト。"""
        entities = [
            MockEntity(1, False),
            MockEntity(2, False),
        ]
        result = filter_by_verification_status(entities, False)
        assert len(result) == 2

        result = filter_by_verification_status(entities, True)
        assert len(result) == 0
