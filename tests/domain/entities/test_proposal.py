"""Tests for Proposal entity."""

from src.domain.entities.proposal import Proposal


class TestProposal:
    """Test cases for Proposal entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        proposal = Proposal(title="予算案の審議について")

        assert proposal.title == "予算案の審議について"
        assert proposal.id is None
        assert proposal.detail_url is None
        assert proposal.status_url is None
        assert proposal.votes_url is None
        assert proposal.meeting_id is None
        assert proposal.conference_id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        proposal = Proposal(
            id=1,
            title="令和6年度予算案の承認について",
            detail_url="https://example.com/proposal/001",
            status_url="https://example.com/proposal/status/001",
            votes_url="https://example.com/proposal/votes/001",
            meeting_id=100,
            conference_id=10,
        )

        assert proposal.id == 1
        assert proposal.title == "令和6年度予算案の承認について"
        assert proposal.detail_url == "https://example.com/proposal/001"
        assert proposal.status_url == "https://example.com/proposal/status/001"
        assert proposal.votes_url == "https://example.com/proposal/votes/001"
        assert proposal.meeting_id == 100
        assert proposal.conference_id == 10

    def test_str_representation_with_id(self) -> None:
        """Test string representation with ID."""
        proposal = Proposal(
            id=1,
            title="短い内容",
        )

        assert str(proposal) == "Proposal ID:1: 短い内容..."

    def test_str_representation_long_title(self) -> None:
        """Test string representation with long title."""
        long_title = (
            "これは非常に長い議案内容で、50文字を超えるような詳細な説明が含まれています。"
            "予算の詳細や実施計画などが記載されています。"
        )
        proposal = Proposal(
            id=2,
            title=long_title,
        )

        # Should truncate at 50 characters
        expected = f"Proposal ID:2: {long_title[:50]}..."
        assert str(proposal) == expected

    def test_str_representation_without_id(self) -> None:
        """Test string representation without ID."""
        proposal = Proposal(
            title="議案内容のテスト",
        )

        assert str(proposal) == "Proposal ID:None: 議案内容のテスト..."

    def test_url_fields(self) -> None:
        """Test URL fields with various values."""
        # Test with detail URL
        proposal_with_detail_url = Proposal(
            title="議案内容",
            detail_url="https://council.example.com/proposals/2024/001",
        )
        assert (
            proposal_with_detail_url.detail_url
            == "https://council.example.com/proposals/2024/001"
        )

        # Test with status URL
        proposal_with_status_url = Proposal(
            title="議案内容",
            status_url="https://council.example.com/proposals/status/001",
        )
        assert (
            proposal_with_status_url.status_url
            == "https://council.example.com/proposals/status/001"
        )

        # Test with votes URL
        proposal_with_votes_url = Proposal(
            title="議案内容",
            votes_url="https://council.example.com/proposals/votes/001",
        )
        assert (
            proposal_with_votes_url.votes_url
            == "https://council.example.com/proposals/votes/001"
        )

    def test_meeting_and_conference_ids(self) -> None:
        """Test meeting_id and conference_id fields."""
        # Test with meeting ID
        proposal_with_meeting = Proposal(
            title="議案内容",
            meeting_id=42,
        )
        assert proposal_with_meeting.meeting_id == 42

        # Test with conference ID
        proposal_with_conference = Proposal(
            title="議案内容",
            conference_id=10,
        )
        assert proposal_with_conference.conference_id == 10

        # Test with both
        proposal_with_both = Proposal(
            title="議案内容",
            meeting_id=42,
            conference_id=10,
        )
        assert proposal_with_both.meeting_id == 42
        assert proposal_with_both.conference_id == 10
