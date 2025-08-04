"""
Test RAG indexing with force reprocessing
"""
import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.rag.file_processor import FileProcessor

def test_force_reindexing():
    """Test file indexing with force reprocessing"""
    print("Testing RAG force reindexing...\n")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_file = f.name
        f.write("This is a test document for indexing.\n")
        f.write("It contains multiple lines of text.\n")
        f.write("We will test the chunking and indexing process.\n")
        f.write("The file processor should create chunks from this content.\n")
    
    try:
        # Initialize processor with embeddings disabled for speed
        print("1. Initializing file processor...")
        processor = FileProcessor(generate_embeddings=False)
        print("✓ File processor initialized\n")
        
        # Process the file without forcing (should skip if already indexed)
        print("2. Processing file normally...")
        result1 = processor.process_file(test_file)
        
        if result1.get('success'):
            action = result1.get('stats', {}).get('action', 'processed')
            if action == 'skipped':
                print("✓ File was skipped (already indexed)")
            else:
                print("✓ File was processed")
                print(f"  Chunks created: {len(result1.get('chunks', []))}")
        else:
            print(f"✗ Processing failed: {result1.get('error')}")
        
        # Process the file with force_reprocess=True
        print("\n3. Force reprocessing the same file...")
        result2 = processor.process_file(test_file, force_reprocess=True)
        
        if result2.get('success'):
            chunks = result2.get('chunks', [])
            print("✓ File force reprocessed successfully!")
            print(f"  File ID: {result2.get('file_id')}")
            print(f"  Chunks created: {len(chunks)}")
            
            # Display chunk details
            if chunks:
                print("\n  Chunk details:")
                for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                    print(f"    Chunk {i+1}:")
                    print(f"      Content: {chunk.content[:50]}...")
                    print(f"      Type: {chunk.metadata.chunk_type}")
                    print(f"      Position: {chunk.metadata.start_pos}-{chunk.metadata.end_pos}")
                
                if len(chunks) > 3:
                    print(f"    ... and {len(chunks) - 3} more chunks")
        else:
            print(f"✗ Force reprocessing failed: {result2.get('error')}")
        
        # Test directory processing
        print("\n4. Testing directory processing...")
        test_dir = os.path.dirname(test_file)
        dir_result = processor.process_directory(
            test_dir,
            recursive=False,
            file_extensions=['.txt'],
            force_reprocess=True
        )
        
        if dir_result.get('success'):
            stats = dir_result.get('stats', {})
            print("✓ Directory processed successfully!")
            print(f"  Total files: {stats.get('total_files', 0)}")
            print(f"  Processed: {stats.get('processed', 0)}")
            print(f"  Failed: {stats.get('failed', 0)}")
            print(f"  Skipped: {stats.get('skipped', 0)}")
            print(f"  Total chunks: {stats.get('total_chunks', 0)}")
        else:
            print(f"✗ Directory processing failed: {dir_result.get('error')}")
        
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.unlink(test_file)
            print("\n✓ Cleaned up test file")

if __name__ == "__main__":
    test_force_reindexing()