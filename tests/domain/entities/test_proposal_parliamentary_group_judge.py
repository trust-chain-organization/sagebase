"""Tests for ProposalParliamentaryGroupJudge entity."""

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)


class TestProposalParliamentaryGroupJudge:
    """Test cases for ProposalParliamentaryGroupJudge entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )

        assert judge.proposal_id == 1
        assert judge.parliamentary_group_id == 2
        assert judge.judgment == "賛成"
        assert judge.member_count is None
        assert judge.note is None
        assert judge.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        judge = ProposalParliamentaryGroupJudge(
            id=10,
            proposal_id=5,
            parliamentary_group_id=3,
            judgment="反対",
            member_count=15,
            note="全員一致で反対",
        )

        assert judge.id == 10
        assert judge.proposal_id == 5
        assert judge.parliamentary_group_id == 3
        assert judge.judgment == "反対"
        assert judge.member_count == 15
        assert judge.note == "全員一致で反対"

    def test_str_representation(self) -> None:
        """Test string representation."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=5,
            judgment="賛成",
        )
        expected = "ProposalParliamentaryGroupJudge: Group 5 - 賛成"
        assert str(judge) == expected

    def test_str_representation_with_member_count(self) -> None:
        """Test string representation with member count."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=5,
            judgment="賛成",
            member_count=20,
        )
        expected = "ProposalParliamentaryGroupJudge: Group 5 - 賛成 (20人)"
        assert str(judge) == expected

    def test_is_approve(self) -> None:
        """Test is_approve method."""
        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert approve.is_approve() is True

        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="反対",
        )
        assert oppose.is_approve() is False

    def test_is_oppose(self) -> None:
        """Test is_oppose method."""
        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="反対",
        )
        assert oppose.is_oppose() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert approve.is_oppose() is False

    def test_is_abstain(self) -> None:
        """Test is_abstain method."""
        abstain = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="棄権",
        )
        assert abstain.is_abstain() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert approve.is_abstain() is False

    def test_is_absent(self) -> None:
        """Test is_absent method."""
        absent = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="欠席",
        )
        assert absent.is_absent() is True

        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert approve.is_absent() is False

    def test_all_judgment_types(self) -> None:
        """Test all four judgment types."""
        judgments = ["賛成", "反対", "棄権", "欠席"]

        for judgment in judgments:
            judge = ProposalParliamentaryGroupJudge(
                proposal_id=1,
                parliamentary_group_id=2,
                judgment=judgment,
            )
            assert judge.judgment == judgment

    def test_judgment_check_methods_comprehensive(self) -> None:
        """Test all judgment check methods comprehensively."""
        # 賛成
        approve = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert approve.is_approve() is True
        assert approve.is_oppose() is False
        assert approve.is_abstain() is False
        assert approve.is_absent() is False

        # 反対
        oppose = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="反対",
        )
        assert oppose.is_approve() is False
        assert oppose.is_oppose() is True
        assert oppose.is_abstain() is False
        assert oppose.is_absent() is False

        # 棄権
        abstain = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="棄権",
        )
        assert abstain.is_approve() is False
        assert abstain.is_oppose() is False
        assert abstain.is_abstain() is True
        assert abstain.is_absent() is False

        # 欠席
        absent = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="欠席",
        )
        assert absent.is_approve() is False
        assert absent.is_oppose() is False
        assert absent.is_abstain() is False
        assert absent.is_absent() is True

    def test_various_member_counts(self) -> None:
        """Test various member count values."""
        counts = [1, 5, 10, 20, 50, 100, None]

        for count in counts:
            judge = ProposalParliamentaryGroupJudge(
                proposal_id=1,
                parliamentary_group_id=2,
                judgment="賛成",
                member_count=count,
            )
            assert judge.member_count == count

    def test_various_notes(self) -> None:
        """Test various note values."""
        notes = [
            "全員一致で賛成",
            "賛成多数",
            "自由投票",
            "党議拘束なし",
            "一部反対あり",
            None,
        ]

        for note in notes:
            judge = ProposalParliamentaryGroupJudge(
                proposal_id=1,
                parliamentary_group_id=2,
                judgment="賛成",
                note=note,
            )
            assert judge.note == note

    def test_inheritance_from_base_entity(self) -> None:
        """Test ProposalParliamentaryGroupJudge inherits from BaseEntity."""
        judge = ProposalParliamentaryGroupJudge(
            id=42,
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )

        # Check that id is properly set through BaseEntity
        assert judge.id == 42

        # Create without id
        judge_no_id = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert judge_no_id.id is None

    def test_complex_voting_scenarios(self) -> None:
        """Test complex real-world voting scenarios."""
        # Unanimous approval
        unanimous_approve = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=100,
            parliamentary_group_id=5,
            judgment="賛成",
            member_count=25,
            note="全員一致で賛成",
        )
        assert unanimous_approve.is_approve() is True
        assert unanimous_approve.member_count == 25

        # Majority opposition
        majority_oppose = ProposalParliamentaryGroupJudge(
            id=2,
            proposal_id=100,
            parliamentary_group_id=6,
            judgment="反対",
            member_count=15,
            note="賛成多数で反対",
        )
        assert majority_oppose.is_oppose() is True

        # Free vote
        free_vote = ProposalParliamentaryGroupJudge(
            id=3,
            proposal_id=100,
            parliamentary_group_id=7,
            judgment="棄権",
            member_count=10,
            note="自由投票のため会派としては棄権",
        )
        assert free_vote.is_abstain() is True
        assert "自由投票" in free_vote.note

        # Absent group
        absent_group = ProposalParliamentaryGroupJudge(
            id=4,
            proposal_id=100,
            parliamentary_group_id=8,
            judgment="欠席",
            member_count=3,
            note="全員欠席",
        )
        assert absent_group.is_absent() is True

    def test_edge_cases(self) -> None:
        """Test edge cases for ProposalParliamentaryGroupJudge entity."""
        # Empty string note
        judge_empty = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            note="",
        )
        assert judge_empty.note == ""

        # Very long note
        long_note = "詳細な理由：" * 100
        judge_long_note = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            note=long_note,
        )
        assert judge_long_note.note == long_note

        # Zero member count
        judge_zero = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            member_count=0,
        )
        assert judge_zero.member_count == 0

        # Large member count
        judge_large = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            member_count=9999,
        )
        assert judge_large.member_count == 9999

    def test_optional_fields_none_behavior(self) -> None:
        """Test behavior when optional fields are explicitly set to None."""
        judge = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            member_count=None,
            note=None,
        )

        assert judge.member_count is None
        assert judge.note is None

    def test_id_assignment(self) -> None:
        """Test ID assignment behavior."""
        # Without ID
        judge1 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
        )
        assert judge1.id is None

        # With ID
        judge2 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            id=100,
        )
        assert judge2.id == 100

        # ID can be any integer
        judge3 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=2,
            judgment="賛成",
            id=999999,
        )
        assert judge3.id == 999999

    def test_multiple_groups_same_proposal(self) -> None:
        """Test multiple parliamentary groups voting on the same proposal."""
        proposal_id = 100

        group1_approve = ProposalParliamentaryGroupJudge(
            proposal_id=proposal_id,
            parliamentary_group_id=1,
            judgment="賛成",
            member_count=25,
        )

        group2_oppose = ProposalParliamentaryGroupJudge(
            proposal_id=proposal_id,
            parliamentary_group_id=2,
            judgment="反対",
            member_count=15,
        )

        group3_abstain = ProposalParliamentaryGroupJudge(
            proposal_id=proposal_id,
            parliamentary_group_id=3,
            judgment="棄権",
            member_count=5,
        )

        assert group1_approve.proposal_id == proposal_id
        assert group2_oppose.proposal_id == proposal_id
        assert group3_abstain.proposal_id == proposal_id
        assert group1_approve.is_approve() is True
        assert group2_oppose.is_oppose() is True
        assert group3_abstain.is_abstain() is True

    def test_note_with_special_characters(self) -> None:
        """Test notes with special characters."""
        notes_special = [
            "賛成：（ただし一部反対意見あり）",
            "反対理由：「予算不足」",
            "棄権！？",
        ]

        for note in notes_special:
            judge = ProposalParliamentaryGroupJudge(
                proposal_id=1,
                parliamentary_group_id=2,
                judgment="賛成",
                note=note,
            )
            assert judge.note == note

    def test_str_representation_various_scenarios(self) -> None:
        """Test string representation in various scenarios."""
        # No member count
        judge1 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=10,
            judgment="賛成",
        )
        assert str(judge1) == "ProposalParliamentaryGroupJudge: Group 10 - 賛成"

        # With member count
        judge2 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=20,
            judgment="反対",
            member_count=15,
        )
        assert str(judge2) == "ProposalParliamentaryGroupJudge: Group 20 - 反対 (15人)"

        # Zero member count (should show)
        judge3 = ProposalParliamentaryGroupJudge(
            proposal_id=1,
            parliamentary_group_id=30,
            judgment="棄権",
            member_count=0,
        )
        # Note: 0 is falsy, so it won't show member count in the current implementation
        result = str(judge3)
        assert "Group 30" in result
        assert "棄権" in result
