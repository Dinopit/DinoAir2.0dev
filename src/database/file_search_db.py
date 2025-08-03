"""
FileSearchDB class for DinoAir 2.0
Provides database operations for RAG-powered file search functionality
with vector storage and retrieval capabilities.
"""

import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..utils.logger import Logger
from .initialize_db import DatabaseManager


class FileSearchDB:
    """
    Handles all database operations for the RAG file search system.
    Manages indexed files, text chunks, vector embeddings, and search settings.
    """
    
    def __init__(self, user_name: Optional[str] = None):
        """
        Initialize FileSearchDB with user-specific database connection.
        
        Args:
            user_name: Username for user-specific database.
                      Defaults to "default_user"
        """
        self.logger = Logger()
        self.db_manager = DatabaseManager(user_name)
        self.user_name = user_name or "default_user"
        
        # Ensure database is initialized
        self._ensure_database_ready()
    
    def _ensure_database_ready(self) -> None:
        """Ensure database is initialized with proper schema"""
        try:
            # Create tables if they don't exist
            self.create_tables()
            self.logger.info("File search database initialized successfully")
        except Exception as e:
            self.logger.error(
                f"Error ensuring file search database readiness: {str(e)}"
            )
            raise
    
    def _get_connection(self):
        """Get database connection for file search operations"""
        return self.db_manager.get_file_search_connection()
    
    def create_tables(self) -> bool:
        """
        Create all necessary tables for the file search system.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Table for tracking indexed files
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS indexed_files (
                        id TEXT PRIMARY KEY,
                        file_path TEXT UNIQUE NOT NULL,
                        file_hash TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        modified_date DATETIME NOT NULL,
                        indexed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        file_type TEXT,
                        status TEXT DEFAULT 'active',
                        metadata TEXT
                    )
                ''')
                
                # Table for storing text chunks
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_chunks (
                        id TEXT PRIMARY KEY,
                        file_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        start_pos INTEGER NOT NULL,
                        end_pos INTEGER NOT NULL,
                        metadata TEXT,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (file_id) REFERENCES indexed_files (id)
                            ON DELETE CASCADE,
                        UNIQUE(file_id, chunk_index)
                    )
                ''')
                
                # Table for storing vector embeddings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_embeddings (
                        id TEXT PRIMARY KEY,
                        chunk_id TEXT UNIQUE NOT NULL,
                        embedding_vector TEXT NOT NULL,  -- JSON array
                        model_name TEXT NOT NULL,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (chunk_id) REFERENCES file_chunks (id)
                            ON DELETE CASCADE
                    )
                ''')
                
                # Table for search settings (directory limiters, etc.)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_settings (
                        id TEXT PRIMARY KEY,
                        setting_name TEXT UNIQUE NOT NULL,
                        setting_value TEXT NOT NULL,
                        created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        modified_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_indexed_files_path ON indexed_files(file_path)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_indexed_files_status ON indexed_files(status)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_indexed_files_type ON indexed_files(file_type)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_file_chunks_file_id ON file_chunks(file_id)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_file_chunks_content ON file_chunks(content)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_file_embeddings_chunk_id
                    ON file_embeddings(chunk_id)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS
                    idx_search_settings_name
                    ON search_settings(setting_name)''')
                
                conn.commit()
                self.logger.info("File search tables created successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Error creating file search tables: {str(e)}")
            return False
    
    def add_indexed_file(self, file_path: str, file_hash: str,
                         size: int, modified_date: datetime,
                         file_type: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None
                         ) -> Dict[str, Any]:
        """
        Add a new file to the index.
        
        Args:
            file_path: Path to the file
            file_hash: Hash of the file content
            size: File size in bytes
            modified_date: Last modification date of the file
            file_type: Type of the file (e.g., 'pdf', 'txt', 'docx')
            metadata: Additional metadata as dictionary
            
        Returns:
            Dict with success status and file_id or error message
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Generate unique ID
                file_id = self._generate_id(file_path)
                
                # Convert metadata to JSON if provided
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO indexed_files
                    (id, file_path, file_hash, size, modified_date, 
                     file_type, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file_id,
                    file_path,
                    file_hash,
                    size,
                    modified_date.isoformat(),
                    file_type,
                    'active',
                    metadata_json
                ))
                
                conn.commit()
                
                self.logger.info(f"Indexed file: {file_path}")
                return {
                    "success": True,
                    "file_id": file_id,
                    "message": "File indexed successfully"
                }
                
        except Exception as e:
            self.logger.error(f"Error indexing file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to index file: {str(e)}"
            }
    
    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file information by path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, file_path, file_hash, size, modified_date,
                           indexed_date, file_type, status, metadata
                    FROM indexed_files
                    WHERE file_path = ? AND status = 'active'
                ''', (file_path,))
                
                row = cursor.fetchone()
                
                if row:
                    file_info = {
                        'id': row[0],
                        'file_path': row[1],
                        'file_hash': row[2],
                        'size': row[3],
                        'modified_date': row[4],
                        'indexed_date': row[5],
                        'file_type': row[6],
                        'status': row[7],
                        'metadata': json.loads(row[8]) if row[8] else None
                    }
                    
                    self.logger.debug(f"Retrieved file info for: {file_path}")
                    return file_info
                else:
                    self.logger.debug(f"File not found: {file_path}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error retrieving file {file_path}: {str(e)}")
            return None
    
    def add_chunk(self, file_id: str, chunk_index: int, 
                  content: str, start_pos: int, end_pos: int,
                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a text chunk for a file.
        
        Args:
            file_id: ID of the parent file
            chunk_index: Index of the chunk (0-based)
            content: Text content of the chunk
            start_pos: Starting position in the original file
            end_pos: Ending position in the original file
            metadata: Additional metadata as dictionary
            
        Returns:
            Dict with success status and chunk_id or error message
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Generate unique chunk ID
                chunk_id = f"{file_id}_chunk_{chunk_index}"
                
                # Convert metadata to JSON if provided
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO file_chunks
                    (id, file_id, chunk_index, content, start_pos,
                     end_pos, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_id,
                    file_id,
                    chunk_index,
                    content,
                    start_pos,
                    end_pos,
                    metadata_json
                ))
                
                conn.commit()
                
                self.logger.debug(
                    f"Added chunk {chunk_index} for file {file_id}"
                )
                return {
                    "success": True,
                    "chunk_id": chunk_id,
                    "message": "Chunk added successfully"
                }
                
        except Exception as e:
            self.logger.error(
                f"Error adding chunk for file {file_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to add chunk: {str(e)}"
            }
    
    def add_embedding(self, chunk_id: str, embedding_vector: List[float],
                      model_name: str) -> Dict[str, Any]:
        """
        Store vector embedding for a chunk.
        
        Args:
            chunk_id: ID of the chunk
            embedding_vector: List of float values representing the embedding
            model_name: Name of the model used to generate the embedding
            
        Returns:
            Dict with success status and embedding_id or error message
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Generate unique embedding ID
                embedding_id = f"{chunk_id}_embedding"
                
                # Convert embedding vector to JSON
                embedding_json = json.dumps(embedding_vector)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO file_embeddings
                    (id, chunk_id, embedding_vector, model_name)
                    VALUES (?, ?, ?, ?)
                ''', (
                    embedding_id,
                    chunk_id,
                    embedding_json,
                    model_name
                ))
                
                conn.commit()
                
                self.logger.debug(f"Added embedding for chunk {chunk_id}")
                return {
                    "success": True,
                    "embedding_id": embedding_id,
                    "message": "Embedding stored successfully"
                }
                
        except Exception as e:
            self.logger.error(
                f"Error adding embedding for chunk {chunk_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to store embedding: {str(e)}"
            }
    
    def get_all_embeddings(self, file_types: Optional[List[str]] = None,
                           file_paths: Optional[List[str]] = None
                           ) -> List[Dict[str, Any]]:
        """
        Retrieve all embeddings with their metadata.
        
        Args:
            file_types: Optional filter by file types
            file_paths: Optional filter by specific file paths
            
        Returns:
            List of dictionaries with embedding data
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT
                        e.id as embedding_id,
                        e.chunk_id,
                        e.embedding_vector,
                        e.model_name,
                        e.created_date as embedding_created,
                        c.file_id,
                        c.chunk_index,
                        c.content,
                        c.start_pos,
                        c.end_pos,
                        c.metadata as chunk_metadata,
                        f.file_path,
                        f.file_type,
                        f.size as file_size,
                        f.modified_date,
                        f.indexed_date
                    FROM file_embeddings e
                    JOIN file_chunks c ON e.chunk_id = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                '''
                
                params = []
                conditions = []
                
                if file_types:
                    placeholders = ','.join(['?' for _ in file_types])
                    conditions.append(f'f.file_type IN ({placeholders})')
                    params.extend(file_types)
                
                if file_paths:
                    placeholders = ','.join(['?' for _ in file_paths])
                    conditions.append(f'f.file_path IN ({placeholders})')
                    params.extend(file_paths)
                
                if conditions:
                    query += ' AND ' + ' AND '.join(conditions)
                
                query += ' ORDER BY f.file_path, c.chunk_index'
                
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result_dict = dict(zip(columns, row))
                    
                    # Parse JSON fields
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
    
    def search_by_keywords(self, keywords: List[str],
                           limit: int = 10,
                           file_types: Optional[List[str]] = None,
                           file_paths: Optional[List[str]] = None
                           ) -> List[Dict[str, Any]]:
        """
        Search chunks by keywords using SQL LIKE.
        
        Args:
            keywords: List of keywords to search for
            limit: Maximum number of results
            file_types: Optional filter by file types
            file_paths: Optional filter by specific file paths
            
        Returns:
            List of matching chunks with relevance scores
        """
        try:
            if not keywords:
                return []
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with LIKE conditions
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
                        f.size as file_size,
                        (
                '''
                
                # Add relevance scoring
                like_conditions = []
                params = []
                
                for keyword in keywords:
                    like_condition = (
                        "CASE WHEN LOWER(c.content) LIKE ? "
                        "THEN 1 ELSE 0 END"
                    )
                    like_conditions.append(like_condition)
                    params.append(f'%{keyword.lower()}%')
                
                query += ' + '.join(like_conditions)
                query += '''
                        ) as match_count
                    FROM file_chunks c
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                    AND (
                '''
                
                # Add WHERE conditions for keywords
                where_conditions = []
                for keyword in keywords:
                    where_conditions.append("LOWER(c.content) LIKE ?")
                    params.append(f'%{keyword.lower()}%')
                
                query += ' OR '.join(where_conditions)
                query += ')'
                
                # Add optional filters
                if file_types:
                    placeholders = ','.join(['?' for _ in file_types])
                    query += f' AND f.file_type IN ({placeholders})'
                    params.extend(file_types)
                
                if file_paths:
                    placeholders = ','.join(['?' for _ in file_paths])
                    query += f' AND f.file_path IN ({placeholders})'
                    params.extend(file_paths)
                
                query += '''
                    ORDER BY match_count DESC, c.chunk_index ASC
                    LIMIT ?
                '''
                params.append(limit)
                
                cursor.execute(query, params)
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                max_match_count = len(keywords)
                
                for row in cursor.fetchall():
                    result_dict = dict(zip(columns, row))
                    
                    # Calculate relevance score
                    match_count = result_dict.pop('match_count', 0)
                    result_dict['relevance_score'] = (
                        match_count / max_match_count if max_match_count > 0
                        else 0.0
                    )
                    
                    # Parse JSON metadata
                    if result_dict.get('chunk_metadata'):
                        try:
                            result_dict['chunk_metadata'] = json.loads(
                                result_dict['chunk_metadata']
                            )
                        except json.JSONDecodeError:
                            result_dict['chunk_metadata'] = None
                    
                    results.append(result_dict)
                
                self.logger.info(
                    f"Keyword search for {keywords} returned "
                    f"{len(results)} results"
                )
                return results
                
        except Exception as e:
            self.logger.error(f"Error in keyword search: {str(e)}")
            return []
    
    def get_embeddings_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Get all embeddings for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of embeddings with chunk information
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT
                        e.id as embedding_id,
                        e.chunk_id,
                        e.embedding_vector,
                        e.model_name,
                        c.chunk_index,
                        c.content,
                        c.start_pos,
                        c.end_pos,
                        c.metadata as chunk_metadata
                    FROM file_embeddings e
                    JOIN file_chunks c ON e.chunk_id = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.file_path = ? AND f.status = 'active'
                    ORDER BY c.chunk_index
                ''', (file_path,))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result_dict = dict(zip(columns, row))
                    
                    # Parse JSON metadata
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
            self.logger.error(
                f"Error getting embeddings for file {file_path}: {str(e)}"
            )
            return []
    
    def batch_add_embeddings(self,
                             embeddings_data: List[Dict[str, Any]]
                             ) -> Dict[str, Any]:
        """
        Add multiple embeddings in a single transaction.
        
        Args:
            embeddings_data: List of dictionaries containing:
                - chunk_id: ID of the chunk
                - embedding_vector: List of float values
                - model_name: Name of the model used
                
        Returns:
            Dict with success status and statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                success_count = 0
                failed_count = 0
                
                for data in embeddings_data:
                    try:
                        embedding_id = f"{data['chunk_id']}_embedding"
                        embedding_json = json.dumps(data['embedding_vector'])
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO file_embeddings
                            (id, chunk_id, embedding_vector, model_name)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            embedding_id,
                            data['chunk_id'],
                            embedding_json,
                            data['model_name']
                        ))
                        
                        success_count += 1
                        
                    except Exception as e:
                        self.logger.error(
                            f"Error adding embedding for chunk "
                            f"{data.get('chunk_id')}: {str(e)}"
                        )
                        failed_count += 1
                
                conn.commit()
                
                self.logger.info(
                    f"Batch added {success_count} embeddings "
                    f"({failed_count} failed)"
                )
                
                return {
                    "success": True,
                    "embeddings_added": success_count,
                    "embeddings_failed": failed_count,
                    "total": len(embeddings_data)
                }
                
        except Exception as e:
            self.logger.error(f"Error in batch add embeddings: {str(e)}")
            return {
                "success": False,
                "error": f"Batch add failed: {str(e)}"
            }
    
    def clear_embeddings_for_file(self, file_path: str) -> Dict[str, Any]:
        """
        Clear all embeddings for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict with success status and number of embeddings removed
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get count of embeddings to be deleted
                cursor.execute('''
                    SELECT COUNT(*) FROM file_embeddings e
                    JOIN file_chunks c ON e.chunk_id = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.file_path = ?
                ''', (file_path,))
                
                count = cursor.fetchone()[0]
                
                # Delete embeddings
                cursor.execute('''
                    DELETE FROM file_embeddings
                    WHERE chunk_id IN (
                        SELECT c.id FROM file_chunks c
                        JOIN indexed_files f ON c.file_id = f.id
                        WHERE f.file_path = ?
                    )
                ''', (file_path,))
                
                conn.commit()
                
                self.logger.info(
                    f"Cleared {count} embeddings for file: {file_path}"
                )
                
                return {
                    "success": True,
                    "embeddings_removed": count
                }
                
        except Exception as e:
            self.logger.error(
                f"Error clearing embeddings for {file_path}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to clear embeddings: {str(e)}"
            }
    
    def update_search_settings(self, setting_name: str, 
                               setting_value: Any) -> Dict[str, Any]:
        """
        Update or create a search setting.
        
        Args:
            setting_name: Name of the setting (e.g., 'search_directories')
            setting_value: Value of the setting (will be JSON serialized)
            
        Returns:
            Dict with success status and message
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Generate unique ID
                setting_id = self._generate_id(setting_name)
                
                # Convert value to JSON
                value_json = json.dumps(setting_value)
                
                # Check if setting exists
                cursor.execute('''
                    SELECT id FROM search_settings WHERE setting_name = ?
                ''', (setting_name,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing setting
                    cursor.execute('''
                        UPDATE search_settings
                        SET setting_value = ?,
                            modified_date = CURRENT_TIMESTAMP
                        WHERE setting_name = ?
                    ''', (value_json, setting_name))
                    action = "updated"
                else:
                    # Create new setting
                    cursor.execute('''
                        INSERT INTO search_settings
                        (id, setting_name, setting_value)
                        VALUES (?, ?, ?)
                    ''', (setting_id, setting_name, value_json))
                    action = "created"
                
                conn.commit()
                
                self.logger.info(f"Search setting '{setting_name}' {action}")
                return {
                    "success": True,
                    "message": f"Setting {action} successfully"
                }
                
        except Exception as e:
            self.logger.error(
                f"Error updating setting {setting_name}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Failed to update setting: {str(e)}"
            }
    
    def get_search_settings(self,
                            setting_name: Optional[str] = None
                            ) -> Dict[str, Any]:
        """
        Retrieve search settings.
        
        Args:
            setting_name: Specific setting to retrieve (optional).
                         If None, returns all settings.
            
        Returns:
            Dictionary of settings or specific setting value
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if setting_name:
                    # Get specific setting
                    cursor.execute('''
                        SELECT setting_value, created_date, modified_date
                        FROM search_settings
                        WHERE setting_name = ?
                    ''', (setting_name,))
                    
                    row = cursor.fetchone()
                    if row:
                        return {
                            "success": True,
                            "setting_name": setting_name,
                            "setting_value": json.loads(row[0]),
                            "created_date": row[1],
                            "modified_date": row[2]
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Setting '{setting_name}' not found"
                        }
                else:
                    # Get all settings
                    cursor.execute('''
                        SELECT setting_name, setting_value,
                               created_date, modified_date
                        FROM search_settings
                        ORDER BY setting_name
                    ''')
                    
                    settings = {}
                    for row in cursor.fetchall():
                        settings[row[0]] = {
                            "value": json.loads(row[1]),
                            "created_date": row[2],
                            "modified_date": row[3]
                        }
                    
                    return {
                        "success": True,
                        "settings": settings
                    }
                    
        except Exception as e:
            self.logger.error(f"Error retrieving settings: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to retrieve settings: {str(e)}"
            }
    
    def get_indexed_files_stats(self) -> Dict[str, Any]:
        """
        Get statistics about indexed files.
        
        Returns:
            Dictionary with file indexing statistics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total indexed files
                cursor.execute('''
                    SELECT COUNT(*) FROM indexed_files WHERE status = 'active'
                ''')
                stats['total_files'] = cursor.fetchone()[0]
                
                # Files by type
                cursor.execute('''
                    SELECT file_type, COUNT(*) 
                    FROM indexed_files 
                    WHERE status = 'active'
                    GROUP BY file_type
                ''')
                stats['files_by_type'] = {
                    row[0] or 'unknown': row[1] for row in cursor.fetchall()
                }
                
                # Total size
                cursor.execute('''
                    SELECT SUM(size) FROM indexed_files WHERE status = 'active'
                ''')
                total_size = cursor.fetchone()[0] or 0
                stats['total_size_bytes'] = total_size
                stats['total_size_mb'] = round(total_size / (1024 * 1024), 2)
                
                # Total chunks
                cursor.execute('''
                    SELECT COUNT(*) FROM file_chunks c
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                ''')
                stats['total_chunks'] = cursor.fetchone()[0]
                
                # Total embeddings
                cursor.execute('''
                    SELECT COUNT(*) FROM file_embeddings e
                    JOIN file_chunks c ON e.chunk_id = c.id
                    JOIN indexed_files f ON c.file_id = f.id
                    WHERE f.status = 'active'
                ''')
                stats['total_embeddings'] = cursor.fetchone()[0]
                
                # Last indexed date
                cursor.execute('''
                    SELECT MAX(indexed_date) FROM indexed_files
                ''')
                stats['last_indexed_date'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting file stats: {str(e)}")
            return {}
    
    def remove_file_from_index(self, file_path: str) -> Dict[str, Any]:
        """
        Remove a file and its associated data from the index.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            Dict with success status and message
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get file ID
                cursor.execute('''
                    SELECT id FROM indexed_files WHERE file_path = ?
                ''', (file_path,))
                
                row = cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "error": "File not found in index"
                    }
                
                file_id = row[0]
                
                # Due to CASCADE, deleting the file will also delete
                # chunks and embeddings
                cursor.execute('''
                    DELETE FROM indexed_files WHERE id = ?
                ''', (file_id,))
                
                conn.commit()
                
                self.logger.info(f"Removed file from index: {file_path}")
                return {
                    "success": True,
                    "message": "File removed from index successfully"
                }
                
        except Exception as e:
            self.logger.error(f"Error removing file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to remove file: {str(e)}"
            }
    
    def _generate_id(self, seed: str) -> str:
        """
        Generate a unique ID based on a seed string.
        
        Args:
            seed: Seed string for ID generation
            
        Returns:
            Unique ID string
        """
        timestamp = datetime.now().isoformat()
        combined = f"{seed}_{timestamp}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def add_allowed_directory(self, directory: str) -> Dict[str, Any]:
        """
        Add a directory to the allowed directories list.
        
        Args:
            directory: Directory path to add
            
        Returns:
            Dict with success status and message
        """
        try:
            # Get current allowed directories
            current_result = self.get_search_settings("allowed_directories")
            if current_result.get("success"):
                current_dirs = current_result.get("setting_value", [])
            else:
                current_dirs = []
            
            # Add new directory if not already present
            if directory not in current_dirs:
                current_dirs.append(directory)
                
                # Update settings
                return self.update_search_settings(
                    "allowed_directories", current_dirs
                )
            else:
                return {
                    "success": True,
                    "message": "Directory already in allowed list"
                }
                
        except Exception as e:
            self.logger.error(f"Error adding allowed directory: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to add directory: {str(e)}"
            }
    
    def remove_allowed_directory(self, directory: str) -> Dict[str, Any]:
        """
        Remove a directory from the allowed directories list.
        
        Args:
            directory: Directory path to remove
            
        Returns:
            Dict with success status and message
        """
        try:
            # Get current allowed directories
            current_result = self.get_search_settings("allowed_directories")
            if not current_result.get("success"):
                return {
                    "success": False,
                    "error": "No allowed directories found"
                }
            
            current_dirs = current_result.get("setting_value", [])
            
            # Remove directory if present
            if directory in current_dirs:
                current_dirs.remove(directory)
                
                # Update settings
                return self.update_search_settings(
                    "allowed_directories", current_dirs
                )
            else:
                return {
                    "success": False,
                    "error": "Directory not in allowed list"
                }
                
        except Exception as e:
            self.logger.error(f"Error removing allowed directory: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to remove directory: {str(e)}"
            }
    
    def add_excluded_directory(self, directory: str) -> Dict[str, Any]:
        """
        Add a directory to the excluded directories list.
        
        Args:
            directory: Directory path to add
            
        Returns:
            Dict with success status and message
        """
        try:
            # Get current excluded directories
            current_result = self.get_search_settings("excluded_directories")
            if current_result.get("success"):
                current_dirs = current_result.get("setting_value", [])
            else:
                current_dirs = []
            
            # Add new directory if not already present
            if directory not in current_dirs:
                current_dirs.append(directory)
                
                # Update settings
                return self.update_search_settings(
                    "excluded_directories", current_dirs
                )
            else:
                return {
                    "success": True,
                    "message": "Directory already in excluded list"
                }
                
        except Exception as e:
            self.logger.error(f"Error adding excluded directory: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to add directory: {str(e)}"
            }
    
    def remove_excluded_directory(self, directory: str) -> Dict[str, Any]:
        """
        Remove a directory from the excluded directories list.
        
        Args:
            directory: Directory path to remove
            
        Returns:
            Dict with success status and message
        """
        try:
            # Get current excluded directories
            current_result = self.get_search_settings("excluded_directories")
            if not current_result.get("success"):
                return {
                    "success": False,
                    "error": "No excluded directories found"
                }
            
            current_dirs = current_result.get("setting_value", [])
            
            # Remove directory if present
            if directory in current_dirs:
                current_dirs.remove(directory)
                
                # Update settings
                return self.update_search_settings(
                    "excluded_directories", current_dirs
                )
            else:
                return {
                    "success": False,
                    "error": "Directory not in excluded list"
                }
                
        except Exception as e:
            self.logger.error(f"Error removing excluded directory: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to remove directory: {str(e)}"
            }
    
    def get_directory_settings(self) -> Dict[str, Any]:
        """
        Get all directory settings (allowed and excluded).
        
        Returns:
            Dict containing allowed and excluded directories
        """
        try:
            # Get allowed directories
            allowed_result = self.get_search_settings("allowed_directories")
            allowed_dirs = []
            if allowed_result.get("success"):
                allowed_dirs = allowed_result.get("setting_value", [])
            
            # Get excluded directories
            excluded_result = self.get_search_settings("excluded_directories")
            excluded_dirs = []
            if excluded_result.get("success"):
                excluded_dirs = excluded_result.get("setting_value", [])
            
            return {
                "success": True,
                "allowed_directories": allowed_dirs,
                "excluded_directories": excluded_dirs,
                "total_allowed": len(allowed_dirs),
                "total_excluded": len(excluded_dirs)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting directory settings: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get directory settings: {str(e)}"
            }
    
    def optimize_database(self) -> Dict[str, Any]:
        """
        Optimize database for better search performance.
        
        Returns:
            Dict with optimization results
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Analyze tables to update query planner statistics
                cursor.execute("ANALYZE indexed_files")
                cursor.execute("ANALYZE file_chunks")
                cursor.execute("ANALYZE file_embeddings")
                
                # Vacuum to reclaim space
                conn.execute("VACUUM")
                
                # Get database statistics
                cursor.execute('''
                    SELECT
                        name,
                        COUNT(*) as row_count
                    FROM sqlite_master
                    WHERE type='table' AND name IN (
                        'indexed_files', 'file_chunks',
                        'file_embeddings', 'search_settings'
                    )
                    GROUP BY name
                ''')
                
                stats = {}
                for row in cursor.fetchall():
                    table_name = row[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    stats[table_name] = cursor.fetchone()[0]
                
                self.logger.info("Database optimization completed")
                
                return {
                    "success": True,
                    "message": "Database optimized successfully",
                    "table_stats": stats
                }
                
        except Exception as e:
            self.logger.error(f"Error optimizing database: {str(e)}")
            return {
                "success": False,
                "error": f"Optimization failed: {str(e)}"
            }