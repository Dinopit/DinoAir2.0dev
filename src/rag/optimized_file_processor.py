"""
Optimized File Processor for RAG File Search System
Implements performance improvements including parallel processing, caching,
and memory-efficient operations.
"""

import os
import hashlib
import concurrent.futures
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Tuple
from collections import OrderedDict
import time
import gc

# Import DinoAir components
from ..utils.logger import Logger
from ..database.file_search_db import FileSearchDB

# Import RAG components
from .text_extractors import ExtractorFactory
from .file_chunker import FileChunker, TextChunk
from .embedding_generator import get_embedding_generator
from .directory_validator import DirectoryValidator
from .file_processor import FileProcessor


class LRUCache:
    """Simple LRU cache implementation for embeddings and file metadata"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any) -> None:
        """Put item in cache"""
        with self.lock:
            if key in self.cache:
                # Update existing
                self.cache.move_to_end(key)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    self.cache.popitem(last=False)
            self.cache[key] = value
    
    def clear(self) -> None:
        """Clear the cache"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate
            }


class OptimizedFileProcessor(FileProcessor):
    """
    Optimized version of FileProcessor with performance improvements:
    - Parallel file processing
    - Caching for embeddings and metadata
    - Batch database operations
    - Memory-efficient file handling
    - Progress tracking with time estimates
    """
    
    def __init__(self,
                 user_name: Optional[str] = None,
                 max_file_size: Optional[int] = None,
                 chunk_size: Optional[int] = None,
                 chunk_overlap: Optional[int] = None,
                 generate_embeddings: bool = True,
                 embedding_batch_size: Optional[int] = None,
                 max_workers: Optional[int] = None,
                 cache_size: int = 1000,
                 enable_caching: bool = True):
        """
        Initialize the OptimizedFileProcessor.
        
        Additional Args:
            max_workers: Maximum number of parallel workers
            cache_size: Size of LRU cache for embeddings
            enable_caching: Whether to enable caching
        """
        super().__init__(
            user_name=user_name,
            max_file_size=max_file_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            generate_embeddings=generate_embeddings,
            embedding_batch_size=embedding_batch_size
        )
        
        # Parallel processing settings
        self.max_workers = max_workers or min(4, os.cpu_count() or 1)
        
        # Initialize caches
        self.enable_caching = enable_caching
        if enable_caching:
            self.file_hash_cache = LRUCache(cache_size)
            self.embedding_cache = LRUCache(cache_size // 2)
            self.metadata_cache = LRUCache(cache_size // 2)
        
        # Performance tracking
        self.processing_times = []
        self._lock = threading.Lock()
        
        self.logger.info(
            f"OptimizedFileProcessor initialized with {self.max_workers} workers, "
            f"caching={'enabled' if enable_caching else 'disabled'}"
        )
    
    def process_directory(self, directory_path: str,
                          recursive: bool = True,
                          file_extensions: Optional[List[str]] = None,
                          force_reprocess: bool = False,
                          progress_callback: Optional[
                              Callable[[str, int, int], None]
                          ] = None) -> Dict[str, Any]:
        """
        Process all files in a directory with parallel processing.
        """
        try:
            # Validate directory and get files (same as parent)
            if not os.path.isdir(directory_path):
                return {
                    "success": False,
                    "error": f"Directory not found: {directory_path}"
                }
            
            validation_result = self.directory_validator.validate_path(
                directory_path
            )
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Directory access denied: {validation_result['message']}"
                }
            
            if not file_extensions:
                file_extensions = self.extractor_factory.get_supported_extensions()
            
            all_files = self._find_files(directory_path, recursive, file_extensions)
            files_to_process = self.directory_validator.get_allowed_files(all_files)
            
            if not files_to_process:
                return {
                    "success": True,
                    "message": "No files found to process",
                    "stats": {
                        "total_files": 0,
                        "processed": 0,
                        "failed": 0,
                        "skipped": 0
                    }
                }
            
            # Initialize results
            results = {
                "success": True,
                "processed_files": [],
                "failed_files": [],
                "skipped_files": [],
                "stats": {
                    "total_files": len(files_to_process),
                    "processed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total_chunks": 0,
                    "total_embeddings": 0,
                    "processing_time": 0,
                    "files_per_second": 0
                }
            }
            
            start_time = time.time()
            
            # Process files in parallel
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(
                        self._process_file_wrapper,
                        file_path,
                        force_reprocess,
                        i,
                        len(files_to_process)
                    ): file_path
                    for i, file_path in enumerate(files_to_process)
                }
                
                # Process completed futures
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    
                    try:
                        result = future.result()
                        self._update_results(results, file_path, result)
                        
                        # Update progress
                        if progress_callback:
                            processed = (
                                results['stats']['processed'] +
                                results['stats']['failed'] +
                                results['stats']['skipped']
                            )
                            elapsed = time.time() - start_time
                            if processed > 0:
                                rate = processed / elapsed
                                remaining = (len(files_to_process) - processed) / rate
                                eta = datetime.now() + timedelta(seconds=remaining)
                                
                                progress_callback(
                                    f"Processing files ({processed}/{len(files_to_process)}) "
                                    f"ETA: {eta.strftime('%H:%M:%S')}",
                                    processed,
                                    len(files_to_process)
                                )
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {file_path}: {str(e)}")
                        results['failed_files'].append({
                            'file_path': file_path,
                            'error': str(e)
                        })
                        results['stats']['failed'] += 1
            
            # Calculate final statistics
            end_time = time.time()
            results['stats']['processing_time'] = end_time - start_time
            if results['stats']['processing_time'] > 0:
                results['stats']['files_per_second'] = (
                    len(files_to_process) / results['stats']['processing_time']
                )
            
            # Update success status
            if results['stats']['failed'] > 0:
                results['success'] = False
                results['error'] = (
                    f"Failed to process {results['stats']['failed']} "
                    f"out of {results['stats']['total_files']} files"
                )
            
            # Add cache statistics if enabled
            if self.enable_caching:
                results['cache_stats'] = {
                    'file_hash_cache': self.file_hash_cache.get_stats(),
                    'embedding_cache': self.embedding_cache.get_stats(),
                    'metadata_cache': self.metadata_cache.get_stats()
                }
            
            return results
            
        except Exception as e:
            self.logger.error(
                f"Error processing directory {directory_path}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def _process_file_wrapper(self, file_path: str, force_reprocess: bool,
                              index: int, total: int) -> Dict[str, Any]:
        """Wrapper for process_file to handle progress tracking"""
        try:
            start_time = time.time()
            
            # Check cache first
            if self.enable_caching and not force_reprocess:
                cached_result = self._check_file_cache(file_path)
                if cached_result:
                    return cached_result
            
            result = self.process_file(
                file_path,
                force_reprocess=force_reprocess,
                store_in_db=True
            )
            
            # Track processing time
            processing_time = time.time() - start_time
            with self._lock:
                self.processing_times.append(processing_time)
            
            # Cache successful results
            if self.enable_caching and result['success']:
                self._cache_file_result(file_path, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in process_file_wrapper: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_file_cache(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Check if file is in cache and still valid"""
        try:
            # Get current file metadata
            stat = os.stat(file_path)
            cache_key = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            
            # Check metadata cache
            cached_metadata = self.metadata_cache.get(cache_key)
            if cached_metadata:
                self.logger.debug(f"Cache hit for file: {file_path}")
                return {
                    "success": True,
                    "file_id": cached_metadata['file_id'],
                    "chunks": [],  # Not stored in cache
                    "message": "Retrieved from cache",
                    "stats": {
                        "action": "cached",
                        "chunk_count": cached_metadata['chunk_count']
                    }
                }
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Cache check failed for {file_path}: {str(e)}")
            return None
    
    def _cache_file_result(self, file_path: str, result: Dict[str, Any]) -> None:
        """Cache successful file processing result"""
        try:
            stat = os.stat(file_path)
            cache_key = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            
            metadata = {
                'file_id': result.get('file_id'),
                'chunk_count': len(result.get('chunks', [])),
                'cached_at': datetime.now().isoformat()
            }
            
            self.metadata_cache.put(cache_key, metadata)
            
        except Exception as e:
            self.logger.debug(f"Failed to cache result for {file_path}: {str(e)}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate file hash with caching"""
        if self.enable_caching:
            # Check cache first
            stat = os.stat(file_path)
            cache_key = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            cached_hash = self.file_hash_cache.get(cache_key)
            if cached_hash:
                return cached_hash
        
        # Calculate hash
        file_hash = super()._calculate_file_hash(file_path)
        
        # Cache the result
        if self.enable_caching:
            self.file_hash_cache.put(cache_key, file_hash)
        
        return file_hash
    
    def _update_results(self, results: Dict[str, Any], file_path: str,
                        file_result: Dict[str, Any]) -> None:
        """Update results dictionary with file processing result"""
        with self._lock:
            if file_result['success']:
                if file_result.get('stats', {}).get('action') == 'skipped':
                    results['skipped_files'].append(file_path)
                    results['stats']['skipped'] += 1
                elif file_result.get('stats', {}).get('action') == 'cached':
                    results['skipped_files'].append(file_path)
                    results['stats']['skipped'] += 1
                else:
                    results['processed_files'].append({
                        'file_path': file_path,
                        'file_id': file_result.get('file_id'),
                        'chunk_count': len(file_result.get('chunks', []))
                    })
                    results['stats']['processed'] += 1
                    results['stats']['total_chunks'] += len(
                        file_result.get('chunks', [])
                    )
                    results['stats']['total_embeddings'] += file_result.get(
                        'stats', {}
                    ).get('embeddings_generated', 0)
            else:
                results['failed_files'].append({
                    'file_path': file_path,
                    'error': file_result.get('error', 'Unknown error')
                })
                results['stats']['failed'] += 1
    
    def _generate_and_store_embeddings(self, chunk_ids: List[str],
                                       chunk_texts: List[str],
                                       progress_callback: Optional[
                                           Callable[[str, int, int], None]
                                       ] = None) -> int:
        """
        Generate embeddings with caching support.
        """
        if not self.generate_embeddings or not self._embedding_generator:
            return 0
        
        try:
            total_chunks = len(chunk_ids)
            embeddings_stored = 0
            embeddings_to_generate = []
            cached_embeddings = []
            
            # Check cache for existing embeddings
            if self.enable_caching:
                for i, (chunk_id, chunk_text) in enumerate(
                    zip(chunk_ids, chunk_texts)
                ):
                    cached = self.embedding_cache.get(chunk_id)
                    if cached:
                        cached_embeddings.append((i, chunk_id, cached))
                    else:
                        embeddings_to_generate.append((i, chunk_id, chunk_text))
            else:
                embeddings_to_generate = [
                    (i, chunk_id, chunk_text)
                    for i, (chunk_id, chunk_text) in enumerate(
                        zip(chunk_ids, chunk_texts)
                    )
                ]
            
            # Generate new embeddings in batches
            new_embeddings = []
            if embeddings_to_generate:
                batch_size = self.embedding_batch_size
                
                for batch_start in range(0, len(embeddings_to_generate), batch_size):
                    batch_end = min(
                        batch_start + batch_size,
                        len(embeddings_to_generate)
                    )
                    batch = embeddings_to_generate[batch_start:batch_end]
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(
                            f"Generating embeddings ({batch_end}/{len(embeddings_to_generate)} new, "
                            f"{len(cached_embeddings)} cached)",
                            batch_end + len(cached_embeddings),
                            total_chunks
                        )
                    
                    # Generate batch embeddings
                    batch_texts = [item[2] for item in batch]
                    try:
                        embeddings = self._embedding_generator.generate_embeddings_batch(
                            batch_texts,
                            batch_size=self.embedding_batch_size,
                            show_progress=False
                        )
                        
                        for (idx, chunk_id, _), embedding in zip(batch, embeddings):
                            new_embeddings.append((idx, chunk_id, embedding))
                            
                            # Cache the embedding
                            if self.enable_caching:
                                self.embedding_cache.put(chunk_id, embedding)
                    
                    except Exception as e:
                        self.logger.error(
                            f"Error generating embeddings for batch: {str(e)}"
                        )
            
            # Combine cached and new embeddings in original order
            all_embeddings = sorted(
                cached_embeddings + new_embeddings,
                key=lambda x: x[0]
            )
            
            # Store all embeddings in database
            for _, chunk_id, embedding in all_embeddings:
                try:
                    result = self.db.add_embedding(
                        chunk_id=chunk_id,
                        embedding_vector=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                        model_name=self._embedding_generator.model_name
                    )
                    
                    if result['success']:
                        embeddings_stored += 1
                    else:
                        self.logger.error(
                            f"Failed to store embedding for {chunk_id}: {result.get('error')}"
                        )
                        
                except Exception as e:
                    self.logger.error(
                        f"Error storing embedding for {chunk_id}: {str(e)}"
                    )
            
            self.logger.info(
                f"Stored {embeddings_stored}/{total_chunks} embeddings "
                f"({len(cached_embeddings)} from cache)"
            )
            
            return embeddings_stored
            
        except Exception as e:
            self.logger.error(f"Error in embedding generation: {str(e)}")
            return 0
    
    def clear_caches(self) -> None:
        """Clear all caches"""
        if self.enable_caching:
            self.file_hash_cache.clear()
            self.embedding_cache.clear()
            self.metadata_cache.clear()
            self.logger.info("All caches cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            "max_workers": self.max_workers,
            "caching_enabled": self.enable_caching
        }
        
        if self.processing_times:
            stats.update({
                "average_file_time": sum(self.processing_times) / len(self.processing_times),
                "total_files_processed": len(self.processing_times),
                "min_file_time": min(self.processing_times),
                "max_file_time": max(self.processing_times)
            })
        
        if self.enable_caching:
            stats["cache_performance"] = {
                "file_hash_cache": self.file_hash_cache.get_stats(),
                "embedding_cache": self.embedding_cache.get_stats(),
                "metadata_cache": self.metadata_cache.get_stats()
            }
        
        return stats
    
    def optimize_for_memory(self) -> None:
        """Optimize memory usage by clearing caches and forcing garbage collection"""
        if self.enable_caching:
            # Clear caches
            self.clear_caches()
        
        # Force garbage collection
        gc.collect()
        
        self.logger.info("Memory optimization completed")


class BatchEmbeddingProcessor:
    """
    Specialized processor for batch embedding generation with progress tracking
    """
    
    def __init__(self, user_name: str, batch_size: int = 32):
        self.logger = Logger()
        self.user_name = user_name
        self.batch_size = batch_size
        self.db = FileSearchDB(user_name)
        self.embedding_generator = get_embedding_generator()
    
    def generate_missing_embeddings(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for all chunks that don't have embeddings yet.
        """
        try:
            # Get chunks without embeddings
            chunks_without_embeddings = self._get_chunks_without_embeddings()
            
            if not chunks_without_embeddings:
                return {
                    "success": True,
                    "message": "All chunks already have embeddings",
                    "stats": {
                        "total_chunks": 0,
                        "embeddings_generated": 0
                    }
                }
            
            total_chunks = len(chunks_without_embeddings)
            embeddings_generated = 0
            start_time = time.time()
            
            # Process in batches
            for i in range(0, total_chunks, self.batch_size):
                batch_end = min(i + self.batch_size, total_chunks)
                batch = chunks_without_embeddings[i:batch_end]
                
                # Update progress
                if progress_callback:
                    elapsed = time.time() - start_time
                    if i > 0:
                        rate = i / elapsed
                        remaining = (total_chunks - i) / rate
                        eta = datetime.now() + timedelta(seconds=remaining)
                        
                        progress_callback(
                            f"Generating embeddings ({i}/{total_chunks}) "
                            f"ETA: {eta.strftime('%H:%M:%S')}",
                            i,
                            total_chunks
                        )
                
                # Generate embeddings for batch
                chunk_texts = [chunk['content'] for chunk in batch]
                
                try:
                    embeddings = self.embedding_generator.generate_embeddings_batch(
                        chunk_texts,
                        batch_size=self.batch_size,
                        show_progress=False
                    )
                    
                    # Store embeddings
                    for chunk, embedding in zip(batch, embeddings):
                        result = self.db.add_embedding(
                            chunk_id=chunk['chunk_id'],
                            embedding_vector=embedding.tolist(),
                            model_name=self.embedding_generator.model_name
                        )
                        
                        if result['success']:
                            embeddings_generated += 1
                        
                except Exception as e:
                    self.logger.error(f"Error generating batch embeddings: {str(e)}")
            
            end_time = time.time()
            
            return {
                "success": True,
                "stats": {
                    "total_chunks": total_chunks,
                    "embeddings_generated": embeddings_generated,
                    "processing_time": end_time - start_time,
                    "embeddings_per_second": embeddings_generated / (end_time - start_time)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in batch embedding generation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_chunks_without_embeddings(self) -> List[Dict[str, Any]]:
        """Get all chunks that don't have embeddings"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT c.id as chunk_id, c.content
                    FROM file_chunks c
                    LEFT JOIN file_embeddings e ON c.id = e.chunk_id
                    WHERE e.id IS NULL
                    ORDER BY c.file_id, c.chunk_index
                ''')
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error getting chunks without embeddings: {str(e)}")
            return []