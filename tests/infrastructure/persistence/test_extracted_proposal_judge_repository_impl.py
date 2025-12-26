"""Tests for ExtractedProposalJudgeRepositoryImpl."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal_judge import ProposalJudge
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)


class TestExtractedProposalJudgeRepositoryImpl:
    """Test cases for ExtractedProposalJudgeRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        # Mock async methods
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.add_all = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> ExtractedProposalJudgeRepositoryImpl:
        """Create extracted proposal judge repository."""
        return ExtractedProposalJudgeRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_judge_dict(self) -> dict[str, Any]:
        """Sample extracted proposal judge data as dict."""
        return {
            "id": 1,
            "proposal_id": 10,
            "extracted_politician_name": "山田太郎",
            "extracted_party_name": "自由民主党",
            "extracted_parliamentary_group_name": None,
            "extracted_judgment": "賛成",
            "source_url": "https://example.com/proposal/1",
            "extracted_at": datetime(2023, 1, 1, 12, 0, 0),
            "matched_politician_id": None,
            "matched_parliamentary_group_id": None,
            "matching_confidence": None,
            "matching_status": "pending",
            "matched_at": None,
            "additional_data": None,
        }

    @pytest.fixture
    def sample_judge_entity(self) -> ExtractedProposalJudge:
        """Sample extracted proposal judge entity."""
        return ExtractedProposalJudge(
            id=1,
            proposal_id=10,
            extracted_politician_name="山田太郎",
            extracted_party_name="自由民主党",
            extracted_judgment="賛成",
            source_url="https://example.com/proposal/1",
            extracted_at=datetime(2023, 1, 1, 12, 0, 0),
            matching_status="pending",
        )

    def _create_mock_row(self, data: dict[str, Any]) -> MagicMock:
        """Create a mock database row."""
        mock_row = MagicMock()
        for key, value in data.items():
            setattr(mock_row, key, value)
        return mock_row

    @pytest.mark.asyncio
    async def test_get_pending_judges(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_pending_judges returns list of pending judges."""
        # Setup mock result
        mock_row = self._create_mock_row(sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_pending_judges()

        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].proposal_id == 10
        assert result[0].extracted_politician_name == "山田太郎"
        assert result[0].matching_status == "pending"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_judges_with_proposal_filter(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_pending_judges with proposal_id filter."""
        # Setup mock result
        mock_row = self._create_mock_row(sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_pending_judges(proposal_id=10)

        # Assert
        assert len(result) == 1
        assert result[0].proposal_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_judges(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_judges returns list of matched judges."""
        # Setup mock result
        matched_dict = {
            "id": 2,
            "proposal_id": 10,
            "extracted_politician_name": "鈴木一郎",
            "extracted_party_name": "立憲民主党",
            "extracted_parliamentary_group_name": None,
            "extracted_judgment": "反対",
            "source_url": "https://example.com/proposal/1",
            "extracted_at": datetime(2023, 1, 1, 12, 0, 0),
            "matched_politician_id": 20,
            "matched_parliamentary_group_id": None,
            "matching_confidence": 0.95,
            "matching_status": "matched",
            "matched_at": datetime(2023, 1, 2, 10, 0, 0),
            "additional_data": None,
        }
        mock_row = self._create_mock_row(matched_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_matched_judges()

        # Assert
        assert len(result) == 1
        assert result[0].id == 2
        assert result[0].matching_status == "matched"
        assert result[0].matched_politician_id == 20
        assert result[0].matching_confidence == 0.95
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_judges_with_min_confidence(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_judges with minimum confidence filter."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_matched_judges(min_confidence=0.8)

        # Assert
        assert len(result) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_needs_review_judges(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_needs_review_judges returns list of judges needing review."""
        # Setup mock result
        review_dict = {
            "id": 3,
            "proposal_id": 10,
            "extracted_politician_name": "佐藤花子",
            "extracted_party_name": "公明党",
            "extracted_parliamentary_group_name": None,
            "extracted_judgment": "棄権",
            "source_url": "https://example.com/proposal/1",
            "extracted_at": datetime(2023, 1, 1, 12, 0, 0),
            "matched_politician_id": None,
            "matched_parliamentary_group_id": None,
            "matching_confidence": 0.6,
            "matching_status": "needs_review",
            "matched_at": None,
            "additional_data": None,
        }
        mock_row = self._create_mock_row(review_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_needs_review_judges()

        # Assert
        assert len(result) == 1
        assert result[0].id == 3
        assert result[0].matching_status == "needs_review"
        assert result[0].matching_confidence == 0.6
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_matching_result(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update_matching_result updates judge matching info."""
        # Setup mock for get_by_id
        updated_judge = ExtractedProposalJudge(
            id=1,
            proposal_id=10,
            extracted_politician_name="山田太郎",
            matching_status="matched",
            matched_politician_id=20,
            matching_confidence=0.9,
        )
        repository.get_by_id = AsyncMock(return_value=updated_judge)

        # Execute
        result = await repository.update_matching_result(
            judge_id=1,
            politician_id=20,
            confidence=0.9,
            status="matched",
        )

        # Assert
        assert result is not None
        assert result.id == 1
        assert result.matched_politician_id == 20
        assert result.matching_confidence == 0.9
        assert result.matching_status == "matched"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
        sample_judge_dict: dict[str, Any],
    ) -> None:
        """Test get_by_proposal returns all judges for a proposal."""
        # Setup mock result
        mock_row = self._create_mock_row(sample_judge_dict)
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_proposal(10)

        # Assert
        assert len(result) == 1
        assert result[0].proposal_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_extraction_summary(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_extraction_summary returns summary statistics."""
        # Setup mock result
        mock_rows = [
            MagicMock(matching_status="pending", count=5),
            MagicMock(matching_status="matched", count=10),
            MagicMock(matching_status="needs_review", count=2),
            MagicMock(matching_status="no_match", count=1),
        ]
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_extraction_summary()

        # Assert
        assert result["total"] == 18
        assert result["pending"] == 5
        assert result["matched"] == 10
        assert result["needs_review"] == 2
        assert result["no_match"] == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create creates multiple judges at once."""
        # Create test entities
        judges = [
            ExtractedProposalJudge(
                proposal_id=10,
                extracted_politician_name=f"議員{i}",
                extracted_judgment="賛成",
            )
            for i in range(3)
        ]

        # Mock the execute result for each insert
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            mock_row.id = i + 1
            mock_row.proposal_id = 10
            mock_row.extracted_politician_name = f"議員{i}"
            mock_row.extracted_party_name = None
            mock_row.extracted_parliamentary_group_name = None
            mock_row.extracted_judgment = "賛成"
            mock_row.source_url = None
            mock_row.extracted_at = None
            mock_row.matched_politician_id = None
            mock_row.matched_parliamentary_group_id = None
            mock_row.matching_confidence = None
            mock_row.matching_status = "pending"
            mock_row.matched_at = None
            mock_row.additional_data = None
            mock_rows.append(mock_row)

        # Create mock results for each insert
        mock_results = []
        for mock_row in mock_rows:
            mock_result = MagicMock()
            mock_result.fetchone = MagicMock(return_value=mock_row)
            mock_results.append(mock_result)

        # Set side effect to return different result for each call
        mock_session.execute.side_effect = mock_results

        # Execute
        result = await repository.bulk_create(judges)

        # Assert
        assert len(result) == 3
        assert mock_session.execute.call_count == 3
        mock_session.commit.assert_called_once()
        # Verify returned entities
        for i, judge in enumerate(result):
            assert judge.id == i + 1
            assert judge.proposal_id == 10
            assert judge.extracted_politician_name == f"議員{i}"

    @pytest.mark.asyncio
    async def test_convert_to_proposal_judge_success(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test successful conversion to ProposalJudge."""
        # Create matched judge
        extracted_judge = ExtractedProposalJudge(
            id=1,
            proposal_id=10,
            extracted_politician_name="山田太郎",
            extracted_judgment="賛成",
            matching_status="matched",
            matched_politician_id=20,
        )

        # Execute
        result = await repository.convert_to_proposal_judge(extracted_judge)

        # Assert
        assert isinstance(result, ProposalJudge)
        assert result.proposal_id == 10
        assert result.politician_id == 20
        assert result.approve == "賛成"

    @pytest.mark.asyncio
    async def test_convert_to_proposal_judge_unmatched_error(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test conversion error for unmatched judge."""
        # Create unmatched judge
        extracted_judge = ExtractedProposalJudge(
            id=1,
            proposal_id=10,
            extracted_politician_name="山田太郎",
            matching_status="pending",
        )

        # Execute and assert
        with pytest.raises(ValueError, match="Cannot convert unmatched"):
            await repository.convert_to_proposal_judge(extracted_judge)

    @pytest.mark.asyncio
    async def test_bulk_convert_to_proposal_judges(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk conversion to ProposalJudge entities."""
        # Setup mock for get_matched_judges
        matched_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=10,
                extracted_politician_name="山田太郎",
                extracted_judgment="賛成",
                matching_status="matched",
                matched_politician_id=20,
            ),
            ExtractedProposalJudge(
                id=2,
                proposal_id=10,
                extracted_politician_name="鈴木一郎",
                extracted_judgment="反対",
                matching_status="matched",
                matched_politician_id=21,
            ),
        ]
        repository.get_matched_judges = AsyncMock(return_value=matched_judges)

        # Execute
        result = await repository.bulk_convert_to_proposal_judges(proposal_id=10)

        # Assert
        assert len(result) == 2
        assert all(isinstance(judge, ProposalJudge) for judge in result)
        assert result[0].politician_id == 20
        assert result[0].approve == "賛成"
        assert result[1].politician_id == 21
        assert result[1].approve == "反対"

    @pytest.mark.asyncio
    async def test_bulk_convert_skips_invalid_judges(
        self,
        repository: ExtractedProposalJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk conversion skips judges that cannot be converted."""
        # Setup mock with one valid and one invalid judge
        matched_judges = [
            ExtractedProposalJudge(
                id=1,
                proposal_id=10,
                extracted_politician_name="山田太郎",
                extracted_judgment="賛成",
                matching_status="matched",
                matched_politician_id=20,
            ),
            ExtractedProposalJudge(
                id=2,
                proposal_id=10,
                extracted_politician_name="鈴木一郎",
                extracted_judgment="反対",
                matching_status="matched",
                matched_politician_id=None,  # Invalid - no politician ID
            ),
        ]
        repository.get_matched_judges = AsyncMock(return_value=matched_judges)

        # Execute
        result = await repository.bulk_convert_to_proposal_judges(proposal_id=10)

        # Assert
        assert len(result) == 1  # Only one valid judge converted
        assert result[0].politician_id == 20
