"""ユーザー認証ユースケースのテスト。"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from src.application.usecases.authenticate_user_usecase import AuthenticateUserUseCase
from src.domain.entities.user import User
from src.domain.repositories.user_repository import IUserRepository


class MockUserRepository(IUserRepository):
    """テスト用のモックUserRepository。"""

    def __init__(self):
        """Initialize mock repository."""
        self.users: dict[str, User] = {}
        self.find_or_create_called = False

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        return self.users.get(email)

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[User]:
        """Get all users."""
        return list(self.users.values())

    async def create(self, user: User) -> User:
        """Create user."""
        user.user_id = uuid4()
        user.created_at = datetime.now()
        user.last_login_at = datetime.now()
        self.users[user.email] = user
        return user

    async def update(self, user: User) -> User:
        """Update user."""
        self.users[user.email] = user
        return user

    async def update_last_login(self, user_id: UUID, last_login_at: datetime) -> bool:
        """Update last login."""
        for user in self.users.values():
            if user.user_id == user_id:
                user.last_login_at = last_login_at
                return True
        return False

    async def delete(self, user_id: UUID) -> bool:
        """Delete user."""
        for email, user in list(self.users.items()):
            if user.user_id == user_id:
                del self.users[email]
                return True
        return False

    async def count(self) -> int:
        """Count users."""
        return len(self.users)

    async def find_or_create_by_email(
        self, email: str, name: str | None = None, picture: str | None = None
    ) -> User:
        """Find or create user by email."""
        self.find_or_create_called = True
        existing_user = await self.get_by_email(email)

        if existing_user:
            # Update last login
            existing_user.last_login_at = datetime.now()
            if name:
                existing_user.name = name
            if picture:
                existing_user.picture = picture
            return existing_user

        # Create new user
        new_user = User(email=email, name=name, picture=picture)
        return await self.create(new_user)


@pytest.mark.asyncio
async def test_authenticate_user_with_new_user():
    """新規ユーザーの認証をテストします。"""
    # Arrange
    mock_repo = MockUserRepository()
    usecase = AuthenticateUserUseCase(mock_repo)

    # Act
    user = await usecase.execute(
        email="test@example.com",
        name="Test User",
        picture="https://example.com/picture.jpg",
    )

    # Assert
    assert user is not None
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.picture == "https://example.com/picture.jpg"
    assert user.user_id is not None
    assert user.created_at is not None
    assert user.last_login_at is not None
    assert mock_repo.find_or_create_called


@pytest.mark.asyncio
async def test_authenticate_user_with_existing_user():
    """既存ユーザーの認証をテストします。"""
    # Arrange
    mock_repo = MockUserRepository()
    usecase = AuthenticateUserUseCase(mock_repo)

    # 既存ユーザーを作成
    existing_user = await usecase.execute(
        email="existing@example.com",
        name="Existing User",
        picture="https://example.com/old_picture.jpg",
    )
    first_login_time = existing_user.last_login_at

    # Act - 同じメールアドレスで再度認証
    user = await usecase.execute(
        email="existing@example.com",
        name="Updated User",
        picture="https://example.com/new_picture.jpg",
    )

    # Assert
    assert user is not None
    assert user.email == "existing@example.com"
    assert user.user_id == existing_user.user_id
    assert user.name == "Updated User"  # 名前が更新される
    assert user.picture == "https://example.com/new_picture.jpg"  # 画像が更新される
    assert user.last_login_at != first_login_time  # last_login_atが更新される


@pytest.mark.asyncio
async def test_authenticate_user_with_invalid_email():
    """無効なメールアドレスでの認証をテストします。"""
    # Arrange
    mock_repo = MockUserRepository()
    usecase = AuthenticateUserUseCase(mock_repo)

    # Act & Assert - 空のメールアドレス
    with pytest.raises(ValueError, match="メールアドレスは必須です"):
        await usecase.execute(email="", name="Test User")

    # Act & Assert - None
    with pytest.raises(ValueError, match="メールアドレスは必須です"):
        await usecase.execute(email=None, name="Test User")  # type: ignore


@pytest.mark.asyncio
async def test_authenticate_user_without_optional_fields():
    """オプションフィールドなしでの認証をテストします。"""
    # Arrange
    mock_repo = MockUserRepository()
    usecase = AuthenticateUserUseCase(mock_repo)

    # Act
    user = await usecase.execute(email="minimal@example.com")

    # Assert
    assert user is not None
    assert user.email == "minimal@example.com"
    assert user.name is None or user.name == "minimal@example.com"
    assert user.picture is None or user.picture == ""
    assert user.user_id is not None
