# 本番環境デプロイチェックリスト

このチェックリストは、app.sage-base.comドメインでSagebaseを本番環境にデプロイする際の
確認項目をまとめたものです。

**Issue**: #726 - [PBI-007] カスタムドメインの設定と本番環境への公開

---

## 📋 デプロイ前の準備

### ドメイン・DNS設定
- [ ] Cloudflareでapp.sage-base.comドメインを購入済み
- [ ] Cloudflare DNSでCNAMEまたはAレコードを設定
- [ ] wwwサブドメインのリダイレクト設定（オプション）
- [ ] DNS伝播の確認（`nslookup app.sage-base.com`）
- [ ] Cloudflare Proxyが有効化されている（オレンジ色のアイコン）

### Cloud Run設定
- [ ] Cloud RunにアプリがデプロイされてStable状態
- [ ] Cloud Runサービス名が `sagebase-streamlit` であることを確認
- [ ] Cloud Runサービスが正常に動作（ヘルスチェック成功）
- [ ] 環境変数を本番環境用に更新
  - [ ] `GOOGLE_OAUTH_REDIRECT_URI=https://app.sage-base.com/`
  - [ ] `GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX`（Secret Manager推奨）
  - [ ] `ENVIRONMENT=production`
  - [ ] `CLOUD_RUN=true`
- [ ] Cloud SQLへの接続が正常に動作
- [ ] Secret Managerから機密情報が正しく注入されている

### Google Analytics設定
- [ ] Google Analytics 4プロパティを作成
- [ ] データストリーム（Web）を追加（URL: https://app.sage-base.com）
- [ ] 測定ID（G-XXXXXXXXXX）をコピー
- [ ] Secret Managerに `google-analytics-id` シークレットを作成
- [ ] Cloud Runの環境変数またはシークレット参照として設定

---

## 🔒 セキュリティ設定

### Cloudflare Workers
- [ ] セキュリティヘッダー用のWorkerを作成
- [ ] Workerスクリプトをデプロイ
- [ ] `app.sage-base.com/*` にルートを追加
- [ ] 以下のヘッダーが設定されているか確認：
  - [ ] `X-Frame-Options: DENY`
  - [ ] `X-Content-Type-Options: nosniff`
  - [ ] `Strict-Transport-Security`
  - [ ] `Content-Security-Policy`
  - [ ] `Referrer-Policy`

### SSL/TLS設定
- [ ] CloudflareのSSL/TLS暗号化モードが **Full (strict)** に設定
- [ ] Cloudflare Universal SSL証明書が発行済み
- [ ] HTTPSアクセスが正常に動作
- [ ] HTTPからHTTPSへの自動リダイレクトが動作（Cloudflare Workers）
- [ ] **Always Use HTTPS** が有効
- [ ] **Minimum TLS Version** が TLS 1.2 以上に設定

### 認証設定
- [ ] Google OAuthクライアントIDとシークレットが設定済み
- [ ] リダイレクトURIに `https://app.sage-base.com/` が登録済み
- [ ] 許可されたメールアドレスリストが設定済み（必要に応じて）
- [ ] OAuth認証フローが本番ドメインで動作

---

## 🔍 SEO・アクセシビリティ設定

### robots.txtとsitemap.xml
- [ ] `robots.txt` がプロジェクトルートに存在
- [ ] `sitemap.xml` がプロジェクトルートに存在
- [ ] https://app.sage-base.com/robots.txt にアクセス可能
- [ ] https://app.sage-base.com/sitemap.xml にアクセス可能
- [ ] robots.txtに正しいサイトマップURLが記載されている

### Google Search Console
- [ ] Google Search Consoleにプロパティを追加
- [ ] DNSベースの所有権確認を完了
- [ ] サイトマップ（https://app.sage-base.com/sitemap.xml）を送信
- [ ] インデックス登録のリクエストを送信（初回のみ）

### メタタグ・OGP設定
- [ ] ページタイトルが適切に設定されている
- [ ] ページアイコン（favicon）が設定されている
- [ ] 404エラーページが実装されている

---

## ✅ 機能テスト

### 基本動作確認
- [ ] https://app.sage-base.com/ (ホームページ) にアクセス可能
- [ ] ログインページが表示される（OAuth無効時はスキップ）
- [ ] Google OAuthでログインできる
- [ ] ログアウトが正常に動作
- [ ] すべてのナビゲーションリンクが動作

### 各ページの動作確認
- [ ] 会議管理ページ（/meetings）が正常に動作
- [ ] 政党管理ページ（/political_parties）が正常に動作
- [ ] 会議体管理ページ（/conferences）が正常に動作
- [ ] 開催主体管理ページ（/governing_bodies）が正常に動作
- [ ] 政治家管理ページ（/politicians）が正常に動作
- [ ] 政治家レビューページ（/extracted_politicians）が正常に動作
- [ ] 議員団管理ページ（/parliamentary_groups）が正常に動作
- [ ] 議案管理ページ（/proposals）が正常に動作
- [ ] 発言レコードページ（/conversations）が正常に動作
- [ ] 発言・発言者管理ページ（/conversations_speakers）が正常に動作
- [ ] 処理実行ページ（/processes）が正常に動作
- [ ] LLM履歴ページ（/llm_history）が正常に動作
- [ ] 作業履歴ページ（/work_history）が正常に動作

### データ操作確認
- [ ] データの閲覧が正常に動作
- [ ] データの検索・フィルタリングが正常に動作
- [ ] データの編集が正常に動作（権限がある場合）
- [ ] データの削除が正常に動作（権限がある場合）
- [ ] ファイルアップロードが正常に動作

### 処理実行確認
- [ ] 議事録処理が正常に実行される
- [ ] 政治家スクレイピングが正常に実行される
- [ ] LLM処理が正常に動作
- [ ] エラーハンドリングが適切に動作
- [ ] 処理履歴が正しく記録される

---

## 📊 モニタリング・分析

### Google Analytics
- [ ] ページビューがトラッキングされている
- [ ] リアルタイムレポートでアクセスが確認できる
- [ ] イベントトラッキングが動作している（必要に応じて）
- [ ] コンバージョン設定が完了している（必要に応じて）

### エラー監視
- [ ] Sentry（またはその他のエラートラッキング）が設定済み
- [ ] エラーが正しく記録される
- [ ] アラート通知が設定されている
- [ ] エラーレートが許容範囲内

### パフォーマンス
- [ ] ページ読み込み時間が3秒以内
- [ ] 大量データの表示が適切にページネーションされている
- [ ] データベースクエリが最適化されている
- [ ] 画像・静的ファイルが最適化されている

---

## 🌐 ブラウザ互換性テスト

### デスクトップブラウザ
- [ ] Chrome (最新版)
- [ ] Firefox (最新版)
- [ ] Safari (最新版)
- [ ] Edge (最新版)

### モバイルブラウザ
- [ ] iOS Safari
- [ ] Android Chrome
- [ ] レスポンシブデザインが正常に動作

### アクセシビリティ
- [ ] キーボードナビゲーションが動作
- [ ] スクリーンリーダー対応（基本的なARIA属性）
- [ ] カラーコントラストが適切

---

## 🔧 インフラ・バックアップ

### Cloud Run
- [ ] Cloud Runサービスのリソース設定が適切（CPU: 2, Memory: 2Gi）
- [ ] 最小インスタンス数の設定（コールドスタート対策）
- [ ] 最大インスタンス数の設定（コスト制御）
- [ ] タイムアウト設定が適切（300秒）
- [ ] Cloud Monitoringでメトリクスを監視

### データベース (Cloud SQL)
- [ ] 本番環境用のCloud SQLインスタンスが稼働中
- [ ] Cloud SQL Proxyが正しく設定されている
- [ ] データベース接続が安定している
- [ ] 自動バックアップが有効（7日間保持）
- [ ] Point-in-Time Recoveryが有効
- [ ] リストア手順が文書化されている

### 環境変数とシークレット
- [ ] すべての必須環境変数が設定されている
- [ ] Secret Managerにすべてのシークレットが保存されている
  - [ ] `google-api-key` (Gemini API)
  - [ ] `database-password`
  - [ ] `google-analytics-id`
- [ ] 機密情報がGitにコミットされていない
- [ ] `.env.example` が最新の状態

---

## 📝 ドキュメント

### 更新が必要なドキュメント
- [ ] README.mdに本番環境URLを追加
- [ ] DEPLOYMENT.mdを更新
- [ ] CUSTOM_DOMAIN_SETUP.mdを確認
- [ ] API ドキュメントを更新（該当する場合）

### 手順書の整備
- [ ] デプロイ手順が文書化されている
- [ ] ロールバック手順が文書化されている
- [ ] トラブルシューティングガイドが用意されている
- [ ] 運用マニュアルが整備されている

---

## 🚀 デプロイ実行

### デプロイ前の最終確認
- [ ] すべての変更がGitにコミット・プッシュされている
- [ ] CIパイプラインがすべてパスしている
- [ ] ステージング環境でテスト済み（該当する場合）
- [ ] チーム全体に本番デプロイを通知

### デプロイ実施
- [ ] GitHub Actionsによる自動デプロイ（mainブランチへのマージ）
  - または手動デプロイ：`gcloud run deploy` コマンド実行
- [ ] Cloud Buildログにエラーがないか確認
- [ ] Cloud Runリビジョンが正常にデプロイされた
- [ ] アプリケーションが正常に起動
- [ ] ヘルスチェックが成功（Cloud Runの内部ヘルスチェック）

### デプロイ後の確認
- [ ] 本番環境でスモークテストを実施
- [ ] 主要機能が正常に動作することを確認
- [ ] エラーログを監視
- [ ] パフォーマンスメトリクスを確認

---

## 🎉 本番公開後

### 公開アナウンス
- [ ] チーム全体に本番公開を通知
- [ ] ユーザーに新しいURLを通知
- [ ] ソーシャルメディアで告知（該当する場合）
- [ ] プレスリリース（該当する場合）

### 監視体制
- [ ] 24時間以内は定期的にエラーログを確認
- [ ] ユーザーフィードバックを収集
- [ ] パフォーマンスメトリクスを継続的に監視
- [ ] インシデント対応体制を整備

### フォローアップ
- [ ] 1週間後にパフォーマンスレビューを実施
- [ ] ユーザーフィードバックを分析
- [ ] 改善点をバックログに追加
- [ ] 次のリリース計画を作成

---

## 🆘 ロールバック手順

何か問題が発生した場合のロールバック手順：

### 即座のロールバック（前のリビジョンに戻す）

```bash
# 環境変数を設定
export PROJECT_ID="your-project-id"
export REGION="asia-northeast1"
export SERVICE_NAME="sagebase-streamlit"

# 直前のリビジョンにロールバック
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=PREVIOUS=100 \
  --region=$REGION \
  --project=$PROJECT_ID
```

### 特定のリビジョンにロールバック

```bash
# 利用可能なリビジョンを確認
gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID

# 特定のリビジョンにロールバック
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=REVISION_NAME=100 \
  --region=$REGION \
  --project=$PROJECT_ID
```

### 詳細なロールバック手順

1. **問題の特定と影響範囲の確認**
   ```bash
   # ログを確認
   gcloud run logs tail $SERVICE_NAME \
     --region=$REGION \
     --project=$PROJECT_ID
   ```

2. **トラフィックを前のリビジョンに切り替え**
   - 上記のコマンドを実行

3. **問題の根本原因を調査**
   - Cloud Loggingで詳細ログを確認
   - Cloud Monitoringでメトリクスを確認

4. **修正とテスト**
   - 問題を修正
   - ローカルまたはステージング環境でテスト

5. **再デプロイ**
   - GitHub Actionsで再デプロイ
   - または手動デプロイ

**緊急連絡先**:
- チームリーダー: [連絡先]
- インフラ担当: [連絡先]
- GCP サポート: https://cloud.google.com/support

---

## ✅ 完了確認

すべてのチェック項目が完了したら、以下を実行：

1. [ ] Issue #726を更新（完了した項目をチェック）
2. [ ] スクリーンショットを添付（主要ページの動作確認）
3. [ ] セキュリティヘッダーのテスト結果を添付
4. [ ] Google Analytics のスクリーンショットを添付
5. [ ] Issue #726をクローズ 🎉

**おめでとうございます！Sagebaseが本番環境で公開されました！** 🚀
