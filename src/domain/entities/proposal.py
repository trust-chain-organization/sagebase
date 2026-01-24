"""Proposal entity module."""

from src.domain.entities.base import BaseEntity


class Proposal(BaseEntity):
    """議案を表すエンティティ."""

    def __init__(
        self,
        title: str,
        detail_url: str | None = None,
        status_url: str | None = None,
        votes_url: str | None = None,
        meeting_id: int | None = None,
        conference_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.title = title
        self.detail_url = detail_url
        self.status_url = status_url
        self.votes_url = votes_url
        self.meeting_id = meeting_id
        self.conference_id = conference_id

    def __str__(self) -> str:
        identifier = f"ID:{self.id}"
        return f"Proposal {identifier}: {self.title[:50]}..."
