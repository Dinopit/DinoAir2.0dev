"""
Test script for the File Search GUI implementation
Tests that all components load without errors
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Import the components we created
from src.gui.pages.file_search_page import FileSearchPage
from src.gui.components.file_search_results import FileSearchResultsWidget
from src.gui.components.file_indexing_status import IndexingStatusWidget
from src.utils.colors import DinoPitColors
from src.rag.vector_search import SearchResult


def test_file_search_page():
    """Test that the FileSearchPage loads correctly"""
    print("Testing FileSearchPage...")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("File Search Test")
    window.setGeometry(100, 100, 1200, 800)
    
    # Set window style
    window.setStyleSheet(f"""
        QMainWindow {{
            background-color: {DinoPitColors.MAIN_BACKGROUND};
        }}
    """)
    
    # Create and set the file search page
    try:
        file_search_page = FileSearchPage()
        window.setCentralWidget(file_search_page)
        print("✓ FileSearchPage created successfully")
    except Exception as e:
        print(f"✗ Error creating FileSearchPage: {e}")
        return False
    
    # Show window
    window.show()
    
    # Test search functionality with mock data
    try:
        # Test search input
        file_search_page.search_input.setText("test query")
        print("✓ Search input accepts text")
        
        # Test file type filters
        items = file_search_page.file_type_checkboxes.items()
        for label, (checkbox, _) in items:
            checkbox.setChecked(True)
        print("✓ File type filters work")
        
        # Test search mode selector
        file_search_page.search_mode_combo.setCurrentText("Hybrid")
        print("✓ Search mode selector works")
        
    except Exception as e:
        print(f"✗ Error testing search controls: {e}")
        return False
    
    return True


def test_search_results_widget():
    """Test that the FileSearchResultsWidget works correctly"""
    print("\nTesting FileSearchResultsWidget...")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    
    try:
        # Create results widget
        results_widget = FileSearchResultsWidget()
        layout.addWidget(results_widget)
        print("✓ FileSearchResultsWidget created successfully")
        
        # Test with mock search results
        mock_results = [
            SearchResult(
                chunk_id="chunk1",
                file_id="file1",
                file_path="C:/Users/Test/Documents/example.pdf",
                content="This is a test document with some sample "
                        "content about testing.",
                score=0.95,
                chunk_index=0,
                start_pos=0,
                end_pos=100,
                file_type="pdf",
                match_type="hybrid"
            ),
            SearchResult(
                chunk_id="chunk2",
                file_id="file2",
                file_path="C:/Users/Test/Documents/code.py",
                content="def test_function():\n    return 'Hello, World!'",
                score=0.85,
                chunk_index=0,
                start_pos=0,
                end_pos=50,
                file_type="python",
                match_type="keyword"
            )
        ]
        
        results_widget.display_results(mock_results, "test")
        print("✓ Results display works correctly")
        
        # Test clear
        results_widget.clear_results()
        print("✓ Clear results works correctly")
        
    except Exception as e:
        print(f"✗ Error testing FileSearchResultsWidget: {e}")
        return False
    
    window.show()
    return True


def test_indexing_status_widget():
    """Test that the IndexingStatusWidget works correctly"""
    print("\nTesting IndexingStatusWidget...")
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    
    try:
        # Create status widget
        status_widget = IndexingStatusWidget()
        layout.addWidget(status_widget)
        print("✓ IndexingStatusWidget created successfully")
        
        # Test status updates
        status_widget.update_status("Test status message", "info")
        print("✓ Status message update works")
        
        # Test progress updates
        status_widget.set_indexing_active(True)
        status_widget.update_progress("Processing files...", 5, 10)
        print("✓ Progress update works")
        
        # Test stats update
        mock_stats = {
            "total_files": 100,
            "total_chunks": 500,
            "total_size": 1024 * 1024 * 50,  # 50MB
            "last_indexed": "2024-01-01T12:00:00"
        }
        status_widget.update_stats(mock_stats)
        print("✓ Stats update works")
        
        # Reset to inactive
        status_widget.set_indexing_active(False)
        
    except Exception as e:
        print(f"✗ Error testing IndexingStatusWidget: {e}")
        return False
    
    window.show()
    return True


def test_integration():
    """Test that all components work together"""
    print("\nTesting integration...")
    
    try:
        # Test imports of RAG components
        from src.rag.vector_search import VectorSearchEngine
        from src.rag.file_processor import FileProcessor
        from src.database.file_search_db import FileSearchDB
        print("✓ All RAG components import successfully")
        
        # Test database connection
        _ = FileSearchDB("test_user")
        print("✓ Database connection works")
        
        # Test search engine initialization
        _ = VectorSearchEngine("test_user")
        print("✓ Search engine initializes correctly")
        
        # Test file processor initialization
        _ = FileProcessor("test_user")
        print("✓ File processor initializes correctly")
        
    except Exception as e:
        print(f"✗ Error in integration test: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=== File Search GUI Test Suite ===\n")
    
    # Run tests
    tests_passed = 0
    tests_total = 4
    
    if test_file_search_page():
        tests_passed += 1
    
    if test_search_results_widget():
        tests_passed += 1
    
    if test_indexing_status_widget():
        tests_passed += 1
    
    if test_integration():
        tests_passed += 1
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n✅ All tests passed! The File Search GUI is ready.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    # Keep the application running for visual inspection
    app = QApplication.instance()
    if app and tests_passed > 0:
        print("\nKeeping windows open for visual inspection...")
        print("Close any window to exit.")
        app.exec()


if __name__ == "__main__":
    main()