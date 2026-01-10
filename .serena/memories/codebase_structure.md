# Polibase Codebase Structure

## Root Directory Structure
```
sagebase/
├── src/                    # Main application code
├── database/              # Database scripts and migrations
├── docker/                # Docker configuration
├── tests/                 # Test files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── data/                  # Data files
├── tmp/                   # Temporary files (gitignored)
├── .github/               # GitHub Actions workflows
├── pyproject.toml         # Python dependencies and config
├── justfile              # Just command runner tasks
├── CLAUDE.md             # Claude Code instructions
├── COMMANDS.md           # Command reference
└── README.md             # Project overview
```

## Clean Architecture Structure (主要構造)

### Domain Layer (`src/domain/`)
- `entities/`: ビジネスエンティティ
  - `base.py`: BaseEntity with common fields
  - `conference.py`, `governing_body.py`, `meeting.py`
  - `politician.py`, `speaker.py`, `proposal.py`
  - `parliamentary_group.py`, `extracted_conference_member.py`
  - `llm_processing_history.py`: LLM処理履歴 (新規追加予定)
- `repositories/`: リポジトリインターフェース
  - `base.py`: BaseRepository[T] generic interface
  - Entity-specific repository interfaces
- `services/`: ドメインサービス
  - `speaker_domain_service.py`: Speaker business logic
  - `politician_domain_service.py`: Politician deduplication
  - `minutes_domain_service.py`: Minutes processing
  - `conference_domain_service.py`: Conference member logic
  - `parliamentary_group_domain_service.py`: Group membership
- `types/`: Type definitions and enums

### Application Layer (`src/application/`)
- `usecases/`: ユースケース実装
  - `process_minutes_usecase.py`: 議事録処理
  - `match_speakers_usecase.py`: 話者マッチング
  - `manage_conference_members_usecase.py`: 議員管理
  - `manage_parliamentary_groups_usecase.py`: 議員団管理
- `dtos/`: データ転送オブジェクト
  - Input/Output DTOs for each use case

### Infrastructure Layer (`src/infrastructure/`)
- `persistence/`: データベース実装
  - `base_repository.py`: BaseRepositoryImpl[T]
  - Entity-specific repository implementations
  - `llm_processing_history_repository.py`: (新規追加予定)
- `external/`: 外部サービス統合
  - `llm_service.py`: ILLMService interface
  - `gemini_llm_service.py`: Gemini API implementation
  - `instrumented_llm_service.py`: 履歴記録対応 (新規追加予定)
  - `storage_service.py`: IStorageService
  - `gcs_storage_service.py`: Google Cloud Storage
  - `playwright_scraper_service.py`: Web scraping
- `interfaces/`: サービスインターフェース定義
  - `llm_service.py`: LLM service contract
  - `storage_service.py`: Storage service contract
  - `web_scraper_service.py`: Scraper contract

### Interfaces Layer (`src/interfaces/`)
- `web/streamlit/`: Streamlit UI (Clean Architecture完了)
- `cli/`: CLI interfaces (完了)

## Feature Modules (機能別モジュール)

### 議事録処理
- `src/minutes_divide_processor/`: LangGraph-based processing
  - `minutes_divider.py`: Main processor
  - `graph.py`: LangGraph state machine
  - `nodes.py`: Processing nodes
  - `state.py`: State definitions

### 政治家・議員情報抽出
- `src/party_member_extractor/`: 政党メンバー抽出
- `src/conference_member_extractor/`: 議会メンバー抽出
- `src/parliamentary_group_member_extractor/`: 議員団メンバー抽出

### Web Scraping
- `src/web_scraper/`: スクレイピング実装
  - `kaigiroku_scraper.py`: kaigiroku.net対応
  - `url_extractor.py`: URL抽出
  - `batch_scraper.py`: バッチ処理

### CLI Package
- `src/cli_package/`: CLIコマンド構造
  - `commands/`: 各コマンド実装
    - `process_minutes.py`, `scrape_politicians.py`
    - `extract_speakers.py`, `update_speakers.py`
    - `conference_members.py`, `coverage.py`
  - `base.py`: Base command classes
  - `utils.py`: CLI utilities

## Database Structure
- `database/init.sql`: 初期スキーマ
- `database/migrations/`: マイグレーションファイル
  - `001-012_*.sql`: 既存マイグレーション
  - `013_create_llm_processing_history.sql`: LLM履歴 (新規追加予定)
  - `014_create_prompt_versions.sql`: プロンプト管理 (新規追加予定)
- `database/02_run_migrations.sql`: マイグレーション実行
- `database/seed_*.sql`: マスターデータ
- `database/backups/`: バックアップ保存

## Test Structure
- `tests/domain/`: ドメイン層テスト
- `tests/application/`: アプリケーション層テスト
- `tests/infrastructure/`: インフラ層テスト
- `tests/integration/`: 統合テスト
- `tests/evaluation/`: LLM評価テスト

## Configuration
- `.env.example`: 環境変数テンプレート
- `pyrightconfig.json`: 型チェック設定
- `.pre-commit-config.yaml`: Pre-commitフック
- `justfile`: Justコマンド定義
- `docker/docker-compose.yml`: Docker設定
- `docker/docker-compose.override.yml`: ポート上書き (git worktree用)

## Entry Points
- `src/cli_package/`: メインCLI (sagebaseコマンド)
- `src/interfaces/web/streamlit/app.py`: Streamlit UI (Clean Architecture)
- `src/monitoring_app.py`: モニタリングダッシュボード

## 移行状況
- Clean Architecture移行: ✅ 95% Complete
- レガシーStreamlit削除完了 (Issue #602)
- 詳細: `docs/CLEAN_ARCHITECTURE_MIGRATION.md`

## 開発中の機能
- LLM処理履歴記録システム (#128)
- プロンプトバージョン管理
- 処理トレーサビリティ向上
