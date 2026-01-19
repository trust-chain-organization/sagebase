"""基本的なデータ転送オブジェクト定義

汎用的に使用されるDTOを定義します。
"""

from datetime import date, datetime
from typing import TypedDict


class GoverningBodyDTO(TypedDict):
    """自治体データ転送オブジェクト"""

    id: int
    name: str
    type: str
    organization_code: str | None
    organization_type: str | None
    created_at: datetime
    updated_at: datetime


class ConferenceBaseDTO(TypedDict):
    """会議体データ転送オブジェクト（基本型）"""

    id: int
    governing_body_id: int
    name: str
    description: str | None
    members_introduction_url: str | None
    created_at: datetime
    updated_at: datetime


class PoliticianBaseDTO(TypedDict):
    """政治家データ転送オブジェクト（汎用型）

    Note:
        これはLLMサービス等で使用される汎用的な政治家DTO。
        アプリケーション層のPoliticianDTOとは異なります。
    """

    id: int
    name: str
    party_id: int | None
    prefecture: str | None
    electoral_district: str | None
    profile_url: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime


class SpeakerBaseDTO(TypedDict):
    """発言者データ転送オブジェクト（基本型）"""

    id: int
    name: str
    normalized_name: str
    is_politician: bool
    meeting_id: int | None
    politician_id: int | None
    party_affiliation: str | None
    position_or_title: str | None
    created_at: datetime
    updated_at: datetime


class MeetingBaseDTO(TypedDict):
    """会議データ転送オブジェクト"""

    id: int
    governing_body_id: int
    conference_id: int
    date: date
    name: str
    url: str | None
    pdf_url: str | None
    gcs_pdf_uri: str | None
    gcs_text_uri: str | None
    created_at: datetime
    updated_at: datetime


class ConversationBaseDTO(TypedDict):
    """発言データ転送オブジェクト"""

    id: int
    speaker_id: int
    meeting_id: int
    sequence_number: int
    content: str
    created_at: datetime
    updated_at: datetime


class MinutesBaseDTO(TypedDict):
    """議事録データ転送オブジェクト"""

    id: int
    meeting_id: int
    content: str
    created_at: datetime
    updated_at: datetime


class ParliamentaryGroupBaseDTO(TypedDict):
    """議員団データ転送オブジェクト"""

    id: int
    conference_id: int
    name: str
    abbreviated_name: str | None
    political_party_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExtractedConferenceMemberBaseDTO(TypedDict):
    """抽出された会議体メンバーデータ転送オブジェクト"""

    id: int
    conference_id: int
    name: str
    party_affiliation: str | None
    role: str | None
    matching_status: str
    matched_politician_id: int | None
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime
