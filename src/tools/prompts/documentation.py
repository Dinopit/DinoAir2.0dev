"""
Tool Documentation Generator

This module provides automated documentation generation for tools,
creating markdown docs, usage examples, and API references.
"""

import os
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json
from pathlib import Path

from ..base import BaseTool, ToolCategory, ParameterType
from ..registry import ToolRegistry
from ..ai_adapter import ToolAIAdapter
from .prompt_templates import create_tool_description_prompt, PromptStyle


class DocumentationGenerator:
    """
    Generates comprehensive documentation for tools
    
    This class creates various types of documentation including:
    - Markdown documentation files
    - API reference documentation
    - Usage examples and tutorials
    - Integration guides
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        output_dir: str = "docs/tools"
    ):
        """
        Initialize the documentation generator
        
        Args:
            registry: Tool registry instance
            output_dir: Output directory for documentation
        """
        self.registry = registry or ToolRegistry()
        self.output_dir = Path(output_dir)
        self.adapter = ToolAIAdapter(registry=self.registry)
    
    def generate_all_documentation(self, include_private: bool = False):
        """
        Generate documentation for all tools
        
        Args:
            include_private: Include private/internal tools
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate index
        self._generate_index()
        
        # Generate category pages
        self._generate_category_pages()
        
        # Generate individual tool docs
        tools = self.registry.list_tools(enabled_only=not include_private)
        for tool_info in tools:
            self.generate_tool_documentation(tool_info["name"])
        
        # Generate API reference
        self._generate_api_reference()
        
        # Generate integration guide
        self._generate_integration_guide()
    
    def generate_tool_documentation(
        self,
        tool_name: str,
        include_source: bool = False
    ) -> str:
        """
        Generate documentation for a specific tool
        
        Args:
            tool_name: Name of the tool
            include_source: Include source code reference
            
        Returns:
            Path to generated documentation file
        """
        tool = self.registry.get_tool(tool_name)
        if not tool or not tool.metadata:
            raise ValueError(f"Tool '{tool_name}' not found or has no metadata")
        
        # Generate markdown content
        content = self._generate_tool_markdown(tool, include_source)
        
        # Write to file
        file_path = self.output_dir / f"{tool_name}.md"
        file_path.write_text(content, encoding="utf-8")
        
        return str(file_path)
    
    def _generate_tool_markdown(
        self,
        tool: BaseTool,
        include_source: bool = False
    ) -> str:
        """Generate markdown documentation for a tool"""
        lines = []
        metadata = tool.metadata
        
        # Header
        lines.append(f"# {metadata.name}")
        lines.append("")
        lines.append(f"**Version:** {metadata.version}")
        lines.append(f"**Category:** {metadata.category.value}")
        if metadata.tags:
            lines.append(f"**Tags:** {', '.join(metadata.tags)}")
        lines.append("")
        
        # Description
        lines.append("## Description")
        lines.append("")
        lines.append(metadata.description)
        lines.append("")
        
        # Capabilities
        if metadata.capabilities:
            lines.append("## Capabilities")
            lines.append("")
            for capability in metadata.capabilities:
                lines.append(f"- {capability}")
            lines.append("")
        
        # Parameters
        lines.append("## Parameters")
        lines.append("")
        if metadata.parameters:
            lines.append("| Name | Type | Required | Description |")
            lines.append("|------|------|----------|-------------|")
            
            for param in metadata.parameters:
                required = "Yes" if param.required else "No"
                param_type = self._format_parameter_type(param)
                desc = param.description.replace("|", "\\|")
                lines.append(f"| {param.name} | {param_type} | {required} | {desc} |")
            
            lines.append("")
            
            # Parameter details
            lines.append("### Parameter Details")
            lines.append("")
            
            for param in metadata.parameters:
                lines.append(f"#### {param.name}")
                lines.append("")
                lines.append(f"- **Type:** `{param.type.value}`")
                lines.append(f"- **Required:** {param.required}")
                lines.append(f"- **Description:** {param.description}")
                
                if param.default is not None:
                    lines.append(f"- **Default:** `{param.default}`")
                if param.example is not None:
                    lines.append(f"- **Example:** `{param.example}`")
                if param.enum_values:
                    lines.append(f"- **Allowed Values:** {param.enum_values}")
                if param.min_value is not None:
                    lines.append(f"- **Minimum:** {param.min_value}")
                if param.max_value is not None:
                    lines.append(f"- **Maximum:** {param.max_value}")
                if param.pattern:
                    lines.append(f"- **Pattern:** `{param.pattern}`")
                
                lines.append("")
        else:
            lines.append("This tool requires no parameters.")
            lines.append("")
        
        # Return Type
        lines.append("## Return Type")
        lines.append("")
        if metadata.return_type:
            lines.append(f"Returns `{metadata.return_type}`")
        else:
            lines.append("Returns a `ToolResult` object with the following structure:")
            lines.append("")
            lines.append("```python")
            lines.append("{")
            lines.append('    "success": bool,')
            lines.append('    "output": Any,  # Tool-specific output')
            lines.append('    "errors": List[str],')
            lines.append('    "warnings": List[str],')
            lines.append('    "metadata": Dict[str, Any]')
            lines.append("}")
            lines.append("```")
        lines.append("")
        
        # Examples
        if metadata.examples:
            lines.append("## Examples")
            lines.append("")
            
            for i, example in enumerate(metadata.examples, 1):
                lines.append(f"### Example {i}")
                if example.get("description"):
                    lines.append(f"_{example['description']}_")
                lines.append("")
                
                # Input
                lines.append("**Input:**")
                lines.append("```json")
                lines.append(json.dumps({
                    "tool": metadata.name,
                    "parameters": example.get("parameters", {})
                }, indent=2))
                lines.append("```")
                lines.append("")
                
                # Output
                if "output" in example:
                    lines.append("**Expected Output:**")
                    lines.append("```json")
                    lines.append(json.dumps(example["output"], indent=2))
                    lines.append("```")
                    lines.append("")
        
        # Usage Notes
        if hasattr(tool, "get_usage_notes") and tool.get_usage_notes():
            lines.append("## Usage Notes")
            lines.append("")
            lines.append(tool.get_usage_notes())
            lines.append("")
        
        # Error Handling
        lines.append("## Error Handling")
        lines.append("")
        lines.append("This tool may return the following errors:")
        lines.append("")
        lines.append("- **ValidationError**: Invalid parameters provided")
        lines.append("- **ExecutionError**: Error during tool execution")
        lines.append("- **TimeoutError**: Operation timed out")
        lines.append("")
        
        # Integration Example
        lines.append("## Integration Example")
        lines.append("")
        lines.append("### Python")
        lines.append("```python")
        lines.append("from tools.registry import ToolRegistry")
        lines.append("")
        lines.append("# Get the tool")
        lines.append("registry = ToolRegistry()")
        lines.append(f'tool = registry.get_tool("{metadata.name}")')
        lines.append("")
        lines.append("# Execute with parameters")
        lines.append("result = tool.execute(")
        
        # Add example parameters
        if metadata.parameters:
            for param in metadata.parameters:
                if param.example is not None:
                    if isinstance(param.example, str):
                        lines.append(f'    {param.name}="{param.example}",')
                    else:
                        lines.append(f'    {param.name}={param.example},')
        
        lines.append(")")
        lines.append("")
        lines.append("# Check result")
        lines.append("if result.success:")
        lines.append("    print(result.output)")
        lines.append("else:")
        lines.append("    print(result.errors)")
        lines.append("```")
        lines.append("")
        
        # AI Integration
        lines.append("### AI Model Integration")
        lines.append("```json")
        lines.append(json.dumps({
            "name": metadata.name,
            "description": metadata.description,
            "parameters": self._generate_ai_parameters(metadata.parameters)
        }, indent=2))
        lines.append("```")
        lines.append("")
        
        # Source Reference
        if include_source:
            lines.append("## Source Reference")
            lines.append("")
            lines.append(f"Implementation: `{tool.__class__.__module__}.{tool.__class__.__name__}`")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        
        return "\n".join(lines)
    
    def _generate_index(self):
        """Generate index page for all tools"""
        lines = []
        
        lines.append("# Tool Documentation")
        lines.append("")
        lines.append("This directory contains documentation for all available tools.")
        lines.append("")
        
        # Overview
        lines.append("## Overview")
        lines.append("")
        
        tools = self.registry.list_tools()
        lines.append(f"Total tools available: **{len(tools)}**")
        lines.append("")
        
        # Categories
        lines.append("## Tools by Category")
        lines.append("")
        
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for tool_info in tools:
            category = tool_info.get("category", "General")
            if category not in categories:
                categories[category] = []
            categories[category].append(tool_info)
        
        for category, category_tools in sorted(categories.items()):
            lines.append(f"### {category}")
            lines.append("")
            
            for tool_info in sorted(category_tools, key=lambda x: x["name"]):
                tool_name = tool_info["name"]
                tool_desc = tool_info.get("description", "No description")
                lines.append(f"- [{tool_name}](./{tool_name}.md) - {tool_desc}")
            
            lines.append("")
        
        # Quick Reference
        lines.append("## Quick Reference")
        lines.append("")
        lines.append("| Tool | Category | Description |")
        lines.append("|------|----------|-------------|")
        
        for tool_info in sorted(tools, key=lambda x: x["name"]):
            name = tool_info["name"]
            category = tool_info.get("category", "General")
            desc = tool_info.get("description", "No description").replace("|", "\\|")
            lines.append(f"| [{name}](./{name}.md) | {category} | {desc} |")
        
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        
        # Write file
        index_path = self.output_dir / "README.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")
    
    def _generate_category_pages(self):
        """Generate documentation pages for each category"""
        categories: Dict[ToolCategory, List[Dict[str, Any]]] = {}
        
        # Group tools by category
        tools = self.registry.list_tools()
        for tool_info in tools:
            # Get actual category enum
            tool = self.registry.get_tool(tool_info["name"])
            if tool and tool.metadata:
                category = tool.metadata.category
                if category not in categories:
                    categories[category] = []
                categories[category].append(tool_info)
        
        # Generate page for each category
        for category, category_tools in categories.items():
            self._generate_category_page(category, category_tools)
    
    def _generate_category_page(
        self,
        category: ToolCategory,
        tools: List[Dict[str, Any]]
    ):
        """Generate documentation page for a category"""
        lines = []
        
        lines.append(f"# {category.value} Tools")
        lines.append("")
        lines.append(f"Tools in the {category.value} category.")
        lines.append("")
        
        lines.append("## Available Tools")
        lines.append("")
        
        for tool_info in sorted(tools, key=lambda x: x["name"]):
            lines.append(f"### [{tool_info['name']}](./{tool_info['name']}.md)")
            lines.append("")
            lines.append(tool_info.get("description", "No description"))
            lines.append("")
            
            # Add quick parameter reference
            tool = self.registry.get_tool(tool_info["name"])
            if tool and tool.metadata and tool.metadata.parameters:
                lines.append("**Parameters:**")
                for param in tool.metadata.parameters:
                    req = " *(required)*" if param.required else ""
                    lines.append(f"- `{param.name}` ({param.type.value}){req}")
                lines.append("")
        
        # Write file
        category_path = self.output_dir / f"category_{category.value.lower()}.md"
        category_path.write_text("\n".join(lines), encoding="utf-8")
    
    def _generate_api_reference(self):
        """Generate API reference documentation"""
        lines = []
        
        lines.append("# API Reference")
        lines.append("")
        lines.append("Complete API reference for all tools.")
        lines.append("")
        
        # Tool schemas
        lines.append("## Tool Schemas")
        lines.append("")
        
        tools = self.registry.list_tools()
        for tool_info in sorted(tools, key=lambda x: x["name"]):
            tool = self.registry.get_tool(tool_info["name"])
            if tool and tool.metadata:
                lines.append(f"### {tool.metadata.name}")
                lines.append("")
                lines.append("```json")
                
                # Generate schema
                schema = self.adapter.formatter.format_tool(tool)
                lines.append(json.dumps(schema, indent=2))
                
                lines.append("```")
                lines.append("")
        
        # Write file
        api_path = self.output_dir / "api_reference.md"
        api_path.write_text("\n".join(lines), encoding="utf-8")
    
    def _generate_integration_guide(self):
        """Generate integration guide"""
        content = """# Tool Integration Guide

This guide explains how to integrate and use tools in your applications.

## Getting Started

### 1. Import Required Modules

```python
from tools.registry import ToolRegistry
from tools.ai_adapter import ToolAIAdapter
```

### 2. Initialize Registry

```python
# Create registry instance
registry = ToolRegistry()

# Discover and load tools
registry.discover_tools()
```

### 3. Get and Use a Tool

```python
# Get a specific tool
tool = registry.get_tool("tool_name")

# Execute with parameters
result = tool.execute(param1="value1", param2="value2")

# Check result
if result.success:
    print(f"Output: {result.output}")
else:
    print(f"Errors: {result.errors}")
```

## AI Model Integration

### Using with AI Models

```python
# Create AI adapter
adapter = ToolAIAdapter(registry=registry)

# Get tool descriptions for AI model
tools = adapter.get_available_tools()

# Execute tool from AI request
ai_request = {
    "name": "tool_name",
    "parameters": {
        "param1": "value1"
    }
}
result = adapter.execute_tool(ai_request)
```

### Prompt Generation

```python
from tools.prompts.prompt_builder import PromptBuilder, PromptContext

# Create prompt builder
builder = PromptBuilder(registry=registry)

# Build context
context = PromptContext(
    task_description="Process some data",
    include_examples=True
)

# Generate prompt
prompt = builder.build_prompt(context)
```

## Best Practices

1. **Validate Parameters**: Always validate parameters before execution
2. **Handle Errors**: Implement proper error handling
3. **Use Caching**: Cache tool results when appropriate
4. **Monitor Performance**: Track execution times
5. **Security**: Sanitize user inputs

## Advanced Usage

### Tool Chaining

```python
# Execute multiple tools in sequence
result1 = registry.get_tool("tool1").execute(data=input_data)
if result1.success:
    result2 = registry.get_tool("tool2").execute(data=result1.output)
```

### Parallel Execution

```python
import asyncio

async def execute_parallel(tools, params):
    tasks = []
    for tool_name, tool_params in zip(tools, params):
        tool = registry.get_tool(tool_name)
        tasks.append(tool.execute_async(**tool_params))
    
    results = await asyncio.gather(*tasks)
    return results
```

## Troubleshooting

### Common Issues

1. **Tool Not Found**: Ensure tools are discovered and loaded
2. **Parameter Validation**: Check parameter types and requirements
3. **Performance Issues**: Consider caching and batch operations

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Tool execution will now show detailed logs
```

---
_For more details, see individual tool documentation._
"""
        
        # Write file
        guide_path = self.output_dir / "integration_guide.md"
        guide_path.write_text(content, encoding="utf-8")
    
    def _format_parameter_type(self, param) -> str:
        """Format parameter type for display"""
        type_str = param.type.value
        
        # Add array item type if specified
        if param.type == ParameterType.ARRAY and hasattr(param, "item_type"):
            type_str = f"array[{param.item_type}]"
        
        return f"`{type_str}`"
    
    def _generate_ai_parameters(self, parameters) -> Dict[str, Any]:
        """Generate AI-friendly parameter schema"""
        if not parameters:
            return {}
        
        schema = {}
        for param in parameters:
            param_schema = {
                "type": param.type.value,
                "description": param.description,
                "required": param.required
            }
            
            if param.default is not None:
                param_schema["default"] = param.default
            if param.enum_values:
                param_schema["enum"] = param.enum_values
            if param.example is not None:
                param_schema["example"] = param.example
            
            schema[param.name] = param_schema
        
        return schema


def generate_tool_documentation(
    tool_name: Optional[str] = None,
    output_dir: str = "docs/tools",
    include_private: bool = False
):
    """
    Convenience function to generate tool documentation
    
    Args:
        tool_name: Specific tool name or None for all tools
        output_dir: Output directory
        include_private: Include private tools
    """
    generator = DocumentationGenerator(output_dir=output_dir)
    
    if tool_name:
        generator.generate_tool_documentation(tool_name)
    else:
        generator.generate_all_documentation(include_private=include_private)