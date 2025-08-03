"""
Artifacts Page - Comprehensive artifact management interface
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import mimetypes
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QMessageBox, QLabel, QPushButton, QFrame,
    QMenu, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QDialog, QFormLayout, QTextEdit, QComboBox,
    QDialogButtonBox, QGroupBox, QCheckBox,
    QTabWidget, QListWidget, QListWidgetItem, QFileDialog,
    QPlainTextEdit
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import (
    QAction, QKeySequence, QShortcut, QDragEnterEvent, QDropEvent,
    QDragMoveEvent
)

from ...database.artifacts_db import ArtifactsDatabase
from ...models.artifact import (
    Artifact, ArtifactType, ArtifactStatus, ArtifactCollection
)
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper
from ...utils.window_state import window_state_manager
from ..components.tag_input_widget import TagInputWidget
from ..components.project_combo_box import ProjectComboBox


class CollectionDialog(QDialog):
    """Dialog for creating/editing collections"""
    
    def __init__(self, parent=None, collection: Optional[ArtifactCollection] = None):
        super().__init__(parent)
        self.logger = Logger()
        self._collection = collection
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
        if collection:
            self.load_collection(collection)
            
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("New Collection" if not self._collection else "Edit Collection")
        self.setModal(True)
        
        # Set minimum size with scaling
        self.setMinimumWidth(self._scaling_helper.scaled_size(400))
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(self._scaling_helper.scaled_size(8))
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter collection name...")
        form_layout.addRow("Name:", self.name_input)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter description (optional)")
        self.description_input.setMaximumHeight(
            self._scaling_helper.scaled_size(80)
        )
        form_layout.addRow("Description:", self.description_input)
        
        # Tags
        self.tags_input = TagInputWidget()
        form_layout.addRow("Tags:", self.tags_input)
        
        # Encryption
        self.encrypted_check = QCheckBox("Enable encryption for this collection")
        form_layout.addRow("Security:", self.encrypted_check)
        
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
            QPushButton:pressed {{
                background-color: #E55A2B;
            }}
        """)
        
        layout.addWidget(buttons)
        
        # Set dialog style
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
            QLabel {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit, QTextEdit {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QCheckBox {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 3px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
    def load_collection(self, collection: ArtifactCollection):
        """Load collection data into the form"""
        self.name_input.setText(collection.name)
        self.description_input.setPlainText(collection.description or "")
        if collection.tags:
            self.tags_input.set_tags(collection.tags)
        self.encrypted_check.setChecked(collection.is_encrypted)
        
    def get_collection_data(self) -> ArtifactCollection:
        """Get collection data from the form"""
        if self._collection:
            collection = self._collection
        else:
            collection = ArtifactCollection()
            
        collection.name = self.name_input.text().strip()
        collection.description = self.description_input.toPlainText().strip() or None
        collection.tags = self.tags_input.get_tags()
        collection.is_encrypted = self.encrypted_check.isChecked()
        collection.updated_at = datetime.now()
        
        return collection


class ArtifactDialog(QDialog):
    """Dialog for creating/editing artifacts"""
    
    def __init__(self, parent=None, artifact: Optional[Artifact] = None,
                 collections: Optional[List[ArtifactCollection]] = None):
        super().__init__(parent)
        self.logger = Logger()
        self._artifact = artifact
        self.collections = collections or []
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
        if artifact:
            self.load_artifact(artifact)
            
    def setup_ui(self):
        """Setup the dialog UI"""
        self.setWindowTitle("New Artifact" if not self._artifact else "Edit Artifact")
        self.setModal(True)
        
        # Set minimum size with scaling
        self.setMinimumWidth(self._scaling_helper.scaled_size(600))
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Create tab widget for different content types
        self.tab_widget = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        general_layout.setSpacing(self._scaling_helper.scaled_size(8))
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter artifact name...")
        general_layout.addRow("Name:", self.name_input)
        
        # Type
        self.type_combo = QComboBox()
        for artifact_type in ArtifactType:
            self.type_combo.addItem(
                artifact_type.value.capitalize(), artifact_type.value
            )
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        general_layout.addRow("Type:", self.type_combo)
        
        # Collection
        self.collection_combo = QComboBox()
        self.collection_combo.addItem("No Collection", None)
        for collection in self.collections:
            self.collection_combo.addItem(collection.name, collection.id)
        general_layout.addRow("Collection:", self.collection_combo)
        
        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Enter description (optional)")
        self.description_input.setMaximumHeight(
            self._scaling_helper.scaled_size(100)
        )
        general_layout.addRow("Description:", self.description_input)
        
        # Tags
        self.tags_input = TagInputWidget()
        general_layout.addRow("Tags:", self.tags_input)
        
        # Status
        self.status_combo = QComboBox()
        for status in ArtifactStatus:
            self.status_combo.addItem(status.value.capitalize(), status.value)
        general_layout.addRow("Status:", self.status_combo)
        
        # Project selector
        self.project_combo = ProjectComboBox(self, include_no_project=True)
        general_layout.addRow("Project:", self.project_combo)
        
        self.tab_widget.addTab(general_tab, "General")
        
        # Content tab
        content_tab = QWidget()
        content_layout = QVBoxLayout(content_tab)
        
        # Content input based on type
        self.content_stack = QTabWidget()
        
        # Text content
        self.text_content = QPlainTextEdit()
        self.text_content.setPlaceholderText("Enter text content...")
        self.content_stack.addTab(self.text_content, "Text")
        
        # Code content with syntax selector
        code_widget = QWidget()
        code_layout = QVBoxLayout(code_widget)
        
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Language:"))
        self.code_language = QComboBox()
        self.code_language.addItems([
            "Python", "JavaScript", "TypeScript", "Java", "C++", 
            "C#", "Go", "Rust", "HTML", "CSS", "SQL", "JSON", "XML"
        ])
        language_layout.addWidget(self.code_language)
        language_layout.addStretch()
        code_layout.addLayout(language_layout)
        
        self.code_content = QPlainTextEdit()
        self.code_content.setPlaceholderText("Enter code...")
        self.code_content.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)
        code_layout.addWidget(self.code_content)
        
        self.content_stack.addTab(code_widget, "Code")
        
        # File upload
        file_widget = QWidget()
        file_layout = QVBoxLayout(file_widget)
        
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        file_layout.addWidget(self.file_path_label)
        
        file_button_layout = QHBoxLayout()
        self.choose_file_btn = QPushButton("Choose File...")
        self.choose_file_btn.clicked.connect(self._choose_file)
        file_button_layout.addWidget(self.choose_file_btn)
        file_button_layout.addStretch()
        file_layout.addLayout(file_button_layout)
        
        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        file_layout.addWidget(self.file_info_label)
        file_layout.addStretch()
        
        self.content_stack.addTab(file_widget, "File")
        
        content_layout.addWidget(self.content_stack)
        
        self.tab_widget.addTab(content_tab, "Content")
        
        # Security tab
        security_tab = QWidget()
        security_layout = QFormLayout(security_tab)
        
        self.encrypt_content_check = QCheckBox("Encrypt content")
        security_layout.addRow("Encryption:", self.encrypt_content_check)
        
        self.encrypt_fields_group = QGroupBox("Fields to encrypt")
        encrypt_fields_layout = QVBoxLayout(self.encrypt_fields_group)
        
        self.encrypt_name_check = QCheckBox("Name")
        self.encrypt_description_check = QCheckBox("Description")
        self.encrypt_tags_check = QCheckBox("Tags")
        
        encrypt_fields_layout.addWidget(self.encrypt_name_check)
        encrypt_fields_layout.addWidget(self.encrypt_description_check)
        encrypt_fields_layout.addWidget(self.encrypt_tags_check)
        
        security_layout.addRow(self.encrypt_fields_group)
        
        self.tab_widget.addTab(security_tab, "Security")
        
        layout.addWidget(self.tab_widget)
        
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
            QPushButton:pressed {{
                background-color: #E55A2B;
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
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 5px;
                color: {DinoPitColors.PRIMARY_TEXT};
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
            }}
            QTabBar::tab:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
            }}
            QCheckBox {{
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 3px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
            }}
            QCheckBox::indicator:checked {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QGroupBox {{
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
            }}
        """)
        
    def _on_type_changed(self, index):
        """Handle artifact type change"""
        artifact_type = self.type_combo.currentData()
        
        # Show appropriate content tab
        if artifact_type == ArtifactType.TEXT.value:
            self.content_stack.setCurrentIndex(0)
        elif artifact_type == ArtifactType.CODE.value:
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(2)
            
    def _choose_file(self):
        """Choose file for artifact"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose File",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            self.file_path = file_path
            path = Path(file_path)
            self.file_path_label.setText(f"File: {path.name}")
            
            # Get file info
            size = path.stat().st_size
            size_str = self._format_size(size)
            mime_type, _ = mimetypes.guess_type(str(path))
            
            self.file_info_label.setText(
                f"Size: {size_str}\nType: {mime_type or 'Unknown'}"
            )
            
    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        size_value = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_value < 1024.0:
                return f"{size_value:.1f} {unit}"
            size_value /= 1024.0
        return f"{size_value:.1f} TB"
        
    def load_artifact(self, artifact: Artifact):
        """Load artifact data into the form"""
        self.name_input.setText(artifact.name)
        
        # Set type
        type_index = self.type_combo.findData(artifact.content_type)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)
            
        # Set collection
        if artifact.collection_id:
            collection_index = self.collection_combo.findData(artifact.collection_id)
            if collection_index >= 0:
                self.collection_combo.setCurrentIndex(collection_index)
                
        self.description_input.setPlainText(artifact.description or "")
        
        if artifact.tags:
            self.tags_input.set_tags(artifact.tags)
            
        # Set status
        status_index = self.status_combo.findData(artifact.status)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
            
        # Set project
        if hasattr(artifact, 'project_id'):
            self.project_combo.set_project_id(artifact.project_id)
        else:
            self.project_combo.set_project_id(None)
            
        # Load content
        if artifact.content:
            if artifact.content_type == ArtifactType.TEXT.value:
                self.text_content.setPlainText(artifact.content)
            elif artifact.content_type == ArtifactType.CODE.value:
                self.code_content.setPlainText(artifact.content)
                
        # Load encryption settings
        if artifact.encrypted_fields:
            self.encrypt_content_check.setChecked('content' in artifact.encrypted_fields)
            self.encrypt_name_check.setChecked('name' in artifact.encrypted_fields)
            self.encrypt_description_check.setChecked('description' in artifact.encrypted_fields)
            self.encrypt_tags_check.setChecked('tags' in artifact.encrypted_fields)
            
    def get_artifact_data(self) -> tuple[Artifact, Optional[bytes]]:
        """Get artifact data from the form"""
        if self._artifact:
            artifact = self._artifact
        else:
            artifact = Artifact()
            
        artifact.name = self.name_input.text().strip()
        artifact.content_type = self.type_combo.currentData()
        artifact.collection_id = self.collection_combo.currentData()
        artifact.description = self.description_input.toPlainText().strip() or None
        artifact.tags = self.tags_input.get_tags()
        artifact.status = self.status_combo.currentData()
        artifact.project_id = self.project_combo.get_selected_project_id()
        
        # Get content based on type
        content_bytes = None
        if artifact.content_type == ArtifactType.TEXT.value:
            artifact.content = self.text_content.toPlainText()
        elif artifact.content_type == ArtifactType.CODE.value:
            artifact.content = self.code_content.toPlainText()
            # Store language in metadata
            artifact.metadata = artifact.metadata or {}
            artifact.metadata['language'] = self.code_language.currentText()
        elif hasattr(self, 'file_path'):
            # Read file content
            with open(self.file_path, 'rb') as f:
                content_bytes = f.read()
            artifact.mime_type, _ = mimetypes.guess_type(self.file_path)
            
        # Set encrypted fields
        encrypted_fields = []
        if self.encrypt_content_check.isChecked():
            encrypted_fields.append('content')
        if self.encrypt_name_check.isChecked():
            encrypted_fields.append('name')
        if self.encrypt_description_check.isChecked():
            encrypted_fields.append('description')
        if self.encrypt_tags_check.isChecked():
            encrypted_fields.append('tags')
        artifact.encrypted_fields = encrypted_fields
        
        # Update timestamp
        artifact.updated_at = datetime.now()
        
        return artifact, content_bytes


class ArtifactsPage(QWidget):
    """Artifacts page with comprehensive management features"""
    
    # Signals
    artifact_selected = Signal(Artifact)
    
    # New signals for coordination
    request_navigate_to_project = Signal(str)  # project_id
    project_filter_requested = Signal(str)     # project_id
    artifact_project_changed = Signal(str, str, str)  # artifact_id, old_project_id, new_project_id
    
    def __init__(self):
        """Initialize the artifacts page"""
        super().__init__()
        self.logger = Logger()
        
        # Initialize database
        from ...database.initialize_db import DatabaseManager
        db_manager = DatabaseManager()
        self.artifacts_db = ArtifactsDatabase(db_manager)
        
        # Initialize projects database for project info
        from ...database.projects_db import ProjectsDatabase
        self.projects_db = ProjectsDatabase(db_manager)
        
        self._current_artifact: Optional[Artifact] = None
        self._current_collection: Optional[str] = None
        self._current_project_filter: Optional[str] = None
        self._collections_cache: List[ArtifactCollection] = []
        self._projects_cache: Dict[str, Any] = {}  # Cache project info
        self._scaling_helper = get_scaling_helper()
        
        # Refresh timer
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._refresh_artifacts)
        self._refresh_timer.setInterval(300000)  # Refresh every 5 minutes
        self._refresh_timer.start()
        
        self.setup_ui()
        self._load_collections()
        self._load_projects_cache()
        self._load_artifacts()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def setup_ui(self):
        """Setup the artifacts page UI"""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar
        toolbar_container = self._create_toolbar()
        layout.addWidget(toolbar_container)
        
        # Create search bar
        search_container = self._create_search_bar()
        layout.addWidget(search_container)
        
        # Create splitter for tree and content
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                width: 2px;
            }}
        """)
        
        # Tree pane
        tree_pane = self._create_tree_pane()
        self.main_splitter.addWidget(tree_pane)
        
        # Content pane
        content_pane = self._create_content_pane()
        self.main_splitter.addWidget(content_pane)
        
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
        
        # New Artifact action
        new_action = QAction("✚ New Artifact", self)
        new_action.triggered.connect(self._create_new_artifact)
        self.toolbar.addAction(new_action)
        
        # Edit action
        self.edit_action = QAction("✏️ Edit", self)
        self.edit_action.triggered.connect(self._edit_artifact)
        self.edit_action.setEnabled(False)
        self.toolbar.addAction(self.edit_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_artifact)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)
        
        # Refresh action
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self._refresh_artifacts)
        self.toolbar.addAction(refresh_action)
        
        # Add spacer
        self.spacer1 = QWidget()
        self.spacer1.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer1)
        
        # New Collection action
        new_collection_action = QAction("📁 New Collection", self)
        new_collection_action.triggered.connect(self._create_new_collection)
        self.toolbar.addAction(new_collection_action)
        
        # Manage Collections action
        manage_collections_action = QAction("⚙️ Manage Collections", self)
        manage_collections_action.triggered.connect(self._manage_collections)
        self.toolbar.addAction(manage_collections_action)
        
        # Another spacer
        self.spacer2 = QWidget()
        self.spacer2.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer2)
        
        # Project selector
        self.project_label = QLabel("Project:")
        self.project_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT}; font-weight: bold;"
        )
        self.toolbar.addWidget(self.project_label)
        
        self.project_combo = ProjectComboBox(self, include_no_project=True)
        self.project_combo.project_changed.connect(
            self._on_project_filter_changed
        )
        self.toolbar.addWidget(self.project_combo)
        
        # View Project button (initially hidden)
        self.view_project_btn = QPushButton("👁️ View Project")
        self.view_project_btn.setVisible(False)
        # Connect later after method is defined
        self.view_project_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                margin-left: 10px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.toolbar.addWidget(self.view_project_btn)
        
        # Another spacer
        self.spacer3 = QWidget()
        self.spacer3.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer3)
        
        # Export action
        self.export_action = QAction("📤 Export", self)
        self.export_action.triggered.connect(self._export_artifact)
        self.export_action.setEnabled(False)
        self.toolbar.addAction(self.export_action)
        
        # Stretch spacer
        stretch_spacer = QWidget()
        stretch_spacer.setSizePolicy(
            stretch_spacer.sizePolicy().horizontalPolicy(),
            stretch_spacer.sizePolicy().verticalPolicy()
        )
        self.toolbar.addWidget(stretch_spacer)
        
        # Stats label
        self.stats_label = QLabel("0 artifacts")
        self.stats_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
        """)
        self.toolbar.addWidget(self.stats_label)
        
        container_layout.addWidget(self.toolbar)
        
        # Setup shortcuts
        self._setup_shortcuts()
        
        # Connect view project button
        self.view_project_btn.clicked.connect(self._view_project)
        
        return container
        
    def _create_search_bar(self) -> QWidget:
        """Create the search bar"""
        container = QWidget()
        container.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 10px;
        """)
        
        layout = QHBoxLayout(container)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search artifacts by name, description, or tags...")
        self.search_input.setStyleSheet(f"""
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 20px;
            padding: 8px 15px;
            color: {DinoPitColors.PRIMARY_TEXT};
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # Type filter
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", None)
        for artifact_type in ArtifactType:
            self.type_filter.addItem(
                artifact_type.value.capitalize(), artifact_type.value
            )
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        
        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItem("All Time", None)
        self.date_filter.addItem("Today", "today")
        self.date_filter.addItem("This Week", "week")
        self.date_filter.addItem("This Month", "month")
        self.date_filter.addItem("This Year", "year")
        self.date_filter.currentIndexChanged.connect(self._apply_filters)
        
        # Clear filters button
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 15px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        clear_btn.clicked.connect(self._clear_filters)
        
        layout.addWidget(self.search_input, 1)
        layout.addWidget(QLabel("Type:"))
        layout.addWidget(self.type_filter)
        layout.addWidget(QLabel("Date:"))
        layout.addWidget(self.date_filter)
        layout.addWidget(clear_btn)
        
        return container
        
    def _create_tree_pane(self) -> QWidget:
        """Create the tree pane for collections and artifacts"""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        
        # Tree header
        header = QLabel("Collections & Artifacts")
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
        
        # Tree widget
        self.artifact_tree = QTreeWidget()
        self.artifact_tree.setHeaderHidden(True)
        self.artifact_tree.setAcceptDrops(True)
        self.artifact_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.artifact_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 0 0 5px 5px;
            }}
            QTreeWidget::item {{
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 5px;
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
        self.artifact_tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.artifact_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.artifact_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.artifact_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        
        layout.addWidget(self.artifact_tree)
        
        return pane
        
    def _create_content_pane(self) -> QWidget:
        """Create the content pane for artifact details"""
        pane = QWidget()
        layout = QVBoxLayout(pane)
        
        # Content header
        self.content_header = QLabel("Select an artifact to view details")
        self.content_header.setStyleSheet(f"""
            background-color: {DinoPitColors.DINOPIT_ORANGE};
            color: white;
            padding: 10px;
            font-weight: bold;
            font-size: 16px;
            border-radius: 5px 5px 0 0;
        """)
        self.content_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.content_header)
        
        # Content tab widget
        self.content_tabs = QTabWidget()
        self.content_tabs.setStyleSheet(f"""
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
            }}
            QTabBar::tab:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
            }}
            QTabBar::tab:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        
        # Details tab
        details_widget = QWidget()
        details_layout = QFormLayout(details_widget)
        
        self.details_labels = {}
        fields = [
            ('name', 'Name:'),
            ('type', 'Type:'),
            ('status', 'Status:'),
            ('collection', 'Collection:'),
            ('size', 'Size:'),
            ('created', 'Created:'),
            ('updated', 'Updated:'),
            ('version', 'Version:')
        ]
        
        for field_id, field_label in fields:
            # Style the field label
            field_label_widget = QLabel(field_label)
            field_label_widget.setStyleSheet(f"""
                color: {DinoPitColors.PRIMARY_TEXT};
                font-weight: bold;
            """)
            
            # Style the value label
            label = QLabel("-")
            label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
            
            details_layout.addRow(field_label_widget, label)
            self.details_labels[field_id] = label
            
        self.content_tabs.addTab(details_widget, "Details")
        
        # Content viewer tab
        self.content_viewer = QTextEdit()
        self.content_viewer.setReadOnly(True)
        self.content_viewer.setStyleSheet(f"""
            background-color: {DinoPitColors.MAIN_BACKGROUND};
            border: none;
            color: {DinoPitColors.PRIMARY_TEXT};
        """)
        self.content_tabs.addTab(self.content_viewer, "Content")
        
        # Version history tab
        self.version_list = QListWidget()
        self.version_list.setStyleSheet(f"""
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
        """)
        self.version_list.itemDoubleClicked.connect(self._restore_version)
        self.content_tabs.addTab(self.version_list, "Version History")
        
        layout.addWidget(self.content_tabs)
        
        # Quick actions
        actions_frame = QFrame()
        actions_frame.setStyleSheet(f"""
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            border: 1px solid {DinoPitColors.SOFT_ORANGE};
            border-radius: 5px;
            padding: 10px;
        """)
        
        actions_layout = QHBoxLayout(actions_frame)
        
        self.star_btn = QPushButton("⭐ Star")
        self.star_btn.setEnabled(False)
        self.star_btn.clicked.connect(self._toggle_star)
        
        self.lock_btn = QPushButton("🔒 Lock")
        self.lock_btn.setEnabled(False)
        self.lock_btn.clicked.connect(self._toggle_encryption)
        
        self.share_btn = QPushButton("🔗 Share")
        self.share_btn.setEnabled(False)
        
        for btn in [self.star_btn, self.lock_btn, self.share_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DinoPitColors.DINOPIT_ORANGE};
                    color: white;
                    border: none;
                    border-radius: 15px;
                    padding: 8px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {DinoPitColors.DINOPIT_FIRE};
                }}
                QPushButton:disabled {{
                    background-color: #666666;
                    color: #999999;
                }}
            """)
            
        actions_layout.addWidget(self.star_btn)
        actions_layout.addWidget(self.lock_btn)
        actions_layout.addWidget(self.share_btn)
        actions_layout.addStretch()
        
        layout.addWidget(actions_frame)
        
        return pane
    
    def apply_project_filter(self, project_id: Optional[str]):
        """Apply project filter from external source
        
        Args:
            project_id: The project ID to filter by, or None for all
        """
        # Update combo box without triggering signals
        if hasattr(self, 'project_combo'):
            self.project_combo.set_project_id_silent(project_id)
        
        # Update internal state and reload
        self._current_project_filter = project_id
        self._load_artifacts()
    
    def navigate_to_artifact(self, artifact_id: str):
        """Navigate to and select a specific artifact
        
        Args:
            artifact_id: The artifact ID to navigate to
        """
        # Find the artifact in the tree
        def find_item(parent_item, target_id):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('type') == 'artifact':
                    if data.get('id') == target_id:
                        return child
                # Recursively search children
                result = find_item(child, target_id)
                if result:
                    return result
            return None
        
        # Search from root
        item = find_item(self.artifact_tree.invisibleRootItem(),
                         artifact_id)
        if item:
            # Select the item
            self.artifact_tree.setCurrentItem(item)
            self.artifact_tree.scrollToItem(item)
            # Ensure it's visible by expanding parents
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()
    
    def _view_project(self):
        """View the current artifact's project"""
        if self._current_artifact and self._current_artifact.project_id:
            self.request_navigate_to_project.emit(
                self._current_artifact.project_id
            )
        
    def _load_collections(self):
        """Load all collections"""
        try:
            self._collections_cache = self.artifacts_db.get_collections()
            self._update_tree()
        except Exception as e:
            self.logger.error(f"Failed to load collections: {str(e)}")
    
    def _load_projects_cache(self):
        """Load project information for badges"""
        try:
            projects = self.projects_db.get_all_projects()
            self._projects_cache = {p.id: p for p in projects}
        except Exception as e:
            self.logger.error(f"Failed to load projects cache: {str(e)}")
            
    def _load_artifacts(self):
        """Load all artifacts"""
        try:
            # Apply project filter if active
            if self._current_project_filter:
                artifacts = self.artifacts_db.get_artifacts_by_project(
                    self._current_project_filter
                )
            else:
                # For now, search with empty query to get all artifacts
                artifacts = self.artifacts_db.search_artifacts("", limit=1000)
            self._update_tree()
            self._update_stats()
        except Exception as e:
            self.logger.error(f"Failed to load artifacts: {str(e)}")
            
    def _update_tree(self):
        """Update the tree view with collections and artifacts"""
        self.artifact_tree.clear()
        
        # Create root items
        self.all_artifacts_item = QTreeWidgetItem(["All Artifacts"])
        self.all_artifacts_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "all"})
        self.artifact_tree.addTopLevelItem(self.all_artifacts_item)
        
        # Add collections
        collection_items = {}
        for collection in self._collections_cache:
            item = QTreeWidgetItem([f"📁 {collection.name}"])
            item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "collection",
                "id": collection.id,
                "collection": collection
            })
            collection_items[collection.id] = item
            
            if collection.parent_id and collection.parent_id in collection_items:
                collection_items[collection.parent_id].addChild(item)
            else:
                self.artifact_tree.addTopLevelItem(item)
                
        # Add artifacts to collections and all artifacts
        if self._current_project_filter:
            artifacts = self.artifacts_db.get_artifacts_by_project(
                self._current_project_filter
            )
        else:
            artifacts = self.artifacts_db.search_artifacts("", limit=1000)
        
        for artifact in artifacts:
            # Create artifact item
            icon = self._get_artifact_icon(artifact.content_type)
            item_text = f"{icon} {artifact.name}"
            
            # Add project badge if artifact has a project
            if hasattr(artifact, 'project_id') and artifact.project_id:
                project = self._projects_cache.get(artifact.project_id)
                if project:
                    # Add project icon and name as a badge
                    project_icon = project.get_display_icon()
                    item_text += f" [{project_icon} {project.name}]"
            
            # Add lock icon if encrypted
            if artifact.is_encrypted():
                item_text += " 🔒"
                
            artifact_item = QTreeWidgetItem([item_text])
            artifact_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "artifact",
                "id": artifact.id,
                "artifact": artifact
            })
            
            # Apply project color if available
            if hasattr(artifact, 'project_id') and artifact.project_id:
                project = self._projects_cache.get(artifact.project_id)
                if project and project.color:
                    from PySide6.QtGui import QBrush, QColor
                    brush = QBrush(QColor(project.color))
                    artifact_item.setForeground(0, brush)
            
            # Add to appropriate collection
            if artifact.collection_id and artifact.collection_id in collection_items:
                collection_items[artifact.collection_id].addChild(artifact_item.clone())
                
            # Always add to all artifacts
            self.all_artifacts_item.addChild(artifact_item)
            
        # Expand all artifacts by default
        self.all_artifacts_item.setExpanded(True)
        
    def _get_artifact_icon(self, content_type: str) -> str:
        """Get icon for artifact type"""
        icons = {
            ArtifactType.TEXT.value: "📄",
            ArtifactType.DOCUMENT.value: "📋",
            ArtifactType.IMAGE.value: "🖼️",
            ArtifactType.CODE.value: "💻",
            ArtifactType.BINARY.value: "📦"
        }
        return icons.get(content_type, "📄")
        
    def _update_stats(self):
        """Update statistics display"""
        try:
            stats = self.artifacts_db.get_artifact_statistics()
            total = stats.get('total_artifacts', 0)
            size = stats.get('total_size_mb', 0)
            
            plural = 's' if total != 1 else ''
            self.stats_label.setText(f"{total} artifact{plural} ({size:.1f} MB)")
        except Exception as e:
            self.logger.error(f"Failed to update stats: {str(e)}")
            
    def _on_tree_selection_changed(self):
        """Handle tree selection change"""
        selected_items = self.artifact_tree.selectedItems()
        
        if selected_items:
            item = selected_items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and data.get('type') == 'artifact':
                self._current_artifact = data.get('artifact')
                if self._current_artifact:
                    self._show_artifact_details(self._current_artifact)
                self.edit_action.setEnabled(True)
                self.delete_action.setEnabled(True)
                self.export_action.setEnabled(True)
                self.star_btn.setEnabled(True)
                self.lock_btn.setEnabled(True)
                self.share_btn.setEnabled(True)
                self.artifact_selected.emit(self._current_artifact)
                
                # Show/hide view project button based on project association
                if hasattr(self, 'view_project_btn'):
                    has_project = (self._current_artifact and
                                   hasattr(self._current_artifact, 'project_id') and
                                   self._current_artifact.project_id)
                    self.view_project_btn.setVisible(bool(has_project))
            else:
                self._current_artifact = None
                self._clear_artifact_details()
                self.edit_action.setEnabled(False)
                self.delete_action.setEnabled(False)
                self.export_action.setEnabled(False)
                self.star_btn.setEnabled(False)
                self.lock_btn.setEnabled(False)
                self.share_btn.setEnabled(False)
                
                # Hide view project button when no artifact selected
                if hasattr(self, 'view_project_btn'):
                    self.view_project_btn.setVisible(False)
                
        if selected_items:
            item = selected_items[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and data.get('type') == 'collection':
                self._current_collection = data.get('id')
            else:
                self._current_collection = None
                    
    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem):
        """Handle tree item double-click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data and data.get('type') == 'artifact':
            self._current_artifact = data.get('artifact')
            self._edit_artifact()
            
    def _show_artifact_details(self, artifact: Artifact):
        """Show artifact details in content pane"""
        self.content_header.setText(f"Artifact: {artifact.name}")
        
        # Update details
        self.details_labels['name'].setText(artifact.name)
        self.details_labels['type'].setText(artifact.content_type.capitalize())
        self.details_labels['status'].setText(artifact.status.capitalize())
        
        if artifact.collection_id:
            collection = next((c for c in self._collections_cache 
                               if c.id == artifact.collection_id), None)
            self.details_labels['collection'].setText(
                collection.name if collection else "Unknown"
            )
        else:
            self.details_labels['collection'].setText("No collection")
            
        self.details_labels['size'].setText(self._format_size(artifact.size_bytes))
        self.details_labels['created'].setText(
            artifact.created_at.strftime("%Y-%m-%d %H:%M") 
            if artifact.created_at else "-"
        )
        self.details_labels['updated'].setText(
            artifact.updated_at.strftime("%Y-%m-%d %H:%M") 
            if artifact.updated_at else "-"
        )
        self.details_labels['version'].setText(str(artifact.version))
        
        # Update content viewer
        content = self.artifacts_db.get_artifact_content(artifact.id)
        if content:
            try:
                text_content = content.decode('utf-8')
                self.content_viewer.setPlainText(text_content)
            except UnicodeDecodeError:
                self.content_viewer.setPlainText(
                    f"[Binary content - {len(content)} bytes]"
                )
        else:
            self.content_viewer.setPlainText("[No content]")
            
        # Update version history
        self._load_version_history(artifact.id)
        
        # Update buttons
        if artifact.metadata and artifact.metadata.get('starred'):
            self.star_btn.setText("✭ Starred")
        else:
            self.star_btn.setText("⭐ Star")
            
        if artifact.is_encrypted():
            self.lock_btn.setText("🔓 Unlock")
        else:
            self.lock_btn.setText("🔒 Lock")
            
    def _clear_artifact_details(self):
        """Clear artifact details"""
        self.content_header.setText("Select an artifact to view details")
        
        for label in self.details_labels.values():
            label.setText("-")
            
        self.content_viewer.clear()
        self.version_list.clear()
        
    def _load_version_history(self, artifact_id: str):
        """Load version history for artifact"""
        self.version_list.clear()
        
        try:
            versions = self.artifacts_db.get_versions(artifact_id)
            for version in versions:
                item_text = f"Version {version.version_number}"
                if version.change_summary:
                    item_text += f" - {version.change_summary}"
                if version.created_at:
                    item_text += f" ({version.created_at.strftime('%Y-%m-%d %H:%M')})"
                    
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, version)
                self.version_list.addItem(item)
        except Exception as e:
            self.logger.error(f"Failed to load version history: {str(e)}")
            
    def _create_new_artifact(self):
        """Create a new artifact"""
        dialog = ArtifactDialog(self, collections=self._collections_cache)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                artifact, content_bytes = dialog.get_artifact_data()
                
                # Validate
                if not artifact.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Artifact",
                        "Please enter a name for the artifact."
                    )
                    return
                    
                # Create artifact
                result = self.artifacts_db.create_artifact(artifact, content_bytes)
                
                if result["success"]:
                    self.logger.info(f"Created new artifact: {artifact.id}")
                    
                    # Refresh displays
                    self._load_artifacts()
                    
                    # TODO: Select the new artifact in tree
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to create artifact: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create artifact: {str(e)}"
                )
                
    def _edit_artifact(self):
        """Edit the selected artifact"""
        if not self._current_artifact:
            return
            
        dialog = ArtifactDialog(
            self, 
            artifact=self._current_artifact,
            collections=self._collections_cache
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                updated_artifact, content_bytes = dialog.get_artifact_data()
                
                # Validate
                if not updated_artifact.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Artifact",
                        "Please enter a name for the artifact."
                    )
                    return
                    
                # Track project changes
                old_project_id = self._current_artifact.project_id
                new_project_id = updated_artifact.project_id
                
                # Update artifact
                updates = updated_artifact.to_dict()
                # Remove fields that shouldn't be updated directly
                for field in ['id', 'created_at', 'version']:
                    updates.pop(field, None)
                    
                success = self.artifacts_db.update_artifact(
                    updated_artifact.id,
                    updates,
                    content_bytes
                )
                
                if success:
                    self.logger.info(f"Updated artifact: {updated_artifact.id}")
                    
                    # Refresh displays
                    self._load_artifacts()
                    self._show_artifact_details(updated_artifact)
                    
                    # Emit project change signal if project changed
                    if old_project_id != new_project_id:
                        self.artifact_project_changed.emit(
                            updated_artifact.id,
                            old_project_id or "",
                            new_project_id or ""
                        )
                        # Reload projects cache to ensure we have latest info
                        self._load_projects_cache()
                else:
                    raise Exception("Failed to update artifact")
                    
            except Exception as e:
                self.logger.error(f"Failed to update artifact: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update artifact: {str(e)}"
                )
                
    def _delete_artifact(self):
        """Delete the selected artifact"""
        if not self._current_artifact:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Artifact",
            f"Are you sure you want to delete '{self._current_artifact.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.artifacts_db.delete_artifact(
                    self._current_artifact.id
                )
                
                if success:
                    self.logger.info(
                        f"Deleted artifact: {self._current_artifact.id}"
                    )
                    
                    # Clear selection
                    self._current_artifact = None
                    self._clear_artifact_details()
                    
                    # Refresh displays
                    self._load_artifacts()
                else:
                    raise Exception("Failed to delete artifact")
                    
            except Exception as e:
                self.logger.error(f"Failed to delete artifact: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete artifact: {str(e)}"
                )
                
    def _create_new_collection(self):
        """Create a new collection"""
        dialog = CollectionDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                collection = dialog.get_collection_data()
                
                # Validate
                if not collection.name:
                    QMessageBox.warning(
                        self,
                        "Invalid Collection",
                        "Please enter a name for the collection."
                    )
                    return
                    
                # Create collection
                result = self.artifacts_db.create_collection(collection)
                
                if result["success"]:
                    self.logger.info(f"Created new collection: {collection.id}")
                    
                    # Refresh displays
                    self._load_collections()
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to create collection: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create collection: {str(e)}"
                )
                
    def _manage_collections(self):
        """Show collection management dialog"""
        # TODO: Implement full collection management dialog
        QMessageBox.information(
            self,
            "Manage Collections",
            "Collection management dialog coming soon!"
        )
        
    def _export_artifact(self):
        """Export the selected artifact"""
        if not self._current_artifact:
            return
            
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Artifact",
                self._current_artifact.name,
                "All Files (*.*)"
            )
            
            if file_path:
                # Get artifact content
                content = self.artifacts_db.get_artifact_content(
                    self._current_artifact.id
                )
                
                if content:
                    with open(file_path, 'wb') as f:
                        f.write(content)
                        
                    QMessageBox.information(
                        self,
                        "Export Successful",
                        f"Artifact exported to: {file_path}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Export Failed",
                        "No content to export."
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to export artifact: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to export artifact: {str(e)}"
            )
            
    def _toggle_star(self):
        """Toggle star/favorite status"""
        if not self._current_artifact:
            return
            
        try:
            metadata = self._current_artifact.metadata or {}
            metadata['starred'] = not metadata.get('starred', False)
            
            updates = {'metadata': metadata}
            success = self.artifacts_db.update_artifact(
                self._current_artifact.id, updates
            )
            
            if success:
                self._current_artifact.metadata = metadata
                if metadata['starred']:
                    self.star_btn.setText("✭ Starred")
                else:
                    self.star_btn.setText("⭐ Star")
                    
        except Exception as e:
            self.logger.error(f"Failed to toggle star: {str(e)}")
            
    def _toggle_encryption(self):
        """Toggle encryption status"""
        if not self._current_artifact:
            return
            
        # TODO: Implement encryption toggle
        QMessageBox.information(
            self,
            "Encryption",
            "Encryption toggle coming soon!"
        )
        
    def _on_search_changed(self, text: str):
        """Handle search text change"""
        self._apply_filters()
        
    def _apply_filters(self):
        """Apply search and filters"""
        # TODO: Implement filtering
        search_text = self.search_input.text()
        if search_text:
            try:
                artifacts = self.artifacts_db.search_artifacts(search_text)
                # Update tree with filtered artifacts
                # For now, just refresh
                self._load_artifacts()
            except Exception as e:
                self.logger.error(f"Search failed: {str(e)}")
                
    def _clear_filters(self):
        """Clear all filters"""
        self.search_input.clear()
        self.type_filter.setCurrentIndex(0)
        self.date_filter.setCurrentIndex(0)
        self._load_artifacts()
        
    def _show_tree_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.artifact_tree.itemAt(position)
        if not item:
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
            
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
        
        if data.get('type') == 'artifact':
            # Artifact context menu
            edit_action = QAction("✏️ Edit", self)
            edit_action.triggered.connect(self._edit_artifact)
            menu.addAction(edit_action)
            
            duplicate_action = QAction("📋 Duplicate", self)
            duplicate_action.triggered.connect(lambda: self._duplicate_artifact(
                data.get('artifact')
            ))
            menu.addAction(duplicate_action)
            
            menu.addSeparator()
            
            export_action = QAction("📤 Export", self)
            export_action.triggered.connect(self._export_artifact)
            menu.addAction(export_action)
            
            menu.addSeparator()
            
            delete_action = QAction("🗑️ Delete", self)
            delete_action.triggered.connect(self._delete_artifact)
            menu.addAction(delete_action)
            
        elif data.get('type') == 'collection':
            # Collection context menu
            new_artifact_action = QAction("✚ New Artifact Here", self)
            new_artifact_action.triggered.connect(self._create_new_artifact)
            menu.addAction(new_artifact_action)
            
            menu.addSeparator()
            
            edit_collection_action = QAction("✏️ Edit Collection", self)
            edit_collection_action.triggered.connect(lambda: self._edit_collection(
                data.get('collection')
            ))
            menu.addAction(edit_collection_action)
            
            delete_collection_action = QAction("🗑️ Delete Collection", self)
            delete_collection_action.triggered.connect(lambda: self._delete_collection(
                data.get('collection')
            ))
            menu.addAction(delete_collection_action)
            
        menu.exec(self.artifact_tree.mapToGlobal(position))
        
    def _duplicate_artifact(self, artifact: Artifact):
        """Duplicate an artifact"""
        try:
            # Create a copy
            new_artifact = Artifact.from_dict(artifact.to_dict())
            import uuid
            new_artifact.id = str(uuid.uuid4())  # New ID
            new_artifact.name = f"{artifact.name} (Copy)"
            new_artifact.created_at = datetime.now()
            new_artifact.updated_at = datetime.now()
            new_artifact.version = 1
            
            # Get content
            content = self.artifacts_db.get_artifact_content(artifact.id)
            
            # Create the duplicate
            result = self.artifacts_db.create_artifact(new_artifact, content)
            
            if result.get("success"):
                self.logger.info(f"Duplicated artifact: {new_artifact.id}")
                self._load_artifacts()
            else:
                raise Exception(result.get("error", "Unknown error"))
                
        except Exception as e:
            self.logger.error(f"Failed to duplicate artifact: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to duplicate artifact: {str(e)}"
            )
            
    def _edit_collection(self, collection: ArtifactCollection):
        """Edit a collection"""
        dialog = CollectionDialog(self, collection=collection)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                updated_collection = dialog.get_collection_data()
                
                # Update collection
                updates = {
                    'name': updated_collection.name,
                    'description': updated_collection.description,
                    'tags': updated_collection.tags,
                    'is_encrypted': updated_collection.is_encrypted
                }
                
                success = self.artifacts_db.update_collection(
                    collection.id, updates
                )
                
                if success:
                    self.logger.info(f"Updated collection: {collection.id}")
                    self._load_collections()
                else:
                    raise Exception("Failed to update collection")
                    
            except Exception as e:
                self.logger.error(f"Failed to update collection: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to update collection: {str(e)}"
                )
                
    def _delete_collection(self, collection: ArtifactCollection):
        """Delete a collection"""
        # Check if collection has artifacts
        artifacts = self.artifacts_db.get_artifacts_by_collection(collection.id)
        
        if artifacts:
            reply = QMessageBox.question(
                self,
                "Delete Collection",
                f"Collection '{collection.name}' contains {len(artifacts)} artifacts. "
                "Deleting the collection will not delete the artifacts. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
        else:
            reply = QMessageBox.question(
                self,
                "Delete Collection",
                f"Are you sure you want to delete collection '{collection.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # For now, we'll remove the collection reference from artifacts
                # In a real implementation, you might want to handle this differently
                for artifact in artifacts:
                    self.artifacts_db.update_artifact(
                        artifact.id, {'collection_id': None}
                    )
                    
                # Note: We don't have a delete_collection method in artifacts_db yet
                # This would need to be implemented
                QMessageBox.information(
                    self,
                    "Delete Collection",
                    "Collection deletion will be implemented soon!"
                )
                
                self._load_collections()
                
            except Exception as e:
                self.logger.error(f"Failed to delete collection: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete collection: {str(e)}"
                )
                
    def _restore_version(self, item: QListWidgetItem):
        """Restore artifact to selected version"""
        version = item.data(Qt.ItemDataRole.UserRole)
        if not version or not self._current_artifact:
            return
            
        reply = QMessageBox.question(
            self,
            "Restore Version",
            f"Restore artifact to version {version.version_number}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.artifacts_db.restore_version(
                    self._current_artifact.id,
                    version.version_number
                )
                
                if success:
                    self.logger.info(
                        f"Restored artifact to version {version.version_number}"
                    )
                    self._load_artifacts()
                    
                    # Refresh current artifact details
                    self._current_artifact = self.artifacts_db.get_artifact(
                        self._current_artifact.id
                    )
                    if self._current_artifact:
                        self._show_artifact_details(self._current_artifact)
                else:
                    raise Exception("Failed to restore version")
                    
            except Exception as e:
                self.logger.error(f"Failed to restore version: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to restore version: {str(e)}"
                )
                
    def _refresh_artifacts(self):
        """Refresh artifacts display"""
        self._load_collections()
        self._load_artifacts()
        
    def _format_size(self, size_bytes: int) -> str:
        """Format file size"""
        if size_bytes == 0:
            return "0 B"
            
        size_value = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_value < 1024.0:
                return f"{size_value:.1f} {unit}"
            size_value /= 1024.0
        return f"{size_value:.1f} TB"
        
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Ctrl+N for new artifact
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self._create_new_artifact)
        
        # Delete key for delete
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._delete_artifact)
        
        # Ctrl+E for edit
        edit_shortcut = QShortcut(QKeySequence("Ctrl+E"), self)
        edit_shortcut.activated.connect(self._edit_artifact)
        
        # F5 for refresh
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._refresh_artifacts)
        
    def _update_splitter_sizes(self):
        """Set splitter proportions based on window width"""
        total_width = self.width()
        self.main_splitter.setSizes([
            int(total_width * 0.35),  # 35% for tree
            int(total_width * 0.65)   # 65% for content
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
            "artifacts_main", self.main_splitter
        )
        
    def _restore_splitter_state(self):
        """Restore the splitter state"""
        window_state_manager.restore_splitter_to_widget(
            "artifacts_main", self.main_splitter
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
        if event.mimeData().hasFormat("application/x-artifact"):
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move event"""
        if event.mimeData().hasFormat("application/x-artifact"):
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        # TODO: Implement drag and drop between collections
        pass
    
    def _on_project_filter_changed(self, project_id: Optional[str]):
        """Handle project filter change from combo box"""
        self._current_project_filter = project_id
        
        # Clear any existing artifact selection
        self._current_artifact = None
        self._clear_artifact_details()
        
        # Reload artifacts with new filter
        self._load_artifacts()
        
        # Update UI state
        self.edit_action.setEnabled(False)
        self.delete_action.setEnabled(False)
        self.export_action.setEnabled(False)
        self.star_btn.setEnabled(False)
        self.lock_btn.setEnabled(False)
        self.share_btn.setEnabled(False)
        
        # Emit filter change signal for coordination
        self.project_filter_requested.emit(project_id)