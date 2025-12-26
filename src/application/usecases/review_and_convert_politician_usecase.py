"""Composite use case for reviewing and optionally converting politicians."""

import logging

from src.application.dtos.convert_extracted_politician_dto import (
    ConvertExtractedPoliticianInputDTO,
)
from src.application.dtos.review_extracted_politician_dto import (
    ReviewExtractedPoliticianInputDTO,
    ReviewExtractedPoliticianOutputDTO,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.domain.repositories.extracted_politician_repository import (
    ExtractedPoliticianRepository,
)


logger = logging.getLogger(__name__)


class ReviewAndConvertPoliticianUseCase:
    """Composite use case that handles review with optional auto-conversion.

    This use case orchestrates the workflow of reviewing a politician
    and automatically converting them if approved. This keeps the
    workflow logic in the Application layer rather than in the Presenter.
    """

    def __init__(
        self,
        review_use_case: ReviewExtractedPoliticianUseCase,
        convert_use_case: ConvertExtractedPoliticianUseCase,
        extracted_politician_repository: ExtractedPoliticianRepository,
    ):
        """Initialize the composite use case.

        Args:
            review_use_case: Use case for reviewing politicians
            convert_use_case: Use case for converting politicians
            extracted_politician_repository: Repository for extracted politicians
        """
        self.review_use_case = review_use_case
        self.convert_use_case = convert_use_case
        self.extracted_politician_repo = extracted_politician_repository

    async def review_with_auto_convert(
        self, request: ReviewExtractedPoliticianInputDTO, auto_convert: bool = True
    ) -> ReviewExtractedPoliticianOutputDTO:
        """Review politician and optionally auto-convert if approved.

        Args:
            request: Input DTO for reviewing the politician
            auto_convert: Whether to automatically convert if approved

        Returns:
            Output DTO with review result and conversion status
        """
        # Review first
        result = await self.review_use_case.review_politician(request)

        # Auto-convert if approved and requested
        if result.success and request.action == "approve" and auto_convert:
            try:
                # Get the politician to find their party_id
                politician = await self.extracted_politician_repo.get_by_id(
                    request.politician_id
                )

                if politician and politician.party_id:
                    # Use the convert use case for single politician
                    # Note: The use case processes approved politicians by party
                    convert_input = ConvertExtractedPoliticianInputDTO(
                        party_id=politician.party_id,
                        batch_size=1,
                        dry_run=False,
                    )
                    convert_result = await self.convert_use_case.execute(convert_input)

                    if convert_result.converted_count > 0:
                        result.message += " and converted to politician"
                    else:
                        result.message += " (auto-conversion failed)"
                else:
                    logger.warning(
                        f"Cannot auto-convert politician {request.politician_id}: "
                        "politician not found or missing party_id"
                    )
                    result.message += " (auto-conversion skipped: no party)"

            except Exception as e:
                logger.warning(
                    f"Failed to auto-convert politician {request.politician_id}: {e}"
                )
                result.message += " (auto-conversion failed)"

        return result
