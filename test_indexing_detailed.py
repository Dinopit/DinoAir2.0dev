"""Detailed test to diagnose indexing issues"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Disable watchdog
os.environ['DINOAIR_DISABLE_WATCHDOG'] = '1'

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import QSettings
from src.gui.pages.file_search_page import FileSearchPage
from src.database.file_search_db import FileSearchDB
from src.utils.logger import Logger
from src.database.initialize_db import initialize_user_databases


class DetailedTestWindow(QMainWindow):
    """Detailed test window for indexing diagnostics"""
    
    def __init__(self):
        super().__init__()
        self.logger = Logger()
        self.setWindowTitle("Indexing Diagnostic Test")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize database
        self.db_manager = initialize_user_databases("default_user")
        self.file_search_db = FileSearchDB(self.db_manager)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add file search page
        self.file_search_page = FileSearchPage()
        layout.addWidget(self.file_search_page)
        
        # Add diagnostic controls
        diag_widget = QWidget()
        diag_layout = QVBoxLayout(diag_widget)
        
        # Database check button
        check_db_btn = QPushButton("Check Database Contents")
        check_db_btn.clicked.connect(self.check_database)
        diag_layout.addWidget(check_db_btn)
        
        # Check embeddings button
        check_embeddings_btn = QPushButton("Check Embeddings")
        check_embeddings_btn.clicked.connect(self.check_embeddings)
        diag_layout.addWidget(check_embeddings_btn)
        
        # Manual index test button
        manual_test_btn = QPushButton("Manual Index Test File")
        manual_test_btn.clicked.connect(self.manual_index_test)
        diag_layout.addWidget(manual_test_btn)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        diag_layout.addWidget(self.output_text)
        
        layout.addWidget(diag_widget)
        
        self.log_output("Diagnostic window ready. Index some files then check the database.")
    
    def log_output(self, message: str):
        """Add message to output area"""
        self.output_text.append(message)
        self.output_text.append("")  # Add blank line
        print(message)
    
    def check_database(self):
        """Check what's in the database"""
        self.log_output("=== DATABASE CHECK ===")
        
        try:
            # Get indexed files
            conn = self.db_manager.get_file_search_connection()
            cursor = conn.cursor()
            
            # Check indexed_files table
            cursor.execute("SELECT COUNT(*) FROM indexed_files")
            file_count = cursor.fetchone()[0]
            self.log_output(f"Total indexed files: {file_count}")
            
            if file_count > 0:
                cursor.execute("""
                    SELECT file_path, file_type, status, indexed_date 
                    FROM indexed_files 
                    ORDER BY indexed_date DESC 
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    self.log_output(f"  File: {row[0]}")
                    self.log_output(f"    Type: {row[1]}, Status: {row[2]}, Date: {row[3]}")
            
            # Check chunks
            cursor.execute("SELECT COUNT(*) FROM file_chunks")
            chunk_count = cursor.fetchone()[0]
            self.log_output(f"\nTotal chunks: {chunk_count}")
            
            # Check embeddings
            cursor.execute("SELECT COUNT(*) FROM file_embeddings")
            embedding_count = cursor.fetchone()[0]
            self.log_output(f"Total embeddings: {embedding_count}")
            
            # Check for files without embeddings
            cursor.execute("""
                SELECT f.file_path 
                FROM indexed_files f
                LEFT JOIN file_chunks c ON f.id = c.file_id
                LEFT JOIN file_embeddings e ON c.id = e.chunk_id
                WHERE e.id IS NULL AND f.status = 'indexed'
            """)
            missing_embeddings = cursor.fetchall()
            if missing_embeddings:
                self.log_output(f"\nFiles missing embeddings: {len(missing_embeddings)}")
                for row in missing_embeddings[:5]:
                    self.log_output(f"  - {row[0]}")
            
            conn.close()
            
        except Exception as e:
            self.log_output(f"Database check error: {e}")
            import traceback
            self.log_output(traceback.format_exc())
    
    def check_embeddings(self):
        """Check embedding generation"""
        self.log_output("=== EMBEDDING CHECK ===")
        
        try:
            # Try to import and test embedding generator
            from src.rag.embedding_generator import EmbeddingGenerator
            
            gen = EmbeddingGenerator()
            self.log_output(f"Embedding model: {gen.model_name}")
            self.log_output(f"Device: {gen.device}")
            
            # Test embedding generation
            test_text = "This is a test sentence for embedding generation."
            self.log_output(f"\nTesting embedding for: '{test_text}'")
            
            embedding = gen.generate_embedding(test_text)
            self.log_output(f"Embedding shape: {embedding.shape}")
            self.log_output(f"Embedding sample: {embedding[:5]}...")
            
            # Check if model is loaded
            info = gen.get_model_info()
            self.log_output(f"\nModel info: {info}")
            
        except ImportError as e:
            self.log_output(f"Import error: {e}")
            self.log_output("sentence-transformers may not be installed!")
        except Exception as e:
            self.log_output(f"Embedding check error: {e}")
            import traceback
            self.log_output(traceback.format_exc())
    
    def manual_index_test(self):
        """Manually test indexing a single file"""
        self.log_output("=== MANUAL INDEX TEST ===")
        
        # Create a test file
        test_file = Path("test_index_file.txt")
        test_content = "This is a test file for manual indexing verification."
        test_file.write_text(test_content)
        
        try:
            from src.rag.file_processor import FileProcessor
            
            # Create processor
            processor = FileProcessor(generate_embeddings=True)
            
            self.log_output(f"Processing file: {test_file}")
            
            # Process the file
            success, message = processor.process_file(str(test_file))
            
            self.log_output(f"Result: {'SUCCESS' if success else 'FAILED'}")
            self.log_output(f"Message: {message}")
            
            # Check if it's in the database
            self.check_database()
            
        except Exception as e:
            self.log_output(f"Manual index error: {e}")
            import traceback
            self.log_output(traceback.format_exc())
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()


def main():
    """Run the detailed test"""
    print("Starting Detailed Indexing Test...")
    print("=" * 50)
    
    app = QApplication(sys.argv)
    app.setApplicationName("DinoAir")
    app.setOrganizationName("DinoAir")
    
    window = DetailedTestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()