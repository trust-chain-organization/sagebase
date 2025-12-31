"""抽出ログリポジトリインターフェース。"""

from abc import abstractmethod

from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.domain.repositories.base import BaseRepository


class ExtractionLogRepository(BaseRepository[ExtractionLog]):
    """抽出ログのリポジトリインターフェース。

    全エンティティタイプのLLM抽出結果を統一的に管理するリポジトリ。
    """

    @abstractmethod
    async def get_by_entity(
        self,
        entity_type: EntityType,
        entity_id: int,
    ) -> list[ExtractionLog]:
        """特定のエンティティに対する全抽出ログを取得する。

        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID

        Returns:
            抽出ログのリスト（作成日時の降順）
        """
        pass

    @abstractmethod
    async def get_by_pipeline_version(
        self,
        version: str,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """特定のパイプラインバージョンによる抽出ログを取得する。

        Args:
            version: パイプラインバージョン
            limit: 取得件数の上限
            offset: 取得開始位置

        Returns:
            抽出ログのリスト（作成日時の降順）
        """
        pass

    @abstractmethod
    async def get_by_entity_type(
        self,
        entity_type: EntityType,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """特定のエンティティタイプの抽出ログを取得する。

        Args:
            entity_type: エンティティタイプ
            limit: 取得件数の上限
            offset: 取得開始位置

        Returns:
            抽出ログのリスト（作成日時の降順）
        """
        pass

    @abstractmethod
    async def get_latest_by_entity(
        self,
        entity_type: EntityType,
        entity_id: int,
    ) -> ExtractionLog | None:
        """特定のエンティティに対する最新の抽出ログを取得する。

        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID

        Returns:
            最新の抽出ログ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def search(
        self,
        entity_type: EntityType | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """複数の条件で抽出ログを検索する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            limit: 取得件数の上限
            offset: 取得開始位置

        Returns:
            抽出ログのリスト（作成日時の降順）
        """
        pass

    @abstractmethod
    async def count_by_entity_type(
        self,
        entity_type: EntityType,
    ) -> int:
        """特定のエンティティタイプのログ件数を取得する。

        Args:
            entity_type: エンティティタイプ

        Returns:
            ログ件数
        """
        pass

    @abstractmethod
    async def count_by_pipeline_version(
        self,
        version: str,
    ) -> int:
        """特定のパイプラインバージョンのログ件数を取得する。

        Args:
            version: パイプラインバージョン

        Returns:
            ログ件数
        """
        pass
