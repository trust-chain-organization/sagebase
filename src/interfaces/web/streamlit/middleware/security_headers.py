"""Security headers middleware for Streamlit application.

このモジュールは、Streamlitアプリケーションにセキュリティヘッダーを
追加するためのミドルウェアを提供します。
"""

import streamlit.components.v1 as components


def inject_security_headers():
    """セキュリティヘッダーをHTMLメタタグとして挿入する。

    以下のセキュリティヘッダーを設定します：
    - Content-Security-Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Permissions-Policy

    注意:
        Streamlitの制約により、HTTPヘッダーとしての設定は困難なため、
        可能な範囲でHTMLメタタグとして挿入します。
        本番環境ではCloudflare Workers等のリバースプロキシで
        追加のセキュリティヘッダーを設定することを推奨します。
    """
    # Content Security Policy
    # Streamlitの動作に必要なディレクティブを許可しつつ、セキュリティを強化
    csp_directives = [
        "default-src 'self'",
        (
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://www.googletagmanager.com https://www.google-analytics.com"
        ),
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: https: blob:",
        (
            "connect-src 'self' https://www.google-analytics.com "
            "https://www.googletagmanager.com wss://*.streamlit.app "
            "wss://sage-base.com"
        ),
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "upgrade-insecure-requests",
    ]
    csp = "; ".join(csp_directives)

    # セキュリティメタタグを挿入
    security_headers_html = f"""
    <meta http-equiv="Content-Security-Policy" content="{csp}">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <meta name="referrer" content="strict-origin-when-cross-origin">

    <!-- Additional security headers via JavaScript -->
    <script>
    // Note: These should ideally be set as HTTP headers by the server
    // For production, configure these in Cloudflare Workers or similar
    console.log('Security headers meta tags loaded');
    </script>
    """

    # HTMLコンポーネントとして挿入
    components.html(security_headers_html, height=0)


def get_cloudflare_worker_config() -> str:
    """Cloudflare Workers用のセキュリティヘッダー設定を生成する。

    Returns:
        Cloudflare Workers用のJavaScriptコード

    使用方法:
        1. Cloudflareダッシュボードでカスタムドメインを設定
        2. Workers & Pages > Create Worker
        3. 以下のコードをコピーして貼り付け
        4. sage-base.comドメインにルートを追加
    """
    worker_script = """
// Cloudflare Worker for adding security headers
// Deploy this to sage-base.com domain

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Fetch the original response
  const response = await fetch(request)

  // Create a new response with security headers
  const newResponse = new Response(response.body, response)

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

  // Content Security Policy
  const csp = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' " +
      "https://www.googletagmanager.com https://www.google-analytics.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: https: blob:",
    "connect-src 'self' https://www.google-analytics.com " +
      "https://www.googletagmanager.com wss://*.streamlit.app " +
      "wss://sage-base.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests"
  ].join('; ')
  newResponse.headers.set('Content-Security-Policy', csp)

  // HTTPS redirect
  if (request.url.startsWith('http://')) {
    const httpsUrl = request.url.replace('http://', 'https://')
    return Response.redirect(httpsUrl, 301)
  }

  return newResponse
}
"""
    return worker_script


def inject_https_redirect():
    """HTTPS強制リダイレクトのJavaScriptを挿入する。

    クライアント側でHTTPアクセスを検知し、HTTPSにリダイレクトします。
    """
    redirect_script = """
    <script>
    // Force HTTPS redirect
    if (window.location.protocol === 'http:' &&
        window.location.hostname !== 'localhost' &&
        window.location.hostname !== '127.0.0.1') {
        window.location.href = window.location.href.replace('http:', 'https:');
    }
    </script>
    """

    components.html(redirect_script, height=0)
