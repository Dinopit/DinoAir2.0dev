"""
Sidebar Component - Navigation sidebar
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtCore import Signal
from ...utils.scaling import get_scaling_helper


class Sidebar(QWidget):
    """Navigation sidebar widget"""
    
    page_changed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.current_page = "notes"
        self._scaling_helper = get_scaling_helper()
        self.setup_ui()
        
        # Connect to zoom changes
        self._scaling_helper.zoom_changed.connect(self._on_zoom_changed)
        
    def setup_ui(self):
        """Setup the sidebar UI"""
        self._update_dimensions()
        self._update_stylesheet()
        
        self.main_layout = QVBoxLayout(self)
        self._update_layout_spacing()
        
        # Navigation buttons
        self.notes_btn = QPushButton("📝 Notes")
        self.notes_btn.setStyleSheet("color: #FFFFFF;")
        self.notes_btn.setCheckable(True)
        self.notes_btn.setChecked(True)
        self.notes_btn.clicked.connect(lambda: self._switch_page("notes"))
        self.main_layout.addWidget(self.notes_btn)
        
        self.calendar_btn = QPushButton("📅 Calendar")
        self.calendar_btn.setStyleSheet("color: #FFFFFF;")
        self.calendar_btn.setCheckable(True)
        self.calendar_btn.clicked.connect(
            lambda: self._switch_page("calendar")
        )
        self.main_layout.addWidget(self.calendar_btn)
        
        self.tasks_btn = QPushButton("✓ Tasks")
        self.tasks_btn.setStyleSheet("color: #FFFFFF;")
        self.tasks_btn.setCheckable(True)
        self.tasks_btn.clicked.connect(lambda: self._switch_page("tasks"))
        self.main_layout.addWidget(self.tasks_btn)
        
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setStyleSheet("color: #FFFFFF;")
        self.settings_btn.setCheckable(True)
        self.settings_btn.clicked.connect(
            lambda: self._switch_page("settings")
        )
        self.main_layout.addWidget(self.settings_btn)
        
        self.main_layout.addStretch()
        
        self.buttons = [self.notes_btn, self.calendar_btn,
                        self.tasks_btn, self.settings_btn]
        
    def _switch_page(self, page_name):
        """Switch to a different page"""
        if page_name != self.current_page:
            # Uncheck all buttons
            for btn in self.buttons:
                btn.setChecked(False)
                
            # Check the clicked button
            if page_name == "notes":
                self.notes_btn.setChecked(True)
            elif page_name == "calendar":
                self.calendar_btn.setChecked(True)
            elif page_name == "tasks":
                self.tasks_btn.setChecked(True)
            elif page_name == "settings":
                self.settings_btn.setChecked(True)
                
            self.current_page = page_name
            self.page_changed.emit(page_name)
    
    def _update_dimensions(self):
        """Update widget dimensions based on current scaling."""
        self.setFixedWidth(self._scaling_helper.scaled_size(200))
    
    def _update_stylesheet(self):
        """Update stylesheet with current scaling."""
        s = self._scaling_helper
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #e8e8e8;
                border-right: {s.scaled_size(1)}px solid #d0d0d0;
            }}
            QPushButton {{
                color: #FFFFFF;
                text-align: left;
                padding: {s.scaled_size(10)}px {s.scaled_size(15)}px;
                border: none;
                background-color: transparent;
                font-size: {s.scaled_font_size(14)}px;
            }}
            QPushButton:hover {{
                background-color: #d0d0d0;
            }}
            QPushButton:checked {{
                background-color: #0078d4;
                color: white;
            }}
        """)
    
    def _update_layout_spacing(self):
        """Update layout spacing based on current scaling."""
        s = self._scaling_helper
        self.main_layout.setContentsMargins(
            0, s.scaled_size(10), 0, s.scaled_size(10)
        )
        self.main_layout.setSpacing(s.scaled_size(5))
    
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        self._update_dimensions()
        self._update_stylesheet()
        self._update_layout_spacing()
