"""Infrastructure implementation of party member extraction service.

This adapter wraps the legacy PartyMemberExtractor to provide extraction
capabilities through the domain interface.
"""

import logging

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.party_member_extraction_service import (
    ExtractedMember,
    IPartyMemberExtractionService,
    MemberExtractionResult,
)
from src.interfaces.factories.party_member_extractor_factory import (
    PartyMemberExtractorFactory,
)


logger = logging.getLogger(__name__)


class PartyMemberExtractionServiceImpl(IPartyMemberExtractionService):
    """Infrastructure implementation using legacy PartyMemberExtractor.

    This adapter allows infrastructure nodes to use member extraction
    through the domain interface without directly depending on legacy modules.
    """

    def __init__(self, llm_service: ILLMService, party_id: int | None = None):
        """Initialize the extraction service.

        Args:
            llm_service: LLM service for extraction
            party_id: Optional party ID for tracking
        """
        self._llm_service = llm_service
        self._party_id = party_id

    async def extract_from_html(
        self,
        html_content: str,
        source_url: str,
        party_name: str,
    ) -> MemberExtractionResult:
        """Extract party members from HTML content.

        Args:
            html_content: Raw HTML content to analyze
            source_url: URL where the content was fetched from
            party_name: Name of the political party

        Returns:
            MemberExtractionResult containing extracted members and metadata

        Raises:
            ValueError: If html_content or party_name is empty
        """
        if not html_content:
            raise ValueError("html_content cannot be empty")
        if not party_name:
            raise ValueError("party_name cannot be empty")

        logger.debug(f"Extracting members from {source_url}")

        try:
            # Create extractor instance (BAML)
            extractor = PartyMemberExtractorFactory.create(
                llm_service=self._llm_service,
            )

            # Use new Clean Architecture extractor's extract_from_html method
            result_dto = await extractor.extract_from_html(
                html_content, source_url, party_name
            )

            if result_dto.error or not result_dto.extracted_members:
                logger.info(f"No members extracted from {source_url}")
                return MemberExtractionResult(
                    members=[],
                    source_url=source_url,
                    extraction_successful=True,
                    error_message=None,
                )

            # Convert DTO to domain model
            extracted_members = [
                ExtractedMember(
                    name=member.name,
                    position=member.position,
                    electoral_district=member.electoral_district,
                    prefecture=member.prefecture,
                    profile_url=member.profile_url,
                    party_position=member.party_position,
                )
                for member in result_dto.extracted_members
            ]

            logger.info(f"Extracted {len(extracted_members)} members from {source_url}")

            return MemberExtractionResult(
                members=extracted_members,
                source_url=source_url,
                extraction_successful=True,
                error_message=None,
            )

        except Exception as e:
            logger.error(
                f"Error extracting members from {source_url}: {e}",
                exc_info=True,
            )
            return MemberExtractionResult(
                members=[],
                source_url=source_url,
                extraction_successful=False,
                error_message=str(e),
            )
