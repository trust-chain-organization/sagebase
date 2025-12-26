"""Base DTOs for Streamlit web interface.

This module provides base Data Transfer Objects for the web interface layer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass
class BaseWebDTO:
    """Base class for all web DTOs."""

    def to_dict(self) -> dict[str, Any]:
        """Convert DTO to dictionary.

        Returns:
            Dictionary representation of the DTO
        """
        return {
            k: v.isoformat() if isinstance(v, datetime) else v
            for k, v in self.__dict__.items()
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseWebDTO":
        """Create DTO from dictionary.

        Args:
            data: Dictionary containing DTO data

        Returns:
            Instance of the DTO
        """
        return cls(**data)


@dataclass
class PaginationDTO(BaseWebDTO):
    """DTO for pagination parameters."""

    page: int = 1
    per_page: int = 20
    total_items: int = 0
    total_pages: int = 0

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


@dataclass
class FilterDTO(BaseWebDTO):
    """Base DTO for filter parameters."""

    search_text: str | None = None
    order_by: str | None = None
    order_direction: str = "asc"

    def validate(self) -> bool:
        """Validate filter parameters.

        Returns:
            True if valid, False otherwise
        """
        if self.order_direction not in ["asc", "desc"]:
            return False
        return True


@dataclass
class WebResponseDTO(BaseWebDTO, Generic[T]):  # noqa: UP046
    """Generic response DTO for web operations."""

    success: bool
    data: T | None = None
    message: str | None = None
    errors: list[str] | None = None

    @classmethod
    def success_response(
        cls, data: T, message: str | None = None
    ) -> "WebResponseDTO[T]":
        """Create a success response.

        Args:
            data: The response data
            message: Optional success message

        Returns:
            Success response DTO
        """
        return cls(success=True, data=data, message=message)

    @classmethod
    def error_response(
        cls, message: str, errors: list[str] | None = None
    ) -> "WebResponseDTO[T]":
        """Create an error response.

        Args:
            message: Error message
            errors: List of detailed errors

        Returns:
            Error response DTO
        """
        return cls(success=False, message=message, errors=errors)


@dataclass
class FormStateDTO(BaseWebDTO):
    """Base DTO for form states in Streamlit."""

    is_editing: bool = False
    is_creating: bool = False
    is_loading: bool = False
    current_id: int | None = None
    validation_errors: dict[str, str] | None = None

    def reset(self) -> None:
        """Reset form state to initial values."""
        self.is_editing = False
        self.is_creating = False
        self.is_loading = False
        self.current_id = None
        self.validation_errors = None

    def set_editing(self, entity_id: int) -> None:
        """Set state to editing mode.

        Args:
            entity_id: ID of the entity being edited
        """
        self.reset()
        self.is_editing = True
        self.current_id = entity_id

    def set_creating(self) -> None:
        """Set state to creating mode."""
        self.reset()
        self.is_creating = True
