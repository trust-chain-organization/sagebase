"""LLM service interface definition for domain layer."""

from typing import Any, Protocol

from src.application.dtos.base_dto import PoliticianBaseDTO
from src.domain.entities.llm_processing_history import LLMProcessingHistory
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
)


class ILLMService(Protocol):
    """Interface for LLM services.

    This is a Protocol (interface) that defines the contract for LLM services.
    It belongs to the domain layer as it represents a core business capability.
    """

    model_name: str
    temperature: float

    async def set_history_repository(
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        """Set the history repository for recording LLM operations.

        Args:
            repository: History repository instance or None to disable recording
        """
        ...

    async def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        """Get processing history for this service.

        Args:
            reference_type: Optional filter by reference type
            reference_id: Optional filter by reference ID

        Returns:
            List of processing history entries
        """
        ...

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from meeting minutes text.

        Args:
            text: Meeting minutes text content

        Returns:
            List of speeches with speaker and content
        """
        ...

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party member information from HTML.

        Args:
            html_content: HTML content of party members page
            party_id: ID of the political party

        Returns:
            Extraction result with member information
        """
        ...

    async def match_conference_member(
        self,
        member_name: str,
        party_name: str | None,
        candidates: list[PoliticianBaseDTO],
    ) -> LLMMatchResult | None:
        """Match a conference member to a politician.

        Args:
            member_name: Name of the conference member
            party_name: Party affiliation if known
            candidates: List of candidate politicians

        Returns:
            Matching result with politician_id and confidence score
        """
        ...

    def get_structured_llm(self, schema: Any) -> Any:
        """Get a structured LLM instance configured with the given schema.

        Args:
            schema: Pydantic model or schema definition

        Returns:
            Configured LLM instance
        """
        ...

    def get_prompt(self, prompt_name: str) -> Any:
        """Get a prompt template by name.

        Args:
            prompt_name: Name identifier of the prompt

        Returns:
            Prompt template instance
        """
        ...

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Invoke an LLM chain with retry logic.

        Args:
            chain: LangChain runnable to invoke
            inputs: Input dictionary for the chain

        Returns:
            Result from the chain invocation
        """
        ...

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Invoke the LLM with messages and return the response content.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            The response content from the LLM
        """
        ...
