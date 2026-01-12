"""Use case for managing politicians."""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities import Politician
from src.domain.repositories.politician_repository import PoliticianRepository


logger = get_logger(__name__)


@dataclass
class PoliticianListInputDto:
    """Input DTO for listing politicians."""

    party_id: int | None = None
    search_name: str | None = None


@dataclass
class PoliticianListOutputDto:
    """Output DTO for listing politicians."""

    politicians: list[Politician]


@dataclass
class CreatePoliticianInputDto:
    """Input DTO for creating a politician."""

    name: str
    prefecture: str
    district: str
    party_id: int | None = None
    profile_url: str | None = None


@dataclass
class CreatePoliticianOutputDto:
    """Output DTO for creating a politician."""

    success: bool
    politician_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdatePoliticianInputDto:
    """Input DTO for updating a politician."""

    id: int
    name: str
    prefecture: str
    district: str
    party_id: int | None = None
    profile_url: str | None = None


@dataclass
class UpdatePoliticianOutputDto:
    """Output DTO for updating a politician."""

    success: bool
    error_message: str | None = None


@dataclass
class DeletePoliticianInputDto:
    """Input DTO for deleting a politician."""

    id: int


@dataclass
class DeletePoliticianOutputDto:
    """Output DTO for deleting a politician."""

    success: bool
    error_message: str | None = None


@dataclass
class MergePoliticiansInputDto:
    """Input DTO for merging politicians."""

    source_id: int
    target_id: int


@dataclass
class MergePoliticiansOutputDto:
    """Output DTO for merging politicians."""

    success: bool
    error_message: str | None = None


class ManagePoliticiansUseCase:
    """Use case for managing politicians."""

    def __init__(self, politician_repository: PoliticianRepository):
        """Initialize the use case.

        Args:
            politician_repository: Repository instance (can be sync or async)
        """
        self.politician_repository = politician_repository

    async def list_politicians(
        self, input_dto: PoliticianListInputDto
    ) -> PoliticianListOutputDto:
        """List politicians with optional filters."""
        try:
            if input_dto.search_name:
                politicians = await self.politician_repository.search_by_name(
                    input_dto.search_name
                )
            elif input_dto.party_id:
                politicians = await self.politician_repository.get_by_party(
                    input_dto.party_id
                )
            else:
                politicians = await self.politician_repository.get_all()

            return PoliticianListOutputDto(politicians=politicians)
        except Exception as e:
            logger.error(f"Failed to list politicians: {e}")
            raise

    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        """Create a new politician."""
        try:
            # Check for duplicates
            existing = await self.politician_repository.get_by_name_and_party(
                input_dto.name, input_dto.party_id
            )
            if existing:
                return CreatePoliticianOutputDto(
                    success=False,
                    error_message="同じ名前と政党の政治家が既に存在します。",
                )

            # Create new politician
            politician = Politician(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                prefecture=input_dto.prefecture,
                political_party_id=input_dto.party_id,
                district=input_dto.district,
                profile_page_url=input_dto.profile_url,
            )

            created = await self.politician_repository.create(politician)
            return CreatePoliticianOutputDto(success=True, politician_id=created.id)
        except Exception as e:
            logger.error(f"Failed to create politician: {e}")
            return CreatePoliticianOutputDto(success=False, error_message=str(e))

    async def update_politician(
        self, input_dto: UpdatePoliticianInputDto
    ) -> UpdatePoliticianOutputDto:
        """Update an existing politician."""
        try:
            # Get existing politician
            existing = await self.politician_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdatePoliticianOutputDto(
                    success=False, error_message="政治家が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            existing.prefecture = input_dto.prefecture
            existing.political_party_id = input_dto.party_id
            existing.district = input_dto.district
            existing.profile_page_url = input_dto.profile_url

            await self.politician_repository.update(existing)
            return UpdatePoliticianOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update politician: {e}")
            return UpdatePoliticianOutputDto(success=False, error_message=str(e))

    async def delete_politician(
        self, input_dto: DeletePoliticianInputDto
    ) -> DeletePoliticianOutputDto:
        """Delete a politician."""
        try:
            # Check if politician exists
            existing = await self.politician_repository.get_by_id(input_dto.id)
            if not existing:
                return DeletePoliticianOutputDto(
                    success=False, error_message="政治家が見つかりません。"
                )

            await self.politician_repository.delete(input_dto.id)
            return DeletePoliticianOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete politician: {e}")
            return DeletePoliticianOutputDto(success=False, error_message=str(e))

    async def merge_politicians(
        self, input_dto: MergePoliticiansInputDto
    ) -> MergePoliticiansOutputDto:
        """Merge two politicians."""
        try:
            # Check if both politicians exist
            source = await self.politician_repository.get_by_id(input_dto.source_id)
            target = await self.politician_repository.get_by_id(input_dto.target_id)

            if not source:
                return MergePoliticiansOutputDto(
                    success=False, error_message="マージ元の政治家が見つかりません。"
                )
            if not target:
                return MergePoliticiansOutputDto(
                    success=False, error_message="マージ先の政治家が見つかりません。"
                )

            # TODO: Implement actual merge logic
            # This would involve updating all references from source to target
            # and then deleting the source

            return MergePoliticiansOutputDto(
                success=False, error_message="マージ機能は現在実装中です。"
            )
        except Exception as e:
            logger.error(f"Failed to merge politicians: {e}")
            return MergePoliticiansOutputDto(success=False, error_message=str(e))
