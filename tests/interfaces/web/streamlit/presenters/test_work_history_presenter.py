"""WorkHistoryPresenterのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.dtos.work_history_dto import WorkHistoryDTO, WorkType


@pytest.fixture
def mock_use_case():
    """GetWorkHistoryUseCaseのモック"""
    use_case = AsyncMock()
    use_case.execute = AsyncMock(return_value=[])
    use_case.get_work_statistics_by_type = AsyncMock(return_value={})
    use_case.get_top_contributors = AsyncMock(return_value=[])
    return use_case


@pytest.fixture
def sample_histories():
    """サンプル作業履歴リスト"""
    return [
        WorkHistoryDTO(
            user_id=uuid4(),
            user_name="テストユーザー1",
            user_email="test1@example.com",
            work_type=WorkType.SPEAKER_POLITICIAN_MATCHING,
            target_data="発言者ID: 100 を 政治家ID: 1 に紐付け",
            executed_at=datetime(2024, 1, 15, 10, 0, 0),
        ),
        WorkHistoryDTO(
            user_id=uuid4(),
            user_name="テストユーザー2",
            user_email="test2@example.com",
            work_type=WorkType.POLITICIAN_CREATE,
            target_data="政治家「山田花子」を作成",
            executed_at=datetime(2024, 1, 16, 11, 0, 0),
        ),
    ]


@pytest.fixture
def presenter(mock_use_case):
    """WorkHistoryPresenterのインスタンス"""
    with patch(
        "src.interfaces.web.streamlit.presenters.work_history_presenter.Container"
    ) as mock_container:
        mock_repos = MagicMock()
        mock_repos.speaker_repository.return_value = MagicMock()
        mock_repos.parliamentary_group_membership_repository.return_value = MagicMock()
        mock_repos.user_repository.return_value = MagicMock()
        mock_repos.politician_operation_log_repository.return_value = MagicMock()
        mock_container.return_value.repositories = mock_repos

        with patch(
            "src.interfaces.web.streamlit.presenters.work_history_presenter.GetWorkHistoryUseCase"
        ) as mock_uc_class:
            mock_uc_class.return_value = mock_use_case

            from src.interfaces.web.streamlit.presenters.work_history_presenter import (
                WorkHistoryPresenter,
            )

            presenter = WorkHistoryPresenter()
            presenter.work_history_usecase = mock_use_case
            return presenter


class TestWorkHistoryPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with patch(
            "src.interfaces.web.streamlit.presenters.work_history_presenter.Container"
        ) as mock_container:
            mock_repos = MagicMock()
            mock_repos.speaker_repository.return_value = MagicMock()
            mock_repos.parliamentary_group_membership_repository.return_value = (
                MagicMock()
            )
            mock_repos.user_repository.return_value = MagicMock()
            mock_repos.politician_operation_log_repository.return_value = MagicMock()
            mock_container.return_value.repositories = mock_repos

            with patch(
                "src.interfaces.web.streamlit.presenters.work_history_presenter.GetWorkHistoryUseCase"
            ):
                from src.interfaces.web.streamlit.presenters.work_history_presenter import (  # noqa: E501
                    WorkHistoryPresenter,
                )

                presenter = WorkHistoryPresenter()
                assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_does_nothing(self, presenter):
        """load_dataが何も行わないことを確認"""
        # Act
        result = presenter.load_data()

        # Assert
        assert result is None


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_does_nothing(self, presenter):
        """handle_actionが何も行わないことを確認"""
        # Act
        result = presenter.handle_action("test", param="value")

        # Assert
        assert result is None


class TestSearchHistories:
    """search_historiesメソッドのテスト"""

    def test_search_histories_success(self, presenter, mock_use_case, sample_histories):
        """作業履歴を検索できることを確認"""
        # Arrange
        mock_use_case.execute.return_value = sample_histories

        with patch("asyncio.run", return_value=sample_histories):
            # Act
            result = presenter.search_histories()

            # Assert
            assert len(result) == 2

    def test_search_histories_with_filters(
        self, presenter, mock_use_case, sample_histories
    ):
        """フィルタ付きで作業履歴を検索できることを確認"""
        # Arrange
        user_id = uuid4()
        mock_use_case.execute.return_value = [sample_histories[0]]

        with patch("asyncio.run", return_value=[sample_histories[0]]):
            # Act
            result = presenter.search_histories(
                user_id=user_id,
                work_types=[WorkType.SPEAKER_POLITICIAN_MATCHING],
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                limit=10,
                offset=0,
            )

            # Assert
            assert len(result) == 1

    def test_search_histories_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        with (
            patch("asyncio.run", side_effect=Exception("Database error")),
            patch(
                "src.interfaces.web.streamlit.presenters.work_history_presenter.st"
            ) as mock_st,
        ):
            # Act
            result = presenter.search_histories()

            # Assert
            assert result == []
            mock_st.error.assert_called_once()


class TestGetStatistics:
    """get_statisticsメソッドのテスト"""

    def test_get_statistics_success(self, presenter, mock_use_case):
        """統計情報を取得できることを確認"""
        # Arrange
        type_stats = {
            WorkType.SPEAKER_POLITICIAN_MATCHING: 10,
            WorkType.POLITICIAN_CREATE: 5,
        }
        contributors = [
            {
                "user_id": uuid4(),
                "user_name": "User1",
                "user_email": "user1@example.com",
                "total_count": 8,
            },
            {
                "user_id": uuid4(),
                "user_name": "User2",
                "user_email": "user2@example.com",
                "total_count": 7,
            },
        ]

        with patch("asyncio.run", side_effect=[type_stats, contributors]):
            # Act
            result = presenter.get_statistics()

            # Assert
            assert "total_count" in result
            assert "work_type_counts" in result
            assert "user_counts" in result

    def test_get_statistics_exception(self, presenter, mock_use_case):
        """例外発生時にデフォルト値を返すことを確認"""
        # Arrange
        with (
            patch("asyncio.run", side_effect=Exception("Database error")),
            patch(
                "src.interfaces.web.streamlit.presenters.work_history_presenter.st"
            ) as mock_st,
        ):
            # Act
            result = presenter.get_statistics()

            # Assert
            assert result["total_count"] == 0
            assert result["work_type_counts"] == {}
            assert result["user_counts"] == {}
            mock_st.error.assert_called_once()


class TestGetWorkTypes:
    """get_work_typesメソッドのテスト"""

    def test_get_work_types(self, presenter):
        """作業タイプのリストを取得できることを確認"""
        # Act
        result = presenter.get_work_types()

        # Assert
        assert isinstance(result, list)
        assert len(result) > 0
        assert WorkType.SPEAKER_POLITICIAN_MATCHING in result
        assert WorkType.POLITICIAN_CREATE in result


class TestGetWorkTypeDisplayNames:
    """get_work_type_display_namesメソッドのテスト"""

    def test_get_work_type_display_names(self, presenter):
        """作業タイプの表示名を取得できることを確認"""
        # Act
        result = presenter.get_work_type_display_names()

        # Assert
        assert isinstance(result, dict)
        assert WorkType.SPEAKER_POLITICIAN_MATCHING in result
        assert result[WorkType.SPEAKER_POLITICIAN_MATCHING] == "発言者-政治家紐付け"
        assert WorkType.POLITICIAN_CREATE in result
        assert result[WorkType.POLITICIAN_CREATE] == "政治家作成"
