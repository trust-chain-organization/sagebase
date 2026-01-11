"""Factory functions for creating test DTOs."""

from typing import Any

from src.application.dtos.conference_dto import (
    AffiliationDTO,
    ConferenceDTO,
    ExtractedConferenceMemberDTO,
)
from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.application.dtos.politician_dto import PoliticianDTO
from src.application.dtos.speaker_dto import SpeakerDTO, SpeakerMatchingDTO


def create_process_minutes_dto(**kwargs: Any) -> ProcessMinutesDTO:
    """Create a test ProcessMinutesDTO."""
    defaults = {
        "meeting_id": 1,
        "pdf_url": None,
        "gcs_text_uri": None,
        "force_reprocess": False,
    }
    defaults.update(kwargs)
    return ProcessMinutesDTO(**defaults)


def create_extracted_speech_dto(**kwargs: Any) -> ExtractedSpeechDTO:
    """Create a test ExtractedSpeechDTO."""
    defaults = {
        "speaker_name": "山田太郎",
        "content": "これはテスト発言です。",
        "sequence_number": 1,
    }
    defaults.update(kwargs)
    return ExtractedSpeechDTO(**defaults)


def create_minutes_processing_result_dto(**kwargs: Any) -> MinutesProcessingResultDTO:
    """Create a test MinutesProcessingResultDTO."""
    defaults = {
        "minutes_id": 1,
        "meeting_id": 1,
        "total_conversations": 10,
        "unique_speakers": 5,
        "processing_time_seconds": 30.5,
        "processed_at": None,
        "errors": None,
    }
    defaults.update(kwargs)
    return MinutesProcessingResultDTO(**defaults)


def create_speaker_dto(**kwargs: Any) -> SpeakerDTO:
    """Create a test SpeakerDTO."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "type": "議員",
        "is_politician": True,
        "political_party_name": None,
        "position": None,
        "conversation_count": 0,
    }
    defaults.update(kwargs)
    return SpeakerDTO(**defaults)


def create_speaker_matching_dto(**kwargs: Any) -> SpeakerMatchingDTO:
    """Create a test SpeakerMatchingDTO."""
    defaults = {
        "speaker_id": 1,
        "speaker_name": "山田太郎",
        "matched_politician_id": None,
        "matched_politician_name": None,
        "confidence_score": 0.0,
        "matching_method": "none",
    }
    defaults.update(kwargs)
    return SpeakerMatchingDTO(**defaults)


def create_politician_dto(**kwargs: Any) -> PoliticianDTO:
    """Create a test PoliticianDTO."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "speaker_id": 1,
        "political_party_id": 1,
        "political_party_name": "自民党",
        "furigana": None,
        "district": None,
        "profile_page_url": None,
    }
    defaults.update(kwargs)
    return PoliticianDTO(**defaults)


def create_conference_dto(**kwargs: Any) -> ConferenceDTO:
    """Create a test ConferenceDTO."""
    defaults = {
        "id": 1,
        "governing_body_id": 1,
        "governing_body_name": "東京都",
        "name": "議会全体",
        "description": None,
        "is_active": True,
        "members_introduction_url": None,
        "member_count": 0,
    }
    defaults.update(kwargs)
    return ConferenceDTO(**defaults)


def create_affiliation_dto(**kwargs: Any) -> AffiliationDTO:
    """Create a test AffiliationDTO."""
    defaults = {
        "id": 1,
        "politician_id": 1,
        "politician_name": "山田太郎",
        "conference_id": 1,
        "conference_name": "議会全体",
        "start_date": "2023-01-01",
        "end_date": None,
        "role": None,
    }
    defaults.update(kwargs)
    return AffiliationDTO(**defaults)


def create_extracted_conference_member_dto(
    **kwargs: Any,
) -> ExtractedConferenceMemberDTO:
    """Create a test ExtractedConferenceMemberDTO."""
    defaults = {
        "id": 1,
        "conference_id": 1,
        "name": "山田太郎",
        "role": None,
        "party_affiliation": None,
        "matching_status": "pending",
        "confidence_score": None,
        "matched_politician_id": None,
        "source_url": "https://example.com/members",
        "extracted_at": None,
    }
    defaults.update(kwargs)
    return ExtractedConferenceMemberDTO(**defaults)
