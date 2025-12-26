"""
Main dependency injection container for Polibase application.

This module provides the main ApplicationContainer that combines all sub-containers
and manages the application-wide dependency injection.
"""

import os
from enum import Enum
from typing import Any

from dependency_injector import containers, providers

from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.di.providers import (
    DatabaseContainer,
    RepositoryContainer,
    ServiceContainer,
    UseCaseContainer,
)


class Environment(Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application container that combines all sub-containers."""

    # Configuration
    config = providers.Configuration()

    # Settings provider
    settings = providers.Singleton(
        get_settings,
    )

    # Database container
    database = providers.Container(
        DatabaseContainer,
        config=config,
    )

    # Repository container
    repositories = providers.Container(
        RepositoryContainer,
        database=database,
    )

    # Service container
    services = providers.Container(
        ServiceContainer,
        config=config,
    )

    # Use case container
    use_cases = providers.Container(
        UseCaseContainer,
        repositories=repositories,
        services=services,
        database=database,
    )

    @classmethod
    def create_from_settings(
        cls, settings: Settings | None = None
    ) -> "ApplicationContainer":
        """Create container from settings object.

        Args:
            settings: Settings object. If None, will load from environment.

        Returns:
            Configured ApplicationContainer instance.
        """
        container = cls()

        # Use provided settings or load from environment
        if settings is None:
            settings = get_settings()

        # Configure container with settings
        container.config.from_dict(
            {
                "database_url": settings.get_database_url(),
                "google_api_key": settings.google_api_key,
                "llm_model": settings.llm_model,
                "llm_temperature": settings.llm_temperature,
                "gcs_bucket_name": settings.gcs_bucket_name,
                "gcs_project_id": settings.gcs_project_id,
                "web_scraper_timeout": settings.web_scraper_timeout,
                "page_load_timeout": settings.page_load_timeout,
            }
        )

        return container

    @classmethod
    def create_for_environment(
        cls, environment: Environment | str | None = None
    ) -> "ApplicationContainer":
        """Create container for specific environment.

        Args:
            environment: Environment type or string. If None, detects from env var.

        Returns:
            Configured ApplicationContainer instance for the environment.
        """
        if environment is None:
            env_str = os.getenv("ENVIRONMENT", "development").lower()
            environment = Environment(env_str)
        elif isinstance(environment, str):
            environment = Environment(environment.lower())

        container = cls()

        # Load settings based on environment
        try:
            settings = get_settings()
        except Exception:
            # If settings failed to load, create a fresh instance
            from src.infrastructure.config.settings import Settings

            settings = Settings()

        # Additional check for None settings
        if settings is None:
            from src.infrastructure.config.settings import Settings

            settings = Settings()

        # Apply environment-specific configuration
        if environment == Environment.TESTING:
            # Override settings for testing
            container.config.from_dict(
                {
                    "database_url": "sqlite:///:memory:",
                    "google_api_key": "test-api-key",
                    "llm_model": "test-model",
                    "llm_temperature": 0.0,
                    "gcs_bucket_name": "test-bucket",
                    "gcs_project_id": "test-project",
                    "web_scraper_timeout": 5,
                    "page_load_timeout": 5,
                }
            )
        elif environment == Environment.PRODUCTION:
            # Use production settings (validate required configs)
            if settings:
                settings.validate()
                database_url = settings.get_database_url()
                google_api_key = settings.get_required("google_api_key")
                llm_model = settings.llm_model
                llm_temperature = settings.llm_temperature
                gcs_bucket_name = settings.gcs_bucket_name
                gcs_project_id = settings.gcs_project_id
                web_scraper_timeout = settings.web_scraper_timeout
                page_load_timeout = settings.page_load_timeout
            else:
                # Production requires proper settings, fall back to defaults but warn
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "Settings not initialized properly, using fallback values"
                )
                database_url = "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db"
                google_api_key = ""  # Will need to be set
                llm_model = "gemini-2.0-flash"
                llm_temperature = 0.0
                gcs_bucket_name = "sagebase-scraped-minutes"
                gcs_project_id = None
                web_scraper_timeout = 60
                page_load_timeout = 30

            container.config.from_dict(
                {
                    "database_url": database_url,
                    "google_api_key": google_api_key,
                    "llm_model": llm_model,
                    "llm_temperature": llm_temperature,
                    "gcs_bucket_name": gcs_bucket_name,
                    "gcs_project_id": gcs_project_id,
                    "web_scraper_timeout": web_scraper_timeout,
                    "page_load_timeout": page_load_timeout,
                }
            )
        else:  # DEVELOPMENT
            # Use development settings (more lenient)
            import logging

            logger = logging.getLogger(__name__)

            if settings:
                database_url = settings.get_database_url()
                google_api_key = settings.google_api_key or "dev-api-key"
                llm_model = settings.llm_model
                llm_temperature = settings.llm_temperature
                gcs_bucket_name = settings.gcs_bucket_name
                gcs_project_id = settings.gcs_project_id
                web_scraper_timeout = settings.web_scraper_timeout
                page_load_timeout = settings.page_load_timeout
            else:
                # Fallback values if settings is None
                logger.warning(
                    "Settings is None, using fallback values for development env"
                )
                database_url = "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db"
                google_api_key = "dev-api-key"
                llm_model = "gemini-2.0-flash"
                llm_temperature = 0.0
                gcs_bucket_name = "sagebase-scraped-minutes"
                gcs_project_id = None
                web_scraper_timeout = 60
                page_load_timeout = 30

            # Ensure database_url is never None
            if database_url is None:
                logger.warning("database_url is None after settings, using fallback")
                database_url = "postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db"

            logger.info(
                f"Setting database_url in container config: {database_url[:50]}..."
            )

            container.config.from_dict(
                {
                    "database_url": database_url,
                    "google_api_key": google_api_key,
                    "llm_model": llm_model,
                    "llm_temperature": llm_temperature,
                    "gcs_bucket_name": gcs_bucket_name,
                    "gcs_project_id": gcs_project_id,
                    "web_scraper_timeout": web_scraper_timeout,
                    "page_load_timeout": page_load_timeout,
                }
            )

        return container

    def wire_modules(self, modules: list[Any]) -> None:
        """Wire container to specified modules.

        Args:
            modules: List of modules to wire the container to.
        """
        self.wire(modules=modules)

    def get_session_context(self) -> Any:
        """Get a database session context manager.

        Returns:
            A context manager that provides a database session.
        """
        from collections.abc import Generator
        from contextlib import contextmanager
        from typing import Any

        @contextmanager
        def session_context() -> Generator[Any]:
            session = self.database.session()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return session_context()


# Global container instance
_container: ApplicationContainer | None = None


def get_container() -> ApplicationContainer:
    """Get the global container instance.

    Returns:
        The global ApplicationContainer instance.

    Raises:
        RuntimeError: If container is not initialized.
    """
    global _container
    if _container is None:
        raise RuntimeError("Container not initialized. Call init_container() first.")
    return _container


def init_container(
    environment: Environment | str | None = None,
    settings: Settings | None = None,
    force_reinit: bool = False,
) -> ApplicationContainer:
    """Initialize the global container.

    Args:
        environment: Environment to use. If None, detects from env var.
        settings: Settings object to use. If None, loads from environment.
        force_reinit: If True, force re-initialization even if container exists.

    Returns:
        The initialized ApplicationContainer instance.
    """
    global _container

    # Return existing container if already initialized and not forcing re-init
    if _container is not None and not force_reinit:
        return _container

    if settings is not None:
        _container = ApplicationContainer.create_from_settings(settings)
    else:
        _container = ApplicationContainer.create_for_environment(environment)

    return _container


def reset_container() -> None:
    """Reset the global container (useful for testing)."""
    global _container
    if _container is not None:
        _container.shutdown_resources()
        _container = None


# Alias for backward compatibility
Container = ApplicationContainer
