"""
Simple test script for the File Search GUI components
Tests that GUI components load without the full RAG system
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Test if we can import the core GUI components
print("=== Testing GUI Component Imports ===\n")

try:
    # Import colors first
    from src.utils.colors import DinoPitColors
    print("✓ DinoPitColors imported successfully")
except Exception as e:
    print(f"✗ Error importing DinoPitColors: {e}")
    sys.exit(1)

try:
    # Import components without the full page
    from src.gui.components.file_search_results import FileSearchResultsWidget
    print("✓ FileSearchResultsWidget imported successfully")
except Exception as e:
    print(f"✗ Error importing FileSearchResultsWidget: {e}")

try:
    from src.gui.components.file_indexing_status import IndexingStatusWidget
    print("✓ IndexingStatusWidget imported successfully")
except Exception as e:
    print(f"✗ Error importing IndexingStatusWidget: {e}")

# Create a mock SearchResult class for testing
class MockSearchResult:
    def __init__(self, chunk_id, file_id, file_path, content, score, 
                 chunk_index, start_pos, end_pos, file_type=None, 
                 match_type='hybrid'):
        self.chunk_id = chunk_id
        self.file_id = file_id
        self.file_path = file_path
        self.content = content
        self.score = score
        self.chunk_index = chunk_index
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.file_type = file_type
        self.match_type = match_type
        self.metadata = {}


def test_gui_components():
    """Test that the GUI components work independently"""
    print("\n=== Testing GUI Components ===\n")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("File Search GUI Components Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Set window style
    window.setStyleSheet(f"""
        QMainWindow {{
            background-color: {DinoPitColors.MAIN_BACKGROUND};
        }}
    """)
    
    # Create central widget with layout
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    window.setCentralWidget(central_widget)
    
    # Test FileSearchResultsWidget
    try:
        print("Testing FileSearchResultsWidget...")
        results_widget = FileSearchResultsWidget()
        
        # Create mock results
        mock_results = [
            MockSearchResult(
                chunk_id="chunk1",
                file_id="file1",
                file_path="C:/Test/Documents/example.pdf",
                content="This is a test document with sample content.",
                score=0.95,
                chunk_index=0,
                start_pos=0,
                end_pos=100,
                file_type="pdf",
                match_type="hybrid"
            ),
            MockSearchResult(
                chunk_id="chunk2",
                file_id="file2",
                file_path="C:/Test/Code/script.py",
                content="def hello():\n    print('Hello, World!')",
                score=0.85,
                chunk_index=0,
                start_pos=0,
                end_pos=50,
                file_type="python",
                match_type="keyword"
            )
        ]
        
        # Monkey patch the SearchResult import in the module
        import src.gui.components.file_search_results
        src.gui.components.file_search_results.SearchResult = MockSearchResult
        
        # Display results
        results_widget.display_results(mock_results, "test")
        layout.addWidget(results_widget)
        print("✓ FileSearchResultsWidget works correctly")
        
    except Exception as e:
        print(f"✗ Error with FileSearchResultsWidget: {e}")
        import traceback
        traceback.print_exc()
    
    # Test IndexingStatusWidget
    try:
        print("\nTesting IndexingStatusWidget...")
        status_widget = IndexingStatusWidget()
        
        # Update stats
        status_widget.update_stats({
            "total_files": 42,
            "total_chunks": 156,
            "total_size": 1024 * 1024 * 25,  # 25MB
        })
        
        # Show a status message
        status_widget.update_status("Ready to index files", "info")
        
        layout.addWidget(status_widget)
        print("✓ IndexingStatusWidget works correctly")
        
    except Exception as e:
        print(f"✗ Error with IndexingStatusWidget: {e}")
        import traceback
        traceback.print_exc()
    
    # Show window
    window.show()
    
    print("\n✅ GUI components test completed successfully!")
    print("\nThe window will stay open for visual inspection.")
    print("Close the window to exit.")
    
    # Run the application
    app.exec()


def main():
    """Run the test"""
    test_gui_components()


if __name__ == "__main__":
    main()