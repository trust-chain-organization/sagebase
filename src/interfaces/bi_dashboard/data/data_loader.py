"""Data loader for BI Dashboard POC.

This module handles data retrieval from PostgreSQL database.
"""

import asyncio
import os
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from src.infrastructure.di.container import get_container, init_container


def get_database_url() -> str:
    """Get database URL from environment variable.

    Returns:
        str: Database connection URL
    """
    return os.getenv(
        "DATABASE_URL", "postgresql://sagebase:sagebase@localhost:5432/sagebase"
    )


def load_governing_bodies_coverage() -> pd.DataFrame:
    """Load governing bodies data with coverage information.

    Returns:
        pd.DataFrame: DataFrame with columns:
            - id: Governing body ID
            - name: Governing body name
            - organization_type: Type (国/都道府県/市町村)
            - prefecture: Prefecture name (extracted from name)
            - has_data: Whether we have data for this body
    """
    engine = create_engine(get_database_url())

    query = text("""
        SELECT
            gb.id,
            gb.name,
            gb.organization_type,
            CASE
                WHEN gb.name ~ '^(北海道|.*[都道府県])' THEN
                    SUBSTRING(gb.name FROM '^(北海道|.*?[都道府県])')
                ELSE
                    '不明'
            END as prefecture,
            CASE
                WHEN COUNT(m.id) > 0 THEN true
                ELSE false
            END as has_data
        FROM governing_bodies gb
        LEFT JOIN conferences c ON gb.id = c.governing_body_id
        LEFT JOIN meetings m ON c.id = m.conference_id
        GROUP BY gb.id, gb.name, gb.organization_type
        ORDER BY gb.organization_type, prefecture, gb.name
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)

    return df


def get_coverage_stats() -> dict[str, Any]:
    """Get coverage statistics.

    Returns:
        dict: Statistics including:
            - total: Total number of governing bodies
            - covered: Number with data
            - coverage_rate: Percentage covered
            - by_type: Coverage by organization type
    """
    df = load_governing_bodies_coverage()

    total = len(df)
    covered = df["has_data"].sum()
    coverage_rate = (covered / total * 100) if total > 0 else 0

    by_type = (
        df.groupby("organization_type")
        .agg({"id": "count", "has_data": "sum"})
        .rename(columns={"id": "total", "has_data": "covered"})
    )
    by_type["coverage_rate"] = by_type["covered"] / by_type["total"] * 100

    return {
        "total": total,
        "covered": int(covered),
        "coverage_rate": round(coverage_rate, 2),
        "by_type": by_type.to_dict("index"),
    }


def get_prefecture_coverage() -> pd.DataFrame:
    """Get coverage by prefecture.

    Returns:
        pd.DataFrame: Coverage statistics by prefecture
    """
    df = load_governing_bodies_coverage()

    # Filter only municipalities (市町村)
    municipalities = df[df["organization_type"] == "市町村"]

    coverage = (
        municipalities.groupby("prefecture")
        .agg({"id": "count", "has_data": "sum"})
        .rename(columns={"id": "total", "has_data": "covered"})
    )

    coverage["coverage_rate"] = coverage["covered"] / coverage["total"] * 100
    coverage = coverage.sort_values("coverage_rate", ascending=False)

    return coverage.reset_index()


# UseCase経由のデータ取得機能


def get_meeting_coverage_data() -> dict[str, Any]:
    """会議カバレッジデータを取得する.

    Returns:
        dict: 会議カバレッジ統計データ
            - total_meetings: 総会議数
            - with_minutes: 議事録がある会議数
            - with_conversations: 発言がある会議数
            - average_conversations_per_meeting: 会議あたりの平均発言数
            - meetings_by_conference: 会議体別の会議数
    """

    async def _get_data() -> dict[str, Any]:
        # DIコンテナを初期化（まだ初期化されていない場合）
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        # UseCaseをDIコンテナから取得
        usecase = container.use_cases.view_meeting_coverage_usecase()

        try:
            result = await usecase.execute()
            return dict(result)
        finally:
            # セッションのクリーンアップ
            await container.database.async_session().close()

    return asyncio.run(_get_data())


def get_speaker_matching_data() -> dict[str, Any]:
    """Speaker紐付け統計データを取得する.

    Returns:
        dict: Speaker紐付け統計データ
            - total_speakers: 総Speaker数
            - matched_speakers: 紐付け済みSpeaker数
            - unmatched_speakers: 未紐付けSpeaker数
            - matching_rate: 紐付け率(%)
            - total_conversations: 総発言数
            - linked_conversations: 紐付け済み発言数
            - linkage_rate: 発言紐付け率(%)
    """

    async def _get_data() -> dict[str, Any]:
        # DIコンテナを初期化（まだ初期化されていない場合）
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        # UseCaseをDIコンテナから取得
        usecase = container.use_cases.view_speaker_matching_stats_usecase()

        try:
            result = await usecase.execute()
            return dict(result)
        finally:
            # セッションのクリーンアップ
            await container.database.async_session().close()

    return asyncio.run(_get_data())


def get_activity_trend_data(period: str = "30d") -> list[dict[str, Any]]:
    """活動推移データを取得する.

    Args:
        period: 期間指定（例: "7d", "30d", "90d"）

    Returns:
        list[dict]: 日別の活動データ
            - date: 日付
            - meetings_count: 会議数
            - conversations_count: 発言数
            - speakers_count: Speaker数
            - politicians_count: 政治家数
    """

    async def _get_data() -> list[dict[str, Any]]:
        # DIコンテナを初期化（まだ初期化されていない場合）
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        # UseCaseをDIコンテナから取得
        usecase = container.use_cases.view_activity_trend_usecase()

        try:
            result = await usecase.execute({"period": period})
            return [dict(item) for item in result]
        finally:
            # セッションのクリーンアップ
            await container.database.async_session().close()

    return asyncio.run(_get_data())


def get_governing_body_coverage_data() -> dict[str, Any]:
    """自治体カバレッジデータを取得する.

    Returns:
        dict: 自治体カバレッジ統計データ
            - total: 総自治体数
            - with_conferences: 会議体がある自治体数
            - with_meetings: 会議がある自治体数
            - coverage_percentage: カバレッジ率(%)
    """

    async def _get_data() -> dict[str, Any]:
        # DIコンテナを初期化（まだ初期化されていない場合）
        try:
            container = get_container()
        except RuntimeError:
            container = init_container()

        # UseCaseをDIコンテナから取得
        usecase = container.use_cases.view_governing_body_coverage_usecase()

        try:
            result = await usecase.execute()
            return dict(result)
        finally:
            # セッションのクリーンアップ
            await container.database.async_session().close()

    return asyncio.run(_get_data())
