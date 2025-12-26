"""Factory for creating LLM services with optional instrumentation."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.llm_processing_history_repository import (
    LLMProcessingHistoryRepository,
)
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.versioned_prompt_manager import VersionedPromptManager
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryRepositoryImpl,
)
from src.infrastructure.persistence.prompt_version_repository_impl import (
    PromptVersionRepositoryImpl,
)


class LLMServiceFactory:
    """Factory for creating LLM services."""

    @staticmethod
    def create_gemini_service(
        api_key: str | None = None,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.1,
        with_history: bool = True,
        history_repository: LLMProcessingHistoryRepository | None = None,
        prompt_repository: PromptVersionRepository | None = None,
    ) -> ILLMService:
        """Create a Gemini LLM service with optional instrumentation.

        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model_name: Name of the Gemini model to use
            temperature: Temperature for generation
            with_history: Whether to enable history recording
            history_repository: Optional custom history repository
            prompt_repository: Optional custom prompt repository

        Returns:
            LLM service instance (instrumented if with_history=True)

        Example:
            # Basic usage with automatic history recording
            llm_service = LLMServiceFactory.create_gemini_service()

            # Without history recording
            llm_service = LLMServiceFactory.create_gemini_service(with_history=False)

            # With custom repositories
            history_repo = LLMProcessingHistoryRepositoryImpl(session)
            prompt_repo = PromptVersionRepositoryImpl(session)
            llm_service = LLMServiceFactory.create_gemini_service(
                history_repository=history_repo,
                prompt_repository=prompt_repo
            )
        """
        # Create prompt manager if repository provided
        prompt_manager = None
        if prompt_repository:
            prompt_manager = VersionedPromptManager(prompt_repository)

        # Create base Gemini service
        base_service = GeminiLLMService(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            prompt_manager=prompt_manager,
        )

        # Return instrumented service if history is enabled
        if with_history:
            return InstrumentedLLMService(
                llm_service=base_service,
                history_repository=history_repository,
                prompt_repository=prompt_repository,
                model_name=model_name,
                model_version="2.0",  # Could be extracted from model_name
            )

        return base_service

    @staticmethod
    def create_default_service(
        session: AsyncSession | None = None, with_history: bool = True
    ) -> ILLMService:
        """Create default LLM service with database repositories.

        Args:
            session: Database session for repositories
            with_history: Whether to enable history recording

        Returns:
            Configured LLM service

        Example:
            # In a use case or service
            from sqlalchemy.ext.asyncio import AsyncSession

            async def process_with_llm(session: AsyncSession):
                llm_service = LLMServiceFactory.create_default_service(session)
                result = await llm_service.match_speaker_to_politician(context)
        """
        # Create repositories if session provided
        history_repo = None
        prompt_repo = None

        if session and with_history:
            history_repo = LLMProcessingHistoryRepositoryImpl(session)
            prompt_repo = PromptVersionRepositoryImpl(session)

        return LLMServiceFactory.create_gemini_service(
            with_history=with_history,
            history_repository=history_repo,
            prompt_repository=prompt_repo,
        )


# Example usage in application code:
"""
# In a use case class
class MatchSpeakersUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session
        # Create LLM service with automatic history recording
        self.llm_service = LLMServiceFactory.create_default_service(session)

    async def execute(self, speaker_data):
        # All LLM operations will be automatically recorded
        result = await self.llm_service.match_speaker_to_politician(speaker_data)
        return result

# For testing or when history is not needed
class TestService:
    def __init__(self):
        # Create without history recording
        self.llm_service = LLMServiceFactory.create_gemini_service(
            with_history=False
        )
"""
