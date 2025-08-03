# RAG File Search System - Developer Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Extension Points](#extension-points)
4. [API Reference](#api-reference)
5. [Testing Guidelines](#testing-guidelines)
6. [Performance Considerations](#performance-considerations)
7. [Security Model](#security-model)
8. [Contributing](#contributing)

---

## Architecture Overview

The RAG (Retrieval-Augmented Generation) File Search system is built with a modular architecture that separates concerns and allows for extensibility.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         GUI Layer                           │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Search      │  │ Indexing     │  │ Directory       │  │
│  │ Results     │  │ Status       │  │ Limiter         │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Context Provider                        │
│         Orchestrates search and provides context            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                         RAG Core                            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ File        │  │ Vector       │  │ Text            │  │
│  │ Processor   │  │ Search       │  │ Extractors      │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ File        │  │ Embedding    │  │ Directory       │  │
│  │ Chunker     │  │ Generator    │  │ Validator       │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ File Search │  │ Indexed      │  │ Embeddings      │  │
│  │ DB          │  │ Files        │  │ Storage         │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Modularity**: Each component has a single responsibility
2. **Extensibility**: Easy to add new file types and extractors
3. **Performance**: Parallel processing, caching, and optimizations
4. **Security**: Directory access controls and input validation
5. **Local-First**: All processing happens locally, no cloud dependencies

---

## Core Components

### 1. File Processor (`file_processor.py`)

The orchestrator for file indexing operations.

```python
class FileProcessor:
    """
    Orchestrates the file processing pipeline:
    1. File validation and metadata extraction
    2. Text extraction using appropriate extractor
    3. Text chunking with configurable strategies
    4. Storage in the file search database
    """
    
    def process_file(self, file_path: str, 
                     force_reprocess: bool = False) -> Dict[str, Any]:
        """Process a single file through the extraction pipeline"""
        
    def process_directory(self, directory_path: str,
                          recursive: bool = True) -> Dict[str, Any]:
        """Process all files in a directory"""
```

**Key Features:**
- Configurable chunk size and overlap
- Parallel directory processing
- Progress callbacks
- File type detection
- Duplicate detection via file hashing

### 2. Text Extractors (`text_extractors.py`)

Modular system for extracting text from various file formats.

```python
class BaseExtractor(ABC):
    """Abstract base class for all text extractors"""
    
    @abstractmethod
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from file"""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        pass

class ExtractorFactory:
    """Factory for creating appropriate extractors"""
    
    def get_extractor(self, file_path: str) -> Optional[BaseExtractor]:
        """Get appropriate extractor for file type"""
```

**Built-in Extractors:**
- `PlainTextExtractor`: .txt, .md, .log files
- `PDFExtractor`: PDF documents (using PyPDF2)
- `DocxExtractor`: Word documents
- `CodeExtractor`: Source code files with syntax awareness

### 3. File Chunker (`file_chunker.py`)

Intelligent text chunking with various strategies.

```python
class FileChunker:
    """Chunks text into smaller pieces for embedding"""
    
    def chunk_text(self, text: str, 
                   respect_boundaries: bool = True) -> List[TextChunk]:
        """Default chunking with sentence boundary respect"""
        
    def chunk_by_paragraphs(self, text: str) -> List[TextChunk]:
        """Chunk text by paragraph boundaries"""
        
    def chunk_by_sentences(self, text: str) -> List[TextChunk]:
        """Chunk text by sentence boundaries"""
        
    def chunk_code(self, code: str, language: str) -> List[TextChunk]:
        """Language-aware code chunking"""
```

**Chunking Strategies:**
- Size-based with overlap
- Paragraph-based (for documents)
- Sentence-based (for precise content)
- Code-aware (respects function boundaries)

### 4. Vector Search Engine (`vector_search.py`)

Semantic search implementation with hybrid capabilities.

```python
class VectorSearchEngine:
    """Handles vector similarity search and hybrid search"""
    
    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Perform vector similarity search"""
        
    def keyword_search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Perform keyword-based search"""
        
    def hybrid_search(self, query: str, top_k: int = 10,
                      vector_weight: float = 0.7) -> List[SearchResult]:
        """Combine vector and keyword search"""
```

**Search Features:**
- Cosine similarity for semantic matching
- BM25-style keyword matching
- Result reranking
- Score normalization

### 5. Embedding Generator (`embedding_generator.py`)

Generates vector embeddings for text chunks.

```python
class EmbeddingGenerator:
    """Generates embeddings using sentence-transformers"""
    
    def generate_embedding(self, text: str, 
                           normalize: bool = True) -> np.ndarray:
        """Generate embedding for single text"""
        
    def generate_embeddings_batch(self, texts: List[str],
                                  batch_size: int = 32) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
```

**Embedding Models:**
- Default: `all-MiniLM-L6-v2` (384 dimensions)
- Configurable model selection
- GPU acceleration support
- Batch processing

### 6. Context Provider (`context_provider.py`)

Bridges RAG search with the application.

```python
class ContextProvider:
    """Provides context from indexed files for chat queries"""
    
    def get_context_for_query(self, query: str,
                              max_results: int = 5) -> List[Dict[str, Any]]:
        """Get relevant file context for a query"""
        
    def format_context_for_chat(self, context_items: List[Dict[str, Any]]) -> str:
        """Format context for inclusion in chat prompts"""
```

### 7. Directory Validator (`directory_validator.py`)

Security component for path validation.

```python
class DirectoryValidator:
    """Validates and controls directory access"""
    
    def validate_path(self, path: str) -> Dict[str, Any]:
        """Validate if path is allowed for indexing"""
        
    def set_allowed_directories(self, directories: List[str]) -> None:
        """Set list of allowed directories"""
        
    def set_excluded_directories(self, directories: List[str]) -> None:
        """Set list of excluded directories"""
```

---

## Extension Points

### Adding a New File Type Extractor

1. Create a new extractor class:

```python
# src/rag/extractors/excel_extractor.py
from typing import Dict, Any, List
from ..text_extractors import BaseExtractor
import pandas as pd

class ExcelExtractor(BaseExtractor):
    """Extract text from Excel files"""
    
    def __init__(self, max_file_size: int):
        self.max_file_size = max_file_size
    
    def extract_text(self, file_path: str) -> Dict[str, Any]:
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Convert to text
            text = df.to_string()
            
            return {
                'success': True,
                'text': text,
                'metadata': {
                    'sheets': len(df) if hasattr(df, '__len__') else 1,
                    'rows': len(df),
                    'columns': len(df.columns)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_supported_extensions(self) -> List[str]:
        return ['.xlsx', '.xls']
```

2. Register with ExtractorFactory:

```python
# In text_extractors.py ExtractorFactory.__init__
self._extractors['.xlsx'] = ExcelExtractor(self.max_file_size)
self._extractors['.xls'] = ExcelExtractor(self.max_file_size)
```

### Adding a New Chunking Strategy

```python
# In file_chunker.py
def chunk_by_custom_delimiter(self, text: str, delimiter: str) -> List[TextChunk]:
    """Chunk text by custom delimiter"""
    chunks = []
    parts = text.split(delimiter)
    
    current_pos = 0
    for i, part in enumerate(parts):
        if not part.strip():
            continue
            
        chunk = TextChunk(
            content=part.strip(),
            metadata=ChunkMetadata(
                start_pos=current_pos,
                end_pos=current_pos + len(part),
                chunk_index=len(chunks),
                chunk_type='custom_delimiter'
            )
        )
        chunks.append(chunk)
        current_pos += len(part) + len(delimiter)
    
    return chunks
```

### Custom Embedding Models

```python
# In embedding_generator.py
def set_model(self, model_name: str) -> None:
    """Change the embedding model"""
    self.model = SentenceTransformer(model_name)
    self.model_name = model_name
    self.embedding_dim = self.model.get_sentence_embedding_dimension()
```

---

## API Reference

### FileProcessor API

```python
# Initialize processor
processor = FileProcessor(
    user_name="default_user",
    chunk_size=1000,
    chunk_overlap=200,
    generate_embeddings=True
)

# Process single file
result = processor.process_file(
    file_path="/path/to/document.pdf",
    force_reprocess=False,
    progress_callback=lambda msg, current, total: print(f"{msg}: {current}/{total}")
)

# Process directory
result = processor.process_directory(
    directory_path="/path/to/documents",
    recursive=True,
    file_extensions=['.pdf', '.txt', '.docx'],
    force_reprocess=False
)

# Update settings
processor.update_settings(
    chunk_size=500,
    max_file_size=100 * 1024 * 1024  # 100MB
)
```

### VectorSearchEngine API

```python
# Initialize search engine
search = VectorSearchEngine(user_name="default_user")

# Vector search
results = search.search(
    query="machine learning algorithms",
    top_k=10,
    similarity_threshold=0.5,
    file_types=['pdf', 'txt']
)

# Keyword search
results = search.keyword_search(
    query="neural network",
    top_k=10
)

# Hybrid search
results = search.hybrid_search(
    query="deep learning tutorial",
    top_k=10,
    vector_weight=0.7,
    keyword_weight=0.3,
    rerank=True
)

# Batch search
queries = ["python", "machine learning", "data science"]
all_results = search.batch_search(
    queries=queries,
    top_k=5,
    search_type='hybrid'
)
```

### ContextProvider API

```python
# Initialize context provider
context = ContextProvider(user_name="default_user")

# Get context for query
context_items = context.get_context_for_query(
    query="How to implement sorting algorithms?",
    file_types=['py', 'md'],
    max_results=5
)

# Format for chat
formatted = context.format_context_for_chat(
    context_items,
    include_metadata=True
)

# Get file summary
summary = context.get_file_summary("/path/to/file.pdf")

# Find related files
related = context.search_related_files(
    file_path="/path/to/file.pdf",
    top_k=5
)
```

### Database API

```python
# Initialize database
db = FileSearchDB(user_name="default_user")

# Add indexed file
result = db.add_indexed_file(
    file_path="/path/to/file.pdf",
    file_hash="abc123...",
    size=1024000,
    modified_date=datetime.now(),
    file_type="pdf",
    metadata={"pages": 50}
)

# Add chunk
result = db.add_chunk(
    file_id="file123",
    chunk_index=0,
    content="This is the chunk content...",
    start_pos=0,
    end_pos=500,
    metadata={"chunk_type": "paragraph"}
)

# Add embedding
result = db.add_embedding(
    chunk_id="chunk123",
    embedding_vector=[0.1, 0.2, ...],  # 384 dimensions
    model_name="all-MiniLM-L6-v2"
)

# Search by keywords
results = db.search_by_keywords(
    keywords=["python", "programming"],
    limit=20,
    file_types=['py', 'md']
)
```

---

## Testing Guidelines

### Unit Testing

Each component should have comprehensive unit tests:

```python
# test_file_processor.py
class TestFileProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = FileProcessor(user_name="test_user")
        self.test_dir = tempfile.mkdtemp()
    
    def test_process_single_file(self):
        # Create test file
        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Process file
        result = self.processor.process_file(test_file)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['file_id'])
        self.assertGreater(len(result['chunks']), 0)
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)
```

### Integration Testing

Test component interactions:

```python
# test_rag_integration.py
class TestRAGIntegration(unittest.TestCase):
    def test_full_pipeline(self):
        # Index files
        processor = FileProcessor(user_name="test_user")
        processor.process_directory("/test/data")
        
        # Search
        search = VectorSearchEngine(user_name="test_user")
        results = search.hybrid_search("test query")
        
        # Get context
        context = ContextProvider(user_name="test_user")
        context_items = context.get_context_for_query("test query")
        
        # Verify pipeline
        self.assertGreater(len(results), 0)
        self.assertGreater(len(context_items), 0)
```

### Performance Testing

```python
# test_performance.py
class TestPerformance(unittest.TestCase):
    def test_large_file_processing(self):
        # Create 10MB file
        large_file = self._create_large_file(10 * 1024 * 1024)
        
        start_time = time.time()
        result = self.processor.process_file(large_file)
        processing_time = time.time() - start_time
        
        self.assertTrue(result['success'])
        self.assertLess(processing_time, 30)  # Should process in < 30s
    
    def test_concurrent_search(self):
        # Run multiple searches concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.search.search, f"query {i}")
                for i in range(50)
            ]
            
            results = [f.result() for f in futures]
            self.assertEqual(len(results), 50)
```

### Security Testing

```python
# test_security.py
class TestSecurity(unittest.TestCase):
    def test_path_traversal_prevention(self):
        validator = DirectoryValidator()
        
        # Test various attacks
        attacks = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/etc/passwd"
        ]
        
        for attack in attacks:
            result = validator.validate_path(attack)
            self.assertFalse(result['valid'])
    
    def test_input_sanitization(self):
        # Test SQL injection prevention
        malicious_query = "'; DROP TABLE files; --"
        results = self.search.search(malicious_query)
        # Should handle gracefully
        self.assertIsInstance(results, list)
```

---

## Performance Considerations

### Optimization Strategies

1. **Parallel Processing**
   ```python
   # Use OptimizedFileProcessor for parallel processing
   processor = OptimizedFileProcessor(
       user_name="default_user",
       max_workers=4,  # Number of parallel workers
       cache_size=1000,
       enable_caching=True
   )
   ```

2. **Caching**
   - File hash caching to avoid re-reading
   - Embedding caching for repeated searches
   - Search result caching with TTL

3. **Batch Operations**
   ```python
   # Batch embedding generation
   embeddings = generator.generate_embeddings_batch(
       texts=chunk_texts,
       batch_size=32
   )
   
   # Batch database operations
   db.batch_add_embeddings(embeddings_data)
   ```

4. **Memory Management**
   ```python
   # Clear caches when needed
   processor.clear_caches()
   search.clear_cache()
   
   # Optimize for memory
   processor.optimize_for_memory()
   ```

### Benchmarks

Expected performance metrics:

| Operation | File Size | Expected Time |
|-----------|-----------|---------------|
| Text extraction (PDF) | 1MB | < 2s |
| Text extraction (DOCX) | 1MB | < 1s |
| Chunking | 10,000 words | < 0.5s |
| Embedding generation | 100 chunks | < 5s |
| Vector search | 10,000 chunks | < 0.1s |
| Hybrid search | 10,000 chunks | < 0.2s |

---

## Security Model

### Directory Access Control

```python
# Configure allowed directories
validator = DirectoryValidator()
validator.set_allowed_directories([
    "C:\\Users\\User\\Documents",
    "C:\\Projects"
])

validator.set_excluded_directories([
    "C:\\Users\\User\\Documents\\Private",
    "C:\\Windows",
    "C:\\Program Files"
])
```

### Input Validation

All user inputs are validated:

```python
# Query validation
is_valid, sanitized_query, error = validator.validate_query(user_query)

# File path validation
is_valid, error = validator.validate_file_path(file_path)

# File type validation
is_valid, sanitized_types, error = validator.validate_file_types(file_types)
```

### Security Best Practices

1. **Path Traversal Prevention**
   - Normalize all paths
   - Check for ".." sequences
   - Validate against allowed directories

2. **File Type Restrictions**
   - Whitelist allowed extensions
   - Verify MIME types when possible
   - Size limits enforcement

3. **Resource Limits**
   - Maximum file size (default: 50MB)
   - Maximum chunk size
   - Query length limits
   - Result count limits

---

## Contributing

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/dinoair2.0.git
   cd dinoair2.0
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Run tests**
   ```bash
   python -m pytest tests/
   python test_rag_complete.py --all
   ```

### Code Style

- Follow PEP 8
- Use type hints
- Document all public methods
- Write comprehensive docstrings

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Adding Features

When adding new features:

1. **Design First**
   - Document the feature design
   - Consider extensibility
   - Plan for testing

2. **Implementation**
   - Follow existing patterns
   - Add unit tests
   - Update documentation

3. **Testing**
   - Unit tests for new code
   - Integration tests if needed
   - Performance impact assessment

4. **Documentation**
   - Update API documentation
   - Add usage examples
   - Update changelog

---

## Troubleshooting

### Common Issues

**Issue: Slow indexing**
```python
# Solution: Adjust batch size and workers
processor = OptimizedFileProcessor(
    embedding_batch_size=64,  # Increase batch size
    max_workers=8  # Increase workers if CPU allows
)
```

**Issue: Out of memory**
```python
# Solution: Process in smaller batches
processor.update_settings(
    chunk_size=500,  # Smaller chunks
    embedding_batch_size=16  # Smaller batches
)
processor.optimize_for_memory()
```

**Issue: Poor search results**
```python
# Solution: Tune search parameters
results = search.hybrid_search(
    query=optimized_query,
    vector_weight=0.6,  # Adjust weights
    keyword_weight=0.4,
    rerank=True,
    similarity_threshold=0.3  # Lower threshold
)
```

---

*Last updated: July 2024 | Version 2.0*