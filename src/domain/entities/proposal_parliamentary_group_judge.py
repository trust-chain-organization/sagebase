"""ProposalParliamentaryGroupJudge entity module."""

from src.domain.entities.base import BaseEntity
from src.domain.value_objects.judge_type import JudgeType


class ProposalParliamentaryGroupJudge(BaseEntity):
    """議案への会派/政治家単位の賛否情報を表すエンティティ.

    Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
    """

    def __init__(
        self,
        proposal_id: int,
        judgment: str,
        judge_type: JudgeType = JudgeType.PARLIAMENTARY_GROUP,
        parliamentary_group_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
        member_count: int | None = None,
        note: str | None = None,
        id: int | None = None,
    ) -> None:
        """Initialize ProposalParliamentaryGroupJudge entity.

        Args:
            proposal_id: 議案ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            judge_type: 賛否の種別（会派単位 or 政治家単位）
            parliamentary_group_ids: 会派IDのリスト（会派単位の場合に使用）
            politician_ids: 政治家IDのリスト（政治家単位の場合に使用）
            member_count: この判断をした会派メンバーの人数（会派単位の場合に使用）
            note: 備考（自由投票など特記事項）
            id: エンティティID
        """
        super().__init__(id)
        self.proposal_id = proposal_id
        self.judgment = judgment
        self.judge_type = judge_type
        self.parliamentary_group_ids = parliamentary_group_ids or []
        self.politician_ids = politician_ids or []
        self.member_count = member_count
        self.note = note

    def is_parliamentary_group_judge(self) -> bool:
        """会派単位の賛否かどうかを判定."""
        return self.judge_type == JudgeType.PARLIAMENTARY_GROUP

    def is_politician_judge(self) -> bool:
        """政治家単位の賛否かどうかを判定."""
        return self.judge_type == JudgeType.POLITICIAN

    def is_approve(self) -> bool:
        """賛成かどうかを判定."""
        return self.judgment == "賛成"

    def is_oppose(self) -> bool:
        """反対かどうかを判定."""
        return self.judgment == "反対"

    def is_abstain(self) -> bool:
        """棄権かどうかを判定."""
        return self.judgment == "棄権"

    def is_absent(self) -> bool:
        """欠席かどうかを判定."""
        return self.judgment == "欠席"

    def __str__(self) -> str:
        if self.is_parliamentary_group_judge():
            group_ids_str = ",".join(map(str, self.parliamentary_group_ids))
            return (
                f"ProposalParliamentaryGroupJudge: "
                f"Groups [{group_ids_str}] - {self.judgment}"
                f"{f' ({self.member_count}人)' if self.member_count else ''}"
            )
        else:
            politician_ids_str = ",".join(map(str, self.politician_ids))
            return (
                f"ProposalParliamentaryGroupJudge: "
                f"Politicians [{politician_ids_str}] - {self.judgment}"
            )
