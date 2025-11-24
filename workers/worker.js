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

    // オリジン間認証のためのシークレットトークン
    // env.CF_SECRET が設定されている場合のみヘッダーを追加
    if (env.CF_SECRET) {
      newRequest.headers.set('X-CF-Secret', env.CF_SECRET);
    }

    // 6. オリジンへのフェッチ実行
    try {
      const response = await fetch(newRequest);

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
      return new Response(`Edge Proxy Error: ${e.message}`, { status: 502 });
    }
  }
};
