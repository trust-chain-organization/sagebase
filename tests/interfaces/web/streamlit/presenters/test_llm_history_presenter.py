"""LLMHistoryPresenterのテスト"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.interfaces.web.streamlit.dto.base import WebResponseDTO


@pytest.fixture
def mock_repo():
    """LLMProcessingHistoryRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = MagicMock(return_value=[])
    repo.get_by_id = MagicMock(return_value=None)
    repo.search = MagicMock(return_value=[])
    repo.count_by_status = MagicMock(return_value=0)
    return repo


@pytest.fixture
def sample_histories():
    """サンプルLLM処理履歴リスト"""
    return [
        LLMProcessingHistory(
            id=1,
            processing_type=ProcessingType.SPEECH_EXTRACTION,
            status=ProcessingStatus.COMPLETED,
            model_name="gemini-2.0-flash",
            model_version="2.0",
            prompt_template="Extract speakers from: {text}",
            prompt_variables={"text": "sample"},
            input_reference_type="meeting",
            input_reference_id=100,
            processing_metadata={
                "token_count_input": 100,
                "token_count_output": 50,
            },
        ),
        LLMProcessingHistory(
            id=2,
            processing_type=ProcessingType.SPEAKER_MATCHING,
            status=ProcessingStatus.FAILED,
            model_name="gemini-1.5-flash",
            model_version="1.5",
            prompt_template="Match speakers: {speakers}",
            prompt_variables={"speakers": "sample"},
            input_reference_type="speaker",
            input_reference_id=200,
            error_message="Rate limit exceeded",
            processing_metadata={
                "token_count_input": 200,
                "token_count_output": 0,
            },
        ),
    ]


@pytest.fixture
def presenter(mock_repo):
    """LLMHistoryPresenterのインスタンス

    依存性をpatchで注入し、内部属性の直接上書きを避ける。
    yieldベースのフィクスチャでpatchのコンテキストをテスト全体で維持する。
    """
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.llm_history_presenter.RepositoryAdapter"
        ) as mock_adapter,
        patch(
            "src.interfaces.web.streamlit.presenters.llm_history_presenter.SessionManager"
        ) as mock_session,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_adapter.return_value = mock_repo

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.llm_history_presenter import (
            LLMHistoryPresenter,
        )

        # patchにより依存性が注入されたPresenterを作成
        yield LLMHistoryPresenter()


class TestLLMHistoryPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.llm_history_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.llm_history_presenter.SessionManager"
            ) as mock_session,
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.llm_history_presenter import (
                LLMHistoryPresenter,
            )

            presenter = LLMHistoryPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_returns_histories(self, presenter, mock_repo, sample_histories):
        """LLM処理履歴を読み込めることを確認"""
        # Arrange
        mock_repo.get_all.return_value = sample_histories

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
        presenter.search_histories = MagicMock(
            return_value=WebResponseDTO.success_response({})
        )

        # Act
        presenter.handle_action("search", limit=10)

        # Assert
        presenter.search_histories.assert_called_once_with(limit=10)

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
        presenter.handle_action("export_csv", histories=[])

        # Assert
        presenter.export_to_csv.assert_called_once()

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")


class TestSearchHistories:
    """search_historiesメソッドのテスト"""

    def test_search_histories_success(self, presenter, mock_repo, sample_histories):
        """履歴を検索できることを確認"""
        # Arrange
        mock_repo.search.return_value = sample_histories
        mock_repo.count_by_status.return_value = 2

        # Act
        result = presenter.search_histories()

        # Assert
        assert result.success is True
        assert "histories" in result.data

    def test_search_histories_with_filters(
        self, presenter, mock_repo, sample_histories
    ):
        """フィルタ付きで検索できることを確認"""
        # Arrange
        mock_repo.search.return_value = [sample_histories[0]]
        mock_repo.count_by_status.return_value = 1

        # Act - ProcessingTypeの値はspeech_extraction
        result = presenter.search_histories(
            processing_type="speech_extraction",
            model_name="gemini-2.0-flash",
            status="completed",
        )

        # Assert
        assert result.success is True

    def test_search_histories_exception(self, presenter, mock_repo):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        mock_repo.search.side_effect = Exception("Database error")

        # Act
        result = presenter.search_histories()

        # Assert
        assert result.success is False
        assert "検索に失敗" in result.message


class TestGetStatistics:
    """get_statisticsメソッドのテスト"""

    def test_get_statistics_success(self, presenter, mock_repo, sample_histories):
        """統計情報を取得できることを確認"""
        # Arrange
        mock_repo.search.return_value = sample_histories

        # Act
        result = presenter.get_statistics()

        # Assert
        assert result.success is True
        assert "total_count" in result.data
        assert "completed_count" in result.data
        assert "failed_count" in result.data

    def test_get_statistics_with_date_range(
        self, presenter, mock_repo, sample_histories
    ):
        """日付範囲付きで統計情報を取得できることを確認"""
        # Arrange
        mock_repo.search.return_value = sample_histories

        # Act
        result = presenter.get_statistics(
            start_date=datetime(2024, 1, 1), end_date=datetime(2024, 12, 31)
        )

        # Assert
        assert result.success is True

    def test_get_statistics_exception(self, presenter, mock_repo):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        mock_repo.search.side_effect = Exception("Database error")

        # Act
        result = presenter.get_statistics()

        # Assert
        assert result.success is False
        assert "統計情報の取得に失敗" in result.message


class TestExportToCsv:
    """export_to_csvメソッドのテスト"""

    def test_export_to_csv_success(self, presenter, sample_histories):
        """CSVにエクスポートできることを確認"""
        # Act
        result = presenter.export_to_csv(sample_histories)

        # Assert
        assert isinstance(result, str)
        assert "ID" in result
        assert "処理タイプ" in result
        assert "ステータス" in result

    def test_export_to_csv_empty(self, presenter):
        """空のリストで空文字列を返すことを確認"""
        # Act
        result = presenter.export_to_csv([])

        # Assert
        assert result == ""


class TestGetProcessingTypes:
    """get_processing_typesメソッドのテスト"""

    def test_get_processing_types(self, presenter):
        """処理タイプを取得できることを確認"""
        # Act
        result = presenter.get_processing_types()

        # Assert
        assert "すべて" in result
        assert len(result) > 1


class TestGetModelNames:
    """get_model_namesメソッドのテスト"""

    def test_get_model_names(self, presenter):
        """モデル名を取得できることを確認"""
        # Act
        result = presenter.get_model_names()

        # Assert
        assert "すべて" in result
        assert "gemini-2.0-flash" in result
        assert "gemini-1.5-flash" in result


class TestGetStatuses:
    """get_statusesメソッドのテスト"""

    def test_get_statuses(self, presenter):
        """ステータスを取得できることを確認"""
        # Act
        result = presenter.get_statuses()

        # Assert
        assert "すべて" in result
        assert len(result) > 1


class TestGetHistoryDetail:
    """get_history_detailメソッドのテスト"""

    def test_get_history_detail_success(self, presenter, mock_repo, sample_histories):
        """履歴詳細を取得できることを確認"""
        # Arrange
        mock_repo.get_by_id.return_value = sample_histories[0]

        # Act
        result = presenter.get_history_detail(1)

        # Assert
        assert result.success is True
        assert result.data["id"] == 1

    def test_get_history_detail_not_found(self, presenter, mock_repo):
        """履歴が見つからない場合のエラーを確認"""
        # Arrange
        mock_repo.get_by_id.return_value = None

        # Act
        result = presenter.get_history_detail(999)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message

    def test_get_history_detail_exception(self, presenter, mock_repo):
        """例外発生時にエラーレスポンスを返すことを確認"""
        # Arrange
        mock_repo.get_by_id.side_effect = Exception("Database error")

        # Act
        result = presenter.get_history_detail(1)

        # Assert
        assert result.success is False
        assert "取得に失敗" in result.message
