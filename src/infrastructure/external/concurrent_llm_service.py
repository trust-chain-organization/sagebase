"""Concurrent LLM service with rate limiting and parallel processing."""

import asyncio

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types import PoliticianDTO
from src.domain.types.llm import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
)


T = TypeVar("T")


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, max_per_second: int = 5, max_concurrent: int = 10):
        """Initialize rate limiter.

        Args:
            max_per_second: Maximum requests per second
            max_concurrent: Maximum concurrent requests
        """
        self._max_per_second = max_per_second
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._last_call_times: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        async with self._semaphore:
            async with self._lock:
                now = asyncio.get_event_loop().time()

                # Remove old timestamps
                cutoff = now - 1.0
                self._last_call_times = [t for t in self._last_call_times if t > cutoff]

                # Check if we need to wait
                if len(self._last_call_times) >= self._max_per_second:
                    wait_time = 1.0 - (now - self._last_call_times[0])
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        now = asyncio.get_event_loop().time()

                self._last_call_times.append(now)


class ConcurrentLLMService(ILLMService):
    """LLM service with concurrent processing capabilities."""

    def __init__(
        self,
        base_service: ILLMService,
        max_concurrent: int = 5,
        max_per_second: int = 10,
    ):
        """Initialize concurrent LLM service.

        Args:
            base_service: The underlying LLM service
            max_concurrent: Maximum concurrent requests
            max_per_second: Maximum requests per second
        """
        self._base_service = base_service
        self._max_concurrent = max_concurrent
        self._rate_limiter = RateLimiter(
            max_per_second=max_per_second, max_concurrent=max_concurrent
        )

    async def _execute_with_rate_limit(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute function with rate limiting."""
        await self._rate_limiter.acquire()
        return await func(*args, **kwargs)

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician with rate limiting."""
        return await self._execute_with_rate_limit(
            self._base_service.match_speaker_to_politician, context
        )

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party members with rate limiting."""
        return await self._execute_with_rate_limit(
            self._base_service.extract_party_members, html_content, party_id
        )

    async def match_conference_member(
        self,
        member_name: str,
        party_name: str | None,
        candidates: list[PoliticianDTO],
    ) -> LLMMatchResult | None:
        """Match conference member with rate limiting."""
        return await self._execute_with_rate_limit(
            self._base_service.match_conference_member,
            member_name,
            party_name,
            candidates,
        )

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches with rate limiting."""
        return await self._execute_with_rate_limit(
            self._base_service.extract_speeches_from_text, text
        )

    async def process_with_concurrency_limit(
        self,
        items: list[T],
        process_func: Callable[[T], Awaitable[Any]],
        max_concurrent: int | None = None,
    ) -> list[Any]:
        """Process items with concurrency limit.

        Args:
            items: Items to process
            process_func: Async function to process each item
            max_concurrent: Maximum concurrent operations (uses default if None)

        Returns:
            List of results in the same order as input
        """
        if max_concurrent is None:
            max_concurrent = self._max_concurrent

        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_limit(item: T) -> Any:
            async with semaphore:
                await self._rate_limiter.acquire()
                return await process_func(item)

        # Process all items concurrently with limits
        tasks = [process_with_limit(item) for item in items]
        return await asyncio.gather(*tasks)

    async def batch_match_speakers_concurrent(
        self,
        contexts: list[LLMSpeakerMatchContext],
        max_concurrent: int | None = None,
    ) -> list[LLMMatchResult | None]:
        """Match multiple speakers concurrently with rate limiting.

        Args:
            contexts: List of speaker contexts to match
            max_concurrent: Maximum concurrent operations

        Returns:
            List of match results
        """

        async def match_single(
            context: LLMSpeakerMatchContext,
        ) -> LLMMatchResult | None:
            return await self._base_service.match_speaker_to_politician(context)

        return await self.process_with_concurrency_limit(
            contexts, match_single, max_concurrent
        )

    async def batch_extract_speeches_concurrent(
        self,
        text_meeting_pairs: list[tuple[str, dict[str, Any]]],
        max_concurrent: int | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Extract speeches from multiple texts concurrently.

        Args:
            text_meeting_pairs: List of (text, meeting_info) tuples
            max_concurrent: Maximum concurrent operations

        Returns:
            List of speech extraction results
        """

        async def extract_single(
            pair: tuple[str, dict[str, Any]],
        ) -> list[dict[str, Any]]:
            text, meeting_info = pair
            return await self._base_service.extract_speeches_from_text(
                text, meeting_info
            )

        return await self.process_with_concurrency_limit(
            text_meeting_pairs, extract_single, max_concurrent
        )
