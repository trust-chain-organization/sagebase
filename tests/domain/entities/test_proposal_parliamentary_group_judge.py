"""Tests for ProposalParliamentaryGroupJudge entity.

Many-to-Many構造: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
"""

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.value_objects.judge_type import JudgeType


class TestProposalParliamentaryGroupJudge:
    """Test cases for ProposalParliamentaryGroupJudge entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )

        assert judge.proposal_id == 1
        assert judge.parliamentary_group_ids == [2]
        assert judge.judgment == "賛成"
        assert judge.judge_type == JudgeType.PARLIAMENTARY_GROUP
        assert judge.member_count is None
        assert judge.note is None
        assert judge.id is None
        assert judge.politician_ids == []

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        judge = ProposalParliamentaryGroupJudge(
            id=10,
            proposal_id=5,
            judgment="反対",
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[3, 4],
            member_count=15,
            note="全員一致で反対",
        )

        assert judge.id == 10
        assert judge.proposal_id == 5
        assert judge.parliamentary_group_ids == [3, 4]
        assert judge.judgment == "反対"
        assert judge.judge_type == JudgeType.PARLIAMENTARY_GROUP
        assert judge.member_count == 15
        assert judge.note == "全員一致で反対"

    def test_politician_judge_initialization(self) -> None:
        """Test entity initialization for politician judge."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100],
        )

        assert judge.proposal_id == 1
        assert judge.judgment == "賛成"
        assert judge.judge_type == JudgeType.POLITICIAN
        assert judge.politician_ids == [100]
        assert judge.parliamentary_group_ids == []

    def test_multiple_ids_initialization(self) -> None:
        """Test entity initialization with multiple IDs."""
        # 複数の会派
        pg_judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[1, 2, 3],
        )
        assert pg_judge.parliamentary_group_ids == [1, 2, 3]

        # 複数の政治家
        pol_judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[10, 20, 30],
        )
        assert pol_judge.politician_ids == [10, 20, 30]

    def test_is_parliamentary_group_judge(self) -> None:
        """Test is_parliamentary_group_judge method."""
        pg_judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert pg_judge.is_parliamentary_group_judge() is True
        assert pg_judge.is_politician_judge() is False

        pol_judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100],
        )
        assert pol_judge.is_parliamentary_group_judge() is False
        assert pol_judge.is_politician_judge() is True

    def test_str_representation(self) -> None:
        """Test string representation for parliamentary group judge."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[5],
        )
        expected = "ProposalParliamentaryGroupJudge: Groups [5] - 賛成"
        assert str(judge) == expected

    def test_str_representation_multiple_groups(self) -> None:
        """Test string representation with multiple groups."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[5, 6, 7],
        )
        expected = "ProposalParliamentaryGroupJudge: Groups [5,6,7] - 賛成"
        assert str(judge) == expected

    def test_str_representation_with_member_count(self) -> None:
        """Test string representation with member count."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[5],
            member_count=20,
        )
        expected = "ProposalParliamentaryGroupJudge: Groups [5] - 賛成 (20人)"
        assert str(judge) == expected

    def test_str_representation_politician(self) -> None:
        """Test string representation for politician judge."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100],
        )
        expected = "ProposalParliamentaryGroupJudge: Politicians [100] - 反対"
        assert str(judge) == expected

    def test_str_representation_multiple_politicians(self) -> None:
        """Test string representation with multiple politicians."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            judge_type=JudgeType.POLITICIAN,
            politician_ids=[100, 101, 102],
        )
        expected = "ProposalParliamentaryGroupJudge: Politicians [100,101,102] - 反対"
        assert str(judge) == expected

    def test_is_approve(self) -> None:
        """Test is_approve method."""
        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert approve.is_approve() is True

        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            parliamentary_group_ids=[2],
        )
        assert oppose.is_approve() is False

    def test_is_oppose(self) -> None:
        """Test is_oppose method."""
        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            parliamentary_group_ids=[2],
        )
        assert oppose.is_oppose() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert approve.is_oppose() is False

    def test_is_abstain(self) -> None:
        """Test is_abstain method."""
        abstain = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="棄権",
            parliamentary_group_ids=[2],
        )
        assert abstain.is_abstain() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert approve.is_abstain() is False

    def test_is_absent(self) -> None:
        """Test is_absent method."""
        absent = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="欠席",
            parliamentary_group_ids=[2],
        )
        assert absent.is_absent() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert approve.is_absent() is False

    def test_all_judgment_types(self) -> None:
        """Test all four judgment types."""
        judgments = ["賛成", "反対", "棄権", "欠席"]

        for judgment in judgments:
            judge = ProposalParliamentaryGroupJudge(
                proposal_id=1,
                judgment=judgment,
                parliamentary_group_ids=[2],
            )
            assert judge.judgment == judgment

    def test_judgment_check_methods_comprehensive(self) -> None:
        """Test all judgment check methods comprehensively."""
        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert approve.is_approve() is True
        assert approve.is_oppose() is False
        assert approve.is_abstain() is False
        assert approve.is_absent() is False

        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="反対",
            parliamentary_group_ids=[2],
        )
        assert oppose.is_approve() is False
        assert oppose.is_oppose() is True
        assert oppose.is_abstain() is False
        assert oppose.is_absent() is False

        abstain = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="棄権",
            parliamentary_group_ids=[2],
        )
        assert abstain.is_approve() is False
        assert abstain.is_oppose() is False
        assert abstain.is_abstain() is True
        assert abstain.is_absent() is False

        absent = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="欠席",
            parliamentary_group_ids=[2],
        )
        assert absent.is_approve() is False
        assert absent.is_oppose() is False
        assert absent.is_abstain() is False
        assert absent.is_absent() is True

    def test_default_judge_type(self) -> None:
        """Test that default judge_type is PARLIAMENTARY_GROUP."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert judge.judge_type == JudgeType.PARLIAMENTARY_GROUP

    def test_inheritance_from_base_entity(self) -> None:
        """Test ProposalParliamentaryGroupJudge inherits from BaseEntity."""
        judge = ProposalParliamentaryGroupJudge(
            id=42,
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )

        assert judge.id == 42

        judge_no_id = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
            parliamentary_group_ids=[2],
        )
        assert judge_no_id.id is None

    def test_empty_ids_default(self) -> None:
        """Test that empty lists are the default for IDs."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            judgment="賛成",
        )
        assert judge.parliamentary_group_ids == []
        assert judge.politician_ids == []
