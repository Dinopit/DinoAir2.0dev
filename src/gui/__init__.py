"""
GUI Package - PySide6 Interface Components
Contains the main window, pages, and reusable components
"""

from .main_window import MainWindow
from .components import (
    TopBar, Sidebar, StatusBar, 
    ArtifactsWidget, ChatInputWidget, EnhancedChatHistoryWidget, 
    TabbedContentWidget, EnhancedChatTabWidget
)
from .pages import NotesPage, CalendarPage, TasksPage, SettingsPage

__all__ = [
    'MainWindow',
    'TopBar', 
    'Sidebar', 
    'StatusBar',
    'ArtifactsWidget',
    'ChatInputWidget',
    'EnhancedChatHistoryWidget',
    'TabbedContentWidget',
    'EnhancedChatTabWidget',
    'NotesPage',
    'CalendarPage', 
    'TasksPage',
    'SettingsPage'
]
