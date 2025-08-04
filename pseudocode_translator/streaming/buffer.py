"""
Buffer management for streaming operations

This module provides efficient buffer management for streaming translations,
including memory-efficient storage, compression, and retrieval of chunks.
"""

import io
import gzip
import json
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import OrderedDict
import logging
import sys

logger = logging.getLogger(__name__)


@dataclass
class BufferConfig:
    """Configuration for stream buffer"""
    max_size_mb: int = 100  # Maximum buffer size in MB
    enable_compression: bool = True  # Enable chunk compression
    compression_level: int = 6  # gzip compression level (1-9)
    eviction_policy: str = "lru"  # lru or fifo
    enable_persistence: bool = False  # Save to disk
    persistence_path: Optional[str] = None


class BufferEntry:
    """Single entry in the buffer"""
    
    def __init__(self, data: Any, compressed: bool = False):
        """
        Initialize buffer entry
        
        Args:
            data: Data to store
            compressed: Whether data is compressed
        """
        self.data = data
        self.compressed = compressed
        self.size = self._calculate_size()
        self.access_count = 0
        
    def _calculate_size(self) -> int:
        """Calculate size of data in bytes"""
        if isinstance(self.data, bytes):
            return len(self.data)
        elif isinstance(self.data, str):
            return len(self.data.encode('utf-8'))
        else:
            # Estimate size for complex objects
            return sys.getsizeof(self.data)
    
    def get_data(self, decompress: bool = True) -> Any:
        """
        Get data from entry
        
        Args:
            decompress: Whether to decompress if compressed
            
        Returns:
            Stored data
        """
        self.access_count += 1
        
        if self.compressed and decompress:
            return self._decompress(self.data)
        return self.data
    
    def _decompress(self, data: bytes) -> Any:
        """Decompress data"""
        try:
            decompressed = gzip.decompress(data)
            return json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            logger.error(f"Decompression error: {e}")
            return None


class StreamBuffer:
    """
    Memory-efficient buffer for streaming operations
    """
    
    def __init__(self, config: Optional[BufferConfig] = None):
        """
        Initialize stream buffer
        
        Args:
            config: Buffer configuration
        """
        self.config = config or BufferConfig()
        self._buffer: OrderedDict[int, BufferEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_size = 0
        # Convert MB to bytes
        self._max_size = self.config.max_size_mb * 1024 * 1024
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'compressions': 0
        }
    
    def add_chunk(self, chunk_index: int, data: Any) -> bool:
        """
        Add a chunk to the buffer
        
        Args:
            chunk_index: Index of the chunk
            data: Data to store
            
        Returns:
            True if successfully added
        """
        with self._lock:
            # Prepare data for storage
            stored_data = data
            compressed = False
            
            if self.config.enable_compression:
                compressed_data = self._compress(data)
                if (compressed_data and
                        len(compressed_data) < sys.getsizeof(data) * 0.8):
                    stored_data = compressed_data
                    compressed = True
                    self._stats['compressions'] += 1
            
            # Create entry
            entry = BufferEntry(stored_data, compressed)
            
            # Check if we need to evict
            while self._current_size + entry.size > self._max_size:
                if not self._evict_entry():
                    logger.warning("Cannot evict more entries, buffer full")
                    return False
            
            # Add to buffer
            if chunk_index in self._buffer:
                # Remove old entry size
                old_entry = self._buffer[chunk_index]
                self._current_size -= old_entry.size
            
            self._buffer[chunk_index] = entry
            self._current_size += entry.size
            
            # Move to end (for LRU)
            if self.config.eviction_policy == "lru":
                self._buffer.move_to_end(chunk_index)
            
            return True
    
    def get_chunk(self, chunk_index: int) -> Optional[Any]:
        """
        Get a chunk from the buffer
        
        Args:
            chunk_index: Index of the chunk
            
        Returns:
            Chunk data or None if not found
        """
        with self._lock:
            if chunk_index in self._buffer:
                self._stats['hits'] += 1
                entry = self._buffer[chunk_index]
                
                # Update LRU order
                if self.config.eviction_policy == "lru":
                    self._buffer.move_to_end(chunk_index)
                
                return entry.get_data()
            else:
                self._stats['misses'] += 1
                return None
    
    def get_chunks_range(self, start: int, end: int) -> List[Any]:
        """
        Get a range of chunks
        
        Args:
            start: Start index (inclusive)
            end: End index (exclusive)
            
        Returns:
            List of chunk data
        """
        chunks = []
        for i in range(start, end):
            chunk = self.get_chunk(i)
            if chunk is not None:
                chunks.append(chunk)
        return chunks
    
    def remove_chunk(self, chunk_index: int) -> bool:
        """
        Remove a chunk from the buffer
        
        Args:
            chunk_index: Index of the chunk
            
        Returns:
            True if removed
        """
        with self._lock:
            if chunk_index in self._buffer:
                entry = self._buffer.pop(chunk_index)
                self._current_size -= entry.size
                return True
            return False
    
    def clear(self):
        """Clear all chunks from buffer"""
        with self._lock:
            self._buffer.clear()
            self._current_size = 0
    
    def get_size(self) -> int:
        """Get current buffer size in bytes"""
        return self._current_size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get buffer statistics"""
        with self._lock:
            return {
                **self._stats,
                'size': self._current_size,
                'chunks': len(self._buffer),
                'hit_rate': (self._stats['hits'] /
                             max(1, self._stats['hits'] +
                                 self._stats['misses']))
            }
    
    def _compress(self, data: Any) -> Optional[bytes]:
        """
        Compress data
        
        Args:
            data: Data to compress
            
        Returns:
            Compressed data or None if failed
        """
        try:
            # Convert to JSON string first
            json_str = json.dumps(data, default=str)
            json_bytes = json_str.encode('utf-8')
            
            # Compress
            compressed = gzip.compress(
                json_bytes, 
                compresslevel=self.config.compression_level
            )
            
            return compressed
        except Exception as e:
            logger.error(f"Compression error: {e}")
            return None
    
    def _evict_entry(self) -> bool:
        """
        Evict an entry based on policy
        
        Returns:
            True if entry was evicted
        """
        if not self._buffer:
            return False
        
        # Get key to evict based on policy
        if self.config.eviction_policy == "lru":
            # Evict least recently used (first item)
            key_to_evict = next(iter(self._buffer))
        else:  # fifo
            # Evict first in (first item)
            key_to_evict = next(iter(self._buffer))
        
        entry = self._buffer.pop(key_to_evict)
        self._current_size -= entry.size
        self._stats['evictions'] += 1
        
        logger.debug(f"Evicted chunk {key_to_evict}, freed {entry.size} bytes")
        return True
    
    def persist_to_disk(self, path: Optional[str] = None):
        """
        Persist buffer to disk
        
        Args:
            path: Path to save to (uses config path if not provided)
        """
        if not self.config.enable_persistence:
            return
        
        save_path = path or self.config.persistence_path
        if not save_path:
            logger.warning("No persistence path configured")
            return
        
        try:
            with self._lock:
                # Prepare data for saving
                save_data = {}
                for chunk_index, entry in self._buffer.items():
                    save_data[str(chunk_index)] = {
                        'data': entry.data,
                        'compressed': entry.compressed
                    }
                
                # Save to file
                with gzip.open(save_path, 'wt', encoding='utf-8') as f:
                    json.dump(save_data, f)
                
                logger.info(
                    f"Persisted {len(save_data)} chunks to {save_path}"
                )
                
        except Exception as e:
            logger.error(f"Error persisting buffer: {e}")
    
    def load_from_disk(self, path: Optional[str] = None) -> bool:
        """
        Load buffer from disk
        
        Args:
            path: Path to load from (uses config path if not provided)
            
        Returns:
            True if loaded successfully
        """
        load_path = path or self.config.persistence_path
        if not load_path:
            return False
        
        try:
            with gzip.open(load_path, 'rt', encoding='utf-8') as f:
                save_data = json.load(f)
            
            with self._lock:
                self.clear()
                
                for chunk_index_str, entry_data in save_data.items():
                    chunk_index = int(chunk_index_str)
                    entry = BufferEntry(
                        entry_data['data'],
                        entry_data['compressed']
                    )
                    self._buffer[chunk_index] = entry
                    self._current_size += entry.size
                
                logger.info(f"Loaded {len(save_data)} chunks from {load_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading buffer: {e}")
            return False


class ContextBuffer:
    """
    Specialized buffer for maintaining translation context
    """
    
    def __init__(self, window_size: int = 1024):
        """
        Initialize context buffer
        
        Args:
            window_size: Size of context window in characters
        """
        self.window_size = window_size
        self._buffer = io.StringIO()
        self._lock = threading.Lock()
    
    def add_context(self, text: str):
        """Add text to context buffer"""
        with self._lock:
            self._buffer.write(text)
            self._buffer.write('\n')
            
            # Trim if too large
            content = self._buffer.getvalue()
            if len(content) > self.window_size * 2:
                # Keep last window_size characters
                self._buffer = io.StringIO()
                self._buffer.write(content[-self.window_size:])
    
    def get_context(self) -> str:
        """Get current context"""
        with self._lock:
            content = self._buffer.getvalue()
            return content[-self.window_size:] if content else ""
    
    def clear(self):
        """Clear context buffer"""
        with self._lock:
            self._buffer = io.StringIO()