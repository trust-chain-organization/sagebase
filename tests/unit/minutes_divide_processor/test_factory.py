"""Tests for MinutesDivider factory"""

from unittest.mock import patch

from src.infrastructure.external.minutes_divider.factory import MinutesDividerFactory


class TestMinutesDividerFactory:
    """Test cases for MinutesDividerFactory"""

    def test_create_baml_implementation_default(self):
        """Test that factory creates BAML implementation by default"""
        # USE_BAML_MINUTES_DIVIDERが設定されていない場合、BAML実装を返す（新デフォルト）
        with patch.dict("os.environ", {}, clear=False):
            # USE_BAML_MINUTES_DIVIDERを削除（もし存在すれば）
            import os

            os.environ.pop("USE_BAML_MINUTES_DIVIDER", None)
            divider = MinutesDividerFactory.create()

            # Assert - should be BAMLMinutesDivider (default)
            assert divider.__class__.__name__ == "BAMLMinutesDivider"

    def test_create_pydantic_implementation_explicit_false(self):
        """Test that factory creates Pydantic implementation when explicitly disabled"""
        with patch.dict("os.environ", {"USE_BAML_MINUTES_DIVIDER": "false"}):
            divider = MinutesDividerFactory.create()

            # Assert - should be MinutesDivider (Pydantic implementation)
            assert divider.__class__.__name__ == "MinutesDivider"

    def test_create_baml_implementation(self):
        """Test that factory creates BAML implementation when enabled"""
        with patch.dict("os.environ", {"USE_BAML_MINUTES_DIVIDER": "true"}):
            divider = MinutesDividerFactory.create()

            # Assert - should be BAMLMinutesDivider
            assert divider.__class__.__name__ == "BAMLMinutesDivider"

    def test_create_baml_implementation_case_insensitive(self):
        """Test that factory handles case-insensitive environment variable"""
        with patch.dict("os.environ", {"USE_BAML_MINUTES_DIVIDER": "TRUE"}):
            divider = MinutesDividerFactory.create()

            # Assert - should be BAMLMinutesDivider
            assert divider.__class__.__name__ == "BAMLMinutesDivider"

    def test_create_with_llm_service(self):
        """Test that factory passes llm_service to Pydantic implementation"""
        from unittest.mock import Mock

        mock_service = Mock()

        with patch.dict("os.environ", {"USE_BAML_MINUTES_DIVIDER": "false"}):
            # Should not raise an error
            divider = MinutesDividerFactory.create(llm_service=mock_service, k=10)

            # Assert
            assert divider.__class__.__name__ == "MinutesDivider"
            assert divider.k == 10

    def test_create_baml_with_k_parameter(self):
        """Test that factory passes k parameter to BAML implementation"""
        with patch.dict("os.environ", {"USE_BAML_MINUTES_DIVIDER": "true"}):
            divider = MinutesDividerFactory.create(k=10)

            # Assert
            assert divider.__class__.__name__ == "BAMLMinutesDivider"
            assert divider.k == 10
