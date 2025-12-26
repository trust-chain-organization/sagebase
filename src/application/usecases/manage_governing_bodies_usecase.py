"""Use case for managing governing bodies."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import GoverningBody
from src.domain.repositories.governing_body_repository import GoverningBodyRepository


logger = get_logger(__name__)


@dataclass
class GoverningBodyListInputDto:
    """Input DTO for listing governing bodies."""

    type_filter: str | None = None
    conference_filter: str | None = None


@dataclass
class GoverningBodyStatistics:
    """Statistics for governing bodies."""

    total_count: int
    country_count: int
    prefecture_count: int
    city_count: int
    with_conference_count: int
    without_conference_count: int


@dataclass
class GoverningBodyListOutputDto:
    """Output DTO for listing governing bodies."""

    governing_bodies: list[GoverningBody]
    statistics: GoverningBodyStatistics


@dataclass
class CreateGoverningBodyInputDto:
    """Input DTO for creating a governing body."""

    name: str
    type: str
    organization_code: str | None = None
    organization_type: str | None = None


@dataclass
class CreateGoverningBodyOutputDto:
    """Output DTO for creating a governing body."""

    success: bool
    governing_body_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdateGoverningBodyInputDto:
    """Input DTO for updating a governing body."""

    id: int
    name: str
    type: str
    organization_code: str | None = None
    organization_type: str | None = None


@dataclass
class UpdateGoverningBodyOutputDto:
    """Output DTO for updating a governing body."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteGoverningBodyInputDto:
    """Input DTO for deleting a governing body."""

    id: int


@dataclass
class DeleteGoverningBodyOutputDto:
    """Output DTO for deleting a governing body."""

    success: bool
    error_message: str | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None


class ManageGoverningBodiesUseCase:
    """Use case for managing governing bodies."""

    def __init__(self, governing_body_repository: GoverningBodyRepository):
        """Initialize the use case.

        Args:
            governing_body_repository: Repository instance (can be sync or async)
        """
        self.governing_body_repository = governing_body_repository

    async def list_governing_bodies(
        self, input_dto: GoverningBodyListInputDto
    ) -> GoverningBodyListOutputDto:
        """List governing bodies with optional filters."""
        try:
            # Get all governing bodies
            all_bodies = await self.governing_body_repository.get_all()
            # Apply type filter
            if input_dto.type_filter and input_dto.type_filter != "すべて":
                all_bodies = [
                    gb for gb in all_bodies if gb.type == input_dto.type_filter
                ]

            # Apply conference filter
            if input_dto.conference_filter == "会議体あり":
                all_bodies = [
                    gb
                    for gb in all_bodies
                    if hasattr(gb, "conference_count") and gb.conference_count > 0
                ]
            elif input_dto.conference_filter == "会議体なし":
                all_bodies = [
                    gb
                    for gb in all_bodies
                    if not hasattr(gb, "conference_count") or gb.conference_count == 0
                ]

            # Calculate statistics
            statistics = GoverningBodyStatistics(
                total_count=len(all_bodies),
                country_count=len([gb for gb in all_bodies if gb.type == "国"]),
                prefecture_count=len(
                    [gb for gb in all_bodies if gb.type == "都道府県"]
                ),
                city_count=len([gb for gb in all_bodies if gb.type == "市町村"]),
                with_conference_count=len(
                    [
                        gb
                        for gb in all_bodies
                        if hasattr(gb, "conference_count") and gb.conference_count > 0
                    ]
                ),
                without_conference_count=len(
                    [
                        gb
                        for gb in all_bodies
                        if not hasattr(gb, "conference_count")
                        or gb.conference_count == 0
                    ]
                ),
            )

            return GoverningBodyListOutputDto(
                governing_bodies=all_bodies, statistics=statistics
            )
        except Exception as e:
            logger.error(f"Failed to list governing bodies: {e}")
            raise

    async def create_governing_body(
        self, input_dto: CreateGoverningBodyInputDto
    ) -> CreateGoverningBodyOutputDto:
        """Create a new governing body."""
        try:
            # Check for duplicates
            existing = await self.governing_body_repository.get_by_name_and_type(
                input_dto.name, input_dto.type
            )
            if existing:
                return CreateGoverningBodyOutputDto(
                    success=False,
                    error_message="同じ名前と種別の開催主体が既に存在します。",
                )

            # Create new governing body
            governing_body = GoverningBody(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                type=input_dto.type,
                organization_code=input_dto.organization_code,
                organization_type=input_dto.organization_type,
            )

            created = await self.governing_body_repository.create(governing_body)
            return CreateGoverningBodyOutputDto(
                success=True, governing_body_id=created.id
            )
        except Exception as e:
            logger.error(f"Failed to create governing body: {e}")
            return CreateGoverningBodyOutputDto(success=False, error_message=str(e))

    async def update_governing_body(
        self, input_dto: UpdateGoverningBodyInputDto
    ) -> UpdateGoverningBodyOutputDto:
        """Update an existing governing body."""
        try:
            # Get existing governing body
            existing = await self.governing_body_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateGoverningBodyOutputDto(
                    success=False, error_message="開催主体が見つかりません。"
                )

            # Check for duplicates (excluding self)
            duplicate = await self.governing_body_repository.get_by_name_and_type(
                input_dto.name, input_dto.type
            )
            if duplicate and duplicate.id != input_dto.id:
                return UpdateGoverningBodyOutputDto(
                    success=False,
                    error_message="同じ名前と種別の開催主体が既に存在します。",
                )

            # Update fields
            existing.name = input_dto.name
            existing.type = input_dto.type
            if input_dto.organization_code is not None:
                existing.organization_code = input_dto.organization_code
            if input_dto.organization_type is not None:
                existing.organization_type = input_dto.organization_type

            await self.governing_body_repository.update(existing)
            return UpdateGoverningBodyOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update governing body: {e}")
            return UpdateGoverningBodyOutputDto(success=False, error_message=str(e))

    async def delete_governing_body(
        self, input_dto: DeleteGoverningBodyInputDto
    ) -> DeleteGoverningBodyOutputDto:
        """Delete a governing body."""
        try:
            # Check if governing body has associated conferences
            existing = await self.governing_body_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteGoverningBodyOutputDto(
                    success=False, error_message="開催主体が見つかりません。"
                )

            if hasattr(existing, "conference_count") and existing.conference_count > 0:
                return DeleteGoverningBodyOutputDto(
                    success=False,
                    error_message=f"この開催主体には{existing.conference_count}件の会議体が関連付けられています。削除するには、先に関連する会議体を削除する必要があります。",
                )

            await self.governing_body_repository.delete(input_dto.id)
            return DeleteGoverningBodyOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete governing body: {e}")
            return DeleteGoverningBodyOutputDto(success=False, error_message=str(e))

    def get_type_options(self) -> list[str]:
        """Get available type options for governing bodies."""
        return ["国", "都道府県", "市町村"]

    async def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for governing bodies."""
        try:
            # Get all governing bodies
            all_bodies = await self.governing_body_repository.get_all()
            # Generate SQL content
            seed_content = "-- Governing Bodies Seed Data\n"
            seed_content += "-- Generated from current database\n\n"
            seed_content += (
                "INSERT INTO governing_bodies "
                "(id, name, type, organization_code, organization_type) VALUES\n"
            )

            values: list[str] = []
            for gb in all_bodies:
                org_code = (
                    f"'{gb.organization_code}'" if gb.organization_code else "NULL"
                )
                org_type = (
                    f"'{gb.organization_type}'" if gb.organization_type else "NULL"
                )
                values.append(
                    f"    ({gb.id}, '{gb.name}', '{gb.type}', {org_code}, {org_type})"
                )

            seed_content += ",\n".join(values) + "\n"
            seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
            seed_content += "    name = EXCLUDED.name,\n"
            seed_content += "    type = EXCLUDED.type,\n"
            seed_content += "    organization_code = EXCLUDED.organization_code,\n"
            seed_content += "    organization_type = EXCLUDED.organization_type;\n"

            # Save to file
            file_path = "database/seed_governing_bodies_generated.sql"
            with open(file_path, "w") as f:
                f.write(seed_content)

            return GenerateSeedFileOutputDto(
                success=True, seed_content=seed_content, file_path=file_path
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
