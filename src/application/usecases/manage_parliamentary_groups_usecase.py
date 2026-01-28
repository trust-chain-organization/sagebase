"""Use case for managing parliamentary groups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from src.application.dtos.extraction_result.parliamentary_group_member_extraction_result import (  # noqa: E501
    ParliamentaryGroupMemberExtractionResult,
)
from src.application.dtos.parliamentary_group_member_dto import (
    ExtractedParliamentaryGroupMemberDTO,
)
from src.common.logging import get_logger
from src.domain.entities import ParliamentaryGroup
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.interfaces.parliamentary_group_member_extractor_service import (
    IParliamentaryGroupMemberExtractorService,
)
from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)


if TYPE_CHECKING:
    from src.application.usecases.update_extracted_parliamentary_group_member_from_extraction_usecase import (  # noqa: E501
        UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase,
    )


logger = get_logger(__name__)


@dataclass
class ParliamentaryGroupListInputDto:
    """Input DTO for listing parliamentary groups."""

    conference_id: int | None = None
    active_only: bool = False


@dataclass
class ParliamentaryGroupListOutputDto:
    """Output DTO for listing parliamentary groups."""

    parliamentary_groups: list[ParliamentaryGroup]


@dataclass
class CreateParliamentaryGroupInputDto:
    """Input DTO for creating a parliamentary group."""

    name: str
    conference_id: int
    url: str | None = None
    description: str | None = None
    is_active: bool = True


@dataclass
class CreateParliamentaryGroupOutputDto:
    """Output DTO for creating a parliamentary group."""

    success: bool
    parliamentary_group: ParliamentaryGroup | None = None
    error_message: str | None = None


@dataclass
class UpdateParliamentaryGroupInputDto:
    """Input DTO for updating a parliamentary group."""

    id: int
    name: str
    url: str | None = None
    description: str | None = None
    is_active: bool = True


@dataclass
class UpdateParliamentaryGroupOutputDto:
    """Output DTO for updating a parliamentary group."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteParliamentaryGroupInputDto:
    """Input DTO for deleting a parliamentary group."""

    id: int


@dataclass
class DeleteParliamentaryGroupOutputDto:
    """Output DTO for deleting a parliamentary group."""

    success: bool
    error_message: str | None = None


@dataclass
class ExtractMembersInputDto:
    """Input DTO for extracting members from URL."""

    parliamentary_group_id: int
    url: str
    confidence_threshold: float = 0.7
    start_date: date | None = None
    dry_run: bool = True


@dataclass
class ExtractMembersOutputDto:
    """議員団メンバー抽出結果のDTO。

    Note: マッチングとメンバーシップ作成は別のUseCaseで行われます：
    - MatchParliamentaryGroupMembersUseCase: 抽出メンバーと政治家のマッチング
    - CreateParliamentaryGroupMembershipsUseCase: メンバーシップの作成
    """

    success: bool
    extracted_members: list[ExtractedParliamentaryGroupMemberDTO] | None = None
    error_message: str | None = None
    errors: list[str] | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None


class ManageParliamentaryGroupsUseCase:
    """Use case for managing parliamentary groups."""

    def __init__(
        self,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        member_extractor: IParliamentaryGroupMemberExtractorService | None = None,
        extracted_member_repository: ExtractedParliamentaryGroupMemberRepository
        | None = None,
        update_usecase: UpdateExtractedParliamentaryGroupMemberFromExtractionUseCase
        | None = None,
        membership_repository: ParliamentaryGroupMembershipRepository | None = None,
    ):
        """Initialize the use case.

        Args:
            parliamentary_group_repository: Repository instance (can be sync or async)
            member_extractor: Member extractor service instance (injected)
            extracted_member_repository: Extracted member repository instance
            update_usecase: 抽出ログを記録するためのUseCase（オプション）
            membership_repository: メンバーシップリポジトリ（削除時チェック用）
        """
        self.parliamentary_group_repository = parliamentary_group_repository
        self.extractor = member_extractor  # Injected instead of created by Factory
        self.extracted_member_repository = extracted_member_repository
        self._update_usecase = update_usecase
        self.membership_repository = membership_repository

    async def list_parliamentary_groups(
        self, input_dto: ParliamentaryGroupListInputDto
    ) -> ParliamentaryGroupListOutputDto:
        """List parliamentary groups with optional filters."""
        try:
            if input_dto.conference_id:
                groups = await self.parliamentary_group_repository.get_by_conference_id(
                    input_dto.conference_id, input_dto.active_only
                )
            else:
                groups = await self.parliamentary_group_repository.get_all()
                if input_dto.active_only:
                    groups = [g for g in groups if g.is_active]

            return ParliamentaryGroupListOutputDto(parliamentary_groups=groups)
        except Exception as e:
            logger.error(f"Failed to list parliamentary groups: {e}")
            raise

    async def create_parliamentary_group(
        self, input_dto: CreateParliamentaryGroupInputDto
    ) -> CreateParliamentaryGroupOutputDto:
        """Create a new parliamentary group."""
        try:
            # Check for duplicates
            existing = (
                await self.parliamentary_group_repository.get_by_name_and_conference(
                    input_dto.name, input_dto.conference_id
                )
            )
            if existing:
                return CreateParliamentaryGroupOutputDto(
                    success=False,
                    error_message="同じ名前の議員団が既に存在します。",
                )

            # Create new parliamentary group
            parliamentary_group = ParliamentaryGroup(
                name=input_dto.name,
                conference_id=input_dto.conference_id,
                url=input_dto.url,
                description=input_dto.description,
                is_active=input_dto.is_active,
            )

            created = await self.parliamentary_group_repository.create(
                parliamentary_group
            )
            return CreateParliamentaryGroupOutputDto(
                success=True, parliamentary_group=created
            )
        except Exception as e:
            logger.error(f"Failed to create parliamentary group: {e}")
            return CreateParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    async def update_parliamentary_group(
        self, input_dto: UpdateParliamentaryGroupInputDto
    ) -> UpdateParliamentaryGroupOutputDto:
        """Update an existing parliamentary group."""
        try:
            # Get existing parliamentary group
            existing = await self.parliamentary_group_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateParliamentaryGroupOutputDto(
                    success=False, error_message="議員団が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            existing.url = input_dto.url
            existing.description = input_dto.description
            existing.is_active = input_dto.is_active

            await self.parliamentary_group_repository.update(existing)
            return UpdateParliamentaryGroupOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update parliamentary group: {e}")
            return UpdateParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    async def delete_parliamentary_group(
        self, input_dto: DeleteParliamentaryGroupInputDto
    ) -> DeleteParliamentaryGroupOutputDto:
        """Delete a parliamentary group."""
        try:
            # Check if parliamentary group exists
            existing = await self.parliamentary_group_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteParliamentaryGroupOutputDto(
                    success=False, error_message="議員団が見つかりません。"
                )

            # Check if it's active
            if existing.is_active:
                return DeleteParliamentaryGroupOutputDto(
                    success=False,
                    error_message="活動中の議員団は削除できません。先に非活動にしてください。",
                )

            # メンバー存在チェック
            if self.membership_repository:
                members = await self.membership_repository.get_by_group(input_dto.id)
                if members:
                    return DeleteParliamentaryGroupOutputDto(
                        success=False,
                        error_message="メンバーが所属している議員団は削除できません。先にメンバーを削除してください。",
                    )

            await self.parliamentary_group_repository.delete(input_dto.id)
            return DeleteParliamentaryGroupOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete parliamentary group: {e}")
            return DeleteParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    async def extract_members(
        self, input_dto: ExtractMembersInputDto
    ) -> ExtractMembersOutputDto:
        """議員団URLからメンバーを抽出する。

        Note: このメソッドはメンバーの抽出のみを行います。
        マッチングとメンバーシップ作成は以下の別のUseCaseで実行してください：
        - MatchParliamentaryGroupMembersUseCase: 抽出メンバーと政治家のマッチング
        - CreateParliamentaryGroupMembershipsUseCase: メンバーシップの作成
        """
        try:
            if not self.extractor:
                return ExtractMembersOutputDto(
                    success=False,
                    error_message="必要なサービスが初期化されていません。LLMサービスとリポジトリが設定されているか確認してください。",
                )

            # Extract members from URL using async extractor
            extraction_result = await self.extractor.extract_members(
                parliamentary_group_id=input_dto.parliamentary_group_id,
                url=input_dto.url,
            )

            if extraction_result.error:
                return ExtractMembersOutputDto(
                    success=False,
                    error_message=f"メンバー抽出エラー: {extraction_result.error}",
                )

            # Save extracted members to database if repository is available
            if self.extracted_member_repository and not input_dto.dry_run:
                saved_count = 0

                for member in extraction_result.extracted_members:
                    try:
                        # Create entity
                        entity = ExtractedParliamentaryGroupMember(
                            parliamentary_group_id=input_dto.parliamentary_group_id,
                            extracted_name=member.name,
                            source_url=input_dto.url,
                            extracted_role=member.role,
                            extracted_party_name=member.party_name,
                            extracted_district=member.district,
                            extracted_at=extraction_result.extraction_date,
                            additional_info=member.additional_info,
                        )

                        # Save entity to database
                        created_entity = await self.extracted_member_repository.create(
                            entity
                        )

                        if created_entity:
                            saved_count += 1

                            # 抽出ログを記録（UseCaseがあれば）
                            if self._update_usecase and created_entity.id:
                                try:
                                    result = ParliamentaryGroupMemberExtractionResult(
                                        parliamentary_group_id=input_dto.parliamentary_group_id,
                                        extracted_name=member.name,
                                        source_url=input_dto.url,
                                        extracted_role=member.role,
                                        extracted_party_name=member.party_name,
                                        extracted_district=member.district,
                                        additional_info=member.additional_info,
                                    )
                                    await self._update_usecase.execute(
                                        entity_id=created_entity.id,
                                        extraction_result=result,
                                        pipeline_version="parliamentary-group-member-extractor-v1",
                                    )
                                except Exception as e:
                                    name = member.name
                                    logger.warning(
                                        f"Failed to log extraction for {name}: {e}"
                                    )
                                    # 抽出ログ記録失敗は処理を中断しない

                    except Exception as e:
                        logger.error(f"Failed to save member {member.name}: {e}")

                logger.info(f"Saved {saved_count} extracted members to database")

            return ExtractMembersOutputDto(
                success=True,
                extracted_members=extraction_result.extracted_members,
            )

        except Exception as e:
            logger.error(f"Failed to extract members: {e}")
            return ExtractMembersOutputDto(success=False, error_message=str(e))

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for parliamentary groups."""
        try:
            # Get all parliamentary groups
            all_groups = await self.parliamentary_group_repository.get_all()

            # Generate SQL content
            seed_content = "-- Parliamentary Groups Seed Data\n"
            seed_content += "-- Generated from current database\n\n"
            seed_content += (
                "INSERT INTO parliamentary_groups "
                "(id, name, conference_id, url, description, is_active) VALUES\n"
            )

            values: list[str] = []
            for group in all_groups:
                url = f"'{group.url}'" if group.url else "NULL"
                description = f"'{group.description}'" if group.description else "NULL"
                is_active = "true" if group.is_active else "false"
                values.append(
                    f"    ({group.id}, '{group.name}', {group.conference_id}, "
                    f"{url}, {description}, {is_active})"
                )

            seed_content += ",\n".join(values) + "\n"
            seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
            seed_content += "    name = EXCLUDED.name,\n"
            seed_content += "    conference_id = EXCLUDED.conference_id,\n"
            seed_content += "    url = EXCLUDED.url,\n"
            seed_content += "    description = EXCLUDED.description,\n"
            seed_content += "    is_active = EXCLUDED.is_active;\n"

            # Save to file
            file_path = "database/seed_parliamentary_groups_generated.sql"
            with open(file_path, "w") as f:
                f.write(seed_content)

            return GenerateSeedFileOutputDto(
                success=True, seed_content=seed_content, file_path=file_path
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
