"""Tests for ExtractedProposalJudge entity."""

from datetime import datetime

import pytest

from tests.fixtures.entity_factories import create_extracted_proposal_judge

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge


class TestExtractedProposalJudge:
    """Test cases for ExtractedProposalJudge entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        judge = ExtractedProposalJudge(
            proposal_id=1,
        )

        assert judge.proposal_id == 1
        assert judge.extracted_politician_name is None
        assert judge.extracted_party_name is None
        assert judge.extracted_parliamentary_group_name is None
        assert judge.extracted_judgment is None
        assert judge.source_url is None
        assert judge.matched_politician_id is None
        assert judge.matched_parliamentary_group_id is None
        assert judge.matching_confidence is None
        assert judge.matching_status == "pending"
        assert judge.matched_at is None
        assert judge.additional_data is None
        assert isinstance(judge.extracted_at, datetime)

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)
        matched_at = datetime(2023, 1, 2, 12, 0, 0)

        judge = ExtractedProposalJudge(
            id=1,
            proposal_id=1,
            extracted_politician_name="山田太郎",
            extracted_party_name="自由民主党",
            extracted_parliamentary_group_name="自民党議員団",
            extracted_judgment="賛成",
            source_url="https://example.com/proposal/1",
            extracted_at=extracted_at,
            matched_politician_id=10,
            matched_parliamentary_group_id=5,
            matching_confidence=0.95,
            matching_status="matched",
            matched_at=matched_at,
            additional_data='{"notes": "特記事項"}',
        )

        assert judge.id == 1
        assert judge.proposal_id == 1
        assert judge.extracted_politician_name == "山田太郎"
        assert judge.extracted_party_name == "自由民主党"
        assert judge.extracted_parliamentary_group_name == "自民党議員団"
        assert judge.extracted_judgment == "賛成"
        assert judge.source_url == "https://example.com/proposal/1"
        assert judge.extracted_at == extracted_at
        assert judge.matched_politician_id == 10
        assert judge.matched_parliamentary_group_id == 5
        assert judge.matching_confidence == 0.95
        assert judge.matching_status == "matched"
        assert judge.matched_at == matched_at
        assert judge.additional_data == '{"notes": "特記事項"}'

    def test_is_matched_method(self) -> None:
        """Test is_matched method with different statuses."""
        # Test with matched status
        matched_judge = create_extracted_proposal_judge(matching_status="matched")
        assert matched_judge.is_matched() is True

        # Test with pending status
        pending_judge = create_extracted_proposal_judge(matching_status="pending")
        assert pending_judge.is_matched() is False

        # Test with needs_review status
        review_judge = create_extracted_proposal_judge(matching_status="needs_review")
        assert review_judge.is_matched() is False

        # Test with no_match status
        no_match_judge = create_extracted_proposal_judge(matching_status="no_match")
        assert no_match_judge.is_matched() is False

    def test_needs_review_method(self) -> None:
        """Test needs_review method with different statuses."""
        # Test with needs_review status
        review_judge = create_extracted_proposal_judge(matching_status="needs_review")
        assert review_judge.needs_review() is True

        # Test with matched status
        matched_judge = create_extracted_proposal_judge(matching_status="matched")
        assert matched_judge.needs_review() is False

        # Test with pending status
        pending_judge = create_extracted_proposal_judge(matching_status="pending")
        assert pending_judge.needs_review() is False

        # Test with no_match status
        no_match_judge = create_extracted_proposal_judge(matching_status="no_match")
        assert no_match_judge.needs_review() is False

    def test_convert_to_proposal_judge_params_success(self) -> None:
        """Test successful conversion to ProposalJudge parameters."""
        judge = create_extracted_proposal_judge(
            proposal_id=1,
            extracted_judgment="賛成",
            matching_status="matched",
            matched_politician_id=10,
        )

        params = judge.convert_to_proposal_judge_params()

        assert params["proposal_id"] == 1
        assert params["politician_id"] == 10
        assert params["approve"] == "賛成"

    def test_convert_to_proposal_judge_params_unmatched_error(self) -> None:
        """Test conversion error when judge is not matched."""
        judge = create_extracted_proposal_judge(
            matching_status="pending",
            matched_politician_id=None,
        )

        with pytest.raises(ValueError) as exc_info:
            judge.convert_to_proposal_judge_params()

        assert "Cannot convert unmatched extracted judge" in str(exc_info.value)

    def test_convert_to_proposal_judge_params_no_politician_error(self) -> None:
        """Test conversion error when politician ID is missing."""
        judge = create_extracted_proposal_judge(
            matching_status="matched",
            matched_politician_id=None,
        )

        with pytest.raises(ValueError) as exc_info:
            judge.convert_to_proposal_judge_params()

        assert "Matched politician ID is required" in str(exc_info.value)

    def test_str_representation_with_politician_name(self) -> None:
        """Test string representation with politician name."""
        judge = create_extracted_proposal_judge(
            extracted_politician_name="鈴木一郎",
            extracted_judgment="反対",
            matching_status="matched",
        )

        expected = (
            "ExtractedProposalJudge(name=鈴木一郎, judgment=反対, status=matched)"
        )
        assert str(judge) == expected

    def test_str_representation_with_parliamentary_group(self) -> None:
        """Test string representation with parliamentary group name."""
        judge = create_extracted_proposal_judge(
            extracted_politician_name=None,
            extracted_parliamentary_group_name="公明党議員団",
            extracted_judgment="賛成",
            matching_status="pending",
        )

        expected = (
            "ExtractedProposalJudge(name=公明党議員団, judgment=賛成, status=pending)"
        )
        assert str(judge) == expected

    def test_str_representation_without_name(self) -> None:
        """Test string representation without name."""
        judge = create_extracted_proposal_judge(
            extracted_politician_name=None,
            extracted_parliamentary_group_name=None,
            extracted_judgment="棄権",
            matching_status="no_match",
        )

        expected = (
            "ExtractedProposalJudge(name=Unknown, judgment=棄権, status=no_match)"
        )
        assert str(judge) == expected

    def test_different_matching_statuses(self) -> None:
        """Test entity with different matching statuses."""
        statuses = ["pending", "matched", "needs_review", "no_match"]

        for status in statuses:
            judge = create_extracted_proposal_judge(matching_status=status)
            assert judge.matching_status == status

    def test_different_judgments(self) -> None:
        """Test entity with different judgment types."""
        judgments = ["賛成", "反対", "棄権", "欠席"]

        for judgment in judgments:
            judge = create_extracted_proposal_judge(extracted_judgment=judgment)
            assert judge.extracted_judgment == judgment

    def test_entity_factory(self) -> None:
        """Test entity creation using factory."""
        judge = create_extracted_proposal_judge()

        assert judge.id == 1
        assert judge.proposal_id == 1
        assert judge.extracted_politician_name == "山田太郎"
        assert judge.extracted_judgment == "賛成"
        assert judge.source_url == "https://example.com/proposal/1"
        assert judge.matching_status == "pending"

    def test_factory_with_overrides(self) -> None:
        """Test entity factory with custom values."""
        judge = create_extracted_proposal_judge(
            id=99,
            extracted_politician_name="佐藤花子",
            extracted_judgment="反対",
            matching_status="matched",
            matching_confidence=0.85,
            matched_politician_id=50,
        )

        assert judge.id == 99
        assert judge.extracted_politician_name == "佐藤花子"
        assert judge.extracted_judgment == "反対"
        assert judge.matching_status == "matched"
        assert judge.matching_confidence == 0.85
        assert judge.matched_politician_id == 50
        # Verify defaults are still applied
        assert judge.proposal_id == 1
        assert judge.source_url == "https://example.com/proposal/1"

    def test_extracted_at_default_value(self) -> None:
        """Test that extracted_at is set to current time by default."""
        before = datetime.now()
        judge = ExtractedProposalJudge(proposal_id=1)
        after = datetime.now()

        assert before <= judge.extracted_at <= after

    def test_matched_judge_with_high_confidence(self) -> None:
        """Test a successfully matched judge with high confidence."""
        judge = create_extracted_proposal_judge(
            matching_status="matched",
            matching_confidence=0.95,
            matched_politician_id=100,
            matched_at=datetime(2023, 1, 15, 10, 30, 0),
        )

        assert judge.is_matched() is True
        assert judge.needs_review() is False
        assert judge.matching_confidence == 0.95
        assert judge.matched_politician_id == 100
        assert judge.matched_at == datetime(2023, 1, 15, 10, 30, 0)

    def test_judge_needing_review_with_medium_confidence(self) -> None:
        """Test a judge that needs manual review."""
        judge = create_extracted_proposal_judge(
            matching_status="needs_review",
            matching_confidence=0.6,
            matched_politician_id=None,
        )

        assert judge.is_matched() is False
        assert judge.needs_review() is True
        assert judge.matching_confidence == 0.6
        assert judge.matched_politician_id is None

    def test_judge_with_parliamentary_group_match(self) -> None:
        """Test a judge matched to a parliamentary group."""
        judge = create_extracted_proposal_judge(
            extracted_parliamentary_group_name="立憲民主党議員団",
            matching_status="matched",
            matched_parliamentary_group_id=3,
            matched_politician_id=None,
            matching_confidence=0.9,
        )

        assert judge.extracted_parliamentary_group_name == "立憲民主党議員団"
        assert judge.matched_parliamentary_group_id == 3
        assert judge.matched_politician_id is None
        assert judge.is_matched() is True
        assert judge.matching_confidence == 0.9
