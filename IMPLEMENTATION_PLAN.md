# Issue #797 実装計画: 発言抽出AgentをMinutesProcessAgentに統合

## 1. 問題の理解

### Issue概要
- **タイトル**: [PBI-004] 発言抽出AgentをMinutesProcessAgentに統合
- **目的**: Issue #796 で実装された発言抽出Agent（SpeechExtractionAgent）をMinutesProcessAgentのParent Graphにサブグラフノードとして統合する

### 受入条件
- [ ] MinutesProcessAgentに発言抽出Agentノードが追加されている
- [ ] エッジとフロー制御が適切に設定されている
- [ ] 既存の`detect_attendee_boundary`と`split_minutes_by_boundary`がAgent化されている
- [ ] 統合テストが作成されている
- [ ] パフォーマンスの劣化が許容範囲内（10%以内）である

## 2. コードベース調査の結果

### SpeechExtractionAgent (Issue #796で実装済み)
**場所**: `src/infrastructure/external/langgraph_speech_extraction_agent.py`

**機能**:
- ReActエージェントとして実装
- 議事録から発言境界を検出・検証
- 3つのツール使用:
  - `validate_boundary_candidate`: 境界候補の妥当性検証
  - `analyze_context`: 境界周辺のコンテキスト分析
  - `verify_boundary`: 最終的な境界検証

**主要メソッド**:
```python
async def extract_boundaries(minutes_text: str) -> BoundaryExtractionResult
def compile() -> CompiledAgent  # サブグラフとして使用可能
```

**状態**:
```python
class SpeechExtractionAgentState(TypedDict):
    minutes_text: str
    boundary_candidates: list[int]
    verified_boundaries: list[VerifiedBoundary]
    current_position: int
    messages: Annotated[list[BaseMessage], add_messages]
    remaining_steps: int
    error_message: str | None
```

### MinutesProcessAgent (既存実装)
**場所**: `src/minutes_divide_processor/minutes_process_agent.py`

**現在のフロー**:
```
process_minutes → divide_minutes_to_keyword → divide_minutes_to_string
→ check_length → divide_speech (loop) → END
```

**現在の境界検出処理** (`_process_minutes`メソッド内):
```python
# 出席者情報と発言部分の境界を検出して分割
boundary = await self.minutes_divider.detect_attendee_boundary(processed_minutes)
_, speech_part = self.minutes_divider.split_minutes_by_boundary(processed_minutes, boundary)
```

**状態**:
```python
class MinutesProcessState(BaseModel):
    original_minutes: str
    processed_minutes_memory_id: str
    section_info_list: Annotated[list[SectionInfo], operator.add]
    section_string_list_memory_id: str
    # ... その他のフィールド
```

### BAMLMinutesDivider
**場所**: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py`

**関連メソッド**:
- `detect_attendee_boundary(minutes_text)`: BAML使用で境界検出
- `split_minutes_by_boundary(minutes_text, boundary)`: 境界で分割

## 3. 技術的な解決策

### 統合アプローチの選択

**検討した選択肢**:

#### 選択肢A: 直接メソッド呼び出し（採用）
```python
# 新ノード内でSpeechExtractionAgentのメソッドを呼び出す
result = await self.speech_extraction_agent.extract_boundaries(minutes_text)
```

**メリット**:
- 実装がシンプル
- 状態管理が明確
- デバッグが容易

**デメリット**:
- サブグラフの再利用性が低い

#### 選択肢B: LangGraphサブグラフ統合
```python
# サブグラフとしてノードに追加（状態変換が必要）
workflow.add_node("speech_extraction", speech_extraction_agent.compile())
```

**メリット**:
- 真のサブグラフとして動作
- LangGraphの機能を最大限活用

**デメリット**:
- 状態スキーマが異なるため、状態変換関数が必要
- 実装が複雑

**決定**: 選択肢Aを採用
- Issueの要件「ノードとして追加」を満たしつつ、実装の複雑さを抑える
- 将来的に選択肢Bへの移行も可能

### 実装設計

#### 1. MinutesProcessState の拡張

新しいフィールドを追加:
```python
class MinutesProcessState(BaseModel):
    # ... 既存フィールド
    boundary_extraction_result_memory_id: str = Field(
        default="",
        description="発言境界抽出結果を保存したメモリID"
    )
```

#### 2. MinutesProcessAgent の更新

**新しいノードの追加**:
```python
async def _extract_speech_boundary(self, state: MinutesProcessState) -> dict[str, str]:
    """発言境界を抽出（SpeechExtractionAgentを使用）"""
    # 前処理済み議事録を取得
    memory_data = self._get_from_memory("processed_minutes", state.processed_minutes_memory_id)
    processed_minutes = memory_data["processed_minutes"]

    # SpeechExtractionAgentで境界抽出
    boundary_result = await self.speech_extraction_agent.extract_boundaries(processed_minutes)

    # 境界で分割（既存のsplit_minutes_by_boundaryを活用）
    # ※ BoundaryExtractionResultからMinutesBoundaryへの変換が必要
    boundary = self._convert_boundary_result(boundary_result)
    _, speech_part = self.minutes_divider.split_minutes_by_boundary(processed_minutes, boundary)

    # メモリに保存
    memory = {"boundary_result": boundary_result, "speech_part": speech_part}
    memory_id = self._put_to_memory("boundary_extraction", memory)

    return {"boundary_extraction_result_memory_id": memory_id}
```

**グラフの再設計**:
```python
def _create_graph(self) -> Any:
    workflow = StateGraph(MinutesProcessState)
    checkpointer = MemorySaver()

    # ノードの追加
    workflow.add_node("process_minutes", self._process_minutes)
    workflow.add_node("extract_speech_boundary", self._extract_speech_boundary)  # 新規
    workflow.add_node("divide_minutes_to_keyword", self._divide_minutes_to_keyword)
    # ... その他のノード

    # エッジの設定（フロー変更）
    workflow.set_entry_point("process_minutes")
    workflow.add_edge("process_minutes", "extract_speech_boundary")  # 変更
    workflow.add_edge("extract_speech_boundary", "divide_minutes_to_keyword")  # 新規
    workflow.add_edge("divide_minutes_to_keyword", "divide_minutes_to_string")
    # ... その他のエッジ
```

**_process_minutes の簡素化**:
```python
async def _process_minutes(self, state: MinutesProcessState) -> dict[str, str]:
    """議事録の前処理のみを行う（境界検出はextract_speech_boundaryに移譲）"""
    processed_minutes = self.minutes_divider.pre_process(state.original_minutes)

    memory = {"processed_minutes": processed_minutes}
    memory_id = self._put_to_memory(namespace="processed_minutes", memory=memory)
    return {"processed_minutes_memory_id": memory_id}
```

**境界結果の変換関数**:
```python
def _convert_boundary_result(
    self, boundary_result: BoundaryExtractionResult
) -> MinutesBoundary:
    """BoundaryExtractionResultをMinutesBoundaryに変換"""
    if not boundary_result["verified_boundaries"]:
        return MinutesBoundary(
            boundary_found=False,
            boundary_text=None,
            boundary_type="none",
            confidence=0.0,
            reason="境界が検出されませんでした"
        )

    # 最も信頼度の高い境界を使用
    best_boundary = max(
        boundary_result["verified_boundaries"],
        key=lambda b: b["confidence"]
    )

    return MinutesBoundary(
        boundary_found=True,
        boundary_text=f"｜境界｜ (position: {best_boundary['position']})",
        boundary_type=best_boundary["boundary_type"],  # type: ignore
        confidence=best_boundary["confidence"],
        reason=f"Agent検出: {best_boundary['boundary_type']}"
    )
```

#### 3. SpeechExtractionAgent の初期化

```python
class MinutesProcessAgent:
    def __init__(
        self,
        llm_service: ILLMService | InstrumentedLLMService | None = None,
        k: int | None = None,
    ):
        # 既存の初期化
        self.minutes_divider = MinutesDividerFactory.create(
            llm_service=llm_service, k=k or 5
        )

        # SpeechExtractionAgentの初期化
        # ※ LLMモデルのインスタンス化が必要
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
        self.speech_extraction_agent = SpeechExtractionAgent(llm)

        # グラフ初期化
        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()
```

## 4. 実装タスク

### Phase 1: 基本統合
1. **MinutesProcessState の拡張**
   - `boundary_extraction_result_memory_id` フィールド追加
   - models.py を更新

2. **MinutesProcessAgent の更新**
   - `_extract_speech_boundary` ノードメソッド追加
   - `_convert_boundary_result` ヘルパーメソッド追加
   - `__init__` で SpeechExtractionAgent を初期化
   - `_create_graph` でノードとエッジを更新
   - `_process_minutes` を簡素化（境界検出ロジック削除）

3. **既存機能の保持**
   - `divide_minutes_to_keyword` で境界抽出結果を使用するよう更新
   - メモリアクセスの調整

### Phase 2: テスト実装
4. **統合テストの作成**
   - `tests/minutes_divide_processor/test_minutes_process_agent_with_subgraph.py`
   - 基本的な境界検出フロー
   - エラーハンドリング
   - メモリ管理の検証

5. **既存テストの更新**
   - 既存のMinutesProcessAgentテストを確認・更新
   - モックの調整が必要な場合は対応

### Phase 3: 検証とパフォーマンステスト
6. **機能検証**
   - 実際の議事録データで動作確認
   - 境界検出精度の確認
   - エラーケースの確認

7. **パフォーマンステスト**
   - 既存実装との比較（10%以内の劣化を確認）
   - LLM呼び出し回数の確認
   - 処理時間の測定

## 5. 変更ファイル一覧

### 修正
- `src/minutes_divide_processor/models.py`
  - MinutesProcessState への新フィールド追加

- `src/minutes_divide_processor/minutes_process_agent.py`
  - __init__ の更新（SpeechExtractionAgent初期化）
  - _create_graph の更新（ノード・エッジ追加）
  - _process_minutes の簡素化
  - _extract_speech_boundary の追加
  - _convert_boundary_result の追加

### 新規作成
- `tests/minutes_divide_processor/test_minutes_process_agent_with_subgraph.py`
  - 統合テスト

## 6. リスクと注意点

### リスク
1. **LLM呼び出しの増加**
   - SpeechExtractionAgentはReActパターンを使用（最大10ステップ）
   - パフォーマンスへの影響を監視

2. **状態管理の複雑化**
   - メモリベースの状態管理が増加
   - デバッグの難易度上昇

3. **既存テストへの影響**
   - エッジとフローの変更により、既存テストが失敗する可能性

### 対策
1. **パフォーマンス対策**
   - 必要に応じてReActステップ数を調整
   - キャッシング機能の検討

2. **デバッグ支援**
   - 詳細なログ出力
   - 境界検出結果の可視化

3. **段階的な移行**
   - まず新フローを実装
   - 既存フローとの比較テスト
   - 問題なければ既存フローを削除

## 7. 実装順序

1. ✅ **調査フェーズ** (完了)
   - Issue内容の理解
   - コードベースの調査
   - 実装計画の作成

2. **Phase 1: 基本統合** (推定: 2-3時間)
   - MinutesProcessState 拡張
   - MinutesProcessAgent 更新
   - 基本動作確認

3. **Phase 2: テスト** (推定: 1-2時間)
   - 統合テスト作成
   - 既存テスト更新

4. **Phase 3: 検証** (推定: 1時間)
   - 機能検証
   - パフォーマンステスト
   - ドキュメント更新

## 8. 質問事項

実装を開始する前に、以下の点について確認させてください：

### Q1: SpeechExtractionAgentの利用方法
現在の計画では、SpeechExtractionAgentを直接メソッド呼び出しで使用する設計（選択肢A）としています。これは実装がシンプルですが、LangGraphのサブグラフ機能を直接活用していません。

**選択肢A（推奨）**: 直接メソッド呼び出し
- `await self.speech_extraction_agent.extract_boundaries(...)`
- シンプルで実装が容易

**選択肢B**: LangGraphサブグラフとして統合
- 状態変換関数が必要
- より複雑だが、LangGraphの機能を最大限活用

どちらを採用すべきでしょうか？

### Q2: 既存の境界検出との関係
既存の `BAMLMinutesDivider.detect_attendee_boundary()` は引き続き維持されます。これは以下の理由からです：
- 後方互換性
- 他の箇所で使用されている可能性

ただし、MinutesProcessAgent では SpeechExtractionAgent を優先的に使用します。この方針で問題ないでしょうか？

### Q3: LLMモデルの初期化
SpeechExtractionAgent の初期化には LangChain の ChatModel インスタンスが必要です。現在の計画では：

```python
from langchain_google_genai import ChatGoogleGenerativeAI
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
self.speech_extraction_agent = SpeechExtractionAgent(llm)
```

この実装で問題ないでしょうか？それとも、既存の `llm_service` を変換して使用すべきでしょうか？

---

以上の実装計画でよろしければ、実装を開始いたします。
変更が必要な箇所や、追加の考慮事項があればお知らせください。
