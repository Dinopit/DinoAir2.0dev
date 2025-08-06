"""
Hardened Tool Execution Dispatcher

This module provides a bulletproof tool execution pipeline with robust error handling,
parameter validation, and comprehensive logging. It ensures reliable tool execution
with proper fallback mechanisms and detailed error reporting.
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .ai_adapter import ToolAIAdapter
from .registry import ToolRegistry
from .base import BaseTool, ToolResult, ParameterType
from .control.tool_context import ExecutionContext

logger = logging.getLogger(__name__)


class ExecutionResult(Enum):
    """Tool execution result types"""
    SUCCESS = "success"
    TOOL_NOT_FOUND = "tool_not_found"
    PARAMETER_ERROR = "parameter_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"


@dataclass
class ToolExecutionMetrics:
    """Metrics for tool execution tracking"""
    tool_name: str
    start_time: float
    end_time: Optional[float] = None
    execution_time: Optional[float] = None
    result_type: Optional[ExecutionResult] = None
    error_details: Optional[str] = None
    retry_count: int = 0
    memory_usage: Optional[int] = None
    
    def mark_completed(self, result_type: ExecutionResult,
                      error_details: Optional[str] = None):
        """Mark execution as completed"""
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
        self.result_type = result_type
        self.error_details = error_details


@dataclass
class ToolExecutionConfig:
    """Configuration for tool execution"""
    max_execution_time: float = 30.0  # seconds
    max_retries: int = 2
    enable_parameter_validation: bool = True
    enable_error_recovery: bool = True
    enable_detailed_logging: bool = True
    fallback_response_enabled: bool = True
    memory_limit_mb: Optional[int] = 100  # MB


class HardenedToolDispatcher:
    """
    Hardened tool execution dispatcher with comprehensive error handling
    
    This dispatcher provides:
    - Robust error handling and recovery
    - Parameter validation and sanitization
    - Execution timeouts and resource limits
    - Comprehensive logging and metrics
    - Fallback mechanisms for failed tools
    - Structured error responses
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        config: Optional[ToolExecutionConfig] = None
    ):
        """
        Initialize the hardened dispatcher
        
        Args:
            registry: Tool registry instance
            config: Execution configuration
        """
        self.registry = registry or ToolRegistry()
        self.config = config or ToolExecutionConfig()
        self.ai_adapter = ToolAIAdapter(registry=self.registry)
        
        # Execution tracking
        self.execution_metrics: List[ToolExecutionMetrics] = []
        self.tool_usage_stats: Dict[str, Dict[str, Any]] = {}
        self.failed_tools: Dict[str, List[str]] = {}
        
        # Tool mapping cache for performance
        self._tool_mapping_cache: Dict[str, BaseTool] = {}
        self._last_cache_refresh = time.time()
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("HardenedToolDispatcher initialized successfully")
    
    def execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        invocation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with comprehensive error handling and validation
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Execution context
            invocation_id: Unique invocation identifier for tracking
            
        Returns:
            Structured execution result with success/error information
        """
        # Create execution metrics
        metrics = ToolExecutionMetrics(
            tool_name=tool_name,
            start_time=time.time()
        )
        
        execution_id = invocation_id or f"exec_{int(time.time() * 1000)}"
        
        try:
            logger.info(f"[{execution_id}] Starting tool execution: {tool_name}")
            
            # 1. Tool Discovery and Validation
            tool_result = self._discover_and_validate_tool(tool_name, execution_id)
            if not tool_result["success"]:
                metrics.mark_completed(ExecutionResult.TOOL_NOT_FOUND, tool_result["error"])
                self._record_metrics(metrics)
                return self._create_error_response(
                    ExecutionResult.TOOL_NOT_FOUND,
                    tool_result["error"],
                    tool_name,
                    execution_id
                )
            
            tool = tool_result["tool"]
            
            # 2. Parameter Validation
            if self.config.enable_parameter_validation:
                validation_result = self._validate_parameters(tool, parameters, execution_id)
                if not validation_result["success"]:
                    metrics.mark_completed(ExecutionResult.PARAMETER_ERROR, validation_result["error"])
                    self._record_metrics(metrics)
                    return self._create_error_response(
                        ExecutionResult.PARAMETER_ERROR,
                        validation_result["error"],
                        tool_name,
                        execution_id,
                        validation_errors=validation_result.get("validation_errors", [])
                    )
            
            # 3. Execute Tool with Error Handling
            execution_result = self._execute_with_safeguards(
                tool, parameters, context, execution_id, metrics
            )
            
            # 4. Record successful execution
            if execution_result["success"]:
                metrics.mark_completed(ExecutionResult.SUCCESS)
                self._update_tool_stats(tool_name, success=True)
            else:
                error_type = self._classify_error(execution_result.get("error", ""))
                metrics.mark_completed(error_type, execution_result.get("error"))
                self._update_tool_stats(tool_name, success=False)
            
            self._record_metrics(metrics)
            
            # 5. Add execution metadata
            execution_result.update({
                "execution_id": execution_id,
                "tool_name": tool_name,
                "execution_time_ms": int((metrics.execution_time or 0) * 1000),
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"[{execution_id}] Tool execution completed: {tool_name} -> {execution_result['success']}")
            return execution_result
            
        except Exception as e:
            # Catch-all error handler
            error_msg = f"Unexpected error during tool execution: {str(e)}"
            logger.error(f"[{execution_id}] {error_msg}", exc_info=True)
            
            metrics.mark_completed(ExecutionResult.EXECUTION_ERROR, error_msg)
            self._record_metrics(metrics)
            self._update_tool_stats(tool_name, success=False)
            
            return self._create_error_response(
                ExecutionResult.EXECUTION_ERROR,
                error_msg,
                tool_name,
                execution_id,
                stack_trace=traceback.format_exc() if self.config.enable_detailed_logging else None
            )
    
    def _discover_and_validate_tool(self, tool_name: str, execution_id: str) -> Dict[str, Any]:
        """
        Discover and validate tool availability
        
        Args:
            tool_name: Name of the tool
            execution_id: Execution identifier
            
        Returns:
            Discovery result with tool instance or error
        """
        try:
            # Check cache first
            if self._is_cache_valid() and tool_name in self._tool_mapping_cache:
                tool = self._tool_mapping_cache[tool_name]
                logger.debug(f"[{execution_id}] Tool '{tool_name}' found in cache")
                return {"success": True, "tool": tool}
            
            # Get tool from registry
            tool = self.registry.get_tool(tool_name)
            
            if tool is None:
                # Try to refresh registry and check again
                available_tools = self.registry.list_tools()
                tool_names = [t["name"] for t in available_tools]
                
                error_msg = f"Tool '{tool_name}' not found in registry"
                suggestion = self._suggest_similar_tool(tool_name, tool_names)
                if suggestion:
                    error_msg += f". Did you mean '{suggestion}'?"
                
                logger.error(f"[{execution_id}] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "available_tools": tool_names[:10],  # First 10 for brevity
                    "suggestion": suggestion
                }
            
            # Validate tool is ready
            if not tool.is_ready:
                error_msg = f"Tool '{tool_name}' is not ready for execution (status: {tool.status})"
                logger.error(f"[{execution_id}] {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Cache the tool
            self._tool_mapping_cache[tool_name] = tool
            
            logger.debug(f"[{execution_id}] Tool '{tool_name}' discovered and validated")
            return {"success": True, "tool": tool}
            
        except Exception as e:
            error_msg = f"Error during tool discovery: {str(e)}"
            logger.error(f"[{execution_id}] {error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}
    
    def _validate_parameters(
        self, 
        tool: BaseTool, 
        parameters: Dict[str, Any], 
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Validate tool parameters against schema
        
        Args:
            tool: Tool instance
            parameters: Parameters to validate
            execution_id: Execution identifier
            
        Returns:
            Validation result
        """
        try:
            # Use tool's built-in validation if available
            if hasattr(tool, 'validate_parameters'):
                is_valid, errors = tool.validate_parameters(parameters)
                if not is_valid:
                    error_msg = f"Parameter validation failed: {', '.join(errors)}"
                    logger.warning(f"[{execution_id}] {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg,
                        "validation_errors": errors
                    }
            
            # Additional custom validation
            validation_errors = []
            
            if tool.metadata and tool.metadata.parameters:
                # Check required parameters
                required_params = [p.name for p in tool.metadata.parameters if p.required]
                missing_params = [p for p in required_params if p not in parameters]
                
                if missing_params:
                    validation_errors.append(f"Missing required parameters: {missing_params}")
                
                # Check parameter types
                for param in tool.metadata.parameters:
                    if param.name in parameters:
                        value = parameters[param.name]
                        type_error = self._validate_parameter_type(param, value)
                        if type_error:
                            validation_errors.append(type_error)
            
            if validation_errors:
                error_msg = f"Parameter validation errors: {', '.join(validation_errors)}"
                logger.warning(f"[{execution_id}] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "validation_errors": validation_errors
                }
            
            logger.debug(f"[{execution_id}] Parameter validation successful")
            return {"success": True}
            
        except Exception as e:
            error_msg = f"Error during parameter validation: {str(e)}"
            logger.error(f"[{execution_id}] {error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}
    
    def _validate_parameter_type(self, param, value) -> Optional[str]:
        """
        Validate parameter type
        
        Args:
            param: Parameter metadata
            value: Parameter value
            
        Returns:
            Error message if validation fails, None if valid
        """
        if param.type == ParameterType.STRING and not isinstance(value, str):
            return f"Parameter '{param.name}' must be a string, got {type(value).__name__}"
        elif param.type == ParameterType.INTEGER and not isinstance(value, int):
            return f"Parameter '{param.name}' must be an integer, got {type(value).__name__}"
        elif param.type == ParameterType.FLOAT and not isinstance(value, (int, float)):
            return f"Parameter '{param.name}' must be a number, got {type(value).__name__}"
        elif param.type == ParameterType.BOOLEAN and not isinstance(value, bool):
            return f"Parameter '{param.name}' must be a boolean, got {type(value).__name__}"
        elif param.type == ParameterType.ARRAY and not isinstance(value, list):
            return f"Parameter '{param.name}' must be an array, got {type(value).__name__}"
        elif param.type == ParameterType.OBJECT and not isinstance(value, dict):
            return f"Parameter '{param.name}' must be an object, got {type(value).__name__}"
        
        return None
    
    def _execute_with_safeguards(
        self,
        tool: BaseTool,
        parameters: Dict[str, Any],
        context: Optional[ExecutionContext],
        execution_id: str,
        metrics: ToolExecutionMetrics
    ) -> Dict[str, Any]:
        """
        Execute tool with comprehensive safeguards
        
        Args:
            tool: Tool to execute
            parameters: Tool parameters
            context: Execution context
            execution_id: Execution identifier
            metrics: Execution metrics
            
        Returns:
            Execution result
        """
        retry_count = 0
        last_error = None
        
        while retry_count <= self.config.max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"[{execution_id}] Retrying tool execution (attempt {retry_count + 1})")
                    metrics.retry_count = retry_count
                
                # Execute with timeout
                result = self._execute_with_timeout(tool, parameters, execution_id)
                
                if result["success"]:
                    logger.debug(f"[{execution_id}] Tool execution successful on attempt {retry_count + 1}")
                    return result
                else:
                    last_error = result.get("error", "Unknown error")
                    logger.warning(f"[{execution_id}] Tool execution failed: {last_error}")
                    
                    # Check if error is retryable
                    if not self._is_retryable_error(last_error):
                        break
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"[{execution_id}] Tool execution exception: {last_error}", exc_info=True)
                
                if not self._is_retryable_error(last_error):
                    break
            
            retry_count += 1
            if retry_count <= self.config.max_retries:
                time.sleep(min(retry_count * 0.5, 2.0))  # Exponential backoff, max 2s
        
        # All retries exhausted
        error_msg = f"Tool execution failed after {retry_count} attempts. Last error: {last_error}"
        logger.error(f"[{execution_id}] {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "retry_count": retry_count,
            "last_error": last_error
        }
    
    def _execute_with_timeout(
        self,
        tool: BaseTool,
        parameters: Dict[str, Any],
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Execute tool with timeout protection
        
        Args:
            tool: Tool to execute
            parameters: Tool parameters
            execution_id: Execution identifier
            
        Returns:
            Execution result
        """
        import threading
        import queue
        
        def timeout_handler():
            raise TimeoutError(f"Tool execution timed out after "
                             f"{self.config.max_execution_time}s")
        
        try:
            # Use threading for timeout (cross-platform)
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def execute_tool():
                try:
                    result = tool.execute(**parameters)
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)
            
            thread = threading.Thread(target=execute_tool)
            thread.daemon = True
            thread.start()
            thread.join(timeout=self.config.max_execution_time)
            
            if thread.is_alive():
                # Tool is still running, consider it timed out
                timeout_handler()
            
            # Check for exceptions
            if not exception_queue.empty():
                raise exception_queue.get()
            
            # Get result
            if not result_queue.empty():
                result = result_queue.get()
            else:
                raise RuntimeError("Tool execution completed but no result")
            
            # Format result
            if isinstance(result, ToolResult):
                return {
                    "success": result.success,
                    "output": result.output,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "execution_time": result.execution_time,
                    "status": result.status.value if result.status else None
                }
            elif isinstance(result, dict):
                return {
                    "success": result.get("success", True),
                    "output": result,
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", [])
                }
            else:
                return {
                    "success": True,
                    "output": {"result": result},
                    "errors": [],
                    "warnings": []
                }
                
        except TimeoutError as e:
            logger.error(f"[{execution_id}] Tool execution timeout: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "timeout"
            }
        except Exception as e:
            logger.error(f"[{execution_id}] Tool execution error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution"
            }
        finally:
            # No cleanup needed for threading approach
            pass
    
    def _is_retryable_error(self, error_msg: str) -> bool:
        """
        Determine if an error is retryable
        
        Args:
            error_msg: Error message
            
        Returns:
            True if error is retryable
        """
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "busy",
            "unavailable"
        ]
        
        error_lower = error_msg.lower()
        return any(pattern in error_lower for pattern in retryable_patterns)
    
    def _classify_error(self, error_msg: str) -> ExecutionResult:
        """
        Classify error type
        
        Args:
            error_msg: Error message
            
        Returns:
            Error classification
        """
        error_lower = error_msg.lower()
        
        if "timeout" in error_lower:
            return ExecutionResult.TIMEOUT_ERROR
        elif "permission" in error_lower or "denied" in error_lower:
            return ExecutionResult.PERMISSION_ERROR
        elif "validation" in error_lower or "parameter" in error_lower:
            return ExecutionResult.VALIDATION_ERROR
        else:
            return ExecutionResult.EXECUTION_ERROR
    
    def _suggest_similar_tool(self, tool_name: str, available_tools: List[str]) -> Optional[str]:
        """
        Suggest similar tool name using simple string similarity
        
        Args:
            tool_name: Tool name that wasn't found
            available_tools: List of available tool names
            
        Returns:
            Suggested tool name or None
        """
        def similarity(a: str, b: str) -> float:
            """Simple similarity calculation"""
            if not a or not b:
                return 0.0
            
            # Exact match
            if a == b:
                return 1.0
            
            # Case insensitive match
            if a.lower() == b.lower():
                return 0.95
            
            # Substring match
            if a.lower() in b.lower() or b.lower() in a.lower():
                return 0.8
            
            # Character overlap
            set_a = set(a.lower())
            set_b = set(b.lower())
            overlap = len(set_a & set_b)
            total = len(set_a | set_b)
            
            return overlap / total if total > 0 else 0.0
        
        similarities = [(tool, similarity(tool_name, tool)) for tool in available_tools]
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        if similarities and similarities[0][1] > 0.6:  # 60% similarity threshold
            return similarities[0][0]
        
        return None
    
    def _create_error_response(
        self,
        error_type: ExecutionResult,
        error_msg: str,
        tool_name: str,
        execution_id: str,
        **additional_fields
    ) -> Dict[str, Any]:
        """
        Create standardized error response
        
        Args:
            error_type: Type of error
            error_msg: Error message
            tool_name: Tool name
            execution_id: Execution identifier
            **additional_fields: Additional error fields
            
        Returns:
            Standardized error response
        """
        response = {
            "success": False,
            "error": error_msg,
            "error_type": error_type.value,
            "tool_name": tool_name,
            "execution_id": execution_id,
            "timestamp": datetime.now().isoformat(),
            **additional_fields
        }
        
        # Add fallback response if enabled
        if self.config.fallback_response_enabled:
            response["fallback_available"] = True
            response["fallback_message"] = self._generate_fallback_message(tool_name, error_type)
        
        return response
    
    def _generate_fallback_message(self, tool_name: str, error_type: ExecutionResult) -> str:
        """Generate helpful fallback message"""
        if error_type == ExecutionResult.TOOL_NOT_FOUND:
            return f"The '{tool_name}' tool is not available. You can list available tools or try a similar operation."
        elif error_type == ExecutionResult.PARAMETER_ERROR:
            return f"The '{tool_name}' tool had parameter issues. Check the tool documentation for correct usage."
        elif error_type == ExecutionResult.TIMEOUT_ERROR:
            return f"The '{tool_name}' tool timed out. Try simplifying the request or breaking it into smaller parts."
        else:
            return f"The '{tool_name}' tool encountered an error. Please try again or use an alternative approach."
    
    def _record_metrics(self, metrics: ToolExecutionMetrics):
        """Record execution metrics"""
        self.execution_metrics.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.execution_metrics) > 1000:
            self.execution_metrics = self.execution_metrics[-1000:]
    
    def _update_tool_stats(self, tool_name: str, success: bool):
        """Update tool usage statistics"""
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "last_used": None,
                "success_rate": 0.0
            }
        
        stats = self.tool_usage_stats[tool_name]
        stats["total_calls"] += 1
        stats["last_used"] = datetime.now().isoformat()
        
        if success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
        
        stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
    
    def _is_cache_valid(self) -> bool:
        """Check if tool mapping cache is still valid"""
        return (time.time() - self._last_cache_refresh) < self._cache_ttl
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        return {
            "total_executions": len(self.execution_metrics),
            "tool_usage_stats": self.tool_usage_stats,
            "recent_executions": self.execution_metrics[-10:] if self.execution_metrics else [],
            "cache_stats": {
                "cached_tools": len(self._tool_mapping_cache),
                "cache_age_seconds": time.time() - self._last_cache_refresh,
                "cache_valid": self._is_cache_valid()
            }
        }
    
    def refresh_tool_cache(self):
        """Manually refresh tool mapping cache"""
        self._tool_mapping_cache.clear()
        self._last_cache_refresh = time.time()
        logger.info("Tool mapping cache refreshed")
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools with metadata"""
        try:
            tools = self.registry.list_tools(enabled_only=True)
            
            # Enhance with usage statistics
            for tool in tools:
                tool_name = tool["name"]
                if tool_name in self.tool_usage_stats:
                    tool.update(self.tool_usage_stats[tool_name])
                else:
                    tool.update({
                        "total_calls": 0,
                        "successful_calls": 0,
                        "failed_calls": 0,
                        "success_rate": 0.0,
                        "last_used": None
                    })
            
            return tools
        except Exception as e:
            logger.error(f"Error listing available tools: {e}")
            return []