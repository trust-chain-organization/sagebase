"""Tests for ProposalSubmitter entity."""

import pytest

from tests.fixtures.entity_factories import create_proposal_submitter

from src.domain.entities.proposal_submitter import ProposalSubmitter
from src.domain.value_objects.submitter_type import SubmitterType


class TestProposalSubmitter:
    """Test cases for ProposalSubmitter entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        submitter = ProposalSubmitter(
            proposal_id=1,
            submitter_type=SubmitterType.POLITICIAN,
        )

        assert submitter.proposal_id == 1
        assert submitter.submitter_type == SubmitterType.POLITICIAN
        assert submitter.politician_id is None
        assert submitter.parliamentary_group_id is None
        assert submitter.conference_id is None
        assert submitter.raw_name is None
        assert submitter.is_representative is False
        assert submitter.display_order == 0
        assert submitter.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        submitter = ProposalSubmitter(
            id=1,
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
            parliamentary_group_id=None,
            raw_name="山田太郎",
            is_representative=True,
            display_order=1,
        )

        assert submitter.id == 1
        assert submitter.proposal_id == 10
        assert submitter.submitter_type == SubmitterType.POLITICIAN
        assert submitter.politician_id == 100
        assert submitter.parliamentary_group_id is None
        assert submitter.raw_name == "山田太郎"
        assert submitter.is_representative is True
        assert submitter.display_order == 1

    def test_is_mayor_submission(self) -> None:
        """Test is_mayor_submission method."""
        mayor_submitter = create_proposal_submitter(submitter_type=SubmitterType.MAYOR)
        assert mayor_submitter.is_mayor_submission() is True

        politician_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN
        )
        assert politician_submitter.is_mayor_submission() is False

    def test_is_politician_submission(self) -> None:
        """Test is_politician_submission method."""
        politician_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN
        )
        assert politician_submitter.is_politician_submission() is True

        mayor_submitter = create_proposal_submitter(submitter_type=SubmitterType.MAYOR)
        assert mayor_submitter.is_politician_submission() is False

    def test_is_parliamentary_group_submission(self) -> None:
        """Test is_parliamentary_group_submission method."""
        group_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP
        )
        assert group_submitter.is_parliamentary_group_submission() is True

        politician_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN
        )
        assert politician_submitter.is_parliamentary_group_submission() is False

    def test_is_committee_submission(self) -> None:
        """Test is_committee_submission method."""
        committee_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.COMMITTEE
        )
        assert committee_submitter.is_committee_submission() is True

        mayor_submitter = create_proposal_submitter(submitter_type=SubmitterType.MAYOR)
        assert mayor_submitter.is_committee_submission() is False

    def test_is_conference_submission(self) -> None:
        """Test is_conference_submission method."""
        conference_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.CONFERENCE
        )
        assert conference_submitter.is_conference_submission() is True

        politician_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN
        )
        assert politician_submitter.is_conference_submission() is False

    def test_is_matched_for_politician_type(self) -> None:
        """Test is_matched method for politician type."""
        matched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=100,
        )
        assert matched_submitter.is_matched() is True

        unmatched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.POLITICIAN,
            politician_id=None,
        )
        assert unmatched_submitter.is_matched() is False

    def test_is_matched_for_parliamentary_group_type(self) -> None:
        """Test is_matched method for parliamentary group type."""
        matched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            parliamentary_group_id=50,
        )
        assert matched_submitter.is_matched() is True

        unmatched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.PARLIAMENTARY_GROUP,
            parliamentary_group_id=None,
        )
        assert unmatched_submitter.is_matched() is False

    def test_is_matched_for_mayor_type(self) -> None:
        """Test is_matched method for mayor type (always returns True)."""
        mayor_submitter = create_proposal_submitter(submitter_type=SubmitterType.MAYOR)
        assert mayor_submitter.is_matched() is True

    def test_is_matched_for_committee_type(self) -> None:
        """Test is_matched method for committee type (always returns True)."""
        committee_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.COMMITTEE
        )
        assert committee_submitter.is_matched() is True

    def test_is_matched_for_other_type(self) -> None:
        """Test is_matched method for other type (always returns True)."""
        other_submitter = create_proposal_submitter(submitter_type=SubmitterType.OTHER)
        assert other_submitter.is_matched() is True

    def test_is_matched_for_conference_type(self) -> None:
        """Test is_matched method for conference type."""
        matched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.CONFERENCE,
            conference_id=10,
        )
        assert matched_submitter.is_matched() is True

        unmatched_submitter = create_proposal_submitter(
            submitter_type=SubmitterType.CONFERENCE,
            conference_id=None,
        )
        assert unmatched_submitter.is_matched() is False

    def test_str_representation(self) -> None:
        """Test string representation of entity."""
        submitter = create_proposal_submitter(
            proposal_id=10,
            submitter_type=SubmitterType.POLITICIAN,
            raw_name="山田太郎",
        )
        result = str(submitter)

        assert "proposal_id=10" in result
        assert "type=politician" in result
        assert "name=山田太郎" in result

    def test_str_representation_without_raw_name(self) -> None:
        """Test string representation when raw_name is None."""
        submitter = create_proposal_submitter(
            proposal_id=10,
            submitter_type=SubmitterType.MAYOR,
            raw_name=None,
        )
        result = str(submitter)

        assert "name=unknown" in result

    def test_all_submitter_types(self) -> None:
        """Test that all submitter types are valid."""
        for submitter_type in SubmitterType:
            submitter = create_proposal_submitter(submitter_type=submitter_type)
            assert submitter.submitter_type == submitter_type


class TestSubmitterType:
    """Test cases for SubmitterType enum."""

    def test_enum_values(self) -> None:
        """Test that all enum values are correct."""
        assert SubmitterType.MAYOR.value == "mayor"
        assert SubmitterType.POLITICIAN.value == "politician"
        assert SubmitterType.PARLIAMENTARY_GROUP.value == "parliamentary_group"
        assert SubmitterType.COMMITTEE.value == "committee"
        assert SubmitterType.CONFERENCE.value == "conference"
        assert SubmitterType.OTHER.value == "other"

    def test_enum_count(self) -> None:
        """Test that there are exactly 6 submitter types."""
        assert len(SubmitterType) == 6

    def test_enum_from_value(self) -> None:
        """Test creating enum from string value."""
        assert SubmitterType("mayor") == SubmitterType.MAYOR
        assert SubmitterType("politician") == SubmitterType.POLITICIAN
        assert SubmitterType("parliamentary_group") == SubmitterType.PARLIAMENTARY_GROUP
        assert SubmitterType("committee") == SubmitterType.COMMITTEE
        assert SubmitterType("conference") == SubmitterType.CONFERENCE
        assert SubmitterType("other") == SubmitterType.OTHER

    def test_enum_invalid_value(self) -> None:
        """Test that invalid value raises ValueError."""
        with pytest.raises(ValueError):
            SubmitterType("invalid")
