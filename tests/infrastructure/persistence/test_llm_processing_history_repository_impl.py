"""Tests for LLMProcessingHistoryRepositoryImpl."""
# pyright: reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false, reportGeneralTypeIssues=false

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryModel,
    LLMProcessingHistoryRepositoryImpl,
)


class TestLLMProcessingHistoryRepositoryImpl:
    """Test cases for LLMProcessingHistoryRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> LLMProcessingHistoryRepositoryImpl:
        """Create test repository."""
        return LLMProcessingHistoryRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_entity(self) -> LLMProcessingHistory:
        """Create sample entity."""
        return LLMProcessingHistory(
            processing_type=ProcessingType.MINUTES_DIVISION,
            model_name="gemini-2.0-flash",
            model_version="2.0.0",
            prompt_template="Divide minutes",
            prompt_variables={"content": "test"},
            input_reference_type="meeting",
            input_reference_id=123,
            status=ProcessingStatus.COMPLETED,
            result={"sections": []},
            processing_metadata={
                "tokens": 1000,
                "token_count_input": 500,
                "token_count_output": 500,
                "processing_time_ms": 1200,
            },
            started_at=datetime.now() - timedelta(minutes=5),
            completed_at=datetime.now(),
            created_by="test_user",
            id=1,
        )

    @pytest.fixture
    def sample_model(self) -> Mock:
        """Create sample model."""
        model = Mock()
        model.id = 1
        model.processing_type = "minutes_division"
        model.model_name = "gemini-2.0-flash"
        model.model_version = "2.0.0"
        model.prompt_template = "Divide minutes"
        model.prompt_variables = {"content": "test"}
        model.input_reference_type = "meeting"
        model.input_reference_id = 123
        model.status = "completed"
        model.result = {"sections": []}
        model.processing_metadata = {
            "tokens": 1000,
            "token_count_input": 500,
            "token_count_output": 500,
            "processing_time_ms": 1200,
        }
        model.started_at = datetime.now() - timedelta(minutes=5)
        model.completed_at = datetime.now()
        model.created_at = datetime.now()
        model.updated_at = datetime.now()
        model.created_by = "test_user"
        return model

    def test_to_entity(
        self,
        repository: LLMProcessingHistoryRepositoryImpl,
        sample_model: Mock,
    ) -> None:
        """Test converting model to entity."""
        entity = repository._to_entity(sample_model)

        assert isinstance(entity, LLMProcessingHistory)
        assert entity.id == sample_model.id
        assert entity.processing_type == ProcessingType.MINUTES_DIVISION
        assert entity.model_name == sample_model.model_name
        assert entity.model_version == sample_model.model_version
        assert entity.prompt_template == sample_model.prompt_template
        assert entity.prompt_variables == sample_model.prompt_variables
        assert entity.input_reference_type == sample_model.input_reference_type
        assert entity.input_reference_id == sample_model.input_reference_id
        assert entity.status == ProcessingStatus.COMPLETED
        assert entity.result == sample_model.result
        assert entity.processing_metadata == sample_model.processing_metadata
        assert entity.created_at == sample_model.created_at
        assert entity.updated_at == sample_model.updated_at
        assert entity.created_by == sample_model.created_by

    def test_to_model(self, repository, sample_entity):
        """Test converting entity to model."""
        model = repository._to_model(sample_entity)

        assert isinstance(model, LLMProcessingHistoryModel)
        assert model.processing_type == "minutes_division"
        assert model.model_name == sample_entity.model_name
        assert model.model_version == sample_entity.model_version
        assert model.prompt_template == sample_entity.prompt_template
        assert model.prompt_variables == sample_entity.prompt_variables
        assert model.input_reference_type == sample_entity.input_reference_type
        assert model.input_reference_id == sample_entity.input_reference_id
        assert model.status == "completed"
        assert model.result == sample_entity.result
        assert model.processing_metadata == sample_entity.processing_metadata
        assert model.created_by == sample_entity.created_by

    def test_update_model(self, repository, sample_entity):
        """Test updating model from entity."""
        model = LLMProcessingHistoryModel()
        repository._update_model(model, sample_entity)

        assert model.processing_type == "minutes_division"
        assert model.model_name == sample_entity.model_name
        assert model.model_version == sample_entity.model_version
        assert model.status == "completed"
        assert model.created_by == sample_entity.created_by

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_by_processing_type(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_by_processing_type method."""
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
        results = await repository.get_by_processing_type(
            ProcessingType.MINUTES_DIVISION, limit=10, offset=0
        )

        # Verify
        assert len(results) == 1
        assert results[0].processing_type == ProcessingType.MINUTES_DIVISION
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_by_status(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_by_status method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repository.get_by_status(ProcessingStatus.COMPLETED)

        # Verify
        assert len(results) == 1
        assert results[0].status == ProcessingStatus.COMPLETED

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_by_model(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_by_model method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repository.get_by_model("gemini-2.0-flash", "2.0.0")

        # Verify
        assert len(results) == 1
        assert results[0].model_name == "gemini-2.0-flash"

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_by_input_reference(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_by_input_reference method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        results = await repository.get_by_input_reference("meeting", 123)

        # Verify
        assert len(results) == 1
        assert results[0].input_reference_type == "meeting"
        assert results[0].input_reference_id == 123

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_latest_by_input(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_latest_by_input method."""
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
        result = await repository.get_latest_by_input(
            "meeting", 123, ProcessingType.MINUTES_DIVISION
        )

        # Verify
        assert result is not None
        assert result.input_reference_type == "meeting"
        assert result.input_reference_id == 123

    @pytest.mark.asyncio
    async def test_count_by_status(self, repository, mock_session):
        """Test count_by_status method."""
        # Setup
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        # Execute
        count = await repository.count_by_status(ProcessingStatus.COMPLETED)

        # Verify
        assert count == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_search(self, mock_select, repository, mock_session, sample_model):
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
        results = await repository.search(
            processing_type=ProcessingType.MINUTES_DIVISION,
            model_name="gemini-2.0-flash",
            status=ProcessingStatus.COMPLETED,
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            limit=10,
            offset=0,
        )

        # Verify
        assert len(results) == 1
        assert results[0].processing_type == ProcessingType.MINUTES_DIVISION

    @pytest.mark.asyncio
    @patch(
        "src.infrastructure.persistence.llm_processing_history_repository_impl.select"
    )
    async def test_get_by_date_range(
        self, mock_select, repository, mock_session, sample_model
    ):
        """Test get_by_date_range method."""
        # Setup
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_model]
        mock_session.execute.return_value = mock_result

        # Execute
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        results = await repository.get_by_date_range(start_date, end_date)

        # Verify
        assert len(results) == 1
