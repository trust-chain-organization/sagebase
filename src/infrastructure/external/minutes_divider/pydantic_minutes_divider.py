import json
import logging
import re
import unicodedata
from typing import Any, cast

from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from src.domain.interfaces.minutes_divider_service import IMinutesDividerService
from src.domain.services.interfaces.llm_service import ILLMService
from src.minutes_divide_processor.models import (
    AttendeesMapping,
    MinutesBoundary,
    RedividedSectionInfoList,
    RedivideSectionString,
    RedivideSectionStringList,
    SectionInfoList,
    SectionString,
    SectionStringList,
    SpeakerAndSpeechContentList,
)
from src.services.llm_factory import LLMServiceFactory

logger = logging.getLogger(__name__)


class MinutesDivider(IMinutesDividerService):
    def __init__(
        self,
        llm_service: ILLMService | None = None,
        k: int = 5,
    ):
        """
        Initialize MinutesDivider

        Args:
            llm_service: LLMService instance (creates default if not provided)
                Can be ILLMService or InstrumentedLLMService
            k: Number of sections (default 5)
        """
        if llm_service is None:
            factory = LLMServiceFactory()
            llm_service = cast(ILLMService, factory.create_advanced())

        self.llm_service: ILLMService = llm_service
        self.section_info_list_formatted_llm = self.llm_service.get_structured_llm(
            SectionInfoList
        )
        self.speaker_and_speech_content_formatted_llm = (
            self.llm_service.get_structured_llm(SpeakerAndSpeechContentList)
        )
        self.k = k

    # 議事録の文字列に対する前処理を行う
    def pre_process(self, original_minutes: str) -> str:
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
        if not processed_minutes:
            return SectionStringList(section_string_list=[])

        # JSON文字列をPythonのリストに変換
        if isinstance(section_info_list, str):
            section_info_list = json.loads(section_info_list)

        # section_info_listがすでにリストの場合はそのまま使用
        if isinstance(section_info_list, list):
            section_info_list_data = section_info_list
        else:
            section_info_list_data = section_info_list.section_info_list

        # Unicode正規化（NFKC）と追加の正規化を適用
        import unicodedata

        def normalize_text(text: str) -> str:
            """テキストを正規化する関数
            1. NFKC正規化で全角英数字・記号を半角に
            2. 議事録特有の記号を統一
            3. タブ文字をスペースに変換
            """
            # NFKC正規化
            normalized = unicodedata.normalize("NFKC", text)
            # 議事録特有の記号の正規化
            # ◯ (U+25EF) → ○ (U+25CB)
            normalized = normalized.replace("◯", "○")
            # ● (U+25CF) → ○ (U+25CB)
            normalized = normalized.replace("●", "○")
            # タブ文字をスペースに変換
            normalized = normalized.replace("\t", " ")
            # 連続するスペースを1つに統一
            import re

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
                        print(
                            f"キーワード '{section_info.keyword}' が"
                            + "見つからないため、先頭から開始します"
                        )
            # キーワードが見つからない場合はスキップ
            if start_index == -1:
                print(
                    f"警告: キーワード '{section_info.keyword}' が"
                    + "見つかりません。スキップします。"
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
                    print(
                        f"警告: キーワード '{next_section.keyword}' が議事録に"
                        + "見つかりません。スキップします。"
                    )
                    skipped_keywords.append(next_section.keyword)
                    j += 1
            if next_keyword_index == -1:
                end_index = len(normalized_minutes)
            else:
                end_index = next_keyword_index
            # 分割された文字列を取得（元のテキストから取得）
            # 正規化されたテキストでインデックスを見つけて、元のテキストから抽出
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

    # 議事録の情報をベースに議事録を30分割する
    async def section_divide_run(self, minutes: str) -> SectionInfoList:
        # Try to get prompt from hub first, fallback to local
        try:
            prompt_template = hub.pull("divide_chapter_prompt")
        except Exception as e:
            logger.warning(f"Failed to pull prompt from hub: {e}. Using local prompt.")
            prompt_template = self.llm_service.get_prompt("minutes_divide")

        runnable_prompt = prompt_template | self.section_info_list_formatted_llm
        # 議事録を分割するチェーンを作成
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt
        # 引数に議事録を渡して実行
        result = self.llm_service.invoke_with_retry(
            chain,
            {
                "minutes": minutes,
            },
        )

        # resultがSectionInfoList型でない場合の処理を追加
        if not isinstance(result, SectionInfoList):
            if isinstance(result, dict) and "section_info_list" in result:
                result = SectionInfoList(**result)  # type: ignore[arg-type, misc]
            elif isinstance(result, list):
                result = SectionInfoList(section_info_list=result)  # type: ignore[arg-type]
            else:
                raise TypeError(f"Unexpected result type: {type(result)}")  # type: ignore[arg-type]

        # section_info_listのchapter_numberを確認して、連番になっているか確認
        last_chapter_number = 0
        for section_info in result.section_info_list:
            if section_info.chapter_number != last_chapter_number + 1:
                print("section_infoのchapter_numberが連番になっていません。")
                # 連番になっていない場合はsection_info.chapter_numberを
                # last_chapter_number + 1で上書きする
                section_info.chapter_number = last_chapter_number + 1
            last_chapter_number = section_info.chapter_number

        return result

    def check_length(
        self, section_string_list: SectionStringList
    ) -> RedivideSectionStringList:
        redivide_list: list[RedivideSectionString] = []
        for index, section_string in enumerate(section_string_list.section_string_list):
            size_in_bytes = len(section_string.section_string.encode("utf-8"))
            print(f"size_in_bytes: {size_in_bytes}")
            if size_in_bytes > 6000:  # 6000文字より多いか確認
                print("section_stringの文字数が6000文字を超えています。再分割します。")
                redivide_dict = RedivideSectionString(
                    original_index=index,
                    redivide_section_string_bytes=size_in_bytes,
                    redivide_section_string=section_string,
                )
                redivide_list.append(redivide_dict)
        return RedivideSectionStringList(redivide_section_string_list=redivide_list)

    def do_redivide(
        self, redivide_section_string_list: RedivideSectionStringList
    ) -> RedividedSectionInfoList:
        # Try to get prompt from hub first, fallback to local
        try:
            prompt_template = hub.pull("redivide_chapter_prompt")
        except Exception as e:
            logger.warning(f"Failed to pull prompt from hub: {e}. Using local prompt.")
            # Create a fallback prompt similar to redivide
            prompt_template = ChatPromptTemplate.from_template(
                "セクションを{divide_counter}個に再分割してください。\n"
                + "元のインデックス: {original_index}\n\n"
                + "セクション内容:\n{minutes}"
            )

        runnable_prompt = prompt_template | self.section_info_list_formatted_llm
        # 議事録を分割するチェーンを作成
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt

        section_info_list: list[Any] = []
        for (
            redivide_section_string
        ) in redivide_section_string_list.redivide_section_string_list:
            divide_counter = (
                redivide_section_string.redivide_section_string_bytes // 20000000
            )
            divide_counter = divide_counter + 2

            # 引数に議事録を渡して実行
            result = self.llm_service.invoke_with_retry(
                chain,
                {
                    "minutes": (
                        redivide_section_string.redivide_section_string.section_string
                    ),
                    "original_index": redivide_section_string.original_index,
                    "divide_counter": divide_counter,
                },
            )
            if isinstance(result, SectionInfoList):
                section_info_list.extend(result.section_info_list)
            elif isinstance(result, list):
                section_info_list.extend(result)  # type: ignore[arg-type]
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
        return RedividedSectionInfoList(redivided_section_info_list=section_info_list)

    # 発言者と発言内容に分割する
    async def detect_attendee_boundary(self, minutes_text: str) -> MinutesBoundary:
        """議事録テキストから出席者情報と発言部分の境界を検出する

        Args:
            minutes_text: 議事録の全文

        Returns:
            MinutesBoundary: 境界検出結果
        """
        logger.info("=== detect_attendee_boundary started ===")
        logger.info(f"Input text length: {len(minutes_text)}")

        # 境界検出用のプロンプトを取得
        logger.info("Getting prompt template...")
        try:
            prompt_template = self.llm_service.get_prompt("minutes_boundary_detect")
            logger.info("Prompt template retrieved successfully")
        except KeyError as e:
            logger.error(f"Prompt template not found: {e}")
            logger.warning("Falling back to treating entire text as speech")
            return MinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.0,
                reason="境界検出プロンプトが見つかりません",
            )

        # 構造化LLMを取得
        logger.info("Getting structured LLM...")
        structured_llm = self.llm_service.get_structured_llm(MinutesBoundary)

        # チェーンを構築
        logger.info("Building chain...")
        chain = prompt_template | structured_llm

        try:
            # LLMで境界を検出
            logger.info("Invoking LLM for boundary detection...")
            result = self.llm_service.invoke_with_retry(
                chain,
                {"minutes_text": minutes_text},
            )
            logger.info(f"LLM invocation completed, result type: {type(result)}")

            if isinstance(result, MinutesBoundary):
                # 結果の詳細をログ出力
                logger.info("Boundary detection result details:")
                logger.info(f"  - boundary_found: {result.boundary_found}")
                logger.info(f"  - boundary_type: {result.boundary_type}")
                logger.info(f"  - confidence: {result.confidence}")
                logger.info(f"  - reason: {result.reason}")
                logger.info(f"  - boundary_text: {result.boundary_text}")

                if result.boundary_text:
                    # boundary_textの詳細を確認
                    logger.info(
                        f"  - boundary_text length: {len(result.boundary_text)}"
                    )
                    logger.info(
                        f"  - Contains '｜境界｜': {'｜境界｜' in result.boundary_text}"
                    )

                return result
            else:
                logger.warning("Unexpected result type from boundary detection")
                return MinutesBoundary(
                    boundary_found=False,
                    boundary_text=None,
                    boundary_type="none",
                    confidence=0.0,
                    reason="LLMからの結果が予期しない形式でした",
                )

        except Exception as e:
            logger.error(f"Error in boundary detection: {e}")
            return MinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.0,
                reason=f"境界検出中にエラーが発生しました: {str(e)}",
            )

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
                after_boundary = parts[
                    -1
                ].strip()  # 最後の部分を使用（複数マーカーがある場合の対応）
            else:
                # マーカーで分割できない場合
                logger.warning(f"Could not split by marker: {boundary.boundary_text}")
                before_boundary = ""
                after_boundary = boundary.boundary_text.strip()
        else:
            # マーカーがない場合、全体を境界後のテキストとして扱う
            logger.warning(
                f"No boundary marker found in boundary_text: {boundary.boundary_text}"
            )
            # 境界テキスト全体を使って検索を試みる
            before_boundary = ""
            after_boundary = boundary.boundary_text.strip()

        logger.info(f"Before boundary text: {repr(before_boundary)}")
        logger.info(f"After boundary text: {repr(after_boundary)}")

        # 元のテキストから境界位置を特定
        split_index = -1

        # まず境界前のテキストを探す
        if before_boundary and len(before_boundary) > 5:  # 5文字以上の場合のみ検索
            # 改行文字を含む検索と含まない検索を両方試す
            search_patterns = [
                before_boundary,
                before_boundary.replace(
                    "\\n", "\n"
                ),  # エスケープされた改行を実際の改行に
                before_boundary.replace("\n", " "),  # 改行をスペースに
                before_boundary.replace("\n", ""),  # 改行を削除
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

            # 境界後テキストの最初の10文字で検索
            if after_boundary and len(after_boundary) > 10:
                partial = after_boundary[:10]
                if partial in minutes_text:
                    split_index = minutes_text.find(partial)
                    logger.info(
                        f"Found boundary using partial text at index {split_index}"
                    )

            # それでも見つからない場合、発言パターンを探す
            if split_index == -1:
                # 一般的な発言開始パターンを探す
                speech_patterns = [
                    r"○.*?議長",
                    r"◆.*?議員",
                    r"［.*?開会］",
                    r"【.*?】",
                    r"○委員長",
                    r"◆委員",
                ]

                import re

                for pattern in speech_patterns:
                    match = re.search(pattern, minutes_text)
                    if match:
                        split_index = match.start()
                        logger.info(
                            f"Found boundary using pattern '{pattern}' at {split_index}"
                        )
                        break

        if split_index == -1:
            # どうしても見つからない場合は全体を発言部分として扱う
            logger.warning(
                f"Could not locate boundary in original text. "
                f"Tried multiple patterns from boundary_text: {boundary.boundary_text}"
            )
            # デバッグ用: 元テキストの先頭と末尾を表示
            logger.info(
                f"Original text preview (first 200 chars): {minutes_text[:200]}"
            )
            logger.info(
                f"Original text preview (last 200 chars): {minutes_text[-200:]}"
            )
            return "", minutes_text

        # 境界位置の妥当性を検証
        # 境界がテキストの末尾付近にある場合は無効とみなす
        text_length = len(minutes_text)
        remaining_length = text_length - split_index

        # 末尾から100文字以内、かつテキスト全体の20%以内の場合は無効
        # (ANDにすることで、短いテキストで有効な境界を誤って拒否することを防ぐ)
        if remaining_length < 100 and remaining_length < text_length * 0.2:
            logger.warning(
                f"Boundary is too close to the end of text "
                f"(remaining: {remaining_length} chars, "
                f"{remaining_length / text_length * 100:.1f}% of total). "
                f"Treating entire text as speech content."
            )
            return "", minutes_text

        # テキストを分割
        attendee_part = minutes_text[:split_index].strip()
        speech_part = minutes_text[split_index:].strip()

        logger.info(f"Split successful at index {split_index}")
        logger.info(f"Attendee part length: {len(attendee_part)}")
        logger.info(f"Speech part length: {len(speech_part)}")

        # 出席者部分のプレビュー（デバッグ用）
        if attendee_part:
            preview_len = min(100, len(attendee_part))
            logger.info(f"Attendee part preview: ...{attendee_part[-preview_len:]}")

        # 発言部分のプレビュー（デバッグ用）
        if speech_part:
            preview_len = min(100, len(speech_part))
            logger.info(f"Speech part preview: {speech_part[:preview_len]}...")

        return attendee_part, speech_part

    async def extract_attendees_mapping(self, attendees_text: str) -> AttendeesMapping:
        """出席者情報から役職と人名のマッピングを抽出する

        Args:
            attendees_text: 出席者情報のテキスト

        Returns:
            AttendeesMapping: 役職と人名のマッピング
        """
        logger.info("=== extract_attendees_mapping started ===")
        logger.info(f"Attendees text length: {len(attendees_text)}")

        if not attendees_text:
            logger.warning("No attendees text provided")
            return AttendeesMapping(
                attendees_mapping={}, regular_attendees=[], confidence=0.0
            )

        try:
            # プロンプトを取得
            prompt_template = self.llm_service.get_prompt("extract_attendees_mapping")

            # 構造化LLMを取得
            structured_llm = self.llm_service.get_structured_llm(AttendeesMapping)

            # チェーンを構築
            chain = prompt_template | structured_llm

            # LLMで出席者マッピングを抽出
            logger.info("Invoking LLM for attendees mapping extraction...")
            logger.info(f"Input text preview: {attendees_text[:200]}...")
            result = self.llm_service.invoke_with_retry(
                chain, {"attendees_text": attendees_text}
            )
            logger.info(f"LLM result type: {type(result)}")
            logger.info(f"LLM result: {result}")

            if isinstance(result, AttendeesMapping):
                # attendees_mappingがNoneまたは文字列の場合は空dictに変換
                if result.attendees_mapping is None or isinstance(
                    result.attendees_mapping, str
                ):
                    logger.info(
                        f"Setting attendees_mapping to empty dict "
                        f"(was: {type(result.attendees_mapping)})"
                    )
                    result.attendees_mapping = {}

                logger.info("Attendees mapping extraction result:")
                mapping_count = (
                    len(result.attendees_mapping) if result.attendees_mapping else 0
                )
                logger.info(f"  - Role mappings: {mapping_count}")
                logger.info(f"  - Regular attendees: {len(result.regular_attendees)}")
                logger.info(f"  - Confidence: {result.confidence}")

                # 人名リストをログ出力
                for name in result.regular_attendees[:10]:
                    logger.info(f"    Attendee: {name}")
                if len(result.regular_attendees) > 10:
                    more_count = len(result.regular_attendees) - 10
                    logger.info(f"    ... and {more_count} more")

                return result
            else:
                logger.warning(
                    "Unexpected result type from attendees mapping extraction"
                )
                return AttendeesMapping(
                    attendees_mapping={}, regular_attendees=[], confidence=0.0
                )

        except Exception as e:
            logger.error(f"Error in attendees mapping extraction: {e}")
            return AttendeesMapping(
                attendees_mapping={}, regular_attendees=[], confidence=0.0
            )

    async def speech_divide_run(
        self, section_string: SectionString
    ) -> SpeakerAndSpeechContentList:
        # セクション全体のテキストを取得
        section_text = section_string.section_string

        # デバッグログ
        logger.info("=== speech_divide_run started ===")
        logger.info(f"Section text length: {len(section_text)}")
        logger.info(f"Section text preview: {section_text[:200]}...")

        # LLMベースの境界検出を実行
        logger.info("Calling detect_attendee_boundary...")
        boundary = await self.detect_attendee_boundary(section_text)
        logger.info(
            f"Boundary detection result: found={boundary.boundary_found}, "
            f"type={boundary.boundary_type}, confidence={boundary.confidence}"
        )

        # 重要: boundary_textの内容も必ずログ出力
        if boundary.boundary_text:
            logger.info(f"Boundary text content: {repr(boundary.boundary_text)}")
        else:
            logger.warning("Boundary text is None or empty!")

        # 境界に基づいてテキストを分割
        logger.info("Calling split_minutes_by_boundary...")
        attendee_part, speech_part = self.split_minutes_by_boundary(
            section_text, boundary
        )
        logger.info(
            f"Split result: attendee_part length={len(attendee_part)}, "
            f"speech_part length={len(speech_part)}"
        )

        # デバッグ: 分割結果のプレビュー
        if attendee_part:
            logger.info(f"Attendee part last 100 chars: ...{attendee_part[-100:]}")
        if speech_part:
            logger.info(f"Speech part first 100 chars: {speech_part[:100]}...")

        # 発言部分がない場合はスキップ
        if not speech_part:
            logger.info("No speech content found in section")
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])

        # 発言部分のみを処理対象とする
        section_text = speech_part

        # 発言部分が短すぎる場合でも、明らかに発言パターンが含まれている場合は処理を続行
        # ○や◆で始まる行がある場合は発言として扱う
        import re

        has_speech_pattern = bool(re.search(r"^[○◆]", section_text, re.MULTILINE))

        if len(section_text) < 30 and not has_speech_pattern:
            logger.info("Speech part too short and no speech pattern found, skipping")
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])

        # 国会議事録向けのプロンプトを使用
        prompt_template = self.llm_service.get_prompt("speech_divide_kokkai")

        runnable_prompt = (
            prompt_template | self.speaker_and_speech_content_formatted_llm
        )
        chain = {"section_string": RunnablePassthrough()} | runnable_prompt
        result = self.llm_service.invoke_with_retry(
            chain,
            {
                "section_string": section_text,  # 文字列を抽出
            },
        )
        if result is None:
            print("Error: result is None")
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])
        # resultがSectionInfoList型であることを確認
        if isinstance(result, SpeakerAndSpeechContentList):
            speaker_and_speech_content_list = result.speaker_and_speech_content_list
        else:
            raise TypeError("Expected result to be of type SpeakerAndSpeechContentList")
        # speaker_and_speech_content_listのspeech_orderを確認して、
        # 連番になっているか確認
        last_speech_order = 0
        for speaker_and_speech_content in speaker_and_speech_content_list:
            if speaker_and_speech_content.speech_order != last_speech_order + 1:
                print(
                    "speaker_and_speech_contentのspeech_orderが連番になっていません。"
                )
                # 連番になっていない場合は
                # speaker_and_speech_content.speech_orderを
                # last_chapter_number + 1で上書きする
                speaker_and_speech_content.speech_order = last_speech_order + 1
            last_speech_order = speaker_and_speech_content.speech_order
        return SpeakerAndSpeechContentList(
            speaker_and_speech_content_list=speaker_and_speech_content_list
        )
