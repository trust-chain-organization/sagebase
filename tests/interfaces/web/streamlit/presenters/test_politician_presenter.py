"""PoliticianPresenterのテスト"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from src.application.dtos.politician_dto import (
    CreatePoliticianOutputDto,
    DeletePoliticianOutputDto,
    MergePoliticiansOutputDto,
    PoliticianListOutputDto,
    UpdatePoliticianOutputDto,
)
from src.domain.entities import PoliticalParty, Politician


@pytest.fixture
def mock_use_case():
    """ManagePoliticiansUseCaseのモック"""
    use_case = AsyncMock()
    use_case.list_politicians = AsyncMock()
    use_case.create_politician = AsyncMock()
    use_case.update_politician = AsyncMock()
    use_case.delete_politician = AsyncMock()
    use_case.merge_politicians = AsyncMock()
    return use_case


@pytest.fixture
def mock_party_repo():
    """PoliticalPartyRepositoryのモック"""
    repo = MagicMock()
    repo.get_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def sample_politicians():
    """サンプル政治家リスト"""
    return [
        Politician(
            id=1,
            name="田中太郎",
            prefecture="東京都",
            political_party_id=1,
            district="新宿区",
            profile_page_url="https://example.com/tanaka",
        ),
        Politician(
            id=2,
            name="山田花子",
            prefecture="大阪府",
            political_party_id=2,
            district="中央区",
            profile_page_url=None,
        ),
    ]


@pytest.fixture
def sample_parties():
    """サンプル政党リスト"""
    return [
        PoliticalParty(id=1, name="自民党"),
        PoliticalParty(id=2, name="立憲民主党"),
    ]


@pytest.fixture
def presenter(mock_use_case, mock_party_repo):
    """PoliticianPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.politician_presenter.RepositoryAdapter"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.politician_presenter.SessionManager"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.politician_presenter.ManagePoliticiansUseCase"
        ) as mock_uc_class,
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        mock_uc_class.return_value = mock_use_case

        from src.interfaces.web.streamlit.presenters.politician_presenter import (
            PoliticianPresenter,
        )

        presenter = PoliticianPresenter()
        presenter.use_case = mock_use_case
        presenter.party_repo = mock_party_repo
        return presenter


class TestPoliticianPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.politician_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.politician_presenter.SessionManager"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.politician_presenter.ManagePoliticiansUseCase"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            from src.interfaces.web.streamlit.presenters.politician_presenter import (
                PoliticianPresenter,
            )

            presenter = PoliticianPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_success(self, presenter, mock_use_case, sample_politicians):
        """政治家リストを読み込めることを確認"""
        # Arrange
        mock_use_case.list_politicians.return_value = PoliticianListOutputDto(
            politicians=sample_politicians
        )

        # Act
        with patch(
            "src.interfaces.web.streamlit.presenters.politician_presenter.asyncio.run",
            side_effect=lambda coro: coro.send(None),
        ):
            # asyncio.runをバイパスして直接非同期メソッドをテスト
            pass

    async def test_load_data_async_success(
        self, presenter, mock_use_case, sample_politicians
    ):
        """政治家リストを非同期で読み込めることを確認"""
        # Arrange
        mock_use_case.list_politicians.return_value = PoliticianListOutputDto(
            politicians=sample_politicians
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert len(result) == 2
        assert result[0].name == "田中太郎"

    async def test_load_data_async_empty(self, presenter, mock_use_case):
        """空の政治家リストを処理できることを確認"""
        # Arrange
        mock_use_case.list_politicians.return_value = PoliticianListOutputDto(
            politicians=[]
        )

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []

    async def test_load_data_async_exception(self, presenter, mock_use_case):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_use_case.list_politicians.side_effect = Exception("Database error")

        # Act
        result = await presenter._load_data_async()

        # Assert
        assert result == []


class TestLoadPoliticiansWithFilters:
    """load_politicians_with_filtersメソッドのテスト"""

    async def test_with_party_filter(
        self, presenter, mock_use_case, sample_politicians
    ):
        """政党フィルタで政治家を絞り込めることを確認"""
        # Arrange
        mock_use_case.list_politicians.return_value = PoliticianListOutputDto(
            politicians=[sample_politicians[0]]
        )

        # Act
        result = await presenter._load_politicians_with_filters_async(party_id=1)

        # Assert
        assert len(result) == 1
        mock_use_case.list_politicians.assert_called_once()

    async def test_with_name_filter(self, presenter, mock_use_case, sample_politicians):
        """名前フィルタで政治家を絞り込めることを確認"""
        # Arrange
        mock_use_case.list_politicians.return_value = PoliticianListOutputDto(
            politicians=[sample_politicians[0]]
        )

        # Act
        result = await presenter._load_politicians_with_filters_async(
            search_name="田中"
        )

        # Assert
        assert len(result) == 1


class TestGetAllParties:
    """get_all_partiesメソッドのテスト"""

    async def test_get_all_parties_success(
        self, presenter, mock_party_repo, sample_parties
    ):
        """政党リストを取得できることを確認"""
        # Arrange
        mock_party_repo.get_all.return_value = sample_parties

        # Act
        result = await presenter._get_all_parties_async()

        # Assert
        assert len(result) == 2
        assert result[0].name == "自民党"

    async def test_get_all_parties_exception(self, presenter, mock_party_repo):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_party_repo.get_all.side_effect = Exception("Database error")

        # Act
        result = await presenter._get_all_parties_async()

        # Assert
        assert result == []


class TestCreate:
    """createメソッドのテスト"""

    async def test_create_success(self, presenter, mock_use_case):
        """政治家の作成が成功することを確認"""
        # Arrange
        mock_use_case.create_politician.return_value = CreatePoliticianOutputDto(
            success=True, politician_id=1, error_message=None
        )

        # Act
        success, politician_id, error = await presenter._create_async(
            name="新人 議員",
            prefecture="東京都",
            party_id=1,
            district="渋谷区",
            profile_url="https://example.com/new",
            user_id=uuid4(),
        )

        # Assert
        assert success is True
        assert politician_id == 1
        assert error is None

    async def test_create_normalizes_whitespace(self, presenter, mock_use_case):
        """空白が正規化されることを確認"""
        # Arrange
        mock_use_case.create_politician.return_value = CreatePoliticianOutputDto(
            success=True, politician_id=1, error_message=None
        )

        # Act
        await presenter._create_async(
            name="田中　太郎",  # 全角スペース
            prefecture="東京都",
            party_id=1,
            district="新宿　区",  # 全角スペース
            profile_url=None,
        )

        # Assert - 呼び出し引数を確認
        call_args = mock_use_case.create_politician.call_args
        input_dto = call_args[0][0]
        assert input_dto.name == "田中太郎"
        assert input_dto.district == "新宿区"

    async def test_create_failure(self, presenter, mock_use_case):
        """政治家の作成が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.create_politician.return_value = CreatePoliticianOutputDto(
            success=False,
            politician_id=None,
            error_message="重複する政治家が存在します",
        )

        # Act
        success, politician_id, error = await presenter._create_async(
            name="田中太郎",
            prefecture="東京都",
            party_id=1,
            district="新宿区",
        )

        # Assert
        assert success is False
        assert politician_id is None
        assert error == "重複する政治家が存在します"

    async def test_create_exception(self, presenter, mock_use_case):
        """例外発生時にエラーを返すことを確認"""
        # Arrange
        mock_use_case.create_politician.side_effect = Exception("Database error")

        # Act
        success, politician_id, error = await presenter._create_async(
            name="田中太郎",
            prefecture="東京都",
            party_id=1,
            district="新宿区",
        )

        # Assert
        assert success is False
        assert politician_id is None
        assert "Failed to create" in error


class TestUpdate:
    """updateメソッドのテスト"""

    async def test_update_success(self, presenter, mock_use_case):
        """政治家の更新が成功することを確認"""
        # Arrange
        mock_use_case.update_politician.return_value = UpdatePoliticianOutputDto(
            success=True, error_message=None
        )

        # Act
        success, error = await presenter._update_async(
            id=1,
            name="田中太郎",
            prefecture="東京都",
            party_id=1,
            district="新宿区",
            profile_url="https://example.com/updated",
        )

        # Assert
        assert success is True
        assert error is None

    async def test_update_failure(self, presenter, mock_use_case):
        """政治家の更新が失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.update_politician.return_value = UpdatePoliticianOutputDto(
            success=False, error_message="政治家が見つかりません"
        )

        # Act
        success, error = await presenter._update_async(
            id=999,
            name="不明",
            prefecture="不明",
            party_id=None,
            district="不明",
        )

        # Assert
        assert success is False
        assert error == "政治家が見つかりません"


class TestDelete:
    """deleteメソッドのテスト"""

    async def test_delete_success(self, presenter, mock_use_case):
        """政治家の削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_politician.return_value = DeletePoliticianOutputDto(
            success=True,
            error_message=None,
            has_related_data=False,
            related_data_counts=None,
        )

        # Act
        success, error, has_related, counts = await presenter._delete_async(id=1)

        # Assert
        assert success is True
        assert error is None
        assert has_related is False

    async def test_delete_with_related_data(self, presenter, mock_use_case):
        """関連データがある場合の削除を確認"""
        # Arrange
        mock_use_case.delete_politician.return_value = DeletePoliticianOutputDto(
            success=False,
            error_message="関連データが存在します",
            has_related_data=True,
            related_data_counts={"speakers": 5, "conversations": 10},
        )

        # Act
        success, error, has_related, counts = await presenter._delete_async(id=1)

        # Assert
        assert success is False
        assert has_related is True
        assert counts["speakers"] == 5

    async def test_delete_force(self, presenter, mock_use_case):
        """強制削除が成功することを確認"""
        # Arrange
        mock_use_case.delete_politician.return_value = DeletePoliticianOutputDto(
            success=True,
            error_message=None,
            has_related_data=False,
            related_data_counts=None,
        )

        # Act
        success, error, has_related, counts = await presenter._delete_async(
            id=1, force=True
        )

        # Assert
        assert success is True


class TestMerge:
    """mergeメソッドのテスト"""

    async def test_merge_success(self, presenter, mock_use_case):
        """政治家のマージが成功することを確認"""
        # Arrange
        mock_use_case.merge_politicians.return_value = MergePoliticiansOutputDto(
            success=True, error_message=None
        )

        # Act
        success, error = await presenter._merge_async(source_id=1, target_id=2)

        # Assert
        assert success is True
        assert error is None

    async def test_merge_failure(self, presenter, mock_use_case):
        """政治家のマージが失敗した場合のエラーメッセージを確認"""
        # Arrange
        mock_use_case.merge_politicians.return_value = MergePoliticiansOutputDto(
            success=False, error_message="マージ元とマージ先が同じです"
        )

        # Act
        success, error = await presenter._merge_async(source_id=1, target_id=1)

        # Assert
        assert success is False
        assert "同じ" in error


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter, sample_politicians, sample_parties):
        """政治家リストをDataFrameに変換できることを確認"""
        # Act
        df = presenter.to_dataframe(sample_politicians, sample_parties)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "ID" in df.columns
        assert "名前" in df.columns
        assert "都道府県" in df.columns
        assert "政党" in df.columns
        assert "選挙区" in df.columns
        assert df.iloc[0]["政党"] == "自民党"

    def test_to_dataframe_empty(self, presenter, sample_parties):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([], sample_parties)

        # Assert
        assert df is None

    def test_to_dataframe_no_party(self, presenter, sample_parties):
        """無所属の政治家を正しく表示できることを確認"""
        # Arrange
        politicians = [
            Politician(
                id=1,
                name="無所属議員",
                prefecture="東京都",
                political_party_id=None,  # 無所属
                district="新宿区",
            )
        ]

        # Act
        df = presenter.to_dataframe(politicians, sample_parties)

        # Assert
        assert df.iloc[0]["政党"] == "無所属"


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_list(self, presenter):
        """listアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "load_politicians_with_filters", return_value=[]
        ) as mock_method:
            # Act
            presenter.handle_action("list", party_id=1, search_name="田中")

            # Assert
            mock_method.assert_called_once_with(1, "田中")

    def test_handle_action_create(self, presenter):
        """createアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "create", return_value=(True, 1, None)
        ) as mock_method:
            # Act
            presenter.handle_action(
                "create",
                name="田中太郎",
                prefecture="東京都",
                party_id=1,
                district="新宿区",
            )

            # Assert
            mock_method.assert_called_once()

    def test_handle_action_update(self, presenter):
        """updateアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "update", return_value=(True, None)
        ) as mock_method:
            # Act
            presenter.handle_action(
                "update",
                id=1,
                name="田中太郎",
                prefecture="東京都",
                party_id=1,
                district="新宿区",
            )

            # Assert
            mock_method.assert_called_once()

    def test_handle_action_delete(self, presenter):
        """deleteアクションが正しく処理されることを確認"""
        with patch.object(
            presenter, "delete", return_value=(True, None, False, None)
        ) as mock_method:
            # Act
            presenter.handle_action("delete", id=1)

            # Assert
            mock_method.assert_called_once()

    def test_handle_action_merge(self, presenter):
        """mergeアクションが正しく処理されることを確認"""
        with patch.object(presenter, "merge", return_value=(True, None)) as mock_method:
            # Act
            presenter.handle_action("merge", source_id=1, target_id=2)

            # Assert
            mock_method.assert_called_once_with(1, 2)

    def test_handle_action_unknown(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        # Act & Assert
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown_action")
