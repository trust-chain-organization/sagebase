"""Politician entity."""

from src.domain.entities.base import BaseEntity


class Politician(BaseEntity):
    """政治家を表すエンティティ."""

    def __init__(
        self,
        name: str,
        political_party_id: int | None = None,
        furigana: str | None = None,
        district: str | None = None,
        profile_page_url: str | None = None,
        party_position: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.political_party_id = political_party_id
        self.furigana = furigana
        self.district = district
        self.profile_page_url = profile_page_url
        self.party_position = party_position

    def __str__(self) -> str:
        return self.name
