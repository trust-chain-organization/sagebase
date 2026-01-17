"""既存議事録の役職-人名マッピングをバックフィルするユースケース

Issue #947: 既存議事録への役職-人名マッピングのバックフィル

このユースケースは、既存の議事録データに対して役職-人名マッピングを
抽出・保存するバックフィル処理を提供します。
"""

from dataclasses import dataclass, field

from src.common.logging import get_logger
from src.domain.entities.minutes import Minutes
from src.domain.interfaces.minutes_divider_service import IMinutesDividerService
from src.domain.interfaces.role_name_mapping_service import IRoleNameMappingService
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.interfaces.unit_of_work import IUnitOfWork


logger = get_logger(__name__)


@dataclass
class BackfillResultDTO:
    """バックフィル結果DTO"""

    total_processed: int = 0
    success_count: int = 0
    skip_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


class BackfillRoleNameMappingsUseCase:
    """既存議事録の役職-人名マッピングをバックフィルするユースケース

    このユースケースは以下の処理を行います：
    1. 処理対象の議事録を取得
    2. 各議事録に対して役職-人名マッピングを抽出
    3. 抽出結果をデータベースに保存

    属性:
        uow: Unit of Work（トランザクション管理）
        storage_service: GCSストレージサービス
        role_name_mapping_service: 役職-人名マッピング抽出サービス
        minutes_divider_service: 議事録分割サービス（境界検出用）
    """

    def __init__(
        self,
        unit_of_work: IUnitOfWork,
        storage_service: IStorageService,
        role_name_mapping_service: IRoleNameMappingService,
        minutes_divider_service: IMinutesDividerService | None = None,
    ):
        """ユースケースを初期化する

        Args:
            unit_of_work: Unit of Work
            storage_service: ストレージサービス
            role_name_mapping_service: 役職-人名マッピング抽出サービス
            minutes_divider_service: 議事録分割サービス（境界検出用、オプション）
        """
        self.uow = unit_of_work
        self.storage_service = storage_service
        self.role_name_mapping_service = role_name_mapping_service
        self.minutes_divider_service = minutes_divider_service

    async def execute(
        self,
        meeting_id: int | None = None,
        force_reprocess: bool = False,
        limit: int | None = None,
        skip_existing: bool = True,
    ) -> BackfillResultDTO:
        """バックフィル処理を実行する

        Args:
            meeting_id: 特定の会議IDのみ処理する場合に指定
            force_reprocess: Trueの場合、既存マッピングを上書き
            limit: 処理件数の上限
            skip_existing: Trueの場合、既にマッピングがある議事録をスキップ

        Returns:
            BackfillResultDTO: バックフィル結果
        """
        result = BackfillResultDTO()

        try:
            # 処理対象の議事録を取得
            if meeting_id:
                minutes = await self.uow.minutes_repository.get_by_meeting(meeting_id)
                minutes_list = [minutes] if minutes else []
            else:
                minutes_list = await self.uow.minutes_repository.get_all(limit=limit)

            logger.info(f"取得した議事録数: {len(minutes_list)}")

            # フィルター（skip_existingの場合）
            if skip_existing and not force_reprocess:
                filtered_list = [m for m in minutes_list if not m.role_name_mappings]
                logger.info(
                    f"フィルター後の議事録数: {len(filtered_list)} "
                    f"(スキップ: {len(minutes_list) - len(filtered_list)})"
                )
                result.skip_count = len(minutes_list) - len(filtered_list)
                minutes_list = filtered_list

            # limit適用（meeting_id指定時以外）
            if limit and not meeting_id and len(minutes_list) > limit:
                minutes_list = minutes_list[:limit]

            # 各議事録を処理
            for idx, minutes in enumerate(minutes_list, 1):
                result.total_processed += 1
                logger.info(
                    f"処理中 [{idx}/{len(minutes_list)}]: "
                    f"Minutes ID={minutes.id}, Meeting ID={minutes.meeting_id}"
                )

                try:
                    success = await self._process_single_minutes(minutes)
                    if success:
                        result.success_count += 1
                        logger.info(f"Minutes ID={minutes.id}: 成功")
                    else:
                        result.skip_count += 1
                        logger.info(f"Minutes ID={minutes.id}: スキップ")

                except Exception as e:
                    result.error_count += 1
                    error_msg = f"Minutes ID={minutes.id}: {e!s}"
                    result.errors.append(error_msg)
                    logger.warning(f"処理エラー: {error_msg}")
                    # 個別エラーでも処理を継続

            # 最終コミット
            await self.uow.commit()
            logger.info(
                f"バックフィル完了: 処理={result.total_processed}, "
                f"成功={result.success_count}, "
                f"スキップ={result.skip_count}, "
                f"エラー={result.error_count}"
            )

        except Exception as e:
            logger.error(f"バックフィル処理全体でエラー: {e}", exc_info=True)
            await self.uow.rollback()
            raise

        return result

    async def _process_single_minutes(self, minutes: Minutes) -> bool:
        """単一の議事録を処理する

        Args:
            minutes: 議事録エンティティ

        Returns:
            bool: 処理成功の場合True、スキップの場合False
        """
        if minutes.id is None:
            logger.warning("Minutes IDがNullです")
            return False

        # 会議情報を取得
        meeting = await self.uow.meeting_repository.get_by_id(minutes.meeting_id)
        if not meeting:
            logger.warning(f"Meeting ID={minutes.meeting_id}が見つかりません")
            return False

        # GCSテキストURIを確認
        if not meeting.gcs_text_uri:
            logger.warning(f"Meeting ID={meeting.id}: GCSテキストURIがありません")
            return False

        # テキストを取得
        try:
            data = await self.storage_service.download_file(meeting.gcs_text_uri)
            if not data:
                logger.warning(f"Meeting ID={meeting.id}: テキストが空です")
                return False
            text = data.decode("utf-8")
            logger.debug(f"テキスト取得完了: {len(text)}文字")
        except Exception as e:
            logger.warning(f"GCSからのテキスト取得エラー: {e}")
            return False

        # 境界検出で出席者部分を抽出
        attendee_text = text
        if self.minutes_divider_service:
            try:
                boundary = await self.minutes_divider_service.detect_attendee_boundary(
                    text
                )
                if boundary.boundary_found and boundary.boundary_text:
                    attendee_text, _ = (
                        self.minutes_divider_service.split_minutes_by_boundary(
                            text, boundary
                        )
                    )
                    logger.debug(f"出席者セクション抽出: {len(attendee_text)}文字")
            except Exception as e:
                logger.warning(f"境界検出エラー（テキスト全体を使用）: {e}")

        # 役職-人名マッピングを抽出
        mapping_result = await self.role_name_mapping_service.extract_role_name_mapping(
            attendee_text
        )

        if not mapping_result.mappings:
            logger.info(f"Minutes ID={minutes.id}: マッピングが抽出されませんでした")
            return False

        mappings_dict = mapping_result.to_dict()
        logger.info(
            f"Minutes ID={minutes.id}: {len(mappings_dict)}件のマッピングを抽出 "
            f"(信頼度: {mapping_result.confidence})"
        )

        # マッピング内容をログ出力
        for role, name in mappings_dict.items():
            logger.debug(f"  {role} → {name}")

        # データベースを更新
        updated = await self.uow.minutes_repository.update_role_name_mappings(
            minutes.id, mappings_dict
        )

        if updated:
            await self.uow.flush()
            return True
        else:
            logger.warning(f"Minutes ID={minutes.id}: 更新に失敗しました")
            return False
