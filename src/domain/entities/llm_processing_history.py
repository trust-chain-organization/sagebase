"""LLM processing history entity."""

from datetime import datetime
from enum import Enum
from typing import Any

from src.domain.entities.base import BaseEntity


class ProcessingType(Enum):
    """Types of LLM processing."""

    MINUTES_DIVISION = "minutes_division"
    SPEECH_EXTRACTION = "speech_extraction"
    # SPEAKER_MATCHING is deprecated and kept only for backward compatibility
    # with existing historical records. Do not use for new processing.
    SPEAKER_MATCHING = "speaker_matching"
    POLITICIAN_EXTRACTION = "politician_extraction"
    CONFERENCE_MEMBER_MATCHING = "conference_member_matching"
    PARLIAMENTARY_GROUP_EXTRACTION = "parliamentary_group_extraction"


class ProcessingStatus(Enum):
    """Status of LLM processing."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProcessingHistory(BaseEntity):
    """Entity to track LLM processing history."""

    def __init__(
        self,
        processing_type: ProcessingType,
        model_name: str,
        model_version: str,
        prompt_template: str,
        prompt_variables: dict[str, Any],
        input_reference_type: str,
        input_reference_id: int,
        status: ProcessingStatus = ProcessingStatus.PENDING,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
        processing_metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        created_by: str | None = None,
        id: int | None = None,
    ) -> None:
        """Initialize LLM processing history.

        Args:
            processing_type: Type of processing being performed
            model_name: Name of the LLM model (e.g., "gemini-2.0-flash")
            model_version: Version of the model
            prompt_template: The prompt template used
            prompt_variables: Variables substituted in the prompt
            input_reference_type: Type of entity being processed
                (e.g., "meeting", "speaker")
            input_reference_id: ID of the entity being processed
            status: Current status of the processing
            result: Processing result (if completed)
            error_message: Error message (if failed)
            processing_metadata: Additional metadata about the processing
                (e.g., token_count_input, token_count_output, processing_time_ms)
            started_at: When processing started
            completed_at: When processing completed
            created_by: User or system that initiated the processing
            id: Entity ID
        """
        super().__init__(id)
        self.processing_type = processing_type
        self.model_name = model_name
        self.model_version = model_version
        self.prompt_template = prompt_template
        self.prompt_variables = prompt_variables or {}
        self.input_reference_type = input_reference_type
        self.input_reference_id = input_reference_id
        self.status = status
        self.result = result
        self.error_message = error_message
        self.processing_metadata = processing_metadata or {}
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_by = created_by or "system"

    def start_processing(self) -> None:
        """Mark processing as started."""
        self.status = ProcessingStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete_processing(self, result: dict[str, Any]) -> None:
        """Mark processing as completed with result."""
        self.status = ProcessingStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def fail_processing(self, error_message: str) -> None:
        """Mark processing as failed with error."""
        self.status = ProcessingStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

    @property
    def processing_duration_seconds(self) -> float | None:
        """Calculate processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def token_count_input(self) -> int | None:
        """Get input token count from metadata."""
        return self.processing_metadata.get("token_count_input")

    @property
    def token_count_output(self) -> int | None:
        """Get output token count from metadata."""
        return self.processing_metadata.get("token_count_output")

    @property
    def processing_time_ms(self) -> int | None:
        """Get processing time in milliseconds from metadata."""
        return self.processing_metadata.get("processing_time_ms")

    def __str__(self) -> str:
        return (
            f"LLMProcessingHistory(type={self.processing_type.value}, "
            f"model={self.model_name}, status={self.status.value})"
        )
