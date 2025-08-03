"""
Context Provider for RAG Integration
Provides relevant file content for chat queries using RAG search capabilities.
"""

import os
from typing import List, Dict, Any, Optional, Tuple

from .vector_search import VectorSearchEngine
from .file_processor import FileProcessor
from ..database.file_search_db import FileSearchDB
from ..utils.logger import Logger


class ContextProvider:
    """
    Provides context from indexed files for chat queries.
    Uses the RAG search engine to find relevant content.
    """
    
    def __init__(self, user_name: str = "default_user"):
        """
        Initialize the context provider.
        
        Args:
            user_name: Username for database and search operations
        """
        self.user_name = user_name
        self.logger = Logger()
        
        # Initialize RAG components
        self.search_engine = VectorSearchEngine(user_name)
        self.file_search_db = FileSearchDB(user_name)
        
        # Configuration
        self.max_context_length = 2000  # Maximum characters for context
        self.max_results = 5  # Maximum number of search results to include
        self.min_score_threshold = 0.5  # Minimum relevance score
        
    def get_context_for_query(
        self,
        query: str,
        file_types: Optional[List[str]] = None,
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relevant file context for a given query.
        
        Args:
            query: The search query
            file_types: Optional list of file extensions to filter
            max_results: Optional maximum number of results
            
        Returns:
            List of context items with file info and content
        """
        try:
            # Use hybrid search for best results
            results = self.search_engine.hybrid_search(
                query=query,
                top_k=max_results or self.max_results,
                file_types=file_types,
                rerank=True
            )
            
            # Filter by score threshold
            filtered_results = [
                r for r in results 
                if r.score >= self.min_score_threshold
            ]
            
            # Build context items
            context_items = []
            for result in filtered_results:
                context_item = {
                    'file_path': result.file_path,
                    'file_name': os.path.basename(result.file_path),
                    'content': result.content,
                    'chunk_index': result.chunk_index,
                    'score': result.score,
                    'match_type': result.match_type
                }
                
                # Add file metadata if available
                file_info = self.file_search_db.get_file_by_path(
                    result.file_path
                )
                if file_info:
                    context_item['file_type'] = file_info.get('file_type')
                    context_item['file_size'] = file_info.get('file_size')
                    context_item['last_modified'] = file_info.get(
                        'last_modified'
                    )
                
                context_items.append(context_item)
            
            return context_items
            
        except Exception as e:
            self.logger.error(f"Failed to get context: {str(e)}")
            return []
    
    def format_context_for_chat(
        self,
        context_items: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> str:
        """
        Format context items into a string suitable for chat prompts.
        
        Args:
            context_items: List of context items from get_context_for_query
            include_metadata: Whether to include file metadata
            
        Returns:
            Formatted context string
        """
        if not context_items:
            return ""
        
        formatted_parts = []
        total_length = 0
        
        for i, item in enumerate(context_items, 1):
            # Build context part
            part = f"\n--- Context {i} ---\n"
            
            if include_metadata:
                part += f"File: {item['file_name']}\n"
                part += f"Relevance: {item['score']:.1%}\n"
                
                if item.get('file_type'):
                    part += f"Type: {item['file_type']}\n"
                
            part += f"\nContent:\n{item['content']}\n"
            
            # Check length constraint
            if total_length + len(part) > self.max_context_length:
                # Truncate if needed
                remaining = self.max_context_length - total_length
                if remaining > 100:  # Only add if meaningful
                    part = part[:remaining] + "\n... (truncated)"
                    formatted_parts.append(part)
                break
            
            formatted_parts.append(part)
            total_length += len(part)
        
        return "\n".join(formatted_parts)
    
    def get_file_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file summary or None if not found
        """
        try:
            file_info = self.file_search_db.get_file_by_path(file_path)
            if not file_info:
                return None
            
            # Get chunks for this file using search
            # Since get_chunks_by_file doesn't exist, use search with file path
            results = self.search_engine.search(
                query="",  # Empty query to get all chunks
                file_types=[os.path.splitext(file_path)[1]],
                top_k=100  # Get many chunks
            )
            chunks = [r for r in results if r.file_path == file_path]
            
            # Build summary
            summary = {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'file_type': file_info.get('file_type'),
                'file_size': file_info.get('file_size'),
                'last_modified': file_info.get('last_modified'),
                'chunk_count': len(chunks),
                'total_content_length': sum(
                    len(chunk.content) for chunk in chunks
                )
            }
            
            # Add first chunk as preview
            if chunks:
                preview_content = chunks[0].content
                if len(preview_content) > 200:
                    preview_content = preview_content[:200] + "..."
                summary['preview'] = preview_content
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get file summary: {str(e)}")
            return None
    
    def search_related_files(
        self,
        file_path: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find files related to a given file based on content similarity.
        
        Args:
            file_path: Path to the reference file
            top_k: Number of related files to return
            
        Returns:
            List of tuples (file_path, similarity_score)
        """
        try:
            # Get content from the file
            file_info = self.file_search_db.get_file_by_path(file_path)
            if not file_info:
                return []
            
            # Get first chunk as representative content
            # Use search to get chunks for this file
            results = self.search_engine.search(
                query="",  # Empty query
                top_k=100
            )
            chunks = [r for r in results if r.file_path == file_path]
            if not chunks:
                return []
            
            # Search using first chunk content
            results = self.search_engine.search(
                query=chunks[0].content if chunks else "",
                top_k=top_k + 1  # +1 to exclude self
            )
            
            # Build related files list
            related_files = []
            seen_files = {file_path}  # Exclude self
            
            for result in results:
                if result.file_path not in seen_files:
                    related_files.append((result.file_path, result.score))
                    seen_files.add(result.file_path)
                
                if len(related_files) >= top_k:
                    break
            
            return related_files
            
        except Exception as e:
            self.logger.error(f"Failed to find related files: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about indexed content.
        
        Returns:
            Dictionary with indexing statistics
        """
        try:
            file_processor = FileProcessor(
                user_name=self.user_name,
                generate_embeddings=False
            )
            stats = file_processor.get_processing_stats()
            
            # Add search engine stats
            search_stats = {
                'vector_search_available': True,  # Always available
                'indexed_files': stats.get('total_files', 0),
                'indexed_chunks': stats.get('total_chunks', 0),
                'total_size': stats.get('total_size', 0)
            }
            
            return search_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {str(e)}")
            return {}