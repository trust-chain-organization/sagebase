"""Performance tests for extracted politician approval and conversion."""

import time

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.convert_extracted_politician_dto import (
    ConvertExtractedPoliticianInputDTO,
)
from src.application.dtos.review_extracted_politician_dto import BulkReviewInputDTO
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.domain.entities.politician import Politician
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)
from src.domain.entities.speaker import Speaker


@pytest.mark.integration
class TestExtractedPoliticianPerformance:
    """Performance tests for bulk operations on extracted politicians.

    These tests verify:
    1. Bulk approval performance
    2. Bulk conversion performance
    3. Transaction handling for large batches
    4. Memory efficiency
    """

    @pytest.fixture
    def mock_extracted_politician_repo(self):
        """Create mock extracted politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_party_repo(self):
        """Create mock party repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def review_use_case(self, mock_extracted_politician_repo, mock_party_repo):
        """Create ReviewExtractedPoliticianUseCase instance."""
        return ReviewExtractedPoliticianUseCase(
            mock_extracted_politician_repo, mock_party_repo
        )

    @pytest.fixture
    def convert_use_case(
        self,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Create ConvertExtractedPoliticianUseCase instance."""
        return ConvertExtractedPoliticianUseCase(
            extracted_politician_repository=mock_extracted_politician_repo,
            politician_repository=mock_politician_repo,
            speaker_repository=mock_speaker_repo,
        )

    def create_mock_extracted_politicians(self, count: int):
        """Helper to create mock extracted politicians."""
        return [
            PoliticianPartyExtractedPolitician(
                id=i,
                name=f"政治家{i}",
                party_id=1,
                district=f"選挙区{i % 10}",
                status="pending",
            )
            for i in range(1, count + 1)
        ]

    @pytest.mark.asyncio
    async def test_bulk_approval_performance(
        self,
        review_use_case,
        mock_extracted_politician_repo,
    ):
        """Test performance of bulk approval operation.

        大量承認のパフォーマンステスト:
        1. 100件のExtractedPoliticianを作成
        2. 一括承認実行
        3. 実行時間が許容範囲内（例: <5秒）
        4. 全件が正常に処理される
        """
        # Setup - 100 politicians
        politician_count = 100
        politicians = self.create_mock_extracted_politicians(politician_count)

        # Mock repository methods
        mock_extracted_politician_repo.get_by_id.side_effect = lambda id: next(
            (p for p in politicians if p.id == id), None
        )

        # Mock update_status to return updated politician
        async def mock_update_status(id, status, reviewer_id=None):
            politician = next((p for p in politicians if p.id == id), None)
            if politician:
                politician.status = status
                return politician
            return None

        mock_extracted_politician_repo.update_status.side_effect = mock_update_status

        # Execute bulk approval
        politician_ids = [p.id for p in politicians]
        request = BulkReviewInputDTO(
            politician_ids=politician_ids,
            action="approve",
            reviewer_id=1,
        )

        start_time = time.time()
        result = await review_use_case.bulk_review(request)
        elapsed_time = time.time() - start_time

        # Assertions
        assert result.total_processed == politician_count
        assert result.successful_count == politician_count
        assert result.failed_count == 0

        # Performance assertion - should complete in reasonable time
        # Allow generous time limit for CI environments
        assert elapsed_time < 10.0, (
            f"Bulk approval took {elapsed_time:.2f}s (expected < 10s)"
        )  # noqa: E501

        # Verify all were updated
        assert (
            mock_extracted_politician_repo.update_status.call_count == politician_count
        )  # noqa: E501

    @pytest.mark.asyncio
    async def test_bulk_conversion_performance(
        self,
        convert_use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test performance of bulk conversion operation.

        大量変換のパフォーマンステスト:
        1. 100件の承認済みExtractedPoliticianを作成
        2. 一括変換実行
        3. 実行時間が許容範囲内
        4. メモリ使用量が安定
        """
        # Setup - 100 approved politicians
        politician_count = 100
        politicians = [
            PoliticianPartyExtractedPolitician(
                id=i,
                name=f"政治家{i}",
                party_id=1,
                status="approved",
            )
            for i in range(1, politician_count + 1)
        ]

        mock_extracted_politician_repo.get_by_status.return_value = politicians
        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_speaker_repo.find_by_name.return_value = None

        # Mock speaker and politician creation
        mock_speaker_repo.create.side_effect = lambda s: Speaker(
            id=s.name.__hash__() % 10000, name=s.name, is_politician=True
        )
        mock_politician_repo.create.side_effect = lambda p: Politician(
            id=p.name.__hash__() % 10000,
            name=p.name,
            political_party_id=p.political_party_id,
        )

        # Execute bulk conversion
        start_time = time.time()
        result = await convert_use_case.execute(
            ConvertExtractedPoliticianInputDTO(batch_size=politician_count)
        )
        elapsed_time = time.time() - start_time

        # Assertions
        assert result.total_processed == politician_count
        assert result.converted_count == politician_count
        assert result.error_count == 0

        # Performance assertion
        assert elapsed_time < 15.0, (
            f"Bulk conversion took {elapsed_time:.2f}s (expected < 15s)"
        )  # noqa: E501

        # Verify all were created
        assert mock_politician_repo.create.call_count == politician_count

    @pytest.mark.asyncio
    async def test_batch_size_control(
        self,
        convert_use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test batch size limiting for memory control.

        バッチサイズ制御のテスト:
        1. 大量のデータが存在
        2. バッチサイズで制限
        3. 指定されたバッチサイズのみ処理
        4. メモリオーバーフローを防ぐ
        """
        # Setup - 500 politicians available
        all_politicians = [
            PoliticianPartyExtractedPolitician(
                id=i,
                name=f"政治家{i}",
                party_id=1,
                status="approved",
            )
            for i in range(1, 501)
        ]

        mock_extracted_politician_repo.get_by_status.return_value = all_politicians
        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_speaker_repo.find_by_name.return_value = None

        mock_speaker_repo.create.side_effect = lambda s: Speaker(
            id=s.name.__hash__() % 10000, name=s.name, is_politician=True
        )
        mock_politician_repo.create.side_effect = lambda p: Politician(
            id=p.name.__hash__() % 10000,
            name=p.name,
            political_party_id=p.political_party_id,
        )

        # Execute with batch size limit
        batch_size = 50
        result = await convert_use_case.execute(
            ConvertExtractedPoliticianInputDTO(batch_size=batch_size)
        )

        # Assertions - only batch_size politicians processed
        assert result.total_processed == batch_size
        assert result.converted_count == batch_size
        assert mock_politician_repo.create.call_count == batch_size

    @pytest.mark.asyncio
    async def test_concurrent_approval_safety(
        self,
        review_use_case,
        mock_extracted_politician_repo,
    ):
        """Test that concurrent approvals are handled safely.

        並行承認の安全性テスト:
        1. 同時に複数の承認リクエスト
        2. トランザクション分離レベルの確認
        3. データ整合性の維持
        """
        # Setup
        politician = PoliticianPartyExtractedPolitician(
            id=1,
            name="テスト太郎",
            party_id=1,
            status="pending",
        )

        mock_extracted_politician_repo.get_by_id.return_value = politician

        call_count = 0

        async def mock_update_status(id, status, reviewer_id=None):
            nonlocal call_count
            call_count += 1
            politician.status = status
            return politician

        mock_extracted_politician_repo.update_status.side_effect = mock_update_status

        # Execute multiple approval requests concurrently
        import asyncio

        from src.application.dtos.review_extracted_politician_dto import (
            ReviewExtractedPoliticianInputDTO,
        )

        requests = [
            ReviewExtractedPoliticianInputDTO(
                politician_id=1, action="approve", reviewer_id=i
            )
            for i in range(1, 4)  # 3 concurrent requests
        ]

        results = await asyncio.gather(
            *[review_use_case.review_politician(req) for req in requests]
        )

        # Assertions
        # All requests should succeed (idempotent)
        assert all(r.success for r in results)
        # But update_status should be called for each request
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_memory_efficiency_with_large_dataset(
        self,
        convert_use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test memory efficiency with large dataset.

        メモリ効率のテスト:
        1. 大量データ処理時のメモリ使用量
        2. バッチ処理によるメモリ管理
        3. メモリリークがないこと
        """
        # This is a lightweight test as we can't measure actual memory in pytest
        # But we can verify the implementation processes in batches

        # Setup - simulate large dataset
        large_count = 1000
        politicians = [
            PoliticianPartyExtractedPolitician(
                id=i,
                name=f"政治家{i}",
                party_id=1,
                status="approved",
            )
            for i in range(1, large_count + 1)
        ]

        mock_extracted_politician_repo.get_by_status.return_value = politicians
        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_speaker_repo.find_by_name.return_value = None

        # Mock with generator-like behavior to simulate streaming
        created_count = 0

        def create_politician(p):
            nonlocal created_count
            created_count += 1
            return Politician(
                id=created_count,
                name=p.name,
                political_party_id=p.political_party_id,
            )

        mock_politician_repo.create.side_effect = create_politician
        mock_speaker_repo.create.side_effect = lambda s: Speaker(
            id=s.name.__hash__() % 10000, name=s.name, is_politician=True
        )

        # Execute with smaller batch size for memory efficiency
        batch_size = 100
        result = await convert_use_case.execute(
            ConvertExtractedPoliticianInputDTO(batch_size=batch_size)
        )

        # Verify batch size was respected
        assert result.total_processed == batch_size
        assert created_count == batch_size
