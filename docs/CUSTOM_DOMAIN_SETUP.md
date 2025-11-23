# カスタムドメイン設定ガイド（Cloud Run + Cloudflare構成）

このドキュメントでは、Sagebase (app.sage-base.com) のカスタムドメイン設定手順を説明します。

**インフラ構成**: Google Cloud Run + Cloudflare（CDN & セキュリティ）

## 📋 前提条件

- [x] Cloudflareでapp.sage-base.comドメインを購入済み
- [ ] Cloud RunにSagebaseアプリがデプロイ済み
- [ ] Google Cloud Projectへのアクセス権限
- [ ] Google Analytics 4 プロパティを作成済み（アナリティクス使用時）
- [ ] Cloudflare Workersへのアクセス権限

---

## 🎯 アーキテクチャ概要

```
ユーザー
  ↓
Cloudflare DNS (app.sage-base.com)
  ↓
Cloudflare CDN + Workers（セキュリティヘッダー、キャッシング）
  ↓
Google Cloud Run (sagebase-streamlit)
  ↓
Cloud SQL (PostgreSQL)
```

**メリット**:
- ✅ Cloudflare CDNで高速配信
- ✅ DDoS保護とセキュリティ機能
- ✅ Cloudflare WorkersでセキュリティヘッダーとHTTPSリダイレクト
- ✅ 無料のSSL/TLS証明書（Cloudflare管理）
- ✅ アクセスログとアナリティクス

---

## ☁️ ステップ1: Cloud Runサービスの確認

### 1.1 現在のCloud Runサービスを確認

```bash
# プロジェクトIDを設定
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"

# Cloud Runサービスの確認
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID

# サービスURLを取得
export CLOUD_RUN_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format='value(status.url)')

echo "Cloud Run URL: $CLOUD_RUN_URL"
# 例: https://sagebase-streamlit-xxxxx-an.a.run.app
```

### 1.2 アプリケーションが正常に動作しているか確認

```bash
# ヘルスチェック
curl -I $CLOUD_RUN_URL

# 期待される結果: HTTP/2 200
```

---

## 🌐 ステップ2: Cloudflare DNS設定

### 2.1 Cloudflareダッシュボードにアクセス

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)にログイン
2. **app.sage-base.com** ドメインを選択
3. 左サイドバーから **DNS** > **Records** を選択

### 2.2 DNSレコードの追加

Cloud RunのURLをCloudflareでプロキシします。

#### CNAMEレコードの追加

```
Type: CNAME
Name: app
Target: sagebase-streamlit-xxxxx-an.a.run.app
  （Cloud RunのURLからhttps://を除いた部分）
TTL: Auto
Proxy status: Proxied (オレンジ色のクラウドアイコンをON)
```

**注意**: sage-base.comはコーポレートサイト用に使用されているため、サブドメイン `app` を使用します。

**重要**: Proxy statusは必ず **Proxied（オレンジ色）** にしてください。これにより、Cloudflare経由でアクセスされます。

---

## 🔒 ステップ3: Cloudflare SSL/TLS設定

### 3.1 SSL/TLS暗号化モードの設定

1. Cloudflareダッシュボード > **SSL/TLS** を選択
2. **Encryption mode** を **Full (strict)** に設定

**設定値の説明**:
- ❌ **Off**: 暗号化なし（非推奨）
- ❌ **Flexible**: Cloudflareとユーザー間のみ暗号化（Cloud Runとの通信は平文）
- ⚠️ **Full**: 暗号化するが証明書検証なし
- ✅ **Full (strict)**: 完全な暗号化（推奨）

Cloud Runは自動的にSSL証明書を提供するため、**Full (strict)** が最適です。

### 3.2 HTTPS常時接続の設定

1. **SSL/TLS** > **Edge Certificates** を選択
2. **Always Use HTTPS** を **On** に設定
3. **Automatic HTTPS Rewrites** を **On** に設定
4. **Minimum TLS Version** を **TLS 1.2** 以上に設定

---

## 🛡️ ステップ4: Cloudflare Workers設定（セキュリティヘッダー）

### 4.1 Cloudflare Workerの作成

1. Cloudflareダッシュボード > **Workers & Pages** を選択
2. **Create Worker** をクリック
3. Worker名を入力（例: `sagebase-security-headers`）
4. **Deploy** をクリック

### 4.2 Workerスクリプトの設定

Workerの編集画面で、以下のコードを貼り付け：

```javascript
// Cloudflare Worker for adding security headers and HTTPS redirect
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // HTTPS redirect
  const url = new URL(request.url)
  if (url.protocol === 'http:') {
    url.protocol = 'https:'
    return Response.redirect(url.toString(), 301)
  }

  // Fetch the original response from Cloud Run
  const response = await fetch(request)

  // Create a new response with security headers
  const newResponse = new Response(response.body, response)

  // Copy all original headers
  response.headers.forEach((value, key) => {
    newResponse.headers.set(key, value)
  })

  // Security Headers
  newResponse.headers.set('X-Frame-Options', 'DENY')
  newResponse.headers.set('X-Content-Type-Options', 'nosniff')
  newResponse.headers.set(
    'Referrer-Policy',
    'strict-origin-when-cross-origin'
  )
  newResponse.headers.set(
    'Permissions-Policy',
    'geolocation=(), microphone=(), camera=()'
  )
  newResponse.headers.set('X-XSS-Protection', '1; mode=block')
  newResponse.headers.set(
    'Strict-Transport-Security',
    'max-age=31536000; includeSubDomains; preload'
  )

  // Content Security Policy
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' " +
      "https://www.googletagmanager.com https://www.google-analytics.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    "img-src 'self' data: https: blob:",
    "connect-src 'self' https://www.google-analytics.com " +
      "https://www.googletagmanager.com " +
      "wss://*.run.app wss://app.sage-base.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests"
  ].join('; ')

  newResponse.headers.set('Content-Security-Policy', csp)

  return newResponse
}
```

### 4.3 Workerのデプロイとルート設定

1. **Save and Deploy** をクリック
2. Workerのダッシュボードに戻る
3. 作成したWorkerを選択
4. **Triggers** タブを開く
5. **Add route** をクリック
6. 以下を設定：
   - Route: `app.sage-base.com/*`
   - Zone: `app.sage-base.com`
7. **Add route** をクリック

**確認**: `https://app.sage-base.com/*` へのすべてのリクエストがこのWorkerを経由するようになります。

---

## 🔧 ステップ5: Cloud Run環境変数の更新

### 5.1 本番環境用の環境変数を設定

Google Cloud ConsoleまたはgcloudコマンドでCloud Runの環境変数を更新：

```bash
# Google Analytics IDを設定（取得後）
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --update-env-vars="GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX"

# OAuth リダイレクトURIを本番ドメインに変更
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --update-env-vars="GOOGLE_OAUTH_REDIRECT_URI=https://app.sage-base.com/"

# 本番環境フラグ
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --update-env-vars="ENVIRONMENT=production"
```

### 5.2 環境変数の確認

```bash
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format='yaml(spec.template.spec.containers[0].env)'
```

---

## 📊 ステップ6: Google Analytics設定

### 6.1 GA4プロパティの作成

1. [Google Analytics](https://analytics.google.com/)にアクセス
2. **Admin** > **Create Property** を選択
3. プロパティ名: `Sagebase`
4. タイムゾーン: `Japan`
5. 通貨: `Japanese Yen (¥)`

### 6.2 データストリームの設定

1. **Data Streams** > **Add stream** > **Web** を選択
2. Website URL: `https://app.sage-base.com`
3. Stream name: `Sagebase Production`
4. **Create stream** をクリック

### 6.3 測定IDのコピーと設定

1. データストリームの詳細画面で **Measurement ID** をコピー
2. 形式: `G-XXXXXXXXXX`
3. Cloud Runの環境変数に設定（ステップ5.1参照）

または、Secret Managerを使用（推奨）：

```bash
# Secret Managerに保存
echo -n "G-XXXXXXXXXX" | gcloud secrets create google-analytics-id \
  --data-file=- \
  --replication-policy=automatic \
  --project=$PROJECT_ID

# Cloud Runからシークレットを参照
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --set-secrets="GOOGLE_ANALYTICS_ID=google-analytics-id:latest"
```

---

## 🔍 ステップ7: SEO設定

### 7.1 robots.txtとsitemap.xmlの確認

これらのファイルはすでにプロジェクトルートに作成済みです：
- `robots.txt`
- `sitemap.xml`

Cloud Runにデプロイされると、自動的に以下のURLでアクセス可能になります：
- https://app.sage-base.com/robots.txt
- https://app.sage-base.com/sitemap.xml

### 7.2 Google Search Consoleへの登録

1. [Google Search Console](https://search.google.com/search-console)にアクセス
2. **Add property** をクリック
3. プロパティタイプ: **Domain**
4. ドメイン名: `app.sage-base.com` を入力
5. DNS認証用のTXTレコードをCloudflare DNSに追加：

```
Type: TXT
Name: app
Content: google-site-verification=xxxxxxxxxxxxxxxxxxxxx
TTL: Auto
Proxy status: DNS only (グレー色)
```

6. **Verify** をクリック

### 7.3 サイトマップの送信

1. Google Search Consoleの **Sitemaps** セクションに移動
2. サイトマップURL: `https://app.sage-base.com/sitemap.xml` を入力
3. **Submit** をクリック

---

## ✅ ステップ8: 動作確認

### 8.1 DNS伝播の確認

```bash
# nslookupでDNS設定を確認
nslookup app.sage-base.com

# digコマンドで詳細確認
dig app.sage-base.com

# Cloudflareを経由しているか確認
dig app.sage-base.com +short
# CloudflareのIPアドレス（104.xx.xx.xx など）が返ってくるはず
```

### 8.2 SSL証明書の確認

ブラウザでhttps://app.sage-base.comにアクセスし、アドレスバーの鍵アイコンをクリック：
- 証明書が有効か確認
- 発行者: Cloudflare（またはGoogle Trust Services）

コマンドラインでも確認可能：

```bash
# SSL証明書の確認
openssl s_client -connect app.sage-base.com:443 -servername app.sage-base.com < /dev/null 2>/dev/null | \
  openssl x509 -noout -text | grep -A2 "Issuer"
```

### 8.3 セキュリティヘッダーの確認

開発者ツールを開いて確認：
1. ブラウザで https://app.sage-base.com を開く
2. 開発者ツール（F12）> **Network** タブ
3. ページをリロード
4. レスポンスヘッダーに以下が含まれているか確認：
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Content-Security-Policy: ...`
   - `Strict-Transport-Security: ...`

オンラインツールでも確認可能：
- [Security Headers](https://securityheaders.com/?q=app.sage-base.com)
- 期待されるグレード: **A** または **A+**

### 8.4 HTTPSリダイレクトの確認

```bash
# HTTPアクセスがHTTPSにリダイレクトされるか確認
curl -I http://app.sage-base.com

# 期待される結果:
# HTTP/1.1 301 Moved Permanently
# Location: https://app.sage-base.com/
```

### 8.5 Google Analyticsの確認

1. Google Analytics > **Realtime** レポートを開く
2. https://app.sage-base.com にアクセス
3. リアルタイムレポートにアクセスが表示されることを確認

### 8.6 全ページの動作確認

以下のページが正しく動作するか確認：
- [ ] https://app.sage-base.com/ (ホーム)
- [ ] https://app.sage-base.com/meetings (会議管理)
- [ ] https://app.sage-base.com/political_parties (政党管理)
- [ ] https://app.sage-base.com/politicians (政治家管理)
- [ ] https://app.sage-base.com/conversations (発言レコード)
- [ ] https://app.sage-base.com/processes (処理実行)
- [ ] https://app.sage-base.com/llm_history (LLM履歴)
- [ ] https://app.sage-base.com/work_history (作業履歴)

---

## 🐛 トラブルシューティング

### DNS設定が反映されない

**原因**: DNS伝播に時間がかかっている

**解決策**:
- 最大48時間待つ（通常は数分〜数時間で完了）
- Cloudflare DNSのTTLを確認
- `dig app.sage-base.com` で現在の設定を確認
- Cloudflareダッシュボードで **Purge Cache** を実行

### SSL証明書エラー

**原因**: CloudflareのSSL/TLS設定が正しくない

**解決策**:
- SSL/TLS暗号化モードを **Full (strict)** に設定
- Cloud RunがHTTPSで応答しているか確認
- Cloudflareの **Universal SSL** が有効か確認

### Cloudflare Workerが動作しない

**原因**: ルート設定が正しくない

**解決策**:
- Workers & Pages > Triggers でルート設定を確認
- `app.sage-base.com/*` が正しく設定されているか確認
- Cloudflare ProxyがON（オレンジ色）になっているか確認
- Workerのログを確認（Workers & Pages > 該当Worker > Logs）

### Google Analyticsでデータが取得できない

**原因**: 測定IDが正しく設定されていない

**解決策**:
- Cloud Runの環境変数で `GOOGLE_ANALYTICS_ID` を確認
- ブラウザの開発者ツールでgtagスクリプトが読み込まれているか確認
- アドブロッカーを無効にしてテスト
- Google Analyticsのデバッグモードで確認

### Cloud Runへのアクセスが遅い

**原因**: Cloud Runのコールドスタート

**解決策**:
- Minimum instancesを1以上に設定（コスト増加に注意）

```bash
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --min-instances=1
```

- Cloudflareのキャッシング設定を最適化
- Cloud RunのCPU/メモリを増強

---

## 🚀 オプション設定

### Cloudflare CDNキャッシング

静的コンテンツをキャッシュしてパフォーマンスを向上：

1. Cloudflareダッシュボード > **Rules** > **Page Rules**
2. **Create Page Rule** をクリック
3. URL: `app.sage-base.com/static/*`
4. Settings:
   - **Cache Level**: Cache Everything
   - **Edge Cache TTL**: 1 month
5. **Save and Deploy**

### Cloudflare Firewall Rules

特定の国やIPアドレスからのアクセスを制限：

1. Cloudflareダッシュボード > **Security** > **WAF**
2. **Create firewall rule** をクリック
3. 例: 日本以外からのアクセスをブロック
   - Field: **Country**
   - Operator: **is not**
   - Value: **Japan**
   - Action: **Block**

### Cloudflare Rate Limiting

DDoS攻撃やボット対策：

1. Cloudflareダッシュボード > **Security** > **WAF**
2. **Rate limiting rules** タブを選択
3. **Create rule** をクリック
4. 例: 10秒間に10リクエスト以上で制限
   - Match: `app.sage-base.com/*`
   - Requests: 10 requests
   - Period: 10 seconds
   - Action: Block

---

## 📚 参考リンク

- [Cloudflare DNS Documentation](https://developers.cloudflare.com/dns/)
- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Cloudflare SSL/TLS Documentation](https://developers.cloudflare.com/ssl/)
- [Google Cloud Run Custom Domains](https://cloud.google.com/run/docs/mapping-custom-domains)
- [Google Analytics 4 Documentation](https://support.google.com/analytics/answer/10089681)
- [Google Search Console Help](https://support.google.com/webmasters/)

---

## ✨ 完了後の確認項目

- [ ] https://app.sage-base.com でアプリにアクセスできる
- [ ] SSL証明書が有効（鍵アイコンが表示される）
- [ ] HTTPからHTTPSへ自動リダイレクトされる
- [ ] セキュリティヘッダーが正しく設定されている（A+グレード）
- [ ] Google Analyticsでトラッキングが動作している
- [ ] robots.txt と sitemap.xml にアクセスできる
- [ ] Google Search Consoleでサイトが認証されている
- [ ] 全ページが正常に動作する
- [ ] OAuth認証が本番ドメインで動作する
- [ ] Cloudflare Workersが正しく動作している
- [ ] DNS設定が完全に伝播している

すべてのチェック項目が完了したら、Issue #726を完了としてクローズできます！ 🎉
