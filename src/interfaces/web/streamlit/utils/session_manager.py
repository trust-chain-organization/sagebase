"""Session state management for Streamlit.

This module provides a centralized way to manage Streamlit session state,
abstracting away direct access to st.session_state.
"""

from typing import Any, TypeVar

import streamlit as st


T = TypeVar("T")


class SessionManager:
    """Manages Streamlit session state in a type-safe way."""

    def __init__(self, namespace: str = ""):
        """Initialize session manager.

        Args:
            namespace: Optional namespace to prefix all keys
        """
        self.namespace = namespace

    def _get_key(self, key: str) -> str:
        """Get the full key with namespace.

        Args:
            key: The base key

        Returns:
            Full key with namespace prefix
        """
        if self.namespace:
            return f"{self.namespace}_{key}"
        return key

    def get(self, key: str, default: T | None = None) -> T | None:
        """Get a value from session state.

        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist

        Returns:
            The value from session state or default
        """
        full_key = self._get_key(key)
        return st.session_state.get(full_key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in session state.

        Args:
            key: The key to set
            value: The value to store
        """
        full_key = self._get_key(key)
        st.session_state[full_key] = value

    def delete(self, key: str) -> None:
        """Delete a value from session state.

        Args:
            key: The key to delete
        """
        full_key = self._get_key(key)
        if full_key in st.session_state:
            del st.session_state[full_key]

    def exists(self, key: str) -> bool:
        """Check if a key exists in session state.

        Args:
            key: The key to check

        Returns:
            True if the key exists, False otherwise
        """
        full_key = self._get_key(key)
        return full_key in st.session_state

    def clear(self) -> None:
        """Clear all keys in this namespace."""
        if self.namespace:
            # Clear only keys with this namespace
            keys_to_delete = [
                key
                for key in st.session_state.keys()
                if isinstance(key, str) and key.startswith(f"{self.namespace}_")
            ]
            for key in keys_to_delete:
                del st.session_state[key]
        else:
            # Clear all session state (use with caution)
            st.session_state.clear()

    def get_or_create(self, key: str, factory: Any) -> Any:
        """Get a value from session state or create it if it doesn't exist.

        Args:
            key: The key to retrieve
            factory: Callable or value to create if key doesn't exist

        Returns:
            The value from session state
        """
        full_key = self._get_key(key)
        if full_key not in st.session_state:
            if callable(factory):
                st.session_state[full_key] = factory()
            else:
                st.session_state[full_key] = factory
        return st.session_state[full_key]


class FormSessionManager(SessionManager):
    """Specialized session manager for form states."""

    def __init__(self, form_name: str):
        """Initialize form session manager.

        Args:
            form_name: Name of the form (used as namespace)
        """
        super().__init__(namespace=f"form_{form_name}")
        self.form_name = form_name

    def get_form_data(self) -> dict[str, Any]:
        """Get all form data.

        Returns:
            Dictionary of all form fields
        """
        form_data = {}
        prefix = f"{self.namespace}_field_"
        for key in st.session_state:
            if key.startswith(prefix):
                field_name = key[len(prefix) :]
                form_data[field_name] = st.session_state[key]
        return form_data

    def set_form_field(self, field_name: str, value: Any) -> None:
        """Set a form field value.

        Args:
            field_name: Name of the form field
            value: Value to set
        """
        self.set(f"field_{field_name}", value)

    def get_form_field(self, field_name: str, default: Any = None) -> Any:
        """Get a form field value.

        Args:
            field_name: Name of the form field
            default: Default value if field doesn't exist

        Returns:
            The field value or default
        """
        return self.get(f"field_{field_name}", default)

    def clear_form(self) -> None:
        """Clear all form fields."""
        prefix = f"{self.namespace}_field_"
        keys_to_delete = [
            key
            for key in st.session_state.keys()
            if isinstance(key, str) and key.startswith(prefix)
        ]
        for key in keys_to_delete:
            del st.session_state[key]

    def is_form_dirty(self) -> bool:
        """Check if form has unsaved changes.

        Returns:
            True if form has been modified, False otherwise
        """
        return bool(self.get("is_dirty", False))

    def mark_dirty(self) -> None:
        """Mark form as having unsaved changes."""
        self.set("is_dirty", True)

    def mark_clean(self) -> None:
        """Mark form as having no unsaved changes."""
        self.set("is_dirty", False)
