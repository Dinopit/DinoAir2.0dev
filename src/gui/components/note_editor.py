"""
Note Editor Component - Provides editor interface for notes
"""

from typing import Optional, List
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QTextEdit,
    QLabel, QFrame, QMessageBox
)
from PySide6.QtCore import Signal, QTimer

from src.utils.colors import DinoPitColors
from src.utils.scaling import get_scaling_helper
from src.gui.components.tag_input_widget import TagInputWidget
from src.gui.components.notes_security import get_notes_security
from src.gui.components.rich_text_toolbar import RichTextToolbar


class NoteEditor(QWidget):
    """Editor widget for creating and editing notes.
    
    Features:
    - Title input field
    - Rich text content editor with formatting toolbar
    - Tag input field (basic implementation)
    - Character and word count display
    - Auto-save functionality with visual status
    - Signals for note_saved, note_changed, and auto_save_requested
    - HTML content support with plain text fallback
    """
    
    # Signals
    note_changed = Signal()  # Emitted when content changes
    note_saved = Signal(str, str, str)  # title, content, tags
    auto_save_requested = Signal()  # Emitted when auto-save timer triggers
    
    def __init__(self):
        """Initialize the note editor."""
        super().__init__()
        self._current_note_id: Optional[str] = None
        self._last_saved_time: Optional[datetime] = None
        self._security = get_notes_security()
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        self._setup_auto_save()
        self._connect_signals()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _setup_ui(self):
        """Setup the editor UI."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self._update_layout_spacing()

        # Title input
        self.title_input = QLineEdit()
        self.title_input.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")
        self.title_input.setPlaceholderText("Note Title...")
        self._update_title_input_style()
        self.main_layout.addWidget(self.title_input)

        # Tags input widget
        self.tags_input = TagInputWidget()
        self.main_layout.addWidget(self.tags_input)

        # Rich text toolbar
        self.toolbar = RichTextToolbar()
        self.main_layout.addWidget(self.toolbar)

        # Content editor with rich text support
        self.content_editor = QTextEdit()
        self.content_editor.setAcceptRichText(True)
        self.content_editor.setPlaceholderText("Start writing your note...")
        self._update_content_editor_style()

        # Connect toolbar to text editor
        self.toolbar.set_text_edit(self.content_editor)

        self.main_layout.addWidget(self.content_editor)
        # Backward-compatibility: tests expect `content_input`
        self.content_input = self.content_editor

        # Stats bar
        self.stats_frame = QFrame()
        self._update_stats_frame_style()
        self.stats_layout = QHBoxLayout(self.stats_frame)
        self._update_stats_layout_margins()

        self.char_count_label = QLabel("0 characters")
        self.char_count_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT};"
        )

        self.word_count_label = QLabel("0 words")
        self.word_count_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT};"
        )

        self.stats_layout.addWidget(self.char_count_label)
        self.stats_layout.addWidget(QLabel("|"))
        self.stats_layout.addWidget(self.word_count_label)

        # Add separator
        separator = QLabel("|")
        separator.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        self.stats_layout.addWidget(separator)

        # Save status indicator
        self.save_status_label = QLabel("All changes saved")
        self.save_status_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-weight: bold;
        """)
        self.stats_layout.addWidget(self.save_status_label)

        # Save time label
        self.save_time_label = QLabel("")
        self.save_time_label.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT};"
        )
        self.stats_layout.addWidget(self.save_time_label)

        self.stats_layout.addStretch()

        self.main_layout.addWidget(self.stats_frame)
        
    def _setup_auto_save(self):
        """Setup auto-save timer."""
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self._trigger_auto_save)
        
        # Auto-save interval in milliseconds (2 seconds)
        self.auto_save_interval = 2000
        self.auto_save_enabled = True
        
    def _connect_signals(self):
        """Connect internal signals."""
        self.title_input.textChanged.connect(self._on_content_changed)
        self.tags_input.tags_changed.connect(self._on_content_changed)
        self.content_editor.textChanged.connect(self._on_content_changed)
        self.toolbar.format_changed.connect(self._on_content_changed)
        
    def _on_content_changed(self):
        """Handle content changes."""
        # Ignore changes while programmatically updating fields
        if getattr(self, "_suppress_changes", False):
            return
        # Update character and word count
        content = self.content_editor.toPlainText()
        char_count = len(content)
        word_count = len(content.split()) if content.strip() else 0
        
        self.char_count_label.setText(f"{char_count} characters")
        self.word_count_label.setText(f"{word_count} words")
        
        # Update save status
        self._update_save_status("Changes not saved",
                                 DinoPitColors.SOFT_ORANGE)
        
        # Reset auto-save timer if enabled
        if self.auto_save_enabled:
            self.auto_save_timer.stop()
            self.auto_save_timer.start(self.auto_save_interval)
        
        # Emit change signal
        self.note_changed.emit()
        
    def clear_editor(self):
        """Clear all editor fields."""
        self._current_note_id = None
        self.title_input.clear()
        self.tags_input.clear_tags()
        self.content_editor.clear()
        
    def load_note(self, note_id: str, title: str, content: str, tags: list,
                  content_html: Optional[str] = None):
        """Load a note into the editor.
        
        Args:
            note_id: The note's ID
            title: The note title
            content: The note content (plain text)
            tags: List of tags
            content_html: Optional HTML content for rich text
        """
        # Suppress change signals during programmatic updates
        self._suppress_changes = True
        try:
            self._current_note_id = note_id
            self.title_input.blockSignals(True)
            self.content_editor.blockSignals(True)
            self.title_input.setText(title)
            # Load HTML content if available, otherwise plain text
            if content_html:
                self.content_editor.setHtml(content_html)
            else:
                self.content_editor.setPlainText(content)
            self.tags_input.blockSignals(True)
            self.tags_input.set_tags(tags)
        finally:
            self.tags_input.blockSignals(False)
            self.content_editor.blockSignals(False)
            self.title_input.blockSignals(False)
            self._suppress_changes = False
        
    def get_note_data(self) -> tuple:
        """Get current note data with sanitization.
        
        Returns:
            Tuple of (note_id, title, content, tags)
        """
        # Get raw data
        raw_title = self.title_input.text().strip()
        raw_content = self.content_editor.toPlainText()
        raw_content_html = self.content_editor.toHtml()
        raw_tags = self.tags_input.get_tags()
        
        # Sanitize all data (HTML not supported by security method)
        sanitized_data = self._security.sanitize_note_data(
            raw_title, raw_content, raw_tags
        )
        
        # Get sanitized HTML from the result
        sanitized_html = sanitized_data.get('content_html', raw_content_html)
        
        # Check for validation errors
        if not sanitized_data['valid']:
            error_msg = "Security validation failed:\n\n"
            error_msg += "\n".join(
                f"• {error}" for error in sanitized_data['errors']
            )
            QMessageBox.warning(
                self,
                "Invalid Input",
                error_msg
            )
            # Return original data so user can fix it (4-tuple for compatibility)
            return (self._current_note_id, raw_title, raw_content, raw_tags)
        
        # Warn if data was modified
        if sanitized_data['modified']:
            QMessageBox.information(
                self,
                "Input Sanitized",
                "Your input was modified for security reasons. "
                "Please review the changes."
            )
            # Update UI with sanitized values
            self.title_input.setText(sanitized_data['title'])
            self.content_editor.setPlainText(sanitized_data['content'])
            self.tags_input.set_tags(sanitized_data['tags'])
            
        # Return 4-tuple for compatibility with tests
        return (
            self._current_note_id,
            sanitized_data['title'],
            sanitized_data['content'],
            sanitized_data['tags']
        )

    def get_note_data_with_html(self) -> tuple:
        """Get current note data including HTML content.
        
        Returns:
            Tuple of (note_id, title, content, tags, content_html)
        """
        note_id, title, content, tags = self.get_note_data()
        content_html = self.content_editor.toHtml()
        return (note_id, title, content, tags, content_html)
        
    def get_current_note_id(self) -> Optional[str]:
        """Get the ID of the currently loaded note."""
        return self._current_note_id

    # Backward-compatibility alias used by tests
    @property
    def _note_id(self) -> Optional[str]:
        return self._current_note_id

    @_note_id.setter
    def _note_id(self, value: Optional[str]):
        self._current_note_id = value
        
    def has_content(self) -> bool:
        """Check if editor has any content."""
        return bool(
            self.title_input.text().strip() or 
            self.content_editor.toPlainText().strip()
        )
        
    def set_focus(self):
        """Set focus to the title input."""
        self.title_input.setFocus()
        
    def set_available_tags(self, tags: List[str]):
        """Set available tags for autocomplete.
        
        Args:
            tags: List of available tag names
        """
        self.tags_input.set_available_tags(tags)
        
    def _trigger_auto_save(self):
        """Trigger auto-save after timer expires."""
        # Only auto-save if we have content or title
        if self.has_content():
            self._update_save_status("Saving...",
                                     DinoPitColors.DINOPIT_ORANGE)
            self.auto_save_requested.emit()
            
    def _update_save_status(self, status: str, color: str):
        """Update the save status display.
        
        Args:
            status: Status message to display
            color: Color for the status text
        """
        self.save_status_label.setText(status)
        self.save_status_label.setStyleSheet(f"""
            color: {color};
            font-weight: bold;
        """)
        
    def set_save_status_saved(self):
        """Set save status to saved with timestamp."""
        self._last_saved_time = datetime.now()
        self._update_save_status("All changes saved",
                                 DinoPitColors.PRIMARY_TEXT)
        time_str = self._last_saved_time.strftime('%H:%M:%S')
        self.save_time_label.setText(f"at {time_str}")
        
    def set_save_status_error(self, error_msg: str = "Save failed"):
        """Set save status to error.
        
        Args:
            error_msg: Error message to display
        """
        self._update_save_status(error_msg, DinoPitColors.DINOPIT_FIRE)
        
    def set_auto_save_enabled(self, enabled: bool):
        """Enable or disable auto-save.
        
        Args:
            enabled: Whether auto-save should be enabled
        """
        self.auto_save_enabled = enabled
        if not enabled:
            self.auto_save_timer.stop()
            
    def set_auto_save_interval(self, seconds: int):
        """Set auto-save interval.
        
        Args:
            seconds: Auto-save interval in seconds (1-10)
        """
        if 1 <= seconds <= 10:
            self.auto_save_interval = seconds * 1000
            
    def trigger_manual_save(self):
        """Manually trigger a save."""
        self.auto_save_timer.stop()
        self._update_save_status("Saving...",
                                 DinoPitColors.DINOPIT_ORANGE)
        
    def validate_current_input(self) -> bool:
        """Validate current input without saving.
        
        Returns:
            True if input is valid, False otherwise
        """
        raw_title = self.title_input.text().strip()
        raw_content = self.content_editor.toPlainText()
        raw_tags = self.tags_input.get_tags()
        
        # Sanitize and validate
        result = self._security.sanitize_note_data(
            raw_title, raw_content, raw_tags
        )
        
        return result['valid']
        
    def set_read_only(self, read_only: bool):
        """Set editor read-only state.
        
        Args:
            read_only: Whether the editor should be read-only
        """
        self.title_input.setReadOnly(read_only)
        self.content_editor.setReadOnly(read_only)
        self.tags_input.setEnabled(not read_only)
        
        # Hide toolbar in read-only mode
        self.toolbar.set_visible(not read_only)
        self.toolbar.set_enabled(not read_only)
    
    def _update_layout_spacing(self):
        """Update layout spacing with current scaling."""
        self.main_layout.setSpacing(self._scaling_helper.scaled_size(10))
    
    def _update_title_input_style(self):
        """Update title input style with current scaling."""
        s = self._scaling_helper
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: {s.scaled_font_size(18)}px;
                font-weight: bold;
                padding: {s.scaled_size(10)}px;
                border: {s.scaled_size(2)}px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {s.scaled_size(5)}px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
    
    def _update_content_editor_style(self):
        """Update content editor style with current scaling."""
        s = self._scaling_helper
        self.content_editor.setStyleSheet(f"""
            QTextEdit {{
                padding: {s.scaled_size(12)}px;
                border: {s.scaled_size(2)}px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: {s.scaled_size(5)}px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: {s.scaled_font_size(14)}px;
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
    
    def _update_stats_frame_style(self):
        """Update stats frame style with current scaling."""
        s = self._scaling_helper
        self.stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border-radius: {s.scaled_size(4)}px;
                padding: {s.scaled_size(5)}px;
            }}
        """)
    
    def _update_stats_layout_margins(self):
        """Update stats layout margins with current scaling."""
        s = self._scaling_helper
        self.stats_layout.setContentsMargins(
            s.scaled_size(10), s.scaled_size(5),
            s.scaled_size(10), s.scaled_size(5)
        )
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update all scaled styles
        self._update_layout_spacing()
        self._update_title_input_style()
        self._update_content_editor_style()
        self._update_stats_frame_style()
        self._update_stats_layout_margins()