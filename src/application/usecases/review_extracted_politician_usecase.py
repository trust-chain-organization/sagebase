"""Use case for reviewing extracted politicians."""

import logging

from src.application.dtos.review_extracted_politician_dto import (
    BulkReviewInputDTO,
    BulkReviewOutputDTO,
    ExtractedPoliticianFilterDTO,
    ExtractedPoliticianStatisticsDTO,
    ReviewExtractedPoliticianInputDTO,
    ReviewExtractedPoliticianOutputDTO,
    UpdateExtractedPoliticianInputDTO,
    UpdateExtractedPoliticianOutputDTO,
)
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository,
)
from src.domain.repositories.political_party_repository import PoliticalPartyRepository


logger = logging.getLogger(__name__)


class ReviewExtractedPoliticianUseCase:
    """Use case for reviewing extracted politicians.

    This use case handles the review process for extracted politicians,
    including approval, rejection, and marking for re-review.
    """

    def __init__(
        self,
        extracted_politician_repository: ExtractedPoliticianRepository,
        party_repository: PoliticalPartyRepository,
    ):
        """Initialize the review use case.

        Args:
            extracted_politician_repository: Repository for extracted politicians
            party_repository: Repository for political parties
        """
        self.extracted_politician_repo = extracted_politician_repository
        self.party_repo = party_repository

    async def review_politician(
        self, request: ReviewExtractedPoliticianInputDTO
    ) -> ReviewExtractedPoliticianOutputDTO:
        """Review a single extracted politician.

        Args:
            request: Input DTO containing politician ID and action

        Returns:
            Output DTO with review result
        """
        try:
            # Get the politician
            politician = await self.extracted_politician_repo.get_by_id(
                request.politician_id
            )
            if not politician:
                return ReviewExtractedPoliticianOutputDTO(
                    success=False,
                    politician_id=request.politician_id,
                    name="",
                    new_status="",
                    message=f"Politician with ID {request.politician_id} not found",
                )

            # Validate action
            if request.action not in ["approve", "reject", "review"]:
                return ReviewExtractedPoliticianOutputDTO(
                    success=False,
                    politician_id=request.politician_id,
                    name=politician.name,
                    new_status=politician.status,
                    message=f"Invalid action: {request.action}",
                )

            # Determine new status
            status_map = {
                "approve": "approved",
                "reject": "rejected",
                "review": "reviewed",
            }
            new_status = status_map[request.action]

            # Update status
            updated_politician = await self.extracted_politician_repo.update_status(
                request.politician_id, new_status, request.reviewer_id
            )

            if updated_politician:
                action_past = {
                    "approve": "approved",
                    "reject": "rejected",
                    "review": "reviewed",
                }
                return ReviewExtractedPoliticianOutputDTO(
                    success=True,
                    politician_id=request.politician_id,
                    name=updated_politician.name,
                    new_status=updated_politician.status,
                    message=(
                        f"Successfully {action_past[request.action]} politician: "
                        f"{updated_politician.name}"
                    ),
                )
            else:
                return ReviewExtractedPoliticianOutputDTO(
                    success=False,
                    politician_id=request.politician_id,
                    name=politician.name,
                    new_status=politician.status,
                    message=f"Failed to update status for {politician.name}",
                )

        except Exception as e:
            logger.error(f"Error reviewing politician {request.politician_id}: {e}")
            return ReviewExtractedPoliticianOutputDTO(
                success=False,
                politician_id=request.politician_id,
                name="",
                new_status="",
                message=f"Error: {str(e)}",
            )

    async def bulk_review(self, request: BulkReviewInputDTO) -> BulkReviewOutputDTO:
        """Review multiple extracted politicians at once.

        Args:
            request: Input DTO containing politician IDs and action

        Returns:
            Output DTO with bulk review results
        """
        results: list[ReviewExtractedPoliticianOutputDTO] = []
        successful_count = 0
        failed_count = 0

        for politician_id in request.politician_ids:
            result = await self.review_politician(
                ReviewExtractedPoliticianInputDTO(
                    politician_id=politician_id,
                    action=request.action,
                    reviewer_id=request.reviewer_id,
                )
            )
            results.append(result)
            if result.success:
                successful_count += 1
            else:
                failed_count += 1

        total_processed = len(request.politician_ids)
        message = (
            f"Processed {total_processed} politicians: "
            f"{successful_count} succeeded, {failed_count} failed"
        )

        return BulkReviewOutputDTO(
            total_processed=total_processed,
            successful_count=successful_count,
            failed_count=failed_count,
            results=results,
            message=message,
        )

    async def get_filtered_politicians(
        self, filter_dto: ExtractedPoliticianFilterDTO
    ) -> list[PoliticianPartyExtractedPolitician]:
        """Get filtered list of extracted politicians.

        Uses database-level filtering for better performance.

        Args:
            filter_dto: DTO containing filter criteria

        Returns:
            List of filtered extracted politicians
        """
        return await self.extracted_politician_repo.get_filtered(
            statuses=filter_dto.statuses,
            party_id=filter_dto.party_id,
            start_date=filter_dto.start_date,
            end_date=filter_dto.end_date,
            search_name=filter_dto.search_name,
            limit=filter_dto.limit,
            offset=filter_dto.offset,
        )

    async def get_statistics(self) -> ExtractedPoliticianStatisticsDTO:
        """Get statistics for extracted politicians.

        Returns:
            Statistics DTO with counts by status and party
        """
        # Get status summary
        status_summary = await self.extracted_politician_repo.get_summary_by_status()

        # Get all parties for party statistics
        parties = await self.party_repo.get_all()
        party_statistics: dict[str, dict[str, int]] = {}

        for party in parties:
            if party.id:
                stats = await self.extracted_politician_repo.get_statistics_by_party(
                    party.id
                )
                if stats["total"] > 0:  # Only include parties with data
                    party_statistics[party.name] = stats

        return ExtractedPoliticianStatisticsDTO(
            total=sum(status_summary.values()),
            pending_count=status_summary.get("pending", 0),
            reviewed_count=status_summary.get("reviewed", 0),
            approved_count=status_summary.get("approved", 0),
            rejected_count=status_summary.get("rejected", 0),
            converted_count=status_summary.get("converted", 0),
            party_statistics=party_statistics,
        )

    async def get_all_parties(self) -> list[PoliticalParty]:
        """Get all political parties for selection.

        Returns:
            List of all political parties
        """
        return await self.party_repo.get_all()

    async def update_politician(
        self, request: UpdateExtractedPoliticianInputDTO
    ) -> UpdateExtractedPoliticianOutputDTO:
        """Update an extracted politician's information.

        Args:
            request: Input DTO with politician ID and updated fields

        Returns:
            Output DTO with update result
        """
        try:
            # Get the politician
            politician = await self.extracted_politician_repo.get_by_id(
                request.politician_id
            )
            if not politician:
                return UpdateExtractedPoliticianOutputDTO(
                    success=False,
                    politician_id=request.politician_id,
                    message=f"Politician with ID {request.politician_id} not found",
                )

            # Update fields
            politician.name = request.name
            politician.party_id = request.party_id
            politician.district = request.district
            politician.profile_url = request.profile_url

            # Save updates
            updated = await self.extracted_politician_repo.update(politician)
            if updated:
                return UpdateExtractedPoliticianOutputDTO(
                    success=True,
                    politician_id=request.politician_id,
                    message=f"Successfully updated politician: {request.name}",
                )
            else:
                return UpdateExtractedPoliticianOutputDTO(
                    success=False,
                    politician_id=request.politician_id,
                    message=f"Failed to update politician ID {request.politician_id}",
                )

        except Exception as e:
            logger.error(f"Error updating politician {request.politician_id}: {e}")
            return UpdateExtractedPoliticianOutputDTO(
                success=False,
                politician_id=request.politician_id,
                message=f"Error: {str(e)}",
            )
