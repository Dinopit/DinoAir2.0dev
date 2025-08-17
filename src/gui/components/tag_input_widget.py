"""
Tag Input Widget - A sophisticated tag input component with chips/badges
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QScrollArea, QCompleter, QMessageBox
)
from PySide6.QtCore import (
    Qt, Signal, QRect, QTimer
)
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor,
    QDragEnterEvent, QDropEvent
)

from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from .notes_security import get_notes_security
try:
    from shiboken6 import Shiboken  # For safe object validity checks
except Exception:  # pragma: no cover - optional at runtime
    Shiboken = None  # type: ignore


class TagChip(QWidget):
    """Individual tag chip/badge widget."""
    
    removed = Signal(str)  # Emitted when tag is removed
    
    def __init__(self, tag: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.logger = Logger()
        self._hover = False
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the tag chip UI."""
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 4, 4)
        layout.setSpacing(5)
        
        # Tag label
        self.label = QWidget()
        self.label.setMinimumWidth(40)
        layout.addWidget(self.label)
        
        # Remove button
        self.remove_btn = QPushButton("×")
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 18px;
                font-weight: bold;
                padding: 0;
                margin: 0;
            }}
            QPushButton:hover {{
                color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self.tag))
        layout.addWidget(self.remove_btn)
        
        # Calculate width based on text
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.tag)
        self.setFixedWidth(text_width + 50)  # padding + button
        
    def paintEvent(self, event: QPaintEvent):
        """Custom paint event for rounded chip appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Generate consistent color based on tag name
        tag_color = self._generate_tag_color(self.tag)
        
        # Background
        if self._hover:
            bg_color = tag_color.lighter(110)
        else:
            bg_color = tag_color
            
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 14, 14)
        
        # Text
        painter.setPen(QColor(DinoPitColors.PRIMARY_TEXT))
        text_rect = QRect(10, 0, self.width() - 40, self.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self.tag)
        
    def _generate_tag_color(self, tag: str) -> QColor:
        """Generate a consistent color for a tag based on its name."""
        # Simple hash-based color generation
        hash_value = sum(ord(c) for c in tag.lower())
        
        # Define a palette of tag colors
        colors = [
            QColor(255, 107, 53, 100),   # Orange with transparency
            QColor(0, 191, 255, 100),     # Cyan with transparency
            QColor(255, 69, 0, 100),      # Fire orange with transparency
            QColor(204, 139, 102, 100),   # Soft orange with transparency
            QColor(52, 67, 89, 150),      # Panel background with more opacity
        ]
        
        return colors[hash_value % len(colors)]
        
    def enterEvent(self, event):
        """Handle mouse enter."""
        self._hover = True
        self.update()
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover = False
        self.update()


class TagInputWidget(QWidget):
    """Tag input widget with chips/badges display and autocomplete."""
    
    tags_changed = Signal(list)  # Emitted when tags are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger()
        self._tags: List[str] = []
        self._all_tags: List[str] = []  # For autocomplete
        self._security = get_notes_security()
        self._setup_ui()
        self._setup_completer()
        
    def _setup_ui(self):
        """Setup the widget UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Container for tags and input
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
            }}
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(5, 5, 5, 5)
        container_layout.setSpacing(5)
        
        # Scroll area for tags
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setMaximumHeight(40)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                height: 8px;
            }
        """)
        
        # Tags container
        self.tags_widget = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(5)
        self.tags_layout.addStretch()
        
        self.scroll_area.setWidget(self.tags_widget)
        container_layout.addWidget(self.scroll_area)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add tag...")
        self.input_field.setMinimumWidth(100)
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background-color: transparent;
                color: {DinoPitColors.PRIMARY_TEXT};
                padding: 4px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                outline: none;
            }}
        """)
        self.input_field.returnPressed.connect(self._add_current_tag)
        self.input_field.textChanged.connect(self._on_text_changed)
        container_layout.addWidget(self.input_field)
        
        main_layout.addWidget(container)
        
        # Set focus on click
        container.mousePressEvent = lambda e: self.input_field.setFocus()
        
    def _setup_completer(self):
        """Setup autocomplete for tag input."""
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input_field.setCompleter(self.completer)
        
    def _on_text_changed(self, text: str):
        """Handle text changes in input field."""
        # Check for comma
        if ',' in text:
            # Split by comma and add tags
            parts = text.split(',')
            for part in parts[:-1]:  # All except last part
                tag = part.strip()
                if tag:
                    self._add_tag(tag)
            # Keep only the last part in input
            self.input_field.setText(parts[-1].strip())
            
    def _add_current_tag(self):
        """Add the current input as a tag."""
        tag = self.input_field.text().strip()
        if tag:
            self._add_tag(tag)
            self.input_field.clear()
            
    def _add_tag(self, tag: str):
        """Add a tag if it doesn't already exist with sanitization."""
        # Sanitize the tag
        sanitized_tag = self._security.sanitize_tag(tag)
        
        if not sanitized_tag:
            # Tag was rejected by security
            QMessageBox.warning(
                self,
                "Invalid Tag",
                f"The tag '{tag}' is not valid and was rejected."
            )
            return
            
        # Check if tag changed significantly
        if sanitized_tag != tag:
            # Warn user about modification
            reply = QMessageBox.question(
                self,
                "Tag Modified",
                f"The tag '{tag}' was modified to '{sanitized_tag}' "
                f"for security reasons. Add the modified tag?",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Case-insensitive duplicate check
        if not any(t.lower() == sanitized_tag.lower() for t in self._tags):
            # Check tag limit
            if len(self._tags) >= 20:  # MAX_TAGS_PER_NOTE from security config
                QMessageBox.warning(
                    self,
                    "Tag Limit Reached",
                    "Maximum number of tags (20) has been reached."
                )
                return
                
            # Create tag chip
            chip = TagChip(sanitized_tag)
            chip.removed.connect(self._remove_tag)
            
            # Insert before the stretch
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, chip)
            
            # Add to tags list
            self._tags.append(sanitized_tag)
            
            # Emit change signal
            self.tags_changed.emit(self._tags.copy())
            
            # Scroll to show new tag (safely)
            self._scroll_chip_into_view_later(chip)
        else:
            # Tag already exists
            QMessageBox.information(
                self,
                "Duplicate Tag",
                f"The tag '{sanitized_tag}' already exists."
            )
            
    def _remove_tag(self, tag: str):
        """Remove a tag."""
        # Find and remove the chip
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagChip) and widget.tag == tag:
                widget.deleteLater()
                self.tags_layout.removeWidget(widget)
                break
                
        # Remove from tags list
        self._tags = [t for t in self._tags if t != tag]
        
        # Emit change signal
        self.tags_changed.emit(self._tags.copy())
        
    def set_tags(self, tags: List[str]):
        """Set the current tags with sanitization."""
        # Clear existing tags
        self.clear_tags()
        
        # Sanitize all tags first
        sanitized_tags = self._security.sanitize_tags(tags)
        
        # Add sanitized tags
        for tag in sanitized_tags:
            if tag:
                # Add without re-sanitizing since already done
                self._add_tag_internal(tag)
                
    def _add_tag_internal(self, tag: str):
        """Internal method to add already sanitized tag."""
        # Case-insensitive duplicate check
        if not any(t.lower() == tag.lower() for t in self._tags):
            # Create tag chip
            chip = TagChip(tag)
            chip.removed.connect(self._remove_tag)
            
            # Insert before the stretch
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, chip)
            
            # Add to tags list
            self._tags.append(tag)
            
            # Emit change signal
            self.tags_changed.emit(self._tags.copy())
            
            # Scroll to show new tag (safely)
            self._scroll_chip_into_view_later(chip)
    
    def _scroll_chip_into_view_later(self, chip: 'TagChip'):
        """Ensure chip is visible later, guarding against deleted objects."""
        def _do_scroll():
            try:
                if Shiboken is not None:
                    if not Shiboken.isValid(self.scroll_area):
                        return
                    if not Shiboken.isValid(chip):
                        return
                # Fallback basic checks
                if self.scroll_area is None or chip is None:
                    return
                self.scroll_area.ensureWidgetVisible(chip)
            except RuntimeError:
                # Under teardown, Qt object may be deleted; ignore
                pass
        QTimer.singleShot(100, _do_scroll)
                
    def get_tags(self) -> List[str]:
        """Get the current tags."""
        return self._tags.copy()
        
    def clear_tags(self):
        """Clear all tags."""
        # Remove all tag chips
        while self.tags_layout.count() > 1:  # Keep the stretch
            item = self.tags_layout.takeAt(0)
            if item.widget() and isinstance(item.widget(), TagChip):
                item.widget().deleteLater()
                
        self._tags.clear()
        self.tags_changed.emit([])
        
    def set_available_tags(self, tags: List[str]):
        """Set available tags for autocomplete."""
        self._all_tags = tags
        # Update the completer with new tags
        self.completer = QCompleter(tags)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input_field.setCompleter(self.completer)

    # Compatibility helpers used by tests expecting a line-edit-like API
    def text(self) -> str:
        """Return tags as a comma-separated string."""
        return ", ".join(self._tags)

    def setText(self, text: str):
        """Set tags from a comma-separated string, trimming whitespace."""
        parts = [t.strip() for t in (text or "").split(',')]
        # Filter empty entries
        tags = [p for p in parts if p]
        self.set_tags(tags)
        
    def focusInEvent(self, event):
        """Handle focus in event."""
        super().focusInEvent(event)
        self.input_field.setFocus()
        
    # Drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        if event.mimeData().hasText():
            text = event.mimeData().text()
            # Parse dropped text as tags (comma separated)
            tags = [t.strip() for t in text.split(',') if t.strip()]
            for tag in tags:
                self._add_tag(tag)
            event.acceptProposedAction()