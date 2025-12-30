"""Tests for speaker matching tools.

このモジュールは、speaker_matching_toolsの各ツールをテストします。
リポジトリはモックを使用してテストします。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.external.langgraph_tools.speaker_matching_tools import (
    _calculate_name_similarity,
    create_speaker_matching_tools,
)


@pytest.fixture
def mock_speaker_repo():
    """Create mock SpeakerRepository."""
    repo = AsyncMock()
    repo.get_all_for_matching = AsyncMock(
        return_value=[
            {"id": 1, "name": "田中太郎", "party": "○○党"},
            {"id": 2, "name": "佐藤花子", "party": "△△党"},
            {"id": 3, "name": "鈴木一郎", "party": "○○党"},
            {"id": 4, "name": "高橋次郎", "party": "□□党"},
        ]
    )
    repo.get_affiliated_speakers = AsyncMock(
        return_value=[
            {"speaker_id": 1, "speaker_name": "田中太郎"},
            {"speaker_id": 2, "speaker_name": "佐藤花子"},
        ]
    )
    return repo


@pytest.fixture
def mock_politician_repo():
    """Create mock PoliticianRepository."""
    repo = AsyncMock()
    repo.get_all_for_matching = AsyncMock(
        return_value=[
            {"id": 101, "name": "田中太郎", "party": "○○党"},
            {"id": 102, "name": "佐藤花子", "party": "△△党"},
            {"id": 103, "name": "鈴木一郎", "party": "○○党"},
            {"id": 104, "name": "高橋次郎", "party": "□□党"},
            {"id": 105, "name": "田中一郎", "party": "○○党"},
        ]
    )
    return repo


@pytest.fixture
def mock_affiliation_repo():
    """Create mock PoliticianAffiliationRepository."""
    repo = AsyncMock()

    # Mock affiliation object
    mock_aff = MagicMock()
    mock_aff.conference_id = 1
    mock_aff.conference = MagicMock()
    mock_aff.conference.name = "○○市議会"
    mock_aff.start_date = MagicMock()
    mock_aff.start_date.isoformat = MagicMock(return_value="2023-01-01")
    mock_aff.end_date = None

    repo.get_by_politician = AsyncMock(return_value=[mock_aff])
    return repo


@pytest.fixture
def tools(mock_speaker_repo, mock_politician_repo, mock_affiliation_repo):
    """Create speaker matching tools fixture."""
    return create_speaker_matching_tools(
        speaker_repo=mock_speaker_repo,
        politician_repo=mock_politician_repo,
        affiliation_repo=mock_affiliation_repo,
    )


class TestEvaluateMatchingCandidates:
    """Tests for evaluate_matching_candidates tool."""

    @pytest.mark.asyncio
    async def test_exact_match(self, tools):
        """Test exact name match."""
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "max_candidates": 10,
            }
        )

        assert "error" not in result
        assert result["total_candidates"] > 0
        assert len(result["candidates"]) > 0

        # First candidate should be exact match
        first_candidate = result["candidates"][0]
        assert first_candidate["politician_name"] == "田中太郎"
        assert first_candidate["match_type"] == "exact"
        assert first_candidate["score"] == 1.0

    @pytest.mark.asyncio
    async def test_partial_match(self, tools):
        """Test partial name match."""
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "田中",
                "max_candidates": 10,
            }
        )

        assert "error" not in result
        assert result["total_candidates"] > 0

        # Check that "田中太郎" and "田中一郎" are in candidates
        candidate_names = [c["politician_name"] for c in result["candidates"]]
        assert "田中太郎" in candidate_names or "田中一郎" in candidate_names

        # Check that partial matches have partial match type
        for candidate in result["candidates"]:
            if "田中" in candidate["politician_name"]:
                assert candidate["match_type"] in ("exact", "partial")

    @pytest.mark.asyncio
    async def test_max_candidates_limit(self, tools):
        """Test that max_candidates limits the number of results."""
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "田中",
                "max_candidates": 2,
            }
        )

        assert "error" not in result
        assert len(result["candidates"]) <= 2

    @pytest.mark.asyncio
    async def test_empty_speaker_name(self, tools):
        """Test with empty speaker name."""
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "",
                "max_candidates": 10,
            }
        )

        assert "error" in result
        assert result["error"] == "発言者名が空です"
        assert result["total_candidates"] == 0
        assert len(result["candidates"]) == 0

    @pytest.mark.asyncio
    async def test_with_meeting_date_and_conference_id(self, tools, mock_speaker_repo):
        """Test with meeting_date and conference_id."""
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "meeting_date": "2024-01-15",
                "conference_id": 1,
                "max_candidates": 10,
            }
        )

        assert "error" not in result
        # get_affiliated_speakers should have been called
        mock_speaker_repo.get_affiliated_speakers.assert_called_once_with(
            "2024-01-15", 1
        )

    @pytest.mark.asyncio
    async def test_no_politicians_available(self, tools, mock_politician_repo):
        """Test when no politicians are available."""
        mock_politician_repo.get_all_for_matching.return_value = []
        evaluate_tool = tools[0]

        result = await evaluate_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "max_candidates": 10,
            }
        )

        assert "error" in result
        assert result["error"] == "利用可能な政治家リストが空です"


class TestSearchAdditionalInfo:
    """Tests for search_additional_info tool."""

    @pytest.mark.asyncio
    async def test_search_politician_info(self, tools, mock_affiliation_repo):
        """Test searching politician information."""
        search_tool = tools[1]

        result = await search_tool.ainvoke(
            {
                "entity_type": "politician",
                "entity_id": 101,
                "info_types": ["affiliation", "party"],
            }
        )

        assert "error" not in result
        assert result["entity_type"] == "politician"
        assert result["entity_id"] == 101
        assert result["entity_name"] == "田中太郎"

        # Check affiliation info
        assert "affiliation" in result["info"]
        assert len(result["info"]["affiliation"]) > 0
        assert result["info"]["affiliation"][0]["conference_id"] == 1

        # Check party info
        assert "party" in result["info"]
        assert result["info"]["party"]["party_name"] == "○○党"

        # get_by_politician should have been called
        mock_affiliation_repo.get_by_politician.assert_called_once_with(101)

    @pytest.mark.asyncio
    async def test_search_speaker_info(self, tools, mock_affiliation_repo):
        """Test searching speaker information."""
        search_tool = tools[1]

        result = await search_tool.ainvoke(
            {
                "entity_type": "speaker",
                "entity_id": 1,
                "info_types": ["party"],
            }
        )

        assert "error" not in result
        assert result["entity_type"] == "speaker"
        assert result["entity_id"] == 1
        assert result["entity_name"] == "田中太郎"

        # Check party info
        assert "party" in result["info"]
        assert result["info"]["party"]["party_name"] == "○○党"

    @pytest.mark.asyncio
    async def test_invalid_entity_type(self, tools):
        """Test with invalid entity_type."""
        search_tool = tools[1]

        result = await search_tool.ainvoke(
            {
                "entity_type": "invalid_type",
                "entity_id": 101,
            }
        )

        assert "error" in result
        assert "無効なentity_type" in result["error"]

    @pytest.mark.asyncio
    async def test_politician_not_found(self, tools):
        """Test when politician is not found."""
        search_tool = tools[1]

        result = await search_tool.ainvoke(
            {
                "entity_type": "politician",
                "entity_id": 9999,  # Non-existent ID
            }
        )

        assert "error" in result
        assert "が見つかりません" in result["error"]

    @pytest.mark.asyncio
    async def test_default_info_types(self, tools):
        """Test with default info_types (all types)."""
        search_tool = tools[1]

        result = await search_tool.ainvoke(
            {
                "entity_type": "politician",
                "entity_id": 101,
                # info_types not specified, should default to all
            }
        )

        assert "error" not in result
        # All info types should be present
        assert "affiliation" in result["info"]
        assert "party" in result["info"]
        assert "history" in result["info"]


class TestJudgeConfidence:
    """Tests for judge_confidence tool."""

    @pytest.mark.asyncio
    async def test_high_confidence_exact_match(self, tools):
        """Test high confidence with exact match."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 101,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 1.0,
            "match_type": "exact",
            "is_affiliated": False,
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "candidate": candidate,
            }
        )

        assert "error" not in result
        assert result["confidence"] == 1.0
        assert result["confidence_level"] == "high"
        assert result["should_match"] is True
        assert "完全一致" in result["reason"]

    @pytest.mark.asyncio
    async def test_confidence_boost_with_affiliation(self, tools):
        """Test confidence boost when affiliated."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 101,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.75,
            "match_type": "partial",
            "is_affiliated": True,
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中",
                "candidate": candidate,
            }
        )

        assert "error" not in result
        # Base score 0.75 + affiliated boost 0.15 = 0.90
        assert result["confidence"] >= 0.9
        assert result["confidence_level"] == "high"
        assert result["should_match"] is True

    @pytest.mark.asyncio
    async def test_confidence_boost_with_additional_info(self, tools):
        """Test confidence boost with additional information."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 101,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.7,
            "match_type": "partial",
            "is_affiliated": False,
        }

        additional_info = {
            "entity_type": "politician",
            "entity_id": 101,
            "entity_name": "田中太郎",
            "info": {
                "affiliation": [
                    {
                        "conference_id": 1,
                        "conference_name": "○○市議会",
                        "start_date": "2023-01-01",
                        "end_date": None,
                    }
                ],
                "party": {"party_id": 1, "party_name": "○○党"},
            },
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中",
                "candidate": candidate,
                "additional_info": additional_info,
            }
        )

        assert "error" not in result
        # Base score 0.7 + affiliation boost 0.1 + party boost 0.05 = 0.85
        assert result["confidence"] >= 0.8
        assert result["should_match"] is True

    @pytest.mark.asyncio
    async def test_low_confidence(self, tools):
        """Test low confidence case."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 104,
            "politician_name": "高橋次郎",
            "party": "□□党",
            "score": 0.5,
            "match_type": "fuzzy",
            "is_affiliated": False,
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "candidate": candidate,
            }
        )

        assert "error" not in result
        assert result["confidence"] < 0.8
        assert result["confidence_level"] == "low"
        assert result["should_match"] is False
        assert "非推奨" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_empty_speaker_name(self, tools):
        """Test with empty speaker name."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 101,
            "politician_name": "田中太郎",
            "score": 1.0,
            "match_type": "exact",
            "is_affiliated": False,
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "",
                "candidate": candidate,
            }
        )

        assert "error" in result
        assert result["confidence"] == 0.0
        assert result["should_match"] is False

    @pytest.mark.asyncio
    async def test_invalid_candidate(self, tools):
        """Test with invalid candidate data."""
        judge_tool = tools[2]

        # Empty candidate dict (missing required fields)
        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "candidate": {},  # Empty dict instead of None
            }
        )

        assert "error" in result
        assert result["confidence"] == 0.0
        assert result["should_match"] is False

    @pytest.mark.asyncio
    async def test_contributing_factors(self, tools):
        """Test that contributing factors are properly tracked."""
        judge_tool = tools[2]

        candidate = {
            "politician_id": 101,
            "politician_name": "田中太郎",
            "party": "○○党",
            "score": 0.8,
            "match_type": "exact",
            "is_affiliated": True,
        }

        result = await judge_tool.ainvoke(
            {
                "speaker_name": "田中太郎",
                "candidate": candidate,
            }
        )

        assert "error" not in result
        assert "contributing_factors" in result
        assert len(result["contributing_factors"]) > 0

        # Check that base_score is in contributing factors
        factors = {f["factor"]: f for f in result["contributing_factors"]}
        assert "base_score" in factors
        assert factors["base_score"]["impact"] == 0.8

        # Check that is_affiliated is in contributing factors
        assert "is_affiliated" in factors
        assert factors["is_affiliated"]["impact"] == 0.15


class TestCalculateNameSimilarity:
    """Tests for _calculate_name_similarity helper function."""

    def test_exact_match(self):
        """Test exact match."""
        score, match_type = _calculate_name_similarity("田中太郎", "田中太郎")
        assert score == 1.0
        assert match_type == "exact"

    def test_exact_match_with_whitespace(self):
        """Test exact match with whitespace normalization."""
        score, match_type = _calculate_name_similarity("田中 太郎", "田中太郎")
        assert score == 1.0
        assert match_type == "exact"

    def test_partial_match_substring(self):
        """Test partial match where one name is substring of another."""
        score, match_type = _calculate_name_similarity("田中", "田中太郎")
        assert 0.0 < score < 1.0
        assert match_type == "partial"

    def test_partial_match_reverse(self):
        """Test partial match in reverse direction."""
        score, match_type = _calculate_name_similarity("田中太郎", "田中")
        assert 0.0 < score < 1.0
        assert match_type == "partial"

    def test_fuzzy_match(self):
        """Test fuzzy match with common characters."""
        score, match_type = _calculate_name_similarity("田中太郎", "田中一郎")
        assert 0.0 < score < 1.0
        assert match_type == "fuzzy"

    def test_no_match(self):
        """Test completely different names."""
        score, match_type = _calculate_name_similarity("田中太郎", "佐藤花子")
        # Should have very low or zero score
        assert score < 0.5
        assert match_type == "fuzzy"

    def test_empty_names(self):
        """Test with empty names."""
        score, match_type = _calculate_name_similarity("", "")
        assert score == 1.0  # Both empty, considered exact match
        assert match_type == "exact"
