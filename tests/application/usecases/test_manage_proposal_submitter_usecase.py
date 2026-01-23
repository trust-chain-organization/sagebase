"""議案提出者管理UseCaseのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.submitter_candidates_dto import (
    SubmitterCandidatesDTO,
)
from src.application.usecases.manage_proposal_submitter_usecase import (
    ClearSubmitterOutputDTO,
    ManageProposalSubmitterUseCase,
    SetSubmitterOutputDTO,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType


class TestManageProposalSubmitterUseCase:
    """議案提出者管理UseCaseのテストケース."""

    @pytest.fixture
    def mock_proposal_repository(self):
        """モックの議案リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def mock_proposal_submitter_repository(self):
        """モックの提出者リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def mock_meeting_repository(self):
        """モックの会議リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def mock_politician_affiliation_repository(self):
        """モックの政治家所属リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def mock_parliamentary_group_repository(self):
        """モックの会派リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def mock_politician_repository(self):
        """モックの政治家リポジトリを作成する."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        mock_meeting_repository,
        mock_politician_affiliation_repository,
        mock_parliamentary_group_repository,
        mock_politician_repository,
    ):
        """UseCaseインスタンスを作成する."""
        return ManageProposalSubmitterUseCase(
            proposal_repository=mock_proposal_repository,
            proposal_submitter_repository=mock_proposal_submitter_repository,
            meeting_repository=mock_meeting_repository,
            politician_affiliation_repository=mock_politician_affiliation_repository,
            parliamentary_group_repository=mock_parliamentary_group_repository,
            politician_repository=mock_politician_repository,
        )

    @pytest.fixture
    def sample_proposal(self):
        """サンプルの議案エンティティを作成する."""
        return Proposal(
            id=1,
            content="議案第1号 予算案",
            meeting_id=10,
        )

    @pytest.fixture
    def sample_politician(self):
        """サンプルの政治家エンティティを作成する."""
        return Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            district="渋谷区",
        )

    @pytest.fixture
    def sample_parliamentary_group(self):
        """サンプルの会派エンティティを作成する."""
        return ParliamentaryGroup(
            id=1,
            name="自民党会派",
            conference_id=100,
        )

    @pytest.fixture
    def sample_submitter(self):
        """サンプルの提出者エンティティを作成する."""
        return ProposalSubmitter(
            id=1,
            proposal_id=1,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=1,
            raw_name="山田太郎",
            is_representative=True,
            display_order=0,
        )

    # ==========================================================================
    # set_submitter() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_set_submitter_politician_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        mock_politician_repository,
        sample_proposal,
        sample_politician,
        sample_submitter,
    ):
        """正常系: 議員提出の設定が成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_politician_repository.get_by_id.return_value = sample_politician
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0
        mock_proposal_submitter_repository.create.return_value = sample_submitter

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=1,
        )

        # Assert
        assert isinstance(result, SetSubmitterOutputDTO)
        assert result.success is True
        assert result.submitter is not None
        assert result.submitter.submitter_type == "politician"
        assert result.submitter.politician_id == 1
        assert "設定しました" in result.message
        mock_proposal_submitter_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_submitter_parliamentary_group_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        mock_parliamentary_group_repository,
        sample_proposal,
        sample_parliamentary_group,
    ):
        """正常系: 会派提出の設定が成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0

        created_submitter = ProposalSubmitter(
            id=2,
            proposal_id=1,
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            parliamentary_group_id=1,
            raw_name="自民党会派",
            is_representative=True,
            display_order=0,
        )
        mock_proposal_submitter_repository.create.return_value = created_submitter

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="自民党会派",
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            submitter_parliamentary_group_id=1,
        )

        # Assert
        assert result.success is True
        assert result.submitter is not None
        assert result.submitter.submitter_type == "parliamentary_group"
        assert result.submitter.parliamentary_group_id == 1

    @pytest.mark.asyncio
    async def test_set_submitter_mayor_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """正常系: 市長提出の設定が成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0

        created_submitter = ProposalSubmitter(
            id=3,
            proposal_id=1,
            submitter_type=SubmitterType.MAYOR,
            raw_name="市長",
            is_representative=True,
            display_order=0,
        )
        mock_proposal_submitter_repository.create.return_value = created_submitter

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="市長",
            submitter_type=SubmitterType.MAYOR,
        )

        # Assert
        assert result.success is True
        assert result.submitter is not None
        assert result.submitter.submitter_type == "mayor"
        assert result.submitter.politician_id is None
        assert result.submitter.parliamentary_group_id is None

    @pytest.mark.asyncio
    async def test_set_submitter_committee_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """正常系: 委員会提出の設定が成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0

        created_submitter = ProposalSubmitter(
            id=4,
            proposal_id=1,
            submitter_type=SubmitterType.COMMITTEE,
            raw_name="総務委員会",
            is_representative=True,
            display_order=0,
        )
        mock_proposal_submitter_repository.create.return_value = created_submitter

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="総務委員会",
            submitter_type=SubmitterType.COMMITTEE,
        )

        # Assert
        assert result.success is True
        assert result.submitter is not None
        assert result.submitter.submitter_type == "committee"
        assert result.submitter.politician_id is None
        assert result.submitter.parliamentary_group_id is None

    @pytest.mark.asyncio
    async def test_set_submitter_other_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """正常系: その他提出の設定が成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0

        created_submitter = ProposalSubmitter(
            id=5,
            proposal_id=1,
            submitter_type=SubmitterType.OTHER,
            raw_name="住民発議",
            is_representative=True,
            display_order=0,
        )
        mock_proposal_submitter_repository.create.return_value = created_submitter

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="住民発議",
            submitter_type=SubmitterType.OTHER,
        )

        # Assert
        assert result.success is True
        assert result.submitter is not None
        assert result.submitter.submitter_type == "other"
        assert result.submitter.politician_id is None
        assert result.submitter.parliamentary_group_id is None

    @pytest.mark.asyncio
    async def test_set_submitter_proposal_not_found(
        self,
        use_case,
        mock_proposal_repository,
    ):
        """異常系: 議案が存在しない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        # Act
        result = await use_case.set_submitter(
            proposal_id=999,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=1,
        )

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_politician_type_without_id(
        self,
        use_case,
        mock_proposal_repository,
        sample_proposal,
    ):
        """異常系: 議員提出でIDがない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=None,
        )

        # Assert
        assert result.success is False
        assert "submitter_politician_idが必須です" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_parliamentary_group_type_without_id(
        self,
        use_case,
        mock_proposal_repository,
        sample_proposal,
    ):
        """異常系: 会派提出でIDがない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="自民党会派",
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            submitter_parliamentary_group_id=None,
        )

        # Assert
        assert result.success is False
        assert "submitter_parliamentary_group_idが必須です" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_politician_type_with_group_id(
        self,
        use_case,
        mock_proposal_repository,
        sample_proposal,
    ):
        """異常系: 議員提出で会派IDが指定されている場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=1,
            submitter_parliamentary_group_id=1,
        )

        # Assert
        assert result.success is False
        assert "指定できません" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_mayor_type_with_politician_id(
        self,
        use_case,
        mock_proposal_repository,
        sample_proposal,
    ):
        """異常系: 市長提出で議員IDが指定されている場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="市長",
            submitter_type=SubmitterType.MAYOR,
            submitter_politician_id=1,
        )

        # Assert
        assert result.success is False
        assert "指定できません" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_politician_not_found(
        self,
        use_case,
        mock_proposal_repository,
        mock_politician_repository,
        sample_proposal,
    ):
        """異常系: 指定された議員が存在しない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_politician_repository.get_by_id.return_value = None

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="山田太郎",
            submitter_type=SubmitterType.POLITICIAN,
            submitter_politician_id=999,
        )

        # Assert
        assert result.success is False
        assert "議員ID 999 が見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_parliamentary_group_not_found(
        self,
        use_case,
        mock_proposal_repository,
        mock_parliamentary_group_repository,
        sample_proposal,
    ):
        """異常系: 指定された会派が存在しない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_parliamentary_group_repository.get_by_id.return_value = None

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="不明会派",
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            submitter_parliamentary_group_id=999,
        )

        # Assert
        assert result.success is False
        assert "会派ID 999 が見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_set_submitter_repository_error(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """異常系: リポジトリエラー時はエラーメッセージを返す."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await use_case.set_submitter(
            proposal_id=1,
            submitter="市長",
            submitter_type=SubmitterType.MAYOR,
        )

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    # ==========================================================================
    # clear_submitter() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_clear_submitter_success(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """正常系: 提出者クリアが成功する."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 1

        # Act
        result = await use_case.clear_submitter(proposal_id=1)

        # Assert
        assert isinstance(result, ClearSubmitterOutputDTO)
        assert result.success is True
        assert result.deleted_count == 1
        assert "クリアしました" in result.message
        mock_proposal_submitter_repository.delete_by_proposal.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_clear_submitter_no_existing(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """正常系: クリアする提出者がない場合."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.return_value = 0

        # Act
        result = await use_case.clear_submitter(proposal_id=1)

        # Assert
        assert result.success is True
        assert result.deleted_count == 0
        assert "提出者情報がありませんでした" in result.message

    @pytest.mark.asyncio
    async def test_clear_submitter_proposal_not_found(
        self,
        use_case,
        mock_proposal_repository,
    ):
        """異常系: 議案が存在しない場合はエラー."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        # Act
        result = await use_case.clear_submitter(proposal_id=999)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_clear_submitter_repository_error(
        self,
        use_case,
        mock_proposal_repository,
        mock_proposal_submitter_repository,
        sample_proposal,
    ):
        """異常系: リポジトリエラー時はエラーメッセージを返す."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = sample_proposal
        mock_proposal_submitter_repository.delete_by_proposal.side_effect = Exception(
            "Database error"
        )

        # Act
        result = await use_case.clear_submitter(proposal_id=1)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    # ==========================================================================
    # get_submitter_candidates() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_submitter_candidates_success(
        self,
        use_case,
        mock_parliamentary_group_repository,
        mock_politician_affiliation_repository,
        mock_politician_repository,
    ):
        """正常系: 候補一覧の取得が成功する."""
        # Arrange
        conference_id = 100

        # 会派データ
        parliamentary_groups = [
            ParliamentaryGroup(id=1, name="自民党会派", conference_id=conference_id),
            ParliamentaryGroup(id=2, name="公明党会派", conference_id=conference_id),
        ]
        mock_parliamentary_group_repository.get_by_conference_id.return_value = (
            parliamentary_groups
        )

        # 所属データ
        affiliations = [
            PoliticianAffiliation(
                id=1,
                politician_id=1,
                conference_id=conference_id,
                start_date=date(2020, 1, 1),
            ),
            PoliticianAffiliation(
                id=2,
                politician_id=2,
                conference_id=conference_id,
                start_date=date(2020, 1, 1),
            ),
        ]
        mock_politician_affiliation_repository.get_by_conference.return_value = (
            affiliations
        )

        # 政治家データ
        politicians = {
            1: Politician(
                id=1, name="山田太郎", prefecture="東京都", district="渋谷区"
            ),
            2: Politician(id=2, name="佐藤花子", prefecture="大阪府", district="北区"),
        }
        mock_politician_repository.get_by_id.side_effect = lambda pid: politicians.get(
            pid
        )

        # Act
        result = await use_case.get_submitter_candidates(conference_id=conference_id)

        # Assert
        assert isinstance(result, SubmitterCandidatesDTO)
        assert result.conference_id == conference_id
        assert len(result.parliamentary_groups) == 2
        assert len(result.politicians) == 2

        # 会派の検証
        group_names = [pg.name for pg in result.parliamentary_groups]
        assert "自民党会派" in group_names
        assert "公明党会派" in group_names

        # 政治家の検証
        politician_names = [p.name for p in result.politicians]
        assert "山田太郎" in politician_names
        assert "佐藤花子" in politician_names

    @pytest.mark.asyncio
    async def test_get_submitter_candidates_empty(
        self,
        use_case,
        mock_parliamentary_group_repository,
        mock_politician_affiliation_repository,
    ):
        """正常系: 候補がない場合は空のリストを返す."""
        # Arrange
        mock_parliamentary_group_repository.get_by_conference_id.return_value = []
        mock_politician_affiliation_repository.get_by_conference.return_value = []

        # Act
        result = await use_case.get_submitter_candidates(conference_id=100)

        # Assert
        assert result.conference_id == 100
        assert len(result.parliamentary_groups) == 0
        assert len(result.politicians) == 0
