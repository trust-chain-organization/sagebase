# Issue #834 実装計画: Phase 4-4 ドキュメント整備 - アーキテクチャガイドとADR

## 概要

Clean Architectureの知識を体系化し、新規開発者が容易にアーキテクチャを理解できるようにするため、包括的なドキュメントを作成します。

## 背景

- 各層の詳細ガイドが不足（4個必要）
- ADRが不足（3個必要）
- 開発者ガイドが存在しない
- 新規開発者のオンボーディングが困難

## 収集済み情報

### 既存ドキュメント
1. `docs/ARCHITECTURE.md` (1228行) - 完全なアーキテクチャドキュメント
2. `docs/CLEAN_ARCHITECTURE_MIGRATION.md` (227行) - 移行ガイド（Phase 1-3完了、Phase 4進行中）
3. `docs/architecture/clean-architecture.md` (994行) - Clean Architecture実装詳細
4. `docs/ADR/001-langgraph-adapter-pattern.md` (214行) - 既存ADR例

### コードベース実装状況
- **Domain層**: 25 entities, 14 services
  - 主要エンティティ: Politician, Speaker, Meeting, Conference, etc.
  - ドメインサービス: PoliticianDomainService, SpeakerDomainService, etc.
- **Application層**: 29 usecases
  - 主要ユースケース: ManagePoliticiansUseCase, ProcessMinutesUseCase, etc.
- **Infrastructure層**: 32 persistence files
  - BaseRepositoryImpl + 具体的な実装（PoliticianRepositoryImpl, etc.）
- **Interface層**:
  - CLI: 20+ コマンドファイル
  - Streamlit UI: views, presenters, components

### BAML実装
- 11個のBAMLファイル: speaker_matching, politician_matching, member_extraction, etc.
- BAML専用化完了（Pydantic実装削除済み）

## 実装計画

### Phase 1: 各層の詳細ガイド作成（4個）

#### 1.1 `docs/architecture/DOMAIN_LAYER.md`

**構成:**
1. 層の責務と境界
   - ビジネスロジックとビジネスルールの実装
   - フレームワーク非依存
   - 他の層に依存しない

2. エンティティ（Entities）
   - BaseEntityパターン
   - 実装例: Politician, Speaker, Meeting
   - ビジネスルールの実装
   - 不変性の保持

3. リポジトリインターフェース（Repository Interfaces）
   - BaseRepository[T]ジェネリックパターン
   - カスタムメソッドの定義
   - ISessionAdapterの活用
   - 実装例: PoliticianRepository

4. ドメインサービス（Domain Services）
   - 複数エンティティにまたがるロジック
   - 実装例: PoliticianDomainService, SpeakerDomainService
   - 名前正規化、類似度計算、重複検出

5. よくある落とし穴と回避方法
   - エンティティにデータベースロジックを含めない
   - 循環依存の回避
   - ビジネスロジックの過度な抽象化

6. チェックリスト
   - [ ] エンティティは他の層に依存していない
   - [ ] ビジネスルールがエンティティに実装されている
   - [ ] リポジトリはインターフェースのみ定義
   - [ ] ドメインサービスは純粋な関数

#### 1.2 `docs/architecture/APPLICATION_LAYER.md`

**構成:**
1. 層の責務と境界
   - ユースケースの実装
   - ビジネスフローの調整
   - トランザクション管理

2. ユースケース（Use Cases）
   - 単一責任の原則
   - 依存性注入パターン
   - 実装例: ManagePoliticiansUseCase, ProcessMinutesUseCase
   - execute()メソッドパターン

3. DTO（Data Transfer Objects）
   - InputDTO / OutputDTOペア
   - dataclass使用
   - 実装例: PoliticianListInputDto, CreatePoliticianInputDto
   - バリデーション戦略

4. エラーハンドリング
   - カスタム例外の定義
   - エラーレスポンスの統一
   - ロギング戦略

5. よくある落とし穴と回避方法
   - ユースケースの肥大化
   - ドメインロジックの漏洩
   - DTOとエンティティの混同

6. チェックリスト
   - [ ] ユースケースは単一の責任を持つ
   - [ ] DTOが層間のデータ転送に使用されている
   - [ ] エンティティを直接公開していない
   - [ ] トランザクションが適切に管理されている

#### 1.3 `docs/architecture/INFRASTRUCTURE_LAYER.md`

**構成:**
1. 層の責務と境界
   - 外部システムとの連携
   - リポジトリの実装
   - フレームワーク依存の実装

2. リポジトリ実装（Repository Implementations）
   - BaseRepositoryImplパターン
   - ISessionAdapterの使用
   - Entity ↔ Model変換
   - 実装例: PoliticianRepositoryImpl
   - 非同期処理（async/await）

3. 外部サービス統合
   - ILLMService実装（GeminiLLMService）
   - IStorageService実装（GCSStorageService）
   - アダプターパターン

4. データベースマッピング
   - SQLAlchemyモデル
   - エンティティとモデルの分離
   - マイグレーション管理

5. よくある落とし穴と回避方法
   - ドメイン層への依存の逆転
   - フレームワーク型の漏洩
   - N+1問題

6. チェックリスト
   - [ ] リポジトリがインターフェースを実装している
   - [ ] エンティティとモデルが分離されている
   - [ ] 外部サービスがインターフェース経由でアクセスされる
   - [ ] ISessionAdapterを使用している

#### 1.4 `docs/architecture/INTERFACE_LAYER.md`

**構成:**
1. 層の責務と境界
   - ユーザーインターフェース
   - エントリーポイント
   - 入出力の変換

2. CLIコマンド（CLI Commands）
   - Clickフレームワークの使用
   - コマンド構造
   - 実装例: politician_commands.py
   - 依存性注入のセットアップ

3. Streamlit UI
   - MVP（Model-View-Presenter）パターン
   - ディレクトリ構造: views, presenters, components
   - 実装例: politicians_view.py
   - セッション状態管理

4. プレゼンターパターン
   - ビジネスロジックとUIの分離
   - DTOの変換
   - エラーハンドリング

5. よくある落とし穴と回避方法
   - ビジネスロジックのUI層への混入
   - 直接的なデータベースアクセス
   - セッション状態の過度な使用

6. チェックリスト
   - [ ] UIコンポーネントがユースケースのみを呼び出す
   - [ ] ビジネスロジックがUI層に含まれていない
   - [ ] プレゼンターパターンが適切に使用されている
   - [ ] エラーメッセージがユーザーフレンドリー

### Phase 2: ADR作成（3個）

#### 2.1 `docs/ADR/0001-clean-architecture-adoption.md`

**内容:**
- Status: Accepted
- Context: レガシーコードの保守性問題、スケーラビリティの課題
- Decision: Clean Architectureの採用
- Consequences: 保守性向上、テスト容易性向上、学習コスト
- Alternatives: MVCパターン、レイヤードアーキテクチャ

#### 2.2 `docs/ADR/0002-baml-for-llm-outputs.md`

**内容:**
- Status: Accepted
- Context: PydanticベースのLLM出力処理の課題（トークン効率、型安全性）
- Decision: BAMLの採用
- Consequences: トークン削減、型安全性向上、DSL学習コスト
- Alternatives: Pydanticのみ、Instructor、Outlines

#### 2.3 `docs/ADR/0003-repository-pattern.md`

**内容:**
- Status: Accepted
- Context: データアクセスの抽象化の必要性
- Decision: リポジトリパターン + ISessionAdapter
- Consequences: テスト容易性、依存性逆転、実装オーバーヘッド
- Alternatives: Active Recordパターン、Data Mapperパターン

### Phase 3: 開発者ガイド作成（1個）

#### 3.1 `docs/DEVELOPMENT_GUIDE.md`

**構成:**
1. はじめに
2. Clean Architecture 概要（簡潔版）
3. 開発環境のセットアップ
4. 新規機能開発の手順
5. テスト作成のガイドライン
6. コーディング規約
7. トラブルシューティング
8. 参考リソース

### Phase 4: 既存ドキュメント更新（2個）

#### 4.1 `docs/CLEAN_ARCHITECTURE_MIGRATION.md` 更新

**更新内容:**
- Phase 4を完了としてマーク
- 完了日の記録（2025-12-29）
- 最終的なファイル数とコード行数の記録
- ドキュメント整備状況の記録

#### 4.2 `README.md` 更新

**追加セクション:**
- Clean Architectureセクションの追加（簡潔版）
- ドキュメントへのリンク追加
- アーキテクチャ図の参照

## 実装の順序

1. **Phase 1**: 各層の詳細ガイド作成（4個）
   - 優先順位: DOMAIN → APPLICATION → INFRASTRUCTURE → INTERFACE
   - 理由: 依存関係の順序に従う

2. **Phase 2**: ADR作成（3個）
   - 0001 → 0002 → 0003 の順序で作成
   - 理由: Clean Architecture採用が基礎、他のADRはそれに基づく決定

3. **Phase 3**: 開発者ガイド作成（1個）
   - すべての層ガイドとADRが完成後に作成
   - 理由: 各ガイドへの参照が必要

4. **Phase 4**: 既存ドキュメント更新（2個）
   - すべての新規ドキュメントが完成後に更新
   - 理由: 完了状況と参照リンクが必要

## リスクと注意点

### リスク
1. **ドキュメントの一貫性**: 複数のドキュメントで情報が矛盾する可能性
   - **対策**: 各ドキュメント作成後に相互参照をチェック

2. **実装例の正確性**: コード例が古くなる可能性
   - **対策**: 実際のコードベースから最新の例を引用

3. **ボリュームの管理**: 各ドキュメントが肥大化する可能性
   - **対策**: 明確なセクション構成と適切な分量管理

### 注意点
1. すべてのドキュメントを日本語で記述
2. 実際のコードベースから例を引用（架空の例を避ける）
3. 各ドキュメントは独立して読めるようにする（適切な相互参照）
4. 図やコード例を積極的に使用（可読性向上）

## 受入条件の確認

- [ ] 4つの層のドキュメントがすべて存在
- [ ] 3つのADRが存在
- [ ] DEVELOPMENT_GUIDE.mdが存在して最新
- [ ] CLEAN_ARCHITECTURE_MIGRATION.mdがPhase 4完了を反映
- [ ] READMEにClean Architectureの説明とリンクが追加
- [ ] 新規開発者がドキュメントのみでアーキテクチャを理解できる

## 推定工数

- **各層ガイド作成**: 1日 × 4 = 4日
- **ADR作成**: 0.5日 × 3 = 1.5日
- **開発者ガイド作成**: 1日
- **既存ドキュメント更新**: 0.5日
- **レビューと調整**: 1日

**合計**: 約8日

## まとめ

このプランに従ってドキュメントを作成することで、Clean Architectureの知識が体系化され、新規開発者が容易にアーキテクチャを理解できるようになります。各ドキュメントは実際のコードベースに基づいており、実用的で正確な情報を提供します。
