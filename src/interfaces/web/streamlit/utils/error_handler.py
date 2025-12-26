"""Error handling utilities for Streamlit interface.

This module provides centralized error handling for the Streamlit UI,
including user-friendly error messages and logging.
"""

import functools
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

import streamlit as st
from src.common.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class UIError(Exception):
    """Base exception for UI-related errors."""

    def __init__(self, message: str, details: str | None = None):
        """Initialize UI error.

        Args:
            message: User-friendly error message
            details: Technical details for logging
        """
        super().__init__(message)
        self.message = message
        self.details = details


def handle_ui_error(error: Exception, context: str = "") -> None:
    """Handle errors in a user-friendly way.

    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
    """
    # Log the full error with traceback
    logger.error(
        f"Error in {context}: {str(error)}",
        exc_info=True,
        extra={"traceback": traceback.format_exc()},
    )

    # Show user-friendly message
    if isinstance(error, UIError):
        st.error(f"❌ {error.message}")
        if error.details:
            with st.expander("技術的な詳細"):
                st.code(error.details)
    else:
        # Generic error message for unexpected errors
        st.error(f"❌ エラーが発生しました: {str(error)}")
        with st.expander("技術的な詳細"):
            st.code(traceback.format_exc())


def with_error_handling(
    context: str = "",
    show_success: bool = True,
    success_message: str = "✅ 操作が成功しました",
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """Decorator for handling errors in Streamlit functions.

    Args:
        context: Context for error messages
        show_success: Whether to show success message
        success_message: Success message to show

    Returns:
        Decorated function with error handling
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T | None:
            try:
                result = func(*args, **kwargs)
                if show_success:
                    st.success(success_message)
                return result
            except Exception as e:
                handle_ui_error(e, context or func.__name__)
                return None

        return wrapper

    return decorator


async def with_async_error_handling(
    context: str = "",
    show_success: bool = True,
    success_message: str = "✅ 操作が成功しました",
) -> Callable[[Callable[..., T]], Callable[..., T | None]]:
    """Decorator for handling errors in async Streamlit functions.

    Args:
        context: Context for error messages
        show_success: Whether to show success message
        success_message: Success message to show

    Returns:
        Decorated async function with error handling
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | None]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T | None:
            try:
                result = await func(*args, **kwargs)
                if show_success:
                    st.success(success_message)
                return result
            except Exception as e:
                handle_ui_error(e, context or func.__name__)
                return None

        return wrapper  # type: ignore[return-value]

    return decorator


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    """Validate that required fields are present and not empty.

    Args:
        data: Data dictionary to validate
        required_fields: List of required field names

    Raises:
        UIError: If validation fails
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)

    if missing_fields:
        raise UIError(
            f"必須フィールドが入力されていません: {', '.join(missing_fields)}",
            f"Missing fields: {missing_fields}",
        )


def validate_positive_number(value: Any, field_name: str) -> None:
    """Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Raises:
        UIError: If validation fails
    """
    try:
        num_value = float(value)
        if num_value <= 0:
            raise ValueError("Value must be positive")
    except (ValueError, TypeError) as e:
        raise UIError(
            f"{field_name}は正の数値である必要があります", f"Invalid number: {value}"
        ) from e


def safe_int_conversion(value: Any, field_name: str) -> int:
    """Safely convert a value to integer.

    Args:
        value: Value to convert
        field_name: Name of the field for error messages

    Returns:
        Integer value

    Raises:
        UIError: If conversion fails
    """
    try:
        return int(value)
    except (ValueError, TypeError) as e:
        raise UIError(
            f"{field_name}は整数である必要があります", f"Cannot convert to int: {value}"
        ) from e
