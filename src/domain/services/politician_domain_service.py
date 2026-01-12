"""Politician domain service for handling politician-related business logic."""

from src.domain.entities.politician import Politician


class PoliticianDomainService:
    """Domain service for politician-related business logic."""

    def normalize_politician_name(self, name: str) -> str:
        """Normalize politician name for comparison."""
        # Remove spaces and convert to consistent format
        normalized = name.strip().replace(" ", "").replace("　", "")
        return normalized

    def extract_surname(self, full_name: str) -> str:
        """Extract surname from full name."""
        # Japanese names typically have surname first
        name_parts = full_name.strip().split()
        if name_parts:
            return name_parts[0]
        return full_name

    def is_duplicate_politician(
        self, new_politician: Politician, existing_politicians: list[Politician]
    ) -> Politician | None:
        """Check if politician already exists based on name and party."""
        normalized_new = self.normalize_politician_name(new_politician.name)

        for existing in existing_politicians:
            normalized_existing = self.normalize_politician_name(existing.name)

            # Exact match
            if normalized_new == normalized_existing:
                # Same party or no party info
                if (
                    new_politician.political_party_id == existing.political_party_id
                    or new_politician.political_party_id is None
                    or existing.political_party_id is None
                ):
                    return existing

        return None

    def merge_politician_info(
        self, existing: Politician, new_info: Politician
    ) -> Politician:
        """Merge new politician information with existing record."""
        # Keep existing ID
        merged = Politician(
            name=existing.name,  # Keep original name format
            prefecture=new_info.prefecture or existing.prefecture,
            political_party_id=new_info.political_party_id
            or existing.political_party_id,
            furigana=new_info.furigana or existing.furigana,
            district=new_info.district or existing.district,
            profile_page_url=new_info.profile_page_url or existing.profile_page_url,
            id=existing.id,
        )
        return merged

    def validate_politician_data(self, politician: Politician) -> list[str]:
        """Validate politician data and return list of issues."""
        issues: list[str] = []

        if not politician.name or not politician.name.strip():
            issues.append("Name is required")

        # Check for suspicious data
        if politician.name and len(politician.name) > 50:
            issues.append("Name is unusually long")

        if politician.district and len(politician.district) > 100:
            issues.append("District name is unusually long")

        return issues

    def group_politicians_by_party(
        self, politicians: list[Politician]
    ) -> dict[int | None, list[Politician]]:
        """Group politicians by their political party."""
        grouped: dict[int | None, list[Politician]] = {}

        for politician in politicians:
            party_id = politician.political_party_id
            if party_id not in grouped:
                grouped[party_id] = []
            grouped[party_id].append(politician)

        return grouped

    def find_similar_politicians(
        self, name: str, politicians: list[Politician], threshold: float = 0.7
    ) -> list[Politician]:
        """Find politicians with similar names."""
        normalized_target = self.normalize_politician_name(name)
        similar: list[Politician] = []

        for politician in politicians:
            normalized_name = self.normalize_politician_name(politician.name)

            # Simple similarity check
            if (
                normalized_target in normalized_name
                or normalized_name in normalized_target
            ):
                similar.append(politician)
            elif (
                self._calculate_similarity(normalized_target, normalized_name)
                >= threshold
            ):
                similar.append(politician)

        return similar

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        if name1 == name2:
            return 1.0

        # Character-based similarity
        chars1 = set(name1)
        chars2 = set(name2)

        if not chars1 or not chars2:
            return 0.0

        intersection = chars1 & chars2
        union = chars1 | chars2

        return len(intersection) / len(union)
