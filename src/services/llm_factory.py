"""Factory pattern for creating LLMService instances"""

from typing import Any, TypedDict

from src.common.logging import get_logger
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.prompt_loader import PromptLoader


logger = get_logger(__name__)


class LLMServiceFactory:
    """Factory for creating LLMService instances with different configurations"""

    # Preset configurations
    class PresetConfig(TypedDict, total=False):
        model_name: str
        temperature: float
        description: str

    PRESETS: dict[str, PresetConfig] = {
        "fast": {
            "model_name": "gemini-1.5-flash",
            "temperature": 0.1,
            "description": "Fast model for simple tasks",
        },
        "advanced": {
            "model_name": "gemini-2.0-flash-exp",
            "temperature": 0.1,
            "description": "Advanced model for complex tasks",
        },
        "creative": {
            "model_name": "gemini-2.0-flash-exp",
            "temperature": 0.7,
            "description": "Creative model with higher temperature",
        },
        "precise": {
            "model_name": "gemini-2.0-flash-exp",
            "temperature": 0.0,
            "description": "Precise model with zero temperature",
        },
        "legacy": {
            "model_name": "gemini-1.5-flash",
            "temperature": 0.1,
            "description": "Legacy model for backward compatibility",
        },
    }

    def __init__(self, prompt_loader: PromptLoader | None = None):
        """
        Initialize factory

        Args:
            prompt_loader: Shared prompt loader instance
        """
        self.prompt_loader = prompt_loader or PromptLoader.get_default_instance()
        self._instances: dict[str, InstrumentedLLMService | GeminiLLMService] = {}

    def create(
        self,
        preset: str | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        api_key: str | None = None,
        use_cache: bool = True,
        enable_metrics: bool = True,
    ) -> InstrumentedLLMService | GeminiLLMService:
        """
        Create LLMService instance

        Args:
            preset: Preset configuration name
            model_name: Model name (overrides preset)
            temperature: Temperature (overrides preset)
            max_tokens: Maximum tokens
            api_key: API key
            use_cache: Whether to cache and reuse instances

        Returns:
            LLMService instance
        """
        # Build configuration
        config: dict[str, Any] = {}

        if preset and preset in self.PRESETS:
            config.update(self.PRESETS[preset])

        # Override with explicit parameters
        if model_name is not None:
            config["model_name"] = model_name
        if temperature is not None:
            config["temperature"] = temperature
        if max_tokens is not None:
            config["max_tokens"] = max_tokens
        if api_key is not None:
            config["api_key"] = api_key

        # Remove non-parameter keys
        config.pop("description", None)

        # Create cache key
        cache_key = self._get_cache_key(config) if use_cache else None

        # Check cache
        if cache_key and cache_key in self._instances:
            logger.debug(f"Returning cached LLMService instance: {cache_key}")
            return self._instances[cache_key]

        # Filter config to only include parameters supported by GeminiLLMService
        gemini_config = {
            k: v
            for k, v in config.items()
            if k in {"api_key", "model_name", "temperature"}
        }

        # Create new instance
        instance = GeminiLLMService(**gemini_config)

        # Wrap with instrumentation if enabled
        if enable_metrics:
            model_name_val = config.get("model_name", "gemini-2.0-flash-exp")
            model_version = config.get("model_version", "latest")
            instance = InstrumentedLLMService(
                instance,
                model_name=(
                    model_name_val
                    if model_name_val is not None
                    else "gemini-2.0-flash-exp"
                ),
                model_version=model_version,
            )

        # Cache if requested
        if cache_key:
            self._instances[cache_key] = instance

        return instance

    def create_fast(self, **kwargs: Any) -> InstrumentedLLMService | GeminiLLMService:
        """Create fast model instance"""
        return self.create(preset="fast", **kwargs)

    def create_advanced(
        self, **kwargs: Any
    ) -> InstrumentedLLMService | GeminiLLMService:
        """Create advanced model instance"""
        return self.create(preset="advanced", **kwargs)

    def create_creative(
        self, **kwargs: Any
    ) -> InstrumentedLLMService | GeminiLLMService:
        """Create creative model instance"""
        return self.create(preset="creative", **kwargs)

    def create_precise(
        self, **kwargs: Any
    ) -> InstrumentedLLMService | GeminiLLMService:
        """Create precise model instance"""
        return self.create(preset="precise", **kwargs)

    def create_legacy(self, **kwargs: Any) -> InstrumentedLLMService | GeminiLLMService:
        """Create legacy model instance"""
        return self.create(preset="legacy", **kwargs)

    def _get_cache_key(self, config: dict[str, Any]) -> str:
        """Generate cache key from configuration"""
        # Exclude api_key from cache key
        key_parts: list[str] = []
        for k, v in sorted(config.items()):
            if k != "api_key":
                key_parts.append(f"{k}={v}")
        return "|".join(key_parts)

    def clear_cache(self):
        """Clear cached instances"""
        self._instances.clear()
        logger.info("LLMService cache cleared")

    def list_presets(self) -> dict[str, str]:
        """List available presets with descriptions"""
        return {k: v.get("description", "") for k, v in self.PRESETS.items()}

    @classmethod
    def create_default_factory(cls) -> "LLMServiceFactory":
        """Create default factory instance"""
        return cls()

    @classmethod
    def create_gemini_service(cls) -> InstrumentedLLMService | GeminiLLMService:
        """Create default Gemini service (for backward compatibility)"""
        factory = cls()
        return factory.create_fast()
