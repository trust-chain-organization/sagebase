# Cloudflare + Cloud Run カスタムドメイン設定の調査依頼

## 📋 現在の状況

### インフラ構成

```
ユーザー → Cloudflare DNS (app.sage-base.com) → Cloudflare Proxy → Cloud Run → Cloud SQL
```

- **メインドメイン**: `sage-base.com`（Cloudflare Pages上の企業サイト）
- **サブドメイン**: `app.sage-base.com`（Streamlitアプリケーション - Cloud Run）
- **Cloud Runサービス**: `sagebase-streamlit-469990531240.asia-northeast1.run.app`
- **リージョン**: `asia-northeast1`
- **Cloudflareプロキシ**: 有効（オレンジ色の雲アイコンON）

### Cloudflare DNS設定（完了済み）

- **Type**: CNAME
- **Name**: `app`
- **Target**: `sagebase-streamlit-469990531240.asia-northeast1.run.app`
- **Proxy status**: Proxied（オレンジ色）
- **SSL/TLS**: Full (strict)

## ❌ 発生している問題

### 問題1: 404エラー

```bash
curl -I https://app.sage-base.com/
# 結果: HTTP/2 404
```

一方、Cloud Run URLに直接アクセスすると成功：

```bash
curl -I https://sagebase-streamlit-469990531240.asia-northeast1.run.app/
# 結果: HTTP/2 200
```

### 問題2: Hostヘッダーの不一致

Cloud Run URLに直接アクセスし、Hostヘッダーを `app.sage-base.com` に設定すると404エラー：

```bash
curl -I https://sagebase-streamlit-469990531240.asia-northeast1.run.app/ -H "Host: app.sage-base.com"
# 結果: HTTP/2 404
```

**原因**: Cloud Runが `app.sage-base.com` というHostヘッダーを認識していない。

## 🔍 試したこと

### 試行1: Cloud Runのドメインマッピング機能

```bash
gcloud beta run domain-mappings create \
  --service=sagebase-streamlit \
  --domain=app.sage-base.com \
  --region=asia-northeast1
```

**結果**: エラー

```
ERROR: (gcloud.beta.run.domain-mappings.create) The provided domain does not appear to be verified for the current account so a domain mapping cannot be created.
You currently have no verified domains.
```

**問題点**:
- Google Cloud側でドメインの所有権検証が必要
- Cloudflareプロキシを使用しているため、DNS検証が複雑
- Cloud Runのドメインマッピングは、Cloud Runが直接DNSを管理する場合に最適化されている

### 試行2: Cloudflare Transform Rules（未完了）

Cloudflare Dashboardで「Transform Rules」メニューが見つからない。

代わりに「Rule Template」→「Transform request or responses」で以下の7択が表示：
1. Rewrite path for object storage bucket
2. Rewrite path of moved section
3. Rewrite path for countries
4. Remove HTTP header from request
5. Add static header to response
6. Remove HTTP header from response
7. Normalize encoded slash in URL path

→ これらではHostヘッダーの書き換えができない

## 🔎 調査して欲しいこと

### 1. 最新のCloudflare設定方法（2025年版）

**質問**:
- 2025年現在、CloudflareでHostヘッダーを書き換える正しい方法は何か？
- 「Transform Rules」メニューはどこにあるのか？（UIが変更されている可能性）
- Cloudflareの無料プランでHostヘッダー書き換えは可能か？有料プランが必要か？
- 最新のCloudflare Dashboardでのメニュー構成と設定手順

**具体的に知りたいこと**:
- Cloudflare Transform Rules（Modify Request Header）の正確な場所
- または、代替方法（Workers、Page Rules、その他）
- 各方法のメリット・デメリット
- 各方法の料金プラン要件

### 2. Cloudflare + Cloud Runのベストプラクティス

**質問**:
- Cloudflareプロキシを使用してCloud Runにカスタムドメインを設定する推奨方法は？
- Cloud Runのドメインマッピング機能 vs Cloudflareの設定、どちらが推奨される？
- Cloudflareプロキシを使う場合、Cloud Runのドメイン検証をスキップする方法はあるか？

**具体的に知りたいこと**:
- Google公式ドキュメントでの推奨構成
- Cloudflare公式ドキュメントでの推奨構成
- 実際のプロダクション環境での事例
- セキュリティ、パフォーマンス、コスト面での考慮事項

### 3. Cloudflare Workersを使った解決策

**質問**:
- Cloudflare WorkersでHostヘッダーを書き換える最新の実装方法は？
- Workers の料金プラン要件は？（無料プランで十分か？）
- Workersを使う場合のパフォーマンス影響は？
- Workersのデプロイとメンテナンスの手順

**具体的に知りたいこと**:
- 最新のWorkers APIでの実装例（2025年版）
- Workersのルーティング設定方法
- エラーハンドリングのベストプラクティス
- 本番環境での運用ノウハウ

### 4. 代替ソリューション

**質問**:
- Cloudflare以外のCDN（Fastly、AWS CloudFront等）を使った場合の実装方法
- Cloud Runのネイティブ機能だけで実現する方法
- Load Balancerを使った方法
- その他の推奨アーキテクチャ

## 💡 理想的な解決策（こういうことができたらいいな）

### 要件

1. **シンプル**: 設定が簡単で、メンテナンスが少ない
2. **CI/CD対応**: GitHub Actionsでデプロイ時に自動設定できる
3. **コスト効率**: 無料プランまたは低コストで実現可能
4. **パフォーマンス**: レイテンシが低く、高速
5. **セキュリティ**: SSL/TLS、セキュリティヘッダー、DDoS保護が適切に設定される
6. **スケーラブル**: トラフィック増加に対応できる

### 理想的なワークフロー

```
1. GitHub Actionsでコードをプッシュ
   ↓
2. Cloud Runに自動デプロイ
   ↓
3. カスタムドメイン設定が自動的に適用される（手動設定不要）
   ↓
4. https://app.sage-base.com/ ですぐにアクセス可能
```

### 技術的な理想

- ✅ Cloudflareプロキシを活用（CDN、DDoS保護）
- ✅ Cloud RunのオートスケーリングとKnative機能を活用
- ✅ SSL/TLS証明書の自動管理
- ✅ セキュリティヘッダーの自動追加
- ✅ Google Analyticsの統合
- ✅ ログとモニタリングの統合
- ✅ 設定ファイル（IaC）で管理可能

## 📚 参考情報

### 現在のドキュメント

- `docs/CUSTOM_DOMAIN_SETUP.md` - カスタムドメイン設定手順（Cloud Run前提）
- `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` - 本番環境デプロイチェックリスト
- `.github/workflows/deploy-to-cloud-run.yml` - デプロイワークフロー

### 既存の実装

- セキュリティヘッダーミドルウェア: `src/interfaces/web/streamlit/middleware/security_headers.py`
- Google Analytics統合: `src/interfaces/web/streamlit/components/analytics.py`
- Cloudflare Workers設定（未デプロイ）: `docs/CUSTOM_DOMAIN_SETUP.md` 内に記載

### 技術スタック

- **バックエンド**: Python 3.13, FastAPI, Streamlit
- **インフラ**: Google Cloud Run, Cloud SQL (PostgreSQL)
- **CDN**: Cloudflare
- **CI/CD**: GitHub Actions
- **コンテナ**: Docker, Artifact Registry

## 🎯 調査結果で欲しいアウトプット

1. **最新のCloudflare設定手順**（2025年版、スクリーンショット付き）
2. **推奨アーキテクチャ**（理由とトレードオフ付き）
3. **実装サンプルコード**（すぐに使えるもの）
4. **料金見積もり**（各ソリューションのコスト比較）
5. **トラブルシューティングガイド**（よくある問題と解決策）
6. **セキュリティチェックリスト**（本番環境向け）

---

以上の情報をもとに、**Cloudflare + Cloud Runでカスタムドメインを設定する最適な方法**を調査してください。

特に、**2025年現在のCloudflareの最新UI/API**と、**Cloudflareプロキシを使う場合のCloud Runとの統合方法**に焦点を当てて調査をお願いします。
