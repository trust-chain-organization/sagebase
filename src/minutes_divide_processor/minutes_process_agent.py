import re
import uuid

from typing import TYPE_CHECKING, Any

import structlog

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.store.memory import InMemoryStore

# Use relative import for modules within the same package
from .models import (
    MinutesBoundary,
    MinutesProcessState,
    SectionStringList,
    SpeakerAndSpeechContent,
)

from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.minutes_divider.factory import MinutesDividerFactory


logger = structlog.get_logger(__name__)


# 循環インポートを避けるため、TYPE_CHECKINGで型ヒントのみに使用
if TYPE_CHECKING:
    pass


class MinutesProcessAgent:
    def __init__(
        self,
        llm_service: ILLMService | InstrumentedLLMService | None = None,
        k: int | None = None,
    ):
        """
        Initialize MinutesProcessAgent

        Args:
            llm_service: LLMService instance (creates default if not provided)
                Can be ILLMService or InstrumentedLLMService
            k: Number of sections
        """
        # 各種ジェネレータの初期化（Factoryパターンで実装を切り替え）
        self.minutes_divider = MinutesDividerFactory.create(
            llm_service=llm_service, k=k or 5
        )

        # SpeechExtractionAgentの初期化（LangGraphサブグラフとして使用）
        # 循環インポートを避けるため、ここでインポート
        from langchain_google_genai import ChatGoogleGenerativeAI

        from src.infrastructure.external.langgraph_speech_extraction_agent import (
            SpeechExtractionAgent,
        )

        # モデル名の環境変数化（See: Issue #977）
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
        self.speech_extraction_agent = SpeechExtractionAgent(llm)

        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()

    def _create_graph(self) -> Any:
        """グラフの初期化（SpeechExtractionAgentサブグラフを統合）

        新しいフロー:
        process_minutes → extract_speech_boundary → divide_minutes_to_keyword
        → divide_minutes_to_string → check_length → divide_speech (loop)
        → normalize_speaker_names → END

        extract_speech_boundaryノードでSpeechExtractionAgentサブグラフを実行し、
        議事録から出席者部分と発言部分を分離します。
        normalize_speaker_namesノードでLLMを使用して発言者名を正規化します
        （Issue #946）。
        """
        # グラフの初期化
        workflow = StateGraph(MinutesProcessState)
        checkpointer = MemorySaver()

        # ノードの追加
        workflow.add_node("process_minutes", self._process_minutes)  # type: ignore[arg-type]
        workflow.add_node("extract_speech_boundary", self._extract_speech_boundary)  # type: ignore[arg-type]  # 新規追加
        workflow.add_node("divide_minutes_to_keyword", self._divide_minutes_to_keyword)  # type: ignore[arg-type]
        workflow.add_node("divide_minutes_to_string", self._divide_minutes_to_string)  # type: ignore[arg-type]
        workflow.add_node("check_length", self._check_length)  # type: ignore[arg-type]
        workflow.add_node("divide_speech", self._divide_speech)  # type: ignore[arg-type]
        workflow.add_node("normalize_speaker_names", self._normalize_speaker_names)  # type: ignore[arg-type]  # Issue #946

        # エッジの設定（フロー変更）
        workflow.set_entry_point("process_minutes")
        # 前処理後に境界抽出
        workflow.add_edge("process_minutes", "extract_speech_boundary")
        # 境界抽出後にキーワード分割
        workflow.add_edge("extract_speech_boundary", "divide_minutes_to_keyword")
        workflow.add_edge("divide_minutes_to_keyword", "divide_minutes_to_string")
        workflow.add_edge("divide_minutes_to_string", "check_length")
        workflow.add_edge("check_length", "divide_speech")
        workflow.add_conditional_edges(
            "divide_speech",
            # indexは1から始まるので、<= で比較する必要がある
            lambda state: state.index <= state.section_list_length,  # type: ignore[arg-type, no-any-return]
            {
                True: "divide_speech",
                False: "normalize_speaker_names",
            },  # ENDの代わりに正規化ノードへ
        )
        # 発言者名正規化後に終了
        workflow.add_edge("normalize_speaker_names", END)

        return workflow.compile(checkpointer=checkpointer, store=self.in_memory_store)  # type: ignore[return-value]  # type: ignore[return-value]

    def _get_from_memory(self, namespace: str, memory_id: str) -> Any | None:
        namespace_for_memory = ("1", namespace)
        memory_item = self.in_memory_store.get(namespace_for_memory, memory_id)
        if memory_item is None:
            return None
        else:
            return memory_item.value

    def _put_to_memory(self, namespace: str, memory: dict[str, Any]) -> str:
        user_id = "1"
        namespace_for_memory = (user_id, namespace)
        memory_id = str(uuid.uuid4())
        # https://langchain-ai.github.io/langgraph/concepts/persistence/#basic-usage
        self.in_memory_store.put(namespace_for_memory, memory_id, memory)
        return memory_id

    async def _process_minutes(self, state: MinutesProcessState) -> dict[str, str]:
        """議事録の前処理のみを行う（境界検出はextract_speech_boundaryサブグラフに移譲）"""
        # 議事録の文字列に対する前処理を行う
        processed_minutes = self.minutes_divider.pre_process(state.original_minutes)

        # 前処理済み議事録をメモリに保存
        memory = {"processed_minutes": processed_minutes}
        memory_id = self._put_to_memory(namespace="processed_minutes", memory=memory)
        return {"processed_minutes_memory_id": memory_id}

    async def _extract_speech_boundary(
        self, state: MinutesProcessState
    ) -> dict[str, str]:
        """発言境界を抽出（SpeechExtractionAgentサブグラフを使用）

        LangGraphのサブグラフ統合パターンに従い、以下を実行：
        1. 親グラフの状態からサブグラフの入力を構築
        2. サブグラフを invoke() で実行
        3. サブグラフの出力を親グラフの状態に変換
        """
        # 前処理済み議事録を取得
        memory_data = self._get_from_memory(
            "processed_minutes", state.processed_minutes_memory_id
        )
        if memory_data is None or "processed_minutes" not in memory_data:
            raise ValueError("Failed to retrieve processed_minutes from memory")

        processed_minutes = memory_data["processed_minutes"]
        if not isinstance(processed_minutes, str):
            raise TypeError("processed_minutes must be a string")

        # ReActエージェントには初期メッセージが必要
        from langchain_core.messages import HumanMessage

        initial_message = HumanMessage(
            content=(
                f"この議事録から発言部分の開始境界を検出してください。"
                f"テキスト長: {len(processed_minutes)}文字"
            )
        )

        # サブグラフを実行（状態変換: MinutesProcessState → SpeechExtractionAgentState）
        # SpeechExtractionAgent.compile()で取得したサブグラフを invoke
        compiled_subgraph = self.speech_extraction_agent.compile()
        raw_result = await compiled_subgraph.ainvoke(
            {
                "minutes_text": processed_minutes,
                "boundary_candidates": [],
                "verified_boundaries": [],
                "current_position": 0,
                "messages": [initial_message],
                "remaining_steps": 10,  # MAX_REACT_STEPS
                "error_message": None,
            }
        )
        # ainvoke()の戻り値は辞書型なので、必要なフィールドを抽出
        boundary_result = {
            "verified_boundaries": raw_result.get("verified_boundaries", []),
            "error_message": raw_result.get("error_message"),
        }

        # サブグラフの出力をMinutesBoundaryに変換
        boundary = self._convert_boundary_result(boundary_result)

        # 境界で議事録を分割
        _, speech_part = self.minutes_divider.split_minutes_by_boundary(
            processed_minutes, boundary
        )

        # 結果をメモリに保存
        memory = {
            "boundary_result": boundary_result,
            "boundary": boundary,
            "speech_part": speech_part,
        }
        memory_id = self._put_to_memory("boundary_extraction", memory)

        return {"boundary_extraction_result_memory_id": memory_id}

    def _convert_boundary_result(
        self, boundary_result: dict[str, Any]
    ) -> MinutesBoundary:
        """BoundaryExtractionResultをMinutesBoundaryに変換

        SpeechExtractionAgentの出力形式を、
        既存のMinutesDividerが期待する形式に変換します。

        Args:
            boundary_result: SpeechExtractionAgentからの境界抽出結果

        Returns:
            MinutesBoundary: 変換された境界情報
        """
        if not boundary_result.get("verified_boundaries"):
            return MinutesBoundary(
                boundary_found=False,
                boundary_text=None,
                boundary_type="none",
                confidence=0.0,
                reason="境界が検出されませんでした",
            )

        # 最も信頼度の高い境界を使用
        best_boundary = max(
            boundary_result["verified_boundaries"], key=lambda b: b["confidence"]
        )

        # 境界位置の前後のテキストを構築（｜境界｜マーカー形式）
        # Note: 実際の位置情報が必要な場合は、元のテキストから抽出する必要がある
        boundary_text = f"｜境界｜ (position: {best_boundary['position']})"

        return MinutesBoundary(
            boundary_found=True,
            boundary_text=boundary_text,
            boundary_type=best_boundary["boundary_type"],  # type: ignore[arg-type]
            confidence=best_boundary["confidence"],
            reason=f"SpeechExtractionAgent検出: {best_boundary['boundary_type']}",
        )

    async def _divide_minutes_to_keyword(
        self, state: MinutesProcessState
    ) -> dict[str, Any]:
        # 境界抽出結果から発言部分を取得
        memory_id = state.boundary_extraction_result_memory_id
        memory_data = self._get_from_memory(
            namespace="boundary_extraction", memory_id=memory_id
        )
        if memory_data is None or "speech_part" not in memory_data:
            raise ValueError("Failed to retrieve speech_part from memory")

        speech_part = memory_data["speech_part"]
        if not isinstance(speech_part, str):
            raise TypeError("speech_part must be a string")

        # 議事録を分割する（発言部分のみ）
        section_info_list = await self.minutes_divider.section_divide_run(speech_part)
        section_list_length = len(section_info_list.section_info_list)
        logger.debug("キーワード分割完了", section_count=section_list_length)
        return {
            # リストとして返す
            "section_info_list": section_info_list.section_info_list,
            "section_list_length": section_list_length,
        }

    def _divide_minutes_to_string(self, state: MinutesProcessState) -> dict[str, str]:
        # 境界抽出結果から発言部分を取得
        memory_id = state.boundary_extraction_result_memory_id
        memory_data = self._get_from_memory("boundary_extraction", memory_id)
        if memory_data is None or "speech_part" not in memory_data:
            raise ValueError("Failed to retrieve speech_part from memory")

        speech_part = memory_data["speech_part"]
        if not isinstance(speech_part, str):
            raise TypeError("speech_part must be a string")

        # 議事録を分割する（発言部分のみ）
        section_string_list = self.minutes_divider.do_divide(
            speech_part, state.section_info_list
        )
        memory = {"section_string_list": section_string_list}
        memory_id = self._put_to_memory(namespace="section_string_list", memory=memory)
        return {"section_string_list_memory_id": memory_id}

    def _check_length(self, state: MinutesProcessState) -> dict[str, str]:
        memory_id = state.section_string_list_memory_id
        memory_data = self._get_from_memory("section_string_list", memory_id)
        if memory_data is None or "section_string_list" not in memory_data:
            raise ValueError("Failed to retrieve section_string_list from memory")

        section_string_list = memory_data["section_string_list"]
        if not isinstance(section_string_list, SectionStringList):
            raise TypeError("section_string_list must be a SectionStringList instance")

        # 文字列のバイト数をチェックする
        redivide_section_string_list = self.minutes_divider.check_length(
            section_string_list
        )
        memory = {"redivide_section_string_list": redivide_section_string_list}
        memory_id = self._put_to_memory(
            namespace="redivide_section_string_list", memory=memory
        )
        logger.debug("セクション長チェック完了")
        return {"redivide_section_string_list_memory_id": memory_id}

    async def _divide_speech(self, state: MinutesProcessState) -> dict[str, Any]:
        memory_id = state.section_string_list_memory_id
        memory_data = self._get_from_memory("section_string_list", memory_id)
        if memory_data is None or "section_string_list" not in memory_data:
            raise ValueError("Failed to retrieve section_string_list from memory")

        section_string_list = memory_data["section_string_list"]
        if not isinstance(section_string_list, SectionStringList):
            raise TypeError("section_string_list must be a SectionStringList instance")

        if state.index - 1 < len(section_string_list.section_string_list):
            # すべてのセクションを処理する（0, 1, 2, 3の制限を削除）
            # 発言者と発言内容に分割する
            speaker_and_speech_content_list = (
                await self.minutes_divider.speech_divide_run(
                    section_string_list.section_string_list[state.index - 1]
                )
            )
        else:
            logger.warning(
                "インデックスが範囲外",
                index=state.index - 1,
                section_count=len(section_string_list.section_string_list),
            )
            speaker_and_speech_content_list = None
        logger.debug(
            "発言分割処理中",
            current_index=state.index,
            total_sections=state.section_list_length,
        )
        # 現在のdivide_speech_listを取得
        memory_id = state.divided_speech_list_memory_id
        memory_data = self._get_from_memory("divided_speech_list", memory_id)

        # 初回はNULLなのでその場合は空配列を作成
        if memory_data is None or "divided_speech_list" not in memory_data:
            divided_speech_list: list[SpeakerAndSpeechContent] = []
        else:
            divided_speech_list = memory_data["divided_speech_list"]
            if not isinstance(divided_speech_list, list):
                raise TypeError("divided_speech_list must be a list")
            # Cast to proper type after type check
            divided_speech_list = divided_speech_list

        # もしspeaker_and_speech_content_listがNoneの場合は、
        # 現在のリストを更新用リストとして返す
        if speaker_and_speech_content_list is None:
            logger.warning("発言リストがNullのためスキップ", index=state.index)
            updated_speaker_and_speech_content_list = divided_speech_list
            memory: dict[str, list[SpeakerAndSpeechContent]] = {
                "divided_speech_list": updated_speaker_and_speech_content_list
            }
            memory_id = self._put_to_memory(
                namespace="divided_speech_list", memory=memory
            )
        else:
            # すべてのセクションの結果を追加
            updated_speaker_and_speech_content_list: list[SpeakerAndSpeechContent] = (
                divided_speech_list
                + speaker_and_speech_content_list.speaker_and_speech_content_list
            )
            memory: dict[str, list[SpeakerAndSpeechContent]] = {
                "divided_speech_list": updated_speaker_and_speech_content_list
            }
            memory_id = self._put_to_memory(
                namespace="divided_speech_list", memory=memory
            )
        incremented_index = state.index + 1
        logger.debug("発言分割インデックス更新", next_index=incremented_index)
        return {"divided_speech_list_memory_id": memory_id, "index": incremented_index}

    def _normalize_speaker_name_rule_based(
        self,
        speaker: str,
        role_name_mappings: dict[str, str] | None,
    ) -> tuple[str, bool, str]:
        """ルールベースで発言者名を正規化する。

        Args:
            speaker: 元の発言者名
            role_name_mappings: 役職-人名マッピング

        Returns:
            (正規化された名前, 有効かどうか, 抽出方法)
        """
        if not speaker or not speaker.strip():
            return ("", False, "empty")

        # 先頭の記号を除去（○◆◇■□●など）
        cleaned = re.sub(r"^[○◆◇■□●◎△▲▽▼☆★]+", "", speaker).strip()

        # 括弧内の人名を抽出（全角・半角両対応）
        # パターン: 役職（人名）、役職(人名)
        bracket_pattern = r"^.+?[（(](.+?)[）)]$"
        match = re.match(bracket_pattern, cleaned)
        if match:
            name = match.group(1)
            # 敬称を除去
            name = self._remove_honorifics(name)
            if name:
                return (name, True, "pattern")

        # 役職のみの場合はマッピングを参照
        role_keywords = [
            "議長",
            "副議長",
            "委員長",
            "副委員長",
            "会長",
            "副会長",
            "理事",
            "幹事",
            "書記",
            "議員",
            "委員",
            "市長",
            "副市長",
            "町長",
            "副町長",
            "村長",
            "副村長",
            "区長",
            "副区長",
            "知事",
            "副知事",
            "部長",
            "局長",
            "課長",
            "事務局長",
            "事務局次長",
            "参考人",
            "証人",
            "説明員",
            "政府参考人",
            "大臣",
            "副大臣",
            "政務官",
        ]

        # 役職のみかどうかを先にチェック
        # （「副市長」が「副」+「市長」と誤解釈されるのを防ぐ）
        is_role_only = cleaned in role_keywords
        if is_role_only:
            if role_name_mappings and cleaned in role_name_mappings:
                return (role_name_mappings[cleaned], True, "mapping")
            else:
                return (cleaned, False, "role_only_no_mapping")

        # 役職+人名パターン（括弧なし）: 「松井市長」→「松井」を抽出
        for role in role_keywords:
            if cleaned.endswith(role) and len(cleaned) > len(role):
                name = cleaned[: -len(role)]
                name = self._remove_honorifics(name)
                if name:
                    return (name, True, "role_suffix")

        # 人名として扱う（敬称除去）
        name = self._remove_honorifics(cleaned)
        if name:
            return (name, True, "as_is")
        return (cleaned, True, "as_is")

    def _remove_honorifics(self, name: str) -> str:
        """敬称を除去する（複数の敬称にも対応）。"""
        honorifics = [
            "君",
            "氏",
            "議員",
            "委員",
            "参考人",
            "証人",
            "説明員",
            "さん",
            "様",
            "先生",
        ]
        result = name
        # 複数の敬称がネストしている場合にも対応（例: 「山田太郎議員先生」）
        changed = True
        while changed:
            changed = False
            for h in honorifics:
                if result.endswith(h):
                    result = result[: -len(h)]
                    changed = True
                    break
        return result.strip()

    async def _normalize_speaker_names(
        self, state: MinutesProcessState
    ) -> dict[str, str]:
        """発言者名をLLMで正規化する（Issue #946）

        役職（人名）パターンから人名を抽出し、役職のみの場合はマッピングを参照して
        人名を取得します。無効な発言者はフィルタリングされます。
        LLMが失敗した場合はルールベースにフォールバックします。
        """
        from baml_client.async_client import b

        # 分割済み発言リストを取得
        memory_id = state.divided_speech_list_memory_id
        memory_data = self._get_from_memory("divided_speech_list", memory_id)
        if memory_data is None or "divided_speech_list" not in memory_data:
            raise ValueError("Failed to retrieve divided_speech_list from memory")

        divided_speech_list = memory_data["divided_speech_list"]
        if not isinstance(divided_speech_list, list):
            raise TypeError("divided_speech_list must be a list")

        if not divided_speech_list:
            # 空の場合はそのまま返す
            memory = {"normalized_speech_list": []}
            memory_id = self._put_to_memory("normalized_speech_list", memory)
            return {"normalized_speech_list_memory_id": memory_id}

        # ユニークな発言者名のリストを抽出
        unique_speakers = list(
            dict.fromkeys(speech.speaker for speech in divided_speech_list)
        )

        logger.info(
            "発言者名の正規化を開始",
            unique_speaker_count=len(unique_speakers),
            has_mappings=bool(state.role_name_mappings),
        )
        logger.debug("正規化対象発言者", speakers=unique_speakers)
        if state.role_name_mappings:
            logger.debug("役職-人名マッピング", mappings=state.role_name_mappings)

        # 正規化マッピングを構築
        normalization_map: dict[str, tuple[str, bool, str]] = {}

        # まずLLMで正規化を試みる
        try:
            logger.debug("LLMベース正規化を試行")
            normalized_results = await b.NormalizeSpeakerNames(
                speakers=unique_speakers,
                role_name_mappings=state.role_name_mappings,
            )
            logger.debug("LLM正規化結果", result_count=len(normalized_results))

            if len(normalized_results) == len(unique_speakers):
                # LLM成功: インデックスベースでマッピング
                logger.info("LLMベースの正規化を使用")
                for speaker, normalized in zip(
                    unique_speakers, normalized_results, strict=True
                ):
                    normalization_map[speaker] = (
                        normalized.normalized_name,
                        normalized.is_valid,
                        normalized.extraction_method,
                    )
                    logger.debug(
                        "LLM正規化結果",
                        original=speaker,
                        normalized=normalized.normalized_name,
                        is_valid=normalized.is_valid,
                        method=normalized.extraction_method,
                    )
            else:
                # LLMの出力数が一致しない場合はルールベースにフォールバック
                logger.warning(
                    "LLM結果数不一致のためルールベースにフォールバック",
                    llm_count=len(normalized_results),
                    expected_count=len(unique_speakers),
                )
                raise ValueError("LLM result count mismatch")
        except Exception as e:
            # LLM失敗時はルールベースにフォールバック
            logger.warning("LLM正規化失敗、ルールベースを使用", error=str(e))
            for speaker in unique_speakers:
                normalized_name, is_valid, method = (
                    self._normalize_speaker_name_rule_based(
                        speaker, state.role_name_mappings
                    )
                )
                normalization_map[speaker] = (normalized_name, is_valid, method)
                logger.debug(
                    "ルールベース正規化結果",
                    original=speaker,
                    normalized=normalized_name,
                    is_valid=is_valid,
                    method=method,
                )

        # 正規化結果を元の発言データに適用
        normalized_speech_list: list[SpeakerAndSpeechContent] = []
        skipped_count = 0

        for speech in divided_speech_list:
            speaker_name = speech.speaker

            # マッピングに存在しない場合はそのまま使用（フォールバック）
            if speaker_name not in normalization_map:
                logger.warning(
                    "発言者がマッピングに存在しないためそのまま使用",
                    speaker=speaker_name,
                )
                normalized_name = speaker_name
                is_valid = bool(speaker_name and speaker_name.strip())
                extraction_method = "fallback"
            else:
                normalized_name, is_valid, extraction_method = normalization_map[
                    speaker_name
                ]

            if not is_valid:
                logger.debug(
                    "無効な発言者をスキップ",
                    speaker=speaker_name,
                    method=extraction_method,
                )
                skipped_count += 1
                continue

            # 発言者名を正規化された名前に置き換え
            normalized_speech = SpeakerAndSpeechContent(
                speaker=normalized_name,
                speech_content=speech.speech_content,
                chapter_number=speech.chapter_number,
                sub_chapter_number=speech.sub_chapter_number,
                speech_order=speech.speech_order,
            )
            normalized_speech_list.append(normalized_speech)

            # ログ出力（変換があった場合のみ）
            if speaker_name != normalized_name:
                logger.debug(
                    "発言者名を正規化",
                    original=speaker_name,
                    normalized=normalized_name,
                    method=extraction_method,
                )

        logger.info(
            "発言者名正規化完了",
            valid_count=len(normalized_speech_list),
            skipped_count=skipped_count,
        )

        # 正規化済みリストをメモリに保存
        memory = {"normalized_speech_list": normalized_speech_list}
        memory_id = self._put_to_memory("normalized_speech_list", memory)
        return {"normalized_speech_list_memory_id": memory_id}

    async def run(
        self,
        original_minutes: str,
        role_name_mappings: dict[str, str] | None = None,
    ) -> list[SpeakerAndSpeechContent]:
        """議事録を処理し、発言者名を正規化した発言リストを返す。

        Args:
            original_minutes: 元の議事録テキスト
            role_name_mappings: 役職-人名マッピング（例: {"議長": "伊藤条一"}）
                発言者名が役職のみの場合に実名に変換（Issue #946）

        Returns:
            list[SpeakerAndSpeechContent]: 正規化された発言リスト
        """
        # 初期状態の設定（role_name_mappingsを含む）
        initial_state = MinutesProcessState(
            original_minutes=original_minutes,
            role_name_mappings=role_name_mappings,
        )
        # グラフの実行
        final_state = await self.graph.ainvoke(
            initial_state, config={"recursion_limit": 300, "thread_id": "example-1"}
        )

        # 正規化済み発言リストを取得（Issue #946）
        memory_id = final_state["normalized_speech_list_memory_id"]
        memory_data = self._get_from_memory("normalized_speech_list", memory_id)
        if memory_data is None or "normalized_speech_list" not in memory_data:
            raise ValueError("Failed to retrieve normalized_speech_list from memory")

        normalized_speech_list = memory_data["normalized_speech_list"]
        if not isinstance(normalized_speech_list, list):
            raise TypeError("normalized_speech_list must be a list")

        return normalized_speech_list  # type: ignore[return-value]
