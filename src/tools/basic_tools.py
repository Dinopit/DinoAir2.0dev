"""
Basic tool functions for DinoAir 2.0 OllamaAgent integration

This module provides fundamental tool functions that can be discovered and used
by the OllamaAgent for enhanced AI assistance capabilities.

All tool functions must have descriptive docstrings with parameter and return
type documentation for proper discovery by the agent system.
"""

import json
import subprocess
import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Import the new AI-accessible tool modules
from .notes_tool import NOTES_TOOLS
from .file_search_tool import FILE_SEARCH_TOOLS
from .projects_tool import PROJECTS_TOOLS


def add_two_numbers(a: float, b: float) -> Dict[str, Any]:
    """
    Add two numbers together and return the result.
    
    This is a basic mathematical operation tool that demonstrates
    proper tool function structure with comprehensive documentation.
    
    Args:
        a (float): The first number to add
        b (float): The second number to add
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - result (float): The sum of the two numbers
            - operation (str): Description of the operation performed
            - success (bool): Whether the operation was successful
            
    Example:
        >>> add_two_numbers(5.0, 3.0)
        {'result': 8.0, 'operation': 'addition', 'success': True}
    """
    try:
        result = a + b
        return {
            "result": result,
            "operation": f"{a} + {b} = {result}",
            "success": True
        }
    except Exception as e:
        return {
            "result": None,
            "operation": f"Failed to add {a} + {b}",
            "success": False,
            "error": str(e)
        }


def get_current_time() -> Dict[str, Any]:
    """
    Get the current date and time in multiple formats.
    
    Returns comprehensive time information including local time,
    UTC time, and formatted strings for various use cases.
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - local_time (str): Local time in ISO format
            - utc_time (str): UTC time in ISO format  
            - formatted_time (str): Human-readable local time
            - timestamp (float): Unix timestamp
            - success (bool): Whether the operation was successful
            
    Example:
        >>> get_current_time()
        {
            'local_time': '2025-01-05T15:30:00.123456',
            'utc_time': '2025-01-05T20:30:00.123456Z',
            'formatted_time': 'January 5, 2025 at 3:30 PM',
            'timestamp': 1736106600.123456,
            'success': True
        }
    """
    try:
        now_local = datetime.datetime.now()
        now_utc = datetime.datetime.utcnow()
        
        return {
            "local_time": now_local.isoformat(),
            "utc_time": now_utc.isoformat() + "Z",
            "formatted_time": now_local.strftime("%B %d, %Y at %I:%M %p"),
            "timestamp": now_local.timestamp(),
            "success": True
        }
    except Exception as e:
        return {
            "local_time": None,
            "utc_time": None,
            "formatted_time": None,
            "timestamp": None,
            "success": False,
            "error": str(e)
        }


def list_directory_contents(path: str = ".") -> Dict[str, Any]:
    """
    List the contents of a directory with detailed information.
    
    Provides comprehensive directory listing including file types,
    sizes, and modification times for better file system navigation.
    
    Args:
        path (str): The directory path to list (defaults to current directory)
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - files (List[Dict]): List of files with details
            - directories (List[Dict]): List of subdirectories with details
            - total_items (int): Total number of items found
            - path (str): The path that was listed
            - success (bool): Whether the operation was successful
            
    Example:
        >>> list_directory_contents("/home/user")
        {
            'files': [{'name': 'file.txt', 'size': 1024,
                      'modified': '2025-01-05T15:30:00'}],
            'directories': [{'name': 'Documents',
                           'modified': '2025-01-05T10:00:00'}],
            'total_items': 2,
            'path': '/home/user',
            'success': True
        }
    """
    try:
        path_obj = Path(path)
        
        if not path_obj.exists():
            return {
                "files": [],
                "directories": [],
                "total_items": 0,
                "path": str(path),
                "success": False,
                "error": f"Path does not exist: {path}"
            }
        
        if not path_obj.is_dir():
            return {
                "files": [],
                "directories": [],
                "total_items": 0,
                "path": str(path),
                "success": False,
                "error": f"Path is not a directory: {path}"
            }
        
        files = []
        directories = []
        
        for item in path_obj.iterdir():
            modified_time = datetime.datetime.fromtimestamp(
                item.stat().st_mtime
            ).isoformat()
            
            if item.is_file():
                item_info = {
                    "name": item.name,
                    "modified": modified_time,
                    "size": item.stat().st_size
                }
                files.append(item_info)
            elif item.is_dir():
                item_info = {
                    "name": item.name,
                    "modified": modified_time
                }
                directories.append(item_info)
        
        return {
            "files": sorted(files, key=lambda x: x["name"]),
            "directories": sorted(directories, key=lambda x: x["name"]),
            "total_items": len(files) + len(directories),
            "path": str(path_obj.absolute()),
            "success": True
        }
        
    except Exception as e:
        return {
            "files": [],
            "directories": [],
            "total_items": 0,
            "path": str(path),
            "success": False,
            "error": str(e)
        }


def read_text_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Read the contents of a text file safely with error handling.
    
    Reads text files with proper encoding handling and provides
    comprehensive error reporting for file operations.
    
    Args:
        file_path (str): Path to the text file to read
        encoding (str): File encoding (defaults to utf-8)
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - content (str): The file contents
            - file_path (str): The path that was read
            - size (int): File size in bytes
            - lines (int): Number of lines in the file
            - encoding (str): Encoding used to read the file
            - success (bool): Whether the operation was successful
            
    Example:
        >>> read_text_file("config.txt")
        {
            'content': 'Configuration data...',
            'file_path': '/path/to/config.txt',
            'size': 1024,
            'lines': 25,
            'encoding': 'utf-8',
            'success': True
        }
    """
    try:
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {
                "content": "",
                "file_path": str(file_path),
                "size": 0,
                "lines": 0,
                "encoding": encoding,
                "success": False,
                "error": f"File does not exist: {file_path}"
            }
        
        if not file_path_obj.is_file():
            return {
                "content": "",
                "file_path": str(file_path),
                "size": 0,
                "lines": 0,
                "encoding": encoding,
                "success": False,
                "error": f"Path is not a file: {file_path}"
            }
        
        with open(file_path_obj, 'r', encoding=encoding) as f:
            content = f.read()
        
        lines = content.count('\n') + 1 if content else 0
        size = file_path_obj.stat().st_size
        
        return {
            "content": content,
            "file_path": str(file_path_obj.absolute()),
            "size": size,
            "lines": lines,
            "encoding": encoding,
            "success": True
        }
        
    except UnicodeDecodeError as e:
        return {
            "content": "",
            "file_path": str(file_path),
            "size": 0,
            "lines": 0,
            "encoding": encoding,
            "success": False,
            "error": f"Encoding error: {e}"
        }
    except Exception as e:
        return {
            "content": "",
            "file_path": str(file_path),
            "size": 0,
            "lines": 0,
            "encoding": encoding,
            "success": False,
            "error": str(e)
        }


def execute_system_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a system command safely with timeout protection.
    
    Runs system commands with proper error handling, timeout protection,
    and comprehensive output capture for system automation tasks.
    
    Args:
        command (str): The system command to execute
        timeout (int): Maximum execution time in seconds (defaults to 30)
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - stdout (str): Standard output from the command
            - stderr (str): Standard error from the command
            - return_code (int): Command exit code
            - command (str): The command that was executed
            - execution_time (float): Time taken to execute
            - success (bool): Whether the command succeeded (return code 0)
            
    Example:
        >>> execute_system_command("echo 'Hello World'")
        {
            'stdout': 'Hello World\n',
            'stderr': '',
            'return_code': 0,
            'command': "echo 'Hello World'",
            'execution_time': 0.05,
            'success': True
        }
    """
    try:
        start_time = datetime.datetime.now()
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        execution_time = (datetime.datetime.now() - start_time).total_seconds()
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "command": command,
            "execution_time": execution_time,
            "success": result.returncode == 0
        }
        
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
            "return_code": -1,
            "command": command,
            "execution_time": timeout,
            "success": False,
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
            "command": command,
            "execution_time": 0,
            "success": False,
            "error": str(e)
        }


def create_json_data(data: Dict[str, Any],
                     file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Create or manipulate JSON data with optional file output.
    
    Provides JSON data handling capabilities including validation,
    formatting, and optional file persistence for data management tasks.
    
    Args:
        data (Dict[str, Any]): The data to convert to JSON
        file_path (Optional[str]): Optional path to save the JSON file
        
    Returns:
        Dict[str, Any]: A dictionary containing:
            - json_string (str): The formatted JSON string
            - data (Dict): The original data
            - file_written (bool): Whether file was written (if path provided)
            - file_path (str): Path where file was written (if applicable)
            - size (int): Size of the JSON string in characters
            - success (bool): Whether the operation was successful
            
    Example:
        >>> create_json_data({"name": "test", "value": 42}, "output.json")
        {
            'json_string': '{\n  "name": "test",\n  "value": 42\n}',
            'data': {"name": "test", "value": 42},
            'file_written': True,
            'file_path': '/path/to/output.json',
            'size': 35,
            'success': True
        }
    """
    try:
        # Convert to JSON with pretty formatting
        json_string = json.dumps(data, indent=2, ensure_ascii=False)
        
        result = {
            "json_string": json_string,
            "data": data,
            "file_written": False,
            "file_path": file_path,
            "size": len(json_string),
            "success": True
        }
        
        # Write to file if path provided
        if file_path:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path_obj, 'w', encoding='utf-8') as f:
                f.write(json_string)
            
            result["file_written"] = True
            result["file_path"] = str(file_path_obj.absolute())
        
        return result
        
    except Exception as e:
        return {
            "json_string": "",
            "data": data,
            "file_written": False,
            "file_path": file_path,
            "size": 0,
            "success": False,
            "error": str(e)
        }


# Tool registry for discovery
AVAILABLE_TOOLS = {
    # Basic utility tools
    "add_two_numbers": add_two_numbers,
    "get_current_time": get_current_time,
    "list_directory_contents": list_directory_contents,
    "read_text_file": read_text_file,
    "execute_system_command": execute_system_command,
    "create_json_data": create_json_data,
}

# Add AI-accessible GUI tool wrappers
AVAILABLE_TOOLS.update(NOTES_TOOLS)
AVAILABLE_TOOLS.update(FILE_SEARCH_TOOLS)
AVAILABLE_TOOLS.update(PROJECTS_TOOLS)