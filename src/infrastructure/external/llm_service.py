"""LLM service interface and implementation."""

import json
import logging
import os
from typing import Any, cast

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_google_genai import ChatGoogleGenerativeAI

from src.domain.entities.llm_processing_history import LLMProcessingHistory
from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
    PoliticianDTO,
)
from src.infrastructure.external.versioned_prompt_manager import VersionedPromptManager


logger = logging.getLogger(__name__)


class GeminiLLMService(ILLMService):
    """Gemini-based implementation of LLM service."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        prompt_manager: VersionedPromptManager | None = None,
    ):
        """Initialize Gemini LLM service.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model_name: Name of the Gemini model to use
            temperature: Temperature for generation
            prompt_manager: Optional prompt manager for versioned prompts
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        self.model_name = model_name
        self.temperature = temperature
        self._prompt_manager = prompt_manager
        self._history_repository: LLMProcessingHistoryRepository | None = None

        # Initialize Gemini client
        self._llm = ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=self.api_key,
        )

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Get the underlying LLM instance."""
        return self._llm

    async def set_history_repository(
        self, repository: LLMProcessingHistoryRepository | None
    ) -> None:
        """Set the history repository for recording LLM operations."""
        self._history_repository = repository

    async def get_processing_history(
        self, reference_type: str | None = None, reference_id: int | None = None
    ) -> list[LLMProcessingHistory]:
        """Get processing history for this service."""
        if not self._history_repository:
            return []

        if reference_type and reference_id:
            return await self._history_repository.get_by_input_reference(
                reference_type, reference_id
            )
        return []

    async def _get_prompt(self, prompt_key: str, variables: dict[str, Any]) -> str:
        """Get prompt from manager or use default.

        Args:
            prompt_key: Key identifying the prompt
            variables: Variables for the prompt

        Returns:
            Formatted prompt string
        """
        if self._prompt_manager:
            try:
                prompt, version = await self._prompt_manager.get_versioned_prompt(
                    prompt_key, variables
                )
                return prompt
            except Exception as e:
                logger.warning(f"Failed to get versioned prompt: {e}")

        # Fallback to hardcoded prompts
        if prompt_key == "speaker_matching":
            return self._get_speaker_matching_prompt(variables)
        elif prompt_key == "party_member_extraction":
            return self._get_party_member_extraction_prompt(variables)
        elif prompt_key == "conference_member_matching":
            return self._get_conference_member_matching_prompt(variables)
        elif prompt_key == "speech_extraction":
            return self._get_speech_extraction_prompt(variables)
        else:
            return f"No prompt found for key: {prompt_key}"

    def _get_speaker_matching_prompt(self, variables: dict[str, Any]) -> str:
        """Get speaker matching prompt."""
        candidates = variables.get("candidates", [])
        speaker_name = variables.get("speaker_name", "")

        candidates_text = "\n".join(
            [
                f"- ID: {c['id']}, Name: {c['name']}, Party: {c.get('party', 'N/A')}"
                for c in candidates
            ]
        )

        return f"""Match the speaker to one of the candidates below.

Speaker: {speaker_name}

Candidates:
{candidates_text}

Return a JSON object with:
- matched: boolean (true if match found)
- confidence: float (0.0-1.0)
- matched_id: int (candidate ID if matched)
- reason: string (explanation)
"""

    def _get_party_member_extraction_prompt(self, variables: dict[str, Any]) -> str:
        """Get party member extraction prompt."""
        return """Extract politician information from the provided HTML content.

Return a JSON object with:
- success: boolean
- extracted_data: array of objects with:
  - name: string (full name)
  - furigana: string (name reading in katakana)
  - position: string (role/position)
  - district: string (electoral district)
- error: string or null"""

    def _get_conference_member_matching_prompt(self, variables: dict[str, Any]) -> str:
        """Get conference member matching prompt."""
        member_name = variables.get("member_name", "")
        party_name = variables.get("party_name", "")
        candidates = variables.get("candidates", [])

        candidates_text = "\n".join(
            [
                f"- ID: {c.id}, Name: {c.name}, Party: {c.party_name or 'N/A'}"
                for c in candidates
            ]
        )

        return f"""Match the conference member to one of the candidates.

Member: {member_name}
Party: {party_name or "Unknown"}

Candidates:
{candidates_text}

Return a JSON object with:
- matched: boolean
- confidence: float (0.0-1.0)
- matched_id: int (candidate ID if matched)
- reason: string
"""

    def _get_speech_extraction_prompt(self, variables: dict[str, Any]) -> str:
        """Get speech extraction prompt."""
        return """Extract speeches from the meeting minutes text.

Return a JSON array of objects with:
- speaker: string (speaker name)
- content: string (speech content)

Format: [{"speaker": "Name", "content": "Speech text"}, ...]"""

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician using Gemini."""
        try:
            # Prepare prompt
            prompt = await self._get_prompt(
                "speaker_matching",
                {
                    "speaker_name": context.get("speaker_name", ""),
                    "candidates": context.get("candidates", []),
                },
            )

            # Create prompt template and invoke
            prompt_template = ChatPromptTemplate.from_template(prompt)
            chain: RunnableSerializable[dict[str, Any], BaseMessage] = cast(
                RunnableSerializable[dict[str, Any], BaseMessage],
                prompt_template | self._llm,
            )
            response = await chain.ainvoke({})

            # Parse response
            if hasattr(response, "content"):
                content = cast(Any, response).content
                if isinstance(content, str):
                    response_text = content
                else:
                    response_text = str(content)
            else:
                response_text = str(response)
            result = json.loads(response_text)

            return LLMMatchResult(
                matched=result.get("matched", False),
                confidence=result.get("confidence", 0.0),
                reason=result.get("reason", ""),
                matched_id=result.get("matched_id"),
                metadata={"model": self.model_name},
            )
        except Exception as e:
            logger.error(f"Failed to match speaker: {e}")
            return None

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract politician information from HTML using Gemini."""
        try:
            # Prepare prompt with HTML content
            prompt = await self._get_prompt("party_member_extraction", {})
            full_prompt = (
                f"{prompt}\n\nHTML Content:\n{html_content[:5000]}"  # Limit HTML size
            )

            # Create prompt template and invoke
            prompt_template = ChatPromptTemplate.from_template(full_prompt)
            chain: RunnableSerializable[dict[str, Any], BaseMessage] = cast(
                RunnableSerializable[dict[str, Any], BaseMessage],
                prompt_template | self._llm,
            )
            response = await chain.ainvoke({})

            # Parse response
            if hasattr(response, "content"):
                content = cast(Any, response).content
                if isinstance(content, str):
                    response_text = content
                else:
                    response_text = str(content)
            else:
                response_text = str(response)
            result = json.loads(response_text)

            return LLMExtractResult(
                success=result.get("success", False),
                extracted_data=result.get("extracted_data", []),
                error=result.get("error"),
                metadata={"party_id": str(party_id), "model": self.model_name},
            )
        except Exception as e:
            logger.error(f"Failed to extract party members: {e}")
            return LLMExtractResult(
                success=False,
                extracted_data=[],
                error=str(e),
                metadata={"party_id": str(party_id), "model": self.model_name},
            )

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[PoliticianDTO]
    ) -> LLMMatchResult | None:
        """Match conference member to politician using Gemini."""
        try:
            # Prepare prompt
            prompt = await self._get_prompt(
                "conference_member_matching",
                {
                    "member_name": member_name,
                    "party_name": party_name,
                    "candidates": candidates,
                },
            )

            # Create prompt template and invoke
            prompt_template = ChatPromptTemplate.from_template(prompt)
            chain: RunnableSerializable[dict[str, Any], BaseMessage] = cast(
                RunnableSerializable[dict[str, Any], BaseMessage],
                prompt_template | self._llm,
            )
            response = await chain.ainvoke({})

            # Parse response
            if hasattr(response, "content"):
                content = cast(Any, response).content
                if isinstance(content, str):
                    response_text = content
                else:
                    response_text = str(content)
            else:
                response_text = str(response)
            result = json.loads(response_text)

            return LLMMatchResult(
                matched=result.get("matched", False),
                confidence=result.get("confidence", 0.0),
                reason=result.get("reason", ""),
                matched_id=result.get("matched_id"),
                metadata={"model": self.model_name, "member_name": member_name},
            )
        except Exception as e:
            logger.error(f"Failed to match conference member: {e}")
            return None

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from minutes text using Gemini."""
        try:
            # Prepare prompt with text
            prompt = await self._get_prompt("speech_extraction", {})
            full_prompt = f"{prompt}\n\nText:\n{text[:10000]}"  # Limit text size

            # Create prompt template and invoke
            prompt_template = ChatPromptTemplate.from_template(full_prompt)
            chain: RunnableSerializable[dict[str, Any], BaseMessage] = cast(
                RunnableSerializable[dict[str, Any], BaseMessage],
                prompt_template | self._llm,
            )
            response = await chain.ainvoke({})

            # Parse response
            if hasattr(response, "content"):
                content = cast(Any, response).content
                if isinstance(content, str):
                    response_text = content
                else:
                    response_text = str(content)
            else:
                response_text = str(response)
            speeches = json.loads(response_text)

            if not isinstance(speeches, list):
                logger.error("Invalid response format: expected list")
                return []

            return speeches  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to extract speeches: {e}")
            return []

    def get_structured_llm(self, schema: Any) -> Any:
        """Get a structured LLM instance configured with the given schema.

        Args:
            schema: Pydantic model or schema definition

        Returns:
            Configured LLM instance
        """
        # For Gemini, we can use with_structured_output method
        return self._llm.with_structured_output(schema)  # type: ignore[return-value]

    def get_prompt(self, prompt_name: str) -> Any:
        """Get a prompt template by name.

        Args:
            prompt_name: Name identifier of the prompt

        Returns:
            Prompt template instance
        """
        # Load prompts from YAML file
        import os

        import yaml

        prompts_path = os.path.join(
            os.path.dirname(__file__), "../prompts/prompts.yaml"
        )

        with open(prompts_path, encoding="utf-8") as f:
            prompts_data = yaml.safe_load(f)

        if "prompts" not in prompts_data:
            raise KeyError("No prompts section found in prompts.yaml")

        prompts = prompts_data["prompts"]

        if prompt_name not in prompts:
            raise KeyError(f"Prompt '{prompt_name}' not found in prompts.yaml")

        prompt_config = prompts[prompt_name]
        template = prompt_config.get("template", "")

        return ChatPromptTemplate.from_template(template)

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Invoke an LLM chain with retry logic.

        Args:
            chain: LangChain runnable to invoke
            inputs: Input dictionary for the chain

        Returns:
            Result from the chain invocation
        """
        # Simple implementation without actual retry logic
        # In production, you'd want to add proper retry logic with exponential backoff
        try:
            return chain.invoke(inputs)
        except Exception as e:
            logger.error(f"Chain invocation failed: {e}")
            raise

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Invoke the LLM with messages and return the response content.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys

        Returns:
            The response content from the LLM
        """
        try:
            response = self._llm.invoke(messages)
            # Ensure we return a string
            content = response.content
            if isinstance(content, str):
                return content
            else:
                # Convert to string if necessary
                return str(content)
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise
