"""
Configuration module for Polibase.

This module provides centralized configuration management.
"""

from src.infrastructure.config.async_database import (
    AsyncDatabase,
    async_db,
    get_async_session,
)
from src.infrastructure.config.config import (
    DATABASE_URL,
    ENV_FILE_PATH,
    GCS_BUCKET_NAME,
    GCS_PROJECT_ID,
    GCS_UPLOAD_ENABLED,
    GOOGLE_API_KEY,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT,
    LANGCHAIN_TRACING_V2,
    OPENAI_API_KEY,
    TAVILY_API_KEY,
    find_env_file,
    get_required_config,
    set_env,
    validate_config,
)
from src.infrastructure.config.database import (
    close_db_engine,
    get_db_engine,
    get_db_session,
    get_db_session_context,
    test_connection,
)
from src.infrastructure.config.sentry import init_sentry
from src.infrastructure.config.settings import Settings, settings


__all__ = [
    # Settings
    "Settings",
    "settings",
    # Async database
    "AsyncDatabase",
    "async_db",
    "get_async_session",
    # Config constants
    "DATABASE_URL",
    "ENV_FILE_PATH",
    "GCS_BUCKET_NAME",
    "GCS_PROJECT_ID",
    "GCS_UPLOAD_ENABLED",
    "GOOGLE_API_KEY",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_PROJECT",
    "LANGCHAIN_TRACING_V2",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    # Config functions
    "find_env_file",
    "get_required_config",
    "set_env",
    "validate_config",
    # Database functions
    "close_db_engine",
    "get_db_engine",
    "get_db_session",
    "get_db_session_context",
    "test_connection",
    # Sentry
    "init_sentry",
]
