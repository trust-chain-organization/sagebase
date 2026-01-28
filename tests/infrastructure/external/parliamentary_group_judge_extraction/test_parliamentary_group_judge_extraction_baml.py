"""Tests for BAML Parliamentary Group Judge Extraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from baml_client.types import JudgmentType, ParliamentaryGroupJudgeExtraction


class TestExtractParliamentaryGroupJudges:
    """Test cases for ExtractParliamentaryGroupJudges BAML function."""

    @pytest.mark.asyncio
    async def test_extract_judges_success(self) -> None:
        """正常系: 会派賛否情報の抽出成功."""
        mock_result = [
            ParliamentaryGroupJudgeExtraction(
                group_name="自民党",
                judgment=JudgmentType.FOR,
                member_count=15,
                note=None,
            ),
            ParliamentaryGroupJudgeExtraction(
                group_name="立憲民主党",
                judgment=JudgmentType.AGAINST,
                member_count=8,
                note=None,
            ),
            ParliamentaryGroupJudgeExtraction(
                group_name="公明党",
                judgment=JudgmentType.FOR,
                member_count=5,
                note=None,
            ),
        ]

        with patch(
            "baml_client.b.ExtractParliamentaryGroupJudges",
            new_callable=MagicMock,
            return_value=mock_result,
        ) as mock_baml:
            from baml_client import b

            result = b.ExtractParliamentaryGroupJudges("<html>test</html>")

            assert len(result) == 3
            assert result[0].group_name == "自民党"
            assert result[0].judgment == JudgmentType.FOR
            assert result[0].member_count == 15
            assert result[1].group_name == "立憲民主党"
            assert result[1].judgment == JudgmentType.AGAINST
            assert result[2].group_name == "公明党"
            assert result[2].judgment == JudgmentType.FOR

            mock_baml.assert_called_once_with("<html>test</html>")

    @pytest.mark.asyncio
    async def test_extract_judges_async_success(self) -> None:
        """正常系: 非同期での会派賛否情報の抽出成功."""
        mock_result = [
            ParliamentaryGroupJudgeExtraction(
                group_name="共産党",
                judgment=JudgmentType.AGAINST,
                member_count=3,
                note="反対討論あり",
            ),
        ]

        with patch(
            "baml_client.b.ExtractParliamentaryGroupJudges",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_baml:
            result = await mock_baml("<html>test</html>")

            assert len(result) == 1
            assert result[0].group_name == "共産党"
            assert result[0].judgment == JudgmentType.AGAINST
            assert result[0].note == "反対討論あり"

    @pytest.mark.asyncio
    async def test_extract_judges_empty_result(self) -> None:
        """正常系: 空の結果の場合."""
        with patch(
            "baml_client.b.ExtractParliamentaryGroupJudges",
            new_callable=MagicMock,
            return_value=[],
        ) as mock_baml:
            from baml_client import b

            result = b.ExtractParliamentaryGroupJudges("<html>no data</html>")

            assert result == []
            mock_baml.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_judges_with_abstain_and_absent(self) -> None:
        """正常系: 棄権と欠席を含む場合."""
        mock_result = [
            ParliamentaryGroupJudgeExtraction(
                group_name="自民党",
                judgment=JudgmentType.FOR,
                member_count=10,
                note=None,
            ),
            ParliamentaryGroupJudgeExtraction(
                group_name="無所属の会",
                judgment=JudgmentType.ABSTAIN,
                member_count=2,
                note="自由投票",
            ),
            ParliamentaryGroupJudgeExtraction(
                group_name="維新の会",
                judgment=JudgmentType.ABSENT,
                member_count=3,
                note="欠席",
            ),
        ]

        with patch(
            "baml_client.b.ExtractParliamentaryGroupJudges",
            new_callable=MagicMock,
            return_value=mock_result,
        ):
            from baml_client import b

            result = b.ExtractParliamentaryGroupJudges("<html>test</html>")

            assert len(result) == 3
            assert result[1].judgment == JudgmentType.ABSTAIN
            assert result[1].note == "自由投票"
            assert result[2].judgment == JudgmentType.ABSENT

    @pytest.mark.asyncio
    async def test_extract_judges_optional_fields_null(self) -> None:
        """正常系: オプショナルフィールド（member_count, note）がnullの場合."""
        mock_result = [
            ParliamentaryGroupJudgeExtraction(
                group_name="自民党京都市議団",
                judgment=JudgmentType.FOR,
                member_count=None,
                note=None,
            ),
        ]

        with patch(
            "baml_client.b.ExtractParliamentaryGroupJudges",
            new_callable=MagicMock,
            return_value=mock_result,
        ):
            from baml_client import b

            result = b.ExtractParliamentaryGroupJudges("<html>test</html>")

            assert len(result) == 1
            assert result[0].group_name == "自民党京都市議団"
            assert result[0].judgment == JudgmentType.FOR
            assert result[0].member_count is None
            assert result[0].note is None


class TestJudgmentType:
    """Test cases for JudgmentType enum."""

    def test_judgment_type_values(self) -> None:
        """賛否判断のEnum値が正しく定義されていることを確認."""
        assert JudgmentType.FOR.value == "FOR"
        assert JudgmentType.AGAINST.value == "AGAINST"
        assert JudgmentType.ABSTAIN.value == "ABSTAIN"
        assert JudgmentType.ABSENT.value == "ABSENT"

    def test_judgment_type_from_string(self) -> None:
        """文字列からEnum変換が正しく動作することを確認."""
        assert JudgmentType("FOR") == JudgmentType.FOR
        assert JudgmentType("AGAINST") == JudgmentType.AGAINST
        assert JudgmentType("ABSTAIN") == JudgmentType.ABSTAIN
        assert JudgmentType("ABSENT") == JudgmentType.ABSENT

    def test_judgment_type_invalid_value(self) -> None:
        """無効な値でValueErrorが発生することを確認."""
        with pytest.raises(ValueError):
            JudgmentType("INVALID")


class TestParliamentaryGroupJudgeExtractionModel:
    """Test cases for ParliamentaryGroupJudgeExtraction model."""

    def test_model_creation(self) -> None:
        """モデルが正しく作成されることを確認."""
        extraction = ParliamentaryGroupJudgeExtraction(
            group_name="自民党",
            judgment=JudgmentType.FOR,
            member_count=15,
            note="全員賛成",
        )

        assert extraction.group_name == "自民党"
        assert extraction.judgment == JudgmentType.FOR
        assert extraction.member_count == 15
        assert extraction.note == "全員賛成"

    def test_model_with_optional_fields_none(self) -> None:
        """オプショナルフィールドがNoneの場合も正しく作成されることを確認."""
        extraction = ParliamentaryGroupJudgeExtraction(
            group_name="立憲民主党",
            judgment=JudgmentType.AGAINST,
        )

        assert extraction.group_name == "立憲民主党"
        assert extraction.judgment == JudgmentType.AGAINST
        assert extraction.member_count is None
        assert extraction.note is None

    def test_model_serialization(self) -> None:
        """モデルがJSON形式に正しくシリアライズされることを確認."""
        extraction = ParliamentaryGroupJudgeExtraction(
            group_name="公明党",
            judgment=JudgmentType.FOR,
            member_count=5,
            note=None,
        )

        json_dict = extraction.model_dump()

        assert json_dict["group_name"] == "公明党"
        assert json_dict["judgment"] == JudgmentType.FOR
        assert json_dict["member_count"] == 5
        assert json_dict["note"] is None

    def test_model_validation_required_fields(self) -> None:
        """必須フィールドが欠けている場合にエラーが発生することを確認."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ParliamentaryGroupJudgeExtraction(
                group_name="自民党",
                # judgment is required but missing
            )  # type: ignore
