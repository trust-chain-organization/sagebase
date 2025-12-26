"""Factory for creating different types of LangChain chains"""

import logging

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableSerializable
from pydantic import BaseModel

from .llm_service import LLMService

from src.infrastructure.external.prompt_manager import PromptManager


logger = logging.getLogger(__name__)


class ChainFactory:
    """Factory for creating configured chains for different use cases"""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        prompt_manager: PromptManager | None = None,
    ):
        """
        Initialize chain factory

        Args:
            llm_service: LLM service instance (creates default if not provided)
            prompt_manager: Prompt manager instance (creates default if not provided)
        """
        self.llm_service = llm_service or LLMService.create_fast_instance()
        self.prompt_manager = prompt_manager or PromptManager.get_default_instance()

    def create_minutes_divider_chain(
        self, output_schema: type[BaseModel]
    ) -> RunnableSerializable[dict[str, Any], BaseModel]:
        """
        Create chain for dividing minutes into sections

        Args:
            output_schema: Schema for section info list

        Returns:
            Configured chain
        """
        try:
            # Try to get from hub first
            prompt = self.prompt_manager.get_hub_prompt("divide_chapter_prompt")
        except Exception:
            # Fall back to default prompt
            template = """Please divide the following minutes into sections:

{minutes}

Return a JSON array of sections with title and content for each."""
            prompt = ChatPromptTemplate.from_template(template)

        llm = self.llm_service.get_structured_llm(output_schema)
        chain = {"minutes": RunnablePassthrough()} | prompt | llm  # type: ignore[misc]
        return chain  # type: ignore[return-value]

    def create_speech_divider_chain(
        self, output_schema: type[BaseModel]
    ) -> RunnableSerializable[dict[str, Any], BaseModel]:
        """
        Create chain for extracting speaker and speech content

        Args:
            output_schema: Schema for speaker and speech list

        Returns:
            Configured chain
        """
        try:
            prompt = self.prompt_manager.get_hub_prompt("identify_speech")
        except Exception:
            template = """Extract speaker names and their speeches from the \
following text:

{text}

Return a JSON array with speaker and content for each speech."""
            prompt = ChatPromptTemplate.from_template(template)

        llm = self.llm_service.get_structured_llm(output_schema)
        chain = {"text": RunnablePassthrough()} | prompt | llm  # type: ignore[misc]
        return chain  # type: ignore[return-value]

    def create_politician_extractor_chain(
        self, output_schema: type[BaseModel]
    ) -> RunnableSerializable[dict[str, Any], BaseModel]:
        """
        Create chain for extracting politician information

        Args:
            output_schema: Schema for politician data

        Returns:
            Configured chain
        """
        template = """Extract politician information from the following HTML:

{html_content}

Return a JSON object with extracted politician data."""
        prompt = ChatPromptTemplate.from_template(template)
        llm = self.llm_service.get_structured_llm(output_schema)
        chain = prompt | llm  # type: ignore[misc]
        return chain  # type: ignore[return-value]

    def create_speaker_matching_chain(
        self, output_schema: type[BaseModel]
    ) -> RunnableSerializable[dict[str, Any], BaseModel]:
        """
        Create chain for matching speakers to politicians

        Args:
            output_schema: Schema for match result

        Returns:
            Configured chain
        """
        try:
            prompt = self.prompt_manager.get_prompt("speaker_match")
        except Exception:
            template = """Match the following speaker to available politicians:

Speaker: {speaker_name}
Available speakers: {available_speakers}

Return a JSON object with match results."""
            prompt = ChatPromptTemplate.from_template(template)

        llm = self.llm_service.get_structured_llm(output_schema)
        chain = prompt | llm  # type: ignore[misc]
        return chain  # type: ignore[return-value]

    def create_party_member_extractor_chain(
        self, output_schema: type[BaseModel]
    ) -> RunnableSerializable[dict[str, Any], BaseModel]:
        """
        Create chain for extracting party member information

        Args:
            output_schema: Schema for party member data

        Returns:
            Configured chain
        """
        template = """Extract party member information from the following HTML:

{html_content}

Return a JSON array of party members with name, position, and other details."""
        prompt = ChatPromptTemplate.from_template(template)
        llm = self.llm_service.get_structured_llm(output_schema)
        chain = prompt | llm  # type: ignore[misc]
        return chain  # type: ignore[return-value]

    def create_generic_chain(
        self,
        prompt_template: str,
        output_schema: type[BaseModel] | None = None,
    ) -> Runnable[dict[str, Any], Any]:
        """
        Create a generic chain with custom prompt

        Args:
            prompt_template: Template string for the prompt
            output_schema: Optional schema for structured output

        Returns:
            Configured chain
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)

        if output_schema:
            llm = self.llm_service.get_structured_llm(output_schema)
            chain = prompt | llm  # type: ignore[misc]
        else:
            chain = prompt | self.llm_service.llm  # type: ignore[misc]

        return chain  # type: ignore[return-value]

    def invoke_with_retry(
        self,
        chain: Runnable[dict[str, Any], Any],
        input_data: dict[str, Any],
        max_retries: int = 3,
    ) -> Any:
        """
        Invoke chain with retry logic

        Args:
            chain: The chain to invoke
            input_data: Input data for the chain
            max_retries: Maximum number of retries

        Returns:
            Result from the chain
        """
        return self.llm_service.invoke_with_retry(chain, input_data, max_retries)
