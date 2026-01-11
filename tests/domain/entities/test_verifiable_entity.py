"""Tests for VerifiableEntity protocol and its implementations."""

from src.domain.entities.conversation import Conversation
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.politician_affiliation import PoliticianAffiliation
from src.domain.entities.speaker import Speaker


class TestVerifiableEntityProtocol:
    """Test VerifiableEntity protocol compliance."""

    def test_speaker_implements_verifiable_entity(self) -> None:
        """Test that Speaker implements VerifiableEntity protocol."""
        speaker = Speaker(name="発言者A")

        assert hasattr(speaker, "is_manually_verified")
        assert hasattr(speaker, "latest_extraction_log_id")
        assert hasattr(speaker, "mark_as_manually_verified")
        assert hasattr(speaker, "update_from_extraction_log")
        assert hasattr(speaker, "can_be_updated_by_ai")

    def test_conversation_implements_verifiable_entity(self) -> None:
        """Test that Conversation implements VerifiableEntity protocol."""
        conversation = Conversation(comment="テストコメント", sequence_number=1)

        assert hasattr(conversation, "is_manually_verified")
        assert hasattr(conversation, "latest_extraction_log_id")
        assert hasattr(conversation, "mark_as_manually_verified")
        assert hasattr(conversation, "update_from_extraction_log")
        assert hasattr(conversation, "can_be_updated_by_ai")

    def test_politician_affiliation_implements_verifiable_entity(self) -> None:
        """Test that PoliticianAffiliation implements VerifiableEntity protocol."""
        from datetime import date

        affiliation = PoliticianAffiliation(
            politician_id=1, conference_id=1, start_date=date(2024, 1, 1)
        )

        assert hasattr(affiliation, "is_manually_verified")
        assert hasattr(affiliation, "latest_extraction_log_id")
        assert hasattr(affiliation, "mark_as_manually_verified")
        assert hasattr(affiliation, "update_from_extraction_log")
        assert hasattr(affiliation, "can_be_updated_by_ai")

    def test_parliamentary_group_membership_implements_verifiable_entity(self) -> None:
        """Test that ParliamentaryGroupMembership implements VerifiableEntity."""
        from datetime import date

        membership = ParliamentaryGroupMembership(
            politician_id=1, parliamentary_group_id=1, start_date=date(2024, 1, 1)
        )

        assert hasattr(membership, "is_manually_verified")
        assert hasattr(membership, "latest_extraction_log_id")
        assert hasattr(membership, "mark_as_manually_verified")
        assert hasattr(membership, "update_from_extraction_log")
        assert hasattr(membership, "can_be_updated_by_ai")


class TestVerifiableEntityMethods:
    """Test VerifiableEntity methods."""

    def test_default_is_manually_verified_is_false(self) -> None:
        """Test that default is_manually_verified is False."""
        entities = [
            Speaker(name="Test"),
            Conversation(comment="Test", sequence_number=1),
        ]

        for entity in entities:
            assert entity.is_manually_verified is False

    def test_default_latest_extraction_log_id_is_none(self) -> None:
        """Test that default latest_extraction_log_id is None."""
        entities = [
            Speaker(name="Test"),
            Conversation(comment="Test", sequence_number=1),
        ]

        for entity in entities:
            assert entity.latest_extraction_log_id is None

    def test_mark_as_manually_verified(self) -> None:
        """Test mark_as_manually_verified sets flag to True."""
        speaker = Speaker(name="Test")
        assert speaker.is_manually_verified is False

        speaker.mark_as_manually_verified()

        assert speaker.is_manually_verified is True

    def test_update_from_extraction_log(self) -> None:
        """Test update_from_extraction_log sets log ID."""
        speaker = Speaker(name="Test")
        assert speaker.latest_extraction_log_id is None

        speaker.update_from_extraction_log(42)

        assert speaker.latest_extraction_log_id == 42

    def test_can_be_updated_by_ai_when_not_verified(self) -> None:
        """Test can_be_updated_by_ai returns True when not verified."""
        conversation = Conversation(comment="Test", sequence_number=1)
        assert conversation.is_manually_verified is False

        assert conversation.can_be_updated_by_ai() is True

    def test_can_be_updated_by_ai_when_verified(self) -> None:
        """Test can_be_updated_by_ai returns False when verified."""
        conversation = Conversation(comment="Test", sequence_number=1)
        conversation.mark_as_manually_verified()

        assert conversation.can_be_updated_by_ai() is False


class TestVerifiableEntityInitialization:
    """Test VerifiableEntity fields during initialization."""

    def test_speaker_can_be_initialized_with_verification_fields(self) -> None:
        """Test Speaker can be initialized with verification fields."""
        speaker = Speaker(
            name="Test",
            is_manually_verified=True,
            latest_extraction_log_id=200,
        )

        assert speaker.is_manually_verified is True
        assert speaker.latest_extraction_log_id == 200

    def test_conversation_can_be_initialized_with_verification_fields(self) -> None:
        """Test Conversation can be initialized with verification fields."""
        conversation = Conversation(
            comment="Test",
            sequence_number=1,
            is_manually_verified=True,
            latest_extraction_log_id=300,
        )

        assert conversation.is_manually_verified is True
        assert conversation.latest_extraction_log_id == 300

    def test_politician_affiliation_can_be_initialized_with_verification_fields(
        self,
    ) -> None:
        """Test PoliticianAffiliation can be initialized with verification fields."""
        from datetime import date

        affiliation = PoliticianAffiliation(
            politician_id=1,
            conference_id=1,
            start_date=date(2024, 1, 1),
            is_manually_verified=True,
            latest_extraction_log_id=400,
        )

        assert affiliation.is_manually_verified is True
        assert affiliation.latest_extraction_log_id == 400

    def test_parliamentary_group_membership_can_be_initialized_with_verification_fields(
        self,
    ) -> None:
        """Test ParliamentaryGroupMembership can be initialized with verification."""
        from datetime import date

        membership = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=1,
            start_date=date(2024, 1, 1),
            is_manually_verified=True,
            latest_extraction_log_id=500,
        )

        assert membership.is_manually_verified is True
        assert membership.latest_extraction_log_id == 500


class TestVerifiableEntityWorkflow:
    """Test real-world workflow scenarios for VerifiableEntity."""

    def test_ai_extraction_to_manual_verification_workflow(self) -> None:
        """Test workflow from AI extraction to manual verification."""
        # Step 1: AI extracts data and creates entity
        speaker = Speaker(name="AI抽出された発言者")
        speaker.update_from_extraction_log(1)

        assert speaker.is_manually_verified is False
        assert speaker.latest_extraction_log_id == 1
        assert speaker.can_be_updated_by_ai() is True

        # Step 2: Human verifies the data
        speaker.mark_as_manually_verified()

        assert speaker.is_manually_verified is True
        assert speaker.can_be_updated_by_ai() is False

        # Step 3: AI tries to update again with new extraction
        speaker.update_from_extraction_log(2)

        # The extraction log is updated, but AI should check can_be_updated_by_ai
        assert speaker.latest_extraction_log_id == 2
        assert speaker.can_be_updated_by_ai() is False

    def test_multiple_ai_extractions_before_verification(self) -> None:
        """Test multiple AI extractions before human verification."""
        speaker = Speaker(name="Speaker A")

        # Multiple AI extractions
        speaker.update_from_extraction_log(1)
        assert speaker.latest_extraction_log_id == 1

        speaker.update_from_extraction_log(2)
        assert speaker.latest_extraction_log_id == 2

        speaker.update_from_extraction_log(3)
        assert speaker.latest_extraction_log_id == 3

        # Still can be updated by AI
        assert speaker.can_be_updated_by_ai() is True

        # Human verification locks it
        speaker.mark_as_manually_verified()
        assert speaker.can_be_updated_by_ai() is False
