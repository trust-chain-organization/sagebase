"""抽出ログリポジトリインターフェース。"""

from abc import abstractmethod
from datetime import datetime

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

    @abstractmethod
    async def search_with_date_range(
        self,
        entity_type: EntityType | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ExtractionLog]:
        """日時範囲を含む複数の条件で抽出ログを検索する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            entity_id: エンティティID（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）
            limit: 取得件数の上限
            offset: 取得開始位置

        Returns:
            抽出ログのリスト（作成日時の降順）
        """
        pass

    @abstractmethod
    async def count_with_filters(
        self,
        entity_type: EntityType | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        min_confidence_score: float | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """フィルター条件に一致するログ件数を取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            entity_id: エンティティID（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）
            min_confidence_score: 最小信頼度スコア（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            ログ件数
        """
        pass

    @abstractmethod
    async def get_distinct_pipeline_versions(self) -> list[str]:
        """登録されている全てのパイプラインバージョンを取得する。

        Returns:
            パイプラインバージョンのリスト（重複なし）
        """
        pass

    @abstractmethod
    async def get_total_count(self) -> int:
        """全ての抽出ログ件数を取得する。

        Returns:
            総ログ件数
        """
        pass

    @abstractmethod
    async def get_average_confidence_score(
        self,
        entity_type: EntityType | None = None,
        pipeline_version: str | None = None,
    ) -> float | None:
        """平均信頼度スコアを取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            pipeline_version: パイプラインバージョン（フィルタ）

        Returns:
            平均信頼度スコア、データがない場合はNone
        """
        pass

    @abstractmethod
    async def get_count_by_date(
        self,
        entity_type: EntityType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[tuple[datetime, int]]:
        """日別の抽出ログ件数を取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            (日付, 件数)のタプルのリスト
        """
        pass

    @abstractmethod
    async def get_count_grouped_by_entity_type(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[EntityType, int]:
        """エンティティタイプ別の件数を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            エンティティタイプをキー、件数を値とする辞書
        """
        pass

    @abstractmethod
    async def get_count_grouped_by_pipeline_version(
        self,
        entity_type: EntityType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, int]:
        """パイプラインバージョン別の件数を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）
            date_from: 検索開始日時（フィルタ）
            date_to: 検索終了日時（フィルタ）

        Returns:
            パイプラインバージョンをキー、件数を値とする辞書
        """
        pass

    @abstractmethod
    async def get_avg_confidence_grouped_by_pipeline_version(
        self,
        entity_type: EntityType | None = None,
    ) -> dict[str, float]:
        """パイプラインバージョン別の平均信頼度を一括取得する。

        N+1クエリを避けるため、GROUP BYで一括取得する。

        Args:
            entity_type: エンティティタイプ（フィルタ）

        Returns:
            パイプラインバージョンをキー、平均信頼度を値とする辞書
        """
        pass
