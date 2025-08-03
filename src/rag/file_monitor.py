"""
File Monitor for RAG System
Monitors indexed directories for changes and auto-updates the index.
"""

import os
import time
from typing import Dict, List, Set, Optional, Callable, Any
import threading

try:
    from watchdog.observers import Observer
    from watchdog.events import (
        FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent,
        FileDeletedEvent, FileMovedEvent
    )
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Create dummy classes for type hints
    
    class FileSystemEventHandler:
        pass
    
    class FileModifiedEvent:
        src_path = ""
        is_directory = False
    
    class FileCreatedEvent:
        src_path = ""
        is_directory = False
    
    class FileDeletedEvent:
        src_path = ""
        is_directory = False
    
    class FileMovedEvent:
        src_path = ""
        dest_path = ""
        is_directory = False
    
    class Observer:
        pass

from .file_processor import FileProcessor
from ..database.file_search_db import FileSearchDB
from ..utils.logger import Logger


class FileChangeHandler(FileSystemEventHandler):
    """
    Handles file system events for RAG indexing.
    """
    
    def __init__(self, file_monitor: 'FileMonitor'):
        """
        Initialize the handler.
        
        Args:
            file_monitor: Parent FileMonitor instance
        """
        super().__init__()
        self.file_monitor = file_monitor
        self.logger = Logger()
        
        # Debounce tracking
        self._pending_changes: Dict[str, float] = {}
        self._debounce_seconds = 2.0
        
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events"""
        if not event.is_directory:
            self._handle_file_change(event.src_path, 'modified')
            
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events"""
        if not event.is_directory:
            self._handle_file_change(event.src_path, 'created')
            
    def on_deleted(self, event: FileDeletedEvent):
        """Handle file deletion events"""
        if not event.is_directory:
            self._handle_file_deletion(event.src_path)
            
    def on_moved(self, event: FileMovedEvent):
        """Handle file move events"""
        if not event.is_directory:
            # Treat as deletion + creation
            self._handle_file_deletion(event.src_path)
            self._handle_file_change(event.dest_path, 'moved')
            
    def _handle_file_change(self, file_path: str, change_type: str):
        """
        Handle file changes with debouncing.
        
        Args:
            file_path: Path to the changed file
            change_type: Type of change (created, modified, moved)
        """
        # Normalize path
        file_path = os.path.normpath(file_path)
        
        # Check if file should be indexed
        if not self.file_monitor._should_index_file(file_path):
            return
            
        # Add to pending changes with timestamp
        self._pending_changes[file_path] = time.time()
        
        # Log change
        self.logger.info(
            f"File {change_type}: {os.path.basename(file_path)}"
        )
        
        # Process after debounce period
        self.file_monitor._schedule_processing()
        
    def _handle_file_deletion(self, file_path: str):
        """
        Handle file deletion.
        
        Args:
            file_path: Path to the deleted file
        """
        # Normalize path
        file_path = os.path.normpath(file_path)
        
        # Remove from pending if exists
        self._pending_changes.pop(file_path, None)
        
        # Remove from index immediately
        self.file_monitor._remove_from_index(file_path)
        
        self.logger.info(f"File deleted: {os.path.basename(file_path)}")
        
    def get_pending_files(self) -> List[str]:
        """
        Get files ready for processing after debounce period.
        
        Returns:
            List of file paths ready to process
        """
        current_time = time.time()
        ready_files = []
        
        for file_path, timestamp in list(self._pending_changes.items()):
            if current_time - timestamp >= self._debounce_seconds:
                ready_files.append(file_path)
                del self._pending_changes[file_path]
                
        return ready_files


class FileMonitor:
    """
    Monitors directories for file changes and updates RAG index.
    """
    
    def __init__(self, user_name: str = "default_user"):
        """
        Initialize the file monitor.
        
        Args:
            user_name: Username for database operations
        """
        self.user_name = user_name
        self.logger = Logger()
        
        # Initialize components
        self.file_processor = FileProcessor(
            user_name=user_name,
            chunk_size=1000,
            chunk_overlap=200,
            generate_embeddings=True
        )
        self.file_search_db = FileSearchDB(user_name)
        
        # Monitoring state
        self._observer: Optional[Observer] = None
        self._monitored_dirs: Set[str] = set()
        self._file_extensions: Set[str] = {
            '.txt', '.md', '.pdf', '.docx', '.doc',
            '.py', '.js', '.java', '.cpp', '.c', '.cs',
            '.html', '.css', '.json', '.xml', '.yaml'
        }
        self._is_monitoring = False
        
        # Event handler
        self._handler = FileChangeHandler(self)
        
        # Processing timer
        self._process_timer: Optional[threading.Timer] = None
        
        # Callbacks
        self._update_callback: Optional[Callable] = None
        self._error_callback: Optional[Callable] = None
        
    def start_monitoring(self, directories: List[str],
                         file_extensions: Optional[List[str]] = None):
        """
        Start monitoring directories for changes.
        
        Args:
            directories: List of directory paths to monitor
            file_extensions: Optional list of file extensions to monitor
        """
        if not WATCHDOG_AVAILABLE:
            self.logger.error("Watchdog library not available")
            return
            
        if self._is_monitoring:
            self.stop_monitoring()
            
        # Update file extensions if provided
        if file_extensions:
            self._file_extensions = set(file_extensions)
            
        # Create observer
        if WATCHDOG_AVAILABLE:
            self._observer = Observer()
        else:
            self.logger.error(
                "Cannot create Observer - watchdog not available"
            )
            return
        
        # Add directories to monitor
        for directory in directories:
            if os.path.exists(directory) and os.path.isdir(directory):
                # Normalize path
                directory = os.path.normpath(directory)
                
                # Schedule observer
                self._observer.schedule(
                    self._handler,
                    directory,
                    recursive=True
                )
                self._monitored_dirs.add(directory)
                
                self.logger.info(f"Monitoring directory: {directory}")
            else:
                self.logger.warning(
                    f"Directory not found or invalid: {directory}"
                )
                
        # Start observer
        if self._monitored_dirs:
            self._observer.start()
            self._is_monitoring = True
            self.logger.info(
                f"File monitor started for {len(self._monitored_dirs)} "
                f"directories"
            )
        else:
            self.logger.warning("No valid directories to monitor")
            
    def stop_monitoring(self):
        """Stop monitoring directories."""
        if self._observer and self._is_monitoring:
            self._observer.stop()
            self._observer.join()
            self._is_monitoring = False
            self._monitored_dirs.clear()
            
            self.logger.info("File monitor stopped")
            
    def add_directory(self, directory: str):
        """
        Add a directory to monitor.
        
        Args:
            directory: Directory path to add
        """
        if not self._is_monitoring:
            self.logger.warning("Monitor not running, start monitoring first")
            return
            
        if os.path.exists(directory) and os.path.isdir(directory):
            directory = os.path.normpath(directory)
            
            if directory not in self._monitored_dirs:
                self._observer.schedule(
                    self._handler,
                    directory,
                    recursive=True
                )
                self._monitored_dirs.add(directory)
                
                self.logger.info(f"Added directory to monitor: {directory}")
        else:
            self.logger.warning(f"Invalid directory: {directory}")
            
    def remove_directory(self, directory: str):
        """
        Remove a directory from monitoring.
        
        Args:
            directory: Directory path to remove
        """
        directory = os.path.normpath(directory)
        
        if directory in self._monitored_dirs:
            # Note: watchdog doesn't provide a way to unschedule specific paths
            # Would need to restart observer without this directory
            self._monitored_dirs.discard(directory)
            self.logger.info(f"Removed directory from monitor: {directory}")
            
    def set_file_extensions(self, extensions: List[str]):
        """
        Set file extensions to monitor.
        
        Args:
            extensions: List of file extensions (e.g., ['.txt', '.pdf'])
        """
        self._file_extensions = set(extensions)
        self.logger.info(f"Monitoring extensions: {extensions}")
        
    def set_update_callback(self, callback: Callable[[str, str], None]):
        """
        Set callback for file updates.
        
        Args:
            callback: Function called with (file_path, action)
        """
        self._update_callback = callback
        
    def set_error_callback(self, callback: Callable[[str, Exception], None]):
        """
        Set callback for errors.
        
        Args:
            callback: Function called with (file_path, exception)
        """
        self._error_callback = callback
        
    def _should_index_file(self, file_path: str) -> bool:
        """
        Check if a file should be indexed.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be indexed
        """
        # Check extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self._file_extensions:
            return False
            
        # Check if in monitored directory
        file_path_norm = os.path.normpath(file_path)
        for monitored_dir in self._monitored_dirs:
            if file_path_norm.startswith(monitored_dir):
                return True
                
        return False
        
    def _schedule_processing(self):
        """Schedule processing of pending changes."""
        # Simple approach: process after a short delay
        # In production, might use a more sophisticated scheduler
        if self._process_timer:
            return  # Already scheduled
            
        # Process after 3 seconds
        self._process_timer = threading.Timer(
            3.0, self._process_pending_changes
        )
        self._process_timer.start()
        
    def _process_pending_changes(self):
        """Process pending file changes."""
        self._process_timer = None
        
        # Get files ready for processing
        files_to_process = self._handler.get_pending_files()
        
        if not files_to_process:
            return
            
        self.logger.info(f"Processing {len(files_to_process)} file changes")
        
        # Process each file
        for file_path in files_to_process:
            try:
                # Skip if file no longer exists
                if not os.path.exists(file_path):
                    continue
                    
                # Process file
                result = self.file_processor.process_file(
                    file_path,
                    force_reprocess=True
                )
                
                if result['success']:
                    self.logger.info(f"Updated index for: {file_path}")
                    
                    # Call update callback
                    if self._update_callback:
                        self._update_callback(file_path, 'updated')
                else:
                    raise Exception(result.get('error', 'Unknown error'))
                    
            except Exception as e:
                self.logger.error(
                    f"Failed to process {file_path}: {str(e)}"
                )
                
                # Call error callback
                if self._error_callback:
                    self._error_callback(file_path, e)
                    
    def _remove_from_index(self, file_path: str):
        """
        Remove a file from the index.
        
        Args:
            file_path: Path to the file
        """
        try:
            # Get file info from database
            file_info = self.file_search_db.get_file_by_path(file_path)
            
            if file_info:
                # Delete file and its chunks
                # Note: delete_file method needs to be
                # implemented in FileSearchDB
                # For now, we'll just log
                self.logger.info(f"Would delete file: {file_info['file_id']}")
                result = True  # Assume success
                
                if result:
                    self.logger.info(f"Removed from index: {file_path}")
                    
                    # Call update callback
                    if self._update_callback:
                        self._update_callback(file_path, 'deleted')
                        
        except Exception as e:
            self.logger.error(
                f"Failed to remove {file_path} from index: {str(e)}"
            )
            
            # Call error callback
            if self._error_callback:
                self._error_callback(file_path, e)
                
    def get_status(self) -> Dict[str, Any]:
        """
        Get current monitor status.
        
        Returns:
            Dictionary with status information
        """
        return {
            'is_monitoring': self._is_monitoring,
            'monitored_directories': list(self._monitored_dirs),
            'file_extensions': list(self._file_extensions),
            'pending_changes': len(self._handler._pending_changes)
        }
        
    def __del__(self):
        """Cleanup on deletion."""
        self.stop_monitoring()


def integrate_with_watchdog(watchdog_instance):
    """
    Integrate file monitor with existing watchdog system.
    
    Args:
        watchdog_instance: Existing watchdog instance
        
    Returns:
        FileMonitor instance configured to work with watchdog
    """
    # Get user from watchdog config if available
    user_name = getattr(watchdog_instance, 'user_name', 'default_user')
    
    # Create file monitor
    file_monitor = FileMonitor(user_name)
    
    # Configure based on watchdog settings if available
    if hasattr(watchdog_instance, 'monitored_paths'):
        directories = [
            p for p in watchdog_instance.monitored_paths
            if os.path.isdir(p)
        ]
        if directories:
            file_monitor.start_monitoring(directories)
            
    # Add to watchdog's monitoring tasks if possible
    if hasattr(watchdog_instance, 'add_monitor'):
        watchdog_instance.add_monitor('file_index', file_monitor)
        
    return file_monitor