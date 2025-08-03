#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ArtifactsWidget class for the PySide6 application.
This widget displays the artifacts in the right sidebar with full
database integration.
"""

from typing import List, Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem,
    QTextEdit, QLineEdit, QToolBar, QMessageBox,
    QSplitter, QComboBox
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QAction, QFont

from ...database.artifacts_db import ArtifactsDatabase
from ...database.initialize_db import DatabaseManager
from ...models.artifact import Artifact, ArtifactType
from ...utils.colors import DinoPitColors
from ...utils.scaling import get_scaling_helper
from ...utils.logger import Logger


class ArtifactListItem(QWidget):
    """Custom widget for displaying an artifact in the list."""
    
    def __init__(self, artifact: Artifact):
        """Initialize the artifact list item.
        
        Args:
            artifact: The Artifact object to display
        """
        super().__init__()
        self.artifact = artifact
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the item UI."""
        layout = QVBoxLayout(self)
        s = self._scaling_helper
        layout.setContentsMargins(
            s.scaled_size(10), s.scaled_size(8),
            s.scaled_size(10), s.scaled_size(8)
        )
        layout.setSpacing(s.scaled_size(4))
        
        # Header with type indicator and name
        header_layout = QHBoxLayout()
        header_layout.setSpacing(s.scaled_size(8))
        
        # Type indicator (colored dot)
        type_indicator = QLabel()
        type_indicator.setStyleSheet("color: #FFFFFF;")
        type_indicator.setFixedSize(s.scaled_size(8), s.scaled_size(8))
        
        # Color based on type
        type_colors = {
            ArtifactType.TEXT.value: "#FFFFFF",  # White
            ArtifactType.DOCUMENT.value: "#4CAF50",  # Green
            ArtifactType.IMAGE.value: "#FF6B35",  # Orange
            ArtifactType.CODE.value: "#9C27B0",  # Purple
            ArtifactType.BINARY.value: "#607D8B"  # Blue-grey
        }
        color = type_colors.get(self.artifact.content_type, "#FFFFFF")
        type_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: {s.scaled_size(4)}px;"
        )
        
        # Name label
        name_label = QLabel(self.artifact.name or "Unnamed Artifact")
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(s.scaled_font_size(11))
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        
        header_layout.addWidget(type_indicator)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        
        # Type label
        type_label = QLabel(self.artifact.content_type.title())
        type_label.setStyleSheet(
            f"color: {DinoPitColors.DINOPIT_ORANGE}; "
            f"font-size: {s.scaled_font_size(9)}px;"
        )
        header_layout.addWidget(type_label)
        
        layout.addLayout(header_layout)
        
        # Description (if any)
        if self.artifact.description:
            desc_text = (self.artifact.description[:60] + "..."
                         if len(self.artifact.description) > 60
                         else self.artifact.description)
            desc_label = QLabel(desc_text)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(
                f"color: {DinoPitColors.PRIMARY_TEXT}; "
                f"font-size: {s.scaled_font_size(10)}px;"
            )
            layout.addWidget(desc_label)
        
        # Bottom row with date and size
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(s.scaled_size(10))
        
        # Date
        date_str = self._format_date()
        date_label = QLabel(date_str)
        date_label.setStyleSheet(
            f"color: {DinoPitColors.SOFT_ORANGE}; "
            f"font-size: {s.scaled_font_size(9)}px;"
        )
        bottom_layout.addWidget(date_label)
        
        # Size
        if self.artifact.size_bytes > 0:
            size_str = self._format_size(self.artifact.size_bytes)
            size_label = QLabel(size_str)
            size_label.setStyleSheet(
                f"color: {DinoPitColors.PRIMARY_TEXT}; "
                f"font-size: {s.scaled_font_size(9)}px;"
            )
            bottom_layout.addWidget(size_label)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
    def _format_date(self) -> str:
        """Format the artifact's date for display."""
        try:
            dt = self.artifact.updated_at
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            
            today = datetime.now().date()
            artifact_date = dt.date()
            
            if artifact_date == today:
                return dt.strftime("Today %I:%M %p")
            elif (today - artifact_date).days == 1:
                return dt.strftime("Yesterday %I:%M %p")
            else:
                return dt.strftime("%b %d, %Y")
        except Exception:
            return "Unknown date"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"


class ArtifactsWidget(QWidget):
    """Widget displaying artifacts in the right sidebar with DB integration."""
    
    # Signals
    artifact_selected = Signal(Artifact)
    artifact_deleted = Signal(str)  # artifact_id
    
    def __init__(self):
        """Initialize the artifacts widget."""
        super().__init__()
        self.logger = Logger()
        self._scaling_helper = get_scaling_helper()
        self._current_artifact: Optional[Artifact] = None
        self._artifacts: List[Artifact] = []
        self._search_query = ""
        self._type_filter = "all"
        
        # Initialize database
        self._init_database()
        
        # Set fixed width
        self.setFixedWidth(300)
        
        # Setup UI
        self._setup_ui()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
        # Load artifacts
        self._load_artifacts()
        
    def _init_database(self):
        """Initialize database connection."""
        try:
            username = "default_user"  # This should come from app context
            self.db_manager = DatabaseManager(username)
            self.artifacts_db = ArtifactsDatabase(self.db_manager)
        except Exception as e:
            self.logger.error(
                f"Failed to initialize artifacts database: {str(e)}"
            )
            self.artifacts_db = None
            
    def _setup_ui(self):
        """Setup the widget UI."""
        # Create main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create header
        self.header = self._create_header()
        self.main_layout.addWidget(self.header)
        
        # Create toolbar
        self.toolbar = self._create_toolbar()
        self.main_layout.addWidget(self.toolbar)
        
        # Create search bar
        self.search_bar = self._create_search_bar()
        self.main_layout.addWidget(self.search_bar)
        
        # Create content splitter
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                height: 2px;
            }}
        """)
        
        # Create artifact list
        self.artifact_list = self._create_artifact_list()
        self.content_splitter.addWidget(self.artifact_list)
        
        # Create details panel
        self.details_panel = self._create_details_panel()
        self.content_splitter.addWidget(self.details_panel)
        
        # Set initial splitter proportions
        self.content_splitter.setSizes([200, 100])
        
        self.main_layout.addWidget(self.content_splitter)
        
    def _create_header(self) -> QWidget:
        """Create the header widget."""
        header = QWidget()
        header.setStyleSheet(
            f"background-color: {DinoPitColors.DINOPIT_ORANGE}; "
            f"border-bottom: 2px solid {DinoPitColors.DINOPIT_FIRE};"
        )
        header.setFixedHeight(self._scaling_helper.scaled_size(50))
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(
            self._scaling_helper.scaled_size(15), 0,
            self._scaling_helper.scaled_size(15), 0
        )
        
        header_label = QLabel("Artifacts")
        header_label.setStyleSheet(
            f"font-weight: bold; color: white; "
            f"font-size: {self._scaling_helper.scaled_font_size(14)}px;"
        )
        
        self.count_label = QLabel("0 items")
        self.count_label.setStyleSheet(
            f"color: white; "
            f"font-size: {self._scaling_helper.scaled_font_size(12)}px;"
        )
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        return header
        
    def _create_toolbar(self) -> QToolBar:
        """Create the toolbar with actions."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        s = self._scaling_helper
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: none;
                padding: {s.scaled_size(5)}px;
                spacing: {s.scaled_size(5)}px;
            }}
            QToolButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: {s.scaled_size(6)}px {s.scaled_size(12)}px;
                font-weight: bold;
                margin-right: {s.scaled_size(3)}px;
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
        
        # New artifact action
        self.new_action = QAction("✚ New", self)
        self.new_action.triggered.connect(self._create_new_artifact)
        toolbar.addAction(self.new_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_artifact)
        self.delete_action.setEnabled(False)
        toolbar.addAction(self.delete_action)
        
        # Refresh action
        self.refresh_action = QAction("🔄 Refresh", self)
        self.refresh_action.triggered.connect(self._load_artifacts)
        toolbar.addAction(self.refresh_action)
        
        return toolbar
        
    def _create_search_bar(self) -> QWidget:
        """Create the search bar widget."""
        search_widget = QWidget()
        search_widget.setStyleSheet(
            f"background-color: {DinoPitColors.PANEL_BACKGROUND};"
        )
        
        layout = QHBoxLayout(search_widget)
        s = self._scaling_helper
        layout.setContentsMargins(
            s.scaled_size(10), s.scaled_size(5),
            s.scaled_size(10), s.scaled_size(5)
        )
        layout.setSpacing(s.scaled_size(5))
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search artifacts...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: {s.scaled_size(1)}px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {s.scaled_size(15)}px;
                padding: {s.scaled_size(6)}px {s.scaled_size(12)}px;
                font-size: {s.scaled_font_size(11)}px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        
        # Type filter
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems([
            "All Types",
            "Text",
            "Document", 
            "Image",
            "Code",
            "Binary"
        ])
        self.type_filter_combo.setStyleSheet(f"""
            QComboBox {{
                border: {s.scaled_size(1)}px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {s.scaled_size(4)}px;
                padding: {s.scaled_size(4)}px {s.scaled_size(8)}px;
                font-size: {s.scaled_font_size(10)}px;
                background-color: {DinoPitColors.MAIN_BACKGROUND};
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
                border-top: 4px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: {s.scaled_size(4)}px;
            }}
        """)
        self.type_filter_combo.currentTextChanged.connect(
            self._on_type_filter_changed
        )
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.type_filter_combo)
        
        return search_widget
        
    def _create_artifact_list(self) -> QListWidget:
        """Create the artifact list widget."""
        list_widget = QListWidget()
        list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border: 1px solid transparent;
                border-radius: 5px;
                margin: 2px;
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QListWidget::item:hover {{
                border-color: {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        
        list_widget.itemClicked.connect(self._on_artifact_clicked)
        list_widget.currentItemChanged.connect(
            self._on_artifact_selection_changed
        )
        
        return list_widget
        
    def _create_details_panel(self) -> QWidget:
        """Create the artifact details panel."""
        panel = QWidget()
        panel.setStyleSheet(
            f"background-color: {DinoPitColors.SIDEBAR_BACKGROUND};"
        )
        
        layout = QVBoxLayout(panel)
        s = self._scaling_helper
        layout.setContentsMargins(
            s.scaled_size(10), s.scaled_size(10),
            s.scaled_size(10), s.scaled_size(10)
        )
        layout.setSpacing(s.scaled_size(8))
        
        # Details header
        self.details_header = QLabel("Select an artifact to view details")
        self.details_header.setWordWrap(True)
        self.details_header.setStyleSheet(
            f"font-weight: bold; color: {DinoPitColors.DINOPIT_ORANGE}; "
            f"font-size: {s.scaled_font_size(12)}px;"
        )
        layout.addWidget(self.details_header)
        
        # Details content
        self.details_content = QTextEdit()
        self.details_content.setReadOnly(True)
        self.details_content.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: {s.scaled_size(1)}px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {s.scaled_size(5)}px;
                padding: {s.scaled_size(8)}px;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {s.scaled_font_size(10)}px;
            }}
        """)
        layout.addWidget(self.details_content)
        
        return panel
        
    def _load_artifacts(self):
        """Load artifacts from database."""
        if not self.artifacts_db:
            self._show_database_error()
            return
            
        try:
            # Clear current list
            self.artifact_list.clear()
            
            # Get artifacts based on filters
            if self._search_query:
                self._artifacts = self.artifacts_db.search_artifacts(
                    self._search_query, limit=50
                )
            elif self._type_filter != "all":
                # Map combo text to artifact type
                type_map = {
                    "Text": ArtifactType.TEXT.value,
                    "Document": ArtifactType.DOCUMENT.value,
                    "Image": ArtifactType.IMAGE.value,
                    "Code": ArtifactType.CODE.value,
                    "Binary": ArtifactType.BINARY.value
                }
                artifact_type = type_map.get(self._type_filter)
                if artifact_type:
                    self._artifacts = self.artifacts_db.get_artifacts_by_type(
                        artifact_type, limit=50
                    )
                else:
                    self._artifacts = []
            else:
                # Get all artifacts
                all_artifacts = []
                for artifact_type in ArtifactType:
                    artifacts = self.artifacts_db.get_artifacts_by_type(
                        artifact_type.value, limit=20
                    )
                    all_artifacts.extend(artifacts)
                # Sort by updated date
                self._artifacts = sorted(
                    all_artifacts, 
                    key=lambda a: a.updated_at, 
                    reverse=True
                )[:50]
            
            # Add artifacts to list
            for artifact in self._artifacts:
                self._add_artifact_to_list(artifact)
                
            # Update count
            self._update_count()
            
            # Clear selection
            self._current_artifact = None
            self.delete_action.setEnabled(False)
            self._clear_details()
            
        except Exception as e:
            self.logger.error(f"Failed to load artifacts: {str(e)}")
            self._show_error("Failed to load artifacts", str(e))
            
    def _add_artifact_to_list(self, artifact: Artifact):
        """Add an artifact to the list widget."""
        # Create custom widget
        item_widget = ArtifactListItem(artifact)
        
        # Create list item
        list_item = QListWidgetItem(self.artifact_list)
        list_item.setSizeHint(
            QSize(0, self._scaling_helper.scaled_size(80))
        )
        list_item.setData(Qt.ItemDataRole.UserRole, artifact)
        
        # Set the custom widget
        self.artifact_list.addItem(list_item)
        self.artifact_list.setItemWidget(list_item, item_widget)
        
    def _update_count(self):
        """Update the artifact count display."""
        count = len(self._artifacts)
        self.count_label.setText(f"{count} item{'s' if count != 1 else ''}")
        
    def _on_artifact_clicked(self, item: QListWidgetItem):
        """Handle artifact click."""
        artifact = item.data(Qt.ItemDataRole.UserRole)
        if artifact:
            self._current_artifact = artifact
            self.artifact_selected.emit(artifact)
            self._show_artifact_details(artifact)
            
    def _on_artifact_selection_changed(self, current: QListWidgetItem,
                                       previous: QListWidgetItem):
        """Handle artifact selection change."""
        if current:
            artifact = current.data(Qt.ItemDataRole.UserRole)
            if artifact:
                self._current_artifact = artifact
                self.delete_action.setEnabled(True)
                self._show_artifact_details(artifact)
        else:
            self._current_artifact = None
            self.delete_action.setEnabled(False)
            self._clear_details()
            
    def _show_artifact_details(self, artifact: Artifact):
        """Show artifact details in the details panel."""
        self.details_header.setText(artifact.name or "Unnamed Artifact")
        
        # Build details text
        details = []
        
        # Basic info
        details.append(f"Type: {artifact.content_type.title()}")
        details.append(f"Status: {artifact.status.title()}")
        
        # Description
        if artifact.description:
            details.append(f"\nDescription:\n{artifact.description}")
            
        # Size
        if artifact.size_bytes > 0:
            size_str = self._format_size(artifact.size_bytes)
            details.append(f"\nSize: {size_str}")
            
        # Tags
        if artifact.tags:
            details.append(f"\nTags: {', '.join(artifact.tags)}")
            
        # Dates
        try:
            created = artifact.created_at
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            details.append(f"\nCreated: {created.strftime('%Y-%m-%d %H:%M')}")
            
            updated = artifact.updated_at
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated)
            details.append(f"Updated: {updated.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass
            
        # Version info
        if artifact.version > 1:
            details.append(f"\nVersion: {artifact.version}")
            
        # Encryption status
        if artifact.is_encrypted():
            details.append("\n🔒 This artifact is encrypted")
            
        self.details_content.setPlainText("\n".join(details))
        
    def _clear_details(self):
        """Clear the details panel."""
        self.details_header.setText("Select an artifact to view details")
        self.details_content.clear()
        
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
            
    def _on_search_changed(self, text: str):
        """Handle search text changes."""
        self._search_query = text.strip()
        # Debounce search
        if hasattr(self, '_search_timer'):
            self._search_timer.stop()
        else:
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._load_artifacts)
        self._search_timer.start(300)  # 300ms delay
        
    def _on_type_filter_changed(self, text: str):
        """Handle type filter changes."""
        if text == "All Types":
            self._type_filter = "all"
        else:
            self._type_filter = text
        self._load_artifacts()
        
    def _create_new_artifact(self):
        """Create a new artifact (placeholder for now)."""
        QMessageBox.information(
            self,
            "Create Artifact",
            "Creating new artifacts will be implemented in a future "
            "update.\n\nArtifacts can be created through the chat "
            "interface or by importing files."
        )
        
    def _delete_artifact(self):
        """Delete the selected artifact."""
        if not self._current_artifact or not self.artifacts_db:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Artifact",
            f"Are you sure you want to delete "
            f"'{self._current_artifact.name}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete from database
                success = self.artifacts_db.delete_artifact(
                    self._current_artifact.id,
                    hard_delete=False  # Soft delete by default
                )
                
                if success:
                    self.logger.info(
                        f"Deleted artifact: {self._current_artifact.id}"
                    )
                    self.artifact_deleted.emit(self._current_artifact.id)
                    
                    # Reload artifacts
                    self._load_artifacts()
                else:
                    self._show_error(
                        "Delete Failed",
                        "Failed to delete the artifact."
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to delete artifact: {str(e)}")
                self._show_error("Delete Error", str(e))
                
    def _show_error(self, title: str, message: str):
        """Show an error message."""
        QMessageBox.critical(self, title, message)
        
    def _show_database_error(self):
        """Show database connection error."""
        self.details_header.setText("Database Error")
        self.details_content.setPlainText(
            "Failed to connect to the artifacts database.\n\n"
            "Please check the application logs for more details."
        )
        
    def refresh(self):
        """Refresh the artifacts list."""
        self._load_artifacts()
        
    def get_artifact_count(self) -> int:
        """Get the number of artifacts currently displayed.
        
        Returns:
            int: The number of artifact items
        """
        return len(self._artifacts)
        
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update header height
        self.header.setFixedHeight(self._scaling_helper.scaled_size(50))
        
        # Force refresh to update all scaled elements
        self._load_artifacts()