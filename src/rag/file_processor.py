"""
File processing orchestrator for DinoAir 2.0 RAG File Search system.
Coordinates text extraction, chunking, and database storage with security validation.
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Import DinoAir components
from ..utils.logger import Logger
from ..database.file_search_db import FileSearchDB

# Import RAG components
from .text_extractors import ExtractorFactory
from .file_chunker import FileChunker, TextChunk
from .embedding_generator import get_embedding_generator
from .directory_validator import DirectoryValidator


class FileProcessor:
    """
    Orchestrates the file processing pipeline:
    1. File validation and metadata extraction
    2. Text extraction using appropriate extractor
    3. Text chunking with configurable strategies
    4. Storage in the file search database
    """
    
    # Default processing settings
    DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    DEFAULT_EMBEDDING_BATCH_SIZE = 32
    
    def __init__(self,
                 user_name: Optional[str] = None,
                 max_file_size: Optional[int] = None,
                 chunk_size: Optional[int] = None,
                 chunk_overlap: Optional[int] = None,
                 generate_embeddings: bool = True,
                 embedding_batch_size: Optional[int] = None):
        """
        Initialize the FileProcessor.
        
        Args:
            user_name: Username for database operations
            max_file_size: Maximum file size to process in bytes
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
            generate_embeddings: Whether to generate embeddings for chunks
            embedding_batch_size: Batch size for embedding generation
        """
        self.logger = Logger()
        self.user_name = user_name
        
        # Initialize settings
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or self.DEFAULT_CHUNK_OVERLAP
        self.generate_embeddings = generate_embeddings
        self.embedding_batch_size = (
            embedding_batch_size or self.DEFAULT_EMBEDDING_BATCH_SIZE
        )
        
        # Initialize components
        self.db = FileSearchDB(user_name)
        self.extractor_factory = ExtractorFactory(self.max_file_size)
        self.chunker = FileChunker(
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap
        )
        
        # Initialize directory validator
        self.directory_validator = DirectoryValidator()
        self._load_directory_settings()
        
        # Initialize embedding generator if needed
        self._embedding_generator = None
        if self.generate_embeddings:
            self._embedding_generator = get_embedding_generator()
        
        self.logger.info(
            f"FileProcessor initialized with chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, max_file_size={self.max_file_size}"
        )
    
    def _load_directory_settings(self) -> None:
        """Load directory settings from database."""
        try:
            # Load allowed directories
            allowed_result = self.db.get_search_settings("allowed_directories")
            if allowed_result.get("success") and allowed_result.get("setting_value"):
                allowed_dirs = allowed_result["setting_value"]
                self.directory_validator.set_allowed_directories(allowed_dirs)
                self.logger.info(
                    f"Loaded {len(allowed_dirs)} allowed directories"
                )
            
            # Load excluded directories
            excluded_result = self.db.get_search_settings("excluded_directories")
            if excluded_result.get("success") and excluded_result.get("setting_value"):
                excluded_dirs = excluded_result["setting_value"]
                self.directory_validator.set_excluded_directories(excluded_dirs)
                self.logger.info(
                    f"Loaded {len(excluded_dirs)} excluded directories"
                )
                
        except Exception as e:
            self.logger.error(f"Error loading directory settings: {str(e)}")
            # Continue with default settings
    
    def process_file(self, file_path: str,
                     force_reprocess: bool = False,
                     store_in_db: bool = True,
                     progress_callback: Optional[
                         Callable[[str, int, int], None]
                     ] = None) -> Dict[str, Any]:
        """
        Process a single file through the extraction pipeline.
        
        Args:
            file_path: Path to the file to process
            force_reprocess: Force reprocessing even if file is already indexed
            store_in_db: Whether to store results in the database
            progress_callback: Callback for progress updates
                              (message, current, total)
            
        Returns:
            Dictionary containing:
                - success: bool
                - file_id: str (if successful)
                - chunks: List[TextChunk] (if successful)
                - error: str (if failed)
                - stats: processing statistics
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            # Validate directory access
            validation_result = self.directory_validator.validate_path(file_path)
            if not validation_result["valid"]:
                self.directory_validator.log_access_attempt(
                    file_path, False, validation_result["message"]
                )
                return {
                    "success": False,
                    "error": f"Access denied: {validation_result['message']}"
                }
            
            # Log successful access validation
            self.directory_validator.log_access_attempt(file_path, True)
            
            # Get file metadata
            file_info = self._get_file_metadata(file_path)
            
            # Check file size
            if file_info['size'] > self.max_file_size:
                return {
                    "success": False,
                    "error": f"File exceeds size limit: "
                             f"{file_info['size']} > {self.max_file_size}"
                }
            
            # Check if file is already indexed
            if not force_reprocess and store_in_db:
                existing_file = self.db.get_file_by_path(file_path)
                if (existing_file and
                        existing_file['file_hash'] == file_info['hash']):
                    self.logger.info(f"File already indexed: {file_path}")
                    return {
                        "success": True,
                        "file_id": existing_file['id'],
                        "chunks": [],  # Would need to retrieve from DB
                        "message": "File already indexed with same content",
                        "stats": {
                            "action": "skipped",
                            "reason": "already_indexed"
                        }
                    }
            
            # Detect file type and get extractor
            file_type = self._detect_file_type(file_path)
            extractor = self.extractor_factory.get_extractor(file_path)
            
            if not extractor:
                return {
                    "success": False,
                    "error": f"No extractor available for file type: "
                             f"{file_type}"
                }
            
            # Extract text
            self.logger.info(f"Extracting text from: {file_path}")
            extraction_result = extractor.extract_text(file_path)
            
            if not extraction_result['success']:
                return {
                    "success": False,
                    "error": extraction_result.get(
                        'error', 'Text extraction failed'
                    )
                }
            
            text = extraction_result['text']
            extraction_metadata = extraction_result.get('metadata', {})
            
            # Check if we got any text
            if not text or not text.strip():
                return {
                    "success": False,
                    "error": "No text content extracted from file"
                }
            
            # Chunk the text
            self.logger.info(f"Chunking text from: {file_path}")
            chunks = self._chunk_text(text, file_type, extraction_metadata)
            
            if not chunks:
                return {
                    "success": False,
                    "error": "Failed to create text chunks"
                }
            
            # Store in database if requested
            file_id = None
            embeddings_generated = 0
            
            if store_in_db:
                store_result = self._store_in_database(
                    file_path, file_info, file_type,
                    chunks, extraction_metadata,
                    progress_callback=progress_callback
                )
                
                if not store_result['success']:
                    return {
                        "success": False,
                        "error": store_result.get(
                            'error', 'Database storage failed'
                        )
                    }
                
                file_id = store_result['file_id']
                embeddings_generated = store_result.get(
                    'embeddings_generated', 0
                )
            
            # Prepare statistics
            stats = {
                "file_size": file_info['size'],
                "file_type": file_type,
                "text_length": len(text),
                "chunk_count": len(chunks),
                "embeddings_generated": embeddings_generated,
                "extraction_metadata": extraction_metadata,
                "processing_time": datetime.now().isoformat()
            }
            
            self.logger.info(
                f"Successfully processed {file_path}: "
                f"{len(chunks)} chunks created"
            )
            
            return {
                "success": True,
                "file_id": file_id,
                "chunks": chunks,
                "stats": stats
            }
            
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def process_directory(self, directory_path: str,
                          recursive: bool = True,
                          file_extensions: Optional[List[str]] = None,
                          force_reprocess: bool = False,
                          progress_callback: Optional[
                              Callable[[str, int, int], None]
                          ] = None) -> Dict[str, Any]:
        """
        Process all files in a directory.
        
        Args:
            directory_path: Path to the directory
            recursive: Whether to process subdirectories
            file_extensions: List of file extensions to process
                            (e.g., ['.txt', '.pdf'])
            force_reprocess: Force reprocessing of already indexed files
            progress_callback: Callback for progress updates
            
        Returns:
            Dictionary with processing results and statistics
        """
        try:
            if not os.path.isdir(directory_path):
                return {
                    "success": False,
                    "error": f"Directory not found: {directory_path}"
                }
            
            # Validate directory access
            validation_result = self.directory_validator.validate_path(
                directory_path
            )
            if not validation_result["valid"]:
                self.directory_validator.log_access_attempt(
                    directory_path, False, validation_result["message"]
                )
                return {
                    "success": False,
                    "error": f"Directory access denied: {validation_result['message']}"
                }
            
            # Get list of supported extensions if not specified
            if not file_extensions:
                file_extensions = (
                    self.extractor_factory.get_supported_extensions()
                )
            
            # Find all files to process
            all_files = self._find_files(
                directory_path, recursive, file_extensions
            )
            
            # Filter files based on directory access rules
            files_to_process = self.directory_validator.get_allowed_files(
                all_files
            )
            
            # Log filtered files
            filtered_count = len(all_files) - len(files_to_process)
            if filtered_count > 0:
                self.logger.info(
                    f"Filtered out {filtered_count} files due to "
                    "directory access restrictions"
                )
            
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
            
            # Process each file
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
                    "total_embeddings": 0
                }
            }
            
            for i, file_path in enumerate(files_to_process):
                self.logger.info(f"Processing file {file_path}")
                
                # Update progress
                if progress_callback:
                    progress_callback(
                        f"Processing {os.path.basename(file_path)}",
                        i + 1,
                        len(files_to_process)
                    )
                
                result = self.process_file(
                    file_path,
                    force_reprocess=force_reprocess,
                    store_in_db=True,
                    progress_callback=progress_callback
                )
                
                if result['success']:
                    if result.get('stats', {}).get('action') == 'skipped':
                        results['skipped_files'].append(file_path)
                        results['stats']['skipped'] += 1
                    else:
                        results['processed_files'].append({
                            'file_path': file_path,
                            'file_id': result.get('file_id'),
                            'chunk_count': len(result.get('chunks', []))
                        })
                        results['stats']['processed'] += 1
                        results['stats']['total_chunks'] += len(
                            result.get('chunks', [])
                        )
                        results['stats']['total_embeddings'] += result.get(
                            'stats', {}
                        ).get('embeddings_generated', 0)
                else:
                    results['failed_files'].append({
                        'file_path': file_path,
                        'error': result.get('error', 'Unknown error')
                    })
                    results['stats']['failed'] += 1
            
            # Update success status based on failures
            if results['stats']['failed'] > 0:
                results['success'] = False
                results['error'] = (
                    f"Failed to process {results['stats']['failed']} "
                    f"out of {results['stats']['total_files']} files"
                )
            
            return results
            
        except Exception as e:
            self.logger.error(
                f"Error processing directory {directory_path}: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def _get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata."""
        stat = os.stat(file_path)
        
        # Calculate file hash
        file_hash = self._calculate_file_hash(file_path)
        
        return {
            'path': file_path,
            'name': os.path.basename(file_path),
            'size': stat.st_size,
            'modified_date': datetime.fromtimestamp(stat.st_mtime),
            'hash': file_hash
        }
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file content."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension."""
        ext = Path(file_path).suffix.lower()
        
        # Map extensions to file types
        type_mapping = {
            '.txt': 'text',
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'doc',
            '.md': 'markdown',
            '.json': 'json',
            '.csv': 'csv',
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.go': 'go',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.rs': 'rust',
            '.ts': 'typescript',
            '.jsx': 'javascript-react',
            '.tsx': 'typescript-react'
        }
        
        return type_mapping.get(ext, ext.lstrip('.') if ext else 'unknown')
    
    def _chunk_text(self, text: str, file_type: str,
                    extraction_metadata: Dict[str, Any]) -> List[TextChunk]:
        """
        Chunk text using appropriate strategy based on file type.
        """
        # Determine chunking strategy based on file type
        if file_type in ['python', 'javascript', 'java', 'cpp', 'c', 
                         'csharp', 'ruby', 'go', 'php', 'swift', 
                         'kotlin', 'rust', 'typescript']:
            # Use code chunking for programming files
            language = extraction_metadata.get('language', file_type)
            return self.chunker.chunk_code(text, language)
        
        elif file_type == 'markdown':
            # Use paragraph chunking for markdown
            return self.chunker.chunk_by_paragraphs(text)
        
        elif file_type in ['pdf', 'docx']:
            # Use sentence chunking for documents
            return self.chunker.chunk_by_sentences(text)
        
        else:
            # Default to standard chunking with boundary respect
            return self.chunker.chunk_text(text, respect_boundaries=True)
    
    def _store_in_database(self, file_path: str,
                           file_info: Dict[str, Any],
                           file_type: str,
                           chunks: List[TextChunk],
                           extraction_metadata: Dict[str, Any],
                           progress_callback: Optional[
                               Callable[[str, int, int], None]
                           ] = None) -> Dict[str, Any]:
        """
        Store file and chunks in the database.
        """
        try:
            # Add file to index
            file_result = self.db.add_indexed_file(
                file_path=file_path,
                file_hash=file_info['hash'],
                size=file_info['size'],
                modified_date=file_info['modified_date'],
                file_type=file_type,
                metadata=extraction_metadata
            )
            
            if not file_result['success']:
                return file_result
            
            file_id = file_result['file_id']
            
            # Store chunks and generate embeddings if enabled
            embeddings_generated = 0
            chunk_ids = []
            chunk_texts = []
            
            # First, add all chunks to database
            for chunk in chunks:
                chunk_result = self.db.add_chunk(
                    file_id=file_id,
                    chunk_index=chunk.metadata.chunk_index,
                    content=chunk.content,
                    start_pos=chunk.metadata.start_pos,
                    end_pos=chunk.metadata.end_pos,
                    metadata={
                        'chunk_type': chunk.metadata.chunk_type,
                        'overlap_prev': chunk.metadata.overlap_with_previous,
                        'overlap_next': chunk.metadata.overlap_with_next,
                        'additional_info': chunk.metadata.additional_info
                    }
                )
                
                if not chunk_result['success']:
                    self.logger.error(
                        f"Failed to store chunk {chunk.metadata.chunk_index}: "
                        f"{chunk_result.get('error')}"
                    )
                else:
                    chunk_ids.append(chunk_result['chunk_id'])
                    chunk_texts.append(chunk.content)
            
            # Generate and store embeddings if enabled
            if (self.generate_embeddings and
                    self._embedding_generator and chunk_ids):
                embeddings_generated = self._generate_and_store_embeddings(
                    chunk_ids, chunk_texts, progress_callback
                )
            
            return {
                "success": True,
                "file_id": file_id,
                "embeddings_generated": embeddings_generated
            }
            
        except Exception as e:
            self.logger.error(f"Error storing in database: {str(e)}")
            return {
                "success": False,
                "error": f"Database storage error: {str(e)}"
            }
    
    def _find_files(self, directory_path: str,
                    recursive: bool,
                    file_extensions: List[str]) -> List[str]:
        """
        Find all files in directory matching the extensions.
        """
        files = []
        
        if recursive:
            for root, _, filenames in os.walk(directory_path):
                for filename in filenames:
                    if any(filename.lower().endswith(ext) 
                           for ext in file_extensions):
                        files.append(os.path.join(root, filename))
        else:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if (os.path.isfile(file_path) and 
                    any(filename.lower().endswith(ext) 
                        for ext in file_extensions)):
                    files.append(file_path)
        
        return sorted(files)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get overall processing statistics from the database.
        """
        return self.db.get_indexed_files_stats()
    
    def update_settings(self, **kwargs) -> None:
        """
        Update processor settings.
        
        Supported settings:
            - chunk_size: New chunk size
            - chunk_overlap: New overlap size
            - max_file_size: New max file size
            - allowed_directories: List of allowed directories
            - excluded_directories: List of excluded directories
        """
        if 'chunk_size' in kwargs:
            self.chunk_size = kwargs['chunk_size']
            self.chunker = FileChunker(
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap
            )
            
        if 'chunk_overlap' in kwargs:
            self.chunk_overlap = kwargs['chunk_overlap']
            self.chunker = FileChunker(
                chunk_size=self.chunk_size,
                overlap=self.chunk_overlap
            )
            
        if 'max_file_size' in kwargs:
            self.max_file_size = kwargs['max_file_size']
            self.extractor_factory = ExtractorFactory(self.max_file_size)
        
        if 'allowed_directories' in kwargs:
            self.directory_validator.set_allowed_directories(
                kwargs['allowed_directories']
            )
            
        if 'excluded_directories' in kwargs:
            self.directory_validator.set_excluded_directories(
                kwargs['excluded_directories']
            )
        
        self.logger.info(f"Updated processor settings: {kwargs}")
    
    def get_directory_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about directory access settings.
        
        Returns:
            Dict with directory validator statistics
        """
        return self.directory_validator.get_statistics()
    
    def _generate_and_store_embeddings(self, chunk_ids: List[str],
                                       chunk_texts: List[str],
                                       progress_callback: Optional[
                                           Callable[[str, int, int], None]
                                       ] = None) -> int:
        """
        Generate embeddings for chunks and store them in the database.
        
        Args:
            chunk_ids: List of chunk IDs
            chunk_texts: List of chunk texts
            progress_callback: Optional progress callback
            
        Returns:
            Number of embeddings successfully generated and stored
        """
        try:
            if not chunk_ids or not chunk_texts:
                return 0
            
            total_chunks = len(chunk_ids)
            embeddings_stored = 0
            
            # Process in batches
            for i in range(0, total_chunks, self.embedding_batch_size):
                batch_end = min(i + self.embedding_batch_size, total_chunks)
                batch_ids = chunk_ids[i:batch_end]
                batch_texts = chunk_texts[i:batch_end]
                
                # Update progress
                if progress_callback:
                    progress_callback(
                        f"Generating embeddings "
                        f"({i + 1}-{batch_end}/{total_chunks})",
                        i + 1,
                        total_chunks
                    )
                
                # Generate embeddings for batch
                self.logger.debug(
                    f"Generating embeddings for batch "
                    f"{i//self.embedding_batch_size + 1}"
                )
                
                try:
                    embeddings = (
                        self._embedding_generator.generate_embeddings_batch(
                            batch_texts,
                            batch_size=self.embedding_batch_size,
                            show_progress=False  # We handle progress ourselves
                        )
                    )
                    
                    # Store each embedding
                    for chunk_id, embedding in zip(batch_ids, embeddings):
                        embedding_result = self.db.add_embedding(
                            chunk_id=chunk_id,
                            embedding_vector=embedding.tolist(),
                            model_name=self._embedding_generator.model_name
                        )
                        
                        if embedding_result['success']:
                            embeddings_stored += 1
                        else:
                            self.logger.error(
                                f"Failed to store embedding for chunk "
                                f"{chunk_id}: {embedding_result.get('error')}"
                            )
                    
                except Exception as e:
                    self.logger.error(
                        f"Error generating embeddings for batch: {str(e)}"
                    )
            
            self.logger.info(
                f"Successfully generated and stored {embeddings_stored} "
                f"out of {total_chunks} embeddings"
            )
            
            return embeddings_stored
            
        except Exception as e:
            self.logger.error(f"Error in embedding generation: {str(e)}")
            return 0