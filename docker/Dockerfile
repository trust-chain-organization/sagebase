# マルチステージビルドを使用して高速化
# ステージ1: 依存関係のビルド
FROM python:3.13-slim AS dependencies

WORKDIR /app

# curlをインストールしてからuvをインストール
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール（BuildKitキャッシュマウントを使用）
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_CACHE_DIR=/root/.cache/uv

# 依存関係ファイルのみをコピー（キャッシュ効率向上）
COPY pyproject.toml uv.lock README.md ./

# 依存関係をインストール（キャッシュマウントを使用）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# ステージ2: システムパッケージのインストール
FROM python:3.13-slim AS system-packages

# システムパッケージを並列でインストール
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    # Playwright用の基本的な依存関係
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxrandr2 libgbm1 libxcb1 \
    libxkbcommon0 libpango-1.0-0 libcairo2 libasound2 \
    libglib2.0-0 libexpat1 libxtst6 libxss1 \
    fonts-liberation libappindicator3-1 libnss3-dev \
    libgtk-3-0 libxshmfence1 \
    # 追加の依存関係（Debian trixie用 - Python 3.13）
    libicu76 libxslt1.1 libwebp7 libwebpdemux2 \
    libwebpmux3 libenchant-2-2 libsecret-1-0 \
    libhyphen0 libgles2 \
    libegl1 libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
    libgstreamer-plugins-bad1.0-0 libevent-2.1-7t64 \
    libvpx9 libopus0 \
    && rm -rf /var/lib/apt/lists/*

# ステージ3: 最終イメージ
FROM system-packages AS final

WORKDIR /app

# uvとPython環境をコピー
COPY --from=dependencies /root/.local /root/.local
COPY --from=dependencies /app/.venv /app/.venv
COPY --from=dependencies /app/pyproject.toml /app/uv.lock /app/README.md ./

ENV PATH="/root/.local/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_CACHE_DIR=/root/.cache/uv

# Playwrightのブラウザをインストール（BuildKitキャッシュを使用してビルド時間短縮）
RUN --mount=type=cache,target=/root/.cache/ms-playwright \
    uv run playwright install chromium

# アプリケーションファイルをコピー
COPY src/ src/
COPY database/ database/
COPY scripts/ scripts/
COPY baml_src/ baml_src/

# BAMLクライアントコードを生成
RUN uv run baml-cli generate

# 実行権限を設定
RUN chmod +x scripts/docker-uv-wrapper.sh scripts/docker-entrypoint.sh && \
    ln -sf /app/scripts/docker-uv-wrapper.sh /usr/local/bin/uv-wrapper

# エントリーポイントを設定
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/bin/bash"]
