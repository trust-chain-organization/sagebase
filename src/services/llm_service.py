"""Centralized LLM Service for managing LLM operations"""

import logging
import os
import time
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.infrastructure.external.llm_errors import (
    LLMAuthenticationError,
    LLMError,
    LLMInvalidResponseError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from src.infrastructure.external.prompt_loader import PromptLoader
from src.infrastructure.external.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Centralized service for LLM operations with consistent configuration
    and error handling"""

    # Default models for different use cases
    DEFAULT_MODELS = {
        "fast": "gemini-2.5-flash",
        "advanced": "gemini-2.5-flash",
        "legacy": "gemini-1.5-flash-latest",
    }

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        api_key: str | None = None,
        use_prompt_manager: bool = True,
        prompt_loader: PromptLoader | None = None,
    ):
        """
        Initialize LLM Service

        Args:
            model_name: Name of the model to use (defaults to 'fast' model)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            api_key: Google API key (defaults to environment variable)
            use_prompt_manager: Whether to use PromptManager for legacy prompts
            prompt_loader: Custom prompt loader instance
        """
        self.model_name = model_name or self.DEFAULT_MODELS["fast"]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise LLMAuthenticationError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable."
            )

        self._llm = None
        self._structured_llms: dict[str, Any] = {}
        self._request_count = 0
        self._last_request_time = 0
        self._rate_limit_delay = 1.0  # Minimum seconds between requests

        # Prompt management
        self.prompt_loader = prompt_loader or PromptLoader.get_default_instance()
        self.prompt_manager = (
            PromptManager.get_default_instance() if use_prompt_manager else None
        )

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Lazy initialization of LLM"""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> ChatGoogleGenerativeAI:
        """Create LLM instance with configuration"""
        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "temperature": self.temperature,
            "google_api_key": self.api_key,
            "timeout": 60,  # 60 seconds timeout
            "max_retries": 2,  # Built-in retries
        }

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        return ChatGoogleGenerativeAI(**kwargs)

    def get_structured_llm(self, schema: type[T]) -> BaseChatModel:
        """
        Get LLM configured for structured output

        Args:
            schema: Pydantic model class for structured output

        Returns:
            LLM configured for structured output
        """
        schema_name = schema.__name__

        if schema_name not in self._structured_llms:
            self._structured_llms[schema_name] = self.llm.with_structured_output(schema)  # type: ignore[misc]

        return self._structured_llms[schema_name]

    def _handle_rate_limit(self):
        """Handle rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self._last_request_time = time.time()
        self._request_count += 1

    def _convert_exception(self, e: Exception) -> LLMError:
        """Convert exceptions to LLMError types"""
        error_str = str(e).lower()

        if "rate limit" in error_str or "quota exceeded" in error_str:
            return LLMRateLimitError(str(e))
        elif "timeout" in error_str:
            return LLMTimeoutError(str(e))
        elif "authentication" in error_str or "api key" in error_str:
            return LLMAuthenticationError(str(e))
        elif "invalid response" in error_str:
            return LLMInvalidResponseError(str(e))
        elif "quota" in error_str:
            return LLMQuotaExceededError(str(e))
        else:
            return LLMError(f"LLM error: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((LLMRateLimitError, LLMTimeoutError)),
    )
    def invoke_with_retry(
        self,
        chain: Runnable[dict[str, Any], Any],
        input_data: dict[str, Any],
        max_retries: int = 3,
    ) -> Any:
        """
        Invoke a chain with retry logic and rate limiting

        Args:
            chain: The chain to invoke
            input_data: Input data for the chain
            max_retries: Maximum number of retries

        Returns:
            Result from the chain
        """
        self._handle_rate_limit()

        try:
            result = chain.invoke(input_data)
            return result
        except Exception as e:
            llm_error = self._convert_exception(e)
            logger.error(f"Error invoking chain: {llm_error}")
            raise llm_error from e

    def get_prompt(self, prompt_key: str) -> ChatPromptTemplate:
        """
        Get prompt template by key

        Args:
            prompt_key: Key identifying the prompt

        Returns:
            ChatPromptTemplate instance
        """
        # Try prompt loader first
        try:
            return self.prompt_loader.get_prompt(prompt_key)
        except KeyError:
            # Fall back to prompt manager if available
            if self.prompt_manager:
                return self.prompt_manager.get_prompt(prompt_key)
            raise

    def create_simple_chain(
        self,
        prompt_template: str | None = None,
        prompt_key: str | None = None,
        output_schema: type[T] | None = None,
        use_passthrough: bool = True,
    ) -> Runnable[dict[str, Any], Any]:
        """
        Create a simple chain with prompt and optional structured output

        Args:
            prompt_template: Prompt template string
            prompt_key: Key to load prompt from prompt manager
            output_schema: Optional Pydantic model for structured output
            use_passthrough: Whether to use RunnablePassthrough for input

        Returns:
            Configured chain
        """
        if prompt_key:
            prompt = self.get_prompt(prompt_key)
        elif prompt_template:
            prompt = ChatPromptTemplate.from_template(prompt_template)
        else:
            raise ValueError("Either prompt_template or prompt_key must be provided")

        # Select appropriate LLM
        if output_schema:
            llm = self.get_structured_llm(output_schema)
        else:
            llm = self.llm

        # Build chain
        if use_passthrough:
            chain = {"input": RunnablePassthrough()} | prompt | llm  # type: ignore[misc]
        else:
            chain = prompt | llm  # type: ignore[misc]

        return chain  # type: ignore[return-value]

    def create_json_output_chain(
        self,
        prompt_template: str | None = None,
        prompt_key: str | None = None,
        output_schema: type[T] | None = None,
    ) -> Runnable[dict[str, Any], Any]:
        """
        Create a chain with JSON output parsing

        Args:
            prompt_template: Prompt template string
            prompt_key: Key to load prompt from prompt manager
            output_schema: Pydantic model for output validation

        Returns:
            Configured chain with JSON parsing
        """
        if prompt_key:
            prompt = self.get_prompt(prompt_key)
        elif prompt_template:
            prompt = ChatPromptTemplate.from_template(prompt_template)
        else:
            raise ValueError("Either prompt_template or prompt_key must be provided")

        if output_schema:
            parser = JsonOutputParser(pydantic_object=output_schema)
            chain = prompt | self.llm | parser  # type: ignore[misc]
        else:
            chain = prompt | self.llm  # type: ignore[misc]

        return chain  # type: ignore[return-value]

    @classmethod
    def create_fast_instance(cls, **kwargs: Any) -> "LLMService":
        """Create instance optimized for speed"""
        # Extract temperature to avoid duplicate keyword argument
        temperature = kwargs.pop("temperature", 0.1)
        return cls(
            model_name=cls.DEFAULT_MODELS["fast"], temperature=temperature, **kwargs
        )

    @classmethod
    def create_advanced_instance(cls, **kwargs: Any) -> "LLMService":
        """Create instance for advanced/complex tasks"""
        # Extract temperature to avoid duplicate keyword argument
        temperature = kwargs.pop("temperature", 0.1)
        return cls(
            model_name=cls.DEFAULT_MODELS["advanced"], temperature=temperature, **kwargs
        )

    def validate_api_key(self) -> bool:
        """Validate that API key is set and working"""
        try:
            # Simple test invocation
            test_prompt = ChatPromptTemplate.from_template("Say 'OK'")
            test_chain = test_prompt | self.llm  # type: ignore[misc]
            test_chain.invoke({})  # type: ignore[misc]
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False

    def invoke_prompt(
        self,
        prompt_key: str,
        variables: dict[str, Any],
        output_schema: type[T] | None = None,
    ) -> Any:
        """
        Invoke a prompt by key with variables

        Args:
            prompt_key: Prompt key
            variables: Variables for the prompt
            output_schema: Optional schema for structured output

        Returns:
            LLM response
        """
        chain = self.create_simple_chain(
            prompt_key=prompt_key, output_schema=output_schema, use_passthrough=False
        )
        return self.invoke_with_retry(chain, variables)

    async def ainvoke_prompt(
        self,
        prompt_key: str,
        variables: dict[str, Any],
        output_schema: type[T] | None = None,
    ) -> Any:
        """
        Async invoke a prompt by key with variables

        Args:
            prompt_key: Prompt key
            variables: Variables for the prompt
            output_schema: Optional schema for structured output

        Returns:
            LLM response
        """
        chain = self.create_simple_chain(
            prompt_key=prompt_key, output_schema=output_schema, use_passthrough=False
        )

        self._handle_rate_limit()

        try:
            result = await chain.ainvoke(variables)
            return result
        except Exception as e:
            llm_error = self._convert_exception(e)
            logger.error(f"Error invoking chain: {llm_error}")
            raise llm_error from e
