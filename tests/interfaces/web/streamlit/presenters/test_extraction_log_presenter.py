"""ExtractionLogPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.interfaces.web.streamlit.dto.base import WebResponseDTO


@pytest.fixture
def mock_usecase():
    """GetExtractionLogsUseCaseのモック"""
    usecase = AsyncMock()
    usecase.execute = AsyncMock()
    usecase.get_statistics = AsyncMock()
    usecase.get_by_id = AsyncMock()
    usecase.get_by_entity = AsyncMock()
    usecase.get_entity_types = MagicMock(return_value=[e.value for e in EntityType])
    usecase.get_pipeline_versions = AsyncMock(return_value=["v1.0", "v2.0"])
    return usecase


@pytest.fixture
def mock_repo():
    """ExtractionLogRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    return repo


@pytest.fixture
def sample_logs():
    """サンプル抽出ログリスト"""
    return [
        ExtractionLog(
            id=1,
            entity_type=EntityType.SPEAKER,
            entity_id=100,
            pipeline_version="v1.0",
            extracted_data={"name": "田中太郎"},
            confidence_score=0.95,
            extraction_metadata={"model_name": "gemini-2.0-flash"},
        ),
        ExtractionLog(
            id=2,
            entity_type=EntityType.POLITICIAN,
            entity_id=200,
            pipeline_version="v2.0",
            extracted_data={"name": "山田花子"},
            confidence_score=0.88,
            extraction_metadata={"model_name": "gemini-1.5-flash"},
        ),
    ]


@pytest.fixture
def presenter(mock_usecase, mock_repo):
    """ExtractionLogPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.extraction_log_presenter.create_repository_adapter"
        ) as mock_create_repo,
        patch(
            "src.interfaces.web.streamlit.presenters.extraction_log_presenter.GetExtractionLogsUseCase"
        ) as mock_uc_class,
        patch(
            "src.interfaces.web.streamlit.presenters.extraction_log_presenter.SessionManager"
        ) as mock_session,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_create_repo.return_value = mock_repo
        mock_uc_class.return_value = mock_usecase

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.extraction_log_presenter import (
            ExtractionLogPresenter,
        )

        presenter = ExtractionLogPresenter()
        presenter._usecase = mock_usecase
        presenter._extraction_log_repo = mock_repo
        return presenter


class TestExtractionLogPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.extraction_log_presenter.create_repository_adapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.extraction_log_presenter.GetExtractionLogsUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.extraction_log_presenter.SessionManager"
            ) as mock_session,
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.extraction_log_presenter import (  # noqa: E501
                ExtractionLogPresenter,
            )

            presenter = ExtractionLogPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_returns_logs(self, presenter, mock_repo, sample_logs):
        """抽出ログを読み込めることを確認"""
        # Arrange
        mock_repo.get_all.return_value = sample_logs

        # Act
        result = presenter.load_data()

        # Assert
        assert len(result) == 2
        mock_repo.get_all.assert_called_once()


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_search(self, presenter):
        """searchアクションが正しく処理されることを確認"""
        # Arrange
        presenter.search_logs = MagicMock(
            return_value=WebResponseDTO.success_response([])
        )

        # Act
        presenter.handle_action("search", limit=10)

        # Assert
        presenter.search_logs.assert_called_once_with(limit=10)

    def test_handle_action_get_statistics(self, presenter):
        """get_statisticsアクションが正しく処理されることを確認"""
        # Arrange
        presenter.get_statistics = MagicMock(
            return_value=WebResponseDTO.success_response({})
        )

        # Act
        presenter.handle_action("get_statistics")

        # Assert
        presenter.get_statistics.assert_called_once()

    def test_handle_action_export_csv(self, presenter):
        """export_csvアクションが正しく処理されることを確認"""
        # Arrange
        presenter.export_to_csv = MagicMock(return_value="")

        # Act
        presenter.handle_action("export_csv", logs=[])

        # Assert
        presenter.export_to_csv.assert_called_once()

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")


class TestSearchLogs:
    """search_logsメソッドのテスト"""

    def test_search_logs_success(self, presenter, mock_usecase, sample_logs):
        """ログを検索できることを確認"""
        # Arrange
        mock_result = MagicMock()
        mock_result.logs = sample_logs
        mock_result.total_count = 2
        mock_result.page_size = 25
        mock_result.current_offset = 0
        mock_usecase.execute.return_value = mock_result
        presenter._run_async = MagicMock(return_value=mock_result)

        # Act
        result = presenter.search_logs()

        # Assert
        assert result.success is True
        assert result.data["total_count"] == 2

    def test_search_logs_with_filters(self, presenter, mock_usecase, sample_logs):
        """フィルタ付きで検索できることを確認"""
        # Arrange
        mock_result = MagicMock()
        mock_result.logs = [sample_logs[0]]
        mock_result.total_count = 1
        mock_result.page_size = 25
        mock_result.current_offset = 0
        presenter._run_async = MagicMock(return_value=mock_result)

        # Act
        result = presenter.search_logs(
            entity_type="speaker",
            pipeline_version="v1.0",
            min_confidence_score=0.9,
        )

        # Assert
        assert result.success is True

    def test_search_logs_exception(self, presenter):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        presenter._run_async = MagicMock(side_effect=Exception("Database error"))

        # Act
        result = presenter.search_logs()

        # Assert
        assert result.success is False
        assert "検索に失敗" in result.message


class TestGetStatistics:
    """get_statisticsメソッドのテスト"""

    def test_get_statistics_success(self, presenter, mock_usecase):
        """統計情報を取得できることを確認"""
        # Arrange
        mock_stats = MagicMock()
        mock_stats.total_count = 100
        mock_stats.by_entity_type = {"speaker": 50, "politician": 50}
        mock_stats.by_pipeline_version = {"v1.0": 60, "v2.0": 40}
        mock_stats.average_confidence = 0.92
        mock_stats.daily_counts = []
        mock_stats.confidence_by_pipeline = {"v1.0": 0.95, "v2.0": 0.88}
        presenter._run_async = MagicMock(return_value=mock_stats)

        # Act
        result = presenter.get_statistics()

        # Assert
        assert result.success is True
        assert result.data["total_count"] == 100

    def test_get_statistics_exception(self, presenter):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        presenter._run_async = MagicMock(side_effect=Exception("Database error"))

        # Act
        result = presenter.get_statistics()

        # Assert
        assert result.success is False
        assert "統計情報の取得に失敗" in result.message


class TestExportToCsv:
    """export_to_csvメソッドのテスト"""

    def test_export_to_csv_success(self, presenter, sample_logs):
        """CSVにエクスポートできることを確認"""
        # Act
        result = presenter.export_to_csv(sample_logs)

        # Assert
        assert isinstance(result, str)
        assert "ID" in result
        assert "エンティティタイプ" in result

    def test_export_to_csv_empty(self, presenter):
        """空のリストで空文字列を返すことを確認"""
        # Act
        result = presenter.export_to_csv([])

        # Assert
        assert result == ""


class TestGetEntityTypes:
    """get_entity_typesメソッドのテスト"""

    def test_get_entity_types(self, presenter, mock_usecase):
        """エンティティタイプを取得できることを確認"""
        # Act
        result = presenter.get_entity_types()

        # Assert
        assert "すべて" in result
        assert len(result) > 1


class TestGetPipelineVersions:
    """get_pipeline_versionsメソッドのテスト"""

    def test_get_pipeline_versions_success(self, presenter):
        """パイプラインバージョンを取得できることを確認"""
        # Arrange
        presenter._run_async = MagicMock(return_value=["v1.0", "v2.0"])

        # Act
        result = presenter.get_pipeline_versions()

        # Assert
        assert "すべて" in result
        assert "v1.0" in result

    def test_get_pipeline_versions_exception(self, presenter):
        """例外発生時にデフォルトを返すことを確認"""
        # Arrange
        presenter._run_async = MagicMock(side_effect=Exception("Error"))

        # Act
        result = presenter.get_pipeline_versions()

        # Assert
        assert result == ["すべて"]


class TestGetLogDetail:
    """get_log_detailメソッドのテスト"""

    def test_get_log_detail_success(self, presenter, sample_logs):
        """ログ詳細を取得できることを確認"""
        # Arrange
        presenter._run_async = MagicMock(return_value=sample_logs[0])

        # Act
        result = presenter.get_log_detail(1)

        # Assert
        assert result.success is True
        assert result.data["id"] == 1

    def test_get_log_detail_not_found(self, presenter):
        """ログが見つからない場合のエラーを確認"""
        # Arrange
        presenter._run_async = MagicMock(return_value=None)

        # Act
        result = presenter.get_log_detail(999)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message


class TestGetEntityHistory:
    """get_entity_historyメソッドのテスト"""

    def test_get_entity_history_success(self, presenter, sample_logs):
        """エンティティ履歴を取得できることを確認"""
        # Arrange
        presenter._run_async = MagicMock(return_value=[sample_logs[0]])

        # Act
        result = presenter.get_entity_history("speaker", 100)

        # Assert
        assert result.success is True
        assert result.data["total_count"] == 1

    def test_get_entity_history_exception(self, presenter):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        presenter._run_async = MagicMock(side_effect=Exception("Database error"))

        # Act
        result = presenter.get_entity_history("speaker", 100)

        # Assert
        assert result.success is False
        assert "取得に失敗" in result.message
