# トラブルシューティングガイド

本ドキュメントは、Sagebase本番環境でよく発生する問題とその解決方法を説明します。

## 目次

- [サービスが応答しない](#サービスが応答しない)
- [データベース接続エラー](#データベース接続エラー)
- [GCS接続エラー](#gcs接続エラー)
- [Gemini API エラー](#gemini-api-エラー)
- [パフォーマンス問題](#パフォーマンス問題)
- [デプロイエラー](#デプロイエラー)
- [メモリ不足エラー](#メモリ不足エラー)
- [認証エラー](#認証エラー)

---

## サービスが応答しない

### 症状

- ブラウザでサービスにアクセスできない
- `curl`でタイムアウトまたは接続拒否
- Uptime checkアラートが発火

### 診断手順

#### 1. Cloud Runサービスの状態確認

```bash
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"

gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.conditions)"
```

**期待される出力**: すべてのconditionが`True`

#### 2. 最新のリビジョン確認

```bash
gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --limit=5
```

#### 3. ログの確認

```bash
# 最新のエラーログを確認
gcloud run logs tail $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --filter="severity>=ERROR" \
  --limit=50
```

### 解決方法

#### Case 1: リビジョンがデプロイに失敗している

**原因**: イメージのビルドエラー、環境変数の設定ミス、シークレットの参照エラー

**解決策**:
1. 最新のデプロイログを確認
2. 問題を修正して再デプロイ
3. または直前の正常なリビジョンにロールバック

```bash
./scripts/rollback.sh --previous
```

#### Case 2: すべてのインスタンスがクラッシュしている

**原因**: アプリケーションのバグ、メモリ不足、依存関係の問題

**解決策**:
1. クラッシュログを確認
```bash
gcloud run logs read $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --filter="severity=CRITICAL OR severity=ERROR" \
  --limit=100
```

2. 直前の正常なリビジョンにロールバック
```bash
./scripts/rollback.sh --previous
```

3. 問題を修正して再デプロイ

#### Case 3: Cloud SQL接続の問題

**原因**: データベースダウン、ネットワーク設定の問題

**解決策**: [データベース接続エラー](#データベース接続エラー) を参照

---

## データベース接続エラー

### 症状

- アプリケーションで`OperationalError`または`DatabaseError`
- ログに`could not connect to server`または`connection refused`
- タイムアウトエラー

### 診断手順

#### 1. Cloud SQLインスタンスの状態確認

```bash
export CLOUD_SQL_INSTANCE="your-instance-name"

gcloud sql instances describe $CLOUD_SQL_INSTANCE \
  --project=$PROJECT_ID \
  --format="value(state)"
```

**期待される出力**: `RUNNABLE`

#### 2. データベース接続設定の確認

```bash
# Cloud Runサービスの環境変数確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)"

# Cloud SQL接続設定の確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.cloudSqlInstances)"
```

#### 3. データベースログの確認

```bash
gcloud logging read \
  "resource.type=cloudsql_database AND severity>=ERROR" \
  --project=$PROJECT_ID \
  --limit=50 \
  --format=json
```

### 解決方法

#### Case 1: Cloud SQLインスタンスが停止している

**原因**: メンテナンス、手動停止、課金問題

**解決策**:
```bash
# インスタンスを起動
gcloud sql instances patch $CLOUD_SQL_INSTANCE \
  --activation-policy=ALWAYS \
  --project=$PROJECT_ID
```

#### Case 2: 接続数が上限に達している

**原因**: コネクションプールの設定ミス、接続リーク

**診断**:
```bash
# アクティブな接続数を確認
gcloud logging read \
  "resource.type=cloudsql_database AND metric.type=\"cloudsql.googleapis.com/database/network/connections\"" \
  --project=$PROJECT_ID \
  --limit=10
```

**解決策**:
1. 一時的にmax_connectionsを増やす
```bash
gcloud sql instances patch $CLOUD_SQL_INSTANCE \
  --database-flags=max_connections=200 \
  --project=$PROJECT_ID
```

2. アプリケーションのコネクションプール設定を確認・修正
3. 長時間実行中のクエリを調査

```sql
-- psqlで実行
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;
```

#### Case 3: 認証エラー

**原因**: パスワード不一致、Secret Manager設定ミス

**解決策**:
```bash
# Secret Managerのパスワードを確認
gcloud secrets versions access latest \
  --secret=database-password \
  --project=$PROJECT_ID

# パスワードをリセット
gcloud sql users set-password sagebase_user \
  --instance=$CLOUD_SQL_INSTANCE \
  --password=NEW_PASSWORD \
  --project=$PROJECT_ID

# Secret Managerを更新
echo -n "NEW_PASSWORD" | gcloud secrets versions add database-password \
  --data-file=- \
  --project=$PROJECT_ID
```

#### Case 4: VPC/ネットワーク設定の問題

**原因**: VPC Connectorの設定ミス、プライベートIP設定の問題

**解決策**:
```bash
# VPC Connectorの状態確認
gcloud compute networks vpc-access connectors describe CONNECTOR_NAME \
  --region=$REGION \
  --project=$PROJECT_ID

# Cloud Runサービスが正しいVPC Connectorを使用しているか確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.vpcAccess.connector)"
```

---

## GCS接続エラー

### 症状

- ファイルのアップロード/ダウンロードに失敗
- `google.api_core.exceptions.Forbidden`または`PermissionDenied`
- `google.api_core.exceptions.NotFound`

### 診断手順

#### 1. バケットの存在確認

```bash
export MINUTES_BUCKET="${PROJECT_ID}-sagebase-minutes-production"

gsutil ls -b gs://$MINUTES_BUCKET
```

#### 2. IAM権限の確認

```bash
# サービスアカウントの確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.serviceAccountName)"

# バケットのIAMポリシー確認
gsutil iam get gs://$MINUTES_BUCKET
```

### 解決方法

#### Case 1: バケットが存在しない

**解決策**:
```bash
# Terraformで作成（推奨）
cd terraform
terraform apply -target=module.storage

# または手動で作成
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$MINUTES_BUCKET
```

#### Case 2: 権限不足

**解決策**:
```bash
# サービスアカウントにStorage Object Admin権限を付与
export SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.serviceAccountName)")

gsutil iam ch serviceAccount:$SERVICE_ACCOUNT:objectAdmin gs://$MINUTES_BUCKET
```

#### Case 3: ストレージクォータ超過

**診断**:
```bash
# バケットの使用量確認
gsutil du -sh gs://$MINUTES_BUCKET
```

**解決策**:
1. 古いファイルを削除またはアーカイブ
2. ライフサイクルポリシーの確認・調整
3. 必要に応じてストレージクォータを増加

---

## Gemini API エラー

### 症状

- `google.api_core.exceptions.PermissionDenied`
- `ResourceExhausted`: クォータ超過
- `InvalidArgument`: リクエストパラメータの問題

### 診断手順

#### 1. Vertex AI API有効化確認

```bash
gcloud services list --enabled \
  --project=$PROJECT_ID \
  --filter="name:aiplatform.googleapis.com"
```

#### 2. API キー/認証情報の確認

```bash
# USE_VERTEX_AIフラグの確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.containers[0].env)" | grep VERTEX_AI
```

#### 3. APIログの確認

```bash
gcloud logging read \
  "resource.type=aiplatform.googleapis.com/Endpoint AND severity>=ERROR" \
  --project=$PROJECT_ID \
  --limit=50
```

### 解決方法

#### Case 1: API未有効化

**解決策**:
```bash
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
```

#### Case 2: クォータ超過

**診断**:
```bash
# クォータ使用状況の確認
gcloud logging read \
  "protoPayload.status.code=8" \
  --project=$PROJECT_ID \
  --limit=10
```

**解決策**:
1. Cloud Console → IAM & Admin → Quotas でクォータを確認
2. 必要に応じてクォータ増加をリクエスト
3. 一時的にリクエスト頻度を制限

#### Case 3: 認証エラー

**解決策**:
```bash
# サービスアカウントにVertex AI User権限を付与
export SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.serviceAccountName)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"
```

---

## パフォーマンス問題

### 症状

- レスポンスタイムが遅い（3秒以上）
- タイムアウトエラー
- ユーザーから「遅い」という報告

### 診断手順

#### 1. Cloud Monitoringダッシュボードの確認

Cloud Console → Monitoring → Dashboards → "Sagebase Monitoring Dashboard"

以下のメトリクスを確認：
- Response Latency (p50, p95, p99)
- CPU Utilization
- Memory Utilization
- Instance Count

#### 2. スロークエリの確認

```bash
# Cloud Runログでレスポンスタイムを確認
gcloud run logs read $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="table(timestamp, httpRequest.latency, httpRequest.requestUrl)" \
  --limit=100
```

#### 3. データベースパフォーマンスの確認

```sql
-- psqlで実行
-- 実行時間の長いクエリ
SELECT
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
ORDER BY duration DESC;

-- インデックス使用状況
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

### 解決方法

#### Case 1: コールドスタート

**原因**: インスタンスが0にスケールダウンしていて、新しいリクエストで起動に時間がかかる

**解決策**:
```bash
# 最小インスタンス数を1以上に設定
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --min-instances=1
```

#### Case 2: CPU/メモリ不足

**診断**: Cloud Monitoringダッシュボードで確認

**解決策**:
```bash
# リソースを増やす
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --cpu=4 \
  --memory=4Gi
```

#### Case 3: データベースのスロークエリ

**診断**: 上記のスロークエリを確認

**解決策**:
1. インデックスを追加
```sql
-- 例: speakers テーブルの name カラムにインデックス
CREATE INDEX idx_speakers_name ON speakers(name);
```

2. クエリを最適化（N+1問題の解消、不要なJOINの削除）

3. データベースインスタンスをスケールアップ
```bash
gcloud sql instances patch $CLOUD_SQL_INSTANCE \
  --tier=db-custom-4-16384 \
  --project=$PROJECT_ID
```

#### Case 4: 外部API呼び出しの遅延

**原因**: Gemini API呼び出しが遅い、タイムアウト

**解決策**:
1. タイムアウト値を調整
2. キャッシュを実装
3. 非同期処理に変更

---

## デプロイエラー

### 症状

- GitHub Actionsのデプロイが失敗
- `gcloud run deploy`コマンドがエラー
- イメージのビルドに失敗

### 診断手順

#### 1. GitHub Actionsログの確認

GitHub → Actions → 該当のワークフロー実行 → ログを確認

#### 2. イメージビルドログの確認

```bash
# Cloud Buildログの確認
gcloud builds list --project=$PROJECT_ID --limit=10
```

#### 3. デプロイログの確認

```bash
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.latestCreatedRevisionName)"

# 最新リビジョンのログ
gcloud run revisions describe REVISION_NAME \
  --region=$REGION \
  --project=$PROJECT_ID
```

### 解決方法

#### Case 1: Dockerイメージビルドエラー

**原因**: Dockerfileの構文エラー、依存関係の問題

**解決策**:
1. ローカルでイメージをビルドして確認
```bash
docker build -f Dockerfile.cloudrun -t test:latest .
```

2. エラーメッセージに従ってDockerfileを修正
3. 再デプロイ

#### Case 2: Secret Manager参照エラー

**原因**: シークレットが存在しない、権限不足

**解決策**:
```bash
# シークレットの存在確認
gcloud secrets list --project=$PROJECT_ID

# シークレットが存在しない場合は作成
echo -n "YOUR_VALUE" | gcloud secrets create SECRET_NAME \
  --data-file=- \
  --replication-policy=automatic \
  --project=$PROJECT_ID

# Cloud Runサービスアカウントに権限付与
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor" \
  --project=$PROJECT_ID
```

#### Case 3: リソースクォータ超過

**原因**: Cloud Runのリソースクォータに達している

**解決策**:
1. Cloud Console → IAM & Admin → Quotas で確認
2. 不要なリビジョンを削除
```bash
# 古いリビジョンを削除
gcloud run revisions delete OLD_REVISION \
  --region=$REGION \
  --project=$PROJECT_ID \
  --quiet
```

3. クォータ増加をリクエスト

---

## メモリ不足エラー

### 症状

- `MemoryError`または`OOMKilled`
- コンテナが突然再起動
- ログに`memory allocation failed`

### 診断手順

#### 1. メモリ使用状況の確認

Cloud Monitoring → Dashboards → "Sagebase Monitoring Dashboard" → Memory Utilization

#### 2. クラッシュログの確認

```bash
gcloud run logs read $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --filter="textPayload:\"OOMKilled\" OR textPayload:\"MemoryError\"" \
  --limit=50
```

### 解決方法

#### Case 1: メモリ割り当てが不足

**解決策**:
```bash
# メモリを増やす
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --memory=4Gi
```

#### Case 2: メモリリーク

**診断**: アプリケーションコードのメモリリークをプロファイリング

**解決策**:
1. メモリリークを修正
2. 定期的なインスタンス再起動
3. `gc.collect()`を適切な箇所で実行

#### Case 3: 大きなファイル処理

**原因**: 大きなPDFや画像をメモリ上で処理

**解決策**:
1. ストリーミング処理に変更
2. チャンク処理を実装
3. 一時ファイルを使用

---

## 認証エラー

### 症状

- `google.auth.exceptions.DefaultCredentialsError`
- `PermissionDenied`
- `Unauthorized`

### 診断手順

#### 1. サービスアカウントの確認

```bash
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.serviceAccountName)"
```

#### 2. IAM権限の確認

```bash
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" \
  --format="table(bindings.role)"
```

### 解決方法

#### Case 1: サービスアカウントが設定されていない

**解決策**:
```bash
# サービスアカウントを作成
gcloud iam service-accounts create cloud-run-sa \
  --display-name="Cloud Run Service Account" \
  --project=$PROJECT_ID

# Cloud Runサービスにサービスアカウントを設定
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --service-account=cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

#### Case 2: 権限不足

**解決策**:
```bash
# 必要な権限を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"
```

---

## 緊急時の対応フロー

### 重大な障害が発生した場合

1. **即座にロールバック**
```bash
./scripts/rollback.sh --previous
```

2. **関係者に通知**
   - Slackチャンネルに投稿
   - ステークホルダーにメール

3. **原因調査**
   - ログを収集
   - メトリクスを確認
   - インシデントレポートを作成

4. **修正とデプロイ**
   - 問題を修正
   - ステージング環境でテスト
   - 本番環境にデプロイ

5. **事後レビュー**
   - インシデントレポート作成
   - 再発防止策の検討
   - ドキュメント更新

---

## よく使うコマンド集

### クイックリファレンス

```bash
# サービス状態確認
gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID

# ログ確認
gcloud run logs tail $SERVICE_NAME --region=$REGION --project=$PROJECT_ID

# ロールバック
./scripts/rollback.sh --previous

# スモークテスト
./scripts/smoke_test.sh

# データベース接続
psql "host=/cloudsql/$CLOUD_SQL_CONNECTION_NAME user=sagebase_user dbname=sagebase_db"

# バケット確認
gsutil ls -b gs://${PROJECT_ID}-sagebase-minutes-production
```

---

## 関連ドキュメント

- [OPERATIONS.md](./OPERATIONS.md) - 日常運用手順
- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ

## サポート

問題が解決しない場合は、以下に連絡してください：

- **技術サポート**: [連絡先を記載]
- **緊急連絡先**: [連絡先を記載]
