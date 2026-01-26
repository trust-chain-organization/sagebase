"""Domain value objects."""

from src.domain.value_objects.judge_type import JudgeType
from src.domain.value_objects.page_classification import PageClassification, PageType
from src.domain.value_objects.politician_match import PoliticianMatch
from src.domain.value_objects.speaker_speech import SpeakerSpeech
from src.domain.value_objects.speaker_with_conversation_count import (
    SpeakerWithConversationCount,
)
from src.domain.value_objects.speaker_with_politician import SpeakerWithPolitician
from src.domain.value_objects.submitter_type import SubmitterType


__all__ = [
    "JudgeType",
    "PageClassification",
    "PageType",
    "PoliticianMatch",
    "SpeakerSpeech",
    "SpeakerWithConversationCount",
    "SpeakerWithPolitician",
    "SubmitterType",
]
