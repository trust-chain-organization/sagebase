"""DTOs for proposal parliamentary group judge use cases."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProposalParliamentaryGroupJudgeDTO:
    """会派賛否情報の出力用DTO."""

    id: int
    proposal_id: int
    parliamentary_group_id: int
    parliamentary_group_name: str
    judgment: str
    member_count: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class CreateProposalParliamentaryGroupJudgeInputDTO:
    """会派賛否情報の作成リクエスト用DTO."""

    proposal_id: int
    parliamentary_group_id: int
    judgment: str
    member_count: int | None = None
    note: str | None = None


@dataclass
class ProposalParliamentaryGroupJudgeListOutputDTO:
    """会派賛否情報の一覧取得結果用DTO."""

    total_count: int
    judges: list[ProposalParliamentaryGroupJudgeDTO]
