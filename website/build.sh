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

    # website/ に変更があるかチェック（ビルドスキップ判定）
    echo "📋 変更ファイルをチェック中..."
    if git fetch origin main --depth=50 2>/dev/null; then
      CHANGED_FILES=$(git diff --name-only origin/main HEAD 2>/dev/null || echo "")

      if [ -n "$CHANGED_FILES" ]; then
        echo "📝 変更されたファイル:"
        echo "$CHANGED_FILES" | head -10

        # website/ ディレクトリに変更がない場合はビルドをスキップ
        if ! echo "$CHANGED_FILES" | grep -q "^website/"; then
          echo "✅ website/ に変更がないため、ビルドをスキップします"
          echo "   （Cloudflare Pages のビルドコストを節約）"

          # ダミーのpublicディレクトリを作成（ビルド成功として扱う）
          mkdir -p public
          echo "<!DOCTYPE html><html><head><title>Build Skipped</title></head><body><h1>Build Skipped</h1><p>No changes in website/ directory.</p></body></html>" > public/index.html

          exit 0
        else
          echo "✓ website/ に変更があります。ビルドを続行します。"
        fi
      else
        echo "⚠️ 変更ファイルを取得できませんでした。ビルドを続行します。"
      fi
    else
      echo "⚠️ git fetch に失敗しました。ビルドを続行します。"
    fi

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
