# Issue #825 実装計画: Phase 4 - テストとドキュメント整備

## 問題の理解

Clean Architecture移行のPhase 4として、各層のテストカバレッジ向上とアーキテクチャドキュメントの整備を行う。

### 現状分析

#### テスト状況
- **全体カバレッジ**: 69.8%（目標: 80%以上、不足: 10.2%）
- **テスト結果**: 2076テスト中、2009成功、6失敗、35スキップ、26エラー
- **主要な問題**:
  - エンティティテストが13個不足
  - Repository Implテストが10個不足
  - 一部のDomain Serviceテストが不足
  - 統合テストのエラーが26個

#### ドキュメント状況
- **既存**:
  - `docs/ARCHITECTURE.md`: 基本構造記載 ✓
  - `docs/CLEAN_ARCHITECTURE_MIGRATION.md`: Phase 3まで記載 ✓
  - `docs/architecture/clean-architecture.md` ✓
  - `docs/architecture/database-design.md` ✓
  - `docs/ADR/001-langgraph-adapter-pattern.md` ✓

- **不足**:
  - 各層の詳細ガイド（DOMAIN_LAYER.md等）4個
  - ADR（Architecture Decision Records）3個
  - `docs/DEVELOPMENT_GUIDE.md`: 完全に不足

### 受入条件（Issue記載）
- [ ] すべての層で80%以上のテストカバレッジ
- [ ] すべてのユニットテストが成功
- [ ] すべての統合テストが成功
- [ ] 各層の詳細ガイドが存在
- [ ] 主要なアーキテクチャ決定がADRとして記録
- [ ] 開発者ガイドが最新状態
- [ ] READMEにClean Architectureの説明とリンク

---

## コードベース調査結果

### 不足しているテスト

#### 1. Domain Layer（エンティティ）
不足している13個のエンティティテスト：
1. `test_conference.py` - Conference エンティティ
2. `test_conversation.py` - Conversation エンティティ
3. `test_data_coverage_stats.py` - DataCoverageStats エンティティ
4. `test_extracted_party_member.py` - ExtractedPartyMember エンティティ
5. `test_meeting.py` - Meeting エンティティ
6. `test_minutes.py` - Minutes エンティティ
7. `test_parliamentary_group.py` - ParliamentaryGroup エンティティ
8. `test_parliamentary_group_membership.py` - ParliamentaryGroupMembership エンティティ
9. `test_party_scraping_state.py` - PartySc rapingState エンティティ（一部存在）
10. `test_political_party.py` - PoliticalParty エンティティ
11. `test_politician.py` - Politician エンティティ
12. `test_politician_party_extracted_politician.py` - PoliticianPartyExtractedPolitician エンティティ
13. `test_proposal_parliamentary_group_judge.py` - ProposalParliamentaryGroupJudge エンティティ

#### 2. Domain Layer（サービス）
不足している1個のドメインサービステスト：
1. `test_party_member_extraction_service.py` - PartyMemberExtractionService

#### 3. Infrastructure Layer（リポジトリ実装）
不足している10個のリポジトリ実装テスト：
1. `test_extracted_conference_member_repository_impl.py`
2. `test_governing_body_repository_impl.py`
3. `test_meeting_repository_impl.py`
4. `test_minutes_repository_impl.py`
5. `test_parliamentary_group_repository_impl.py`（統合テストには存在）
6. `test_political_party_repository_impl.py`（統合テストには存在）
7. `test_politician_affiliation_repository_impl.py`
8. `test_politician_repository_impl.py`（`tests/infrastructure/`に存在する可能性）
9. `test_prompt_version_repository_impl.py`
10. `test_proposal_parliamentary_group_judge_repository_impl.py`

#### 4. 統合テストのエラー
26個のエラーが発生している統合テスト：
- `test_monitoring_repository.py`: 8エラー
- `test_political_party_repository.py`: 6エラー
- `test_parliamentary_group_repository_integration.py`: 12エラー

### 不足しているドキュメント

#### 1. アーキテクチャ詳細ドキュメント（4個）
1. `docs/architecture/DOMAIN_LAYER.md` - ドメイン層の詳細ガイド
2. `docs/architecture/APPLICATION_LAYER.md` - アプリケーション層の詳細ガイド
3. `docs/architecture/INFRASTRUCTURE_LAYER.md` - インフラ層の詳細ガイド
4. `docs/architecture/INTERFACE_LAYER.md` - インターフェース層の詳細ガイド

#### 2. ADR（Architecture Decision Records）（3個）
1. `docs/ADR/0001-clean-architecture-adoption.md` - Clean Architecture採用の経緯と理由
2. `docs/ADR/0002-baml-for-llm-outputs.md` - BAML使用の決定
3. `docs/ADR/0003-repository-pattern.md` - リポジトリパターンの実装方針

#### 3. 開発者ガイド（1個）
1. `docs/DEVELOPMENT_GUIDE.md` - Clean Architecture準拠の開発手順

---

## 技術的な解決策

### テスト戦略

#### 1. エンティティテスト
- **目的**: エンティティのバリデーションロジックとビジネスルールのテスト
- **アプローチ**:
  - 各エンティティの初期化とバリデーション
  - 不正なデータでの例外発生の確認
  - エンティティのメソッドのロジック検証
- **使用ツール**: pytest, pytest-asyncio

#### 2. ドメインサービステスト
- **目的**: ドメインロジックの正確性の検証
- **アプローチ**:
  - リポジトリをモック化してサービスロジックのみテスト
  - ビジネスルールの検証
  - エッジケースの処理
- **使用ツール**: pytest, pytest-mock, unittest.mock

#### 3. リポジトリ実装テスト
- **目的**: データアクセス層の正確性の検証
- **アプローチ**:
  - テスト用データベースを使用した統合テスト
  - CRUD操作の検証
  - トランザクション処理の確認
  - エラーハンドリングの検証
- **使用ツール**: pytest, pytest-asyncio, SQLAlchemy

#### 4. 統合テストの修正
- **目的**: 既存の失敗・エラーテストの修正
- **アプローチ**:
  - エラーの原因特定（依存関係、設定、データベーススキーマ等）
  - 適切な修正または無効化（Issue作成）
- **優先度**: 高（26エラーの解消が必須）

### ドキュメント戦略

#### 1. 各層の詳細ガイド
- **内容**:
  - 層の責務と境界
  - 実装パターンとベストプラクティス
  - コード例
  - よくある落とし穴と回避方法
  - チェックリスト

#### 2. ADR（Architecture Decision Records）
- **フォーマット**:
  - Context（背景）
  - Decision（決定内容）
  - Consequences（結果・影響）
  - Alternatives Considered（検討した代替案）
- **保存場所**: `docs/ADR/`

#### 3. 開発者ガイド
- **内容**:
  - Clean Architecture概要
  - 開発環境のセットアップ
  - 新規機能開発の手順
  - テスト作成のガイドライン
  - コーディング規約
  - トラブルシューティング

---

## 実装計画

このIssueは非常に大規模なため、段階的に実装します。

### フェーズ分割戦略

#### フェーズ0: 未使用コードの大掃除（Week 1）
**目標**: プロジェクト全体の未使用コードを削除し、クリーンで保守しやすい状態にする

**背景**:
- Issue #822、#824でほとんどのレガシーコードは削除済み
- しかし、調査により**33個の未使用モジュール**が検出された
- 古いStreamlitコンポーネント、空のディレクトリ、refactoredファイルなどが残存
- 未使用コードが残っているとテストカバレッジ計算に影響し、混乱を招く
- コードベースが肥大化し、メンテナンスコストが増加

**調査結果: 未使用コード一覧（33個）**

### 1. Streamlit関連（8個）- 確実に未使用

- [ ] `src/interfaces/web/streamlit/views/error_404_view.py` - エラーページ（未使用）
- [ ] `src/interfaces/web/streamlit/components/charts/` - 空ディレクトリ
- [ ] `src/interfaces/web/streamlit/components/forms/` - 空ディレクトリ
- [ ] `src/interfaces/web/streamlit/components/tables/` - 空ディレクトリ
- [ ] `src/interfaces/web/streamlit/dto/request/` - 空ディレクトリ
- [ ] `src/interfaces/web/streamlit/dto/response/` - 空ディレクトリ
- [ ] `src/interfaces/web/streamlit/health.py` - ヘルスチェック（未統合）
- [ ] `src/interfaces/web/streamlit/middleware/cloudflare_auth.py` - Cloudflare認証（未使用）

### 2. Infrastructure層（6個）- 要確認

- [ ] `src/infrastructure/persistence/llm_history_helper.py` - 同期版LLM履歴ヘルパー（0インポート）
- [ ] `src/infrastructure/persistence/optimized_politician_repository.py` - 最適化版リポジトリ（未使用？）
- [ ] `src/infrastructure/persistence/proposal_parliamentary_group_judge_repository_impl.py` - 未実装？
- [ ] `src/infrastructure/external/langgraph_nodes/extract_members_node.py` - 古いLangGraphノード
- [ ] `src/infrastructure/external/llm_service_factory.py` - 古いファクトリー
- [ ] `src/infrastructure/logging/formatters.py` - カスタムフォーマッター（未使用）

### 3. Domain層（2個）

- [ ] `src/domain/entities/extracted_party_member.py` - 抽出済み政党メンバー（未使用？）
- [ ] `src/domain/types/common.py` - 共通型定義（未使用）

### 4. Application層（1個）

- [ ] `src/application/handlers/` - 空ディレクトリ

### 5. その他（16個）

**CLI関連:**
- [ ] `src/interfaces/cli/commands/database_commands.py` - 古いデータベースコマンド（要確認）
- [ ] `src/interfaces/cli/commands/monitoring/` - 空ディレクトリ
- [ ] `src/interfaces/cli/commands/processing/` - 空ディレクトリ
- [ ] `src/interfaces/cli/commands/scraping/` - 空ディレクトリ

**BI Dashboard関連:**
- [ ] `src/interfaces/bi_dashboard/callbacks/` - 空ディレクトリ
- [ ] `src/interfaces/bi_dashboard/layouts/` - 空ディレクトリ

**旧実装:**
- [ ] `src/minutes_divide_processor/minutes_divider_refactored.py` - リファクタリング前の実装
- [ ] `src/services/chain_factory.py` - 古いチェーンファクトリー

**Web Scraper:**
- [ ] `src/web_scraper/extractors/content_extractor.py` - 未使用抽出ツール
- [ ] `src/web_scraper/extractors/speaker_extractor.py` - 未使用抽出ツール
- [ ] `src/web_scraper/handlers/` - ハンドラーディレクトリ（要確認）
- [ ] `src/web_scraper/handlers/file_handler.py`
- [ ] `src/web_scraper/handlers/pdf_handler.py`

**その他:**
- [ ] `src/party_member_extractor/tools/` - 空ディレクトリ

### 6. BAML vs Pydantic（オプション）- 要ユーザー確認

- [ ] `src/domain/services/politician_matching_service.py` (Pydantic版)
- [ ] `src/domain/services/speaker_matching_service.py` (Pydantic版)
- フィーチャーフラグ: `USE_BAML_*_MATCHING`（デフォルト: false）
- **判断**: BAML専用化するか、両方を維持するか

---

**実装手順:**

### Phase 0.1: 確実に削除可能なファイル（2日）

1. **空ディレクトリの削除**
   - [ ] Streamlitの空ディレクトリ（charts, forms, tables, request, response）
   - [ ] CLIの空ディレクトリ（monitoring, processing, scraping）
   - [ ] その他の空ディレクトリ（handlers, callbacks, layouts, tools）

2. **明らかに未使用のファイル削除**
   - [ ] `error_404_view.py`
   - [ ] `llm_history_helper.py` + テスト
   - [ ] `minutes_divider_refactored.py`
   - [ ] `cloudflare_auth.py`（Cloudflare認証は別の方法で実装済み）

3. **テストの実行**
   - [ ] 削除後、すべてのテストが成功することを確認
   - [ ] CI/CDが正常に動作することを確認

### Phase 0.2: 要確認ファイルの調査と削除（2日）

1. **Infrastructure層の確認**
   - [ ] 各ファイルの使用状況を手動確認
   - [ ] 未使用確認後、削除

2. **Web Scraper関連の確認**
   - [ ] extractorとhandlerの使用状況確認
   - [ ] 未使用確認後、削除

3. **その他の個別確認**
   - [ ] BI Dashboard関連
   - [ ] CLI commands関連
   - [ ] Domain/Application層の未使用ファイル

### Phase 0.3: BAML専用化の決定と実装（1日）- オプション

1. **ユーザー確認**
   - [ ] BAML専用化するか、フィーチャーフラグを維持するか決定

2. **BAML専用化の実装（選択された場合）**
   - [ ] Factoryの簡略化
   - [ ] Pydantic版の削除
   - [ ] テストの更新

### Phase 0.4: ドキュメントとカバレッジ（0.5日）

1. **ドキュメント更新**
   - [ ] `docs/CLEAN_ARCHITECTURE_MIGRATION.md` - Phase 3完了マーク
   - [ ] `CLAUDE.md` - 削除したコンポーネントの情報を更新

2. **カバレッジ再測定**
   - [ ] 削除後のカバレッジを測定
   - [ ] 不要なコードが除外され、正確なカバレッジを確認

---

**成功基準:**
- [ ] 未使用ファイルが0個（または意図的に残すファイルのみ）
- [ ] 空ディレクトリが0個
- [ ] すべてのテストが成功
- [ ] CI/CDが正常に動作
- [ ] カバレッジ測定が正確になる（不要なコードが除外）

**推定工数:** 5-6日

**優先度:** 最高 - テスト整備の前提条件

**リスク:**
- BAML専用化により予期しない動作の変更（軽減策: テストの徹底実行）
- ユーザーがフィーチャーフラグを使用している可能性（軽減策: 事前確認）

---

#### フェーズ1: クリティカルパス（Week 1）
**目標**: 統合テストのエラー修正とエンティティテストの基盤整備

1. **統合テストのエラー修正**（優先度: 最高）
   - [ ] `test_monitoring_repository.py`の8エラーを調査・修正
   - [ ] `test_political_party_repository.py`の6エラーを調査・修正
   - [ ] `test_parliamentary_group_repository_integration.py`の12エラーを調査・修正
   - **理由**: エラーがあるとCI/CDが不安定になり、他の開発に影響

2. **主要エンティティテストの作成**（優先度: 高）
   - [ ] `test_politician.py` - 最も重要なエンティティ
   - [ ] `test_conference.py` - 会議体の基盤
   - [ ] `test_meeting.py` - 議事録処理の基盤
   - [ ] `test_parliamentary_group.py` - 議員団管理
   - **理由**: これらはシステムの中核エンティティ

#### フェーズ2: Domain Layer完全化（Week 2）
**目標**: Domain Layerのテストを80%以上に

1. **残りのエンティティテスト作成**
   - [ ] `test_conversation.py`
   - [ ] `test_minutes.py`
   - [ ] `test_political_party.py`
   - [ ] `test_parliamentary_group_membership.py`
   - [ ] `test_data_coverage_stats.py`
   - [ ] `test_extracted_party_member.py`
   - [ ] `test_politician_party_extracted_politician.py`
   - [ ] `test_proposal_parliamentary_group_judge.py`

2. **ドメインサービステスト作成**
   - [ ] `test_party_member_extraction_service.py`

3. **Domain Layer カバレッジ測定**
   - [ ] Domain Layerのみのカバレッジレポート作成
   - [ ] 80%達成の確認

#### フェーズ3: Infrastructure Layer強化（Week 3）
**目標**: Infrastructure Layerのテストを80%以上に

1. **優先度の高いリポジトリテスト作成**
   - [ ] `test_politician_repository_impl.py`（未確認）
   - [ ] `test_meeting_repository_impl.py`
   - [ ] `test_minutes_repository_impl.py`
   - [ ] `test_parliamentary_group_repository_impl.py`（ユニットテスト）
   - [ ] `test_political_party_repository_impl.py`（ユニットテスト）

2. **残りのリポジトリテスト作成**
   - [ ] `test_extracted_conference_member_repository_impl.py`
   - [ ] `test_governing_body_repository_impl.py`
   - [ ] `test_politician_affiliation_repository_impl.py`
   - [ ] `test_prompt_version_repository_impl.py`
   - [ ] `test_proposal_parliamentary_group_judge_repository_impl.py`

3. **Infrastructure Layer カバレッジ測定**
   - [ ] Infrastructure Layerのみのカバレッジレポート作成
   - [ ] 80%達成の確認

#### フェーズ4: ドキュメント整備（Week 4）
**目標**: 全ドキュメントの作成と更新

1. **各層の詳細ガイド作成**
   - [ ] `docs/architecture/DOMAIN_LAYER.md`
   - [ ] `docs/architecture/APPLICATION_LAYER.md`
   - [ ] `docs/architecture/INFRASTRUCTURE_LAYER.md`
   - [ ] `docs/architecture/INTERFACE_LAYER.md`

2. **ADR作成**
   - [ ] `docs/ADR/0001-clean-architecture-adoption.md`
   - [ ] `docs/ADR/0002-baml-for-llm-outputs.md`
   - [ ] `docs/ADR/0003-repository-pattern.md`

3. **開発者ガイド作成**
   - [ ] `docs/DEVELOPMENT_GUIDE.md`

4. **既存ドキュメント更新**
   - [ ] `docs/CLEAN_ARCHITECTURE_MIGRATION.md` - Phase 4完了のマーク
   - [ ] `README.md` - Clean Architectureセクションの追加

#### フェーズ5: 最終調整とカバレッジ目標達成（Week 5）
**目標**: 全体カバレッジ80%達成とCI/CD安定化

1. **全体カバレッジ測定**
   - [ ] 全体のテストカバレッジレポート作成
   - [ ] 層別カバレッジの分析

2. **カバレッジギャップの特定と対応**
   - [ ] 80%未満の箇所を特定
   - [ ] 優先度の高い箇所のテスト追加

3. **CI/CD統合**
   - [ ] GitHub Actionsでカバレッジレポート自動生成
   - [ ] READMEにカバレッジバッジ追加

4. **最終レビュー**
   - [ ] すべてのテストが成功することを確認
   - [ ] すべてのドキュメントが最新であることを確認
   - [ ] Issue #825の受入条件をすべて満たすことを確認

---

## 実装の優先順位とリスク

### 優先順位

1. **最高優先度**: 統合テストのエラー修正（フェーズ1）
   - **理由**: CI/CDの安定性に直接影響、他の作業をブロック

2. **高優先度**: 主要エンティティテスト（フェーズ1）
   - **理由**: システムの中核部分、他のテストの基盤

3. **中優先度**: 残りのDomain/Infrastructure Layerテスト（フェーズ2-3）
   - **理由**: カバレッジ目標達成に必要

4. **中優先度**: ドキュメント整備（フェーズ4）
   - **理由**: 長期的な保守性向上、新規開発者のオンボーディング

5. **低優先度**: カバレッジバッジとCI/CD統合（フェーズ5）
   - **理由**: 可視化と自動化、機能的影響は小さい

### リスク と対策

#### リスク1: テストエラーの原因が複雑
- **影響**: フェーズ1の遅延
- **対策**:
  - 各エラーに最大2時間の調査時間を設定
  - 解決困難な場合は新しいIssueを作成して後回し
  - スキップマークを付けて進行

#### リスク2: エンティティテスト作成に予想以上の時間
- **影響**: フェーズ2の遅延、全体スケジュールの遅延
- **対策**:
  - テストテンプレートを作成して効率化
  - 類似エンティティはコピー＆修正で対応
  - 完璧を求めず、基本的なテストから開始

#### リスク3: カバレッジ80%の達成が困難
- **影響**: 受入条件の未達成
- **対策**:
  - フェーズ3終了時点でギャップ分析
  - 優先度の低いファイルは除外を検討
  - 必要に応じてフェーズ5を延長

#### リスク4: ドキュメント作成に時間がかかりすぎる
- **影響**: フェーズ4-5の遅延
- **対策**:
  - テンプレートを活用
  - 既存のdocsを参考に構造を統一
  - 最初は簡潔に、後で充実させる

---

## 実装における注意点

### テスト作成時
1. **外部サービスのモック化**
   - LLM API、GCS、Playwrightなどは必ずモック
   - 実際のAPIコールは統合テストでも避ける（コスト・時間）

2. **async/await パターン**
   - すべてのリポジトリテストは`pytest-asyncio`を使用
   - `@pytest.mark.asyncio`デコレータを忘れない

3. **テストの独立性**
   - 各テストは他のテストに依存しない
   - テストデータは各テスト内で生成
   - データベースのクリーンアップを適切に実施

4. **既存のテストパターンに従う**
   - `tests/application/usecases/`のテストを参考
   - `tests/domain/services/`のテストを参考
   - フィクスチャの再利用（`tests/fixtures/`）

### ドキュメント作成時
1. **一貫性**
   - 既存のdocsと同じトーンとスタイル
   - Markdownフォーマットの統一

2. **実用性**
   - 理論だけでなく、実際のコード例を含める
   - よくある間違いとその回避方法を記載

3. **保守性**
   - 将来の変更に対応しやすい構造
   - 具体的なファイルパスやバージョンは別途管理

---

## 成功基準

### テスト
- [ ] 全体のテストカバレッジが80%以上
- [ ] Domain Layerのカバレッジが80%以上
- [ ] Infrastructure Layerのカバレッジが80%以上
- [ ] 統合テストのエラーが0個
- [ ] テスト失敗が0個
- [ ] CI/CDで自動的にテストが実行される

### ドキュメント
- [ ] 4つの層のドキュメントがすべて存在
- [ ] 3つのADRが存在
- [ ] DEVELOPMENT_GUIDE.mdが存在して最新
- [ ] CLEAN_ARCHITECTURE_MIGRATION.mdがPhase 4完了を反映
- [ ] READMEにClean Architectureの説明とリンクが追加

### 全体
- [ ] Issue #825のすべての受入条件を満たす
- [ ] 新規開発者がドキュメントのみでアーキテクチャを理解できる
- [ ] テストの実行が安定している

---

## 次のステップ

このプランが承認されたら、以下の順序で実装を開始します：

1. **フェーズ0の開始（最優先）**
   - **Phase 0.1**: 確実に削除可能なファイル（空ディレクトリ、明らかに未使用のファイル）
   - **Phase 0.2**: 要確認ファイルの調査と削除
   - **Phase 0.3**: BAML専用化の決定（ユーザー確認必要）
   - **Phase 0.4**: ドキュメント更新とカバレッジ再測定
   - **目標**: 33個の未使用モジュールを削除し、コードベースをクリーンに

2. **フェーズ1への移行**
   - レガシーコード削除完了後、統合テストエラーの調査開始
   - 主要エンティティテストの作成開始

3. **進捗の追跡**
   - 週次で進捗をレビュー
   - 必要に応じてスケジュール調整

4. **継続的なフィードバック**
   - テスト作成時に発見した問題を随時報告
   - ドキュメントのドラフトをレビュー依頼

---

## 補足情報

### 参考になる既存ファイル

#### テスト
- `tests/application/usecases/test_manage_conference_members_usecase.py` - 718行の充実したテスト
- `tests/domain/entities/test_speaker.py` - エンティティテストの良い例
- `tests/infrastructure/persistence/test_conference_repository_impl.py` - リポジトリテストの例

#### ドキュメント
- `docs/ARCHITECTURE.md` - アーキテクチャの概要
- `docs/architecture/clean-architecture.md` - Clean Architectureの詳細
- `docs/ADR/001-langgraph-adapter-pattern.md` - ADRの例

### 推定工数

- **フェーズ0**: 5-6日（未使用コードの大掃除）
- **フェーズ1**: 5-7日
- **フェーズ2**: 5-7日
- **フェーズ3**: 5-7日
- **フェーズ4**: 5-7日
- **フェーズ5**: 3-5日

**合計**: 28-39日（約6-8週間）

ただし、これは専任で作業した場合の見積もりです。実際には他のタスクと並行する可能性があるため、カレンダー日数ではより長くなる可能性があります。
