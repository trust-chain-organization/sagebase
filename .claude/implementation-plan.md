# Issue #800 実装計画: 名寄せAgentの統合と既存フロー置き換え

## 概要

名寄せAgent（LangGraph ReActエージェント）を既存の`BAMLSpeakerMatchingService`に統合し、ハイブリッドマッチングフロー（ルールベース + Agent）を実装します。

## 前提条件

- **Issue #799 (PBI-006)**: 名寄せAgentサブグラフ実装（完了）
  - ブランチ: `origin/okodoon/nayose_agent_subgraph`
  - 実装ファイル: `src/infrastructure/external/langgraph_speaker_matching_agent.py`
  - テストファイル: `tests/infrastructure/external/test_langgraph_speaker_matching_agent.py`
  - 状態: **未マージ（mainブランチに含まれていない）**

## 問題の理解

### 現在の状況

1. **既存の実装**: `BAMLSpeakerMatchingService`
   - 場所: `src/domain/services/baml_speaker_matching_service.py`
   - 処理フロー:
     1. ルールベースマッチング（高速パス、信頼度0.9以上）
     2. BAMLマッチング（候補絞り込み → BAML関数呼び出し）
   - メソッド:
     - `find_best_match()`: 最適なマッチを見つける
     - `_rule_based_matching()`: ルールベースマッチング
     - `_filter_candidates()`: 候補を絞り込む
     - `_format_speakers_for_llm()`: LLM用にフォーマット

2. **名寄せAgent**: `SpeakerMatchingAgent`
   - 場所: `src/infrastructure/external/langgraph_speaker_matching_agent.py`（未マージ）
   - LangGraphのReActエージェントとして実装
   - ツール: `create_speaker_matching_tools()`を使用
     - `evaluate_matching_candidates`: マッチング候補を評価
     - `search_additional_info`: 追加情報を検索
     - `judge_confidence`: 信頼度を判定

### 受入条件

- [ ] `SpeakerMatchingService`に名寄せAgentが統合されている
- [ ] 既存の`find_best_match`メソッドがAgent化されている
- [ ] ルールベースマッチングとAgentマッチングのハイブリッド処理が実装されている
- [ ] 統合テストが作成されている
- [ ] パフォーマンスの劣化が許容範囲内（10%以内）である

## 実装方針

### アーキテクチャ設計

1. **サービスクラスの拡張**
   - `BAMLSpeakerMatchingService`を拡張して`SpeakerMatchingAgent`を統合
   - または、新しいサービスクラス（例: `HybridSpeakerMatchingService`）を作成

2. **ハイブリッド処理フロー**
   ```
   発言者名 → ルールベースマッチング（高速パス）
              ├─ 信頼度0.9以上 → マッチング成功
              └─ 信頼度0.9未満 → Agentマッチング
                                 ├─ Agent処理（ツール使用、反復評価）
                                 └─ 信頼度0.8以上 → マッチング成功
                                    └─ 信頼度0.8未満 → マッチング失敗
   ```

3. **Clean Architecture遵守**
   - `SpeakerMatchingAgent`はインフラストラクチャ層（`src/infrastructure/external/`）
   - サービスクラスはドメイン層（`src/domain/services/`）
   - リポジトリインターフェースを使用してデータアクセス

### 実装手順

#### Phase 1: 準備

**タスク 1.1: 名寄せAgentブランチのマージ**

- `origin/okodoon/nayose_agent_subgraph`を現在のブランチにマージする
- 以下のcommitが含まれる:
  - `fa29f790`: 名寄せAgentサブグラフ実装
  - `775490e8`: BAMLツールテストのモック化によるCI対応
  - `bfabaece`: BAMLモックのパスを修正してCI対応
  - その他のcommit（Streamlit UI、スキル追加など）
- コンフリクトの解決（もしあれば）
- テストが全てパスすることを確認

**成果物:**
- マージ済みブランチ
- `src/infrastructure/external/langgraph_speaker_matching_agent.py`が利用可能
- `tests/infrastructure/external/test_langgraph_speaker_matching_agent.py`が実行可能

**リスク:**
- マージコンフリクトの可能性（mainブランチとの差分が大きい）
- 既存のテストが失敗する可能性

#### Phase 2: サービスの拡張

**タスク 2.1: `BAMLSpeakerMatchingService`の拡張**

ファイル: `src/domain/services/baml_speaker_matching_service.py`

変更内容:
1. `SpeakerMatchingAgent`のインポート追加
2. `__init__`メソッドの拡張:
   - `llm_service`から`BaseChatModel`を取得（LangChain互換）
   - `SpeakerMatchingAgent`のインスタンスを作成
3. `find_best_match`メソッドの更新:
   - ルールベースマッチング（既存）
   - 信頼度0.9以上 → そのまま返す
   - 信頼度0.9未満 → Agentマッチングを呼び出す
   - Agentマッチング結果を`SpeakerMatch`形式に変換
4. 新しいメソッド `_agent_based_matching()`:
   - `SpeakerMatchingAgent.match()`を呼び出す
   - 結果を`SpeakerMatch`に変換

**実装例:**
```python
class BAMLSpeakerMatchingService:
    def __init__(
        self,
        llm_service: ILLMService,
        speaker_repository: SpeakerRepository,
    ):
        self.llm_service = llm_service
        self.speaker_repository = speaker_repository

        # LangChain互換のLLMを取得
        self.llm = self._get_langchain_llm(llm_service)

        # 名寄せAgentを初期化
        self.matching_agent = SpeakerMatchingAgent(
            llm=self.llm,
            speaker_repo=speaker_repository,
            # 他のリポジトリも必要に応じて追加
        )
        logger.info("BAMLSpeakerMatchingService with Agent initialized")

    async def find_best_match(
        self,
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
    ) -> SpeakerMatch:
        # 既存の発言者リストを取得
        available_speakers = await self.speaker_repository.get_all_for_matching()

        if not available_speakers:
            return SpeakerMatch(
                matched=False, confidence=0.0, reason="利用可能な発言者リストが空です"
            )

        # ルールベースマッチング（高速パス）
        rule_based_match = self._rule_based_matching(speaker_name, available_speakers)
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            logger.info(f"Rule-based match found for '{speaker_name}'")
            return rule_based_match

        # Agentマッチング
        try:
            agent_result = await self._agent_based_matching(
                speaker_name, meeting_date, conference_id
            )
            logger.info(
                f"Agent match result for '{speaker_name}': "
                f"matched={agent_result.matched}, confidence={agent_result.confidence}"
            )
            return agent_result
        except Exception as e:
            logger.error(f"Agent matching error: {e}")
            # フォールバック: BAMLマッチング（既存）
            return await self._baml_matching(speaker_name, available_speakers, ...)

    async def _agent_based_matching(
        self,
        speaker_name: str,
        meeting_date: str | None,
        conference_id: int | None,
    ) -> SpeakerMatch:
        """Agentベースのマッチング"""
        result = await self.matching_agent.match(
            speaker_name=speaker_name,
            meeting_date=meeting_date,
            conference_id=conference_id,
        )

        # SpeakerMatchingResultをSpeakerMatchに変換
        return SpeakerMatch(
            matched=result["matched"],
            speaker_id=result.get("politician_id"),
            speaker_name=result.get("politician_name"),
            confidence=result["confidence"],
            reason=result["reason"],
        )

    def _get_langchain_llm(self, llm_service: ILLMService) -> BaseChatModel:
        """ILLMServiceからLangChain互換のLLMを取得"""
        # ILLMServiceの実装に応じて適切なLLMを返す
        # 例: llm_service.get_langchain_model() など
        # または、新しいChatGoogleGenerativeAIインスタンスを作成
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash")
```

**成果物:**
- 拡張された`BAMLSpeakerMatchingService`
- ハイブリッド処理フローの実装

**リスク:**
- `ILLMService`とLangChain互換LLMの変換が複雑になる可能性
- リポジトリの依存関係が増える

**注意点:**
- BAMLマッチングをフォールバックとして残す（エラー時の保険）
- 環境変数でAgent/BAMLを切り替え可能にする（オプション）

#### Phase 3: テスト

**タスク 3.1: 統合テストの作成**

ファイル: `tests/domain/services/test_speaker_matching_service_with_agent.py`

テスト項目:
1. ルールベースマッチング（高速パス）のテスト
   - 信頼度0.9以上の場合、Agentを呼ばないこと
2. Agentマッチングのテスト
   - ルールベースが失敗した場合、Agentが呼ばれること
   - Agent結果が正しく変換されること
3. エラーハンドリングのテスト
   - Agentエラー時にBAMLフォールバックが動作すること
4. パフォーマンステスト
   - 処理時間が既存の実装と比較して10%以内の劣化であること

**成果物:**
- 統合テストファイル（全テストパス）

**リスク:**
- Agentのモック化が複雑になる可能性
- パフォーマンステストの基準設定が難しい

#### Phase 4: クリーンアップとドキュメント更新

**タスク 4.1: コードのクリーンアップ**

- 不要なコメントやデバッグコードの削除
- コーディング規約の遵守（Ruff、型チェック）
- ログ出力の整理

**タスク 4.2: ドキュメント更新**

- `src/domain/services/baml_speaker_matching_service.py`のdocstringを更新
- CLAUDE.mdのBAML統合セクションを更新（Agent統合を反映）

**成果物:**
- クリーンなコード
- 更新されたドキュメント

## タスク一覧

### Phase 1: 準備
- [ ] 1.1: 名寄せAgentブランチのマージ
  - [ ] `git merge origin/okodoon/nayose_agent_subgraph`を実行
  - [ ] コンフリクトがあれば解決
  - [ ] テストを実行して全てパスすることを確認

### Phase 2: サービスの拡張
- [ ] 2.1: `BAMLSpeakerMatchingService`の拡張
  - [ ] `SpeakerMatchingAgent`のインポート追加
  - [ ] `__init__`メソッドでAgentインスタンスを作成
  - [ ] `find_best_match`メソッドを更新（ハイブリッド処理）
  - [ ] `_agent_based_matching()`メソッドを追加
  - [ ] `_get_langchain_llm()`メソッドを追加（LLM変換）
  - [ ] 既存のBAMLマッチングをフォールバックとして残す

### Phase 3: テスト
- [ ] 3.1: 統合テストの作成
  - [ ] `tests/domain/services/test_speaker_matching_service_with_agent.py`を作成
  - [ ] ルールベースマッチングのテスト
  - [ ] Agentマッチングのテスト
  - [ ] エラーハンドリングのテスト
  - [ ] パフォーマンステスト
  - [ ] 全テストがパスすることを確認

### Phase 4: クリーンアップとドキュメント更新
- [ ] 4.1: コードのクリーンアップ
  - [ ] 不要なコメント削除
  - [ ] Ruff、pyrightでコード品質チェック
  - [ ] ログ出力の整理
- [ ] 4.2: ドキュメント更新
  - [ ] docstring更新
  - [ ] CLAUDE.md更新（Agent統合を反映）

### Phase 5: 最終確認
- [ ] 5.1: 動作確認
  - [ ] 実際の議事録データでマッチングテスト
  - [ ] パフォーマンス測定（10%以内の劣化を確認）
- [ ] 5.2: コード品質チェック
  - [ ] `uv run ruff format .`
  - [ ] `uv run ruff check . --fix`
  - [ ] `uv run pyright`
- [ ] 5.3: テストの実行
  - [ ] `uv run pytest -xvs tests/domain/services/test_speaker_matching_service_with_agent.py`
  - [ ] 全テストがパスすることを確認

## 依存関係

- **前提**: Issue #799 (PBI-006) - 名寄せAgentサブグラフ実装（完了）
- **ブロック**: PBI-008（Issue #800完了後に開始）

## 見積もり

- **開発工数**: 2日
- **複雑度**: Medium

## リスクと注意点

### 技術的リスク

1. **ブランチマージのコンフリクト**
   - 対策: マージ前に差分を確認し、慎重にマージする
   - 影響: 作業時間の増加（+2-4時間）

2. **LLMサービスの互換性**
   - 問題: `ILLMService`とLangChain `BaseChatModel`の変換
   - 対策: 既存の実装を参考にアダプタを作成
   - 影響: 実装の複雑化

3. **パフォーマンス劣化**
   - 問題: Agent処理がBAMLより遅い可能性
   - 対策: ルールベースマッチングで高速パスを維持、Agent呼び出しを最小化
   - 目標: 10%以内の劣化

### 開発上の注意点

- **Clean Architecture遵守**: ドメイン層がインフラストラクチャ層に依存しないように注意
- **テストの充実**: Agentのモック化が複雑なため、テストを慎重に設計
- **エラーハンドリング**: Agent失敗時のフォールバック処理を実装

## 成功基準

- [ ] 全ての受入条件が満たされている
- [ ] 統合テストが全てパスする
- [ ] パフォーマンスが許容範囲内（10%以内の劣化）
- [ ] コード品質チェック（Ruff、pyright）がパスする
- [ ] 既存の機能が壊れていない

## 参考情報

### 関連Issue

- Issue #799 (PBI-006): 名寄せAgentサブグラフ実装
- Issue #798 (PBI-005): 名寄せAgent用のLangGraphツール実装

### 関連ファイル

- `src/domain/services/baml_speaker_matching_service.py` - 既存のマッチングサービス
- `src/infrastructure/external/langgraph_speaker_matching_agent.py` - 名寄せAgent（未マージ）
- `src/infrastructure/external/langgraph_tools/speaker_matching_tools.py` - LangGraphツール
- `tests/domain/services/test_baml_speaker_matching_service.py` - 既存のテスト

### 技術スタック

- LangGraph: ReActエージェントフレームワーク
- BAML: 構造化出力のDSL
- LangChain: LLMインターフェース
- Google Gemini API: LLMバックエンド
