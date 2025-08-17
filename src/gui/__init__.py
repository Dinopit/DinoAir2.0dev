"""
GUI Package - lightweight initializer

Purpose:
- Export `MainWindow` without importing all pages/components at import time.
- Reduce import-time side effects and risk of circular imports.

Consumers should import specific components directly, e.g.:
    from src.gui.components.tabbed_content import TabbedContentWidget
    from src.gui.pages.notes_page import NotesPage
"""

from .main_window import MainWindow

__all__ = [
    'MainWindow',
]
