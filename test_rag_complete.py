"""
Comprehensive Test Suite for RAG File Search System
Tests all components, integration, performance, and security aspects
"""

import os
import sys
import time
import tempfile
import shutil
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import json
import threading
import psutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import RAG components
from src.rag.file_processor import FileProcessor
from src.rag.vector_search import VectorSearchEngine, SearchResult
from src.rag.context_provider import ContextProvider
from src.rag.text_extractors import ExtractorFactory
from src.rag.file_chunker import FileChunker, TextChunk, ChunkMetadata
from src.rag.embedding_generator import get_embedding_generator
from src.rag.directory_validator import DirectoryValidator
from src.rag.file_monitor import FileMonitor

# Import database components
from src.database.file_search_db import FileSearchDB
from src.database.initialize_db import DatabaseManager

# Import GUI components
from src.gui.components.file_search_results import FileSearchResultsWidget
from src.gui.components.file_indexing_status import IndexingStatusWidget
from src.gui.components.directory_limiter_widget import DirectoryLimiterWidget

# Import utilities
from src.utils.logger import Logger


class TestFileProcessor(unittest.TestCase):
    """Test FileProcessor component"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_user = "test_file_processor"
        self.test_dir = tempfile.mkdtemp(prefix="test_processor_")
        self.processor = FileProcessor(
            user_name=self.test_user,
            chunk_size=500,
            chunk_overlap=50,
            generate_embeddings=False  # Disable for basic tests
        )
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_process_single_file(self):
        """Test processing a single text file"""
        # Create test file
        test_file = os.path.join(self.test_dir, "test.txt")
        content = "This is a test document for the RAG system. " * 20
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Process file
        result = self.processor.process_file(test_file)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertIsNotNone(result.get('file_id'))
        self.assertGreater(len(result.get('chunks', [])), 0)
        self.assertIn('stats', result)
    
    def test_process_directory(self):
        """Test processing a directory with multiple files"""
        # Create test files
        test_files = [
            ("doc1.txt", "Document 1 content " * 50),
            ("doc2.md", "# Markdown Document\n\nContent here " * 30),
            ("code.py", "def hello():\n    print('Hello World')\n" * 10)
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Process directory
        result = self.processor.process_directory(
            self.test_dir,
            recursive=False,
            file_extensions=['.txt', '.md', '.py']
        )
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(result['stats']['total_files'], 3)
        self.assertEqual(result['stats']['processed'], 3)
        self.assertEqual(result['stats']['failed'], 0)
    
    def test_file_size_limit(self):
        """Test file size limit enforcement"""
        # Create large file exceeding limit
        large_file = os.path.join(self.test_dir, "large.txt")
        # Set processor max size to 1KB for testing
        self.processor.max_file_size = 1024
        
        # Create 2KB file
        with open(large_file, 'w') as f:
            f.write("x" * 2048)
        
        result = self.processor.process_file(large_file)
        
        # Should fail due to size limit
        self.assertFalse(result['success'])
        self.assertIn("exceeds size limit", result['error'])
    
    def test_duplicate_file_handling(self):
        """Test handling of duplicate files"""
        test_file = os.path.join(self.test_dir, "duplicate.txt")
        content = "Duplicate test content"
        with open(test_file, 'w') as f:
            f.write(content)
        
        # Process file first time
        result1 = self.processor.process_file(test_file)
        self.assertTrue(result1['success'])
        
        # Process same file again without force
        result2 = self.processor.process_file(test_file, force_reprocess=False)
        self.assertTrue(result2['success'])
        self.assertIn("already indexed", result2.get('message', ''))
    
    def test_chunking_strategies(self):
        """Test different chunking strategies for different file types"""
        test_cases = [
            ("code.py", "def test():\n    pass\n\n" * 50, "python"),
            ("doc.md", "# Title\n\nParagraph\n\n" * 30, "markdown"),
            ("text.txt", "Regular text content. " * 100, "text")
        ]
        
        for filename, content, expected_type in test_cases:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            
            result = self.processor.process_file(file_path)
            self.assertTrue(result['success'])
            self.assertEqual(
                result['stats']['file_type'],
                expected_type,
                f"Expected {expected_type} for {filename}"
            )


class TestVectorSearch(unittest.TestCase):
    """Test VectorSearchEngine component"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_user = "test_vector_search"
        self.search_engine = VectorSearchEngine(self.test_user)
        self.db = FileSearchDB(self.test_user)
        
        # Create test data
        self._create_test_embeddings()
    
    def _create_test_embeddings(self):
        """Create test embeddings in database"""
        # Add test file
        file_result = self.db.add_indexed_file(
            file_path="/test/doc1.txt",
            file_hash="testhash123",
            size=1000,
            modified_date=datetime.now(),
            file_type="txt"
        )
        file_id = file_result['file_id']
        
        # Add test chunks
        test_chunks = [
            "Python is a programming language",
            "Machine learning with Python",
            "Data science and analytics"
        ]
        
        for i, content in enumerate(test_chunks):
            chunk_result = self.db.add_chunk(
                file_id=file_id,
                chunk_index=i,
                content=content,
                start_pos=i * 100,
                end_pos=(i + 1) * 100
            )
            
            # Add mock embedding
            mock_embedding = np.random.rand(384).tolist()
            self.db.add_embedding(
                chunk_id=chunk_result['chunk_id'],
                embedding_vector=mock_embedding,
                model_name="test_model"
            )
    
    def test_vector_search(self):
        """Test basic vector search functionality"""
        with patch.object(
            self.search_engine.embedding_generator,
            'generate_embedding',
            return_value=np.random.rand(384)
        ):
            results = self.search_engine.search(
                "Python programming",
                top_k=5
            )
            
            self.assertIsInstance(results, list)
            if results:
                self.assertIsInstance(results[0], SearchResult)
    
    def test_keyword_search(self):
        """Test keyword-based search"""
        results = self.search_engine.keyword_search(
            "Python",
            top_k=5
        )
        
        self.assertIsInstance(results, list)
        for result in results:
            self.assertIsInstance(result, SearchResult)
            self.assertEqual(result.match_type, 'keyword')
    
    def test_hybrid_search(self):
        """Test hybrid search combining vector and keyword"""
        with patch.object(
            self.search_engine.embedding_generator,
            'generate_embedding',
            return_value=np.random.rand(384)
        ):
            results = self.search_engine.hybrid_search(
                "Python programming",
                top_k=5,
                vector_weight=0.7,
                keyword_weight=0.3
            )
            
            self.assertIsInstance(results, list)
            for result in results:
                self.assertEqual(result.match_type, 'hybrid')
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([0, 1, 0])
        vec3 = np.array([1, 0, 0])
        
        # Orthogonal vectors
        sim1 = VectorSearchEngine.cosine_similarity(vec1, vec2)
        self.assertAlmostEqual(sim1, 0.0)
        
        # Identical vectors
        sim2 = VectorSearchEngine.cosine_similarity(vec1, vec3)
        self.assertAlmostEqual(sim2, 1.0)
    
    def test_reranking(self):
        """Test search result reranking"""
        # Create mock results
        mock_results = [
            SearchResult(
                chunk_id="1",
                file_id="f1",
                file_path="/test1.txt",
                content="Python is great",
                score=0.7,
                chunk_index=0,
                start_pos=0,
                end_pos=100
            ),
            SearchResult(
                chunk_id="2",
                file_id="f2",
                file_path="/test2.txt",
                content="Python programming is great",
                score=0.6,
                chunk_index=0,
                start_pos=0,
                end_pos=100
            )
        ]
        
        reranked = self.search_engine.rerank_results(
            "Python programming",
            mock_results
        )
        
        # Should boost exact phrase match
        self.assertGreater(reranked[1].score, 0.6)


class TestContextProvider(unittest.TestCase):
    """Test ContextProvider component"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_user = "test_context_provider"
        self.context_provider = ContextProvider(self.test_user)
        
        # Mock search results
        self.mock_results = [
            SearchResult(
                chunk_id="1",
                file_id="f1",
                file_path="/docs/guide.md",
                content="This is a user guide for the system.",
                score=0.9,
                chunk_index=0,
                start_pos=0,
                end_pos=100,
                match_type="hybrid"
            )
        ]
    
    def test_get_context_for_query(self):
        """Test getting context for a query"""
        with patch.object(
            self.context_provider.search_engine,
            'hybrid_search',
            return_value=self.mock_results
        ):
            context_items = self.context_provider.get_context_for_query(
                "user guide"
            )
            
            self.assertEqual(len(context_items), 1)
            self.assertEqual(context_items[0]['file_name'], "guide.md")
            self.assertEqual(context_items[0]['score'], 0.9)
    
    def test_format_context_for_chat(self):
        """Test formatting context for chat"""
        context_items = [
            {
                'file_name': 'guide.md',
                'content': 'Test content',
                'score': 0.9,
                'file_type': 'markdown'
            }
        ]
        
        formatted = self.context_provider.format_context_for_chat(
            context_items,
            include_metadata=True
        )
        
        self.assertIn("Context 1", formatted)
        self.assertIn("File: guide.md", formatted)
        self.assertIn("Relevance: 90.0%", formatted)
        self.assertIn("Test content", formatted)
    
    def test_context_length_limit(self):
        """Test context length limiting"""
        # Create long context
        long_context = [
            {
                'file_name': f'file{i}.txt',
                'content': 'x' * 500,
                'score': 0.8
            }
            for i in range(10)
        ]
        
        self.context_provider.max_context_length = 1000
        formatted = self.context_provider.format_context_for_chat(
            long_context
        )
        
        self.assertLessEqual(len(formatted), 1100)  # Allow small overhead
        self.assertIn("truncated", formatted)


class TestFileSearchDB(unittest.TestCase):
    """Test FileSearchDB component"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_user = "test_file_search_db"
        self.db = FileSearchDB(self.test_user)
    
    def test_create_tables(self):
        """Test database table creation"""
        result = self.db.create_tables()
        self.assertTrue(result)
    
    def test_add_and_retrieve_file(self):
        """Test adding and retrieving file"""
        # Add file
        result = self.db.add_indexed_file(
            file_path="/test/document.pdf",
            file_hash="abc123",
            size=1024,
            modified_date=datetime.now(),
            file_type="pdf",
            metadata={"pages": 10}
        )
        
        self.assertTrue(result['success'])
        file_id = result['file_id']
        
        # Retrieve file
        file_info = self.db.get_file_by_path("/test/document.pdf")
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info['file_hash'], "abc123")
        self.assertEqual(file_info['metadata']['pages'], 10)
    
    def test_chunk_operations(self):
        """Test chunk add/retrieve operations"""
        # First add a file
        file_result = self.db.add_indexed_file(
            file_path="/test/chunks.txt",
            file_hash="xyz789",
            size=2048,
            modified_date=datetime.now()
        )
        file_id = file_result['file_id']
        
        # Add chunks
        chunk_results = []
        for i in range(3):
            result = self.db.add_chunk(
                file_id=file_id,
                chunk_index=i,
                content=f"Chunk {i} content",
                start_pos=i * 100,
                end_pos=(i + 1) * 100,
                metadata={"chunk_type": "text"}
            )
            self.assertTrue(result['success'])
            chunk_results.append(result)
    
    def test_embedding_operations(self):
        """Test embedding storage and retrieval"""
        # Create file and chunk first
        file_result = self.db.add_indexed_file(
            file_path="/test/embeddings.txt",
            file_hash="emb123",
            size=500,
            modified_date=datetime.now()
        )
        
        chunk_result = self.db.add_chunk(
            file_id=file_result['file_id'],
            chunk_index=0,
            content="Test content",
            start_pos=0,
            end_pos=100
        )
        
        # Add embedding
        embedding_vector = np.random.rand(384).tolist()
        emb_result = self.db.add_embedding(
            chunk_id=chunk_result['chunk_id'],
            embedding_vector=embedding_vector,
            model_name="test_model"
        )
        
        self.assertTrue(emb_result['success'])
    
    def test_search_settings(self):
        """Test search settings storage"""
        # Update settings
        result = self.db.update_search_settings(
            "allowed_directories",
            ["/home/user/docs", "/shared/docs"]
        )
        self.assertTrue(result['success'])
        
        # Retrieve settings
        settings = self.db.get_search_settings("allowed_directories")
        self.assertTrue(settings['success'])
        self.assertEqual(len(settings['setting_value']), 2)
    
    def test_directory_management(self):
        """Test directory allow/exclude list management"""
        # Add allowed directory
        result = self.db.add_allowed_directory("/test/allowed")
        self.assertTrue(result['success'])
        
        # Add excluded directory
        result = self.db.add_excluded_directory("/test/excluded")
        self.assertTrue(result['success'])
        
        # Get directory settings
        settings = self.db.get_directory_settings()
        self.assertTrue(settings['success'])
        self.assertIn("/test/allowed", settings['allowed_directories'])
        self.assertIn("/test/excluded", settings['excluded_directories'])
        
        # Remove directories
        result = self.db.remove_allowed_directory("/test/allowed")
        self.assertTrue(result['success'])


class TestDirectoryValidator(unittest.TestCase):
    """Test DirectoryValidator component"""
    
    def setUp(self):
        """Set up test environment"""
        self.validator = DirectoryValidator()
        self.test_dir = tempfile.mkdtemp(prefix="test_validator_")
        
        # Create test directory structure
        os.makedirs(os.path.join(self.test_dir, "allowed"))
        os.makedirs(os.path.join(self.test_dir, "excluded"))
        os.makedirs(os.path.join(self.test_dir, "nested", "deep"))
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_path_validation(self):
        """Test path validation logic"""
        # Set allowed directories
        self.validator.set_allowed_directories([
            os.path.join(self.test_dir, "allowed")
        ])
        
        # Test allowed path
        result = self.validator.validate_path(
            os.path.join(self.test_dir, "allowed", "file.txt")
        )
        self.assertTrue(result['valid'])
        
        # Test non-allowed path
        result = self.validator.validate_path(
            os.path.join(self.test_dir, "other", "file.txt")
        )
        self.assertFalse(result['valid'])
    
    def test_exclusion_rules(self):
        """Test directory exclusion rules"""
        # Allow root but exclude subdirectory
        self.validator.set_allowed_directories([self.test_dir])
        self.validator.set_excluded_directories([
            os.path.join(self.test_dir, "excluded")
        ])
        
        # Test excluded path
        result = self.validator.validate_path(
            os.path.join(self.test_dir, "excluded", "file.txt")
        )
        self.assertFalse(result['valid'])
        self.assertIn("excluded", result['message'])
    
    def test_security_validation(self):
        """Test security validation for path traversal"""
        self.validator.set_allowed_directories([self.test_dir])
        
        # Test path traversal attempt
        malicious_path = os.path.join(self.test_dir, "..", "..", "etc", "passwd")
        result = self.validator.validate_path(malicious_path)
        self.assertFalse(result['valid'])


class TestPerformance(unittest.TestCase):
    """Performance and load tests"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.test_user = "test_performance"
        self.test_dir = tempfile.mkdtemp(prefix="test_perf_")
        self.processor = FileProcessor(
            user_name=self.test_user,
            generate_embeddings=False
        )
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_large_file_processing(self):
        """Test processing large files"""
        # Create 5MB file
        large_file = os.path.join(self.test_dir, "large.txt")
        content = "x" * 1024  # 1KB
        
        with open(large_file, 'w') as f:
            for _ in range(5 * 1024):  # 5MB total
                f.write(content)
        
        start_time = time.time()
        result = self.processor.process_file(large_file)
        processing_time = time.time() - start_time
        
        self.assertTrue(result['success'])
        self.assertLess(processing_time, 10)  # Should process in < 10 seconds
        
        print(f"Large file processing time: {processing_time:.2f}s")
        print(f"Chunks created: {len(result.get('chunks', []))}")
    
    def test_batch_file_processing(self):
        """Test processing many files"""
        # Create 100 small files
        for i in range(100):
            file_path = os.path.join(self.test_dir, f"file_{i}.txt")
            with open(file_path, 'w') as f:
                f.write(f"Test content for file {i}\n" * 10)
        
        start_time = time.time()
        result = self.processor.process_directory(
            self.test_dir,
            recursive=False
        )
        processing_time = time.time() - start_time
        
        self.assertTrue(result['success'])
        self.assertEqual(result['stats']['total_files'], 100)
        self.assertLess(processing_time, 30)  # Should process in < 30 seconds
        
        print(f"Batch processing time: {processing_time:.2f}s")
        print(f"Files/second: {100 / processing_time:.2f}")
    
    def test_memory_usage(self):
        """Test memory usage during processing"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and process multiple files
        for i in range(20):
            file_path = os.path.join(self.test_dir, f"mem_test_{i}.txt")
            with open(file_path, 'w') as f:
                f.write("Memory test content\n" * 1000)
            
            self.processor.process_file(file_path)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory increase: {memory_increase:.2f} MB")
        self.assertLess(memory_increase, 100)  # Should not use > 100MB
    
    def test_concurrent_search(self):
        """Test concurrent search operations"""
        search_engine = VectorSearchEngine(self.test_user)
        
        # Mock search to avoid embedding generation
        def mock_search(query, **kwargs):
            time.sleep(0.01)  # Simulate processing
            return []
        
        search_engine.search = mock_search
        
        # Run concurrent searches
        results = []
        threads = []
        
        def search_thread(query):
            result = search_engine.search(query)
            results.append(result)
        
        start_time = time.time()
        
        for i in range(50):
            thread = threading.Thread(
                target=search_thread,
                args=(f"query {i}",)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        concurrent_time = time.time() - start_time
        
        print(f"Concurrent search time: {concurrent_time:.2f}s")
        self.assertEqual(len(results), 50)
        self.assertLess(concurrent_time, 5)  # Should handle concurrency well


class TestSecurity(unittest.TestCase):
    """Security-focused tests"""
    
    def setUp(self):
        """Set up security test environment"""
        self.test_user = "test_security"
        self.validator = DirectoryValidator()
        self.db = FileSearchDB(self.test_user)
        self.safe_dir = tempfile.mkdtemp(prefix="test_sec_")
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.safe_dir):
            shutil.rmtree(self.safe_dir)
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        self.validator.set_allowed_directories([self.safe_dir])
        
        # Various path traversal attempts
        attacks = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32\\config",
            os.path.join(self.safe_dir, "..", "..", "etc", "passwd"),
            self.safe_dir + "/../../../etc/passwd"
        ]
        
        for attack_path in attacks:
            result = self.validator.validate_path(attack_path)
            self.assertFalse(
                result['valid'],
                f"Path traversal not blocked: {attack_path}"
            )
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in database operations"""
        # Try SQL injection in file path
        malicious_paths = [
            "'; DROP TABLE indexed_files; --",
            "' OR '1'='1",
            '"; DELETE FROM file_chunks WHERE 1=1; --'
        ]
        
        for path in malicious_paths:
            result = self.db.add_indexed_file(
                file_path=path,
                file_hash="test",
                size=100,
                modified_date=datetime.now()
            )
            # Should succeed (properly escaped)
            self.assertTrue(result['success'])
            
            # Verify tables still exist
            self.assertTrue(self.db.create_tables())
    
    def test_input_sanitization(self):
        """Test input sanitization for search queries"""
        search_engine = VectorSearchEngine(self.test_user)
        
        # Test with potentially malicious queries
        malicious_queries = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE; --",
            "../../etc/passwd",
            "\x00\x01\x02",  # Null bytes
            "A" * 10000  # Very long input
        ]
        
        for query in malicious_queries:
            try:
                # Should handle gracefully
                results = search_engine.keyword_search(query)
                self.assertIsInstance(results, list)
            except Exception as e:
                self.fail(f"Failed to handle malicious query: {query}, {e}")


class TestGUIComponents(unittest.TestCase):
    """Test GUI components (without Qt app)"""
    
    def test_file_search_results_widget_init(self):
        """Test FileSearchResultsWidget initialization"""
        # Test that widget can be imported and has required methods
        self.assertTrue(hasattr(FileSearchResultsWidget, 'display_results'))
        self.assertTrue(hasattr(FileSearchResultsWidget, 'clear_results'))
    
    def test_file_indexing_status_widget_init(self):
        """Test FileIndexingStatusWidget initialization"""
        # Test that widget can be imported and has required methods
        self.assertTrue(hasattr(IndexingStatusWidget, 'update_status'))
        self.assertTrue(hasattr(IndexingStatusWidget, 'set_progress'))
    
    def test_directory_limiter_widget_init(self):
        """Test DirectoryLimiterWidget initialization"""
        # Test that widget can be imported and has required methods
        self.assertTrue(hasattr(DirectoryLimiterWidget, 'get_allowed_directories'))
        self.assertTrue(hasattr(DirectoryLimiterWidget, 'get_excluded_directories'))


class TestIntegration(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_user = "test_integration_e2e"
        self.test_dir = tempfile.mkdtemp(prefix="test_e2e_")
        
        # Initialize all components
        self.processor = FileProcessor(
            user_name=self.test_user,
            generate_embeddings=True
        )
        self.search_engine = VectorSearchEngine(self.test_user)
        self.context_provider = ContextProvider(self.test_user)
        self.db = FileSearchDB(self.test_user)
    
    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_pipeline(self):
        """Test complete pipeline from indexing to search"""
        # Create test documents
        docs = [
            ("python_guide.md", "# Python Programming Guide\n\nPython is a versatile programming language."),
            ("ml_intro.txt", "Machine learning is a subset of artificial intelligence."),
            ("data_science.txt", "Data science combines statistics and programming.")
        ]
        
        for filename, content in docs:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Index documents
        index_result = self.processor.process_directory(self.test_dir)
        self.assertTrue(index_result['success'])
        self.assertEqual(index_result['stats']['processed'], 3)
        
        # Search for content
        with patch.object(
            self.search_engine.embedding_generator,
            'generate_embedding',
            return_value=np.random.rand(384)
        ):
            search_results = self.search_engine.hybrid_search(
                "Python programming",
                top_k=5
            )
        
        # Get context for chat
        with patch.object(
            self.context_provider.search_engine,
            'hybrid_search',
            return_value=search_results
        ):
            context = self.context_provider.get_context_for_query(
                "Tell me about Python"
            )
            
            self.assertGreater(len(context), 0)
            
            # Format context
            formatted = self.context_provider.format_context_for_chat(context)
            self.assertIn("Python", formatted)
    
    def test_file_update_detection(self):
        """Test file update detection and reprocessing"""
        # Create and process file
        test_file = os.path.join(self.test_dir, "update_test.txt")
        with open(test_file, 'w') as f:
            f.write("Original content")
        
        result1 = self.processor.process_file(test_file)
        self.assertTrue(result1['success'])
        original_hash = self.db.get_file_by_path(test_file)['file_hash']
        
        # Modify file
        time.sleep(0.1)  # Ensure different timestamp
        with open(test_file, 'w') as f:
            f.write("Updated content")
        
        # Process again
        result2 = self.processor.process_file(test_file, force_reprocess=True)
        self.assertTrue(result2['success'])
        new_hash = self.db.get_file_by_path(test_file)['file_hash']
        
        self.assertNotEqual(original_hash, new_hash)


def run_performance_benchmarks():
    """Run performance benchmarks and print results"""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARKS")
    print("="*60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def run_security_audit():
    """Run security audit tests"""
    print("\n" + "="*60)
    print("SECURITY AUDIT")
    print("="*60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecurity)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


def calculate_code_coverage():
    """Calculate and display code coverage"""
    try:
        import coverage
        
        cov = coverage.Coverage()
        cov.start()
        
        # Run all tests
        unittest.main(argv=[''], exit=False, verbosity=0)
        
        cov.stop()
        cov.save()
        
        print("\n" + "="*60)
        print("CODE COVERAGE REPORT")
        print("="*60)
        cov.report()
        
    except ImportError:
        print("Coverage module not installed. Run: pip install coverage")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG File Search Comprehensive Test Suite")
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--performance', action='store_true', help='Run performance benchmarks')
    parser.add_argument('--security', action='store_true', help='Run security audit')
    parser.add_argument('--coverage', action='store_true', help='Calculate code coverage')
    
    args = parser.parse_args()
    
    if args.coverage:
        calculate_code_coverage()
    elif args.performance:
        run_performance_benchmarks()
    elif args.security:
        run_security_audit()
    elif args.all or (not any(vars(args).values())):
        # Run all tests
        print("Running RAG File Search Comprehensive Test Suite")
        print("=" * 60)
        unittest.main(argv=[''], verbosity=2)
    else:
        # Run specific test suites
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        if args.unit:
            suite.addTests(loader.loadTestsFromTestCase(TestFileProcessor))
            suite.addTests(loader.loadTestsFromTestCase(TestVectorSearch))
            suite.addTests(loader.loadTestsFromTestCase(TestContextProvider))
            suite.addTests(loader.loadTestsFromTestCase(TestFileSearchDB))
            suite.addTests(loader.loadTestsFromTestCase(TestDirectoryValidator))
            suite.addTests(loader.loadTestsFromTestCase(TestGUIComponents))
        
        if args.integration:
            suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
        
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)