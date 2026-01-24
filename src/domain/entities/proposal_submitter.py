"""議案の提出者を表すエンティティ."""

from src.domain.entities.base import BaseEntity
from src.domain.value_objects.submitter_type import SubmitterType


class ProposalSubmitter(BaseEntity):
    """議案の提出者を表す中間エンティティ.

    1つの議案に対して複数の提出者（連名提出）を紐付けることができる。
    """

    def __init__(
        self,
        proposal_id: int,
        submitter_type: SubmitterType,
        politician_id: int | None = None,
        parliamentary_group_id: int | None = None,
        conference_id: int | None = None,
        raw_name: str | None = None,
        is_representative: bool = False,
        display_order: int = 0,
        id: int | None = None,
    ) -> None:
        """Initialize ProposalSubmitter entity.

        Args:
            proposal_id: 議案ID
            submitter_type: 提出者種別
            politician_id: 議員提出の場合のPolitician ID
            parliamentary_group_id: 会派提出の場合のParliamentaryGroup ID
            conference_id: 会議体提出の場合のConference ID
            raw_name: 生の提出者名（マッチング前の文字列）
            is_representative: 代表提出者かどうか
            display_order: 表示順序
            id: エンティティID
        """
        super().__init__(id)
        self.proposal_id = proposal_id
        self.submitter_type = submitter_type
        self.politician_id = politician_id
        self.parliamentary_group_id = parliamentary_group_id
        self.conference_id = conference_id
        self.raw_name = raw_name
        self.is_representative = is_representative
        self.display_order = display_order

    def is_mayor_submission(self) -> bool:
        """市長提出かどうかを判定."""
        return self.submitter_type == SubmitterType.MAYOR

    def is_politician_submission(self) -> bool:
        """議員提出かどうかを判定."""
        return self.submitter_type == SubmitterType.POLITICIAN

    def is_parliamentary_group_submission(self) -> bool:
        """会派提出かどうかを判定."""
        return self.submitter_type == SubmitterType.PARLIAMENTARY_GROUP

    def is_committee_submission(self) -> bool:
        """委員会提出かどうかを判定."""
        return self.submitter_type == SubmitterType.COMMITTEE

    def is_conference_submission(self) -> bool:
        """会議体提出かどうかを判定."""
        return self.submitter_type == SubmitterType.CONFERENCE

    def is_matched(self) -> bool:
        """マッチング済みかどうかを判定."""
        if self.submitter_type == SubmitterType.POLITICIAN:
            return self.politician_id is not None
        if self.submitter_type == SubmitterType.PARLIAMENTARY_GROUP:
            return self.parliamentary_group_id is not None
        if self.submitter_type == SubmitterType.CONFERENCE:
            return self.conference_id is not None
        return True

    def __str__(self) -> str:
        name_part = self.raw_name or "unknown"
        return (
            f"ProposalSubmitter(proposal_id={self.proposal_id}, "
            f"type={self.submitter_type.value}, name={name_part})"
        )
