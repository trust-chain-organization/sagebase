# BI Dashboard Documentation

## 概要

Polibase BI Dashboardは、Plotly Dashを使用したデータカバレッジ可視化ツールです。全国の自治体（governing bodies）におけるデータ収集状況をインタラクティブなダッシュボードで確認できます。

### 主な機能

- **全体カバレッジ率**: 円グラフでデータ取得状況を可視化
- **組織タイプ別カバレッジ**: 国/都道府県/市町村別の棒グラフ
- **都道府県別カバレッジ**: 上位10都道府県の詳細テーブル
- **リアルタイム更新**: 更新ボタンでデータを再取得

## アーキテクチャ

### Clean Architectureでの位置づけ

```
┌─────────────────────────────────────┐
│     Interfaces Layer (UI)          │
│  ┌───────────────────────────────┐ │
│  │  BI Dashboard (Plotly Dash)   │ │
│  │  - layouts/                    │ │
│  │  - callbacks/                  │ │
│  │  - data/                       │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Application Layer (Use Cases)    │
│  - ViewGoverningBodyCoverageUseCase │
│  - ViewMeetingCoverageUseCase       │
│  - ViewSpeakerMatchingStatsUseCase  │
│  - ViewActivityTrendUseCase         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│       Domain Layer (Entities)       │
│  - GoverningBody                    │
│  - Meeting, Politician              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Infrastructure Layer (Repository)  │
│  - PostgreSQL                       │
└─────────────────────────────────────┘
```

### ディレクトリ構造

```
src/interfaces/bi_dashboard/
├── Dockerfile              # Docker設定
├── requirements.txt        # Python依存関係
├── app.py                  # Dashアプリエントリーポイント
├── layouts/
│   └── main_layout.py     # レイアウト定義
├── callbacks/
│   └── data_callbacks.py  # コールバック定義
└── data/
    └── data_loader.py     # データ取得ロジック
```

## セットアップと実行

### 前提条件

- Docker & Docker Compose
- PostgreSQL (Polibaseデータベース)

### Docker Composeでの起動

プロジェクトルートから以下のコマンドを実行：

```bash
# すべてのサービスを起動（PostgreSQL含む）
docker compose -f docker/docker-compose.yml up -d

# BI Dashboardのみを起動（既存のPostgreSQLを使用）
docker compose -f docker/docker-compose.yml up -d bi-dashboard
```

### アクセス方法

ブラウザで以下のURLにアクセス：

```
http://localhost:8050
```

### サービスの停止

```bash
# すべてのサービスを停止
docker compose -f docker/docker-compose.yml down

# BI Dashboardのみを停止
docker compose -f docker/docker-compose.yml stop bi-dashboard
```

## 使用方法

### ダッシュボードの見方

1. **サマリーカード** (上部)
   - 総自治体数: 全国の自治体総数
   - データ取得済み: データが収集されている自治体数
   - カバレッジ率: データ取得率（パーセンテージ）

2. **全体カバレッジ率** (左下)
   - 円グラフ: データあり/なしの割合を表示
   - ドーナツ型グラフで視覚的に理解しやすい

3. **組織タイプ別カバレッジ** (右下)
   - 棒グラフ: 国/都道府県/市町村別のデータ取得状況
   - 積み上げグラフでデータあり/なしを表示

4. **都道府県別カバレッジ** (中央下)
   - テーブル: 上位10都道府県のカバレッジ詳細
   - 色分け: 80%以上（緑）、50-80%（黄）、50%未満（赤）

### データの更新

画面下部の「データを更新」ボタンをクリックすると、最新のデータベース情報を取得して表示を更新します。

## 技術スタック

- **Dash 2.14.2**: Plotlyのダッシュボードフレームワーク
- **Plotly 5.18.0**: インタラクティブグラフライブラリ
- **Pandas 2.1.4**: データ処理
- **SQLAlchemy 2.0.23**: ORMとデータベース接続
- **psycopg2-binary 2.9.9**: PostgreSQLドライバ

## 開発ガイド

### ローカル開発環境

```bash
# ディレクトリに移動
cd src/interfaces/bi_dashboard

# 環境変数を設定
export DATABASE_URL=postgresql://sagebase_user:sagebase_password@localhost:5432/sagebase_db

# 依存関係をインストール
pip install -r requirements.txt

# アプリを起動
python app.py
```

### レイアウトのカスタマイズ

`layouts/main_layout.py` を編集して、ダッシュボードのレイアウトを変更できます。

```python
def create_layout() -> html.Div:
    """Create the main dashboard layout."""
    return html.Div([
        # ここにコンポーネントを追加
    ])
```

### コールバックの追加

`callbacks/data_callbacks.py` を編集して、インタラクティブ機能を追加できます。

```python
@app.callback(
    Output("output-id", "property"),
    Input("input-id", "property")
)
def callback_function(input_value):
    # コールバック処理
    return output_value
```

### データ取得ロジックの変更

`data/data_loader.py` を編集して、データ取得方法を変更できます。

```python
def load_custom_data() -> pd.DataFrame:
    """Load custom data from database."""
    engine = create_engine(get_database_url())
    query = text("SELECT ...")
    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn)
    return df
```

## トラブルシューティング

### データベース接続エラー

**症状**: `sqlalchemy.exc.OperationalError: could not connect to server`

**解決方法**:
1. PostgreSQLサービスが起動しているか確認
   ```bash
   docker compose -f docker/docker-compose.yml ps postgres
   ```
2. DATABASE_URL環境変数が正しく設定されているか確認
   ```bash
   docker compose -f docker/docker-compose.yml exec bi-dashboard env | grep DATABASE_URL
   ```

### ポート競合エラー

**症状**: `Error starting userland proxy: listen tcp4 0.0.0.0:8050: bind: address already in use`

**解決方法**:
1. ポート8050を使用しているプロセスを確認
   ```bash
   lsof -i :8050
   ```
2. プロセスを停止するか、docker-compose.ymlでポート番号を変更

### データが表示されない

**症状**: ダッシュボードは起動するがデータが表示されない

**解決方法**:
1. データベースにデータが存在するか確認
   ```bash
   docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db -c "SELECT COUNT(*) FROM governing_bodies;"
   ```
2. ブラウザの開発者ツールでJavaScriptエラーを確認
3. コンテナログを確認
   ```bash
   docker compose -f docker/docker-compose.yml logs bi-dashboard
   ```

## 今後の拡張計画

1. **Clean Architecture統合**: Repository経由でのデータ取得に変更
2. **機能拡張**:
   - 日本地図可視化（Folium統合）
   - 時系列データ表示
   - フィルタリング機能
   - エクスポート機能（CSV/Excel）
3. **テスト作成**: ユニットテストとインテグレーションテスト
4. **認証機能**: ユーザー認証とアクセス制御

## 参考資料

- [Plotly Dash公式ドキュメント](https://dash.plotly.com/)
- [Plotly Graph Objects](https://plotly.com/python/graph-objects/)
- [SQLAlchemy公式ドキュメント](https://docs.sqlalchemy.org/)
- [BIツール評価結果](../tmp/bi_tool_evaluation_20251102.md)
