"""Tests for MinutesDivider factory"""

from src.infrastructure.external.minutes_divider.factory import MinutesDividerFactory


class TestMinutesDividerFactory:
    """Test cases for MinutesDividerFactory"""

    def test_create_baml_implementation(self):
        """Test that factory creates BAML implementation"""
        divider = MinutesDividerFactory.create()

        # Assert - should be BAMLMinutesDivider
        assert divider.__class__.__name__ == "BAMLMinutesDivider"

    def test_create_with_k_parameter(self):
        """Test that factory passes k parameter to BAML implementation"""
        divider = MinutesDividerFactory.create(k=10)

        # Assert
        assert divider.__class__.__name__ == "BAMLMinutesDivider"
        assert divider.k == 10
