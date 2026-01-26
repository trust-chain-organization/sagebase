"""DTOs for proposal parliamentary group judge use cases.

Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProposalParliamentaryGroupJudgeDTO:
    """会派/政治家賛否情報の出力用DTO.

    Many-to-Many構造に対応: 複数の会派ID/名前、政治家ID/名前をリストで保持。
    """

    id: int
    proposal_id: int
    judge_type: str
    judgment: str
    # 複数対応（リスト形式）
    parliamentary_group_ids: list[int] = field(default_factory=list)
    parliamentary_group_names: list[str] = field(default_factory=list)
    politician_ids: list[int] = field(default_factory=list)
    politician_names: list[str] = field(default_factory=list)
    member_count: int | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class CreateProposalParliamentaryGroupJudgeInputDTO:
    """会派/政治家賛否情報の作成リクエスト用DTO.

    Many-to-Many構造に対応: 複数の会派ID/政治家IDをリストで受け取る。
    """

    proposal_id: int
    judgment: str
    judge_type: str = "parliamentary_group"
    parliamentary_group_ids: list[int] = field(default_factory=list)
    politician_ids: list[int] = field(default_factory=list)
    member_count: int | None = None
    note: str | None = None


@dataclass
class ProposalParliamentaryGroupJudgeListOutputDTO:
    """会派/政治家賛否情報の一覧取得結果用DTO."""

    total_count: int
    judges: list[ProposalParliamentaryGroupJudgeDTO]
