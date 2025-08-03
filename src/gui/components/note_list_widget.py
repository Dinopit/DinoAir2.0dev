"""
Note List Widget Component - Displays list of notes with custom items
"""

from typing import List, Optional
from datetime import datetime
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont

from ...utils.colors import DinoPitColors
from ...utils.scaling import get_scaling_helper
from ...models.note import Note


class NoteListItem(QWidget):
    """Custom widget for displaying a note in the list."""
    
    def __init__(self, note: Note, search_query: str = ""):
        """Initialize the note list item.
        
        Args:
            note: The Note object to display
            search_query: Optional search query to highlight
        """
        super().__init__()
        self.note = note
        self.search_query = search_query
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the item UI."""
        self._scaling_helper = get_scaling_helper()
        layout = QVBoxLayout(self)
        s = self._scaling_helper  # Shorter alias
        layout.setContentsMargins(
            s.scaled_size(10), s.scaled_size(8),
            s.scaled_size(10), s.scaled_size(8)
        )
        layout.setSpacing(s.scaled_size(4))
        
        # Title
        self.title_label = QLabel(self.note.title or "Untitled Note")
        self.title_label.setStyleSheet("color: #FFFFFF;")
        self.title_font = QFont()
        self.title_font.setBold(True)
        self.title_font.setPointSize(self._scaling_helper.scaled_font_size(11))
        self.title_label.setFont(self.title_font)
        self.title_label.setStyleSheet(f"color: {DinoPitColors.PRIMARY_TEXT};")
        layout.addWidget(self.title_label)
        
        # Preview text (with possible highlighting)
        preview_text = self._get_preview_text()
        if preview_text:
            if self.search_query:
                # Highlight search terms in preview
                preview_html = self._highlight_text(
                    preview_text, self.search_query
                )
                self.preview_label = QLabel(preview_html)
                self.preview_label.setTextFormat(Qt.TextFormat.RichText)
            else:
                self.preview_label = QLabel(preview_text)
                
            self.preview_label.setStyleSheet("color: #FFFFFF;")
            self.preview_label.setWordWrap(False)
            self._update_preview_style()
            layout.addWidget(self.preview_label)
        
        # Bottom row with date and tags
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(self._scaling_helper.scaled_size(10))
        
        # Date
        date_str = self._format_date()
        self.date_label = QLabel(date_str)
        self.date_label.setStyleSheet("color: #FFFFFF;")
        self._update_date_style()
        bottom_layout.addWidget(self.date_label)
        
        # Tags (if any)
        if self.note.tags:
            tags_text = " • ".join(self.note.tags[:3])  # Show max 3 tags
            if len(self.note.tags) > 3:
                tags_text += f" +{len(self.note.tags) - 3}"
            self.tags_label = QLabel(tags_text)
            self.tags_label.setStyleSheet("color: #FFFFFF;")
            self._update_tags_style()
            bottom_layout.addWidget(self.tags_label)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
    def _get_preview_text(self) -> str:
        """Get preview text from note content."""
        if not self.note.content:
            return ""
        
        # Get first line or first 60 chars
        lines = self.note.content.strip().split('\n')
        preview = lines[0] if lines else self.note.content
        
        if len(preview) > 60:
            preview = preview[:57] + "..."
            
        return preview
        
    def _format_date(self) -> str:
        """Format the note's date for display."""
        try:
            # Parse ISO format date
            dt = datetime.fromisoformat(self.note.updated_at)
            
            # Check if today
            today = datetime.now().date()
            note_date = dt.date()
            
            if note_date == today:
                return dt.strftime("Today %I:%M %p")
            elif (today - note_date).days == 1:
                return dt.strftime("Yesterday %I:%M %p")
            elif (today - note_date).days < 7:
                return dt.strftime("%A")  # Day name
            else:
                return dt.strftime("%b %d, %Y")
        except Exception:
            return "Unknown date"
    
    def _highlight_text(self, text: str, query: str) -> str:
        """Highlight search query in text."""
        if not query:
            return text
            
        # Escape special regex characters in query
        escaped_query = re.escape(query)
        # Create case-insensitive pattern
        pattern = re.compile(f'({escaped_query})', re.IGNORECASE)
        # Replace matches with highlighted version
        highlighted = pattern.sub(
            f'<span style="background-color: {DinoPitColors.DINOPIT_ORANGE}; '
            f'color: white; padding: 1px 2px; border-radius: 2px;">\\1</span>',
            text
        )
        return highlighted
    
    def _update_preview_style(self):
        """Update preview label style with current scaling."""
        if hasattr(self, 'preview_label'):
            self.preview_label.setStyleSheet(
                f"color: {DinoPitColors.PRIMARY_TEXT}; "
                f"font-size: {self._scaling_helper.scaled_font_size(10)}px;"
            )
    
    def _update_date_style(self):
        """Update date label style with current scaling."""
        self.date_label.setStyleSheet(
            f"color: {DinoPitColors.SOFT_ORANGE}; "
            f"font-size: {self._scaling_helper.scaled_font_size(9)}px;"
        )
    
    def _update_tags_style(self):
        """Update tags label style with current scaling."""
        if hasattr(self, 'tags_label'):
            self.tags_label.setStyleSheet(
                f"color: {DinoPitColors.PRIMARY_TEXT}; "
                f"font-size: {self._scaling_helper.scaled_font_size(9)}px;"
            )


class NoteListWidget(QWidget):
    """Widget for displaying a list of notes with custom items.
    
    Features:
    - Custom note item display with title and preview
    - Note selection signals
    - Refresh capability
    - Styling consistent with DinoAir theme
    """
    
    # Signals
    note_selected = Signal(Note)  # Emitted when a note is selected
    
    def __init__(self):
        """Initialize the note list widget."""
        super().__init__()
        self._notes: List[Note] = []
        self._filtered_notes: List[Note] = []
        self._selected_note_id: Optional[str] = None
        self._search_mode = False
        self._search_query = ""
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def _setup_ui(self):
        """Setup the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create container for list and empty state
        self.container = QWidget()
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the list widget
        self.list_widget = QListWidget()
        self._update_list_style(False)
        
        # Create empty state widget
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.empty_icon = QLabel("🔍")
        self.empty_icon.setStyleSheet("color: #FFFFFF;")
        self._update_empty_icon_style()
        self.empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.empty_text = QLabel("No notes found")
        self.empty_text.setStyleSheet("color: #FFFFFF;")
        self._update_empty_text_style()
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_icon)
        empty_layout.addWidget(self.empty_text)
        empty_layout.addStretch()
        
        # Add widgets to container
        container_layout.addWidget(self.list_widget)
        container_layout.addWidget(self.empty_state)
        
        # Initially hide empty state
        self.empty_state.hide()
        
        # Connect signals
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.currentItemChanged.connect(self._on_current_changed)
        
        layout.addWidget(self.container)
        
    def load_notes(self, notes: List[Note]):
        """Load notes into the list widget.
        
        Args:
            notes: List of Note objects to display
        """
        # Clear existing items
        self.list_widget.clear()
        self._notes = notes
        
        # Display appropriate notes based on search mode
        notes_to_display = self._filtered_notes if self._search_mode else notes
        
        # Show/hide empty state
        if not notes_to_display and self._search_mode:
            self.list_widget.hide()
            self.empty_state.show()
            self.empty_text.setText(
                f'No notes found for "{self._search_query}"'
            )
        else:
            self.list_widget.show()
            self.empty_state.hide()
        
        # Add notes to list
        for note in notes_to_display:
            # Create custom widget with search highlighting if in search mode
            item_widget = NoteListItem(
                note,
                self._search_query if self._search_mode else ""
            )
            
            # Create list item
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(
                QSize(0, self._scaling_helper.scaled_size(80))
            )  # Scaled height
            list_item.setData(Qt.ItemDataRole.UserRole, note.id)
            
            # Set the custom widget
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            
        # Restore selection if possible
        if self._selected_note_id:
            self._select_note_by_id(self._selected_note_id)
            
    def refresh_notes(self, notes: List[Note]):
        """Refresh the notes list while maintaining selection.
        
        Args:
            notes: Updated list of Note objects
        """
        # Store current selection
        current_item = self.list_widget.currentItem()
        if current_item:
            self._selected_note_id = current_item.data(
                Qt.ItemDataRole.UserRole
            )
            
        # Reload notes
        self.load_notes(notes)
        
    def get_selected_note(self) -> Optional[Note]:
        """Get the currently selected note.
        
        Returns:
            The selected Note object or None
        """
        current_item = self.list_widget.currentItem()
        if not current_item:
            return None
            
        note_id = current_item.data(Qt.ItemDataRole.UserRole)
        for note in self._notes:
            if note.id == note_id:
                return note
                
        return None
        
    def select_first_note(self):
        """Select the first note in the list."""
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
            
    def clear_selection(self):
        """Clear the current selection."""
        self.list_widget.clearSelection()
        self._selected_note_id = None
        
    def _select_note_by_id(self, note_id: str):
        """Select a note by its ID.
        
        Args:
            note_id: The ID of the note to select
        """
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.list_widget.setCurrentItem(item)
                break
                
    def _on_item_clicked(self, item: QListWidgetItem):
        """Handle item click."""
        note_id = item.data(Qt.ItemDataRole.UserRole)
        for note in self._notes:
            if note.id == note_id:
                self._selected_note_id = note_id
                self.note_selected.emit(note)
                break
                
    def _on_current_changed(self, current: QListWidgetItem,
                            previous: QListWidgetItem):
        """Handle current item change."""
        if current:
            self._on_item_clicked(current)
            
    def get_note_count(self) -> int:
        """Get the total number of notes in the list."""
        if self._search_mode:
            return len(self._filtered_notes)
        return len(self._notes)
    
    def filter_notes(self, search_results: List[Note], search_query: str):
        """Filter displayed notes based on search results.
        
        Args:
            search_results: List of notes matching the search
            search_query: The search query used
        """
        self._search_mode = True
        self._search_query = search_query
        self._filtered_notes = search_results
        self._update_list_style(True)
        
        # Reload display with filtered notes
        self.load_notes(self._notes)
        
    def clear_filter(self):
        """Clear search filter and show all notes."""
        self._search_mode = False
        self._search_query = ""
        self._filtered_notes = []
        self._update_list_style(False)
        
        # Reload display with all notes
        self.load_notes(self._notes)
        
    def _update_list_style(self, search_mode: bool):
        """Update list widget style based on search mode."""
        if search_mode:
            # Search mode style with different background
            self.list_widget.setStyleSheet(f"""
                QListWidget {{
                    background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                    border: 2px solid {DinoPitColors.DINOPIT_ORANGE};
                    border-radius: 5px;
                    outline: none;
                }}
                QListWidget::item {{
                    background-color: {DinoPitColors.PANEL_BACKGROUND};
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
        else:
            # Normal mode style
            self.list_widget.setStyleSheet(f"""
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
    
    def is_search_mode(self) -> bool:
        """Check if currently in search mode."""
        return self._search_mode
    
    def _update_empty_icon_style(self):
        """Update empty icon style with current scaling."""
        self.empty_icon.setStyleSheet(
            f"font-size: {self._scaling_helper.scaled_font_size(48)}px; "
            f"color: {DinoPitColors.PRIMARY_TEXT}"
        )
    
    def _update_empty_text_style(self):
        """Update empty text style with current scaling."""
        self.empty_text.setStyleSheet(
            f"color: {DinoPitColors.PRIMARY_TEXT}; "
            f"font-size: {self._scaling_helper.scaled_font_size(16)}px;"
        )
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        # Update empty state styles
        self._update_empty_icon_style()
        self._update_empty_text_style()
        
        # Force reload of notes to update item sizes
        if self._notes:
            # Store current selection
            current_item = self.list_widget.currentItem()
            if current_item:
                self._selected_note_id = current_item.data(
                    Qt.ItemDataRole.UserRole
                )
            
            # Reload notes with new scaling
            self.load_notes(self._notes)