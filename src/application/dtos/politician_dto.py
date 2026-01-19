"""Politician-related DTOs.

このモジュールは政治家管理に関するDTOを定義します。
Issue #969: UseCase層のリファクタリングにより、ManagePoliticiansUseCaseから移動。
"""

from dataclasses import dataclass
from uuid import UUID

from src.domain.entities import Politician


# =============================================================================
# 汎用DTO（インフラ層などで使用）
# =============================================================================


@dataclass
class CreatePoliticianDTO:
    """DTO for creating a politician."""

    name: str
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class UpdatePoliticianDTO:
    """DTO for updating a politician."""

    id: int
    name: str | None = None
    political_party_id: int | None = None
    furigana: str | None = None
    district: str | None = None
    profile_page_url: str | None = None
    party_position: str | None = None


@dataclass
class PoliticianDTO:
    """DTO for politician data."""

    id: int
    name: str
    political_party_id: int | None
    political_party_name: str | None
    furigana: str | None
    district: str | None
    profile_page_url: str | None
    party_position: str | None = None


# =============================================================================
# ManagePoliticiansUseCase用 Input/Output DTO
# Issue #969: UseCase層のリファクタリングにより移動
# =============================================================================


@dataclass
class PoliticianListInputDto:
    """Input DTO for listing politicians."""

    party_id: int | None = None
    search_name: str | None = None


@dataclass
class PoliticianListOutputDto:
    """Output DTO for listing politicians."""

    politicians: list[Politician]


@dataclass
class CreatePoliticianInputDto:
    """Input DTO for creating a politician."""

    name: str
    prefecture: str
    district: str
    party_id: int | None = None
    profile_url: str | None = None
    user_id: UUID | None = None  # 操作ユーザーID（ログ記録用）


@dataclass
class CreatePoliticianOutputDto:
    """Output DTO for creating a politician."""

    success: bool
    politician_id: int | None = None
    error_message: str | None = None


@dataclass
class UpdatePoliticianInputDto:
    """Input DTO for updating a politician."""

    id: int
    name: str
    prefecture: str
    district: str
    party_id: int | None = None
    profile_url: str | None = None
    user_id: UUID | None = None  # 操作ユーザーID（ログ記録用）


@dataclass
class UpdatePoliticianOutputDto:
    """Output DTO for updating a politician."""

    success: bool
    error_message: str | None = None


@dataclass
class DeletePoliticianInputDto:
    """Input DTO for deleting a politician."""

    id: int
    user_id: UUID | None = None  # 操作ユーザーID（ログ記録用）
    force: bool = False  # 警告を無視して削除を実行（speakerとの紐づきを解除）


@dataclass
class DeletePoliticianOutputDto:
    """Output DTO for deleting a politician."""

    success: bool
    error_message: str | None = None
    has_related_data: bool = False  # 関連データがあるかどうか
    related_data_counts: dict[str, int] | None = None  # テーブル名と件数のマッピング


@dataclass
class MergePoliticiansInputDto:
    """Input DTO for merging politicians."""

    source_id: int
    target_id: int


@dataclass
class MergePoliticiansOutputDto:
    """Output DTO for merging politicians."""

    success: bool
    error_message: str | None = None
