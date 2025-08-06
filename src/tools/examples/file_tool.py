"""
File Tool Example

A file operations tool that demonstrates file handling, progress reporting,
and safety features like sandboxing and permission checking.
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import hashlib

from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType, ToolProgress
)


logger = logging.getLogger(__name__)


class FileTool(BaseTool):
    """
    File operations tool
    
    This tool provides safe file operations including:
    - Reading and writing files
    - File information and metadata
    - Directory operations
    - File searching
    - Basic file transformations
    """
    
    SUPPORTED_OPERATIONS = {
        # Read operations
        'read': 'Read file contents',
        'read_lines': 'Read file as lines',
        'read_json': 'Read JSON file',
        'read_csv': 'Read CSV file',
        
        # Write operations
        'write': 'Write content to file',
        'append': 'Append content to file',
        'write_json': 'Write JSON to file',
        'write_csv': 'Write CSV to file',
        
        # File operations
        'copy': 'Copy file',
        'move': 'Move/rename file',
        'delete': 'Delete file',
        'exists': 'Check if file exists',
        'info': 'Get file information',
        
        # Directory operations
        'list_dir': 'List directory contents',
        'create_dir': 'Create directory',
        'delete_dir': 'Delete directory',
        
        # Search operations
        'find_files': 'Find files by pattern',
        'search_content': 'Search file content',
        
        # Utility operations
        'checksum': 'Calculate file checksum',
        'compare': 'Compare two files',
        'size_format': 'Format file size'
    }
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="file_tool",
            version="1.5.0",
            description="Safe file operations tool with sandboxing",
            author="DinoAir Team",
            category=ToolCategory.UTILITY,
            tags=["file", "io", "storage", "filesystem"],
            documentation_url="https://github.com/dinoair/tools/file",
            license="MIT",
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.ENUM,
                    description="File operation to perform",
                    required=True,
                    enum_values=list(self.SUPPORTED_OPERATIONS.keys()),
                    example="read"
                ),
                ToolParameter(
                    name="path",
                    type=ParameterType.FILE_PATH,
                    description="Primary file or directory path",
                    required=True,
                    example="./data/input.txt"
                ),
                ToolParameter(
                    name="target_path",
                    type=ParameterType.FILE_PATH,
                    description="Target path for copy/move operations",
                    required=False,
                    example="./data/output.txt"
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="Content for write operations",
                    required=False,
                    example="Hello, World!"
                ),
                ToolParameter(
                    name="encoding",
                    type=ParameterType.STRING,
                    description="File encoding",
                    required=False,
                    default="utf-8",
                    example="utf-8"
                ),
                ToolParameter(
                    name="pattern",
                    type=ParameterType.STRING,
                    description="Search pattern (glob or regex)",
                    required=False,
                    example="*.txt"
                ),
                ToolParameter(
                    name="recursive",
                    type=ParameterType.BOOLEAN,
                    description="Recursive operation for directories",
                    required=False,
                    default=False,
                    example=True
                ),
                ToolParameter(
                    name="create_parents",
                    type=ParameterType.BOOLEAN,
                    description="Create parent directories if needed",
                    required=False,
                    default=True,
                    example=True
                ),
                ToolParameter(
                    name="safe_mode",
                    type=ParameterType.BOOLEAN,
                    description="Enable safety checks and sandboxing",
                    required=False,
                    default=True,
                    example=True
                ),
                ToolParameter(
                    name="max_size",
                    type=ParameterType.INTEGER,
                    description="Maximum file size in bytes",
                    required=False,
                    default=10485760,  # 10MB
                    min_value=0,
                    max_value=104857600,  # 100MB
                    example=1048576
                )
            ],
            capabilities={
                "async_support": True,
                "streaming": True,
                "cancellable": True,
                "progress_reporting": True,
                "batch_processing": True,
                "caching": False,
                "stateful": False
            },
            examples=[
                {
                    "name": "Read text file",
                    "description": "Read contents of a text file",
                    "parameters": {
                        "operation": "read",
                        "path": "./README.md"
                    }
                },
                {
                    "name": "Write JSON file",
                    "description": "Write data to JSON file",
                    "parameters": {
                        "operation": "write_json",
                        "path": "./data/config.json",
                        "content": '{"key": "value"}'
                    }
                },
                {
                    "name": "Find files",
                    "description": "Find all Python files recursively",
                    "parameters": {
                        "operation": "find_files",
                        "path": "./src",
                        "pattern": "*.py",
                        "recursive": True
                    }
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("FileTool initialized")
        
        # Set up sandboxed directory (configurable)
        self.sandbox_root = Path(self._config.get(
            'sandbox_root', 
            os.path.expanduser('~/dinoair_file_sandbox')
        ))
        
        # Allowed extensions for safe mode
        self.allowed_extensions = set(self._config.get(
            'allowed_extensions',
            ['.txt', '.json', '.csv', '.md', '.log', '.xml', '.yaml', '.yml']
        ))
        
        # Create sandbox if needed
        if self._config.get('create_sandbox', True):
            self.sandbox_root.mkdir(parents=True, exist_ok=True)
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute file operation
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with operation result
        """
        try:
            # Extract parameters
            operation = kwargs.get('operation')
            path = kwargs.get('path')
            safe_mode = kwargs.get('safe_mode', True)
            
            # Report progress
            self._report_progress(ToolProgress(
                percentage=0,
                message=f"Starting {operation} operation",
                current_step="validation"
            ))
            
            # Validate operation
            if operation not in self.SUPPORTED_OPERATIONS:
                return ToolResult(
                    success=False,
                    errors=[f"Unsupported operation: {operation}"],
                    status=ToolStatus.FAILED
                )
            
            # Validate and resolve path
            if not path:
                return ToolResult(
                    success=False,
                    errors=["No path provided"],
                    status=ToolStatus.FAILED
                )
            
            resolved_path = self._resolve_path(str(path), safe_mode)
            if not resolved_path:
                return ToolResult(
                    success=False,
                    errors=[f"Invalid or unsafe path: {path}"],
                    status=ToolStatus.FAILED
                )
            
            # Execute operation
            self._report_progress(ToolProgress(
                percentage=50,
                message=f"Executing {self.SUPPORTED_OPERATIONS[operation]}",
                current_step="execution"
            ))
            
            result = self._execute_operation(operation, resolved_path, kwargs)
            
            # Report completion
            self._report_progress(ToolProgress(
                percentage=100,
                message="Operation complete",
                current_step="complete"
            ))
            
            return result
            
        except Exception as e:
            logger.error(f"File operation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def _resolve_path(self, path: str, safe_mode: bool) -> Optional[Path]:
        """Resolve and validate path"""
        try:
            path_obj = Path(path)
            
            if safe_mode:
                # Ensure path is within sandbox
                if not path_obj.is_absolute():
                    path_obj = self.sandbox_root / path_obj
                
                # Check if path is within sandbox
                try:
                    path_obj.resolve().relative_to(self.sandbox_root.resolve())
                except ValueError:
                    logger.warning(f"Path outside sandbox: {path}")
                    return None
                
                # Check extension for write operations
                if (path_obj.suffix and
                        path_obj.suffix not in self.allowed_extensions):
                    logger.warning(f"Disallowed extension: {path_obj.suffix}")
                    return None
            
            return path_obj
            
        except Exception as e:
            logger.error(f"Path resolution error: {e}")
            return None
    
    def _execute_operation(
        self, 
        operation: str, 
        path: Path, 
        params: Dict[str, Any]
    ) -> ToolResult:
        """Execute the specific operation"""
        # Read operations
        if operation == 'read':
            return self._read_file(path, params)
        elif operation == 'read_json':
            return self._read_json(path, params)
            
        # Write operations
        elif operation == 'write':
            return self._write_file(path, params)
        elif operation == 'write_json':
            return self._write_json(path, params)
            
        # File operations
        elif operation == 'exists':
            return ToolResult(
                success=True,
                output=path.exists(),
                metadata={'path': str(path)}
            )
        elif operation == 'info':
            return self._get_file_info(path, params)
            
        # Directory operations
        elif operation == 'list_dir':
            return self._list_directory(path, params)
        elif operation == 'create_dir':
            if params.get('create_parents', True):
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.mkdir(exist_ok=True)
            return ToolResult(
                success=True,
                output=f"Created directory: {path}",
                metadata={'path': str(path)}
            )
            
        # Search operations
        elif operation == 'find_files':
            return self._find_files(path, params)
            
        # Utility operations
        elif operation == 'checksum':
            return self._calculate_checksum(path, params)
            
        else:
            return ToolResult(
                success=False,
                errors=[f"Operation not implemented: {operation}"],
                status=ToolStatus.FAILED
            )
    
    def _read_file(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Read file contents"""
        try:
            encoding = params.get('encoding', 'utf-8')
            max_size = params.get('max_size', 10485760)
            
            # Check file size
            if path.stat().st_size > max_size:
                return ToolResult(
                    success=False,
                    errors=[f"File too large: {path.stat().st_size} bytes"],
                    warnings=[f"Maximum size: {max_size} bytes"]
                )
            
            content = path.read_text(encoding=encoding)
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    'path': str(path),
                    'size': path.stat().st_size,
                    'lines': content.count('\n') + 1,
                    'encoding': encoding
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Read error: {e}"]
            )
    
    def _write_file(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Write content to file"""
        try:
            content = params.get('content', '')
            encoding = params.get('encoding', 'utf-8')
            create_parents = params.get('create_parents', True)
            
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            path.write_text(content, encoding=encoding)
            
            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} characters to {path}",
                metadata={
                    'path': str(path),
                    'size': len(content),
                    'encoding': encoding
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Write error: {e}"]
            )
    
    def _read_json(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Read JSON file"""
        try:
            encoding = params.get('encoding', 'utf-8')
            
            with path.open('r', encoding=encoding) as f:
                data = json.load(f)
            
            return ToolResult(
                success=True,
                output=data,
                metadata={
                    'path': str(path),
                    'size': path.stat().st_size,
                    'encoding': encoding
                }
            )
            
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {e}"]
            )
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Read error: {e}"]
            )
    
    def _write_json(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Write JSON file"""
        try:
            content = params.get('content')
            encoding = params.get('encoding', 'utf-8')
            create_parents = params.get('create_parents', True)
            
            # Parse content if it's a string
            if isinstance(content, str):
                data = json.loads(content)
            else:
                data = content
            
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            with path.open('w', encoding=encoding) as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return ToolResult(
                success=True,
                output=f"Wrote JSON to {path}",
                metadata={
                    'path': str(path),
                    'size': path.stat().st_size,
                    'encoding': encoding
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Write error: {e}"]
            )
    
    def _get_file_info(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Get file information"""
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    errors=[f"Path does not exist: {path}"]
                )
            
            stat = path.stat()
            info = {
                'path': str(path),
                'exists': True,
                'is_file': path.is_file(),
                'is_dir': path.is_dir(),
                'size': stat.st_size if path.is_file() else None,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'permissions': oct(stat.st_mode)[-3:]
            }
            
            if path.is_file():
                info['extension'] = path.suffix
                info['name'] = path.name
                info['parent'] = str(path.parent)
            
            return ToolResult(
                success=True,
                output=info,
                metadata=info
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Info error: {e}"]
            )
    
    def _list_directory(
        self, path: Path, params: Dict[str, Any]
    ) -> ToolResult:
        """List directory contents"""
        try:
            pattern = params.get('pattern', '*')
            recursive = params.get('recursive', False)
            
            if not path.is_dir():
                return ToolResult(
                    success=False,
                    errors=[f"Not a directory: {path}"]
                )
            
            if recursive:
                files = list(path.rglob(pattern))
            else:
                files = list(path.glob(pattern))
            
            file_info = []
            for f in files:
                if f.is_file():
                    file_info.append({
                        'path': str(f.relative_to(path)),
                        'size': f.stat().st_size,
                        'modified': f.stat().st_mtime,
                        'is_dir': False
                    })
                elif f.is_dir():
                    file_info.append({
                        'path': str(f.relative_to(path)),
                        'is_dir': True
                    })
            
            return ToolResult(
                success=True,
                output=file_info,
                metadata={
                    'path': str(path),
                    'count': len(file_info),
                    'pattern': pattern,
                    'recursive': recursive
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"List error: {e}"]
            )
    
    def _find_files(self, path: Path, params: Dict[str, Any]) -> ToolResult:
        """Find files by pattern"""
        try:
            pattern = params.get('pattern', '*')
            recursive = params.get('recursive', True)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    errors=[f"Path does not exist: {path}"]
                )
            
            if path.is_file():
                # Single file check
                if path.match(pattern):
                    found = [str(path)]
                else:
                    found = []
            else:
                # Directory search
                if recursive:
                    found = [str(f) for f in path.rglob(pattern)
                             if f.is_file()]
                else:
                    found = [str(f) for f in path.glob(pattern) if f.is_file()]
            
            return ToolResult(
                success=True,
                output=found,
                metadata={
                    'path': str(path),
                    'pattern': pattern,
                    'count': len(found),
                    'recursive': recursive
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Search error: {e}"]
            )
    
    def _calculate_checksum(
        self, path: Path, params: Dict[str, Any]
    ) -> ToolResult:
        """Calculate file checksum"""
        try:
            algorithm = params.get('algorithm', 'sha256')
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    errors=[f"Not a file: {path}"]
                )
            
            # Get hash function
            hash_func = getattr(hashlib, algorithm, None)
            if not hash_func:
                return ToolResult(
                    success=False,
                    errors=[f"Unknown algorithm: {algorithm}"]
                )
            
            # Calculate checksum
            hasher = hash_func()
            with path.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            
            checksum = hasher.hexdigest()
            
            return ToolResult(
                success=True,
                output=checksum,
                metadata={
                    'path': str(path),
                    'algorithm': algorithm,
                    'checksum': checksum,
                    'size': path.stat().st_size
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                errors=[f"Checksum error: {e}"]
            )
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info("FileTool shutting down")
        # No specific cleanup needed for this tool