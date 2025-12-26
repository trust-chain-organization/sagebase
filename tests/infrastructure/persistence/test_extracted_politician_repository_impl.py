"""Tests for ExtractedPoliticianRepositoryImpl."""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.infrastructure.persistence.extracted_politician_repository_impl import (
    ExtractedPoliticianModel,
    ExtractedPoliticianRepositoryImpl,
)


class TestExtractedPoliticianRepositoryImpl:
    """Test cases for ExtractedPoliticianRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock session."""
        session = MagicMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ExtractedPoliticianRepositoryImpl:
        """Create extracted politician repository."""
        return ExtractedPoliticianRepositoryImpl(mock_session)

    def _create_mock_row(self, **kwargs: Any) -> MagicMock:
        """Create a mock database row."""
        defaults = {
            "id": 1,
            "name": "山田太郎",
            "party_id": 1,
            "district": "東京1区",
            "profile_url": "https://example.com/profile",
            "status": "pending",
            "extracted_at": datetime(2023, 1, 1),
            "reviewed_at": None,
            "reviewer_id": None,
        }
        defaults.update(kwargs)

        mock_row = MagicMock()
        mock_row._mapping = defaults
        for key, value in defaults.items():
            setattr(mock_row, key, value)
        return mock_row

    @pytest.mark.asyncio
    async def test_get_pending_without_party_id(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_pending without party_id filter."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, status="pending"),
            self._create_mock_row(id=2, status="pending", party_id=2),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_pending()

        # Verify
        assert len(result) == 2
        assert all(p.status == "pending" for p in result)
        assert result[0].id == 1
        assert result[1].id == 2

    @pytest.mark.asyncio
    async def test_get_pending_with_party_id(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_pending with party_id filter."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, status="pending", party_id=1),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_pending(party_id=1)

        # Verify
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].party_id == 1
        assert result[0].status == "pending"

    @pytest.mark.asyncio
    async def test_get_by_status(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_status method."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, status="approved"),
            self._create_mock_row(id=2, status="approved", name="鈴木一郎"),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_by_status("approved")

        # Verify
        assert len(result) == 2
        assert all(p.status == "approved" for p in result)
        assert result[0].id == 1
        assert result[1].name == "鈴木一郎"

    @pytest.mark.asyncio
    async def test_get_by_party(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_by_party method."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, party_id=2, name="佐藤太郎"),
            self._create_mock_row(id=2, party_id=2, name="田中花子"),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_by_party(2)

        # Verify
        assert len(result) == 2
        assert all(p.party_id == 2 for p in result)
        assert result[0].name == "佐藤太郎"
        assert result[1].name == "田中花子"

    @pytest.mark.asyncio
    async def test_update_status_to_approved(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_status to approved status."""
        # Setup
        reviewed_at = datetime.now()
        updated_row = self._create_mock_row(
            id=1,
            status="approved",
            reviewed_at=reviewed_at,
            reviewer_id=5,
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = updated_row

        execute_count = 0

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            nonlocal execute_count
            execute_count += 1
            if execute_count == 2:  # Second call is for get_by_id
                return mock_result
            return MagicMock()

        mock_session.execute = async_execute

        async def async_commit() -> None:
            return None

        mock_session.commit = async_commit

        async def async_get(
            model_class: Any, entity_id: Any
        ) -> ExtractedPoliticianModel:
            return ExtractedPoliticianModel(
                id=1,
                name="山田太郎",
                party_id=1,
                district="東京1区",
                position="衆議院議員",
                profile_url="https://example.com/profile",
                status="approved",
                extracted_at=datetime(2023, 1, 1),
                reviewed_at=reviewed_at,
                reviewer_id=5,
            )

        mock_session.get = async_get

        # Execute
        result = await repository.update_status(1, "approved", reviewer_id=5)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.status == "approved"
        assert result.reviewed_at == reviewed_at
        assert result.reviewer_id == 5

    @pytest.mark.asyncio
    async def test_update_status_to_pending(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test update_status to pending status (should clear reviewer info)."""
        # Setup
        updated_row = self._create_mock_row(
            id=1,
            status="pending",
            reviewed_at=None,
            reviewer_id=None,
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = updated_row

        execute_count = 0

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            nonlocal execute_count
            execute_count += 1
            if execute_count == 2:  # Second call is for get_by_id
                return mock_result
            return MagicMock()

        mock_session.execute = async_execute

        async def async_commit() -> None:
            return None

        mock_session.commit = async_commit

        async def async_get(
            model_class: Any, entity_id: Any
        ) -> ExtractedPoliticianModel:
            return ExtractedPoliticianModel(
                id=1,
                name="山田太郎",
                party_id=1,
                district="東京1区",
                position="衆議院議員",
                profile_url="https://example.com/profile",
                status="pending",
                extracted_at=datetime(2023, 1, 1),
                reviewed_at=None,
                reviewer_id=None,
            )

        mock_session.get = async_get

        # Execute
        result = await repository.update_status(1, "pending")

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.status == "pending"
        assert result.reviewed_at is None
        assert result.reviewer_id is None

    @pytest.mark.asyncio
    async def test_get_summary_by_status(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_summary_by_status method."""
        # Setup
        mock_rows = [
            MagicMock(status="pending", count=5),
            MagicMock(status="approved", count=3),
            MagicMock(status="rejected", count=1),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_summary_by_status()

        # Verify
        assert result["pending"] == 5
        assert result["approved"] == 3
        assert result["rejected"] == 1
        assert result["reviewed"] == 0
        assert result["total"] == 9  # 5 + 3 + 1

    @pytest.mark.asyncio
    async def test_bulk_create(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test bulk_create method."""
        # Setup
        politicians = [
            PoliticianPartyExtractedPolitician(name="山田太郎", party_id=1),
            PoliticianPartyExtractedPolitician(name="鈴木花子", party_id=2),
        ]

        # Mock add_all and refresh
        mock_session.add_all = MagicMock()

        async def async_commit() -> None:
            return None

        mock_commit = MagicMock(side_effect=async_commit)
        mock_session.commit = mock_commit

        async def async_refresh(model: Any) -> None:
            model.id = 1 if model.name == "山田太郎" else 2

        mock_session.refresh = async_refresh

        # Execute
        result = await repository.bulk_create(politicians)

        # Verify
        assert len(result) == 2
        assert result[0].name == "山田太郎"
        assert result[1].name == "鈴木花子"
        mock_session.add_all.assert_called_once()
        mock_commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_duplicates_with_party_id(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_duplicates with party_id filter."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, name="山田太郎", party_id=1),
            self._create_mock_row(id=2, name="山田太郎", party_id=1),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_duplicates("山田太郎", party_id=1)

        # Verify
        assert len(result) == 2
        assert all(p.name == "山田太郎" for p in result)
        assert all(p.party_id == 1 for p in result)

    @pytest.mark.asyncio
    async def test_get_duplicates_without_party_id(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test get_duplicates without party_id filter."""
        # Setup
        mock_rows = [
            self._create_mock_row(id=1, name="山田太郎", party_id=1),
            self._create_mock_row(id=2, name="山田太郎", party_id=2),
            self._create_mock_row(id=3, name="山田太郎", party_id=None),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        async def async_execute(query: Any, params: Any = None) -> MagicMock:
            return mock_result

        mock_session.execute = async_execute

        # Execute
        result = await repository.get_duplicates("山田太郎")

        # Verify
        assert len(result) == 3
        assert all(p.name == "山田太郎" for p in result)
        assert result[0].party_id == 1
        assert result[1].party_id == 2
        assert result[2].party_id is None

    @pytest.mark.asyncio
    async def test_row_to_entity_conversion(
        self, repository: ExtractedPoliticianRepositoryImpl, mock_session: MagicMock
    ) -> None:
        """Test conversion from database row to domain entity."""
        # Setup
        extracted_at = datetime(2023, 1, 1, 12, 0, 0)
        reviewed_at = datetime(2023, 1, 2, 12, 0, 0)

        mock_row = self._create_mock_row(
            id=99,
            name="テスト政治家",
            party_id=3,
            district="大阪1区",
            profile_url="https://test.com/profile",
            status="reviewed",
            extracted_at=extracted_at,
            reviewed_at=reviewed_at,
            reviewer_id=10,
        )

        # Execute
        entity = repository._row_to_entity(mock_row)  # type: ignore[attr-defined]

        # Verify
        assert isinstance(entity, PoliticianPartyExtractedPolitician)
        assert entity.id == 99
        assert entity.name == "テスト政治家"
        assert entity.party_id == 3
        assert entity.district == "大阪1区"
        assert entity.profile_url == "https://test.com/profile"
        assert entity.status == "reviewed"
        assert entity.extracted_at == extracted_at
        assert entity.reviewed_at == reviewed_at
        assert entity.reviewer_id == 10
