"""
Prompt Template System

This module provides a flexible system for creating and managing prompt templates
that help AI models understand and effectively use tools.
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from abc import ABC, abstractmethod


class PromptStyle(Enum):
    """Different styles of prompts for various use cases"""
    DETAILED = "detailed"  # Full explanations with examples
    CONCISE = "concise"  # Brief, to-the-point descriptions
    FEW_SHOT = "few_shot"  # Focused on examples
    STRUCTURED = "structured"  # Highly structured format
    CONVERSATIONAL = "conversational"  # Natural language style


class ModelCapability(Enum):
    """AI model capabilities that affect prompt generation"""
    BASIC = "basic"  # Simple instruction following
    ADVANCED = "advanced"  # Complex reasoning and tool use
    FUNCTION_CALLING = "function_calling"  # Native function calling support
    JSON_MODE = "json_mode"  # Structured JSON output
    VISION = "vision"  # Can process images
    LONG_CONTEXT = "long_context"  # Supports long prompts


@dataclass
class PromptTemplate:
    """Base class for all prompt templates"""
    name: str
    description: str
    template: str
    variables: List[str] = field(default_factory=list)
    style: PromptStyle = PromptStyle.DETAILED
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def render(self, **kwargs) -> str:
        """Render the template with provided variables"""
        # Check all required variables are provided
        missing = [var for var in self.variables if var not in kwargs]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Render template
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Template variable not found: {e}")


class ToolDescriptionTemplate(PromptTemplate):
    """Template for describing a tool to an AI model"""
    
    def __init__(self, style: PromptStyle = PromptStyle.DETAILED):
        templates = {
            PromptStyle.DETAILED: """
## Tool: {tool_name}

**Description:** {description}

**Category:** {category}

**Purpose:** {purpose}

**Parameters:**
{parameters}

**Returns:** {returns}

**Usage Guidelines:**
{guidelines}

**Example Usage:**
{examples}

**Error Handling:**
{error_handling}
""",
            PromptStyle.CONCISE: """
**{tool_name}**: {description}

Parameters: {parameters}
Returns: {returns}

Example: {examples}
""",
            PromptStyle.STRUCTURED: """
{
    "tool": "{tool_name}",
    "description": "{description}",
    "parameters": {parameters_json},
    "returns": {returns_json},
    "examples": {examples_json}
}
""",
            PromptStyle.FEW_SHOT: """
Tool: {tool_name}

Examples:
{examples}

Pattern: {pattern}
""",
            PromptStyle.CONVERSATIONAL: """
The {tool_name} tool {description}. 

To use it, you'll need to provide {parameters_natural}. 

It will return {returns_natural}.

For example: {examples_natural}
"""
        }
        
        super().__init__(
            name="tool_description",
            description="Template for describing a tool",
            template=templates.get(style, templates[PromptStyle.DETAILED]),
            variables=[
                "tool_name", "description", "category", "purpose",
                "parameters", "returns", "guidelines", "examples",
                "error_handling", "parameters_json", "returns_json",
                "examples_json", "pattern", "parameters_natural",
                "returns_natural", "examples_natural"
            ],
            style=style
        )


class ParameterExplanationTemplate(PromptTemplate):
    """Template for explaining tool parameters"""
    
    def __init__(self):
        super().__init__(
            name="parameter_explanation",
            description="Template for explaining a parameter",
            template="""
- **{param_name}** ({param_type}){required_marker}: {description}
  - Type: `{type_detail}`
  - Constraints: {constraints}
  - Default: {default_value}
  - Example: `{example_value}`
""",
            variables=[
                "param_name", "param_type", "required_marker",
                "description", "type_detail", "constraints",
                "default_value", "example_value"
            ]
        )


class UsageExampleTemplate(PromptTemplate):
    """Template for showing tool usage examples"""
    
    def __init__(self, format_type: str = "json"):
        templates = {
            "json": """
```json
{
    "tool": "{tool_name}",
    "parameters": {parameters_json},
    "expected_output": {output_json},
    "description": "{description}"
}
```
""",
            "python": """
```python
# {description}
result = {tool_name}({parameters_python})
# Expected output: {output_description}
```
""",
            "natural": """
To {description}, use the {tool_name} tool with {parameters_natural}.
This will return {output_description}.
"""
        }
        
        super().__init__(
            name="usage_example",
            description="Template for usage examples",
            template=templates.get(format_type, templates["json"]),
            variables=[
                "tool_name", "parameters_json", "output_json",
                "description", "parameters_python", "output_description",
                "parameters_natural"
            ]
        )


class ErrorHandlingTemplate(PromptTemplate):
    """Template for error handling guidance"""
    
    def __init__(self):
        super().__init__(
            name="error_handling",
            description="Template for error handling guidance",
            template="""
**Common Errors and Solutions:**

{error_list}

**Best Practices:**
- Always validate parameters before calling the tool
- Check for required parameters
- Handle both success and failure cases
- Log errors for debugging
- Provide meaningful error messages to users

**Recovery Strategies:**
{recovery_strategies}
""",
            variables=["error_list", "recovery_strategies"]
        )


class ToolSelectionTemplate(PromptTemplate):
    """Template for helping models select the right tool"""
    
    def __init__(self):
        super().__init__(
            name="tool_selection",
            description="Template for tool selection guidance",
            template="""
## Selecting the Right Tool

**Available Tools:**
{tool_list}

**Selection Criteria:**
1. **Task Match**: Choose tools that directly address the task requirements
2. **Parameter Availability**: Ensure you have all required parameters
3. **Output Requirements**: Verify the tool provides the needed output format
4. **Efficiency**: Select the most efficient tool for the task
5. **Error Tolerance**: Consider tools with better error handling for critical tasks

**Decision Tree:**
{decision_tree}

**Tool Categories:**
{categories}

**Recommendations:**
{recommendations}
""",
            variables=[
                "tool_list", "decision_tree", "categories", "recommendations"
            ]
        )


class ToolContextTemplate(PromptTemplate):
    """Template for providing comprehensive tool context"""
    
    def __init__(self):
        super().__init__(
            name="tool_context",
            description="Template for comprehensive tool context",
            template="""
# Tool System Context

## Overview
{system_overview}

## Available Tools
{tools_summary}

## Tool Categories
{categories_detail}

## Usage Patterns
{usage_patterns}

## Integration Guidelines
{integration_guidelines}

## Performance Considerations
{performance_notes}

## Security Guidelines
{security_guidelines}

## Examples and Best Practices
{examples_section}
""",
            variables=[
                "system_overview", "tools_summary", "categories_detail",
                "usage_patterns", "integration_guidelines", "performance_notes",
                "security_guidelines", "examples_section"
            ]
        )


class ChainedToolTemplate(PromptTemplate):
    """Template for explaining how to chain tools together"""
    
    def __init__(self):
        super().__init__(
            name="chained_tools",
            description="Template for tool chaining guidance",
            template="""
## Tool Chaining: {chain_name}

**Objective:** {objective}

**Tool Sequence:**
{tool_sequence}

**Data Flow:**
{data_flow}

**Example Workflow:**
{workflow_example}

**Error Propagation:**
{error_handling}

**Best Practices:**
- Validate data between tool calls
- Handle partial failures gracefully
- Log intermediate results
- Provide progress updates
""",
            variables=[
                "chain_name", "objective", "tool_sequence",
                "data_flow", "workflow_example", "error_handling"
            ]
        )


class PromptTemplateFactory:
    """Factory for creating prompt templates"""
    
    _templates: Dict[str, type] = {
        "tool_description": ToolDescriptionTemplate,
        "parameter_explanation": ParameterExplanationTemplate,
        "usage_example": UsageExampleTemplate,
        "error_handling": ErrorHandlingTemplate,
        "tool_selection": ToolSelectionTemplate,
        "tool_context": ToolContextTemplate,
        "chained_tools": ChainedToolTemplate
    }
    
    @classmethod
    def create(
        cls,
        template_type: str,
        **kwargs
    ) -> PromptTemplate:
        """Create a prompt template of the specified type"""
        if template_type not in cls._templates:
            raise ValueError(
                f"Unknown template type: {template_type}. "
                f"Available types: {list(cls._templates.keys())}"
            )
        
        template_class = cls._templates[template_type]
        return template_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, template_class: type):
        """Register a new template type"""
        if not issubclass(template_class, PromptTemplate):
            raise ValueError(
                "Template class must inherit from PromptTemplate"
            )
        cls._templates[name] = template_class
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List all available template types"""
        return list(cls._templates.keys())


class CompositePromptTemplate:
    """Combines multiple templates into a single prompt"""
    
    def __init__(self, name: str = "composite"):
        self.name = name
        self.templates: List[PromptTemplate] = []
        self.separator = "\n\n---\n\n"
    
    def add_template(self, template: PromptTemplate):
        """Add a template to the composite"""
        self.templates.append(template)
    
    def render(self, **kwargs) -> str:
        """Render all templates with provided variables"""
        rendered = []
        
        for template in self.templates:
            # Only render if all required variables are available
            if all(var in kwargs for var in template.variables):
                try:
                    rendered.append(template.render(**kwargs))
                except Exception:
                    # Skip templates that fail to render
                    continue
        
        return self.separator.join(rendered)
    
    def get_required_variables(self) -> List[str]:
        """Get all required variables across templates"""
        variables = set()
        for template in self.templates:
            variables.update(template.variables)
        return list(variables)


# Utility functions

def create_tool_description_prompt(
    tool_info: Dict[str, Any],
    style: PromptStyle = PromptStyle.DETAILED,
    include_examples: bool = True
) -> str:
    """Create a tool description prompt from tool information"""
    template = ToolDescriptionTemplate(style=style)
    
    # Prepare variables
    variables = {
        "tool_name": tool_info.get("name", "Unknown Tool"),
        "description": tool_info.get("description", "No description"),
        "category": tool_info.get("category", "General"),
        "purpose": tool_info.get("purpose", tool_info.get("description", "")),
        "parameters": _format_parameters(tool_info.get("parameters", {})),
        "returns": _format_returns(tool_info.get("returns", {})),
        "guidelines": tool_info.get("guidelines", "Follow general best practices"),
        "examples": _format_examples(tool_info.get("examples", [])) if include_examples else "N/A",
        "error_handling": tool_info.get("error_handling", "Handle errors appropriately"),
        # Additional format-specific variables
        "parameters_json": json.dumps(tool_info.get("parameters", {}), indent=2),
        "returns_json": json.dumps(tool_info.get("returns", {}), indent=2),
        "examples_json": json.dumps(tool_info.get("examples", []), indent=2),
        "pattern": _extract_pattern(tool_info.get("examples", [])),
        "parameters_natural": _natural_parameters(tool_info.get("parameters", {})),
        "returns_natural": _natural_returns(tool_info.get("returns", {})),
        "examples_natural": _natural_examples(tool_info.get("examples", []))
    }
    
    return template.render(**variables)


def _format_parameters(parameters: Dict[str, Any]) -> str:
    """Format parameters for display"""
    if not parameters:
        return "No parameters required"
    
    template = ParameterExplanationTemplate()
    formatted = []
    
    for param_name, param_info in parameters.items():
        variables = {
            "param_name": param_name,
            "param_type": param_info.get("type", "any"),
            "required_marker": " **(required)**" if param_info.get("required", False) else "",
            "description": param_info.get("description", "No description"),
            "type_detail": param_info.get("type", "any"),
            "constraints": _format_constraints(param_info),
            "default_value": param_info.get("default", "None"),
            "example_value": param_info.get("example", "N/A")
        }
        formatted.append(template.render(**variables).strip())
    
    return "\n".join(formatted)


def _format_constraints(param_info: Dict[str, Any]) -> str:
    """Format parameter constraints"""
    constraints = []
    
    if "enum" in param_info:
        constraints.append(f"Values: {param_info['enum']}")
    if "min" in param_info:
        constraints.append(f"Min: {param_info['min']}")
    if "max" in param_info:
        constraints.append(f"Max: {param_info['max']}")
    if "pattern" in param_info:
        constraints.append(f"Pattern: {param_info['pattern']}")
    
    return " | ".join(constraints) if constraints else "None"


def _format_returns(returns: Dict[str, Any]) -> str:
    """Format return value information"""
    if not returns:
        return "No return value"
    
    return f"{returns.get('type', 'any')}: {returns.get('description', 'No description')}"


def _format_examples(examples: List[Dict[str, Any]]) -> str:
    """Format usage examples"""
    if not examples:
        return "No examples available"
    
    template = UsageExampleTemplate()
    formatted = []
    
    for i, example in enumerate(examples, 1):
        variables = {
            "tool_name": example.get("tool", "tool"),
            "parameters_json": json.dumps(example.get("parameters", {}), indent=4),
            "output_json": json.dumps(example.get("output", {}), indent=4),
            "description": example.get("description", f"Example {i}"),
            "parameters_python": _python_parameters(example.get("parameters", {})),
            "output_description": example.get("output_description", "See output above"),
            "parameters_natural": _natural_parameters(example.get("parameters", {}))
        }
        formatted.append(template.render(**variables))
    
    return "\n".join(formatted)


def _extract_pattern(examples: List[Dict[str, Any]]) -> str:
    """Extract common patterns from examples"""
    if not examples:
        return "No pattern available"
    
    # Simple pattern extraction - could be enhanced
    return "tool_name(required_params, optional_params) -> output"


def _natural_parameters(parameters: Dict[str, Any]) -> str:
    """Convert parameters to natural language"""
    if not parameters:
        return "no parameters"
    
    parts = []
    for name, info in parameters.items():
        if info.get("required", False):
            parts.append(f"{name} (required)")
        else:
            parts.append(f"{name} (optional)")
    
    return ", ".join(parts)


def _natural_returns(returns: Dict[str, Any]) -> str:
    """Convert returns to natural language"""
    if not returns:
        return "nothing"
    
    return returns.get("description", f"a {returns.get('type', 'value')}")


def _natural_examples(examples: List[Dict[str, Any]]) -> str:
    """Convert examples to natural language"""
    if not examples:
        return "no examples available"
    
    if len(examples) == 1:
        return examples[0].get("description", "see the example above")
    
    return f"see the {len(examples)} examples above"


def _python_parameters(parameters: Dict[str, Any]) -> str:
    """Format parameters for Python function call"""
    if not parameters:
        return ""
    
    parts = []
    for name, value in parameters.items():
        if isinstance(value, str):
            parts.append(f'{name}="{value}"')
        else:
            parts.append(f'{name}={value}')
    
    return ", ".join(parts)