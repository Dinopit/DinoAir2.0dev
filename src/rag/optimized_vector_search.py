"""
Optimized Vector Search for RAG File Search System
Implements performance improvements including result caching, parallel search,
and efficient similarity calculations.
"""

import numpy as np
import json
import time
import concurrent.futures
from typing import List, Dict, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
import threading
import heapq

# Import DinoAir components
from ..utils.logger import Logger
from ..database.file_search_db import FileSearchDB

# Import RAG components
from .embedding_generator import get_embedding_generator
from .vector_search import VectorSearchEngine, SearchResult


class SearchCache:
    """Thread-safe cache for search results with TTL support"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, query: str, params: Dict[str, Any]) -> str:
        """Create cache key from query and parameters"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{query}:{param_str}"
    
    def get(self, query: str, params: Dict[str, Any]) -> Optional[List[SearchResult]]:
        """Get cached results if available and not expired"""
        key = self._make_key(query, params)
        
        with self.lock:
            if key in self.cache:
                # Check if expired
                if time.time() - self.access_times[key] < self.ttl_seconds:
                    self.hits += 1
                    self.access_times[key] = time.time()
                    return self.cache[key]
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    del self.access_times[key]
            
            self.misses += 1
            return None
    
    def put(self, query: str, params: Dict[str, Any], results: List[SearchResult]):
        """Cache search results"""
        key = self._make_key(query, params)
        
        with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = min(self.access_times, key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = results
            self.access_times[key] = time.time()
    
    def clear(self):
        """Clear the cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
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
                "hit_rate": hit_rate,
                "ttl_seconds": self.ttl_seconds
            }


class OptimizedVectorSearchEngine(VectorSearchEngine):
    """
    Optimized vector search with performance improvements:
    - Result caching with TTL
    - Parallel similarity calculations
    - Efficient top-k selection using heaps
    - Batch embedding loading
    - Pre-computed normalized vectors
    """
    
    def __init__(self, user_name: Optional[str] = None,
                 embedding_generator=None,
                 cache_size: int = 100,
                 cache_ttl: int = 3600,
                 enable_caching: bool = True,
                 max_workers: Optional[int] = None):
        """
        Initialize OptimizedVectorSearchEngine.
        
        Additional Args:
            cache_size: Maximum number of cached queries
            cache_ttl: Cache time-to-live in seconds
            enable_caching: Whether to enable result caching
            max_workers: Maximum number of parallel workers
        """
        super().__init__(user_name, embedding_generator)
        
        # Caching
        self.enable_caching = enable_caching
        if enable_caching:
            self.search_cache = SearchCache(cache_size, cache_ttl)
        
        # Parallel processing
        self.max_workers = max_workers or min(4, os.cpu_count() or 1)
        
        # Pre-computed embeddings cache
        self._embeddings_cache = None
        self._embeddings_cache_time = 0
        self._cache_refresh_interval = 300  # 5 minutes
        
        self.logger.info(
            f"OptimizedVectorSearchEngine initialized with "
            f"caching={'enabled' if enable_caching else 'disabled'}, "
            f"max_workers={self.max_workers}"
        )
    
    def search(self, query: str,
               top_k: int = 10,
               similarity_threshold: Optional[float] = None,
               file_types: Optional[List[str]] = None,
               distance_metric: str = 'cosine') -> List[SearchResult]:
        """
        Perform optimized vector similarity search.
        """
        try:
            # Check cache first
            if self.enable_caching:
                cache_params = {
                    'top_k': top_k,
                    'threshold': similarity_threshold,
                    'file_types': file_types,
                    'metric': distance_metric
                }
                cached_results = self.search_cache.get(query, cache_params)
                if cached_results is not None:
                    self.logger.debug(f"Cache hit for query: {query[:50]}...")
                    return cached_results
            
            # Generate query embedding
            query_embedding = self.embedding_generator.generate_embedding(
                query, normalize=True
            )
            
            # Get embeddings (with caching)
            all_embeddings = self._get_cached_embeddings(file_types)
            
            if not all_embeddings:
                self.logger.info("No embeddings found in database")
                return []
            
            # Perform parallel similarity search
            results = self._parallel_similarity_search(
                query_embedding,
                all_embeddings,
                top_k,
                similarity_threshold or self.DEFAULT_SIMILARITY_THRESHOLD,
                distance_metric
            )
            
            # Cache results
            if self.enable_caching:
                self.search_cache.put(query, cache_params, results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error performing optimized search: {str(e)}")
            return []
    
    def _get_cached_embeddings(self, file_types: Optional[List[str]] = None
                               ) -> List[Dict[str, Any]]:
        """Get embeddings with caching"""
        # Check if cache needs refresh
        current_time = time.time()
        if (self._embeddings_cache is None or 
            current_time - self._embeddings_cache_time > self._cache_refresh_interval):
            
            self.logger.debug("Refreshing embeddings cache")
            self._embeddings_cache = self._retrieve_all_embeddings(file_types)
            self._embeddings_cache_time = current_time
            
            # Pre-parse embeddings for efficiency
            for emb_data in self._embeddings_cache:
                if isinstance(emb_data['embedding_vector'], str):
                    emb_data['embedding_vector'] = np.array(
                        json.loads(emb_data['embedding_vector'])
                    )
        
        # Filter by file types if needed
        if file_types and self._embeddings_cache:
            return [
                emb for emb in self._embeddings_cache
                if emb.get('file_type') in file_types
            ]
        
        return self._embeddings_cache or []
    
    def _parallel_similarity_search(
        self,
        query_embedding: np.ndarray,
        all_embeddings: List[Dict[str, Any]],
        top_k: int,
        similarity_threshold: float,
        distance_metric: str
    ) -> List[SearchResult]:
        """Perform similarity search in parallel"""
        
        # Choose similarity function
        similarity_func = (
            self.cosine_similarity if distance_metric == 'cosine'
            else self.euclidean_similarity
        )
        
        # Split embeddings for parallel processing
        chunk_size = max(100, len(all_embeddings) // self.max_workers)
        chunks = [
            all_embeddings[i:i + chunk_size]
            for i in range(0, len(all_embeddings), chunk_size)
        ]
        
        # Process chunks in parallel
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_chunk = {
                executor.submit(
                    self._process_embedding_chunk,
                    query_embedding,
                    chunk,
                    similarity_func,
                    similarity_threshold
                ): chunk
                for chunk in chunks
            }
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                try:
                    chunk_results = future.result()
                    all_results.extend(chunk_results)
                except Exception as e:
                    self.logger.error(f"Error processing chunk: {str(e)}")
        
        # Use heap for efficient top-k selection
        return self._get_top_k_results(all_results, top_k)
    
    def _process_embedding_chunk(
        self,
        query_embedding: np.ndarray,
        embeddings_chunk: List[Dict[str, Any]],
        similarity_func: Callable,
        threshold: float
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """Process a chunk of embeddings"""
        results = []
        
        for emb_data in embeddings_chunk:
            # Get embedding vector
            if isinstance(emb_data['embedding_vector'], str):
                embedding = np.array(json.loads(emb_data['embedding_vector']))
            else:
                embedding = emb_data['embedding_vector']
            
            # Calculate similarity
            similarity = similarity_func(query_embedding, embedding)
            
            # Apply threshold
            if similarity >= threshold:
                results.append((similarity, emb_data))
        
        return results
    
    def _get_top_k_results(
        self,
        scored_results: List[Tuple[float, Dict[str, Any]]],
        top_k: int
    ) -> List[SearchResult]:
        """Efficiently get top-k results using a heap"""
        # Use negative scores for max heap
        heap = []
        
        for score, emb_data in scored_results:
            if len(heap) < top_k:
                heapq.heappush(heap, (-score, emb_data))
            elif score > -heap[0][0]:
                heapq.heapreplace(heap, (-score, emb_data))
        
        # Extract results in descending order
        results = []
        while heap:
            neg_score, emb_data = heapq.heappop(heap)
            score = -neg_score
            
            result = SearchResult(
                chunk_id=emb_data['chunk_id'],
                file_id=emb_data['file_id'],
                file_path=emb_data['file_path'],
                content=emb_data['content'],
                score=score,
                chunk_index=emb_data['chunk_index'],
                start_pos=emb_data['start_pos'],
                end_pos=emb_data['end_pos'],
                file_type=emb_data.get('file_type'),
                metadata=emb_data.get('chunk_metadata'),
                match_type='vector'
            )
            results.append(result)
        
        # Reverse to get descending order
        results.reverse()
        
        self.logger.info(f"Vector search found {len(results)} results")
        return results
    
    def hybrid_search(self, query: str,
                      top_k: int = 10,
                      vector_weight: float = 0.7,
                      keyword_weight: float = 0.3,
                      similarity_threshold: Optional[float] = None,
                      file_types: Optional[List[str]] = None,
                      rerank: bool = True) -> List[SearchResult]:
        """
        Optimized hybrid search with parallel execution.
        """
        try:
            # Check cache for hybrid results
            if self.enable_caching:
                cache_params = {
                    'top_k': top_k,
                    'vector_weight': vector_weight,
                    'keyword_weight': keyword_weight,
                    'threshold': similarity_threshold,
                    'file_types': file_types,
                    'rerank': rerank,
                    'type': 'hybrid'
                }
                cached_results = self.search_cache.get(query, cache_params)
                if cached_results is not None:
                    return cached_results
            
            # Normalize weights
            total_weight = vector_weight + keyword_weight
            vector_weight = vector_weight / total_weight
            keyword_weight = keyword_weight / total_weight
            
            # Execute searches in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Submit both searches
                vector_future = executor.submit(
                    self.search,
                    query,
                    top_k * 2,  # Get more for merging
                    similarity_threshold,
                    file_types
                )
                
                keyword_future = executor.submit(
                    self.keyword_search,
                    query,
                    top_k * 2,
                    file_types
                )
                
                # Get results
                vector_results = vector_future.result()
                keyword_results = keyword_future.result()
            
            # Merge results
            merged_results = self._merge_search_results(
                vector_results,
                keyword_results,
                vector_weight,
                keyword_weight
            )
            
            # Rerank if requested
            if rerank and merged_results:
                merged_results = self.rerank_results(
                    query, merged_results, top_k=top_k
                )
            else:
                merged_results = merged_results[:top_k]
            
            # Cache results
            if self.enable_caching:
                self.search_cache.put(query, cache_params, merged_results)
            
            self.logger.info(
                f"Hybrid search returned {len(merged_results)} results"
            )
            
            return merged_results
            
        except Exception as e:
            self.logger.error(f"Error performing hybrid search: {str(e)}")
            return []
    
    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
        search_type: str = 'hybrid',
        **kwargs
    ) -> Dict[str, List[SearchResult]]:
        """
        Perform batch search for multiple queries efficiently.
        
        Args:
            queries: List of search queries
            top_k: Number of results per query
            search_type: 'vector', 'keyword', or 'hybrid'
            **kwargs: Additional search parameters
            
        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        
        # Choose search function
        if search_type == 'vector':
            search_func = self.search
        elif search_type == 'keyword':
            search_func = self.keyword_search
        else:
            search_func = self.hybrid_search
        
        # Process queries in parallel
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_query = {
                executor.submit(search_func, query, top_k, **kwargs): query
                for query in queries
            }
            
            for future in concurrent.futures.as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    results[query] = future.result()
                except Exception as e:
                    self.logger.error(f"Error searching for '{query}': {str(e)}")
                    results[query] = []
        
        return results
    
    def clear_cache(self):
        """Clear all caches"""
        if self.enable_caching:
            self.search_cache.clear()
        self._embeddings_cache = None
        self._embeddings_cache_time = 0
        self.logger.info("Search caches cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {
            "max_workers": self.max_workers,
            "caching_enabled": self.enable_caching
        }
        
        if self.enable_caching:
            stats["search_cache"] = self.search_cache.get_stats()
        
        if self._embeddings_cache is not None:
            stats["embeddings_cache"] = {
                "size": len(self._embeddings_cache),
                "age_seconds": time.time() - self._embeddings_cache_time,
                "refresh_interval": self._cache_refresh_interval
            }
        
        return stats
    
    def warmup_cache(self, common_queries: List[str], **search_params):
        """
        Warm up the cache with common queries.
        
        Args:
            common_queries: List of common search queries
            **search_params: Parameters to use for searches
        """
        if not self.enable_caching:
            self.logger.warning("Cache warmup called but caching is disabled")
            return
        
        self.logger.info(f"Warming up cache with {len(common_queries)} queries")
        
        # Load embeddings into cache
        self._get_cached_embeddings()
        
        # Perform searches to populate cache
        for query in common_queries:
            try:
                self.hybrid_search(query, **search_params)
            except Exception as e:
                self.logger.error(f"Error warming cache for '{query}': {str(e)}")
        
        self.logger.info("Cache warmup complete")


class SearchOptimizer:
    """
    Utility class for optimizing search queries and results
    """
    
    def __init__(self):
        self.logger = Logger()
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with', 'this', 'but',
            'they', 'have', 'had', 'what', 'when', 'where', 'who',
            'which', 'why', 'how'
        }
    
    def optimize_query(self, query: str) -> str:
        """
        Optimize query for better search results.
        
        Args:
            query: Original search query
            
        Returns:
            Optimized query
        """
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Convert to lowercase for processing
        query_lower = query.lower()
        
        # Remove very short queries
        if len(query_lower) < 3:
            return query
        
        # Expand common abbreviations
        abbreviations = {
            'ml': 'machine learning',
            'ai': 'artificial intelligence',
            'db': 'database',
            'api': 'application programming interface',
            'ui': 'user interface',
            'ux': 'user experience'
        }
        
        for abbr, expansion in abbreviations.items():
            if f' {abbr} ' in f' {query_lower} ':
                query_lower = query_lower.replace(f' {abbr} ', f' {expansion} ')
        
        return query_lower.strip()
    
    def extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from query for keyword search.
        
        Args:
            query: Search query
            
        Returns:
            List of key terms
        """
        # Tokenize and clean
        words = query.lower().split()
        
        # Remove stop words and short words
        key_terms = [
            word for word in words
            if word not in self.stop_words and len(word) > 2
        ]
        
        # Add bigrams for better context
        bigrams = []
        for i in range(len(words) - 1):
            if (words[i] not in self.stop_words and 
                words[i + 1] not in self.stop_words):
                bigrams.append(f"{words[i]} {words[i + 1]}")
        
        return key_terms + bigrams
    
    def group_results_by_file(
        self,
        results: List[SearchResult]
    ) -> Dict[str, List[SearchResult]]:
        """
        Group search results by file for better presentation.
        
        Args:
            results: List of search results
            
        Returns:
            Dictionary mapping file paths to their results
        """
        grouped = defaultdict(list)
        
        for result in results:
            grouped[result.file_path].append(result)
        
        # Sort results within each file by chunk index
        for file_path in grouped:
            grouped[file_path].sort(key=lambda x: x.chunk_index)
        
        return dict(grouped)
    
    def deduplicate_results(
        self,
        results: List[SearchResult],
        similarity_threshold: float = 0.9
    ) -> List[SearchResult]:
        """
        Remove duplicate or highly similar results.
        
        Args:
            results: List of search results
            similarity_threshold: Threshold for considering results as duplicates
            
        Returns:
            Deduplicated list of results
        """
        if len(results) <= 1:
            return results
        
        deduplicated = [results[0]]
        
        for result in results[1:]:
            is_duplicate = False
            
            for kept_result in deduplicated:
                # Check if from same file and overlapping chunks
                if (result.file_id == kept_result.file_id and
                    abs(result.chunk_index - kept_result.chunk_index) <= 1):
                    is_duplicate = True
                    break
                
                # Check content similarity
                if self._text_similarity(
                    result.content,
                    kept_result.content
                ) > similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
        
        return deduplicated
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using Jaccard index"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


# Import os for cpu_count
import os