"""DTO for ProposalSubmitter entities."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProposalSubmitterDTO:
    """議案提出者情報の出力用DTO."""

    id: int
    proposal_id: int
    submitter_type: str
    politician_id: int | None
    politician_name: str | None
    parliamentary_group_id: int | None
    parliamentary_group_name: str | None
    raw_name: str | None
    is_representative: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
