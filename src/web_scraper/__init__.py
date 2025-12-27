"""Web scraper module for extracting minutes from various council websites"""

from .base_scraper import BaseScraper
from .exceptions import (
    CacheError,
    GCSUploadError,
    PDFDownloadError,
    PDFExtractionError,
    ScraperConnectionError,
    ScraperError,
    ScraperParseError,
    ScraperTimeoutError,
)
from .kaigiroku_net_scraper import KaigirokuNetScraper
from .models import MinutesData, SpeakerData
from .scraper_service import ScraperService


__all__ = [
    # Base classes
    "BaseScraper",
    # Models
    "MinutesData",
    "SpeakerData",
    # Scrapers
    "KaigirokuNetScraper",
    "ScraperService",
    # Exceptions
    "ScraperError",
    "ScraperConnectionError",
    "ScraperParseError",
    "ScraperTimeoutError",
    "PDFDownloadError",
    "PDFExtractionError",
    "CacheError",
    "GCSUploadError",
]
