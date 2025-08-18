"""
Notes Search Widget - Search functionality with filtering and debouncing
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton,
    QComboBox
)
from PySide6.QtCore import Signal, QTimer

from src.utils.colors import DinoPitColors
from src.gui.components.notes_security import get_notes_security


class NotesSearchWidget(QWidget):
    """Search widget for notes with debouncing and filter options.
    
    Features:
    - Search input field with placeholder text
    - Search and clear buttons
    - Filter options dropdown (All, Title Only, Content Only, Tags Only)
    - Debouncing mechanism (300ms)
    - Keyboard shortcuts support
    """
    
    # Signals
    search_requested = Signal(str, str)  # search_query, filter_option
    clear_requested = Signal()
    
    def __init__(self):
        """Initialize the search widget."""
        super().__init__()
        self._security = get_notes_security()
        self._setup_ui()
        self._setup_debounce_timer()
        self._connect_signals()
        
    def _setup_ui(self):
        """Setup the search widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All",
            "Title Only",
            "Content Only",
            "Tags Only"
        ])
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 6px 10px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                min-width: 100px;
            }}
            QComboBox:hover {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 5px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {DinoPitColors.PRIMARY_TEXT};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DinoPitColors.SIDEBAR_BACKGROUND};
                border: 1px solid {DinoPitColors.SOFT_ORANGE};
                selection-background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: {DinoPitColors.PRIMARY_TEXT};
            }}
        """)
        layout.addWidget(self.filter_combo)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 2px solid {DinoPitColors.SOFT_ORANGE};
                border-radius: 4px;
                background-color: {DinoPitColors.PANEL_BACKGROUND};
                color: {DinoPitColors.PRIMARY_TEXT};
                font-size: 14px;
                min-width: 250px;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.5);
            }}
            QLineEdit:focus {{
                border-color: {DinoPitColors.DINOPIT_ORANGE};
            }}
        """)
        layout.addWidget(self.search_input, 1)  # Stretch factor 1
        
        # Search button
        self.search_button = QPushButton("🔍 Search")
        self.search_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.DINOPIT_ORANGE};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {DinoPitColors.DINOPIT_FIRE};
            }}
            QPushButton:pressed {{
                background-color: #E55A2B;
            }}
        """)
        layout.addWidget(self.search_button)
        
        # Clear button
        self.clear_button = QPushButton("✖ Clear")
        self.clear_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {DinoPitColors.PRIMARY_TEXT};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #6A6A6A;
            }}
            QPushButton:pressed {{
                background-color: #4A4A4A;
            }}
        """)
        self.clear_button.setEnabled(False)
        layout.addWidget(self.clear_button)
        
    def _setup_debounce_timer(self):
        """Setup the debounce timer for search input."""
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._perform_search)
        
    def _connect_signals(self):
        """Connect widget signals."""
        # Search input with debouncing
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._immediate_search)
        
        # Button clicks
        self.search_button.clicked.connect(self._immediate_search)
        self.clear_button.clicked.connect(self._clear_search)
        
        # Filter change
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        
    def _on_search_text_changed(self, text: str):
        """Handle search text changes with debouncing."""
        # Stop any existing timer
        self.debounce_timer.stop()
        
        # Enable/disable clear button
        self.clear_button.setEnabled(bool(text))
        
        # Start debounce timer (300ms)
        if text:
            self.debounce_timer.start(300)
        else:
            # If text is empty, clear search immediately
            self._clear_search()
            
    def _on_filter_changed(self):
        """Handle filter option change."""
        # Perform search immediately with new filter
        if self.search_input.text():
            self._immediate_search()
            
    def _immediate_search(self):
        """Perform search immediately (bypassing debounce)."""
        self.debounce_timer.stop()
        self._perform_search()
        
    def _perform_search(self):
        """Actually perform the search with sanitization."""
        raw_query = self.search_input.text().strip()
        if raw_query:
            # Sanitize search query for SQL safety
            sanitized_query = self._security.sanitize_search_query(raw_query)
            
            # Warn if query was modified
            if sanitized_query != raw_query:
                # Update search input to show sanitized query
                self.search_input.setText(sanitized_query)
                
            filter_option = self.filter_combo.currentText()
            self.search_requested.emit(sanitized_query, filter_option)
            
    def _clear_search(self):
        """Clear the search."""
        self.search_input.clear()
        self.clear_button.setEnabled(False)
        self.clear_requested.emit()
        
    def focus_search(self):
        """Set focus to the search input."""
        self.search_input.setFocus()
        self.search_input.selectAll()
        
    def get_search_query(self) -> str:
        """Get the current search query."""
        return self.search_input.text().strip()
        
    def get_filter_option(self) -> str:
        """Get the current filter option."""
        return self.filter_combo.currentText()
        
    def set_search_query(self, query: str):
        """Set the search query programmatically with sanitization."""
        # Sanitize before setting
        sanitized_query = self._security.sanitize_search_query(query)
        self.search_input.setText(sanitized_query)
        
    def is_searching(self) -> bool:
        """Check if currently in search mode."""
        return bool(self.search_input.text().strip())