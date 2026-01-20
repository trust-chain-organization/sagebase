"""PoliticalPartyPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_political_parties_usecase import (
    GenerateSeedFileOutputDto,
    ManagePoliticalPartiesUseCase,
    PoliticalPartyListOutputDto,
    PoliticalPartyStatistics,
    UpdatePoliticalPartyUrlOutputDto,
)
from src.domain.entities.political_party import PoliticalParty


@pytest.fixture
def mock_use_case():
    """ManagePoliticalPartiesUseCaseのモック"""
    return AsyncMock(spec=ManagePoliticalPartiesUseCase)


@pytest.fixture
def sample_parties():
    """サンプル政党リスト"""
    return [
        PoliticalParty(
            id=1, name="自民党", members_list_url="https://example.com/jimin"
        ),
        PoliticalParty(id=2, name="立憲民主党", members_list_url=None),
    ]


@pytest.fixture
def sample_statistics():
    """サンプル統計情報"""
    return PoliticalPartyStatistics(
        total=2,
        with_url=1,
        without_url=1,
    )


@pytest.fixture
def presenter(mock_use_case):
    """PoliticalPartyPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.political_party_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.political_party_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.political_party_presenter.ManagePoliticalPartiesUseCase"
        ) as mock_uc_class,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.political_party_presenter import (
            PoliticalPartyPresenter,
        )

        presenter = PoliticalPartyPresenter()
        presenter.use_case = mock_use_case
        return presenter


class TestPoliticalPartyPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.political_party_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.political_party_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.political_party_presenter.ManagePoliticalPartiesUseCase"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.political_party_presenter import (  # noqa: E501
                PoliticalPartyPresenter,
            )

            presenter = PoliticalPartyPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    async def test_load_data_filtered_success(
        self, presenter, mock_use_case, sample_parties, sample_statistics
    ):
        """政党リストをフィルタ付きで読み込めることを確認"""
        # Arrange
        mock_use_case.list_parties.return_value = PoliticalPartyListOutputDto(
            parties=sample_parties, statistics=sample_statistics
        )

        # Act
        result = await presenter._load_data_filtered_async("all")

        # Assert
        assert len(result.parties) == 2
        assert result.statistics.total == 2

    async def test_load_data_filtered_with_url(
        self, presenter, mock_use_case, sample_parties, sample_statistics
    ):
        """URL設定済みフィルタで読み込めることを確認"""
        # Arrange
        mock_use_case.list_parties.return_value = PoliticalPartyListOutputDto(
            parties=[sample_parties[0]], statistics=sample_statistics
        )

        # Act
        result = await presenter._load_data_filtered_async("with_url")

        # Assert
        assert len(result.parties) == 1
        mock_use_case.list_parties.assert_called_once()

    async def test_load_data_filtered_exception(self, presenter, mock_use_case):
        """例外発生時にエラーを伝播することを確認"""
        # Arrange
        mock_use_case.list_parties.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await presenter._load_data_filtered_async("all")


class TestCRUDOperations:
    """CRUD操作のテスト"""

    def test_create_raises_not_implemented(self, presenter):
        """createが未実装エラーを発生させることを確認"""
        with pytest.raises(
            NotImplementedError, match="政党の作成はサポートされていません"
        ):
            presenter.create()

    def test_delete_raises_not_implemented(self, presenter):
        """deleteが未実装エラーを発生させることを確認"""
        with pytest.raises(
            NotImplementedError, match="政党の削除はサポートされていません"
        ):
            presenter.delete()

    def test_read_success(self, presenter):
        """政党を読み込めることを確認"""
        # Arrange
        mock_party = PoliticalParty(id=1, name="自民党")
        presenter.repository = MagicMock()
        presenter.repository.get_by_id = MagicMock(return_value=mock_party)

        # Act
        result = presenter.read(party_id=1)

        # Assert
        assert result.id == 1
        assert result.name == "自民党"

    def test_read_without_party_id(self, presenter):
        """party_idなしでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="party_id is required"):
            presenter.read()

    def test_read_not_found(self, presenter):
        """政党が見つからない場合のエラーを確認"""
        # Arrange
        presenter.repository = MagicMock()
        presenter.repository.get_by_id = MagicMock(return_value=None)

        # Act & Assert
        with pytest.raises(ValueError, match="見つかりません"):
            presenter.read(party_id=999)

    async def test_update_success(self, presenter, mock_use_case):
        """URL更新が成功することを確認"""
        # Arrange
        mock_use_case.update_party_url.return_value = UpdatePoliticalPartyUrlOutputDto(
            success=True, message="更新成功"
        )

        # Act
        result = await presenter._update_async(
            party_id=1, members_list_url="https://example.com/new"
        )

        # Assert
        assert result.success is True
        mock_use_case.update_party_url.assert_called_once()

    async def test_update_without_party_id(self, presenter):
        """party_idなしで更新するとエラーが発生することを確認"""
        with pytest.raises(ValueError, match="party_id is required"):
            await presenter._update_async(members_list_url="https://example.com")


class TestList:
    """listメソッドのテスト"""

    def test_list_returns_parties(
        self, presenter, mock_use_case, sample_parties, sample_statistics
    ):
        """政党リストを取得できることを確認"""
        # Arrange
        mock_use_case.list_parties.return_value = PoliticalPartyListOutputDto(
            parties=sample_parties, statistics=sample_statistics
        )
        presenter._run_async = MagicMock(
            return_value=PoliticalPartyListOutputDto(
                parties=sample_parties, statistics=sample_statistics
            )
        )

        # Act
        result = presenter.list()

        # Assert
        assert len(result) == 2


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト"""

    def test_generate_seed_file_success(self, presenter, mock_use_case):
        """シードファイル生成が成功することを確認"""
        # Arrange
        mock_use_case.generate_seed_file.return_value = GenerateSeedFileOutputDto(
            success=True,
            message="シードファイルを生成しました",
            content="INSERT INTO...",
            file_path="/tmp/seed.sql",
        )
        presenter._run_async = MagicMock(
            return_value=GenerateSeedFileOutputDto(
                success=True,
                message="シードファイルを生成しました",
                content="INSERT INTO...",
                file_path="/tmp/seed.sql",
            )
        )

        # Act
        result = presenter.generate_seed_file()

        # Assert
        assert result.success is True
        assert result.file_path == "/tmp/seed.sql"


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter, sample_parties):
        """政党リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter.to_dataframe(sample_parties)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "政党名" in df.columns
        assert "議員一覧URL" in df.columns
        assert df.iloc[0]["政党名"] == "自民党"
        assert df.iloc[1]["議員一覧URL"] == "未設定"

    def test_to_dataframe_empty(self, presenter):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([])

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert "ID" in df.columns


class TestFormState:
    """フォーム状態管理のテスト"""

    def test_set_editing_mode(self, presenter):
        """編集モードを設定できることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter._save_form_state = MagicMock()

        # Act
        presenter.set_editing_mode(party_id=1)

        # Assert
        presenter.form_state.set_editing.assert_called_once_with(1)
        presenter._save_form_state.assert_called_once()

    def test_cancel_editing(self, presenter):
        """編集モードをキャンセルできることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter._save_form_state = MagicMock()

        # Act
        presenter.cancel_editing()

        # Assert
        presenter.form_state.reset.assert_called_once()
        presenter._save_form_state.assert_called_once()

    def test_is_editing_true(self, presenter):
        """編集中かどうかを正しく判定できることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter.form_state.is_editing = True
        presenter.form_state.current_id = 1

        # Act & Assert
        assert presenter.is_editing(party_id=1) is True

    def test_is_editing_false(self, presenter):
        """編集中でない場合を正しく判定できることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter.form_state.is_editing = False
        presenter.form_state.current_id = None

        # Act & Assert
        assert presenter.is_editing(party_id=1) is False


class TestGetStatisticsSummary:
    """get_statistics_summaryメソッドのテスト"""

    def test_get_statistics_summary(self, presenter, sample_statistics):
        """統計サマリーを取得できることを確認"""
        # Act
        summary = presenter.get_statistics_summary(sample_statistics)

        # Assert
        assert "全政党数" in summary
        assert summary["全政党数"] == "2"
        assert "URL設定済み" in summary
        assert "50.0%" in summary["URL設定済み"]
        assert "URL未設定" in summary
