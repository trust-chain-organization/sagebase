"""Tests for PoliticianDomainService."""

import pytest

from src.domain.entities.politician import Politician
from src.domain.services.politician_domain_service import PoliticianDomainService


class TestPoliticianDomainService:
    """Test cases for PoliticianDomainService."""

    @pytest.fixture
    def service(self):
        """Create PoliticianDomainService instance."""
        return PoliticianDomainService()

    @pytest.fixture
    def sample_politician(self):
        """Create sample politician."""
        return Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            furigana="ヤマダタロウ",
            district="東京1区",
            profile_page_url="https://example.com/profile",
        )

    def test_normalize_politician_name(self, service):
        """Test politician name normalization."""
        # Test with regular spaces
        assert service.normalize_politician_name("山田 太郎") == "山田太郎"

        # Test with full-width spaces
        assert service.normalize_politician_name("山田　太郎") == "山田太郎"

        # Test with mixed spaces
        assert service.normalize_politician_name("山田 　太郎") == "山田太郎"

        # Test with leading/trailing spaces
        assert service.normalize_politician_name("  山田太郎  ") == "山田太郎"

        # Test empty string
        assert service.normalize_politician_name("") == ""

    def test_extract_surname(self, service):
        """Test surname extraction."""
        # Test normal Japanese name
        assert service.extract_surname("山田太郎") == "山田太郎"

        # Test name with space
        assert service.extract_surname("山田 太郎") == "山田"

        # Test single name
        assert service.extract_surname("山田") == "山田"

        # Test empty string
        assert service.extract_surname("") == ""

        # Test with multiple spaces
        assert service.extract_surname("山田 太郎 次郎") == "山田"

    def test_is_duplicate_politician_exact_match(self, service):
        """Test duplicate detection with exact name match."""
        existing = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            ),
            Politician(
                id=2,
                name="鈴木花子",
                prefecture="大阪府",
                district="大阪1区",
                political_party_id=2,
            ),
        ]

        # Exact match with same party
        new = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        duplicate = service.is_duplicate_politician(new, existing)
        assert duplicate is not None
        assert duplicate.id == 1

        # Exact match with different party
        new = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=3,
        )
        duplicate = service.is_duplicate_politician(new, existing)
        assert duplicate is None

    def test_is_duplicate_politician_with_spaces(self, service):
        """Test duplicate detection with spaces in names."""
        existing = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            ),
        ]

        # Same name with spaces
        new = Politician(
            name="山田 太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        duplicate = service.is_duplicate_politician(new, existing)
        assert duplicate is not None
        assert duplicate.id == 1

    def test_is_duplicate_politician_no_party_info(self, service):
        """Test duplicate detection when party info is missing."""
        existing = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=None,
            ),
        ]

        # New politician with party info
        new = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        duplicate = service.is_duplicate_politician(new, existing)
        assert duplicate is not None
        assert duplicate.id == 1

        # Both without party info
        existing = [
            Politician(
                id=1,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            ),
        ]
        new = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=None,
        )
        duplicate = service.is_duplicate_politician(new, existing)
        assert duplicate is not None

    def test_merge_politician_info(self, service, sample_politician):
        """Test merging politician information."""
        existing = Politician(
            id=1,
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            furigana=None,
            district="東京1区",
            profile_page_url=None,
        )

        new_info = Politician(
            name="山田　太郎",  # Different format
            prefecture="東京都",
            political_party_id=2,
            furigana="ヤマダタロウ",
            district="東京2区",
            profile_page_url="https://example.com/new",
        )

        merged = service.merge_politician_info(existing, new_info)

        # Should keep existing ID
        assert merged.id == 1
        assert merged.name == "山田太郎"  # Keep original name format

        # Should take new values when existing is None
        assert merged.political_party_id == 2
        assert merged.furigana == "ヤマダタロウ"
        assert merged.profile_page_url == "https://example.com/new"

        # Should take new value when provided
        assert merged.district == "東京2区"

    def test_validate_politician_data(self, service):
        """Test politician data validation."""
        # Valid politician
        valid = Politician(
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            district="東京1区",
        )
        issues = service.validate_politician_data(valid)
        assert len(issues) == 0

        # Missing name
        invalid = Politician(name="", prefecture="東京都", district="東京1区")
        issues = service.validate_politician_data(invalid)
        assert "Name is required" in issues

        # Party can be None
        valid = Politician(
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=None,
        )
        issues = service.validate_politician_data(valid)
        assert len(issues) == 0

        # Long name
        invalid = Politician(
            name="あ" * 51,  # 51 characters
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        issues = service.validate_politician_data(invalid)
        assert "Name is unusually long" in issues

        # Long district
        invalid = Politician(
            name="山田太郎",
            prefecture="東京都",
            political_party_id=1,
            district="あ" * 101,  # 101 characters
        )
        issues = service.validate_politician_data(invalid)
        assert "District name is unusually long" in issues

    def test_group_politicians_by_party(self, service):
        """Test grouping politicians by party."""
        politicians = [
            Politician(
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
                political_party_id=1,
            ),
            Politician(
                name="鈴木花子",
                prefecture="大阪府",
                district="大阪1区",
                political_party_id=1,
            ),
            Politician(
                name="佐藤次郎",
                prefecture="愛知県",
                district="愛知1区",
                political_party_id=2,
            ),
            Politician(
                name="田中三郎",
                prefecture="福岡県",
                district="福岡1区",
                political_party_id=None,
            ),
            Politician(
                name="高橋四郎",
                prefecture="北海道",
                district="北海道1区",
                political_party_id=None,
            ),
        ]

        grouped = service.group_politicians_by_party(politicians)

        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 1
        assert len(grouped[None]) == 2

        assert grouped[1][0].name == "山田太郎"
        assert grouped[1][1].name == "鈴木花子"
        assert grouped[2][0].name == "佐藤次郎"

    def test_find_similar_politicians(self, service):
        """Test finding similar politicians."""
        politicians = [
            Politician(id=1, name="山田太郎", prefecture="東京都", district="東京1区"),
            Politician(id=2, name="山田次郎", prefecture="東京都", district="東京2区"),
            Politician(id=3, name="田中太郎", prefecture="大阪府", district="大阪1区"),
            Politician(id=4, name="鈴木花子", prefecture="愛知県", district="愛知1区"),
        ]

        # Find by substring
        similar = service.find_similar_politicians("山田", politicians)
        assert len(similar) == 2
        assert similar[0].id in [1, 2]
        assert similar[1].id in [1, 2]

        # Find by full name
        similar = service.find_similar_politicians("山田太郎", politicians)
        assert len(similar) >= 1
        assert any(p.id == 1 for p in similar)

        # No matches
        similar = service.find_similar_politicians("佐藤", politicians)
        assert len(similar) == 0

    def test_calculate_similarity(self, service):
        """Test name similarity calculation."""
        # Exact match
        assert service._calculate_similarity("山田太郎", "山田太郎") == 1.0

        # Completely different
        assert service._calculate_similarity("山田", "鈴木") == 0.0

        # Partial overlap
        similarity = service._calculate_similarity("山田太郎", "山田次郎")
        assert 0 < similarity < 1

        # Empty strings
        assert service._calculate_similarity("", "") == 1.0
        assert service._calculate_similarity("山田", "") == 0.0
        assert service._calculate_similarity("", "山田") == 0.0
