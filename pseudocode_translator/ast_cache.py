"""
AST Cache module for the Pseudocode Translator

Provides a thread-safe LRU cache with TTL, size limits, and persistent storage
for AST parsing results to improve performance by avoiding redundant parsing.
"""

import ast
import threading
import time
import pickle
import hashlib
import shutil
from collections import OrderedDict
from typing import Any, Optional, Union, Dict
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata"""
    ast_obj: Any
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def update_access(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_access = time.time()


class ASTCache:
    """
    Thread-safe LRU (Least Recently Used) cache for AST parsing results with:
    - TTL (Time-To-Live) based eviction
    - Size-based memory limits
    - Persistent disk storage
    - Comprehensive statistics
    """
    
    def __init__(
        self, 
        max_size: int = 100,
        ttl_seconds: Optional[float] = None,
        max_memory_mb: float = 100.0,
        persistent_path: Optional[Union[str, Path]] = None,
        enable_compression: bool = True
    ):
        """
        Initialize the AST cache.
        
        Args:
            max_size: Maximum number of entries to store (default: 100)
            ttl_seconds: Time-to-live for cache entries in seconds
                (None = no TTL)
            max_memory_mb: Maximum memory usage in MB (default: 100.0)
            persistent_path: Path for persistent cache storage
                (None = memory only)
            enable_compression: Enable compression for persistent storage
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.enable_compression = enable_compression
        
        # Cache storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_memory_usage = 0
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._ttl_evictions = 0
        self._size_evictions = 0
        
        # Persistent storage setup
        self.persistent_path = None
        if persistent_path:
            self.persistent_path = Path(persistent_path)
            self._setup_persistent_storage()
            self._load_from_disk()
        
        # Background cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        if ttl_seconds:
            self._start_cleanup_thread()
    
    def parse(
        self, 
        source: Union[str, bytes], 
        filename: str = '<unknown>', 
        mode: str = 'exec'
    ) -> Any:
        """
        Parse source code into an AST, using the cache when possible.
        
        Args:
            source: Source code to parse
            filename: Filename to use for error messages
            mode: Parsing mode ('exec', 'eval', or 'single')
            
        Returns:
            Parsed AST object
            
        Raises:
            SyntaxError: If the source code contains syntax errors
        """
        # Generate cache key
        cache_key = self._generate_cache_key(source, filename, mode)
        
        with self._lock:
            # Check if already in cache
            entry = self._get_valid_entry(cache_key)
            if entry:
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                entry.update_access()
                self._hits += 1
                return entry.ast_obj
            
            # Not in cache, parse it
            self._misses += 1
        
        # Parse outside the lock to avoid blocking
        try:
            ast_obj = ast.parse(source, filename, mode)
        except Exception:
            # Re-raise any parsing errors
            raise
        
        # Calculate size
        size_bytes = self._estimate_ast_size(ast_obj)
        
        # Create cache entry
        entry = CacheEntry(
            ast_obj=ast_obj,
            size_bytes=size_bytes
        )
        
        # Store in cache
        with self._lock:
            self._add_entry(cache_key, entry)
        
        return ast_obj
    
    def get(
        self, 
        source: Union[str, bytes], 
        filename: str = '<unknown>', 
        mode: str = 'exec'
    ) -> Optional[Any]:
        """
        Get a cached AST if available, without parsing.
        
        Args:
            source: Source code
            filename: Filename used when parsing
            mode: Parsing mode used
            
        Returns:
            Cached AST object if available, None otherwise
        """
        cache_key = self._generate_cache_key(source, filename, mode)
        
        with self._lock:
            entry = self._get_valid_entry(cache_key)
            if entry:
                # Move to end (most recently used)
                self._cache.move_to_end(cache_key)
                entry.update_access()
                self._hits += 1
                return entry.ast_obj
            
            self._misses += 1
            return None
    
    def put(
        self, 
        source: Union[str, bytes], 
        ast_obj: Any,
        filename: str = '<unknown>', 
        mode: str = 'exec'
    ) -> None:
        """
        Store an AST object in the cache.
        
        Args:
            source: Source code that was parsed
            ast_obj: The parsed AST object
            filename: Filename used when parsing
            mode: Parsing mode used
        """
        cache_key = self._generate_cache_key(source, filename, mode)
        size_bytes = self._estimate_ast_size(ast_obj)
        
        entry = CacheEntry(
            ast_obj=ast_obj,
            size_bytes=size_bytes
        )
        
        with self._lock:
            self._add_entry(cache_key, entry)
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._current_memory_usage = 0
            
        # Clear persistent storage if enabled
        if self.persistent_path and self.persistent_path.exists():
            try:
                shutil.rmtree(self.persistent_path)
                self._setup_persistent_storage()
            except Exception as e:
                logger.warning(f"Failed to clear persistent cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (
                (self._hits / total_requests * 100)
                if total_requests > 0 else 0.0
            )
            
            # Calculate average entry size
            avg_entry_size = (
                self._current_memory_usage / len(self._cache)
                if self._cache else 0
            )
            
            # Find hottest entries
            hot_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].access_count,
                reverse=True
            )[:5]
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'ttl_evictions': self._ttl_evictions,
                'size_evictions': self._size_evictions,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate, 2),
                'memory_usage_mb': round(
                    self._current_memory_usage / 1024 / 1024, 2
                ),
                'max_memory_mb': round(
                    self.max_memory_bytes / 1024 / 1024, 2
                ),
                'avg_entry_size_kb': round(avg_entry_size / 1024, 2),
                'ttl_enabled': self.ttl_seconds is not None,
                'ttl_seconds': self.ttl_seconds,
                'persistent_enabled': self.persistent_path is not None,
                'hot_entries': [
                    {
                        'key': key[:8] + '...',
                        'access_count': entry.access_count,
                        'size_kb': round(entry.size_bytes / 1024, 2)
                    }
                    for key, entry in hot_entries
                ]
            }
    
    def reset_stats(self) -> None:
        """Reset cache statistics without clearing the cache."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._ttl_evictions = 0
            self._size_evictions = 0
    
    def save_to_disk(self) -> bool:
        """
        Save current cache to disk.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.persistent_path:
            return False
        
        try:
            with self._lock:
                # Create temporary file
                temp_file = self.persistent_path / "cache.tmp"
                
                # Prepare data for serialization
                cache_data = {
                    'version': 1,
                    'entries': {},
                    'stats': {
                        'hits': self._hits,
                        'misses': self._misses,
                        'evictions': self._evictions
                    }
                }
                
                # Convert AST objects to serializable format
                for key, entry in self._cache.items():
                    try:
                        # Compile AST to code object for better serialization
                        code_obj = compile(entry.ast_obj, '<cache>', 'exec')
                        cache_data['entries'][key] = {
                            'code': code_obj,
                            'timestamp': entry.timestamp,
                            'size_bytes': entry.size_bytes,
                            'access_count': entry.access_count
                        }
                    except Exception as e:
                        logger.debug(f"Skipping cache entry {key[:8]}...: {e}")
                
                # Save to disk
                with open(temp_file, 'wb') as f:
                    if self.enable_compression:
                        import gzip
                        gz_file = temp_file.with_suffix('.gz')
                        with gzip.open(gz_file, 'wb') as gz:
                            pickle.dump(
                                cache_data, gz,
                                protocol=pickle.HIGHEST_PROTOCOL
                            )
                        temp_file.with_suffix('.gz').rename(
                            self.persistent_path / "cache.pkl.gz"
                        )
                    else:
                        pickle.dump(
                            cache_data, f,
                            protocol=pickle.HIGHEST_PROTOCOL
                        )
                        temp_file.rename(self.persistent_path / "cache.pkl")
                
                logger.info(
                    f"Saved {len(cache_data['entries'])} entries to disk"
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
            return False
    
    def _setup_persistent_storage(self) -> None:
        """Setup persistent storage directory"""
        if not self.persistent_path:
            return
        try:
            self.persistent_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create persistent cache directory: {e}")
            self.persistent_path = None
    
    def _load_from_disk(self) -> None:
        """Load cache from disk if available"""
        if not self.persistent_path:
            return
        
        cache_file = self.persistent_path / "cache.pkl"
        if self.enable_compression:
            cache_file = cache_file.with_suffix('.pkl.gz')
        
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'rb') as f:
                if self.enable_compression:
                    import gzip
                    with gzip.open(cache_file, 'rb') as gz:
                        cache_data = pickle.load(gz)
                else:
                    cache_data = pickle.load(f)
            
            # Restore cache entries
            loaded_count = 0
            for key, data in cache_data.get('entries', {}).items():
                try:
                    # Recreate AST from code object
                    # Note: This is a simplified approach
                    entry = CacheEntry(
                        # Would need proper AST recreation
                        ast_obj=data['code'],
                        timestamp=data['timestamp'],
                        size_bytes=data['size_bytes'],
                        access_count=data['access_count']
                    )
                    
                    # Check if entry is still valid
                    if self._is_entry_valid(entry):
                        self._cache[key] = entry
                        self._current_memory_usage += entry.size_bytes
                        loaded_count += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to restore cache entry: {e}")
            
            # Restore stats
            stats = cache_data.get('stats', {})
            self._hits = stats.get('hits', 0)
            self._misses = stats.get('misses', 0)
            self._evictions = stats.get('evictions', 0)
            
            logger.info(f"Loaded {loaded_count} entries from disk")
            
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")
    
    def _add_entry(self, cache_key: str, entry: CacheEntry) -> None:
        """Add an entry to the cache with eviction handling"""
        # Check if we need to evict based on memory
        while (self._current_memory_usage + entry.size_bytes >
               self.max_memory_bytes and self._cache):
            self._evict_by_memory()
        
        # Check if we need to evict based on count
        while len(self._cache) >= self.max_size:
            self._evict_oldest()
        
        # Add the new entry
        self._cache[cache_key] = entry
        self._cache.move_to_end(cache_key)
        self._current_memory_usage += entry.size_bytes
        
        # Save to disk if persistent storage is enabled
        if self.persistent_path and len(self._cache) % 10 == 0:
            # Save every 10 entries
            threading.Thread(target=self.save_to_disk, daemon=True).start()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest entry"""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._current_memory_usage -= entry.size_bytes
            self._evictions += 1
    
    def _evict_by_memory(self) -> None:
        """Evict entries to free up memory"""
        if self._cache:
            # Evict least recently used
            key, entry = self._cache.popitem(last=False)
            self._current_memory_usage -= entry.size_bytes
            self._evictions += 1
            self._size_evictions += 1
    
    def _get_valid_entry(self, cache_key: str) -> Optional[CacheEntry]:
        """Get entry if it exists and is still valid"""
        if cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        
        # Check TTL if enabled
        if self.ttl_seconds and self._is_entry_expired(entry):
            # Remove expired entry
            del self._cache[cache_key]
            self._current_memory_usage -= entry.size_bytes
            self._ttl_evictions += 1
            return None
        
        return entry
    
    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if an entry is still valid"""
        if self.ttl_seconds and self._is_entry_expired(entry):
            return False
        return True
    
    def _is_entry_expired(self, entry: CacheEntry) -> bool:
        """Check if an entry has expired based on TTL"""
        if not self.ttl_seconds:
            return False
        return (time.time() - entry.timestamp) > self.ttl_seconds
    
    def _cleanup_expired_entries(self) -> None:
        """Remove expired entries (called by background thread)"""
        with self._lock:
            expired_keys = []
            for key, entry in self._cache.items():
                if self._is_entry_expired(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                entry = self._cache.pop(key)
                self._current_memory_usage -= entry.size_bytes
                self._ttl_evictions += 1
    
    def _start_cleanup_thread(self) -> None:
        """Start background thread for cleaning up expired entries"""
        def cleanup_loop():
            while not self._stop_cleanup.is_set():
                self._cleanup_expired_entries()
                # Check every 60 seconds or 1/10 of TTL, whichever is smaller
                sleep_time = min(60, self.ttl_seconds / 10
                                 if self.ttl_seconds else 60)
                self._stop_cleanup.wait(sleep_time)
        
        self._cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True,
            name="ASTCache-Cleanup"
        )
        self._cleanup_thread.start()
    
    def _estimate_ast_size(self, ast_obj: Any) -> int:
        """Estimate the memory size of an AST object"""
        # This is a rough estimation
        # In production, you might want to use sys.getsizeof recursively
        try:
            # Count nodes
            node_count = sum(1 for _ in ast.walk(ast_obj))
            # Estimate ~200 bytes per node (rough average)
            estimated_size = node_count * 200
            return estimated_size
        except Exception:
            # Default size if estimation fails
            return 1024
    
    def _generate_cache_key(
        self, 
        source: Union[str, bytes], 
        filename: str, 
        mode: str
    ) -> str:
        """Generate a cache key for the given source code and parameters"""
        # Convert source to bytes if necessary
        if isinstance(source, str):
            source_bytes = source.encode('utf-8')
        else:
            source_bytes = source
        
        # Create a hash of the source code and parameters
        hasher = hashlib.sha256()
        hasher.update(source_bytes)
        hasher.update(filename.encode('utf-8'))
        hasher.update(mode.encode('utf-8'))
        
        return hasher.hexdigest()
    
    def __len__(self) -> int:
        """Return the current size of the cache"""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, source: Union[str, bytes]) -> bool:
        """Check if source code is in the cache"""
        cache_key = self._generate_cache_key(source, '<unknown>', 'exec')
        with self._lock:
            return (cache_key in self._cache and
                    self._get_valid_entry(cache_key) is not None)
    
    def __del__(self):
        """Cleanup when cache is destroyed"""
        # Stop cleanup thread
        if self._cleanup_thread:
            self._stop_cleanup.set()
            
        # Save to disk one final time
        if self.persistent_path:
            self.save_to_disk()


# Global cache instance with enhanced configuration
_global_cache = ASTCache(
    max_size=500,  # Increased from 100
    ttl_seconds=3600,  # 1 hour TTL
    max_memory_mb=200,  # 200MB memory limit
    persistent_path=None  # Can be configured by user
)


# Convenience functions that use the global cache
def parse_cached(
    source: Union[str, bytes], 
    filename: str = '<unknown>', 
    mode: str = 'exec'
) -> Any:
    """
    Parse source code using the global AST cache.
    
    This is a convenience function that uses a global cache instance.
    For more control, create your own ASTCache instance.
    
    Args:
        source: Source code to parse
        filename: Filename to use for error messages
        mode: Parsing mode ('exec', 'eval', or 'single')
        
    Returns:
        Parsed AST object
    """
    return _global_cache.parse(source, filename, mode)


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics from the global AST cache."""
    return _global_cache.get_stats()


def clear_cache() -> None:
    """Clear the global AST cache."""
    _global_cache.clear()


def reset_cache_stats() -> None:
    """Reset statistics for the global AST cache."""
    _global_cache.reset_stats()


def configure_global_cache(
    max_size: Optional[int] = None,
    ttl_seconds: Optional[float] = None,
    max_memory_mb: Optional[float] = None,
    persistent_path: Optional[Union[str, Path]] = None
) -> None:
    """
    Configure the global cache instance.
    
    Args:
        max_size: Maximum number of entries
        ttl_seconds: Time-to-live in seconds
        max_memory_mb: Maximum memory usage in MB
        persistent_path: Path for persistent storage
    """
    global _global_cache
    
    # Create new cache with updated configuration
    _global_cache = ASTCache(
        max_size=max_size or _global_cache.max_size,
        ttl_seconds=(ttl_seconds if ttl_seconds is not None
                     else _global_cache.ttl_seconds),
        max_memory_mb=(max_memory_mb or
                       (_global_cache.max_memory_bytes / 1024 / 1024)),
        persistent_path=persistent_path,
        enable_compression=True
    )