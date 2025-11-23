"""ユーザー統計プレゼンターのテスト"""

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pandas as pd
import pytest

from src.application.dtos.user_statistics_dto import (
    ContributorRank,
    TimelineDataPoint,
    UserStatisticsDTO,
)
from src.application.dtos.work_history_dto import WorkType
from src.interfaces.web.streamlit.presenters.user_statistics_presenter import (
    UserStatisticsPresenter,
)


@pytest.fixture
def sample_statistics_dto():
    """サンプル統計DTO"""
    return UserStatisticsDTO(
        total_count=10,
        work_type_counts={
            WorkType.SPEAKER_POLITICIAN_MATCHING.value: 6,
            WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION.value: 4,
        },
        user_counts={"User1 (user1@example.com)": 6, "User2 (user2@example.com)": 4},
        timeline_data=[
            TimelineDataPoint(date=date(2024, 1, 1), count=5, work_type=None),
            TimelineDataPoint(date=date(2024, 1, 2), count=5, work_type=None),
        ],
        top_contributors=[
            ContributorRank(
                rank=1,
                user_name="User1",
                user_email="user1@example.com",
                total_works=6,
                work_type_breakdown={
                    WorkType.SPEAKER_POLITICIAN_MATCHING.value: 4,
                    WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION.value: 2,
                },
            ),
        ],
    )


def test_get_timeline_dataframe_success(sample_statistics_dto):
    """時系列データのDataFrame変換が成功することを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()

    # Act
    result = presenter.get_timeline_dataframe(sample_statistics_dto)

    # Assert
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "日付" in result.columns
    assert "作業件数" in result.columns
    assert result["作業件数"].sum() == 10


def test_get_timeline_dataframe_empty():
    """空の時系列データの場合にNoneを返すことを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()
    empty_stats = UserStatisticsDTO(
        total_count=0,
        work_type_counts={},
        user_counts={},
        timeline_data=[],  # 空
        top_contributors=[],
    )

    # Act
    result = presenter.get_timeline_dataframe(empty_stats)

    # Assert
    assert result is None


def test_get_contributors_dataframe_success(sample_statistics_dto):
    """貢献者データのDataFrame変換が成功することを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()

    # Act
    result = presenter.get_contributors_dataframe(sample_statistics_dto)

    # Assert
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1
    assert "順位" in result.columns
    assert "ユーザー名" in result.columns
    assert "総作業件数" in result.columns
    assert result.iloc[0]["総作業件数"] == 6


def test_get_contributors_dataframe_empty():
    """空の貢献者データの場合にNoneを返すことを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()
    empty_stats = UserStatisticsDTO(
        total_count=0,
        work_type_counts={},
        user_counts={},
        timeline_data=[],
        top_contributors=[],  # 空
    )

    # Act
    result = presenter.get_contributors_dataframe(empty_stats)

    # Assert
    assert result is None


def test_get_work_type_display_names():
    """作業タイプの表示名マッピングが正しいことを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()

    # Act
    display_names = presenter.get_work_type_display_names()

    # Assert
    assert WorkType.SPEAKER_POLITICIAN_MATCHING in display_names
    assert display_names[WorkType.SPEAKER_POLITICIAN_MATCHING] == "発言者-政治家紐付け"
    assert WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION in display_names
    assert (
        display_names[WorkType.PARLIAMENTARY_GROUP_MEMBERSHIP_CREATION]
        == "議員団メンバー作成"
    )


def test_get_statistics_success():
    """統計取得が成功することを確認"""
    # Arrange
    user_id = uuid4()
    expected_stats = UserStatisticsDTO(
        total_count=5,
        work_type_counts={WorkType.SPEAKER_POLITICIAN_MATCHING.value: 5},
        user_counts={"Test User (test@example.com)": 5},
        timeline_data=[
            TimelineDataPoint(date=date(2024, 1, 1), count=5, work_type=None)
        ],
        top_contributors=[
            ContributorRank(
                rank=1,
                user_name="Test User",
                user_email="test@example.com",
                total_works=5,
                work_type_breakdown={WorkType.SPEAKER_POLITICIAN_MATCHING.value: 5},
            )
        ],
    )

    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()

        # UseCaseのexecuteメソッドをモック
        with patch.object(
            presenter.user_statistics_usecase, "execute", return_value=expected_stats
        ):
            # Act
            result = presenter.get_statistics(user_id=user_id)

            # Assert
            assert result == expected_stats
            # asyncio.runが呼ばれることを確認（実際にはexecuteが呼ばれる）


def test_get_statistics_error_handling():
    """統計取得時のエラーハンドリングを確認"""
    # Arrange
    with patch(
        "src.interfaces.web.streamlit.presenters.user_statistics_presenter.Container"
    ):
        presenter = UserStatisticsPresenter()

        with patch(
            "src.interfaces.web.streamlit.presenters.user_statistics_presenter.asyncio.run",
            side_effect=Exception("Database error"),
        ):
            with patch(
                "src.interfaces.web.streamlit.presenters.user_statistics_presenter.st"
            ):
                # Act
                result = presenter.get_statistics()

                # Assert - エラー時は空の統計を返す
                assert result.total_count == 0
                assert len(result.work_type_counts) == 0
