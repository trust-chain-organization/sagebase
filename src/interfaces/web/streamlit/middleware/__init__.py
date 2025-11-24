"""Middleware modules for Streamlit application.

This package provides authentication middleware for protecting routes.
"""

from src.interfaces.web.streamlit.auth.google_sign_in import render_login_page
from src.interfaces.web.streamlit.middleware.auth_middleware import require_auth

__all__ = ["require_auth", "render_login_page"]
