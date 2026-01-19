"""Adapter to make async LLM service work in sync context."""

import asyncio

from collections.abc import Coroutine
from typing import Any, TypeVar

from src.application.dtos.base_dto import PoliticianBaseDTO
from src.domain.entities.llm_processing_history import LLMProcessingHistory
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
)


T = TypeVar("T")


class LLMServiceAdapter:
    """Adapter to make async LLM service work synchronously."""

    def __init__(self, llm_service: ILLMService):
        """Initialize the adapter.

        Args:
            llm_service: The async LLM service to wrap
        """
        self._llm_service = llm_service
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._llm_service.model_name

    @property
    def temperature(self) -> float:
        """Get the temperature."""
        return self._llm_service.temperature

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return getattr(self._llm_service, "api_key", "")

    @property
    def llm(self) -> Any:
        """Get the underlying LLM instance.

        Returns:
            The LangChain LLM instance from the wrapped service
        """
        return getattr(self._llm_service, "llm", None)

    def _run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async function in sync context.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        try:
            loop = asyncio.get_event_loop()
            # Check if the loop is closed and create a new one if needed
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # No event loop in current thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def set_history_repository(
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        """Set the history repository for recording LLM operations.

        Args:
            repository: History repository instance or None to disable recording
        """
        self._run_async(self._llm_service.set_history_repository(repository))

    def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        """Get processing history for this service.

        Args:
            reference_type: Optional filter by reference type
            reference_id: Optional filter by reference ID

        Returns:
            List of processing history entries
        """
        return self._run_async(
            self._llm_service.get_processing_history(reference_type, reference_id)
        )

    def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from text using LLM.

        Args:
            text: The text to extract speeches from

        Returns:
            List of extracted speeches with speaker and content
        """
        return self._run_async(self._llm_service.extract_speeches_from_text(text))

    def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party members from HTML content.

        Args:
            html_content: The HTML content to extract from
            party_id: ID of the political party

        Returns:
            Extraction result with member information
        """
        return self._run_async(
            self._llm_service.extract_party_members(html_content, party_id)
        )

    def match_conference_member(
        self,
        member_name: str,
        party_name: str | None,
        candidates: list[PoliticianBaseDTO],
    ) -> LLMMatchResult | None:
        """Match a conference member to a politician.

        Args:
            member_name: Name of the member
            party_name: Optional party name
            candidates: List of candidate politicians

        Returns:
            Matching result with politician_id and confidence score
        """
        return self._run_async(
            self._llm_service.match_conference_member(
                member_name, party_name, candidates
            )
        )

    def set_input_reference(self, reference_type: str, reference_id: int) -> None:
        """Set input reference for history tracking.

        Args:
            reference_type: Type of reference (e.g., 'speaker', 'meeting')
            reference_id: ID of the referenced entity
        """
        # Check if the wrapped service has this method
        if hasattr(self._llm_service, "set_input_reference"):
            # Call it directly if it's a sync method
            self._llm_service.set_input_reference(  # type: ignore[attr-defined]
                reference_type, reference_id
            )

    def get_structured_llm(self, schema: Any) -> Any:
        """Get a structured LLM instance configured with the given schema.

        Args:
            schema: Pydantic model or schema definition

        Returns:
            Configured LLM instance
        """
        return self._llm_service.get_structured_llm(schema)

    def get_prompt(self, prompt_name: str) -> Any:
        """Get a prompt template by name.

        Args:
            prompt_name: Name identifier of the prompt

        Returns:
            Prompt template instance
        """
        return self._llm_service.get_prompt(prompt_name)

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Invoke an LLM chain with retry logic.

        Args:
            chain: LangChain runnable to invoke
            inputs: Input dictionary for the chain

        Returns:
            Result from the chain invocation
        """
        return self._llm_service.invoke_with_retry(chain, inputs)

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Invoke the LLM with messages and return the response content.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            The response content from the LLM
        """
        return self._llm_service.invoke_llm(messages)
