"""BasePresenterとCRUDPresenterのテスト"""

from unittest.mock import MagicMock

import pytest

from src.infrastructure.di.container import Container


class ConcretePresenter:
    """テスト用の具象プレゼンタークラス"""

    def __init__(self, container=None):
        self.container = container or MagicMock()
        self.logger = MagicMock()

    def load_data(self):
        return []

    def handle_action(self, action: str, **kwargs):
        if action == "test":
            return "success"
        raise ValueError(f"Unknown action: {action}")

    def handle_error(self, error, context=""):
        error_msg = f"Error in {context}: {str(error)}" if context else str(error)
        self.logger.error(error_msg, exc_info=True)
        return error_msg

    def validate_input(self, data: dict, required_fields: list) -> tuple[bool, str]:
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return False, f"必須フィールドが不足しています: {', '.join(missing_fields)}"
        return True, ""


class ConcreteCRUDPresenter(ConcretePresenter):
    """テスト用の具象CRUDプレゼンタークラス"""

    def handle_action(self, action: str, **kwargs):
        if action == "create":
            return self.create(**kwargs)
        elif action == "read":
            return self.read(**kwargs)
        elif action == "update":
            return self.update(**kwargs)
        elif action == "delete":
            return self.delete(**kwargs)
        elif action == "list":
            return self.list(**kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def create(self, **kwargs):
        return {"id": 1, **kwargs}

    def read(self, **kwargs):
        return {"id": kwargs.get("id")}

    def update(self, **kwargs):
        return {"updated": True, **kwargs}

    def delete(self, **kwargs):
        return {"deleted": True, "id": kwargs.get("id")}

    def list(self, **kwargs):
        return [{"id": 1}, {"id": 2}]


class TestBasePresenter:
    """BasePresenterの基本機能テスト"""

    @pytest.fixture
    def presenter(self):
        """ConcretePresenterのインスタンス"""
        return ConcretePresenter()

    def test_init_creates_instance(self, presenter):
        """Presenterが正しく初期化されることを確認"""
        assert presenter is not None
        assert presenter.container is not None
        assert presenter.logger is not None

    def test_init_with_container(self):
        """コンテナを指定して初期化できることを確認"""
        mock_container = MagicMock(spec=Container)
        presenter = ConcretePresenter(container=mock_container)
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


class TestCRUDPresenter:
    """CRUDPresenterのテスト"""

    @pytest.fixture
    def presenter(self):
        """ConcreteCRUDPresenterのインスタンス"""
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
        with pytest.raises(ValueError, match="Unknown action"):
            presenter.handle_action("unknown")

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
