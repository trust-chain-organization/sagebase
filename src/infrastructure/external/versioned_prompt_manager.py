"""Versioned prompt management with database backing."""

import logging

from datetime import datetime
from typing import Any

from src.domain.entities.prompt_version import PromptVersion
from src.domain.repositories.prompt_version_repository import PromptVersionRepository
from src.infrastructure.external.prompt_manager import PromptManager


logger = logging.getLogger(__name__)


class VersionedPromptManager(PromptManager):
    """Extended prompt manager with version control capabilities."""

    def __init__(self, repository: PromptVersionRepository | None = None):
        """Initialize versioned prompt manager.

        Args:
            repository: Optional prompt version repository. If not provided,
                       falls back to in-memory prompt management.
        """
        super().__init__()
        self.repository = repository
        self._version_cache: dict[str, PromptVersion] = {}

    async def get_versioned_prompt(
        self, prompt_key: str, variables: dict[str, Any] | None = None
    ) -> tuple[str, str]:
        """Get a versioned prompt and format it with variables.

        Args:
            prompt_key: Key identifying the prompt
            variables: Optional variables to format the prompt with

        Returns:
            Tuple of (formatted_prompt, version)

        Raises:
            ValueError: If prompt not found or variables are invalid
        """
        # Try to get from repository first
        if self.repository:
            prompt_version = await self._get_active_version(prompt_key)
            if prompt_version:
                formatted = prompt_version.format_template(variables or {})
                return formatted, prompt_version.version

        # Fall back to parent implementation
        prompt_template = self.get_prompt(prompt_key)
        formatted = prompt_template.format(**(variables or {}))
        return formatted, "legacy"

    async def _get_active_version(self, prompt_key: str) -> PromptVersion | None:
        """Get active version from cache or repository.

        Args:
            prompt_key: Key identifying the prompt

        Returns:
            Active prompt version or None
        """
        if not self.repository:
            return None

        # Check cache first
        if prompt_key in self._version_cache:
            cached = self._version_cache[prompt_key]
            # Simple cache invalidation after 5 minutes
            if (
                cached.updated_at
                and (datetime.now() - cached.updated_at).total_seconds() < 300
            ):
                return cached

        # Fetch from repository
        try:
            version = await self.repository.get_active_version(prompt_key)
            if version:
                self._version_cache[prompt_key] = version
            return version
        except Exception as e:
            logger.error(f"Failed to fetch prompt version for {prompt_key}: {e}")
            return None

    async def save_new_version(
        self,
        prompt_key: str,
        template: str,
        version: str | None = None,
        description: str | None = None,
        variables: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
        activate: bool = True,
    ) -> PromptVersion | None:
        """Save a new version of a prompt.

        Args:
            prompt_key: Key identifying the prompt
            template: The prompt template content
            version: Version identifier (auto-generated if not provided)
            description: Optional description
            variables: List of variable names
            metadata: Additional metadata
            created_by: Creator identifier
            activate: Whether to activate this version immediately

        Returns:
            Created prompt version or None if repository not available
        """
        if not self.repository:
            logger.warning("No repository available for saving prompt version")
            return None

        # Auto-generate version if not provided
        if not version:
            version = datetime.now().strftime("%Y%m%d-%H%M%S")

        try:
            prompt_version = await self.repository.create_version(
                prompt_key=prompt_key,
                template=template,
                version=version,
                description=description,
                variables=variables,
                metadata=metadata,
                created_by=created_by,
                activate=activate,
            )

            # Update cache if activated
            if activate:
                self._version_cache[prompt_key] = prompt_version

            logger.info(f"Saved prompt version {prompt_key}:{version}")
            return prompt_version

        except Exception as e:
            logger.error(f"Failed to save prompt version: {e}")
            raise

    async def get_prompt_history(
        self, prompt_key: str, limit: int | None = None
    ) -> list[PromptVersion]:
        """Get version history for a prompt.

        Args:
            prompt_key: Key identifying the prompt
            limit: Maximum number of versions to return

        Returns:
            List of prompt versions
        """
        if not self.repository:
            return []

        try:
            return await self.repository.get_versions_by_key(prompt_key, limit)
        except Exception as e:
            logger.error(f"Failed to fetch prompt history: {e}")
            return []

    async def activate_version(self, prompt_key: str, version: str) -> bool:
        """Activate a specific version of a prompt.

        Args:
            prompt_key: Key identifying the prompt
            version: Version to activate

        Returns:
            True if successful
        """
        if not self.repository:
            return False

        try:
            success = await self.repository.activate_version(prompt_key, version)
            if success:
                # Invalidate cache
                self._version_cache.pop(prompt_key, None)
            return success
        except Exception as e:
            logger.error(f"Failed to activate prompt version: {e}")
            return False

    async def get_specific_version(
        self, prompt_key: str, version: str
    ) -> PromptVersion | None:
        """Get a specific version of a prompt.

        Args:
            prompt_key: Key identifying the prompt
            version: Version identifier

        Returns:
            Prompt version or None
        """
        if not self.repository:
            return None

        try:
            return await self.repository.get_by_key_and_version(prompt_key, version)
        except Exception as e:
            logger.error(f"Failed to fetch specific prompt version: {e}")
            return None

    async def migrate_existing_prompts(self, created_by: str = "system") -> int:
        """Migrate existing in-memory prompts to versioned storage.

        Args:
            created_by: Identifier for migration creator

        Returns:
            Number of prompts migrated
        """
        if not self.repository:
            return 0

        migrated = 0
        skipped = 0

        # Get existing versions to check for duplicates
        # Check all versions with version "1.0.0" to avoid duplicate initial migrations
        existing_versions = await self.repository.search(limit=1000)
        existing_migrations = {
            v.prompt_key for v in existing_versions if v.version == "1.0.0"
        }

        # Migrate static prompts
        for prompt_key, template in self.PROMPTS.items():
            # Skip if already exists with version 1.0.0
            if prompt_key in existing_migrations:
                logger.info(f"Skipping existing prompt: {prompt_key}")
                skipped += 1
                continue

            try:
                # Extract variables from template
                prompt_version = PromptVersion(
                    prompt_key=prompt_key,
                    template=template,
                    version="1.0.0",
                    description="Initial version migrated from static prompts",
                    created_by=created_by,
                )
                variables = prompt_version.extract_variables()

                await self.save_new_version(
                    prompt_key=prompt_key,
                    template=template,
                    version="1.0.0",
                    description="Initial version migrated from static prompts",
                    variables=variables,
                    metadata={"migrated": True, "source": "static"},
                    created_by=created_by,
                    activate=True,
                )
                migrated += 1
                logger.info(f"Migrated prompt: {prompt_key}")

            except Exception as e:
                logger.error(f"Failed to migrate prompt {prompt_key}: {e}")

        if skipped > 0:
            logger.info(f"Skipped {skipped} existing prompts")

        return migrated

    def clear_cache(self) -> None:
        """Clear the version cache."""
        self._version_cache.clear()
        logger.info("Cleared prompt version cache")
