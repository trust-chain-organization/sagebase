"""会派/政治家賛否管理UseCaseのテスト.

Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
"""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.proposal_parliamentary_group_judge_dto import (
    ProposalParliamentaryGroupJudgeListOutputDTO,
)
from src.application.usecases.manage_parliamentary_group_judges_usecase import (
    CreateJudgeOutputDTO,
    DeleteJudgeOutputDTO,
    ManageParliamentaryGroupJudgesUseCase,
    UpdateJudgeOutputDTO,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.value_objects.judge_type import JudgeType


class TestManageParliamentaryGroupJudgesUseCase:
    """会派/政治家賛否管理UseCaseのテストケース."""

    @pytest.fixture
    def mock_judge_repository(self):
        """モックの賛否リポジトリを作成する."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_parliamentary_group_repository(self):
        """モックの会派リポジトリを作成する."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repository(self):
        """モックの政治家リポジトリを作成する."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(
        self,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        mock_politician_repository,
    ):
        """UseCaseインスタンスを作成する."""
        return ManageParliamentaryGroupJudgesUseCase(
            judge_repository=mock_judge_repository,
            parliamentary_group_repository=mock_parliamentary_group_repository,
            politician_repository=mock_politician_repository,
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
    def sample_parliamentary_group_2(self):
        """サンプルの会派エンティティを作成する（2つ目）."""
        return ParliamentaryGroup(
            id=2,
            name="公明党会派",
            conference_id=100,
        )

    @pytest.fixture
    def sample_politician(self):
        """サンプルの政治家エンティティを作成する."""
        return Politician(
            id=100,
            name="山田太郎",
            prefecture="東京都",
            district="渋谷区",
        )

    @pytest.fixture
    def sample_politician_2(self):
        """サンプルの政治家エンティティを作成する（2人目）."""
        return Politician(
            id=101,
            name="田中花子",
            prefecture="東京都",
            district="新宿区",
        )

    @pytest.fixture
    def sample_judge(self):
        """サンプルの会派賛否エンティティを作成する."""
        return ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[1],
            member_count=5,
            note="全員一致",
        )

    @pytest.fixture
    def sample_judge_multiple_groups(self):
        """サンプルの会派賛否エンティティ（複数会派）を作成する."""
        return ProposalParliamentaryGroupJudge(
            id=3,
            proposal_id=10,
            judgment="賛成",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[1, 2],
            member_count=10,
            note="統一会派",
        )

    @pytest.fixture
    def sample_politician_judge(self):
        """サンプルの政治家賛否エンティティを作成する."""
        return ProposalParliamentaryGroupJudge(
            id=2,
            proposal_id=10,
            judgment="反対",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100],
            note="個人的意見",
        )

    @pytest.fixture
    def sample_politician_judge_multiple(self):
        """サンプルの政治家賛否エンティティ（複数政治家）を作成する."""
        return ProposalParliamentaryGroupJudge(
            id=4,
            proposal_id=10,
            judgment="反対",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100, 101],
            note="連名で反対",
        )

    # ==========================================================================
    # create() のテスト - 会派単位
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_judge,
    ):
        """正常系: 会派賛否の新規登録が成功する."""
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_judge_repository.get_by_proposal_and_groups.return_value = None
        mock_judge_repository.create.return_value = sample_judge

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[1],
            member_count=5,
            note="全員一致",
        )

        assert isinstance(result, CreateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.judgment == "賛成"
        assert result.judge.judge_type == "parliamentary_group"
        mock_judge_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_multiple_ids_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_parliamentary_group_2,
        sample_judge_multiple_groups,
    ):
        """正常系: 複数会派の賛否登録が成功する."""

        def get_by_id_side_effect(pg_id):
            if pg_id == 1:
                return sample_parliamentary_group
            elif pg_id == 2:
                return sample_parliamentary_group_2
            return None

        mock_parliamentary_group_repository.get_by_id.side_effect = (
            get_by_id_side_effect
        )
        mock_judge_repository.get_by_proposal_and_groups.return_value = None
        mock_judge_repository.create.return_value = sample_judge_multiple_groups

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[1, 2],
            member_count=10,
            note="統一会派",
        )

        assert isinstance(result, CreateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.parliamentary_group_ids == [1, 2]
        mock_judge_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_duplicate_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_judge,
    ):
        """異常系: 同一議案・同一会派の重複登録はエラー."""
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_judge_repository.get_by_proposal_and_groups.return_value = sample_judge

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[1],
        )

        assert result.success is False
        assert "既に登録されています" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_missing_id_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 会派単位で会派IDが未指定はエラー."""
        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="parliamentary_group",
        )

        assert result.success is False
        assert "会派IDが必要" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 会派が存在しない場合はエラー."""
        mock_parliamentary_group_repository.get_by_id.return_value = None

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[999],
        )

        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.create.assert_not_called()

    # ==========================================================================
    # create() のテスト - 政治家単位
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_politician_success(
        self,
        use_case,
        mock_judge_repository,
        mock_politician_repository,
        sample_politician,
        sample_politician_judge,
    ):
        """正常系: 政治家賛否の新規登録が成功する."""
        mock_politician_repository.get_by_id.return_value = sample_politician
        mock_judge_repository.get_by_proposal_and_politicians.return_value = None
        mock_judge_repository.create.return_value = sample_politician_judge

        result = await use_case.create(
            proposal_id=10,
            judgment="反対",
            judge_type="politician",
            politician_ids=[100],
            note="個人的意見",
        )

        assert isinstance(result, CreateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.judgment == "反対"
        assert result.judge.judge_type == "politician"
        mock_judge_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_politician_multiple_ids_success(
        self,
        use_case,
        mock_judge_repository,
        mock_politician_repository,
        sample_politician,
        sample_politician_2,
        sample_politician_judge_multiple,
    ):
        """正常系: 複数政治家の賛否登録が成功する."""

        def get_by_id_side_effect(pol_id):
            if pol_id == 100:
                return sample_politician
            elif pol_id == 101:
                return sample_politician_2
            return None

        mock_politician_repository.get_by_id.side_effect = get_by_id_side_effect
        mock_judge_repository.get_by_proposal_and_politicians.return_value = None
        mock_judge_repository.create.return_value = sample_politician_judge_multiple

        result = await use_case.create(
            proposal_id=10,
            judgment="反対",
            judge_type="politician",
            politician_ids=[100, 101],
            note="連名で反対",
        )

        assert isinstance(result, CreateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.politician_ids == [100, 101]
        mock_judge_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_politician_duplicate_error(
        self,
        use_case,
        mock_judge_repository,
        mock_politician_repository,
        sample_politician,
        sample_politician_judge,
    ):
        """異常系: 同一議案・同一政治家の重複登録はエラー."""
        mock_politician_repository.get_by_id.return_value = sample_politician
        mock_judge_repository.get_by_proposal_and_politicians.return_value = (
            sample_politician_judge
        )

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="politician",
            politician_ids=[100],
        )

        assert result.success is False
        assert "既に登録されています" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_politician_missing_id_error(
        self,
        use_case,
        mock_judge_repository,
        mock_politician_repository,
    ):
        """異常系: 政治家単位で政治家IDが未指定はエラー."""
        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="politician",
        )

        assert result.success is False
        assert "政治家IDが必要" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_politician_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_politician_repository,
    ):
        """異常系: 政治家が存在しない場合はエラー."""
        mock_politician_repository.get_by_id.return_value = None

        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="politician",
            politician_ids=[999],
        )

        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.create.assert_not_called()

    # ==========================================================================
    # create() のテスト - 共通エラー
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_invalid_judgment_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 無効なjudgment値はエラー."""
        result = await use_case.create(
            proposal_id=10,
            judgment="無効な値",
            judge_type="parliamentary_group",
            parliamentary_group_ids=[1],
        )

        assert result.success is False
        assert "無効なjudgment値です" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_invalid_judge_type_error(
        self,
        use_case,
        mock_judge_repository,
    ):
        """異常系: 無効なjudge_type値はエラー."""
        result = await use_case.create(
            proposal_id=10,
            judgment="賛成",
            judge_type="invalid_type",
            parliamentary_group_ids=[1],
        )

        assert result.success is False
        assert "judge_type" in result.message
        mock_judge_repository.create.assert_not_called()

    # ==========================================================================
    # update() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_judge,
    ):
        """正常系: 賛否の更新が成功する."""
        mock_judge_repository.get_by_id.return_value = sample_judge
        updated_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            judgment="反対",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[1],
            member_count=3,
            note="賛否が分かれた",
        )
        mock_judge_repository.update.return_value = updated_judge
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )

        result = await use_case.update(
            judge_id=1,
            judgment="反対",
            member_count=3,
            note="賛否が分かれた",
        )

        assert isinstance(result, UpdateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.judgment == "反対"
        mock_judge_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 対象が存在しない場合はエラー."""
        mock_judge_repository.get_by_id.return_value = None

        result = await use_case.update(
            judge_id=999,
            judgment="反対",
        )

        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_invalid_judgment_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """異常系: 無効なjudgment値はエラー."""
        mock_judge_repository.get_by_id.return_value = sample_judge

        result = await use_case.update(
            judge_id=1,
            judgment="無効な値",
        )

        assert result.success is False
        assert "無効なjudgment値です" in result.message
        mock_judge_repository.update.assert_not_called()

    # ==========================================================================
    # delete() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """正常系: 賛否の削除が成功する."""
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.delete.return_value = True

        result = await use_case.delete(judge_id=1)

        assert isinstance(result, DeleteJudgeOutputDTO)
        assert result.success is True
        assert "削除しました" in result.message
        mock_judge_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 対象が存在しない場合はエラー."""
        mock_judge_repository.get_by_id.return_value = None

        result = await use_case.delete(judge_id=999)

        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_failed(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """異常系: 削除に失敗した場合はエラー."""
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.delete.return_value = False

        result = await use_case.delete(judge_id=1)

        assert result.success is False
        assert "削除に失敗しました" in result.message

    # ==========================================================================
    # list_by_proposal() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_list_by_proposal_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_parliamentary_group_2,
    ):
        """正常系: 議案に紐づく賛否一覧を取得する."""
        judges = [
            ProposalParliamentaryGroupJudge(
                id=1,
                proposal_id=10,
                judgment="賛成",
                parliamentary_group_ids=[1],
                member_count=5,
            ),
            ProposalParliamentaryGroupJudge(
                id=2,
                proposal_id=10,
                judgment="反対",
                parliamentary_group_ids=[2],
                member_count=3,
            ),
        ]
        mock_judge_repository.get_by_proposal.return_value = judges

        def get_by_id_side_effect(pg_id):
            if pg_id == 1:
                return sample_parliamentary_group
            elif pg_id == 2:
                return sample_parliamentary_group_2
            return None

        mock_parliamentary_group_repository.get_by_id.side_effect = (
            get_by_id_side_effect
        )

        result = await use_case.list_by_proposal(proposal_id=10)

        assert isinstance(result, ProposalParliamentaryGroupJudgeListOutputDTO)
        assert result.total_count == 2
        assert len(result.judges) == 2
        mock_judge_repository.get_by_proposal.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_by_proposal_with_multiple_ids(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_parliamentary_group_2,
    ):
        """正常系: 複数会派を含む賛否一覧を取得する."""
        judges = [
            ProposalParliamentaryGroupJudge(
                id=1,
                proposal_id=10,
                judgment="賛成",
                parliamentary_group_ids=[1, 2],  # 複数会派
                member_count=10,
            ),
        ]
        mock_judge_repository.get_by_proposal.return_value = judges

        def get_by_id_side_effect(pg_id):
            if pg_id == 1:
                return sample_parliamentary_group
            elif pg_id == 2:
                return sample_parliamentary_group_2
            return None

        mock_parliamentary_group_repository.get_by_id.side_effect = (
            get_by_id_side_effect
        )

        result = await use_case.list_by_proposal(proposal_id=10)

        assert isinstance(result, ProposalParliamentaryGroupJudgeListOutputDTO)
        assert result.total_count == 1
        assert len(result.judges) == 1
        # 複数の会派名が取得されていることを確認
        assert len(result.judges[0].parliamentary_group_names) == 2

    @pytest.mark.asyncio
    async def test_list_by_proposal_empty(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """正常系: 賛否が存在しない場合は空のリストを返す."""
        mock_judge_repository.get_by_proposal.return_value = []

        result = await use_case.list_by_proposal(proposal_id=10)

        assert result.total_count == 0
        assert len(result.judges) == 0

    @pytest.mark.asyncio
    async def test_list_by_proposal_repository_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: リポジトリエラー時は例外を投げる."""
        mock_judge_repository.get_by_proposal.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await use_case.list_by_proposal(proposal_id=10)
