# WebSocket トラブルシューティングガイド

このドキュメントは、StreamlitアプリケーションにおけるWebSocket接続の問題を診断・解決するためのガイドです。

## 📋 目次

- [概要](#概要)
- [Cloudflare設定の確認](#cloudflare設定の確認)
- [トラブルシューティング手順](#トラブルシューティング手順)
- [一般的な問題と解決策](#一般的な問題と解決策)
- [ログの確認方法](#ログの確認方法)

## 概要

Streamlitアプリケーションは、リアルタイムなUI更新のためにWebSocket接続を使用します。Cloudflare WorkersとCloud Runを経由する構成では、以下の要素が正しく設定されている必要があります：

```
ブラウザ (wss://)
  ↓
Cloudflare Edge + Worker
  ↓
Cloud Run (Streamlit)
```

## Cloudflare設定の確認

### 1. WebSocketサポートの確認

Cloudflare Workersは、デフォルトでWebSocketをサポートしていますが、ダッシュボードで設定を確認することが重要です。

#### 手順

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) にログイン
2. ドメイン `sage-base.com` を選択
3. **Network** セクションに移動
4. **WebSockets** が有効になっていることを確認

#### 期待される設定

- **WebSockets**: `On` (デフォルトで有効)
- **Proxy status**: `Proxied` (オレンジ色のクラウド)

### 2. DNS設定の確認

1. **DNS** セクションに移動
2. `app.sage-base.com` のレコードを確認

#### 期待される設定

| Type | Name | Content | Proxy status |
|------|------|---------|--------------|
| CNAME | app | sagebase-streamlit-469990531240.asia-northeast1.run.app | Proxied |

**重要**: Proxy statusは必ず「Proxied」（オレンジ色のクラウド）である必要があります。

### 3. Worker設定の確認

1. **Workers & Pages** セクションに移動
2. `sagebase-proxy` Workerを選択
3. **Settings** → **Triggers** で以下を確認

#### 期待される設定

- **Route**: `app.sage-base.com/*`
- **Zone**: `sage-base.com`

## トラブルシューティング手順

### ステップ1: ブラウザコンソールの確認

1. ブラウザで `https://app.sage-base.com/` を開く
2. 開発者ツールを開く（F12キー）
3. **Console** タブを確認

#### 正常な場合

```
WebSocket connection to 'wss://app.sage-base.com/_stcore/stream' established
```

#### エラーの場合

```
WebSocket connection to 'wss://app.sage-base.com/_stcore/stream' failed: Error during WebSocket handshake
```

または

```
WebSocket onerror
```

### ステップ2: ネットワークタブの確認

1. 開発者ツールの **Network** タブを開く
2. **WS**（WebSocket）フィルターを選択
3. `_stcore/stream` の接続を確認

#### 確認ポイント

- **Status**: `101 Switching Protocols` であること
- **Upgrade**: `websocket` ヘッダーが存在すること
- **Connection**: `Upgrade` ヘッダーが存在すること

### ステップ3: Workerログの確認

ローカル環境でWorkerログを確認：

```bash
# Wranglerがインストールされている場合
wrangler tail sagebase-proxy

# エラーのみを表示
wrangler tail sagebase-proxy --status error
```

#### 確認ポイント

- `Edge Proxy Error` がログに表示されていないか
- `isWebSocket: true` のリクエストでエラーが発生していないか

### ステップ4: Cloud Runログの確認

Google Cloud Consoleでログを確認：

1. [Cloud Console](https://console.cloud.google.com/) にログイン
2. **Cloud Run** → `sagebase-streamlit` を選択
3. **Logs** タブを確認

#### 確認ポイント

- WebSocket接続のエラーログがないか
- タイムアウトエラーが発生していないか

## 一般的な問題と解決策

### 問題1: WebSocket接続が即座に切断される

#### 症状

```
WebSocket connection closed immediately after opening
```

#### 原因

- Cloudflare WorkerがWebSocketのUpgradeヘッダーを正しく転送していない
- `X-Forwarded-Proto` ヘッダーが設定されていない

#### 解決策

`workers/worker.js` に以下のヘッダーが設定されていることを確認：

```javascript
newRequest.headers.set('X-Forwarded-Proto', 'https');
newRequest.headers.set('X-Forwarded-Host', 'app.sage-base.com');
```

### 問題2: 403 Forbiddenエラー

#### 症状

```
WebSocket connection failed: Received HTTP 403
```

#### 原因

- Cloud Runのミドルウェアで認証エラーが発生している
- `X-CF-Secret` ヘッダーが不正または欠落している

#### 解決策

1. GitHub Secretsで `CLOUDFLARE_WORKER_SECRET` が設定されていることを確認
2. Cloud Runの環境変数で `CLOUDFLARE_WORKER_SECRET` が設定されていることを確認
3. Workerとバックエンドで同じシークレットが使用されていることを確認

### 問題3: タイムアウトエラー

#### 症状

```
WebSocket connection timeout
```

#### 原因

- Cloudflareのタイムアウト（デフォルト100秒）
- Cloud Runのタイムアウト設定

#### 解決策

Cloudflare Workersは最大100秒のWebSocket接続をサポートします。これ以上の長時間接続が必要な場合：

1. Streamlitの再接続ロジックが動作していることを確認
2. Keep-alive pingを送信するようにStreamlitを設定

### 問題4: ローカル開発環境での動作確認

#### ローカルでのWorkerテスト

```bash
cd workers
wrangler dev
```

ブラウザで `http://localhost:8787/` にアクセスして動作を確認します。

**注意**: ローカル環境では `CF-Connecting-IP` ヘッダーは利用できないため、一部の機能が動作しない場合があります。

## ログの確認方法

### Cloudflare Workerログ

```bash
# リアルタイムログの確認
wrangler tail sagebase-proxy

# 特定のステータスコードのみフィルタ
wrangler tail sagebase-proxy --status error

# 特定の時間範囲のログを取得
wrangler tail sagebase-proxy --since 1h
```

### Cloud Runログ

```bash
# gcloud CLIを使用したログの確認
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sagebase-streamlit" \
  --limit 50 \
  --format json

# WebSocket関連のログのみを抽出
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=sagebase-streamlit AND textPayload=~\"websocket\"" \
  --limit 50 \
  --format json
```

### ブラウザ開発者ツール

1. Chrome/Firefox/Safariで開発者ツールを開く（F12キー）
2. **Network** タブ → **WS** フィルターを選択
3. WebSocket接続を選択して詳細を確認：
   - **Headers**: リクエスト/レスポンスヘッダー
   - **Messages**: 送受信されたメッセージ
   - **Frames**: WebSocketフレームの詳細

## デバッグのベストプラクティス

### 1. 段階的な確認

1. **HTTPリクエストが正常に動作するか確認**
   ```bash
   curl -I https://app.sage-base.com/
   ```
   期待される結果: `HTTP/2 200`

2. **WebSocket Upgradeリクエストが正常に処理されるか確認**
   ```bash
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" https://app.sage-base.com/_stcore/stream
   ```
   期待される結果: `HTTP/1.1 101 Switching Protocols`

3. **ブラウザで実際のStreamlitアプリを確認**

### 2. ヘッダーの確認

ブラウザの開発者ツールでWebSocket接続のヘッダーを確認：

#### 必須ヘッダー（リクエスト）

- `Upgrade: websocket`
- `Connection: Upgrade`
- `Sec-WebSocket-Version: 13`
- `Sec-WebSocket-Key: <ランダムな値>`

#### 必須ヘッダー（レスポンス）

- `HTTP/1.1 101 Switching Protocols`
- `Upgrade: websocket`
- `Connection: Upgrade`
- `Sec-WebSocket-Accept: <計算された値>`

### 3. エラーパターンの理解

| エラーメッセージ | 原因 | 解決策 |
|----------------|------|--------|
| `WebSocket onerror` | 接続失敗 | Workerのヘッダー設定を確認 |
| `403 Forbidden` | 認証エラー | シークレットトークンを確認 |
| `502 Bad Gateway` | Workerエラー | Workerのログを確認 |
| `Connection timeout` | タイムアウト | Cloud RunとCloudflareの設定を確認 |

## 関連ドキュメント

- [Cloudflare Workers実装計画](./CLOUDFLARE_WORKERS_IMPLEMENTATION_PLAN.md)
- [Cloudflare + Cloud Runドメイン設定調査](./researchment_cloudflare_cloudrun_domain.md)
- [Streamlit公式ドキュメント: WebSocket Configuration](https://docs.streamlit.io/library/advanced-features/configuration#server)
- [Cloudflare Workers: WebSocket Support](https://developers.cloudflare.com/workers/examples/websockets/)

## サポート

問題が解決しない場合：

1. [GitHub Issues](https://github.com/trust-chain-organization/sagebase/issues) で新しいIssueを作成
2. 以下の情報を含める：
   - ブラウザのコンソールログ
   - ネットワークタブのスクリーンショット
   - Cloud RunとWorkerのログ
   - 使用しているブラウザとバージョン
