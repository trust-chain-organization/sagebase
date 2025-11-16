"""Tests for MatchSpeakersUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


class TestMatchSpeakersUseCase:
    """Test cases for MatchSpeakersUseCase."""

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conversation_repo(self):
        """Create mock conversation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_service(self):
        """Create mock speaker domain service."""
        service = MagicMock()
        service.normalize_speaker_name = MagicMock(side_effect=lambda x: x.strip())
        service.calculate_name_similarity = MagicMock(return_value=0.9)
        return service

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def use_case(
        self,
        mock_speaker_repo,
        mock_politician_repo,
        mock_conversation_repo,
        mock_speaker_service,
        mock_llm_service,
    ):
        """Create MatchSpeakersUseCase instance."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=mock_llm_service,
        )

    @pytest.mark.asyncio
    async def test_execute_with_existing_politician_link(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test matching when speaker already has a linked politician."""
        # Setup
        speaker = Speaker(id=1, name="山田太郎", is_politician=True, politician_id=10)
        politician = Politician(id=10, name="山田太郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_id.return_value = politician

        # Execute
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 1
        assert results[0].matched_politician_id == 10
        assert results[0].confidence_score == 1.0
        assert results[0].matching_method == "existing"

    @pytest.mark.asyncio
    async def test_execute_with_rule_based_matching(
        self, use_case, mock_speaker_repo, mock_politician_repo, mock_speaker_service
    ):
        """Test rule-based matching."""
        # Setup
        speaker = Speaker(id=2, name="鈴木花子", is_politician=True)
        politician = Politician(id=20, name="鈴木花子", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = [politician]
        mock_speaker_service.calculate_name_similarity.return_value = 0.9

        # Execute
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 2
        assert results[0].matched_politician_id == 20
        assert results[0].confidence_score == 0.9
        assert results[0].matching_method == "rule-based"

    @pytest.mark.asyncio
    async def test_execute_with_llm_matching(
        self, use_case, mock_speaker_repo, mock_politician_repo, mock_llm_service
    ):
        """Test LLM-based matching."""
        # Setup
        speaker = Speaker(id=3, name="田中次郎", is_politician=True)
        politician = Politician(id=30, name="田中次郎", political_party_id=2)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        mock_llm_service.match_speaker_to_politician.return_value = {
            "matched_id": 30,
            "confidence": 0.85,
        }

        # Execute
        results = await use_case.execute(use_llm=True)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 3
        assert results[0].matched_politician_id == 30
        assert results[0].confidence_score == 0.85
        assert results[0].matching_method == "llm"

    @pytest.mark.asyncio
    async def test_execute_no_match_found(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test when no match is found."""
        # Setup
        speaker = Speaker(id=4, name="佐藤三郎", is_politician=True)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []

        # Execute
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 4
        assert results[0].matched_politician_id is None
        assert results[0].confidence_score == 0.0
        assert results[0].matching_method == "none"

    @pytest.mark.asyncio
    async def test_execute_with_specific_speaker_ids(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test matching specific speakers by ID."""
        # Setup
        speaker1 = Speaker(id=1, name="山田太郎", is_politician=True)
        speaker2 = Speaker(id=2, name="鈴木花子", is_politician=True)

        # Configure mock to not have batch_get_by_ids method
        del mock_speaker_repo.batch_get_by_ids
        mock_speaker_repo.get_by_id.side_effect = [speaker1, speaker2]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []

        # Execute
        results = await use_case.execute(use_llm=False, speaker_ids=[1, 2])

        # Verify
        assert len(results) == 2
        assert mock_speaker_repo.get_by_id.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_limit(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test matching with limit."""
        # Setup
        speakers = [
            Speaker(id=i, name=f"議員{i}", is_politician=True) for i in range(1, 6)
        ]

        mock_speaker_repo.get_politicians.return_value = speakers
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []

        # Execute
        results = await use_case.execute(use_llm=False, limit=3)

        # Verify
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_execute_skip_speaker_without_id(self, use_case, mock_speaker_repo):
        """Test that speakers without ID are skipped."""
        # Setup
        speakers = [
            Speaker(id=None, name="無効な議員", is_politician=True),
            Speaker(id=1, name="有効な議員", is_politician=True),
        ]

        mock_speaker_repo.get_politicians.return_value = speakers
        mock_politician_repo = use_case.politician_repo
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []

        # Execute
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].speaker_id == 1

    @pytest.mark.asyncio
    async def test_rule_based_matching_with_party_boost(
        self, use_case, mock_speaker_repo, mock_politician_repo, mock_speaker_service
    ):
        """Test rule-based matching with party information boost."""
        # Setup
        speaker = Speaker(
            id=5,
            name="高橋四郎",
            is_politician=True,
            political_party_name="自民党",
        )
        politician = Politician(
            id=50,
            name="高橋四郎",
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = [politician]
        mock_speaker_service.calculate_name_similarity.return_value = 0.75

        # Execute
        results = await use_case.execute(use_llm=False)

        # Verify
        assert len(results) == 1
        assert results[0].matched_politician_id == 50
        # Score should be boosted by 0.1 for party match
        assert results[0].confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_llm_matching_no_candidates(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test LLM matching when no candidates exist."""
        # Setup
        speaker = Speaker(id=6, name="新人議員", is_politician=True)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        # No existing politician link
        mock_politician_repo.search_by_name.return_value = []
        # Configure mock to not have get_all_cached method
        del mock_politician_repo.get_all_cached
        mock_politician_repo.get_all.return_value = []  # No candidates

        # Execute
        results = await use_case.execute(use_llm=True)

        # Verify
        assert len(results) == 1
        assert results[0].matched_politician_id is None
        assert results[0].matching_method == "none"

    @pytest.mark.asyncio
    async def test_execute_saves_user_id_on_successful_match(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test that user_id is saved when matching succeeds."""
        from uuid import uuid4

        # Setup
        test_user_id = uuid4()
        speaker = Speaker(id=1, name="山田太郎", is_politician=True)
        politician = Politician(id=10, name="山田太郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = [politician]

        # Mock the update method to capture the updated speaker
        updated_speaker = None

        async def capture_update(s):
            nonlocal updated_speaker
            updated_speaker = s
            return s

        mock_speaker_repo.update = capture_update

        # Execute
        results = await use_case.execute(use_llm=False, user_id=test_user_id)

        # Verify
        assert updated_speaker is not None
        assert updated_speaker.matched_by_user_id == test_user_id
        assert updated_speaker.politician_id == 10
        assert len(results) == 1
        assert results[0].matched_politician_id == 10

    @pytest.mark.asyncio
    async def test_execute_without_user_id(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test that matching works when user_id is None."""
        # Setup
        speaker = Speaker(id=1, name="山田太郎", is_politician=True)
        politician = Politician(id=10, name="山田太郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.search_by_name.return_value = [politician]

        updated_speaker = None

        async def capture_update(s):
            nonlocal updated_speaker
            updated_speaker = s
            return s

        mock_speaker_repo.update = capture_update

        # Execute without user_id
        results = await use_case.execute(use_llm=False, user_id=None)

        # Verify
        assert updated_speaker is not None
        assert updated_speaker.matched_by_user_id is None  # NULL is acceptable
        assert updated_speaker.politician_id == 10
        assert len(results) == 1
        assert results[0].matched_politician_id == 10

    @pytest.mark.asyncio
    async def test_execute_does_not_update_user_id_for_existing_match(
        self, use_case, mock_speaker_repo, mock_politician_repo
    ):
        """Test that user_id is not updated for existing politician links."""
        from uuid import uuid4

        # Setup
        original_user_id = uuid4()
        new_user_id = uuid4()
        speaker = Speaker(
            id=1,
            name="山田太郎",
            is_politician=True,
            politician_id=10,
            matched_by_user_id=original_user_id,
        )
        politician = Politician(id=10, name="山田太郎", political_party_id=1)

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_id.return_value = politician

        # Ensure update is not called
        mock_speaker_repo.update = AsyncMock()

        # Execute with different user_id
        results = await use_case.execute(use_llm=False, user_id=new_user_id)

        # Verify - user_id should NOT be updated
        assert results[0].matching_method == "existing"
        # update should not be called for existing matches
        mock_speaker_repo.update.assert_not_called()
