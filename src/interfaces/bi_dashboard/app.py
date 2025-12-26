"""BI Dashboard POC - Main Application.

This is a proof-of-concept for data coverage dashboard using Plotly Dash.
It demonstrates:
- Code-based dashboard definition
- PostgreSQL integration
- Docker deployment
- Clean Architecture compatibility
"""

import sys

from pathlib import Path

from dash import Dash

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from callbacks.data_callbacks import register_callbacks
from layouts.main_layout import create_layout


def create_app() -> Dash:
    """Create and configure the Dash application.

    Returns:
        Dash: Configured Dash application instance
    """
    app = Dash(
        __name__,
        title="Polibase データカバレッジダッシュボード",
        suppress_callback_exceptions=True,
    )

    # Set layout
    app.layout = create_layout()

    # Register callbacks
    register_callbacks(app)

    return app


def main() -> None:
    """Run the Dash application."""
    app = create_app()
    app.run_server(host="0.0.0.0", port=8050, debug=True)


if __name__ == "__main__":
    main()
