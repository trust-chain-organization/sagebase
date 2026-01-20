"""ParliamentaryGroupMemberPresenterのテスト"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician


@pytest.fixture
def mock_repos():
    """リポジトリのモック"""
    repos = {
        "extracted_member_repo": MagicMock(),
        "membership_repo": MagicMock(),
        "parliamentary_group_repo": MagicMock(),
        "politician_repo": MagicMock(),
        "political_party_repo": MagicMock(),
    }
    for repo in repos.values():
        repo.get_all = MagicMock(return_value=[])
        repo.get_by_id = MagicMock(return_value=None)
    return repos


@pytest.fixture
def sample_extracted_members():
    """サンプル抽出メンバーリスト"""
    return [
        ExtractedParliamentaryGroupMember(
            id=1,
            parliamentary_group_id=100,
            extracted_name="田中太郎",
            source_url="https://example.com/members",
            extracted_role="団長",
            matched_politician_id=1,
            matching_confidence=0.95,
            matching_status="matched",
        ),
        ExtractedParliamentaryGroupMember(
            id=2,
            parliamentary_group_id=100,
            extracted_name="山田花子",
            source_url="https://example.com/members",
            extracted_role="幹事長",
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="pending",
        ),
    ]


@pytest.fixture
def sample_parliamentary_groups():
    """サンプル議員団リスト"""
    return [
        ParliamentaryGroup(id=100, name="自民党会派", conference_id=1),
        ParliamentaryGroup(id=101, name="立憲民主党会派", conference_id=1),
    ]


@pytest.fixture
def sample_politicians():
    """サンプル政治家リスト"""
    return [
        Politician(id=1, name="田中太郎", prefecture="東京都", district="第1選挙区"),
        Politician(id=2, name="山田花子", prefecture="大阪府", district="第2選挙区"),
    ]


@pytest.fixture
def presenter(mock_repos):
    """ParliamentaryGroupMemberPresenterのインスタンス"""
    with (
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.RepositoryAdapter"
        ) as mock_adapter,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.SessionManager"
        ) as mock_session,
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.GeminiLLMService"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.SpeakerDomainService"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.ParliamentaryGroupMemberMatchingService"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.MatchParliamentaryGroupMembersUseCase"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.CreateParliamentaryGroupMembershipsUseCase"
        ),
        patch(
            "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.ReviewExtractedMemberUseCase"
        ),
        patch("src.interfaces.web.streamlit.presenters.base.Container"),
    ):
        # Mock RepositoryAdapter to return appropriate repos
        def adapter_side_effect(repo_class):
            class_name = repo_class.__name__
            if "ExtractedParliamentaryGroupMember" in class_name:
                return mock_repos["extracted_member_repo"]
            elif "ParliamentaryGroupMembership" in class_name:
                return mock_repos["membership_repo"]
            elif "ParliamentaryGroup" in class_name:
                return mock_repos["parliamentary_group_repo"]
            elif "Politician" in class_name:
                return mock_repos["politician_repo"]
            elif "PoliticalParty" in class_name:
                return mock_repos["political_party_repo"]
            return MagicMock()

        mock_adapter.side_effect = adapter_side_effect

        mock_session_instance = MagicMock()
        mock_session_instance.get = MagicMock(return_value={})
        mock_session.return_value = mock_session_instance

        from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
            ParliamentaryGroupMemberPresenter,
        )

        presenter = ParliamentaryGroupMemberPresenter()
        presenter.extracted_member_repo = mock_repos["extracted_member_repo"]
        presenter.parliamentary_group_repo = mock_repos["parliamentary_group_repo"]
        presenter.politician_repo = mock_repos["politician_repo"]
        presenter.political_party_repo = mock_repos["political_party_repo"]
        return presenter


class TestParliamentaryGroupMemberPresenterInit:
    """初期化テスト"""

    def test_init_creates_instance(self):
        """Presenterが正しく初期化されることを確認"""
        with (
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.RepositoryAdapter"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.SessionManager"
            ) as mock_session,
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.GeminiLLMService"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.SpeakerDomainService"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.ParliamentaryGroupMemberMatchingService"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.MatchParliamentaryGroupMembersUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.CreateParliamentaryGroupMembershipsUseCase"
            ),
            patch(
                "src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter.ReviewExtractedMemberUseCase"
            ),
            patch("src.interfaces.web.streamlit.presenters.base.Container"),
        ):
            mock_session_instance = MagicMock()
            mock_session_instance.get = MagicMock(return_value={})
            mock_session.return_value = mock_session_instance

            from src.interfaces.web.streamlit.presenters.parliamentary_group_member_presenter import (  # noqa: E501
                ParliamentaryGroupMemberPresenter,
            )

            presenter = ParliamentaryGroupMemberPresenter()
            assert presenter is not None


class TestLoadData:
    """load_dataメソッドのテスト"""

    def test_load_data_success(
        self,
        presenter,
        mock_repos,
        sample_parliamentary_groups,
        sample_extracted_members,
    ):
        """抽出メンバーを読み込めることを確認"""
        # Arrange
        mock_repos[
            "parliamentary_group_repo"
        ].get_all.return_value = sample_parliamentary_groups
        mock_repos["extracted_member_repo"].get_by_parliamentary_group = MagicMock(
            return_value=sample_extracted_members
        )

        # Act
        result = presenter.load_data()

        # Assert
        assert len(result) == 4  # 2 groups * 2 members

    def test_load_data_exception(self, presenter, mock_repos):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_repos["parliamentary_group_repo"].get_all.side_effect = Exception(
            "Database error"
        )

        # Act
        result = presenter.load_data()

        # Assert
        assert result == []


class TestGetAllParliamentaryGroups:
    """get_all_parliamentary_groupsメソッドのテスト"""

    def test_get_all_parliamentary_groups_success(
        self, presenter, mock_repos, sample_parliamentary_groups
    ):
        """議員団リストを取得できることを確認"""
        # Arrange
        mock_repos[
            "parliamentary_group_repo"
        ].get_all.return_value = sample_parliamentary_groups

        # Act
        result = presenter.get_all_parliamentary_groups()

        # Assert
        assert len(result) == 2

    def test_get_all_parliamentary_groups_exception(self, presenter, mock_repos):
        """例外発生時に空リストを返すことを確認"""
        # Arrange
        mock_repos["parliamentary_group_repo"].get_all.side_effect = Exception("Error")

        # Act
        result = presenter.get_all_parliamentary_groups()

        # Assert
        assert result == []


class TestGetAllPoliticalParties:
    """get_all_political_partiesメソッドのテスト"""

    def test_get_all_political_parties_success(self, presenter, mock_repos):
        """政党リストを取得できることを確認"""
        # Arrange
        mock_parties = [
            MagicMock(id=1, name="自民党"),
            MagicMock(id=2, name="立憲民主党"),
        ]
        mock_repos["political_party_repo"].get_all.return_value = mock_parties

        # Act
        result = presenter.get_all_political_parties()

        # Assert
        assert len(result) == 2


class TestGetFilteredExtractedMembers:
    """get_filtered_extracted_membersメソッドのテスト"""

    def test_get_filtered_by_group(
        self, presenter, mock_repos, sample_extracted_members
    ):
        """議員団でフィルタできることを確認"""
        # Arrange
        mock_repos["extracted_member_repo"].get_by_parliamentary_group = MagicMock(
            return_value=sample_extracted_members
        )

        # Act
        result = presenter.get_filtered_extracted_members(parliamentary_group_id=100)

        # Assert
        assert len(result) == 2


class TestGetStatistics:
    """get_statisticsメソッドのテスト"""

    def test_get_statistics(self, presenter, mock_repos):
        """統計情報を取得できることを確認"""
        # Arrange
        presenter.extracted_member_repo = MagicMock()
        presenter.extracted_member_repo.get_extraction_summary = MagicMock(
            return_value={
                "total": 10,
                "pending": 3,
                "matched": 5,
                "needs_review": 1,
                "no_match": 1,
            }
        )

        # Act
        result = presenter.get_statistics()

        # Assert
        assert "total" in result
        assert "matched" in result
        assert "pending" in result


class TestGetPoliticianById:
    """get_politician_by_idメソッドのテスト"""

    def test_get_politician_by_id_success(
        self, presenter, mock_repos, sample_politicians
    ):
        """政治家を取得できることを確認"""
        # Arrange
        mock_repos["politician_repo"].get_by_id = MagicMock(
            return_value=sample_politicians[0]
        )

        # Act
        result = presenter.get_politician_by_id(1)

        # Assert
        assert result.name == "田中太郎"

    def test_get_politician_by_id_not_found(self, presenter, mock_repos):
        """政治家が見つからない場合にNoneを返すことを確認"""
        # Arrange
        mock_repos["politician_repo"].get_by_id = MagicMock(return_value=None)

        # Act
        result = presenter.get_politician_by_id(999)

        # Assert
        assert result is None


class TestSearchPoliticians:
    """search_politiciansメソッドのテスト"""

    def test_search_politicians_success(
        self, presenter, mock_repos, sample_politicians
    ):
        """政治家を検索できることを確認"""
        # Arrange - search_politiciansはget_all()を使って内部でフィルタリングする
        presenter.politician_repo = MagicMock()
        presenter.politician_repo.get_all = MagicMock(return_value=sample_politicians)

        # Act
        result = presenter.search_politicians("田中")

        # Assert - 田中を名前に含む政治家は1人
        assert len(result) == 1


class TestToDataframe:
    """to_dataframeメソッドのテスト"""

    def test_to_dataframe_success(self, presenter, sample_extracted_members):
        """抽出メンバーをDataFrameに変換できることを確認"""
        # Arrange
        presenter.parliamentary_group_repo = MagicMock()
        presenter.parliamentary_group_repo.get_by_id = MagicMock(
            return_value=ParliamentaryGroup(id=100, name="自民党会派", conference_id=1)
        )

        # Act
        df = presenter.to_dataframe(sample_extracted_members)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "名前" in df.columns
        assert "役職" in df.columns

    def test_to_dataframe_empty(self, presenter):
        """空のリストを処理できることを確認"""
        # Act
        df = presenter.to_dataframe([])

        # Assert - 空リストの場合はNoneを返す
        assert df is None


class TestHandleAction:
    """handle_actionメソッドのテスト"""

    def test_handle_action_review(self, presenter):
        """reviewアクションが正しく処理されることを確認"""
        # Arrange
        presenter.review_extracted_member = MagicMock(return_value=None)

        # Act
        presenter.handle_action("review", member_id=1, review_action="approve")

        # Assert
        presenter.review_extracted_member.assert_called_once()

    def test_handle_action_rematch(self, presenter):
        """rematchアクションが正しく処理されることを確認"""
        # Arrange
        presenter.rematch_members = MagicMock(return_value=None)

        # Act
        presenter.handle_action("rematch", parliamentary_group_id=1)

        # Assert
        presenter.rematch_members.assert_called_once()

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")
