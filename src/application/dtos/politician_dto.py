"""Politician-related DTOs."""

from dataclasses import dataclass


@dataclass
class CreatePoliticianDTO:
    """DTO for creating a politician."""

    name: str
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class UpdatePoliticianDTO:
    """DTO for updating a politician."""

    id: int
    name: str | None = None
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class PoliticianDTO:
    """DTO for politician data."""

    id: int
    name: str
    political_party_id: int | None
    political_party_name: str | None
    furigana: str | None
    district: str | None
    profile_page_url: str | None
    party_position: str | None = None
