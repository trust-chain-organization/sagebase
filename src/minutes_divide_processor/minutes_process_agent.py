import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.store.memory import InMemoryStore

from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.minutes_divider.factory import MinutesDividerFactory

# Use relative import for modules within the same package
from .models import (
    MinutesProcessState,
    SectionStringList,
    SpeakerAndSpeechContent,
)


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
        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()

    def _create_graph(self) -> Any:
        # グラフの初期化
        workflow = StateGraph(MinutesProcessState)
        checkpointer = MemorySaver()

        workflow.add_node("process_minutes", self._process_minutes)  # type: ignore[arg-type]
        workflow.add_node("divide_minutes_to_keyword", self._divide_minutes_to_keyword)  # type: ignore[arg-type]
        workflow.add_node("divide_minutes_to_string", self._divide_minutes_to_string)  # type: ignore[arg-type]
        workflow.add_node("check_length", self._check_length)  # type: ignore[arg-type]
        workflow.add_node("divide_speech", self._divide_speech)  # type: ignore[arg-type]
        workflow.set_entry_point("process_minutes")
        workflow.add_edge("process_minutes", "divide_minutes_to_keyword")
        workflow.add_edge("divide_minutes_to_keyword", "divide_minutes_to_string")
        workflow.add_edge("divide_minutes_to_string", "check_length")
        workflow.add_edge("check_length", "divide_speech")
        workflow.add_conditional_edges(
            "divide_speech",
            # indexは1から始まるので、<= で比較する必要がある
            lambda state: state.index <= state.section_list_length,  # type: ignore[arg-type, no-any-return]
            {True: "divide_speech", False: END},
        )

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

    def _process_minutes(self, state: MinutesProcessState) -> dict[str, str]:
        # 議事録の文字列に対する前処理を行う
        processed_minutes = self.minutes_divider.pre_process(state.original_minutes)

        # 出席者情報と発言部分の境界を検出して分割
        boundary = self.minutes_divider.detect_attendee_boundary(processed_minutes)
        _, speech_part = self.minutes_divider.split_minutes_by_boundary(
            processed_minutes, boundary
        )

        # 発言部分のみを後続の処理に渡す
        memory = {"processed_minutes": speech_part}
        memory_id = self._put_to_memory(namespace="processed_minutes", memory=memory)
        return {"processed_minutes_memory_id": memory_id}

    def _divide_minutes_to_keyword(self, state: MinutesProcessState) -> dict[str, Any]:
        memory_id = state.processed_minutes_memory_id
        memory_data = self._get_from_memory(
            namespace="processed_minutes", memory_id=memory_id
        )
        if memory_data is None or "processed_minutes" not in memory_data:
            raise ValueError("Failed to retrieve processed_minutes from memory")

        processed_minutes = memory_data["processed_minutes"]
        if not isinstance(processed_minutes, str):
            raise TypeError("processed_minutes must be a string")

        # 議事録を分割する
        section_info_list = self.minutes_divider.section_divide_run(processed_minutes)
        section_list_length = len(section_info_list.section_info_list)
        print("divide_minutes_to_keyword_done")
        return {
            # リストとして返す
            "section_info_list": section_info_list.section_info_list,
            "section_list_length": section_list_length,
        }

    def _divide_minutes_to_string(self, state: MinutesProcessState) -> dict[str, str]:
        memory_id = state.processed_minutes_memory_id
        memory_data = self._get_from_memory("processed_minutes", memory_id)
        if memory_data is None or "processed_minutes" not in memory_data:
            raise ValueError("Failed to retrieve processed_minutes from memory")

        processed_minutes = memory_data["processed_minutes"]
        if not isinstance(processed_minutes, str):
            raise TypeError("processed_minutes must be a string")

        # 議事録を分割する
        section_string_list = self.minutes_divider.do_divide(
            processed_minutes, state.section_info_list
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
        print("check_length_done")
        return {"redivide_section_string_list_memory_id": memory_id}

    def _divide_speech(self, state: MinutesProcessState) -> dict[str, Any]:
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
            speaker_and_speech_content_list = self.minutes_divider.speech_divide_run(
                section_string_list.section_string_list[state.index - 1]
            )
        else:
            print(
                f"Warning: Index {state.index - 1} is out of range "
                + "for section_string_list."
            )
            speaker_and_speech_content_list = None
        print(
            f"divide_speech_done on index_number: {state.index} "
            + f"all_length: {state.section_list_length}"
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
            print(
                "Warning: speaker_and_speech_content_list is None. "
                + "Skipping this section."
            )
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
        print(f"incremented_speech_divide_index: {incremented_index}")
        return {"divided_speech_list_memory_id": memory_id, "index": incremented_index}

    def run(self, original_minutes: str) -> list[SpeakerAndSpeechContent]:
        # 初期状態の設定
        initial_state = MinutesProcessState(original_minutes=original_minutes)
        # グラフの実行
        final_state = self.graph.invoke(
            initial_state, config={"recursion_limit": 300, "thread_id": "example-1"}
        )
        # 分割結果の取得
        memory_id = final_state["divided_speech_list_memory_id"]
        memory_data = self._get_from_memory("divided_speech_list", memory_id)
        if memory_data is None or "divided_speech_list" not in memory_data:
            raise ValueError("Failed to retrieve divided_speech_list from memory")

        divided_speech_list = memory_data["divided_speech_list"]
        if not isinstance(divided_speech_list, list):
            raise TypeError("divided_speech_list must be a list")

        return divided_speech_list  # type: ignore[return-value]
