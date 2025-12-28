# Issue #831 実装計画: 統合テストエラー修正と主要エンティティテスト

## 問題の理解

### 統合テストエラーについて

調査の結果、統合テストのエラーは以下の原因によるものです：

1. **データベース接続エラー**:
   - 統合テストはPostgreSQLデータベース接続が必要
   - ローカル環境ではDocker起動が必要（`just up`コマンド）
   - CI環境では`pytestmark = pytest.mark.skipif(os.getenv("CI") == "true", ...)`でスキップされる設定

2. **現在のエラー状況**:
   - `test_monitoring_repository.py` (8テスト)
   - `test_political_party_repository.py` (6テスト)
   - `test_parliamentary_group_repository_integration.py` (12テスト)

### 主要エンティティテスト不足について

以下の4つの主要エンティティのテストが存在しません：

- `Politician` (src/domain/entities/politician.py)
- `Conference` (src/domain/entities/conference.py)
- `Meeting` (src/domain/entities/meeting.py)
- `ParliamentaryGroup` (src/domain/entities/parliamentary_group.py)

## 実装アプローチ

### フェーズ1: 統合テストの修正（優先度: 最高）

#### 1.1 統合テスト実行環境の確認

**タスク:**
- Dockerコンテナを起動してPostgreSQLデータベースを利用可能にする
- データベース接続を確認する

**手順:**
```bash
just up  # Dockerコンテナ起動
just db  # データベース接続確認
```

#### 1.2 MonitoringRepositoryテストの修正 (8エラー)

**調査ファイル:**
- `tests/integration/database/test_monitoring_repository.py`
- `src/infrastructure/persistence/monitoring_repository_impl.py`

**予想される問題:**
- データベーススキーマとリポジトリ実装の不整合
- `processed_at`カラムの不在（コメントで言及あり）
- 非同期メソッドの実装不備

**修正方針:**
1. リポジトリ実装のSQLクエリを確認
2. スキーマとの整合性を確認
3. 非同期メソッドが正しく実装されているか確認
4. テストデータのセットアップを確認

#### 1.3 PoliticalPartyRepositoryテストの修正 (6エラー)

**調査ファイル:**
- `tests/integration/database/test_political_party_repository.py`
- `src/infrastructure/persistence/political_party_repository_impl.py`

**予想される問題:**
- リポジトリが非同期対応していない可能性
- `AsyncSessionAdapter`の使用方法の不備

**修正方針:**
1. リポジトリ実装が`async/await`パターンに従っているか確認
2. テストフィクスチャで`AsyncSessionAdapter`を使用しているか確認
3. トランザクション管理の実装を確認

#### 1.4 ParliamentaryGroupRepositoryテストの修正 (12エラー)

**調査ファイル:**
- `tests/integration/parliamentary/test_parliamentary_group_repository_integration.py`
- `src/infrastructure/persistence/parliamentary_group_repository_impl.py`
- `src/infrastructure/persistence/parliamentary_group_membership_repository_impl.py`

**予想される問題:**
- Migration 032での`speaker_id`カラム削除への未対応
- テストデータセットアップの不備
- リポジトリメソッドの実装不備

**修正方針:**
1. Migration 032の変更（`politician.speaker_id`削除）に対応したテストデータ作成
2. リポジトリメソッドの非同期実装を確認
3. 外部キー制約のエラーを解決

### フェーズ2: 主要エンティティテストの作成（優先度: 高）

#### 2.1 テスト設計の原則

**参考実装:**
- `tests/domain/entities/test_speaker.py` - 既存の良好なテスト例

**テストパターン:**
1. **初期化テスト**
   - 必須フィールドのみでの初期化
   - 全フィールドでの初期化
   - デフォルト値の確認

2. **文字列表現テスト**
   - `__str__`メソッドの動作確認
   - 各種条件での表示内容確認

3. **ファクトリ関数テスト**
   - `create_*`関数の動作確認
   - オーバーライドパラメータの確認

4. **エッジケーステスト**
   - 空文字列、None値の扱い
   - 長い文字列、特殊文字の扱い

5. **バリデーションテスト**
   - 不正な値での例外発生確認（必要に応じて）

#### 2.2 Politicianエンティティテストの作成

**ファイル:** `tests/domain/entities/test_politician.py`

**テスト項目:**
- 必須フィールド（name）のみでの初期化
- 全フィールドでの初期化
- `__str__`メソッドのテスト（nameを返す）
- `create_politician`ファクトリのテスト
- 各種オプションフィールドの組み合わせテスト
- エッジケース（空文字列、長い名前、特殊文字）

**注意点:**
- Migration 032で`speaker_id`が削除されているため、`create_politician`ファクトリ関数の修正も必要

#### 2.3 Conferenceエンティティテストの作成

**ファイル:** `tests/domain/entities/test_conference.py`

**テスト項目:**
- 必須フィールド（name, governing_body_id）での初期化
- 全フィールドでの初期化
- `__str__`メソッドのテスト（nameを返す）
- `create_conference`ファクトリのテスト
- typeフィールドの各種値のテスト
- エッジケース

**注意点:**
- `governing_body_id`は必須フィールド

#### 2.4 Meetingエンティティテストの作成

**ファイル:** `tests/domain/entities/test_meeting.py`

**テスト項目:**
- 必須フィールド（conference_id）での初期化
- 全フィールドでの初期化
- `__str__`メソッドの各種条件でのテスト
  - nameがある場合
  - dateのみの場合
  - idのみの場合
  - 何もない場合
- `create_meeting`ファクトリのテスト
- attendees_mappingの扱いテスト
- エッジケース

#### 2.5 ParliamentaryGroupエンティティテストの作成

**ファイル:** `tests/domain/entities/test_parliamentary_group.py`

**テスト項目:**
- 必須フィールド（name, conference_id）での初期化
- 全フィールドでの初期化
- `__str__`メソッドのテスト（nameを返す）
- `create_parliamentary_group`ファクトリのテスト
- `is_active`フラグのテスト
- エッジケース

### フェーズ3: ファクトリ関数の修正

#### 3.1 create_politician関数の修正

**ファイル:** `tests/fixtures/entity_factories.py`

**問題:**
- `speaker_id`パラメータが存在するが、Politicianエンティティには不要（Migration 032で削除）

**修正内容:**
```python
def create_politician(**kwargs: Any) -> Politician:
    """Create a test politician."""
    defaults = {
        "id": 1,
        "name": "山田太郎",
        "political_party_id": None,
        "furigana": None,
        "district": None,
        "profile_page_url": None,
        "party_position": None,  # このフィールドを追加
    }
    defaults.update(kwargs)
    return Politician(**defaults)
```

#### 3.2 create_conference関数の修正

**ファイル:** `tests/fixtures/entity_factories.py`

**問題:**
- `description`と`is_active`パラメータが存在するが、Conferenceエンティティには不要

**修正内容:**
```python
def create_conference(**kwargs: Any) -> Conference:
    """Create a test conference."""
    defaults = {
        "id": 1,
        "governing_body_id": 1,
        "name": "議会全体",
        "type": "地方議会全体",
        "members_introduction_url": None,
    }
    defaults.update(kwargs)
    return Conference(**defaults)
```

## 実装順序

### ステップ1: 環境準備とファクトリ修正
1. Dockerコンテナ起動
2. ファクトリ関数の修正（`create_politician`, `create_conference`）
3. 修正のテスト

### ステップ2: エンティティテストの作成
1. `test_politician.py`の作成
2. `test_conference.py`の作成
3. `test_meeting.py`の作成
4. `test_parliamentary_group.py`の作成
5. 各テストの実行と確認

### ステップ3: 統合テストの修正
1. MonitoringRepositoryの調査と修正
2. PoliticalPartyRepositoryの調査と修正
3. ParliamentaryGroupRepositoryの調査と修正
4. 全統合テストの実行と確認

### ステップ4: 最終確認
1. 全テストの実行
   ```bash
   uv run pytest -xvs
   ```
2. コード品質チェック
   ```bash
   uv run --frozen ruff format .
   uv run --frozen ruff check . --fix
   uv run --frozen pyright
   ```

## リスクと注意点

### リスク

1. **データベーススキーマの変更**
   - Migration 032での変更が他の箇所に影響している可能性
   - データベースマイグレーションの実行が必要な場合がある

2. **非同期実装の複雑さ**
   - `AsyncSessionAdapter`の使用方法が統一されていない可能性
   - テストフィクスチャの設定が複雑

3. **外部キー制約**
   - テストデータのセットアップ順序が重要
   - トランザクションロールバックの動作確認が必要

### 注意点

1. **CI/CD環境**
   - 統合テストはCI環境でスキップされる
   - ローカル環境でのみ実行・確認が必要

2. **テストの独立性**
   - 各テストは独立して実行可能である必要がある
   - トランザクションロールバックによるクリーンアップを確認

3. **既存コードへの影響**
   - ファクトリ関数の修正が既存テストに影響しないか確認
   - エンティティ定義の変更が他の箇所に影響しないか確認

## 受入基準の確認

✅ 統合テストのエラーが0個
✅ 主要4エンティティのテストが作成され、成功
✅ CI/CDが安定して動作（統合テストはスキップ）
✅ すべてのテストが成功
✅ コード品質チェック（Ruff、Pyright）が成功

## 推定工数

- **フェーズ1（統合テスト修正）**: 2-3日
  - 環境準備: 0.5日
  - MonitoringRepository修正: 0.5-1日
  - PoliticalPartyRepository修正: 0.5日
  - ParliamentaryGroupRepository修正: 0.5-1日

- **フェーズ2（エンティティテスト作成）**: 1-2日
  - ファクトリ修正: 0.5日
  - 4エンティティのテスト作成: 0.5-1.5日

- **フェーズ3（最終確認とドキュメント）**: 0.5-1日

**合計**: 3.5-6日

この計画では、統合テストの修正を優先し、次にエンティティテストを作成する順序で進めます。
