"""提出者候補一覧のDTO."""

from dataclasses import dataclass


@dataclass
class PoliticianCandidateDTO:
    """議員候補のDTO."""

    id: int
    name: str


@dataclass
class ParliamentaryGroupCandidateDTO:
    """会派候補のDTO."""

    id: int
    name: str


@dataclass
class SubmitterCandidatesDTO:
    """提出者候補一覧のDTO."""

    conference_id: int
    politicians: list[PoliticianCandidateDTO]
    parliamentary_groups: list[ParliamentaryGroupCandidateDTO]
