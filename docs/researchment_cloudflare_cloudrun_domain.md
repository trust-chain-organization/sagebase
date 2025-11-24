クラウドネイティブアーキテクチャにおけるエッジとサーバーレスの統合：CloudflareとGoogle Cloud Runの接続課題に関する包括的技術レポート


1. エグゼクティブサマリーとアーキテクチャの背景

現代のWebアプリケーションデリバリにおいて、グローバルなエッジネットワークとリージョナルなサーバーレスコンピューティングリソースの統合は、スケーラビリティ、パフォーマンス、セキュリティを最大化するための標準的なアーキテクチャパターンとして確立されています。本レポートは、特定の技術スタックであるCloudflare（グローバルエッジ）とGoogle Cloud Run（リージョナルサーバーレスオリジン）の統合における技術的課題、特にカスタムドメイン設定時に発生するHostヘッダーの不整合による接続障害について、徹底的な調査と分析を行った結果をまとめたものです。
今回の調査対象となっている事象は、ユーザーがCloudflareをプロキシとして設定し、バックエンドのCloud Runへリクエストを転送する際に、HTTP 404エラーが発生するという問題です。これは、プロキシサーバー（Cloudflare）とオリジンサーバー（Cloud Run）の間で、リクエストのルーティング識別子として機能するHostヘッダーの期待値が一致していないことに起因する「スプリットホライズン（Split-Horizon）」ルーティングの典型的な障害事例です。本稿では、この問題の根本原因をHTTPプロトコルおよびTLSハンドシェイクのレベルで解剖し、2025年現在のCloudflareおよびGoogle Cloudの最新の仕様に基づいた最適な解決策を提示します。
特に、従来のインフラストラクチャでは一般的であったIPアドレスベースのルーティングとは異なり、サーバーレスアーキテクチャにおいてはHTTPヘッダーがルーティングの決定的な要素となるため、その制御が極めて重要になります。Cloudflareの最新機能である「Origin Rules」や「Cloudflare Workers」を活用したプログラムによるリクエスト制御、そしてGoogle Cloud側の「Domain Mapping」や「Load Balancing」といったネイティブ機能を比較検討し、コスト、メンテナンス性、パフォーマンスの観点から最適なアーキテクチャを導き出します。
本レポートは、単なるトラブルシューティングガイドにとどまらず、エッジコンピューティングとサーバーレスアーキテクチャの融合におけるベストプラクティス、セキュリティ設計（ゼロトラストモデル）、そして継続的デプロイメント（CI/CD）への統合手法までを網羅した、包括的な技術文書として構成されています。

2. 理論的枠組み：エッジ・ツー・オリジン トラフィックの力学

堅牢な解決策を実装するためには、まず障害の根底にあるメカニズムを深く理解する必要があります。発生している404エラーは単なる「設定ミス」ではなく、信頼境界とルーティングロジックの衝突によって引き起こされています。ここでは、CloudflareとCloud Runがどのようにリクエストを処理し、なぜその連携が破綻しているのかを理論的に分解します。

2.1 サーバーレスルーティングにおけるHostヘッダーの役割

従来のVMベースのホスティング（例：Google Compute Engine上のNginxやApache）では、サーバーは固定IPアドレスを持ち、到着したリクエストのHostヘッダーを使用して、適切なserver_block（バーチャルホスト）を選択していました。もしヘッダーが一致しない場合でも、default_server設定によってリクエストをキャッチし、コンテンツを返すことが容易でした。
しかし、Cloud RunのようなKnativeベースのサーバーレスプラットフォームでは、ルーティングロジックは厳密にマルチテナント型です。GoogleのグローバルなフロントエンドインフラストラクチャであるGoogle Front End（GFE）は、数百万のコンテナに対する数十億のリクエストを処理しています。GFEは、着信リクエストを特定のプロジェクトおよび特定のコンテナリビジョンにルーティングするための主要なルックアップキーとして、Hostヘッダーに全面的に依存しています。
GFEのルーティングテーブルには、サービス作成時に自動的に生成される*.run.appというドメインが登録されます。これはそのサービスの「正規の識別子」です。一方で、ユーザー独自のカスタムドメイン（例：app.sage-base.com）を使用する場合、そのドメインを明示的にDomain Mapping APIを通じてGFEに登録する必要があります。この登録が行われていない状態で、CloudflareがオリジナルのHostヘッダー（app.sage-base.com）を維持したままリクエストを転送すると、GFEは「私は自分が誰であるか（Googleのインフラであること）は知っているが、あなたが探しているテナント（app.sage-base.com）がこのプロジェクト内のどのコンテナに対応するのか知らない」と判断します。その結果、リクエストは拒否され、HTTP 404 Not Foundが返されることになります。

2.2 TLS終端とHTTPルーティングの乖離

ユーザーの設定状況において、CloudflareのSSL/TLS設定が「Full (strict)」となっている点は、セキュリティ上は正しい選択ですが、デバッグと構成を複雑化させる要因の一つです。通信経路は以下の2つのレッグに分かれます。
レッグA（ユーザー → Cloudflare）： 通信は暗号化されています。Cloudflareは*.sage-base.comの証明書を提示し、TLSハンドシェイクは成功します。
レッグB（Cloudflare → Cloud Run）： 通信は暗号化されています。「Full (strict)」モードでは、Cloudflareはオリジンが提示する証明書が有効であり、かつ信頼できる認証局によって署名されていることを検証します。
ここで重要となるのが、TLSハンドシェイク中に送信されるSNI（Server Name Indication）拡張です。デフォルトでは、Cloudflareはクライアントから受け取ったHostヘッダーと同じ値をSNIとしてオリジンに送信します。つまり、CloudflareはCloud Runに対して「app.sage-base.comの証明書をください」と要求します。しかし、Cloud Run側でドメインマッピングが完了していない場合、Cloud Runはこのドメインに対する有効な証明書を持っていません。通常であればここでTLSハンドシェイクエラーが発生しますが、Cloud Runはデフォルトの証明書（*.run.app用など）を返す挙動をとる場合があり、これがHostヘッダーの不一致と相まって、HTTPレベルでの404エラーへと繋がります。

2.3 「バーチャルホスト」のパラドックスと解決戦略

我々が直面しているのは、リソース（Cloud Run Service）がアドレスA（sagebase...run.app）に存在しているにもかかわらず、リクエストがリソースB（app.sage-base.com）を要求しているというパラドックスです。この矛盾を解消し、正常な通信を確立するためには、論理的に以下の2つの戦略のいずれかを採用する必要があります。
オリジンに真実を教える（Teach the Origin）： Google Cloud Runに対して、「あなたはapp.sage-base.comとしても振る舞うべきである」と教え込む方法です。具体的にはGoogle CloudのDomain Mapping機能を使用します。しかし、これはCloudflareがプロキシとして機能している場合、DNS検証のプロセスで循環的な依存関係や検証エラーが発生しやすく、実装の難易度が高い傾向にあります。
オリジンに対して嘘をつく（Lie to the Origin）： Cloudflare側でリクエストを操作し、Cloud Runに到達する直前に、「これはsagebase...run.appへのリクエストです」と書き換える方法です。これをHostヘッダーのリライト（書き換え）と呼びます。
本レポートでは、特に「オリジンに対して嘘をつく（Cloudflare側での制御）」アプローチを推奨される主要な解決策として位置づけます。これは、Google Cloud側の複雑な検証プロセスをバイパスでき、インフラストラクチャの変更に対する柔軟性が高いためです。次章以降では、2025年現在のCloudflareのエコシステムにおいて、この戦略をどのように実装すべきか詳細に解説します。

3. 主要な解決策：Cloudflare Workersによるミドルウェアパターン

2025年現在、Cloudflareの背後にあるCloud Runにカスタムドメインを設定する際、Google Cloud側の設定を変更せずに最も堅牢かつ柔軟に対応できる方法は、Cloudflare Workersを使用することです。これはユーザーの要件である「シンプルさ」、「CI/CD対応」、「スケーラビリティ」をすべて満たすソリューションです。

3.1 Cloudflare Workersを選択すべき理由

ユーザーの調査において「Transform Rules」メニューでHostヘッダーの書き換えが見つからなかったという報告がありましたが、これは非常に重要な発見です。Cloudflareの製品階層において、GUI（Origin Rulesなど）を通じたHostヘッダーの書き換えは、しばしばEnterpriseプラン限定の機能として提供されています。これは「ドメインフロンティング（Domain Fronting）」と呼ばれる、検閲回避や攻撃目的で使用される技術を防止するためのセキュリティ措置でもあります。
しかし、Cloudflare Workers（サーバーレスエッジコンピューティング環境）を使用すれば、FreeプランであってもJavaScript（またはTypeScript/Rust）を用いてリクエストのあらゆる側面をプログラムで制御することが可能です。これにはHostヘッダーの書き換えも含まれます。Workersは実質的に、エッジで動作する「プログラマブルなリバースプロキシ」として機能し、UIの制限を合法的に回避する手段を提供します。

3.2 実装ガイド：2025年版最新API対応

以下に、Streamlitアプリケーション向けに最適化されたCloudflare Workerの実装詳細を示します。このコードは、リクエストをインターセプトし、ターゲットURLとHostヘッダーをCloud Runのデフォルトドメインに書き換えて転送します。

3.2.1 Workerコードの設計 (worker.js)

このスクリプトは、単なる転送だけでなく、WebSocketのサポート（Streamlitの動作に必須）や、セキュリティヘッダーの付与も行います。

JavaScript


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
    // パス(/foo)やクエリパラメータ(?bar=baz)は維持したまま、接続先ホスト名のみを変更します。
    url.hostname = UPSTREAM_ORIGIN;

    // 3. 新しいリクエストオブジェクトの作成
    // 受信したrequestオブジェクトはイミュータブル（変更不可）なプロパティが多いため、
    // 新しいRequestオブジェクトを作成してプロパティをコピーします。
    const newRequest = new Request(url.toString(), {
      method: request.method,
      headers: request.headers, // 元のヘッダーをすべてコピー
      body: request.body,
      redirect: 'follow'
    });

    // 4. 重要：Hostヘッダーのオーバーライド
    // これによりCloud RunのGFEは、このリクエストが正規のrun.app宛てであると認識します。
    newRequest.headers.set('Host', UPSTREAM_ORIGIN);

    // 5. セキュリティとトレーサビリティのためのヘッダー付与
    // バックエンドアプリが「ユーザーが実際にアクセスしたドメイン」を知るために必要です。
    newRequest.headers.set('X-Forwarded-Host', 'app.sage-base.com');

    // オリジン間認証のためのシークレットトークン（推奨されるセキュリティ強化策）
    // newRequest.headers.set('X-CF-Secret', env.OP_SECRET);

    // WebSocket接続（Upgradeヘッダー）の処理は、標準のfetch APIが自動的に処理しますが、
    // 明示的に確認することも可能です。StreamlitはWebSocketに強く依存しています。

    // 6. オリジンへのフェッチ実行
    try {
      const response = await fetch(newRequest);

      // 7. レスポンスヘッダーの処理（オプション）
      // 必要に応じてセキュリティヘッダー（HSTSなど）を追加します。
      const newResponseHeaders = new Headers(response.headers);
      newResponseHeaders.set('X-Worker-Proxy', 'Active');

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


このコードの重要なポイントは、newRequest.headers.set('Host', UPSTREAM_ORIGIN); の行です。これにより、Cloud Run側での設定変更を一切行うことなく、404エラーを解消できます。また、X-Forwarded-Host を設定することで、バックエンドのPythonアプリケーション（FastAPI/Streamlit）が正しいURL生成を行えるように配慮しています。

3.2.2 wrangler を用いたCI/CDパイプラインの構築

「GitHub Actionsで自動設定できる」という要件を満たすため、CloudflareのCLIツールである wrangler を使用したデプロイフローを構築します。これにより、インフラストラクチャの設定がコードとして管理（IaC）され、再現性が保証されます。
設定ファイル (wrangler.toml) の作成
リポジトリのルートまたは workers/ ディレクトリに配置します。

Ini, TOML


name = "sagebase-proxy"
main = "worker.js"
compatibility_date = "2025-01-01"

# ルーティング設定
# CloudflareのDNSに登録されているゾーンと一致させる必要があります。
# この設定により、app.sage-base.comへのすべてのリクエストがWorkerによって処理されます。
[[routes]]
pattern = "app.sage-base.com/*"
zone_name = "sage-base.com"

# 環境変数の設定（必要に応じて）
[vars]
ENVIRONMENT = "production"


GitHub Actions ワークフロー (.github/workflows/deploy-worker.yml)
アプリケーションのコードと同時に、プロキシロジックも更新できるようにします。

YAML


name: Deploy Cloudflare Worker

on:
  push:
    branches:
      - main
    paths:
      - 'workers/**'
      - '.github/workflows/deploy-worker.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: Deploy
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Cloudflare Workers
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          workingDirectory: 'workers'
          command: deploy



3.3 Workersアプローチのメリットとデメリット分析

機能・特性
評価
詳細分析
Hostヘッダー書き換え
✅ 解決
プログラムによる完全な制御が可能なため、UIの制限に関係なく任意のヘッダー操作が可能です。Cloud RunのデフォルトURLへのマスカレードが完璧に行えます。
コスト効率
🟡 中程度
Cloudflare WorkersのFreeプランには、1日あたり10万リクエストまでの制限があります。StreamlitアプリケーションはポーリングやWebSocketによる通信頻度が高いため（"Chatty"なアプリ）、ユーザー数が増加すると有料プラン（Workers Paid: 月額$5〜）が必要になる可能性があります。
パフォーマンス
🟢 高い
Workersは世界中のエッジロケーションで実行され、コールドスタート時間は数ミリ秒です。Pythonバックエンドの処理時間に比べれば、オーバーヘッドは無視できるレベルです。
保守・運用
🟡 中程度
新たにJavaScript/TypeScriptのコードベースを管理する必要があります。ただし、一度設定すれば変更頻度は低いです。
検証プロセス
✅ 回避
最大の利点です。Google Cloud側でのドメイン所有権検証プロセスを完全にスキップできます。Google側から見れば、アクセスは常に正規の*.run.appに対して行われているように見えるためです。


4. 代替解決策の比較検討：なぜ他の方法は失敗したのか？

ユーザーは調査過程で「Transform Rules」や「Cloud Run Domain Mapping」を試行し、壁にぶつかりました。ここでは、それらがなぜ機能しなかったのか、そして2025年のCloudflareエコシステムにおける正しい代替手段（Origin Rules）について解説します。

4.1 Transform Rules vs. Origin Rules：UIの混乱を解く

ユーザーが「Transform Rules」メニューでHostヘッダーの書き換え機能を見つけられなかったのは、Cloudflareのルールエンジンの設計思想によるものです。
Transform Rules (Request Modify): これはリクエストがCloudflareのキャッシュやWAFなどの機能によって処理される前に実行されます。主にパスの書き換え（URL Rewrite）やカスタムヘッダーの追加に使用されます。ここでHostヘッダーを変更することは、後続のSNI解決や内部ルーティングに影響を与えるため、通常は許可されていません。
Origin Rules: これはリクエストがCloudflareを離れ、オリジンサーバーに向かう直前に適用されます。ここで初めて、DNSの解決先の上書き（Resolve Override）やHostヘッダーの書き換え（Host Header Override）が可能になります。

4.2 2025年版 Cloudflare Dashboard 設定ガイド

もしユーザーがEnterpriseプラン、あるいは特定のAdd-on契約を持っている場合、コードを書かずにGUIで設定することも可能です。しかし、Free/Proプランでは制限されることが一般的です。
Cloudflareダッシュボードにログインし、対象ドメイン（sage-base.com）を選択。
左サイドメニューの Rules を展開し、Origin Rules を選択（Transform Rulesではありません）。
Create Rule をクリック。
ルール名を入力（例：Rewrite Host for Cloud Run）。
Field: Hostname, Operator: equals, Value: app.sage-base.com と設定。
Then... セクションで Host Header Override を探します。
重要: ここでテキストボックスに sagebase-streamlit-....run.app を入力します。もしこのオプションがグレーアウトしている、あるいは存在しない場合、現在のアカウントプランではこの機能がサポートされていないことを意味します。これがユーザーが「7つの選択肢」しか見つけられなかった根本原因です。

4.3 Google Cloud Run ネイティブドメインマッピングの課題

ユーザーが試みた gcloud beta run domain-mappings コマンドが失敗した理由は、ドメインの所有権検証プロセスにおける「鶏と卵」の問題です。
Googleはドメイン（app.sage-base.com）の所有権を確認するため、DNSレコード（AレコードまたはCNAME）がGoogleのインフラを指していることを要求します。
しかし、ユーザーはCloudflareのプロキシ（オレンジ色の雲アイコン）を有効にしています。これにより、DNSクエリの結果はCloudflareのIPアドレスを返します。
Googleの検証ボットはCloudflareのIPを見て、「これはGoogleのIPではない」と判断し、検証を失敗させます。
解決のためのワークフロー（DNS検証のみを利用する方法）：
この方法を採用する場合、プロキシを一時的に解除する必要はありませんが、手順が複雑です。
Webmaster Centralでの検証: app サブドメインではなく、ルートドメイン sage-base.com レベルでGoogle Search Console（旧Webmaster Central）にてTXTレコードによるDNS検証を行います。これにより、配下のすべてのサブドメインに対する権限が証明されます。
マッピングの作成: ルートドメインが検証済みであれば、gcloud コマンドによるマッピング作成が成功する可能性が高まります。
証明書のプロビジョニング問題: たとえマッピングが作成できても、Cloud Runが管理するSSL証明書（Managed Certificate）の発行には、HTTP-01チャレンジが必要です。Cloudflareがプロキシとして介入している場合、このチャレンジリクエストが正しくCloud Runに到達せず、証明書が「Provisioning」状態のままスタックするリスクがあります。
結論: Cloudflareプロキシを維持したままCloud Runのネイティブマッピングを使用することは、運用上の不安定要因（特に証明書更新時）を抱えることになります。したがって、前述のWorkersアプローチの方が、長期的な安定性と管理の容易さにおいて優れています。

5. ストリームリット（Streamlit）特有の最適化と注意点

Streamlitアプリケーションは、一般的なREST APIバックエンドとは異なり、WebSocketsを多用し、セッション状態をサーバーメモリ上に保持する特性があります。Cloudflareを介する場合、いくつかの特定の調整が必要です。

5.1 WebSocketのサポートとタイムアウト設定

CloudflareはデフォルトでWebSocketsをサポートしていますが、長時間の接続に対しては注意が必要です。
接続の切断: Cloudflareのエッジには読み取りタイムアウト（デフォルト100秒）が存在します。Streamlitアプリが長時間アイドル状態になった場合や、重い計算処理中にデータの送受信がない場合、接続が切断され、画面上に「Connection lost」が表示される原因となります。
対策: Pythonアプリケーション側で定期的に「キープアライブ」信号（ping/pong）を送信するか、Workersスクリプト内で明示的にWebSocketのハンドリングを強化する必要があります。ただし、基本的な利用においてはデフォルト設定でも多くのケースで動作します。

5.2 レスポンスバッファリングの無効化

Streamlitの特長である「順次表示（Streaming output）」を阻害しないために、Cloudflare側のバッファリング機能を無効化することが推奨されます。
設定箇所: Cloudflare Dashboard > Rules > Configuration Rules (旧Page Rules) にて、app.sage-base.com/* に対するルールを作成し、"Disable Performance" または "Cache Level: Bypass" を設定することを検討してください。これにより、エッジでの不要なキャッシュやバッファリングを防ぎ、リアルタイム性を確保できます。

5.3 _stcore パスと静的アセット

Streamlitは内部的に /_stcore/ というパスを使用してヘルスチェックや静的ファイルの配信を行います。
Workersスクリプトを作成する際、特定のパスを除外しない限りすべてのリクエストがプロキシされます。これは正しい挙動ですが、もし将来的にアクセス制限（認証など）を導入する場合、/_stcore/health などのエンドポイントがブロックされないように除外ルールを設ける必要があります。
パフォーマンス向上策: 画像やCSSなどの静的アセット（通常 static ディレクトリ配下）については、Workersでキャッシュヘッダーを操作し、Cloudflareエッジにキャッシュさせることで、Cloud Runへのリクエスト数を減らし、課金対象となるコンピュート時間と帯域幅を節約することが可能です。

6. セキュリティアーキテクチャ：ゼロトラストとオリジンロックダウン

単に接続を確立するだけでなく、本番環境（Production）としてふさわしいセキュリティレベルを確保する必要があります。現状の構成では、攻撃者がCloudflareを迂回して、Cloud RunのURL（sagebase...run.app）に直接アクセスすることが可能です。これを防ぐための設計を示します。

6.1 アプリケーション層でのシークレット検証（推奨）

Cloud RunのIngress設定を「すべてのトラフィックを許可」のままにしつつ、正当な経路（Cloudflare経由）からのアクセスのみを許可する最もシンプルな方法は、共有シークレット（Shared Secret）を用いた検証です。
実装ステップ:
Worker側: リクエストヘッダーに秘密のトークンを埋め込みます。
JavaScript
// worker.js内
newRequest.headers.set('X-CF-Secret', 'your-secure-random-token-v1');

※実際の運用では、このトークンはGitHub Secretsに保存し、デプロイ時に環境変数としてWorkerに注入します。
Cloud Run (FastAPI)側: ミドルウェアでこのヘッダーを検証します。
src/interfaces/web/streamlit/middleware/security_headers.py を拡張します。
Python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class CloudflareSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ローカル開発環境やヘルスチェックは除外
        if request.url.path == "/_stcore/health":
            return await call_next(request)

        # 本番環境での検証
        expected_token = os.getenv("CLOUDFLARE_WORKER_SECRET")
        incoming_token = request.headers.get("X-CF-Secret")

        # トークンが不一致の場合、403 Forbiddenを返す
        if expected_token and incoming_token!= expected_token:
            # ログに記録（攻撃の予兆として監視）
            print(f"Unauthorized access attempt from {request.client.host}")
            return Response("Direct access strictly forbidden.", status_code=403)

        response = await call_next(request)
        return response



6.2 Authenticated Origin Pulls (AOP)

より高度なセキュリティが必要な場合、CloudflareのAuthenticated Origin Pulls機能を使用します。これは、Cloudflareがオリジンに接続する際にクライアント証明書を提示し、オリジン側（Cloud Runの前段にロードバランサがある場合など）でその証明書を検証する相互TLS（mTLS）の仕組みです。
しかし、Cloud Run単体ではカスタムクライアント証明書の検証をネイティブにサポートしていないため、この機能をフルに活用するには前段にEnvoyプロキシやGoogle Cloud Load Balancerを配置する必要があり、構成が複雑化します。したがって、前述のアプリケーション層でのトークン検証が、コストと効果のバランスにおいて最適解となります。

7. コストとパフォーマンスの分析

各ソリューションを採用した場合のコストとパフォーマンスへの影響を比較分析します。

7.1 コストシミュレーション

項目
ソリューションA: Workers (推奨)
ソリューションB: Load Balancer (GCLB)
ソリューションC: ドメインマッピング
Cloudflare
無料 (〜10万リクエスト/日)

超過時はPaidプラン ($5/月〜)
無料
無料
Google Cloud Run
vCPU/メモリ課金 (共通)
vCPU/メモリ課金 (共通)
vCPU/メモリ課金 (共通)
Google Network
標準の下り転送料金
標準の下り転送料金
標準の下り転送料金
Google Load Balancer
$0
約 $18/月 (転送ルール + IP代)
$0
初期構築コスト
低 (Workerスクリプト作成)
中 (LB, NEG, SSL設定)
高 (DNS検証トラブル対応)
月額推定コスト
$0 〜 $5
$18 〜
$0

分析:
スタートアップや中規模のプロジェクトにとって、Google Cloud Load Balancerの固定費（約$18/月）は無視できないコストになる場合があります。Workersプランはリクエストベースの従量課金であり、スモールスタートに最適です。仮にトラフィックが急増してWorkers Paidプラン（$5/月）が必要になったとしても、GCLBより安価であり、かつDDoS対策やWAFなどの付加価値を享受できます。

7.2 パフォーマンスへの影響

レイテンシ:
Workers: Cloudflareのエッジで実行されるため、ユーザーに物理的に近い場所で処理されます。スクリプトの実行時間は通常10ms未満であり、これによる遅延は、Cloud RunのコールドスタートやPythonアプリケーションの処理時間に比べれば誤差の範囲です。むしろ、エッジでの静的アセットキャッシュを実装することで、トータルの表示速度は向上します。
Load Balancer: Googleのプレミアムネットワーク層を使用するため非常に高速ですが、Cloudflareを経由してからさらにGCLBを経由するため、ホップ数が1つ増えることになります。

8. 詳細なトラブルシューティングガイド

実装後に発生しうる一般的な問題とその解決策をまとめました。

8.1 リダイレクトループ (ERR_TOO_MANY_REDIRECTS)

症状: ブラウザでページが開かず、リダイレクトが繰り返されたというエラーが出る。
原因: CloudflareのSSL/TLS設定が「Flexible」になっている場合に多発します。Cloudflareとオリジン間がHTTP（非暗号化）で通信され、Cloud RunがHTTPSへのリダイレクトを返し、Cloudflareが再びHTTPでアクセスする無限ループです。
対策: CloudflareのSSL/TLS設定を必ず 「Full (strict)」 に設定してください。

8.2 502 Bad Gateway

症状: Cloudflareのブランド画面で502エラーが表示される。
原因1: Workerスクリプト内の UPSTREAM_ORIGIN に誤字がある。
原因2: Cloud Runサービスがダウンしている、またはコールドスタートでタイムアウト（Cloudflareのデフォルトタイムアウト100秒を超過）している。
対策: Workerのログ（wrangler tail）を確認し、オリジンへの接続エラーの詳細を特定します。Cloud Runの最小インスタンス数を1に設定してコールドスタートを回避するテストを行います。

8.3 Streamlit画面が "Please wait..." で止まる

原因: WebSocket接続が確立できていない、またはX-Forwarded-Protoヘッダーが欠落しており、Streamlitが安全なWebSocket（wss://）ではなく非安全な（ws://）接続を試みている。
対策: ブラウザの開発者ツールのConsoleを確認し、WebSocket接続エラーが出ていないか確認します。Workerコードでヘッダーを透過的に転送していることを再確認します。

9. 結論と推奨ロードマップ

本調査の結果、ユーザーが直面している「Cloudflare + Cloud Run カスタムドメイン設定における404エラーとHostヘッダー不整合」に対する最適な解決策は、Cloudflare Workersを用いたリバースプロキシパターンの導入であると結論付けられます。

推奨される実装ステップ

即時対応: 本レポートのセクション3.2で提供した worker.js コードを基に、Cloudflare Workerをデプロイしてください。これにより、Google Cloud側の設定変更を待たずに即座にサービスを公開できます。
セキュリティ強化: アプリケーションが安定稼働した後、セクション6.1の共有シークレットによる検証ロジックをFastAPIミドルウェアに追加し、オリジンへの直接アクセスを遮断してください。
自動化: wrangler 設定とGitHub Actionsワークフローをリポジトリにコミットし、将来的な変更が自動的に適用されるCI/CD環境を確立してください。
このアーキテクチャは、2025年時点でのクラウドネイティブなWebアプリケーション配信における「ベスト・オブ・ブリード（最適解の組み合わせ）」のアプローチです。Google Cloud Runの強力なコンピュート能力と、Cloudflareのプログラム可能なエッジネットワークを組み合わせることで、コスト効率、パフォーマンス、セキュリティのすべてにおいて妥協のない環境を実現できます。
