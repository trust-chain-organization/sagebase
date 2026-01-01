"""汎用的なAI抽出結果からのエンティティ更新UseCase。

人間による手動修正を保護しつつ、AI抽出結果でGoldエンティティを更新する
汎用基盤を提供する。
"""

import logging

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.entities.verifiable_entity import VerifiableEntity
from src.domain.repositories.extraction_log_repository import ExtractionLogRepository
from src.domain.repositories.session_adapter import ISessionAdapter


# VerifiableEntityプロトコルを満たすエンティティの型変数
TEntity = TypeVar("TEntity", bound=VerifiableEntity)
# 抽出結果の型変数（各エンティティ固有の抽出結果DTO）
TExtractionResult = TypeVar("TExtractionResult")

logger = logging.getLogger(__name__)


@dataclass
class UpdateEntityResult:
    """エンティティ更新結果を表すDTO。

    Attributes:
        updated: 更新が実行されたかどうか
        reason: 更新されなかった理由（更新された場合はNone）
            - "manually_verified": 手動検証済みのため更新スキップ
            - "entity_not_found": エンティティが見つからなかった
            - "no_changes": 変更がなかった（将来の拡張用）
        extraction_log_id: 保存された抽出ログのID
    """

    updated: bool
    reason: str | None
    extraction_log_id: int


class UpdateEntityFromExtractionUseCase(ABC, Generic[TEntity, TExtractionResult]):  # noqa: UP046
    """AI抽出結果からGoldエンティティを更新する汎用UseCase。

    このクラスは、以下の責務を持つ：
    1. 抽出ログを必ず保存（分析用のBronze Layer）
    2. 人間の手動修正を保護（is_manually_verifiedフラグチェック）
    3. 未確定エンティティのみAI結果を反映
    4. トランザクション管理
    5. ログ出力

    サブクラスは、エンティティ固有の処理を実装する：
    - _get_entity_type(): エンティティタイプを返す
    - _get_entity(): エンティティを取得する
    - _save_entity(): エンティティを保存する
    - _to_extracted_data(): 抽出結果をdictに変換する
    - _apply_extraction(): 抽出結果をエンティティに適用する
    - _get_confidence_score(): 信頼度スコアを取得する（オプション）
    - _get_metadata(): 抽出メタデータを取得する（オプション）
    """

    def __init__(
        self,
        extraction_log_repo: ExtractionLogRepository,
        session_adapter: ISessionAdapter,
    ) -> None:
        """UseCaseを初期化する。

        Args:
            extraction_log_repo: 抽出ログリポジトリ
            session_adapter: セッションアダプター（トランザクション管理用）
        """
        self._extraction_log_repo = extraction_log_repo
        self._session = session_adapter

    async def execute(
        self,
        entity_id: int,
        extraction_result: TExtractionResult,
        pipeline_version: str,
    ) -> UpdateEntityResult:
        """AI抽出結果でエンティティを更新する。

        処理フロー：
        1. 抽出ログを必ず保存（分析用）
        2. 現在のエンティティを取得
        3. ガード処理：手動検証済みなら上書きしない
        4. 未確定ならAI結果を反映

        Args:
            entity_id: 更新対象のエンティティID
            extraction_result: AI抽出結果
            pipeline_version: パイプラインバージョン（例: "gemini-2.0-flash-v1"）

        Returns:
            UpdateEntityResult: 更新結果

        Note:
            抽出ログは更新の成否に関わらず必ず保存される。
            これにより、AI精度分析とトレーサビリティが確保される。
        """
        # 1. 抽出ログを必ず保存（分析用のBronze Layer）
        log = ExtractionLog(
            entity_type=self._get_entity_type(),
            entity_id=entity_id,
            pipeline_version=pipeline_version,
            extracted_data=self._to_extracted_data(extraction_result),
            confidence_score=self._get_confidence_score(extraction_result),
            extraction_metadata=self._get_metadata(extraction_result),
        )
        created_log = await self._extraction_log_repo.create(log)
        log_id = created_log.id
        if log_id is None:
            raise ValueError("Failed to create extraction log: ID is None")

        logger.info(
            f"Extraction log saved: {self._get_entity_type().value} "
            f"entity_id={entity_id}, log_id={log_id}"
        )

        # 2. 現在のエンティティを取得
        entity = await self._get_entity(entity_id)
        if entity is None:
            logger.warning(
                f"Entity not found: {self._get_entity_type().value} id={entity_id}"
            )
            return UpdateEntityResult(
                updated=False, reason="entity_not_found", extraction_log_id=log_id
            )

        # 3. ガード処理: 人間が修正済みなら上書きしない
        if not entity.can_be_updated_by_ai():
            logger.info(
                f"Skipping update: {self._get_entity_type().value} {entity_id} "
                f"is manually verified"
            )
            return UpdateEntityResult(
                updated=False, reason="manually_verified", extraction_log_id=log_id
            )

        # 4. 未確定ならAI結果を反映
        try:
            await self._apply_extraction(entity, extraction_result, log_id)
            await self._save_entity(entity)
            await self._session.commit()

            logger.info(
                f"Successfully updated: {self._get_entity_type().value} id={entity_id}"
            )
            return UpdateEntityResult(
                updated=True, reason=None, extraction_log_id=log_id
            )
        except Exception as e:
            await self._session.rollback()
            logger.error(
                f"Failed to update entity: {self._get_entity_type().value} "
                f"id={entity_id}, error={e}"
            )
            raise

    @abstractmethod
    def _get_entity_type(self) -> EntityType:
        """エンティティタイプを返す。

        Returns:
            EntityType: このUseCaseが対象とするエンティティタイプ
        """
        ...

    @abstractmethod
    async def _get_entity(self, entity_id: int) -> TEntity | None:
        """エンティティを取得する。

        Args:
            entity_id: エンティティID

        Returns:
            エンティティ、存在しない場合はNone
        """
        ...

    @abstractmethod
    async def _save_entity(self, entity: TEntity) -> None:
        """エンティティを保存する。

        Args:
            entity: 保存するエンティティ
        """
        ...

    @abstractmethod
    def _to_extracted_data(self, result: TExtractionResult) -> dict[str, Any]:
        """抽出結果をdictに変換する。

        Args:
            result: 抽出結果

        Returns:
            抽出データのdict表現（ExtractionLogのextracted_dataフィールド用）
        """
        ...

    @abstractmethod
    async def _apply_extraction(
        self, entity: TEntity, result: TExtractionResult, log_id: int
    ) -> None:
        """抽出結果をエンティティに適用する。

        Args:
            entity: 更新対象のエンティティ
            result: 抽出結果
            log_id: 抽出ログID
        """
        ...

    def _get_confidence_score(self, result: TExtractionResult) -> float | None:
        """信頼度スコアを取得する（オプション）。

        デフォルト実装ではNoneを返す。
        サブクラスでオーバーライドして信頼度スコアを提供できる。

        Args:
            result: 抽出結果

        Returns:
            信頼度スコア（0.0〜1.0）、または取得できない場合はNone
        """
        return None

    def _get_metadata(self, result: TExtractionResult) -> dict[str, Any]:
        """抽出メタデータを取得する（オプション）。

        デフォルト実装では空のdictを返す。
        サブクラスでオーバーライドしてメタデータを提供できる。

        Args:
            result: 抽出結果

        Returns:
            抽出メタデータのdict（モデル名、トークン数、処理時間など）
        """
        return {}
