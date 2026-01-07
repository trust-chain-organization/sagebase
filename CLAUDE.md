# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**IMPORTANT: このプロジェクトでは、すべての説明、コメント、ドキュメントを日本語で記述してください。**

- コードのコメント: 日本語で記述
- Git commitメッセージ: 日本語で記述
- ドキュメント: 日本語で記述
- Claude Codeとのやり取り: 日本語で応答

This project primarily uses Japanese for all documentation, comments, and communication.

## Project Overview

Sagebase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

### Core Concepts

- **Politician Information**: Scraped from political party websites
- **Speakers & Speeches**: Extracted from meeting minutes
- **Speaker-Politician Matching**: LLM-based matching with hybrid approach
- **Parliamentary Groups**: Voting blocs within conferences
- **Staged Processing**: Multi-step workflows with manual review capability
- **Conference Member Extraction**: Web scraping + LLM extraction using BAML for structured output

## Quick Start

```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY
just up               # Start environment

# Run application
just up               # Start all services and launch Streamlit UI
just bi-dashboard     # Launch BI Dashboard

# Development
just test             # Run tests
just format && just lint  # Format and lint code

# Database
just db               # Connect to PostgreSQL
./reset-database.sh   # Reset database
```

**📖 For detailed commands**: See [.claude/skills/sagebase-commands/](.claude/skills/sagebase-commands/)

## Architecture

Sagebase follows **Clean Architecture** principles. **Status: 🟢 100% Complete**

### Layer Overview

```
src/
├── domain/          # Entities, Repository Interfaces, Domain Services (77 files)
├── application/     # Use Cases, DTOs (37 files)
├── infrastructure/  # Repository Implementations, External Services (63 files)
└── interfaces/      # CLI, Web UI (63 files)
```

### Key Principles

- **Dependency Rule**: Dependencies point inward (Domain ← Application ← Infrastructure ← Interfaces)
- **Entity Independence**: Domain entities have no framework dependencies
- **Repository Pattern**: All repositories use async/await with `ISessionAdapter`
- **DTO Usage**: DTOs for layer boundaries

**📖 For detailed architecture**: See [.claude/skills/clean-architecture-checker/](.claude/skills/clean-architecture-checker/)

### Visual Diagrams

- [Layer Dependency](docs/diagrams/layer-dependency.mmd)
- [Component Interaction](docs/diagrams/component-interaction.mmd)
- [Minutes Processing Flow](docs/diagrams/data-flow-minutes-processing.mmd)
- [Speaker Matching Flow](docs/diagrams/data-flow-speaker-matching.mmd)
- [Repository Pattern](docs/diagrams/repository-pattern.mmd)

**📖 Full documentation**: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

## Technology Stack

- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **Structured Output**: BAML (Boundary ML) for type-safe LLM outputs
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Management**: UV (modern Python package manager)
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Testing**: pytest with pytest-asyncio
- **Cloud Storage**: Google Cloud Storage
- **Data Visualization**: Plotly, Folium, Streamlit

## Skill Usage Guide

**重要**: 以下のskillは特定のタスクで自動的にアクティベートされるべきです。タスクの内容に応じて適切なskillを使用してください。

### Architecture & Code Quality

#### clean-architecture-checker
**使用タイミング**:
- `src/domain/`、`src/application/`、`src/infrastructure/`、`src/interfaces/` 配下のファイルを作成・修正する時
- Clean Architectureの原則に従っているか検証する必要がある時
- リポジトリパターン、依存性ルール、エンティティの独立性をチェックする時

#### test-writer
**使用タイミング**:
- テストファイルを作成する時
- テスト作成ガイドが必要な時
- 外部サービス（LLM、API）のモックが必要な時
- pytest-asyncioを使用した非同期テストを書く時
- CI失敗を防ぐためのテスト品質を確保したい時

### Development Workflow

#### project-conventions
**使用タイミング**:
- プロジェクトの規約とベストプラクティスを確認したい時
- Pre-commit hooks の遵守方法を知りたい時
- CI/CD運用のルールを確認したい時
- 中間ファイル管理（`tmp/`ディレクトリ）について知りたい時
- 知識蓄積層（`_docs/`）の活用方法を知りたい時

#### development-workflows
**使用タイミング**:
- Docker-first開発の手順を確認したい時
- 環境変数管理の方法を知りたい時
- 新機能追加の標準手順を確認したい時
- 日常的な開発作業のベストプラクティスを知りたい時

#### temp-file-management
**使用タイミング**:
- 一時ファイルを作成する時（データ処理の中間結果、ダウンロードファイルなど）
- 中間ファイルを作成する時（議事録処理、PDF解析、Web scrapingの結果など）
- ファイルパスを指定する時
- データ処理スクリプトを書く時

#### plan-writer
**使用タイミング**:
- 実装計画を作成する時
- 調査結果をドキュメント化する時
- 一時的な分析結果を保存する時
- Issue解決のための計画を立てる時
- **重要**: 計画ファイルは必ず`tmp/`に配置すること

#### sagebase-commands
**使用タイミング**:
- アプリケーションの起動方法を知りたい時
- テスト、フォーマット、lintコマンドを実行したい時
- データベース操作コマンドを知りたい時
- Dockerコマンドやsagebase CLIの使い方を知りたい時
- `just`コマンドの一覧を確認したい時

#### git-branch-cleanup
**使用タイミング**:
- ユーザーが「ブランチを整理」「ブランチをクリーンアップ」と依頼した時
- ユーザーが「古いブランチを削除」と依頼した時
- ユーザーが「どのブランチを削除できるか」と質問した時
- ユーザーが「Gitブランチを整理」と依頼した時
- 多数のローカルブランチが存在している時

### Database

#### migration-helper
**使用タイミング**:
- データベースマイグレーションファイルを作成する時
- テーブル、カラム、インデックスを追加・変更する時
- `database/02_run_migrations.sql`への追加が必要な時
- マイグレーションの命名規則（連番）を確認したい時

### Data Processing

#### data-processing-workflows
**使用タイミング**:
- 議事録処理のワークフローを理解したい時
- Web scrapingのパイプラインを確認したい時
- 政治家データ収集の処理フローを知りたい時
- 話者マッチングの依存関係・実行順序を理解したい時
- データ処理の全体像を把握したい時

#### baml-integration
**使用タイミング**:
- BAML (Boundary ML) の使い方を知りたい時
- BAML定義ファイルを作成・修正する時
- BAMLクライアントを再生成する必要がある時
- Factory Patternを使った実装を設計する時
- ハイブリッドアプローチ（ルールベース + LLM）を実装する時

#### data-layer-architecture
**使用タイミング**:
- LLM抽出処理を新規実装する時
- ExtractionLogエンティティを使用する時
- `is_manually_verified`フラグを扱う時
- 抽出結果からGoldエンティティを更新する時
- Bronze Layer / Gold Layerの設計について質問された時

### Operations

#### bi-dashboard-commands
**使用タイミング**:
- BI Dashboard (Plotly Dash) を起動したい時
- BI Dashboardのテストを実行したい時
- BI Dashboardの動作確認手順を知りたい時
- BI Dashboardのトラブルシューティングが必要な時

### SKILL Management

#### skill-design-principles
**使用タイミング**:
- 新しいSKILLを作成する時
- 既存のSKILLをレビュー・改善する時
- SKILLが適切かどうか判断する時
- CLAUDE.mdからSKILL化すべき内容を検討する時

## Documentation

### Architecture & Development

**📖 Overview Documents**:
- **[ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)**: Complete system architecture
- **[CLEAN_ARCHITECTURE_MIGRATION.md](docs/architecture/CLEAN_ARCHITECTURE_MIGRATION.md)**: Migration progress
- **[DEVELOPMENT_GUIDE.md](docs/guides/DEVELOPMENT_GUIDE.md)**: Development workflows

**📁 Architecture Decision Records (ADR)** - `docs/ADR/`:
アーキテクチャに関する重要な意思決定の記録を保管

- ADR作成ルール: `NNNN-kebab-case-title.md`形式、必須セクション（Status, Context, Decision, Consequences）
- 既存のADR:
  - [0001-clean-architecture-adoption.md](docs/ADR/0001-clean-architecture-adoption.md): Clean Architecture採用の経緯
  - [0002-baml-for-llm-outputs.md](docs/ADR/0002-baml-for-llm-outputs.md): BAML採用の経緯
  - [0003-repository-pattern.md](docs/ADR/0003-repository-pattern.md): Repository Pattern採用
  - [0004-langgraph-adapter-pattern.md](docs/ADR/0004-langgraph-adapter-pattern.md): LangGraph Adapter Pattern

**📁 Layer Guides** - `docs/architecture/`:
Clean Architectureの各層の詳細な実装ガイドを保管（責務、実装例、落とし穴、チェックリスト）

- [DOMAIN_LAYER.md](docs/architecture/DOMAIN_LAYER.md): エンティティ、リポジトリIF、ドメインサービス
- [APPLICATION_LAYER.md](docs/architecture/APPLICATION_LAYER.md): ユースケース、DTO、トランザクション管理
- [INFRASTRUCTURE_LAYER.md](docs/architecture/INFRASTRUCTURE_LAYER.md): リポジトリ実装、外部サービス
- [INTERFACE_LAYER.md](docs/architecture/INTERFACE_LAYER.md): CLI、Streamlit UI、プレゼンター

### Operations
- **[DEPLOYMENT.md](docs/guides/DEPLOYMENT.md)**: Deployment procedures
- **[BI_DASHBOARD.md](docs/guides/BI_DASHBOARD.md)**: BI Dashboard (Plotly Dash) setup and usage
- **[CICD.md](docs/guides/CICD.md)**: CI/CD workflows
- **[OPERATIONS.md](docs/guides/OPERATIONS.md)**: Operations guide
- **[TROUBLESHOOTING.md](docs/guides/TROUBLESHOOTING.md)**: Troubleshooting guide
- **[docs/monitoring/](docs/monitoring/)**: Monitoring setup (Grafana, Prometheus)

## Important Notes

### Critical Requirements
- **API Key Required**: `GOOGLE_API_KEY` must be set in `.env` for Gemini API access
- **Processing Order**: Always run `process-minutes → extract-speakers → update-speakers` in sequence
- **GCS Authentication**: Run `gcloud auth application-default login` before using GCS features

### File Management
- **Intermediate Files**: Always create temporary files in `tmp/` directory (gitignored)
- **Knowledge Base**: Record important decisions in `_docs/` (gitignored, for Claude's memory)
- **NEVER create .md files in docs/ without explicit approval** - docs/の構成は固定されています
- **Implementation plans go to tmp/** - 実装計画は`tmp/implementation_plan_{issue_number}.md`に配置

### Code Quality
- **Pre-commit Hooks**: **NEVER use `--no-verify`** - always fix errors before committing
- **Testing**: External services (LLM, APIs) must be mocked in tests
- **CI/CD**: Create Issues for any skipped tests with `continue-on-error: true`

### Database
- **Master Data**: Governing bodies and conferences are fixed master data
- **Coverage**: All 1,966 Japanese municipalities tracked with organization codes
- **Migrations**: Always add new migrations to `database/02_run_migrations.sql`

### Development
- **Docker-first**: All commands run through Docker containers
- **Unified CLI**: `sagebase` command provides single entry point
- **GCS URI Format**: Always use `gs://` format, not HTTPS URLs

**📖 For detailed conventions**: See [.claude/skills/project-conventions/](.claude/skills/project-conventions/)

## BAML Integration

### Overview
Sagebaseでは、以下の機能にBAML (Boundary ML)を使用しています。BAMLはLLMの構造化出力を型安全に扱うためのドメイン特化言語(DSL)です。

### Key Features
- **型安全性**: Pydanticモデルと完全に互換性のある型定義
- **トークン効率**: 最適化されたプロンプト生成により、従来のPydantic実装よりトークン使用量を削減
- **パース精度**: LLMの出力を確実に構造化データに変換
- **フィーチャーフラグ対応**: 環境変数で実装を切り替え可能

### BAML対応機能

#### 1. 議事録分割処理（Minutes Divider） **BAML専用**
- **BAML定義**: `baml_src/minutes_divider.baml`
- **実装**: `src/infrastructure/external/minutes_divider/baml_minutes_divider.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 2. 会議体メンバー抽出（Conference Member Extraction） **BAML専用**
- **BAML定義**: `baml_src/member_extraction.baml`
- **実装**: `src/infrastructure/external/conference_member_extractor/baml_extractor.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 3. 議員団メンバー抽出（Parliamentary Group Member Extraction） **BAML専用**
- **BAML定義**: `baml_src/parliamentary_group_member_extractor.baml`
- **実装**: `src/infrastructure/external/parliamentary_group_member_extractor/baml_extractor.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 4. 政党メンバー抽出（Party Member Extraction） **BAML専用**
- **BAML定義**: `baml_src/party_member_extractor.baml`
- **実装**: `src/party_member_extractor/baml_llm_extractor.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用

#### 5. 話者マッチング（Speaker Matching） **BAML専用**
- **BAML定義**: `baml_src/speaker_matching.baml`
- **実装**: `src/domain/services/baml_speaker_matching_service.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用
- **ハイブリッドアプローチ**: ルールベースマッチング（高速パス）+ BAMLマッチング

#### 6. 政治家マッチング（Politician Matching） **BAML専用**
- **BAML定義**: `baml_src/politician_matching.baml`
- **実装**: `src/domain/services/baml_politician_matching_service.py`
- **備考**: Pydantic実装は削除済み、BAML実装のみ使用
- **ハイブリッドアプローチ**: ルールベースマッチング（高速パス）+ BAMLマッチング

### Implementation Pattern
- **High-Speed Path**: ルールベースマッチング（完全一致、部分一致）で信頼度0.9以上の場合はLLMをスキップ
- **LLM Matching**: 複雑なケースのみBAMLを使用してマッチング

### トークン削減効果
- **議事録分割**: 約10-15%削減
- **話者マッチング**: 約5-10%削減（目標）
- **政治家マッチング**: 約10-15%削減（目標）

### Usage in Streamlit
会議体管理画面の「会議体一覧」タブで、会議体を選択して「選択した会議体から議員情報を抽出」ボタンをクリックすると、BAMLを使用してメンバー情報を抽出できます。抽出結果は「抽出結果確認」タブで確認できます。

## Data Layer Architecture（Bronze Layer / Gold Layer）

Sagebaseでは、LLM抽出結果と確定データを分離する**2層アーキテクチャ**を採用しています。

- **Bronze Layer（抽出ログ層）**: LLM抽出結果を追記専用（Immutable）で保存
- **Gold Layer（確定データ層）**: ユーザーに提供する確定データ、人間の修正が最優先

**📖 For detailed architecture**: See [.claude/skills/data-layer-architecture/](.claude/skills/data-layer-architecture/)
