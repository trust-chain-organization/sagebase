"""会派賛否管理UseCaseのテスト."""

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
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)


class TestManageParliamentaryGroupJudgesUseCase:
    """会派賛否管理UseCaseのテストケース."""

    @pytest.fixture
    def mock_judge_repository(self):
        """モックの会派賛否リポジトリを作成する."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_parliamentary_group_repository(self):
        """モックの会派リポジトリを作成する."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_judge_repository, mock_parliamentary_group_repository):
        """UseCaseインスタンスを作成する."""
        return ManageParliamentaryGroupJudgesUseCase(
            judge_repository=mock_judge_repository,
            parliamentary_group_repository=mock_parliamentary_group_repository,
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
    def sample_judge(self):
        """サンプルの会派賛否エンティティを作成する."""
        return ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="賛成",
            member_count=5,
            note="全員一致",
        )

    # ==========================================================================
    # create() のテスト
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_judge,
    ):
        """正常系: 会派賛否の新規登録が成功する."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_judge_repository.get_by_proposal_and_group.return_value = None
        mock_judge_repository.create.return_value = sample_judge

        # Act
        result = await use_case.create(
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="賛成",
            member_count=5,
            note="全員一致",
        )

        # Assert
        assert isinstance(result, CreateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.judgment == "賛成"
        assert result.judge.member_count == 5
        assert "作成しました" in result.message
        mock_judge_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
        sample_judge,
    ):
        """異常系: 同一議案・同一会派の重複登録はエラー."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_judge_repository.get_by_proposal_and_group.return_value = sample_judge

        # Act
        result = await use_case.create(
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="賛成",
        )

        # Assert
        assert result.success is False
        assert "既に登録されています" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_invalid_judgment_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 無効なjudgment値はエラー."""
        # Act
        result = await use_case.create(
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="無効な値",
        )

        # Assert
        assert result.success is False
        assert "無効なjudgment値です" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_parliamentary_group_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 会派が存在しない場合はエラー."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = None

        # Act
        result = await use_case.create(
            proposal_id=10,
            parliamentary_group_id=999,
            judgment="賛成",
        )

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_repository_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_parliamentary_group,
    ):
        """異常系: リポジトリエラー時はエラーメッセージを返す."""
        # Arrange
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )
        mock_judge_repository.get_by_proposal_and_group.return_value = None
        mock_judge_repository.create.side_effect = Exception("Database error")

        # Act
        result = await use_case.create(
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="賛成",
        )

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

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
        """正常系: 会派賛否の更新が成功する."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge
        updated_judge = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_id=1,
            judgment="反対",
            member_count=3,
            note="賛否が分かれた",
        )
        mock_judge_repository.update.return_value = updated_judge
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )

        # Act
        result = await use_case.update(
            judge_id=1,
            judgment="反対",
            member_count=3,
            note="賛否が分かれた",
        )

        # Assert
        assert isinstance(result, UpdateJudgeOutputDTO)
        assert result.success is True
        assert result.judge is not None
        assert result.judge.judgment == "反対"
        assert "更新しました" in result.message
        mock_judge_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """異常系: 対象が存在しない場合はエラー."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = None

        # Act
        result = await use_case.update(
            judge_id=999,
            judgment="反対",
        )

        # Assert
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
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge

        # Act
        result = await use_case.update(
            judge_id=1,
            judgment="無効な値",
        )

        # Assert
        assert result.success is False
        assert "無効なjudgment値です" in result.message
        mock_judge_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_repository_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """異常系: リポジトリエラー時はエラーメッセージを返す."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.update.side_effect = Exception("Database error")

        # Act
        result = await use_case.update(
            judge_id=1,
            judgment="反対",
        )

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

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
        """正常系: 会派賛否の削除が成功する."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.delete.return_value = True

        # Act
        result = await use_case.delete(judge_id=1)

        # Assert
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
        # Arrange
        mock_judge_repository.get_by_id.return_value = None

        # Act
        result = await use_case.delete(judge_id=999)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_judge_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_repository_error(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """異常系: リポジトリエラー時はエラーメッセージを返す."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.delete.side_effect = Exception("Database error")

        # Act
        result = await use_case.delete(judge_id=1)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_delete_failed(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
        sample_judge,
    ):
        """異常系: 削除に失敗した場合はエラー."""
        # Arrange
        mock_judge_repository.get_by_id.return_value = sample_judge
        mock_judge_repository.delete.return_value = False

        # Act
        result = await use_case.delete(judge_id=1)

        # Assert
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
    ):
        """正常系: 議案に紐づく会派賛否一覧を取得する."""
        # Arrange
        judges = [
            ProposalParliamentaryGroupJudge(
                id=1,
                proposal_id=10,
                parliamentary_group_id=1,
                judgment="賛成",
                member_count=5,
            ),
            ProposalParliamentaryGroupJudge(
                id=2,
                proposal_id=10,
                parliamentary_group_id=2,
                judgment="反対",
                member_count=3,
            ),
        ]
        mock_judge_repository.get_by_proposal.return_value = judges
        mock_parliamentary_group_repository.get_by_id.return_value = (
            sample_parliamentary_group
        )

        # Act
        result = await use_case.list_by_proposal(proposal_id=10)

        # Assert
        assert isinstance(result, ProposalParliamentaryGroupJudgeListOutputDTO)
        assert result.total_count == 2
        assert len(result.judges) == 2
        mock_judge_repository.get_by_proposal.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_list_by_proposal_empty(
        self,
        use_case,
        mock_judge_repository,
        mock_parliamentary_group_repository,
    ):
        """正常系: 会派賛否が存在しない場合は空のリストを返す."""
        # Arrange
        mock_judge_repository.get_by_proposal.return_value = []

        # Act
        result = await use_case.list_by_proposal(proposal_id=10)

        # Assert
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
        # Arrange
        mock_judge_repository.get_by_proposal.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await use_case.list_by_proposal(proposal_id=10)
