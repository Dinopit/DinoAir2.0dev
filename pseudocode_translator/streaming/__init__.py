"""
Streaming support for the Pseudocode Translator

This module provides memory-efficient streaming capabilities for processing
large files through chunk-based processing while maintaining code quality
and respecting code boundaries.
"""

from .chunker import CodeChunker, ChunkConfig
from .pipeline import StreamingPipeline, StreamConfig
from .buffer import StreamBuffer, BufferConfig

__all__ = [
    'CodeChunker',
    'ChunkConfig',
    'StreamingPipeline',
    'StreamConfig',
    'StreamBuffer',
    'BufferConfig',
]

# Version info
__version__ = '1.0.0'