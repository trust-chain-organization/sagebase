"""Minutes domain service for handling minutes processing business logic."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.domain.entities.conversation import Conversation
from src.domain.entities.minutes import Minutes


if TYPE_CHECKING:
    from src.application.dtos.minutes_dto import ExtractedSpeechDTO


class MinutesDomainService:
    """Domain service for minutes processing business logic."""

    def validate_minutes_url(self, url: str) -> bool:
        """Validate if URL is a valid minutes URL."""
        if not url:
            return False

        # Check for common patterns
        valid_extensions = [".pdf", ".html", ".htm"]
        valid_domains = ["kaigiroku.net", ".go.jp", ".lg.jp"]

        url_lower = url.lower()
        has_valid_extension = any(ext in url_lower for ext in valid_extensions)
        has_valid_domain = any(domain in url_lower for domain in valid_domains)

        return has_valid_extension or has_valid_domain

    def extract_meeting_info_from_url(self, url: str) -> tuple[str | None, str | None]:
        """Extract meeting date and name from URL if possible."""
        import re

        # Try to extract date pattern (YYYY-MM-DD or YYYYMMDD)
        date_pattern = r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})"
        date_match = re.search(date_pattern, url)

        meeting_date = None
        if date_match:
            year, month, day = date_match.groups()
            meeting_date = f"{year}-{month}-{day}"

        # Try to extract meeting name from URL
        meeting_name = None
        name_patterns = [
            r"/([\u4e00-\u9fa5]+会議?)/",  # Japanese meeting names
            r"/([\u4e00-\u9fa5]+委員会)/",  # Committee names
        ]

        for pattern in name_patterns:
            match = re.search(pattern, url)
            if match:
                meeting_name = match.group(1)
                break

        return meeting_date, meeting_name

    def create_conversations_from_speeches(
        self,
        speeches: list[dict[str, Any]] | list["ExtractedSpeechDTO"],
        minutes_id: int,
        chapter_number: int = 1,
    ) -> list[Conversation]:
        """Create conversation entities from extracted speeches."""
        conversations: list[Conversation] = []

        for idx, speech in enumerate(speeches):
            if isinstance(speech, dict):
                speaker_name = speech.get("speaker", "").strip()
                content = speech.get("content", "").strip()
            else:  # ExtractedSpeechDTO
                speaker_name = speech.speaker_name.strip()
                content = speech.content.strip()

            if not content:
                continue

            conversation = Conversation(
                comment=content,
                sequence_number=idx + 1,
                minutes_id=minutes_id,
                speaker_name=speaker_name if speaker_name else None,
                chapter_number=chapter_number,
                sub_chapter_number=None,
            )
            conversations.append(conversation)

        return conversations

    def split_long_conversation(
        self,
        conversation: Conversation,
        max_length: int = 1000,
    ) -> list[Conversation]:
        """Split long conversation into smaller chunks."""
        if len(conversation.comment) <= max_length:
            return [conversation]

        # Split by sentences first
        sentences = self._split_into_sentences(conversation.comment)

        chunks: list[Conversation] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            if current_length + sentence_length > max_length and current_chunk:
                # Create conversation for current chunk
                chunk_text = "".join(current_chunk)
                chunk_conv = Conversation(
                    comment=chunk_text,
                    sequence_number=conversation.sequence_number,
                    minutes_id=conversation.minutes_id,
                    speaker_id=conversation.speaker_id,
                    speaker_name=conversation.speaker_name,
                    chapter_number=conversation.chapter_number,
                    sub_chapter_number=len(chunks) + 1,
                )
                chunks.append(chunk_conv)

                # Start new chunk
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add remaining chunk
        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunk_conv = Conversation(
                comment=chunk_text,
                sequence_number=conversation.sequence_number,
                minutes_id=conversation.minutes_id,
                speaker_id=conversation.speaker_id,
                speaker_name=conversation.speaker_name,
                chapter_number=conversation.chapter_number,
                sub_chapter_number=len(chunks) + 1,
            )
            chunks.append(chunk_conv)

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Japanese sentence endings
        sentence_endings = ["。", "！", "？", "\n"]

        sentences: list[str] = []
        current: list[str] = []

        for char in text:
            current.append(char)
            if char in sentence_endings:
                sentences.append("".join(current))
                current: list[str] = []

        # Add remaining text
        if current:
            sentences.append("".join(current))

        return sentences

    def calculate_processing_duration(
        self, start_time: datetime, end_time: datetime
    ) -> float:
        """Calculate processing duration in seconds."""
        duration = end_time - start_time
        return duration.total_seconds()

    def is_minutes_processed(self, minutes: Minutes) -> bool:
        """Check if minutes have been processed."""
        return minutes.processed_at is not None

    def validate_conversation_sequence(
        self, conversations: list[Conversation]
    ) -> list[str]:
        """Validate conversation sequence and return issues."""
        issues: list[str] = []

        if not conversations:
            return ["No conversations found"]

        # Check sequence numbers
        sequence_numbers = [c.sequence_number for c in conversations]
        expected_sequence = list(range(1, len(conversations) + 1))

        if sorted(sequence_numbers) != expected_sequence:
            issues.append("Sequence numbers are not continuous")

        # Check for empty content
        empty_count = sum(1 for c in conversations if not c.comment.strip())
        if empty_count > 0:
            issues.append(f"{empty_count} conversations have empty content")

        return issues
