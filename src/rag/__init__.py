"""
RAG (Retrieval-Augmented Generation) File Search System for DinoAir 2.0

This module provides text extraction and chunking capabilities for various file formats
to support intelligent file search functionality.
"""

from .text_extractors import (
    BaseExtractor,
    TextFileExtractor,
    PDFExtractor,
    DocxExtractor,
    CodeFileExtractor,
    MarkdownExtractor,
    JSONExtractor,
    CSVExtractor,
    ExtractorFactory
)

from .file_chunker import (
    FileChunker,
    TextChunk,
    ChunkMetadata
)

from .file_processor import FileProcessor

__all__ = [
    # Extractors
    'BaseExtractor',
    'TextFileExtractor',
    'PDFExtractor',
    'DocxExtractor',
    'CodeFileExtractor',
    'MarkdownExtractor',
    'JSONExtractor',
    'CSVExtractor',
    'ExtractorFactory',
    # Chunker
    'FileChunker',
    'TextChunk',
    'ChunkMetadata',
    # Processor
    'FileProcessor'
]

__version__ = '1.0.0'