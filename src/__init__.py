"""
Polibase package

Political Activity Tracking Application for managing and analyzing
Japanese political activities.
"""

# Export exceptions for easier access
from src.domain.exceptions import (
    BusinessRuleViolationException,
    DuplicateEntityException,
    EntityNotFoundException,
    PolibaseError,
)
from src.infrastructure.exceptions import (
    APIKeyError,
    ConnectionError,
    DatabaseError,
    DeleteException,
    DownloadException,
    ElementNotFoundException,
    FileNotFoundException,
    IntegrityError,
    LLMError,
    PageLoadException,
    PermissionError,
    QueryException,
    RecordNotFoundError,
    ResponseParsingException,
    SaveError,
    ScrapingError,
    StorageError,
    TokenLimitException,
    UpdateError,
    UploadException,
    URLException,
)


__all__ = [
    # Base exception
    "PolibaseError",
    # Domain exceptions
    "EntityNotFoundException",
    "BusinessRuleViolationException",
    "DuplicateEntityException",
    # Database
    "DatabaseError",
    "ConnectionError",
    "QueryException",
    "IntegrityError",
    "RecordNotFoundError",
    # LLM/AI
    "LLMError",
    "APIKeyError",
    "TokenLimitException",
    "ResponseParsingException",
    # Web Scraping
    "ScrapingError",
    "URLException",
    "PageLoadException",
    "ElementNotFoundException",
    "DownloadException",
    # Storage
    "StorageError",
    "FileNotFoundException",
    "UploadException",
    "PermissionError",
    # Repository
    "SaveError",
    "UpdateError",
    "DeleteException",
]

__version__ = "0.1.0"
