# Deployment Guide

このドキュメントは、Polibaseアプリケーションをクラウド環境（特にGoogle Cloud Platform）にデプロイする方法を説明します。

## 目次

- [環境別のデータベース構成](#環境別のデータベース構成)
- [Cloud SQL セットアップ](#cloud-sql-セットアップ)
- [ローカル開発環境からのCloud SQL接続](#ローカル開発環境からのcloud-sql接続)
- [データベース移行](#データベース移行)
- [GitHub Actionsによる自動デプロイ](#github-actionsによる自動デプロイ)
- [Cloud Run デプロイ](#cloud-run-デプロイ)
- [Secret Manager 設定](#secret-manager-設定)
- [バックアップと復元](#バックアップと復元)
- [トラブルシューティング](#トラブルシューティング)

---

## 環境別のデータベース構成

Polibaseは環境に応じて異なるデータベース構成を使用します。

### 📋 構成の概要

| 環境 | データベース | 接続方法 | 設定場所 | 用途 |
|------|-------------|---------|---------|------|
| **ローカル開発** | Docker PostgreSQL | 直接接続 (localhost:5432) | `.env` | 開発・テスト |
| **Cloud Run** | Cloud SQL | Cloud SQL Proxy（自動） | Terraform | 本番デプロイ |
| **ローカル→Cloud SQL** | Cloud SQL | Cloud SQL Proxy（手動） | `.env` + スクリプト | Cloud SQLのテスト |

### 🔧 ローカル開発環境（デフォルト）

**使用するデータベース**: DockerコンテナのPostgreSQL

**.envファイル設定**:
```bash
# ローカルPostgreSQL（デフォルト）
DATABASE_URL=postgresql://sagebase_user:sagebase_password@localhost:5432/sagebase_db
USE_CLOUD_SQL_PROXY=false  # または未設定
```

**起動方法**:
```bash
# Dockerコンテナを起動
just up

# アプリケーション起動
just streamlit
```

**特徴**:
- ✅ 高速な起動・停止
- ✅ GCP費用が発生しない
- ✅ オフラインで開発可能
- ✅ データのリセットが簡単（`./scripts/reset-database.sh`）

### ☁️ Cloud Runデプロイ（本番環境）

**使用するデータベース**: Cloud SQL（PostgreSQL）

**環境変数設定**: Terraformで自動設定
```bash
USE_CLOUD_SQL_PROXY=true
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
```

**デプロイ方法**:
```bash
# インフラ構築
cd terraform
terraform apply

# コンテナイメージのビルド＆デプロイ
docker build -t asia-northeast1-docker.pkg.dev/PROJECT_ID/polibase/streamlit-ui:latest .
docker push asia-northeast1-docker.pkg.dev/PROJECT_ID/polibase/streamlit-ui:latest

# Cloud Runへデプロイ（Terraformで自動実行可能）
gcloud run deploy sagebase-ui --image=... --region=asia-northeast1
```

**特徴**:
- ✅ Cloud SQL Proxyが自動的に設定される（`cloud_sql_instances`）
- ✅ Unixソケット経由で安全な接続
- ✅ VPCプライベート接続で高セキュリティ
- ✅ 自動バックアップ・高可用性

**Terraformによる自動設定**:

`terraform/modules/app/main.tf`では、すべてのCloud Runサービスに以下が自動設定されます：

```hcl
# Cloud SQL接続を有効化
cloud_sql_instances = [var.database_connection_name]

# 環境変数の自動設定
env {
  name  = "USE_CLOUD_SQL_PROXY"
  value = "true"
}

env {
  name  = "CLOUD_SQL_CONNECTION_NAME"
  value = var.database_connection_name
}
```

### 🔄 ローカル開発環境からCloud SQLに接続

**使用するデータベース**: Cloud SQL（PostgreSQL）
**接続方法**: Cloud SQL Proxy（手動起動）

**.envファイル設定**:
```bash
# Cloud SQL接続を有効化
USE_CLOUD_SQL_PROXY=true
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
CLOUD_SQL_UNIX_SOCKET_DIR=/cloudsql

# データベース認証情報
DB_USER=sagebase_user
DB_PASSWORD=YOUR_PASSWORD
DB_NAME=sagebase_db
```

**セットアップ方法**:
```bash
# 1. Cloud SQL Proxyをセットアップ
./scripts/cloud_sql_proxy_setup.sh

# 2. アプリケーション起動
just streamlit
```

**使用ケース**:
- 🧪 本番データでのローカルテスト
- 🔍 Cloud SQL接続のデバッグ
- 📊 本番データの分析

### 🎯 どの構成を使うべきか？

```mermaid
graph TD
    A[開発作業] --> B{何をしたい？}
    B -->|通常の開発・テスト| C[Docker PostgreSQL]
    B -->|本番デプロイ| D[Cloud Run + Cloud SQL]
    B -->|本番データで検証| E[ローカル + Cloud SQL Proxy]

    C --> F[.env: USE_CLOUD_SQL_PROXY=false]
    D --> G[Terraform: 自動設定]
    E --> H[.env: USE_CLOUD_SQL_PROXY=true]
```

**推奨**:
1. **日常の開発**: Docker PostgreSQL（デフォルト設定）
2. **本番デプロイ**: Terraformでインフラ構築 → Cloud Runにデプロイ
3. **必要に応じて**: Cloud SQL Proxyでローカルから本番DBにアクセス

---

## Cloud SQL セットアップ

### 前提条件

1. Google Cloud Platform（GCP）プロジェクトが作成されている
2. gcloud CLIがインストールされている
3. Terraformがインストールされている（v1.0以降）
4. 適切な権限（Cloud SQL管理者、Secret Manager管理者など）

### 1. Terraformによるインフラ構築

PolibaseのCloud SQLインフラはTerraformで管理されています。

```bash
cd terraform

# 初回のみ：Terraformを初期化
terraform init

# 変数ファイルを作成
cp terraform.tfvars.example terraform.tfvars

# terraform.tfvarsを編集
# 必要な変数を設定：
# - project_id: GCPプロジェクトID
# - region: デプロイ先リージョン（デフォルト: asia-northeast1）
# - database_password: データベースパスワード（Secret Managerで管理を推奨）
# - google_api_key: Google API Key (Gemini)

# プランの確認
terraform plan

# 適用
terraform apply
```

作成されるリソース：

- **Cloud SQL インスタンス**: PostgreSQL 15
- **データベース**: sagebase_db
- **データベースユーザー**: sagebase_user
- **VPCネットワーク**: プライベートIP接続用
- **Secret Manager**: API キーとパスワードの保存
- **バックアップ設定**: 自動バックアップ（7日間保持）

### 2. Cloud SQLインスタンスの確認

```bash
# インスタンス一覧
gcloud sql instances list --project=YOUR_PROJECT_ID

# インスタンスの詳細確認
gcloud sql instances describe INSTANCE_NAME --project=YOUR_PROJECT_ID

# 接続名の取得
gcloud sql instances describe INSTANCE_NAME \
  --project=YOUR_PROJECT_ID \
  --format='value(connectionName)'
```

---

## ローカル開発環境からのCloud SQL接続

ローカル開発環境からCloud SQLに接続するには、**Cloud SQL Auth Proxy**を使用します。

### Cloud SQL Auth Proxyのセットアップ

自動セットアップスクリプトを使用：

```bash
./scripts/cloud_sql_proxy_setup.sh
```

このスクリプトは以下を実行します：

1. Cloud SQL Auth Proxyのダウンロードとインストール
2. 環境変数の確認
3. GCP認証の確認
4. Unixソケットディレクトリの準備
5. Cloud SQL Auth Proxyの起動（オプション）

### 手動セットアップ

1. **Cloud SQL Auth Proxyのダウンロード**

```bash
# macOS (Intel)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64

# macOS (Apple Silicon)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.arm64

# Linux
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64

chmod +x cloud-sql-proxy
```

2. **GCP認証**

```bash
gcloud auth application-default login
```

3. **.envファイルの設定**

```bash
# Cloud SQL接続設定
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
USE_CLOUD_SQL_PROXY=true
CLOUD_SQL_UNIX_SOCKET_DIR=/cloudsql

# データベース認証情報
DB_USER=sagebase_user
DB_PASSWORD=YOUR_PASSWORD
DB_NAME=sagebase_db
```

4. **Cloud SQL Auth Proxyの起動**

```bash
# Unixソケット接続（推奨）
mkdir -p /cloudsql
./cloud-sql-proxy --unix-socket=/cloudsql PROJECT_ID:REGION:INSTANCE_NAME

# TCP接続（代替方法）
# ./cloud-sql-proxy --port=5433 PROJECT_ID:REGION:INSTANCE_NAME
# DATABASE_URL=postgresql://sagebase_user:password@localhost:5433/sagebase_db
```

### 接続テスト

```bash
# Pythonスクリプトで接続テスト
python -m src.infrastructure.config.database

# psqlで直接接続（Unixソケット）
psql "host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME user=sagebase_user dbname=sagebase_db"
```

---

## データベース移行

ローカルのPostgreSQLデータベースからCloud SQLへデータを移行します。

### 自動移行スクリプト

```bash
./scripts/migrate_to_cloud_sql.sh
```

このスクリプトは以下を実行します：

1. ローカルPostgreSQLからデータエクスポート
2. Cloud SQLインスタンスの確認
3. GCSへのバックアップアップロード
4. Cloud SQLへのインポート
5. 接続テストのセットアップ

### 手動移行手順

#### 1. ローカルデータベースのエクスポート

```bash
# Dockerコンテナからエクスポート
docker exec docker-postgres-1 pg_dump \
  -U sagebase_user \
  -d sagebase_db \
  --clean --if-exists \
  > backup.sql
```

#### 2. GCSへのアップロード

```bash
# GCSバケット作成（初回のみ）
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l asia-northeast1 gs://sagebase-backups

# バックアップをアップロード
gsutil cp backup.sql gs://sagebase-backups/migrations/backup_$(date +%Y%m%d).sql
```

#### 3. Cloud SQLへのインポート

```bash
gcloud sql import sql INSTANCE_NAME \
  gs://sagebase-backups/migrations/backup_YYYYMMDD.sql \
  --database=sagebase_db \
  --project=YOUR_PROJECT_ID
```

#### 4. インポート確認

```bash
# Cloud SQL Proxyを起動
./cloud-sql-proxy --unix-socket=/cloudsql PROJECT_ID:REGION:INSTANCE_NAME

# psqlで接続して確認
psql "host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME user=sagebase_user dbname=sagebase_db"

# テーブル一覧
\dt

# データ確認
SELECT COUNT(*) FROM meetings;
SELECT COUNT(*) FROM politicians;
```

---

## GitHub Actionsによる自動デプロイ

**推奨**: 本番環境へのデプロイには、GitHub Actionsによる自動デプロイを使用してください。

### 概要

mainブランチへのマージで自動的にCloud Runにデプロイされます。

- ✅ 自動テスト実行
- ✅ コード品質チェック
- ✅ Dockerイメージビルド
- ✅ Cloud Runデプロイ
- ✅ ヘルスチェック
- ✅ ロールバック機能

詳細は **[CI/CD Documentation](./CICD.md)** を参照してください。

### セットアップ

#### 1. GitHub Secretsの設定

リポジトリの **Settings** → **Secrets and variables** → **Actions** で以下を設定：

**必須Secrets**:
- `GCP_PROJECT_ID`: GCPプロジェクトID
- `GCP_SA_KEY`: サービスアカウントキー（JSON形式）

**オプションSecrets**:
- `GCP_REGION`: デプロイリージョン（デフォルト: asia-northeast1）
- `GCP_SERVICE_NAME`: Cloud Runサービス名（デフォルト: sagebase-streamlit）
- `CLOUD_SQL_INSTANCE`: Cloud SQLインスタンス名
- `SLACK_WEBHOOK_URL`: Slack通知用WebhookURL

#### 2. サービスアカウントの作成と権限設定

```bash
# サービスアカウント作成
gcloud iam service-accounts create github-actions-deployer \
  --display-name="GitHub Actions Deployer" \
  --project=YOUR_PROJECT_ID

# 必要な権限を付与
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# キーの作成とダウンロード
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### 3. Secret Managerの設定

GitHub Actionsでデプロイされるアプリケーションが使用するシークレット：

```bash
# Google API Key
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# データベースパスワード
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create database-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# Cloud Runサービスアカウントに権限付与
gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=YOUR_PROJECT_ID

gcloud secrets add-iam-policy-binding database-password \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=YOUR_PROJECT_ID
```

### デプロイフロー

#### 自動デプロイ（mainブランチへのマージ）

```bash
# 1. 開発ブランチで作業
git checkout -b feature/new-feature

# 2. コードの変更とコミット
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature

# 3. PRを作成
gh pr create --title "feat: add new feature"

# 4. レビューと承認後、mainにマージ
gh pr merge --squash

# 5. GitHub Actionsが自動実行
#    - テスト実行
#    - イメージビルド
#    - Cloud Runデプロイ
```

#### 手動デプロイ

GitHub UIから手動でトリガー：

1. リポジトリの **Actions** タブを開く
2. **Deploy to Cloud Run** ワークフローを選択
3. **Run workflow** をクリック
4. 環境を選択して実行

### ロールバック

デプロイに問題が発生した場合：

```bash
# 直前のリビジョンにロールバック
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"

./scripts/rollback.sh --previous
```

詳細は **[CI/CD Documentation](./CICD.md#ロールバック手順)** を参照してください。

### モニタリング

```bash
# デプロイ状況の確認
gcloud run services describe sagebase-streamlit \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# ログの確認
gcloud run logs tail sagebase-streamlit \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

---

## Cloud Run デプロイ

**注**: 以下は手動デプロイの手順です。本番環境へのデプロイには上記の「GitHub Actionsによる自動デプロイ」を推奨します。

PolibaseのStreamlitアプリケーションをCloud Runにデプロイする方法を説明します。

### 前提条件

1. GCPプロジェクトが作成されている
2. gcloud CLIがインストール・認証済み
3. Docker Engineがインストールされている
4. Cloud SQL インスタンスが作成されている（[Cloud SQL セットアップ](#cloud-sql-セットアップ)参照）
5. Secret Managerにシークレットが登録されている（[Secret Manager 設定](#secret-manager-設定)参照）

### 方法1: 自動デプロイスクリプト（推奨）

最も簡単な方法は、用意されているデプロイスクリプトを使用することです。

```bash
# 環境変数を設定
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"
export CLOUD_SQL_INSTANCE="your-project:asia-northeast1:sagebase-db"

# デプロイスクリプトを実行
./scripts/deploy_to_cloud_run.sh
```

このスクリプトは以下を自動実行します：

1. Artifact Registryリポジトリの確認/作成
2. Dockerイメージのビルド（`Dockerfile.cloudrun`使用）
3. イメージのプッシュ
4. Cloud Runサービスのデプロイ
5. ヘルスチェックの確認

### 方法2: Cloud Build（CI/CD）

Cloud Buildを使用した自動デプロイも可能です。

```bash
# Cloud Build設定ファイルを使用してデプロイ
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_CLOUD_SQL_INSTANCE="PROJECT_ID:REGION:INSTANCE_NAME" \
  --project=YOUR_PROJECT_ID
```

`cloudbuild.yaml`では以下のステップが実行されます：

1. Dockerイメージのビルド
2. Artifact Registryへのプッシュ
3. Cloud Runへのデプロイ
4. ヘルスチェックの確認

### 方法3: 手動デプロイ（詳細制御）

#### 1. コンテナイメージのビルド

```bash
# Artifact Registryリポジトリの作成（初回のみ）
gcloud artifacts repositories create polibase \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# Docker認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# Dockerイメージのビルド（Cloud Run用Dockerfile使用）
docker build -f Dockerfile.cloudrun \
  -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:latest .

# イメージのプッシュ
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:latest
```

#### 2. Cloud Runサービスのデプロイ

```bash
gcloud run deploy sagebase-streamlit \
  --image=asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=2 \
  --memory=2Gi \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0 \
  --set-env-vars="CLOUD_RUN=true,PORT=8080,HEALTH_CHECK_PORT=8081,LOG_LEVEL=INFO" \
  --set-env-vars="USE_CLOUD_SQL_PROXY=true" \
  --set-env-vars="CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME" \
  --set-env-vars="CLOUD_SQL_UNIX_SOCKET_DIR=/cloudsql" \
  --set-env-vars="DB_USER=sagebase_user" \
  --set-env-vars="DB_NAME=sagebase_db" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-secrets="DB_PASSWORD=database-password:latest" \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
  --no-cpu-throttling \
  --project=YOUR_PROJECT_ID
```

**重要事項**:

- `--add-cloudsql-instances`: Cloud SQL Proxyを自動設定
- `--port=8080`: Streamlitアプリのポート
- `--no-cpu-throttling`: アイドル時のCPU制限を無効化（レスポンス速度向上）
- `--set-secrets`: Secret Managerからシークレットを自動注入

### ローカルテスト

デプロイ前にローカルでCloud Run環境をテストできます。

```bash
# ローカルテストスクリプトを実行
./scripts/test_cloud_run_locally.sh
```

このスクリプトは以下を実行します：

1. `Dockerfile.cloudrun`でイメージをビルド
2. ローカルでコンテナを起動
3. ヘルスチェックエンドポイント確認（`http://localhost:8081/health`）
4. Streamlitアプリケーション確認（`http://localhost:8080`）

### デプロイ後の確認

```bash
# サービスURLの取得
SERVICE_URL=$(gcloud run services describe sagebase-streamlit \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# ヘルスチェック確認（注: Cloud Runではポート8081は外部公開されません）
# ヘルスチェックはCloud Run内部で使用されます

# アプリケーションアクセス
curl "$SERVICE_URL"

# ログの確認
gcloud run logs tail sagebase-streamlit \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

### 環境変数とシークレット

Cloud Runサービスで設定される主な環境変数：

| 環境変数 | 値 | 説明 |
|---------|-----|------|
| `CLOUD_RUN` | `true` | Cloud Run環境フラグ |
| `PORT` | `8080` | Streamlitアプリのポート |
| `HEALTH_CHECK_PORT` | `8081` | ヘルスチェックポート（内部使用） |
| `USE_CLOUD_SQL_PROXY` | `true` | Cloud SQL Proxy有効化 |
| `CLOUD_SQL_CONNECTION_NAME` | `PROJECT:REGION:INSTANCE` | Cloud SQLインスタンス名 |
| `LOG_LEVEL` | `INFO` | ログレベル |

Secret Managerから注入されるシークレット：

- `GOOGLE_API_KEY`: Google Gemini API キー
- `DB_PASSWORD`: データベースパスワード

### サービスの更新

既存のサービスを更新する場合：

```bash
# 新しいイメージをビルド＆プッシュ
docker build -f Dockerfile.cloudrun \
  -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:v2 .
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:v2

# サービスを更新
gcloud run services update sagebase-streamlit \
  --image=asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/sagebase-streamlit:v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

または、デプロイスクリプトを再実行：

```bash
./scripts/deploy_to_cloud_run.sh
```

---

## Secret Manager 設定

機密情報はSecret Managerで管理します。

### シークレットの作成

```bash
# Google API Key
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# データベースパスワード
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create database-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# Sentry DSN（オプション）
echo -n "YOUR_SENTRY_DSN" | gcloud secrets create sentry-dsn \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID
```

### シークレットの使用

Terraformでは`terraform/modules/security/main.tf`でSecret Managerを管理しています。

Cloud Runでシークレットを使用：

```bash
gcloud run services update sagebase-ui \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-secrets="DB_PASSWORD=database-password:latest" \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

---

## バックアップと復元

### 自動バックアップ

Cloud SQLの自動バックアップはTerraformで設定済み：

- **バックアップ時間**: 毎日 3:00 AM JST
- **保持期間**: 7日間
- **Point-in-Time Recovery**: 有効

```bash
# バックアップ一覧
gcloud sql backups list --instance=INSTANCE_NAME --project=YOUR_PROJECT_ID

# バックアップからの復元
gcloud sql backups restore BACKUP_ID \
  --backup-instance=SOURCE_INSTANCE \
  --backup-id=BACKUP_ID \
  --project=YOUR_PROJECT_ID
```

### 手動バックアップ

```bash
# オンデマンドバックアップ
gcloud sql backups create --instance=INSTANCE_NAME --project=YOUR_PROJECT_ID

# GCSへのエクスポート（推奨）
gcloud sql export sql INSTANCE_NAME \
  gs://sagebase-backups/manual-backups/backup_$(date +%Y%m%d_%H%M%S).sql \
  --database=sagebase_db \
  --project=YOUR_PROJECT_ID
```

### Point-in-Time Recovery

```bash
# 特定の時刻に復元
gcloud sql instances clone SOURCE_INSTANCE TARGET_INSTANCE \
  --point-in-time='2024-01-15T10:00:00.000Z' \
  --project=YOUR_PROJECT_ID
```

---

## トラブルシューティング

### Cloud SQL Proxyが接続できない

**症状**: `connection refused` または `permission denied`

**解決方法**:

1. GCP認証を確認

```bash
gcloud auth application-default login
gcloud auth application-default print-access-token
```

2. Cloud SQL Admin APIが有効か確認

```bash
gcloud services enable sqladmin.googleapis.com --project=YOUR_PROJECT_ID
```

3. IAM権限を確認（Cloud SQL Client ロールが必要）

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/cloudsql.client"
```

### データベース接続エラー

**症状**: `FATAL: password authentication failed`

**解決方法**:

1. パスワードを確認

```bash
# Secret Managerから取得
gcloud secrets versions access latest --secret=database-password --project=YOUR_PROJECT_ID
```

2. ユーザーを再作成

```bash
gcloud sql users set-password sagebase_user \
  --instance=INSTANCE_NAME \
  --password=NEW_PASSWORD \
  --project=YOUR_PROJECT_ID
```

### Cloud Runからの接続エラー

**症状**: Cloud Runサービスがデータベースに接続できない

**解決方法**:

1. Cloud SQL接続が設定されているか確認

```bash
gcloud run services describe sagebase-ui \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format='value(spec.template.spec.containers[0].cloudSqlInstances)'
```

2. 環境変数を確認

```bash
gcloud run services describe sagebase-ui \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format='value(spec.template.spec.containers[0].env)'
```

3. Cloud Runサービスアカウントに権限を付与

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"
```

### インポート/エクスポートエラー

**症状**: `AccessDeniedException` または timeout

**解決方法**:

1. Cloud SQL サービスアカウントにGCSアクセス権限を付与

```bash
# Cloud SQLサービスアカウントを確認
gcloud sql instances describe INSTANCE_NAME \
  --format='value(serviceAccountEmailAddress)' \
  --project=YOUR_PROJECT_ID

# GCSバケットへのアクセス権限を付与
gsutil iam ch serviceAccount:SERVICE_ACCOUNT_EMAIL:objectAdmin \
  gs://sagebase-backups
```

2. ファイルサイズとタイムアウトを確認

```bash
# 大きなファイルの場合、圧縮を検討
gzip backup.sql
gsutil cp backup.sql.gz gs://sagebase-backups/
```

---

## 参考リンク

- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

---

## 更新履歴

- 2024-01-XX: 初版作成（PBI-003対応）
