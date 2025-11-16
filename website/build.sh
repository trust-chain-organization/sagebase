#!/bin/bash

# Cloudflare Pagesビルドスクリプト
# プレビュー環境では動的にbaseURLを設定し、本番環境では固定URLを使用

set -e

echo "🚀 Hugoビルドを開始します..."

# Cloudflare Pagesの環境変数を確認
if [ -n "$CF_PAGES" ]; then
  echo "📦 Cloudflare Pages環境で実行中"

  # プレビュー環境かどうかを判定
  if [ "$CF_PAGES_BRANCH" != "main" ]; then
    echo "🔍 プレビュー環境を検出"
    echo "   ブランチ: $CF_PAGES_BRANCH"
    echo "   デプロイメントURL: $CF_PAGES_URL"

    # プレビュー環境ではCF_PAGES_URLをbaseURLとして使用
    hugo --baseURL="$CF_PAGES_URL" --minify
    echo "✅ プレビュー環境用にビルド完了 (baseURL: $CF_PAGES_URL)"
  else
    echo "🌐 本番環境を検出"
    # 本番環境ではhugo.tomlのbaseURLを使用
    hugo --minify
    echo "✅本番環境用にビルド完了"
  fi
else
  echo "💻 ローカル環境で実行中"
  # ローカル環境ではhugo.tomlのbaseURLを使用
  hugo --minify
  echo "✅ ローカル環境用にビルド完了"
fi

echo "📊 ビルド結果:"
ls -lh public/index.html 2>/dev/null || echo "⚠️ index.htmlが見つかりません"
