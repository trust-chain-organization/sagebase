"""Tests for SpeakerMatchingServiceFactory

These tests are marked with @pytest.mark.baml and should run in separate BAML CI.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.domain.services.factories.speaker_matching_factory import (
    SpeakerMatchingServiceFactory,
)

pytestmark = pytest.mark.baml


@pytest.fixture
def mock_llm_service():
    """Mock LLM service"""
    return MagicMock()


@pytest.fixture
def mock_speaker_repository():
    """Mock speaker repository"""
    return MagicMock()


class TestSpeakerMatchingServiceFactory:
    """SpeakerMatchingServiceFactory tests"""

    def test_create_returns_standard_implementation_by_default(
        self, mock_llm_service, mock_speaker_repository
    ):
        """デフォルトで標準実装を返すテスト"""
        service = SpeakerMatchingServiceFactory.create(
            mock_llm_service, mock_speaker_repository
        )

        # 標準実装かどうかを確認
        assert service.__class__.__name__ == "SpeakerMatchingService"

    def test_create_returns_standard_when_env_is_false(
        self, mock_llm_service, mock_speaker_repository
    ):
        """USE_BAML_SPEAKER_MATCHING=falseで標準実装を返すテスト"""
        with patch.dict("os.environ", {"USE_BAML_SPEAKER_MATCHING": "false"}):
            service = SpeakerMatchingServiceFactory.create(
                mock_llm_service, mock_speaker_repository
            )

            assert service.__class__.__name__ == "SpeakerMatchingService"

    def test_create_returns_baml_when_env_is_true(
        self, mock_llm_service, mock_speaker_repository
    ):
        """USE_BAML_SPEAKER_MATCHING=trueでBAML実装を返すテスト"""
        with patch.dict("os.environ", {"USE_BAML_SPEAKER_MATCHING": "true"}):
            service = SpeakerMatchingServiceFactory.create(
                mock_llm_service, mock_speaker_repository
            )

            assert service.__class__.__name__ == "BAMLSpeakerMatchingService"

    def test_create_returns_baml_when_env_is_uppercase_true(
        self, mock_llm_service, mock_speaker_repository
    ):
        """USE_BAML_SPEAKER_MATCHING=TRUEでもBAML実装を返すテスト（大文字対応）"""
        with patch.dict("os.environ", {"USE_BAML_SPEAKER_MATCHING": "TRUE"}):
            service = SpeakerMatchingServiceFactory.create(
                mock_llm_service, mock_speaker_repository
            )

            assert service.__class__.__name__ == "BAMLSpeakerMatchingService"

    def test_both_implementations_have_same_interface(
        self, mock_llm_service, mock_speaker_repository
    ):
        """両実装が同じインターフェースを持つことを確認"""
        # 標準実装
        with patch.dict("os.environ", {"USE_BAML_SPEAKER_MATCHING": "false"}):
            standard_service = SpeakerMatchingServiceFactory.create(
                mock_llm_service, mock_speaker_repository
            )

        # BAML実装
        with patch.dict("os.environ", {"USE_BAML_SPEAKER_MATCHING": "true"}):
            baml_service = SpeakerMatchingServiceFactory.create(
                mock_llm_service, mock_speaker_repository
            )

        # 両方とも同じメソッドを持つことを確認
        assert hasattr(standard_service, "find_best_match")
        assert hasattr(baml_service, "find_best_match")
        assert callable(standard_service.find_best_match)
        assert callable(baml_service.find_best_match)
