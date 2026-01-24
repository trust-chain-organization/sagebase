"""ProposalOperationLogエンティティのテスト."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.domain.entities.proposal_operation_log import (
    ProposalOperationLog,
    ProposalOperationType,
)


class TestProposalOperationType:
    """ProposalOperationType enumのテスト."""

    def test_enum_values(self) -> None:
        """enumの値が正しいことを確認."""
        assert ProposalOperationType.CREATE.value == "create"
        assert ProposalOperationType.UPDATE.value == "update"
        assert ProposalOperationType.DELETE.value == "delete"

    def test_enum_count(self) -> None:
        """enumの数が正しいことを確認."""
        assert len(ProposalOperationType) == 3


class TestProposalOperationLog:
    """ProposalOperationLogエンティティのテスト."""

    def test_initialization_with_required_fields(self) -> None:
        """必須フィールドのみでの初期化テスト."""
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title="テスト議案",
            operation_type=ProposalOperationType.CREATE,
        )

        assert log.proposal_id == 1
        assert log.proposal_title == "テスト議案"
        assert log.operation_type == ProposalOperationType.CREATE
        assert log.user_id is None
        assert log.operation_details == {}
        assert log.operated_at is not None
        assert log.id is None

    def test_initialization_with_all_fields(self) -> None:
        """全フィールドでの初期化テスト."""
        user_id = uuid4()
        operated_at = datetime(2024, 1, 15, 10, 30, 0)
        operation_details = {"old_title": "旧タイトル", "new_title": "新タイトル"}

        log = ProposalOperationLog(
            id=42,
            proposal_id=100,
            proposal_title="予算案",
            operation_type=ProposalOperationType.UPDATE,
            user_id=user_id,
            operation_details=operation_details,
            operated_at=operated_at,
        )

        assert log.id == 42
        assert log.proposal_id == 100
        assert log.proposal_title == "予算案"
        assert log.operation_type == ProposalOperationType.UPDATE
        assert log.user_id == user_id
        assert log.operation_details == operation_details
        assert log.operated_at == operated_at

    def test_operation_details_defaults_to_empty_dict(self) -> None:
        """operation_detailsがNoneの場合、空の辞書にデフォルトされることを確認."""
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title="テスト",
            operation_type=ProposalOperationType.DELETE,
            operation_details=None,
        )

        assert log.operation_details == {}

    def test_operated_at_defaults_to_now(self) -> None:
        """operated_atがNoneの場合、現在時刻にデフォルトされることを確認."""
        before = datetime.now()
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title="テスト",
            operation_type=ProposalOperationType.CREATE,
        )
        after = datetime.now()

        assert before <= log.operated_at <= after

    def test_str_representation(self) -> None:
        """文字列表現のテスト."""
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title="テスト議案タイトル",
            operation_type=ProposalOperationType.DELETE,
        )

        str_repr = str(log)
        assert "proposal_id=1" in str_repr
        assert "operation_type=delete" in str_repr
        assert "ProposalOperationLog" in str_repr

    def test_str_representation_with_long_title(self) -> None:
        """長いタイトルの文字列表現テスト（30文字で切り詰められることを確認）."""
        long_title = "A" * 50  # 50文字のタイトル
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title=long_title,
            operation_type=ProposalOperationType.UPDATE,
        )

        str_repr = str(log)
        # 30文字 + "..." が含まれることを確認
        assert "A" * 30 in str_repr
        assert "..." in str_repr

    @pytest.mark.parametrize(
        "operation_type",
        [
            ProposalOperationType.CREATE,
            ProposalOperationType.UPDATE,
            ProposalOperationType.DELETE,
        ],
    )
    def test_all_operation_types(self, operation_type: ProposalOperationType) -> None:
        """全ての操作タイプで正しく初期化されることを確認."""
        log = ProposalOperationLog(
            proposal_id=1,
            proposal_title="テスト",
            operation_type=operation_type,
        )

        assert log.operation_type == operation_type

    def test_inherits_from_base_entity(self) -> None:
        """BaseEntityを継承していることを確認."""
        log = ProposalOperationLog(
            id=1,
            proposal_id=1,
            proposal_title="テスト",
            operation_type=ProposalOperationType.CREATE,
        )

        # BaseEntityのidフィールドが継承されていることを確認
        assert hasattr(log, "id")
        assert log.id == 1
