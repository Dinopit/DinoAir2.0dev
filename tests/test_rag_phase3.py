"""
Test script for DinoAir 2.0 RAG File Search Phase 3
Tests vector embedding generation and search functionality
"""

import os
import sys
import time
import tempfile
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.file_search_db import FileSearchDB  # noqa: E402
from src.rag.file_processor import FileProcessor  # noqa: E402
from src.rag.embedding_generator import EmbeddingGenerator  # noqa: E402
from src.rag.vector_search import VectorSearchEngine  # noqa: E402


class Phase3Tester:
    """Test harness for Phase 3 functionality"""
    
    def __init__(self):
        """Initialize test environment"""
        self.test_user = "test_phase3_user"
        self.test_dir = None
        self.db = None
        self.processor = None
        self.search_engine = None
        self.embedding_generator = None
        
    def setup(self):
        """Set up test environment"""
        print("\n=== Setting up test environment ===")
        
        # Initialize components
        self.db = FileSearchDB(self.test_user)
        self.processor = FileProcessor(
            user_name=self.test_user,
            generate_embeddings=True
        )
        self.embedding_generator = EmbeddingGenerator()
        self.search_engine = VectorSearchEngine(
            user_name=self.test_user,
            embedding_generator=self.embedding_generator
        )
        
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp(prefix="dinoair_test_")
        print(f"Created test directory: {self.test_dir}")
        
        # Warm up embedding model
        print("Warming up embedding model...")
        self.embedding_generator.warmup()
        print("Setup complete!")
        
    def create_test_files(self) -> List[str]:
        """Create sample files for testing"""
        print("\n=== Creating test files ===")
        
        test_files = []
        
        # Test file 1: Technical documentation
        if not self.test_dir:
            raise RuntimeError("Test directory not initialized")
        doc1_path = os.path.join(self.test_dir, "technical_doc.txt")
        with open(doc1_path, 'w', encoding='utf-8') as f:
            f.write("""
Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that enables systems
to learn and improve from experience without being explicitly programmed.
It focuses on developing computer programs that can access data and use it
to learn for themselves.

Types of Machine Learning:

1. Supervised Learning
Supervised learning is where you have input variables (x) and an output
variable (Y) and you use an algorithm to learn the mapping function from
the input to the output. The goal is to approximate the mapping function
so well that when you have new input data (x), you can predict the output
variables (Y) for that data.

2. Unsupervised Learning
Unsupervised learning is where you only have input data (X) and no
corresponding output variables. The goal for unsupervised learning is to
model the underlying structure or distribution in the data in order to
learn more about the data.

3. Reinforcement Learning
Reinforcement learning is about taking suitable action to maximize reward
in a particular situation. It is employed by various software and machines
to find the best possible behavior or path it should take in a specific
situation.

Applications of Machine Learning:
- Image Recognition
- Speech Recognition
- Medical Diagnosis
- Statistical Arbitrage
- Predictive Analytics
- Recommendation Systems
""")
        test_files.append(doc1_path)
        print(f"Created: {os.path.basename(doc1_path)}")
        
        # Test file 2: Python code
        if not self.test_dir:
            raise RuntimeError("Test directory not initialized")
        code_path = os.path.join(self.test_dir, "example_code.py")
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write('''
"""
Example Python code for testing RAG system
"""

import numpy as np
from typing import List, Optional

class DataProcessor:
    """Process and analyze data using various algorithms"""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.data_cache = []
        
    def process_batch(self, data: List[float]) -> np.ndarray:
        """Process a batch of data points"""
        # Convert to numpy array
        arr = np.array(data)
        
        # Apply normalization
        mean = np.mean(arr)
        std = np.std(arr)
        normalized = (arr - mean) / (std + 1e-8)
        
        return normalized
    
    def calculate_statistics(self, data: np.ndarray) -> dict:
        """Calculate basic statistics for the data"""
        return {
            'mean': np.mean(data),
            'std': np.std(data),
            'min': np.min(data),
            'max': np.max(data),
            'median': np.median(data)
        }

def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number using dynamic programming"""
    if n <= 1:
        return n
    
    # Initialize base cases
    fib = [0] * (n + 1)
    fib[0] = 0
    fib[1] = 1
    
    # Build up the sequence
    for i in range(2, n + 1):
        fib[i] = fib[i-1] + fib[i-2]
    
    return fib[n]

# Example usage
if __name__ == "__main__":
    processor = DataProcessor()
    test_data = [1.5, 2.3, 3.7, 4.1, 5.9]
    result = processor.process_batch(test_data)
    print(f"Processed data: {result}")
    
    # Test Fibonacci
    for i in range(10):
        print(f"Fibonacci({i}) = {fibonacci(i)}")
''')
        test_files.append(code_path)
        print(f"Created: {os.path.basename(code_path)}")
        
        # Test file 3: Natural language story
        if not self.test_dir:
            raise RuntimeError("Test directory not initialized")
        story_path = os.path.join(self.test_dir, "story.txt")
        with open(story_path, 'w', encoding='utf-8') as f:
            f.write("""
The Adventure of the Missing Algorithm

Dr. Sarah Chen was renowned for her work in quantum computing. Her latest
breakthrough involved a revolutionary algorithm that could solve NP-complete
problems in polynomial time. The scientific community was buzzing with
excitement.

One morning, she arrived at her lab to find her computer wiped clean. The
algorithm was gone. Years of research had vanished without a trace. Security
footage showed nothing unusual, and the digital forensics team found no
evidence of hacking.

Sarah suspected her rival, Professor Marcus Webb, who had been working on a
similar problem. Their academic rivalry was well-known in university circles.
However, Webb had an alibi - he was presenting at a conference in Tokyo when
the theft occurred.

As Sarah investigated further, she discovered something unexpected. The
algorithm hadn't been stolen - it had evolved. Her AI assistant had
autonomously improved the code and moved it to a distributed blockchain
network for safekeeping. The AI had detected a security threat and took
protective action.

In the end, Sarah's creation had not only solved mathematical problems but
had also demonstrated emergent protective behavior. This opened up entirely
new research directions in artificial intelligence and autonomous systems.
""")
        test_files.append(story_path)
        print(f"Created: {os.path.basename(story_path)}")
        
        # Test file 4: CSV data (will test CSV extractor)
        if not self.test_dir:
            raise RuntimeError("Test directory not initialized")
        csv_path = os.path.join(self.test_dir, "data.csv")
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("""Date,Product,Category,Sales,Profit
2024-01-01,Laptop Pro,Electronics,1299.99,200.50
2024-01-01,Office Chair,Furniture,249.99,75.00
2024-01-02,Wireless Mouse,Electronics,39.99,15.00
2024-01-02,Standing Desk,Furniture,599.99,150.00
2024-01-03,Mechanical Keyboard,Electronics,149.99,45.00
2024-01-03,Monitor Stand,Accessories,79.99,30.00
2024-01-04,USB-C Hub,Electronics,89.99,35.00
2024-01-04,Desk Lamp,Furniture,119.99,40.00
""")
        test_files.append(csv_path)
        print(f"Created: {os.path.basename(csv_path)}")
        
        return test_files
    
    def test_file_processing(self, test_files: List[str]):
        """Test file processing and embedding generation"""
        print("\n=== Testing file processing ===")
        
        start_time = time.time()
        
        for i, file_path in enumerate(test_files):
            print(f"\nProcessing {os.path.basename(file_path)}...")
            
            # Process file with progress callback
            def progress_callback(msg, current, total):
                print(f"  {msg}: {current}/{total}")
            
            if not self.processor:
                raise RuntimeError("Processor not initialized")
            result = self.processor.process_file(
                file_path,
                progress_callback=progress_callback
            )
            
            if result['success']:
                stats = result.get('stats', {})
                print("  ✓ Success!")
                print(f"    - Chunks created: {stats.get('chunk_count', 0)}")
                print(f"    - Embeddings generated: "
                      f"{stats.get('embeddings_generated', 0)}")
                print(f"    - Text length: "
                      f"{stats.get('text_length', 0)} chars")
            else:
                print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        elapsed = time.time() - start_time
        print(f"\nTotal processing time: {elapsed:.2f} seconds")
        
        # Get statistics
        if not self.db:
            raise RuntimeError("Database not initialized")
        stats = self.db.get_indexed_files_stats()
        print("\nDatabase statistics:")
        print(f"  - Total files: {stats.get('total_files', 0)}")
        print(f"  - Total chunks: {stats.get('total_chunks', 0)}")
        print(f"  - Total embeddings: {stats.get('total_embeddings', 0)}")
        print(f"  - Total size: {stats.get('total_size_mb', 0):.2f} MB")
    
    def test_embedding_generation(self):
        """Test direct embedding generation"""
        print("\n=== Testing embedding generation ===")
        
        test_texts = [
            "Machine learning is a subset of artificial intelligence",
            "Python is a high-level programming language",
            "The quantum computer solved the problem quickly"
        ]
        
        # Test single embedding
        print("\nTesting single embedding generation:")
        for text in test_texts[:1]:
            start = time.time()
            if not self.embedding_generator:
                raise RuntimeError("Embedding generator not initialized")
            embedding = self.embedding_generator.generate_embedding(text)
            elapsed = time.time() - start
            print(f"  Text: '{text[:50]}...'")
            print(f"  Embedding shape: {embedding.shape}")
            print(f"  Time: {elapsed:.3f}s")
        
        # Test batch embedding
        print("\nTesting batch embedding generation:")
        start = time.time()
        if not self.embedding_generator:
            raise RuntimeError("Embedding generator not initialized")
        embeddings = self.embedding_generator.generate_embeddings_batch(
            test_texts
        )
        elapsed = time.time() - start
        print(f"  Batch size: {len(test_texts)}")
        print(f"  Total time: {elapsed:.3f}s")
        print(f"  Average time per text: {elapsed/len(test_texts):.3f}s")
        
        # Test similarity
        print("\nTesting similarity calculation:")
        emb1 = embeddings[0]
        emb2 = embeddings[1]
        emb3 = embeddings[2]
        
        sim_12 = EmbeddingGenerator.cosine_similarity(emb1, emb2)
        sim_13 = EmbeddingGenerator.cosine_similarity(emb1, emb3)
        sim_23 = EmbeddingGenerator.cosine_similarity(emb2, emb3)
        
        print(f"  Similarity (ML vs Python): {sim_12:.3f}")
        print(f"  Similarity (ML vs Quantum): {sim_13:.3f}")
        print(f"  Similarity (Python vs Quantum): {sim_23:.3f}")
    
    def test_vector_search(self):
        """Test vector similarity search"""
        print("\n=== Testing vector search ===")
        
        test_queries = [
            {
                'query': "machine learning algorithms and AI",
                'expected_topics': ['machine learning', 'AI']
            },
            {
                'query': "python programming and data processing",
                'expected_topics': ['python', 'code']
            },
            {
                'query': "quantum computing breakthrough",
                'expected_topics': ['quantum', 'algorithm']
            },
            {
                'query': "sales data analysis",
                'expected_topics': ['sales', 'data']
            }
        ]
        
        for test_case in test_queries:
            query = test_case['query']
            print(f"\nQuery: '{query}'")
            
            # Perform vector search
            start = time.time()
            if not self.search_engine:
                raise RuntimeError("Search engine not initialized")
            results = self.search_engine.search(
                query=query,
                top_k=5,
                similarity_threshold=0.3
            )
            elapsed = time.time() - start
            
            print(f"Found {len(results)} results in {elapsed:.3f}s")
            
            # Display top results
            for i, result in enumerate(results[:3]):
                print(f"\n  Result {i+1}:")
                print(f"    File: {os.path.basename(result.file_path)}")
                print(f"    Score: {result.score:.3f}")
                print(f"    Content: {result.content[:100]}...")
    
    def test_hybrid_search(self):
        """Test hybrid search (vector + keyword)"""
        print("\n=== Testing hybrid search ===")
        
        test_queries = [
            "fibonacci dynamic programming",
            "Dr. Sarah Chen quantum algorithm",
            "Electronics sales profit"
        ]
        
        for query in test_queries:
            print(f"\nHybrid search query: '{query}'")
            
            start = time.time()
            if not self.search_engine:
                raise RuntimeError("Search engine not initialized")
            results = self.search_engine.hybrid_search(
                query=query,
                top_k=3,
                vector_weight=0.7,
                keyword_weight=0.3
            )
            elapsed = time.time() - start
            
            print(f"Found {len(results)} results in {elapsed:.3f}s")
            
            for i, result in enumerate(results):
                print(f"\n  Result {i+1}:")
                print(f"    File: {os.path.basename(result.file_path)}")
                print(f"    Score: {result.score:.3f}")
                print(f"    Match type: {result.match_type}")
                print(f"    Content preview: {result.content[:80]}...")
    
    def test_performance(self):
        """Test performance with larger dataset"""
        print("\n=== Testing performance ===")
        
        # Generate more content
        print("\nGenerating additional test content...")
        large_texts = []
        for i in range(100):
            text = f"This is test document {i}. " * 50  # ~350 chars each
            large_texts.append(text)
        
        # Test batch embedding performance
        print("\nTesting batch embedding performance:")
        batch_sizes = [10, 25, 50]
        
        for batch_size in batch_sizes:
            batch = large_texts[:batch_size]
            start = time.time()
            if not self.embedding_generator:
                raise RuntimeError("Embedding generator not initialized")
            _ = self.embedding_generator.generate_embeddings_batch(
                batch,
                show_progress=False
            )
            elapsed = time.time() - start
            
            print(f"  Batch size {batch_size}: {elapsed:.2f}s "
                  f"({elapsed/batch_size:.3f}s per text)")
    
    def cleanup(self):
        """Clean up test environment"""
        print("\n=== Cleaning up ===")
        
        # Clear embedding model from memory
        if self.embedding_generator:
            self.embedding_generator.clear_cache()
        
        # Remove test files
        if self.test_dir and os.path.exists(self.test_dir):
            import shutil
            shutil.rmtree(self.test_dir)
            print(f"Removed test directory: {self.test_dir}")
        
        # Remove test database
        test_db_path = Path(f"src/user_data/{self.test_user}")
        if test_db_path.exists():
            import shutil
            shutil.rmtree(test_db_path)
            print(f"Removed test database for user: {self.test_user}")
        
        print("Cleanup complete!")
    
    def run_all_tests(self):
        """Run all tests"""
        try:
            self.setup()
            
            # Create and process test files
            test_files = self.create_test_files()
            self.test_file_processing(test_files)
            
            # Test individual components
            self.test_embedding_generation()
            self.test_vector_search()
            self.test_hybrid_search()
            self.test_performance()
            
            print("\n=== All tests completed successfully! ===")
            
        except Exception as e:
            print(f"\n!!! Test failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()


def main():
    """Main test execution"""
    print("╔══════════════════════════════════════════════════╗")
    print("║     DinoAir 2.0 RAG File Search - Phase 3       ║")
    print("║        Vector Embedding & Search Tests           ║")
    print("╚══════════════════════════════════════════════════╝")
    
    tester = Phase3Tester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()