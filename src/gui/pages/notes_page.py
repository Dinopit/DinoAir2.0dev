"""
Notes Page - Main notes interface with full CRUD functionality and auto-save
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QMessageBox, QLabel, QPushButton, QFrame,
    QMenu, QToolButton
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut

from ...database.notes_db import NotesDatabase
from ...models.note import Note
from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...utils.scaling import get_scaling_helper
from ...utils.window_state import window_state_manager
from ..components.note_editor import NoteEditor
from ..components.note_list_widget import NoteListWidget
from ..components.notes_search import NotesSearchWidget
from ..components.tag_manager import TagManager
from ..components.notes_security import get_notes_security
from ..components.notes_exporter import NotesExporter
from ..components.project_combo_box import ProjectComboBox


class NotesPage(QWidget):
    """Notes page widget with full database integration.
    
    Features:
    - Note list on the left showing all notes
    - Note editor on the right for editing
    - Toolbar with New, Save, and Delete buttons
    - Full CRUD operations with database
    - Auto-save functionality with conflict detection
    """
    
    def __init__(self):
        """Initialize the notes page."""
        super().__init__()
        self.logger = Logger()
        self.notes_db = NotesDatabase()
        self._security = get_notes_security()
        self._exporter = NotesExporter(self)
        self._current_note: Optional[Note] = None
        self._has_unsaved_changes = False
        self._active_tag_filters: List[str] = []
        self._tag_panel_visible = False
        self._auto_save_enabled = True
        self._last_saved_content: Dict[str, Any] = {}
        self._current_project_filter: Optional[str] = None
        self._conflict_check_timer = QTimer()
        self._conflict_check_timer.timeout.connect(self._check_for_conflicts)
        self._conflict_check_timer.setInterval(5000)  # Check every 5 seconds
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        self._load_notes()
        self._update_available_tags()
        self._load_auto_save_settings()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def setup_ui(self):
        """Setup the notes page UI."""
        layout = QVBoxLayout(self)
        
        # Use font metrics for consistent spacing
        font_metrics = self.fontMetrics()
        margin = font_metrics.height() // 2  # Half line height
        spacing = font_metrics.height() // 4  # Quarter line height
        
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        
        # Create toolbar with search
        toolbar_container = self._create_toolbar_with_search()
        layout.addWidget(toolbar_container)
        
        # Main content area with tag panel
        main_content = QWidget()
        main_layout = QHBoxLayout(main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for notes list and editor
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                width: 2px;
            }}
        """)
        
        # Notes list pane
        notes_pane = QWidget()
        notes_layout = QVBoxLayout(notes_pane)
        
        # Use scaled margins
        notes_layout.setContentsMargins(0, margin, spacing, 0)
        
        # Add note list widget
        self.note_list = NoteListWidget()
        self.note_list.note_selected.connect(self._on_note_selected)
        notes_layout.addWidget(self.note_list)
        
        # Use scaled widths
        notes_pane.setMaximumWidth(self._scaling_helper.scaled_size(350))
        notes_pane.setMinimumWidth(self._scaling_helper.scaled_size(200))
        self.content_splitter.addWidget(notes_pane)
        
        # Note editor pane
        editor_pane = QWidget()
        editor_layout = QVBoxLayout(editor_pane)
        editor_layout.setContentsMargins(spacing, margin, 0, 0)
        
        # Add note editor
        self.note_editor = NoteEditor()
        self.note_editor.note_changed.connect(self._on_note_changed)
        self.note_editor.auto_save_requested.connect(
            self._on_auto_save_requested
        )
        editor_layout.addWidget(self.note_editor)
        
        self.content_splitter.addWidget(editor_pane)
        
        # Set initial splitter proportions based on window width
        self._update_splitter_sizes()
        
        # Connect splitter moved signal to save state
        self.content_splitter.splitterMoved.connect(
            self._save_content_splitter_state
        )
        
        # Restore splitter state if available
        self._restore_content_splitter_state()
        
        main_layout.addWidget(self.content_splitter)
        
        # Tag panel (initially hidden)
        self.tag_panel = self._create_tag_panel()
        self.tag_panel.setMaximumWidth(0)
        self.tag_panel.setMinimumWidth(0)
        main_layout.addWidget(self.tag_panel)
        
        layout.addWidget(main_content)
        
    def _create_toolbar_with_search(self) -> QWidget:
        """Create the toolbar with actions and search widget."""
        # Use font metrics for spacing
        font_metrics = self.fontMetrics()
        spacing = font_metrics.height() // 4  # Quarter line height
        
        # Container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(spacing)
        
        # Search widget
        self.search_widget = NotesSearchWidget()
        self.search_widget.search_requested.connect(self._search_notes)
        self.search_widget.clear_requested.connect(self._clear_search)
        container_layout.addWidget(self.search_widget)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self._update_toolbar_style()
        
        # New Note action
        new_action = QAction("✚ New Note", self)
        new_action.triggered.connect(self._create_new_note)
        self.toolbar.addAction(new_action)
        
        # Save action
        self.save_action = QAction("💾 Save", self)
        self.save_action.triggered.connect(self._save_note)
        self.save_action.setEnabled(False)
        self.toolbar.addAction(self.save_action)
        
        # Delete action
        self.delete_action = QAction("🗑️ Delete", self)
        self.delete_action.triggered.connect(self._delete_note)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)
        
        # Add stretch
        self.spacer1 = QWidget()
        self.spacer1.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer1)
        
        # Tags toggle button
        self.tags_action = QAction("🏷️ Tags", self)
        self.tags_action.setCheckable(True)
        self.tags_action.triggered.connect(self._toggle_tag_panel)
        self.toolbar.addAction(self.tags_action)
        
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
        
        # Another spacer
        self.spacer5 = QWidget()
        self.spacer5.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer5)
        
        # Auto-save toggle
        self.auto_save_action = QAction("⚡ Auto-save", self)
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.setChecked(self._auto_save_enabled)
        self.auto_save_action.triggered.connect(self._toggle_auto_save)
        self.toolbar.addAction(self.auto_save_action)
        
        # Another spacer
        self.spacer3 = QWidget()
        self.spacer3.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer3)
        
        # Search in Files action
        self.search_files_action = QAction("🔍 Search in Files", self)
        self.search_files_action.triggered.connect(self._open_file_search)
        self.toolbar.addAction(self.search_files_action)
        
        # Another spacer
        self.spacer4 = QWidget()
        self.spacer4.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer4)
        
        # Export action with dropdown menu
        self.export_action = QAction("📤 Export", self)
        self.export_action.setEnabled(False)
        self.toolbar.addAction(self.export_action)
        
        # Get the button widget for the export action to add popup menu
        export_button = None
        for widget in self.toolbar.children():
            if (isinstance(widget, QToolButton) and
                    widget.defaultAction() == self.export_action):
                export_button = widget
                break
                
        if export_button:
            export_button.setPopupMode(
                QToolButton.ToolButtonPopupMode.InstantPopup
            )
            
            # Create export menu
            export_menu = QMenu(self)
            export_menu.setStyleSheet(f"""
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
            
            # Export current note options
            export_html_action = QAction("📄 Export as HTML", self)
            export_html_action.triggered.connect(
                self._export_current_note_html)
            export_menu.addAction(export_html_action)
            
            export_txt_action = QAction("📝 Export as Text", self)
            export_txt_action.triggered.connect(self._export_current_note_txt)
            export_menu.addAction(export_txt_action)
            
            export_pdf_action = QAction("📑 Export as PDF", self)
            export_pdf_action.triggered.connect(self._export_current_note_pdf)
            export_menu.addAction(export_pdf_action)
            
            export_menu.addSeparator()
            
            # Export all notes option
            export_all_action = QAction("📦 Export All Notes (ZIP)", self)
            export_all_action.triggered.connect(self._export_all_notes)
            export_menu.addAction(export_all_action)
            
            export_button.setMenu(export_menu)
        
        # Another spacer
        self.spacer6 = QWidget()
        self.spacer6.setFixedWidth(self._scaling_helper.scaled_size(20))
        self.toolbar.addWidget(self.spacer6)
        
        # Note count label
        self.count_label = QLabel("0 notes")
        self.count_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
        """)
        self.toolbar.addWidget(self.count_label)
        
        container_layout.addWidget(self.toolbar)
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
        
        return container
    
    def _create_tag_panel(self) -> QWidget:
        """Create the collapsible tag panel."""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border-left: 2px solid {DinoPitColors.SOFT_ORANGE};
            }}
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tag filter info
        self.tag_filter_info = QLabel("No tag filters active")
        self.tag_filter_info.setStyleSheet(f"""
            padding: 10px;
            background-color: {DinoPitColors.PANEL_BACKGROUND};
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
        """)
        self.tag_filter_info.hide()
        layout.addWidget(self.tag_filter_info)
        
        # Clear filters button
        self.clear_filters_btn = QPushButton("Clear Filters")
        self.clear_filters_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        self.clear_filters_btn.clicked.connect(self._clear_tag_filters)
        self.clear_filters_btn.hide()
        layout.addWidget(self.clear_filters_btn)
        
        # Tag manager
        self.tag_manager = TagManager()
        self.tag_manager.tag_clicked.connect(self._on_tag_clicked)
        self.tag_manager.tags_updated.connect(self._on_tags_updated)
        layout.addWidget(self.tag_manager)
        
        return panel
        
    def _load_notes(self):
        """Load notes from database."""
        try:
            # Apply project filter if active
            if self._current_project_filter:
                notes = self.notes_db.get_notes_by_project(
                    self._current_project_filter
                )
            else:
                notes = self.notes_db.get_all_notes()
            
            self.note_list.load_notes(notes)
            self._update_note_count()
            
            # Select first note if available
            if notes:
                self.note_list.select_first_note()
            else:
                # Clear editor if no notes
                self.note_editor.clear_editor()
                self._current_note = None
                
                # Update UI state
                if hasattr(self, 'export_action'):
                    self.export_action.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Failed to load notes: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load notes: {str(e)}"
            )
            
    def _create_new_note(self):
        """Create a new note."""
        # Check for unsaved changes
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
                
        # Clear editor and selection
        self.note_editor.clear_editor()
        self.note_list.clear_selection()
        self._current_note = None
        self._has_unsaved_changes = False
        
        # Focus on title
        self.note_editor.set_focus()
        
        # Update UI state
        self.save_action.setEnabled(True)
        self.delete_action.setEnabled(False)
        if hasattr(self, 'export_action'):
            self.export_action.setEnabled(False)
        
    def _on_note_selected(self, note: Note):
        """Handle note selection from list."""
        # Check for unsaved changes
        if self._has_unsaved_changes and self._current_note:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them first?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                # Restore previous selection
                if self._current_note:
                    self.note_list._select_note_by_id(self._current_note.id)
                return
                
        # Load selected note
        self._current_note = note
        
        # Update project combo box to match note's project
        if hasattr(note, 'project_id'):
            self.project_combo.set_project_id(note.project_id)
        else:
            self.project_combo.set_project_id(None)
        
        # Check if note has HTML content
        content_html = getattr(note, 'content_html', None)
        
        self.note_editor.load_note(
            note.id,
            note.title,
            note.content,
            note.tags,
            content_html=content_html
        )
        self._has_unsaved_changes = False
        
        # Update UI state
        self.save_action.setEnabled(False)
        self.delete_action.setEnabled(True)
        self.export_action.setEnabled(True)
        
        # Update available tags for autocomplete
        self._update_available_tags()
        
    def _on_note_changed(self):
        """Handle changes in the editor."""
        self._has_unsaved_changes = True
        self.save_action.setEnabled(True)
        
    def _on_auto_save_requested(self):
        """Handle auto-save request from editor with rate limiting."""
        if self._auto_save_enabled and self._has_unsaved_changes:
            # Apply rate limiting
            if self._security.rate_limiter.is_allowed():
                self._auto_save_note()
            else:
                self.logger.warning(
                    "Auto-save rate limit exceeded, skipping save"
                )
                self.note_editor.set_save_status_error(
                    "Auto-save rate limit exceeded"
                )
        
    def _save_note(self, is_auto_save: bool = False):
        """Save current note.
        
        Args:
            is_auto_save: Whether this is an auto-save operation
        """
        # Get note data (already sanitized by note_editor)
        note_data = self.note_editor.get_note_data()
        
        # Handle both 4-tuple (old) and 5-tuple (new with HTML) returns
        if len(note_data) == 5:
            note_id, title, content, tags, content_html = note_data
        else:
            # Backward compatibility
            note_id, title, content, tags = note_data
            content_html = None
        
        # Validate
        if not title and not content:
            if not is_auto_save:
                QMessageBox.warning(
                    self,
                    "Empty Note",
                    "Cannot save an empty note. Please add a title or content."
                )
            return
            
        # For new notes, require at least a title before auto-saving
        if is_auto_save and not note_id and not title:
            return
            
        try:
            if note_id:
                # Update existing note
                updates = {
                    "title": title or "Untitled Note",
                    "content": content,
                    "tags": tags
                }
                
                # Add HTML content if available
                if content_html:
                    updates["content_html"] = content_html
                
                # Add project_id from combo box
                project_id = self.project_combo.get_selected_project_id()
                current_project_id = getattr(
                    self._current_note, 'project_id', None
                )
                if project_id != current_project_id:
                    updates["project_id"] = project_id
                
                result = self.notes_db.update_note(note_id, updates)
                
                if result["success"]:
                    self.logger.info(f"Updated note: {note_id}")
                    self._has_unsaved_changes = False
                    self.save_action.setEnabled(False)
                    
                    # Update save status
                    self.note_editor.set_save_status_saved()
                    
                    # Store last saved content for conflict detection
                    self._last_saved_content[note_id] = {
                        'title': title,
                        'content': content,
                        'tags': tags,
                        'content_html': content_html,
                        'timestamp': datetime.now()
                    }
                    
                    # Refresh list
                    self._load_notes()
                    
                    # Restore selection
                    self.note_list._select_note_by_id(note_id)
                    
                    # Start conflict checking if auto-save is enabled
                    if (self._auto_save_enabled and
                            not self._conflict_check_timer.isActive()):
                        self._conflict_check_timer.start()
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            else:
                # Create new note
                new_note = Note(
                    title=title or "Untitled Note",
                    content=content,
                    tags=tags
                )
                
                # Get selected project ID
                project_id = self.project_combo.get_selected_project_id()
                
                result = self.notes_db.create_note(
                    new_note, content_html, project_id
                )
                
                if result["success"]:
                    self.logger.info(f"Created new note: {new_note.id}")
                    self._has_unsaved_changes = False
                    self.save_action.setEnabled(False)
                    
                    # Update save status
                    self.note_editor.set_save_status_saved()
                    
                    # Store last saved content
                    self._last_saved_content[new_note.id] = {
                        'title': title,
                        'content': content,
                        'tags': tags,
                        'content_html': content_html,
                        'timestamp': datetime.now()
                    }
                    
                    # Update current note ID in editor
                    self._current_note = new_note
                    self.note_editor._current_note_id = new_note.id
                    
                    # Refresh list
                    self._load_notes()
                    
                    # Select the new note
                    self.note_list._select_note_by_id(new_note.id)
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
        except Exception as e:
            self.logger.error(f"Failed to save note: {str(e)}")
            self.note_editor.set_save_status_error()
            if not is_auto_save:
                QMessageBox.critical(
                    self,
                    "Save Error",
                    f"Failed to save note: {str(e)}"
                )
    
    def _toggle_auto_save(self, checked: bool):
        """Toggle auto-save functionality."""
        self._auto_save_enabled = checked
        self.note_editor.set_auto_save_enabled(checked)
        self._save_auto_save_settings()
        
        if checked:
            self.logger.info("Auto-save enabled")
        else:
            self.logger.info("Auto-save disabled")
            self._conflict_check_timer.stop()
            
    def _auto_save_note(self):
        """Perform auto-save operation."""
        self._save_note(is_auto_save=True)
        
    def _check_for_conflicts(self):
        """Check if the current note was modified elsewhere."""
        if not self._current_note or not self._auto_save_enabled:
            return
            
        try:
            # Get current version from database
            db_note = self.notes_db.get_note(self._current_note.id)
            if not db_note:
                return
                
            # Check if note was modified since last save
            last_save = self._last_saved_content.get(self._current_note.id)
            if not last_save:
                return
                
            # Compare with database version
            if (db_note.title != last_save['title'] or
                    db_note.content != last_save['content'] or
                    set(db_note.tags) != set(last_save['tags'])):
                
                # Conflict detected
                self.note_editor.set_save_status_error("Conflict detected!")
                
                reply = QMessageBox.question(
                    self,
                    "Note Modified Elsewhere",
                    "This note has been modified elsewhere. "
                    "Would you like to:\n\n"
                    "• Keep your version (overwrite the other changes)\n"
                    "• Load the other version (lose your changes)\n",
                    QMessageBox.StandardButton.Save |
                    QMessageBox.StandardButton.Discard,
                    QMessageBox.StandardButton.Save
                )
                
                if reply == QMessageBox.StandardButton.Discard:
                    # Load the database version
                    self._on_note_selected(db_note)
                else:
                    # Keep current version and save
                    self._save_note()
                    
        except Exception as e:
            self.logger.error(f"Failed to check for conflicts: {str(e)}")
            
    def _load_auto_save_settings(self):
        """Load auto-save settings from configuration."""
        try:
            import json
            import os
            
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(__file__)
                ))),
                'config',
                'app_config.json'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    
                notes_config = config.get('notes', {})
                auto_save_config = notes_config.get('auto_save', {})
                
                # Load settings
                self._auto_save_enabled = auto_save_config.get('enabled', True)
                interval = auto_save_config.get('interval_seconds', 2)
                conflict_interval = auto_save_config.get(
                    'conflict_check_interval_seconds', 5
                )
                
                # Apply settings
                self.note_editor.set_auto_save_enabled(self._auto_save_enabled)
                self.note_editor.set_auto_save_interval(interval)
                self._conflict_check_timer.setInterval(
                    conflict_interval * 1000
                )
                
                # Update UI
                self.auto_save_action.setChecked(self._auto_save_enabled)
                
                self.logger.info(
                    f"Loaded auto-save settings: "
                    f"enabled={self._auto_save_enabled}, "
                    f"interval={interval}s"
                )
            else:
                # Default settings
                self._auto_save_enabled = True
                self.note_editor.set_auto_save_enabled(True)
                
        except Exception as e:
            self.logger.error(f"Failed to load auto-save settings: {str(e)}")
            # Use defaults on error
            self._auto_save_enabled = True
            self.note_editor.set_auto_save_enabled(True)
        
    def _save_auto_save_settings(self):
        """Save auto-save settings to configuration."""
        try:
            import json
            import os
            
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.dirname(__file__)
                ))),
                'config',
                'app_config.json'
            )
            
            # Read existing config
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update auto-save setting
            if 'notes' not in config:
                config['notes'] = {}
            if 'auto_save' not in config['notes']:
                config['notes']['auto_save'] = {}
                
            config['notes']['auto_save']['enabled'] = self._auto_save_enabled
            
            # Write back
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            self.logger.info(
                f"Saved auto-save settings: "
                f"enabled={self._auto_save_enabled}"
            )
                
        except Exception as e:
            self.logger.error(f"Failed to save auto-save settings: {str(e)}")
            
    def _delete_note(self):
        """Delete current note."""
        if not self._current_note:
            return
            
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Delete Note",
            f"Are you sure you want to delete '{self._current_note.title}'?",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                result = self.notes_db.delete_note(self._current_note.id)
                
                if result["success"]:
                    self.logger.info(f"Deleted note: {self._current_note.id}")
                    
                    # Clear editor
                    self.note_editor.clear_editor()
                    self._current_note = None
                    self._has_unsaved_changes = False
                    
                    # Update UI state
                    if hasattr(self, 'export_action'):
                        self.export_action.setEnabled(False)
                    
                    # Refresh list
                    self._load_notes()
                else:
                    raise Exception(result.get("error", "Unknown error"))
                    
            except Exception as e:
                self.logger.error(f"Failed to delete note: {str(e)}")
                QMessageBox.critical(
                    self,
                    "Delete Error",
                    f"Failed to delete note: {str(e)}"
                )
                
    def _update_note_count(self):
        """Update the note count display."""
        count = self.note_list.get_note_count()
        self.count_label.setText(f"{count} note{'s' if count != 1 else ''}")
        
    def closeEvent(self, event):
        """Handle close event to check for unsaved changes."""
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._save_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
                
        event.accept()
    
    def _search_notes(self, query: str, filter_option: str):
        """Search notes based on query and filter.
        
        Note: Query is already sanitized by NotesSearchWidget
        """
        try:
            # Perform search (query already sanitized by search widget)
            # Include current project filter if active
            search_results = self.notes_db.search_notes(
                query, filter_option, self._current_project_filter
            )
            
            # Update note list with search results
            self.note_list.filter_notes(search_results, query)
            
            # Update count label
            count = len(search_results)
            if count == 0:
                self.count_label.setText(f"No notes found for '{query}'")
            else:
                self.count_label.setText(
                    f"{count} note{'s' if count != 1 else ''} found"
                )
                
            # Select first result if available
            if search_results:
                self.note_list.select_first_note()
            else:
                # Clear editor if no results
                self.note_editor.clear_editor()
                self._current_note = None
                
        except Exception as e:
            self.logger.error(f"Failed to search notes: {str(e)}")
            QMessageBox.critical(
                self,
                "Search Error",
                f"Failed to search notes: {str(e)}"
            )
            
    def _clear_search(self):
        """Clear search and show all notes."""
        # Clear filter in note list
        self.note_list.clear_filter()
        
        # Reload notes with project filter still applied
        self._load_notes()
        
        # If no notes were selected, select the first one
        has_selection = self.note_list.get_selected_note()
        has_notes = self.note_list.get_note_count() > 0
        if not has_selection and has_notes:
            self.note_list.select_first_note()
            
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Ctrl+F to focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.search_widget.focus_search)
        
        # Escape to clear search (when search is focused)
        escape_shortcut = QShortcut(
            QKeySequence("Escape"),
            self.search_widget.search_input
        )
        escape_shortcut.activated.connect(self._clear_search)
    
    def _toggle_tag_panel(self, checked: bool):
        """Toggle the tag panel visibility with animation."""
        self._tag_panel_visible = checked
        
        # Create animation
        self.tag_panel_animation = QPropertyAnimation(
            self.tag_panel, b"maximumWidth"
        )
        self.tag_panel_animation.setDuration(300)
        self.tag_panel_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if checked:
            # Show panel
            self.tag_panel_animation.setStartValue(0)
            # Try to restore saved width or use default
            saved_width = window_state_manager.get_splitter_state(
                "notes_tag_panel"
            )
            if saved_width:
                # Tag panel stores a single width value
                if isinstance(saved_width, int):
                    width_value = saved_width
                else:
                    width_value = 300  # Default if unexpected type
                scaled_width = self._scaling_helper.scaled_size(width_value)
            else:
                scaled_width = self._scaling_helper.scaled_size(300)
            self.tag_panel_animation.setEndValue(scaled_width)
            self.tag_panel.setMinimumWidth(
                self._scaling_helper.scaled_size(250)
            )
            # Connect to save state when animation finishes
            self.tag_panel_animation.finished.connect(
                self._save_tag_panel_state
            )
        else:
            # Hide panel
            self.tag_panel_animation.setStartValue(self.tag_panel.width())
            self.tag_panel_animation.setEndValue(0)
            self.tag_panel_animation.finished.connect(
                lambda: self.tag_panel.setMinimumWidth(0)
            )
        
        self.tag_panel_animation.start()
    
    def _update_available_tags(self):
        """Update available tags for autocomplete."""
        try:
            tags = list(self.notes_db.get_all_tags().keys())
            self.note_editor.set_available_tags(tags)
        except Exception as e:
            self.logger.error(f"Failed to update available tags: {str(e)}")
    
    def _on_tag_clicked(self, tag: str):
        """Handle tag click from tag manager."""
        if tag in self._active_tag_filters:
            # Remove from filters
            self._active_tag_filters.remove(tag)
        else:
            # Add to filters
            self._active_tag_filters.append(tag)
        
        # Update filter display
        self._update_tag_filter_display()
        
        # Apply filters
        self._apply_tag_filters()
    
    def _update_tag_filter_display(self):
        """Update the tag filter information display."""
        if self._active_tag_filters:
            self.tag_filter_info.setText(
                f"Filtering by: {', '.join(self._active_tag_filters)}"
            )
            self.tag_filter_info.show()
            self.clear_filters_btn.show()
        else:
            self.tag_filter_info.hide()
            self.clear_filters_btn.hide()
    
    def _apply_tag_filters(self):
        """Apply tag filters to the note list."""
        if not self._active_tag_filters:
            # No filters, show all notes
            self._load_notes()
            return
        
        try:
            # Get all notes and filter by tags
            all_notes = self.notes_db.get_all_notes()
            filtered_notes = []
            
            for note in all_notes:
                # Check if note has all active filter tags
                note_tags_lower = [t.lower() for t in note.tags]
                if all(filter_tag.lower() in note_tags_lower
                       for filter_tag in self._active_tag_filters):
                    filtered_notes.append(note)
            
            # Update note list
            self.note_list.load_notes(filtered_notes)
            
            # Update count
            count = len(filtered_notes)
            filter_count = len(self._active_tag_filters)
            self.count_label.setText(
                f"{count} note{'s' if count != 1 else ''} "
                f"(filtered by {filter_count} "
                f"tag{'s' if filter_count != 1 else ''})"
            )
            
            # Select first note if available
            if filtered_notes:
                self.note_list.select_first_note()
            else:
                # Clear editor if no results
                self.note_editor.clear_editor()
                self._current_note = None
                
        except Exception as e:
            self.logger.error(f"Failed to apply tag filters: {str(e)}")
            QMessageBox.critical(
                self,
                "Filter Error",
                f"Failed to apply tag filters: {str(e)}"
            )
    
    def _clear_tag_filters(self):
        """Clear all tag filters."""
        self._active_tag_filters.clear()
        self.tag_manager.clear_selection()
        self._update_tag_filter_display()
        self._load_notes()
    
    def _on_tags_updated(self):
        """Handle tag updates from tag manager."""
        # Refresh the tag list in tag manager
        self.tag_manager.refresh_tags()
        
        # Update available tags for autocomplete
        self._update_available_tags()
        
        # Reload notes to reflect any tag changes
        if self._active_tag_filters:
            self._apply_tag_filters()
        else:
            self._load_notes()
    
    def _export_current_note_html(self):
        """Export current note as HTML."""
        if not self._current_note:
            QMessageBox.warning(
                self,
                "No Note Selected",
                "Please select a note to export."
            )
            return
            
        self._exporter.export_note_as_html(self._current_note, self)
        
    def _export_current_note_txt(self):
        """Export current note as text."""
        if not self._current_note:
            QMessageBox.warning(
                self,
                "No Note Selected",
                "Please select a note to export."
            )
            return
            
        self._exporter.export_note_as_txt(self._current_note, self)
        
    def _export_current_note_pdf(self):
        """Export current note as PDF."""
        if not self._current_note:
            QMessageBox.warning(
                self,
                "No Note Selected",
                "Please select a note to export."
            )
            return
            
        self._exporter.export_note_as_pdf(self._current_note, self)
        
    def _export_all_notes(self):
        """Export all notes as ZIP archive."""
        try:
            # Get all notes
            notes = self.notes_db.get_all_notes()
            
            if not notes:
                QMessageBox.information(
                    self,
                    "No Notes",
                    "There are no notes to export."
                )
                return
                
            self._exporter.export_all_notes(notes, self)
            
        except Exception as e:
            self.logger.error(f"Failed to export all notes: {str(e)}")
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export notes: {str(e)}"
            )
    
    def _update_splitter_sizes(self):
        """Set splitter proportions based on window width."""
        total_width = self.width()
        self.content_splitter.setSizes([
            int(total_width * 0.3),  # 30% for list
            int(total_width * 0.7)   # 70% for editor
        ])
    
    def resizeEvent(self, event):
        """Handle resize events to update splitter proportions."""
        super().resizeEvent(event)
        if hasattr(self, 'content_splitter'):
            # Don't update sizes if we have restored state
            if not hasattr(self, '_state_restored'):
                self._update_splitter_sizes()
    
    def _save_content_splitter_state(self):
        """Save the content splitter state when it changes."""
        window_state_manager.save_splitter_from_widget(
            "notes_content", self.content_splitter
        )
    
    def _restore_content_splitter_state(self):
        """Restore the content splitter state if available."""
        window_state_manager.restore_splitter_to_widget(
            "notes_content", self.content_splitter
        )
        self._state_restored = True
    
    def _save_tag_panel_state(self):
        """Save the tag panel width when visible."""
        if self._tag_panel_visible and self.tag_panel.width() > 0:
            # Save the unscaled width value (as a single int, not list)
            scale_factor = self._scaling_helper.get_scale_factor()
            unscaled_width = int(self.tag_panel.width() / scale_factor)
            # For tag panel, save as single value
            window_state_manager.state_data["splitters"]["notes_tag_panel"] = \
                unscaled_width
            window_state_manager._save_state()
    
    def _update_toolbar_style(self):
        """Update toolbar style with current scaling."""
        s = self._scaling_helper  # Shorter alias
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
        """)
    
    def _update_spacer_widths(self):
        """Update spacer widths with current scaling."""
        spacer_width = self._scaling_helper.scaled_size(20)
        if hasattr(self, 'spacer1'):
            self.spacer1.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer2'):
            self.spacer2.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer3'):
            self.spacer3.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer4'):
            self.spacer4.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer5'):
            self.spacer5.setFixedWidth(spacer_width)
        if hasattr(self, 'spacer6'):
            self.spacer6.setFixedWidth(spacer_width)
    
    def _update_notes_pane_sizes(self):
        """Update notes pane sizes with current scaling."""
        # Find the notes pane widget
        if hasattr(self, 'content_splitter'):
            notes_pane = self.content_splitter.widget(0)
            if notes_pane:
                notes_pane.setMaximumWidth(
                    self._scaling_helper.scaled_size(350)
                )
                notes_pane.setMinimumWidth(
                    self._scaling_helper.scaled_size(200)
                )
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update toolbar style
        self._update_toolbar_style()
        
        # Update spacer widths
        self._update_spacer_widths()
        
        # Update notes pane sizes
        self._update_notes_pane_sizes()
        
        # Update tag panel if visible
        if self._tag_panel_visible and hasattr(self, 'tag_panel'):
            # Update minimum width
            self.tag_panel.setMinimumWidth(
                self._scaling_helper.scaled_size(250)
            )
            # If panel is visible, update its current width
            if self.tag_panel.width() > 0:
                # Get saved unscaled width
                saved_width = window_state_manager.get_splitter_state(
                    "notes_tag_panel"
                )
                if saved_width:
                    if isinstance(saved_width, int):
                        width_value = saved_width
                    else:
                        width_value = 300
                    scaled_width = self._scaling_helper.scaled_size(
                        width_value
                    )
                    self.tag_panel.setMaximumWidth(scaled_width)
    
    def _open_file_search(self):
        """Open the File Search page for cross-referencing"""
        # Get the current note content or selection
        search_query = ""
        if self._current_note and self._current_note.title:
            # Use note title as default search
            search_query = self._current_note.title
        
        # Import here to avoid circular imports
        from PySide6.QtWidgets import QApplication
        
        # Get main window reference
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if widget.__class__.__name__ == 'MainWindow':
                main_window = widget
                break
        
        if main_window and hasattr(main_window, 'tabbed_content'):
            # Access tabbed_content safely
            tabbed_content = getattr(main_window, 'tabbed_content', None)
            if tabbed_content and hasattr(tabbed_content, 'tabs'):
                # Switch to File Search tab
                tabs = getattr(tabbed_content, 'tabs', [])
                tab_widget = getattr(tabbed_content, 'tab_widget', None)
                
                for i, tab in enumerate(tabs):
                    if tab.get('id') == 'file_search' and tab_widget:
                        tab_widget.setCurrentIndex(i)
                        
                        # Get the file search page
                        file_search_page = tab_widget.widget(i)
                        
                        # Set the search query if available
                        if (hasattr(file_search_page, 'search_input') and
                                search_query):
                            file_search_page.search_input.setText(search_query)
                            if hasattr(file_search_page, '_perform_search'):
                                file_search_page._perform_search()
                        
                        break
    
    def _on_project_filter_changed(self, project_id: Optional[str]):
        """Handle project filter change from combo box"""
        self._current_project_filter = project_id
        
        # Clear any existing note selection
        self.note_editor.clear_editor()
        self._current_note = None
        self._has_unsaved_changes = False
        
        # Reload notes with new filter
        self._load_notes()
        
        # Update UI state
        self.save_action.setEnabled(False)
        self.delete_action.setEnabled(False)
        if hasattr(self, 'export_action'):
            self.export_action.setEnabled(False)
