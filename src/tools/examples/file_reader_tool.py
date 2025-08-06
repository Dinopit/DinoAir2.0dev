"""
File Reader Tool - Text file reading utility

This tool provides safe text file reading capabilities for 
AI-assisted file analysis and processing tasks.
"""

import logging
from pathlib import Path
from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType
)

logger = logging.getLogger(__name__)


class FileReaderTool(BaseTool):
    """
    Text file reading tool
    
    This tool provides safe file reading including:
    - Read text files with encoding detection
    - Line-by-line reading with limits
    - File size validation
    - Safe encoding handling
    """
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="file_reader_tool",
            version="1.0.0",
            description="Read text files safely with encoding detection",
            author="DinoAir Team",
            category=ToolCategory.SYSTEM,
            tags=["file", "text", "read", "encoding"],
            parameters=[
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path to the text file to read",
                    required=True,
                    example="/path/to/file.txt"
                ),
                ToolParameter(
                    name="max_lines",
                    type=ParameterType.INTEGER,
                    description="Maximum number of lines to read",
                    required=False,
                    default=1000,
                    min_value=1,
                    max_value=10000,
                    example=100
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="File encoding (auto-detect if not specified)",
                    required=False,
                    default="utf-8",
                    example="utf-8"
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
                    "name": "Read small text file",
                    "description": "Read entire content of a small text file",
                    "parameters": {
                        "file_path": "./example.txt"
                    },
                    "expected_output": "File content here..."
                },
                {
                    "name": "Read first 50 lines",
                    "description": "Read only first 50 lines of a large file",
                    "parameters": {
                        "file_path": "./large_file.log",
                        "max_lines": 50
                    },
                    "expected_output": "First 50 lines of content..."
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("FileReaderTool initialized")
        self._read_count = 0
        self._max_file_size = 10 * 1024 * 1024  # 10MB limit
        
    def execute(self, **kwargs) -> ToolResult:
        """
        Read text file content
        
        Args:
            file_path: Path to the file to read
            max_lines: Maximum number of lines to read (default: 1000)
            encoding: File encoding (default: utf-8)
            
        Returns:
            ToolResult with file content
        """
        try:
            file_path_str = kwargs.get('file_path')
            max_lines = kwargs.get('max_lines', 1000)
            encoding = kwargs.get('encoding', 'utf-8')
            
            if not file_path_str:
                return ToolResult(
                    success=False,
                    errors=["file_path parameter is required"],
                    status=ToolStatus.FAILED
                )
            
            # Validate file path
            file_path = Path(file_path_str)
            if not file_path.exists():
                return ToolResult(
                    success=False,
                    errors=[f"File does not exist: {file_path_str}"],
                    status=ToolStatus.FAILED
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False,
                    errors=[f"Path is not a file: {file_path_str}"],
                    status=ToolStatus.FAILED
                )
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self._max_file_size:
                return ToolResult(
                    success=False,
                    errors=[f"File too large: {file_size} bytes "
                            f"(max: {self._max_file_size})"],
                    status=ToolStatus.FAILED
                )
            
            # Read file content
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n\r'))
                    
                    content = '\n'.join(lines)
                
            except UnicodeDecodeError:
                # Try common encodings if specified encoding fails
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ascii']
                content = None
                
                for try_encoding in encodings_to_try:
                    try:
                        with open(file_path, 'r', encoding=try_encoding) as f:
                            lines = []
                            for i, line in enumerate(f):
                                if i >= max_lines:
                                    break
                                lines.append(line.rstrip('\n\r'))
                            content = '\n'.join(lines)
                            encoding = try_encoding
                            break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    return ToolResult(
                        success=False,
                        errors=["Could not decode file with any encoding"],
                        status=ToolStatus.FAILED
                    )
            
            except PermissionError:
                return ToolResult(
                    success=False,
                    errors=[f"Permission denied reading: {file_path_str}"],
                    status=ToolStatus.FAILED
                )
            
            self._read_count += 1
            
            # Calculate actual lines read
            actual_lines = len(content.split('\n')) if content else 0
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    'file_path': str(file_path.absolute()),
                    'file_size': file_size,
                    'encoding_used': encoding,
                    'lines_read': actual_lines,
                    'max_lines_limit': max_lines,
                    'truncated': actual_lines >= max_lines,
                    'read_count': self._read_count
                }
            )
            
        except Exception as e:
            logger.error(f"File reading failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def shutdown(self):
        """Cleanup tool resources"""
        logger.info(
            f"FileReaderTool shutting down. "
            f"Read {self._read_count} files"
        )