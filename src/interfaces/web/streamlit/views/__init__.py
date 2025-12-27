"""Streamlit views for web interface."""

from .conferences_view import render_conferences_page
from .conversations_speakers_view import render_conversations_speakers_page
from .conversations_view import render_conversations_page
from .governing_bodies_view import render_governing_bodies_page
from .llm_history_view import render_llm_history_page
from .meetings_view import render_meetings_page
from .parliamentary_groups_view import render_parliamentary_groups_page
from .political_parties_view import render_political_parties_page
from .politicians_view import render_politicians_page
from .processes_view import render_processes_page


__all__ = [
    "render_conferences_page",
    "render_conversations_page",
    "render_conversations_speakers_page",
    "render_governing_bodies_page",
    "render_llm_history_page",
    "render_meetings_page",
    "render_parliamentary_groups_page",
    "render_political_parties_page",
    "render_politicians_page",
    "render_processes_page",
]
