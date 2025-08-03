"""
Index directories with embeddings enabled for full search functionality
"""
import os
import sys

# Disable Watchdog first
os.environ['DINOAIR_DISABLE_WATCHDOG'] = '1'

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from rag.file_processor import FileProcessor
from utils.logger import Logger

def index_directory_with_embeddings(directory_path):
    """Index a directory with embeddings enabled"""
    logger = Logger()
    
    print(f"\n🔍 Indexing directory with embeddings: {directory_path}")
    print("This will enable full semantic search capabilities\n")
    
    # Initialize processor WITH embeddings
    processor = FileProcessor(
        generate_embeddings=True,  # Enable embeddings
        embedding_batch_size=16    # Process 16 texts at a time
    )
    
    # Process directory
    result = processor.process_directory(
        directory_path,
        recursive=True,
        file_extensions=['.txt', '.md', '.pdf', '.docx', '.py', '.js'],
        force_reprocess=True,  # Force to generate embeddings
        progress_callback=lambda msg, curr, total: print(f"Progress: {msg} ({curr}/{total})")
    )
    
    if result.get('success'):
        stats = result.get('stats', {})
        print(f"\n✅ Indexing complete!")
        print(f"📊 Statistics:")
        print(f"  - Files processed: {stats.get('processed', 0)}")
        print(f"  - Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  - Embeddings generated: {stats.get('total_embeddings', 0)}")
        print(f"  - Failed: {stats.get('failed', 0)}")
        
        if stats.get('failed', 0) > 0:
            print(f"\n❌ Failed files:")
            for failed in result.get('failed_files', []):
                print(f"  - {failed['file_path']}: {failed['error']}")
    else:
        print(f"\n❌ Indexing failed: {result.get('error')}")

if __name__ == "__main__":
    # Example: Index the docs directory
    docs_dir = "C:/Users/DinoP/Documents/DinoAir2.0dev/docs"
    
    if os.path.exists(docs_dir):
        index_directory_with_embeddings(docs_dir)
    else:
        print(f"Directory not found: {docs_dir}")
        print("\nYou can modify the script to index any directory:")
        print('  docs_dir = "C:/path/to/your/documents"')