"""Use case for managing conferences."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import Conference
from src.domain.repositories.conference_repository import ConferenceRepository


logger = get_logger(__name__)


@dataclass
class ConferenceListInputDto:
    """Input DTO for listing conferences."""

    governing_body_id: int | None = None
    with_members_url: bool | None = None


@dataclass
class ConferenceListOutputDto:
    """Output DTO for listing conferences."""

    conferences: list[Conference]
    with_url_count: int
    without_url_count: int


@dataclass
class CreateConferenceInputDto:
    """Input DTO for creating a conference."""

    name: str
    governing_body_id: int | None = None
    type: str | None = None
    members_introduction_url: str | None = None


@dataclass
class CreateConferenceOutputDto:
    """Output DTO for creating a conference."""

    success: bool
    conference_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateConferenceInputDto:
    """Input DTO for updating a conference."""

    id: int
    name: str
    governing_body_id: int | None = None
    type: str | None = None
    members_introduction_url: str | None = None


@dataclass
class UpdateConferenceOutputDto:
    """Output DTO for updating a conference."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteConferenceInputDto:
    """Input DTO for deleting a conference."""

    id: int


@dataclass
class DeleteConferenceOutputDto:
    """Output DTO for deleting a conference."""

    success: bool
    error_message: str | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None


class ManageConferencesUseCase:
    """Use case for managing conferences."""

    def __init__(self, conference_repository: ConferenceRepository):
        """Initialize the use case.

        Args:
            conference_repository: Repository instance (can be sync or async)
        """
        self.conference_repository = conference_repository

    async def list_conferences(
        self, input_dto: ConferenceListInputDto
    ) -> ConferenceListOutputDto:
        """List conferences with optional filters."""
        try:
            if input_dto.governing_body_id:
                conferences = await self.conference_repository.get_by_governing_body(
                    input_dto.governing_body_id
                )
            else:
                conferences = await self.conference_repository.get_all()
            # Apply URL filter if specified
            if input_dto.with_members_url is not None:
                if input_dto.with_members_url:
                    conferences = [c for c in conferences if c.members_introduction_url]
                else:
                    conferences = [
                        c for c in conferences if not c.members_introduction_url
                    ]

            # Count statistics
            all_conferences = await self.conference_repository.get_all()
            with_url_count = len(
                [c for c in all_conferences if c.members_introduction_url]
            )
            without_url_count = len(all_conferences) - with_url_count
            return ConferenceListOutputDto(
                conferences=conferences,
                with_url_count=with_url_count,
                without_url_count=without_url_count,
            )
        except Exception as e:
            logger.error(f"Failed to list conferences: {e}")
            raise

    async def create_conference(
        self, input_dto: CreateConferenceInputDto
    ) -> CreateConferenceOutputDto:
        """Create a new conference."""
        try:
            # Check for duplicates
            if input_dto.governing_body_id is not None:
                existing = (
                    await self.conference_repository.get_by_name_and_governing_body(
                        input_dto.name, input_dto.governing_body_id
                    )
                )
            else:
                existing = None

            if existing:
                return CreateConferenceOutputDto(
                    success=False,
                    error_message="同じ名前の会議体が既に存在します。",
                )

            # Create new conference
            conference = Conference(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                governing_body_id=(
                    input_dto.governing_body_id if input_dto.governing_body_id else 0
                ),
                type=input_dto.type,
                members_introduction_url=input_dto.members_introduction_url,
            )

            created = await self.conference_repository.create(conference)
            return CreateConferenceOutputDto(success=True, conference_id=created.id)
        except Exception as e:
            logger.error(f"Failed to create conference: {e}")
            return CreateConferenceOutputDto(success=False, error_message=str(e))

    async def update_conference(
        self, input_dto: UpdateConferenceInputDto
    ) -> UpdateConferenceOutputDto:
        """Update an existing conference."""
        try:
            # Get existing conference
            existing = await self.conference_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateConferenceOutputDto(
                    success=False, error_message="会議体が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            if input_dto.governing_body_id is not None:
                existing.governing_body_id = input_dto.governing_body_id
            existing.type = input_dto.type
            existing.members_introduction_url = input_dto.members_introduction_url
            await self.conference_repository.update(existing)
            return UpdateConferenceOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update conference: {e}")
            return UpdateConferenceOutputDto(success=False, error_message=str(e))

    async def delete_conference(
        self, input_dto: DeleteConferenceInputDto
    ) -> DeleteConferenceOutputDto:
        """Delete a conference."""
        try:
            # Check if conference exists
            existing = await self.conference_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteConferenceOutputDto(
                    success=False, error_message="会議体が見つかりません。"
                )

            # TODO: Check if conference has related meetings
            # This would require a meeting repository

            await self.conference_repository.delete(input_dto.id)
            return DeleteConferenceOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete conference: {e}")
            return DeleteConferenceOutputDto(success=False, error_message=str(e))

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for conferences."""
        try:
            # Get all conferences
            all_conferences = await self.conference_repository.get_all()
            # Generate SQL content
            seed_content = "-- Conferences Seed Data\n"
            seed_content += "-- Generated from current database\n\n"
            seed_content += (
                "INSERT INTO conferences "
                "(id, name, governing_body_id, type, members_introduction_url) VALUES\n"
            )

            values: list[str] = []
            for conf in all_conferences:
                gb_id = conf.governing_body_id if conf.governing_body_id else "NULL"
                conf_type = f"'{conf.type}'" if conf.type else "NULL"
                members_url = (
                    f"'{conf.members_introduction_url}'"
                    if conf.members_introduction_url
                    else "NULL"
                )
                values.append(
                    f"    ({conf.id}, '{conf.name}', {gb_id}, "
                    f"{conf_type}, {members_url})"
                )

            seed_content += ",\n".join(values) + "\n"
            seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
            seed_content += "    name = EXCLUDED.name,\n"
            seed_content += "    governing_body_id = EXCLUDED.governing_body_id,\n"
            seed_content += "    type = EXCLUDED.type,\n"
            seed_content += (
                "    members_introduction_url = EXCLUDED.members_introduction_url;\n"
            )

            # Save to file
            file_path = "database/seed_conferences_generated.sql"
            with open(file_path, "w") as f:
                f.write(seed_content)

            return GenerateSeedFileOutputDto(
                success=True, seed_content=seed_content, file_path=file_path
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
