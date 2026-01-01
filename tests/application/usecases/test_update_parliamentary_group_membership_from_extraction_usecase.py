"""Tests for UpdateParliamentaryGroupMembershipFromExtractionUseCase."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.extraction_result.parliamentary_group_membership_extraction_result import (  # noqa: E501
    ParliamentaryGroupMembershipExtractionResult,
)
from src.application.usecases.update_parliamentary_group_membership_from_extraction_usecase import (  # noqa: E501
    UpdateParliamentaryGroupMembershipFromExtractionUseCase,
)
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)


class TestUpdateParliamentaryGroupMembershipFromExtractionUseCase:
    """Test cases for UpdateParliamentaryGroupMembershipFromExtractionUseCase."""

    @pytest.fixture
    def mock_membership_repo(self):
        """Create mock membership repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extraction_log_repo(self):
        """Create mock extraction log repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_session_adapter(self):
        """Create mock session adapter."""
        adapter = AsyncMock()
        return adapter

    @pytest.fixture
    def use_case(
        self, mock_membership_repo, mock_extraction_log_repo, mock_session_adapter
    ):
        """Create UpdateParliamentaryGroupMembershipFromExtractionUseCase instance."""
        return UpdateParliamentaryGroupMembershipFromExtractionUseCase(
            membership_repo=mock_membership_repo,
            extraction_log_repo=mock_extraction_log_repo,
            session_adapter=mock_session_adapter,
        )

    @pytest.mark.asyncio
    async def test_update_membership_success(
        self,
        use_case,
        mock_membership_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """議員団メンバーシップの更新が成功する。"""
        # Setup
        membership = ParliamentaryGroupMembership(
            id=1,
            politician_id=100,
            parliamentary_group_id=10,
            start_date=date(2023, 1, 1),
            is_manually_verified=False,
        )
        extraction_result = ParliamentaryGroupMembershipExtractionResult(
            politician_id=100,
            parliamentary_group_id=10,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
            role="副代表",
        )
        extraction_log = ExtractionLog(
            id=400,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_membership_repo.get_by_id.return_value = membership
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is True
        assert result.extraction_log_id == 400

        # メンバーシップの各フィールドが更新されたことを確認
        assert membership.politician_id == 100
        assert membership.parliamentary_group_id == 10
        assert membership.start_date == date(2023, 1, 1)
        assert membership.end_date == date(2024, 12, 31)
        assert membership.role == "副代表"
        assert membership.latest_extraction_log_id == 400

        mock_membership_repo.update.assert_called_once_with(membership)
        mock_session_adapter.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_update_when_manually_verified(
        self,
        use_case,
        mock_membership_repo,
        mock_extraction_log_repo,
        mock_session_adapter,
    ):
        """手動検証済みの議員団メンバーシップは更新がスキップされる。"""
        # Setup
        membership = ParliamentaryGroupMembership(
            id=1,
            politician_id=100,
            parliamentary_group_id=10,
            start_date=date(2023, 1, 1),
            role="代表",
            is_manually_verified=True,
        )
        extraction_result = ParliamentaryGroupMembershipExtractionResult(
            politician_id=100,
            parliamentary_group_id=10,
            start_date=date(2023, 1, 1),
            role="副代表",  # 異なる役職
        )
        extraction_log = ExtractionLog(
            id=400,
            entity_type=EntityType.PARLIAMENTARY_GROUP_MEMBER,
            entity_id=1,
            pipeline_version="v1.0",
            extracted_data=extraction_result.to_dict(),
        )

        mock_membership_repo.get_by_id.return_value = membership
        mock_extraction_log_repo.create.return_value = extraction_log

        # Execute
        result = await use_case.execute(
            entity_id=1,
            extraction_result=extraction_result,
            pipeline_version="v1.0",
        )

        # Assert
        assert result.updated is False
        assert result.reason == "manually_verified"

        # メンバーシップは更新されていないことを確認
        assert membership.role == "代表"  # 元の役職のまま

        mock_membership_repo.update.assert_not_called()
        mock_session_adapter.commit.assert_not_called()
