"""MinutesProcessAgentの発言者名正規化機能のテスト。

_normalize_speaker_name_rule_basedメソッドと_remove_honorificsメソッドの
単体テストを含む（Issue #946）。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.minutes_divide_processor.models import (
    MinutesProcessState,
    SpeakerAndSpeechContent,
)


# テスト用のモック化されたAgentを作成するフィクスチャ
@pytest.fixture
def mocked_agent() -> MinutesProcessAgent:
    """モックを適用したMinutesProcessAgentのインスタンスを作成。"""
    with (
        patch("langchain_google_genai.ChatGoogleGenerativeAI"),
        patch(
            "src.infrastructure.external.langgraph_speech_extraction_agent"
            ".SpeechExtractionAgent"
        ),
    ):
        return MinutesProcessAgent()


class TestRemoveHonorifics:
    """_remove_honorificsメソッドのテスト。"""

    def test_remove_single_honorific_kun(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """「君」を除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎君") == "山田太郎"

    def test_remove_single_honorific_shi(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """「氏」を除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎氏") == "山田太郎"

    def test_remove_single_honorific_giin(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """「議員」を除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎議員") == "山田太郎"

    def test_remove_single_honorific_sensei(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """「先生」を除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎先生") == "山田太郎"

    def test_remove_multiple_honorifics(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """複数の敬称（「議員先生」など）を除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎議員先生") == "山田太郎"

    def test_remove_nested_honorifics(self, mocked_agent: MinutesProcessAgent) -> None:
        """ネストした敬称を全て除去できることを確認。"""
        assert mocked_agent._remove_honorifics("山田太郎委員様") == "山田太郎"

    def test_no_honorific(self, mocked_agent: MinutesProcessAgent) -> None:
        """敬称がない場合はそのまま返す。"""
        assert mocked_agent._remove_honorifics("山田太郎") == "山田太郎"

    def test_empty_string(self, mocked_agent: MinutesProcessAgent) -> None:
        """空文字列の場合は空文字列を返す。"""
        assert mocked_agent._remove_honorifics("") == ""

    def test_honorific_only(self, mocked_agent: MinutesProcessAgent) -> None:
        """敬称のみの場合は空文字列を返す。"""
        assert mocked_agent._remove_honorifics("議員") == ""


class TestNormalizeSpeakerNameRuleBased:
    """_normalize_speaker_name_rule_basedメソッドのテスト。"""

    def test_extract_name_from_full_width_brackets(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """全角括弧内の人名を抽出できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based(
            "市長（松井一郎）", None
        )
        assert result == ("松井一郎", True, "pattern")

    def test_extract_name_from_half_width_brackets(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """半角括弧内の人名を抽出できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("市長(松井一郎)", None)
        assert result == ("松井一郎", True, "pattern")

    def test_extract_name_with_honorific_in_brackets(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """括弧内の人名から敬称を除去できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based(
            "議長（西村義直君）", None
        )
        assert result == ("西村義直", True, "pattern")

    def test_extract_name_with_leading_symbol(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """先頭の記号を除去して括弧内の人名を抽出できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based(
            "○議長（西村義直）", None
        )
        assert result == ("西村義直", True, "pattern")

    def test_role_with_name_suffix(self, mocked_agent: MinutesProcessAgent) -> None:
        """役職+人名パターン（「松井市長」→「松井」）を抽出できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("松井市長", None)
        assert result == ("松井", True, "role_suffix")

    def test_role_only_with_mapping(self, mocked_agent: MinutesProcessAgent) -> None:
        """役職のみでマッピングありの場合、人名を解決できることを確認。"""
        mappings = {"議長": "伊藤条一"}
        result = mocked_agent._normalize_speaker_name_rule_based("議長", mappings)
        assert result == ("伊藤条一", True, "mapping")

    def test_role_only_without_mapping(self, mocked_agent: MinutesProcessAgent) -> None:
        """役職のみでマッピングなしの場合、無効となることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("議長", None)
        assert result == ("議長", False, "role_only_no_mapping")

    def test_role_only_with_empty_mapping(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """役職のみでマッピングが空辞書の場合、無効となることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("議長", {})
        assert result == ("議長", False, "role_only_no_mapping")

    def test_role_only_with_different_mapping(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """役職のみで異なるマッピングの場合、無効となることを確認。"""
        mappings = {"副議長": "田中花子"}
        result = mocked_agent._normalize_speaker_name_rule_based("議長", mappings)
        assert result == ("議長", False, "role_only_no_mapping")

    def test_name_only(self, mocked_agent: MinutesProcessAgent) -> None:
        """人名のみの場合はそのまま使用することを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("山田太郎", None)
        assert result == ("山田太郎", True, "as_is")

    def test_name_with_honorific(self, mocked_agent: MinutesProcessAgent) -> None:
        """人名+敬称の場合、敬称を除去することを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("山田太郎君", None)
        assert result == ("山田太郎", True, "as_is")

    def test_empty_string(self, mocked_agent: MinutesProcessAgent) -> None:
        """空文字列の場合は無効となることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("", None)
        assert result == ("", False, "empty")

    def test_whitespace_only(self, mocked_agent: MinutesProcessAgent) -> None:
        """空白文字のみの場合は無効となることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("   ", None)
        assert result == ("", False, "empty")

    def test_remove_multiple_leading_symbols(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """複数の先頭記号を除去できることを確認。"""
        result = mocked_agent._normalize_speaker_name_rule_based("○◆山田太郎", None)
        assert result == ("山田太郎", True, "as_is")

    def test_various_roles_with_mapping(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """様々な役職でマッピングが機能することを確認。"""
        mappings = {
            "委員長": "鈴木一郎",
            "副市長": "田中花子",
            "事務局長": "佐藤次郎",
        }
        assert mocked_agent._normalize_speaker_name_rule_based("委員長", mappings) == (
            "鈴木一郎",
            True,
            "mapping",
        )
        assert mocked_agent._normalize_speaker_name_rule_based("副市長", mappings) == (
            "田中花子",
            True,
            "mapping",
        )
        assert mocked_agent._normalize_speaker_name_rule_based(
            "事務局長", mappings
        ) == (
            "佐藤次郎",
            True,
            "mapping",
        )


class TestNormalizeSpeakerNamesIntegration:
    """_normalize_speaker_namesメソッドの統合テスト。"""

    @pytest.mark.asyncio
    async def test_normalize_with_llm_success(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """LLM正規化成功時の動作を確認。"""
        # テストデータをメモリに設定
        divided_speech_list = [
            SpeakerAndSpeechContent(
                speaker="議長（西村義直）",
                speech_content="開会を宣言します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="市長",
                speech_content="ご説明いたします。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]
        memory_id = mocked_agent._put_to_memory(
            "divided_speech_list", {"divided_speech_list": divided_speech_list}
        )

        state = MinutesProcessState(
            original_minutes="テスト議事録",
            divided_speech_list_memory_id=memory_id,
            role_name_mappings={"市長": "松井一郎"},
        )

        # LLM呼び出しをモック
        mock_normalized_results = [
            MagicMock(
                normalized_name="西村義直",
                is_valid=True,
                extraction_method="pattern",
            ),
            MagicMock(
                normalized_name="松井一郎",
                is_valid=True,
                extraction_method="mapping",
            ),
        ]

        with patch("baml_client.async_client.b") as mock_b:
            mock_b.NormalizeSpeakerNames = AsyncMock(
                return_value=mock_normalized_results
            )
            result = await mocked_agent._normalize_speaker_names(state)

        # 結果を検証
        normalized_memory = mocked_agent._get_from_memory(
            "normalized_speech_list", result["normalized_speech_list_memory_id"]
        )
        assert normalized_memory is not None
        normalized_list = normalized_memory["normalized_speech_list"]
        assert len(normalized_list) == 2
        assert normalized_list[0].speaker == "西村義直"
        assert normalized_list[1].speaker == "松井一郎"

    @pytest.mark.asyncio
    async def test_normalize_with_llm_failure_fallback_to_rule_based(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """LLM失敗時にルールベースにフォールバックすることを確認。"""
        # テストデータをメモリに設定
        divided_speech_list = [
            SpeakerAndSpeechContent(
                speaker="議長（西村義直君）",
                speech_content="開会を宣言します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
        ]
        memory_id = mocked_agent._put_to_memory(
            "divided_speech_list", {"divided_speech_list": divided_speech_list}
        )

        state = MinutesProcessState(
            original_minutes="テスト議事録",
            divided_speech_list_memory_id=memory_id,
            role_name_mappings=None,
        )

        # LLM呼び出しを失敗させる
        with patch("baml_client.async_client.b") as mock_b:
            mock_b.NormalizeSpeakerNames = AsyncMock(side_effect=Exception("LLM error"))
            result = await mocked_agent._normalize_speaker_names(state)

        # 結果を検証（ルールベースでの正規化結果）
        normalized_memory = mocked_agent._get_from_memory(
            "normalized_speech_list", result["normalized_speech_list_memory_id"]
        )
        assert normalized_memory is not None
        normalized_list = normalized_memory["normalized_speech_list"]
        assert len(normalized_list) == 1
        assert normalized_list[0].speaker == "西村義直"

    @pytest.mark.asyncio
    async def test_normalize_filters_invalid_speakers(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """無効な発言者（役職のみでマッピングなし）がフィルタされることを確認。"""
        # テストデータをメモリに設定
        divided_speech_list = [
            SpeakerAndSpeechContent(
                speaker="議長",  # 役職のみ、マッピングなし
                speech_content="開会を宣言します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="山田太郎",  # 有効な人名
                speech_content="賛成します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=2,
            ),
        ]
        memory_id = mocked_agent._put_to_memory(
            "divided_speech_list", {"divided_speech_list": divided_speech_list}
        )

        state = MinutesProcessState(
            original_minutes="テスト議事録",
            divided_speech_list_memory_id=memory_id,
            role_name_mappings=None,  # マッピングなし
        )

        # LLM呼び出しを失敗させてルールベースを使用
        with patch("baml_client.async_client.b") as mock_b:
            mock_b.NormalizeSpeakerNames = AsyncMock(side_effect=Exception("LLM error"))
            result = await mocked_agent._normalize_speaker_names(state)

        # 結果を検証（役職のみはフィルタされる）
        normalized_memory = mocked_agent._get_from_memory(
            "normalized_speech_list", result["normalized_speech_list_memory_id"]
        )
        assert normalized_memory is not None
        normalized_list = normalized_memory["normalized_speech_list"]
        assert len(normalized_list) == 1
        assert normalized_list[0].speaker == "山田太郎"

    @pytest.mark.asyncio
    async def test_normalize_empty_list(
        self, mocked_agent: MinutesProcessAgent
    ) -> None:
        """空のリストの場合は空のリストを返すことを確認。"""
        # 空のリストをメモリに設定
        memory_id = mocked_agent._put_to_memory(
            "divided_speech_list", {"divided_speech_list": []}
        )

        state = MinutesProcessState(
            original_minutes="テスト議事録",
            divided_speech_list_memory_id=memory_id,
            role_name_mappings=None,
        )

        result = await mocked_agent._normalize_speaker_names(state)

        # 結果を検証
        normalized_memory = mocked_agent._get_from_memory(
            "normalized_speech_list", result["normalized_speech_list_memory_id"]
        )
        assert normalized_memory is not None
        normalized_list = normalized_memory["normalized_speech_list"]
        assert len(normalized_list) == 0
