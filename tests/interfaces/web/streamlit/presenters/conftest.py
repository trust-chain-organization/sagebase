"""Presenter層テスト用の共通フィクスチャ"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_session_manager():
    """SessionManagerの共通モック

    SessionManagerをモックするための共通設定を提供します。
    form_stateの取得・設定をサポートします。
    """
    mock_session_instance = MagicMock()
    mock_session_instance.get = MagicMock(return_value={})
    mock_session_instance.set = MagicMock()
    return mock_session_instance


@pytest.fixture
def mock_repository_adapter():
    """RepositoryAdapterの共通モック

    RepositoryAdapterをモックするための共通設定を提供します。
    """
    return MagicMock()


@pytest.fixture
def mock_container():
    """Containerの共通モック

    DIコンテナをモックするための共通設定を提供します。
    """
    return MagicMock()
