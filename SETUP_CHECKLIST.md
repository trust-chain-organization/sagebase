# CI/CD & Cloud Run セットアップチェックリスト

このチェックリストは、SagebaseアプリケーションをCloud Runにデプロイするための完全なセットアップ手順です。
上から順番に進めてください。

**参照ドキュメント**:
- [CICD.md](docs/CICD.md)
- [DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✅ Phase 1: 事前準備

### 1.1 必要なツールの確認

- [x] **gcloud CLIのインストール確認**
  ```bash
  gcloud --version
  # インストールされていない場合: https://cloud.google.com/sdk/docs/install
  ```

- [x] **gcloud認証**
  ```bash
  gcloud auth login
  gcloud auth application-default login
  ```

- [x] **GitHub CLIのインストール確認**
  ```bash
  gh --version
  # インストールされていない場合: https://cli.github.com/
  ```

- [x] **Dockerのインストール確認**
  ```bash
  docker --version
  ```

### 1.2 GCPプロジェクトの設定

- [x] **プロジェクトIDを決定**
  ```bash
  # 既存プロジェクトを使用する場合
  export PROJECT_ID="your-existing-project-id"

  # または新規作成する場合
  export PROJECT_ID="sagebase-production"
  gcloud projects create $PROJECT_ID --name="Sagebase Production"
  ```

- [x] **プロジェクトIDを環境変数に保存**
  ```bash
  # ~/.bashrc または ~/.zshrc に追加
  echo "export PROJECT_ID=\"$PROJECT_ID\"" >> ~/.bashrc
  echo "export REGION=\"asia-northeast1\"" >> ~/.bashrc
  source ~/.bashrc
  ```

- [x] **プロジェクトを設定**
  ```bash
  gcloud config set project $PROJECT_ID
  ```

- [x] **課金アカウントの確認・設定**
  ```bash
  # 課金アカウント一覧
  gcloud billing accounts list

  # プロジェクトに課金アカウントをリンク
  gcloud billing projects link $PROJECT_ID \
    --billing-account=BILLING_ACCOUNT_ID
  ```

### 1.3 必要なAPIの有効化

- [x] **Cloud Run API**
  ```bash
  gcloud services enable run.googleapis.com --project=$PROJECT_ID
  ```

- [x] **Cloud SQL Admin API**
  ```bash
  gcloud services enable sqladmin.googleapis.com --project=$PROJECT_ID
  ```

- [x] **Artifact Registry API**
  ```bash
  gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
  ```

- [x] **Secret Manager API**
  ```bash
  gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID
  ```

- [x] **Cloud Build API**（オプション）
  ```bash
  gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
  ```

- [ ] **Vertex AI API**（Gemini使用のため必須）
  ```bash
  gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
  ```

- [x] **API有効化の確認**
  ```bash
  gcloud services list --enabled --project=$PROJECT_ID | grep -E "(run|sqladmin|artifactregistry|secretmanager|aiplatform)"
  ```

---

## ✅ Phase 2: Cloud SQLのセットアップ

### 2.1 Cloud SQLインスタンスの作成

- [ ] **インスタンス名を決定**
  ```bash
  export INSTANCE_NAME="sagebase-db"
  ```

- [x] **Cloud SQLインスタンスを作成**
  ```bash
  gcloud sql instances create sagebase-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=asia-northeast1 \
    --root-password="CHANGE_THIS_PASSWORD" \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --retained-backups-count=7 \
    --project=trust-chain-828ad

  # 注意: --root-password は安全なパスワードに変更してください
  ```

  **所要時間**: 約5-10分

- [x] **インスタンスの作成完了を確認**
  ```bash
  gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID
  ```

### 2.2 データベースとユーザーの作成

- [x] **データベースパスワードを決定**
  ```bash
  # 安全なパスワードを生成
  export DB_PASSWORD=$(openssl rand -base64 32)
  echo "DB_PASSWORD: $DB_PASSWORD"
  # このパスワードを安全に保存してください！
  ```

- [x] **データベースユーザーを作成**
  ```bash
  gcloud sql users create sagebase_user \
    --instance=sagebase-db \
    --password="$DB_PASSWORD" \
    --project=trust-chain-828ad
  ```

- [x] **データベースを作成**
  ```bash
  gcloud sql databases create sagebase_db \
    --instance=sagebase-db \
    --project=trust-chain-828ad
  ```

### 2.3 Cloud SQL接続名の取得

- [x] **接続名を取得して保存**
  ```bash
  export CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe sagebase-db \
    --project=trust-chain-828ad \
    --format='value(connectionName)')

  echo "CLOUD_SQL_CONNECTION_NAME: $CLOUD_SQL_CONNECTION_NAME"
  # 形式: PROJECT_ID:REGION:INSTANCE_NAME

  # 環境変数に保存
  echo "export CLOUD_SQL_CONNECTION_NAME=\"$CLOUD_SQL_CONNECTION_NAME\"" >> ~/.zshrc
  source ~/.zshrc
  ```

---

## ✅ Phase 3: Secret Managerのセットアップ

### 3.1 Vertex AI権限の設定（Gemini使用）

**注意**: Vertex AI経由でGeminiを使用するため、API Keyは不要です。代わりにService Accountに権限を付与します。

- [ ] **Vertex AI APIが有効化されていることを確認**
  ```bash
  gcloud services list --enabled --project=$PROJECT_ID | grep aiplatform
  ```

- [ ] **Cloud RunサービスアカウントにVertex AI権限を付与**
  ```bash
  # プロジェクト番号を取得
  export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

  # Vertex AI User権限を付与
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user"

  echo "Vertex AI権限を付与しました: ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  ```

- [ ] **権限付与の確認**
  ```bash
  gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

  # roles/aiplatform.user が表示されることを確認
  ```

### 3.2 データベースパスワードの登録

- [ ] **Secret Managerに登録**
  ```bash
  echo -n "$DB_PASSWORD" | gcloud secrets create database-password \
    --data-file=- \
    --replication-policy=automatic \
    --project=$PROJECT_ID
  ```

- [ ] **登録確認**
  ```bash
  gcloud secrets describe database-password --project=$PROJECT_ID
  ```

### 3.3 Secret Managerへのアクセス権限設定

- [ ] **Cloud RunサービスアカウントにSecret Manager権限付与**
  ```bash
  # プロジェクト番号を取得（上記で取得済みの場合はスキップ可）
  export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

  # データベースパスワードへのアクセス権限を付与
  gcloud secrets add-iam-policy-binding database-password \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
  ```

- [ ] **権限設定の確認**
  ```bash
  gcloud secrets get-iam-policy database-password --project=$PROJECT_ID

  # 以下が表示されることを確認:
  # - serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
  # - role: roles/secretmanager.secretAccessor
  ```

---

## ✅ Phase 4: GitHub Actions用サービスアカウントのセットアップ

### 4.1 サービスアカウントの作成

- [ ] **サービスアカウント作成**
  ```bash
  gcloud iam service-accounts create github-actions-deployer \
    --display-name="GitHub Actions Deployer" \
    --project=$PROJECT_ID
  ```

- [ ] **作成確認**
  ```bash
  gcloud iam service-accounts list --project=$PROJECT_ID
  ```

### 4.2 権限の付与

- [ ] **Cloud Run Admin権限**
  ```bash
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin"
  ```

- [ ] **Artifact Registry Writer権限**
  ```bash
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.writer"
  ```

- [ ] **Service Account User権限**
  ```bash
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"
  ```

- [ ] **Storage Admin権限**（イメージプッシュ用）
  ```bash
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin"
  ```

- [ ] **権限設定の確認**
  ```bash
  gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
  ```

### 4.3 サービスアカウントキーの作成

- [ ] **キーを作成してダウンロード**
  ```bash
  gcloud iam service-accounts keys create ~/github-actions-key.json \
    --iam-account=github-actions-deployer@${PROJECT_ID}.iam.gserviceaccount.com

  # キーファイルの確認
  ls -la ~/github-actions-key.json
  ```

- [ ] **キーファイルの内容を確認**
  ```bash
  cat ~/github-actions-key.json
  # この内容を次のステップでGitHub Secretsに登録します
  ```

---

## ✅ Phase 5: GitHub Secretsの設定

### 5.1 必須Secretsの設定

- [ ] **GCP_PROJECT_ID**
  ```bash
  gh secret set GCP_PROJECT_ID --body "$PROJECT_ID"
  ```

- [ ] **GCP_SA_KEY**
  ```bash
  gh secret set GCP_SA_KEY < ~/github-actions-key.json
  ```

- [ ] **GCP_REGION**
  ```bash
  gh secret set GCP_REGION --body "$REGION"
  ```

- [ ] **CLOUD_SQL_INSTANCE**
  ```bash
  gh secret set CLOUD_SQL_INSTANCE --body "$CLOUD_SQL_CONNECTION_NAME"
  ```

- [ ] **GCP_SERVICE_NAME**（オプション、デフォルト: sagebase-streamlit）
  ```bash
  gh secret set GCP_SERVICE_NAME --body "sagebase-streamlit"
  ```

- [ ] **GCP_ARTIFACT_REPOSITORY**（オプション、デフォルト: sagebase）
  ```bash
  gh secret set GCP_ARTIFACT_REPOSITORY --body "sagebase"
  ```

### 5.2 オプションSecretsの設定

- [ ] **SLACK_WEBHOOK_URL**（Slack通知を使用する場合）
  ```bash
  # Slackでincoming webhookを作成: https://api.slack.com/messaging/webhooks
  gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/..."
  ```

### 5.3 GitHub Secretsの確認

- [ ] **設定済みSecretsの確認**
  ```bash
  gh secret list
  ```

  期待される出力:
  ```
  GCP_PROJECT_ID
  GCP_SA_KEY
  GCP_REGION
  CLOUD_SQL_INSTANCE
  GCP_SERVICE_NAME
  GCP_ARTIFACT_REPOSITORY
  SLACK_WEBHOOK_URL (optional)
  ```

---

## ✅ Phase 6: Artifact Registryのセットアップ

### 6.1 Artifact Registryリポジトリの作成

- [ ] **リポジトリ作成**（GitHub Actionsで自動作成されますが、手動でも可）
  ```bash
  gcloud artifacts repositories create sagebase \
    --repository-format=docker \
    --location=$REGION \
    --description="Sagebase container images" \
    --project=$PROJECT_ID
  ```

- [ ] **作成確認**
  ```bash
  gcloud artifacts repositories describe sagebase \
    --location=$REGION \
    --project=$PROJECT_ID
  ```

### 6.2 Docker認証の設定

- [ ] **Docker認証設定**
  ```bash
  gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
  ```

- [ ] **認証確認**
  ```bash
  cat ~/.docker/config.json | grep "$REGION-docker.pkg.dev"
  ```

---

## ✅ Phase 7: データベース初期化

### 7.1 Cloud SQL Proxyのセットアップ

- [ ] **Cloud SQL Proxyをダウンロード**
  ```bash
  # macOS (Apple Silicon)
  curl -o ~/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.arm64

  # macOS (Intel)
  # curl -o ~/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64

  # Linux
  # curl -o ~/cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64

  chmod +x ~/cloud-sql-proxy
  ```

- [ ] **Cloud SQL Proxyを起動**（別ターミナルで）
  ```bash
  mkdir -p /tmp/cloudsql
  ~/cloud-sql-proxy --unix-socket=/tmp/cloudsql $CLOUD_SQL_CONNECTION_NAME
  ```

### 7.2 データベースマイグレーションの実行

- [ ] **psqlで接続確認**
  ```bash
  psql "host=/tmp/cloudsql/${CLOUD_SQL_CONNECTION_NAME} user=sagebase_user dbname=sagebase_db"
  # パスワード: $DB_PASSWORD
  ```

- [ ] **マイグレーションSQLを実行**
  ```bash
  # プロジェクトディレクトリに移動
  cd /path/to/sagebase

  # 初期化SQLを実行
  PGPASSWORD=$DB_PASSWORD psql \
    "host=/tmp/cloudsql/${CLOUD_SQL_CONNECTION_NAME} user=sagebase_user dbname=sagebase_db" \
    -f database/init.sql

  # マイグレーションを実行
  for file in database/migrations/*.sql; do
    if [ -f "$file" ]; then
      echo "Applying migration: $file"
      PGPASSWORD=$DB_PASSWORD psql \
        "host=/tmp/cloudsql/${CLOUD_SQL_CONNECTION_NAME} user=sagebase_user dbname=sagebase_db" \
        -f "$file"
    fi
  done
  ```

- [ ] **テーブル作成確認**
  ```bash
  PGPASSWORD=$DB_PASSWORD psql \
    "host=/tmp/cloudsql/${CLOUD_SQL_CONNECTION_NAME} user=sagebase_user dbname=sagebase_db" \
    -c "\dt"
  ```

---

## ✅ Phase 8: 初回デプロイ（手動）

### 8.1 ローカルでのDockerイメージビルドテスト

- [ ] **Dockerイメージをビルド**
  ```bash
  docker build -f Dockerfile.cloudrun -t test-sagebase .
  ```

- [ ] **ビルド成功確認**
  ```bash
  docker images | grep test-sagebase
  ```

### 8.2 GitHub Actionsでの手動デプロイ

- [ ] **GitHub UIから手動トリガー**
  1. リポジトリの **Actions** タブを開く
  2. **Deploy to Cloud Run** ワークフローを選択
  3. **Run workflow** をクリック
  4. 環境: `production` を選択
  5. **Run workflow** をクリック

- [ ] **デプロイ完了を確認**
  - GitHub Actionsのログを確認
  - すべてのステップが成功していることを確認

### 8.3 デプロイされたサービスの確認

- [ ] **Cloud Runサービス情報を取得**
  ```bash
  gcloud run services describe sagebase-streamlit \
    --region=$REGION \
    --project=$PROJECT_ID
  ```

- [ ] **サービスURLを取得**
  ```bash
  export SERVICE_URL=$(gcloud run services describe sagebase-streamlit \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.url)')

  echo "Service URL: $SERVICE_URL"
  ```

- [ ] **サービスにアクセス**
  ```bash
  # ブラウザで開く
  open $SERVICE_URL

  # またはcurlで確認
  curl $SERVICE_URL
  ```

- [ ] **ログを確認**
  ```bash
  gcloud run logs tail sagebase-streamlit \
    --region=$REGION \
    --project=$PROJECT_ID
  ```

---

## ✅ Phase 9: 自動デプロイの動作確認

### 9.1 テストコミットでの自動デプロイ

- [ ] **テストブランチを作成**
  ```bash
  git checkout -b test/auto-deploy
  ```

- [ ] **軽微な変更を加える**
  ```bash
  echo "# Test auto deploy" >> README.md
  git add README.md
  git commit -m "test: verify auto deploy"
  git push origin test/auto-deploy
  ```

- [ ] **PRを作成**
  ```bash
  gh pr create --title "test: verify auto deploy" --body "Testing automatic deployment"
  ```

- [ ] **CIチェックの完了を確認**
  - GitHub Actions の CI/テストワークフローが成功

- [ ] **PRをマージ**
  ```bash
  gh pr merge --squash
  ```

- [ ] **自動デプロイの開始を確認**
  - GitHub Actions の **Deploy to Cloud Run** ワークフローが自動起動

- [ ] **デプロイ完了を確認**
  - すべてのステップが成功
  - デプロイサマリーが表示される

- [ ] **サービスが更新されたことを確認**
  ```bash
  gcloud run revisions list \
    --service=sagebase-streamlit \
    --region=$REGION \
    --project=$PROJECT_ID \
    --limit=3
  ```

---

## ✅ Phase 10: ロールバックテスト

### 10.1 ロールバックスクリプトのテスト

- [ ] **リビジョン一覧を表示**
  ```bash
  export PROJECT_ID="$PROJECT_ID"
  export REGION="$REGION"
  export SERVICE_NAME="sagebase-streamlit"

  ./scripts/rollback.sh --list
  ```

- [ ] **前のリビジョンにロールバック**
  ```bash
  ./scripts/rollback.sh --previous
  ```

- [ ] **ロールバック成功を確認**
  ```bash
  gcloud run services describe sagebase-streamlit \
    --region=$REGION \
    --project=$PROJECT_ID \
    --format='value(status.latestReadyRevisionName)'
  ```

- [ ] **サービスが正常に動作することを確認**
  ```bash
  curl $SERVICE_URL
  ```

- [ ] **最新リビジョンに戻す**
  ```bash
  # リビジョン一覧から最新のリビジョン名を取得
  ./scripts/rollback.sh --list

  # 最新リビジョンにロールバック
  ./scripts/rollback.sh --revision LATEST_REVISION_NAME
  ```

---

## ✅ Phase 11: モニタリングとメンテナンス

### 11.1 モニタリングの設定

- [ ] **Cloud Runメトリクスの確認**
  ```bash
  # Cloud Consoleで確認
  open "https://console.cloud.google.com/run/detail/${REGION}/sagebase-streamlit/metrics?project=${PROJECT_ID}"
  ```

- [ ] **ログベースのアラート設定**（オプション）
  - Cloud Loggingでエラーログのアラート設定
  - Slackへの通知設定

### 11.2 定期メンテナンス

- [ ] **古いリビジョンの削除**
  ```bash
  # 最新5つを残して古いリビジョンを削除
  gcloud run revisions list \
    --service=sagebase-streamlit \
    --region=$REGION \
    --format="value(metadata.name)" \
    --sort-by="~metadata.creationTimestamp" \
    | tail -n +6 \
    | xargs -I {} gcloud run revisions delete {} \
      --region=$REGION \
      --quiet
  ```

- [ ] **Cloud SQLバックアップの確認**
  ```bash
  gcloud sql backups list --instance=$INSTANCE_NAME --project=$PROJECT_ID
  ```

---

## 🎉 セットアップ完了！

すべてのチェックが完了したら、以下が動作しています：

✅ Streamlitアプリケーションが Cloud Run で稼働
✅ Cloud SQL でデータベースが動作
✅ Secret Manager でシークレットが管理されている
✅ GitHub Actions で自動デプロイが動作
✅ ロールバック機能が使用可能

### 📚 次のステップ

- [ ] [CICD.md](docs/CICD.md) でベストプラクティスを確認
- [ ] [DEPLOYMENT.md](docs/DEPLOYMENT.md) で運用手順を確認
- [ ] チームメンバーに共有

### 🔗 便利なリンク

- **Cloud Runコンソール**: https://console.cloud.google.com/run?project=$PROJECT_ID
- **Cloud SQLコンソール**: https://console.cloud.google.com/sql?project=$PROJECT_ID
- **Secret Managerコンソール**: https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID
- **GitHub Actionsワークフロー**: https://github.com/trust-chain-organization/sagebase/actions

### 📞 トラブルシューティング

問題が発生した場合は、[docs/CICD.md#トラブルシューティング](docs/CICD.md#トラブルシューティング) を参照してください。

---

**作成日**: 2025-01-16
**バージョン**: 1.0.0
