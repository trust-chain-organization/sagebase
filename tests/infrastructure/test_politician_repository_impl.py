"""Tests for PoliticianRepositoryImpl

Test suite covering initialization, conversion methods, and selected query methods
for the Politician repository.

NOTE: Most CRUD operations and complex queries are not included in this unit test
suite due to the repository's extensive use of raw SQL instead of ORM methods.
These operations require integration tests with a real database to test properly.
This test suite focuses on:
1. Initialization with different session types
2. Conversion methods (row ↔ entity ↔ model)
3. Selected critical query methods with mocked database responses

See Issue #684 and #692 for testing strategy decisions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician import Politician
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


@pytest.fixture
def mock_async_session():
    """Create mock async session for testing"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def async_repository(mock_async_session):
    """Create repository with async session"""
    return PoliticianRepositoryImpl(session=mock_async_session)


@pytest.fixture
def sample_politician():
    """Create sample politician entity for testing"""
    return Politician(
        id=1,
        name="テスト太郎",
        political_party_id=2,
        furigana="てすとたろう",
        district="東京1区",
        profile_page_url="https://example.com/politician/1",
    )


@pytest.fixture
def sample_politician_row():
    """Create sample politician row data for testing"""
    return {
        "id": 1,
        "name": "テスト太郎",
        "political_party_id": 2,
        "furigana": "てすとたろう",
        "prefecture": None,
        "electoral_district": "東京1区",
        "profile_url": "https://example.com/politician/1",
        "party_position": None,
    }


class TestPoliticianRepositoryImplInitialization:
    """Test repository initialization with different session types"""

    @pytest.mark.asyncio
    async def test_async_session_initialization(self):
        """Test that async session is properly initialized"""
        async_session = AsyncMock(spec=AsyncSession)
        repo = PoliticianRepositoryImpl(session=async_session)

        assert repo.session == async_session
        assert repo.entity_class == Politician

    @pytest.mark.asyncio
    async def test_initialization_with_custom_model_class(self):
        """Test initialization with custom model class"""
        async_session = AsyncMock(spec=AsyncSession)
        custom_model = MagicMock()
        repo = PoliticianRepositoryImpl(session=async_session, model_class=custom_model)

        assert repo.session == async_session
        assert repo.model_class == custom_model

    @pytest.mark.asyncio
    async def test_initialization_with_default_model_class(self):
        """Test default PoliticianModel when no model_class provided"""
        from src.infrastructure.persistence.politician_repository_impl import (
            PoliticianModel,
        )

        async_session = AsyncMock(spec=AsyncSession)
        repo = PoliticianRepositoryImpl(session=async_session)

        assert repo.model_class == PoliticianModel


class TestPoliticianRepositoryImplConversions:
    """Test conversion methods between row, entity, and model"""

    def test_row_to_entity_complete_data(self, async_repository, sample_politician_row):
        """Test converting database row to entity with complete data"""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_row
        for key, value in sample_politician_row.items():
            setattr(mock_row, key, value)

        entity = async_repository._row_to_entity(mock_row)

        assert isinstance(entity, Politician)
        assert entity.id == 1
        assert entity.name == "テスト太郎"
        assert entity.political_party_id == 2
        assert entity.furigana == "てすとたろう"
        assert entity.district == "東京1区"  # electoral_district → district mapping
        assert (
            entity.profile_page_url == "https://example.com/politician/1"
        )  # profile_url → profile_page_url mapping

    def test_row_to_entity_minimal_data(self, async_repository):
        """Test converting row to entity with minimal required data"""
        minimal_row = {"id": 1, "name": "最小太郎", "political_party_id": 3}

        mock_row = MagicMock()
        mock_row._mapping = minimal_row
        for key, value in minimal_row.items():
            setattr(mock_row, key, value)

        entity = async_repository._row_to_entity(mock_row)

        assert entity.id == 1
        assert entity.name == "最小太郎"
        assert entity.political_party_id == 3
        assert entity.district is None
        assert entity.profile_page_url is None

    def test_row_to_entity_with_dict_input(self, async_repository):
        """Test _row_to_entity handles dict input"""
        row_dict = {
            "id": 2,
            "name": "辞書太郎",
            "political_party_id": 4,
            "electoral_district": "大阪1区",
            "profile_url": "https://example.com/dict",
        }

        # Create mock with _mapping for dict-like rows
        mock_row = MagicMock()
        mock_row._mapping = row_dict

        entity = async_repository._row_to_entity(mock_row)

        assert entity.id == 2
        assert entity.name == "辞書太郎"
        assert entity.district == "大阪1区"

    def test_row_to_entity_raises_on_none(self, async_repository):
        """Test that _row_to_entity raises error on None input"""
        with pytest.raises(
            ValueError, match="Cannot convert None to Politician entity"
        ):
            async_repository._row_to_entity(None)

    def test_to_entity(self, async_repository, sample_politician_row):
        """Test _to_entity delegates to _row_to_entity"""
        mock_model = MagicMock()
        mock_model._mapping = sample_politician_row
        for key, value in sample_politician_row.items():
            setattr(mock_model, key, value)

        entity = async_repository._to_entity(mock_model)

        assert isinstance(entity, Politician)
        assert entity.name == "テスト太郎"

    def test_to_model_complete_data(self, async_repository, sample_politician):
        """Test converting entity to model with complete data"""
        model = async_repository._to_model(sample_politician)

        assert model.id == 1
        assert model.name == "テスト太郎"
        assert model.political_party_id == 2
        assert model.furigana == "てすとたろう"
        assert (
            model.electoral_district == "東京1区"
        )  # district → electoral_district mapping
        assert (
            model.profile_url == "https://example.com/politician/1"
        )  # profile_page_url → profile_url mapping
        assert model.prefecture is None  # No direct mapping from entity
        assert model.party_position is None  # Not in entity

    def test_to_model_minimal_data(self, async_repository):
        """Test converting entity to model with minimal data"""
        minimal_politician = Politician(name="最小太郎", political_party_id=3)

        model = async_repository._to_model(minimal_politician)

        assert model.name == "最小太郎"
        assert model.political_party_id == 3
        assert model.electoral_district is None
        assert model.profile_url is None

    def test_update_model_all_fields(self, async_repository, sample_politician):
        """Test updating all model fields from entity"""
        mock_model = MagicMock()

        async_repository._update_model(mock_model, sample_politician)

        assert mock_model.name == "テスト太郎"
        assert mock_model.political_party_id == 2
        assert mock_model.furigana == "てすとたろう"
        assert mock_model.electoral_district == "東京1区"
        assert mock_model.profile_url == "https://example.com/politician/1"

    def test_update_model_partial_fields(self, async_repository):
        """Test updating model with partial entity data"""
        mock_model = MagicMock()
        mock_model.name = "旧名前"
        mock_model.furigana = "きゅうなまえ"

        partial_politician = Politician(
            name="新名前", political_party_id=5, furigana="しんなまえ"
        )

        async_repository._update_model(mock_model, partial_politician)

        assert mock_model.name == "新名前"
        assert mock_model.furigana == "しんなまえ"
        assert mock_model.political_party_id == 5


class TestPoliticianRepositoryImplCRUD:
    """Test CRUD operations with mocked responses

    NOTE: These tests use mocks due to raw SQL implementation.
    For comprehensive testing, integration tests with a real database are recommended.
    """

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, async_repository, sample_politician_row):
        """Test get_by_id returns politician when found"""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_row
        for key, value in sample_politician_row.items():
            setattr(mock_row, key, value)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "テスト太郎"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, async_repository):
        """Test get_by_id returns None when not found"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_with_limit(self, async_repository):
        """Test get_all returns politicians with limit and offset"""
        row1_data = {
            "id": 1,
            "name": "太郎",
            "political_party_id": 1,
            "party_name": "党A",
        }
        row2_data = {
            "id": 2,
            "name": "次郎",
            "political_party_id": 2,
            "party_name": "党B",
        }

        mock_rows = []
        for row_data in [row1_data, row2_data]:
            mock_row = MagicMock()
            mock_row._mapping = row_data
            for key, value in row_data.items():
                setattr(mock_row, key, value)
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.get_all(limit=10, offset=0)

        assert len(results) == 2
        assert results[0].name == "太郎"
        assert results[1].name == "次郎"

    @pytest.mark.asyncio
    async def test_get_all_without_limit(self, async_repository):
        """Test get_all returns all politicians without limit"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.get_all(limit=None)

        assert results == []

    @pytest.mark.asyncio
    async def test_create_success(self, async_repository, sample_politician):
        """Test create successfully creates a politician"""
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 100,
            "name": sample_politician.name,
            "political_party_id": sample_politician.political_party_id,
            "electoral_district": sample_politician.district,
            "profile_url": sample_politician.profile_page_url,
            "furigana": sample_politician.furigana,
        }
        for key, value in mock_row._mapping.items():
            setattr(mock_row, key, value)

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        result = await async_repository.create(sample_politician)

        assert result.id == 100
        assert result.name == sample_politician.name
        async_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_failure(self, async_repository, sample_politician):
        """Test create raises error when no row returned"""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        with pytest.raises(RuntimeError, match="Failed to create politician"):
            await async_repository.create(sample_politician)

    @pytest.mark.asyncio
    async def test_update_success(self, async_repository):
        """Test update successfully updates a politician"""
        politician = Politician(
            id=50,
            name="更新太郎",
            political_party_id=3,
            furigana="こうしんたろう",
        )

        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 50,
            "name": "更新太郎",
            "political_party_id": 3,
            "furigana": "こうしんたろう",
            "electoral_district": None,
            "profile_url": None,
        }
        for key, value in mock_row._mapping.items():
            setattr(mock_row, key, value)

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        result = await async_repository.update(politician)

        assert result.id == 50
        assert result.name == "更新太郎"
        async_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, async_repository):
        """Test update raises error when politician not found"""
        from src.infrastructure.exceptions import UpdateError

        politician = Politician(
            id=999,
            name="存在しない",
            political_party_id=1,
        )

        mock_result = MagicMock()
        mock_result.first.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        with pytest.raises(UpdateError):
            await async_repository.update(politician)

    @pytest.mark.asyncio
    async def test_delete_success(self, async_repository):
        """Test delete successfully removes a politician"""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        result = await async_repository.delete(1)

        assert result is True
        async_repository.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, async_repository):
        """Test delete returns False when politician not found"""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        async_repository.session.execute = AsyncMock(return_value=mock_result)
        async_repository.session.commit = AsyncMock()

        result = await async_repository.delete(999)

        assert result is False


class TestPoliticianRepositoryImplQueryMethods:
    """Test selected critical query methods with mocked responses

    NOTE: These tests use mocks due to raw SQL implementation.
    For comprehensive testing, integration tests with a real database are recommended.
    """

    @pytest.mark.asyncio
    async def test_get_by_party(self, async_repository):
        """Test get_by_party returns all politicians for a party"""
        row1_data = {"id": 1, "name": "党員1", "political_party_id": 2}
        row2_data = {"id": 2, "name": "党員2", "political_party_id": 2}

        mock_rows = []
        for row_data in [row1_data, row2_data]:
            mock_row = MagicMock()
            mock_row._mapping = row_data
            for key, value in row_data.items():
                setattr(mock_row, key, value)
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.get_by_party(2)

        assert len(results) == 2
        assert results[0].name == "党員1"
        assert results[1].name == "党員2"

    @pytest.mark.asyncio
    async def test_get_by_party_empty(self, async_repository):
        """Test get_by_party returns empty list when no politicians found"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.get_by_party(999)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_all_for_matching(self, async_repository):
        """Test get_all_for_matching returns politicians with relevant fields"""
        row1_data = {
            "id": 1,
            "name": "マッチ太郎",
            "position": "議員",
            "prefecture": "東京都",
            "electoral_district": "東京1区",
            "party_name": "テスト党",
        }
        row2_data = {
            "id": 2,
            "name": "マッチ次郎",
            "position": "参議院",
            "prefecture": "大阪府",
            "electoral_district": "大阪1区",
            "party_name": "サンプル党",
        }

        mock_rows = []
        for row_data in [row1_data, row2_data]:
            mock_row = MagicMock()
            for key, value in row_data.items():
                setattr(mock_row, key, value)
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.get_all_for_matching()

        assert len(results) == 2
        assert results[0]["name"] == "マッチ太郎"
        assert results[0]["party_name"] == "テスト党"
        assert results[1]["name"] == "マッチ次郎"
        assert results[1]["party_name"] == "サンプル党"

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_found(
        self, async_repository, sample_politician_row
    ):
        """Test get_by_name_and_party returns politician when found"""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_row
        for key, value in sample_politician_row.items():
            setattr(mock_row, key, value)

        # Create mock result with synchronous methods (fetchone is NOT async)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        # session.execute IS async
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_name_and_party("テスト太郎", 2)

        assert result is not None
        assert result.name == "テスト太郎"
        assert result.political_party_id == 2

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_not_found(self, async_repository):
        """Test get_by_name_and_party returns None when not found"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_name_and_party("存在しない", 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_without_party_id(
        self, async_repository, sample_politician_row
    ):
        """Test get_by_name_and_party with None party_id searches by name only"""
        mock_row = MagicMock()
        mock_row._mapping = sample_politician_row
        for key, value in sample_politician_row.items():
            setattr(mock_row, key, value)

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_name_and_party("テスト太郎", None)

        assert result is not None
        assert result.name == "テスト太郎"

    @pytest.mark.asyncio
    async def test_search_by_name_multiple_results(self, async_repository):
        """Test search_by_name returns multiple matching politicians"""
        row1 = {
            "id": 1,
            "name": "テスト太郎",
            "political_party_id": 2,
            "electoral_district": "東京1区",
        }
        row2 = {
            "id": 2,
            "name": "テスト次郎",
            "political_party_id": 3,
            "electoral_district": "東京2区",
        }

        mock_rows = []
        for row_data in [row1, row2]:
            mock_row = MagicMock()
            mock_row._mapping = row_data
            for key, value in row_data.items():
                setattr(mock_row, key, value)
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.search_by_name("テスト")

        assert len(results) == 2
        assert results[0].name == "テスト太郎"
        assert results[1].name == "テスト次郎"

    @pytest.mark.asyncio
    async def test_search_by_name_no_results(self, async_repository):
        """Test search_by_name returns empty list when no matches"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.search_by_name("存在しない")

        assert results == []

    @pytest.mark.asyncio
    async def test_upsert_creates_new_politician(self, async_repository):
        """Test upsert creates new politician when not exists"""
        new_politician = Politician(
            name="新規太郎", political_party_id=4, furigana="しんきたろう"
        )

        with patch.object(
            async_repository, "get_by_name_and_party", return_value=None
        ) as mock_get:
            created_politician = Politician(
                id=10,
                name="新規太郎",
                political_party_id=4,
                furigana="しんきたろう",
            )
            with patch.object(
                async_repository, "create", return_value=created_politician
            ) as mock_create:
                result = await async_repository.upsert(new_politician)

                assert result.id == 10
                assert result.name == "新規太郎"
                mock_get.assert_called_once_with("新規太郎", 4)
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_politician(self, async_repository):
        """Test upsert updates existing politician when found"""
        existing = Politician(
            id=5, name="既存太郎", political_party_id=6, furigana="きそんたろう"
        )
        update_data = Politician(
            name="既存太郎",
            political_party_id=6,
            furigana="きそんたろう",
            district="更新区",
        )

        with patch.object(
            async_repository, "get_by_name_and_party", return_value=existing
        ) as mock_get:
            updated = Politician(
                id=5,
                name="既存太郎",
                political_party_id=6,
                furigana="きそんたろう",
                district="更新区",
            )
            with patch.object(
                async_repository, "update", return_value=updated
            ) as mock_update:
                result = await async_repository.upsert(update_data)

                assert result.id == 5
                assert result.district == "更新区"
                mock_get.assert_called_once()
                mock_update.assert_called_once()
                # Verify ID was set from existing
                assert mock_update.call_args[0][0].id == 5

    @pytest.mark.asyncio
    async def test_count_returns_total(self, async_repository):
        """Test count returns total number of politicians"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        count = await async_repository.count()

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_none(self, async_repository):
        """Test count returns 0 when scalar returns None"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        count = await async_repository.count()

        assert count == 0

    @pytest.mark.asyncio
    async def test_count_by_party(self, async_repository):
        """Test count_by_party returns count for specific party"""
        mock_row = MagicMock()
        mock_row.count = 15

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        count = await async_repository.count_by_party(2)

        assert count == 15

    @pytest.mark.asyncio
    async def test_count_by_party_returns_zero_when_none(self, async_repository):
        """Test count_by_party returns 0 when no row found"""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        count = await async_repository.count_by_party(999)

        assert count == 0


class TestPoliticianRepositoryImplBulkOperations:
    """Test bulk operations with mocked responses"""

    @pytest.mark.asyncio
    async def test_bulk_create_politicians_creates_new(self, async_repository):
        """Test bulk_create_politicians creates new politicians"""
        politicians_data = [
            {
                "name": "バルク太郎",
                "political_party_id": 7,
                "electoral_district": "神奈川1区",
            },
            {
                "name": "バルク次郎",
                "political_party_id": 7,
                "electoral_district": "神奈川2区",
            },
        ]

        created_politician1 = Politician(
            id=20,
            name="バルク太郎",
            political_party_id=7,
            district="神奈川1区",
        )
        created_politician2 = Politician(
            id=21,
            name="バルク次郎",
            political_party_id=7,
            district="神奈川2区",
        )

        # Mock get_by_name_and_party to return None (not exists)
        with patch.object(async_repository, "get_by_name_and_party", return_value=None):
            # Mock create_entity to return created politicians
            with patch.object(
                async_repository,
                "create_entity",
                side_effect=[created_politician1, created_politician2],
            ):
                # Mock session commit
                async_repository.session.commit = AsyncMock()

                result = await async_repository.bulk_create_politicians(
                    politicians_data
                )

                assert len(result["created"]) == 2
                assert len(result["updated"]) == 0
                assert len(result["errors"]) == 0
                assert result["created"][0].name == "バルク太郎"
                assert result["created"][1].name == "バルク次郎"

    @pytest.mark.asyncio
    async def test_bulk_create_politicians_updates_existing(self, async_repository):
        """Test bulk_create_politicians updates existing politicians"""
        politicians_data = [
            {
                "name": "既存太郎",
                "political_party_id": 8,
                "electoral_district": "新区画",
                "profile_url": "https://example.com/new",
            }
        ]

        existing = Politician(
            id=30,
            name="既存太郎",
            political_party_id=8,
            district="旧区画",
            profile_page_url="https://example.com/old",
        )
        updated = Politician(
            id=30,
            name="既存太郎",
            political_party_id=8,
            district="新区画",
            profile_page_url="https://example.com/new",
        )

        with patch.object(
            async_repository, "get_by_name_and_party", return_value=existing
        ):
            with patch.object(async_repository, "update", return_value=updated):
                async_repository.session.commit = AsyncMock()

                result = await async_repository.bulk_create_politicians(
                    politicians_data
                )

                assert len(result["created"]) == 0
                assert len(result["updated"]) == 1
                assert len(result["errors"]) == 0
                assert result["updated"][0].district == "新区画"

    @pytest.mark.asyncio
    async def test_bulk_create_politicians_handles_errors(self, async_repository):
        """Test bulk_create_politicians handles errors gracefully"""
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        politicians_data = [
            {"name": "エラー太郎", "political_party_id": 9},
            {"name": "成功太郎", "political_party_id": 9},
        ]

        # First politician causes error, second succeeds
        def side_effect_get(name, party_id):
            if name == "エラー太郎":
                raise SQLIntegrityError("statement", "params", "orig")
            return None

        created = Politician(id=40, name="成功太郎", political_party_id=9)

        with patch.object(
            async_repository, "get_by_name_and_party", side_effect=side_effect_get
        ):
            with patch.object(async_repository, "create_entity", return_value=created):
                async_repository.session.commit = AsyncMock()

                result = await async_repository.bulk_create_politicians(
                    politicians_data
                )

                # One succeeded, one failed
                assert len(result["created"]) == 1
                assert len(result["errors"]) == 1
                assert result["errors"][0]["data"]["name"] == "エラー太郎"


class TestPoliticianRepositoryImplUtilityMethods:
    """Test utility and helper methods"""

    @pytest.mark.asyncio
    async def test_fetch_as_dict_async(self, async_repository):
        """Test fetch_as_dict_async executes query and returns dicts"""
        row1_data = {"id": 1, "name": "辞書太郎", "party_name": "辞書党"}
        row2_data = {"id": 2, "name": "辞書次郎", "party_name": "辞書党"}

        mock_rows = []
        for row_data in [row1_data, row2_data]:
            mock_row = MagicMock()
            mock_row._mapping = row_data
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        async_repository.session.execute = AsyncMock(return_value=mock_result)

        results = await async_repository.fetch_as_dict_async(
            "SELECT * FROM politicians", {"limit": 10}
        )

        assert len(results) == 2
        assert results[0]["name"] == "辞書太郎"
        assert results[1]["name"] == "辞書次郎"

    @pytest.mark.asyncio
    async def test_create_entity_without_commit(
        self, async_repository, sample_politician
    ):
        """Test create_entity flushes but doesn't commit"""
        mock_model = MagicMock()
        mock_model.id = 50

        with patch.object(async_repository, "_to_model", return_value=mock_model):
            with patch.object(
                async_repository, "_to_entity", return_value=sample_politician
            ):
                async_repository.session.add = MagicMock()
                async_repository.session.flush = AsyncMock()
                async_repository.session.refresh = AsyncMock()

                await async_repository.create_entity(sample_politician)

                async_repository.session.add.assert_called_once()
                async_repository.session.flush.assert_called_once()
                async_repository.session.refresh.assert_called_once()
                # commit should NOT be called
                async_repository.session.commit.assert_not_called()
