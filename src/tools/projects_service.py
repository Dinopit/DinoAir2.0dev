"""
Projects Service
Provides a thin, testable layer over ProjectsDatabase for GUI consumers.
"""

from typing import List, Optional

from src.database.initialize_db import DatabaseManager
from src.database.projects_db import ProjectsDatabase
from src.models.project import Project, ProjectStatus
from src.utils.logger import Logger


class ProjectsService:
    """Service for retrieving and filtering projects.

    This keeps database access out of the GUI layer and offers
    a small, focused API that can be mocked in tests.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        projects_db: Optional[ProjectsDatabase] = None,
    ):
        self.logger = Logger()
        self._db_manager = db_manager or DatabaseManager()
        self._projects_db = projects_db or ProjectsDatabase(self._db_manager)

    def get_projects(self, filter_active_only: bool = True) -> List[Project]:
        """Return projects, optionally filtered to active ones.

        Args:
            filter_active_only: When True, only return ACTIVE projects.

        Returns:
            List of Project
        """
        try:
            projects = self._projects_db.get_all_projects()
            if filter_active_only:
                projects = [
                    p for p in projects
                    if p.status == ProjectStatus.ACTIVE.value
                ]
            return projects
        except Exception as e:
            self.logger.error(f"Failed to get projects: {e}")
            return []
