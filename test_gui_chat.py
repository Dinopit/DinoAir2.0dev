#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test script to verify the GUI chat functionality."""

import sys
from PySide6.QtWidgets import QApplication

# Add src to path
sys.path.insert(0, 'src')

from gui.main_window import MainWindow
from database.initialize_db import DatabaseManager


def main():
    """Run the GUI test."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Create database manager
    db_manager = DatabaseManager()
    
    # Set database manager on window
    # This should trigger creation of the enhanced chat tab with input field
    window.set_database_manager(db_manager)
    
    # Show window
    window.show()
    
    # Print debug info
    print("GUI launched successfully!")
    print("Chat tab should now have an input field at the bottom.")
    print("If you don't see it, check the Chat tab.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()