"""
Project Combo Box Widget
A reusable combo box for project selection with hierarchical display
"""

from typing import Optional, List, Dict
from PySide6.QtWidgets import QComboBox, QWidget
from PySide6.QtCore import Signal, QTimer

from src.tools.projects_service import ProjectsService
from src.models.project import Project, ProjectStatus
from src.utils.logger import Logger
from src.utils.colors import DinoPitColors


class ProjectComboBox(QComboBox):
    """Combo box for project selection with hierarchy support"""
    
    # Signal emitted when project selection changes
    project_changed = Signal(str)  # Emits project_id or None
    
    def __init__(self, parent: Optional[QWidget] = None, 
                 include_no_project: bool = True,
                 filter_active_only: bool = True,
                 projects_service: Optional[ProjectsService] = None):
        """Initialize the project combo box
        
        Args:
            parent: Parent widget
            include_no_project: Whether to include "(No Project)" option
            filter_active_only: Whether to show only active projects
        """
        super().__init__(parent)
        self.logger = Logger()
        self._include_no_project = include_no_project
        self._filter_active_only = filter_active_only
        self._projects_cache = {}

        # Injected service to decouple GUI from DB layer
        self._projects_service = projects_service or ProjectsService()
        
        # Setup UI
        self._setup_ui()
        
        # Load projects
        self.refresh_projects()
        
        # Connect signals
        self.currentIndexChanged.connect(self._on_selection_changed)
        
        # Setup auto-refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh_projects)
        self._refresh_timer.setInterval(30000)  # Refresh every 30 seconds
        self._refresh_timer.start()
        
    def _setup_ui(self):
        """Setup the UI appearance"""
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
                min-width: 200px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
                outline: none;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                selection-background-color: {DinoPitColors.DINOPIT_ORANGE};
                selection-color: white;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QComboBox QAbstractItemView::item {{
                padding: 5px;
                min-height: 25px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        
    def refresh_projects(self):
        """Refresh the project list from database"""
        try:
            # Remember current selection
            current_project_id = self.currentData()
            
            # Clear existing items
            self.clear()
            self._projects_cache.clear()
            
            # Add "No Project" option if enabled
            if self._include_no_project:
                self.addItem("(No Project)", None)
            
            # Get projects from service with filtering
            projects = self._projects_service.get_projects(self._filter_active_only)
            
            # Build project hierarchy
            root_projects = [p for p in projects if not p.parent_project_id]
            
            # Sort root projects by name
            root_projects.sort(key=lambda p: p.name.lower())
            
            # Add projects hierarchically
            for root_project in root_projects:
                self._add_project_hierarchically(root_project, projects, 0)
            
            # Restore selection if possible
            if current_project_id is not None:
                index = self.findData(current_project_id)
                if index >= 0:
                    self.setCurrentIndex(index)
            elif self._include_no_project:
                self.setCurrentIndex(0)  # Select "(No Project)"
                
        except Exception as e:
            self.logger.error(f"Failed to refresh projects: {str(e)}")
            
    def _add_project_hierarchically(self, project: Project,
                                    all_projects: List[Project],
                                    level: int):
        """Add a project and its children to the combo box
        
        Args:
            project: The project to add
            all_projects: List of all projects for finding children
            level: Indentation level (0 for root)
        """
        # Create display text with indentation
        indent = "  " * level
        
        # Add icon and color indicator
        icon = project.icon or "📁"
        display_text = f"{indent}{icon} {project.name}"
        
        # Add status indicator if not active
        if project.status != ProjectStatus.ACTIVE.value:
            status_text = project.get_status_display()
            display_text += f" ({status_text})"
        
        # Add item
        self.addItem(display_text, project.id)
        
        # Cache the project
        self._projects_cache[project.id] = project
        
        # Note: QComboBox item styling is limited, color indicator
        # is shown in the icon instead
        
        # Find and add children
        children = [p for p in all_projects
                    if p.parent_project_id == project.id]
        children.sort(key=lambda p: p.name.lower())
        
        for child in children:
            self._add_project_hierarchically(child, all_projects, level + 1)
            
    def _on_selection_changed(self, index: int):
        """Handle selection change"""
        if index >= 0:
            project_id = self.currentData()
            self.project_changed.emit(project_id)
    
    def set_project_id_silent(self, project_id: Optional[str]):
        """Set project without emitting signals (for synchronization)
        
        Args:
            project_id: Project ID to select, or None for no project
        """
        self.blockSignals(True)
        self.set_project_id(project_id)
        self.blockSignals(False)
    
    def is_syncing(self) -> bool:
        """Check if currently syncing to prevent circular updates
        
        Returns:
            True if signals are blocked
        """
        return self.signalsBlocked()
            
    def get_selected_project_id(self) -> Optional[str]:
        """Get the currently selected project ID"""
        return self.currentData()
        
    def get_selected_project(self) -> Optional[Project]:
        """Get the currently selected project object"""
        project_id = self.get_selected_project_id()
        if project_id and project_id in self._projects_cache:
            return self._projects_cache[project_id]
        return None
        
    def set_project_id(self, project_id: Optional[str]):
        """Set the selected project by ID
        
        Args:
            project_id: Project ID to select, or None for no project
        """
        if project_id is None and self._include_no_project:
            self.setCurrentIndex(0)
        else:
            index = self.findData(project_id)
            if index >= 0:
                self.setCurrentIndex(index)
            elif self._include_no_project:
                self.setCurrentIndex(0)  # Fall back to no project
                
    def add_project_filter(self, status: Optional[str] = None):
        """Add additional filtering to projects
        
        Args:
            status: Filter by specific status, or None for all
        """
        # This would require refactoring to store filter state
        # and apply during refresh_projects
        pass
        
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, '_refresh_timer'):
            self._refresh_timer.stop()


class ProjectFilterWidget(QWidget):
    """Widget for filtering by project with multiple selection support"""
    
    # Signal emitted when filter changes
    filter_changed = Signal(list)  # Emits list of project_ids
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the project filter widget"""
        super().__init__(parent)
        # TODO: Implement multi-select project filter widget
        # This could use QListWidget with checkboxes for multiple selection
        pass