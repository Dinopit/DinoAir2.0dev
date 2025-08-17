"""
Projects Page - Comprehensive project management interface with hierarchical organization
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QMessageBox, QLabel, QPushButton, QFrame,
    QMenu, QTreeWidget, QTreeWidgetItem, QTabWidget,
    QListWidget, QListWidgetItem, QDialog, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QDialogButtonBox,
    QColorDialog, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer, QMimeData, QByteArray
from PySide6.QtGui import (
    QAction, QKeySequence, QShortcut, QColor, QIcon,
    QDragEnterEvent, QDropEvent, QDragMoveEvent
)

try:
    from src.database.projects_db import ProjectsDatabase
except ImportError:
    from database.projects_db import ProjectsDatabase
# Test-friendly aliases for patch targets used by integration tests
try:
    from ...database.notes_db import NotesDatabase as _NotesDatabase
except Exception:  # pragma: no cover
    class _NotesDatabase:
        pass
try:
    from ...database.artifacts_db import ArtifactsDatabase as _ArtifactsDatabase
except Exception:  # pragma: no cover
    class _ArtifactsDatabase:
        pass
try:
    from ...database.appointments_db import AppointmentsDatabase as _AppointmentsDatabase
except Exception:  # pragma: no cover
    class _AppointmentsDatabase:
        pass

# Re-export for tests expecting module attributes
NotesDatabase = _NotesDatabase
ArtifactsDatabase = _ArtifactsDatabase
AppointmentsDatabase = _AppointmentsDatabase
try:
    from src.models.project import Project, ProjectStatus, ProjectStatistics
    from src.utils.colors import DinoPitColors
    from src.utils.logger import Logger
    from src.utils.scaling import get_scaling_helper
    from src.utils.window_state import window_state_manager
except ImportError:
    from models.project import Project, ProjectStatus, ProjectStatistics
    from utils.colors import DinoPitColors
    from utils.logger import Logger
    from utils.scaling import get_scaling_helper
    from utils.window_state import window_state_manager
from ..components.tag_input_widget import TagInputWidget
try:
    from src.tools.projects_service import ProjectsService
    from src.tools.notes_service import NotesService
    from src.tools.artifacts_service import ArtifactsService
except ImportError:
    from tools.projects_service import ProjectsService
    from tools.notes_service import NotesService
    from tools.artifacts_service import ArtifactsService


class IconSelectorDialog(QDialog):
    """Dialog for selecting project icons"""
    
    def __init__(self, parent=None, current_icon: Optional[str] = None):
        super().__init__(parent)
        self.selected_icon = current_icon
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the icon selector UI"""
        self.setWindowTitle("Select Project Icon")
        self.setModal(True)
        
        # Set minimum size
        self.setMinimumWidth(self._scaling_helper.scaled_size(400))
        self.setMinimumHeight(self._scaling_helper.scaled_size(300))
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Icon grid
        icon_grid = QGridLayout()
        icon_grid.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Common project icons
        icons = [
            "📁", "📂", "📋", "📊", "📈", "📉", "💼", "🎯",
            "🚀", "💡", "🔧", "⚙️", "🛠️", "📱", "💻", "🖥️",
            "🌐", "🏗️", "🏠", "🏢", "🏭", "🎨", "🎬", "🎵",
            "📚", "📖", "✏️", "🖊️", "📝", "📄", "📑", "📌",
            "📍", "🔍", "🔎", "🔒", "🔓", "🔑", "⏰", "📅",
            "📆", "⏱️", "⌚", "💰", "💳", "💎", "🎁", "🎉",
            "🎊", "🏆", "🥇", "🥈", "🥉", "⭐", "🌟", "✨",
            "🔥", "💥", "⚡", "🌈", "☀️", "🌙", "🌍", "🌎"
        ]
        
        row = 0
        col = 0
        for icon in icons:
            btn = QPushButton(icon)
            btn.setFixedSize(
                self._scaling_helper.scaled_size(50),
                self._scaling_helper.scaled_size(50)
            )
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 24px;
                    border: 2px solid {DinoPitColors.SOFT_ORANGE};
                    border-radius: 5px;
                    background-color: {DinoPitColors.MAIN_BACKGROUND};
                }}
                QPushButton:hover {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
                    border-color: {DinoPitColors.DINOPIT_ORANGE};
                }}
                QPushButton:pressed {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                }}
            """)
            btn.clicked.connect(lambda checked, i=icon: self.select_icon(i))
            icon_grid.addWidget(btn, row, col)
            
            col += 1
            if col > 7:  # 8 columns
                col = 0
                row += 1
        
        # Scroll area for icons
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        icon_widget = QWidget()
        icon_widget.setLayout(icon_grid)
        scroll_area.setWidget(icon_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Style buttons
        buttons.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        
        layout.addWidget(buttons)
        
        # Set dialog style
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
    def select_icon(self, icon: str):
        """Select an icon and close dialog"""
        self.selected_icon = icon
        self.accept()
        
    def get_selected_icon(self) -> Optional[str]:
        """Get the selected icon"""
        return self.selected_icon


class ProjectDialog(QDialog):
    """Dialog for creating/editing projects"""
    
    def __init__(self, parent=None, project: Optional[Project] = None,
                 all_projects: Optional[List[Project]] = None):
        super().__init__(parent)
        self.logger = Logger()
        self._project = project
        self.all_projects = all_projects or []
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
        if project:
            self.load_project(project)
            
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("New Project" if not self._project else "Edit Project")
        self.setModal(True)
        
        # Set minimum size
        self.setMinimumWidth(self._scaling_helper.scaled_size(500))
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(self._scaling_helper.scaled_size(12))
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Project name
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")
        self.name_input.setPlaceholderText("Enter project name...")
        form_layout.addRow("Name:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter project description (optional)")
        self.description_input.setMaximumHeight(
            self._scaling_helper.scaled_size(100)
        )
        form_layout.addRow("Description:", self.description_input)
        
        # Parent project
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("No Parent", None)
        
        # Add all projects except the current one (to avoid circular references)
        current_id = self._project.id if self._project else None
        for project in self.all_projects:
            if project.id != current_id:
                self.parent_combo.addItem(
                    f"{project.get_display_icon()} {project.name}",
                    project.id
                )
        form_layout.addRow("Parent Project:", self.parent_combo)
        
        # Status
        self.status_combo = QComboBox()
        for status in ProjectStatus:
            self.status_combo.addItem(status.value.capitalize(), status.value)
        form_layout.addRow("Status:", self.status_combo)
        
        # Visual customization group
        visual_group = QGroupBox("Visual Customization")
        visual_layout = QGridLayout(visual_group)
        visual_layout.setColumnStretch(1, 1)
        visual_layout.setColumnStretch(3, 1)
        visual_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Color selection
        color_label = QLabel("Color:")
        color_label.setStyleSheet("color: #FFFFFF;")
        color_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.color_button = QPushButton("Select Color")
        self.color_button.setStyleSheet("color: #FFFFFF;")
        self.color_button.clicked.connect(self._select_color)
        self.selected_color = None
        self._update_color_button()
        
        # Icon selection
        icon_label = QLabel("Icon:")
        icon_label.setStyleSheet("color: #FFFFFF;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.icon_button = QPushButton("Select Icon")
        self.icon_button.setStyleSheet("color: #FFFFFF;")
        self.icon_button.clicked.connect(self._select_icon)
        self.selected_icon = "📁"
        self._update_icon_button()
        
        # Add to grid layout
        visual_layout.addWidget(color_label, 0, 0)
        visual_layout.addWidget(self.color_button, 0, 1)
        visual_layout.addWidget(icon_label, 0, 2)
        visual_layout.addWidget(self.icon_button, 0, 3)
        
        form_layout.addRow(visual_group)
        
        # Tags
        self.tags_input = TagInputWidget()
        form_layout.addRow("Tags:", self.tags_input)
        
        layout.addLayout(form_layout)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Style buttons
        buttons.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        
        layout.addWidget(buttons)
        
        # Apply dialog styles
        self._apply_styles()
        
    def _apply_styles(self):
        """Apply dialog styles"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            QLabel {{
                color: {DinoPitColors.PRIMARY_TEXT};
                min-width: 100px;
            }}
            QLineEdit, QTextEdit {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
                background-color: #1F2937;
            }}
            QComboBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
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
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
        """)
        
    def _select_color(self):
        """Open color picker dialog"""
        initial_color = QColor(self.selected_color) if self.selected_color else QColor("#007bff")
        color = QColorDialog.getColor(initial_color, self, "Select Project Color")
        
        if color.isValid():
            self.selected_color = color.name()
            self._update_color_button()
            
    def _update_color_button(self):
        """Update color button appearance"""
        color = self.selected_color or "#007bff"
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
    def _select_icon(self):
        """Open icon selector dialog"""
        dialog = IconSelectorDialog(self, self.selected_icon)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_icon = dialog.get_selected_icon()
            self._update_icon_button()
            
    def _update_icon_button(self):
        """Update icon button display"""
        self.icon_button.setText(f"{self.selected_icon} Select Icon")
        
    def load_project(self, project: Project):
        """Load project data into the form"""
        self.name_input.setText(project.name)
        self.description_input.setPlainText(project.description or "")
        
        # Set parent project
        if project.parent_project_id:
            parent_index = self.parent_combo.findData(project.parent_project_id)
            if parent_index >= 0:
                self.parent_combo.setCurrentIndex(parent_index)
                
        # Set status
        status_index = self.status_combo.findData(project.status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
            
        # Set visual customization
        self.selected_color = project.color
        self._update_color_button()
        
        self.selected_icon = project.icon or "📁"
        self._update_icon_button()
        
        # Set tags
        if project.tags:
            self.tags_input.set_tags(project.tags)
            
    def get_project_data(self) -> Project:
        """Get project data from the form"""
        if self._project:
            project = self._project
        else:
            project = Project()
            
        project.name = self.name_input.text().strip()
        project.description = self.description_input.toPlainText().strip() or None
        project.parent_project_id = self.parent_combo.currentData()
        project.status = self.status_combo.currentData()
        project.color = self.selected_color
        project.icon = self.selected_icon
        project.tags = self.tags_input.get_tags()
        project.updated_at = datetime.now()
        
        # Handle status-specific timestamps
        if project.status == ProjectStatus.COMPLETED.value and not project.completed_at:
            project.completed_at = datetime.now()
        elif project.status == ProjectStatus.ARCHIVED.value and not project.archived_at:
            project.archived_at = datetime.now()
        elif project.status == ProjectStatus.ACTIVE.value:
            project.completed_at = None
            project.archived_at = None
            
        return project


class ProjectsPage(QWidget):
    """Projects page with hierarchical project management"""
    
    # Signals
    project_selected = Signal(Project)
    
    # New signals for cross-page navigation
    request_navigate_to_artifact = Signal(str)  # artifact_id
    request_navigate_to_note = Signal(str)      # note_id
    request_navigate_to_event = Signal(str)     # event_id
    
    # Signals for real-time updates when unlinking items
    artifact_unlinked_from_project = Signal(str, str)  # artifact_id, project_id
    note_unlinked_from_project = Signal(str, str)     # note_id, project_id
    event_unlinked_from_project = Signal(str, str)    # event_id, project_id
    
    def __init__(self):
        """Initialize the projects page"""
        super().__init__()
        self.logger = Logger()
        
        # Initialize database
        try:
            from src.database.initialize_db import DatabaseManager
        except ImportError:
            from database.initialize_db import DatabaseManager
        db_manager = DatabaseManager()
        self.projects_db = ProjectsDatabase(db_manager)
        try:
            self.projects_service = ProjectsService(db_manager=db_manager)
        except Exception:
            self.projects_service = None  # pragma: no cover
        
        # Initialize notes database for cross-referencing
        try:
            from src.database.notes_db import NotesDatabase
        except ImportError:
            from database.notes_db import NotesDatabase
        self.notes_db = NotesDatabase()
        try:
            self.notes_service = NotesService(notes_db=self.notes_db)
        except Exception:
            self.notes_service = None  # pragma: no cover
        
        # Initialize artifacts database for cross-referencing
        try:
            from src.database.artifacts_db import ArtifactsDatabase
        except ImportError:
            from database.artifacts_db import ArtifactsDatabase
        self.artifacts_db = ArtifactsDatabase(db_manager)
        try:
            self.artifacts_service = ArtifactsService(db_manager=db_manager, artifacts_db=self.artifacts_db)
        except Exception:
            self.artifacts_service = None  # pragma: no cover
        
        # Initialize appointments database for calendar integration
        try:
            from src.database.appointments_db import AppointmentsDatabase
        except ImportError:
            from database.appointments_db import AppointmentsDatabase
        self.appointments_db = AppointmentsDatabase(db_manager)
        
        self._current_project: Optional[Project] = None
        self._projects_cache: Dict[str, Project] = {}
        self._scaling_helper = get_scaling_helper()
        
        # Refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_projects)
        self._refresh_timer.setInterval(300000)  # Refresh every 5 minutes
        self._refresh_timer.start()
        
        self.setup_ui()
        self._load_projects()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def setup_ui(self):
        """Setup the projects page UI"""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar
        toolbar_container = self._create_toolbar()
        layout.addWidget(toolbar_container)
        
        # Create splitter for tree and details
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                width: 2px;
            }}
        """)
        
        # Left panel - Project tree
        tree_panel = self._create_tree_panel()
        self.main_splitter.addWidget(tree_panel)
        
        # Right panel - Project details
        details_panel = self._create_details_panel()
        self.main_splitter.addWidget(details_panel)
        
        # Set initial splitter proportions
        self._update_splitter_sizes()
        
        # Connect splitter moved signal
        self.main_splitter.splitterMoved.connect(self._save_splitter_state)
        
        # Restore splitter state if available
        self._restore_splitter_state()
        
        layout.addWidget(self.main_splitter)
        
    def _create_toolbar(self) -> QWidget:
        """Create the toolbar with actions"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Use font metrics for spacing
        font_metrics = self.fontMetrics()
        spacing = font_metrics.height() // 4
        container_layout.setSpacing(spacing)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self._update_toolbar_style()
        
        # New Project action
        new_action = QAction("✚ New Project", self)
        new_action.triggered.connect(self._create_new_project)
        self.toolbar.addAction(new_action)
        
        # Edit action
        self.edit_action = QAction("✏️ Edit", self)
        self.edit_action.triggered.connect(self._edit_project)
        self.edit_action.setEnabled(False)
        self.toolbar.addAction(self.edit_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_project)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)
        
        # Archive action
        self.archive_action = QAction("📦 Archive", self)
        self.archive_action.triggered.connect(self._archive_project)
        self.archive_action.setEnabled(False)
        self.toolbar.addAction(self.archive_action)
        
        # Add spacer
        self.spacer1 = QWidget()
        self.spacer1.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer1)
        
        # Refresh action
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self._refresh_projects)
        self.toolbar.addAction(refresh_action)
        
        # Add search
        from PySide6.QtWidgets import QLineEdit
        self.spacer2 = QWidget()
        self.spacer2.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer2)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search projects...")
        self.search_input.setMaximumWidth(self._scaling_helper.scaled_size(200))
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 15px;
                padding: 5px 15px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.search_input.textChanged.connect(self._filter_projects)
        self.toolbar.addWidget(self.search_input)
        
        # Stretch spacer
        stretch_spacer = QWidget()
        stretch_spacer.setSizePolicy(
            stretch_spacer.sizePolicy().horizontalPolicy(),
            stretch_spacer.sizePolicy().verticalPolicy()
        )
        self.toolbar.addWidget(stretch_spacer)
        
        # Project count label
        self.count_label = QLabel("0 projects")
        self.count_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;")
        self.toolbar.addWidget(self.count_label)
        
        container_layout.addWidget(self.toolbar)
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        return container
        
    def _create_tree_panel(self) -> QWidget:
        """Create the project tree panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tree header
        header = QLabel("Projects")
        header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Project tree
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderHidden(True)
        self.project_tree.setAcceptDrops(True)
        self.project_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.project_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 0 0 5px 5px;
            }}
            QTreeWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 8px;
            }}
            QTreeWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QTreeWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
        # Connect signals
        self.project_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.project_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.project_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        
        layout.addWidget(self.project_tree)
        
        return panel
        
    def _create_details_panel(self) -> QWidget:
        """Create the project details panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Details header
        self.details_header = QLabel("Select a project to view details")
        self.details_header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        self.details_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.details_header)
        
        # Project info section
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 15px;
        """)
        
        info_layout = QFormLayout(info_frame)
        
        # Project details labels
        self.info_labels = {}
        fields = [
            ('name', 'Name:'),
            ('description', 'Description:'),
            ('status', 'Status:'),
            ('parent', 'Parent Project:'),
            ('created', 'Created:'),
            ('updated', 'Last Updated:')
        ]
        
        for field_id, field_label in fields:
            # Style the field label
            field_label_widget = QLabel(field_label)
            field_label_widget.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
                min-width: 120px;
            """)
            
            # Style the value label
            label = QLabel("-")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
            
            info_layout.addRow(field_label_widget, label)
            self.info_labels[field_id] = label
            
        layout.addWidget(info_frame)
        
        # Statistics widget
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 15px;
        """)
        
        stats_layout = QGridLayout(stats_frame)
        
        self.stats_widgets = {}
        stat_items = [
            ('notes', '📝 Notes:', 0, 0),
            ('artifacts', '📦 Artifacts:', 0, 1),
            ('events', '📅 Events:', 1, 0),
            ('subprojects', '📁 Subprojects:', 1, 1)
        ]
        
        for stat_id, stat_label, row, col in stat_items:
            label = QLabel(stat_label)
            label.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
                font-size: 14px;
            """)
            value = QLabel("0")
            value.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 24px;
                font-weight: bold;
            """)
            stats_layout.addWidget(label, row * 2, col)
            stats_layout.addWidget(value, row * 2 + 1, col)
            self.stats_widgets[stat_id] = value
            
        layout.addWidget(stats_frame)
        
        # Associated items tabs
        self.items_tabs = QTabWidget()
        self.items_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 8px 16px;
                margin-right: 2px;
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-bottom: none;
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
            }}
        """)
        
        # Notes tab
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        
        self.notes_list = QListWidget()
        self.notes_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
            }}
            QListWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 10px;
                border-bottom: 1px solid {DinoPitColors.SOFT_ORANGE};
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        self.notes_list.itemDoubleClicked.connect(self._view_note)
        notes_layout.addWidget(self.notes_list)
        
        # Notes actions
        notes_actions = QHBoxLayout()
        view_note_btn = QPushButton("👁️ View")
        view_note_btn.setStyleSheet("color: #FFFFFF;")
        view_note_btn.clicked.connect(self._view_note)
        unlink_note_btn = QPushButton("🔗 Unlink")
        unlink_note_btn.setStyleSheet("color: #FFFFFF;")
        unlink_note_btn.clicked.connect(self._unlink_note)
        
        for btn in [view_note_btn, unlink_note_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DinoPitColors.DINOPIT_FIRE};
                }}
            """)
            
        notes_actions.addWidget(view_note_btn)
        notes_actions.addWidget(unlink_note_btn)
        notes_actions.addStretch()
        notes_layout.addLayout(notes_actions)
        
        self.items_tabs.addTab(notes_widget, "Notes")
        
        # Artifacts tab
        artifacts_widget = QWidget()
        artifacts_layout = QVBoxLayout(artifacts_widget)
        
        self.artifacts_list = QListWidget()
        self.artifacts_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
            }}
            QListWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 10px;
                border-bottom: 1px solid {DinoPitColors.SOFT_ORANGE};
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        self.artifacts_list.itemDoubleClicked.connect(self._view_artifact)
        artifacts_layout.addWidget(self.artifacts_list)
        
        # Artifacts actions
        artifacts_actions = QHBoxLayout()
        view_artifact_btn = QPushButton("👁️ View")
        view_artifact_btn.setStyleSheet("color: #FFFFFF;")
        view_artifact_btn.clicked.connect(self._view_artifact)
        unlink_artifact_btn = QPushButton("🔗 Unlink")
        unlink_artifact_btn.setStyleSheet("color: #FFFFFF;")
        unlink_artifact_btn.clicked.connect(self._unlink_artifact)
        
        for btn in [view_artifact_btn, unlink_artifact_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DinoPitColors.DINOPIT_FIRE};
                }}
            """)
            
        artifacts_actions.addWidget(view_artifact_btn)
        artifacts_actions.addWidget(unlink_artifact_btn)
        artifacts_actions.addStretch()
        artifacts_layout.addLayout(artifacts_actions)
        
        self.items_tabs.addTab(artifacts_widget, "Artifacts")
        
        # Calendar/Events tab
        events_widget = QWidget()
        events_layout = QVBoxLayout(events_widget)
        
        self.events_list = QListWidget()
        self.events_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: none;
            }}
            QListWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 10px;
                border-bottom: 1px solid {DinoPitColors.SOFT_ORANGE};
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        self.events_list.itemDoubleClicked.connect(self._view_event)
        events_layout.addWidget(self.events_list)
        
        # Calendar actions
        events_actions = QHBoxLayout()
        view_event_btn = QPushButton("👁️ View")
        view_event_btn.setStyleSheet("color: #FFFFFF;")
        view_event_btn.clicked.connect(self._view_event)
        unlink_event_btn = QPushButton("🔗 Unlink")
        unlink_event_btn.setStyleSheet("color: #FFFFFF;")
        unlink_event_btn.clicked.connect(self._unlink_event)
        
        for btn in [view_event_btn, unlink_event_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DinoPitColors.DINOPIT_FIRE};
                }}
            """)
            
        events_actions.addWidget(view_event_btn)
        events_actions.addWidget(unlink_event_btn)
        events_actions.addStretch()
        events_layout.addLayout(events_actions)
        
        self.items_tabs.addTab(events_widget, "Calendar")
        
        layout.addWidget(self.items_tabs)
        
        return panel
        
    def _load_projects(self):
        """Load all projects from database"""
        try:
            self._projects_cache.clear()
            self.project_tree.clear()
            
            # Get all projects
            if getattr(self, 'projects_service', None):
                projects = self.projects_service.get_projects(filter_active_only=False)
            else:
                projects = self.projects_db.get_all_projects()
            
            # Build project cache
            for project in projects:
                self._projects_cache[project.id] = project
                
            # Build tree hierarchy
            root_projects = [p for p in projects if not p.parent_project_id]
            
            # Create tree items
            for project in root_projects:
                self._add_project_to_tree(project, self.project_tree)
                
            # Update count
            self.count_label.setText(f"{len(projects)} project{'s' if len(projects) != 1 else ''}")
            
            # Expand all items by default
            self.project_tree.expandAll()
            
        except Exception as e:
            self.logger.error(f"Failed to load projects: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load projects: {str(e)}"
            )
            
    def _add_project_to_tree(self, project: Project, parent_item):
        """Add project to tree recursively"""
        # Create tree item
        item_text = f"{project.get_display_icon()} {project.name}"
        if project.status != ProjectStatus.ACTIVE.value:
            item_text += f" ({project.get_status_display()})"
            
        if isinstance(parent_item, QTreeWidget):
            item = QTreeWidgetItem([item_text])
            parent_item.addTopLevelItem(item)
        else:
            item = QTreeWidgetItem(parent_item, [item_text])
            
        # Store project reference
        item.setData(0, Qt.ItemDataRole.UserRole, project.id)
        
        # Set color if specified
        if project.color:
            from PySide6.QtGui import QBrush
            brush = QBrush(QColor(project.color))
            item.setForeground(0, brush)
            
        # Add children recursively
        children = [p for p in self._projects_cache.values() 
                    if p.parent_project_id == project.id]
        for child in children:
            self._add_project_to_tree(child, item)
            
    def _on_tree_selection_changed(self):
        """Handle project selection in tree"""
        selected_items = self.project_tree.selectedItems()
        
        if selected_items:
            item = selected_items[0]
            project_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            if project_id and project_id in self._projects_cache:
                self._current_project = self._projects_cache[project_id]
                self._show_project_details(self._current_project)
                
                # Enable actions
                self.edit_action.setEnabled(True)
                self.delete_action.setEnabled(True)
                self.archive_action.setEnabled(
                    self._current_project.status != ProjectStatus.ARCHIVED.value
                )
                
                # Emit signal
                self.project_selected.emit(self._current_project)
            else:
                self._clear_project_details()
        else:
            self._current_project = None
            self._clear_project_details()
            
    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem):
        """Handle tree item double-click"""
        project_id = item.data(0, Qt.ItemDataRole.UserRole)
        if project_id and project_id in self._projects_cache:
            self._current_project = self._projects_cache[project_id]
            self._edit_project()
            
    def _show_project_details(self, project: Project):
        """Show project details in right panel"""
        # Update header
        self.details_header.setText(f"{project.get_display_icon()} {project.name}")
        
        # Update info
        self.info_labels['name'].setText(project.name)
        self.info_labels['description'].setText(project.description or "No description")
        self.info_labels['status'].setText(project.get_status_display())
        
        if project.parent_project_id and project.parent_project_id in self._projects_cache:
            parent = self._projects_cache[project.parent_project_id]
            self.info_labels['parent'].setText(f"{parent.get_display_icon()} {parent.name}")
        else:
            self.info_labels['parent'].setText("No parent project")
            
        self.info_labels['created'].setText(
            project.created_at.strftime("%Y-%m-%d %H:%M") if project.created_at else "-"
        )
        self.info_labels['updated'].setText(
            project.updated_at.strftime("%Y-%m-%d %H:%M") if project.updated_at else "-"
        )
        
        # Get and display statistics
        stats = self.projects_db.get_project_statistics(project.id)
        self.stats_widgets['notes'].setText(str(stats.total_notes))
        self.stats_widgets['artifacts'].setText(str(stats.total_artifacts))
        self.stats_widgets['events'].setText(str(stats.total_calendar_events))
        self.stats_widgets['subprojects'].setText(str(stats.child_project_count))
        
        # Load associated items
        self._load_project_notes(project.id)
        self._load_project_artifacts(project.id)
        self._load_project_events(project.id)
        
    def _clear_project_details(self):
        """Clear project details display"""
        self.details_header.setText("Select a project to view details")
        
        for label in self.info_labels.values():
            label.setText("-")
            
        for widget in self.stats_widgets.values():
            widget.setText("0")
            
        self.notes_list.clear()
        self.artifacts_list.clear()
        self.events_list.clear()
        
        # Disable actions
        self.edit_action.setEnabled(False)
        self.delete_action.setEnabled(False)
        self.archive_action.setEnabled(False)
        
    def _load_project_notes(self, project_id: str):
        """Load notes associated with project"""
        self.notes_list.clear()
        
        try:
            # Get notes for this project
            notes = self.notes_db.get_notes_by_project(project_id)
            
            for note in notes:
                item_text = f"📝 {note.title}"
                if note.tags:
                    item_text += f" [{', '.join(note.tags[:2])}]"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, note.id)
                self.notes_list.addItem(item)
                
            if not notes:
                item = QListWidgetItem("No notes associated with this project")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.notes_list.addItem(item)
                
        except Exception as e:
            self.logger.error(f"Failed to load project notes: {str(e)}")
            
    def _create_new_project(self):
        """Create a new project"""
        dialog = ProjectDialog(self, all_projects=list(self._projects_cache.values()))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                project = dialog.get_project_data()
                
                # Validate
                if not project.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Project",
                        "Please enter a name for the project."
                    )
                    return
                    
                # Create project
                result = self.projects_db.create_project(project)
                
                if result["success"]:
                    self.logger.info(f"Created new project: {project.id}")
                    
                    # Refresh display
                    self._load_projects()
                    
                    # Select the new project
                    self._select_project_in_tree(project.id)
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to create project: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create project: {str(e)}"
                )
                
    def _edit_project(self):
        """Edit the selected project"""
        if not self._current_project:
            return
            
        dialog = ProjectDialog(
            self,
            project=self._current_project,
            all_projects=list(self._projects_cache.values())
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                updated_project = dialog.get_project_data()
                
                # Validate
                if not updated_project.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Project",
                        "Please enter a name for the project."
                    )
                    return
                    
                # Update project
                updates = updated_project.to_dict()
                # Remove fields that shouldn't be updated directly
                for field in ['id', 'created_at']:
                    updates.pop(field, None)
                    
                success = self.projects_db.update_project(
                    updated_project.id,
                    updates
                )
                
                if success:
                    self.logger.info(f"Updated project: {updated_project.id}")
                    
                    # Refresh display
                    self._load_projects()
                    
                    # Restore selection
                    self._select_project_in_tree(updated_project.id)
                else:
                    raise Exception("Failed to update project")
                    
            except Exception as e:
                self.logger.error(f"Failed to update project: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update project: {str(e)}"
                )
                
    def _delete_project(self):
        """Delete the selected project"""
        if not self._current_project:
            return
            
        # Check if project has children
        children = [p for p in self._projects_cache.values() 
                    if p.parent_project_id == self._current_project.id]
        
        message = f"Are you sure you want to delete '{self._current_project.name}'?"
        if children:
            message += f"\n\nThis project has {len(children)} subproject(s). They will become root projects."
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Project",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.projects_db.delete_project(
                    self._current_project.id,
                    cascade=False  # Don't cascade delete children
                )
                
                if success:
                    self.logger.info(f"Deleted project: {self._current_project.id}")
                    
                    # Clear selection
                    self._current_project = None
                    self._clear_project_details()
                    
                    # Refresh display
                    self._load_projects()
                else:
                    raise Exception("Failed to delete project")
                    
            except Exception as e:
                self.logger.error(f"Failed to delete project: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete project: {str(e)}"
                )
                
    def _archive_project(self):
        """Archive the selected project"""
        if not self._current_project:
            return
            
        try:
            updates = {"status": ProjectStatus.ARCHIVED.value}
            success = self.projects_db.update_project(
                self._current_project.id,
                updates
            )
            
            if success:
                self.logger.info(f"Archived project: {self._current_project.id}")
                
                # Refresh display
                self._load_projects()
                
                # Restore selection
                self._select_project_in_tree(self._current_project.id)
            else:
                raise Exception("Failed to archive project")
                
        except Exception as e:
            self.logger.error(f"Failed to archive project: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to archive project: {str(e)}"
            )
            
    def _filter_projects(self, search_text: str):
        """Filter projects based on search text"""
        if not search_text:
            # Show all items
            self._show_all_tree_items(self.project_tree.invisibleRootItem())
        else:
            # Hide non-matching items
            self._filter_tree_items(self.project_tree.invisibleRootItem(), search_text.lower())
            
    def _show_all_tree_items(self, parent_item):
        """Show all tree items recursively"""
        if parent_item != self.project_tree.invisibleRootItem():
            parent_item.setHidden(False)
            
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            self._show_all_tree_items(child)
            
    def _filter_tree_items(self, parent_item, search_text: str) -> bool:
        """Filter tree items based on search text, returns True if any child matches"""
        if parent_item == self.project_tree.invisibleRootItem():
            # Root item - just process children
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                self._filter_tree_items(child, search_text)
            return False
            
        # Check if this item matches
        project_id = parent_item.data(0, Qt.ItemDataRole.UserRole)
        matches = False
        
        if project_id and project_id in self._projects_cache:
            project = self._projects_cache[project_id]
            matches = (search_text in project.name.lower() or
                       (project.description and search_text in project.description.lower()) or
                       any(search_text in tag.lower() for tag in project.tags))
                       
        # Check children
        child_matches = False
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if self._filter_tree_items(child, search_text):
                child_matches = True
                
        # Show item if it matches or has matching children
        parent_item.setHidden(not (matches or child_matches))
        
        return matches or child_matches
        
    def _select_project_in_tree(self, project_id: str):
        """Select a project in the tree by ID"""
        # Find the tree item
        item = self._find_tree_item(self.project_tree.invisibleRootItem(), project_id)
        if item:
            self.project_tree.setCurrentItem(item)
            self.project_tree.scrollToItem(item)
            
    def _find_tree_item(self, parent_item, project_id: str) -> Optional[QTreeWidgetItem]:
        """Find tree item by project ID"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == project_id:
                return child
                
            # Check children recursively
            found = self._find_tree_item(child, project_id)
            if found:
                return found
                
        return None
        
    def _load_project_artifacts(self, project_id: str):
        """Load artifacts for the selected project"""
        try:
            # Get artifacts for the project
            # For now, this is a placeholder - actual implementation depends on artifacts_db
            self.artifacts_list.clear()
            
            # Get artifacts for the project
            artifacts = self.artifacts_db.get_artifacts_by_project(project_id)
            
            for artifact in artifacts:
                item = QListWidgetItem(f"🎨 {artifact.name}")
                item.setData(Qt.ItemDataRole.UserRole, artifact.id)
                self.artifacts_list.addItem(item)
                
            if not artifacts:
                item = QListWidgetItem("No artifacts linked to this project")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.artifacts_list.addItem(item)
                
        except Exception as e:
            self.logger.error(f"Failed to load project artifacts: {str(e)}")
    
    def _load_project_events(self, project_id: str):
        """Load calendar events for the selected project"""
        try:
            # Get events for the project
            # For now, this is a placeholder - actual implementation depends on calendar_db
            self.events_list.clear()
            
            events = self.appointments_db.get_events_by_project(project_id)
            
            for event in events:
                event_text = f"📅 {event.title}"
                if event.event_date:
                    event_text += f" - {event.event_date}"
                item = QListWidgetItem(event_text)
                item.setData(Qt.ItemDataRole.UserRole, event.id)
                self.events_list.addItem(item)
                
            if not events:
                item = QListWidgetItem("No calendar events linked to this project")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.events_list.addItem(item)
                
        except Exception as e:
            self.logger.error(f"Failed to load project events: {str(e)}")
            
    def _view_note(self):
        """View the selected note"""
        current_item = self.notes_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            note_id = current_item.data(Qt.ItemDataRole.UserRole)
            # Emit signal to open note in notes page
            self.request_navigate_to_note.emit(note_id)
    
    def _unlink_note(self):
        """Unlink the selected note from the project"""
        current_item = self.notes_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            note_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            reply = QMessageBox.question(
                self, "Unlink Note",
                "Are you sure you want to unlink this note from the project?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Update the note to remove project association
                    self.notes_db.update_note_project(note_id, None)
                    
                    # Emit signal for real-time updates
                    if self._current_project:
                        self.note_unlinked_from_project.emit(note_id, self._current_project.id)
                        self._load_project_notes(self._current_project.id)
                    
                    self.logger.info(f"Unlinked note {note_id} from project")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to unlink note: {str(e)}")
    
    def _view_artifact(self):
        """View the selected artifact"""
        current_item = self.artifacts_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            artifact_id = current_item.data(Qt.ItemDataRole.UserRole)
            # Emit signal to open artifact in artifacts page
            self.request_navigate_to_artifact.emit(artifact_id)
    
    def _unlink_artifact(self):
        """Unlink the selected artifact from the project"""
        current_item = self.artifacts_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            artifact_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            reply = QMessageBox.question(
                self, "Unlink Artifact",
                "Are you sure you want to unlink this artifact from the project?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Update the artifact to remove project association
                    if getattr(self, 'artifacts_service', None):
                        self.artifacts_service.link_artifact_to_project(artifact_id, None)
                    else:
                        self.artifacts_db.update_artifact_project(artifact_id, None)
                    
                    # Invalidate caches so other views pick up the change
                    if getattr(self, 'artifacts_service', None):
                        try:
                            self.artifacts_service.invalidate_cache()
                        except Exception:
                            pass
                    # Emit signal for real-time updates
                    if self._current_project:
                        self.artifact_unlinked_from_project.emit(artifact_id, self._current_project.id)
                        self._load_project_artifacts(self._current_project.id)
                    
                    self.logger.info(f"Unlinked artifact {artifact_id} from project")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to unlink artifact: {str(e)}")
    
    def _view_event(self):
        """View the selected calendar event"""
        current_item = self.events_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            event_id = current_item.data(Qt.ItemDataRole.UserRole)
            # Emit signal to open event in calendar page
            self.request_navigate_to_event.emit(event_id)
    
    def _unlink_event(self):
        """Unlink the selected calendar event from the project"""
        current_item = self.events_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole):
            event_id = current_item.data(Qt.ItemDataRole.UserRole)
            
            reply = QMessageBox.question(
                self, "Unlink Event",
                "Are you sure you want to unlink this calendar event from the project?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Update the event to remove project association
                    self.appointments_db.update_event(event_id, {'project_id': None})
                    
                    # Emit signal for real-time updates
                    if self._current_project:
                        self.event_unlinked_from_project.emit(event_id, self._current_project.id)
                        self._load_project_events(self._current_project.id)
                    
                    self.logger.info(f"Unlinked event {event_id} from project")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to unlink event: {str(e)}")
            
    def _show_tree_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.project_tree.itemAt(position)
        if not item:
            return
            
        project_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not project_id or project_id not in self._projects_cache:
            return
            
        project = self._projects_cache[project_id]
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
            }}
            QMenu::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                color: white;
            }}
        """)
        
        # Edit action
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(self._edit_project)
        menu.addAction(edit_action)
        
        # New subproject action
        new_sub_action = QAction("✚ New Subproject", self)
        new_sub_action.triggered.connect(lambda: self._create_subproject(project))
        menu.addAction(new_sub_action)
        
        menu.addSeparator()
        
        # Status actions
        if project.status != ProjectStatus.ACTIVE.value:
            activate_action = QAction("✅ Mark Active", self)
            activate_action.triggered.connect(
                lambda: self._update_project_status(project, ProjectStatus.ACTIVE.value)
            )
            menu.addAction(activate_action)
            
        if project.status != ProjectStatus.COMPLETED.value:
            complete_action = QAction("🏁 Mark Completed", self)
            complete_action.triggered.connect(
                lambda: self._update_project_status(project, ProjectStatus.COMPLETED.value)
            )
            menu.addAction(complete_action)
            
        if project.status != ProjectStatus.ARCHIVED.value:
            archive_action = QAction("📦 Archive", self)
            archive_action.triggered.connect(
                lambda: self._update_project_status(project, ProjectStatus.ARCHIVED.value)
            )
            menu.addAction(archive_action)
            
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self._delete_project)
        menu.addAction(delete_action)
        
        menu.exec(self.project_tree.mapToGlobal(position))
        
    def _create_subproject(self, parent_project: Project):
        """Create a new subproject"""
        dialog = ProjectDialog(self, all_projects=list(self._projects_cache.values()))
        # Pre-set the parent
        parent_index = dialog.parent_combo.findData(parent_project.id)
        if parent_index >= 0:
            dialog.parent_combo.setCurrentIndex(parent_index)
            
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                project = dialog.get_project_data()
                project.parent_project_id = parent_project.id
                
                # Validate
                if not project.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Project",
                        "Please enter a name for the project."
                    )
                    return
                    
                # Create project
                result = self.projects_db.create_project(project)
                
                if result["success"]:
                    self.logger.info(f"Created new subproject: {project.id}")
                    
                    # Refresh display
                    self._load_projects()
                    
                    # Select the new project
                    self._select_project_in_tree(project.id)
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to create subproject: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create subproject: {str(e)}"
                )
                
    def _update_project_status(self, project: Project, new_status: str):
        """Update project status"""
        try:
            updates = {"status": new_status}
            success = self.projects_db.update_project(project.id, updates)
            
            if success:
                self.logger.info(f"Updated project status: {project.id} -> {new_status}")
                
                # Refresh display
                self._load_projects()
                
                # Restore selection
                self._select_project_in_tree(project.id)
            else:
                raise Exception("Failed to update project status")
                
        except Exception as e:
            self.logger.error(f"Failed to update project status: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update project status: {str(e)}"
            )
            
    def _refresh_projects(self):
        """Refresh projects display"""
        self._load_projects()
        
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+N for new project
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self._create_new_project)
        
        # Delete key for delete
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._delete_project)
        
        # Ctrl+E for edit
        edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        edit_shortcut.activated.connect(self._edit_project)
        
        # F5 for refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._refresh_projects)
        
        # Ctrl+F for search focus
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_input.setFocus)
        
    def _update_splitter_sizes(self):
        """Set splitter proportions based on window width"""
        total_width = self.width()
        self.main_splitter.setSizes([
            int(total_width * 0.35),  # 35% for tree
            int(total_width * 0.65)   # 65% for details
        ])
        
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if hasattr(self, 'main_splitter'):
            # Don't update sizes if we have restored state
            if not hasattr(self, '_state_restored'):
                self._update_splitter_sizes()
                
    def _save_splitter_state(self):
        """Save the splitter state"""
        window_state_manager.save_splitter_from_widget(
            "projects_main", self.main_splitter
        )
        
    def _restore_splitter_state(self):
        """Restore the splitter state"""
        window_state_manager.restore_splitter_to_widget(
            "projects_main", self.main_splitter
        )
        self._state_restored = True
        
    def _update_toolbar_style(self):
        """Update toolbar style with current scaling"""
        s = self._scaling_helper
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: none;
                padding: {s.scaled_size(5)}px;
                spacing: {s.scaled_size(10)}px;
            }}
            QToolButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: {s.scaled_size(8)}px {s.scaled_size(16)}px;
                font-weight: bold;
                margin-right: {s.scaled_size(5)}px;
            }}
            QToolButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QToolButton:pressed {{
                background-color: #E55A2B;
            }}
            QToolButton:disabled {{
                background-color: #666666;
                color: #999999;
            }}
        """)
        
    def _update_spacer_widths(self):
        """Update spacer widths with current scaling"""
        spacer_width = self._scaling_helper.scaled_size(20)
        if hasattr(self, 'spacer1'):
            self.spacer1.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer2'):
            self.spacer2.setFixedWidth(spacer_width)
            
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes"""
        # Update toolbar style
        self._update_toolbar_style()
        
        # Update spacer widths
        self._update_spacer_widths()
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasFormat("application/x-project"):
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move event"""
        if event.mimeData().hasFormat("application/x-project"):
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event for project reorganization"""
        # TODO: Implement drag and drop for project hierarchy reorganization
        pass
    
    def apply_project_filter(self, project_id: Optional[str]):
        """Apply project filter by selecting a specific project
        
        Args:
            project_id: The project ID to select, or None to clear selection
        """
        if project_id:
            # Find and select the project in the tree
            self._select_project_in_tree(project_id)
        else:
            # Clear selection
            self.project_tree.clearSelection()
            self._current_project = None
            self._clear_project_details()
    
    def navigate_to_project(self, project_id: str):
        """Navigate to and select a specific project
        
        Args:
            project_id: The project ID to navigate to
        """
        # Find and select the project
        self._select_project_in_tree(project_id)
