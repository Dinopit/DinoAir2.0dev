"""
ToolAdapter Execution Layer

This module provides the final execution pipeline component for bulletproof
tool execution. It serves as a direct bridge between model tool_call JSON
and actual Python function execution.

Key Features:
- Direct tool name to function mapping
- Bulletproof error handling and timeout support
- Structured success/failure response format
- Comprehensive logging of all execution attempts
- Production-ready reliability and monitoring
"""

import logging
import asyncio
import time
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from concurrent.futures import (
    ThreadPoolExecutor, TimeoutError as FutureTimeoutError
)
import traceback

logger = logging.getLogger(__name__)


class ToolAdapter:
    """
    Production-ready tool execution adapter
    
    This adapter provides bulletproof execution of tools with comprehensive
    error handling, timeout protection, and standardized response formats.
    """
    
    def __init__(self, tool_registry: Optional[Dict[str, Callable]] = None, 
                 default_timeout: float = 30.0, max_workers: int = 4):
        """
        Initialize the ToolAdapter
        
        Args:
            tool_registry: Dictionary mapping tool names to functions
            default_timeout: Default execution timeout in seconds
            max_workers: Maximum number of worker threads
        """
        self.tool_registry = tool_registry or {}
        self.default_timeout = default_timeout
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Execution statistics
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_execution_time = 0.0
        
        logger.info(
            f"ToolAdapter initialized with {len(self.tool_registry)} tools"
        )
    
    def register_tool(self, name: str, function: Callable) -> bool:
        """
        Register a tool function
        
        Args:
            name: Tool name
            function: Tool function
            
        Returns:
            True if successfully registered
        """
        try:
            if not callable(function):
                logger.error(
                    f"Cannot register non-callable object as tool '{name}'"
                )
                return False
            
            self.tool_registry[name] = function
            logger.info(f"Registered tool: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool '{name}': {e}")
            return False
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            name: Tool name to unregister
            
        Returns:
            True if successfully unregistered
        """
        if name in self.tool_registry:
            del self.tool_registry[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False
    
    def list_tools(self) -> List[str]:
        """
        Get list of registered tool names
        
        Returns:
            List of tool names
        """
        return list(self.tool_registry.keys())
    
    def has_tool(self, name: str) -> bool:
        """
        Check if tool is registered
        
        Args:
            name: Tool name
            
        Returns:
            True if tool exists
        """
        return name in self.tool_registry
    
    def execute_tool(self, name: str, parameters: Dict[str, Any],
                     timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a tool with bulletproof error handling
        
        Args:
            name: Tool name
            parameters: Tool parameters
            timeout: Execution timeout (uses default if None)
            
        Returns:
            Standardized execution result dictionary
        """
        start_time = time.time()
        execution_timeout = timeout or self.default_timeout
        
        # Update statistics
        self.execution_count += 1
        
        try:
            logger.info(
                f"Executing tool '{name}' with parameters: {parameters}"
            )
            
            # Check if tool exists
            if name not in self.tool_registry:
                self.failure_count += 1
                error_msg = f"Tool '{name}' not found"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": "ToolNotFound",
                    "execution_time": time.time() - start_time,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Get the tool function
            tool_function = self.tool_registry[name]
            
            # Execute with timeout protection
            try:
                future = self.executor.submit(
                    self._safe_execute, tool_function, parameters
                )
                result = future.result(timeout=execution_timeout)
                
                execution_time = time.time() - start_time
                self.total_execution_time += execution_time
                
                # Handle different result formats
                if isinstance(result, dict):
                    # Tool returned structured result
                    success = result.get('success', True)
                    if success:
                        self.success_count += 1
                    else:
                        self.failure_count += 1
                    
                    # Ensure standard fields
                    result.setdefault('success', success)
                    result.setdefault('execution_time', execution_time)
                    result.setdefault('timestamp', datetime.now().isoformat())
                    
                    logger.info(
                        f"Tool '{name}' executed successfully in "
                        f"{execution_time:.2f}s"
                    )
                    return result
                else:
                    # Tool returned simple value
                    self.success_count += 1
                    logger.info(
                        f"Tool '{name}' executed successfully in "
                        f"{execution_time:.2f}s"
                    )
                    return {
                        "success": True,
                        "result": result,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat()
                    }
                
            except FutureTimeoutError:
                self.failure_count += 1
                error_msg = (
                    f"Tool '{name}' execution timed out after "
                    f"{execution_timeout}s"
                )
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": "TimeoutError",
                    "execution_time": execution_timeout,
                    "timestamp": datetime.now().isoformat()
                }
            
        except Exception as e:
            self.failure_count += 1
            execution_time = time.time() - start_time
            error_msg = f"Unexpected error executing tool '{name}': {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": type(e).__name__,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_exc()
            }
    
    def _safe_execute(self, tool_function: Callable,
                      parameters: Dict[str, Any]) -> Any:
        """
        Safely execute a tool function with parameter validation
        
        Args:
            tool_function: Function to execute
            parameters: Function parameters
            
        Returns:
            Function result
            
        Raises:
            Various exceptions for different failure modes
        """
        try:
            # Validate parameters are a dictionary
            if not isinstance(parameters, dict):
                raise ValueError(
                    f"Parameters must be a dictionary, got {type(parameters)}"
                )
            
            # Execute the function
            return tool_function(**parameters)
            
        except TypeError as e:
            if "unexpected keyword argument" in str(e) or "missing" in str(e):
                raise ValueError(f"Invalid parameters for tool: {e}")
            else:
                raise
        except Exception as e:
            # Re-raise with original exception type
            raise
    
    async def execute_tool_async(self, name: str, parameters: Dict[str, Any],
                                 timeout: Optional[float] = None
                                 ) -> Dict[str, Any]:
        """
        Async version of execute_tool
        
        Args:
            name: Tool name
            parameters: Tool parameters
            timeout: Execution timeout
            
        Returns:
            Standardized execution result dictionary
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.execute_tool, name, parameters, timeout
        )
    
    def batch_execute(self, executions: List[Dict[str, Any]],
                      stop_on_error: bool = False) -> List[Dict[str, Any]]:
        """
        Execute multiple tools in batch
        
        Args:
            executions: List of {"name": str, "parameters": dict} dicts
            stop_on_error: Whether to stop on first error
            
        Returns:
            List of execution results
        """
        results = []
        
        for execution in executions:
            name = execution.get("name")
            parameters = execution.get("parameters", {})
            
            if not name:
                results.append({
                    "success": False,
                    "error": "Missing tool name in execution request",
                    "error_type": "ValidationError",
                    "timestamp": datetime.now().isoformat()
                })
                if stop_on_error:
                    break
                continue
            
            result = self.execute_tool(name, parameters)
            results.append(result)
            
            if not result["success"] and stop_on_error:
                logger.warning(
                    f"Stopping batch execution due to error in tool '{name}'"
                )
                break
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics
        
        Returns:
            Statistics dictionary
        """
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        success_rate = (
            self.success_count / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        return {
            "total_executions": self.execution_count,
            "successful_executions": self.success_count,
            "failed_executions": self.failure_count,
            "success_rate": success_rate,
            "average_execution_time": avg_execution_time,
            "total_execution_time": self.total_execution_time,
            "registered_tools": len(self.tool_registry),
            "available_tools": self.list_tools()
        }
    
    def reset_statistics(self):
        """Reset execution statistics"""
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_execution_time = 0.0
        logger.info("ToolAdapter statistics reset")
    
    def shutdown(self):
        """Shutdown the tool adapter and cleanup resources"""
        try:
            self.executor.shutdown(wait=True)
            logger.info("ToolAdapter shutdown completed")
        except Exception as e:
            logger.error(f"Error during ToolAdapter shutdown: {e}")


# Global production registry
TOOL_REGISTRY: Dict[str, Callable] = {}


def register_tool(name: str, function: Callable) -> bool:
    """
    Global helper function to register tools
    
    Args:
        name: Tool name
        function: Tool function
        
    Returns:
        True if successfully registered
    """
    global TOOL_REGISTRY
    
    try:
        if not callable(function):
            logger.error(
                f"Cannot register non-callable object as tool '{name}'"
            )
            return False
        
        TOOL_REGISTRY[name] = function
        logger.info(f"Globally registered tool: {name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to globally register tool '{name}': {e}")
        return False


def get_global_registry() -> Dict[str, Callable]:
    """
    Get the global tool registry
    
    Returns:
        Global tool registry dictionary
    """
    return TOOL_REGISTRY.copy()


def create_production_tool_adapter() -> ToolAdapter:
    """
    Create a production-ready ToolAdapter with all registered tools
    
    Returns:
        Configured ToolAdapter instance
    """
    return ToolAdapter(tool_registry=TOOL_REGISTRY.copy())


def initialize_production_registry():
    """
    Initialize the production registry with all available tools
    
    This function registers all 38+ tools from:
    - Basic utility tools (6 tools)
    - Notes management tools (8 tools)
    - File search tools (8 tools)
    - Project management tools (9 tools)
    - Additional example tools (7+ tools)
    """
    global TOOL_REGISTRY
    
    try:
        total_registered = 0
        
        # 1. Register basic utility tools
        try:
            from ..basic_tools import AVAILABLE_TOOLS
            logger.info(f"Registering {len(AVAILABLE_TOOLS)} basic tools")
            
            for tool_name, tool_function in AVAILABLE_TOOLS.items():
                if register_tool(tool_name, tool_function):
                    total_registered += 1
                    
        except ImportError as e:
            logger.error(f"Failed to import basic_tools: {e}")
        
        # 2. Register notes tools (these are included in AVAILABLE_TOOLS but
        # let's verify they're there)
        try:
            from ..notes_tool import NOTES_TOOLS
            logger.info(f"Notes tools available: {len(NOTES_TOOLS)}")
            
            # These should already be in AVAILABLE_TOOLS, but register any missing
            for tool_name, tool_function in NOTES_TOOLS.items():
                if tool_name not in TOOL_REGISTRY:
                    if register_tool(tool_name, tool_function):
                        total_registered += 1
                        
        except ImportError as e:
            logger.warning(f"Could not import notes_tool: {e}")
        
        # 3. Register file search tools
        try:
            from ..file_search_tool import FILE_SEARCH_TOOLS
            logger.info(f"File search tools available: {len(FILE_SEARCH_TOOLS)}")
            
            for tool_name, tool_function in FILE_SEARCH_TOOLS.items():
                if tool_name not in TOOL_REGISTRY:
                    if register_tool(tool_name, tool_function):
                        total_registered += 1
                        
        except ImportError as e:
            logger.warning(f"Could not import file_search_tool: {e}")
        
        # 4. Register project management tools
        try:
            from ..projects_tool import PROJECTS_TOOLS
            logger.info(f"Project tools available: {len(PROJECTS_TOOLS)}")
            
            for tool_name, tool_function in PROJECTS_TOOLS.items():
                if tool_name not in TOOL_REGISTRY:
                    if register_tool(tool_name, tool_function):
                        total_registered += 1
                        
        except ImportError as e:
            logger.warning(f"Could not import projects_tool: {e}")
        
        # 5. Register additional example tools
        try:
            from pathlib import Path
            examples_dir = Path(__file__).parent.parent / "examples"
            
            if examples_dir.exists():
                # Import and register example tools
                example_tools = {}
                
                try:
                    from ..examples.math_tool import MATH_TOOLS
                    example_tools.update(MATH_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.time_tool import TIME_TOOLS
                    example_tools.update(TIME_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.directory_tool import DIRECTORY_TOOLS
                    example_tools.update(DIRECTORY_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.file_tool import FILE_TOOLS
                    example_tools.update(FILE_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.system_command_tool import SYSTEM_TOOLS
                    example_tools.update(SYSTEM_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.system_info_tool import SYSTEM_INFO_TOOLS
                    example_tools.update(SYSTEM_INFO_TOOLS)
                except ImportError:
                    pass
                    
                try:
                    from ..examples.json_data_tool import JSON_TOOLS
                    example_tools.update(JSON_TOOLS)
                except ImportError:
                    pass
                
                logger.info(f"Example tools available: {len(example_tools)}")
                
                for tool_name, tool_function in example_tools.items():
                    if tool_name not in TOOL_REGISTRY:
                        if register_tool(tool_name, tool_function):
                            total_registered += 1
                            
        except Exception as e:
            logger.warning(f"Could not load example tools: {e}")
        
        # Final registry summary
        final_count = len(TOOL_REGISTRY)
        logger.info(
            f"Production registry initialization complete: "
            f"{final_count} total tools registered"
        )
        
        # Log all registered tools for verification
        tool_names = sorted(TOOL_REGISTRY.keys())
        logger.info(f"All registered tools ({len(tool_names)}): {tool_names}")
        
        # Categorize tools for better visibility
        basic_tools = [t for t in tool_names if any(x in t for x in [
            'add_two_numbers', 'get_current_time', 'list_directory',
            'read_text_file', 'execute_system', 'create_json'
        ])]
        notes_tools = [t for t in tool_names if any(x in t for x in [
            'note', 'notes', 'tag'
        ])]
        file_tools = [t for t in tool_names if any(x in t for x in [
            'file', 'search', 'index', 'embedding'
        ])]
        project_tools = [t for t in tool_names if any(x in t for x in [
            'project', 'statistics', 'tree'
        ])]
        
        logger.info(f"Tool categories registered:")
        logger.info(f"  Basic tools ({len(basic_tools)}): {basic_tools}")
        logger.info(f"  Notes tools ({len(notes_tools)}): {notes_tools}")
        logger.info(f"  File tools ({len(file_tools)}): {file_tools}")
        logger.info(f"  Project tools ({len(project_tools)}): {project_tools}")
        
        other_tools = [t for t in tool_names if t not in
                      basic_tools + notes_tools + file_tools + project_tools]
        if other_tools:
            logger.info(f"  Other tools ({len(other_tools)}): {other_tools}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize production registry: {e}")
        return False


# Initialize the production registry on module import
initialize_production_registry()