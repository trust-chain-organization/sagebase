# Sagebase - 政治活動追跡アプリケーション

[![Tests](https://github.com/trust-chain-organization/sagebase/actions/workflows/test.yml/badge.svg)](https://github.com/trust-chain-organization/sagebase/actions/workflows/test.yml)
[![Type Check](https://github.com/trust-chain-organization/sagebase/actions/workflows/pyright.yml/badge.svg)](https://github.com/trust-chain-organization/sagebase/actions/workflows/pyright.yml)
[![codecov](https://codecov.io/gh/trust-chain-organization/sagebase/branch/main/graph/badge.svg)](https://codecov.io/gh/trust-chain-organization/sagebase)

政治家の発言、議事録、公約などを体系的に管理・分析するためのアプリケーションです。

## 🗄️ テーブル構造
詳細なデータベース設計はこちらをご確認ください：
https://dbdocs.io/sagebase/Sagebase

### 主要エンティティの役割

- **Speaker**: 議事録から抽出された発言者。議事録における政治家の表現（例：「山田太郎君」「山田議員」など）を記録
- **Politician**: 政治家マスタデータ。議事録由来（speaker_id有）と政党サイト由来（speaker_id無）の両方を管理
- **ExtractedPolitician**: 政党サイトから抽出された政治家の中間データ。レビュー後に承認されるとPoliticianテーブルに変換される
- **PoliticalParty**: 政党マスタデータ
- **Conversation**: 議事録の発言内容

## 🚀 環境構築手順

### 前提条件
- Docker & Docker Compose
- Python 3.13
- uv（Pythonパッケージマネージャー）
- Google Cloud SDK（GCS機能を使用する場合）

### 1. リポジトリのクローン
```bash
git clone https://github.com/trust-chain-organization/sagebase.git
cd sagebase
```

### 2. 環境変数の設定
```bash
# .envファイルを作成（必要に応じて設定を調整）
cp .env.example .env

# Google Gemini APIキーを設定（議事録処理に必要）
# .envファイルのGOOGLE_API_KEYを実際のAPIキーに置き換えてください
```

**重要**: Google Gemini APIキーは以下で取得できます：
- [Google AI Studio](https://aistudio.google.com/)でAPIキーを取得
- `.env`ファイルの`GOOGLE_API_KEY`に設定

**Google Cloud Storage（オプション）**:
- スクレイピングしたデータをGCSに保存する場合は、以下の設定も必要です：
  - `gcloud auth application-default login`で認証
  - `.env`ファイルで`GCS_BUCKET_NAME`と`GCS_UPLOAD_ENABLED=true`を設定

### 3. Docker環境の起動
```bash
# PostgreSQLデータベースとアプリケーションを起動
docker compose -f docker/docker-compose.yml up -d

# ログの確認
docker compose -f docker/docker-compose.yml logs -f
```

### 4. Python依存関係のインストール（ローカル開発用）
```bash
# uvを使用して依存関係をインストール
uv sync
```

### 5. セットアップの確認
```bash
# セットアップが正常に完了したか確認
./scripts/test-setup.sh
```

## 🏃 使用方法

### システムデザイン

Sagebaseは以下の設計原則に基づいて構築されています：

1. **政治家の情報は政党のWebサイトから取得**
   - 各政党の公式サイトから最新の議員情報を定期的に取得
   - 名前、所属、役職、選挙区などの情報を構造化して保存

2. **発言者と発言内容は議事録から抽出**
   - 議事録PDFやWebページから発言者名と発言内容を自動抽出
   - 発言順序や文脈を保持したまま構造化データとして保存

3. **発言者と政治家はLLMを利用して紐付け**
   - 表記揺れや敬称の違いに対応する高精度マッチング
   - ルールベース + LLMベースのハイブリッドアプローチ

4. **会議体の所属議員情報は段階的に抽出・マッチング**
   - 議会の議員紹介ページから情報を自動抽出
   - 中間ステージングテーブルで確認・修正が可能
   - LLMによる高精度な既存政治家とのマッチング

5. **議員団（会派）による政策の賛否を管理**
   - 議員団単位での賛成・反対を記録
   - 政治家の議員団所属履歴を管理
   - 議案への賛否を個人・政党・議員団で分析可能

6. **データ入力はStreamlit UIを通じて**
   - 政党の議員一覧URLの設定
   - 議事録URLの登録と管理
   - 会議体の議員紹介URLの設定
   - 直感的なWebインターフェースで操作

7. **データカバレッジを監視ダッシュボードで可視化**
   - **監視ダッシュボード（Streamlit）**: 全国の議会・議事録データの入力状況を一覧表示
     - 議会別・都道府県別・政党別のカバレッジ率を視覚化
     - 時系列でのデータ入力推移を分析
     - 日本地図による視覚的なカバレッジ表示
   - **BIダッシュボード（Plotly Dash）**: データカバレッジの詳細分析
     - インタラクティブなグラフと表でデータ分析
     - 都道府県・組織タイプ別の詳細なカバレッジ統計
     - リアルタイムデータ更新とフィルタリング機能
     - Clean Architecture準拠の独立アプリケーション

8. **LLM処理履歴とプロンプトバージョン管理**
   - すべてのLLM処理（議事録分割、発言者抽出、政治家マッチング等）の履歴を記録
   - プロンプトテンプレートのバージョン管理により再現性を確保
   - 処理の成功/失敗、使用モデル、トークン使用量などを追跡
   - A/Bテストや改善のためのプロンプト履歴分析が可能

## 🏗️ アーキテクチャ

Sagebaseは**Clean Architecture**を採用しており、ビジネスロジックをフレームワークや外部システムから完全に独立させています。

### 4層構造

```
┌─────────────────────────────────────────────────────────────┐
│ Interface Layer (CLI, Streamlit UI)                         │
│  - ユーザーインターフェース、エントリーポイント                │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Application Layer (Use Cases, DTOs)                         │
│  - ビジネスフローの調整、トランザクション管理                  │
└───────────────────────┬─────────────────────────────────────┘
                        │ 依存
┌───────────────────────▼─────────────────────────────────────┐
│ Domain Layer (Entities, Domain Services, Repositories)      │
│  - ビジネスロジック、ビジネスルール（フレームワーク非依存）      │
└───────────────────────▲─────────────────────────────────────┘
                        │ 実装
┌───────────────────────┴─────────────────────────────────────┐
│ Infrastructure Layer (Repository Impl, External Services)   │
│  - データベースアクセス、外部サービス統合                      │
└─────────────────────────────────────────────────────────────┘
```

### 主な利点

- **テスト容易性**: ドメインロジックを外部依存なしで単体テスト可能
- **保守性**: 責務が明確で、変更の影響範囲が限定的
- **柔軟性**: LLMプロバイダーやデータベースの変更がビジネスロジックに影響しない

### ドキュメント

- **[DEVELOPMENT_GUIDE.md](docs/guides/DEVELOPMENT_GUIDE.md)** - 新規開発者向けガイド
- **各層の詳細ガイド**:
  - [DOMAIN_LAYER.md](docs/architecture/DOMAIN_LAYER.md) - エンティティ、リポジトリ、ドメインサービス
  - [APPLICATION_LAYER.md](docs/architecture/APPLICATION_LAYER.md) - ユースケース、DTO
  - [INFRASTRUCTURE_LAYER.md](docs/architecture/INFRASTRUCTURE_LAYER.md) - リポジトリ実装、外部サービス
  - [INTERFACE_LAYER.md](docs/architecture/INTERFACE_LAYER.md) - CLI、Streamlit UI
- **ADR（アーキテクチャ決定記録）**:
  - [ADR 0001: Clean Architecture採用](docs/ADR/0001-clean-architecture-adoption.md)
  - [ADR 0002: BAML for LLM Outputs](docs/ADR/0002-baml-for-llm-outputs.md)
  - [ADR 0003: リポジトリパターン](docs/ADR/0003-repository-pattern.md)
  - [ADR 0004: LangGraph Adapter Pattern](docs/ADR/0004-langgraph-adapter-pattern.md)
  - [ADR 0005: 抽出層とGold Layer分離](docs/ADR/0005-extraction-layer-gold-layer-separation.md)
- **[CLEAN_ARCHITECTURE_MIGRATION.md](docs/architecture/CLEAN_ARCHITECTURE_MIGRATION.md)** - 移行の進捗状況

### コマンドリファレンス

📚 **すべてのコマンドの詳細は [COMMANDS.md](COMMANDS.md) を参照してください。**

以下は基本的な使用例です：

### クイックスタート

```bash
# 議事録を処理（発言を抽出）
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase process-minutes

# 会議管理Web UIを起動
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase streamlit
```

### 主要な機能

#### 議事録処理
議事録PDFファイルを読み込み、発言単位に分割してデータベースに保存します。

#### 会議管理Web UI
Webブラウザで会議情報（URL、日付）と政党情報を管理できるインターフェースを提供します：
- 会議一覧の表示・フィルタリング
- 新規会議の登録（開催主体、会議体、日付、URL）
- 既存会議の編集・削除
- 政党管理（議員一覧ページURLの設定）

アクセスURL: http://localhost:8501

#### データカバレッジ監視ダッシュボード
データ入力の進捗状況を可視化する監視ダッシュボードを提供します：
- **全体概要**: 議会数、会議数、議事録数、政治家数などの主要メトリクス
- **日本地図表示**: 都道府県ごとのデータ充実度を地図上で可視化
- **議会別カバレッジ**: 各議会のデータ入力率をヒートマップで表示
- **時系列分析**: データ入力の推移を時系列グラフで確認

アクセスURL: http://localhost:8502 （Docker Compose使用時）

#### BIダッシュボード（データカバレッジ分析）
Plotly Dashを使用した高度なデータカバレッジ分析ダッシュボードを提供します：
- **インタラクティブグラフ**: 円グラフ、棒グラフによるカバレッジ可視化
- **組織タイプ別分析**: 国/都道府県/市町村のカバレッジ率比較
- **都道府県別統計**: 各都道府県のデータ取得状況を詳細表示
- **リアルタイム更新**: データベースから最新情報を取得

**特徴**:
- Clean Architecture準拠の独立アプリケーション
- 完全にPythonコードで定義された可視化
- メインのDocker Compose設定で統合管理
- 将来の機能拡張に対応した設計

**起動方法**:
```bash
# すべてのサービスを起動（PostgreSQL含む）
docker compose -f docker/docker-compose.yml up -d

# BI Dashboardのみを起動（既存のPostgreSQLを使用）
docker compose -f docker/docker-compose.yml up -d bi-dashboard

# ログの確認
docker compose -f docker/docker-compose.yml logs -f bi-dashboard
```

アクセスURL: http://localhost:8050

詳細は [docs/guides/BI_DASHBOARD.md](docs/guides/BI_DASHBOARD.md) を参照してください。

### テストの実行
```bash
# 全テスト実行
docker compose -f docker/docker-compose.yml exec sagebase uv run pytest

# 特定のテストを実行
uv run pytest tests/test_minutes_divider.py -v
```

## 🗃️ データベースの確認方法

### マスターデータについて

**開催主体（governing_bodies）と会議体（conferences）**は基本的に増減しない固定的なマスターデータとして扱います。これらのデータは以下のSEEDファイルで管理しています：

- `database/seed_governing_bodies_generated.sql`: 日本国、47都道府県、全国1,939市町村（全自治体）
- `database/seed_conferences_generated.sql`: 国会・各委員会、都道府県議会、市区議会
- `database/seed_political_parties_generated.sql`: 主要政党、地域政党、過去の政党（会員リストURLを含む）

これらのマスターデータは、システム初期化時に自動的に投入され、アプリケーション運用中は基本的に変更されません。

### 1. PostgreSQLに接続
```bash
# Docker環境のPostgreSQLに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db
```

### 2. 基本的なSQLクエリ例
```sql
-- テーブル一覧を確認
\dt

-- 政党一覧を確認
SELECT * FROM political_parties;

-- 開催主体を確認
SELECT * FROM governing_bodies;

-- 会議体を確認
SELECT c.*, g.name as governing_body_name
FROM conferences c
JOIN governing_bodies g ON c.governing_body_id = g.id;

-- 発言データと発言者の紐付け状況を確認
SELECT
    COUNT(*) as total_conversations,
    COUNT(speaker_id) as linked_conversations,
    COUNT(*) - COUNT(speaker_id) as unlinked_conversations
FROM conversations;

-- 発言データを確認（サンプルがある場合）
SELECT s.name as speaker_name, c.comment, c.sequence_number
FROM conversations c
JOIN speakers s ON c.speaker_id = s.id
LIMIT 10;
```

### 3. データベース接続テスト
```bash
# Pythonでデータベース接続をテスト
docker compose -f docker/docker-compose.yml exec sagebase uv run python -c "
from src.config.database import test_connection
test_connection()
"
```

## 💾 データベースの永続化とリセット

### データ永続化について

**デフォルト設定（永続化モード）**:
- `docker compose.yml`を使用すると、データベースは自動的に永続化されます
- `postgres_data`ボリュームにデータが保存され、コンテナを停止・再起動してもデータは保持されます

```bash
# 永続化モードで起動（デフォルト）
docker compose -f docker/docker-compose.yml up -d

# コンテナを停止してもデータは保持される
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d  # データがそのまま残る
```

**非永続化モード（一時的な使用）**:
- テストや一時的な使用の場合は、非永続化モードを使用できます
- コンテナ停止時にデータは全て削除されます

```bash
# 非永続化モードで起動
docker compose -f docker/docker-compose.temp.yml up -d

# または、既存のボリュームを使用せずに起動
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d --renew-anon-volumes
```

### データベースのリセット

#### 完全リセット（推奨）
```bash
# 自動化されたリセットスクリプトを使用
./scripts/reset-database.sh
```

#### 手動リセット
```bash
# 1. コンテナとボリュームを完全削除
docker compose -f docker/docker-compose.yml down -v

# 2. 再起動（初期データで復元）
docker compose -f docker/docker-compose.yml up -d
```

### データのバックアップ・リストア

Sagebaseは、ローカルとGoogle Cloud Storage（GCS）の両方にデータベースバックアップを保存できます。

**GCS連携の設定（オプション）**:
- GCSを使用する場合は、事前に以下の設定が必要です：
  1. `gcloud auth application-default login`で認証
  2. `.env`ファイルで`GCS_BUCKET_NAME`と`GCS_UPLOAD_ENABLED=true`を設定
- GCSが設定されていない場合は、自動的にローカルのみのバックアップになります

#### バックアップ作成
```bash
# ローカルとGCSの両方にバックアップ（デフォルト）
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database backup

# ローカルのみにバックアップ
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database backup --no-gcs

# 従来のスクリプトを使用（ローカルのみ）
./scripts/backup-database.sh backup
```

#### バックアップ一覧の確認
```bash
# ローカルとGCSのバックアップを表示
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database list

# ローカルのバックアップのみ表示
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database list --no-gcs

# 従来のスクリプトを使用
./scripts/backup-database.sh list
```

#### リストア実行
```bash
# ローカルファイルからリストア
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database restore database/backups/sagebase_backup_20241230_123456.sql

# GCSからリストア
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database restore gs://sagebase-scraped-minutes/database-backups/sagebase_backup_20241230_123456.sql

# 従来のスクリプトを使用（ローカルのみ）
./scripts/backup-database.sh restore database/backups/sagebase_backup_20240529_123456.sql
```

#### 手動バックアップ・リストア
```bash
# 手動バックアップ
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U sagebase_user sagebase_db > backup.sql

# 手動リストア
docker compose -f docker/docker-compose.yml exec -T postgres psql -U sagebase_user -d sagebase_db < backup.sql
```

## 🔧 開発

### コードフォーマットとリンティング
```bash
# コードフォーマット
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff format .

# リンティング
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff check .

# 型チェック
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen pyright
```

詳細な開発用コマンドは [COMMANDS.md](COMMANDS.md#開発用コマンド) を参照してください。

## 📊 監視システム

Sagebaseには、Grafana、Prometheus、Lokiを使用した包括的な監視システムが含まれています。

### 監視サービスの起動

```bash
# 監視サービスを起動
docker compose -f docker/docker-compose.yml -f docker/docker-compose.monitoring.yml up -d

# 動作確認
docker compose -f docker/docker-compose.yml exec sagebase uv run python scripts/verify_monitoring.py
```

### アクセスURL

- **Grafana**: http://localhost:3000 (初期: admin/admin)
- **Prometheus**: http://localhost:9091
- **Loki**: http://localhost:3100

### 提供されるダッシュボード

1. **システム概要**: 稼働状況、エラー率、処理済み議事録数
2. **パフォーマンス**: API応答時間、データベース性能、LLM使用状況
3. **エラー追跡**: エラー率の推移、タイプ別分析、ログ検索
4. **ビジネスメトリクス**: 議事録処理統計、データ品質指標

### 主要なメトリクス

- システムの可用性（SLO: > 99.5%）
- P95レスポンスタイム（SLO: < 2秒）
- エラー率（SLO: < 1%）
- LLMトークン使用量とコスト推定

詳細な設定とカスタマイズ方法は [監視システムセットアップガイド](docs/monitoring/grafana-setup.md) を参照してください。

## ⚙️ 環境変数設定

主要な環境変数（`.env`ファイルで設定）:

### 必須設定
- `GOOGLE_API_KEY`: Google Gemini APIキー（議事録処理・政治家抽出に必要）
- `DATABASE_URL`: PostgreSQL接続URL（デフォルト: `postgresql://sagebase_user:sagebase_password@localhost:5432/sagebase_db`）

### タイムアウト設定（秒単位）
- `WEB_SCRAPER_TIMEOUT`: Webページ読み込みタイムアウト（デフォルト: 60秒）
- `PDF_DOWNLOAD_TIMEOUT`: PDFダウンロードタイムアウト（デフォルト: 120秒）
- `PAGE_LOAD_TIMEOUT`: ページロード状態待機タイムアウト（デフォルト: 30秒）
- `SELECTOR_WAIT_TIMEOUT`: セレクタ待機タイムアウト（デフォルト: 10秒）

### その他の設定
- `LLM_MODEL`: 使用するLLMモデル（デフォルト: `gemini-2.0-flash`）
- `LLM_TEMPERATURE`: LLMの温度パラメータ（デフォルト: 0.0）
- `GCS_BUCKET_NAME`: Google Cloud Storageバケット名
- `GCS_UPLOAD_ENABLED`: GCS自動アップロード有効化（`true`/`false`）
- `GCS_PROJECT_ID`: Google CloudプロジェクトID（省略時はデフォルト使用）

処理時間の長いスクレイピングや大きなPDFファイルの処理でタイムアウトが発生する場合は、これらの値を調整してください。

## 📁 プロジェクト構成

```
sagebase/
├── src/                          # メインアプリケーションコード
│   ├── cli.py                   # 統一CLIエントリーポイント
│   ├── process_minutes.py       # 議事録分割処理
│   ├── extract_speakers_from_minutes.py   # 発言者抽出処理
│   ├── update_speaker_links.py  # 発言者紐付け更新スクリプト（レガシー）
│   ├── update_speaker_links_llm.py # LLMベース発言者マッチングスクリプト
│   ├── update_speaker_links_llm_refactored.py # LLMベース発言者マッチング（リファクタリング版）
│   ├── config/                   # 設定ファイル
│   │   ├── database.py          # データベース接続設定
│   │   ├── config.py            # アプリケーション設定
│   │   └── settings.py          # 環境変数管理
│   ├── common/                   # 共通機能
│   │   ├── app_logic.py         # アプリケーション共通ロジック
│   │   └── database_utils.py    # データベース共通処理
│   ├── minutes_divide_processor/ # 議事録分割処理
│   │   └── minutes_divider.py   # 分割ロジック
│   ├── politician_extract_processor/ # 政治家抽出処理
│   ├── web_scraper/             # 議事録Web取得
│   │   ├── base_scraper.py      # スクレーパー基底クラス
│   │   ├── kaigiroku_net_scraper.py # kaigiroku.net対応スクレーパー
│   │   └── scraper_service.py   # スクレーパーサービス
│   ├── database/                 # データベースリポジトリ
│   │   ├── meeting_repository.py # 会議データリポジトリ
│   │   └── ...                  # その他リポジトリ
│   ├── utils/                   # ユーティリティ関数
│   │   └── gcs_storage.py       # Google Cloud Storageユーティリティ（GCS URI対応）
│   │
│   ├── domain/                  # ドメイン層（Clean Architecture）
│   │   ├── entities/            # ドメインエンティティ
│   │   │   ├── base.py         # 基底エンティティ
│   │   │   ├── governing_body.py
│   │   │   ├── conference.py
│   │   │   ├── meeting.py
│   │   │   ├── politician.py
│   │   │   └── ...
│   │   ├── repositories/        # リポジトリインターフェース
│   │   │   ├── base.py         # 基底リポジトリ
│   │   │   └── ...
│   │   └── services/           # ドメインサービス
│   │       ├── speaker_domain_service.py
│   │       ├── politician_domain_service.py
│   │       └── ...
│   │
│   ├── application/            # アプリケーション層（Clean Architecture）
│   │   ├── dtos/              # データ転送オブジェクト
│   │   │   ├── speaker_dto.py
│   │   │   ├── politician_dto.py
│   │   │   └── ...
│   │   └── usecases/          # ユースケース
│   │       ├── process_minutes_usecase.py
│   │       ├── match_speakers_usecase.py
│   │       └── ...
│   │
│   ├── infrastructure/         # インフラストラクチャ層（Clean Architecture）
│   │   ├── persistence/       # データ永続化実装
│   │   │   ├── base_repository_impl.py
│   │   │   └── speaker_repository_impl.py
│   │   └── external/          # 外部サービス連携
│   │       ├── llm_service.py
│   │       ├── storage_service.py
│   │       └── web_scraper_service.py
│   │
│   └── interfaces/             # インターフェース層（Clean Architecture）
│       ├── cli/               # CLIインターフェース
│       ├── web/               # Webインターフェース（Streamlit）
│       └── bi_dashboard/      # BIダッシュボード（Plotly Dash・独立アプリ）
│           ├── app.py         # Dashアプリエントリーポイント
│           ├── layouts/       # レイアウト定義
│           ├── callbacks/     # インタラクティブロジック
│           ├── data/          # データ取得ロジック
│           ├── Dockerfile     # Docker設定
│           ├── docker-compose.yml  # 独立起動用設定
│           └── README.md      # BIダッシュボード詳細ドキュメント
│
├── database/                    # データベース関連
│   ├── init.sql                # データベース初期化スクリプト
│   ├── migrations/             # データベースマイグレーション
│   │   ├── 001_add_url_to_meetings.sql
│   │   ├── 002_add_members_list_url_to_political_parties.sql
│   │   ├── 003_add_politician_details.sql
│   │   ├── 004_add_gcs_uri_to_meetings.sql  # GCS URI保存用カラム追加
│   │   ├── 013_create_llm_processing_history.sql  # LLM処理履歴テーブル
│   │   └── 014_create_prompt_versions.sql  # プロンプトバージョン管理テーブル
│   └── backups/                # データベースバックアップファイル
├── docker/                      # Docker関連ファイル
│   ├── docker-compose.yml       # Docker Compose設定（永続化モード）
│   ├── docker-compose.temp.yml  # Docker Compose設定（非永続化モード）
│   └── Dockerfile               # Dockerイメージ設定
├── scripts/                     # 管理スクリプト
│   ├── backup-database.sh      # データベースバックアップスクリプト
│   ├── reset-database.sh       # データベースリセットスクリプト
│   ├── test-setup.sh           # セットアップテストスクリプト
│   └── setup_database.sh       # データベースセットアップスクリプト
├── docs/                       # ドキュメント
│   ├── ARCHITECTURE.md         # システムアーキテクチャ説明
│   └── CLEAN_ARCHITECTURE_MIGRATION.md  # Clean Architecture移行ガイド
├── data/                       # データファイル
├── tests/                      # テストコード
│   ├── domain/                # ドメイン層のテスト
│   │   └── test_speaker_domain_service.py
│   └── pytest.ini              # pytest設定ファイル
├── backup-database.sh          # → scripts/backup-database.sh (シンボリックリンク)
├── reset-database.sh           # → scripts/reset-database.sh (シンボリックリンク)
├── test-setup.sh              # → scripts/test-setup.sh (シンボリックリンク)
├── pyproject.toml             # Python依存関係
├── CLAUDE.md                  # Claude Code用ガイド
└── sagebase.dbml              # データベーススキーマ定義
```

## 🛠️ トラブルシューティング

### Docker関連のエラー

#### ポートが既に使用されている場合
```bash
# 使用中のポートを確認
lsof -i :5432
lsof -i :8000

# Docker Composeを再起動
docker compose down
docker compose up -d
```

#### データベース接続エラー
```bash
# PostgreSQLコンテナのログを確認
docker compose -f docker/docker-compose.yml logs postgres

# データベース接続テスト
./test-setup.sh
```

#### コンテナのリセット
```bash
# 全てのコンテナとボリュームを削除して再作成
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

#### データベースの問題

**データベースのリセット方法**:

`reset-database.sh`スクリプトは、データベースを完全にリセットして初期状態に戻します。このスクリプトは以下を実行します：
- 既存のデータベースを削除
- テーブルの再作成（init.sql）
- 全マイグレーションの適用（migrations/*.sql）
- 初期データの投入（seed_*.sql）

```bash
# ローカル環境から実行（推奨）
./scripts/reset-database.sh

# または、プロジェクトルートから実行
bash scripts/reset-database.sh
```

**注意**:
- このスクリプトはホストマシンから実行します（Docker内ではありません）
- 実行時に確認プロンプトが表示されます
- 全てのデータが削除されるため、必要に応じてバックアップを取得してください

**古いデータを残したい場合**:
```bash
# バックアップを作成してからリセット
./scripts/backup-database.sh backup
./scripts/reset-database.sh
```

**ディスク容量不足**:
```bash
# 不要なDockerボリュームを削除
docker volume prune

# 古いイメージを削除
docker image prune -a
```

### Python環境の問題

#### uvが見つからない場合
```bash
# uvをインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

#### 依存関係の問題
```bash
# 依存関係を再インストール
uv sync --reinstall
```

### Google Cloud Storage関連の問題

#### 認証エラー
```bash
# GCP認証を再設定
gcloud auth application-default login

# プロジェクトIDを設定
gcloud config set project YOUR_PROJECT_ID
```

#### バケットアクセスエラー
```bash
# バケットの存在確認
gsutil ls gs://YOUR_BUCKET_NAME/

# 権限の確認
gsutil iam get gs://YOUR_BUCKET_NAME/
```

## 🏗️ アーキテクチャ

> 📚 **詳細な図とガイド**: [docs/diagrams/](docs/diagrams/) にすべてのアーキテクチャ図と詳細な説明があります
> 📖 **包括的なドキュメント**: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) でアーキテクチャの全体像を参照
> ☁️ **クラウドアーキテクチャ**: GCP上でのデプロイメント設計については [docs/architecture/ARCHITECTURE.md#クラウドアーキテクチャ-google-cloud-platform](docs/architecture/ARCHITECTURE.md#クラウドアーキテクチャ-google-cloud-platform) を参照

### Clean Architecture

Sagebaseは、保守性と拡張性を向上させるためClean Architectureを採用しています。

**移行状況**: 🟢 **90%完了** - コアアーキテクチャは完全に実装され、レガシーコードのクリーンアップが進行中です。

**注**: 以下はアーキテクチャの概要です。詳細な説明、データフロー図、セキュリティ設計、クラウド構成などは **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** を参照してください。

### アーキテクチャ概要図

```mermaid
graph TB
    subgraph interfaces["🖥️ Interfaces Layer"]
        CLI["CLI Commands"]
        WEB["Streamlit UI"]
    end

    subgraph application["⚙️ Application Layer"]
        UC["Use Cases (21)"]
        DTO["DTOs (16)"]
    end

    subgraph domain["🎯 Domain Layer (Core)"]
        ENT["Entities (21)"]
        DS["Domain Services (18)"]
        RI["Repository Interfaces (22)"]
    end

    subgraph infrastructure["🔧 Infrastructure Layer"]
        PERSIST["Persistence (22+)"]
        EXT["External Services"]
    end

    CLI --> UC
    WEB --> UC
    UC --> DS
    UC --> RI
    PERSIST -.implements.-> RI

    classDef interfaceStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef applicationStyle fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef domainStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    classDef infrastructureStyle fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class interfaces interfaceStyle
    class application applicationStyle
    class domain domainStyle
    class infrastructure infrastructureStyle
```

**重要原則**:
- 依存関係は内側（ドメイン層）に向かう
- ドメイン層は外部フレームワークに依存しない
- 各層を独立してテスト可能

**詳細な図**:
- [レイヤー依存関係図](docs/diagrams/layer-dependency.mmd) - 4層の詳細な依存関係
- [コンポーネント相互作用図](docs/diagrams/component-interaction.mmd) - リクエストフローの詳細
- [データフロー図](docs/diagrams/) - 主要ワークフローのシーケンス図
- [リポジトリパターン図](docs/diagrams/repository-pattern.mmd) - データアクセス層の実装

#### レイヤー構成

1. **ドメイン層** (`src/domain/`) - ✅ 完全実装
   - **エンティティ** (21ファイル): ビジネスルールを含む中心的なビジネスオブジェクト
     - `BaseEntity`: 共通基底クラス
     - 主要エンティティ: `Politician`, `Speaker`, `Meeting`, `Conference`, `Proposal` など
   - **リポジトリインターフェース** (22ファイル): データアクセスの抽象化
     - `BaseRepository[T]`: ジェネリック基底リポジトリ
     - `ISessionAdapter`: データベースセッション抽象化（Issue #592で完全性達成）
   - **ドメインサービス** (18ファイル): エンティティに属さないビジネスロジック
     - `SpeakerDomainService`, `PoliticianDomainService`, `MinutesDomainService` など
   - **サービスインターフェース** (8ファイル): 外部サービスへの抽象化
     - `ILLMService`, `IStorageService`, `IWebScraperService` など

2. **アプリケーション層** (`src/application/`) - ✅ 完全実装
   - **ユースケース** (21ファイル): アプリケーション固有のビジネスルール
     - `ProcessMinutesUseCase`: 議事録処理ワークフロー
     - `MatchSpeakersUseCase`: 発言者マッチング
     - `ScrapePoliticiansUseCase`: 政治家情報収集
     - その他管理系ユースケース
   - **DTO** (16ファイル): レイヤー間のデータ転送オブジェクト
     - ドメインエンティティの漏洩を防ぐ
     - バリデーションロジックを含む

3. **インフラストラクチャ層** (`src/infrastructure/`) - ✅ 完全実装
   - **永続化** (22+ファイル): データベースアクセスの実装
     - `BaseRepositoryImpl[T]`: ジェネリックSQLAlchemyリポジトリ
     - すべてのドメインリポジトリに対応する実装
     - `AsyncSessionAdapter`: 同期セッションのasyncラッパー
     - `UnitOfWorkImpl`: トランザクション管理
   - **外部サービス**: LLM、ストレージ、Webスクレイピングの実装
     - `GeminiLLMService`: Google Gemini API統合
     - `CachedLLMService`, `InstrumentedLLMService`: デコレーター
     - `GCSStorageService`: Google Cloud Storage統合
     - `WebScraperService`: Playwright Webスクレイピング
   - **その他**: DI Container, Logging, Monitoring, Error Handling

4. **インターフェース層** (`src/interfaces/`) - ✅ 大部分完了
   - **CLI** (`src/interfaces/cli/`): コマンドラインインターフェース
     - 統一CLIエントリーポイント: `sagebase`コマンド
     - 構造化されたコマンド群: scraping, database, processing, monitoring
   - **Web** (`src/interfaces/web/streamlit/`): Streamlit Webインターフェース
     - Views, Presenters, Components, DTOsで構成
     - ビジネスロジックとUIの完全分離

#### アーキテクチャの特徴

**完全な依存性逆転**:
- ドメイン層がすべてのインターフェースを定義
- インフラ層がドメインのインターフェースを実装
- 例: `ISessionAdapter` (domain) ← `AsyncSessionAdapter` (infrastructure)

**高いテスト容易性**:
- モックやスタブの作成が容易
- ドメインロジックを外部依存なしでテスト可能
- 統合テストとユニットテストの明確な分離

**将来の拡張性**:
- 新しいデータソースへの対応が容易
- LLMプロバイダーの切り替えが容易
- UIフレームワークの変更が容易

#### レガシーコードについて

以下のディレクトリ・ファイルは段階的に廃止予定です：
- `src/cli.py` → `src/interfaces/cli/cli.py` へ移行済み
- `src/streamlit/` → `src/interfaces/web/streamlit/` へ移行済み
- `src/monitoring_app.py` → `src/interfaces/metrics_app.py` へ移行済み

詳細は `tmp/clean_architecture_analysis_2025.md` を参照してください。

#### 参考ドキュメント

- [Clean Architecture移行ガイド](docs/architecture/CLEAN_ARCHITECTURE_MIGRATION.md) - 移行の詳細手順
- [アーキテクチャ分析レポート](tmp/clean_architecture_analysis_2025.md) - 実装状況の詳細分析

## 🗂️ データの流れ

### 標準フロー（PDFファイルから処理）
1. **議事録PDFの処理**: `src/process_minutes.py` - 議事録を発言単位に分割してデータベースに保存
2. **発言者情報の抽出**: `src/extract_speakers_from_minutes.py` - 発言から発言者情報を抽出してspeakersテーブルに保存
3. **発言者マッチング**: `update_speaker_links_llm.py` - LLMを活用して発言と発言者を高精度でマッチング
4. **政治家情報の取得**: `sagebase scrape-politicians` - 政党のWebサイトから最新の政治家情報を取得
5. **データベース保存**: 抽出・マッチングされた情報をPostgreSQLに保存
6. **分析・検索**: 蓄積されたデータから政治活動を分析

### Webスクレイピングフロー（GCS統合）
1. **議事録Web取得**: `sagebase scrape-minutes` - Webから議事録を取得
2. **GCS保存**: 取得したデータをGoogle Cloud Storageに自動アップロード
3. **URI記録**: GCS URIをmeetingsテーブルに保存
4. **GCSから処理**: `process_minutes.py --meeting-id` でGCSから直接データを取得して処理
5. **後続処理**: 政治家抽出、発言者マッチングなどの処理を実行

### LLM処理履歴管理システム
#### 処理履歴の記録（llm_processing_historyテーブル）
- **統一的な履歴管理**: すべてのLLM処理を1つのテーブルで管理
- **処理タイプ**: MINUTES_DIVISION（議事録分割）、SPEECH_EXTRACTION（発言抽出）、SPEAKER_MATCHING（発言者マッチング）、POLITICIAN_EXTRACTION（政治家抽出）など
- **詳細な記録内容**:
  - 使用したLLMモデル名とバージョン
  - 入力・出力トークン数とコスト
  - 処理時間と成功/失敗状態
  - 使用したプロンプトテンプレート
  - 処理対象のエンティティID（meeting_id、speaker_idなど）
- **活用例**:
  - 処理の成功率分析
  - コスト最適化のためのトークン使用量分析
  - エラー傾向の把握と改善

#### プロンプトバージョン管理（prompt_versionsテーブル）
- **バージョン管理**: プロンプトテンプレートの変更履歴を完全に追跡
- **アクティブバージョン**: 各プロンプトキー（minutes_divide、speaker_matchなど）ごとに1つのアクティブバージョンを管理
- **変数対応**: テンプレート内の変数を自動検出し、実行時に検証
- **メタデータ管理**: パフォーマンス指標、使用上の注意などを保存
- **活用例**:
  - 過去の処理の完全な再現
  - A/Bテストによるプロンプト改善
  - 効果的なプロンプトの分析と共有

## 🚀 クイックリファレンス

```bash
# 🏗️ 初期セットアップ
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
./test-setup.sh

# 🔄 通常の起動・停止
docker compose -f docker/docker-compose.yml up -d      # バックグラウンド起動
docker compose -f docker/docker-compose.yml down       # 停止（データは保持）

# 🏃 主要な処理実行
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase process-minutes      # 議事録分割
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase streamlit           # Web UI起動（管理）

# 📊 BIダッシュボード起動（別インスタンス）
cd src/interfaces/bi_dashboard && docker-compose up --build                                   # BIダッシュボード起動
```

📚 **すべてのコマンドの詳細は [COMMANDS.md](COMMANDS.md) を参照してください。**
