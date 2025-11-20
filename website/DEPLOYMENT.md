# Cloudflare Pagesへのデプロイメント手順

このドキュメントでは、PolibaseのHugoサイトをCloudflare Pagesにデプロイする手順を説明します。

## 📋 前提条件

- Cloudflareアカウント（無料プランで利用可能）
- GitHubアカウント
- trust-chain-organization/polibase リポジトリへのアクセス権

## 🚀 初回デプロイ手順

### 1. Cloudflare Pagesプロジェクトの作成

1. **Cloudflare Dashboardにログイン**
   - https://dash.cloudflare.com/ にアクセス
   - アカウントにログイン

2. **Pagesセクションへ移動**
   - 左側のメニューから「Workers & Pages」を選択
   - 「Create application」ボタンをクリック
   - 「Pages」タブを選択
   - 「Connect to Git」を選択

3. **GitHubリポジトリとの連携**
   - 「Connect GitHub」をクリック
   - 権限の認可画面が表示されたら、Cloudflare Pagesに必要な権限を付与
   - リポジトリ一覧から `trust-chain-organization/polibase` を選択
   - 「Begin setup」をクリック

### 2. ビルド設定の構成

**プロジェクト設定**:
```
Project name: polibase-website（または任意の名前）
Production branch: main
```

**ビルド設定**:
```
Build command: ./build.sh
Build output directory: public
Root directory (advanced): website
```

> **💡 重要**: `build.sh`スクリプトを使用することで、プレビュー環境では自動的に正しいbaseURLが設定されます。これにより、プレビュー環境でのリンクが正しく動作します。

**環境変数**:

「Environment variables (advanced)」セクションで以下の環境変数を追加：

| Variable name | Value | Description |
|--------------|-------|-------------|
| `HUGO_VERSION` | `0.152.2` | Hugoのバージョン指定 |
| `HUGO_ENV` | `production` | 本番環境設定 |

> **注意**: Cloudflare PagesはHugo Extendedを自動的に使用します。

### 3. ブランチデプロイの設定

**本番デプロイ**:
- `main` ブランチへのプッシュ → 本番環境へ自動デプロイ

**プレビューデプロイ**:
- その他のブランチへのプッシュ → プレビュー環境へ自動デプロイ
- プレビューURLは `<ブランチ名>.<プロジェクト名>.pages.dev` の形式

デフォルトで全ブランチのプレビューデプロイが有効になっています。

### 4. デプロイの開始

1. 「Save and Deploy」をクリック
2. 初回ビルドが開始されます（通常1-3分）
3. ビルドログで進捗を確認できます

### 5. デプロイ完了の確認

ビルドが成功すると：
- 本番URL: `<プロジェクト名>.pages.dev`
- デプロイ履歴とログが確認可能

ブラウザでURLにアクセスして、サイトが正常に表示されることを確認してください。

## 🔄 継続的デプロイ

初回設定が完了すると、以降は自動的にデプロイされます：

### 本番デプロイ
```bash
git checkout main
git pull origin main
# 変更を加える
git add .
git commit -m "サイトの更新"
git push origin main
```

→ `main` ブランチへのプッシュで本番環境が自動更新されます

### プレビューデプロイ
```bash
git checkout -b feature/new-content
# 変更を加える
git add .
git commit -m "新しいコンテンツを追加"
git push origin feature/new-content
```

→ フィーチャーブランチへのプッシュでプレビュー環境が自動作成されます

プレビューURL: `feature-new-content.polibase-website.pages.dev`

## 🎨 カスタムドメインの設定（オプション）

独自ドメインを使用する場合：

1. Cloudflare Pages プロジェクト設定で「Custom domains」を選択
2. 「Set up a custom domain」をクリック
3. ドメイン名を入力（例: `www.polibase.org`）
4. DNS設定の指示に従って設定
5. SSL/TLS証明書が自動的に発行されます

## 🔧 詳細設定

### ビルド設定の変更

プロジェクト設定から以下を変更できます：

- **Settings** > **Builds & deployments**
  - ビルドコマンドの変更
  - 環境変数の追加・編集
  - Node.jsバージョンの指定

### プレビューデプロイの制御

プレビューデプロイを特定のブランチのみに限定する場合：

1. **Settings** > **Builds & deployments** > **Branch deployments**
2. 「Configure preview deployments」で設定を変更
3. ブランチパターンでフィルタリング可能

### ビルドキャッシュのクリア

ビルドに問題がある場合、キャッシュをクリアできます：

1. プロジェクトの**Deployments**ページへ移動
2. 該当のデプロイメントの「...」メニューから「Retry deployment」
3. 「Clear build cache and retry」を選択

## 🐛 トラブルシューティング

### ビルドが失敗する

**症状**: ビルドログに `hugo: command not found` や類似のエラー

**解決策**:
1. 環境変数 `HUGO_VERSION` が正しく設定されているか確認
2. ビルドコマンドが `hugo --minify` であることを確認

---

**症状**: `Error: module "PaperMod" not found`

**解決策**:
- GitHubリポジトリでサブモジュールが正しく設定されているか確認
- Cloudflare Pagesはデフォルトでサブモジュールを取得します
- サブモジュールの初期化コマンドは不要です

### テーマが表示されない

**症状**: サイトが真っ白で、スタイルが適用されていない

**解決策**:
1. `hugo.toml` の `baseURL` が正しいか確認
2. Cloudflare Pages の環境変数 `HUGO_ENV=production` が設定されているか確認

### プレビューデプロイが作成されない

**症状**: ブランチにプッシュしてもプレビュー環境が作成されない

**解決策**:
1. **Settings** > **Builds & deployments** > **Branch deployments** を確認
2. 「Enable preview deployments」が有効になっているか確認
3. ブランチパターンに該当しているか確認

### プレビュー環境でリンクが本番環境に遷移する

**症状**: プレビュー環境でページ内のリンクをクリックすると、本番環境（sage-base.com）に遷移してしまう

**原因**: ビルド時に固定のbaseURLが使用されている

**解決策**:
1. **Settings** > **Builds & deployments** > **Build configuration** で「Edit configuration」をクリック
2. **Build command** を `./build.sh` に変更
3. 「Save」をクリック
4. 次回のデプロイから、プレビュー環境では正しいURLが使用されます

`build.sh`スクリプトは、環境変数`CF_PAGES_URL`を使用してプレビュー環境のbaseURLを自動設定します。

## 📊 デプロイメントの監視

### デプロイ履歴の確認

1. Cloudflare Pages プロジェクトの **Deployments** タブを開く
2. 各デプロイメントの状態（Success/Failed）を確認
3. ビルドログをクリックして詳細を確認

### ロールバック

問題のあるデプロイをロールバックする場合：

1. **Deployments** タブで以前の成功したデプロイを選択
2. 「...」メニューから「Rollback to this deployment」を選択
3. 本番環境が即座に以前のバージョンに戻ります

## 🔒 セキュリティ設定

### アクセス制限（オプション）

プレビュー環境にアクセス制限をかける場合：

1. **Settings** > **Preview deployments access**
2. 「Require authorization」を有効化
3. アクセスを許可するメールアドレスを追加

## 🧹 プレビュー環境の自動クリーンアップ

### 背景

Cloudflare Pagesでは、PRがマージまたはクローズされても、プレビュー環境（デプロイメント）は**自動的に削除されません**。これにより、以下の問題が発生します：

- デプロイメント履歴が累積し、管理が煩雑化
- 古いプレビュー環境が公開され続け、セキュリティリスクが発生
- デプロイメント数が数千件に達すると、プロジェクト自体の削除が困難になる

### 自動クリーンアップの設定

このプロジェクトでは、GitHub Actionsを使用して、PRがクローズされた際に自動的にプレビュー環境を削除します。

#### 必要な設定

1. **Cloudflare APIトークンの生成**
   - Cloudflareダッシュボードにログイン
   - 「My Profile」→「API Tokens」→「Create Token」
   - 「Custom token」を選択
   - 権限を設定：
     - Account: Cloudflare Pages = Edit
   - トークンを生成し、安全に保管

2. **Cloudflareアカウント IDの確認**
   - Cloudflareダッシュボードの右サイドバーに表示されている「Account ID」をコピー

3. **GitHubシークレットの設定**
   - GitHubリポジトリの「Settings」→「Secrets and variables」→「Actions」
   - 以下の2つのシークレットを追加：
     - `CLOUDFLARE_API_TOKEN`: 手順1で生成したAPIトークン
     - `CLOUDFLARE_ACCOUNT_ID`: 手順2で確認したアカウントID

4. **プロジェクト名の確認**
   - `.github/workflows/cleanup-cloudflare-previews.yml`の`project`パラメータが、Cloudflare Pagesのプロジェクト名と一致していることを確認
   - プロジェクト名は、Cloudflare Pagesダッシュボードで確認できます（例：`sagebase`）

#### 動作

- PRがマージまたはクローズされると、GitHub Actionsが自動的に実行されます
- 該当するブランチのプレビュー環境（デプロイメントとエイリアス）が削除されます
- ログは「Actions」タブで確認できます

#### トラブルシューティング

**エラー: "Resource not found"**
- `project`パラメータが正しいプロジェクト名になっているか確認してください

**エラー: "Authentication failed"**
- `CLOUDFLARE_API_TOKEN`が正しく設定されているか確認してください
- APIトークンの権限が「Cloudflare Pages: Edit」になっているか確認してください

**デプロイメントが削除されない**
- GitHub Actionsのログを確認してください（「Actions」タブ）
- ワークフローが正常に実行されているか確認してください

## 📚 参考リンク

- [Cloudflare Pages公式ドキュメント](https://developers.cloudflare.com/pages/)
- [HugoとCloudflare Pagesの統合ガイド](https://developers.cloudflare.com/pages/framework-guides/deploy-a-hugo-site/)
- [Cloudflare Pages 環境変数](https://developers.cloudflare.com/pages/configuration/build-configuration/)

## 🆘 サポート

問題が解決しない場合：

1. [Cloudflare Community Forum](https://community.cloudflare.com/)で質問
2. [GitHub Issues](https://github.com/trust-chain-organization/polibase/issues)でプロジェクトチームに報告
