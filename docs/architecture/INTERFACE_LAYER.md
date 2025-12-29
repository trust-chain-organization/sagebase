# Interface Layer（インターフェース層）

## 目次

1. [層の責務と境界](#層の責務と境界)
2. [CLIコマンド](#cliコマンド)
3. [Streamlit UI](#streamlit-ui)
4. [プレゼンターパターン](#プレゼンターパターン)
5. [よくある落とし穴と回避方法](#よくある落とし穴と回避方法)
6. [チェックリスト](#チェックリスト)
7. [参考資料](#参考資料)

---

## 層の責務と境界

### 責務

Interface層は、ユーザーとシステムの接点であり、すべての入出力を担当します：

- **ユーザーインターフェースの提供**: CLI、Web UI（Streamlit）など
- **エントリーポイント**: アプリケーションへのアクセスポイント
- **入出力の変換**: ユーザー入力をDTOに変換、DTOをユーザーフレンドリーな形式に変換
- **セッション管理**: UI状態やユーザーセッションの管理

### 境界

Interface層は**最も外側の層**であり、ユーザーとの接点です：

```
User → Interface ← Application ← Domain
```

**依存関係のルール**:
- **Interface層がApplication層に依存**: ユースケースを呼び出す
- **Interface層がDomain層に依存することもある**: エンティティやDTOを表示
- **Application層やDomain層がInterface層に依存してはならない**: 依存性逆転の原則

### ディレクトリ構造

```
src/interfaces/
├── cli/                       # CLIインターフェース
│   ├── base.py               # ベースコマンドクラス
│   ├── commands/             # 個別コマンド
│   │   ├── politician_commands.py
│   │   ├── minutes_commands.py
│   │   └── ...
│   └── progress.py           # プログレス表示ユーティリティ
├── web/
│   └── streamlit/            # Streamlit UIインターフェース
│       ├── views/            # ビュー（UI表示）
│       │   ├── politicians_view.py
│       │   ├── conferences_view.py
│       │   └── ...
│       ├── presenters/       # プレゼンター（UIロジック）
│       │   ├── base.py       # ベースプレゼンター
│       │   ├── politician_presenter.py
│       │   └── ...
│       ├── components/       # 再利用可能UIコンポーネント
│       │   ├── header.py
│       │   └── analytics.py
│       └── utils/            # ユーティリティ
│           └── session_manager.py
└── factories/                # ファクトリー（依存性注入）
    └── ...
```

---

## CLIコマンド

SagebaseのCLIは、Clickフレームワークを使用して実装されています。すべてのCLIコマンドは`sagebase`コマンドの下にサブコマンドとして配置されます。

### Clickフレームワークの使用

Clickは、Pythonで宣言的なCLIを構築するためのフレームワークです。

#### コマンド構造

```python
# src/interfaces/cli/commands/politician_commands.py

import asyncio
import click
from ..base import BaseCommand, with_error_handling


class PoliticianCommands(BaseCommand):
    """Commands for processing politician data"""

    @staticmethod
    @click.command()
    @click.option("--party-id", type=int, help="Specific party ID to scrape")
    @click.option(
        "--all-parties", is_flag=True, help="Scrape all parties with member list URLs"
    )
    @click.option(
        "--dry-run", is_flag=True, help="Show what would be scraped without saving"
    )
    @click.option("--max-pages", default=10, help="Maximum pages to fetch per party")
    @with_error_handling
    def scrape_politicians(
        party_id: int | None,
        all_parties: bool,
        dry_run: bool,
        max_pages: int,
    ):
        """Scrape politician data from party member list pages (政党議員一覧取得)

        This command fetches politician information from political party websites
        using LLM to extract structured data and saves them to the database.

        Examples:
            sagebase scrape-politicians --party-id 1
            sagebase scrape-politicians --all-parties
            sagebase scrape-politicians --all-parties --dry-run
        """
        # Run the async scraping operation
        asyncio.run(
            PoliticianCommands._async_scrape_politicians(
                party_id, all_parties, dry_run, max_pages
            )
        )

    @staticmethod
    async def _async_scrape_politicians(
        party_id: int | None,
        all_parties: bool,
        dry_run: bool,
        max_pages: int,
    ):
        """Async implementation of scrape_politicians"""
        # ユースケースを呼び出す
        from src.infrastructure.di.container import Container

        container = Container.create_for_environment()
        use_case = container.get_politician_scraping_usecase()

        result = await use_case.scrape_politicians(
            party_id=party_id,
            all_parties=all_parties,
            dry_run=dry_run,
            max_pages=max_pages,
        )

        # 結果を表示
        if result.success:
            click.echo(f"✅ Successfully scraped {result.total_scraped} politicians")
        else:
            click.echo(f"❌ Scraping failed: {result.error_message}", err=True)
```

**実装のポイント**:

1. **`@click.command()` デコレーター**: 関数をCLIコマンドとして登録
2. **`@click.option()` デコレーター**: コマンドラインオプションを定義
   - `type`: オプションの型（int, str, boolなど）
   - `help`: ヘルプメッセージ
   - `is_flag`: フラグ（真偽値）として扱う
   - `default`: デフォルト値
3. **`@with_error_handling` デコレーター**: エラーハンドリングを統一
4. **非同期処理**: `asyncio.run()`でユースケースを実行

### BaseCommand パターン

すべてのコマンドクラスは`BaseCommand`を継承します：

```python
# src/interfaces/cli/base.py

from abc import ABC
from functools import wraps
import click


class BaseCommand(ABC):
    """Base class for CLI commands."""

    pass


def with_error_handling(func):
    """Decorator to add consistent error handling to commands."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            click.echo(f"❌ Error: {str(e)}", err=True)
            raise click.Abort()

    return wrapper
```

### 依存性注入のセットアップ

CLIコマンドでは、DIコンテナを使用してユースケースや依存関係を取得します：

```python
from src.infrastructure.di.container import Container

# コンテナの作成
container = Container.create_for_environment()

# ユースケースの取得
use_case = container.get_politician_scraping_usecase()

# ユースケースの実行
result = await use_case.scrape_politicians(...)
```

**重要なポイント**:
- コマンド内でリポジトリを直接インスタンス化しない
- DIコンテナを使用して依存関係を解決
- テスト時にモックに差し替え可能

### プログレス表示

長時間実行されるコマンドには、プログレス表示を追加します：

```python
# src/interfaces/cli/progress.py

from contextlib import contextmanager
import click


@contextmanager
def spinner(message: str):
    """Show a spinner with a message."""
    with click.progressbar(
        length=100,
        label=message,
        show_eta=False,
        show_percent=False,
    ) as bar:
        yield bar


# 使用例
with spinner("政治家データを取得中..."):
    result = await use_case.scrape_politicians(...)
```

---

## Streamlit UI

Sagebaseは、Streamlitを使用してWebベースの管理画面を提供しています。StreamlitはPythonでインタラクティブなWebアプリケーションを簡単に構築できるフレームワークです。

### MVP（Model-View-Presenter）パターン

Streamlit UIは**MVPパターン**を採用しています：

```
User → View ← Presenter → UseCase (Application Layer)
```

| コンポーネント | 役割 |
|--------------|------|
| **View** | UI表示（Streamlitウィジェット） |
| **Presenter** | UIロジック、ユースケース呼び出し、データ変換 |
| **Model** | ドメインエンティティ、DTO（Domain/Application層） |

### ビュー（View）の実装

ビューは、Streamlitウィジェットを使用してUIを構築します。

#### 実装例: politicians_view.py

```python
# src/interfaces/web/streamlit/views/politicians_view.py

import streamlit as st
from src.interfaces.web.streamlit.presenters.politician_presenter import (
    PoliticianPresenter,
)


def render_politicians_page() -> None:
    """Render the politicians management page."""
    st.header("政治家管理")
    st.markdown("政治家の情報を管理します")

    # プレゼンターの初期化
    presenter = PoliticianPresenter()

    # タブの作成
    tabs = st.tabs(["政治家一覧", "新規登録", "編集・削除", "重複統合"])

    with tabs[0]:
        render_politicians_list_tab(presenter)

    with tabs[1]:
        render_new_politician_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_merge_tab(presenter)


def render_politicians_list_tab(presenter: PoliticianPresenter) -> None:
    """Render the politicians list tab."""
    st.subheader("政治家一覧")

    # 政党でフィルタ
    parties = presenter.get_all_parties()
    col1, col2 = st.columns(2)

    with col1:
        party_options = ["すべて"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("政党でフィルタ", party_options)

    with col2:
        search_name = st.text_input("名前で検索", placeholder="例: 山田")

    # データの読み込み
    party_id = party_map.get(selected_party) if selected_party != "すべて" else None
    politicians = presenter.load_politicians_with_filters(
        party_id, search_name if search_name else None
    )

    if politicians:
        # DataFrameで表示
        df = presenter.to_dataframe(politicians, parties)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # 統計情報
        st.markdown("### 統計情報")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("総数", len(politicians))
        with col2:
            party_count = len(set(p.party_id for p in politicians if p.party_id))
            st.metric("政党数", party_count)
    else:
        st.info("該当する政治家が見つかりませんでした")


def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    """Render the new politician registration tab."""
    st.subheader("新規政治家登録")

    with st.form("new_politician_form"):
        name = st.text_input("氏名 *", placeholder="山田太郎")
        name_furigana = st.text_input("ふりがな", placeholder="やまだたろう")

        # 政党選択
        parties = presenter.get_all_parties()
        party_options = ["なし"] + [p.name for p in parties]
        party_map = {p.name: p.id for p in parties}
        selected_party = st.selectbox("政党", party_options)

        district = st.text_input("選挙区", placeholder="東京都第1区")
        bio = st.text_area("経歴", placeholder="略歴を入力...")

        submitted = st.form_submit_button("登録")

        if submitted:
            if not name:
                st.error("氏名は必須です")
            else:
                # プレゼンター経由で登録
                party_id = party_map.get(selected_party) if selected_party != "なし" else None
                result = presenter.create_politician(
                    name=name,
                    name_furigana=name_furigana,
                    party_id=party_id,
                    district=district,
                    bio=bio,
                )

                if result.success:
                    st.success(f"✅ 政治家を登録しました（ID: {result.politician_id}）")
                    st.rerun()  # ページをリロード
                else:
                    st.error(f"❌ 登録に失敗しました: {result.error_message}")
```

**ビュー実装のポイント**:

1. **Presenterのみを呼び出す**: ビューはプレゼンターのみと対話
2. **Streamlitウィジェット**: `st.text_input()`, `st.selectbox()`, `st.dataframe()`などを使用
3. **フォーム送信**: `st.form()`でフォームをグループ化
4. **エラーメッセージ**: `st.error()`, `st.success()`, `st.info()`でユーザーフィードバック
5. **リロード**: `st.rerun()`でページをリロード（データ更新後）

### セッション状態管理

Streamlitは、ページリロード間で状態を保持するための`st.session_state`を提供します。

#### SessionManager の実装

```python
# src/interfaces/web/streamlit/utils/session_manager.py

import streamlit as st
from typing import Any


class SessionManager:
    """Manage Streamlit session state."""

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from session state."""
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        """Set value in session state."""
        st.session_state[key] = value

    @staticmethod
    def delete(key: str) -> None:
        """Delete value from session state."""
        if key in st.session_state:
            del st.session_state[key]

    @staticmethod
    def has(key: str) -> bool:
        """Check if key exists in session state."""
        return key in st.session_state
```

**使用例**:

```python
session = SessionManager()

# 値の保存
session.set("selected_politician_id", politician_id)

# 値の取得
politician_id = session.get("selected_politician_id")

# 値の削除
session.delete("selected_politician_id")
```

**注意点**:
- セッション状態は**ブラウザセッション単位**で保持される
- 過度な使用はメモリリークの原因になる
- 必要最小限の情報のみ保存する

---

## プレゼンターパターン

プレゼンターは、ビューとユースケース（Application層）の間の橋渡しを行います。

### BasePresenter の実装

すべてのプレゼンターは`BasePresenter[T]`を継承します。

```python
# src/interfaces/web/streamlit/presenters/base.py

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any, Generic, TypeVar

import nest_asyncio
from src.common.logging import get_logger
from src.infrastructure.di.container import Container


T = TypeVar("T")
R = TypeVar("R")


class BasePresenter(ABC, Generic[T]):
    """Base presenter class for Streamlit interface layer.

    This class provides common functionality for all presenters including:
    - Dependency injection via container
    - Logging
    - Error handling
    - State management abstraction
    """

    def __init__(self, container: Container | None = None):
        """Initialize the base presenter.

        Args:
            container: Dependency injection container. If None, creates a new instance.
        """
        self.container = container or Container.create_for_environment()
        self.logger = get_logger(self.__class__.__name__)

    def _run_async(self, coro: Coroutine[Any, Any, R]) -> R:
        """Run an async coroutine from sync context.

        This helper method allows presenters to call async use cases from
        synchronous Streamlit code. It handles event loop management and
        nested asyncio scenarios.

        Args:
            coro: The async coroutine to run

        Returns:
            The result of the coroutine

        Raises:
            Exception: If the async operation fails
        """
        nest_asyncio.apply()
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    @abstractmethod
    def load_data(self) -> T:
        """Load data for the view.

        Returns:
            Data to be displayed in the view
        """
        pass
```

**BasePresenter の役割**:

1. **依存性注入**: DIコンテナを使用してユースケースを取得
2. **非同期→同期変換**: `_run_async()`でユースケースの非同期メソッドを同期的に呼び出す
3. **ログ管理**: すべてのプレゼンターでロガーを使用可能
4. **エラーハンドリング**: 共通のエラー処理ロジック

### 具体的なプレゼンターの実装

#### PoliticianPresenter の実装例

```python
# src/interfaces/web/streamlit/presenters/politician_presenter.py

from typing import Any
import pandas as pd

from src.application.usecases.manage_politicians_usecase import (
    CreatePoliticianInputDto,
    DeletePoliticianInputDto,
    ManagePoliticiansUseCase,
    PoliticianListInputDto,
    UpdatePoliticianInputDto,
)
from src.common.logging import get_logger
from src.domain.entities import PoliticalParty, Politician
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class PoliticianPresenter(BasePresenter[list[Politician]]):
    """Presenter for politician management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # Initialize repositories and use case
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.party_repo = RepositoryAdapter(PoliticalPartyRepositoryImpl)
        self.use_case = ManagePoliticiansUseCase(
            self.politician_repo  # type: ignore[arg-type]
        )
        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> list[Politician]:
        """Load all politicians."""
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[Politician]:
        """Load all politicians (async implementation)."""
        try:
            result = await self.use_case.list_politicians(PoliticianListInputDto())
            return result.politicians
        except Exception as e:
            self.logger.error(f"Failed to load politicians: {e}")
            return []

    def load_politicians_with_filters(
        self, party_id: int | None = None, search_name: str | None = None
    ) -> list[Politician]:
        """Load politicians with filters."""
        return self._run_async(
            self._load_politicians_with_filters_async(party_id, search_name)
        )

    async def _load_politicians_with_filters_async(
        self, party_id: int | None = None, search_name: str | None = None
    ) -> list[Politician]:
        """Load politicians with filters (async implementation)."""
        try:
            result = await self.use_case.list_politicians(
                PoliticianListInputDto(party_id=party_id, search_name=search_name)
            )
            return result.politicians
        except Exception as e:
            self.logger.error(f"Failed to load politicians with filters: {e}")
            return []

    def get_all_parties(self) -> list[PoliticalParty]:
        """Get all political parties."""
        return self._run_async(self._get_all_parties_async())

    async def _get_all_parties_async(self) -> list[PoliticalParty]:
        """Get all political parties (async implementation)."""
        try:
            return await self.party_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load parties: {e}")
            return []

    def create_politician(
        self,
        name: str,
        name_furigana: str | None,
        party_id: int | None,
        district: str | None,
        bio: str | None,
    ) -> Any:
        """Create a new politician."""
        return self._run_async(
            self._create_politician_async(name, name_furigana, party_id, district, bio)
        )

    async def _create_politician_async(
        self,
        name: str,
        name_furigana: str | None,
        party_id: int | None,
        district: str | None,
        bio: str | None,
    ) -> Any:
        """Create a new politician (async implementation)."""
        try:
            input_dto = CreatePoliticianInputDto(
                name=name,
                name_furigana=name_furigana,
                party_id=party_id,
                district=district,
                bio=bio,
            )
            return await self.use_case.create_politician(input_dto)
        except Exception as e:
            self.logger.error(f"Failed to create politician: {e}")
            return {"success": False, "error_message": str(e)}

    def to_dataframe(
        self, politicians: list[Politician], parties: list[PoliticalParty]
    ) -> pd.DataFrame | None:
        """Convert politicians to DataFrame for display."""
        if not politicians:
            return None

        # Create party lookup
        party_map = {p.id: p.name for p in parties}

        data = []
        for p in politicians:
            data.append(
                {
                    "ID": p.id,
                    "氏名": p.name,
                    "ふりがな": p.name_furigana or "",
                    "政党": party_map.get(p.party_id, "なし") if p.party_id else "なし",
                    "選挙区": p.district or "",
                }
            )

        return pd.DataFrame(data)
```

**プレゼンター実装のポイント**:

1. **ユースケースの呼び出し**: Application層のユースケースのみを呼び出す
2. **DTOの構築**: ユーザー入力からInputDTOを構築
3. **非同期処理**: すべてのユースケース呼び出しは非同期メソッドで実装し、`_run_async()`でラップ
4. **エラーハンドリング**: 例外をキャッチしてログに記録
5. **データ変換**: エンティティをDataFrameなどの表示用形式に変換

### ビジネスロジックとUIの分離

**重要な原則**: プレゼンターにビジネスロジックを含めない。

#### 悪い例（アンチパターン）

```python
# ❌ プレゼンターにビジネスロジックを含める（悪い例）

class PoliticianPresenter(BasePresenter):
    def create_politician(self, name: str, party_id: int | None) -> Any:
        # ❌ ビジネスロジック（重複チェック）をプレゼンターに実装
        existing = self._run_async(
            self.politician_repo.get_by_name_and_party(name, party_id)
        )
        if existing:
            return {"success": False, "error_message": "同名の政治家が既に存在します"}

        # ❌ ビジネスルール（名前の正規化）をプレゼンターに実装
        normalized_name = name.replace("　", " ").strip()

        politician = Politician(id=None, name=normalized_name, party_id=party_id)
        created = self._run_async(self.politician_repo.create(politician))
        return {"success": True, "politician_id": created.id}
```

#### 良い例

```python
# ✅ プレゼンターはユースケースを呼び出すのみ

class PoliticianPresenter(BasePresenter):
    def create_politician(self, name: str, party_id: int | None) -> Any:
        # ✅ ユースケースに委譲
        input_dto = CreatePoliticianInputDto(name=name, party_id=party_id)
        return self._run_async(self.use_case.create_politician(input_dto))
```

**ビジネスロジックはユースケース層に実装**:

```python
# src/application/usecases/manage_politicians_usecase.py

class ManagePoliticiansUseCase:
    async def create_politician(
        self, input_dto: CreatePoliticianInputDto
    ) -> CreatePoliticianOutputDto:
        # ✅ ビジネスロジック（重複チェック）はユースケースで実装
        existing = await self.politician_repository.get_by_name_and_party(
            input_dto.name, input_dto.party_id
        )
        if existing:
            return CreatePoliticianOutputDto(
                success=False, error_message="同名の政治家が既に存在します"
            )

        # ✅ ビジネスルール（名前の正規化）もユースケースで実装
        normalized_name = input_dto.name.replace("　", " ").strip()

        politician = Politician(id=None, name=normalized_name, party_id=input_dto.party_id)
        created = await self.politician_repository.create(politician)
        return CreatePoliticianOutputDto(success=True, politician_id=created.id)
```

---

## よくある落とし穴と回避方法

### 1. ビジネスロジックのUI層への混入

#### 問題

プレゼンターやビューにビジネスロジックを実装してしまう。

#### 悪い例

```python
# ❌ ビューにビジネスロジックを実装（悪い例）

def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    with st.form("new_politician_form"):
        name = st.text_input("氏名")
        party_id = st.selectbox("政党", ...)

        submitted = st.form_submit_button("登録")

        if submitted:
            # ❌ ビジネスルール（重複チェック）をビューに実装
            politicians = presenter.load_data()
            if any(p.name == name and p.party_id == party_id for p in politicians):
                st.error("同名の政治家が既に存在します")
                return

            # ❌ ビジネスルール（名前の正規化）をビューに実装
            normalized_name = name.replace("　", " ").strip()

            result = presenter.create_politician(normalized_name, party_id)
```

#### 良い例

```python
# ✅ ビューはプレゼンターを呼び出すのみ

def render_new_politician_tab(presenter: PoliticianPresenter) -> None:
    with st.form("new_politician_form"):
        name = st.text_input("氏名")
        party_id = st.selectbox("政党", ...)

        submitted = st.form_submit_button("登録")

        if submitted:
            # ✅ プレゼンター経由でユースケースに委譲
            result = presenter.create_politician(name, party_id)

            if result.success:
                st.success("✅ 登録しました")
            else:
                st.error(f"❌ {result.error_message}")
```

**解決策**:
- ビジネスロジックはすべてApplication層（ユースケース）に実装
- UI層はユーザー入力の収集と結果の表示のみ

---

### 2. 直接的なデータベースアクセス

#### 問題

ビューやプレゼンターがリポジトリを直接呼び出してしまう。

#### 悪い例

```python
# ❌ プレゼンターがリポジトリを直接呼び出す（悪い例）

class PoliticianPresenter(BasePresenter):
    def load_politicians_with_filters(self, party_id: int | None) -> list[Politician]:
        # ❌ リポジトリを直接呼び出す
        if party_id:
            return self._run_async(self.politician_repo.get_by_party(party_id))
        else:
            return self._run_async(self.politician_repo.get_all())
```

#### 良い例

```python
# ✅ プレゼンターはユースケースを呼び出す

class PoliticianPresenter(BasePresenter):
    def load_politicians_with_filters(self, party_id: int | None) -> list[Politician]:
        # ✅ ユースケースを呼び出す
        input_dto = PoliticianListInputDto(party_id=party_id)
        result = self._run_async(self.use_case.list_politicians(input_dto))
        return result.politicians
```

**解決策**:
- プレゼンターはユースケースのみを呼び出す
- リポジトリへのアクセスはユースケース層に限定

---

### 3. セッション状態の過度な使用

#### 問題

セッション状態に大量のデータや不要なデータを保存してしまう。

#### 悪い例

```python
# ❌ セッション状態に大量のデータを保存（悪い例）

def render_politicians_list_tab(presenter: PoliticianPresenter) -> None:
    # ❌ すべての政治家データをセッションに保存
    if "all_politicians" not in st.session_state:
        st.session_state["all_politicians"] = presenter.load_data()

    politicians = st.session_state["all_politicians"]

    # ❌ フィルタリング結果もセッションに保存
    st.session_state["filtered_politicians"] = [
        p for p in politicians if p.party_id == selected_party_id
    ]
```

#### 良い例

```python
# ✅ セッション状態は最小限に

def render_politicians_list_tab(presenter: PoliticianPresenter) -> None:
    # ✅ 必要なときにデータを読み込む
    politicians = presenter.load_politicians_with_filters(
        party_id=selected_party_id
    )

    # ✅ セッション状態は選択中のIDのみ保存
    if st.button("編集", key=f"edit_{politician.id}"):
        st.session_state["selected_politician_id"] = politician.id
```

**解決策**:
- セッション状態には必要最小限の情報のみ保存（IDなど）
- 大量のデータは毎回読み込む（パフォーマンスが問題になる場合はキャッシュを検討）

---

### 4. エラーメッセージが技術的すぎる

#### 問題

技術的なエラーメッセージをそのままユーザーに表示してしまう。

#### 悪い例

```python
# ❌ 技術的なエラーメッセージをそのまま表示（悪い例）

if submitted:
    result = presenter.create_politician(name, party_id)
    if not result.success:
        # ❌ "Foreign key constraint violation" などの技術的メッセージ
        st.error(f"❌ {result.error_message}")
```

#### 良い例

```python
# ✅ ユーザーフレンドリーなメッセージに変換

if submitted:
    result = presenter.create_politician(name, party_id)
    if not result.success:
        # ✅ 技術的エラーをユーザーフレンドリーなメッセージに変換
        error_message = result.error_message
        if "Foreign key constraint" in error_message:
            st.error("❌ 選択された政党が存在しません")
        elif "Unique constraint" in error_message:
            st.error("❌ 同名の政治家が既に登録されています")
        else:
            st.error("❌ 登録に失敗しました。管理者に連絡してください")
```

**解決策**:
- エラーメッセージをユーザーフレンドリーに変換
- 技術的な詳細はログに記録

---

### 5. 非同期処理の誤った使用

#### 問題

Streamlitの同期的な実行環境で非同期処理を正しく扱えていない。

#### 悪い例

```python
# ❌ 非同期メソッドを同期的に呼び出す（悪い例）

class PoliticianPresenter(BasePresenter):
    def load_data(self) -> list[Politician]:
        # ❌ asyncメソッドをawaitなしで呼び出す
        result = self.use_case.list_politicians(PoliticianListInputDto())
        return result.politicians  # エラー: コルーチンオブジェクトが返る
```

#### 良い例

```python
# ✅ _run_async()を使用して非同期メソッドを呼び出す

class PoliticianPresenter(BasePresenter):
    def load_data(self) -> list[Politician]:
        # ✅ _run_async()でコルーチンを実行
        return self._run_async(self._load_data_async())

    async def _load_data_async(self) -> list[Politician]:
        result = await self.use_case.list_politicians(PoliticianListInputDto())
        return result.politicians
```

**解決策**:
- 非同期メソッドは`async def`で定義
- プレゼンターの公開メソッドは同期メソッドで、内部で`_run_async()`を使用
- `_run_async()`にコルーチンを渡す

---

## チェックリスト

新しいCLIコマンドやStreamlit UIを実装する際は、以下をチェックしてください：

### CLIコマンド

- [ ] `BaseCommand`を継承している
- [ ] `@click.command()`デコレーターを使用している
- [ ] すべてのオプションに適切な`help`メッセージがある
- [ ] `@with_error_handling`デコレーターでエラーハンドリングを実装している
- [ ] DIコンテナを使用してユースケースを取得している
- [ ] リポジトリを直接インスタンス化していない
- [ ] 非同期処理を`asyncio.run()`で実行している
- [ ] ユーザーフレンドリーなメッセージを表示している（絵文字使用）

### Streamlit ビュー

- [ ] プレゼンターのみを呼び出している
- [ ] ビジネスロジックがビュー内に含まれていない
- [ ] リポジトリを直接呼び出していない
- [ ] Streamlitウィジェットを適切に使用している
- [ ] フォーム送信に`st.form()`を使用している
- [ ] エラーメッセージがユーザーフレンドリー
- [ ] 成功/失敗のフィードバックを表示している（`st.success()`, `st.error()`）

### Streamlit プレゼンター

- [ ] `BasePresenter[T]`を継承している
- [ ] ユースケースのみを呼び出している（リポジトリ直接アクセスなし）
- [ ] ビジネスロジックがプレゼンター内に含まれていない
- [ ] 非同期処理を`_run_async()`でラップしている
- [ ] すべての公開メソッドが同期メソッド
- [ ] エラーハンドリングとログ記録を実装している
- [ ] DTOの構築と変換を実装している

### セッション管理

- [ ] セッション状態は必要最小限（IDなど）
- [ ] 大量のデータをセッションに保存していない
- [ ] `SessionManager`を使用している
- [ ] セッション状態のクリーンアップを実装している

---

## 参考資料

### 関連ドキュメント

- [DOMAIN_LAYER.md](DOMAIN_LAYER.md) - Domain層の詳細ガイド
- [APPLICATION_LAYER.md](APPLICATION_LAYER.md) - Application層の詳細ガイド
- [INFRASTRUCTURE_LAYER.md](INFRASTRUCTURE_LAYER.md) - Infrastructure層の詳細ガイド
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) - 全体的なアーキテクチャドキュメント

### コード例

- `src/interfaces/cli/commands/politician_commands.py` - CLIコマンド実装例
- `src/interfaces/web/streamlit/views/politicians_view.py` - Streamlitビュー実装例
- `src/interfaces/web/streamlit/presenters/politician_presenter.py` - プレゼンター実装例
- `src/interfaces/web/streamlit/presenters/base.py` - BasePresenter実装
- `src/interfaces/cli/base.py` - BaseCommand実装

### 外部リソース

- [Click Documentation](https://click.palletsprojects.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [MVP Pattern](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93presenter)

---

## まとめ

Interface層は、ユーザーとシステムの接点として、使いやすいインターフェースを提供する責任があります。重要なのは：

1. **ビジネスロジックを含めない**: UI層はユースケースを呼び出すのみ
2. **プレゼンターパターンを使用**: ビューとビジネスロジックを分離
3. **ユーザーフレンドリーなメッセージ**: 技術的な詳細を隠蔽
4. **適切なエラーハンドリング**: ユーザーに分かりやすいフィードバック
5. **セッション状態は最小限**: 必要なデータのみ保存

これらの原則を守ることで、保守性が高く、テスト可能で、ユーザーフレンドリーなインターフェースを実現できます。
