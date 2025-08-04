"""
Test script to verify GUI integration for pseudocode translator
"""

from PySide6.QtWidgets import QApplication, QMainWindow
from src.gui.components.tabbed_content import TabbedContentWidget
import sys

def test_gui():
    app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("GUI Integration Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Create tabbed content widget
    tabbed_widget = TabbedContentWidget()
    window.setCentralWidget(tabbed_widget)
    
    # Show window
    window.show()
    
    # Check if pseudocode tab exists
    print("Tabs found:")
    for i in range(tabbed_widget.tab_widget.count()):
        tab_text = tabbed_widget.tab_widget.tabText(i)
        print(f"  Tab {i}: {tab_text}")
        if tab_text == "Pseudocode Translator":
            print("    ✓ Pseudocode tab found!")
            tabbed_widget.tab_widget.setCurrentIndex(i)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_gui()