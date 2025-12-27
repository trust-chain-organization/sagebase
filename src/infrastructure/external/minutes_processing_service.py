"""Minutes processing service implementation wrapping MinutesProcessAgent."""

import structlog

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent


logger = structlog.get_logger(__name__)


class MinutesProcessAgentService(IMinutesProcessingService):
    """Service that wraps MinutesProcessAgent for Clean Architecture compliance.

    This service implements the IMinutesProcessingService interface and delegates
    to the MinutesProcessAgent for the actual processing logic. This allows the
    application layer to depend on a domain interface rather than directly on
    infrastructure code.
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize the minutes processing service.

        Args:
            llm_service: LLM service instance to use for processing
        """
        self.llm_service = llm_service
        self.agent = MinutesProcessAgent(llm_service=llm_service)

    async def process_minutes(self, original_minutes: str) -> list[SpeakerSpeech]:
        """Process meeting minutes text and extract speeches.

        This method wraps the synchronous MinutesProcessAgent and converts
        infrastructure-specific models to domain value objects.

        Args:
            original_minutes: Raw meeting minutes text content

        Returns:
            List of extracted speeches with speaker information as domain value objects.
            Empty speeches (with empty speaker or speech_content) are filtered out.

        Raises:
            ValueError: If processing fails or invalid input is provided
            TypeError: If the result format is invalid
        """
        # The agent's run method is now async
        infrastructure_results = await self.agent.run(original_minutes)

        # Filter out invalid results and convert to domain value objects
        domain_results: list[SpeakerSpeech] = []
        filtered_count = 0

        for result in infrastructure_results:
            # Skip entries with empty speaker or speech_content
            if not result.speaker or not result.speaker.strip():
                logger.warning(
                    "Skipping speech with empty speaker",
                    speech_order=result.speech_order,
                    chapter_number=result.chapter_number,
                )
                filtered_count += 1
                continue

            if not result.speech_content or not result.speech_content.strip():
                logger.warning(
                    "Skipping speech with empty content",
                    speaker=result.speaker,
                    speech_order=result.speech_order,
                    chapter_number=result.chapter_number,
                )
                filtered_count += 1
                continue

            # Create domain value object for valid speeches
            domain_results.append(
                SpeakerSpeech(
                    speaker=result.speaker,
                    speech_content=result.speech_content,
                    chapter_number=result.chapter_number,
                    sub_chapter_number=result.sub_chapter_number,
                    speech_order=result.speech_order,
                )
            )

        if filtered_count > 0:
            logger.info(
                "Filtered out invalid speeches",
                total_results=len(infrastructure_results),
                filtered_count=filtered_count,
                valid_count=len(domain_results),
            )

        return domain_results
