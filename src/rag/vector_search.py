"""
Vector search module for DinoAir 2.0 RAG File Search system.
Provides vector similarity search and hybrid search capabilities.
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import re

# Import DinoAir components
from ..utils.logger import Logger
from ..database.file_search_db import FileSearchDB

# Import RAG components
from .embedding_generator import EmbeddingGenerator, get_embedding_generator


@dataclass
class SearchResult:
    """Represents a search result with metadata."""
    chunk_id: str
    file_id: str
    file_path: str
    content: str
    score: float
    chunk_index: int
    start_pos: int
    end_pos: int
    file_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    match_type: str = 'vector'  # 'vector', 'keyword', or 'hybrid'


class VectorSearchEngine:
    """
    Handles vector similarity search and hybrid search operations.
    Combines semantic search with keyword matching for better results.
    """
    
    # Default search parameters
    DEFAULT_TOP_K = 10
    DEFAULT_SIMILARITY_THRESHOLD = 0.5
    DEFAULT_VECTOR_WEIGHT = 0.7  # Weight for vector similarity
    DEFAULT_KEYWORD_WEIGHT = 0.3  # Weight for keyword match
    
    def __init__(self, user_name: Optional[str] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None):
        """
        Initialize the VectorSearchEngine.
        
        Args:
            user_name: Username for database operations
            embedding_generator: Optional pre-configured embedding generator
        """
        self.logger = Logger()
        self.user_name = user_name
        self.db = FileSearchDB(user_name)
        
        # Use provided generator or create default one
        if embedding_generator:
            self.embedding_generator = embedding_generator
        else:
            self.embedding_generator = get_embedding_generator()
        
        self.logger.info("VectorSearchEngine initialized")
    
    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        # Ensure numpy arrays
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @staticmethod
    def euclidean_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate Euclidean-based similarity between two vectors.
        Converts distance to similarity score.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Similarity score between 0 and 1
        """
        # Calculate Euclidean distance
        distance = np.linalg.norm(np.array(vec1) - np.array(vec2))
        
        # Convert to similarity (1 / (1 + distance))
        return float(1.0 / (1.0 + float(distance)))
    
    def search(self, query: str,
               top_k: int = DEFAULT_TOP_K,
               similarity_threshold: Optional[float] = None,
               file_types: Optional[List[str]] = None,
               distance_metric: str = 'cosine') -> List[SearchResult]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            file_types: Filter by file types (e.g., ['pdf', 'txt'])
            distance_metric: 'cosine' or 'euclidean'
            
        Returns:
            List of SearchResult objects sorted by similarity
        """
        try:
            if not query or not query.strip():
                self.logger.warning("Empty query provided")
                return []
            
            # Set default threshold if not provided
            if similarity_threshold is None:
                similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD
            
            # Generate query embedding
            self.logger.info(
                f"Generating embedding for query: {query[:50]}..."
            )
            query_embedding = self.embedding_generator.generate_embedding(
                query, normalize=True
            )
            
            # Retrieve all embeddings from database
            all_embeddings = self._retrieve_all_embeddings(file_types)
            
            if not all_embeddings:
                self.logger.info("No embeddings found in database")
                return []
            
            # Calculate similarities
            results = []
            similarity_func = (self.cosine_similarity
                               if distance_metric == 'cosine'
                               else self.euclidean_similarity)
            
            for embedding_data in all_embeddings:
                # Parse stored embedding
                stored_embedding = np.array(
                    json.loads(embedding_data['embedding_vector'])
                )
                
                # Calculate similarity
                similarity = similarity_func(query_embedding, stored_embedding)
                
                # Apply threshold
                if similarity >= similarity_threshold:
                    result = SearchResult(
                        chunk_id=embedding_data['chunk_id'],
                        file_id=embedding_data['file_id'],
                        file_path=embedding_data['file_path'],
                        content=embedding_data['content'],
                        score=similarity,
                        chunk_index=embedding_data['chunk_index'],
                        start_pos=embedding_data['start_pos'],
                        end_pos=embedding_data['end_pos'],
                        file_type=embedding_data.get('file_type'),
                        metadata=embedding_data.get('chunk_metadata'),
                        match_type='vector'
                    )
                    results.append(result)
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Return top k results
            top_results = results[:top_k]
            
            self.logger.info(
                f"Vector search found {len(top_results)} results "
                f"(from {len(results)} above threshold)"
            )
            
            return top_results
            
        except Exception as e:
            self.logger.error(f"Error performing vector search: {str(e)}")
            return []
    
    def keyword_search(self, query: str,
                       top_k: int = DEFAULT_TOP_K,
                       file_types: Optional[List[str]] = None
                       ) -> List[SearchResult]:
        """
        Perform keyword-based search using SQLite FTS or LIKE.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            file_types: Filter by file types
            
        Returns:
            List of SearchResult objects
        """
        try:
            if not query or not query.strip():
                return []
            
            # Simple keyword extraction (can be enhanced)
            keywords = self._extract_keywords(query)
            
            if not keywords:
                return []
            
            # Search in database
            results = self._search_by_keywords(keywords, file_types)
            
            # Convert to SearchResult objects
            search_results = []
            for result in results[:top_k]:
                search_result = SearchResult(
                    chunk_id=result['chunk_id'],
                    file_id=result['file_id'],
                    file_path=result['file_path'],
                    content=result['content'],
                    score=result['relevance_score'],
                    chunk_index=result['chunk_index'],
                    start_pos=result['start_pos'],
                    end_pos=result['end_pos'],
                    file_type=result.get('file_type'),
                    metadata=result.get('chunk_metadata'),
                    match_type='keyword'
                )
                search_results.append(search_result)
            
            self.logger.info(
                f"Keyword search found {len(search_results)} results"
            )
            return search_results
            
        except Exception as e:
            self.logger.error(f"Error performing keyword search: {str(e)}")
            return []
    
    def hybrid_search(self, query: str,
                      top_k: int = DEFAULT_TOP_K,
                      vector_weight: float = DEFAULT_VECTOR_WEIGHT,
                      keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
                      similarity_threshold: Optional[float] = None,
                      file_types: Optional[List[str]] = None,
                      rerank: bool = True) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            vector_weight: Weight for vector similarity scores
            keyword_weight: Weight for keyword match scores
            similarity_threshold: Minimum similarity for vector search
            file_types: Filter by file types
            rerank: Whether to rerank results
            
        Returns:
            List of SearchResult objects with combined scores
        """
        try:
            # Normalize weights
            total_weight = vector_weight + keyword_weight
            vector_weight = vector_weight / total_weight
            keyword_weight = keyword_weight / total_weight
            
            # Perform vector search
            vector_results = self.search(
                query, 
                top_k=top_k * 2,  # Get more results for merging
                similarity_threshold=similarity_threshold,
                file_types=file_types
            )
            
            # Perform keyword search
            keyword_results = self.keyword_search(
                query,
                top_k=top_k * 2,
                file_types=file_types
            )
            
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
                # Just take top k
                merged_results = merged_results[:top_k]
            
            self.logger.info(
                f"Hybrid search returned {len(merged_results)} results"
            )
            
            return merged_results
            
        except Exception as e:
            self.logger.error(f"Error performing hybrid search: {str(e)}")
            return []
    
    def rerank_results(self, query: str,
                       results: List[SearchResult],
                       top_k: Optional[int] = None,
                       rerank_func: Optional[Callable] = None
                       ) -> List[SearchResult]:
        """
        Rerank search results for better relevance.
        
        Args:
            query: Original search query
            results: List of search results to rerank
            top_k: Number of results to return (None for all)
            rerank_func: Custom reranking function
            
        Returns:
            Reranked list of SearchResult objects
        """
        try:
            if not results:
                return []
            
            # Use custom rerank function if provided
            if rerank_func:
                reranked = rerank_func(query, results)
                return reranked[:top_k] if top_k else reranked
            
            # Default reranking based on multiple factors
            query_lower = query.lower()
            query_terms = set(query_lower.split())
            
            for result in results:
                # Calculate additional relevance factors
                content_lower = result.content.lower()
                
                # Exact phrase match bonus
                exact_match_bonus = (0.2 if query_lower in content_lower
                                     else 0.0)
                
                # Term frequency bonus
                term_matches = sum(1 for term in query_terms
                                   if term in content_lower)
                term_bonus = min(0.3, term_matches * 0.05)
                
                # Position bonus (prefer matches at beginning)
                position_bonus = 0.0
                if query_lower in content_lower:
                    position = content_lower.find(query_lower)
                    position_bonus = 0.1 * (
                        1.0 - position / len(content_lower)
                    )
                
                # File type bonus (configurable)
                file_type_bonus = 0.0
                if result.file_type in ['pdf', 'docx']:
                    file_type_bonus = 0.05
                
                # Combine with original score
                boost = (exact_match_bonus + term_bonus +
                         position_bonus + file_type_bonus)
                result.score = min(1.0, result.score + boost)
            
            # Sort by new scores
            results.sort(key=lambda x: x.score, reverse=True)
            
            return results[:top_k] if top_k else results
            
        except Exception as e:
            self.logger.error(f"Error reranking results: {str(e)}")
            return results
    
    def _retrieve_all_embeddings(self,
                                 file_types: Optional[List[str]] = None
                                 ) -> List[Dict[str, Any]]:
        """
        Retrieve all embeddings from the database.
        
        Args:
            file_types: Optional filter by file types
            
        Returns:
            List of embedding data dictionaries
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query
                query = '''
                    SELECT 
                        e.id as embedding_id,
                        e.chunk_id,
                        e.embedding_vector,
                        e.model_name,
                        c.file_id,
                        c.chunk_index,
                        c.content,
                        c.start_pos,
                        c.end_pos,
                        c.metadata as chunk_metadata,
                        f.file_path,
                        f.file_type
                    FROM file_embeddings e
                    JOIN file_chunks c ON e.chunk_id = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                '''
                
                params = []
                if file_types:
                    placeholders = ','.join(['?' for _ in file_types])
                    query += f' AND f.file_type IN ({placeholders})'
                    params.extend(file_types)
                
                cursor.execute(query, params)
                
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result_dict = dict(zip(columns, row))
                    
                    # Parse JSON metadata if present
                    if result_dict.get('chunk_metadata'):
                        try:
                            result_dict['chunk_metadata'] = json.loads(
                                result_dict['chunk_metadata']
                            )
                        except json.JSONDecodeError:
                            result_dict['chunk_metadata'] = None
                    
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error retrieving embeddings: {str(e)}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract keywords from query text.
        Simple implementation - can be enhanced with NLP.
        
        Args:
            query: Query text
            
        Returns:
            List of keywords
        """
        # Remove punctuation and convert to lowercase
        cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into words
        words = cleaned.split()
        
        # Remove common stop words (basic list)
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'will', 'with', 'the', 'this',
            'but', 'they', 'have', 'had', 'what', 'when', 'where', 'who',
            'which', 'why', 'how'
        }
        
        keywords = [word for word in words
                    if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _search_by_keywords(self, keywords: List[str],
                            file_types: Optional[List[str]] = None
                            ) -> List[Dict[str, Any]]:
        """
        Search chunks by keywords using SQL LIKE.
        
        Args:
            keywords: List of keywords to search
            file_types: Optional filter by file types
            
        Returns:
            List of matching chunks with relevance scores
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with LIKE conditions for each keyword
                query = '''
                    SELECT 
                        c.id as chunk_id,
                        c.file_id,
                        c.chunk_index,
                        c.content,
                        c.start_pos,
                        c.end_pos,
                        c.metadata as chunk_metadata,
                        f.file_path,
                        f.file_type,
                        (
                '''
                
                # Add relevance scoring based on keyword matches
                like_conditions = []
                params = []
                
                for keyword in keywords:
                    like_condition = (
                        "CASE WHEN LOWER(c.content) LIKE ? "
                        "THEN 1 ELSE 0 END"
                    )
                    like_conditions.append(like_condition)
                    params.append(f'%{keyword}%')
                
                query += ' + '.join(like_conditions)
                query += '''
                        ) as match_count
                    FROM file_chunks c
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                    AND (
                '''
                
                # Add WHERE conditions
                where_conditions = []
                for keyword in keywords:
                    where_conditions.append("LOWER(c.content) LIKE ?")
                    params.append(f'%{keyword}%')
                
                query += ' OR '.join(where_conditions)
                query += ')'
                
                # Add file type filter if specified
                if file_types:
                    placeholders = ','.join(['?' for _ in file_types])
                    query += f' AND f.file_type IN ({placeholders})'
                    params.extend(file_types)
                
                query += ' ORDER BY match_count DESC, c.chunk_index ASC'
                
                cursor.execute(query, params)
                
                # Convert to list of dictionaries with relevance scores
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                max_match_count = len(keywords)
                
                for row in cursor.fetchall():
                    result_dict = dict(zip(columns, row))
                    
                    # Calculate relevance score (0-1)
                    match_count = result_dict.pop('match_count', 0)
                    result_dict['relevance_score'] = (
                        match_count / max_match_count
                    )
                    
                    # Parse JSON metadata if present
                    if result_dict.get('chunk_metadata'):
                        try:
                            result_dict['chunk_metadata'] = json.loads(
                                result_dict['chunk_metadata']
                            )
                        except json.JSONDecodeError:
                            result_dict['chunk_metadata'] = None
                    
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error searching by keywords: {str(e)}")
            return []
    
    def _merge_search_results(self, vector_results: List[SearchResult],
                              keyword_results: List[SearchResult],
                              vector_weight: float,
                              keyword_weight: float) -> List[SearchResult]:
        """
        Merge vector and keyword search results with weighted scores.
        
        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search
            vector_weight: Weight for vector scores
            keyword_weight: Weight for keyword scores
            
        Returns:
            Merged and sorted list of SearchResult objects
        """
        # Create a dictionary to store merged results by chunk_id
        merged_dict = {}
        
        # Add vector results
        for result in vector_results:
            merged_dict[result.chunk_id] = SearchResult(
                chunk_id=result.chunk_id,
                file_id=result.file_id,
                file_path=result.file_path,
                content=result.content,
                score=result.score * vector_weight,
                chunk_index=result.chunk_index,
                start_pos=result.start_pos,
                end_pos=result.end_pos,
                file_type=result.file_type,
                metadata=result.metadata,
                match_type='hybrid'
            )
        
        # Add or update with keyword results
        for result in keyword_results:
            if result.chunk_id in merged_dict:
                # Combine scores
                merged_dict[result.chunk_id].score += (
                    result.score * keyword_weight
                )
            else:
                # Add new result
                merged_dict[result.chunk_id] = SearchResult(
                    chunk_id=result.chunk_id,
                    file_id=result.file_id,
                    file_path=result.file_path,
                    content=result.content,
                    score=result.score * keyword_weight,
                    chunk_index=result.chunk_index,
                    start_pos=result.start_pos,
                    end_pos=result.end_pos,
                    file_type=result.file_type,
                    metadata=result.metadata,
                    match_type='hybrid'
                )
        
        # Convert to list and sort by score
        merged_results = list(merged_dict.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results