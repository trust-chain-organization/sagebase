"""Prompt template loader from YAML files"""

import logging
from pathlib import Path
from typing import Any

import yaml
from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


class PromptLoader:
    """Load and manage prompts from YAML files"""

    def __init__(self, prompt_dir: Path | str | None = None):
        """
        Initialize prompt loader

        Args:
            prompt_dir: Directory containing prompt YAML files
        """
        if prompt_dir is None:
            # Prompts are in src/infrastructure/prompts/
            prompt_dir = Path(__file__).parent.parent / "prompts"
        self.prompt_dir = Path(prompt_dir)
        self._prompts: dict[str, dict[str, Any]] = {}
        self._prompt_templates: dict[str, ChatPromptTemplate] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load all prompts from YAML files"""
        yaml_files = list(self.prompt_dir.glob("*.yaml")) + list(
            self.prompt_dir.glob("*.yml")
        )

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                # Load regular prompts
                if "prompts" in data:
                    for key, prompt_data in data["prompts"].items():
                        self._prompts[key] = prompt_data
                        logger.debug(f"Loaded prompt: {key}")

                # Store version info
                if "version" in data:
                    self._prompts["_version"] = data["version"]

            except Exception as e:
                logger.error(f"Failed to load prompts from {yaml_file}: {e}")

    def get_prompt(self, key: str) -> ChatPromptTemplate:
        """
        Get a prompt template by key

        Args:
            key: Prompt key

        Returns:
            ChatPromptTemplate instance
        """
        if key not in self._prompt_templates:
            if key not in self._prompts:
                raise KeyError(f"Prompt not found: {key}")

            prompt_data = self._prompts[key]
            template = prompt_data.get("template", "")

            # Create prompt template
            self._prompt_templates[key] = ChatPromptTemplate.from_template(template)

        return self._prompt_templates[key]

    def get_prompt_template(self, key: str) -> str:
        """
        Get raw prompt template string

        Args:
            key: Prompt key

        Returns:
            Template string
        """
        if key not in self._prompts:
            raise KeyError(f"Prompt not found: {key}")

        return self._prompts[key].get("template", "")

    def get_variables(self, key: str) -> list[str]:
        """
        Get required variables for a prompt

        Args:
            key: Prompt key

        Returns:
            List of variable names
        """
        if key not in self._prompts:
            raise KeyError(f"Prompt not found: {key}")

        return self._prompts[key].get("variables", [])

    def get_description(self, key: str) -> str:
        """
        Get prompt description

        Args:
            key: Prompt key

        Returns:
            Description string
        """
        if key not in self._prompts:
            raise KeyError(f"Prompt not found: {key}")

        return self._prompts[key].get("description", "")

    def list_prompts(self) -> list[str]:
        """List all available prompt keys"""
        return [k for k in self._prompts.keys() if not k.startswith("_")]

    def get_version(self) -> str:
        """Get prompts version"""
        version = self._prompts.get("_version", "unknown")
        return str(version) if version else "unknown"

    def reload(self):
        """Reload prompts from files"""
        self._prompts.clear()
        self._prompt_templates.clear()
        self._load_prompts()
        logger.info("Prompts reloaded")

    @classmethod
    def get_default_instance(cls) -> "PromptLoader":
        """Get default instance (singleton pattern)"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance
