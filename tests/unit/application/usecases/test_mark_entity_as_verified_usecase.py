"""MarkEntityAsVerifiedUseCaseの単体テスト。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.mark_entity_as_verified_usecase import (
    EntityType,
    MarkEntityAsVerifiedInputDto,
    MarkEntityAsVerifiedUseCase,
)
from src.domain.entities import Politician
from src.domain.entities.conversation import Conversation
from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)


class TestMarkEntityAsVerifiedUseCase:
    """MarkEntityAsVerifiedUseCaseのテスト。"""

    @pytest.fixture
    def mock_politician_repo(self) -> MagicMock:
        """政治家リポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_conversation_repo(self) -> MagicMock:
        """発言リポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_conference_member_repo(self) -> MagicMock:
        """会議体メンバーリポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def mock_parliamentary_group_member_repo(self) -> MagicMock:
        """議員団メンバーリポジトリのモック。"""
        return MagicMock()

    @pytest.fixture
    def usecase(
        self,
        mock_politician_repo: MagicMock,
        mock_conversation_repo: MagicMock,
        mock_conference_member_repo: MagicMock,
        mock_parliamentary_group_member_repo: MagicMock,
    ) -> MarkEntityAsVerifiedUseCase:
        """UseCaseのインスタンス。"""
        return MarkEntityAsVerifiedUseCase(
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            conference_member_repository=mock_conference_member_repo,
            parliamentary_group_member_repository=mock_parliamentary_group_member_repo,
        )

    @pytest.mark.asyncio
    async def test_mark_politician_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家を手動検証済みにマーク成功のテスト。"""
        # Arrange
        politician = Politician(id=1, name="テスト政治家")
        mock_politician_repo.get_by_id = AsyncMock(return_value=politician)
        mock_politician_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert politician.is_manually_verified is True
        mock_politician_repo.get_by_id.assert_called_once_with(1)
        mock_politician_repo.update.assert_called_once_with(politician)

    @pytest.mark.asyncio
    async def test_mark_politician_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家の手動検証済みを解除するテスト。"""
        # Arrange
        politician = Politician(id=1, name="テスト政治家")
        politician.mark_as_manually_verified()
        assert politician.is_manually_verified is True

        mock_politician_repo.get_by_id = AsyncMock(return_value=politician)
        mock_politician_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert politician.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_politician_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """政治家が見つからない場合のテスト。"""
        # Arrange
        mock_politician_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "政治家が見つかりません。"

    @pytest.mark.asyncio
    async def test_repository_not_configured(self) -> None:
        """リポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]

    @pytest.mark.asyncio
    async def test_repository_error_handling(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_politician_repo: MagicMock,
    ) -> None:
        """リポジトリエラー時のハンドリングテスト。"""
        # Arrange
        mock_politician_repo.get_by_id = AsyncMock(
            side_effect=Exception("Database error")
        )

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.POLITICIAN,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message  # type: ignore[operator]

    # ========== Conversationエンティティのテスト ==========

    @pytest.mark.asyncio
    async def test_mark_conversation_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言を手動検証済みにマーク成功のテスト。"""
        # Arrange
        conversation = Conversation(
            id=1,
            comment="テスト発言",
            sequence_number=1,
            minutes_id=1,
        )
        mock_conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        mock_conversation_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert conversation.is_manually_verified is True
        mock_conversation_repo.get_by_id.assert_called_once_with(1)
        mock_conversation_repo.update.assert_called_once_with(conversation)

    @pytest.mark.asyncio
    async def test_mark_conversation_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言の手動検証済みを解除するテスト。"""
        # Arrange
        conversation = Conversation(
            id=1,
            comment="テスト発言",
            sequence_number=1,
            minutes_id=1,
        )
        conversation.mark_as_manually_verified()
        assert conversation.is_manually_verified is True

        mock_conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        mock_conversation_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert conversation.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_conversation_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conversation_repo: MagicMock,
    ) -> None:
        """発言が見つからない場合のテスト。"""
        # Arrange
        mock_conversation_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "発言が見つかりません。"

    @pytest.mark.asyncio
    async def test_conversation_repository_not_configured(self) -> None:
        """発言リポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONVERSATION,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]

    # ========== ConferenceMemberエンティティのテスト ==========

    @pytest.mark.asyncio
    async def test_mark_conference_member_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conference_member_repo: MagicMock,
    ) -> None:
        """会議体メンバーを手動検証済みにマーク成功のテスト。"""
        # Arrange
        member = ExtractedConferenceMember(
            id=1,
            conference_id=1,
            extracted_name="テスト議員",
            source_url="https://example.com",
        )
        mock_conference_member_repo.get_by_id = AsyncMock(return_value=member)
        mock_conference_member_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert member.is_manually_verified is True
        mock_conference_member_repo.get_by_id.assert_called_once_with(1)
        mock_conference_member_repo.update.assert_called_once_with(member)

    @pytest.mark.asyncio
    async def test_mark_conference_member_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conference_member_repo: MagicMock,
    ) -> None:
        """会議体メンバーの手動検証済みを解除するテスト。"""
        # Arrange
        member = ExtractedConferenceMember(
            id=1,
            conference_id=1,
            extracted_name="テスト議員",
            source_url="https://example.com",
        )
        member.mark_as_manually_verified()
        assert member.is_manually_verified is True

        mock_conference_member_repo.get_by_id = AsyncMock(return_value=member)
        mock_conference_member_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert member.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_conference_member_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_conference_member_repo: MagicMock,
    ) -> None:
        """会議体メンバーが見つからない場合のテスト。"""
        # Arrange
        mock_conference_member_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "会議体メンバーが見つかりません。"

    @pytest.mark.asyncio
    async def test_conference_member_repository_not_configured(self) -> None:
        """会議体メンバーリポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.CONFERENCE_MEMBER,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]

    # ========== ParliamentaryGroupMemberエンティティのテスト ==========

    @pytest.mark.asyncio
    async def test_mark_parliamentary_group_member_as_verified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_parliamentary_group_member_repo: MagicMock,
    ) -> None:
        """議員団メンバーを手動検証済みにマーク成功のテスト。"""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=1,
            extracted_name="テスト議員",
            source_url="https://example.com",
        )
        mock_parliamentary_group_member_repo.get_by_id = AsyncMock(return_value=member)
        mock_parliamentary_group_member_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert member.is_manually_verified is True
        mock_parliamentary_group_member_repo.get_by_id.assert_called_once_with(1)
        mock_parliamentary_group_member_repo.update.assert_called_once_with(member)

    @pytest.mark.asyncio
    async def test_mark_parliamentary_group_member_as_unverified_success(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_parliamentary_group_member_repo: MagicMock,
    ) -> None:
        """議員団メンバーの手動検証済みを解除するテスト。"""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=1,
            extracted_name="テスト議員",
            source_url="https://example.com",
        )
        member.mark_as_manually_verified()
        assert member.is_manually_verified is True

        mock_parliamentary_group_member_repo.get_by_id = AsyncMock(return_value=member)
        mock_parliamentary_group_member_repo.update = AsyncMock()

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            is_verified=False,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.error_message is None
        assert member.is_manually_verified is False

    @pytest.mark.asyncio
    async def test_mark_parliamentary_group_member_not_found(
        self,
        usecase: MarkEntityAsVerifiedUseCase,
        mock_parliamentary_group_member_repo: MagicMock,
    ) -> None:
        """議員団メンバーが見つからない場合のテスト。"""
        # Arrange
        mock_parliamentary_group_member_repo.get_by_id = AsyncMock(return_value=None)

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=999,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert result.error_message == "議員団メンバーが見つかりません。"

    @pytest.mark.asyncio
    async def test_parliamentary_group_member_repository_not_configured(self) -> None:
        """議員団メンバーリポジトリが未設定の場合のテスト。"""
        # Arrange
        usecase = MarkEntityAsVerifiedUseCase()  # リポジトリなしで作成

        input_dto = MarkEntityAsVerifiedInputDto(
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            is_verified=True,
        )

        # Act
        result = await usecase.execute(input_dto)

        # Assert
        assert result.success is False
        assert "not configured" in result.error_message  # type: ignore[operator]
