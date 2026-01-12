"""Tests for PoliticianOperationLog entity."""

from datetime import datetime
from uuid import uuid4

from src.domain.entities.politician_operation_log import (
    PoliticianOperationLog,
    PoliticianOperationType,
)


class TestPoliticianOperationType:
    """Test cases for PoliticianOperationType enum."""

    def test_create_type_value(self) -> None:
        """Test CREATE type has correct value."""
        assert PoliticianOperationType.CREATE.value == "create"

    def test_update_type_value(self) -> None:
        """Test UPDATE type has correct value."""
        assert PoliticianOperationType.UPDATE.value == "update"

    def test_delete_type_value(self) -> None:
        """Test DELETE type has correct value."""
        assert PoliticianOperationType.DELETE.value == "delete"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert PoliticianOperationType("create") == PoliticianOperationType.CREATE
        assert PoliticianOperationType("update") == PoliticianOperationType.UPDATE
        assert PoliticianOperationType("delete") == PoliticianOperationType.DELETE


class TestPoliticianOperationLog:
    """Test cases for PoliticianOperationLog entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        log = PoliticianOperationLog(
            politician_id=1,
            politician_name="山田太郎",
            operation_type=PoliticianOperationType.CREATE,
        )

        assert log.politician_id == 1
        assert log.politician_name == "山田太郎"
        assert log.operation_type == PoliticianOperationType.CREATE
        assert log.user_id is None
        assert log.operation_details == {}
        assert log.operated_at is not None
        assert log.id is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        user_id = uuid4()
        operated_at = datetime(2024, 1, 15, 10, 0)
        details = {"prefecture": "東京都", "district": "東京1区"}

        log = PoliticianOperationLog(
            id=1,
            politician_id=42,
            politician_name="田中花子",
            operation_type=PoliticianOperationType.UPDATE,
            user_id=user_id,
            operation_details=details,
            operated_at=operated_at,
        )

        assert log.id == 1
        assert log.politician_id == 42
        assert log.politician_name == "田中花子"
        assert log.operation_type == PoliticianOperationType.UPDATE
        assert log.user_id == user_id
        assert log.operation_details == details
        assert log.operated_at == operated_at

    def test_str_representation(self) -> None:
        """Test string representation."""
        log = PoliticianOperationLog(
            politician_id=1,
            politician_name="山田太郎",
            operation_type=PoliticianOperationType.CREATE,
        )

        str_repr = str(log)
        assert "山田太郎" in str_repr
        assert "create" in str_repr

    def test_operation_details_default_empty_dict(self) -> None:
        """Test that operation_details defaults to empty dict when None."""
        log = PoliticianOperationLog(
            politician_id=1,
            politician_name="Test",
            operation_type=PoliticianOperationType.DELETE,
            operation_details=None,
        )

        assert log.operation_details == {}

    def test_operated_at_default_to_now(self) -> None:
        """Test that operated_at defaults to current time."""
        before = datetime.now()
        log = PoliticianOperationLog(
            politician_id=1,
            politician_name="Test",
            operation_type=PoliticianOperationType.CREATE,
        )
        after = datetime.now()

        assert before <= log.operated_at <= after

    def test_each_operation_type(self) -> None:
        """Test creating log with each operation type."""
        for op_type in PoliticianOperationType:
            log = PoliticianOperationLog(
                politician_id=1,
                politician_name="Test",
                operation_type=op_type,
            )
            assert log.operation_type == op_type

    def test_operation_details_with_various_data(self) -> None:
        """Test operation_details can hold various types of data."""
        details = {
            "prefecture": "東京都",
            "district": "東京1区",
            "party_id": 1,
            "profile_url": "https://example.com/profile",
            "nested": {"key": "value"},
        }
        log = PoliticianOperationLog(
            politician_id=1,
            politician_name="Test",
            operation_type=PoliticianOperationType.CREATE,
            operation_details=details,
        )

        assert log.operation_details == details
        assert log.operation_details["prefecture"] == "東京都"
        assert log.operation_details["party_id"] == 1
        assert log.operation_details["nested"]["key"] == "value"
