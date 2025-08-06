"""
Prompt Builder System

This module provides a flexible system for building prompts based on
different scenarios, model capabilities, and user preferences.
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import json
import logging

from ..base import BaseTool, ToolCategory
from ..registry import ToolRegistry
from ..ai_adapter import ToolAIAdapter
from .prompt_templates import (
    PromptStyle, ModelCapability, PromptTemplate,
    PromptTemplateFactory, CompositePromptTemplate,
    create_tool_description_prompt
)


logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    """Context information for prompt building"""
    task_description: Optional[str] = None
    model_capabilities: Set[ModelCapability] = field(
        default_factory=lambda: {ModelCapability.BASIC}
    )
    style_preference: PromptStyle = PromptStyle.DETAILED
    include_examples: bool = True
    max_tokens: Optional[int] = None
    tools_filter: Optional[List[str]] = None
    categories_filter: Optional[List[ToolCategory]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PromptBuilder:
    """
    Main prompt builder for creating customized prompts
    
    This class orchestrates the creation of prompts by combining
    templates, context, and tool information.
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        adapter: Optional[ToolAIAdapter] = None
    ):
        """
        Initialize the prompt builder
        
        Args:
            registry: Tool registry instance
            adapter: Tool AI adapter instance
        """
        self.registry = registry or ToolRegistry()
        self.adapter = adapter or ToolAIAdapter(registry=self.registry)
        self._template_cache: Dict[str, PromptTemplate] = {}
    
    def build_prompt(
        self,
        context: PromptContext,
        prompt_type: str = "comprehensive"
    ) -> str:
        """
        Build a prompt based on context and type
        
        Args:
            context: Prompt context information
            prompt_type: Type of prompt to build
            
        Returns:
            Generated prompt string
        """
        builders = {
            "comprehensive": self._build_comprehensive_prompt,
            "tool_selection": self._build_tool_selection_prompt,
            "few_shot": self._build_few_shot_prompt,
            "minimal": self._build_minimal_prompt,
            "tutorial": self._build_tutorial_prompt,
            "reference": self._build_reference_prompt
        }
        
        builder = builders.get(prompt_type, self._build_comprehensive_prompt)
        return builder(context)
    
    def _build_comprehensive_prompt(self, context: PromptContext) -> str:
        """Build a comprehensive prompt with full context"""
        sections = []
        
        # Add task description if provided
        if context.task_description:
            sections.append(f"# Task\n\n{context.task_description}\n")
        
        # Add tool context
        if ModelCapability.LONG_CONTEXT in context.model_capabilities:
            tool_context = self.adapter.generate_tool_context_prompt(
                include_categories=True,
                include_capabilities=True,
                include_examples=context.include_examples,
                model_capability=max(context.model_capabilities)
            )
            sections.append(tool_context)
        else:
            # Use condensed version for limited context
            sections.append(self._build_condensed_tools_section(context))
        
        # Add usage guidelines
        sections.append(self._build_usage_guidelines(context))
        
        # Add examples if requested
        if context.include_examples:
            examples = self.adapter.generate_few_shot_examples(
                num_examples=3,
                include_errors=True
            )
            if examples:
                sections.append(f"# Examples\n\n{examples}")
        
        return "\n\n".join(sections)
    
    def _build_tool_selection_prompt(self, context: PromptContext) -> str:
        """Build a prompt focused on tool selection"""
        if not context.task_description:
            raise ValueError("Task description required for tool selection prompt")
        
        return self.adapter.generate_tool_selection_prompt(
            task_description=context.task_description,
            available_tools=context.tools_filter,
            constraints=context.metadata.get("constraints")
        )
    
    def _build_few_shot_prompt(self, context: PromptContext) -> str:
        """Build a prompt with focus on examples"""
        sections = []
        
        # Brief introduction
        sections.append("# Tool Usage Examples\n")
        
        if context.task_description:
            sections.append(f"Task: {context.task_description}\n")
        
        # Get relevant examples
        tool_name = None
        if context.tools_filter and len(context.tools_filter) == 1:
            tool_name = context.tools_filter[0]
        
        examples = self.adapter.generate_few_shot_examples(
            tool_name=tool_name,
            num_examples=5,
            include_errors=True
        )
        
        sections.append(examples)
        
        # Add pattern description
        sections.append("\n## Usage Pattern")
        sections.append(
            "1. Select appropriate tool based on task\n"
            "2. Prepare parameters according to tool requirements\n"
            "3. Execute tool with validated parameters\n"
            "4. Handle response appropriately (success or error)"
        )
        
        return "\n\n".join(sections)
    
    def _build_minimal_prompt(self, context: PromptContext) -> str:
        """Build a minimal prompt with essential information only"""
        tools = self._get_filtered_tools(context)
        
        lines = ["# Available Tools\n"]
        
        for tool in tools[:5]:  # Limit to 5 tools for minimal prompt
            lines.append(f"- **{tool['name']}**: {tool['description']}")
        
        if len(tools) > 5:
            lines.append(f"- ... and {len(tools) - 5} more tools")
        
        if context.task_description:
            lines.append(f"\n# Task\n{context.task_description}")
        
        return "\n".join(lines)
    
    def _build_tutorial_prompt(self, context: PromptContext) -> str:
        """Build an educational prompt for learning tool usage"""
        sections = []
        
        # Introduction
        sections.append("""# Tool Usage Tutorial

This tutorial will guide you through using the available tools effectively.

## Overview

Tools are specialized functions that perform specific tasks. Each tool has:
- A unique name
- A description of its purpose
- Required and optional parameters
- Expected output format
""")
        
        # Get a sample tool for detailed explanation
        tools = self._get_filtered_tools(context)
        if tools:
            sample_tool = tools[0]
            sections.append(f"\n## Example Tool: {sample_tool['name']}")
            
            # Detailed explanation
            tool_prompt = create_tool_description_prompt(
                sample_tool,
                style=PromptStyle.CONVERSATIONAL,
                include_examples=True
            )
            sections.append(tool_prompt)
        
        # General usage steps
        sections.append("""
## General Usage Steps

1. **Identify the Task**: Understand what needs to be accomplished
2. **Select the Tool**: Choose the most appropriate tool
3. **Prepare Parameters**: Gather required information
4. **Validate Input**: Ensure parameters meet requirements
5. **Execute**: Call the tool with parameters
6. **Handle Response**: Process success or error appropriately

## Best Practices

- Always validate parameters before execution
- Handle errors gracefully
- Chain tools for complex workflows
- Log important operations
- Consider performance implications
""")
        
        return "\n".join(sections)
    
    def _build_reference_prompt(self, context: PromptContext) -> str:
        """Build a reference-style prompt with detailed specifications"""
        composite = CompositePromptTemplate(name="reference")
        
        # Add tool descriptions
        tools = self._get_filtered_tools(context)
        for tool in tools:
            if context.style_preference == PromptStyle.STRUCTURED:
                # JSON-style reference
                composite.add_template(
                    PromptTemplateFactory.create(
                        "tool_description",
                        style=PromptStyle.STRUCTURED
                    )
                )
            else:
                # Detailed reference
                composite.add_template(
                    PromptTemplateFactory.create(
                        "tool_description",
                        style=PromptStyle.DETAILED
                    )
                )
        
        # Prepare all variables
        all_vars = {}
        for tool in tools:
            tool_vars = self._prepare_tool_variables(tool)
            # Prefix variables with tool name to avoid conflicts
            for key, value in tool_vars.items():
                all_vars[f"{tool['name']}_{key}"] = value
        
        return composite.render(**all_vars)
    
    def _build_condensed_tools_section(self, context: PromptContext) -> str:
        """Build condensed tools section for limited context"""
        tools = self._get_filtered_tools(context)
        
        lines = ["# Tools Summary\n"]
        
        # Group by category if many tools
        if len(tools) > 10:
            categories = {}
            for tool in tools:
                cat = tool.get('category', 'General')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tool['name'])
            
            for cat, tool_names in categories.items():
                lines.append(f"**{cat}**: {', '.join(tool_names)}")
        else:
            # List all tools
            for tool in tools:
                req_params = tool.get('required', [])
                params_str = f" (requires: {', '.join(req_params)})" if req_params else ""
                lines.append(f"- **{tool['name']}**: {tool['description']}{params_str}")
        
        return "\n".join(lines)
    
    def _build_usage_guidelines(self, context: PromptContext) -> str:
        """Build usage guidelines section"""
        guidelines = ["# Usage Guidelines\n"]
        
        # Model-specific guidelines
        if ModelCapability.FUNCTION_CALLING in context.model_capabilities:
            guidelines.append(
                "- Use function calling syntax for tool invocation"
            )
        else:
            guidelines.append(
                "- Format tool calls as JSON objects with 'tool' and 'parameters' fields"
            )
        
        if ModelCapability.JSON_MODE in context.model_capabilities:
            guidelines.append(
                "- All tool interactions should use valid JSON format"
            )
        
        # General guidelines
        guidelines.extend([
            "- Validate all required parameters before tool execution",
            "- Handle both success and error responses",
            "- Chain tools together for complex tasks",
            "- Use appropriate tools based on task requirements"
        ])
        
        return "\n".join(guidelines)
    
    def _get_filtered_tools(self, context: PromptContext) -> List[Dict[str, Any]]:
        """Get tools filtered by context"""
        # Apply filters
        if context.tools_filter:
            # Get specific tools
            tools = []
            for tool_name in context.tools_filter:
                tool = self.registry.get_tool(tool_name)
                if tool and tool.is_ready:
                    try:
                        formatted = self.adapter.formatter.format_tool(tool)
                        tools.append(formatted)
                    except Exception as e:
                        logger.error(f"Failed to format tool {tool_name}: {e}")
        else:
            # Get all tools, optionally filtered by category
            tools = []
            if context.categories_filter:
                for category in context.categories_filter:
                    tools.extend(
                        self.adapter.get_available_tools(category=category)
                    )
            else:
                tools = self.adapter.get_available_tools()
        
        return tools
    
    def _prepare_tool_variables(
        self,
        tool: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare variables for tool template rendering"""
        return {
            "tool_name": tool.get("name", "Unknown"),
            "description": tool.get("description", "No description"),
            "category": tool.get("category", "General"),
            "purpose": tool.get("purpose", tool.get("description", "")),
            "parameters": self._format_parameters_text(tool.get("parameters", {})),
            "returns": self._format_returns_text(tool.get("returns", {})),
            "guidelines": tool.get("guidelines", "Follow best practices"),
            "examples": self._format_examples_text(tool.get("examples", [])),
            "error_handling": tool.get("error_handling", "Handle errors appropriately"),
            "parameters_json": json.dumps(tool.get("parameters", {}), indent=2),
            "returns_json": json.dumps(tool.get("returns", {}), indent=2),
            "examples_json": json.dumps(tool.get("examples", []), indent=2),
            "pattern": "tool(parameters) -> result",
            "parameters_natural": self._natural_language_params(tool.get("parameters", {})),
            "returns_natural": self._natural_language_returns(tool.get("returns", {})),
            "examples_natural": "see examples above"
        }
    
    def _format_parameters_text(self, parameters: Dict[str, Any]) -> str:
        """Format parameters as text"""
        if not parameters:
            return "No parameters"
        
        lines = []
        for name, info in parameters.items():
            lines.append(f"- {name}: {info.get('description', 'No description')}")
        
        return "\n".join(lines)
    
    def _format_returns_text(self, returns: Dict[str, Any]) -> str:
        """Format returns as text"""
        if not returns:
            return "No return value"
        
        return f"{returns.get('type', 'any')}: {returns.get('description', 'Result')}"
    
    def _format_examples_text(self, examples: List[Dict[str, Any]]) -> str:
        """Format examples as text"""
        if not examples:
            return "No examples"
        
        return f"{len(examples)} example(s) available"
    
    def _natural_language_params(self, parameters: Dict[str, Any]) -> str:
        """Convert parameters to natural language"""
        if not parameters:
            return "no parameters"
        
        param_names = list(parameters.keys())
        if len(param_names) == 1:
            return param_names[0]
        elif len(param_names) == 2:
            return f"{param_names[0]} and {param_names[1]}"
        else:
            return f"{', '.join(param_names[:-1])}, and {param_names[-1]}"
    
    def _natural_language_returns(self, returns: Dict[str, Any]) -> str:
        """Convert returns to natural language"""
        if not returns:
            return "nothing"
        
        return returns.get('description', 'a result')


class AdaptivePromptBuilder(PromptBuilder):
    """
    Adaptive prompt builder that adjusts based on model feedback
    
    This builder can learn from model responses and adapt its
    prompt generation strategy.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._performance_history: List[Dict[str, Any]] = []
        self._strategy_weights: Dict[str, float] = {
            "detailed": 1.0,
            "concise": 1.0,
            "examples": 1.0,
            "structured": 1.0
        }
    
    def build_adaptive_prompt(
        self,
        context: PromptContext,
        model_feedback: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build an adaptive prompt based on model feedback
        
        Args:
            context: Prompt context
            model_feedback: Feedback from previous interactions
            
        Returns:
            Adapted prompt string
        """
        # Update strategy based on feedback
        if model_feedback:
            self._update_strategy(model_feedback)
        
        # Choose prompt style based on weights
        style = self._choose_style(context)
        context.style_preference = style
        
        # Adjust example inclusion
        context.include_examples = self._should_include_examples()
        
        # Build prompt with adapted context
        return self.build_prompt(context, prompt_type="comprehensive")
    
    def _update_strategy(self, feedback: Dict[str, Any]):
        """Update strategy weights based on feedback"""
        success = feedback.get("success", False)
        prompt_style = feedback.get("prompt_style", "detailed")
        
        # Adjust weights
        if success:
            self._strategy_weights[prompt_style] *= 1.1
        else:
            self._strategy_weights[prompt_style] *= 0.9
        
        # Normalize weights
        total = sum(self._strategy_weights.values())
        for key in self._strategy_weights:
            self._strategy_weights[key] /= total
        
        # Record history
        self._performance_history.append({
            "feedback": feedback,
            "weights": self._strategy_weights.copy()
        })
    
    def _choose_style(self, context: PromptContext) -> PromptStyle:
        """Choose prompt style based on weights"""
        # Map weights to styles
        style_mapping = {
            "detailed": PromptStyle.DETAILED,
            "concise": PromptStyle.CONCISE,
            "examples": PromptStyle.FEW_SHOT,
            "structured": PromptStyle.STRUCTURED
        }
        
        # Choose based on highest weight
        best_strategy = max(
            self._strategy_weights.items(),
            key=lambda x: x[1]
        )[0]
        
        return style_mapping.get(best_strategy, PromptStyle.DETAILED)
    
    def _should_include_examples(self) -> bool:
        """Determine if examples should be included"""
        return self._strategy_weights.get("examples", 1.0) > 0.5


def create_prompt_for_task(
    task: str,
    model_capabilities: Optional[Set[ModelCapability]] = None,
    style: PromptStyle = PromptStyle.DETAILED,
    tools: Optional[List[str]] = None
) -> str:
    """
    Convenience function to create a prompt for a task
    
    Args:
        task: Task description
        model_capabilities: Model capabilities
        style: Prompt style preference
        tools: Specific tools to include
        
    Returns:
        Generated prompt
    """
    context = PromptContext(
        task_description=task,
        model_capabilities=model_capabilities or {ModelCapability.BASIC},
        style_preference=style,
        tools_filter=tools
    )
    
    builder = PromptBuilder()
    return builder.build_prompt(context)


def create_adaptive_prompt(
    task: str,
    feedback_history: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Create an adaptive prompt based on feedback history
    
    Args:
        task: Task description
        feedback_history: History of model feedback
        
    Returns:
        Adapted prompt
    """
    context = PromptContext(task_description=task)
    builder = AdaptivePromptBuilder()
    
    # Process feedback history
    if feedback_history:
        for feedback in feedback_history:
            builder._update_strategy(feedback)
    
    return builder.build_adaptive_prompt(context)