"""
Tag Manager Component - Displays all tags with cloud visualization
"""

from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QMenu, QInputDialog, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import (
    QPainter, QPaintEvent, QColor, QFont, QFontMetrics,
    QMouseEvent, QContextMenuEvent
)

from ...utils.colors import DinoPitColors
from ...utils.logger import Logger
from ...database.notes_db import NotesDatabase


class TagCloudItem(QWidget):
    """Individual tag item in the tag cloud."""
    
    clicked = Signal(str)  # Emitted when tag is clicked
    context_menu_requested = Signal(str, QPoint)  # tag, global_pos
    
    def __init__(self, tag: str, count: int, max_count: int, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.count = count
        self.max_count = max_count
        self.logger = Logger()
        self._hover = False
        self._selected = False
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the tag item UI."""
        # Calculate font size based on count (min 12, max 24)
        self.font_size = self._calculate_font_size()
        
        # Calculate dimensions
        font = QFont()
        font.setPointSize(self.font_size)
        metrics = QFontMetrics(font)
        
        # Text with count
        self.display_text = f"{self.tag} ({self.count})"
        text_width = metrics.horizontalAdvance(self.display_text)
        text_height = metrics.height()
        
        # Set widget size with padding
        self.setFixedSize(text_width + 20, text_height + 10)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def _calculate_font_size(self) -> int:
        """Calculate font size based on tag frequency."""
        if self.max_count == 0:
            return 12
        
        # Normalize count to 0-1 range
        normalized = self.count / self.max_count
        
        # Map to font size range (12-24)
        return int(12 + (normalized * 12))
        
    def _generate_tag_color(self, tag: str) -> QColor:
        """Generate a consistent color for a tag based on its name."""
        # Simple hash-based color generation
        hash_value = sum(ord(c) for c in tag.lower())
        
        # Define a palette of tag colors
        colors = [
            QColor(255, 107, 53),      # Orange
            QColor(0, 191, 255),       # Cyan
            QColor(255, 69, 0),        # Fire orange
            QColor(204, 139, 102),     # Soft orange
            QColor(52, 67, 89),        # Panel background
        ]
        
        base_color = colors[hash_value % len(colors)]
        
        # Adjust opacity based on selection/hover
        if self._selected:
            return base_color
        elif self._hover:
            base_color.setAlpha(200)
            return base_color
        else:
            base_color.setAlpha(150)
            return base_color
        
    def paintEvent(self, event: QPaintEvent):
        """Custom paint event for tag appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get tag color
        tag_color = self._generate_tag_color(self.tag)
        
        # Background
        painter.setBrush(tag_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        
        # Text
        font = QFont()
        font.setPointSize(self.font_size)
        painter.setFont(font)
        painter.setPen(QColor(DinoPitColors.PRIMARY_TEXT))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.display_text)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag)
            
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle context menu."""
        self.context_menu_requested.emit(self.tag, event.globalPos())
        
    def enterEvent(self, event):
        """Handle mouse enter."""
        self._hover = True
        self.update()
        
    def leaveEvent(self, event):
        """Handle mouse leave."""
        self._hover = False
        self.update()
        
    def set_selected(self, selected: bool):
        """Set selection state."""
        self._selected = selected
        self.update()


class TagManager(QWidget):
    """Tag manager widget with tag cloud display."""
    
    tag_clicked = Signal(str)  # Emitted when a tag is clicked
    tags_updated = Signal()    # Emitted when tags are modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger()
        self.notes_db = NotesDatabase()
        self._tag_items: Dict[str, TagCloudItem] = {}
        self._selected_tags: set = set()
        self._setup_ui()
        self.refresh_tags()
        
    def _setup_ui(self):
        """Setup the tag manager UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Tags")
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {DinoPitColors.DINOPIT_ORANGE};
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setToolTip("Refresh tags")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                border: none;
                border-radius: 15px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_tags)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DinoPitColors.SOFT_ORANGE};")
        layout.addWidget(separator)
        
        # Scroll area for tag cloud
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border-radius: 5px;
            }}
        """)
        
        # Tag cloud container
        self.tag_cloud_widget = QWidget()
        self.tag_cloud_layout = FlowLayout(self.tag_cloud_widget)
        self.tag_cloud_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.tag_cloud_widget)
        layout.addWidget(self.scroll_area)
        
        # Info label
        self.info_label = QLabel("No tags found")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"""
            color: {DinoPitColors.PRIMARY_TEXT};
            font-style: italic;
            padding: 20px;
        """)
        self.info_label.hide()
        layout.addWidget(self.info_label)
        
    def refresh_tags(self):
        """Refresh the tag list from database."""
        try:
            # Clear existing tags
            self._clear_tag_items()
            
            # Get all tags with counts
            tags = self.notes_db.get_all_tags()
            
            if not tags:
                self.scroll_area.hide()
                self.info_label.show()
                return
            else:
                self.scroll_area.show()
                self.info_label.hide()
            
            # Find max count for scaling
            max_count = max(tags.values()) if tags else 1
            
            # Create tag items
            for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
                item = TagCloudItem(tag, count, max_count)
                item.clicked.connect(self._on_tag_clicked)
                item.context_menu_requested.connect(self._show_context_menu)
                
                # Check if selected
                if tag in self._selected_tags:
                    item.set_selected(True)
                
                self.tag_cloud_layout.addWidget(item)
                self._tag_items[tag] = item
                
            self.logger.info(f"Loaded {len(tags)} tags")
            
        except Exception as e:
            self.logger.error(f"Failed to refresh tags: {str(e)}")
            
    def _clear_tag_items(self):
        """Clear all tag items from the layout."""
        while self.tag_cloud_layout.count():
            item = self.tag_cloud_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tag_items.clear()
        
    def _on_tag_clicked(self, tag: str):
        """Handle tag click."""
        # Toggle selection
        if tag in self._selected_tags:
            self._selected_tags.remove(tag)
            if tag in self._tag_items:
                self._tag_items[tag].set_selected(False)
        else:
            self._selected_tags.add(tag)
            if tag in self._tag_items:
                self._tag_items[tag].set_selected(True)
        
        # Emit signal
        self.tag_clicked.emit(tag)
        
    def _show_context_menu(self, tag: str, pos: QPoint):
        """Show context menu for tag."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                padding: 5px;
            }}
            QMenu::item {{
                padding: 5px 20px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QMenu::item:selected {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        
        # Rename action
        rename_action = menu.addAction("✏️ Rename Tag")
        rename_action.triggered.connect(lambda: self._rename_tag(tag))
        
        # Delete action
        delete_action = menu.addAction("🗑️ Delete Tag")
        delete_action.triggered.connect(lambda: self._delete_tag(tag))
        
        menu.exec(pos)
        
    def _rename_tag(self, old_tag: str):
        """Rename a tag."""
        new_tag, ok = QInputDialog.getText(
            self,
            "Rename Tag",
            f"Enter new name for tag '{old_tag}':",
            text=old_tag
        )
        
        if ok and new_tag and new_tag != old_tag:
            # Confirm action
            reply = QMessageBox.question(
                self,
                "Confirm Rename",
                f"Rename tag '{old_tag}' to '{new_tag}' in all notes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                result = self.notes_db.rename_tag(old_tag, new_tag)
                
                if result["success"]:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Tag renamed in {result['affected_notes']} notes"
                    )
                    # Update selected tags if needed
                    if old_tag in self._selected_tags:
                        self._selected_tags.remove(old_tag)
                        self._selected_tags.add(new_tag)
                    
                    self.refresh_tags()
                    self.tags_updated.emit()
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"Failed to rename tag: {result.get('error', 'Unknown error')}"
                    )
                    
    def _delete_tag(self, tag: str):
        """Delete a tag from all notes."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Remove tag '{tag}' from all notes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.notes_db.delete_tag(tag)
            
            if result["success"]:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Tag removed from {result['affected_notes']} notes"
                )
                # Remove from selected tags
                self._selected_tags.discard(tag)
                
                self.refresh_tags()
                self.tags_updated.emit()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete tag: {result.get('error', 'Unknown error')}"
                )
                
    def get_selected_tags(self) -> list:
        """Get list of currently selected tags."""
        return list(self._selected_tags)
        
    def clear_selection(self):
        """Clear all tag selections."""
        self._selected_tags.clear()
        for item in self._tag_items.values():
            item.set_selected(False)


class FlowLayout(QVBoxLayout):
    """Flow layout for tag cloud - wraps items to new rows."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        
    def addWidget(self, widget):
        """Add a widget to the flow layout."""
        self._items.append(widget)
        self._rearrange()
        
    def _rearrange(self):
        """Rearrange items in rows."""
        # Clear current layout
        while self.count():
            self.takeAt(0)
            
        if not self._items:
            return
            
        # Get available width
        parent_width = self.parentWidget().width() if self.parentWidget() else 400
        
        # Create rows
        current_row = QHBoxLayout()
        current_row.setSpacing(10)
        current_width = 0
        
        for item in self._items:
            item_width = item.width() + 10  # Include spacing
            
            if current_width + item_width > parent_width and current_row.count() > 0:
                # Start new row
                current_row.addStretch()
                self.addLayout(current_row)
                current_row = QHBoxLayout()
                current_row.setSpacing(10)
                current_width = 0
                
            current_row.addWidget(item)
            current_width += item_width
            
        # Add last row
        if current_row.count() > 0:
            current_row.addStretch()
            self.addLayout(current_row)
            
        self.addStretch()