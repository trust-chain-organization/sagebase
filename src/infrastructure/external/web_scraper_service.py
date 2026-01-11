"""Web scraper service implementation using Playwright."""

from typing import Any

from src.domain.services.interfaces.web_scraper_service import IWebScraperService


class PlaywrightScraperService(IWebScraperService):
    """Playwright-based implementation of web scraper."""

    def __init__(self, headless: bool = True, llm_service: Any | None = None):
        """Initialize the PlaywrightScraperService.

        Args:
            headless: Whether to run the browser in headless mode
            llm_service: Optional LLM service for content extraction.
                        If not provided, a default GeminiLLMService will be created.
        """
        self.headless = headless
        self._llm_service = llm_service
        # Initialize Playwright here

    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported for scraping.

        Args:
            url: URL to check

        Returns:
            True if the URL is supported, False otherwise
        """
        # Support common Japanese government and council websites
        supported_domains = [
            "kaigiroku.net",
            "metro.tokyo.lg.jp",
            "pref.kyoto.lg.jp",
            "pref.osaka.lg.jp",
            "city.kyoto.lg.jp",
            "city.osaka.lg.jp",
            "shugiin.go.jp",
            "sangiin.go.jp",
        ]

        return any(domain in url for domain in supported_domains)

    async def fetch_html(self, url: str) -> str:
        """Fetch raw HTML content from a URL using Playwright.

        Args:
            url: URL to fetch

        Returns:
            Raw HTML content as string

        Raises:
            ValueError: If URL is invalid or inaccessible
        """
        import logging

        from playwright.async_api import async_playwright

        logger = logging.getLogger(__name__)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Navigate to the URL
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for content to load
                await page.wait_for_load_state("domcontentloaded")

                # Get the HTML content
                html_content = await page.content()

                await browser.close()

                logger.debug(f"Fetched HTML from {url} ({len(html_content)} bytes)")
                return html_content

        except Exception as e:
            logger.error(f"Failed to fetch HTML from {url}: {e}")
            raise ValueError(f"Failed to fetch HTML from {url}: {e}") from e

    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference members using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return [
            {
                "name": "佐藤花子",
                "party": "○○党",
                "role": "議長",
                "profile_url": "https://example.com/member/1",
            }
        ]

    async def scrape_meeting_minutes(
        self, url: str, upload_to_gcs: bool = False
    ) -> dict[str, Any]:
        """Scrape meeting minutes using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return {
            "meeting_date": "2024-01-15",
            "meeting_name": "本会議",
            "pdf_url": "https://example.com/minutes.pdf",
            "text_content": "会議の内容...",
            "gcs_pdf_uri": "gs://bucket/minutes.pdf" if upload_to_gcs else None,
            "gcs_text_uri": "gs://bucket/minutes.txt" if upload_to_gcs else None,
        }

    async def scrape_proposal_judges(self, url: str) -> list[dict[str, Any]]:
        """Scrape proposal voting information from website.

        Args:
            url: URL of the proposal voting results page

        Returns:
            List of voting information with name, party, and judgment
        """
        import logging

        from playwright.async_api import async_playwright

        from src.domain.services.proposal_judge_extraction_service import (
            ProposalJudgeExtractionService,
        )

        logger = logging.getLogger(__name__)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Navigate to the URL
                await page.goto(url, wait_until="networkidle")

                # Wait for content to load
                await page.wait_for_load_state("domcontentloaded")

                # Get the page content
                text_content = await page.inner_text("body")

                await browser.close()

                # Use LLM to extract voting information
                # Use injected service or create default
                if self._llm_service:
                    llm_service = self._llm_service
                else:
                    from src.infrastructure.external.llm_service import GeminiLLMService

                    llm_service = GeminiLLMService()

                # Extract voting information using LLM
                import json

                from langchain_core.prompts import ChatPromptTemplate

                prompt = f"""
以下のウェブページから議案の賛否情報を抽出してください。

ページのURL: {url}
ページの内容:
{text_content[:8000]}

以下の形式のJSON配列として返してください。会派名や議員団名が記載されている場合は、その単位で抽出してください：
[
    {{"name": "会派名または議員名", "party": "所属政党（わかる場合）",
      "judgment": "賛成または反対または棄権または欠席"}},
    ...
]

注意事項:
- 会派名（例：自由民主党議員団など）で賛否が記載されている場合は会派名をnameに記載
- 個別の議員名が記載されている場合は、議員名をnameに記載
- 賛成は「賛成」、反対は「反対」、棄権は「棄権」、欠席は「欠席」と記載
- 敬称（議員、君、さん等）は除去
- JSONのみを返し、他の説明文は含めない
"""

                try:
                    # Use the LLM directly for extraction
                    if hasattr(llm_service, "get_llm"):
                        llm = llm_service.get_llm()  # type: ignore
                    elif hasattr(llm_service, "_llm"):
                        llm = llm_service._llm  # type: ignore
                    else:
                        llm = llm_service.get_structured_llm(dict)

                    # Create prompt template
                    prompt_template = ChatPromptTemplate.from_template("{text}")
                    chain = prompt_template | llm

                    # Get response
                    response = await chain.ainvoke({"text": prompt})

                    # Parse response
                    if hasattr(response, "content"):
                        response_text = response.content
                    else:
                        response_text = str(response)

                    # Ensure response_text is a string
                    if not isinstance(response_text, str):
                        response_text = str(response_text)

                    # Try to extract JSON from the response
                    # Remove markdown code blocks if present
                    response_text = response_text.strip()
                    if response_text.startswith("```json"):
                        response_text = response_text[7:]
                    if response_text.startswith("```"):
                        response_text = response_text[3:]
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]

                    response_text = response_text.strip()

                    # Parse JSON
                    judges_data = json.loads(response_text)

                    count = len(judges_data) if isinstance(judges_data, list) else 0
                    logger.info(f"Successfully extracted {count} judges from {url}")

                except Exception as parse_error:
                    logger.warning(
                        f"Failed to parse LLM response as JSON: {parse_error}"
                    )
                    # Fallback: try to parse text content
                    judges_data = (
                        ProposalJudgeExtractionService.parse_voting_result_text(
                            text_content
                        )
                    )

                # Process the extracted data
                if isinstance(judges_data, list):
                    # Normalize the data using domain service
                    normalized_judges = []
                    for judge in judges_data:
                        judgment_text = judge.get("judgment", "")
                        normalized_judgment, is_known = (
                            ProposalJudgeExtractionService.normalize_judgment_type(
                                judgment_text
                            )
                        )

                        # Log unknown judgment types
                        if not is_known:
                            logger.warning(
                                f"Unknown judgment type: {judgment_text}, "
                                f"defaulting to APPROVE"
                            )

                        normalized_judges.append(
                            {
                                "name": (
                                    ProposalJudgeExtractionService.normalize_politician_name(
                                        judge.get("name", "")
                                    )
                                ),
                                "party": judge.get("party"),
                                "judgment": normalized_judgment,
                            }
                        )
                    return normalized_judges

                # If not a list, try text parsing
                return ProposalJudgeExtractionService.parse_voting_result_text(
                    text_content
                )

        except Exception as e:
            logger.error(f"Failed to scrape proposal judges from {url}: {e}")
            return []
