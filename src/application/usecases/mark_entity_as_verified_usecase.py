"""手動検証フラグ更新UseCase。

VerifiableEntityプロトコルを実装したエンティティの手動検証フラグを
更新するための汎用的なUseCase。
"""

from dataclasses import dataclass
from enum import Enum

from src.common.logging import get_logger
from src.domain.repositories import (
    ConversationRepository,
    PoliticianRepository,
)
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)
from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)


logger = get_logger(__name__)


class EntityType(Enum):
    """手動検証可能なエンティティタイプ。"""

    POLITICIAN = "politician"
    CONVERSATION = "conversation"
    CONFERENCE_MEMBER = "conference_member"
    PARLIAMENTARY_GROUP_MEMBER = "parliamentary_group_member"


@dataclass
class MarkEntityAsVerifiedInputDto:
    """手動検証フラグ更新の入力DTO。"""

    entity_type: EntityType
    entity_id: int
    is_verified: bool


@dataclass
class MarkEntityAsVerifiedOutputDto:
    """手動検証フラグ更新の出力DTO。"""

    success: bool
    error_message: str | None = None


class MarkEntityAsVerifiedUseCase:
    """手動検証フラグ更新UseCase。

    各エンティティの手動検証フラグを更新する汎用的なUseCase。
    エンティティタイプに応じて適切なリポジトリを使用する。
    """

    def __init__(
        self,
        politician_repository: PoliticianRepository | None = None,
        conversation_repository: ConversationRepository | None = None,
        conference_member_repository: (
            ExtractedConferenceMemberRepository | None
        ) = None,
        parliamentary_group_member_repository: (
            ExtractedParliamentaryGroupMemberRepository | None
        ) = None,
    ):
        """初期化。

        Args:
            politician_repository: 政治家リポジトリ
            conversation_repository: 発言リポジトリ
            conference_member_repository: 会議体メンバーリポジトリ
            parliamentary_group_member_repository: 議員団メンバーリポジトリ
        """
        self._politician_repo = politician_repository
        self._conversation_repo = conversation_repository
        self._conference_member_repo = conference_member_repository
        self._parliamentary_group_member_repo = parliamentary_group_member_repository

    async def execute(
        self, input_dto: MarkEntityAsVerifiedInputDto
    ) -> MarkEntityAsVerifiedOutputDto:
        """手動検証フラグを更新する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO
        """
        try:
            if input_dto.entity_type == EntityType.POLITICIAN:
                return await self._update_politician(
                    input_dto.entity_id, input_dto.is_verified
                )
            elif input_dto.entity_type == EntityType.CONVERSATION:
                return await self._update_conversation(
                    input_dto.entity_id, input_dto.is_verified
                )
            elif input_dto.entity_type == EntityType.CONFERENCE_MEMBER:
                return await self._update_conference_member(
                    input_dto.entity_id, input_dto.is_verified
                )
            elif input_dto.entity_type == EntityType.PARLIAMENTARY_GROUP_MEMBER:
                return await self._update_parliamentary_group_member(
                    input_dto.entity_id, input_dto.is_verified
                )
            else:
                return MarkEntityAsVerifiedOutputDto(
                    success=False,
                    error_message=f"Unknown entity type: {input_dto.entity_type}",
                )
        except Exception as e:
            logger.error(f"Failed to update verification status: {e}")
            return MarkEntityAsVerifiedOutputDto(success=False, error_message=str(e))

    async def _update_politician(
        self, entity_id: int, is_verified: bool
    ) -> MarkEntityAsVerifiedOutputDto:
        """政治家の手動検証フラグを更新する。"""
        if not self._politician_repo:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="Politician repository not configured",
            )

        entity = await self._politician_repo.get_by_id(entity_id)
        if not entity:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="政治家が見つかりません。",
            )

        if is_verified:
            entity.mark_as_manually_verified()
        else:
            entity.is_manually_verified = False

        await self._politician_repo.update(entity)
        return MarkEntityAsVerifiedOutputDto(success=True)

    async def _update_conversation(
        self, entity_id: int, is_verified: bool
    ) -> MarkEntityAsVerifiedOutputDto:
        """発言の手動検証フラグを更新する。"""
        if not self._conversation_repo:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="Conversation repository not configured",
            )

        entity = await self._conversation_repo.get_by_id(entity_id)
        if not entity:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="発言が見つかりません。",
            )

        if is_verified:
            entity.mark_as_manually_verified()
        else:
            entity.is_manually_verified = False

        await self._conversation_repo.update(entity)
        return MarkEntityAsVerifiedOutputDto(success=True)

    async def _update_conference_member(
        self, entity_id: int, is_verified: bool
    ) -> MarkEntityAsVerifiedOutputDto:
        """会議体メンバーの手動検証フラグを更新する。"""
        if not self._conference_member_repo:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="Conference member repository not configured",
            )

        entity = await self._conference_member_repo.get_by_id(entity_id)
        if not entity:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="会議体メンバーが見つかりません。",
            )

        if is_verified:
            entity.mark_as_manually_verified()
        else:
            entity.is_manually_verified = False

        await self._conference_member_repo.update(entity)
        return MarkEntityAsVerifiedOutputDto(success=True)

    async def _update_parliamentary_group_member(
        self, entity_id: int, is_verified: bool
    ) -> MarkEntityAsVerifiedOutputDto:
        """議員団メンバーの手動検証フラグを更新する。"""
        if not self._parliamentary_group_member_repo:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="Parliamentary group member repository not configured",
            )

        entity = await self._parliamentary_group_member_repo.get_by_id(entity_id)
        if not entity:
            return MarkEntityAsVerifiedOutputDto(
                success=False,
                error_message="議員団メンバーが見つかりません。",
            )

        if is_verified:
            entity.mark_as_manually_verified()
        else:
            entity.is_manually_verified = False

        await self._parliamentary_group_member_repo.update(entity)
        return MarkEntityAsVerifiedOutputDto(success=True)
