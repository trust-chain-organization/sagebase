"""User repository implementation."""

import logging

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.repositories.session_adapter import ISessionAdapter
from src.domain.repositories.user_repository import IUserRepository

logger = logging.getLogger(__name__)


class UserRepositoryImpl(IUserRepository):
    """Implementation of user repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository.

        Args:
            session: AsyncSession or ISessionAdapter for database operations
        """
        self.session = session

    def _row_to_entity(self, row: Any) -> User:
        """Convert database row to User entity.

        Args:
            row: Database row

        Returns:
            User entity
        """
        return User(
            user_id=row.user_id,
            email=row.email,
            name=row.name,
            picture=row.picture,
            created_at=row.created_at,
            last_login_at=row.last_login_at,
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        query = text("""
            SELECT user_id, email, name, picture, created_at, last_login_at
            FROM users
            WHERE user_id = :user_id
        """)
        result = await self.session.execute(query, {"user_id": user_id})
        row = result.fetchone()
        return self._row_to_entity(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        query = text("""
            SELECT user_id, email, name, picture, created_at, last_login_at
            FROM users
            WHERE email = :email
        """)
        result = await self.session.execute(query, {"email": email})
        row = result.fetchone()
        return self._row_to_entity(row) if row else None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[User]:
        """Get all users with optional pagination."""
        query_str = """
            SELECT user_id, email, name, picture, created_at, last_login_at
            FROM users
            ORDER BY created_at DESC
        """
        params: dict[str, Any] = {}

        if limit is not None:
            query_str += " LIMIT :limit"
            params["limit"] = limit

        if offset is not None:
            query_str += " OFFSET :offset"
            params["offset"] = offset

        query = text(query_str)
        result = await self.session.execute(query, params)
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def create(self, user: User) -> User:
        """Create a new user."""
        try:
            query = text("""
                INSERT INTO users (email, name, picture, created_at, last_login_at)
                VALUES (:email, :name, :picture, :created_at, :last_login_at)
                RETURNING user_id, email, name, picture, created_at, last_login_at
            """)
            now = datetime.now()
            params = {
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "created_at": user.created_at or now,
                "last_login_at": user.last_login_at or now,
            }
            result = await self.session.execute(query, params)
            await self.session.commit()
            row = result.fetchone()
            if not row:
                raise RuntimeError("Failed to create user")
            return self._row_to_entity(row)
        except SQLIntegrityError as e:
            await self.session.rollback()
            logger.error(f"Failed to create user: {e}")
            raise

    async def update(self, user: User) -> User:
        """Update an existing user."""
        if user.user_id is None:
            raise ValueError("User ID is required for update")

        try:
            query = text("""
                UPDATE users
                SET email = :email,
                    name = :name,
                    picture = :picture,
                    last_login_at = :last_login_at
                WHERE user_id = :user_id
                RETURNING user_id, email, name, picture, created_at, last_login_at
            """)
            params = {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "last_login_at": user.last_login_at or datetime.now(),
            }
            result = await self.session.execute(query, params)
            await self.session.commit()
            row = result.fetchone()
            if not row:
                raise RuntimeError(f"User not found: {user.user_id}")
            return self._row_to_entity(row)
        except SQLIntegrityError as e:
            await self.session.rollback()
            logger.error(f"Failed to update user: {e}")
            raise

    async def update_last_login(self, user_id: UUID, last_login_at: datetime) -> bool:
        """Update user's last login timestamp."""
        try:
            query = text("""
                UPDATE users
                SET last_login_at = :last_login_at
                WHERE user_id = :user_id
            """)
            result = await self.session.execute(
                query, {"user_id": user_id, "last_login_at": last_login_at}
            )
            await self.session.commit()
            return result.rowcount > 0
        except SQLIntegrityError as e:
            await self.session.rollback()
            logger.error(f"Failed to update last login: {e}")
            raise

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID."""
        try:
            query = text("""
                DELETE FROM users
                WHERE user_id = :user_id
            """)
            result = await self.session.execute(query, {"user_id": user_id})
            await self.session.commit()
            return result.rowcount > 0
        except SQLIntegrityError as e:
            await self.session.rollback()
            logger.error(f"Failed to delete user: {e}")
            raise

    async def count(self) -> int:
        """Count total number of users."""
        query = text("SELECT COUNT(*) FROM users")
        result = await self.session.execute(query)
        row = result.fetchone()
        return row[0] if row else 0

    async def find_or_create_by_email(
        self, email: str, name: str | None = None, picture: str | None = None
    ) -> User:
        """Find user by email or create if not exists."""
        # Try to find existing user
        existing_user = await self.get_by_email(email)

        if existing_user:
            # Update last login time
            await self.update_last_login(existing_user.user_id, datetime.now())  # type: ignore
            existing_user.last_login_at = datetime.now()
            # Update name and picture if provided
            if name and existing_user.name != name:
                existing_user.name = name
                await self.update(existing_user)
            if picture and existing_user.picture != picture:
                existing_user.picture = picture
                await self.update(existing_user)
            return existing_user

        # Create new user
        new_user = User(email=email, name=name, picture=picture)
        return await self.create(new_user)
