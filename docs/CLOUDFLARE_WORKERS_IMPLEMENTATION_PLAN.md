# Cloudflare Workers実装計画

## 📋 エグゼクティブサマリー

Deep Researchの調査結果に基づき、**Cloudflare Workersを使用したリバースプロキシパターン**が最適解と判明しました。

### 主要な発見

1. ❌ **Transform Rulesでは不可能**: GUI経由でのHostヘッダー書き換えはEnterpriseプラン限定
2. ❌ **Cloud Runドメインマッピングの課題**: Cloudflareプロキシとの組み合わせでドメイン検証が失敗
3. ✅ **Cloudflare Workers**: Freeプランでも完全なHostヘッダー制御が可能

### 推奨アーキテクチャ

```
ユーザー
  ↓ HTTPS (app.sage-base.com)
Cloudflare Edge (Worker実行)
  ↓ Hostヘッダー書き換え (*.run.app)
Cloud Run (sagebase-streamlit)
  ↓
Cloud SQL
```

## 🎯 実装目標

- ✅ Google Cloud側の設定変更なし（ドメイン検証不要）
- ✅ CI/CD完全対応（GitHub Actions自動デプロイ）
- ✅ 無料プランで動作（10万リクエスト/日まで）
- ✅ セキュリティ強化（直接アクセス防止）
- ✅ Streamlit最適化（WebSocket対応）

---

## 📝 実装計画（4ステップ）

### Phase 1: Cloudflare Workerの作成とデプロイ

**作業時間**: 30分
**担当**: インフラ担当
**依存関係**: なし

#### タスク
1. ✅ `workers/` ディレクトリ作成
2. ✅ `workers/worker.js` 作成（プロキシスクリプト）
3. ✅ `workers/wrangler.toml` 作成（設定ファイル）
4. ✅ Cloudflare API Tokenの取得
5. ✅ 手動デプロイでテスト

### Phase 2: GitHub Actions CI/CD統合

**作業時間**: 20分
**担当**: DevOps担当
**依存関係**: Phase 1完了

#### タスク
1. ✅ `.github/workflows/deploy-worker.yml` 作成
2. ✅ GitHub SecretsにCloudflare認証情報を追加
3. ✅ デプロイワークフローのテスト

### Phase 3: セキュリティ強化

**作業時間**: 40分
**担当**: バックエンド担当
**依存関係**: Phase 1完了

#### タスク
1. ✅ 共有シークレットの生成
2. ✅ Worker側でシークレットヘッダー追加
3. ✅ FastAPIミドルウェアで検証ロジック実装
4. ✅ 直接アクセスのブロック確認

### Phase 4: 最適化と監視

**作業時間**: 30分
**担当**: インフラ・バックエンド担当
**依存関係**: Phase 1-3完了

#### タスク
1. ✅ WebSocketタイムアウト設定
2. ✅ 静的アセットキャッシュ設定
3. ✅ Workerログ監視設定（`wrangler tail`）
4. ✅ パフォーマンステスト

---

## 🔧 Phase 1: 詳細実装手順

### 1.1 プロジェクト構造の作成

```bash
mkdir -p workers
cd workers
```

### 1.2 Worker スクリプトの作成

**ファイル**: `workers/worker.js`

```javascript
/**
 * Cloudflare Worker for Cloud Run Proxy
 * Target: sagebase-streamlit-469990531240.asia-northeast1.run.app
 *
 * このWorkerは、着信リクエストのHostヘッダーをCloud Runが期待する形式に書き換え、
 * オリジンからのレスポンスをクライアントに返送します。
 */

// 定数定義：転送先のCloud Runホスト名
const UPSTREAM_ORIGIN = 'sagebase-streamlit-469990531240.asia-northeast1.run.app';

export default {
  async fetch(request, env, ctx) {
    // 1. リクエストURLの解析
    const url = new URL(request.url);

    // 2. ホスト名の書き換え
    // パス(/foo)やクエリパラメータ(?bar=baz)は維持したまま、接続先ホスト名のみを変更
    url.hostname = UPSTREAM_ORIGIN;

    // 3. 新しいリクエストオブジェクトの作成
    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });

    // 4. 重要：Hostヘッダーのオーバーライド
    // これによりCloud RunのGFEは、このリクエストが正規のrun.app宛てであると認識
    newRequest.headers.set('Host', UPSTREAM_ORIGIN);

    // 5. セキュリティとトレーサビリティのためのヘッダー付与
    // バックエンドアプリが「ユーザーが実際にアクセスしたドメイン」を知るために必要
    newRequest.headers.set('X-Forwarded-Host', 'app.sage-base.com');

    // オリジン間認証のためのシークレットトークン（Phase 3で実装）
    // newRequest.headers.set('X-CF-Secret', env.CF_SECRET);

    // 6. オリジンへのフェッチ実行
    try {
      const response = await fetch(newRequest);

      // 7. レスポンスヘッダーの処理
      const newResponseHeaders = new Headers(response.headers);
      newResponseHeaders.set('X-Worker-Proxy', 'Active');

      // デバッグ用情報の削除（セキュリティ向上）
      newResponseHeaders.delete('X-Cloud-Trace-Context');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newResponseHeaders
      });

    } catch (e) {
      // 8. エラーハンドリング
      return new Response(`Edge Proxy Error: ${e.message}`, { status: 502 });
    }
  }
};
```

### 1.3 Wrangler設定ファイルの作成

**ファイル**: `workers/wrangler.toml`

```toml
name = "sagebase-proxy"
main = "worker.js"
compatibility_date = "2025-01-01"

# ルーティング設定
# app.sage-base.comへのすべてのリクエストがWorkerによって処理されます
[[routes]]
pattern = "app.sage-base.com/*"
zone_name = "sage-base.com"

# 環境変数の設定
[vars]
ENVIRONMENT = "production"
```

### 1.4 Cloudflare API Tokenの取得

1. [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens) にアクセス
2. **Create Token** をクリック
3. **Edit Cloudflare Workers** テンプレートを選択
4. 権限を確認：
   - Account: `Workers Scripts:Edit`
   - Zone: `Zone:Read`
5. **Continue to summary** → **Create Token**
6. トークンをコピー（**一度しか表示されません**）

### 1.5 手動デプロイ（テスト）

```bash
# wranglerのインストール（初回のみ）
npm install -g wrangler

# ログイン
wrangler login

# デプロイ
cd workers
wrangler deploy
```

### 1.6 動作確認

```bash
# カスタムドメインにアクセス
curl -I https://app.sage-base.com/

# 期待される結果：HTTP/2 200
```

---

## 🚀 Phase 2: GitHub Actions統合

### 2.1 GitHub Actionsワークフローの作成

**ファイル**: `.github/workflows/deploy-worker.yml`

```yaml
name: Deploy Cloudflare Worker

on:
  push:
    branches:
      - main
    paths:
      - 'workers/**'
      - '.github/workflows/deploy-worker.yml'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: Deploy Worker to Cloudflare
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          workingDirectory: 'workers'
          command: deploy

      - name: Verify deployment
        run: |
          echo "Waiting for deployment to propagate..."
          sleep 10

          # ヘルスチェック
          STATUS=$(curl -o /dev/null -s -w "%{http_code}" https://app.sage-base.com/)

          if [ "$STATUS" -eq 200 ]; then
            echo "✅ Deployment successful! Status: $STATUS"
          else
            echo "❌ Deployment verification failed. Status: $STATUS"
            exit 1
          fi

      - name: Deployment summary
        if: always()
        run: |
          echo "## 🚀 Worker Deployment Summary" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- **Worker**: sagebase-proxy" >> $GITHUB_STEP_SUMMARY
          echo "- **Route**: app.sage-base.com/*" >> $GITHUB_STEP_SUMMARY
          echo "- **Target**: sagebase-streamlit-469990531240.asia-northeast1.run.app" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "🔗 [Test URL](https://app.sage-base.com/)" >> $GITHUB_STEP_SUMMARY
```

### 2.2 GitHub Secretsの設定

1. **GitHub Repository → Settings → Secrets and variables → Actions**
2. 以下のシークレットを追加：

| シークレット名 | 値 | 取得方法 |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | 先ほど取得したAPIトークン | Phase 1.4 |
| `CLOUDFLARE_ACCOUNT_ID` | CloudflareアカウントID | Dashboard → ドメイン選択 → 右サイドバー |

### 2.3 ワークフローのテスト

```bash
# 変更をコミット＆プッシュ
git add workers/ .github/workflows/deploy-worker.yml
git commit -m "feat: Add Cloudflare Worker for custom domain"
git push

# GitHub Actionsでワークフローが実行されることを確認
```

---

## 🔒 Phase 3: セキュリティ強化

### 3.1 共有シークレットの生成

```bash
# 強力なランダムトークンを生成
openssl rand -base64 32
```

出力例: `8xK9mPqR3vL2nWcT5yH7jF1dS4gA6bN0`

### 3.2 Worker側でシークレットヘッダー追加

**更新**: `workers/worker.js`

```javascript
// 行86付近（オリジン間認証のためのシークレットトークン）
newRequest.headers.set('X-CF-Secret', env.CF_SECRET);
```

**更新**: `workers/wrangler.toml`

```toml
# シークレット変数の設定（平文では記載しない）
# デプロイ時にGitHub Actionsから注入される
```

**更新**: `.github/workflows/deploy-worker.yml`

```yaml
- name: Deploy to Cloudflare Workers
  uses: cloudflare/wrangler-action@v3
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    workingDirectory: 'workers'
    command: deploy
    secrets: |
      CF_SECRET
  env:
    CF_SECRET: ${{ secrets.CLOUDFLARE_WORKER_SECRET }}
```

### 3.3 FastAPIミドルウェアの実装

**新規作成**: `src/interfaces/web/streamlit/middleware/cloudflare_auth.py`

```python
"""Cloudflare Worker認証ミドルウェア."""

import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class CloudflareSecurityMiddleware(BaseHTTPMiddleware):
    """Cloudflare Worker経由のリクエストのみを許可するミドルウェア."""

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """リクエストを処理する."""
        # ヘルスチェックエンドポイントは認証をスキップ
        if request.url.path == "/_stcore/health":
            return await call_next(request)

        # ローカル開発環境では認証をスキップ
        if os.getenv("ENVIRONMENT") == "development":
            return await call_next(request)

        # 本番環境での検証
        expected_token = os.getenv("CLOUDFLARE_WORKER_SECRET")
        incoming_token = request.headers.get("X-CF-Secret")

        # トークンが設定されていて、かつ不一致の場合、403を返す
        if expected_token and incoming_token != expected_token:
            # ログに記録（攻撃の予兆として監視）
            print(
                f"⚠️ Unauthorized access attempt from {request.client.host}"
            )
            return Response(
                "Direct access is strictly forbidden. "
                "Please access via app.sage-base.com",
                status_code=403,
            )

        # 正常なリクエストを処理
        response = await call_next(request)
        return response
```

**更新**: `src/interfaces/web/streamlit/app.py`

```python
from src.interfaces.web.streamlit.middleware.cloudflare_auth import (
    CloudflareSecurityMiddleware,
)

# ミドルウェアの追加（既存のセキュリティヘッダーの後）
app.add_middleware(CloudflareSecurityMiddleware)
```

### 3.4 環境変数の設定

**GitHub Secrets追加**:
- `CLOUDFLARE_WORKER_SECRET`: 生成したシークレット

**Cloud Run環境変数更新** (`.github/workflows/deploy-to-cloud-run.yml`):

```yaml
# 行137付近
"--set-env-vars=CLOUD_RUN=true,LOG_LEVEL=INFO,ENVIRONMENT=production"
```

**Secret Manager追加**:

```bash
# シークレットを作成
echo -n "8xK9mPqR3vL2nWcT5yH7jF1dS4gA6bN0" | \
  gcloud secrets create cloudflare-worker-secret \
    --data-file=- \
    --project=YOUR_PROJECT_ID

# Cloud Runデプロイ設定に追加
# .github/workflows/deploy-to-cloud-run.yml 行144付近
if gcloud secrets describe cloudflare-worker-secret --project=${{ env.PROJECT_ID }} > /dev/null 2>&1; then
  DEPLOY_ARGS+=("--set-secrets=CLOUDFLARE_WORKER_SECRET=cloudflare-worker-secret:latest")
fi
```

---

## 📊 Phase 4: 最適化と監視

### 4.1 静的アセットキャッシュ最適化

**更新**: `workers/worker.js`

```javascript
// 7. レスポンスヘッダーの処理（キャッシュ最適化）
const newResponseHeaders = new Headers(response.headers);
newResponseHeaders.set('X-Worker-Proxy', 'Active');

// 静的アセットのキャッシュ設定
if (url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2)$/)) {
  // Cloudflareエッジで1日キャッシュ
  newResponseHeaders.set('Cache-Control', 'public, max-age=86400');
}

// デバッグ用情報の削除（セキュリティ向上）
newResponseHeaders.delete('X-Cloud-Trace-Context');
```

### 4.2 Workerログ監視

```bash
# リアルタイムログ監視
wrangler tail sagebase-proxy

# 特定のステータスコードのみフィルタ
wrangler tail sagebase-proxy --status error
```

### 4.3 パフォーマンステスト

```bash
# レスポンスタイムのテスト
curl -w "@curl-format.txt" -o /dev/null -s https://app.sage-base.com/

# curl-format.txt の内容
# time_namelookup:  %{time_namelookup}\n
# time_connect:     %{time_connect}\n
# time_starttransfer: %{time_starttransfer}\n
# time_total:       %{time_total}\n
```

---

## ✅ 完了チェックリスト

### Phase 1: Worker作成
- [ ] `workers/worker.js` 作成
- [ ] `workers/wrangler.toml` 作成
- [ ] Cloudflare API Token取得
- [ ] 手動デプロイ成功
- [ ] `https://app.sage-base.com/` で200 OK確認

### Phase 2: CI/CD統合
- [ ] `.github/workflows/deploy-worker.yml` 作成
- [ ] GitHub Secrets設定（API Token, Account ID）
- [ ] GitHub Actionsでデプロイ成功

### Phase 3: セキュリティ
- [ ] 共有シークレット生成
- [ ] Worker側でヘッダー追加
- [ ] FastAPIミドルウェア実装
- [ ] Cloud Run環境変数設定
- [ ] 直接アクセス（`*.run.app`）で403確認

### Phase 4: 最適化
- [ ] 静的アセットキャッシュ設定
- [ ] Workerログ監視設定
- [ ] パフォーマンステスト完了
- [ ] ドキュメント更新

---

## 🎯 次のステップ

1. **Phase 1を実装**: Workerスクリプトを作成し、手動デプロイ
2. **動作確認**: `https://app.sage-base.com/` で200 OKを確認
3. **Phase 2-4を順次実装**: CI/CD、セキュリティ、最適化
4. **本番デプロイ**: mainブランチにマージ

---

## 📚 参考資料

- Deep Research調査結果: `docs/researchment_cloudflare_cloudrun_domain.md`
- Cloudflare Workers公式ドキュメント: https://developers.cloudflare.com/workers/
- Wrangler CLI: https://developers.cloudflare.com/workers/wrangler/
- Cloud Run公式ドキュメント: https://cloud.google.com/run/docs

---

**推定作業時間**: 合計 2時間
**推定コスト**: $0/月（無料プラン、10万リクエスト/日まで）
**メンテナンス**: 低（一度設定すれば変更不要）
