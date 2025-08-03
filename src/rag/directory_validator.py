"""Directory Validator for RAG File Search System.

This module provides security validation for directory and file access,
preventing unauthorized access and path traversal attacks.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from src.utils.logger import Logger


class DirectoryValidator:
    """Validates directory and file access for the RAG file search system.
    
    Features:
    - Path traversal attack prevention
    - Allowed/excluded directory checking
    - Absolute path resolution
    - Security logging
    - File filtering based on directory rules
    """
    
    def __init__(self, allowed_dirs: Optional[List[str]] = None,
                 excluded_dirs: Optional[List[str]] = None):
        """Initialize the directory validator.
        
        Args:
            allowed_dirs: List of allowed directory paths
            excluded_dirs: List of excluded directory paths
        """
        self.logger = Logger()
        self._allowed_dirs: Set[str] = set()
        self._excluded_dirs: Set[str] = set()
        
        # Default excluded system directories for Windows
        self._default_excluded = {
            "C:\\Windows",
            "C:\\Windows\\System32", 
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            "C:\\ProgramData",
            "C:\\$Recycle.Bin",
            "C:\\System Volume Information",
            "C:\\Recovery"
        }
        
        # Initialize with provided directories
        if allowed_dirs:
            self.set_allowed_directories(allowed_dirs)
        if excluded_dirs:
            self.set_excluded_directories(excluded_dirs)
        else:
            # Use default exclusions if none provided
            self._excluded_dirs = self._default_excluded.copy()
    
    def set_allowed_directories(self, directories: List[str]) -> None:
        """Set the list of allowed directories.
        
        Args:
            directories: List of directory paths to allow
        """
        self._allowed_dirs.clear()
        for directory in directories:
            try:
                abs_path = self.resolve_path(directory)
                if abs_path:
                    self._allowed_dirs.add(abs_path)
                    self.logger.info(f"Added allowed directory: {abs_path}")
            except Exception as e:
                self.logger.error(
                    f"Error adding allowed directory {directory}: {str(e)}"
                )
    
    def set_excluded_directories(self, directories: List[str]) -> None:
        """Set the list of excluded directories.
        
        Args:
            directories: List of directory paths to exclude
        """
        self._excluded_dirs = self._default_excluded.copy()
        for directory in directories:
            try:
                abs_path = self.resolve_path(directory)
                if abs_path:
                    self._excluded_dirs.add(abs_path)
                    self.logger.info(f"Added excluded directory: {abs_path}")
            except Exception as e:
                self.logger.error(
                    f"Error adding excluded directory {directory}: {str(e)}"
                )
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed for access.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is allowed, False otherwise
        """
        try:
            # Resolve to absolute path
            abs_path = self.resolve_path(path)
            if not abs_path:
                return False
            
            # Check if it's a critical system file
            if self._is_critical_system_file(abs_path):
                self.logger.warning(
                    f"Access denied to critical system file: {abs_path}"
                )
                return False
            
            # Check against excluded directories
            for excluded in self._excluded_dirs:
                if abs_path.lower().startswith(excluded.lower()):
                    self.logger.debug(
                        f"Path {abs_path} is in excluded directory {excluded}"
                    )
                    return False
            
            # If we have allowed directories, check if path is within them
            if self._allowed_dirs:
                for allowed in self._allowed_dirs:
                    if abs_path.lower().startswith(allowed.lower()):
                        self.logger.debug(
                            f"Path {abs_path} is in allowed directory {allowed}"
                        )
                        return True
                # Path not in any allowed directory
                self.logger.debug(
                    f"Path {abs_path} is not in any allowed directory"
                )
                return False
            
            # No allowed directories specified, so allow if not excluded
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking path {path}: {str(e)}")
            return False
    
    def validate_path(self, path: str) -> Dict[str, Any]:
        """Validate a path for security issues.
        
        Args:
            path: Path to validate
            
        Returns:
            Dict with 'valid' bool, 'resolved_path' str, and 'message' str
        """
        try:
            # Check for path traversal attempts
            if ".." in path or "~" in path:
                return {
                    "valid": False,
                    "resolved_path": None,
                    "message": "Path traversal detected"
                }
            
            # Resolve to absolute path
            abs_path = self.resolve_path(path)
            if not abs_path:
                return {
                    "valid": False,
                    "resolved_path": None,
                    "message": "Invalid path or path does not exist"
                }
            
            # Check if path exists
            if not os.path.exists(abs_path):
                return {
                    "valid": False,
                    "resolved_path": abs_path,
                    "message": "Path does not exist"
                }
            
            # Check if allowed
            if not self.is_path_allowed(abs_path):
                return {
                    "valid": False,
                    "resolved_path": abs_path,
                    "message": "Path is not allowed or is excluded"
                }
            
            return {
                "valid": True,
                "resolved_path": abs_path,
                "message": "Path is valid"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "resolved_path": None,
                "message": f"Validation error: {str(e)}"
            }
    
    def resolve_path(self, path: str) -> Optional[str]:
        """Safely resolve a path to its absolute form.
        
        Args:
            path: Path to resolve
            
        Returns:
            Absolute path string or None if invalid
        """
        try:
            # Convert to Path object
            path_obj = Path(path)
            
            # Resolve to absolute path
            abs_path = path_obj.resolve()
            
            # Ensure it's a string
            abs_path_str = str(abs_path)
            
            # Normalize path separators for Windows
            abs_path_str = os.path.normpath(abs_path_str)
            
            # Additional validation
            if not abs_path_str or abs_path_str == ".":
                return None
            
            return abs_path_str
            
        except Exception as e:
            self.logger.error(f"Error resolving path {path}: {str(e)}")
            return None
    
    def get_allowed_files(self, file_paths: List[str]) -> List[str]:
        """Filter a list of file paths to only include allowed ones.
        
        Args:
            file_paths: List of file paths to filter
            
        Returns:
            List of allowed file paths
        """
        allowed_files = []
        
        for file_path in file_paths:
            if self.is_path_allowed(file_path):
                allowed_files.append(file_path)
            else:
                self.logger.debug(f"Filtered out file: {file_path}")
        
        return allowed_files
    
    def _is_critical_system_file(self, path: str) -> bool:
        """Check if a path is a critical system file.
        
        Args:
            path: Absolute path to check
            
        Returns:
            True if path is a critical system file
        """
        critical_files = {
            "pagefile.sys",
            "hiberfil.sys", 
            "swapfile.sys",
            "bootmgr",
            "ntldr",
            "ntdetect.com",
            "boot.ini"
        }
        
        critical_paths = {
            "C:\\Windows\\System32\\config",
            "C:\\Windows\\System32\\drivers",
            "C:\\Windows\\CSC",  # Client Side Caching
            "C:\\Windows\\Prefetch",
            "C:\\Windows\\System32\\spool",
            "C:\\Windows\\System32\\LogFiles"
        }
        
        # Check filename
        filename = os.path.basename(path).lower()
        if filename in critical_files:
            return True
        
        # Check critical paths
        path_lower = path.lower()
        for critical in critical_paths:
            if path_lower.startswith(critical.lower()):
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current directory settings.
        
        Returns:
            Dict with statistics
        """
        return {
            "allowed_directories": list(self._allowed_dirs),
            "excluded_directories": list(self._excluded_dirs),
            "allowed_count": len(self._allowed_dirs),
            "excluded_count": len(self._excluded_dirs),
            "has_restrictions": bool(self._allowed_dirs)
        }
    
    def log_access_attempt(self, path: str, allowed: bool,
                          reason: Optional[str] = None) -> None:
        """Log an access attempt for security auditing.
        
        Args:
            path: Path that was accessed
            allowed: Whether access was allowed
            reason: Optional reason for denial
        """
        if allowed:
            self.logger.info(f"File access allowed: {path}")
        else:
            msg = f"File access denied: {path}"
            if reason:
                msg += f" (Reason: {reason})"
            self.logger.warning(msg)
    
    def validate_directory_list(self, directories: List[str]) -> Dict[str, Any]:
        """Validate a list of directories.
        
        Args:
            directories: List of directory paths to validate
            
        Returns:
            Dict with validation results
        """
        results = {
            "valid": [],
            "invalid": [],
            "warnings": []
        }
        
        for directory in directories:
            validation = self.validate_path(directory)
            
            if validation["valid"]:
                # Additional check: is it a directory?
                if os.path.isdir(validation["resolved_path"]):
                    results["valid"].append({
                        "path": directory,
                        "resolved": validation["resolved_path"]
                    })
                else:
                    results["invalid"].append({
                        "path": directory,
                        "reason": "Path is not a directory"
                    })
            else:
                results["invalid"].append({
                    "path": directory,
                    "reason": validation["message"]
                })
            
            # Check for potentially problematic paths
            if validation.get("resolved_path"):
                resolved = validation["resolved_path"]
                if "Program Files" in resolved:
                    results["warnings"].append({
                        "path": directory,
                        "warning": "Indexing Program Files may include many "
                                 "binary files"
                    })
                elif "AppData" in resolved:
                    results["warnings"].append({
                        "path": directory,
                        "warning": "AppData contains application data that "
                                 "may change frequently"
                    })
        
        return results