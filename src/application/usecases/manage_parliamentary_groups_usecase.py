"""Use case for managing parliamentary groups."""

from dataclasses import dataclass
from datetime import date

from src.common.logging import get_logger
from src.domain.entities import ParliamentaryGroup
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
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
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.parliamentary_group_member_extractor.factory import (
    ParliamentaryGroupMemberExtractorFactory,
)
from src.parliamentary_group_member_extractor.service import (
    ParliamentaryGroupMembershipService,
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
class ExtractedMember:
    """Extracted member information."""

    name: str
    role: str | None = None
    party_name: str | None = None
    district: str | None = None
    additional_info: str | None = None


@dataclass
class MemberMatchingResult:
    """Member matching result."""

    extracted_member: ExtractedMember
    politician_id: int | None = None
    politician_name: str | None = None
    confidence_score: float = 0.0
    matching_reason: str = ""


@dataclass
class ExtractMembersOutputDto:
    """Output DTO for extracting members."""

    success: bool
    extracted_members: list[ExtractedMember] | None = None
    matching_results: list[MemberMatchingResult] | None = None
    created_count: int = 0
    skipped_count: int = 0
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
        politician_repository: PoliticianRepository | None = None,
        membership_repository: ParliamentaryGroupMembershipRepository | None = None,
        llm_service: ILLMService | None = None,
        extracted_member_repository: ExtractedParliamentaryGroupMemberRepository
        | None = None,
    ):
        """Initialize the use case.

        Args:
            parliamentary_group_repository: Repository instance (can be sync or async)
            politician_repository: Politician repository instance
            membership_repository: Membership repository instance
            llm_service: LLM service instance
            extracted_member_repository: Extracted member repository instance
        """
        self.parliamentary_group_repository = parliamentary_group_repository
        self.politician_repository = politician_repository
        self.membership_repository = membership_repository
        self.llm_service = llm_service
        self.extracted_member_repository = extracted_member_repository

        # Initialize extractor and service if all dependencies are available
        if llm_service:
            self.extractor = ParliamentaryGroupMemberExtractorFactory.create()
        else:
            self.extractor = None

        if all(
            [
                politician_repository,
                parliamentary_group_repository,
                membership_repository,
                llm_service,
            ]
        ):
            self.membership_service = ParliamentaryGroupMembershipService(
                llm_service=llm_service,
                politician_repo=politician_repository,
                group_repo=parliamentary_group_repository,
                membership_repo=membership_repository,
            )
        else:
            self.membership_service = None

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
                id=0,  # Will be assigned by database
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

            # TODO: Check if it has members
            # This would require a membership repository

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
        """Extract members from parliamentary group URL."""
        try:
            # Check if services are available
            if not self.extractor or not self.membership_service:
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

            # Convert extracted members to DTO format
            extracted_members = [
                ExtractedMember(
                    name=member.name,
                    role=member.role,
                    party_name=member.party_name,
                    district=member.district,
                    additional_info=member.additional_info,
                )
                for member in extraction_result.extracted_members
            ]

            # Save extracted members to database if repository is available
            if self.extracted_member_repository and not input_dto.dry_run:
                # Create ExtractedParliamentaryGroupMember entities
                entities_to_save = [
                    ExtractedParliamentaryGroupMember(
                        parliamentary_group_id=input_dto.parliamentary_group_id,
                        extracted_name=member.name,
                        source_url=input_dto.url,
                        extracted_role=member.role,
                        extracted_party_name=member.party_name,
                        extracted_district=member.district,
                        extracted_at=extraction_result.extraction_date,
                        additional_info=member.additional_info,
                    )
                    for member in extraction_result.extracted_members
                ]

                # Bulk create in database
                try:
                    if hasattr(self.extracted_member_repository, "bulk_create"):
                        # Use await for async repositories
                        await self.extracted_member_repository.bulk_create(
                            entities_to_save
                        )
                    logger.info(
                        f"Saved {len(entities_to_save)} extracted members to database"
                    )
                except Exception as e:
                    logger.error(f"Failed to save extracted members to database: {e}")

            if input_dto.dry_run:
                # Dry run mode - just return extracted members without saving
                return ExtractMembersOutputDto(
                    success=True,
                    extracted_members=extracted_members,
                    created_count=0,
                    skipped_count=0,
                )

            # Match politicians with extracted members
            matching_results_from_service = (
                await self.membership_service.match_politicians(
                    extracted_members=extraction_result.extracted_members,
                    conference_id=None,  # Can be set if needed to narrow search
                )
            )

            # Create memberships if not dry run
            if not input_dto.dry_run:
                creation_result = self.membership_service.create_memberships(
                    parliamentary_group_id=input_dto.parliamentary_group_id,
                    matching_results=matching_results_from_service,
                    start_date=input_dto.start_date,
                    confidence_threshold=input_dto.confidence_threshold,
                    dry_run=False,
                )
                created_count = creation_result.created_count
                skipped_count = creation_result.skipped_count
            else:
                # In dry run mode, just count potential matches
                created_count = 0
                skipped_count = 0
                for match in matching_results_from_service:
                    if (
                        match.politician_id
                        and match.confidence_score >= input_dto.confidence_threshold
                    ):
                        created_count += 1
                    else:
                        skipped_count += 1

            # Convert service results to DTO format
            matching_results = []
            for idx, match in enumerate(matching_results_from_service):
                extracted_member = extracted_members[idx]
                matching_results.append(
                    MemberMatchingResult(
                        extracted_member=extracted_member,
                        politician_id=match.politician_id,
                        politician_name=match.politician_name,
                        confidence_score=match.confidence_score,
                        matching_reason=match.matching_reason,
                    )
                )

            return ExtractMembersOutputDto(
                success=True,
                extracted_members=extracted_members,
                matching_results=matching_results,
                created_count=created_count,
                skipped_count=skipped_count,
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
