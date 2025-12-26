"""Synchronous adapter for Politician repository.

This adapter wraps the async PoliticianRepositoryImpl and provides
synchronous methods for backward compatibility with sync code.
"""

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.application.dtos.politician_dto import CreatePoliticianDTO, UpdatePoliticianDTO
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


logger = logging.getLogger(__name__)


class PoliticianRepositorySyncImpl:
    """Synchronous adapter for PoliticianRepository.

    This class provides synchronous wrappers around the async repository methods.
    It's designed for backward compatibility with code that cannot easily be
    converted to async (e.g., Streamlit, CLI commands, synchronous services).
    """

    def __init__(self, session: Session | AsyncSession):
        """Initialize the sync adapter.

        Args:
            session: Database session (sync or async). If sync session is provided,
                    operations will use direct SQL execution. If async session is
                    provided, it will be wrapped for async operations.
        """
        self.sync_session: Session | None = None
        self.async_session: AsyncSession | None = None

        if isinstance(session, AsyncSession):
            # If async session provided, store it for async operations
            self.async_session = session
            self.async_repo = PoliticianRepositoryImpl(session)
        else:
            # Sync session - will use direct SQL
            self.sync_session = session

    def _run_async(self, coro: Any) -> Any:
        """Run async coroutine in sync context."""
        try:
            # Try to get existing event loop
            asyncio.get_running_loop()
            # We're already in an async context, this shouldn't be used
            raise RuntimeError(
                "Cannot use sync methods from within an async context. "
                "Use the async repository directly."
            )
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(coro)

    def search_by_name_sync(self, name_pattern: str) -> list[dict[str, Any]]:
        """Search politicians by name (synchronous).

        Returns list of dictionaries for backward compatibility.
        """
        if self.sync_session:
            query = """
                SELECT * FROM politicians
                WHERE name LIKE :pattern
                ORDER BY name
            """
            result = self.sync_session.execute(
                text(query), {"pattern": f"%{name_pattern}%"}
            )
            rows = result.fetchall()
            results = []
            for row in rows:
                if hasattr(row, "_mapping"):
                    results.append(dict(row._mapping))  # type: ignore[attr-defined]
                else:
                    results.append(dict(row))
            return results
        elif self.async_session:
            # Use async repo with asyncio.run
            coro = self.async_repo.search_by_name(name_pattern)
            politicians = self._run_async(coro)
            # Convert to dicts for backward compatibility
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "political_party_id": p.political_party_id,
                    "electoral_district": p.district,
                    "profile_url": p.profile_page_url,
                    "furigana": p.furigana,
                }
                for p in politicians
            ]
        return []

    def bulk_create_politicians_sync(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Any] | list[dict[str, Any]]]:
        """Bulk create or update politicians (synchronous).

        Returns dict with 'created', 'updated', and 'errors' keys.
        """
        if self.sync_session:
            from sqlalchemy.exc import IntegrityError as SQLIntegrityError

            created = []
            updated = []
            errors = []

            for data in politicians_data:
                try:
                    # Check if politician exists
                    existing = self.find_by_name_and_party(
                        data.get("name", ""), data.get("political_party_id")
                    )

                    if existing:
                        # Update existing politician if needed
                        update_fields = []
                        update_values = {"id": existing["id"]}
                        for field in [
                            "prefecture",
                            "electoral_district",
                            "profile_url",
                            "party_position",
                        ]:
                            if field in data and data[field] != existing.get(field):
                                update_fields.append(f"{field} = :{field}")
                                update_values[field] = data[field]

                        if update_fields:
                            query = (
                                f"UPDATE politicians SET {', '.join(update_fields)} "
                                f"WHERE id = :id RETURNING *"
                            )
                            result = self.sync_session.execute(
                                text(query), update_values
                            )
                            row = result.first()
                            if row:
                                if hasattr(row, "_mapping"):
                                    updated.append(dict(row._mapping))  # type: ignore[attr-defined]
                                else:
                                    updated.append(dict(row))
                    else:
                        # Create new politician
                        columns = ", ".join(data.keys())
                        values = ", ".join([f":{key}" for key in data.keys()])
                        query = (
                            f"INSERT INTO politicians ({columns}) "
                            f"VALUES ({values}) RETURNING *"
                        )
                        result = self.sync_session.execute(text(query), data)
                        row = result.first()
                        if row:
                            if hasattr(row, "_mapping"):
                                created.append(dict(row._mapping))  # type: ignore[attr-defined]
                            else:
                                created.append(dict(row))

                except SQLIntegrityError as e:
                    errors.append(
                        {
                            "data": data,
                            "error": f"Duplicate or constraint violation: {str(e)}",
                        }
                    )
                except Exception as e:
                    errors.append({"data": data, "error": f"Error: {str(e)}"})

            self.sync_session.commit()
            return {"created": created, "updated": updated, "errors": errors}

        elif self.async_session:
            # Use async repo with asyncio.run
            coro = self.async_repo.bulk_create_politicians(politicians_data)
            result = self._run_async(coro)
            # Convert entities to dicts for backward compatibility
            return {
                "created": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "political_party_id": p.political_party_id,
                        "electoral_district": p.district,
                        "profile_url": p.profile_page_url,
                        "furigana": p.furigana,
                    }
                    for p in result["created"]
                ],
                "updated": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "political_party_id": p.political_party_id,
                        "electoral_district": p.district,
                        "profile_url": p.profile_page_url,
                        "furigana": p.furigana,
                    }
                    for p in result["updated"]
                ],
                "errors": result["errors"],
            }

        return {"created": [], "updated": [], "errors": []}

    def find_by_name_and_party(
        self, name: str, political_party_id: int | None = None
    ) -> dict[str, Any] | None:
        """Find politician by name and party (synchronous).

        Returns dict for backward compatibility.
        """
        if self.sync_session:
            query = "SELECT * FROM politicians WHERE name = :name"
            params: dict[str, Any] = {"name": name}
            if political_party_id is not None:
                query += " AND political_party_id = :party_id"
                params["party_id"] = political_party_id
            query += " LIMIT 1"
            result = self.sync_session.execute(text(query), params)
            row = result.first()
            if row:
                if hasattr(row, "_mapping"):
                    return dict(row._mapping)  # type: ignore[attr-defined]
                return dict(row)
            return None
        elif self.async_session:
            # Use async repo with asyncio.run
            coro = self.async_repo.get_by_name_and_party(name, political_party_id)
            politician = self._run_async(coro)
            if politician:
                return {
                    "id": politician.id,
                    "name": politician.name,
                    "political_party_id": politician.political_party_id,
                    "electoral_district": politician.district,
                    "profile_url": politician.profile_page_url,
                    "furigana": politician.furigana,
                }
            return None
        return None

    def fetch_as_dict_sync(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query and return results as dicts (synchronous)."""
        if self.sync_session:
            result = self.sync_session.execute(text(query), params or {})
            rows = result.fetchall()
            result_list = []
            for row in rows:
                try:
                    if hasattr(row, "_mapping"):
                        result_list.append(dict(row._mapping))  # type: ignore[attr-defined]
                    elif hasattr(row, "keys"):
                        result_list.append(dict(zip(row.keys(), row, strict=False)))
                    else:
                        result_list.append(dict(row))
                except Exception:
                    try:
                        result_list.append(dict(row))
                    except Exception:
                        if hasattr(row, "keys"):
                            result_list.append({k: row[k] for k in row.keys()})
                        else:
                            result_list.append({})
            return result_list
        elif self.async_session:
            # Use async repo with asyncio.run
            coro = self.async_repo.fetch_as_dict_async(query, params)
            return self._run_async(coro)
        return []

    # Alias for backward compatibility
    fetch_as_dict = fetch_as_dict_sync

    def find_by_name(self, name: str) -> list[dict[str, Any]]:
        """Find politicians by name (backward compatibility)."""
        return self.search_by_name_sync(name)

    def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query (backward compatibility)."""
        return self.fetch_as_dict_sync(query, params)

    def create_sync(
        self, politician_create: CreatePoliticianDTO
    ) -> dict[str, Any] | None:
        """Create politician (synchronous, backward compatibility)."""
        if self.sync_session:
            data = {k: v for k, v in asdict(politician_create).items() if v is not None}
            columns = ", ".join(data.keys())
            values = ", ".join([f":{key}" for key in data.keys()])
            query = f"INSERT INTO politicians ({columns}) VALUES ({values}) RETURNING *"
            result = self.sync_session.execute(text(query), data)
            self.sync_session.commit()
            row = result.first()
            if row:
                if hasattr(row, "_mapping"):
                    return dict(row._mapping)  # type: ignore[attr-defined]
                return dict(row)
            return None
        return None

    def update_v2(
        self, politician_id: int, update_data: UpdatePoliticianDTO
    ) -> dict[str, Any] | None:
        """Update politician (synchronous, backward compatibility)."""
        if self.sync_session:
            data_dict = asdict(update_data)
            # Remove id from update data
            data_dict.pop("id", None)
            # Only include non-None values
            data = {k: v for k, v in data_dict.items() if v is not None}
            if not data:
                return None
            set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
            query = f"UPDATE politicians SET {set_clause} WHERE id = :id RETURNING *"
            data["id"] = politician_id
            result = self.sync_session.execute(text(query), data)
            self.sync_session.commit()
            row = result.first()
            if row:
                if hasattr(row, "_mapping"):
                    return dict(row._mapping)  # type: ignore[attr-defined]
                return dict(row)
            return None
        return None

    def fetch_all_as_models(
        self,
        model_class: type[Any],
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Fetch all rows as models (synchronous)."""
        if self.sync_session:
            result = self.sync_session.execute(text(query), params or {})
            rows = result.fetchall()
            result_list = []
            for row in rows:
                if hasattr(row, "_mapping"):
                    result_list.append(model_class(**dict(row._mapping)))  # type: ignore[attr-defined]
                else:
                    result_list.append(model_class(**dict(row)))
            return result_list
        return []

    def close(self) -> None:
        """Close the session if needed.

        Note: Sessions are typically managed by the application,
        not the repository. This is here for backward compatibility.
        """
        pass
