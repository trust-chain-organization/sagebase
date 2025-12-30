# LangGraph + BAML統合ガイド

LangGraphエージェントとBAMLを統合して、型安全かつ保守性の高いAIエージェントを構築するためのスキルです。

---

## Purpose（目的）

LangGraphのReActエージェントにBAMLを統合し、以下を実現します：

- **制御フローの明確化**: LangGraphで状態遷移とツール選択を管理
- **LLM通信の型安全性**: BAMLで構造化出力を保証
- **プロンプト管理の集約**: `.baml`ファイルでプロンプトを一元管理
- **テスト容易性**: BAML PlaygroundでLLM部分を独立テスト可能

---

## Activation（アクティベーション条件）

以下の場合にこのスキルを使用してください：

- ✅ LangGraphのReActエージェントを新規作成する
- ✅ 既存のLangGraphエージェントにBAMLツールを追加する
- ✅ エージェントツールの実装を改善・リファクタリングする
- ✅ LLMの構造化出力が必要なツールを実装する
- ✅ プロンプト管理を改善したい

---

## Architecture Overview（アーキテクチャ概要）

### ハイブリッド構成の原則

```
┌─────────────────────────────────────────┐
│  LangGraph (ワークフロー層)              │
│  - 状態管理 (State)                      │
│  - 制御フロー (ループ、分岐)              │
│  - ツール選択 (ReAct思考)                │
└─────────────────────────────────────────┘
              ↓ ツール呼び出し
┌─────────────────────────────────────────┐
│  BAML (LLM通信層)                        │
│  - 構造化プロンプト (.baml)              │
│  - 型安全な出力 (Pydantic互換)           │
│  - パース処理                            │
└─────────────────────────────────────────┘
```

### ツール設計の判断基準

| ツールの特性 | 推奨実装 | 理由 |
|-------------|---------|------|
| 大量データのフィルタリング | ルールベース | コスト・速度効率 |
| 単純なDB検索・取得 | ルールベース | LLM不要 |
| 複雑な判断・推論 | **BAML** | LLMの推論能力を活用 |
| 構造化データ抽出 | **BAML** | 型安全性・精度向上 |

---

## Implementation Checklist（実装チェックリスト）

### 1. BAML定義ファイルの作成

**ファイル配置**: `baml_src/<feature_name>.baml`

```baml
// 例: baml_src/speaker_matching_tools.baml

function JudgeMatchingConfidence(
  speaker_name: string,
  candidate_json: string,
  additional_info_json: string?
) -> ConfidenceJudgement {
  client Gemini2Flash
  prompt #"
    あなたは専門家です。以下のタスクを実行してください。

    ## 入力情報
    **対象名**: {{ speaker_name }}
    **候補データ** (JSON):
    {{ candidate_json }}

    {% if additional_info_json %}
    **追加情報** (JSON):
    {{ additional_info_json }}
    {% endif %}

    ## 出力要件
    **必須フィールド（すべて出力してください）:**

    1. **confidence**: 0.0〜1.0の数値
    2. **confidence_level**: レベル（"HIGH"/"MEDIUM"/"LOW"）
    3. **should_match**: マッチ推奨（boolean）
    4. **reason**: 判定理由（日本語で明確に）
    5. **contributing_factors**: 要素のリスト
    6. **recommendation**: 推奨アクション

    **重要**: 上記のすべてのフィールドを必ず出力してください。
  "#
}

class ConfidenceJudgement {
  confidence float @description("確信度 (0.0-1.0)")
  confidence_level string @description("確信度レベル (HIGH/MEDIUM/LOW)")
  should_match bool @description("マッチ推奨")
  reason string @description("判定理由")
  contributing_factors ContributingFactor[] @description("寄与要素")
  recommendation string @description("推奨アクション")
}

class ContributingFactor {
  factor string @description("要素名")
  impact float @description("影響度 (-1.0 to 1.0)")
  description string @description("説明")
}
```

**ポイント:**
- ✅ 必須フィールドを**明示的に列挙**（LLMが見落とさないように）
- ✅ プロンプト内で「**重要**」「**必ず**」などの強調語を使用
- ✅ JSON入力を受け取る場合は`string`型で受け取り、プロンプト内に展開
- ✅ オプショナルフィールドには`?`を付ける

### 2. BAMLクライアントの生成

```bash
uv run baml-cli generate
```

**確認事項:**
- ✅ `baml_client/`ディレクトリに型定義が生成される
- ✅ `baml_client/types.py`で型を確認
- ✅ `baml_client/async_client.py`と`sync_client.py`が両方存在

### 3. LangGraphツールの実装

**ファイル**: `src/infrastructure/external/langgraph_tools/<feature>_tools.py`

```python
"""LangGraph tools for <feature>.

Tools:
- tool1: Description (Rule-based)
- tool2: Description (BAML-powered)
"""

import json
import logging
from typing import Any

from langchain_core.tools import tool
from baml_client.async_client import b  # ← 非同期クライアントを使用！

logger = logging.getLogger(__name__)


@tool
async def rule_based_tool(
    input_data: str,
    max_items: int = 10,
) -> dict[str, Any]:
    """ルールベースツールの例（高速フィルタリング用）"""
    try:
        # ルールベース処理
        results = perform_filtering(input_data, max_items)
        return {
            "items": results,
            "total": len(results),
        }
    except Exception as e:
        logger.error(f"Error in rule_based_tool: {e}", exc_info=True)
        return {"items": [], "total": 0, "error": str(e)}


@tool
async def baml_powered_tool(
    input_name: str,
    candidate: dict[str, Any],
    additional_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """BAML搭載ツールの例（複雑な判断用）

    Args:
        input_name: 入力名
        candidate: 候補データ（辞書）
        additional_info: 追加情報（オプション）

    Returns:
        判定結果を含む辞書
    """
    try:
        # Input validation
        if not input_name or not input_name.strip():
            return {
                "success": False,
                "reason": "入力名が空です",
                "error": "Empty input",
            }

        # データをJSON文字列に変換（BAMLはJSONを受け取る）
        candidate_json = json.dumps(candidate, ensure_ascii=False, indent=2)
        additional_info_json = (
            json.dumps(additional_info, ensure_ascii=False, indent=2)
            if additional_info
            else None
        )

        logger.info(f"Calling BAML function for input='{input_name}'")

        # BAML関数呼び出し（awaitを忘れずに！）
        result = await b.YourBamlFunction(
            input_name=input_name,
            candidate_json=candidate_json,
            additional_info_json=additional_info_json,
        )

        # BAML結果を辞書に変換
        return {
            "success": result.success,
            "confidence": result.confidence,
            "confidence_level": result.confidence_level.lower(),
            "reason": result.reason,
            "recommendation": result.recommendation,
        }

    except Exception as e:
        logger.error(f"Error in baml_powered_tool: {e}", exc_info=True)
        return {
            "success": False,
            "reason": f"処理中にエラー: {str(e)}",
            "error": str(e),
        }
```

**重要なポイント:**

1. **非同期クライアントのインポート**
   ```python
   from baml_client.async_client import b  # ← async_client!
   # ❌ from baml_client import b  # これは同期版
   ```

2. **JSON変換**
   - 辞書データは`json.dumps()`でJSON文字列化
   - `ensure_ascii=False`で日本語を保持
   - `indent=2`でLLMが読みやすい形式に

3. **エラーハンドリング**
   - 必ず`try-except`でラップ
   - エラー時も構造化した辞書を返す
   - ログに詳細を記録（`exc_info=True`）

4. **戻り値の変換**
   - BAMLの結果を辞書に変換して返す
   - `confidence_level.lower()`で統一形式に

### 4. LangGraphエージェントの実装

**ファイル**: `src/infrastructure/external/langgraph_<feature>_agent.py`

```python
"""<Feature> Agent実装

LangGraphのReActエージェントを使用した高精度な処理を実現します。
"""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

from src.infrastructure.external.langgraph_tools.your_tools import (
    create_your_tools,
)

logger = logging.getLogger(__name__)

# 最大ReActステップ数
MAX_REACT_STEPS = 10

# 閾値などの定数
THRESHOLD = 0.8


class YourAgentState(TypedDict):
    """エージェント固有の状態定義

    LangGraphのサブグラフとして動作するために必要な状態を定義します。
    ReActエージェントの要件として `messages` と `remaining_steps` が必須です。
    """

    # 入力データ
    input_name: str  # 入力対象
    context_date: str | None  # コンテキスト日付（オプション）

    # 処理中のデータ
    candidates: list[dict[str, Any]]  # 候補リスト
    best_result: dict[str, Any] | None  # 最良結果

    # ReAct必須フィールド（これらは絶対に必要！）
    messages: Annotated[list[BaseMessage], add_messages]  # エージェントメッセージ履歴
    remaining_steps: int  # ReActエージェントの残りステップ数

    # エラーハンドリング
    error_message: str | None  # エラーメッセージ


class YourAgentResult(TypedDict):
    """処理結果の型定義"""

    success: bool  # 処理が成功したか
    result_data: dict[str, Any] | None  # 結果データ
    confidence: float  # 確信度（0.0-1.0）
    reason: str  # 処理結果の理由
    error_message: str | None  # エラーメッセージ（エラー時のみ）


class YourAgent:
    """<Feature>用のReActエージェント

    LangGraphのサブグラフとして動作し、ツールを使用した試行錯誤により
    高精度な処理を実現します。

    Attributes:
        llm: 使用するLangChainチャットモデル
        tools: 処理用のツールリスト
        agent: コンパイル済みのReActエージェント
    """

    def __init__(
        self,
        llm: BaseChatModel,
        # リポジトリなどの依存性
        data_repo: Any = None,
    ):
        """エージェントを初期化

        Args:
            llm: LangChainのチャットモデル（例: ChatGoogleGenerativeAI）
            data_repo: データリポジトリ（オプション）
        """
        self.llm = llm
        self.tools = create_your_tools(data_repo=data_repo)
        self.agent = self._create_workflow()
        logger.info(f"YourAgent initialized with {len(self.tools)} tools")

    def _create_workflow(self):
        """ReActグラフを構築

        Returns:
            コンパイル済みのReActエージェント（サブグラフとして使用可能）
        """
        system_prompt = f"""あなたは<Feature>を専門とするエージェントです。

あなたの役割:
1. 入力データから最適な結果を見つける
2. 提供されたツールを使用して候補を評価し、確信度を判定する
3. 高精度な処理のために試行錯誤を行う

利用可能なツール:
- tool1: ツール1の説明
- tool2: ツール2の説明（BAML搭載）

処理の判断基準:
- 基準1: 説明
- 基準2: 説明
- 確信度{THRESHOLD}以上の結果のみを採用

推奨される手順:
1. tool1で候補を取得
2. 上位候補に対してtool2で詳細評価
3. 確信度が{THRESHOLD}以上なら成功、なければ失敗
"""

        logger.info("Creating ReAct workflow")

        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            state_schema=YourAgentState,
            prompt=system_prompt,
        )

    def compile(self):
        """サブグラフとして使用可能な形にコンパイル

        Returns:
            コンパイル済みエージェント
        """
        logger.debug("Compiling agent as subgraph")
        return self.agent

    async def process(
        self,
        input_name: str,
        context_date: str | None = None,
    ) -> YourAgentResult:
        """処理を実行

        Args:
            input_name: 入力名
            context_date: コンテキスト日付（オプション）

        Returns:
            処理結果
        """
        logger.info(f"Starting process for '{input_name}' (date={context_date})")

        # タスク指示メッセージを作成（重要！空だとエラーになる）
        task_description = f"'{input_name}'を処理してください。"
        if context_date:
            task_description += f"\nコンテキスト日付: {context_date}"

        initial_state: YourAgentState = {
            "input_name": input_name,
            "context_date": context_date,
            "candidates": [],
            "best_result": None,
            "messages": [HumanMessage(content=task_description)],  # ← 必須！
            "remaining_steps": MAX_REACT_STEPS,
            "error_message": None,
        }

        try:
            result = await self.agent.ainvoke(initial_state)

            # 結果から最良結果を抽出
            best_result = result.get("best_result")

            if best_result and best_result.get("confidence", 0.0) >= THRESHOLD:
                logger.info(f"Process completed successfully")
                return YourAgentResult(
                    success=True,
                    result_data=best_result,
                    confidence=best_result.get("confidence", 0.0),
                    reason=best_result.get("reason", ""),
                    error_message=None,
                )
            else:
                logger.info("Process completed with no result")
                return YourAgentResult(
                    success=False,
                    result_data=None,
                    confidence=0.0,
                    reason="確信度が閾値に達しませんでした",
                    error_message=None,
                )

        except Exception as e:
            logger.error(f"Error during process: {str(e)}", exc_info=True)
            return YourAgentResult(
                success=False,
                result_data=None,
                confidence=0.0,
                reason="",
                error_message=f"処理中にエラーが発生しました: {str(e)}",
            )
```

**重要なポイント:**

1. **初期メッセージは必須**
   ```python
   "messages": [HumanMessage(content=task_description)],  # 空だとエラー！
   ```

2. **State定義の必須フィールド**
   - `messages: Annotated[list[BaseMessage], add_messages]`
   - `remaining_steps: int`

3. **システムプロンプトの設計**
   - 役割を明確に
   - ツールの説明
   - 推奨手順を提示

### 5. テストの実装

**ファイル**: `tests/infrastructure/external/test_langgraph_<feature>_agent.py`

```python
"""YourAgent のユニットテスト"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel

from src.infrastructure.external.langgraph_your_agent import (
    YourAgent,
    YourAgentState,
)


class TestYourAgent:
    """YourAgent のテストケース"""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """モックLLMを作成"""
        mock = MagicMock(spec=BaseChatModel)
        return mock

    @pytest.fixture
    def agent(self, mock_llm: MagicMock) -> YourAgent:
        """エージェントインスタンスを作成"""
        return YourAgent(llm=mock_llm)

    def test_initialization(self, agent: YourAgent) -> None:
        """エージェントの初期化テスト"""
        assert agent.llm is not None
        assert len(agent.tools) > 0
        assert agent.agent is not None

    @pytest.mark.asyncio
    async def test_process_success(self, agent: YourAgent) -> None:
        """正常な処理のテスト"""
        input_name = "テスト入力"

        # エージェントの実行をモック
        mock_result = {
            "input_name": input_name,
            "best_result": {
                "confidence": 0.95,
                "reason": "高確信度",
            },
            "error_message": None,
        }

        with patch.object(
            agent.agent, "ainvoke", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await agent.process(input_name)

            assert result["success"] is True
            assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_process_handles_exception(self, agent: YourAgent) -> None:
        """例外処理のテスト"""
        with patch.object(
            agent.agent,
            "ainvoke",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ):
            result = await agent.process("test")

            assert result["success"] is False
            assert result["error_message"] is not None
```

**ツールテストの例:**

```python
"""Tools のテスト"""

import pytest


class TestBamlPoweredTool:
    """BAML搭載ツールのテスト（LLMを実際に呼び出す統合テスト）"""

    @pytest.mark.asyncio
    async def test_high_confidence_case(self, tools):
        """高確信度ケースのテスト"""
        tool = tools[1]  # BAML搭載ツール

        candidate = {
            "id": 101,
            "name": "テスト候補",
            "score": 1.0,
        }

        result = await tool.ainvoke(
            {
                "input_name": "テスト",
                "candidate": candidate,
            }
        )

        assert "error" not in result
        # LLMは柔軟に判断するため、範囲チェック
        assert result["confidence"] >= 0.8
        assert result["confidence_level"] in ("medium", "high")
        assert result["success"] is True
```

**テストのポイント:**

- ✅ エージェント自体は`ainvoke`をモック（高速化）
- ✅ BAML搭載ツールは実際のLLM呼び出しを許容（統合テスト）
- ✅ LLMの柔軟な判断を受け入れる（固定値期待を避ける）
- ✅ エラーケースも必ずテスト

---

## Common Pitfalls（よくある落とし穴）

### 1. ❌ 同期クライアントを使ってしまう

```python
# ❌ 間違い
from baml_client import b  # これは sync_client

# ✅ 正しい
from baml_client.async_client import b
```

**エラー**: `object ConfidenceJudgement can't be used in 'await' expression`

### 2. ❌ 初期メッセージが空

```python
# ❌ 間違い
initial_state = {
    "messages": [],  # 空！
    ...
}

# ✅ 正しい
initial_state = {
    "messages": [HumanMessage(content="タスク指示")],
    ...
}
```

**エラー**: `GenerateContentRequest.contents: contents is not specified`

### 3. ❌ 必須フィールドをLLMが出力しない

```baml
# ❌ プロンプトで明示していない
prompt #"
    確信度を判定してください。
"#

# ✅ 必須フィールドを明示
prompt #"
    ## 出力要件
    **必須フィールド（すべて出力してください）:**
    1. **confidence**: 数値
    2. **confidence_level**: レベル

    **重要**: 上記のすべてのフィールドを必ず出力してください。
"#
```

**エラー**: `Missing required field: confidence_level`

### 4. ❌ 辞書をそのままBAMLに渡す

```python
# ❌ 間違い
result = await b.Function(candidate=candidate_dict)

# ✅ 正しい
candidate_json = json.dumps(candidate_dict, ensure_ascii=False, indent=2)
result = await b.Function(candidate_json=candidate_json)
```

### 5. ❌ テストで固定値を期待

```python
# ❌ LLMは毎回違う値を返す可能性がある
assert result["confidence"] == 0.95

# ✅ 範囲チェック
assert result["confidence"] >= 0.8
assert result["confidence_level"] in ("medium", "high")
```

---

## Best Practices（ベストプラクティス）

### 1. ツール設計の原則

```python
# ✅ 高速パス + LLMパスのハイブリッド
async def smart_matching_tool(input_name: str):
    # 1. ルールベースで上位候補をフィルタ（高速）
    candidates = rule_based_filter(input_name, top_k=10)

    # 2. 上位候補のみLLMで詳細評価（コスト効率）
    for candidate in candidates[:3]:
        result = await b.JudgeCandidate(
            input_name=input_name,
            candidate_json=json.dumps(candidate),
        )
        if result.confidence >= 0.8:
            return result

    return None  # マッチなし
```

### 2. エラーハンドリング

```python
@tool
async def robust_tool(...) -> dict[str, Any]:
    try:
        # メイン処理
        result = await b.Function(...)

        return {
            "success": True,
            "data": result.data,
        }

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        # 構造を保って返す
        return {
            "success": False,
            "data": None,
            "error": str(e),
        }
```

### 3. ログ出力

```python
# ✅ 処理の各段階でログ
logger.info(f"Starting process for '{input_name}'")
logger.info(f"Calling BAML function")
logger.info(f"Process completed successfully with confidence={result.confidence}")

# ❌ ログなし or デバッグログのみ
# （本番環境でトラブルシュート困難）
```

### 4. 型定義の活用

```python
# ✅ TypedDictで明確な型定義
class AgentState(TypedDict):
    input_name: str
    candidates: list[dict[str, Any]]
    messages: Annotated[list[BaseMessage], add_messages]
    remaining_steps: int

# ❌ Anyや辞書で曖昧に
state: dict[str, Any] = {...}
```

---

## Quick Reference（クイックリファレンス）

### ファイル構成

```
project/
├── baml_src/
│   └── feature_name.baml          # BAML定義
├── baml_client/                   # 自動生成（git管理）
│   ├── async_client.py
│   └── types.py
├── src/infrastructure/external/
│   ├── langgraph_tools/
│   │   └── feature_tools.py       # ツール実装
│   └── langgraph_feature_agent.py # エージェント実装
└── tests/infrastructure/external/
    ├── langgraph_tools/
    │   └── test_feature_tools.py  # ツールテスト
    └── test_langgraph_feature_agent.py  # エージェントテスト
```

### コマンド

```bash
# BAML定義を編集したら必ず実行
uv run baml-cli generate

# テスト実行
uv run pytest tests/infrastructure/external/test_langgraph_feature_agent.py -v

# コード品質チェック
uv run --frozen ruff format .
uv run --frozen ruff check . --fix
uv run --frozen pyright
```

### インポートテンプレート

```python
# LangGraphエージェント
from typing import Annotated, Any, TypedDict
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent

# BAML
from baml_client.async_client import b

# ツール
from langchain_core.tools import tool
```

---

## Examples（実装例）

実装例は以下を参照してください：

- **エージェント実装**: `src/infrastructure/external/langgraph_speaker_matching_agent.py`
- **ツール実装**: `src/infrastructure/external/langgraph_tools/speaker_matching_tools.py`
- **BAML定義**: `baml_src/speaker_matching_tools.baml`
- **テスト**: `tests/infrastructure/external/test_langgraph_speaker_matching_agent.py`

---

## Troubleshooting（トラブルシューティング）

### Q: BAML関数が見つからない

```
AttributeError: module 'baml_client' has no attribute 'YourFunction'
```

**解決策**: `uv run baml-cli generate`を実行してクライアントを再生成

### Q: LLMが必須フィールドを出力しない

```
BamlValidationError: Missing required field: field_name
```

**解決策**: プロンプトで必須フィールドを明示的に列挙し、「必ず出力してください」と強調

### Q: テストでLLMの出力が不安定

**解決策**: 固定値期待ではなく、範囲チェックや意図の確認に変更

```python
# Before
assert result["recommendation"] == "マッチング非推奨"

# After
assert any(word in result["recommendation"] for word in ["非推奨", "別の候補"])
```

---

このスキルを活用して、型安全で保守性の高いLangGraph + BAMLエージェントを構築してください！
