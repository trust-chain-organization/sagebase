Cloudflare Pages プレビューデプロイメントのライフサイクル管理：現状の仕様分析と自動クリーンアップ戦略の徹底解説


エグゼクティブ・サマリー：Cloudflare Pages プレビューデプロイメントのライフサイクル管理と自動化戦略

本レポートは、Cloudflare Pagesのプレビューデプロイメントの管理に関するユーザーの具体的な疑問に回答し、その背景にある技術的仕様と、現状で最適解となる自動化戦略を提示するものです。
まず、ユーザーの2つの主要な疑問に対して、明確かつ直接的な回答を提示します。
「GitHubでブランチを削除してもプレビューデプロイメントは削除されない」という過去の情報は現在も有効か？
回答：はい、有効です。 2024年現在も、GitHubリポジトリでブランチを削除（またはプルリクエストをマージ/クローズ）しても、それに関連するCloudflare Pagesのプレビューデプロイメントおよびブランチエイリアス（例: feature-x.project.pages.dev）は自動的に削除されません 1。これは、2021年頃 1 からコミュニティで一貫して報告され続けており 4、仕様として現在も変更されていません。
ブランチマージ時にプレビュー環境を自動削除する「組み込み機能」はCloudflareに存在するか？
回答：いいえ、存在しません。 Cloudflare Pagesのダッシュボードやwrangler.toml設定ファイルには、マージやブランチ削除をトリガーとしてプレビュー環境を自動的にクリーンアップする組み込み機能は提供されていません 6。
この仕様は、デプロイメントの「陳腐化（Clutter）」10 を引き起こすだけでなく、古いプレビューに機密情報や不正確な情報が残存するセキュリティリスク 5 や、デプロイメント数が数千件に達した場合にプロジェクト自体の削除がAPI経由で不可能になるという深刻な運用リスク 11 に直結します。
したがって、本レポートでは、この問題の技術的根本原因である「アトミックデプロイメントとエイリアスの分離」12 を分析し、唯一の実践的ソリューションであるCloudflare API 1 とGitHub Actions 13 を組み合わせた、pull_request: closed イベントをトリガーとする自動クリーンアップワークフローの構築方法を詳細に解説します。

第1章：Cloudflare Pages プレビューデプロイメントの永続性に関する技術的詳細

Cloudflare Pagesのプレビューデプロイメントが自動削除されない現象は、バグではなく、そのアーキテクチャの根幹に起因する仕様です。この章では、問題の根本原因を技術的に分析します。

1.1. プレビューデプロイメントの生成プロセス

Cloudflare Pagesは、Gitプロバイダ（GitHubまたはGitLab）と深く統合されています 14。プレビューデプロイメントは、以下の2つの主要なアクションによって自動的にトリガーされます。
プルリクエスト（PR）のオープン: GitHubリポジトリで新しいプルリクエストがオープンされると、Cloudflare Pagesは即座にビルドプロセスを開始し、そのPR専用のユニークなプレビューURLを生成します 12。
非本番ブランチへのプッシュ: プロダクションブランチ（例: main）以外として設定されたブランチ 6 に新しいコミットがプッシュされると、同様にプレビューデプロイメントが生成されます 12。
このシームレスな統合 14 は開発速度を向上させる一方で、クリーンアップの責務を開発者側に残す結果となっています。

1.2. 核心：「アトミックデプロイメント」と「ブランチエイリアス」

この問題を理解する鍵は、Cloudflare Pagesが2種類のデプロイメントURLを管理している点にあります 12。
アトミックデプロイメント（Atomic Deployment）:
373f31e2.user-example.pages.dev のような、ランダムなハッシュ値に基づいたユニークなURLです 12。
これは、特定の1コミットのスナップショット（Immutable Snapshot）です。
公式ドキュメント 12 には「これらはアトミックであり、将来にわたって常に訪問可能である（may always be visited in the future）」と明記されています。この**永続性（Permanence）**こそが、Jamstackアーキテクチャの核心的な特徴の一つです。
ブランチエイリアス（Branch Alias）:
development.user-example.pages.dev のような、Gitのブランチ名に基づいた、人間が判読可能なURLです 12。
このエイリアスは、単なる「ポインタ」です。12 が示す通り、このエイリアスは「常にそのブランチの最新のコミット（のアトミックデプロイメント）を指すように更新され続けます」。

1.3. 現状の仕様（2024年以降）：自動削除機能の不在

ユーザーの疑問（「仕様は変わったか？」）に対する答えは、コミュニティと公式ドキュメントの時系列分析によって明確になります。
技術的根本原因の分析: CloudflareのGit統合は、Webhookの「受信」にのみ特化しています。push や pull_request の opened / synchronize イベントをリッスンしてデプロイメントを「作成」することはできます 14。しかし、GitHubが送信する pull_request の closed イベントや branch の deleted イベントをリッスンして、対応するデプロイメントやエイリアスを「削除」するロジックが、Cloudflare Pagesのプラットフォーム側に実装されていません。
証拠（時系列）：
2021年: ユーザーがこの問題を活発に報告し始めました。「GitHubリポジトリからブランチを削除しても、CF Pagesは同期せず、エイリアスが永遠に表示されるのか？ これは非常識だ」1。「dependabotによって作成されたブランチを削除したいが、ダッシュボードではエイリアスに割り当てられているため削除できない」1。
2021年10月: Cloudflareスタッフが、API経由での強制削除コマンド（後述）をコミュニティで共有し、「UIは近日公開 (UI coming soon)」とコメントしました 1。
2022年: コミュニティメンバーが「一度にすべての古いデプロイメントを削除することはできません。APIを使う必要がある」と確認しています 15。また、公式のcloudflare/pages-action 16 に対しても、PRクローズ時の自動削除機能の要望がIssueとして起票されましたが 2、実装には至っていません。
2024年: 3ヶ月前のRedditスレッドでも「（自動削除は）されません。しかし、自動化することは可能です」と、依然としてサードパーティのスクリプト 4 が解決策として提示されています。
2024年10月: 「約3000のデプロイメントがあり、APIを使おうとしているが...」という、問題の深刻さを示す投稿があります 5。
導き出される結論：
第1階層の分析: ユーザーの懸念通り、プレビューデプロイメントは自動削除されません。
第2階層の分析: 2021年に示唆された「UI coming soon」1 は、少なくとも「自動クリーンアップ機能」としては実現しませんでした。Cloudflareの公式機能は、デプロイメントの「作成」12 や「アクセス制御」12 に重点が置かれ、「クリーンアップ（ライフサイクル管理）」は開発者の責務範囲とされています。
第3階層の分析: この仕様は、「アトミックデプロイメントは不変」12 という設計思想の副産物です。ブランチを削除しても、過去のコミット（アトミックデプロイメント）の履歴は参照可能であるべき、という思想です。問題は、「エイリアス」までが永続化されてしまう点にあります。この「エイリアス」を削除する仕組みが、API経由の能動的なアクション以外に存在しないのです。

1.4. 問題の影響：デプロイメントの陳 buddha 化と運用リスク

この仕様がもたらす問題は、単なる「不便さ」を超え、具体的な「運用リスク」に発展します。
管理の煩雑化: 大量のアクティブでないプレビューがダッシュボードを埋め尽くし、管理を非効率にします 10。
セキュリティと信頼性のリスク: 開発中の（あるいはバグを含んだ）古いプレビューが公開され続けることで、不正確な情報が外部からアクセス可能な状態になります 5。
プラットフォームのロックイン（最悪のケース）: デプロイメント数が数千、数万に達すると、プロジェクト自体の削除が不可能になるという致命的なエラーが報告されています 11。あるユーザーは「デプロイメントが多すぎるため、プロジェクトを削除できません (Your project has too many deployments to be deleted.)」というAPIエラー (code: 8000076) に直面し、手動での削除もできなくなりました 11。
因果関係の分析:
デプロイメントの放置（第1段階） → ダッシュボードの陳腐化 10（第2段階） → APIによる手動クリーンアップの試行 5（第3段階） → デプロイメント数の累積によるプラットフォーム制限への到達 → プロジェクト削除不可 11（最終段階）。
このように、自動クリーンアップ戦略の欠如は、単なる「技術的負債」ではなく、将来的にプロジェクトを修復不可能な状態に陥れる「運用上の時限爆弾」であると言えます。

第2章：手動およびAPIによるデプロイメント削除の実行

自動化ソリューションを構築する前に、デプロイメントを削除する「手動」および「API」のメカニズムを理解することが不可欠です。特にAPIの仕様は、自動化の鍵となります。

2.1. ダッシュボードによる手動削除の限界

Cloudflareダッシュボードからデプロイメントを個別に削除することは可能です 15。しかし、このアプローチには深刻な限界があります。
一括削除の欠如: デプロイメントは1件ずつしか削除できません 15。
確認プロセスの煩雑さ: 10 の報告によれば、各デプロイメントの削除には確認ダイアログが表示され、さらにそのデプロイメントが「エイリアス」を持っている場合、削除のためにエイリアス名（ブランチ名）の入力を求められます。
スケーラビリティの欠如: 5 のユーザーのように3000件のデプロイメント履歴がある場合、UIをスクロールして目的のデプロイメントを探し出し、1件ずつ削除することは非現実的です。

2.2. Cloudflare APIによる直接操作（自動化の基盤）

唯一スケーラブルな削除方法は、Cloudflare APIを直接利用することです。
ステップ1：認証の準備
Cloudflare APIトークンが必要です。このトークンには「Cloudflare Pages:Edit」権限が必須です 17。
ステップ2：デプロイメントIDの特定
削除には、まず GET /client/v4/accounts/{account_id}/pages/projects/{project_name}/deployments エンドポイントを呼び出し、削除対象のブランチ名（例: github.head_ref）に関連するデプロイメントのIDを特定する必要があります 5。
ステップ3：削除の実行と「エイリアスの罠」
DELETE /client/v4/accounts/{account_id}/pages/projects/{project_name}/deployments/{deployment_id} エンドポイントを使用します。
技術的障壁の分析（最重要）： もし削除対象のデプロイメントがブランチエイリアス（例: dependabot-patch-1.project.pages.dev）に紐付いている場合、単純なDELETEリクエストは失敗します 1。
APIは以下のエラーを返します 1：
JSON
{
  "success": false,
  "errors": [
    { "code": 8000035, "message": "Cannot delete aliased deployment without?force=true" }
  ]
}


解決策: エラーメッセージが示す通り、クエリパラメータ ?force=true を付与してリクエストを再送信する必要があります 1。
Bash
curl -X DELETE "https://api.cloudflare.com/client/v4/accounts/<account-id>/pages/projects/<project-name>/deployments/<deployment-id>?force=true" \
     -H "Authorization: Bearer <api-token>"


技術的分析:
この ?force=true パラメータこそが、自動化の鍵です。これは「エイリアスされたデプロイメント」を削除できないというダッシュボード上の制約 1 を、APIレベルでバイパスする唯一の手段です。このパラメータは、Cloudflareに対し「このデプロイメントに紐付いているブランチエイリアス（ポインタ）を解除し、デプロイメント本体（アトミックデプロイメント）を削除する」ことを強制します。

2.3. 【参照テーブル】主要Cloudflare Pages APIエンドポイント

自動クリーンアップスクリプトの構築に必要な主要APIオペレーションを以下にまとめます。

HTTPメソッド
エンドポイント（短縮形）
目的と解説
必須パラメータ/権限
GET
.../deployments
プロジェクトの全デプロイメントを一覧取得する。env=preview 5 やブランチ名でフィルタリングし、削除対象のIDを特定するために使用する。
Pages:Read
DELETE
.../deployments/{deployment_id}
特定のデプロイメントを削除する。ただし、エイリアスに紐付いている場合は失敗する 1。
Pages:Edit
DELETE
.../deployments/{deployment_id}?force=true
自動化の鍵。 エイリアスに紐付いたデプロイメントを強制的に削除する 1。ブランチエイリアスごとクリーンアップするために必須。
Pages:Edit


第3章：【実践的ソリューション】GitHub Actionsによるプレビュー環境の自動クリーンアップ

Cloudflare側に組み込み機能が存在しない以上、CI/CDパイプライン側で能動的にクリーンアップ処理を実装する必要があります。GitHub Actionsは、このタスクに最適です。

3.1. 自動化のアーキテクチャ：pull_request: closed トリガー

ユーザーの要求（「ブランチをマージしたら削除する」）を満たす理想的な自動化アーキテクチャは、GitHub Actionsの pull_request イベントをトリガーとすることです。
トリガーイベント: on: pull_request: types: [closed] 13。
この closed タイプは、プルリクエストがマージされた時と、マージされずにクローズされた時の両方で発火します。これは、不要になったプレビュー環境をクリーンアップする上で完璧なタイミングです 13。
実行ロジック:
ワークフローが pull_request: closed でトリガーされます。
ワークフローは、クローズされたPRのブランチ名（github.head_ref）を取得します 13。
Cloudflare API 17 を使用して、APIトークン (secrets.CLOUDFLARE_API_TOKEN) で認証します。
API 1 を呼び出し、取得したブランチ名に紐づくデプロイメントを ?force=true 付きで削除します。

3.2. ソリューションA：コミュニティ提供のGitHub Actionの活用（推奨）

このロジックを自前で実装する（curl や jq を使う）19 必要はなく、このタスク専用にコミュニティが開発した優れたGitHub Actionを利用するのが最も効率的です。
推奨Action: go-fjords/cloudflare-delete-deployments-action 13。
このActionは、まさにpull_request: closed イベントでブランチのデプロイメントを削除するためだけに設計されています。
導入ステップと完全なYAMLサンプル:
APIトークンの設定:
CloudflareダッシュボードでAPIトークンを生成します 17。権限は「Account」>「Cloudflare Pages」>「Edit」 17 を選択します。
GitHubリポジトリの Settings > Secrets and variables > Actions に、CLOUDFLARE_API_TOKEN という名前で生成したトークンを保存します。
CloudflareのアカウントID (CLOUDFLARE_ACCOUNT_ID) も同様にシークレットとして保存します 17。
ワークフローファイルの作成:
.github/workflows/cleanup-previews.yml という名前で以下のファイルを作成します。
YAML
#.github/workflows/cleanup-previews.yml
#  のサンプルに基づく、PRクローズ時にプレビューを削除するワークフロー

name: Cleanup Cloudflare Previews

on:
  pull_request:
    types:
      - closed # PRがマージまたはクローズされた時に実行

# の 'concurrency' 設定は、同一PRでの重複実行を防ぐために有効
concurrency:
  group: pr_cleanup_${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  delete-cloudflare-preview:
    name: Delete Cloudflare Preview Deployment
    runs-on: ubuntu-latest
    steps:
      - name: Delete Cloudflare Pages Deployment
        #  で参照されているコミュニティActionを使用
        uses: go-fjords/cloudflare-delete-deployments-action@main
        with:
          # GitHubシークレットからCloudflare APIトークンを読み込む
          token: ${{ secrets.CLOUDFLARE_API_TOKEN }}

          # GitHubシークレットからCloudflareアカウントIDを読み込む
          account: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}

          # あなたのCloudflare Pagesプロジェクト名
          project: 'your-pages-project-name'

          # クローズされたPRのブランチ名を動的に取得
          branch: ${{ github.head_ref }}


代替Action: eve0415/cf-pages-clean-deployments-action 21 も存在します。これは、cloudflare/pages-action 16 と組み合わせて使用し、delete イベント（ブランチ削除）をトリガーにしたり、古いプレビュー全般をクリーンアップしたりすることを目的としています 21。pull_request: closed に特化した go-fjords の方が、今回のユースケースにはより直接的です。

3.3. 公式pages-actionの限界とカスタム実装

公式Actionの限界: Cloudflare公式が提供する cloudflare/pages-action 16 は、あくまでデプロイメントの実行（wrangler pages deploy） 17 を目的としています。
分析: 2 や 2 で報告されている通り、多くの開発者がこの公式Actionにクリーンアップ機能（pr: closed での削除）を期待しましたが、2024年現在も実装されていません。これは、Cloudflareがデプロイメントのライフサイクル管理をプラットフォームの責務ではなく、ユーザーのCI/CDパイプラインの責務と位置づけていることを強く示唆しています。
カスタムスクリプトによる実装:
22 は、wrangler を使用して、クリーンアップロジックを持つ 別のCloudflare Worker をデプロイし、それを cron スケジュールで定期実行するという、より高度なバッチ処理アプローチを示しています。
19 は、GitHub Actions内で直接シェルスクリプトを実行し、APIを叩くアプローチを示しています。
パターン分析: 自動化には2つのパターンが存在します。
イベント駆動型（推奨）： pull_request: closed 13。即時性があり、クリーンアップ対象が明確。ユーザーの要求に最も近い。
バッチ（スケジュール）型: schedule: cron 22。イベント駆動型で漏れたデプロイメント（例: 手動でブランチを削除した場合など）を定期的に掃除する「ガベージコレクタ」として有効。

3.4. 【参照テーブル】自動化ソリューションの比較


アクション / 手法
主なトリガー
主な機能
セットアップ
ユースケース
cloudflare/pages-action 16
push
デプロイ
容易
新規・本番デプロイ。削除機能なし。
go-fjords/cloudflare-delete-deployments-action 13
pull_request: closed
PRブランチの削除
容易
PRマージ/クローズ時の自動クリーンアップ。
eve0415/cf-pages-clean-deployments-action 21
delete (ブランチ削除)
古いプレビューの削除
中
ブランチ削除時、またはデプロイ後の汎用クリーンアップ。
カスタムCron Worker 10
schedule
全デプロイメントの棚卸し
難
定期的なバッチ処理による「ガベージコレクション」。


第4章：補足：デプロイメントの「防止」と「管理」

クリーンアップ（事後対応）だけでなく、不要なデプロイメントの「防止」（事前対応）と、既存デプロイメントの「管理」を組み合わせることで、より堅牢なワークフローが完成します。

4.1. ブランチビルドコントロールによる「防止」

Cloudflare Pagesには、そもそもどのブランチがプレビューデプロイメントをトリガーするかを制御する機能が組み込まれています。
機能: Settings > Builds & deployments > Configure Production deployments 6 および、プレビューブランチの制御 6。
設定オプション 6:
All non-Production branches (デフォルト): すべての非本番ブランチでビルドが実行されます。
None: プレビュービルドをすべて無効化します 23。
Custom branches: 特定のブランチパターンを「含める」または「除外する」設定が可能です 7。
実践的アドバイス:
3 や 1 で問題となっていた dependabot ブランチのように、プレビューが不要なブランチが明確なパターン（例: dependabot/**, renovate/**）を持つ場合、この「Custom branches」設定でそれらを**除外（Exclude）**することが、クリーンアップの負荷を軽減する最も効果的な「第一の防御線」となります。

4.2. コミットメッセージによるビルドのスキップ

Cloudflare PagesのGit統合は、コミットメッセージに基づくビルドのスキップをサポートしています 14。CI/CDの一般的な慣習である [ci skip] や [skip ci] といった文字列をコミットメッセージに含めることで、ドキュメントのタイポ修正など、プレビューが不要なコミットでのビルド実行を抑制できます。

4.3. プレビューへのアクセス制御による「リスク軽減」

デプロイメントを削除する代わりに、それらを非公開にすることでリスクを管理する方法もあります。
機能: Settings > General > Enable access policy 12。
効果: この設定を有効にすると、*.pages.dev のプレビューデプロイメント（373f31e2.project.pages.dev など）へのアクセスが、Cloudflare Access（Zero Trust）ポリシーによって保護されます。
分析: これは、5 で懸念された「（古いプレビューに）悪い情報が含まれている」問題に対する直接的なリスク軽減策です。クリーンアップ（第3章）が「デプロイメントゴミ」そのものを削除するのに対し、アクセス制御は「ゴミが外部から見える」リスクを軽減します。両者は排他的ではなく、併用すべき戦略です。

第5章：結論と推奨ワークフロー

本レポートは、Cloudflare Pagesのプレビューデプロイメントが、ブランチの削除やマージによって自動的にはクリーンアップされない仕様（2024年現在も有効）であることを確認しました。この仕様は、Jamstackの「不変なアトミックデプロイメント」12 という設計思想に起因しますが、結果としてデプロイメントの陳腐化 10 や、最悪の場合プロジェクトの管理不能 11 といった運用リスクをもたらします。
Cloudflare側に組み込みの自動削除機能は存在しないため、開発者はCI/CDプロセスにおいて能動的なクリーンアップ戦略を導入する必要があります。

5.1. 推奨される「多層防御」ワークフロー

最も堅牢なソリューションは、単一のツールに依存するのではなく、以下の4つのレイヤーを組み合わせた多層的なアプローチです。
レイヤー1：防止（Prevent）
アクション: Cloudflareダッシュボードの「ブランチビルドコントロール」6 を設定します。
目的: dependabot/** のような、プレビューが不要なブランチを「除外」リストに追加し、不要なデプロイメントの生成を未然に防ぎます。
レイヤー2：削除（Delete） - イベント駆動型
アクション: 第3章で解説したGitHub Action (go-fjords/cloudflare-delete-deployments-action 13) を導入します。
目的: pull_request: closed イベントをトリガーに、マージまたはクローズされたPRのプレビュー環境（エイリアスとデプロイメント）を即時に自動削除します。これがクリーンアップ戦略の核となります。
レイヤー3：軽減（Mitigate）
アクション: Cloudflareダッシュボードで「アクセス制御（Access Policy）」12 を有効にします。
目的: レイヤー1および2で処理しきれなかったアクティブなプレビュー、または意図的に残しているプレビューへの一般アクセスをブロックし、5 で指摘されたような情報漏洩リスクを軽減します。
レイヤー4：収集（Garbage Collect） - バッチ型（オプション）
アクション: カスタムスクリプト 10 やスケジュール実行のWorker 22 を導入します。
目的: pull_request: closed イベント（レイヤー2）では捕捉できない孤立したデプロイメント（例: PRを経由せずに作成され、手動でブランチが削除されたもの）を、「30日以上更新がないプレビューを削除する」といったルールで定期的に棚卸し・削除します。
この多層的なアプローチを採用することで、Cloudflare Pagesの強力なプレビュー機能を享受しつつ、それに伴うデプロイメントの陳腐化と運用リスクを体系的に管理することが可能になります。
引用文献
How to Delete Aliased Preview Deployments? - Cloudflare Community, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/how-to-delete-aliased-preview-deployments/269292
Ability to delete preview site when pr is closed · Issue #47 · cloudflare/pages-action - GitHub, 11月 16, 2025にアクセス、 https://github.com/cloudflare/pages-action/issues/47
How to Delete Aliased Preview Deployments? - #4 by crtyk - Cloudflare Pages, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/how-to-delete-aliased-preview-deployments/269292/4
[Cloudflare Pages] Are old deployments ever automatically deleted? - Reddit, 11月 16, 2025にアクセス、 https://www.reddit.com/r/CloudFlare/comments/1aeyjzl/cloudflare_pages_are_old_deployments_ever/
Delete an old preview deployment without the deployment ID - Cloudflare Community, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/delete-an-old-preview-deployment-without-the-deployment-id/730502
Branch deployment controls · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/configuration/branch-build-controls/
GitHub integration · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/
Configuration · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/functions/wrangler-configuration/
Configuration - Wrangler · Cloudflare Workers docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/workers/wrangler/configuration/
Cleaning up Obsolete Cloudflare Page Deployments | Blog | Maxim Radugin, 11月 16, 2025にアクセス、 https://radugin.com/posts/2024-04-28/cloudflare-cleanup-page-deployments/
Unable to delete Pages projects due to “too many deployments” error, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/unable-to-delete-pages-projects-due-to-too-many-deployments-error/846036
Preview deployments · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/configuration/preview-deployments/
Cloudflare Delete Deployments Action - GitHub Marketplace, 11月 16, 2025にアクセス、 https://github.com/marketplace/actions/cloudflare-delete-deployments-action
Git integration · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/configuration/git-integration/
Delete Cloudlfare Pages deployments - Getting Started - Cloudflare Community, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/delete-cloudlfare-pages-deployments/345640
GitHub Action for Cloudflare Pages - GitHub Marketplace, 11月 16, 2025にアクセス、 https://github.com/marketplace/actions/github-action-for-cloudflare-pages
Use Direct Upload with continuous integration · Cloudflare Pages docs, 11月 16, 2025にアクセス、 https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/
mass delete cloudflare pages deployments - Stack Overflow, 11月 16, 2025にアクセス、 https://stackoverflow.com/questions/79606336/mass-delete-cloudflare-pages-deployments
A Neon branch for every Cloudflare Preview Deployment - GitHub, 11月 16, 2025にアクセス、 https://github.com/neondatabase/preview-branches-with-cloudflare
Automate all the things (like Cloudflare cache purge) with Github actions, Postman and APIs, 11月 16, 2025にアクセス、 https://apihandyman.io/automate-all-the-things-with-github-actions-postman-and-apis/
CloudFlare Pages Clean Deployment Action - GitHub Marketplace, 11月 16, 2025にアクセス、 https://github.com/marketplace/actions/cloudflare-pages-clean-deployment-action
Ergberg/cloudflare-pages-cleanup: Cloudflare worker that automatically deletes old deployments at Cloudflare Pages. - GitHub, 11月 16, 2025にアクセス、 https://github.com/Ergberg/cloudflare-pages-cleanup
How to remove staging/preview environment and its URL from Cloudflare? - Reddit, 11月 16, 2025にアクセス、 https://www.reddit.com/r/CloudFlare/comments/17ocriq/how_to_remove_stagingpreview_environment_and_its/
Disable Preview Publishing on Pages - Cloudflare Community, 11月 16, 2025にアクセス、 https://community.cloudflare.com/t/disable-preview-publishing-on-pages/252329
