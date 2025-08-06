"""
Function Tool Wrapper

This module provides a wrapper to convert function-based tools from
basic_tools.py into proper BaseTool instances that can be registered with the
ToolRegistry. This bridges the gap between the legacy function-based tools
and the new class-based tool system.
"""

import logging
import inspect
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ParameterType, ToolCategory, ToolStatus
)

logger = logging.getLogger(__name__)


@dataclass
class FunctionToolConfig:
    """Configuration for function tool wrapper"""
    name: str
    function: Callable
    description: str
    category: ToolCategory = ToolCategory.UTILITY
    version: str = "1.0.0"
    parameters: Optional[List[ToolParameter]] = None
    examples: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class FunctionToolWrapper(BaseTool):
    """
    Wrapper that converts function-based tools to BaseTool instances
    
    This wrapper allows legacy function-based tools to be used within
    the new tool registry system while maintaining backward compatibility.
    """
    
    def __init__(self, config: FunctionToolConfig):
        """
        Initialize the function wrapper
        
        Args:
            config: Configuration for the function tool
        """
        self._function = config.function
        self._function_name = config.name
        self._config_obj = config
        
        # Initialize base tool
        super().__init__()
        
        logger.info(f"Created function wrapper for '{config.name}'")
    
    def _create_metadata(self) -> ToolMetadata:
        """
        Create tool metadata from configuration
        
        Returns:
            ToolMetadata instance
        """
        config = self._config_obj
        
        # Extract parameters from function signature if not provided
        if config.parameters is None:
            parameters = self._extract_parameters_from_function()
        else:
            parameters = config.parameters
        
        # Create metadata
        return ToolMetadata(
            name=config.name,
            description=config.description,
            author="DinoAir Function Wrapper",
            version=config.version,
            category=config.category,
            parameters=parameters,
            examples=config.examples or [],
            tags=config.tags or [],
            capabilities={"function_based": True, "synchronous": True}
        )
    
    def _extract_parameters_from_function(self) -> List[ToolParameter]:
        """
        Extract parameters from function signature and docstring
        
        Returns:
            List of tool parameters
        """
        parameters = []
        
        try:
            # Get function signature
            sig = inspect.signature(self._function)
            
            # Parse docstring for parameter descriptions
            docstring = inspect.getdoc(self._function) or ""
            param_descriptions = self._parse_docstring_parameters(docstring)
            
            for param_name, param in sig.parameters.items():
                # Skip *args and **kwargs
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                
                # Determine parameter type from annotation
                param_type = self._get_parameter_type(param.annotation)
                
                # Get description from docstring
                description = param_descriptions.get(
                    param_name, 
                    f"Parameter for {self._function_name}"
                )
                
                # Determine if required (no default value)
                required = param.default == param.empty
                default_value = None if required else param.default
                
                tool_param = ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=description,
                    required=required,
                    default=default_value
                )
                
                parameters.append(tool_param)
                
        except Exception as e:
            logger.warning(
                f"Failed to extract parameters from function "
                f"'{self._function_name}': {e}"
            )
            # Return empty list if extraction fails
            
        return parameters
    
    def _parse_docstring_parameters(self, docstring: str) -> Dict[str, str]:
        """
        Parse parameter descriptions from docstring
        
        Args:
            docstring: Function docstring
            
        Returns:
            Dictionary mapping parameter names to descriptions
        """
        param_descriptions = {}
        
        try:
            lines = docstring.split('\n')
            in_args_section = False
            
            for line in lines:
                line = line.strip()
                
                # Look for Args: section
                if line.lower().startswith('args:'):
                    in_args_section = True
                    continue
                elif line.lower().startswith(
                    ('returns:', 'return:', 'example:')
                ):
                    in_args_section = False
                    continue
                
                # Parse parameter descriptions
                if in_args_section and ':' in line:
                    # Look for pattern: param_name (type): description
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        param_part = parts[0].strip()
                        description = parts[1].strip()
                        
                        # Extract parameter name (remove type annotation)
                        if '(' in param_part and ')' in param_part:
                            param_name = param_part.split('(')[0].strip()
                        else:
                            param_name = param_part
                        
                        # Clean up parameter name
                        param_name = param_name.replace('-', '').strip()
                        
                        if param_name:
                            param_descriptions[param_name] = description
                            
        except Exception as e:
            logger.warning(f"Failed to parse docstring parameters: {e}")
            
        return param_descriptions
    
    def _get_parameter_type(self, annotation: Any) -> ParameterType:
        """
        Convert Python type annotation to ParameterType
        
        Args:
            annotation: Type annotation
            
        Returns:
            Corresponding ParameterType
        """
        if annotation == inspect.Parameter.empty:
            return ParameterType.ANY
        
        # Handle string representations
        if isinstance(annotation, str):
            annotation_lower = annotation.lower()
            if 'str' in annotation_lower:
                return ParameterType.STRING
            elif 'int' in annotation_lower:
                return ParameterType.INTEGER
            elif 'float' in annotation_lower:
                return ParameterType.FLOAT
            elif 'bool' in annotation_lower:
                return ParameterType.BOOLEAN
            elif 'dict' in annotation_lower:
                return ParameterType.OBJECT
            elif 'list' in annotation_lower:
                return ParameterType.ARRAY
            else:
                return ParameterType.ANY
        
        # Handle actual type objects
        type_mapping = {
            str: ParameterType.STRING,
            int: ParameterType.INTEGER,
            float: ParameterType.FLOAT,
            bool: ParameterType.BOOLEAN,
            dict: ParameterType.OBJECT,
            list: ParameterType.ARRAY,
            Dict: ParameterType.OBJECT,
            List: ParameterType.ARRAY,
        }
        
        return type_mapping.get(annotation, ParameterType.ANY)
    
    def initialize(self):
        """
        Initialize the function wrapper
        """
        try:
            # Verify function is callable
            if not callable(self._function):
                logger.error(
                    f"Function {self._function_name} is not callable"
                )
                self._status = ToolStatus.FAILED
                return
            
            self._status = ToolStatus.READY
            logger.debug(
                f"Function wrapper '{self.name}' initialized successfully"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to initialize function wrapper '{self.name}': {e}"
            )
            self._status = ToolStatus.FAILED
    
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the wrapped function
        
        Args:
            **kwargs: Function parameters
            
        Returns:
            Tool execution result
        """
        start_time = datetime.now()
        
        try:
            # Validate we're ready
            if self._status != ToolStatus.READY:
                return ToolResult(
                    success=False,
                    status=self._status,
                    errors=[f"Tool not ready: {self._status.value}"],
                    timestamp=start_time
                )
            
            # Set status to running
            self._status = ToolStatus.RUNNING
            
            # Execute the function
            result = self._function(**kwargs)
            
            # Set status back to ready
            self._status = ToolStatus.READY
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Handle different result formats
            if isinstance(result, dict):
                # Function returns structured result
                success = result.get('success', True)
                output = result
                errors = result.get('error', []) if not success else []
                if isinstance(errors, str):
                    errors = [errors]
            else:
                # Function returns simple value
                success = True
                output = {"result": result}
                errors = []
            
            return ToolResult(
                success=success,
                output=output,
                errors=errors,
                execution_time=execution_time,
                timestamp=start_time,
                status=ToolStatus.READY
            )
            
        except Exception as e:
            self._status = ToolStatus.FAILED
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"Function execution failed for '{self.name}': {e}")
            
            return ToolResult(
                success=False,
                errors=[f"Execution failed: {str(e)}"],
                execution_time=execution_time,
                timestamp=start_time,
                status=ToolStatus.FAILED
            )
    
    def shutdown(self):
        """
        Shutdown the function wrapper
        """
        self._status = ToolStatus.IDLE
        logger.debug(f"Function wrapper '{self.name}' shutdown")


def create_function_tool_wrapper(
    name: str,
    function: Callable,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.UTILITY,
    version: str = "1.0.0",
    parameters: Optional[List[ToolParameter]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None
) -> FunctionToolWrapper:
    """
    Create a function tool wrapper
    
    Args:
        name: Tool name
        function: Function to wrap
        description: Tool description (from docstring if not provided)
        category: Tool category
        version: Tool version
        parameters: Parameter definitions (auto-extracted if not provided)
        examples: Usage examples
        tags: Tool tags
        
    Returns:
        Function tool wrapper instance
    """
    # Extract description from docstring if not provided
    if description is None:
        docstring = inspect.getdoc(function)
        if docstring:
            # Get first line or paragraph as description
            lines = docstring.strip().split('\n')
            description = lines[0].strip()
            if not description and len(lines) > 1:
                description = lines[1].strip()
        
        if not description:
            description = f"Function tool: {name}"
    
    # Create configuration
    config = FunctionToolConfig(
        name=name,
        function=function,
        description=description,
        category=category,
        version=version,
        parameters=parameters,
        examples=examples,
        tags=tags
    )
    
    # Create and initialize wrapper
    wrapper = FunctionToolWrapper(config)
    wrapper.initialize()
    
    return wrapper


def wrap_available_tools(
    available_tools: Dict[str, Callable]
) -> Dict[str, FunctionToolWrapper]:
    """
    Convert a dictionary of available tools to wrapped BaseTool instances
    
    Args:
        available_tools: Dictionary mapping tool names to functions
        
    Returns:
        Dictionary mapping tool names to wrapped BaseTool instances
    """
    wrapped_tools = {}
    
    for tool_name, function in available_tools.items():
        try:
            # Determine category based on tool name
            category = _categorize_tool(tool_name, function)
            
            # Create wrapper
            wrapper = create_function_tool_wrapper(
                name=tool_name,
                function=function,
                category=category,
                tags=_generate_tags(tool_name, function)
            )
            
            wrapped_tools[tool_name] = wrapper
            logger.info(f"Successfully wrapped tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Failed to wrap tool '{tool_name}': {e}")
            
    return wrapped_tools


def _categorize_tool(tool_name: str, function: Callable) -> ToolCategory:
    """
    Determine appropriate category for a tool
    
    Args:
        tool_name: Name of the tool
        function: Function implementation
        
    Returns:
        Appropriate tool category
    """
    name_lower = tool_name.lower()
    
    if any(keyword in name_lower for keyword in [
        'file', 'read', 'write', 'directory'
    ]):
        return ToolCategory.SYSTEM
    elif any(keyword in name_lower for keyword in ['note', 'project']):
        return ToolCategory.UTILITY
    elif any(keyword in name_lower for keyword in ['search', 'find']):
        return ToolCategory.ANALYSIS
    elif any(keyword in name_lower for keyword in [
        'time', 'date', 'add', 'calculate'
    ]):
        return ToolCategory.UTILITY
    elif any(keyword in name_lower for keyword in [
        'execute', 'command', 'system'
    ]):
        return ToolCategory.SYSTEM
    elif any(keyword in name_lower for keyword in ['json', 'data']):
        return ToolCategory.TRANSFORMATION
    else:
        return ToolCategory.UTILITY


def _generate_tags(tool_name: str, function: Callable) -> List[str]:
    """
    Generate appropriate tags for a tool
    
    Args:
        tool_name: Name of the tool
        function: Function implementation
        
    Returns:
        List of relevant tags
    """
    tags = ["function_based", "legacy"]
    
    name_lower = tool_name.lower()
    
    # Add functional tags
    if any(keyword in name_lower for keyword in ['read', 'get', 'list']):
        tags.append("read")
    if any(keyword in name_lower for keyword in [
        'write', 'create', 'execute'
    ]):
        tags.append("write")
    if any(keyword in name_lower for keyword in ['file', 'directory']):
        tags.append("filesystem")
    if any(keyword in name_lower for keyword in ['time', 'date']):
        tags.append("temporal")
    if any(keyword in name_lower for keyword in ['add', 'calculate']):
        tags.append("math")
    if any(keyword in name_lower for keyword in ['system', 'command']):
        tags.append("system")
    if any(keyword in name_lower for keyword in ['note', 'project']):
        tags.append("productivity")
    if any(keyword in name_lower for keyword in ['search']):
        tags.append("search")
    if any(keyword in name_lower for keyword in ['json', 'data']):
        tags.append("data")
    
    return tags