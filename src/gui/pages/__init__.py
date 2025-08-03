"""
GUI Pages Package
Individual page components for different application sections
"""

from .notes_page import NotesPage
from .calendar_page import CalendarPage
from .tasks_page import ProjectsPage as TasksPage  # Actual class name
from .settings_page import SettingsPage
from .file_search_page import FileSearchPage

__all__ = [
    'NotesPage', 'CalendarPage', 'TasksPage',
    'SettingsPage', 'FileSearchPage'
]
