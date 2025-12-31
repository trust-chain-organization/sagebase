"""汎用抽出ログエンティティ。

全エンティティ（Statement, Politician, Speaker, ConferenceMember,
ParliamentaryGroupMember）のLLM抽出結果を統一的に履歴管理する
ためのドメインエンティティ。
"""

from enum import Enum
from typing import Any

from src.domain.entities.base import BaseEntity


class EntityType(Enum):
    """抽出対象エンティティのタイプ。"""

    STATEMENT = "statement"
    POLITICIAN = "politician"
    SPEAKER = "speaker"
    CONFERENCE_MEMBER = "conference_member"
    PARLIAMENTARY_GROUP_MEMBER = "parliamentary_group_member"


class ExtractionLog(BaseEntity):
    """LLM抽出結果の履歴を記録するエンティティ。

    このエンティティは、LLM による抽出処理の結果をスナップショットとして保存し、
    トレーサビリティと AI 精度分析を可能にします。

    主な特徴:
    - Immutable: 作成後は更新されない（履歴として保持）
    - 汎用設計: 全エンティティタイプに対応
    - トレーサビリティ: パイプラインバージョンと抽出データを記録
    """

    def __init__(
        self,
        entity_type: EntityType,
        entity_id: int,
        pipeline_version: str,
        extracted_data: dict[str, Any],
        confidence_score: float | None = None,
        extraction_metadata: dict[str, Any] | None = None,
        id: int | None = None,
    ) -> None:
        """抽出ログを初期化する。

        Args:
            entity_type: 抽出対象のエンティティタイプ
            entity_id: 抽出対象のエンティティID
            pipeline_version: パイプラインのバージョン（例: "gemini-2.0-flash-v1"）
            extracted_data: LLMが出力した生データ（JSON形式）
            confidence_score: 抽出の信頼度スコア（0.0〜1.0）
            extraction_metadata: 抽出に関する追加メタデータ
                （例: モデル名、トークン数、処理時間など）
            id: エンティティID
        """
        super().__init__(id)
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.pipeline_version = pipeline_version
        self.extracted_data = extracted_data
        self.confidence_score = confidence_score
        self.extraction_metadata = extraction_metadata or {}

    @property
    def model_name(self) -> str | None:
        """メタデータからモデル名を取得する。"""
        return self.extraction_metadata.get("model_name")

    @property
    def token_count_input(self) -> int | None:
        """メタデータから入力トークン数を取得する。"""
        return self.extraction_metadata.get("token_count_input")

    @property
    def token_count_output(self) -> int | None:
        """メタデータから出力トークン数を取得する。"""
        return self.extraction_metadata.get("token_count_output")

    @property
    def processing_time_ms(self) -> int | None:
        """メタデータから処理時間（ミリ秒）を取得する。"""
        return self.extraction_metadata.get("processing_time_ms")

    def __str__(self) -> str:
        return (
            f"ExtractionLog(type={self.entity_type.value}, "
            f"entity_id={self.entity_id}, "
            f"version={self.pipeline_version})"
        )

    def __repr__(self) -> str:
        return (
            f"ExtractionLog(id={self.id}, "
            f"entity_type={self.entity_type}, "
            f"entity_id={self.entity_id}, "
            f"pipeline_version={self.pipeline_version}, "
            f"confidence_score={self.confidence_score})"
        )
