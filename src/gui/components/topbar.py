"""
Top Bar Component - Application top navigation bar
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit
from PySide6.QtCore import Qt, Signal


class TopBar(QWidget):
    """Top navigation bar widget"""
    
    search_requested = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the top bar UI"""
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-bottom: 1px solid #d0d0d0;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # App title
        title_label = QLabel("DinoAir 2.0")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setStyleSheet("color: #FFFFFF; background-color: #2B3A52; border: 1px solid #4A5A7A; padding: 5px;")
        self.search_input.setPlaceholderText("Search notes...")
        self.search_input.setFixedWidth(300)
        self.search_input.returnPressed.connect(self._on_search)
        layout.addWidget(self.search_input)
        
        # Menu button
        menu_btn = QPushButton("☰")
        menu_btn.setStyleSheet("color: #FFFFFF;")
        menu_btn.setFixedSize(30, 30)
        layout.addWidget(menu_btn)
        
    def _on_search(self):
        """Handle search request"""
        text = self.search_input.text().strip()
        if text:
            self.search_requested.emit(text)
