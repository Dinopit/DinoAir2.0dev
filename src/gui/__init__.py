"""
GUI Package - PySide6 Interface Components
Contains the main window, pages, and reusable components
"""

from .main_window import MainWindow
from .components import (
    TopBar, Sidebar, StatusBar, 
    ArtifactsWidget, ChatInputWidget, ChatHistoryWidget, 
    TabbedContentWidget, ChatTabWidget
)
from .pages import NotesPage, CalendarPage, TasksPage, SettingsPage

__all__ = [
    'MainWindow',
    'TopBar', 
    'Sidebar', 
    'StatusBar',
    'ArtifactsWidget',
    'ChatInputWidget',
    'ChatHistoryWidget',
    'TabbedContentWidget',
    'ChatTabWidget',
    'NotesPage',
    'CalendarPage', 
    'TasksPage',
    'SettingsPage'
]
