"""BasePresenterとCRUDPresenterのテスト

プロダクションコードのBasePresenterとCRUDPresenterを継承してテストする。
"""

import asyncio

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter, CRUDPresenter


class ConcreteBasePresenter(BasePresenter[list]):
    """BasePresenterを継承したテスト用具象クラス"""

    def load_data(self) -> list:
        return []

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        if action == "test":
            return "success"
        raise ValueError(f"Unknown action: {action}")


class ConcreteCRUDPresenter(CRUDPresenter[dict]):
    """CRUDPresenterを継承したテスト用具象クラス"""

    def load_data(self) -> dict:
        return {}

    def create(self, **kwargs: Any) -> dict:
        return {"id": 1, **kwargs}

    def read(self, **kwargs: Any) -> dict:
        return {"id": kwargs.get("id")}

    def update(self, **kwargs: Any) -> dict:
        return {"updated": True, **kwargs}

    def delete(self, **kwargs: Any) -> dict:
        return {"deleted": True, "id": kwargs.get("id")}

    def list(self, **kwargs: Any) -> list:
        return [{"id": 1}, {"id": 2}]


class TestBasePresenter:
    """BasePresenterの基本機能テスト"""

    @pytest.fixture
    def presenter(self):
        """ConcreteBasePresenterのインスタンス"""
        with patch.object(Container, "create_for_environment") as mock_create:
            mock_container = MagicMock(spec=Container)
            mock_create.return_value = mock_container
            return ConcreteBasePresenter()

    def test_init_creates_instance(self, presenter):
        """Presenterが正しく初期化されることを確認"""
        assert presenter is not None
        assert presenter.container is not None
        assert presenter.logger is not None

    def test_init_with_container(self):
        """コンテナを指定して初期化できることを確認"""
        mock_container = MagicMock(spec=Container)
        presenter = ConcreteBasePresenter(container=mock_container)
        assert presenter.container == mock_container

    def test_init_creates_container_if_none(self):
        """コンテナが指定されない場合、自動生成されることを確認"""
        with patch.object(Container, "create_for_environment") as mock_create:
            mock_container = MagicMock(spec=Container)
            mock_create.return_value = mock_container
            presenter = ConcreteBasePresenter()
            mock_create.assert_called_once()
            assert presenter.container == mock_container

    def test_load_data_returns_empty_list(self, presenter):
        """load_dataが空リストを返すことを確認"""
        result = presenter.load_data()
        assert result == []

    def test_handle_action_success(self, presenter):
        """handle_actionが成功することを確認"""
        result = presenter.handle_action("test")
        assert result == "success"

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")

    def test_handle_error_with_context(self, presenter):
        """コンテキスト付きでエラーを処理できることを確認"""
        error = Exception("Test error")
        result = presenter.handle_error(error, context="testing")
        assert "Error in testing" in result
        assert "Test error" in result

    def test_handle_error_without_context(self, presenter):
        """コンテキストなしでエラーを処理できることを確認"""
        error = Exception("Test error")
        result = presenter.handle_error(error)
        assert result == "Test error"

    def test_validate_input_success(self, presenter):
        """入力検証が成功することを確認"""
        data = {"name": "Test", "type": "A"}
        is_valid, error = presenter.validate_input(data, ["name", "type"])
        assert is_valid is True
        assert error == ""

    def test_validate_input_missing_fields(self, presenter):
        """必須フィールドが不足している場合のエラーを確認"""
        data = {"name": "Test"}
        is_valid, error = presenter.validate_input(data, ["name", "type", "value"])
        assert is_valid is False
        assert "必須フィールド" in error
        assert "type" in error
        assert "value" in error

    def test_validate_input_empty_value(self, presenter):
        """空の値が不足として扱われることを確認"""
        data = {"name": "", "type": "A"}
        is_valid, error = presenter.validate_input(data, ["name", "type"])
        assert is_valid is False
        assert "name" in error


class TestBasePresenterRunAsync:
    """BasePresenterの_run_asyncメソッドのテスト"""

    @pytest.fixture
    def presenter(self):
        """ConcreteBasePresenterのインスタンス"""
        with patch.object(Container, "create_for_environment") as mock_create:
            mock_container = MagicMock(spec=Container)
            mock_create.return_value = mock_container
            return ConcreteBasePresenter()

    def test_run_async_executes_coroutine(self, presenter):
        """非同期コルーチンが正しく実行されることを確認"""

        async def sample_coro():
            return "async_result"

        result = presenter._run_async(sample_coro())
        assert result == "async_result"

    def test_run_async_with_await(self, presenter):
        """awaitを含むコルーチンが正しく実行されることを確認"""

        async def coro_with_await():
            await asyncio.sleep(0.001)
            return "awaited_result"

        result = presenter._run_async(coro_with_await())
        assert result == "awaited_result"

    def test_run_async_raises_exception(self, presenter):
        """非同期処理で例外が発生した場合、伝播することを確認"""

        async def failing_coro():
            raise ValueError("Async error")

        with pytest.raises(ValueError, match="Async error"):
            presenter._run_async(failing_coro())

    def test_run_async_handles_nested_loop(self, presenter):
        """ネストしたイベントループでも動作することを確認"""

        async def nested_coro():
            return "nested_result"

        # nest_asyncioが適用されているため、ネストしたループでも動作する
        result = presenter._run_async(nested_coro())
        assert result == "nested_result"


class TestCRUDPresenter:
    """CRUDPresenterのテスト"""

    @pytest.fixture
    def presenter(self):
        """ConcreteCRUDPresenterのインスタンス"""
        with patch.object(Container, "create_for_environment") as mock_create:
            mock_container = MagicMock(spec=Container)
            mock_create.return_value = mock_container
            return ConcreteCRUDPresenter()

    def test_handle_action_create(self, presenter):
        """createアクションが正しく処理されることを確認"""
        result = presenter.handle_action("create", name="Test")
        assert result["id"] == 1
        assert result["name"] == "Test"

    def test_handle_action_read(self, presenter):
        """readアクションが正しく処理されることを確認"""
        result = presenter.handle_action("read", id=1)
        assert result["id"] == 1

    def test_handle_action_update(self, presenter):
        """updateアクションが正しく処理されることを確認"""
        result = presenter.handle_action("update", id=1, name="Updated")
        assert result["updated"] is True
        assert result["name"] == "Updated"

    def test_handle_action_delete(self, presenter):
        """deleteアクションが正しく処理されることを確認"""
        result = presenter.handle_action("delete", id=1)
        assert result["deleted"] is True
        assert result["id"] == 1

    def test_handle_action_list(self, presenter):
        """listアクションが正しく処理されることを確認"""
        result = presenter.handle_action("list")
        assert len(result) == 2
        assert result[0]["id"] == 1

    def test_handle_action_unknown_raises_error(self, presenter):
        """不明なアクションでエラーが発生することを確認"""
        with pytest.raises(Exception) as exc_info:
            presenter.handle_action("unknown")
        assert "Unknown action" in str(exc_info.value)

    def test_create_method(self, presenter):
        """createメソッドが正しく動作することを確認"""
        result = presenter.create(name="Test", type="A")
        assert result["id"] == 1
        assert result["name"] == "Test"
        assert result["type"] == "A"

    def test_read_method(self, presenter):
        """readメソッドが正しく動作することを確認"""
        result = presenter.read(id=5)
        assert result["id"] == 5

    def test_update_method(self, presenter):
        """updateメソッドが正しく動作することを確認"""
        result = presenter.update(id=1, name="Updated")
        assert result["updated"] is True

    def test_delete_method(self, presenter):
        """deleteメソッドが正しく動作することを確認"""
        result = presenter.delete(id=1)
        assert result["deleted"] is True

    def test_list_method(self, presenter):
        """listメソッドが正しく動作することを確認"""
        result = presenter.list()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_load_data_returns_empty_dict(self, presenter):
        """load_dataが空辞書を返すことを確認"""
        result = presenter.load_data()
        assert result == {}


class TestCRUDPresenterErrorHandling:
    """CRUDPresenterのエラーハンドリングテスト"""

    @pytest.fixture
    def failing_presenter(self):
        """エラーを発生させるPresenter"""

        class FailingCRUDPresenter(CRUDPresenter[dict]):
            def load_data(self) -> dict:
                return {}

            def create(self, **kwargs):
                raise ValueError("Create failed")

            def read(self, **kwargs):
                raise ValueError("Read failed")

            def update(self, **kwargs):
                raise ValueError("Update failed")

            def delete(self, **kwargs):
                raise ValueError("Delete failed")

            def list(self, **kwargs):
                raise ValueError("List failed")

        with patch.object(Container, "create_for_environment") as mock_create:
            mock_container = MagicMock(spec=Container)
            mock_create.return_value = mock_container
            return FailingCRUDPresenter()

    def test_handle_action_create_error(self, failing_presenter):
        """createアクションでエラーが発生した場合の処理を確認"""
        with pytest.raises(Exception) as exc_info:
            failing_presenter.handle_action("create")
        assert "Create failed" in str(exc_info.value)

    def test_handle_action_read_error(self, failing_presenter):
        """readアクションでエラーが発生した場合の処理を確認"""
        with pytest.raises(Exception) as exc_info:
            failing_presenter.handle_action("read", id=1)
        assert "Read failed" in str(exc_info.value)

    def test_handle_action_update_error(self, failing_presenter):
        """updateアクションでエラーが発生した場合の処理を確認"""
        with pytest.raises(Exception) as exc_info:
            failing_presenter.handle_action("update", id=1)
        assert "Update failed" in str(exc_info.value)

    def test_handle_action_delete_error(self, failing_presenter):
        """deleteアクションでエラーが発生した場合の処理を確認"""
        with pytest.raises(Exception) as exc_info:
            failing_presenter.handle_action("delete", id=1)
        assert "Delete failed" in str(exc_info.value)

    def test_handle_action_list_error(self, failing_presenter):
        """listアクションでエラーが発生した場合の処理を確認"""
        with pytest.raises(Exception) as exc_info:
            failing_presenter.handle_action("list")
        assert "List failed" in str(exc_info.value)
