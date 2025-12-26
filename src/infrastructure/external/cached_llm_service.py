"""Cached LLM service implementation with deduplication and batching."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.types import PoliticianDTO
from src.domain.types.llm import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
)
from src.infrastructure.external.llm_service import GeminiLLMService


class LLMCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, ttl_minutes: int = 60):
        """Initialize cache with TTL in minutes."""
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)

    def _generate_key(self, prompt: str, context: Any = None) -> str:
        """Generate cache key from prompt and context."""
        content = prompt
        if context:
            if hasattr(context, "model_dump_json"):
                content += context.model_dump_json()
            elif isinstance(context, dict):
                # Handle dictionary contexts
                content += json.dumps(context, sort_keys=True, default=str)
            elif hasattr(context, "__dict__"):
                try:
                    content += json.dumps(context.__dict__, sort_keys=True, default=str)
                except (TypeError, ValueError):
                    content += str(id(context))  # Use object ID for mocks
            else:
                content += str(id(context))

        # Ensure content is always a string
        if not isinstance(content, str):
            content = str(content)

        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    def get(self, prompt: str, context: Any = None) -> Any | None:
        """Get cached result if available and not expired."""
        key = self._generate_key(prompt, context)

        if key in self._cache:
            result, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return result
            else:
                # Remove expired entry
                del self._cache[key]

        return None

    def set(self, prompt: str, context: Any, result: Any) -> None:
        """Cache the result."""
        key = self._generate_key(prompt, context)
        self._cache[key] = (result, datetime.now())

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        total = len(self._cache)
        expired = sum(
            1
            for _, (_, timestamp) in self._cache.items()
            if datetime.now() - timestamp >= self._ttl
        )
        return {
            "total_entries": total,
            "active_entries": total - expired,
            "expired_entries": expired,
        }


class CachedLLMService(ILLMService):
    """LLM service with caching and batching capabilities."""

    def __init__(
        self,
        base_service: GeminiLLMService,
        cache_ttl_minutes: int = 60,
        enable_batching: bool = True,
    ):
        """Initialize cached LLM service.

        Args:
            base_service: The underlying LLM service
            cache_ttl_minutes: Cache TTL in minutes
            enable_batching: Whether to enable batch processing
        """
        self._base_service = base_service
        self._cache = LLMCache(ttl_minutes=cache_ttl_minutes)
        self._enable_batching = enable_batching
        self._pending_batch: list[tuple[str, Any, Any]] = []

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician with caching.

        Args:
            context: Speaker matching context

        Returns:
            Match result or None if no match
        """
        # Check cache first
        cached = self._cache.get("match_speaker", context)
        if cached is not None:
            return cached

        # Call base service
        result = await self._base_service.match_speaker_to_politician(context)

        # Cache the result
        self._cache.set("match_speaker", context, result)

        return result

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract party members with caching.

        Args:
            html_content: HTML content to parse
            party_id: Political party ID

        Returns:
            Extraction result with member information
        """
        # Check cache
        cache_context = {
            "html_hash": hashlib.md5(
                html_content.encode(), usedforsecurity=False
            ).hexdigest(),
            "party_id": party_id,
        }
        cached = self._cache.get("extract_members", cache_context)
        if cached is not None:
            return cached

        # Call base service
        result = await self._base_service.extract_party_members(html_content, party_id)

        # Cache the result
        self._cache.set("extract_members", cache_context, result)

        return result

    async def match_conference_member(
        self,
        member_name: str,
        party_name: str | None,
        candidates: list[PoliticianDTO],
    ) -> LLMMatchResult | None:
        """Match conference member with caching.

        Args:
            member_name: Member name to match
            party_name: Party affiliation if known
            candidates: List of candidate politicians

        Returns:
            Match result or None if no match
        """
        # Create cache context
        cache_context = {
            "member_name": member_name,
            "party_name": party_name,
            "politician_count": len(candidates),
            "politician_names": [
                p["name"] for p in candidates[:10]
            ],  # Sample for cache key
        }

        # Check cache
        cached = self._cache.get("match_conference_member", cache_context)
        if cached is not None:
            return cached

        # Call base service
        result = await self._base_service.match_conference_member(
            member_name, party_name, candidates
        )

        # Cache the result
        self._cache.set("match_conference_member", cache_context, result)

        return result

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches with caching.

        Args:
            text: Text to extract speeches from

        Returns:
            List of extracted speeches
        """
        # Create cache context
        cache_context = {
            "text_hash": hashlib.md5(text.encode(), usedforsecurity=False).hexdigest(),
        }

        # Check cache
        cached = self._cache.get("extract_speeches", cache_context)
        if cached is not None:
            return cached

        # Call base service
        result = await self._base_service.extract_speeches_from_text(text)

        # Cache the result
        self._cache.set("extract_speeches", cache_context, result)

        return result

    async def batch_match_speakers(
        self, contexts: list[LLMSpeakerMatchContext]
    ) -> list[LLMMatchResult | None]:
        """Batch process multiple speaker matching requests.

        Args:
            contexts: List of speaker matching contexts

        Returns:
            List of match results
        """
        if not self._enable_batching or len(contexts) <= 1:
            # Fall back to individual processing
            results = []
            for context in contexts:
                result = await self.match_speaker_to_politician(context)
                results.append(result)
            return results

        # Check cache for each context
        results = []
        uncached_contexts = []
        uncached_indices = []

        for i, context in enumerate(contexts):
            cached = self._cache.get("match_speaker", context)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)  # Placeholder
                uncached_contexts.append(context)
                uncached_indices.append(i)

        # Process uncached items in batch
        if uncached_contexts:
            # Create a combined prompt for batch processing
            # This is a simplified example - actual implementation would need
            # to handle the batch response parsing
            batch_results = []
            for context in uncached_contexts:
                result = await self._base_service.match_speaker_to_politician(context)
                batch_results.append(result)
                self._cache.set("match_speaker", context, result)

            # Fill in the results
            for i, result in zip(uncached_indices, batch_results, strict=False):
                results[i] = result

        return results

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return self._cache.stats()
