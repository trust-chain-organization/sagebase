"""ProposalPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.application.usecases.manage_proposals_usecase import (
    CreateProposalOutputDto,
    DeleteProposalOutputDto,
    ManageProposalsUseCase,
    ProposalListOutputDto,
    ProposalStatistics,
    UpdateProposalOutputDto,
)
from src.domain.entities.proposal import Proposal


@pytest.fixture
def mock_use_case():
    """ManageProposalsUseCaseのモック"""
    return AsyncMock(spec=ManageProposalsUseCase)


@pytest.fixture
def sample_proposals():
    """サンプル議案リスト"""
    return [
        Proposal(
            id=1,
            title="予算案",
            detail_url="https://example.com/1",
            meeting_id=100,
        ),
        Proposal(
            id=2,
            title="条例案",
            status_url="https://example.com/status/2",
            meeting_id=100,
        ),
    ]


@pytest.fixture
def sample_statistics():
    """サンプル統計情報"""
    return ProposalStatistics(
        total=2,
        with_detail_url=1,
        with_status_url=1,
        with_votes_url=0,
    )


@pytest.fixture
def presenter(mock_use_case):
    """ProposalPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.proposal_presenter.ManageProposalsUseCase"
        ) as mock_uc_class,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session_instance.set = MagicMock()
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.proposal_presenter import (
            ProposalPresenter,
        )

        presenter = ProposalPresenter()
        presenter.manage_usecase = mock_use_case
        return presenter


class TestProposalPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.proposal_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.proposal_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.proposal_presenter.ManageProposalsUseCase"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.proposal_presenter import (
                ProposalPresenter,
            )

            presenter = ProposalPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    async def test_load_data_filtered_success(
        self, presenter, mock_use_case, sample_proposals, sample_statistics
    ):
        """議案リストをフィルタ付きで読み込めることを確認"""
        # Arrange
        mock_use_case.list_proposals.return_value = ProposalListOutputDto(
            proposals=sample_proposals, statistics=sample_statistics
        )

        # Act
        result = await presenter._load_data_filtered_async("all")

        # Assert
        assert len(result.proposals) == 2
        mock_use_case.list_proposals.assert_called_once()

    async def test_load_data_filtered_by_meeting(
        self, presenter, mock_use_case, sample_proposals, sample_statistics
    ):
        """会議IDフィルタで読み込めることを確認"""
        # Arrange
        mock_use_case.list_proposals.return_value = ProposalListOutputDto(
            proposals=[sample_proposals[0]], statistics=sample_statistics
        )

        # Act
        result = await presenter._load_data_filtered_async("by_meeting", meeting_id=100)

        # Assert
        assert len(result.proposals) == 1

    async def test_load_data_filtered_exception(self, presenter, mock_use_case):
        """例外発生時にエラーを伝播することを確認"""
        # Arrange
        mock_use_case.list_proposals.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await presenter._load_data_filtered_async("all")


class TestCreate:
    """createメソッドのテスト"""

    async def test_create_success(self, presenter, mock_use_case, sample_proposals):
        """議案の作成が成功することを確認"""
        # Arrange
        mock_use_case.create_proposal.return_value = CreateProposalOutputDto(
            success=True, message="作成成功", proposal=sample_proposals[0]
        )

        # Act
        result = await presenter._create_async(
            title="新規議案",
        )

        # Assert
        assert result.success is True
        assert result.proposal is not None

    async def test_create_failure(self, presenter, mock_use_case):
        """議案の作成が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.create_proposal.return_value = CreateProposalOutputDto(
            success=False, message="作成に失敗しました", proposal=None
        )

        # Act
        result = await presenter._create_async(title="新規議案")

        # Assert
        assert result.success is False


class TestUpdate:
    """updateメソッドのテスト"""

    async def test_update_success(self, presenter, mock_use_case):
        """議案の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_proposal.return_value = UpdateProposalOutputDto(
            success=True, message="更新成功"
        )

        # Act
        result = await presenter._update_async(proposal_id=1, title="更新された議案")

        # Assert
        assert result.success is True

    async def test_update_failure(self, presenter, mock_use_case):
        """議案の更新が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.update_proposal.return_value = UpdateProposalOutputDto(
            success=False, message="更新に失敗しました"
        )

        # Act
        result = await presenter._update_async(proposal_id=999, title="不明")

        # Assert
        assert result.success is False


class TestDelete:
    """deleteメソッドのテスト"""

    async def test_delete_success(self, presenter, mock_use_case):
        """議案の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_proposal.return_value = DeleteProposalOutputDto(
            success=True, message="削除成功"
        )

        # Act
        result = await presenter._delete_async(proposal_id=1)

        # Assert
        assert result.success is True

    async def test_delete_failure(self, presenter, mock_use_case):
        """議案の削除が失敗した場合のエラーを確認"""
        # Arrange
        mock_use_case.delete_proposal.return_value = DeleteProposalOutputDto(
            success=False, message="削除に失敗しました"
        )

        # Act
        result = await presenter._delete_async(proposal_id=1)

        # Assert
        assert result.success is False


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter, sample_proposals):
        """議案リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter.to_dataframe(sample_proposals)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "タイトル" in df.columns

    def test_to_dataframe_empty(self, presenter):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([])

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestFormState:
    """フォーム状態管理のテスト"""

    def test_set_editing_mode(self, presenter):
        """編集モードを設定できることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter._save_form_state = MagicMock()

        # Act
        presenter.set_editing_mode(proposal_id=1)

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
        assert presenter.is_editing(proposal_id=1) is True

    def test_is_editing_false(self, presenter):
        """編集中でない場合を正しく判定できることを確認"""
        # Arrange
        presenter.form_state = MagicMock()
        presenter.form_state.is_editing = False
        presenter.form_state.current_id = None

        # Act & Assert
        assert presenter.is_editing(proposal_id=1) is False
