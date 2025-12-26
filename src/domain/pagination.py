"""Pagination models and utilities for domain layer."""

from dataclasses import dataclass
from typing import Any, TypeVar


T = TypeVar("T")


@dataclass
class PaginationParams:
    """Parameters for pagination."""

    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.per_page

    def validate(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.per_page < 1:
            raise ValueError("Per page must be >= 1")
        if self.per_page > 100:
            raise ValueError("Per page must be <= 100")


@dataclass
class PaginatedResult[T]:
    """Result container for paginated queries."""

    items: list[T]
    total_count: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.total_count == 0:
            return 0
        return (self.total_count + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1

    @property
    def next_page(self) -> int | None:
        """Get next page number if available."""
        return self.page + 1 if self.has_next else None

    @property
    def previous_page(self) -> int | None:
        """Get previous page number if available."""
        return self.page - 1 if self.has_previous else None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "items": self.items,
            "pagination": {
                "total_count": self.total_count,
                "total_pages": self.total_pages,
                "current_page": self.page,
                "per_page": self.per_page,
                "has_next": self.has_next,
                "has_previous": self.has_previous,
                "next_page": self.next_page,
                "previous_page": self.previous_page,
            },
        }
