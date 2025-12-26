"""Instrumented LLM Service with automatic history recording."""

import asyncio
import inspect
import logging
from collections.abc import Callable
from datetime import UTC
from typing import Any

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
    PoliticianDTO,
)


logger = logging.getLogger(__name__)


class InstrumentedLLMService(ILLMService):
    """Decorator for LLM services that adds automatic history recording."""

    def __init__(
        self,
        llm_service: ILLMService,
        history_repository: LLMProcessingHistoryRepository | None = None,
        prompt_repository: PromptVersionRepository | None = None,
        model_name: str = "unknown",
        model_version: str = "unknown",
        input_reference_type: str | None = None,
        input_reference_id: int | None = None,
    ):
        """Initialize instrumented LLM service.

        Args:
            llm_service: The underlying LLM service to wrap
            history_repository: Repository for storing processing history
            prompt_repository: Repository for prompt version management
            model_name: Name of the LLM model
            model_version: Version of the LLM model
        """
        self._llm_service = llm_service
        self._history_repository = history_repository
        self._prompt_repository = prompt_repository
        self._model_name = model_name
        self._model_version = model_version
        self._input_reference_type = input_reference_type
        self._input_reference_id = input_reference_id

        # Required attributes for ILLMService protocol
        self.temperature = self._llm_service.temperature
        self.model_name = self._model_name

    def set_input_reference(
        self, reference_type: str | None, reference_id: int | None
    ) -> None:
        """Set the input reference for history tracking.

        Args:
            reference_type: Type of reference (e.g., 'meeting')
            reference_id: ID of the reference
        """
        self._input_reference_type = reference_type
        self._input_reference_id = reference_id

    def set_history_repository(  # type: ignore[override]
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        """Set the history repository for recording LLM operations."""
        self._history_repository = repository

    def get_processing_history(  # type: ignore[override]
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        """Get processing history for this service."""
        if not self._history_repository:
            return []

        if reference_type and reference_id:
            return self._history_repository.get_by_input_reference(  # type: ignore[attr-defined]
                reference_type, reference_id
            )
        return []

    async def _record_processing(
        self,
        processing_type: ProcessingType,
        input_reference_type: str,
        input_reference_id: int,
        prompt_template: str,
        prompt_variables: dict[str, Any],
        processing_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Record LLM processing with history tracking.

        Args:
            processing_type: Type of processing
            input_reference_type: Type of entity being processed
            input_reference_id: ID of entity being processed
            prompt_template: Template used for the prompt
            prompt_variables: Variables used in the prompt
            processing_func: The actual processing function to call
            *args: Arguments for the processing function
            **kwargs: Keyword arguments for the processing function

        Returns:
            Result from the processing function
        """
        # Create history entry
        history_entry = None
        if self._history_repository:
            history_entry = LLMProcessingHistory(
                processing_type=processing_type,
                model_name=self._model_name,
                model_version=self._model_version,
                prompt_template=prompt_template,
                prompt_variables=prompt_variables,
                input_reference_type=input_reference_type,
                input_reference_id=input_reference_id,
                status=ProcessingStatus.PENDING,
                processing_metadata={
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys()),
                },
            )
            history_entry.start_processing()

            try:
                # Save initial entry - handle async repository
                history_entry = await self._history_repository.create(history_entry)  # type: ignore[attr-defined]
            except Exception as e:
                logger.error(f"Failed to create history entry: {e}")
                history_entry = None

        try:
            # Execute the actual processing
            result = processing_func(*args, **kwargs)

            # Handle async processing function
            if inspect.iscoroutine(result):
                result = await result

            # Update history with success
            if history_entry and self._history_repository:
                # Extract result metadata
                result_metadata = self._extract_result_metadata(result)
                history_entry.complete_processing(result_metadata)

                # Handle async repository update
                await self._history_repository.update(history_entry)  # type: ignore[attr-defined]

            return result

        except Exception as e:
            # Update history with failure
            if history_entry and self._history_repository:
                history_entry.fail_processing(str(e))

                # Handle async repository update for failure
                await self._history_repository.update(history_entry)  # type: ignore[attr-defined]

            # Re-raise the exception
            raise

    def _extract_result_metadata(self, result: Any) -> dict[str, Any]:
        """Extract metadata from processing result.

        Args:
            result: The processing result

        Returns:
            Dictionary of metadata
        """
        metadata: dict[str, Any] = {"type": type(result).__name__}

        if isinstance(result, dict):
            # For dict results, include some key info
            metadata["keys"] = list(result.keys()) if result else []  # type: ignore[arg-type]
            if "matched" in result:
                metadata["matched"] = result["matched"]
            if "confidence" in result:
                metadata["confidence"] = result["confidence"]
            if "success" in result:
                metadata["success"] = result["success"]
        elif isinstance(result, list):
            metadata["count"] = len(result)  # type: ignore[arg-type]
        elif result is None:
            metadata["is_null"] = True

        return metadata

    async def match_speaker_to_politician(  # type: ignore[override]
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match a speaker to a politician using LLM with history recording."""
        # Extract prompt information
        prompt_template = "speaker_matching"  # This would be from prompt manager
        prompt_variables: dict[str, Any] = {
            "speaker_name": context.get("speaker_name", ""),
            "candidates_count": len(context.get("candidates", [])),
        }

        # Use configured reference if set via set_input_reference, else defaults
        reference_type = self._input_reference_type or "speaker"
        reference_id = self._input_reference_id
        if reference_id is None:
            # TypedDict doesn't have speaker_id, use speaker_name as reference
            reference_id = hash(context.get("speaker_name", "")) % 1000000

        return await self._record_processing(
            ProcessingType.SPEAKER_MATCHING,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.match_speaker_to_politician,
            context,
        )

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:  # type: ignore[override]
        """Extract speeches from meeting minutes text with history recording."""
        prompt_template = "speech_extraction"
        prompt_variables = {"text_length": len(text)}

        # Use configured reference type/id if available, otherwise use defaults
        reference_type = self._input_reference_type or "text"
        reference_id = (
            self._input_reference_id
            if self._input_reference_id is not None
            else hash(text[:100]) % 1000000  # Simple hash for tracking
        )

        return await self._record_processing(
            ProcessingType.SPEECH_EXTRACTION,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.extract_speeches_from_text,
            text,
        )

    async def process_minutes_division(
        self,
        processing_func: Callable[..., Any],
        prompt_name: str,
        prompt_variables: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Process minutes division operations with history recording."""
        # Use configured reference type/id if available
        reference_type = self._input_reference_type or "meeting"
        reference_id = self._input_reference_id or 0

        return await self._record_processing(
            ProcessingType.MINUTES_DIVISION,
            reference_type,
            reference_id,
            prompt_name,
            prompt_variables,
            processing_func,
            *args,
            **kwargs,
        )

    async def extract_party_members(  # type: ignore[override]
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party member information from HTML with history recording."""
        prompt_template = "party_member_extraction"
        prompt_variables = {"html_length": len(html_content), "party_id": party_id}

        reference_type = "party"
        reference_id = party_id

        return await self._record_processing(
            ProcessingType.POLITICIAN_EXTRACTION,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.extract_party_members,
            html_content,
            party_id,
        )

    async def match_conference_member(  # type: ignore[override]
        self, member_name: str, party_name: str | None, candidates: list[PoliticianDTO]
    ) -> LLMMatchResult | None:
        """Match a conference member to a politician with history recording."""
        prompt_template = "conference_member_matching"
        prompt_variables: dict[str, Any] = {
            "member_name": member_name,
            "party_name": party_name,
            "candidates_count": len(candidates),
        }

        # Use a hash of member name for reference
        reference_type = "conference_member"
        reference_id = hash(member_name) % 1000000

        return await self._record_processing(
            ProcessingType.CONFERENCE_MEMBER_MATCHING,
            reference_type,
            reference_id,
            prompt_template,
            prompt_variables,
            self._llm_service.match_conference_member,
            member_name,
            party_name,
            candidates,
        )

    # Delegation methods for ILLMService compatibility
    def get_structured_llm(self, schema: Any) -> Any:
        """Delegate to wrapped LLM service."""
        return self._llm_service.get_structured_llm(schema)

    def get_prompt(self, prompt_name: str) -> Any:
        """Delegate to wrapped LLM service."""
        return self._llm_service.get_prompt(prompt_name)

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Invoke chain with retry and history recording for minutes processing."""
        # If we have a history repository and this looks like minutes processing
        if self._history_repository and self._input_reference_type == "meeting":
            import uuid
            from datetime import datetime

            # Generate a process ID
            process_id = str(uuid.uuid4())

            # Determine processing type based on inputs
            processing_type = ProcessingType.MINUTES_DIVISION
            if "section_string" in inputs:
                processing_type = ProcessingType.SPEECH_EXTRACTION

            # Extract prompt info from chain if possible
            prompt_name = "minutes_division"
            if hasattr(chain, "first") and hasattr(chain.first, "template"):
                # Try to extract prompt name from template
                template_str = str(chain.first.template)
                if "speech" in template_str.lower():
                    prompt_name = "speech_extraction"

            # Create history record
            history = LLMProcessingHistory(
                processing_type=processing_type,
                model_name=self._model_name,
                model_version=self._model_version,
                prompt_template=prompt_name,
                prompt_variables=inputs,
                input_reference_type=self._input_reference_type or "meeting",
                input_reference_id=self._input_reference_id or 0,
                status=ProcessingStatus.IN_PROGRESS,
                started_at=datetime.now(UTC),
                processing_metadata={
                    "process_id": process_id,
                    "chain_type": type(chain).__name__,
                },
            )

            # Create history record - handle async repository
            create_result = self._history_repository.create(history)  # type: ignore[attr-defined]
            if inspect.iscoroutine(create_result):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    history = loop.run_until_complete(create_result)
                finally:
                    loop.close()
            else:
                history = create_result

            try:
                # Execute the actual processing
                result = self._llm_service.invoke_with_retry(chain, inputs)

                # Update history with success
                history.status = ProcessingStatus.COMPLETED
                history.completed_at = datetime.now(UTC)
                history.result = self._extract_result_metadata(result)

                # Update history - handle async repository
                update_result = self._history_repository.update(history)  # type: ignore[attr-defined]
                if inspect.iscoroutine(update_result):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(update_result)

                return result

            except Exception as e:
                # Update history with failure
                history.status = ProcessingStatus.FAILED
                history.completed_at = datetime.now(UTC)
                history.error_message = str(e)

                # Update history - handle async repository
                update_result = self._history_repository.update(history)  # type: ignore[attr-defined]
                if inspect.iscoroutine(update_result):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(update_result)

                raise

        # Fallback to simple delegation
        return self._llm_service.invoke_with_retry(chain, inputs)

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Delegate to wrapped LLM service."""
        return self._llm_service.invoke_llm(messages)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to wrapped service."""
        return getattr(self._llm_service, name)
