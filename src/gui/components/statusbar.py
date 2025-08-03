"""
Status Bar Component - Application status bar
"""

from PySide6.QtWidgets import QStatusBar, QLabel
from PySide6.QtCore import QTimer


class StatusBar(QStatusBar):
    """Application status bar"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the status bar UI"""
        # Database status
        self.db_status = QLabel("Database: Ready")
        self.db_status.setStyleSheet("color: #FFFFFF;")
        self.addPermanentWidget(self.db_status)
        
        # Show ready message
        self.showMessage("Ready", 3000)
        
    def set_database_status(self, status):
        """Update database status"""
        self.db_status.setText(f"Database: {status}")
        
    def show_temporary_message(self, message, timeout=3000):
        """Show a temporary message"""
        self.showMessage(message, timeout)
