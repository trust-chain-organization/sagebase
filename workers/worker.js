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
    // 受信したrequestオブジェクトはイミュータブル（変更不可）なプロパティが多いため、
    // 新しいRequestオブジェクトを作成してプロパティをコピーします。
    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      redirect: 'follow'
    });

    // 4. 重要：Hostヘッダーのオーバーライド
    // これによりCloud RunのGFEは、このリクエストが正規のrun.app宛てであると認識します。
    newRequest.headers.set('Host', UPSTREAM_ORIGIN);

    // 5. セキュリティとトレーサビリティのためのヘッダー付与
    // バックエンドアプリが「ユーザーが実際にアクセスしたドメイン」を知るために必要です。
    newRequest.headers.set('X-Forwarded-Host', 'app.sage-base.com');

    // WebSocket接続のための追加ヘッダー
    // StreamlitがHTTPS経由のWebSocket (wss://) を使用することを保証
    newRequest.headers.set('X-Forwarded-Proto', 'https');

    // クライアントの実IPアドレスを転送（Cloudflareが自動設定）
    const clientIp = request.headers.get('CF-Connecting-IP');
    if (clientIp) {
      newRequest.headers.set('X-Real-IP', clientIp);
      newRequest.headers.set('X-Forwarded-For', clientIp);
    }

    // オリジン間認証のためのシークレットトークン
    // env.CF_SECRET が設定されている場合のみヘッダーを追加
    if (env.CF_SECRET) {
      newRequest.headers.set('X-CF-Secret', env.CF_SECRET);
    }

    // 6. オリジンへのフェッチ実行
    try {
      const response = await fetch(newRequest);

      // WebSocketのアップグレードレスポンス（status: 101）の場合はそのまま返す
      // レスポンスを変更するとWebSocket接続が失敗する
      if (response.status === 101) {
        return response;
      }

      // 7. レスポンスヘッダーの処理（キャッシュ最適化）
      const newResponseHeaders = new Headers(response.headers);
      newResponseHeaders.set('X-Worker-Proxy', 'Active');

      // 静的アセットのキャッシュ設定（Phase 4最適化）
      if (url.pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|woff|woff2|ico)$/)) {
        // Cloudflareエッジで1日キャッシュ
        newResponseHeaders.set('Cache-Control', 'public, max-age=86400');
      }

      // デバッグ用情報の削除（セキュリティ向上）
      newResponseHeaders.delete('X-Cloud-Trace-Context');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: newResponseHeaders
      });

    } catch (e) {
      // 8. エラーハンドリング
      // オリジンへの接続失敗時などに、ユーザーフレンドリーなエラーまたは502 Bad Gatewayを返します。
      console.error('Edge Proxy Error:', {
        error: e.message,
        url: url.toString(),
        method: request.method,
        isWebSocket: request.headers.get('Upgrade') === 'websocket',
      });
      return new Response(`Edge Proxy Error: ${e.message}`, { status: 502 });
    }
  }
};
