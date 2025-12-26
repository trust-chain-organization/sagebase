"""Use cases for viewing data coverage statistics."""

import logging
import re

from src.application.dtos.data_coverage_dto import (
    ActivityTrendDataDTO,
    GoverningBodyCoverageOutputDTO,
    MeetingCoverageOutputDTO,
    SpeakerMatchingStatsOutputDTO,
    ViewActivityTrendInputDTO,
)
from src.domain.repositories.data_coverage_repository import IDataCoverageRepository


logger = logging.getLogger(__name__)

# Valid period format pattern: number followed by unit (d/D, m/M, y/Y)
PERIOD_PATTERN = re.compile(r"^\d+[dDmMyY]$")


class ViewGoverningBodyCoverageUseCase:
    """Use case for viewing governing body coverage statistics.

    This use case retrieves statistics about governing body coverage,
    including the total number of governing bodies, those with conferences,
    those with meetings, and the overall coverage percentage.
    """

    def __init__(self, data_coverage_repo: IDataCoverageRepository) -> None:
        """Initialize the use case.

        Args:
            data_coverage_repo: Data coverage repository
        """
        self._data_coverage_repo = data_coverage_repo

    async def execute(self) -> GoverningBodyCoverageOutputDTO:
        """Get governing body coverage statistics.

        Returns:
            GoverningBodyCoverageOutputDTO: Statistics about governing body coverage

        Raises:
            Exception: If there's an error retrieving the statistics
        """
        try:
            logger.info("Retrieving governing body coverage statistics")
            stats = await self._data_coverage_repo.get_governing_body_stats()

            result: GoverningBodyCoverageOutputDTO = {
                "total": stats["total"],
                "with_conferences": stats["with_conferences"],
                "with_meetings": stats["with_meetings"],
                "coverage_percentage": stats["coverage_percentage"],
            }

            logger.info(
                "Retrieved governing body coverage statistics: "
                f"total={result['total']}, "
                f"with_conferences={result['with_conferences']}, "
                f"with_meetings={result['with_meetings']}, "
                f"coverage_percentage={result['coverage_percentage']:.2f}%"
            )

            return result

        except Exception as e:
            logger.error(f"Error retrieving governing body coverage statistics: {e}")
            raise


class ViewMeetingCoverageUseCase:
    """Use case for viewing meeting coverage statistics.

    This use case retrieves statistics about meetings, including the total
    number of meetings, those with minutes, those with conversations, and
    the average number of conversations per meeting.
    """

    def __init__(self, data_coverage_repo: IDataCoverageRepository) -> None:
        """Initialize the use case.

        Args:
            data_coverage_repo: Data coverage repository
        """
        self._data_coverage_repo = data_coverage_repo

    async def execute(self) -> MeetingCoverageOutputDTO:
        """Get meeting coverage statistics.

        Returns:
            MeetingCoverageOutputDTO: Statistics about meeting coverage

        Raises:
            Exception: If there's an error retrieving the statistics
        """
        try:
            logger.info("Retrieving meeting coverage statistics")
            stats = await self._data_coverage_repo.get_meeting_stats()

            result: MeetingCoverageOutputDTO = {
                "total_meetings": stats["total_meetings"],
                "with_minutes": stats["with_minutes"],
                "with_conversations": stats["with_conversations"],
                "average_conversations_per_meeting": stats[
                    "average_conversations_per_meeting"
                ],
                "meetings_by_conference": stats["meetings_by_conference"],
            }

            logger.info(
                "Retrieved meeting coverage statistics: "
                f"total_meetings={result['total_meetings']}, "
                f"with_minutes={result['with_minutes']}, "
                f"with_conversations={result['with_conversations']}, "
                f"avg_conversations={result['average_conversations_per_meeting']:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error retrieving meeting coverage statistics: {e}")
            raise


class ViewSpeakerMatchingStatsUseCase:
    """Use case for viewing speaker matching statistics.

    This use case retrieves statistics about speaker-politician matching,
    including match rates and conversation linkage rates.
    """

    def __init__(self, data_coverage_repo: IDataCoverageRepository) -> None:
        """Initialize the use case.

        Args:
            data_coverage_repo: Data coverage repository
        """
        self._data_coverage_repo = data_coverage_repo

    async def execute(self) -> SpeakerMatchingStatsOutputDTO:
        """Get speaker matching statistics.

        Returns:
            SpeakerMatchingStatsOutputDTO: Statistics about speaker matching

        Raises:
            Exception: If there's an error retrieving the statistics
        """
        try:
            logger.info("Retrieving speaker matching statistics")
            stats = await self._data_coverage_repo.get_speaker_matching_stats()

            result: SpeakerMatchingStatsOutputDTO = {
                "total_speakers": stats["total_speakers"],
                "matched_speakers": stats["matched_speakers"],
                "unmatched_speakers": stats["unmatched_speakers"],
                "matching_rate": stats["matching_rate"],
                "total_conversations": stats["total_conversations"],
                "linked_conversations": stats["linked_conversations"],
                "linkage_rate": stats["linkage_rate"],
            }

            logger.info(
                "Retrieved speaker matching statistics: "
                f"total_speakers={result['total_speakers']}, "
                f"matched_speakers={result['matched_speakers']}, "
                f"matching_rate={result['matching_rate']:.2f}%, "
                f"linkage_rate={result['linkage_rate']:.2f}%"
            )

            return result

        except Exception as e:
            logger.error(f"Error retrieving speaker matching statistics: {e}")
            raise


class ViewActivityTrendUseCase:
    """Use case for viewing activity trend data.

    This use case retrieves activity trend data for a specified period,
    including daily counts of meetings, conversations, speakers, and politicians.
    """

    def __init__(self, data_coverage_repo: IDataCoverageRepository) -> None:
        """Initialize the use case.

        Args:
            data_coverage_repo: Data coverage repository
        """
        self._data_coverage_repo = data_coverage_repo

    async def execute(
        self, input_dto: ViewActivityTrendInputDTO
    ) -> list[ActivityTrendDataDTO]:
        """Get activity trend data for a specified period.

        Args:
            input_dto: Input DTO containing period specification

        Returns:
            list[ActivityTrendDataDTO]: List of daily activity data points

        Raises:
            ValueError: If the period format is invalid
            Exception: If there's an error retrieving the statistics
        """
        period = input_dto["period"]

        # Validate period format
        if not PERIOD_PATTERN.match(period):
            error_msg = (
                f"Invalid period format: '{period}'. "
                f"Expected format: number followed by unit (e.g., '7d', '30d', '90d')"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            logger.info(f"Retrieving activity trend data for period: {period}")

            trend_data = await self._data_coverage_repo.get_activity_trend(period)

            result: list[ActivityTrendDataDTO] = [
                {
                    "date": data["date"],
                    "meetings_count": data["meetings_count"],
                    "conversations_count": data["conversations_count"],
                    "speakers_count": data["speakers_count"],
                    "politicians_count": data["politicians_count"],
                }
                for data in trend_data
            ]

            logger.info(
                f"Retrieved activity trend data: "
                f"{len(result)} data points for period {period}"
            )

            return result

        except Exception as e:
            logger.error(f"Error retrieving activity trend data: {e}")
            raise
