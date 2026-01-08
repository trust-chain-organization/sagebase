"""Domain value objects."""

from src.domain.value_objects.page_classification import PageClassification, PageType
from src.domain.value_objects.politician_match import PoliticianMatch
from src.domain.value_objects.speaker_speech import SpeakerSpeech


__all__ = [
    "PageClassification",
    "PageType",
    "PoliticianMatch",
    "SpeakerSpeech",
]
