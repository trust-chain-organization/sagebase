# 運用手順書（Operations Guide）

本ドキュメントは、Sagebase本番環境の日常的な運用手順を説明します。

## 目次

- [日常運用タスク](#日常運用タスク)
- [監視とアラート](#監視とアラート)
- [ログの確認](#ログの確認)
- [バックアップと復元](#バックアップと復元)
- [スケーリング](#スケーリング)
- [デプロイとロールバック](#デプロイとロールバック)
- [データベースメンテナンス](#データベースメンテナンス)
- [セキュリティ管理](#セキュリティ管理)
- [定期メンテナンス](#定期メンテナンス)

---

## 日常運用タスク

### 毎日のチェックリスト

#### 1. サービス稼働確認

```bash
# Cloud Runサービスの状態確認
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"

gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.conditions[0].status)"
```

**期待される結果**: `True`

#### 2. スモークテストの実行

```bash
# 基本動作確認
export SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status.url)")

./scripts/smoke_test.sh
```

#### 3. エラーログの確認

```bash
# 過去24時間のエラーログを確認
gcloud run logs tail $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --filter="severity>=ERROR" \
  --format="table(timestamp, severity, textPayload)" \
  --limit=50
```

#### 4. リソース使用状況の確認

Cloud Monitoringダッシュボードで以下を確認：
- CPU使用率 (目標: 80%未満)
- メモリ使用率 (目標: 85%未満)
- レスポンスタイム (目標: p95で3秒未満)
- エラー率 (目標: 1%未満)

---

## 監視とアラート

### Cloud Monitoringダッシュボード

#### ダッシュボードへのアクセス

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを選択
3. **Monitoring** → **Dashboards** を開く
4. "Sagebase Monitoring Dashboard" を選択

#### 主要メトリクス

| メトリクス | 説明 | 閾値 | アクション |
|-----------|------|------|----------|
| Request Count | リクエスト数/秒 | - | トラフィックパターンの監視 |
| Error Rate (5xx) | 5xxエラー率 | 5% | エラーログ確認、必要に応じて緊急対応 |
| Response Latency | レスポンスタイム | p95で3秒 | パフォーマンス調査 |
| CPU Utilization | CPU使用率 | 80% | スケーリング検討 |
| Memory Utilization | メモリ使用率 | 85% | メモリリーク調査またはスケーリング |
| Instance Count | インスタンス数 | - | 負荷パターンの把握 |
| DB Connections | アクティブな接続数 | max_connections未満 | 接続プーリング確認 |

### アラート対応

#### アラートポリシー一覧

1. **Service Availability** - サービス停止
   - **トリガー**: Uptime checkが5分間失敗
   - **対応**: [トラブルシューティング](./TROUBLESHOOTING.md#サービスが応答しない) を参照

2. **High Error Rate** - エラー率上昇
   - **トリガー**: 5xxエラー率が5%超過
   - **対応**: エラーログ確認、必要に応じてロールバック

3. **High Response Time** - レスポンスタイム遅延
   - **トリガー**: p95レスポンスタイムが3秒超過
   - **対応**: パフォーマンス調査、スケーリング検討

4. **High CPU Usage** - CPU使用率上昇
   - **トリガー**: CPU使用率が80%超過
   - **対応**: インスタンス数増加またはCPU割り当て増加

5. **High Memory Usage** - メモリ使用率上昇
   - **トリガー**: メモリ使用率が85%超過
   - **対応**: メモリリーク調査またはメモリ割り当て増加

6. **Database Connection Failures** - DB接続失敗
   - **トリガー**: Cloud SQL接続数が0
   - **対応**: データベースとネットワーク設定確認

#### アラート通知設定

Slack通知を設定する場合：

```bash
# Notification Channelの作成
gcloud alpha monitoring channels create \
  --display-name="Slack - Sagebase Alerts" \
  --type=slack \
  --channel-labels=url=YOUR_SLACK_WEBHOOK_URL \
  --project=$PROJECT_ID
```

---

## ログの確認

### Cloud Runログの確認

#### リアルタイムログ

```bash
# すべてのログをリアルタイム表示
gcloud run logs tail $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID

# エラーログのみ表示
gcloud run logs tail $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --filter="severity>=ERROR"
```

#### 過去のログ検索

```bash
# 特定期間のログを検索
gcloud run logs read $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="table(timestamp, severity, textPayload)" \
  --filter="timestamp>=\"2024-01-15T00:00:00Z\"" \
  --limit=100
```

#### Log Explorerでの高度な検索

Cloud Console → Logging → Log Explorer で以下のクエリを使用：

```
resource.type="cloud_run_revision"
resource.labels.service_name="sagebase-streamlit"
severity>=ERROR
timestamp>="2024-01-15T00:00:00Z"
```

### データベースログの確認

```bash
# Cloud SQL インスタンスのログ
gcloud sql operations list \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID \
  --limit=10

# エラーログの確認
gcloud logging read \
  "resource.type=cloudsql_database AND severity>=ERROR" \
  --project=$PROJECT_ID \
  --limit=50 \
  --format=json
```

---

## バックアップと復元

### 自動バックアップ

Cloud SQLの自動バックアップは以下のスケジュールで実行されます：
- **時刻**: 毎日 3:00 AM JST
- **保持期間**: 7日間
- **Point-in-Time Recovery**: 有効（7日分のトランザクションログ）

#### バックアップ確認

```bash
# バックアップ一覧
gcloud sql backups list \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID

# 最新のバックアップ確認
gcloud sql backups list \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID \
  --limit=1
```

### 手動バックアップ

#### オンデマンドバックアップ

```bash
# 今すぐバックアップを作成
gcloud sql backups create \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID \
  --description="Manual backup before major update"
```

#### GCSへのエクスポート

```bash
# データベース全体をGCSにエクスポート
gcloud sql export sql INSTANCE_NAME \
  gs://${PROJECT_ID}-sagebase-backups/manual-backups/backup_$(date +%Y%m%d_%H%M%S).sql \
  --database=sagebase_db \
  --project=$PROJECT_ID
```

### データ復元

#### バックアップからの復元

```bash
# 特定のバックアップから復元
gcloud sql backups restore BACKUP_ID \
  --backup-instance=SOURCE_INSTANCE \
  --project=$PROJECT_ID

# 確認プロンプトをスキップする場合
gcloud sql backups restore BACKUP_ID \
  --backup-instance=SOURCE_INSTANCE \
  --project=$PROJECT_ID \
  --quiet
```

#### Point-in-Time Recovery

```bash
# 特定の時刻に復元（新しいインスタンスとしてクローン）
gcloud sql instances clone SOURCE_INSTANCE TARGET_INSTANCE \
  --point-in-time='2024-01-15T10:00:00.000Z' \
  --project=$PROJECT_ID
```

#### GCSからのインポート

```bash
# GCSからデータをインポート
gcloud sql import sql INSTANCE_NAME \
  gs://${PROJECT_ID}-sagebase-backups/manual-backups/backup_YYYYMMDD.sql \
  --database=sagebase_db \
  --project=$PROJECT_ID
```

---

## スケーリング

### Cloud Runのスケーリング

#### 自動スケーリング設定の確認

```bash
# 現在のスケーリング設定を確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(spec.template.spec.scaling)"
```

#### インスタンス数の調整

```bash
# 最小/最大インスタンス数を変更
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --min-instances=2 \
  --max-instances=20
```

**推奨設定**:
- **開発環境**: min=0, max=3
- **ステージング**: min=0, max=5
- **本番環境**: min=1, max=10

#### リソース割り当ての変更

```bash
# CPUとメモリを変更
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --cpu=4 \
  --memory=4Gi
```

### Cloud SQLのスケーリング

#### インスタンスタイプの変更

```bash
# より大きなインスタンスタイプに変更
gcloud sql instances patch INSTANCE_NAME \
  --tier=db-custom-4-16384 \
  --project=$PROJECT_ID
```

**インスタンスタイプ例**:
- `db-f1-micro`: 0.6GB RAM（開発用）
- `db-g1-small`: 1.7GB RAM（小規模）
- `db-custom-2-8192`: 2 vCPU, 8GB RAM（中規模）
- `db-custom-4-16384`: 4 vCPU, 16GB RAM（大規模）

#### ストレージの拡張

```bash
# ディスクサイズを拡張（縮小は不可）
gcloud sql instances patch INSTANCE_NAME \
  --storage-size=100 \
  --project=$PROJECT_ID
```

---

## デプロイとロールバック

### 通常のデプロイ

GitHub ActionsによるCI/CDを使用：

1. mainブランチにマージ
2. 自動でテスト実行
3. 自動でイメージビルド＆デプロイ
4. 自動でヘルスチェック

詳細は [DEPLOYMENT.md](./DEPLOYMENT.md) を参照。

### 緊急ロールバック

#### 直前のリビジョンにロールバック

```bash
./scripts/rollback.sh --previous
```

#### 特定のリビジョンにロールバック

```bash
# リビジョン一覧を確認
gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID

# 特定のリビジョンにロールバック
./scripts/rollback.sh --revision REVISION_NAME
```

---

## データベースメンテナンス

### 定期メンテナンス

Cloud SQLの自動メンテナンス:
- **曜日**: 日曜日
- **時刻**: 4:00 AM JST
- **内容**: マイナーバージョン更新、セキュリティパッチ

#### メンテナンスウィンドウの確認

```bash
gcloud sql instances describe INSTANCE_NAME \
  --project=$PROJECT_ID \
  --format="value(settings.maintenanceWindow)"
```

### データベース統計の更新

```bash
# Cloud SQL Proxyを起動してpsqlで接続
psql "host=/cloudsql/$CLOUD_SQL_CONNECTION_NAME user=sagebase_user dbname=sagebase_db"

# 統計情報の更新
ANALYZE;

# バキューム（自動バキュームが有効だが、必要に応じて手動実行）
VACUUM ANALYZE;
```

### インデックスの確認

```sql
-- 未使用インデックスの確認
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY schemaname, tablename;

-- インデックスサイズの確認
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## セキュリティ管理

### Secret Managerの管理

#### シークレットの確認

```bash
# シークレット一覧
gcloud secrets list --project=$PROJECT_ID

# シークレットの内容確認（最新バージョン）
gcloud secrets versions access latest \
  --secret=database-password \
  --project=$PROJECT_ID
```

#### シークレットの更新

```bash
# 新しいバージョンを追加
echo -n "NEW_PASSWORD" | gcloud secrets versions add database-password \
  --data-file=- \
  --project=$PROJECT_ID

# Cloud Runサービスを再起動して反映
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID
```

### IAM権限の監査

```bash
# サービスアカウントの権限確認
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:serviceAccount:*"
```

### アクセスログの確認

```bash
# Cloud Run アクセスログ
gcloud logging read \
  "resource.type=cloud_run_revision AND httpRequest.requestUrl!=\"\"" \
  --project=$PROJECT_ID \
  --format=json \
  --limit=100
```

---

## 定期メンテナンス

### 週次タスク

#### 1. バックアップの確認

```bash
# 過去7日分のバックアップを確認
gcloud sql backups list \
  --instance=INSTANCE_NAME \
  --project=$PROJECT_ID \
  --limit=7
```

#### 2. ログの確認とクリーンアップ

```bash
# エラーログの集計
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR" \
  --project=$PROJECT_ID \
  --format="table(timestamp, severity, jsonPayload.message)" \
  --freshness=7d
```

#### 3. コスト確認

Cloud Console → Billing → Cost Table で以下を確認：
- Cloud Run
- Cloud SQL
- Cloud Storage
- Vertex AI (Gemini API)

### 月次タスク

#### 1. パフォーマンスレビュー

Cloud Monitoringダッシュボードで過去30日間のメトリクスを確認：
- 平均レスポンスタイム
- エラー率
- リソース使用率のトレンド

#### 2. セキュリティアップデート

```bash
# 利用可能な更新を確認
gcloud sql instances describe INSTANCE_NAME \
  --project=$PROJECT_ID \
  --format="value(maintenanceVersion)"
```

#### 3. ストレージ使用量の確認

```bash
# Cloud SQLストレージ使用量
gcloud sql instances describe INSTANCE_NAME \
  --project=$PROJECT_ID \
  --format="value(settings.dataDiskSizeGb, currentDiskSize)"

# GCSバケット使用量
gsutil du -sh gs://${PROJECT_ID}-sagebase-minutes-production
gsutil du -sh gs://${PROJECT_ID}-sagebase-backups-production
```

---

## 関連ドキュメント

- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - トラブルシューティング
- [ARCHITECTURE.md](./ARCHITECTURE.md) - システムアーキテクチャ
- [MONITORING.md](./MONITORING.md) - 監視設定の詳細

---

## 緊急連絡先

問題が発生した場合の連絡先：

1. **技術責任者**: [連絡先を記載]
2. **データベース管理者**: [連絡先を記載]
3. **セキュリティ担当**: [連絡先を記載]

## エスカレーションフロー

1. アラート検知 → 運用担当者が初期対応
2. 30分以内に解決しない → 技術責任者にエスカレーション
3. 1時間以内に解決しない → すべてのステークホルダーに通知
