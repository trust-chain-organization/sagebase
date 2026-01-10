"""抽出結果DTOモジュール。"""

from src.application.dtos.extraction_result.conference_member_extraction_result import (
    ConferenceMemberExtractionResult,
)
from src.application.dtos.extraction_result.conversation_extraction_result import (
    ConversationExtractionResult,
)
from src.application.dtos.extraction_result.parliamentary_group_member_extraction_result import (  # noqa: E501
    ParliamentaryGroupMemberExtractionResult,
)
from src.application.dtos.extraction_result.parliamentary_group_membership_extraction_result import (  # noqa: E501
    ParliamentaryGroupMembershipExtractionResult,
)
from src.application.dtos.extraction_result.speaker_extraction_result import (
    SpeakerExtractionResult,
)


__all__ = [
    "ConferenceMemberExtractionResult",
    "ConversationExtractionResult",
    "ParliamentaryGroupMemberExtractionResult",
    "ParliamentaryGroupMembershipExtractionResult",
    "SpeakerExtractionResult",
]
