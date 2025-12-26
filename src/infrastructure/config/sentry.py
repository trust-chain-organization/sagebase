"""Sentry error tracking configuration and initialization

This module handles Sentry SDK initialization with environment-specific
settings and integrations.
"""

import logging
import os
from collections.abc import Callable
from typing import Any, Literal, TypeVar, cast

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.types import Event

from .settings import get_settings


F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)
# Global flag to track if Sentry has been initialized
initialized: bool = False


def init_sentry() -> None:
    """Initialize Sentry SDK with environment configuration

    This function sets up Sentry for error tracking with the following features:
    - Automatic error capture
    - Performance monitoring
    - SQLAlchemy integration
    - Logging integration
    - Environment-aware configuration

    Note: This function ensures Sentry is only initialized once per process.
    """
    global initialized

    # Check if already initialized
    if initialized:
        logger.debug("Sentry is already initialized, skipping...")
        return

    settings = get_settings()

    # Get Sentry DSN from environment
    dsn = os.getenv("SENTRY_DSN", "")

    if not dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        initialized = True  # Mark as initialized even when skipped
        return

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development")

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    # Configure SQLAlchemy integration
    sqlalchemy_integration = SqlalchemyIntegration()

    # Performance monitoring sample rate
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

    # Initialize Sentry
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            integrations=[
                logging_integration,
                sqlalchemy_integration,
            ],
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personally identifiable information
            release=os.getenv("SENTRY_RELEASE", "sagebase@0.1.0"),
            debug=settings.debug,
            before_send=before_send_filter,
            before_send_transaction=before_send_transaction_filter,
        )

        logger.info(f"Sentry initialized successfully for environment: {environment}")
        initialized = True  # Mark as successfully initialized

        # Set user context if available
        if user_id := os.getenv("SENTRY_USER_ID"):
            sentry_sdk.set_user({"id": user_id})

        # Set additional context
        sentry_sdk.set_context(
            "app",
            {
                "version": "0.1.0",
                "llm_model": settings.llm_model,
            },
        )

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event: Event, hint: dict[str, Any]) -> Event | None:
    """Filter events before sending to Sentry

    This function allows filtering out sensitive data or unwanted events.

    Args:
        event: The event dictionary
        hint: Additional information about the event

    Returns:
        Modified event or None to drop the event
    """
    # Filter out specific error types if needed
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Example: Don't send KeyboardInterrupt
        if exc_type is KeyboardInterrupt:
            return None

    # Remove sensitive data from event
    event_dict = cast(dict[str, Any], event)
    if "request" in event_dict and "data" in event_dict["request"]:
        # Remove any API keys or sensitive data from request
        if isinstance(event_dict["request"]["data"], dict):
            for key in ["api_key", "password", "token", "secret"]:
                event_dict["request"]["data"].pop(key, None)

    # Sanitize error messages
    if "exception" in event_dict and "values" in event_dict["exception"]:
        for exception in event_dict["exception"]["values"]:
            if "value" in exception:
                # Remove any API keys from error messages
                exception["value"] = sanitize_message(exception["value"])

    return cast(Event, event_dict)


def before_send_transaction_filter(event: Event, hint: dict[str, Any]) -> Event | None:
    """Filter performance transactions before sending to Sentry

    Args:
        event: The transaction event
        hint: Additional information

    Returns:
        Modified event or None to drop the transaction
    """
    # Filter out health check endpoints
    event_dict = cast(dict[str, Any], event)
    if event_dict.get("transaction") in ["/health", "/metrics", "/ping"]:
        return None

    return event


def sanitize_message(message: str) -> str:
    """Sanitize error messages to remove sensitive information

    Args:
        message: The error message

    Returns:
        Sanitized message
    """
    import re

    # List of patterns to redact
    sensitive_patterns = [
        # API keys with values
        (r"GOOGLE_API_KEY\s*=\s*[\w\-\.]+", "[REDACTED_API_KEY]"),
        (r"SENTRY_DSN\s*=\s*[\w\-\.\:\/\@]+", "[REDACTED_SENTRY_DSN]"),
        (r"DATABASE_URL\s*=\s*[\w\-\.\:\/\@]+", "[REDACTED_DATABASE_URL]"),
        # PostgreSQL URLs
        (r"postgresql://[^\s]+", "postgresql://[REDACTED]"),
        (r"postgres://[^\s]+", "postgres://[REDACTED]"),
        # Generic API keys and tokens
        (r"api[_\-]?key\s*[:=]\s*[\w\-\.]+", "api_key=[REDACTED]"),
        (r"token\s*[:=]\s*[\w\-\.]+", "token=[REDACTED]"),
        (r"secret\s*[:=]\s*[\w\-\.]+", "secret=[REDACTED]"),
    ]

    sanitized = message
    for pattern, replacement in sensitive_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def capture_message(
    message: str,
    level: Literal["debug", "info", "warning", "error", "fatal"] = "info",
    **kwargs: Any,
) -> None:
    """Capture a message to Sentry

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        **kwargs: Additional context
    """
    sentry_sdk.capture_message(message, level=level, **kwargs)


def capture_exception(error: Exception | None = None, **kwargs: Any) -> None:
    """Capture an exception to Sentry

    Args:
        error: The exception to capture (or current exception if None)
        **kwargs: Additional context
    """
    sentry_sdk.capture_exception(error, **kwargs)


def add_breadcrumb(message: str, category: str | None = None, **kwargs: Any) -> None:
    """Add a breadcrumb for context

    Args:
        message: Breadcrumb message
        category: Category for grouping
        **kwargs: Additional data
    """
    sentry_sdk.add_breadcrumb(message=message, category=category, **kwargs)


def set_context(name: str, value: dict[str, Any]) -> None:
    """Set custom context

    Args:
        name: Context name
        value: Context data
    """
    sentry_sdk.set_context(name, value)


def set_tag(key: str, value: str) -> None:
    """Set a tag for filtering

    Args:
        key: Tag key
        value: Tag value
    """
    sentry_sdk.set_tag(key, value)


def start_transaction(name: str, op: str = "task", **kwargs: Any) -> Any:
    """Start a performance monitoring transaction

    Args:
        name: Transaction name
        op: Operation type (task, http.server, db.query, etc.)
        **kwargs: Additional transaction attributes

    Returns:
        Transaction object
    """
    return sentry_sdk.start_transaction(name=name, op=op, **kwargs)


def monitor_performance(
    op: str = "task", description: str | None = None
) -> Callable[[F], F]:
    """Decorator for monitoring function performance

    Args:
        op: Operation type
        description: Optional description

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            transaction_name = description or f"{func.__module__}.{func.__name__}"
            with sentry_sdk.start_transaction(
                op=op, name=transaction_name
            ) as transaction:
                try:
                    result = func(*args, **kwargs)
                    transaction.set_status("ok")
                    return result
                except Exception:
                    transaction.set_status("internal_error")
                    raise

        return cast(F, wrapper)

    return decorator


def monitor_db_query(query_name: str):
    """Decorator for monitoring database queries

    Args:
        query_name: Name of the query for tracking

    Returns:
        Decorated function
    """
    return monitor_performance(op="db.query", description=query_name)


def monitor_llm_call(model: str | None = None) -> Callable[[F], F]:
    """Decorator for monitoring LLM API calls

    Args:
        model: LLM model name

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = f"llm.{model}" if model else "llm.call"
            with sentry_sdk.start_transaction(
                op=op_name, name=func.__name__
            ) as transaction:
                transaction.set_tag("llm.model", model or "unknown")
                try:
                    result = func(*args, **kwargs)
                    transaction.set_status("ok")
                    return result
                except Exception:
                    transaction.set_status("internal_error")
                    raise

        return cast(F, wrapper)

    return decorator


def monitor_web_scraping(url: str | None = None) -> Callable[[F], F]:
    """Decorator for monitoring web scraping operations

    Args:
        url: URL being scraped

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with sentry_sdk.start_transaction(
                op="http.client", name=func.__name__
            ) as transaction:
                if url:
                    transaction.set_tag("url", url)
                try:
                    result = func(*args, **kwargs)
                    transaction.set_status("ok")
                    return result
                except Exception:
                    transaction.set_status("internal_error")
                    raise

        return cast(F, wrapper)

    return decorator
