"""Application query services."""

from src.application.queries.politician_statistics_query import (
    PartyStatistics,
    PoliticianStatisticsQuery,
)


__all__ = ["PoliticianStatisticsQuery", "PartyStatistics"]
