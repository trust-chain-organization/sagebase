"""Domain service interfaces."""

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.domain.services.interfaces.politician_matching_service import (
    IPoliticianMatchingService,
)
from src.domain.services.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)
from src.domain.services.interfaces.web_scraper_service import IWebScraperService


__all__ = [
    "ILLMService",
    "IMinutesProcessingService",
    "IPageClassifierService",
    "IPoliticianMatchingService",
    "IProposalScraperService",
    "IWebScraperService",
]
