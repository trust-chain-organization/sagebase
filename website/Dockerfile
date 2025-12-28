# Alpine Linuxベースイメージ
FROM alpine:3.19

# アーキテクチャに応じたHugo Extended版をインストール
RUN apk add --no-cache \
    wget \
    ca-certificates \
    libc6-compat \
    libstdc++ && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        HUGO_ARCH="amd64"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        HUGO_ARCH="arm64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget https://github.com/gohugoio/hugo/releases/download/v0.152.2/hugo_extended_0.152.2_linux-${HUGO_ARCH}.tar.gz && \
    tar -xzf hugo_extended_0.152.2_linux-${HUGO_ARCH}.tar.gz && \
    mv hugo /usr/local/bin/ && \
    rm hugo_extended_0.152.2_linux-${HUGO_ARCH}.tar.gz && \
    hugo version

# 作業ディレクトリを設定
WORKDIR /site

# サイトファイルをコピー
COPY . .

# デフォルトコマンド: 開発サーバーを起動
CMD ["hugo", "server", "--bind", "0.0.0.0", "--buildDrafts"]
