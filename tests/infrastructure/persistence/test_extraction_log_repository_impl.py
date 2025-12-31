"""Tests for ExtractionLogRepositoryImpl."""

# pyright: reportUnknownParameterType=false, reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false, reportUnknownVariableType=false
# pyright: reportMissingParameterType=false, reportAttributeAccessIssue=false
# pyright: reportPrivateUsage=false, reportGeneralTypeIssues=false

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogModel,
    ExtractionLogRepositoryImpl,
)


class TestExtractionLogRepositoryImpl:
    """Test cases for ExtractionLogRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> ExtractionLogRepositoryImpl:
        """Create test repository."""
        return ExtractionLogRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_entity(self) -> ExtractionLog:
        """Create sample extraction log entity."""
        return ExtractionLog(
            entity_type=EntityType.SPEAKER,
            entity_id=123,
            pipeline_version="gemini-2.0-flash-v1",
            extracted_data={"name": "田中太郎", "role": "議員"},
            confidence_score=0.95,
            extraction_metadata={
                "model_name": "gemini-2.0-flash",
                "token_count_input": 100,
                "token_count_output": 50,
                "processing_time_ms": 500,
            },
            id=1,
        )

    @pytest.fixture
    def sample_model(self) -> Mock:
        """Create sample extraction log model."""
        model = Mock()
        model.id = 1
        model.entity_type = "speaker"
        model.entity_id = 123
        model.pipeline_version = "gemini-2.0-flash-v1"
        model.extracted_data = {"name": "田中太郎", "role": "議員"}
        model.confidence_score = 0.95
        model.extraction_metadata = {
            "model_name": "gemini-2.0-flash",
            "token_count_input": 100,
            "token_count_output": 50,
            "processing_time_ms": 500,
        }
        model.created_at = datetime.now()
        model.updated_at = datetime.now()
        return model

    def test_to_entity(
        self,
        repository: ExtractionLogRepositoryImpl,
        sample_model: Mock,
    ) -> None:
        """Test converting model to entity."""
        entity = repository._to_entity(sample_model)

        assert isinstance(entity, ExtractionLog)
        assert entity.id == sample_model.id
        assert entity.entity_type == EntityType.SPEAKER
        assert entity.entity_id == sample_model.entity_id
        assert entity.pipeline_version == sample_model.pipeline_version
        assert entity.extracted_data == sample_model.extracted_data
        assert entity.confidence_score == sample_model.confidence_score
        assert entity.extraction_metadata == sample_model.extraction_metadata
        assert entity.created_at == sample_model.created_at
        assert entity.updated_at == sample_model.updated_at

    def test_to_model(
        self,
        repository: ExtractionLogRepositoryImpl,
        sample_entity: ExtractionLog,
    ) -> None:
        """Test converting entity to model."""
        model = repository._to_model(sample_entity)

        assert isinstance(model, ExtractionLogModel)
        assert model.entity_type == "speaker"
        assert model.entity_id == sample_entity.entity_id
        assert model.pipeline_version == sample_entity.pipeline_version
        assert model.extracted_data == sample_entity.extracted_data
        assert model.confidence_score == sample_entity.confidence_score
        assert model.extraction_metadata == sample_entity.extraction_metadata

    def test_update_model_raises_not_implemented(
        self,
        repository: ExtractionLogRepositoryImpl,
        sample_entity: ExtractionLog,
    ) -> None:
        """Test that _update_model raises NotImplementedError."""
        model = ExtractionLogModel()

        with pytest.raises(NotImplementedError) as exc_info:
            repository._update_model(model, sample_entity)

        assert "immutable" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_get_by_entity(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
        sample_model: Mock,
    ) -> None:
        """Test get_by_entity method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            sample_model,
            sample_model,
        ]
        mock_session.execute.return_value = mock_result

        # Execute
        logs = await repository.get_by_entity(EntityType.SPEAKER, 123)

        # Assert
        assert len(logs) == 2
        assert all(isinstance(log, ExtractionLog) for log in logs)
        assert all(log.entity_type == EntityType.SPEAKER for log in logs)
        assert all(log.entity_id == 123 for log in logs)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_get_by_pipeline_version(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
        sample_model: Mock,
    ) -> None:
        """Test get_by_pipeline_version method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        logs = await repository.get_by_pipeline_version(
            "gemini-2.0-flash-v1", limit=10, offset=0
        )

        # Assert
        assert len(logs) == 1
        assert all(isinstance(log, ExtractionLog) for log in logs)
        assert all(log.pipeline_version == "gemini-2.0-flash-v1" for log in logs)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_get_by_entity_type(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
        sample_model: Mock,
    ) -> None:
        """Test get_by_entity_type method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        logs = await repository.get_by_entity_type(
            EntityType.SPEAKER, limit=10, offset=0
        )

        # Assert
        assert len(logs) == 1
        assert all(isinstance(log, ExtractionLog) for log in logs)
        assert all(log.entity_type == EntityType.SPEAKER for log in logs)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_get_latest_by_entity(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
        sample_model: Mock,
    ) -> None:
        """Test get_latest_by_entity method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_session.execute.return_value = mock_result

        # Execute
        log = await repository.get_latest_by_entity(EntityType.SPEAKER, 123)

        # Assert
        assert log is not None
        assert isinstance(log, ExtractionLog)
        assert log.entity_type == EntityType.SPEAKER
        assert log.entity_id == 123

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_get_latest_by_entity_not_found(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """Test get_latest_by_entity method when no log exists."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Execute
        log = await repository.get_latest_by_entity(EntityType.SPEAKER, 123)

        # Assert
        assert log is None

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_search_with_filters(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
        sample_model: Mock,
    ) -> None:
        """Test search method with multiple filters."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        logs = await repository.search(
            entity_type=EntityType.SPEAKER,
            pipeline_version="gemini-2.0-flash-v1",
            min_confidence_score=0.9,
            limit=10,
            offset=0,
        )

        # Assert
        assert len(logs) == 1
        assert all(isinstance(log, ExtractionLog) for log in logs)

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_count_by_entity_type(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """Test count_by_entity_type method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repository.count_by_entity_type(EntityType.SPEAKER)

        # Assert
        assert count == 42

    @pytest.mark.asyncio
    @patch("src.infrastructure.persistence.extraction_log_repository_impl.select")
    async def test_count_by_pipeline_version(
        self,
        mock_select: MagicMock,
        repository: ExtractionLogRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """Test count_by_pipeline_version method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repository.count_by_pipeline_version("gemini-2.0-flash-v1")

        # Assert
        assert count == 15

    @pytest.mark.parametrize(
        "entity_type",
        [
            EntityType.STATEMENT,
            EntityType.POLITICIAN,
            EntityType.SPEAKER,
            EntityType.CONFERENCE_MEMBER,
            EntityType.PARLIAMENTARY_GROUP_MEMBER,
        ],
    )
    def test_to_entity_all_entity_types(
        self, repository: ExtractionLogRepositoryImpl, entity_type: EntityType
    ) -> None:
        """Test _to_entity works for all entity types."""
        model = Mock()
        model.id = 1
        model.entity_type = entity_type.value
        model.entity_id = 100
        model.pipeline_version = "test-v1"
        model.extracted_data = {"test": "data"}
        model.confidence_score = 0.8
        model.extraction_metadata = {}
        model.created_at = datetime.now()
        model.updated_at = datetime.now()

        entity = repository._to_entity(model)

        assert entity.entity_type == entity_type
        assert entity.entity_id == 100
