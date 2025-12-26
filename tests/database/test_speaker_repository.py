"""Tests for SpeakerRepository with politician linking features."""

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl as SpeakerRepository,
)


@pytest.fixture
def test_session() -> Iterator[Session]:
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")

    # Create tables
    with engine.begin() as conn:
        # Enable foreign key support in SQLite
        conn.execute(text("PRAGMA foreign_keys = OFF"))

        # Create political_parties table
        conn.execute(
            text(
                """
                CREATE TABLE political_parties (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR NOT NULL
                )
                """
            )
        )

        # Create speakers table (without politician_id FK constraint initially)
        conn.execute(
            text(
                """
                CREATE TABLE speakers (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    type VARCHAR,
                    political_party_name VARCHAR,
                    position VARCHAR,
                    is_politician BOOLEAN DEFAULT FALSE,
                    politician_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )

        # Create politicians table
        conn.execute(
            text(
                """
                CREATE TABLE politicians (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    political_party_id INTEGER REFERENCES political_parties(id),
                    speaker_id INTEGER UNIQUE NOT NULL REFERENCES speakers(id)
                )
                """
            )
        )

        # Create conversations table
        conn.execute(
            text(
                """
                CREATE TABLE conversations (
                    id INTEGER PRIMARY KEY,
                    speaker_id INTEGER REFERENCES speakers(id),
                    speaker_name VARCHAR,
                    comment TEXT NOT NULL
                )
                """
            )
        )

        # Re-enable foreign keys
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()

    # Create session
    session_local = sessionmaker(bind=engine)
    session = session_local()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def speaker_repo(test_session: Session) -> SpeakerRepository:
    """Create a SpeakerRepository instance."""
    async_session = AsyncSessionAdapter(test_session)
    return SpeakerRepository(session=async_session)


def setup_test_data(session: Session):
    """Set up test data for speakers and politicians."""
    # Insert political parties
    session.execute(
        text(
            "INSERT INTO political_parties (id, name) "
            "VALUES (1, '自由民主党'), (2, '立憲民主党')"
        )
    )

    # Insert speakers
    session.execute(
        text(
            """
            INSERT INTO speakers
                (id, name, type, political_party_name, position, is_politician)
            VALUES
                (1, '山田太郎', '議員', '自由民主党', '委員長', TRUE),
                (2, '鈴木花子', '議員', '立憲民主党', NULL, TRUE),
                (3, '田中一郎', '参考人', NULL, '大学教授', FALSE),
                (4, '佐藤次郎', '議員', '自由民主党', NULL, TRUE)
            """
        )
    )

    # Insert politicians (link only some speakers)
    session.execute(
        text(
            """
            INSERT INTO politicians (id, name, political_party_id, speaker_id)
            VALUES
                (1, '山田太郎', 1, 1),
                (2, '鈴木花子', 2, 2)
            """
        )
    )

    # Update speakers to link back to politicians
    session.execute(text("UPDATE speakers SET politician_id = 1 WHERE id = 1"))
    session.execute(text("UPDATE speakers SET politician_id = 2 WHERE id = 2"))

    # Insert conversations
    session.execute(
        text(
            """
            INSERT INTO conversations (id, speaker_id, speaker_name, comment)
            VALUES
                (1, 1, '山田太郎', '本日の議題について'),
                (2, 1, '山田太郎', '賛成です'),
                (3, 2, '鈴木花子', '反対意見を述べます'),
                (4, 3, '田中一郎', '専門的見地から')
            """
        )
    )

    session.commit()


@pytest.mark.asyncio
async def test_get_speakers_with_politician_info(
    speaker_repo: SpeakerRepository, test_session: Session
) -> None:
    """Test getting speakers with linked politician information."""
    setup_test_data(test_session)

    results = await speaker_repo.get_speakers_with_politician_info()

    assert len(results) == 4

    # Check linked politician (山田太郎)
    yamada = next(r for r in results if r["name"] == "山田太郎")
    assert yamada["is_politician"] == 1  # SQLite returns 1 for True
    assert yamada["politician_id"] == 1
    assert yamada["politician_name"] == "山田太郎"
    assert yamada["party_name_from_politician"] == "自由民主党"
    assert yamada["conversation_count"] == 2

    # Check linked politician (鈴木花子)
    suzuki = next(r for r in results if r["name"] == "鈴木花子")
    assert suzuki["is_politician"] == 1  # SQLite returns 1 for True
    assert suzuki["politician_id"] == 2
    assert suzuki["politician_name"] == "鈴木花子"
    assert suzuki["party_name_from_politician"] == "立憲民主党"
    assert suzuki["conversation_count"] == 1

    # Check unlinked politician (佐藤次郎)
    sato = next(r for r in results if r["name"] == "佐藤次郎")
    assert sato["is_politician"] == 1  # SQLite returns 1 for True
    assert sato["politician_id"] is None
    assert sato["politician_name"] is None
    assert sato["party_name_from_politician"] is None
    assert sato["conversation_count"] == 0

    # Check non-politician (田中一郎)
    tanaka = next(r for r in results if r["name"] == "田中一郎")
    assert tanaka["is_politician"] == 0  # SQLite returns 0 for False
    assert tanaka["politician_id"] is None
    assert tanaka["politician_name"] is None
    assert tanaka["conversation_count"] == 1


@pytest.mark.asyncio
async def test_get_speaker_politician_stats(
    speaker_repo: SpeakerRepository, test_session: Session
) -> None:
    """Test getting speaker-politician linking statistics."""
    setup_test_data(test_session)

    stats = await speaker_repo.get_speaker_politician_stats()

    assert stats["total_speakers"] == 4
    assert stats["politician_speakers"] == 3  # 山田、鈴木、佐藤
    assert stats["non_politician_speakers"] == 1  # 田中
    assert stats["linked_speakers"] == 2  # 山田、鈴木
    assert stats["linked_politician_speakers"] == 2  # 山田、鈴木 (linked)
    # Verify: politician_speakers(3) - linked_politician_speakers(2)
    # = unlinked count of 1 (佐藤)
    assert stats["link_rate"] == pytest.approx(66.7, rel=0.1)  # 2/3 = 66.7%


@pytest.mark.asyncio
async def test_get_speaker_politician_stats_empty(
    speaker_repo: SpeakerRepository, test_session: Session
) -> None:
    """Test statistics with no data."""
    stats = await speaker_repo.get_speaker_politician_stats()

    assert stats["total_speakers"] == 0
    assert stats["politician_speakers"] == 0
    assert stats["non_politician_speakers"] == 0
    assert stats["linked_speakers"] == 0
    assert stats["linked_politician_speakers"] == 0
    assert stats["link_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_speaker_politician_stats_no_politicians(
    speaker_repo: SpeakerRepository, test_session: Session
) -> None:
    """Test statistics when all speakers are not politicians."""
    # Insert only non-politician speakers
    test_session.execute(
        text(
            """
            INSERT INTO speakers (id, name, type, is_politician)
            VALUES
                (1, '参考人A', '参考人', FALSE),
                (2, '参考人B', '参考人', FALSE)
            """
        )
    )
    test_session.commit()

    stats = await speaker_repo.get_speaker_politician_stats()

    assert stats["total_speakers"] == 2
    assert stats["politician_speakers"] == 0
    assert stats["non_politician_speakers"] == 2
    assert stats["linked_speakers"] == 0
    assert stats["linked_politician_speakers"] == 0
    assert stats["link_rate"] == 0.0
