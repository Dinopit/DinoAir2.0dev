"""
RAG File Search System Integration Test
Tests the integration of all Phase 7 components
"""

import os
import sys
import time
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.rag.context_provider import ContextProvider  # noqa: E402
from src.rag.file_monitor import FileMonitor, WATCHDOG_AVAILABLE  # noqa: E402
from src.rag.file_processor import FileProcessor  # noqa: E402
from src.rag.vector_search import VectorSearchEngine  # noqa: E402
from src.database.file_search_db import FileSearchDB  # noqa: E402
from src.database.notes_db import NotesDatabase  # noqa: E402
from src.database.artifacts_db import ArtifactsDatabase  # noqa: E402
from src.models.note import Note  # noqa: E402
from src.models.artifact import Artifact  # noqa: E402
from src.utils.logger import Logger  # noqa: E402


class IntegrationTester:
    """Test RAG system integration"""
    
    def __init__(self):
        self.logger = Logger()
        self.test_user = "test_integration_user"
        self.test_dir: str = ""
        self.passed_tests = 0
        self.failed_tests = 0
        
    def setup(self):
        """Setup test environment"""
        print("\n=== Setting up test environment ===")
        
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp(prefix="rag_test_")
        print(f"Created test directory: {self.test_dir}")
        
        # Create test files
        self._create_test_files()
        
        # Initialize components
        self.file_processor = FileProcessor(
            user_name=self.test_user,
            chunk_size=500,
            chunk_overlap=50,
            generate_embeddings=True
        )
        self.search_engine = VectorSearchEngine(self.test_user)
        self.context_provider = ContextProvider(self.test_user)
        self.file_monitor = FileMonitor(self.test_user)
        self.file_search_db = FileSearchDB(self.test_user)
        self.notes_db = NotesDatabase(self.test_user)
        self.artifacts_db = ArtifactsDatabase(self.test_user)
        
        print("Components initialized")
        
    def _create_test_files(self):
        """Create test files for indexing"""
        test_files = [
            ("test1.txt", "This is a test document about Python programming."),
            ("test2.py", "def hello_world():\n    print('Hello, World!')"),
            ("test3.md", "# Test Markdown\n\nThis is a test markdown file."),
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"Created {len(test_files)} test files")
        
    def run_tests(self):
        """Run all integration tests"""
        print("\n=== Running Integration Tests ===\n")
        
        # Test 1: File indexing
        self.test_file_indexing()
        
        # Test 2: Search functionality
        self.test_search_functionality()
        
        # Test 3: Context provider
        self.test_context_provider()
        
        # Test 4: Cross-module integration
        self.test_cross_module_integration()
        
        # Test 5: File monitoring (if available)
        if WATCHDOG_AVAILABLE:
            self.test_file_monitoring()
        else:
            print("⚠️  Skipping file monitoring test (watchdog not available)")
        
        # Test 6: Circular dependencies
        self.test_no_circular_dependencies()
        
        # Print summary
        self.print_summary()
        
    def test_file_indexing(self):
        """Test file indexing functionality"""
        print("Test 1: File Indexing")
        print("-" * 40)
        
        try:
            # Process test directory
            result = self.file_processor.process_directory(
                self.test_dir,
                recursive=False,
                file_extensions=['.txt', '.py', '.md']
            )
            
            if result['success']:
                stats = result.get('stats', {})
                print(f"✓ Indexed {stats.get('processed', 0)} files")
                print(f"  Created {stats.get('chunks_created', 0)} chunks")
                self.passed_tests += 1
            else:
                print(f"✗ Indexing failed: {result.get('error')}")
                self.failed_tests += 1
                
        except Exception as e:
            print(f"✗ Indexing error: {str(e)}")
            self.failed_tests += 1
            
    def test_search_functionality(self):
        """Test search functionality"""
        print("\nTest 2: Search Functionality")
        print("-" * 40)
        
        try:
            # Test vector search
            results = self.search_engine.search("Python programming", top_k=5)
            print(f"✓ Vector search returned {len(results)} results")
            
            # Test keyword search
            results = self.search_engine.keyword_search("test", top_k=5)
            print(f"✓ Keyword search returned {len(results)} results")
            
            # Test hybrid search
            results = self.search_engine.hybrid_search(
                "test document", top_k=5
            )
            print(f"✓ Hybrid search returned {len(results)} results")
            
            self.passed_tests += 1
            
        except Exception as e:
            print(f"✗ Search error: {str(e)}")
            self.failed_tests += 1
            
    def test_context_provider(self):
        """Test context provider functionality"""
        print("\nTest 3: Context Provider")
        print("-" * 40)
        
        try:
            # Get context for a query
            context_items = self.context_provider.get_context_for_query(
                "Python programming"
            )
            
            if context_items:
                print(f"✓ Retrieved {len(context_items)} context items")
                
                # Format context
                formatted = self.context_provider.format_context_for_chat(
                    context_items
                )
                print(f"✓ Formatted context: {len(formatted)} chars")
                
                self.passed_tests += 1
            else:
                print("✗ No context items retrieved")
                self.failed_tests += 1
                
        except Exception as e:
            print(f"✗ Context provider error: {str(e)}")
            self.failed_tests += 1
            
    def test_cross_module_integration(self):
        """Test integration with Notes and Artifacts"""
        print("\nTest 4: Cross-Module Integration")
        print("-" * 40)
        
        try:
            # Create a note referencing a test file
            test_file_path = os.path.join(self.test_dir, "test1.txt")
            note = Note(
                title="Test Note",
                content=f"This note references file: {test_file_path}",
                tags=["test", "integration"]
            )
            
            result = self.notes_db.create_note(note)
            if result['success']:
                print("✓ Created note with file reference")
            else:
                print(f"✗ Failed to create note: {result.get('error')}")
                
            # Create an artifact from search result
            artifact = Artifact(
                name="Test Search Result",
                description="Test artifact from search",
                content="Search result content",
                metadata={
                    'file_path': test_file_path,
                    'search_query': 'test'
                }
            )
            
            art_result = self.artifacts_db.create_artifact(artifact)
            if art_result['success']:
                print("✓ Created artifact from search result")
                self.passed_tests += 1
            else:
                error = art_result.get('error')
                print(f"✗ Failed to create artifact: {error}")
                self.failed_tests += 1
                
        except Exception as e:
            print(f"✗ Cross-module integration error: {str(e)}")
            self.failed_tests += 1
            
    def test_file_monitoring(self):
        """Test file monitoring functionality"""
        print("\nTest 5: File Monitoring")
        print("-" * 40)
        
        try:
            # Track updates
            updates = []
            
            def update_callback(file_path, action):
                updates.append((file_path, action))
                print(f"  File {action}: {os.path.basename(file_path)}")
            
            # Setup monitoring
            self.file_monitor.set_update_callback(update_callback)
            self.file_monitor.set_file_extensions(['.txt', '.py', '.md'])
            self.file_monitor.start_monitoring([self.test_dir])
            
            print("✓ File monitor started")
            
            # Create a new file
            new_file = os.path.join(self.test_dir, "test_new.txt")
            with open(new_file, 'w') as f:
                f.write("New test file content")
            
            # Modify existing file
            existing_file = os.path.join(self.test_dir, "test1.txt")
            with open(existing_file, 'a') as f:
                f.write("\nAppended content")
            
            # Wait for processing
            print("  Waiting for file changes to be detected...")
            time.sleep(5)
            
            # Stop monitoring
            self.file_monitor.stop_monitoring()
            
            if updates:
                print(f"✓ Detected {len(updates)} file changes")
                self.passed_tests += 1
            else:
                print("✗ No file changes detected")
                self.failed_tests += 1
                
        except Exception as e:
            print(f"✗ File monitoring error: {str(e)}")
            self.failed_tests += 1
            
    def test_no_circular_dependencies(self):
        """Test for circular dependencies"""
        print("\nTest 6: Circular Dependencies Check")
        print("-" * 40)
        
        try:
            # Try importing all modules in different orders
            import_tests = [
                "from src.gui.pages.file_search_page import FileSearchPage",
                "from src.gui.pages.notes_page import NotesPage",
                ("from src.gui.components.file_search_results import "
                 "FileSearchResultsWidget"),
                "from src.rag.context_provider import ContextProvider",
            ]
            
            for import_stmt in import_tests:
                try:
                    exec(import_stmt)
                    print(f"✓ {import_stmt}")
                except ImportError as e:
                    print(f"✗ Import failed: {import_stmt}")
                    print(f"   Error: {str(e)}")
                    raise
                    
            print("✓ No circular dependencies detected")
            self.passed_tests += 1
            
        except Exception as e:
            print(f"✗ Circular dependency detected: {str(e)}")
            self.failed_tests += 1
            
    def cleanup(self):
        """Cleanup test environment"""
        print("\n=== Cleaning up ===")
        
        try:
            # Stop file monitor if running
            if hasattr(self, 'file_monitor'):
                self.file_monitor.stop_monitoring()
            
            # Remove test directory
            if self.test_dir and os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
                print(f"Removed test directory: {self.test_dir}")
                
            # Clean up test databases
            # Note: In production, you'd want to properly clean up DB entries
            
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
            
    def print_summary(self):
        """Print test summary"""
        total_tests = self.passed_tests + self.failed_tests
        
        print("\n" + "=" * 50)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests} ✓")
        print(f"Failed: {self.failed_tests} ✗")
        
        if self.failed_tests == 0:
            print("\n🎉 All integration tests passed!")
        else:
            print(f"\n⚠️  {self.failed_tests} test(s) failed")
        
        print("=" * 50)


def main():
    """Run integration tests"""
    print("RAG File Search System - Integration Test Suite")
    print("=" * 50)
    
    tester = IntegrationTester()
    
    try:
        tester.setup()
        tester.run_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()