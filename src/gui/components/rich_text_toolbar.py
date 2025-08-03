"""
Rich Text Toolbar Component - Provides formatting controls for rich text
editing in the Notes feature.
"""

from typing import Callable
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolBar, QToolButton, QComboBox,
    QColorDialog, QFontComboBox
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import (
    QAction, QTextCharFormat, QTextBlockFormat, QFont,
    QTextCursor, QTextListFormat, QKeySequence
)

from ...utils.colors import DinoPitColors


class RichTextToolbar(QWidget):
    """Toolbar widget for rich text formatting controls.
    
    Features:
    - Text formatting: Bold, Italic, Underline, Strikethrough
    - Text color and highlight color
    - Font family and size selection
    - Lists: Bullet and Numbered
    - Indentation controls
    - Text alignment options
    - Keyboard shortcuts for all actions
    """
    
    # Signals
    format_changed = Signal()  # Emitted when any format is applied
    
    def __init__(self, parent=None):
        """Initialize the rich text toolbar."""
        super().__init__(parent)
        self._text_edit = None
        self._setup_ui()
        self._setup_actions()
        self._setup_shortcuts()
        
    def _setup_ui(self):
        """Setup the toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                padding: 2px;
            }}
            QToolButton {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px;
                margin: 1px;
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
            QToolButton:hover {{
                background-color: {DinoPitColors.SOFT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QToolButton:pressed {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QToolButton:checked {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                border-color: {DinoPitColors.DINOPIT_FIRE};
            }}
        """)
        
        layout.addWidget(self.toolbar)
        
    def _setup_actions(self):
        """Setup toolbar actions."""
        # Text formatting actions
        self.bold_action = self._create_action(
            "B", "Bold", self.toggle_bold, checkable=True
        )
        self.bold_action.setShortcut(QKeySequence.StandardKey.Bold)
        
        self.italic_action = self._create_action(
            "I", "Italic", self.toggle_italic, checkable=True
        )
        self.italic_action.setShortcut(QKeySequence.StandardKey.Italic)
        
        self.underline_action = self._create_action(
            "U", "Underline", self.toggle_underline, checkable=True
        )
        self.underline_action.setShortcut(QKeySequence.StandardKey.Underline)
        
        self.strikethrough_action = self._create_action(
            "S", "Strikethrough", self.toggle_strikethrough, checkable=True
        )
        
        # Add formatting actions to toolbar
        self.toolbar.addAction(self.bold_action)
        self.toolbar.addAction(self.italic_action)
        self.toolbar.addAction(self.underline_action)
        self.toolbar.addAction(self.strikethrough_action)
        self.toolbar.addSeparator()
        
        # Font controls
        self.font_combo = QFontComboBox()
        self.font_combo.setMaximumWidth(150)
        self.font_combo.setCurrentFont(QFont("Arial"))
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        self.toolbar.addWidget(self.font_combo)
        
        self.font_size_combo = QComboBox()
        self.font_size_combo.setEditable(True)
        self.font_size_combo.setMaximumWidth(60)
        font_sizes = ["8", "9", "10", "11", "12", "14", "16",
                      "18", "20", "22", "24"]
        self.font_size_combo.addItems(font_sizes)
        self.font_size_combo.setCurrentText("12")
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        self.toolbar.addWidget(self.font_size_combo)
        self.toolbar.addSeparator()
        
        # Color actions
        self.text_color_action = self._create_action(
            "A", "Text Color", self.change_text_color
        )
        self.highlight_color_action = self._create_action(
            "H", "Highlight Color", self.change_highlight_color
        )
        
        self.toolbar.addAction(self.text_color_action)
        self.toolbar.addAction(self.highlight_color_action)
        self.toolbar.addSeparator()
        
        # List actions
        self.bullet_list_action = self._create_action(
            "•", "Bullet List", self.toggle_bullet_list, checkable=True
        )
        self.numbered_list_action = self._create_action(
            "#", "Numbered List", self.toggle_numbered_list, checkable=True
        )
        
        self.toolbar.addAction(self.bullet_list_action)
        self.toolbar.addAction(self.numbered_list_action)
        self.toolbar.addSeparator()
        
        # Indentation actions
        self.indent_action = self._create_action(
            "→", "Increase Indent", self.increase_indent
        )
        self.outdent_action = self._create_action(
            "←", "Decrease Indent", self.decrease_indent
        )
        
        self.toolbar.addAction(self.indent_action)
        self.toolbar.addAction(self.outdent_action)
        self.toolbar.addSeparator()
        
        # Alignment actions
        self.align_left_action = self._create_action(
            "L", "Align Left",
            lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft),
            checkable=True
        )
        self.align_center_action = self._create_action(
            "C", "Align Center",
            lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter),
            checkable=True
        )
        self.align_right_action = self._create_action(
            "R", "Align Right",
            lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight),
            checkable=True
        )
        self.align_justify_action = self._create_action(
            "J", "Justify",
            lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify),
            checkable=True
        )
        
        # Group alignment actions
        self.alignment_group = [
            self.align_left_action,
            self.align_center_action,
            self.align_right_action,
            self.align_justify_action
        ]
        
        self.toolbar.addAction(self.align_left_action)
        self.toolbar.addAction(self.align_center_action)
        self.toolbar.addAction(self.align_right_action)
        self.toolbar.addAction(self.align_justify_action)
        
    def _create_action(
        self, 
        text: str, 
        tooltip: str, 
        callback: Callable,
        checkable: bool = False
    ) -> QAction:
        """Create a toolbar action.
        
        Args:
            text: Button text
            tooltip: Tooltip text
            callback: Function to call when triggered
            checkable: Whether the action is checkable
            
        Returns:
            QAction instance
        """
        action = QAction(text, self)
        action.setToolTip(tooltip)
        action.setCheckable(checkable)
        action.triggered.connect(callback)
        
        # Style the text for better visibility
        button = QToolButton()
        button.setDefaultAction(action)
        button.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        return action
        
    def _setup_shortcuts(self):
        """Setup additional keyboard shortcuts."""
        # Additional shortcuts not covered by standard QKeySequence
        self.strikethrough_action.setShortcut("Ctrl+Shift+S")
        self.indent_action.setShortcut("Tab")
        self.outdent_action.setShortcut("Shift+Tab")
        
    def set_text_edit(self, text_edit):
        """Set the QTextEdit widget to apply formatting to.
        
        Args:
            text_edit: QTextEdit widget
        """
        self._text_edit = text_edit
        
        # Connect to cursor position changes to update toolbar state
        if self._text_edit:
            self._text_edit.cursorPositionChanged.connect(
                self._update_format_buttons
            )
            
    def toggle_bold(self):
        """Toggle bold formatting."""
        if not self._text_edit:
            return
            
        fmt = QTextCharFormat()
        fmt.setFontWeight(
            QFont.Weight.Bold if self.bold_action.isChecked()
            else QFont.Weight.Normal
        )
        self._merge_format_on_selection(fmt)
        self.format_changed.emit()
        
    def toggle_italic(self):
        """Toggle italic formatting."""
        if not self._text_edit:
            return
            
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_action.isChecked())
        self._merge_format_on_selection(fmt)
        self.format_changed.emit()
        
    def toggle_underline(self):
        """Toggle underline formatting."""
        if not self._text_edit:
            return
            
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_action.isChecked())
        self._merge_format_on_selection(fmt)
        self.format_changed.emit()
        
    def toggle_strikethrough(self):
        """Toggle strikethrough formatting."""
        if not self._text_edit:
            return
            
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(self.strikethrough_action.isChecked())
        self._merge_format_on_selection(fmt)
        self.format_changed.emit()
        
    def change_font_family(self, font: QFont):
        """Change font family.
        
        Args:
            font: QFont with the desired font family
        """
        if not self._text_edit:
            return
            
        fmt = QTextCharFormat()
        fmt.setFontFamily(font.family())
        self._merge_format_on_selection(fmt)
        self.format_changed.emit()
        
    def change_font_size(self, size_str: str):
        """Change font size.
        
        Args:
            size_str: Font size as string
        """
        if not self._text_edit or not size_str:
            return
            
        try:
            size = int(size_str)
            if 8 <= size <= 24:  # Limit font size range
                fmt = QTextCharFormat()
                fmt.setFontPointSize(size)
                self._merge_format_on_selection(fmt)
                self.format_changed.emit()
        except ValueError:
            pass  # Invalid size entered
            
    def change_text_color(self):
        """Change text color."""
        if not self._text_edit:
            return
            
        color = QColorDialog.getColor(Qt.GlobalColor.black, self,
                                      "Select Text Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_format_on_selection(fmt)
            self.format_changed.emit()
            
    def change_highlight_color(self):
        """Change text highlight/background color."""
        if not self._text_edit:
            return
            
        color = QColorDialog.getColor(Qt.GlobalColor.yellow, self,
                                      "Select Highlight Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self._merge_format_on_selection(fmt)
            self.format_changed.emit()
            
    def toggle_bullet_list(self):
        """Toggle bullet list."""
        if not self._text_edit:
            return
            
        cursor = self._text_edit.textCursor()
        
        if self.bullet_list_action.isChecked():
            # Apply bullet list
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_format)
        else:
            # Remove list
            cursor.currentList().remove(cursor.block())
            
        self.numbered_list_action.setChecked(False)
        self.format_changed.emit()
        
    def toggle_numbered_list(self):
        """Toggle numbered list."""
        if not self._text_edit:
            return
            
        cursor = self._text_edit.textCursor()
        
        if self.numbered_list_action.isChecked():
            # Apply numbered list
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.createList(list_format)
        else:
            # Remove list
            if cursor.currentList():
                cursor.currentList().remove(cursor.block())
                
        self.bullet_list_action.setChecked(False)
        self.format_changed.emit()
        
    def increase_indent(self):
        """Increase paragraph indent."""
        if not self._text_edit:
            return
            
        cursor = self._text_edit.textCursor()
        if cursor.currentList():
            # For lists, increase indent level
            list_format = cursor.currentList().format()
            list_format.setIndent(list_format.indent() + 1)
            cursor.currentList().setFormat(list_format)
        else:
            # For regular text, increase block indent
            block_format = cursor.blockFormat()
            block_format.setIndent(block_format.indent() + 1)
            cursor.setBlockFormat(block_format)
            
        self.format_changed.emit()
        
    def decrease_indent(self):
        """Decrease paragraph indent."""
        if not self._text_edit:
            return
            
        cursor = self._text_edit.textCursor()
        if cursor.currentList():
            # For lists, decrease indent level
            list_format = cursor.currentList().format()
            if list_format.indent() > 0:
                list_format.setIndent(list_format.indent() - 1)
                cursor.currentList().setFormat(list_format)
        else:
            # For regular text, decrease block indent
            block_format = cursor.blockFormat()
            if block_format.indent() > 0:
                block_format.setIndent(block_format.indent() - 1)
                cursor.setBlockFormat(block_format)
                
        self.format_changed.emit()
        
    def set_alignment(self, alignment: Qt.AlignmentFlag):
        """Set text alignment.
        
        Args:
            alignment: Qt.AlignmentFlag value
        """
        if not self._text_edit:
            return
            
        block_format = QTextBlockFormat()
        block_format.setAlignment(alignment)
        
        cursor = self._text_edit.textCursor()
        cursor.mergeBlockFormat(block_format)
        
        # Update button states
        for action in self.alignment_group:
            action.setChecked(False)
            
        if alignment == Qt.AlignmentFlag.AlignLeft:
            self.align_left_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignCenter:
            self.align_center_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignRight:
            self.align_right_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignJustify:
            self.align_justify_action.setChecked(True)
            
        self.format_changed.emit()
        
    def _merge_format_on_selection(self, format: QTextCharFormat):
        """Apply format to current selection.
        
        Args:
            format: QTextCharFormat to apply
        """
        if self._text_edit:
            cursor = self._text_edit.textCursor()
            if not cursor.hasSelection():
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)
            cursor.mergeCharFormat(format)
            self._text_edit.mergeCurrentCharFormat(format)
        
    def _update_format_buttons(self):
        """Update format button states based on current cursor position."""
        if not self._text_edit:
            return
            
        # Get current format
        cursor = self._text_edit.textCursor()
        char_format = cursor.charFormat()
        block_format = cursor.blockFormat()
        
        # Update text format buttons
        self.bold_action.setChecked(
            char_format.fontWeight() == QFont.Weight.Bold
        )
        self.italic_action.setChecked(char_format.fontItalic())
        self.underline_action.setChecked(char_format.fontUnderline())
        self.strikethrough_action.setChecked(char_format.fontStrikeOut())
        
        # Update font combo boxes
        self.font_combo.setCurrentFont(char_format.font())
        font_size = char_format.fontPointSize()
        if font_size > 0:
            self.font_size_combo.setCurrentText(str(int(font_size)))
            
        # Update list buttons
        current_list = cursor.currentList()
        if current_list:
            list_style = current_list.format().style()
            self.bullet_list_action.setChecked(
                list_style == QTextListFormat.Style.ListDisc
            )
            self.numbered_list_action.setChecked(
                list_style == QTextListFormat.Style.ListDecimal
            )
        else:
            self.bullet_list_action.setChecked(False)
            self.numbered_list_action.setChecked(False)
            
        # Update alignment buttons
        alignment = block_format.alignment()
        for action in self.alignment_group:
            action.setChecked(False)
            
        if alignment == Qt.AlignmentFlag.AlignLeft:
            self.align_left_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignCenter:
            self.align_center_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignRight:
            self.align_right_action.setChecked(True)
        elif alignment == Qt.AlignmentFlag.AlignJustify:
            self.align_justify_action.setChecked(True)
            
    def set_visible(self, visible: bool):
        """Set toolbar visibility.
        
        Args:
            visible: Whether toolbar should be visible
        """
        self.setVisible(visible)
        
    def set_enabled(self, enabled: bool):
        """Set toolbar enabled state.
        
        Args:
            enabled: Whether toolbar should be enabled
        """
        self.setEnabled(enabled)
        
    def reset_format(self):
        """Reset all formatting to default."""
        if not self._text_edit:
            return
            
        cursor = self._text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        # Clear all formatting
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        
        # Reset block format
        default_block_format = QTextBlockFormat()
        cursor.setBlockFormat(default_block_format)
        
        # Clear selection
        cursor.clearSelection()
        self._text_edit.setTextCursor(cursor)
        
        # Update button states
        self._update_format_buttons()
        self.format_changed.emit()