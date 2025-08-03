"""
Test script for Directory Selection functionality in RAG File Search
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PySide6.QtCore import QSettings
from src.gui.pages.file_search_page import FileSearchPage
from src.utils.logger import Logger


class TestWindow(QMainWindow):
    """Test window for directory selection functionality"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.setWindowTitle("RAG Directory Selection Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add file search page
        self.file_search_page = FileSearchPage()
        layout.addWidget(self.file_search_page)
        
        # Add test controls
        test_controls = QWidget()
        test_layout = QVBoxLayout(test_controls)
        
        # Button to show current settings
        show_settings_btn = QPushButton("Show Current Settings")
        show_settings_btn.clicked.connect(self.show_current_settings)
        test_layout.addWidget(show_settings_btn)
        
        # Button to clear settings
        clear_settings_btn = QPushButton("Clear All Settings")
        clear_settings_btn.clicked.connect(self.clear_settings)
        test_layout.addWidget(clear_settings_btn)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(150)
        test_layout.addWidget(self.output_text)
        
        layout.addWidget(test_controls)
        
        # Connect to file search page signals
        self.file_search_page.indexing_status.index_directory_requested.connect(
            self.on_directory_requested
        )
        
        self.log_output("Test window initialized. Click 'Index Directory' to test.")
    
    def on_directory_requested(self, directory: str):
        """Handle directory indexing request"""
        self.log_output(f"Directory requested for indexing: {directory}")
    
    def show_current_settings(self):
        """Display current settings"""
        settings = QSettings("DinoAir", "FileSearch")
        
        output = "=== Current Settings ===\n"
        
        # Allowed directories
        allowed_dirs = settings.value("allowed_directories", [], list)
        output += f"\nAllowed Directories ({len(allowed_dirs)}):\n"
        for dir in allowed_dirs:
            output += f"  - {dir}\n"
        
        # Excluded directories  
        excluded_dirs = settings.value("excluded_directories", [], list)
        output += f"\nExcluded Directories ({len(excluded_dirs)}):\n"
        for dir in excluded_dirs:
            output += f"  - {dir}\n"
        
        # Indexed directories
        indexed_dirs = settings.value("indexed_directories", [], list)
        output += f"\nIndexed Directories ({len(indexed_dirs)}):\n"
        for dir in indexed_dirs:
            output += f"  - {dir}\n"
        
        # Last selected directory
        last_dir = settings.value("last_selected_directory", "", str)
        output += f"\nLast Selected Directory: {last_dir}\n"
        
        self.log_output(output)
    
    def clear_settings(self):
        """Clear all settings"""
        settings = QSettings("DinoAir", "FileSearch")
        settings.clear()
        settings.sync()
        self.log_output("All settings cleared.")
        
        # Reload settings in file search page
        self.file_search_page._load_directory_settings()
        self.log_output("Settings reloaded in file search page.")
    
    def log_output(self, message: str):
        """Add message to output area"""
        self.output_text.append(message)
        self.output_text.append("")  # Add blank line
        
        # Also log to console
        print(message)


def main():
    """Run the test"""
    print("Starting RAG Directory Selection Test...")
    print("=" * 50)
    print("This test verifies:")
    print("1. Directory selection dialog opens")
    print("2. Selected directories are validated")
    print("3. Settings are persisted")
    print("4. Indexing starts when directory is selected")
    print("5. Last directory is remembered")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    app.setApplicationName("DinoAir")
    app.setOrganizationName("DinoAir")
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()