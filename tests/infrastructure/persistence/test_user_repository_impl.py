"""Tests for UserRepositoryImpl."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.infrastructure.persistence.user_repository_impl import UserRepositoryImpl


class TestUserRepositoryImpl:
    """Test cases for UserRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> UserRepositoryImpl:
        """Create user repository."""
        return UserRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_user_id(self) -> UUID:
        """Sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_user_dict(self, sample_user_id: UUID) -> dict[str, Any]:
        """Sample user data as dict."""
        return {
            "user_id": sample_user_id,
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/picture.jpg",
            "created_at": datetime(2024, 1, 1, 0, 0, 0),
            "last_login_at": datetime(2024, 1, 15, 12, 0, 0),
        }

    @pytest.fixture
    def sample_user_entity(self, sample_user_id: UUID) -> User:
        """Sample user entity."""
        return User(
            user_id=sample_user_id,
            email="test@example.com",
            name="Test User",
            picture="https://example.com/picture.jpg",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            last_login_at=datetime(2024, 1, 15, 12, 0, 0),
        )

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when user is found."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(sample_user_id)

        # Assert
        assert result is not None
        assert result.user_id == sample_user_id
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when user is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test get_by_email when user is found."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_email("test@example.com")

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test create user."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        user = User(email="test@example.com", name="Test User")
        result = await repository.create(user)

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test update_last_login."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        last_login = datetime.now()
        result = await repository.update_last_login(sample_user_id, last_login)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count users."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=5)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.count()

        # Assert
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_or_create_by_email_existing_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test find_or_create_by_email with existing user."""
        # Setup mock result for get_by_email
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_result.rowcount = 1

        # Mock session to return user on first call (get_by_email)
        # and success on second call (update_last_login)
        mock_session.execute.side_effect = [mock_result, mock_result]

        # Execute
        result = await repository.find_or_create_by_email("test@example.com")

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        # Should call execute twice: get_by_email and update_last_login
        assert mock_session.execute.call_count >= 2
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_find_or_create_by_email_new_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test find_or_create_by_email creates new user when not found."""
        # Setup mock for get_by_email returning None (user not found)
        mock_result_not_found = MagicMock()
        mock_result_not_found.fetchone = MagicMock(return_value=None)

        # Setup mock for create returning new user
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result_create = MagicMock()
        mock_result_create.fetchone = MagicMock(return_value=mock_row)

        mock_session.execute.side_effect = [mock_result_not_found, mock_result_create]

        # Execute
        result = await repository.find_or_create_by_email(
            "test@example.com", name="Test User", picture="https://example.com/pic.jpg"
        )

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        # Should call execute twice: get_by_email and create
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_or_create_by_email_updates_name(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test find_or_create_by_email updates name when different."""
        # Setup mock for get_by_email with old name
        mock_row = MagicMock()
        user_dict_old_name = sample_user_dict.copy()
        user_dict_old_name["name"] = "Old Name"
        for key, value in user_dict_old_name.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_result.rowcount = 1

        # Setup mock for update with new name
        mock_row_updated = MagicMock()
        user_dict_new_name = sample_user_dict.copy()
        user_dict_new_name["name"] = "New Name"
        for key, value in user_dict_new_name.items():
            setattr(mock_row_updated, key, value)
        mock_result_update = MagicMock()
        mock_result_update.fetchone = MagicMock(return_value=mock_row_updated)

        mock_session.execute.side_effect = [
            mock_result,  # get_by_email
            mock_result,  # update_last_login
            mock_result_update,  # update (name change)
        ]

        # Execute
        result = await repository.find_or_create_by_email(
            "test@example.com", name="New Name"
        )

        # Assert
        assert result is not None
        assert result.name == "New Name"
        # Should call execute three times: get_by_email, update_last_login, update
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_find_or_create_by_email_updates_picture(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test find_or_create_by_email updates picture when different."""
        # Setup mock for get_by_email with old picture
        mock_row = MagicMock()
        user_dict_old_pic = sample_user_dict.copy()
        user_dict_old_pic["picture"] = "https://example.com/old.jpg"
        for key, value in user_dict_old_pic.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_result.rowcount = 1

        # Setup mock for update with new picture
        mock_row_updated = MagicMock()
        user_dict_new_pic = sample_user_dict.copy()
        user_dict_new_pic["picture"] = "https://example.com/new.jpg"
        for key, value in user_dict_new_pic.items():
            setattr(mock_row_updated, key, value)
        mock_result_update = MagicMock()
        mock_result_update.fetchone = MagicMock(return_value=mock_row_updated)

        mock_session.execute.side_effect = [
            mock_result,  # get_by_email
            mock_result,  # update_last_login
            mock_result_update,  # update (picture change)
        ]

        # Execute
        result = await repository.find_or_create_by_email(
            "test@example.com", picture="https://example.com/new.jpg"
        )

        # Assert
        assert result is not None
        assert result.picture == "https://example.com/new.jpg"
        # Should call execute three times: get_by_email, update_last_login, update
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test create user with duplicate email raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        # Setup mock to raise IntegrityError
        mock_session.execute.side_effect = SQLIntegrityError(
            "duplicate key", {}, Exception()
        )

        # Execute and Assert
        user = User(email="test@example.com", name="Test User")
        with pytest.raises(SQLIntegrityError):
            await repository.create(user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_without_id(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update user without user_id raises ValueError."""
        # Create user without user_id
        user = User(email="test@example.com", name="Test User")

        # Execute and Assert
        with pytest.raises(ValueError, match="User ID is required for update"):
            await repository.update(user)

    @pytest.mark.asyncio
    async def test_update_nonexistent_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test update user that doesn't exist raises RuntimeError."""
        # Setup mock to return no rows (user not found)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Create user with ID that doesn't exist
        user = User(user_id=sample_user_id, email="test@example.com", name="Test User")

        # Execute and Assert
        with pytest.raises(RuntimeError, match="User not found"):
            await repository.update(user)

    @pytest.mark.asyncio
    async def test_update_user_duplicate_email(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test update user with duplicate email raises IntegrityError."""
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        # Setup mock to raise IntegrityError
        mock_session.execute.side_effect = SQLIntegrityError(
            "duplicate key", {}, Exception()
        )

        # Create user with ID
        user = User(user_id=sample_user_id, email="test@example.com", name="Test User")

        # Execute and Assert
        with pytest.raises(SQLIntegrityError):
            await repository.update(user)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_with_integrity_error(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test delete user with IntegrityError (e.g., foreign key constraint)."""
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        # Setup mock to raise IntegrityError (foreign key constraint)
        mock_session.execute.side_effect = SQLIntegrityError(
            "foreign key constraint", {}, Exception()
        )

        # Execute and Assert
        with pytest.raises(SQLIntegrityError):
            await repository.delete(sample_user_id)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test delete user that doesn't exist returns False."""
        # Setup mock to return 0 rows affected
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.delete(sample_user_id)

        # Assert
        assert result is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login_user_not_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test update_last_login for non-existent user returns False."""
        # Setup mock to return 0 rows affected
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        # Execute
        last_login = datetime.now()
        result = await repository.update_last_login(sample_user_id, last_login)

        # Assert
        assert result is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_and_offset(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test get_all with limit and offset pagination."""
        # Setup mock result with multiple users
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            user_dict = sample_user_dict.copy()
            user_dict["user_id"] = uuid4()
            user_dict["email"] = f"user{i}@example.com"
            for key, value in user_dict.items():
                setattr(mock_row, key, value)
            mock_rows.append(mock_row)

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=mock_rows)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=5)

        # Assert
        assert len(result) == 3
        assert all(isinstance(user, User) for user in result)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty_result(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with no users returns empty list."""
        # Setup mock to return empty list
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all()

        # Assert
        assert result == []
        assert isinstance(result, list)
