"""Simple test to check indexing functionality"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Disable watchdog
os.environ['DINOAIR_DISABLE_WATCHDOG'] = '1'

print("Testing RAG indexing...")

# Test 1: Check if sentence-transformers is installed
print("\n1. Checking sentence-transformers installation...")
try:
    import sentence_transformers
    print("✓ sentence-transformers is installed")
except ImportError as e:
    print("✗ sentence-transformers NOT installed!")
    print("  Install with: pip install sentence-transformers")
    print(f"  Error: {e}")

# Test 2: Check if torch is installed
print("\n2. Checking torch installation...")
try:
    import torch
    print(f"✓ torch is installed (version: {torch.__version__})")
    if torch.cuda.is_available():
        print(f"  CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print("  Using CPU (no CUDA)")
except ImportError as e:
    print("✗ torch NOT installed!")
    print("  Install with: pip install torch")
    print(f"  Error: {e}")

# Test 3: Test embedding generation
print("\n3. Testing embedding generation...")
try:
    from src.rag.embedding_generator import EmbeddingGenerator
    
    gen = EmbeddingGenerator()
    print(f"  Model: {gen.model_name}")
    print(f"  Device: {gen.device}")
    
    # Test embedding
    test_text = "This is a test sentence."
    print(f"  Generating embedding for: '{test_text}'")
    
    embedding = gen.generate_embedding(test_text)
    print(f"✓ Embedding generated successfully!")
    print(f"  Shape: {embedding.shape}")
    print(f"  Sample values: {embedding[:5]}")
    
except Exception as e:
    print(f"✗ Embedding generation failed!")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Test file processing
print("\n4. Testing file processing...")
test_file = Path("test_simple.txt")
test_file.write_text("This is a simple test file for indexing.")

try:
    from src.rag.file_processor import FileProcessor
    
    processor = FileProcessor(generate_embeddings=False)  # Disable embeddings for now
    print(f"  Processing file: {test_file}")
    
    result = processor.process_file(str(test_file))
    
    if result.get('success'):
        print("✓ File processed successfully!")
        print(f"  File ID: {result.get('file_id')}")
        print(f"  Chunks created: {len(result.get('chunks', []))}")
    else:
        print(f"✗ File processing failed: {result.get('error', 'Unknown error')}")
        
except Exception as e:
    print(f"✗ File processing error!")
    print(f"  Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if test_file.exists():
        test_file.unlink()

# Test 5: Test database access
print("\n5. Testing database access...")
try:
    # Try to access the file search database directly
    db_path = Path("src/user_data/default_user/databases/file_search.db")
    if db_path.exists():
        print(f"✓ Database exists at: {db_path}")
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"  Tables: {[t[0] for t in tables]}")
        
        # Check indexed files
        cursor.execute("SELECT COUNT(*) FROM indexed_files")
        count = cursor.fetchone()[0]
        print(f"  Indexed files: {count}")
        
        conn.close()
    else:
        print(f"✗ Database not found at: {db_path}")
        
except Exception as e:
    print(f"✗ Database access error!")
    print(f"  Error: {e}")

print("\n" + "="*50)
print("Diagnostics complete!")
print("\nIf sentence-transformers is not installed, run:")
print("  pip install sentence-transformers")
print("\nThis will also install torch and other dependencies.")