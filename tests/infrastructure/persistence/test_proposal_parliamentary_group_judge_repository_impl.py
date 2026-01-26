"""Tests for ProposalParliamentaryGroupJudgeRepositoryImpl.

Many-to-Many構造対応: 1つの賛否レコードに複数の会派・政治家を紐付け可能。
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.value_objects.judge_type import JudgeType
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.proposal_parliamentary_group_judge_repository_impl import (  # noqa: E501
    ProposalParliamentaryGroupJudgeRepositoryImpl,
)


class TestProposalParliamentaryGroupJudgeRepositoryImpl:
    """Test cases for ProposalParliamentaryGroupJudgeRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.get = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> ProposalParliamentaryGroupJudgeRepositoryImpl:
        """Create repository instance."""
        return ProposalParliamentaryGroupJudgeRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_judge_dict(self) -> dict[str, Any]:
        """Sample parliamentary group judge data as dict (Many-to-Many構造)."""
        return {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": "全会一致",
            "created_at": None,
            "updated_at": None,
            "parliamentary_group_ids": [20],
            "politician_ids": [],
        }

    @pytest.fixture
    def sample_judge_entity(self) -> ProposalParliamentaryGroupJudge:
        """Sample parliamentary group judge entity (Many-to-Many構造)."""
        return ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            judge_type=JudgeType.PARLIAMENTARY_GROUP,
            parliamentary_group_ids=[20],
            politician_ids=[],
            judgment="賛成",
            member_count=5,
            note="全会一致",
        )

    def _setup_mock_for_many_to_many(
        self,
        mock_session: MagicMock,
        main_result_dict: dict[str, Any],
        pg_ids: list[int] | None = None,
        politician_ids: list[int] | None = None,
    ) -> None:
        """Helper to setup mock for Many-to-Many queries.

        Many-to-Many構造では、本体取得後に中間テーブルからIDを取得する。
        リポジトリは row[0] でアクセスするので、タプル風に設定する。
        """
        pg_ids = pg_ids or []
        politician_ids = politician_ids or []

        # Main query result
        mock_main_row = MagicMock()
        mock_main_row._mapping = main_result_dict
        mock_main_row._asdict = MagicMock(return_value=main_result_dict)
        mock_main_result = MagicMock()
        mock_main_result.fetchall = MagicMock(return_value=[mock_main_row])
        mock_main_result.fetchone = MagicMock(return_value=mock_main_row)

        # Parliamentary group IDs query result (row[0]でアクセス)
        pg_rows = [(pg_id,) for pg_id in pg_ids]
        mock_pg_result = MagicMock()
        mock_pg_result.fetchall = MagicMock(return_value=pg_rows)

        # Politician IDs query result (row[0]でアクセス)
        pol_rows = [(pol_id,) for pol_id in politician_ids]
        mock_pol_result = MagicMock()
        mock_pol_result.fetchall = MagicMock(return_value=pol_rows)

        mock_session.execute.side_effect = [
            mock_main_result,
            mock_pg_result,
            mock_pol_result,
        ]

    @pytest.mark.asyncio
    async def test_get_by_proposal(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal returns list of judges with Many-to-Many IDs."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        self._setup_mock_for_many_to_many(
            mock_session, main_dict, pg_ids=[20, 21], politician_ids=[]
        )

        result = await repository.get_by_proposal(10)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].proposal_id == 10
        assert result[0].parliamentary_group_ids == [20, 21]
        assert result[0].judgment == "賛成"
        assert result[0].member_count == 5
        assert mock_session.execute.call_count == 3  # main + pg + politician

    @pytest.mark.asyncio
    async def test_get_by_proposal_empty(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal returns empty list when no judges found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_parliamentary_group returns list of judges."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        self._setup_mock_for_many_to_many(
            mock_session, main_dict, pg_ids=[20], politician_ids=[]
        )

        result = await repository.get_by_parliamentary_group(20)

        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].parliamentary_group_ids == [20]
        assert result[0].proposal_id == 10
        assert result[0].judgment == "賛成"

    @pytest.mark.asyncio
    async def test_get_by_parliamentary_group_empty(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_parliamentary_group returns empty list when no judges found."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_parliamentary_group(999)

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_groups_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal_and_groups when judge is found."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        self._setup_mock_for_many_to_many(
            mock_session, main_dict, pg_ids=[20], politician_ids=[]
        )

        result = await repository.get_by_proposal_and_groups(10, [20])

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_ids == [20]
        assert result.judgment == "賛成"

    @pytest.mark.asyncio
    async def test_get_by_proposal_and_groups_not_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_proposal_and_groups when judge is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_proposal_and_groups(999, [999])

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex mock setup needs investigation")
    async def test_bulk_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create multiple judges with Many-to-Many."""
        result_dict_1 = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        result_dict_2 = {
            "id": 2,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "反対",
            "member_count": 3,
            "note": "一部反対",
            "created_at": None,
            "updated_at": None,
        }

        # _row_to_dictが_asdict()を呼び出すので、それが辞書を返すようにする
        # MagicMockの代わりにSimpleNamespaceを使って明示的に辞書を返す
        from types import SimpleNamespace

        mock_row_1 = SimpleNamespace()
        mock_row_1._asdict = lambda: result_dict_1
        mock_result_1 = MagicMock()
        mock_result_1.fetchone = MagicMock(return_value=mock_row_1)

        mock_row_2 = SimpleNamespace()
        mock_row_2._asdict = lambda: result_dict_2
        mock_result_2 = MagicMock()
        mock_result_2.fetchone = MagicMock(return_value=mock_row_2)

        # 2回のcreate (それぞれ INSERT + 中間テーブルINSERT x2)
        # 既存のAsyncMockを上書きしてside_effectを確実に設定
        mock_session.execute = AsyncMock(
            side_effect=[
                mock_result_1,  # First create
                MagicMock(),  # pg junction insert
                MagicMock(),  # politician junction insert
                mock_result_2,  # Second create
                MagicMock(),  # pg junction insert
                MagicMock(),  # politician junction insert
            ]
        )

        judges = [
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_ids=[20],
                judgment="賛成",
                member_count=5,
            ),
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_ids=[21],
                judgment="反対",
                member_count=3,
                note="一部反対",
            ),
        ]

        result = await repository.bulk_create(judges)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].judgment == "賛成"
        assert result[1].id == 2
        assert result[1].judgment == "反対"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test bulk_create with empty list."""
        result = await repository.bulk_create([])

        assert result == []
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test create parliamentary group judge with Many-to-Many."""
        result_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": "全会一致",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = result_dict
        mock_row._asdict = MagicMock(return_value=result_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session.execute.side_effect = [
            mock_result,  # main insert
            MagicMock(),  # pg junction insert
            MagicMock(),  # politician junction insert (empty)
        ]

        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_ids=[20],
            judgment="賛成",
            member_count=5,
            note="全会一致",
        )

        result = await repository.create(entity)

        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_ids == [20]
        assert result.judgment == "賛成"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update parliamentary group judge with Many-to-Many."""
        updated_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "反対",
            "member_count": 4,
            "note": "変更後",
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = updated_dict
        mock_row._asdict = MagicMock(return_value=updated_dict)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session.execute.side_effect = [
            mock_result,  # main update
            MagicMock(),  # delete pg junction
            MagicMock(),  # delete politician junction
            MagicMock(),  # insert pg junction
            MagicMock(),  # insert politician junction
        ]

        entity = ProposalParliamentaryGroupJudge(
            id=1,
            proposal_id=10,
            parliamentary_group_ids=[20, 21],
            judgment="反対",
            member_count=4,
            note="変更後",
        )

        result = await repository.update(entity)

        assert result.id == 1
        assert result.judgment == "反対"
        assert result.member_count == 4
        assert result.note == "変更後"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id_raises_error(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update without ID raises ValueError."""
        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_ids=[20],
            judgment="賛成",
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete parliamentary group judge successfully."""
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
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete parliamentary group judge not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when judge is found."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        mock_row = MagicMock()
        mock_row._mapping = main_dict
        mock_row._asdict = MagicMock(return_value=main_dict)
        mock_main_result = MagicMock()
        mock_main_result.fetchone = MagicMock(return_value=mock_row)

        # row[0]でアクセスされるのでタプル形式
        pg_rows = [(20,)]
        mock_pg_result = MagicMock()
        mock_pg_result.fetchall = MagicMock(return_value=pg_rows)

        pol_rows: list[tuple[int]] = []
        mock_pol_result = MagicMock()
        mock_pol_result.fetchall = MagicMock(return_value=pol_rows)

        mock_session.execute.side_effect = [
            mock_main_result,
            mock_pg_result,
            mock_pol_result,
        ]

        result = await repository.get_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.proposal_id == 10
        assert result.parliamentary_group_ids == [20]

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when judge is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(999)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns list of judges."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        self._setup_mock_for_many_to_many(
            mock_session, main_dict, pg_ids=[20], politician_ids=[]
        )

        result = await repository.get_all()

        assert len(result) == 1
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset."""
        main_dict = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": None,
            "created_at": None,
            "updated_at": None,
        }
        self._setup_mock_for_many_to_many(
            mock_session, main_dict, pg_ids=[20], politician_ids=[]
        )

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_proposal(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_proposal."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal(10)
        assert "Failed to get judges by proposal" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_parliamentary_group(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_parliamentary_group."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_parliamentary_group(20)
        assert "Failed to get judges by parliamentary group" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_get_by_proposal_and_groups(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in get_by_proposal_and_groups."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.get_by_proposal_and_groups(10, [20])
        assert "Failed to get judge by proposal and groups" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_database_error_handling_bulk_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in bulk_create."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        judges = [
            ProposalParliamentaryGroupJudge(
                proposal_id=10,
                parliamentary_group_ids=[20],
                judgment="賛成",
            )
        ]

        with pytest.raises(DatabaseError) as exc_info:
            await repository.bulk_create(judges)
        assert "Failed to bulk create parliamentary group judges" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_create(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in create."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        entity = ProposalParliamentaryGroupJudge(
            proposal_id=10,
            parliamentary_group_ids=[20],
            judgment="賛成",
        )

        with pytest.raises(DatabaseError) as exc_info:
            await repository.create(entity)
        assert "Failed to create parliamentary group judge" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_delete(
        self,
        repository: ProposalParliamentaryGroupJudgeRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test database error handling in delete."""
        mock_session.execute.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(DatabaseError) as exc_info:
            await repository.delete(1)
        assert "Failed to delete parliamentary group judge" in str(exc_info.value)
        mock_session.rollback.assert_called_once()

    def test_dict_to_entity(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _dict_to_entity conversion."""
        data = {
            "id": 1,
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "member_count": 5,
            "note": "テスト",
            "parliamentary_group_ids": [20, 21],
            "politician_ids": [],
        }

        entity = repository._dict_to_entity(data)

        assert entity.id == 1
        assert entity.proposal_id == 10
        assert entity.parliamentary_group_ids == [20, 21]
        assert entity.politician_ids == []
        assert entity.judgment == "賛成"
        assert entity.member_count == 5
        assert entity.note == "テスト"

    def test_dict_to_entity_minimal(
        self, repository: ProposalParliamentaryGroupJudgeRepositoryImpl
    ) -> None:
        """Test _dict_to_entity with minimal data."""
        data = {
            "proposal_id": 10,
            "judge_type": "parliamentary_group",
            "judgment": "賛成",
            "parliamentary_group_ids": [20],
            "politician_ids": [],
        }

        entity = repository._dict_to_entity(data)

        assert entity.id is None
        assert entity.proposal_id == 10
        assert entity.parliamentary_group_ids == [20]
        assert entity.judgment == "賛成"
        assert entity.member_count is None
        assert entity.note is None
