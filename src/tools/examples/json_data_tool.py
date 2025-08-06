"""
JSON Data Tool for DinoAir 2.0

JSON manipulation and validation tool with comprehensive operations.
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path

from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolCategory, ParameterType
)


logger = logging.getLogger(__name__)


class JsonDataTool(BaseTool):
    """Tool for JSON data manipulation, validation and analysis."""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata."""
        return ToolMetadata(
            name="json_data",
            version="1.0.0",
            description="JSON manipulation, validation and analysis tool",
            author="DinoAir Team",
            category=ToolCategory.TRANSFORMATION,
            tags=["json", "data", "validation", "manipulation"],
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.ENUM,
                    description="JSON operation to perform",
                    required=True,
                    enum_values=[
                        "validate", "pretty_print", "minify", "extract",
                        "merge", "filter", "transform", "compare",
                        "analyze", "from_file", "to_file"
                    ],
                    example="validate"
                ),
                ToolParameter(
                    name="data",
                    type=ParameterType.STRING,
                    description="JSON data as string or file path",
                    required=False,
                    example='{"key": "value"}'
                ),
                ToolParameter(
                    name="data2",
                    type=ParameterType.STRING,
                    description="Second JSON data for merge/compare ops",
                    required=False,
                    example='{"key2": "value2"}'
                ),
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="JSON path for extract/filter operations",
                    required=False,
                    example="$.users[0].name"
                ),
                ToolParameter(
                    name="file_path",
                    type=ParameterType.FILE_PATH,
                    description="File path for file operations",
                    required=False,
                    example="/path/to/data.json"
                ),
                ToolParameter(
                    name="indent",
                    type=ParameterType.INTEGER,
                    description="Indentation for pretty printing",
                    required=False,
                    default=2,
                    min_value=0,
                    max_value=8,
                    example=4
                ),
                ToolParameter(
                    name="sort_keys",
                    type=ParameterType.BOOLEAN,
                    description="Sort keys when formatting",
                    required=False,
                    default=False,
                    example=True
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": False,
                "progress_reporting": False,
                "batch_processing": True,
                "caching": False,
                "stateful": False
            },
            examples=[
                {
                    "name": "Validate JSON",
                    "description": "Validate JSON string",
                    "parameters": {
                        "operation": "validate",
                        "data": '{"name": "John", "age": 30}'
                    }
                },
                {
                    "name": "Pretty print JSON",
                    "description": "Format JSON with indentation",
                    "parameters": {
                        "operation": "pretty_print",
                        "data": '{"name":"John","age":30}',
                        "indent": 4
                    }
                },
                {
                    "name": "Extract JSON path",
                    "description": "Extract value from JSON path",
                    "parameters": {
                        "operation": "extract",
                        "data": '{"users": [{"name": "John"}]}',
                        "path": "$.users[0].name"
                    }
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool."""
        logger.info("JsonDataTool initialized")
        self._max_file_size = 10 * 1024 * 1024  # 10MB limit
        self._max_depth = 100  # Maximum nesting depth
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute JSON operation."""
        try:
            operation = kwargs.get('operation')
            data = kwargs.get('data')
            data2 = kwargs.get('data2')
            path = kwargs.get('path')
            file_path = kwargs.get('file_path')
            indent = kwargs.get('indent', 2)
            sort_keys = kwargs.get('sort_keys', False)
            
            # Validate operation
            if not operation:
                return ToolResult(
                    success=False,
                    errors=["Operation is required"]
                )
            
            # Execute operation
            if operation == "validate":
                return self._validate_json(data or "")
            elif operation == "pretty_print":
                return self._pretty_print_json(data or "", indent, sort_keys)
            elif operation == "minify":
                return self._minify_json(data or "")
            elif operation == "extract":
                return self._extract_json_path(data or "", path or "")
            elif operation == "merge":
                return self._merge_json(data or "", data2 or "")
            elif operation == "filter":
                return self._filter_json(data or "", path or "")
            elif operation == "compare":
                return self._compare_json(data or "", data2 or "")
            elif operation == "analyze":
                return self._analyze_json(data or "")
            elif operation == "from_file":
                return self._load_from_file(file_path or "")
            elif operation == "to_file":
                return self._save_to_file(data or "", file_path or "",
                                          indent, sort_keys)
            else:
                return ToolResult(
                    success=False,
                    errors=[f"Unknown operation: {operation}"]
                )
                
        except Exception as e:
            logger.error(f"JSON operation failed: {e}")
            return ToolResult(
                success=False,
                errors=[f"JSON operation failed: {str(e)}"]
            )
    
    def _validate_json(self, data: str) -> ToolResult:
        """Validate JSON string."""
        if not data:
            return ToolResult(
                success=False,
                errors=["No data provided for validation"]
            )
        
        try:
            parsed = json.loads(data)
            return ToolResult(
                success=True,
                output={
                    "valid": True,
                    "type": type(parsed).__name__,
                    "size": len(str(parsed))
                },
                metadata={"operation": "validate"}
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output={"valid": False},
                errors=[f"Invalid JSON: {str(e)}"],
                metadata={"operation": "validate", "error_type": "parse_error"}
            )
    
    def _pretty_print_json(self, data: str, indent: int,
                           sort_keys: bool) -> ToolResult:
        """Pretty print JSON with formatting."""
        try:
            parsed = json.loads(data)
            formatted = json.dumps(
                parsed, indent=indent, sort_keys=sort_keys,
                ensure_ascii=False
            )
            
            return ToolResult(
                success=True,
                output=formatted,
                metadata={
                    "operation": "pretty_print",
                    "indent": indent,
                    "sort_keys": sort_keys,
                    "size_before": len(data),
                    "size_after": len(formatted)
                }
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _minify_json(self, data: str) -> ToolResult:
        """Minify JSON by removing whitespace."""
        try:
            parsed = json.loads(data)
            minified = json.dumps(parsed, separators=(',', ':'))
            
            return ToolResult(
                success=True,
                output=minified,
                metadata={
                    "operation": "minify",
                    "size_before": len(data),
                    "size_after": len(minified),
                    "compression_ratio": len(minified) / len(data)
                }
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _extract_json_path(self, data: str, path: str) -> ToolResult:
        """Extract value from JSON using simple path notation."""
        if not path:
            return ToolResult(
                success=False,
                errors=["Path is required for extract operation"]
            )
        
        try:
            parsed = json.loads(data)
            result = self._get_nested_value(parsed, path)
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    "operation": "extract",
                    "path": path,
                    "result_type": type(result).__name__
                }
            )
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
            return ToolResult(
                success=False,
                errors=[f"Extract failed: {str(e)}"]
            )
    
    def _merge_json(self, data1: str, data2: str) -> ToolResult:
        """Merge two JSON objects."""
        if not data1 or not data2:
            return ToolResult(
                success=False,
                errors=["Both data and data2 are required for merge"]
            )
        
        try:
            obj1 = json.loads(data1)
            obj2 = json.loads(data2)
            
            if not isinstance(obj1, dict) or not isinstance(obj2, dict):
                return ToolResult(
                    success=False,
                    errors=["Both objects must be JSON objects for merge"]
                )
            
            merged = {**obj1, **obj2}
            result = json.dumps(merged, indent=2)
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    "operation": "merge",
                    "keys_in_data1": len(obj1),
                    "keys_in_data2": len(obj2),
                    "keys_in_result": len(merged)
                }
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _filter_json(self, data: str, path: str) -> ToolResult:
        """Filter JSON data based on path criteria."""
        # Simplified filtering - in a real implementation,
        # you'd use JSONPath or similar
        try:
            parsed = json.loads(data)
            # Basic filtering logic
            filtered = self._apply_filter(parsed, path)
            result = json.dumps(filtered, indent=2)
            
            return ToolResult(
                success=True,
                output=result,
                metadata={"operation": "filter", "filter": path}
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _compare_json(self, data1: str, data2: str) -> ToolResult:
        """Compare two JSON objects."""
        if not data1 or not data2:
            return ToolResult(
                success=False,
                errors=["Both data and data2 are required for comparison"]
            )
        
        try:
            obj1 = json.loads(data1)
            obj2 = json.loads(data2)
            
            are_equal = obj1 == obj2
            
            return ToolResult(
                success=True,
                output={
                    "equal": are_equal,
                    "type1": type(obj1).__name__,
                    "type2": type(obj2).__name__,
                    "size1": len(str(obj1)),
                    "size2": len(str(obj2))
                },
                metadata={"operation": "compare"}
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _analyze_json(self, data: str) -> ToolResult:
        """Analyze JSON structure and provide statistics."""
        try:
            parsed = json.loads(data)
            analysis = self._get_json_stats(parsed)
            
            return ToolResult(
                success=True,
                output=analysis,
                metadata={"operation": "analyze"}
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
    
    def _load_from_file(self, file_path: str) -> ToolResult:
        """Load JSON from file."""
        if not file_path:
            return ToolResult(
                success=False,
                errors=["File path is required"]
            )
        
        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    errors=[f"File not found: {file_path}"]
                )
            
            if path.stat().st_size > self._max_file_size:
                return ToolResult(
                    success=False,
                    errors=[f"File too large: {path.stat().st_size} bytes"]
                )
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                parsed = json.loads(content)
            
            return ToolResult(
                success=True,
                output=content,
                metadata={
                    "operation": "from_file",
                    "file_path": str(path),
                    "file_size": path.stat().st_size,
                    "data_type": type(parsed).__name__
                }
            )
        except (json.JSONDecodeError, IOError) as e:
            return ToolResult(
                success=False,
                errors=[f"Failed to load JSON file: {str(e)}"]
            )
    
    def _save_to_file(self, data: str, file_path: str, indent: int,
                      sort_keys: bool) -> ToolResult:
        """Save JSON to file."""
        if not data or not file_path:
            return ToolResult(
                success=False,
                errors=["Both data and file_path are required"]
            )
        
        try:
            parsed = json.loads(data)
            path = Path(file_path)
            
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=indent, sort_keys=sort_keys,
                          ensure_ascii=False)
            
            return ToolResult(
                success=True,
                output=f"JSON saved to {file_path}",
                metadata={
                    "operation": "to_file",
                    "file_path": str(path),
                    "file_size": path.stat().st_size
                }
            )
        except (json.JSONDecodeError, IOError) as e:
            return ToolResult(
                success=False,
                errors=[f"Failed to save JSON file: {str(e)}"]
            )
    
    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Get nested value using simple dot notation."""
        # Simple path parsing - in production, use JSONPath library
        if path.startswith('$.'):
            path = path[2:]
        
        parts = path.split('.')
        current = data
        
        for part in parts:
            if '[' in part and ']' in part:
                # Handle array access like users[0]
                key, index_part = part.split('[', 1)
                index = int(index_part.rstrip(']'))
                if key:
                    current = current[key]
                current = current[index]
            else:
                current = current[part]
        
        return current
    
    def _apply_filter(self, data: Any, filter_criteria: str) -> Any:
        """Apply basic filtering to JSON data."""
        # Simplified filtering - implement more sophisticated logic as needed
        if isinstance(data, dict):
            if filter_criteria in data:
                return {filter_criteria: data[filter_criteria]}
        elif isinstance(data, list):
            return [item for item in data if str(filter_criteria) in str(item)]
        
        return data
    
    def _get_json_stats(self, data: Any, depth: int = 0) -> Dict[str, Any]:
        """Get statistics about JSON structure."""
        stats = {
            "type": type(data).__name__,
            "depth": depth,
            "size": 1
        }
        
        if isinstance(data, dict):
            stats.update({
                "keys": len(data),
                "key_types": list(set(type(k).__name__ for k in data.keys())),
                "value_types": list(set(type(v).__name__
                                        for v in data.values()))
            })
            if data:
                max_subdepth = max(
                    self._get_json_stats(v, depth + 1)["depth"]
                    for v in data.values()
                )
                stats["max_depth"] = max_subdepth
        elif isinstance(data, list):
            stats.update({
                "length": len(data),
                "item_types": list(set(type(item).__name__ for item in data))
            })
            if data:
                max_subdepth = max(
                    self._get_json_stats(item, depth + 1)["depth"]
                    for item in data
                )
                stats["max_depth"] = max_subdepth
        elif isinstance(data, str):
            stats["string_length"] = len(data)
        
        return stats
    
    def shutdown(self):
        """Cleanup tool resources."""
        logger.info("JsonDataTool shutting down")
        # No persistent resources to clean up