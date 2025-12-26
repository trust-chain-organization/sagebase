"""Implementation of proposal scraping service using LLM for flexible extraction."""

import asyncio
import json
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)
from src.domain.types.scraper_types import ScrapedProposal
from src.infrastructure.constants.scraper_prompts import (
    PROPOSAL_EXTRACTION_PROMPT,
    PROPOSAL_EXTRACTION_SYSTEM_PROMPT,
)


class ProposalScraperService(IProposalScraperService):
    """Service for scraping proposal from Japanese government websites using LLM."""

    def __init__(self, llm_service: ILLMService, headless: bool = True):
        """Initialize the scraper service.

        Args:
            llm_service: LLM service for content extraction
            headless: Whether to run browser in headless mode
        """
        self.llm_service = llm_service
        self.headless = headless

    def is_supported_url(self, url: str) -> bool:
        """Check if the given URL is supported by this scraper.

        Args:
            url: URL to check

        Returns:
            True if the URL is valid (always returns True for any URL)
        """
        # Accept any URL since users will input specific URLs they want to scrape
        return bool(url and url.startswith(("http://", "https://")))

    async def scrape_proposal(self, url: str) -> ScrapedProposal:
        """Scrape proposal details from a given URL using LLM extraction.

        Args:
            url: URL of the proposal page

        Returns:
            ScrapedProposal object containing scraped information

        Raises:
            ValueError: If the URL format is not supported
            RuntimeError: If scraping fails
        """
        if not self.is_supported_url(url):
            raise ValueError(f"Invalid URL format: {url}")

        return await self._scrape_with_llm(url)

    async def _scrape_with_llm(self, url: str) -> ScrapedProposal:
        """Scrape proposal from any government website using LLM.

        Args:
            url: URL of the proposal page

        Returns:
            Dictionary containing scraped proposal information
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(1)  # Wait for dynamic content

                # Get the page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # Get text content from the page
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text content
                text_content = soup.get_text(separator="\n", strip=True)

                # Limit text content to avoid token limits
                max_chars = 10000
                if len(text_content) > max_chars:
                    text_content = text_content[:max_chars] + "..."

                # Use LLM to extract proposal information
                extraction_prompt = PROPOSAL_EXTRACTION_PROMPT.format(
                    url=url, text_content=text_content
                )

                # Call LLM to extract information
                messages = [
                    {"role": "system", "content": PROPOSAL_EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": extraction_prompt},
                ]

                llm_response = self.llm_service.invoke_llm(messages)

                # Parse the LLM response
                extracted_data: dict[str, Any]
                try:
                    # Try to parse as JSON
                    extracted_data = json.loads(llm_response)
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract from the text response
                    extracted_data = {
                        "content": "",
                        "proposal_number": None,
                        "submission_date": None,
                        "summary": None,
                    }
                    # Simple fallback extraction from LLM text response
                    if "content:" in llm_response:
                        content_match = (
                            llm_response.split("content:")[1].split("\n")[0].strip()
                        )
                        extracted_data["content"] = content_match.strip('"').strip()

                # Build the proposal data
                return ScrapedProposal(
                    url=url,
                    content=str(extracted_data.get("content", "")),
                    proposal_number=extracted_data.get("proposal_number")
                    if extracted_data.get("proposal_number")
                    else None,
                    submission_date=extracted_data.get("submission_date")
                    if extracted_data.get("submission_date")
                    else None,
                    summary=extracted_data.get("summary")
                    if extracted_data.get("summary")
                    else None,
                )

            except Exception as e:
                raise RuntimeError(
                    f"Failed to scrape proposal from {url}: {str(e)}"
                ) from e
            finally:
                await browser.close()
