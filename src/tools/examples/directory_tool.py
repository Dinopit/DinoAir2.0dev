"""
Directory Tool - File system directory listing

This tool provides directory listing capabilities for browsing
file systems during AI-assisted tasks.
"""

import logging
from pathlib import Path
from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType
)

logger = logging.getLogger(__name__)


class DirectoryTool(BaseTool):
    """
    Directory listing tool
    
    This tool provides file system navigation including:
    - List directory contents
    - Show file sizes and types
    - Filter by file extensions
    - Recursive directory traversal
    """
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="directory_tool",
            version="1.0.0",
            description="List directory contents and file information",
            author="DinoAir Team",
            category=ToolCategory.SYSTEM,
            tags=["filesystem", "directory", "files", "listing"],
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="Directory path to list",
                    required=False,
                    default=".",
                    example="/path/to/directory"
                ),
                ToolParameter(
                    name="show_hidden",
                    type=ParameterType.BOOLEAN,
                    description="Include hidden files and directories",
                    required=False,
                    default=False,
                    example=True
                ),
                ToolParameter(
                    name="show_details",
                    type=ParameterType.BOOLEAN,
                    description="Show detailed file information (size, type)",
                    required=False,
                    default=False,
                    example=True
                ),
                ToolParameter(
                    name="filter_extension",
                    type=ParameterType.STRING,
                    description="Filter files by extension",
                    required=False,
                    example=".py"
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": False,
                "progress_reporting": False,
                "batch_processing": False,
                "caching": True,
                "stateful": False
            },
            examples=[
                {
                    "name": "List current directory",
                    "description": "List files in current directory",
                    "parameters": {
                        "path": "."
                    },
                    "expected_output": ["file1.txt", "file2.py", "subfolder/"]
                },
                {
                    "name": "List Python files with details",
                    "description": "List Python files with size information",
                    "parameters": {
                        "path": "./src",
                        "filter_extension": ".py",
                        "show_details": True
                    },
                    "expected_output": ["main.py (1.2 KB)", "utils.py (856 B)"]
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("DirectoryTool initialized")
        self._listing_count = 0
        
    def execute(self, **kwargs) -> ToolResult:
        """
        List directory contents
        
        Args:
            path: Directory path to list (default: current directory)
            show_hidden: Include hidden files (default: False)
            show_details: Show file details like size (default: False)
            filter_extension: Filter by file extension (optional)
            
        Returns:
            ToolResult with directory listing
        """
        try:
            path_str = kwargs.get('path', '.')
            show_hidden = kwargs.get('show_hidden', False)
            show_details = kwargs.get('show_details', False)
            filter_ext = kwargs.get('filter_extension')
            
            # Validate path
            target_path = Path(path_str)
            if not target_path.exists():
                return ToolResult(
                    success=False,
                    errors=[f"Path does not exist: {path_str}"],
                    status=ToolStatus.FAILED
                )
            
            if not target_path.is_dir():
                return ToolResult(
                    success=False,
                    errors=[f"Path is not a directory: {path_str}"],
                    status=ToolStatus.FAILED
                )
            
            # List directory contents
            entries = []
            try:
                for item in target_path.iterdir():
                    # Skip hidden files if not requested
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    
                    # Apply extension filter
                    if filter_ext and item.is_file():
                        if not item.name.endswith(filter_ext):
                            continue
                    
                    # Build entry info
                    if show_details:
                        if item.is_file():
                            size = item.stat().st_size
                            size_str = self._format_size(size)
                            entry = f"{item.name} ({size_str})"
                        else:
                            entry = f"{item.name}/ (directory)"
                    else:
                        entry = f"{item.name}/" if item.is_dir() else item.name
                    
                    entries.append(entry)
                
            except PermissionError:
                return ToolResult(
                    success=False,
                    errors=[f"Permission denied accessing: {path_str}"],
                    status=ToolStatus.FAILED
                )
            
            # Sort entries
            entries.sort()
            
            self._listing_count += 1
            
            return ToolResult(
                success=True,
                output=entries,
                metadata={
                    'path': str(target_path.absolute()),
                    'item_count': len(entries),
                    'show_hidden': show_hidden,
                    'show_details': show_details,
                    'filter_extension': filter_ext,
                    'listing_count': self._listing_count
                }
            )
            
        except Exception as e:
            logger.error(f"Directory listing failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def shutdown(self):
        """Cleanup tool resources"""
        logger.info(
            f"DirectoryTool shutting down. "
            f"Performed {self._listing_count} listings"
        )