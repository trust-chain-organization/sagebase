"""抽出ログPresenter for Streamlit web interface."""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.extraction_log import EntityType, ExtractionLog
from src.infrastructure.persistence.extraction_log_repository_impl import (
    ExtractionLogRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import WebResponseDTO
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ExtractionLogPresenter(BasePresenter[list[ExtractionLog]]):
    """抽出ログ管理用Presenter。"""

    def __init__(self, container: Any = None):
        """Presenterを初期化する。

        Args:
            container: 依存性注入コンテナ
        """
        super().__init__(container)
        self.extraction_log_repo = RepositoryAdapter(ExtractionLogRepositoryImpl)
        self.session = SessionManager(namespace="extraction_logs")
        self.logger = get_logger(self.__class__.__name__)

    def load_data(self) -> list[ExtractionLog]:
        """全ての抽出ログを読み込む。

        Returns:
            抽出ログのリスト
        """
        return self.extraction_log_repo.get_all()

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """ユーザーアクションを処理する。

        Args:
            action: 実行するアクション
            **kwargs: アクションの追加パラメータ

        Returns:
            アクションの結果
        """
        if action == "search":
            return self.search_logs(**kwargs)
        elif action == "get_statistics":
            return self.get_statistics(**kwargs)
        elif action == "export_csv":
            return self.export_to_csv(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_logs(
        self,
        entity_type: str | None = None,
        entity_id: int | None = None,
        pipeline_version: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_confidence_score: float | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> WebResponseDTO[dict[str, Any]]:
        """抽出ログを検索する。

        Args:
            entity_type: エンティティタイプフィルタ
            entity_id: エンティティIDフィルタ
            pipeline_version: パイプラインバージョンフィルタ
            start_date: 開始日フィルタ
            end_date: 終了日フィルタ
            min_confidence_score: 最小信頼度スコアフィルタ
            limit: ページあたりの件数
            offset: オフセット

        Returns:
            検索結果とメタデータを含むレスポンス
        """
        try:
            # 文字列フィルタをEnum/Noneに変換
            entity_type_enum = (
                EntityType(entity_type)
                if entity_type and entity_type != "すべて"
                else None
            )
            pipeline = None if pipeline_version == "すべて" else pipeline_version

            # ログを検索
            logs = self.extraction_log_repo.search_with_date_range(
                entity_type=entity_type_enum,
                entity_id=entity_id,
                pipeline_version=pipeline,
                min_confidence_score=min_confidence_score,
                date_from=start_date,
                date_to=end_date,
                limit=limit,
                offset=offset,
            )

            # 総件数を取得
            total_count = self.extraction_log_repo.count_with_filters(
                entity_type=entity_type_enum,
                entity_id=entity_id,
                pipeline_version=pipeline,
                min_confidence_score=min_confidence_score,
                date_from=start_date,
                date_to=end_date,
            )

            return WebResponseDTO.success_response(
                data={
                    "logs": logs,
                    "total_count": total_count,
                    "page_size": limit,
                    "current_offset": offset,
                }
            )

        except Exception as e:
            self.logger.error(f"Error searching logs: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"ログの検索に失敗しました: {str(e)}")

    def get_statistics(
        self,
        entity_type: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> WebResponseDTO[dict[str, Any]]:
        """抽出統計情報を取得する。

        Args:
            entity_type: エンティティタイプフィルタ
            start_date: 開始日フィルタ
            end_date: 終了日フィルタ

        Returns:
            統計データを含むレスポンス
        """
        try:
            # デフォルトの日付範囲（過去30日）
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()

            # 文字列フィルタをEnum/Noneに変換
            entity_type_enum = (
                EntityType(entity_type)
                if entity_type and entity_type != "すべて"
                else None
            )

            # 総件数
            total_count = self.extraction_log_repo.count_with_filters(
                entity_type=entity_type_enum,
                date_from=start_date,
                date_to=end_date,
            )

            # エンティティタイプ別件数
            by_entity_type: dict[str, int] = {}
            for et in EntityType:
                count = self.extraction_log_repo.count_with_filters(
                    entity_type=et,
                    date_from=start_date,
                    date_to=end_date,
                )
                if count > 0:
                    by_entity_type[et.value] = count

            # パイプラインバージョン一覧取得
            pipeline_versions = (
                self.extraction_log_repo.get_distinct_pipeline_versions()
            )

            # パイプラインバージョン別件数と平均信頼度
            by_pipeline_version: dict[str, int] = {}
            confidence_by_pipeline: dict[str, float] = {}

            for version in pipeline_versions:
                count = self.extraction_log_repo.count_with_filters(
                    entity_type=entity_type_enum,
                    pipeline_version=version,
                    date_from=start_date,
                    date_to=end_date,
                )
                if count > 0:
                    by_pipeline_version[version] = count

                    # パイプラインバージョン別平均信頼度
                    avg_confidence = (
                        self.extraction_log_repo.get_average_confidence_score(
                            entity_type=entity_type_enum,
                            pipeline_version=version,
                        )
                    )
                    if avg_confidence is not None:
                        confidence_by_pipeline[version] = round(avg_confidence, 3)

            # 全体平均信頼度
            average_confidence = self.extraction_log_repo.get_average_confidence_score(
                entity_type=entity_type_enum,
            )

            # 日別件数
            daily_counts_raw = self.extraction_log_repo.get_count_by_date(
                entity_type=entity_type_enum,
                date_from=start_date,
                date_to=end_date,
            )
            daily_counts = [
                {"date": dt.strftime("%Y-%m-%d"), "count": count}
                for dt, count in daily_counts_raw
            ]

            return WebResponseDTO.success_response(
                data={
                    "total_count": total_count,
                    "by_entity_type": by_entity_type,
                    "by_pipeline_version": by_pipeline_version,
                    "average_confidence": round(average_confidence, 3)
                    if average_confidence
                    else None,
                    "daily_counts": daily_counts,
                    "confidence_by_pipeline": confidence_by_pipeline,
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                }
            )

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"統計情報の取得に失敗しました: {str(e)}"
            )

    def export_to_csv(self, logs: list[ExtractionLog]) -> str:
        """ログをCSV形式でエクスポートする。

        Args:
            logs: エクスポートするログのリスト

        Returns:
            CSVデータの文字列
        """
        if not logs:
            return ""

        # DataFrameに変換
        data = []
        for log in logs:
            data.append(
                {
                    "ID": log.id,
                    "エンティティタイプ": log.entity_type.value,
                    "エンティティID": log.entity_id,
                    "パイプラインバージョン": log.pipeline_version,
                    "信頼度スコア": log.confidence_score,
                    "作成日時": (
                        log.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if log.created_at
                        else ""
                    ),
                    "モデル名": log.model_name or "",
                    "入力トークン数": log.token_count_input or "",
                    "出力トークン数": log.token_count_output or "",
                    "処理時間(ms)": log.processing_time_ms or "",
                }
            )

        df = pd.DataFrame(data)
        return df.to_csv(index=False, encoding="utf-8-sig")

    def get_entity_types(self) -> list[str]:
        """全エンティティタイプオプションを取得する。

        Returns:
            'すべて'を含むエンティティタイプ値のリスト
        """
        return ["すべて"] + [et.value for et in EntityType]

    def get_pipeline_versions(self) -> list[str]:
        """登録されているパイプラインバージョンを取得する。

        Returns:
            'すべて'を含むパイプラインバージョンのリスト
        """
        try:
            versions = self.extraction_log_repo.get_distinct_pipeline_versions()
            return ["すべて"] + list(versions)
        except Exception as e:
            self.logger.error(f"Error getting pipeline versions: {e}")
            return ["すべて"]

    def get_log_detail(self, log_id: int) -> WebResponseDTO[dict[str, Any]]:
        """特定のログの詳細情報を取得する。

        Args:
            log_id: 取得するログのID

        Returns:
            ログ詳細を含むレスポンス
        """
        try:
            log = self.extraction_log_repo.get_by_id(log_id)
            if not log:
                return WebResponseDTO.error_response(
                    f"ログID {log_id} が見つかりません"
                )

            # 詳細データをフォーマット
            detail_data = {
                "id": log.id,
                "entity_type": log.entity_type.value,
                "entity_id": log.entity_id,
                "pipeline_version": log.pipeline_version,
                "confidence_score": log.confidence_score,
                "extracted_data": log.extracted_data,
                "extraction_metadata": log.extraction_metadata,
                "created_at": log.created_at,
                "updated_at": log.updated_at,
            }

            return WebResponseDTO.success_response(detail_data)

        except Exception as e:
            self.logger.error(f"Error getting log detail: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"ログ詳細の取得に失敗しました: {str(e)}"
            )

    def get_entity_history(
        self, entity_type: str, entity_id: int
    ) -> WebResponseDTO[dict[str, Any]]:
        """特定エンティティの抽出履歴を取得する。

        Args:
            entity_type: エンティティタイプ
            entity_id: エンティティID

        Returns:
            抽出履歴を含むレスポンス
        """
        try:
            entity_type_enum = EntityType(entity_type)
            logs = self.extraction_log_repo.get_by_entity(
                entity_type=entity_type_enum,
                entity_id=entity_id,
            )

            return WebResponseDTO.success_response(
                data={
                    "logs": logs,
                    "total_count": len(logs),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                }
            )

        except Exception as e:
            self.logger.error(f"Error getting entity history: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"エンティティ履歴の取得に失敗しました: {str(e)}"
            )
