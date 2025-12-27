"""LLM testing mock utilities"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Any, TypeVar, cast
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class MockLLMResponse:
    """Mock response builder for LLM testing"""

    def __init__(self, content: str | dict[str, Any] | BaseModel):
        self.content = content

    def as_message(self) -> AIMessage:
        """Convert to AIMessage"""
        if isinstance(self.content, BaseModel):
            return AIMessage(content=self.content.model_dump_json())
        elif isinstance(self.content, dict):
            import json

            return AIMessage(content=json.dumps(self.content))
        else:
            return AIMessage(content=str(self.content))

    def as_chat_result(self) -> ChatResult:
        """Convert to ChatResult"""
        message = self.as_message()
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])


class MockLLM(Runnable[Any, BaseMessage]):
    """Mock LLM for testing"""

    def __init__(self, responses: list[Any] | None = None):
        """
        Initialize mock LLM

        Args:
            responses: List of responses to return in order
        """
        self.responses = responses or []
        self.call_count = 0
        self.call_history: list[dict[str, Any]] = []

    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> BaseMessage:
        """Mock invoke method"""
        self.call_history.append({"method": "invoke", "input": input})

        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockLLMResponse(response).as_message()

        return AIMessage(content="Default mock response")

    def with_structured_output(self, schema: type[T]) -> MockStructuredLLM[T]:
        """Return mock structured LLM"""
        return MockStructuredLLM(schema, self.responses, self.call_history)

    def reset(self):
        """Reset call tracking"""
        self.call_count = 0
        self.call_history.clear()


class MockStructuredLLM(Runnable[Any, T]):
    """Mock structured LLM for testing"""

    def __init__(
        self,
        schema: type[T],
        responses: list[Any] | None = None,
        shared_history: list[dict[str, Any]] | None = None,
    ):
        self.schema = schema
        self.responses = responses or []
        self.call_count = 0
        self.call_history = shared_history if shared_history is not None else []

    def invoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> T:
        """Mock invoke method returning structured output"""
        self.call_history.append(
            {"method": "invoke_structured", "input": input, "schema": self.schema}
        )

        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1

            # Convert response to schema instance
            if isinstance(response, self.schema):
                return cast(T, response)
            elif isinstance(response, dict):
                return cast(T, self.schema(**response))
            else:
                # Try to parse as JSON
                import json

                data = json.loads(str(response))
                return cast(T, self.schema(**data))

        # Return default instance
        return self._create_default_instance()

    def _create_default_instance(self) -> T:
        """Create default instance of schema"""
        # Simple default values for common types
        defaults: dict[str, Any] = {
            "str": "default",
            "int": 0,
            "float": 0.0,
            "bool": False,
            "list": [],
            "dict": {},
        }

        kwargs = {}
        for field_name, field_info in self.schema.model_fields.items():
            field_type = field_info.annotation
            type_name = (
                field_type.__name__
                if field_type is not None and hasattr(field_type, "__name__")
                else str(field_type)
            )

            # Set default based on type
            for default_type, default_value in defaults.items():
                if default_type in type_name.lower():
                    kwargs[field_name] = default_value
                    break
            else:
                kwargs[field_name] = None

        return cast(T, self.schema(**kwargs))


class LLMServiceMock:
    """Context manager for mocking LLMService"""

    def __init__(self, responses: list[Any] | None = None):
        self.mock_llm = MockLLM(responses)
        self.patches: list[Any] = []

    def __enter__(self):
        """Enter context manager"""
        # Patch GeminiLLMService creation (new location)
        llm_service_patch = patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        )
        mock_class = llm_service_patch.start()
        mock_class.return_value = self.mock_llm
        self.patches.append(llm_service_patch)

        # Also patch old location for backward compatibility
        old_service_patch = patch("src.services.llm_service.ChatGoogleGenerativeAI")
        old_mock_class = old_service_patch.start()
        old_mock_class.return_value = self.mock_llm
        self.patches.append(old_service_patch)

        # Also patch direct ChatGoogleGenerativeAI usage
        direct_patch = patch("langchain_google_genai.ChatGoogleGenerativeAI")
        mock_direct = direct_patch.start()
        mock_direct.return_value = self.mock_llm
        self.patches.append(direct_patch)

        return self.mock_llm

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager"""
        for patch_obj in self.patches:
            patch_obj.stop()


def mock_llm_service(
    responses: list[Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for mocking LLMService in tests

    Usage:
        @mock_llm_service([{"name": "Test"}])
        def test_something():
            # LLM calls will return the mocked responses
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with LLMServiceMock(responses) as mock:
                # Add mock to kwargs if function accepts it
                import inspect

                sig = inspect.signature(func)
                if "mock_llm" in sig.parameters:
                    kwargs["mock_llm"] = mock
                return func(*args, **kwargs)

        return wrapper

    return decorator


def create_mock_llm_service():
    """Create a mock LLMService instance for testing"""
    mock_service = MagicMock()

    # Mock the main methods
    mock_service.invoke_with_retry = MagicMock()
    mock_service.create_simple_chain = MagicMock()
    mock_service.create_json_output_chain = MagicMock()
    mock_service.get_structured_llm = MagicMock()

    # Mock class methods
    mock_service.create_fast_instance = MagicMock(return_value=mock_service)
    mock_service.create_advanced_instance = MagicMock(return_value=mock_service)

    return mock_service
