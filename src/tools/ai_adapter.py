"""
Tool AI Adapter

This module provides adapters for integrating tools with AI models,
formatting tool information for model context and handling tool execution.
Now includes policy enforcement and context-aware tool selection.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import json
from math import isfinite
from abc import ABC, abstractmethod

from .base import (
    BaseTool, ToolParameter, ToolResult,
    ParameterType, ToolCategory
)
from .registry import ToolRegistry
from .control.tool_controller import ToolController, PolicyBasedToolController
from .control.tool_context import (
    ExecutionContext, ContextualToolSelector,
    UserContext, TaskContext, EnvironmentContext,
    TaskType
)
from .control.restrictions import RestrictionManager
from .prompts.prompt_templates import (
    ModelCapability,
    ToolSelectionTemplate,
    ErrorHandlingTemplate, UsageExampleTemplate,
    ToolContextTemplate
)


logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema representation of a tool for AI models"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]
    returns: Dict[str, Any]
    examples: List[Dict[str, Any]] = field(default_factory=list)
    category: str = ""
    version: str = ""
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            },
            "returns": self.returns,
            "examples": self.examples
        }
    
    def to_function_calling_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required
            }
        }


class ToolFormatter(ABC):
    """Abstract base class for tool formatters"""
    
    @abstractmethod
    def format_tool(self, tool: BaseTool) -> Dict[str, Any]:
        """Format tool for AI model consumption"""
        pass
    
    @abstractmethod
    def format_result(self, result: ToolResult) -> Dict[str, Any]:
        """Format tool result for AI model consumption"""
        pass
    
    @abstractmethod
    def parse_invocation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse tool invocation from AI model"""
        pass


class StandardToolFormatter(ToolFormatter):
    """Standard formatter for tools"""
    
    def format_tool(self, tool: BaseTool) -> Dict[str, Any]:
        """Format tool for AI model consumption"""
        if not tool.metadata:
            raise ValueError(f"Tool {tool.name} has no metadata")
        
        # Convert parameters to schema
        properties = {}
        required = []
        
        for param in tool.metadata.parameters:
            prop = self._parameter_to_schema(param)
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        
        return {
            "name": tool.metadata.name,
            "description": tool.metadata.description,
            "parameters": properties,
            "required": required,
            "category": tool.metadata.category.value,
            "version": tool.metadata.version,
            "capabilities": tool.metadata.capabilities,
            "examples": tool.metadata.examples
        }
    
    def _parameter_to_schema(self, param: ToolParameter) -> Dict[str, Any]:
        """Convert parameter to JSON schema"""
        schema: Dict[str, Any] = {
            "description": param.description
        }
        
        # Map parameter types to JSON schema types
        type_mapping = {
            ParameterType.STRING: "string",
            ParameterType.INTEGER: "integer",
            ParameterType.FLOAT: "number",
            ParameterType.BOOLEAN: "boolean",
            ParameterType.ARRAY: "array",
            ParameterType.OBJECT: "object",
            ParameterType.FILE_PATH: "string",
            ParameterType.URL: "string",
            ParameterType.ANY: [
                "string", "number", "boolean", "object", "array"
            ]
        }
        
        schema["type"] = type_mapping.get(param.type, "string")
        
        # Add constraints
        if param.enum_values:
            schema["enum"] = param.enum_values
        if param.min_value is not None:
            schema["minimum"] = param.min_value
        if param.max_value is not None:
            schema["maximum"] = param.max_value
        if param.pattern:
            schema["pattern"] = param.pattern
        if param.example is not None:
            schema["example"] = param.example
        if param.default is not None:
            schema["default"] = param.default
            
        # Special handling for file paths and URLs
        if param.type == ParameterType.FILE_PATH:
            schema["format"] = "file-path"
        elif param.type == ParameterType.URL:
            schema["format"] = "uri"
            
        return schema
    
    def format_result(self, result: ToolResult) -> Dict[str, Any]:
        """Format tool result for AI model consumption"""
        formatted = {
            "success": result.success,
            "status": result.status.value,
            "timestamp": result.timestamp.isoformat()
        }
        
        if result.output is not None:
            # Handle different output types
            if isinstance(result.output, (dict, list)):
                formatted["output"] = result.output
            else:
                formatted["output"] = str(result.output)
        
        if result.errors:
            formatted["errors"] = result.errors
        
        if result.warnings:
            formatted["warnings"] = result.warnings
            
        if result.metadata:
            formatted["metadata"] = result.metadata
            
        if result.execution_time:
            formatted["execution_time_ms"] = int(result.execution_time * 1000)
            
        return formatted
    
    def parse_invocation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse tool invocation from AI model"""
        # Extract tool name and parameters
        if "name" not in data:
            raise ValueError("Tool invocation missing 'name' field")
            
        return {
            "tool_name": data["name"],
            "parameters": data.get("parameters", {}),
            "metadata": data.get("metadata", {})
        }


class ToolAIAdapter:
    """
    Adapter for integrating tools with AI models
    
    This class provides a unified interface for:
    - Formatting tool descriptions for AI models
    - Executing tools based on AI model requests
    - Converting results back to AI model format
    - Managing tool context and history
    - Enforcing policies and restrictions
    - Context-aware tool selection
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        formatter: Optional[ToolFormatter] = None,
        controller: Optional[ToolController] = None,
        enable_policies: bool = False,  # Changed default to False
        enable_restrictions: bool = False  # Changed default to False
    ):
        """
        Initialize the adapter
        
        Args:
            registry: Tool registry instance (uses global if not provided)
            formatter: Tool formatter (uses standard if not provided)
            controller: Tool controller for policy enforcement
            enable_policies: Whether to enable policy enforcement
            enable_restrictions: Whether to enable usage restrictions
        """
        self.registry = registry or ToolRegistry()
        self.formatter = formatter or StandardToolFormatter()
        self._execution_history: List[Dict[str, Any]] = []
        self._context: Dict[str, Any] = {}
        self._current_execution_context: Optional[ExecutionContext] = None
        self.enable_policies = enable_policies
        self.enable_restrictions = enable_restrictions
        
        # Initialize control systems
        if enable_policies:
            self.controller = controller or PolicyBasedToolController(
                registry=self.registry,
                safe_mode=True
            )
        else:
            self.controller = controller or ToolController(
                registry=self.registry
            )
            
        # Initialize contextual selector
        self.contextual_selector = ContextualToolSelector(
            controller=self.controller,
            registry=self.registry
        )
        
        # Initialize restriction manager
        self.restriction_manager = (
            RestrictionManager() if enable_restrictions else None
        )
        
        # Configure default restrictions if enabled
        if self.restriction_manager and enable_restrictions:
            self._configure_default_restrictions()
    
    def _configure_default_restrictions(self):
        """Configure default usage restrictions"""
        if self.restriction_manager:
            # Add default rate limiter
            self.restriction_manager.add_rate_limiter(
                "default",
                rate=10.0,  # 10 requests per second
                burst=20,
                per_user=True
            )
            
            # Add high-cost rate limiter
            self.restriction_manager.add_rate_limiter(
                "high_cost",
                rate=1.0,  # 1 request per second
                burst=5,
                per_user=True
            )
    
    def set_execution_context(
        self,
        user: Optional[UserContext] = None,
        task: Optional[TaskContext] = None,
        environment: Optional[EnvironmentContext] = None
    ):
        """
        Set the current execution context
        
        Args:
            user: User context
            task: Task context
            environment: Environment context
        """
        self._current_execution_context = ExecutionContext(
            user=user,
            task=task,
            environment=environment
        )
        
    def get_available_tools(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        format_type: str = "standard",
        apply_policies: Optional[bool] = None,
        context: Optional[ExecutionContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available tools formatted for AI model
        
        Args:
            category: Filter by category
            tags: Filter by tags
            format_type: Format type (standard, function_calling, etc.)
            apply_policies: Whether to apply policy filtering
            context: Execution context for policy evaluation
            
        Returns:
            List of formatted tool descriptions
        """
        # Use current context if not provided
        context = context or self._current_execution_context
        
        # Use instance policy setting if not explicitly specified
        if apply_policies is None:
            apply_policies = self.enable_policies
        
        if apply_policies and self.controller:
            # Get tools filtered by policies
            allowed_tools = self.controller.filter_tools(
                context=context.to_dict() if context else None,
                category=category,
                tags=tags
            )
            tool_list = list(allowed_tools.values())
        else:
            # Get tools from registry without policy filtering
            tool_infos = self.registry.list_tools(
                category=category,
                tags=tags,
                enabled_only=True
            )
            tool_list = []
            for info in tool_infos:
                tool = self.registry.get_tool(info["name"])
                if tool and tool.is_ready:
                    tool_list.append(tool)
        
        formatted_tools = []
        for tool in tool_list:
            try:
                formatted = self.formatter.format_tool(tool)
                
                # Apply format type transformations
                if format_type == "function_calling":
                    schema = ToolSchema(
                        name=formatted["name"],
                        description=formatted["description"],
                        parameters=formatted["parameters"],
                        required=formatted["required"],
                        returns={},
                        examples=formatted.get("examples", [])
                    )
                    formatted = schema.to_function_calling_format()
                    
                formatted_tools.append(formatted)
            except Exception as e:
                logger.error(f"Failed to format tool {tool.name}: {e}")
                    
        return formatted_tools
    
    def execute_tool(
        self,
        invocation: Union[Dict[str, Any], str],
        track_history: bool = True,
        validate_params: bool = True,
        check_policies: Optional[bool] = None,
        check_restrictions: Optional[bool] = None,
        context: Optional[ExecutionContext] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool based on AI model invocation
        
        Args:
            invocation: Tool invocation data (dict or JSON string)
            track_history: Whether to track in execution history
            validate_params: Whether to validate parameters
            check_policies: Whether to check policies
            check_restrictions: Whether to check restrictions
            context: Execution context
            
        Returns:
            Formatted result dictionary
        """
        # Use current context if not provided
        context = context or self._current_execution_context
        
        # Use instance settings if not explicitly specified
        if check_policies is None:
            check_policies = self.enable_policies
        if check_restrictions is None:
            check_restrictions = self.enable_restrictions
        
        # Parse invocation if string
        if isinstance(invocation, str):
            try:
                invocation_dict = json.loads(invocation)
            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Invalid JSON: {e}",
                    "timestamp": datetime.now().isoformat()
                }
        else:
            invocation_dict = invocation
        
        # Parse invocation
        try:
            parsed = self.formatter.parse_invocation(invocation_dict)
            tool_name = parsed["tool_name"]
            parameters = parsed["parameters"]
            metadata = parsed.get("metadata", {})
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse invocation: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get tool
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found",
                "timestamp": datetime.now().isoformat()
            }
        
        # Check policies if enabled
        if check_policies and self.controller:
            can_use, reason = self.controller.can_use_tool(
                tool_name,
                context.to_dict() if context else None
            )
            if not can_use:
                return {
                    "success": False,
                    "error": f"Policy violation: {reason}",
                    "timestamp": datetime.now().isoformat(),
                    "policy_denied": True
                }
        
        # Check restrictions if enabled
        if check_restrictions and self.restriction_manager:
            is_allowed, restriction = self.restriction_manager.is_allowed(
                tool, context
            )
            if not is_allowed:
                if restriction:
                    # Ensure retry_after is a finite value for JSON serialization
                    retry_after = restriction.retry_after
                    if retry_after is not None:
                        if not isinstance(retry_after, (int, float)) or not isfinite(retry_after):
                            retry_after = 60.0  # Default to 60 seconds
                        else:
                            retry_after = min(retry_after, 3600.0)  # Cap at 1 hour
                    
                    return {
                        "success": False,
                        "error": (
                            f"Restriction violation: {restriction.reason}"
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "restriction_type": restriction.restriction_type.value,
                        "retry_after": retry_after
                    }
                else:
                    return {
                        "success": False,
                        "error": "Unknown restriction violation",
                        "timestamp": datetime.now().isoformat()
                    }
        
        # Validate parameters if requested
        if validate_params:
            is_valid, errors = tool.validate_parameters(parameters)
            if not is_valid:
                return {
                    "success": False,
                    "error": "Parameter validation failed",
                    "errors": errors,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Execute tool
        try:
            result = tool.execute(**parameters)
            formatted_result = self.formatter.format_result(result)
            
            # Track history if requested
            if track_history:
                self._execution_history.append({
                    "invocation": invocation_dict,
                    "result": formatted_result,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata,
                    "context": context.to_dict() if context else None
                })
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def batch_execute(
        self,
        invocations: List[Dict[str, Any]],
        parallel: bool = False,
        stop_on_error: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool invocations
        
        Args:
            invocations: List of tool invocations
            parallel: Whether to execute in parallel (not implemented)
            stop_on_error: Whether to stop on first error
            
        Returns:
            List of formatted results
        """
        results = []
        
        for invocation in invocations:
            result = self.execute_tool(invocation)
            results.append(result)
            
            if not result["success"] and stop_on_error:
                break
                
        return results
    
    def get_context_prompt(
        self,
        include_tools: bool = True,
        include_history: bool = True,
        max_history: int = 10
    ) -> str:
        """
        Generate context prompt for AI model
        
        Args:
            include_tools: Include available tools
            include_history: Include execution history
            max_history: Maximum history entries to include
            
        Returns:
            Context prompt string
        """
        sections = []
        
        # Tool descriptions
        if include_tools:
            tools = self.get_available_tools()
            if tools:
                sections.append("## Available Tools\n")
                for tool in tools:
                    sections.append(f"### {tool['name']}")
                    sections.append(f"{tool['description']}\n")
                    
                    if tool.get('parameters'):
                        sections.append("Parameters:")
                        params = tool['parameters'].items()
                        for param_name, param_info in params:
                            required = param_name in tool.get('required', [])
                            req_str = (
                                " (required)" if required else " (optional)"
                            )
                            desc = param_info.get('description',
                                                  'No description')
                            sections.append(f"- {param_name}{req_str}: {desc}")
                        sections.append("")
        
        # Execution history
        if include_history and self._execution_history:
            sections.append("\n## Recent Tool Usage\n")
            history_entries = self._execution_history[-max_history:]
            
            for entry in history_entries:
                invocation = entry['invocation']
                result = entry['result']
                
                sections.append(
                    f"- {invocation.get('name', 'Unknown')}: "
                    f"{'Success' if result['success'] else 'Failed'}"
                )
                
        return "\n".join(sections)
    
    def clear_history(self):
        """Clear execution history"""
        self._execution_history.clear()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get execution history"""
        return self._execution_history.copy()
    
    def set_context(self, key: str, value: Any):
        """Set context value"""
        self._context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value"""
        return self._context.get(key, default)
    
    def create_tool_prompt(
        self,
        tool_name: str,
        include_examples: bool = True
    ) -> str:
        """
        Create a detailed prompt for a specific tool
        
        Args:
            tool_name: Name of the tool
            include_examples: Whether to include examples
            
        Returns:
            Tool prompt string
        """
        tool = self.registry.get_tool(tool_name)
        if not tool or not tool.metadata:
            return f"Tool '{tool_name}' not found or has no metadata."
        
        formatted = self.formatter.format_tool(tool)
        
        lines = [
            f"# Tool: {formatted['name']}",
            f"\n{formatted['description']}",
            "\n## Parameters:"
        ]
        
        # Format parameters
        for param_name, param_info in formatted['parameters'].items():
            required = param_name in formatted.get('required', [])
            req_str = " (required)" if required else " (optional)"
            
            param_desc = [f"\n### {param_name}{req_str}"]
            param_desc.append(f"- Type: {param_info.get('type', 'any')}")
            param_desc.append(
                f"- Description: "
                f"{param_info.get('description', 'No description')}"
            )
            
            if 'enum' in param_info:
                param_desc.append(f"- Allowed values: {param_info['enum']}")
            if 'minimum' in param_info:
                param_desc.append(f"- Minimum: {param_info['minimum']}")
            if 'maximum' in param_info:
                param_desc.append(f"- Maximum: {param_info['maximum']}")
            if 'default' in param_info:
                param_desc.append(f"- Default: {param_info['default']}")
            if 'example' in param_info:
                param_desc.append(f"- Example: {param_info['example']}")
                
            lines.extend(param_desc)
        
        # Add examples if requested
        if include_examples and formatted.get('examples'):
            lines.append("\n## Examples:")
            for i, example in enumerate(formatted['examples'], 1):
                lines.append(f"\n### Example {i}")
                lines.append("```json")
                lines.append(json.dumps(example, indent=2))
                lines.append("```")
        
        return "\n".join(lines)
    
    def generate_tool_context_prompt(
        self,
        include_categories: bool = True,
        include_capabilities: bool = True,
        include_examples: bool = True,
        model_capability: ModelCapability = ModelCapability.ADVANCED
    ) -> str:
        """
        Generate comprehensive tool context for AI models
        
        Args:
            include_categories: Include tool categorization
            include_capabilities: Include tool capabilities
            include_examples: Include usage examples
            model_capability: Model capability level
            
        Returns:
            Comprehensive tool context prompt
        """
        template = ToolContextTemplate()
        
        # Get all tools
        tools = self.get_available_tools()
        
        # System overview
        system_overview = (
            "This system provides a comprehensive set of tools for various "
            "tasks. Each tool has specific parameters, capabilities, and "
            "usage patterns. Tools can be used individually or chained "
            "together for complex workflows."
        )
        
        # Tools summary
        tools_summary = self._generate_tools_summary(tools)
        
        # Categories detail
        categories_detail = ""
        if include_categories:
            categories_detail = self._generate_categories_detail()
        
        # Usage patterns
        usage_patterns = """
1. **Single Tool Usage**: Call one tool with appropriate parameters
2. **Tool Chaining**: Use output from one tool as input to another
3. **Parallel Execution**: Run multiple independent tools simultaneously
4. **Conditional Logic**: Choose tools based on previous results
5. **Error Recovery**: Handle tool failures gracefully
"""
        
        # Integration guidelines
        integration_guidelines = """
- Validate all parameters before tool execution
- Check tool availability and readiness
- Handle both synchronous and asynchronous operations
- Respect rate limits and resource constraints
- Log all tool interactions for debugging
"""
        
        # Performance notes
        performance_notes = """
- Cache frequently used tool results when appropriate
- Batch operations when possible
- Monitor execution time and resource usage
- Use appropriate timeouts for long-running operations
"""
        
        # Security guidelines
        security_guidelines = """
- Validate and sanitize all user inputs
- Check permissions before sensitive operations
- Avoid exposing internal system details
- Log security-relevant events
- Follow principle of least privilege
"""
        
        # Examples section
        examples_section = ""
        if include_examples:
            examples_section = self._generate_examples_section(tools[:3])
        
        # Render template
        return template.render(
            system_overview=system_overview,
            tools_summary=tools_summary,
            categories_detail=categories_detail,
            usage_patterns=usage_patterns,
            integration_guidelines=integration_guidelines,
            performance_notes=performance_notes,
            security_guidelines=security_guidelines,
            examples_section=examples_section
        )
    
    def generate_few_shot_examples(
        self,
        tool_name: Optional[str] = None,
        num_examples: int = 3,
        include_errors: bool = True
    ) -> str:
        """
        Generate few-shot examples for tool usage
        
        Args:
            tool_name: Specific tool name (None for mixed examples)
            num_examples: Number of examples to generate
            include_errors: Include error handling examples
            
        Returns:
            Few-shot examples prompt
        """
        examples = []
        
        if tool_name:
            # Get specific tool examples
            tool = self.registry.get_tool(tool_name)
            if tool and tool.metadata and tool.metadata.examples:
                for i, example in enumerate(
                    tool.metadata.examples[:num_examples]
                ):
                    examples.append(
                        self._format_example(
                            tool_name, example, i + 1
                        )
                    )
        else:
            # Get mixed examples from different tools
            all_tools = self.get_available_tools()
            for i, tool_info in enumerate(all_tools[:num_examples]):
                if tool_info.get('examples'):
                    examples.append(
                        self._format_example(
                            tool_info['name'],
                            tool_info['examples'][0],
                            i + 1
                        )
                    )
        
        # Add error examples if requested
        if include_errors:
            examples.append(self._generate_error_example())
        
        return "\n\n".join(examples)
    
    def generate_tool_selection_prompt(
        self,
        task_description: str,
        available_tools: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        use_contextual_selection: bool = True
    ) -> str:
        """
        Generate prompt to help models select appropriate tools
        
        Args:
            task_description: Description of the task
            available_tools: List of available tool names
            constraints: Task constraints
            use_contextual_selection: Whether to use context-aware selection
            
        Returns:
            Tool selection guidance prompt
        """
        template = ToolSelectionTemplate()
        
        # Use contextual selection if enabled
        if use_contextual_selection and self._current_execution_context:
            # Get context-aware recommendations
            recommended = self.contextual_selector.select_tools(
                self._current_execution_context,
                max_tools=10
            )
            tools = []
            for tool_name, score in recommended:
                tool = self.registry.get_tool(tool_name)
                if tool:
                    formatted = self.formatter.format_tool(tool)
                    formatted['_score'] = score
                    tools.append(formatted)
        elif available_tools:
            tools = []
            for name in available_tools:
                tool = self.registry.get_tool(name)
                if tool:
                    tools.append(self.formatter.format_tool(tool))
        else:
            tools = self.get_available_tools()
        
        # Format tool list
        tool_list = self._format_tool_list_for_selection(tools)
        
        # Generate decision tree
        decision_tree = self._generate_decision_tree(
            task_description, tools
        )
        
        # Categories
        categories = self._get_tool_categories(tools)
        
        # Recommendations
        recommendations = self._generate_recommendations(
            task_description, tools, constraints
        )
        
        return template.render(
            tool_list=tool_list,
            decision_tree=decision_tree,
            categories=categories,
            recommendations=recommendations
        )
    
    def recommend_tools_for_task(
        self,
        task_description: str,
        task_type: Optional[TaskType] = None,
        max_recommendations: int = 5,
        context: Optional[ExecutionContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tool recommendations for a specific task
        
        Args:
            task_description: Description of the task
            task_type: Type of task
            max_recommendations: Maximum number of recommendations
            context: Execution context
            
        Returns:
            List of recommended tools with scores
        """
        # Use provided context or current
        context = context or self._current_execution_context
        
        # Create task context if needed
        if not context or not context.task:
            task_ctx = TaskContext(
                task_id=f"task_{datetime.now().timestamp()}",
                task_type=task_type or TaskType.GENERAL,
                description=task_description
            )
            if context:
                context.task = task_ctx
            else:
                context = ExecutionContext(task=task_ctx)
        
        # Get recommendations from controller
        result = self.controller.recommend_tools(
            task_description,
            context.to_dict() if context else None,
            max_recommendations=max_recommendations
        )
        
        # Format results
        recommendations = []
        for tool_name in result.selected_tools:
            tool = self.registry.get_tool(tool_name)
            if tool:
                score_info = result.scores.get(tool_name)
                rec = self.formatter.format_tool(tool)
                rec['score'] = score_info.total_score if score_info else 0.0
                rec['reasons'] = score_info.reasons if score_info else []
                recommendations.append(rec)
        
        return recommendations
    
    def generate_error_recovery_prompt(
        self,
        error_type: str,
        error_message: str,
        tool_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate prompt for error recovery
        
        Args:
            error_type: Type of error
            error_message: Error message
            tool_name: Tool that failed
            context: Additional context
            
        Returns:
            Error recovery guidance prompt
        """
        template = ErrorHandlingTemplate()
        
        # Generate error list
        error_list = f"""
1. **Current Error**: {error_type}
   - Tool: {tool_name}
   - Message: {error_message}
   - Context: {json.dumps(context or {}, indent=2)}
"""
        
        # Recovery strategies
        recovery_strategies = self._generate_recovery_strategies(
            error_type, tool_name
        )
        
        return template.render(
            error_list=error_list,
            recovery_strategies=recovery_strategies
        )
    
    # Helper methods
    
    def _generate_tools_summary(self, tools: List[Dict[str, Any]]) -> str:
        """Generate summary of available tools"""
        if not tools:
            return "No tools available"
        
        summary_lines = []
        for tool in tools:
            summary_lines.append(
                f"- **{tool['name']}**: {tool['description']}"
            )
        
        return "\n".join(summary_lines)
    
    def _generate_categories_detail(self) -> str:
        """Generate detailed category information"""
        categories = {}
        
        # Group tools by category
        for category in ToolCategory:
            tools = self.get_available_tools(category=category)
            if tools:
                categories[category.value] = tools
        
        # Format categories
        lines = []
        for category_name, tools in categories.items():
            lines.append(f"\n### {category_name.title()}")
            for tool in tools:
                lines.append(f"- {tool['name']}")
        
        return "\n".join(lines)
    
    def _generate_examples_section(
        self,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Generate examples section"""
        if not tools:
            return "No examples available"
        
        lines = []
        for tool in tools:
            if tool.get('examples'):
                lines.append(f"\n### {tool['name']} Example")
                example = tool['examples'][0]
                lines.append("```json")
                lines.append(json.dumps({
                    "tool": tool['name'],
                    "parameters": example.get('parameters', {}),
                    "expected_output": example.get('output', {})
                }, indent=2))
                lines.append("```")
        
        return "\n".join(lines)
    
    def _format_example(
        self,
        tool_name: str,
        example: Dict[str, Any],
        index: int
    ) -> str:
        """Format a single example"""
        template = UsageExampleTemplate(format_type="json")
        
        return template.render(
            tool_name=tool_name,
            parameters_json=json.dumps(
                example.get('parameters', {}), indent=2
            ),
            output_json=json.dumps(
                example.get('output', {}), indent=2
            ),
            description=example.get(
                'description', f"Example {index}"
            ),
            parameters_python="",  # Not used in JSON format
            output_description="",  # Not used in JSON format
            parameters_natural=""  # Not used in JSON format
        )
    
    def _generate_error_example(self) -> str:
        """Generate an error handling example"""
        return """
### Error Handling Example

```json
{
    "tool": "file_reader",
    "parameters": {
        "path": "/nonexistent/file.txt"
    },
    "error": {
        "type": "FileNotFoundError",
        "message": "File not found: /nonexistent/file.txt",
        "recovery": [
            "Check if file path is correct",
            "Verify file exists before reading",
            "Use alternative file if available"
        ]
    }
}
```
"""
    
    def _format_tool_list_for_selection(
        self,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Format tool list for selection prompt"""
        lines = []
        
        for tool in tools:
            lines.append(f"\n**{tool['name']}**")
            lines.append(f"- Purpose: {tool['description']}")
            lines.append(f"- Category: {tool.get('category', 'General')}")
            
            # Add key parameters
            if tool.get('required'):
                lines.append(
                    f"- Required parameters: {', '.join(tool['required'])}"
                )
            
            # Add capabilities if present
            if tool.get('capabilities'):
                lines.append(
                    f"- Capabilities: {', '.join(tool['capabilities'])}"
                )
        
        return "\n".join(lines)
    
    def _generate_decision_tree(
        self,
        task_description: str,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Generate a decision tree for tool selection"""
        # This is a simplified example
        return f"""
```
Task: {task_description}
│
├─ Does task involve file operations?
│  ├─ Yes → Consider: file_reader, file_writer, file_manager
│  └─ No → Continue
│
├─ Does task involve data processing?
│  ├─ Yes → Consider: data_processor, calculator, converter
│  └─ No → Continue
│
├─ Does task involve external services?
│  ├─ Yes → Consider: api_caller, web_scraper, database_connector
│  └─ No → Continue
│
└─ Default → Consider: {tools[0]['name'] if tools else 'general_tool'}
```
"""
    
    def _get_tool_categories(
        self,
        tools: List[Dict[str, Any]]
    ) -> str:
        """Get tool categories"""
        categories = {}
        
        for tool in tools:
            category = tool.get('category', 'General')
            if category not in categories:
                categories[category] = []
            categories[category].append(tool['name'])
        
        lines = []
        for category, tool_names in categories.items():
            lines.append(f"- **{category}**: {', '.join(tool_names)}")
        
        return "\n".join(lines)
    
    def _generate_recommendations(
        self,
        task_description: str,
        tools: List[Dict[str, Any]],
        constraints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate tool recommendations"""
        recommendations = []
        
        # Simple keyword-based recommendations
        task_lower = task_description.lower()
        
        for tool in tools:
            tool_name_lower = tool['name'].lower()
            tool_desc_lower = tool['description'].lower()
            
            # Check for keyword matches
            if any(keyword in task_lower for keyword in [
                tool_name_lower,
                tool_desc_lower.split()[0]
            ]):
                recommendations.append(
                    f"- **{tool['name']}** - High relevance to task"
                )
            elif tool.get('category', '').lower() in task_lower:
                recommendations.append(
                    f"- **{tool['name']}** - Category match"
                )
        
        # Add constraint-based recommendations
        if constraints:
            if constraints.get('performance_critical'):
                recommendations.append(
                    "- Prioritize tools with low latency"
                )
            if constraints.get('security_sensitive'):
                recommendations.append(
                    "- Use tools with security features"
                )
        
        return "\n".join(recommendations) if recommendations else (
            "No specific recommendations based on task description"
        )
    
    def _generate_recovery_strategies(
        self,
        error_type: str,
        tool_name: str
    ) -> str:
        """Generate recovery strategies for errors"""
        strategies = {
            "ValidationError": [
                "1. Review parameter requirements",
                "2. Check data types and formats",
                "3. Ensure all required parameters are provided",
                "4. Validate parameter values against constraints"
            ],
            "TimeoutError": [
                "1. Retry with increased timeout",
                "2. Check if service is available",
                "3. Break operation into smaller chunks",
                "4. Use asynchronous execution if available"
            ],
            "PermissionError": [
                "1. Verify user permissions",
                "2. Check authentication status",
                "3. Request necessary permissions",
                "4. Use alternative tool with lower permissions"
            ],
            "ResourceError": [
                "1. Check resource availability",
                "2. Free up resources and retry",
                "3. Use resource-efficient alternatives",
                "4. Schedule operation for off-peak times"
            ]
        }
        
        # Get specific strategies or default
        specific_strategies = strategies.get(
            error_type,
            [
                "1. Check error message for details",
                "2. Verify input parameters",
                "3. Check tool documentation",
                "4. Try alternative approach"
            ]
        )
        
        return "\n".join(specific_strategies)


# Convenience functions

def create_tool_context(
    tools: Optional[List[str]] = None,
    categories: Optional[List[ToolCategory]] = None
) -> str:
    """
    Create a tool context prompt for AI models
    
    Args:
        tools: Specific tool names to include
        categories: Tool categories to include
        
    Returns:
        Context prompt string
    """
    adapter = ToolAIAdapter()
    
    if tools:
        # Get specific tools
        sections = []
        for tool_name in tools:
            prompt = adapter.create_tool_prompt(tool_name)
            sections.append(prompt)
        return "\n\n---\n\n".join(sections)
    else:
        # Get by categories or all
        all_tools = []
        if categories:
            for category in categories:
                all_tools.extend(
                    adapter.get_available_tools(category=category)
                )
        else:
            all_tools = adapter.get_available_tools()
            
        return adapter.get_context_prompt(
            include_tools=True, include_history=False
        )


def execute_ai_tool_request(
    request: Union[Dict[str, Any], str]
) -> Dict[str, Any]:
    """
    Execute a tool request from an AI model
    
    Args:
        request: Tool invocation request
        
    Returns:
        Execution result
    """
    adapter = ToolAIAdapter()
    return adapter.execute_tool(request)