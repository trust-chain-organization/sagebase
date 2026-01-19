"""BAML-based MinutesDivider

このモジュールは、BAMLを使用して議事録分割処理を行います。
既存のPydantic実装と並行して動作し、フィーチャーフラグで切り替え可能です。
"""

import logging
import re
import unicodedata

from typing import Any

from baml_py.errors import BamlValidationError

from baml_client.async_client import b

from src.domain.exceptions import ExternalServiceException
from src.domain.interfaces.minutes_divider_service import IMinutesDividerService

# 既存のPydanticモデルを使用（BAML結果をこれに変換）
from src.minutes_divide_processor.models import (
    AttendeesMapping,
    MinutesBoundary,
    RedividedSectionInfo,
    RedividedSectionInfoList,
    RedivideSectionString,
    RedivideSectionStringList,
    SectionInfo,
    SectionInfoList,
    SectionString,
    SectionStringList,
    SpeakerAndSpeechContent,
    SpeakerAndSpeechContentList,
)


logger = logging.getLogger(__name__)


class BAMLMinutesDivider(IMinutesDividerService):
    """BAML-based MinutesDivider

    BAMLを使用して議事録分割処理を行うクラス。
    既存のMinutesDividerと同じインターフェースを持ち、
    トークン効率とパース精度の向上を目指します。
    """

    def __init__(
        self,
        llm_service: Any | None = None,  # BAML使用時は不要だが互換性のため
        k: int = 5,
    ):
        """
        Initialize BAMLMinutesDivider

        Args:
            llm_service: 互換性のためのパラメータ（BAML使用時は不要）
            k: Number of sections (default 5)
        """
        self.k = k
        logger.info("BAMLMinutesDivider initialized")

    # ========================================
    # LLM不使用メソッド（既存実装をコピー）
    # ========================================

    def pre_process(self, original_minutes: str) -> str:
        """議事録の文字列に対する前処理を行う

        Args:
            original_minutes: 元の議事録

        Returns:
            前処理された議事録
        """
        # 議事録の改行とスペースを削除します
        processed_minutes = original_minutes.replace("\r\n", "\n")  # Windows改行を統一
        processed_minutes = processed_minutes.replace("（", "(").replace(
            "）", ")"
        )  # 丸括弧を半角に統一
        # 全角スペースを半角スペースに統一
        processed_minutes = re.sub(r"[　]", " ", processed_minutes)
        # 連続するスペースを1つのスペースに置換し、前後の空白を削除
        processed_minutes = re.sub(r"[ ]+", " ", processed_minutes).strip()
        # 制御文字を削除
        processed_minutes = "".join(
            ch for ch in processed_minutes if unicodedata.category(ch)[0] != "C"
        )
        # 区切り記号を削除
        processed_minutes = "".join(
            ch for ch in processed_minutes if unicodedata.category(ch)[0] != "Z"
        )
        return processed_minutes

    def do_divide(
        self,
        processed_minutes: str,
        section_info_list: SectionInfoList | list[Any],
    ) -> SectionStringList:
        """議事録を実際に分割する

        Args:
            processed_minutes: 前処理された議事録
            section_info_list: セクション情報リスト

        Returns:
            分割されたセクション文字列リスト
        """
        if not processed_minutes:
            return SectionStringList(section_string_list=[])

        # JSON文字列をPythonのリストに変換
        if isinstance(section_info_list, str):
            import json

            section_info_list = json.loads(section_info_list)

        # section_info_listがすでにリストの場合はそのまま使用
        if isinstance(section_info_list, list):
            section_info_list_data = section_info_list
        else:
            section_info_list_data = section_info_list.section_info_list

        # Unicode正規化（NFKC）と追加の正規化を適用
        def normalize_text(text: str) -> str:
            """テキストを正規化する関数"""
            # NFKC正規化
            normalized = unicodedata.normalize("NFKC", text)
            # 議事録特有の記号の正規化
            normalized = normalized.replace("◯", "○")
            normalized = normalized.replace("●", "○")
            # タブ文字をスペースに変換
            normalized = normalized.replace("\t", " ")
            # 連続するスペースを1つに統一
            normalized = re.sub(r" +", " ", normalized)
            return normalized

        # 議事録全体を正規化
        normalized_minutes = normalize_text(processed_minutes)

        split_minutes_list: list[SectionString] = []
        start_index = 0
        skipped_keywords: list[str] = []
        i = 0
        output_order = 1  # 出現順を記録する変数

        while i < len(section_info_list_data):
            section_info = section_info_list_data[i]
            # キーワードも同様に正規化
            keyword = normalize_text(section_info.keyword)

            # 最初のキーワードの場合、議事録の先頭から検索を開始
            if i == 0 and start_index == 0:
                start_index = normalized_minutes.find(keyword)
                if start_index == -1:
                    # 部分一致も試す（キーワードが長すぎる場合）
                    if len(keyword) > 10:
                        partial_keyword = keyword[:10]
                        start_index = normalized_minutes.find(partial_keyword)
                        if start_index != -1:
                            logger.info(
                                f"Found keyword using partial match: {partial_keyword}"
                            )

                    if start_index == -1:
                        start_index = 0
                        logger.warning(
                            f"キーワード '{section_info.keyword}' が"
                            "見つからないため、先頭から開始します"
                        )
            # キーワードが見つからない場合はスキップ
            if start_index == -1:
                logger.warning(
                    f"キーワード '{section_info.keyword}' が"
                    "見つかりません。スキップします。"
                )
                skipped_keywords.append(section_info.keyword)
                i += 1
                continue
            # 次のキーワードの開始位置を検索
            next_keyword_index = -1
            j = i + 1
            while j < len(section_info_list_data):
                next_section = section_info_list_data[j]
                # 次のキーワードも正規化
                next_keyword = normalize_text(next_section.keyword)
                next_keyword_index = normalized_minutes.find(
                    next_keyword, start_index + 1
                )
                if next_keyword_index == -1 and len(next_keyword) > 10:
                    # 部分一致も試す
                    partial_next = next_keyword[:10]
                    next_keyword_index = normalized_minutes.find(
                        partial_next, start_index + 1
                    )
                    if next_keyword_index != -1:
                        logger.info(
                            f"Found next keyword using partial match: {partial_next}"
                        )

                if next_keyword_index != -1:
                    break
                else:
                    logger.warning(
                        f"キーワード '{next_section.keyword}' が議事録に"
                        "見つかりません。スキップします。"
                    )
                    skipped_keywords.append(next_section.keyword)
                    j += 1
            if next_keyword_index == -1:
                end_index = len(normalized_minutes)
            else:
                end_index = next_keyword_index
            # 分割された文字列を取得（元のテキストから取得）
            split_text = processed_minutes[start_index:end_index].strip()
            # SectionStringインスタンスを作成してlistにappend
            split_minutes_list.append(
                SectionString(
                    chapter_number=section_info.chapter_number,
                    sub_chapter_number=1,
                    section_string=split_text,
                )
            )
            # 次の検索開始位置を更新
            start_index = end_index
            # インデックスと出現順を更新
            i = j
            output_order += 1
        return SectionStringList(section_string_list=split_minutes_list)

    def check_length(
        self, section_string_list: SectionStringList
    ) -> RedivideSectionStringList:
        """セクションの長さをチェックし、長すぎるセクションを特定する

        Args:
            section_string_list: セクション文字列リスト

        Returns:
            再分割が必要なセクションのリスト
        """
        redivide_list: list[RedivideSectionString] = []
        for index, section_string in enumerate(section_string_list.section_string_list):
            size_in_bytes = len(section_string.section_string.encode("utf-8"))
            logger.debug(f"size_in_bytes: {size_in_bytes}")
            if size_in_bytes > 6000:  # 6000文字より多いか確認
                logger.info(
                    "section_stringの文字数が6000文字を超えています。再分割します。"
                )
                redivide_dict = RedivideSectionString(
                    original_index=index,
                    redivide_section_string_bytes=size_in_bytes,
                    redivide_section_string=section_string,
                )
                redivide_list.append(redivide_dict)
        return RedivideSectionStringList(redivide_section_string_list=redivide_list)

    def split_minutes_by_boundary(
        self, minutes_text: str, boundary: MinutesBoundary
    ) -> tuple[str, str]:
        """境界情報に基づいて議事録を出席者部分と発言部分に分割する

        Args:
            minutes_text: 議事録の全文
            boundary: 境界検出結果

        Returns:
            Tuple[str, str]: (出席者部分, 発言部分)
        """
        logger.info("=== split_minutes_by_boundary started ===")

        if not boundary.boundary_found or not boundary.boundary_text:
            # 境界が見つからない場合は全体を発言部分として扱う
            logger.info("No boundary found, treating entire text as speech")
            return "", minutes_text

        # boundary_textから境界マーカーを探す（複数のパターンに対応）
        boundary_markers = ["｜境界｜", "|境界|", "境界", "｜", "|"]
        boundary_marker = None
        for marker in boundary_markers:
            if marker in boundary.boundary_text:
                boundary_marker = marker
                break

        logger.info("Looking for boundary marker in boundary_text")
        logger.info(f"boundary_text content: {repr(boundary.boundary_text)}")

        if boundary_marker:
            logger.info(f"Found boundary marker: '{boundary_marker}'")
            # 境界マーカーの前後のテキストを取得
            parts = boundary.boundary_text.split(boundary_marker)
            if len(parts) >= 2:
                before_boundary = parts[0].strip()
                after_boundary = parts[-1].strip()
            else:
                logger.warning(f"Could not split by marker: {boundary.boundary_text}")
                before_boundary = ""
                after_boundary = boundary.boundary_text.strip()
        else:
            logger.warning(
                f"No boundary marker found in boundary_text: {boundary.boundary_text}"
            )
            before_boundary = ""
            after_boundary = boundary.boundary_text.strip()

        logger.info(f"Before boundary text: {repr(before_boundary)}")
        logger.info(f"After boundary text: {repr(after_boundary)}")

        # 元のテキストから境界位置を特定
        split_index = -1

        # まず境界前のテキストを探す
        if before_boundary and len(before_boundary) > 5:
            search_patterns = [
                before_boundary,
                before_boundary.replace("\\n", "\n"),
                before_boundary.replace("\n", " "),
                before_boundary.replace("\n", ""),
            ]

            for pattern in search_patterns:
                if pattern in minutes_text:
                    before_index = minutes_text.find(pattern)
                    split_index = before_index + len(pattern)
                    logger.info(
                        f"Found boundary using before_text at index {split_index}"
                    )
                    break

        # 境界前で見つからない場合は境界後のテキストで探す
        if split_index == -1 and after_boundary and len(after_boundary) > 5:
            search_patterns = [
                after_boundary,
                after_boundary.replace("\\n", "\n"),
                after_boundary.replace("\n", " "),
                after_boundary.replace("\n", ""),
            ]

            for pattern in search_patterns:
                if pattern in minutes_text:
                    split_index = minutes_text.find(pattern)
                    logger.info(
                        f"Found boundary using after_text at index {split_index}"
                    )
                    break

        # それでも見つからない場合、部分一致を試みる
        if split_index == -1:
            logger.warning("Could not find exact match, trying partial match")

            if after_boundary and len(after_boundary) > 10:
                partial = after_boundary[:10]
                if partial in minutes_text:
                    split_index = minutes_text.find(partial)
                    logger.info(
                        f"Found boundary using partial text at index {split_index}"
                    )

            # それでも見つからない場合、発言パターンを探す
            if split_index == -1:
                speech_patterns = [
                    r"○.*?議長",
                    r"◆.*?議員",
                    r"［.*?開会］",
                    r"【.*?】",
                    r"○委員長",
                    r"◆委員",
                ]

                for pattern in speech_patterns:
                    match = re.search(pattern, minutes_text)
                    if match:
                        split_index = match.start()
                        logger.info(
                            f"Found boundary using pattern '{pattern}' at {split_index}"
                        )
                        break

        if split_index == -1:
            logger.warning("Could not locate boundary in original text")
            return "", minutes_text

        # 境界位置の妥当性を検証
        text_length = len(minutes_text)
        remaining_length = text_length - split_index

        if remaining_length < 100 and remaining_length < text_length * 0.2:
            logger.warning(
                f"Boundary is too close to the end of text "
                f"(remaining: {remaining_length} chars). "
                f"Treating entire text as speech content."
            )
            return "", minutes_text

        # テキストを分割
        attendee_part = minutes_text[:split_index].strip()
        speech_part = minutes_text[split_index:].strip()

        logger.info(f"Split successful at index {split_index}")
        logger.info(f"Attendee part length: {len(attendee_part)}")
        logger.info(f"Speech part length: {len(speech_part)}")

        return attendee_part, speech_part

    # ========================================
    # BAML使用メソッド
    # ========================================

    async def section_divide_run(self, minutes: str) -> SectionInfoList:
        """議事録を章に分割する（BAML使用）

        Args:
            minutes: 議事録

        Returns:
            セクション情報リスト

        Raises:
            ExternalServiceException: BAML呼び出しエラー（BamlValidationError以外）
        """
        try:
            # BAMLを呼び出し
            logger.info("Calling BAML DivideMinutesToKeywords")
            baml_result = await b.DivideMinutesToKeywords(minutes)

            # BAML結果をPydanticモデルに変換
            section_info_list = [
                SectionInfo(chapter_number=item.chapter_number, keyword=item.keyword)
                for item in baml_result
            ]

            # chapter_numberが連番になっているか確認して修正
            last_chapter_number = 0
            for section_info in section_info_list:
                if section_info.chapter_number != last_chapter_number + 1:
                    logger.warning(
                        "section_infoのchapter_numberが連番になっていません。"
                    )
                    section_info.chapter_number = last_chapter_number + 1
                last_chapter_number = section_info.chapter_number

            logger.info(f"BAML returned {len(section_info_list)} sections")
            return SectionInfoList(section_info_list=section_info_list)

        except BamlValidationError as e:
            # LLMが構造化出力を返さなかった場合（許容される状況）
            logger.warning(
                f"BAML section_divide_run バリデーション失敗: {e}. "
                "空のリストを返します。"
            )
            return SectionInfoList(section_info_list=[])
        except Exception as e:
            logger.error(f"BAML section_divide_run failed: {e}", exc_info=True)
            raise ExternalServiceException(
                service_name="BAML",
                operation="section_divide_run",
                reason=str(e),
            ) from e

    async def do_redivide(
        self, redivide_section_string_list: RedivideSectionStringList
    ) -> RedividedSectionInfoList:
        """長いセクションを再分割する（BAML使用）

        Args:
            redivide_section_string_list: 再分割対象のセクションリスト

        Returns:
            再分割されたセクション情報リスト

        Note:
            個別のセクション処理でエラーが発生した場合はそのセクションをスキップして続行します。
            BamlValidationErrorはLLM出力の構造化失敗を示し、その他のエラーもログ出力後にスキップします。
        """
        section_info_list: list[Any] = []
        errors_occurred: list[tuple[int, str]] = []

        for (
            redivide_section_string
        ) in redivide_section_string_list.redivide_section_string_list:
            divide_counter = (
                redivide_section_string.redivide_section_string_bytes // 20000000
            )
            divide_counter = divide_counter + 2

            try:
                # BAMLを呼び出し
                logger.info(
                    f"Calling BAML RedivideSection "
                    f"(divide_counter={divide_counter}, "
                    f"original_index={redivide_section_string.original_index})"
                )
                baml_result = await b.RedivideSection(
                    redivide_section_string.redivide_section_string.section_string,
                    divide_counter,
                    redivide_section_string.original_index,
                )

                # BAML結果をPydanticモデルに変換してリストに追加
                for item in baml_result:
                    section_info_list.append(
                        RedividedSectionInfo(
                            chapter_number=item.chapter_number,
                            # BAMLでは設定されないのでデフォルト値
                            sub_chapter_number=1,
                            keyword=item.keyword,
                        )
                    )
                logger.info(f"BAML returned {len(baml_result)} redivided sections")

            except BamlValidationError as e:
                # LLMが構造化出力を返さなかった場合（スキップして続行）
                logger.warning(
                    f"BAML do_redivide バリデーション失敗 "
                    f"(original_index={redivide_section_string.original_index}): {e}. "
                    "スキップして続行します。"
                )
                errors_occurred.append(
                    (
                        redivide_section_string.original_index,
                        f"BamlValidationError: {e}",
                    )
                )
            except Exception as e:
                logger.error(
                    f"BAML do_redivide failed "
                    f"(original_index={redivide_section_string.original_index}): {e}",
                    exc_info=True,
                )
                errors_occurred.append((redivide_section_string.original_index, str(e)))

        if errors_occurred:
            logger.warning(
                f"do_redivide completed with {len(errors_occurred)} errors: "
                f"{errors_occurred}"
            )

        return RedividedSectionInfoList(redivided_section_info_list=section_info_list)

    async def detect_attendee_boundary(self, minutes_text: str) -> MinutesBoundary:
        """出席者情報と発言部分の境界を検出する（BAML使用）

        Args:
            minutes_text: 議事録の全文

        Returns:
            境界検出結果

        Note:
            BamlValidationErrorの場合は境界なし結果を返します。
            その他のエラーの場合もフォールバックとして境界なし結果を返しますが、
            エラー情報をreasonフィールドに含めます。
        """
        logger.info("=== detect_attendee_boundary started ===")
        logger.info(f"Input text length: {len(minutes_text)}")

        try:
            # BAMLを呼び出し
            logger.info("Calling BAML DetectBoundary")
            baml_result = await b.DetectBoundary(minutes_text)

            # BAML結果をPydanticモデルに変換
            result = MinutesBoundary(
                boundary_found=baml_result.boundary_found,
                boundary_text=baml_result.boundary_text,
                boundary_type=baml_result.boundary_type,  # type: ignore[arg-type]
                confidence=baml_result.confidence,
                reason=baml_result.reason,
            )

            logger.info("Boundary detection result details:")
            logger.info(f"  - boundary_found: {result.boundary_found}")
            logger.info(f"  - boundary_type: {result.boundary_type}")
            logger.info(f"  - confidence: {result.confidence}")
            logger.info(f"  - reason: {result.reason}")

            return result

        except BamlValidationError as e:
            # LLMが構造化出力を返さなかった場合
            logger.warning(
                f"BAML detect_attendee_boundary バリデーション失敗: {e}. "
                "境界なし結果を返します。"
            )
            return MinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.0,
                reason=f"LLMが構造化出力を返せませんでした: {e}",
            )
        except Exception as e:
            logger.error(f"BAML detect_attendee_boundary failed: {e}", exc_info=True)
            return MinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.0,
                reason=f"境界検出中にエラーが発生しました: {str(e)}",
            )

    async def extract_attendees_mapping(self, attendees_text: str) -> AttendeesMapping:
        """出席者情報から役職と人名のマッピングを抽出する（BAML使用）

        Args:
            attendees_text: 出席者情報のテキスト

        Returns:
            役職と人名のマッピング

        Note:
            BamlValidationErrorの場合は空のマッピングを返します。
            その他のエラーの場合も空のマッピングを返します。
        """
        logger.info("=== extract_attendees_mapping started ===")
        logger.info(f"Attendees text length: {len(attendees_text)}")

        if not attendees_text:
            logger.warning("No attendees text provided")
            return AttendeesMapping(
                attendees_mapping={}, regular_attendees=[], confidence=0.0
            )

        try:
            # BAMLを呼び出し
            logger.info("Calling BAML ExtractAttendees")
            baml_result = await b.ExtractAttendees(attendees_text)

            # BAML結果をPydanticモデルに変換
            result = AttendeesMapping(
                attendees_mapping=baml_result.attendees_mapping or {},
                regular_attendees=baml_result.regular_attendees,
                confidence=baml_result.confidence,
            )

            logger.info("Attendees mapping extraction result:")
            mapping_count = (
                len(result.attendees_mapping) if result.attendees_mapping else 0
            )
            logger.info(f"  - Role mappings: {mapping_count}")
            logger.info(f"  - Regular attendees: {len(result.regular_attendees)}")
            logger.info(f"  - Confidence: {result.confidence}")

            return result

        except BamlValidationError as e:
            # LLMが構造化出力を返さなかった場合
            logger.warning(
                f"BAML extract_attendees_mapping バリデーション失敗: {e}. "
                "空のマッピングを返します。"
            )
            return AttendeesMapping(
                attendees_mapping={}, regular_attendees=[], confidence=0.0
            )
        except Exception as e:
            logger.error(f"BAML extract_attendees_mapping failed: {e}", exc_info=True)
            return AttendeesMapping(
                attendees_mapping={}, regular_attendees=[], confidence=0.0
            )

    async def speech_divide_run(
        self, section_string: SectionString
    ) -> SpeakerAndSpeechContentList:
        """発言者と発言内容に分割する（BAML使用）

        セクション全体を直接DivideSpeechに渡す。
        発言者マーカー（○議長（名前）など）はDivideSpeechプロンプトで認識される。

        Args:
            section_string: セクション文字列

        Returns:
            発言者と発言内容のリスト

        Raises:
            ExternalServiceException: BAML呼び出しエラー（BamlValidationError以外）
        """
        section_text = section_string.section_string

        # 発言パターンが含まれているかチェック
        # ○◆◎●などの記号で始まる発言者マーカーがあるか確認
        has_speech_pattern = bool(re.search(r"[○◆◎●]", section_text))

        if len(section_text) < 30 and not has_speech_pattern:
            logger.debug("セクションが短く発言パターンもないためスキップ")
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])

        try:
            # BAMLを呼び出し（セクション全体を渡す）
            baml_result = await b.DivideSpeech(section_text)

            # BAML結果をPydanticモデルに変換
            speaker_and_speech_content_list = [
                SpeakerAndSpeechContent(
                    speaker=item.speaker,
                    speech_content=item.speech_content,
                    chapter_number=item.chapter_number,
                    sub_chapter_number=item.sub_chapter_number,
                    speech_order=item.speech_order,
                )
                for item in baml_result
            ]

            # speech_orderが連番になっているか確認して修正
            last_speech_order = 0
            for speaker_and_speech_content in speaker_and_speech_content_list:
                if speaker_and_speech_content.speech_order != last_speech_order + 1:
                    logger.warning(
                        "speaker_and_speech_contentのspeech_orderが連番になっていません。"
                    )
                    speaker_and_speech_content.speech_order = last_speech_order + 1
                last_speech_order = speaker_and_speech_content.speech_order

            logger.info(
                f"BAML returned {len(speaker_and_speech_content_list)} speeches"
            )
            return SpeakerAndSpeechContentList(
                speaker_and_speech_content_list=speaker_and_speech_content_list
            )

        except BamlValidationError as e:
            # LLMが構造化出力を返さなかった場合（許容される状況）
            logger.warning(
                f"BAML speech_divide_run バリデーション失敗: {e}. "
                "空のリストを返します。"
            )
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])
        except Exception as e:
            logger.error(f"BAML speech_divide_run failed: {e}", exc_info=True)
            raise ExternalServiceException(
                service_name="BAML",
                operation="speech_divide_run",
                reason=str(e),
            ) from e
