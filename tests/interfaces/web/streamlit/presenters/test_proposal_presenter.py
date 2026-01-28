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


# ========== Submitter Methods Tests (Issue #1023) ==========


class TestSetSubmitter:
    """set_submitterメソッドのテスト"""

    async def test_set_submitter_success(self, presenter):
        """提出者を設定できることを確認"""
        from datetime import UTC, datetime

        from src.application.dtos.proposal_submitter_dto import ProposalSubmitterDTO
        from src.application.usecases.manage_proposal_submitter_usecase import (
            SetSubmitterOutputDTO,
        )
        from src.domain.value_objects.submitter_type import SubmitterType

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        expected_dto = ProposalSubmitterDTO(
            id=1,
            proposal_id=1,
            submitter_type="politician",
            politician_id=10,
            politician_name="山田太郎",
            parliamentary_group_id=None,
            parliamentary_group_name=None,
            raw_name="山田太郎",
            is_representative=True,
            display_order=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_submitter_usecase.set_submitter.return_value = SetSubmitterOutputDTO(
            success=True,
            message="提出者情報を設定しました",
            submitter=expected_dto,
        )

        # Act
        result = await presenter._set_submitter_async(
            proposal_id=1,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=10,
        )

        # Assert
        assert result.success is True
        assert result.submitter is not None
        mock_submitter_usecase.set_submitter.assert_called_once()

    async def test_set_submitter_failure(self, presenter):
        """提出者設定の失敗を確認"""
        from src.application.usecases.manage_proposal_submitter_usecase import (
            SetSubmitterOutputDTO,
        )
        from src.domain.value_objects.submitter_type import SubmitterType

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        mock_submitter_usecase.set_submitter.return_value = SetSubmitterOutputDTO(
            success=False,
            message="議案ID 999 が見つかりません",
        )

        # Act
        result = await presenter._set_submitter_async(
            proposal_id=999,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=10,
        )

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message


class TestClearSubmitter:
    """clear_submitterメソッドのテスト"""

    async def test_clear_submitter_success(self, presenter):
        """提出者クリアが成功することを確認"""
        from src.application.usecases.manage_proposal_submitter_usecase import (
            ClearSubmitterOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        mock_submitter_usecase.clear_submitter.return_value = ClearSubmitterOutputDTO(
            success=True,
            message="提出者情報をクリアしました",
            deleted_count=1,
        )

        # Act
        result = await presenter._clear_submitter_async(proposal_id=1)

        # Assert
        assert result.success is True
        assert result.deleted_count == 1
        mock_submitter_usecase.clear_submitter.assert_called_once_with(1)

    async def test_clear_submitter_no_data(self, presenter):
        """クリアするデータがない場合を確認"""
        from src.application.usecases.manage_proposal_submitter_usecase import (
            ClearSubmitterOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        mock_submitter_usecase.clear_submitter.return_value = ClearSubmitterOutputDTO(
            success=True,
            message="クリアする提出者情報がありませんでした",
            deleted_count=0,
        )

        # Act
        result = await presenter._clear_submitter_async(proposal_id=1)

        # Assert
        assert result.success is True
        assert result.deleted_count == 0


class TestGetSubmitterCandidates:
    """get_submitter_candidatesメソッドのテスト"""

    async def test_get_submitter_candidates_success(self, presenter):
        """提出者候補を取得できることを確認"""
        from src.application.dtos.submitter_candidates_dto import (
            ParliamentaryGroupCandidateDTO,
            PoliticianCandidateDTO,
            SubmitterCandidatesDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        expected_candidates = SubmitterCandidatesDTO(
            conference_id=1,
            politicians=[
                PoliticianCandidateDTO(id=1, name="山田太郎"),
                PoliticianCandidateDTO(id=2, name="佐藤花子"),
            ],
            parliamentary_groups=[
                ParliamentaryGroupCandidateDTO(id=1, name="自民党"),
                ParliamentaryGroupCandidateDTO(id=2, name="公明党"),
            ],
        )
        mock_submitter_usecase.get_submitter_candidates.return_value = (
            expected_candidates
        )

        # Act
        result = await presenter._get_submitter_candidates_async(conference_id=1)

        # Assert
        assert result.conference_id == 1
        assert len(result.politicians) == 2
        assert len(result.parliamentary_groups) == 2
        mock_submitter_usecase.get_submitter_candidates.assert_called_once_with(1)


class TestGetConferenceIdForProposal:
    """get_conference_id_for_proposalメソッドのテスト"""

    async def test_get_conference_id_success(self, presenter):
        """議案から会議体IDを取得できることを確認"""
        from src.domain.entities.meeting import Meeting
        from src.domain.entities.proposal import Proposal

        # Arrange
        mock_proposal_repo = AsyncMock()
        mock_meeting_repo = AsyncMock()
        presenter.proposal_repository = mock_proposal_repo
        presenter.meeting_repository = mock_meeting_repo

        mock_proposal_repo.get_by_id.return_value = Proposal(
            id=1,
            title="テスト議案",
            meeting_id=100,
        )
        mock_meeting_repo.get_by_id.return_value = Meeting(
            id=100,
            name="テスト会議",
            conference_id=10,
        )

        # Act
        result = await presenter._get_conference_id_for_proposal_async(proposal_id=1)

        # Assert
        assert result == 10

    async def test_get_conference_id_proposal_not_found(self, presenter):
        """議案が見つからない場合を確認"""
        # Arrange
        mock_proposal_repo = AsyncMock()
        presenter.proposal_repository = mock_proposal_repo

        mock_proposal_repo.get_by_id.return_value = None

        # Act
        result = await presenter._get_conference_id_for_proposal_async(proposal_id=999)

        # Assert
        assert result is None

    async def test_get_conference_id_no_meeting_id(self, presenter):
        """議案にmeeting_idがない場合を確認"""
        from src.domain.entities.proposal import Proposal

        # Arrange
        mock_proposal_repo = AsyncMock()
        presenter.proposal_repository = mock_proposal_repo

        mock_proposal_repo.get_by_id.return_value = Proposal(
            id=1,
            title="テスト議案",
            meeting_id=None,  # meeting_idがない
        )

        # Act
        result = await presenter._get_conference_id_for_proposal_async(proposal_id=1)

        # Assert
        assert result is None


class TestUpdateSubmitters:
    """update_submittersメソッドのテスト"""

    async def test_update_submitters_with_politicians(self, presenter):
        """議員提出者を設定できることを確認"""
        from datetime import UTC, datetime

        from src.application.dtos.proposal_submitter_dto import ProposalSubmitterDTO
        from src.application.usecases.manage_proposal_submitter_usecase import (
            UpdateSubmittersOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        expected_dtos = [
            ProposalSubmitterDTO(
                id=1,
                proposal_id=1,
                submitter_type="politician",
                politician_id=10,
                politician_name="山田太郎",
                parliamentary_group_id=None,
                parliamentary_group_name=None,
                raw_name=None,
                is_representative=True,
                display_order=0,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
            ProposalSubmitterDTO(
                id=2,
                proposal_id=1,
                submitter_type="politician",
                politician_id=11,
                politician_name="佐藤花子",
                parliamentary_group_id=None,
                parliamentary_group_name=None,
                raw_name=None,
                is_representative=False,
                display_order=1,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            ),
        ]
        mock_submitter_usecase.update_submitters.return_value = (
            UpdateSubmittersOutputDTO(
                success=True,
                message="2件の提出者を登録しました",
                submitters=expected_dtos,
            )
        )

        # Act
        result = await presenter._update_submitters_async(
            proposal_id=1,
            politician_ids=[10, 11],
        )

        # Assert
        assert result.success is True
        assert result.submitters is not None
        assert len(result.submitters) == 2
        mock_submitter_usecase.update_submitters.assert_called_once()

    async def test_update_submitters_with_parliamentary_group(self, presenter):
        """会派提出者を設定できることを確認"""
        from datetime import UTC, datetime

        from src.application.dtos.proposal_submitter_dto import ProposalSubmitterDTO
        from src.application.usecases.manage_proposal_submitter_usecase import (
            UpdateSubmittersOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        expected_dto = ProposalSubmitterDTO(
            id=1,
            proposal_id=1,
            submitter_type="parliamentary_group",
            politician_id=None,
            politician_name=None,
            parliamentary_group_id=5,
            parliamentary_group_name="自民党",
            raw_name=None,
            is_representative=True,
            display_order=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_submitter_usecase.update_submitters.return_value = (
            UpdateSubmittersOutputDTO(
                success=True,
                message="1件の提出者を登録しました",
                submitters=[expected_dto],
            )
        )

        # Act
        result = await presenter._update_submitters_async(
            proposal_id=1,
            parliamentary_group_id=5,
        )

        # Assert
        assert result.success is True
        assert result.submitters is not None
        assert len(result.submitters) == 1
        assert result.submitters[0].parliamentary_group_id == 5

    async def test_update_submitters_with_other_type(self, presenter):
        """市長・委員会等の提出者を設定できることを確認"""
        from datetime import UTC, datetime

        from src.application.dtos.proposal_submitter_dto import ProposalSubmitterDTO
        from src.application.usecases.manage_proposal_submitter_usecase import (
            UpdateSubmittersOutputDTO,
        )
        from src.domain.value_objects.submitter_type import SubmitterType

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        expected_dto = ProposalSubmitterDTO(
            id=1,
            proposal_id=1,
            submitter_type="mayor",
            politician_id=None,
            politician_name=None,
            parliamentary_group_id=None,
            parliamentary_group_name=None,
            raw_name="田中市長",
            is_representative=True,
            display_order=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_submitter_usecase.update_submitters.return_value = (
            UpdateSubmittersOutputDTO(
                success=True,
                message="1件の提出者を登録しました",
                submitters=[expected_dto],
            )
        )

        # Act
        result = await presenter._update_submitters_async(
            proposal_id=1,
            other_submitter=(SubmitterType.MAYOR, "田中市長"),
        )

        # Assert
        assert result.success is True
        assert result.submitters is not None
        assert len(result.submitters) == 1
        assert result.submitters[0].raw_name == "田中市長"

    async def test_update_submitters_clear(self, presenter):
        """提出者をクリアできることを確認"""
        from src.application.usecases.manage_proposal_submitter_usecase import (
            UpdateSubmittersOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        mock_submitter_usecase.update_submitters.return_value = (
            UpdateSubmittersOutputDTO(
                success=True,
                message="提出者をクリアしました",
                submitters=[],
            )
        )

        # Act
        result = await presenter._update_submitters_async(
            proposal_id=1,
            # 何も指定しない
        )

        # Assert
        assert result.success is True
        assert result.submitters == []

    async def test_update_submitters_failure(self, presenter):
        """提出者更新の失敗を確認"""
        from src.application.usecases.manage_proposal_submitter_usecase import (
            UpdateSubmittersOutputDTO,
        )

        # Arrange
        mock_submitter_usecase = AsyncMock()
        presenter.manage_submitter_usecase = mock_submitter_usecase

        mock_submitter_usecase.update_submitters.return_value = (
            UpdateSubmittersOutputDTO(
                success=False,
                message="議案ID 999 が見つかりません",
            )
        )

        # Act
        result = await presenter._update_submitters_async(
            proposal_id=999,
            politician_ids=[10],
        )

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message


# ========== Issue #1017: 会議体名・開催主体名表示機能のテスト ==========


class TestLoadGoverningBodies:
    """load_governing_bodiesメソッドのテスト"""

    async def test_load_governing_bodies_success(self, presenter):
        """開催主体一覧を取得できることを確認"""
        from src.domain.entities.governing_body import GoverningBody

        # Arrange
        mock_governing_body_repo = AsyncMock()
        presenter.governing_body_repository = mock_governing_body_repo

        mock_governing_body_repo.get_all.return_value = [
            GoverningBody(id=1, name="東京都"),
            GoverningBody(id=2, name="横浜市"),
        ]

        # Act
        result = await presenter._load_governing_bodies_async()

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "東京都"
        assert result[1]["id"] == 2
        assert result[1]["name"] == "横浜市"
        mock_governing_body_repo.get_all.assert_called_once()

    async def test_load_governing_bodies_empty(self, presenter):
        """開催主体が空の場合を確認"""
        # Arrange
        mock_governing_body_repo = AsyncMock()
        presenter.governing_body_repository = mock_governing_body_repo

        mock_governing_body_repo.get_all.return_value = []

        # Act
        result = await presenter._load_governing_bodies_async()

        # Assert
        assert len(result) == 0


class TestBuildProposalRelatedDataMap:
    """build_proposal_related_data_mapメソッドのテスト"""

    async def test_build_related_data_map_with_conference_id(self, presenter):
        """conference_idを持つ議案の関連データマップを構築できることを確認"""
        from src.domain.entities.conference import Conference
        from src.domain.entities.governing_body import GoverningBody
        from src.domain.entities.proposal import Proposal

        # Arrange
        mock_conference_repo = AsyncMock()
        mock_governing_body_repo = AsyncMock()
        mock_meeting_repo = AsyncMock()
        presenter.conference_repository = mock_conference_repo
        presenter.governing_body_repository = mock_governing_body_repo
        presenter.meeting_repository = mock_meeting_repo

        proposals = [
            Proposal(id=1, title="議案A", conference_id=10),
            Proposal(id=2, title="議案B", conference_id=10),
        ]

        mock_conference_repo.get_by_id.return_value = Conference(
            id=10, name="東京都議会本会議", governing_body_id=100
        )
        mock_governing_body_repo.get_by_id.return_value = GoverningBody(
            id=100, name="東京都"
        )

        # Act
        result = await presenter._build_proposal_related_data_map_async(proposals)

        # Assert
        assert 1 in result
        assert result[1]["conference_name"] == "東京都議会本会議"
        assert result[1]["governing_body_name"] == "東京都"
        assert 2 in result
        assert result[2]["conference_name"] == "東京都議会本会議"
        assert result[2]["governing_body_name"] == "東京都"

    async def test_build_related_data_map_with_meeting_id(self, presenter):
        """meeting_idを持つ議案の関連データマップを構築できることを確認"""
        from src.domain.entities.conference import Conference
        from src.domain.entities.governing_body import GoverningBody
        from src.domain.entities.meeting import Meeting
        from src.domain.entities.proposal import Proposal

        # Arrange
        mock_conference_repo = AsyncMock()
        mock_governing_body_repo = AsyncMock()
        mock_meeting_repo = AsyncMock()
        presenter.conference_repository = mock_conference_repo
        presenter.governing_body_repository = mock_governing_body_repo
        presenter.meeting_repository = mock_meeting_repo

        proposals = [
            Proposal(id=1, title="議案A", meeting_id=200),
        ]

        mock_meeting_repo.get_by_id.return_value = Meeting(
            id=200, name="第1回定例会", conference_id=10
        )
        mock_conference_repo.get_by_id.return_value = Conference(
            id=10, name="横浜市議会", governing_body_id=101
        )
        mock_governing_body_repo.get_by_id.return_value = GoverningBody(
            id=101, name="横浜市"
        )

        # Act
        result = await presenter._build_proposal_related_data_map_async(proposals)

        # Assert
        assert 1 in result
        assert result[1]["conference_name"] == "横浜市議会"
        assert result[1]["governing_body_name"] == "横浜市"

    async def test_build_related_data_map_no_related_data(self, presenter):
        """関連データがない議案の場合を確認"""
        from src.domain.entities.proposal import Proposal

        # Arrange
        mock_conference_repo = AsyncMock()
        mock_governing_body_repo = AsyncMock()
        mock_meeting_repo = AsyncMock()
        presenter.conference_repository = mock_conference_repo
        presenter.governing_body_repository = mock_governing_body_repo
        presenter.meeting_repository = mock_meeting_repo

        proposals = [
            Proposal(id=1, title="議案A"),  # conference_id, meeting_idなし
        ]

        # Act
        result = await presenter._build_proposal_related_data_map_async(proposals)

        # Assert
        assert 1 in result
        assert result[1]["conference_name"] is None
        assert result[1]["governing_body_name"] is None

    async def test_build_related_data_map_empty_proposals(self, presenter):
        """空の議案リストの場合を確認"""
        # Act
        result = await presenter._build_proposal_related_data_map_async([])

        # Assert
        assert result == {}
