"""
Test script for the Notes export functionality in DinoAir 2.0
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QMessageBox
from PySide6.QtCore import Qt

from src.gui.pages.notes_page import NotesPage
from src.models.note import Note
from src.database.notes_db import NotesDatabase


class ExportTestWindow(QMainWindow):
    """Test window for export functionality."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notes Export Test - DinoAir 2.0")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add notes page
        self.notes_page = NotesPage()
        layout.addWidget(self.notes_page)
        
        # Add test controls
        test_controls = QWidget()
        test_layout = QVBoxLayout(test_controls)
        
        # Create test notes button
        create_test_btn = QPushButton("Create Test Notes")
        create_test_btn.clicked.connect(self.create_test_notes)
        test_layout.addWidget(create_test_btn)
        
        # Test log
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        test_layout.addWidget(self.log_text)
        
        layout.addWidget(test_controls)
        
        # Apply some styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF8C61;
            }
            QTextEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 5px;
            }
        """)
        
        self.log("Export test window initialized")
        
    def create_test_notes(self):
        """Create sample notes for testing export functionality."""
        try:
            db = NotesDatabase()
            
            # Sample notes with various content
            test_notes = [
                {
                    "title": "Welcome to DinoAir Notes",
                    "content": "This is a test note with **bold text**, *italic text*, and regular text.\n\nIt has multiple paragraphs to test formatting.",
                    "tags": ["welcome", "test", "formatting"],
                    "content_html": "<p>This is a test note with <strong>bold text</strong>, <em>italic text</em>, and regular text.</p><p>It has multiple paragraphs to test formatting.</p>"
                },
                {
                    "title": "Project Ideas",
                    "content": "1. Build a weather app\n2. Create a todo list\n3. Design a portfolio website\n\nThese are some project ideas to explore.",
                    "tags": ["projects", "ideas", "development"]
                },
                {
                    "title": "Meeting Notes - Export Feature",
                    "content": "Discussed the following export formats:\n- HTML (with styling)\n- Plain text\n- PDF (if supported)\n- ZIP archive for bulk export\n\nDeadline: End of month",
                    "tags": ["meeting", "export", "features"]
                },
                {
                    "title": "Code Snippet Example",
                    "content": "Here's a Python function:\n\ndef hello_world():\n    print('Hello, DinoAir!')\n    return True\n\nThis demonstrates code in notes.",
                    "tags": ["code", "python", "example"]
                },
                {
                    "title": "Special Characters Test",
                    "content": "Testing special chars: & < > \" ' \n\nUnicode: ★ ♦ ♠ ♣ ♥ 🦖\n\nMath: ∑ ∏ √ ∞ ≠ ≤ ≥",
                    "tags": ["test", "unicode", "special-chars"]
                }
            ]
            
            created_count = 0
            for note_data in test_notes:
                note = Note(
                    title=note_data["title"],
                    content=note_data["content"],
                    tags=note_data["tags"]
                )
                
                # Create note with optional HTML content
                content_html = note_data.get("content_html")
                result = db.create_note(note, content_html)
                
                if result["success"]:
                    created_count += 1
                    self.log(f"Created note: {note_data['title']}")
                else:
                    self.log(f"Failed to create note: {note_data['title']}")
            
            self.log(f"\nCreated {created_count} test notes successfully!")
            
            # Refresh the notes page
            self.notes_page._load_notes()
            
            # Show instructions
            QMessageBox.information(
                self,
                "Test Notes Created",
                f"Created {created_count} test notes!\n\n"
                "You can now test the export functionality:\n"
                "1. Select a note and use Export button to export single notes\n"
                "2. Use 'Export All Notes (ZIP)' to export all notes at once\n"
                "3. Check the exported files in your chosen location"
            )
            
        except Exception as e:
            self.log(f"Error creating test notes: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create test notes: {str(e)}"
            )
    
    def log(self, message):
        """Add message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main():
    """Run the export test application."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = ExportTestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()