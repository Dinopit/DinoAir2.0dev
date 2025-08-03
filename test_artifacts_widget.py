#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the enhanced ArtifactsWidget with database integration.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from src.gui.components.artifact_panel import ArtifactsWidget
from src.utils.logger import Logger


class TestWindow(QMainWindow):
    """Test window for the ArtifactsWidget."""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.setWindowTitle("Artifacts Widget Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set dark theme to match DinoAir
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B3A52;
            }
        """)
        
        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add some space on the left
        left_spacer = QWidget()
        left_spacer.setMinimumWidth(600)
        left_spacer.setStyleSheet("background-color: #34435A;")
        layout.addWidget(left_spacer)
        
        # Create and add the artifacts widget
        self.artifacts_widget = ArtifactsWidget()
        layout.addWidget(self.artifacts_widget)
        
        # Connect signals for testing
        self.artifacts_widget.artifact_selected.connect(
            self.on_artifact_selected
        )
        self.artifacts_widget.artifact_deleted.connect(
            self.on_artifact_deleted
        )
        
    def on_artifact_selected(self, artifact):
        """Handle artifact selection."""
        self.logger.info(
            f"Artifact selected: {artifact.name} (ID: {artifact.id})"
        )
        
    def on_artifact_deleted(self, artifact_id):
        """Handle artifact deletion."""
        self.logger.info(f"Artifact deleted: {artifact_id}")


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    
    # Enable high DPI support
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create and show test window
    window = TestWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()