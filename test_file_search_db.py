#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for FileSearchDB functionality
Tests the RAG file search database initialization and basic operations
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

from src.database.initialize_db import DatabaseManager
from src.database.file_search_db import FileSearchDB


def test_database_initialization():
    """Test database initialization"""
    print("Testing FileSearchDB initialization...")
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(user_name="test_file_search_user")
        db_manager.initialize_all_databases()
        print("✓ Database manager initialized successfully")
        
        # Test FileSearchDB initialization
        file_search_db = FileSearchDB(user_name="test_file_search_user")
        print("✓ FileSearchDB initialized successfully")
        
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {str(e)}")
        return False


def test_file_indexing():
    """Test file indexing operations"""
    print("\nTesting file indexing operations...")
    
    try:
        # Initialize FileSearchDB
        file_search_db = FileSearchDB(user_name="test_file_search_user")
        
        # Test adding an indexed file
        test_file_path = "test_documents/sample.txt"
        result = file_search_db.add_indexed_file(
            file_path=test_file_path,
            file_hash="abc123def456",
            size=1024,
            modified_date=datetime.now(),
            file_type="txt",
            metadata={"encoding": "utf-8", "language": "en"}
        )
        
        if result["success"]:
            print(f"✓ File indexed successfully: {result['file_id']}")
            file_id = result["file_id"]
        else:
            print(f"✗ Failed to index file: {result['error']}")
            return False
        
        # Test retrieving file by path
        file_info = file_search_db.get_file_by_path(test_file_path)
        if file_info:
            print(f"✓ Retrieved file info: {file_info['file_path']}")
        else:
            print("✗ Failed to retrieve file info")
            return False
        
        # Test adding chunks
        chunk_result = file_search_db.add_chunk(
            file_id=file_id,
            chunk_index=0,
            content="This is a test chunk of text content.",
            start_pos=0,
            end_pos=37,
            metadata={"paragraph": 1}
        )
        
        if chunk_result["success"]:
            print(f"✓ Chunk added successfully: {chunk_result['chunk_id']}")
            chunk_id = chunk_result["chunk_id"]
        else:
            print(f"✗ Failed to add chunk: {chunk_result['error']}")
            return False
        
        # Test adding embedding
        test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Sample embedding vector
        embedding_result = file_search_db.add_embedding(
            chunk_id=chunk_id,
            embedding_vector=test_embedding,
            model_name="test-model-v1"
        )
        
        if embedding_result["success"]:
            print(f"✓ Embedding stored successfully: {embedding_result['embedding_id']}")
        else:
            print(f"✗ Failed to store embedding: {embedding_result['error']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ File indexing test failed: {str(e)}")
        return False


def test_search_settings():
    """Test search settings operations"""
    print("\nTesting search settings operations...")
    
    try:
        # Initialize FileSearchDB
        file_search_db = FileSearchDB(user_name="test_file_search_user")
        
        # Test updating search settings
        test_directories = ["/path/to/documents", "/another/path"]
        result = file_search_db.update_search_settings(
            setting_name="search_directories",
            setting_value=test_directories
        )
        
        if result["success"]:
            print("✓ Search settings updated successfully")
        else:
            print(f"✗ Failed to update settings: {result['error']}")
            return False
        
        # Test retrieving settings
        settings = file_search_db.get_search_settings("search_directories")
        if settings["success"]:
            print(f"✓ Retrieved settings: {settings['setting_value']}")
        else:
            print("✗ Failed to retrieve settings")
            return False
        
        # Test retrieving all settings
        all_settings = file_search_db.get_search_settings()
        if all_settings["success"]:
            print(f"✓ Retrieved all settings: {len(all_settings['settings'])} settings found")
        else:
            print("✗ Failed to retrieve all settings")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Search settings test failed: {str(e)}")
        return False


def test_statistics():
    """Test statistics retrieval"""
    print("\nTesting statistics retrieval...")
    
    try:
        # Initialize FileSearchDB
        file_search_db = FileSearchDB(user_name="test_file_search_user")
        
        # Get statistics
        stats = file_search_db.get_indexed_files_stats()
        
        print("✓ Statistics retrieved:")
        print(f"  - Total files: {stats.get('total_files', 0)}")
        print(f"  - Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  - Total embeddings: {stats.get('total_embeddings', 0)}")
        print(f"  - Total size: {stats.get('total_size_mb', 0)} MB")
        print(f"  - Files by type: {stats.get('files_by_type', {})}")
        
        return True
        
    except Exception as e:
        print(f"✗ Statistics test failed: {str(e)}")
        return False


def test_cleanup():
    """Test cleanup operations"""
    print("\nTesting cleanup operations...")
    
    try:
        # Initialize FileSearchDB
        file_search_db = FileSearchDB(user_name="test_file_search_user")
        
        # Remove test file from index
        result = file_search_db.remove_file_from_index("test_documents/sample.txt")
        
        if result["success"]:
            print("✓ Test file removed from index successfully")
        else:
            print(f"Note: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Cleanup test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("FileSearchDB Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    if not test_database_initialization():
        all_passed = False
    
    if not test_file_indexing():
        all_passed = False
    
    if not test_search_settings():
        all_passed = False
    
    if not test_statistics():
        all_passed = False
    
    if not test_cleanup():
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed successfully!")
    else:
        print("✗ Some tests failed. Please check the output above.")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)