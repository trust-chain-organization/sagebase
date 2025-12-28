"""Tests for ExtractedConferenceMemberRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberModel,
    ExtractedConferenceMemberRepositoryImpl,
)


class TestExtractedConferenceMemberRepositoryImpl:
    """Test cases for ExtractedConferenceMemberRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> ExtractedConferenceMemberRepositoryImpl:
        """Create extracted conference member repository."""
        return ExtractedConferenceMemberRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_member_entity(self) -> ExtractedConferenceMember:
        """Sample extracted conference member entity."""
        return ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            extracted_party_name="自民党",
            matching_status="pending",
            matched_politician_id=None,
        )

    @pytest.mark.asyncio
    async def test_get_pending_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_pending_members returns pending members."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matching_status = "pending"
        mock_row.matched_politician_id = None
        mock_row.matching_confidence = None
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_pending_members(10)

        assert len(result) == 1
        assert result[0].matching_status == "pending"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_members returns matched members."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matching_status = "matched"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_matched_members(10)

        assert len(result) == 1
        assert result[0].matched_politician_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_matching_result_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update_matching_result successfully updates result."""
        # Mock for update query
        mock_update_result = MagicMock()

        # Mock for get_by_id query
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.matching_status = "matched"
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_get_result = MagicMock()
        mock_get_result.fetchone = MagicMock(return_value=mock_row)

        mock_session.execute.side_effect = [mock_update_result, mock_get_result]

        result = await repository.update_matching_result(1, 100, 0.95, "matched")

        assert result is not None
        assert result.matched_politician_id == 100
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_matching_result_not_found(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update_matching_result returns None when not found."""
        # Mock for update query
        mock_update_result = MagicMock()

        # Mock for get_by_id query (returns None)
        mock_get_result = MagicMock()
        mock_get_result.fetchone = MagicMock(return_value=None)

        mock_session.execute.side_effect = [mock_update_result, mock_get_result]

        result = await repository.update_matching_result(999, 100, 0.95, "matched")

        assert result is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference returns members for conference."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = None
        mock_row.extracted_at = None
        mock_row.matching_status = "pending"
        mock_row.matched_politician_id = None
        mock_row.matching_confidence = None
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10)

        assert len(result) == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_extraction_summary(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_extraction_summary returns summary dict."""
        # Mock rows returned by SQL query
        mock_row1 = MagicMock()
        mock_row1.matching_status = "pending"
        mock_row1.count = 20

        mock_row2 = MagicMock()
        mock_row2.matching_status = "matched"
        mock_row2.count = 80

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_extraction_summary()

        # Result should be a dict
        assert isinstance(result, dict)
        assert result["total"] == 100
        assert result["pending"] == 20
        assert result["matched"] == 80
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test bulk_create creates multiple members."""
        # Mock session methods
        mock_session.add_all = MagicMock()
        mock_session.refresh = AsyncMock()

        result = await repository.bulk_create([sample_member_entity])

        # Result should be a list of entities
        assert isinstance(result, list)
        assert len(result) == 1
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_to_entity(
        self, repository: ExtractedConferenceMemberRepositoryImpl
    ) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = ExtractedConferenceMemberModel(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            extracted_role="議員",
            extracted_party_name="自民党",
            extracted_at=None,
            matched_politician_id=None,
            matching_confidence=None,
            matching_status="pending",
            matched_at=None,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, ExtractedConferenceMember)
        assert entity.id == 1
        assert entity.extracted_name == "山田太郎"

    def test_to_model(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_member_entity)

        assert isinstance(model, ExtractedConferenceMemberModel)
        assert model.conference_id == 10
        assert model.extracted_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_get_all_returns_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all members."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.conference_id = 10
        mock_row1.extracted_name = "山田太郎"
        mock_row1.source_url = "https://example.com/member1"
        mock_row1.matching_status = "pending"
        mock_row1.extracted_at = None

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.conference_id = 10
        mock_row2.extracted_name = "鈴木花子"
        mock_row2.source_url = "https://example.com/member2"
        mock_row2.matching_status = "matched"
        mock_row2.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].extracted_name == "山田太郎"
        assert result[1].extracted_name == "鈴木花子"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset parameters."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.matching_status = "pending"
        mock_row.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns empty list when no members exist."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test create successfully creates member."""
        mock_row = MagicMock()
        mock_row.id = 1

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_member_entity)

        assert result.id == 1
        assert result.extracted_name == "山田太郎"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test update successfully updates member."""
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result

        sample_member_entity.extracted_name = "山田太郎（更新）"
        result = await repository.update(sample_member_entity)

        assert result.extracted_name == "山田太郎（更新）"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update raises ValueError when entity has no ID."""
        entity = ExtractedConferenceMember(
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            matching_status="pending",
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete successfully deletes member."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete returns False when member not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number of members."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns 0 when no members exist."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_members_all(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_pending_members with conference_id=None returns all pending."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.matching_status = "pending"
        mock_row.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_pending_members(None)

        assert len(result) == 1
        assert result[0].matching_status == "pending"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_members_all(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_members with conference_id=None returns all matched."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.matching_status = "matched"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_matched_members(None)

        assert len(result) == 1
        assert result[0].matching_status == "matched"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_members_with_min_confidence(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_members with min_confidence filter."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.matching_status = "matched"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_matched_members(10, min_confidence=0.9)

        assert len(result) == 1
        assert result[0].matching_confidence >= 0.9
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_extraction_summary_all(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_extraction_summary with conference_id=None."""
        mock_row1 = MagicMock()
        mock_row1.matching_status = "pending"
        mock_row1.count = 30

        mock_row2 = MagicMock()
        mock_row2.matching_status = "matched"
        mock_row2.count = 70

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_extraction_summary(None)

        assert result["total"] == 100
        assert result["pending"] == 30
        assert result["matched"] == 70
        mock_session.execute.assert_called_once()

    def test_update_model(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = ExtractedConferenceMemberModel(
            id=1,
            conference_id=5,
            extracted_name="旧名前",
            source_url="https://old.com/member",
            matching_status="pending",
            extracted_at=None,
        )

        repository._update_model(model, sample_member_entity)

        assert model.conference_id == 10
        assert model.extracted_name == "山田太郎"
        assert model.source_url == "https://example.com/member"

    def test_to_model_with_additional_data(
        self, repository: ExtractedConferenceMemberRepositoryImpl
    ) -> None:
        """Test _to_model with additional_data."""
        entity = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            matching_status="pending",
            additional_data='{"key": "value"}',
        )

        model = repository._to_model(entity)

        assert isinstance(model, ExtractedConferenceMemberModel)
        assert model.additional_data == '{"key": "value"}'
