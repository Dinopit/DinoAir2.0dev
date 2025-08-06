"""
Prompt Engineering Demonstrations

This module demonstrates how to use the prompt engineering system
to create effective prompts for AI models using tools.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from tools.registry import ToolRegistry
from tools.ai_adapter import ToolAIAdapter
from tools.prompts.prompt_builder import (
    PromptBuilder, PromptContext, AdaptivePromptBuilder,
    create_prompt_for_task, create_adaptive_prompt,
    ModelCapability, PromptStyle
)
from tools.prompts.prompt_templates import (
    PromptTemplateFactory, CompositePromptTemplate
)
from tools.prompts.documentation import DocumentationGenerator


def demo_basic_prompt_generation():
    """Demonstrate basic prompt generation"""
    print("=== Basic Prompt Generation Demo ===\n")
    
    # Initialize components
    registry = ToolRegistry()
    builder = PromptBuilder(registry=registry)
    
    # Create context
    context = PromptContext(
        task_description="Process a CSV file and calculate statistics",
        style_preference=PromptStyle.DETAILED,
        include_examples=True
    )
    
    # Generate prompt
    prompt = builder.build_prompt(context)
    print("Generated Prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    print()


def demo_tool_specific_prompt():
    """Demonstrate tool-specific prompt generation"""
    print("=== Tool-Specific Prompt Demo ===\n")
    
    registry = ToolRegistry()
    adapter = ToolAIAdapter(registry=registry)
    
    # Assume we have a file_tool registered
    tool_name = "file_tool"
    
    try:
        # Create detailed prompt for specific tool
        prompt = adapter.create_tool_prompt(
            tool_name=tool_name,
            include_examples=True
        )
        print(f"Prompt for {tool_name}:")
        print("-" * 50)
        print(prompt)
        print("-" * 50)
    except Exception as e:
        print(f"Note: {e}")
        print("This demo requires the file_tool to be registered.")
    print()


def demo_few_shot_examples():
    """Demonstrate few-shot example generation"""
    print("=== Few-Shot Examples Demo ===\n")
    
    registry = ToolRegistry()
    adapter = ToolAIAdapter(registry=registry)
    
    # Generate few-shot examples
    examples = adapter.generate_few_shot_examples(
        num_examples=3,
        include_errors=True
    )
    
    print("Few-Shot Examples:")
    print("-" * 50)
    print(examples)
    print("-" * 50)
    print()


def demo_tool_selection_prompt():
    """Demonstrate tool selection prompt generation"""
    print("=== Tool Selection Prompt Demo ===\n")
    
    registry = ToolRegistry()
    adapter = ToolAIAdapter(registry=registry)
    
    # Task requiring tool selection
    task = "I need to read a JSON file, extract specific fields, and save the results"
    
    # Generate selection prompt
    prompt = adapter.generate_tool_selection_prompt(
        task_description=task,
        constraints={"performance_critical": True}
    )
    
    print("Tool Selection Prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    print()


def demo_error_recovery_prompt():
    """Demonstrate error recovery prompt generation"""
    print("=== Error Recovery Prompt Demo ===\n")
    
    registry = ToolRegistry()
    adapter = ToolAIAdapter(registry=registry)
    
    # Simulate an error
    error_prompt = adapter.generate_error_recovery_prompt(
        error_type="ValidationError",
        error_message="Parameter 'file_path' is required but not provided",
        tool_name="file_reader",
        context={"attempted_params": {"content": "test"}}
    )
    
    print("Error Recovery Prompt:")
    print("-" * 50)
    print(error_prompt)
    print("-" * 50)
    print()


def demo_adaptive_prompting():
    """Demonstrate adaptive prompt generation"""
    print("=== Adaptive Prompting Demo ===\n")
    
    # Simulate feedback history
    feedback_history = [
        {"success": True, "prompt_style": "detailed"},
        {"success": False, "prompt_style": "concise"},
        {"success": True, "prompt_style": "examples"},
        {"success": True, "prompt_style": "examples"},
    ]
    
    # Create adaptive prompt
    prompt = create_adaptive_prompt(
        task="Parse and validate configuration files",
        feedback_history=feedback_history
    )
    
    print("Adaptive Prompt (based on feedback):")
    print("-" * 50)
    print(prompt)
    print("-" * 50)
    print()


def demo_different_prompt_styles():
    """Demonstrate different prompt styles"""
    print("=== Different Prompt Styles Demo ===\n")
    
    task = "Convert temperature from Celsius to Fahrenheit"
    
    styles = [
        PromptStyle.DETAILED,
        PromptStyle.CONCISE,
        PromptStyle.FEW_SHOT,
        PromptStyle.STRUCTURED,
        PromptStyle.CONVERSATIONAL
    ]
    
    for style in styles:
        print(f"\n--- {style.value.upper()} Style ---")
        prompt = create_prompt_for_task(
            task=task,
            style=style,
            model_capabilities={ModelCapability.BASIC}
        )
        print(prompt[:300] + "..." if len(prompt) > 300 else prompt)


def demo_model_capability_adaptation():
    """Demonstrate adaptation based on model capabilities"""
    print("=== Model Capability Adaptation Demo ===\n")
    
    task = "Analyze log files and identify errors"
    
    # Basic model
    print("--- Basic Model ---")
    basic_prompt = create_prompt_for_task(
        task=task,
        model_capabilities={ModelCapability.BASIC}
    )
    print(basic_prompt[:200] + "...")
    
    # Advanced model with function calling
    print("\n--- Advanced Model with Function Calling ---")
    advanced_prompt = create_prompt_for_task(
        task=task,
        model_capabilities={
            ModelCapability.ADVANCED,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.LONG_CONTEXT
        }
    )
    print(advanced_prompt[:200] + "...")


def demo_composite_prompts():
    """Demonstrate composite prompt templates"""
    print("=== Composite Prompt Templates Demo ===\n")
    
    # Create composite template
    composite = CompositePromptTemplate(name="multi_tool_workflow")
    
    # Add different template types
    composite.add_template(
        PromptTemplateFactory.create("tool_description")
    )
    composite.add_template(
        PromptTemplateFactory.create("usage_example")
    )
    composite.add_template(
        PromptTemplateFactory.create("error_handling")
    )
    
    # Prepare variables
    variables = {
        "tool_name": "data_processor",
        "description": "Process and transform data",
        "category": "Data",
        "purpose": "Transform data between formats",
        "parameters": "- input_data: The data to process\n- format: Output format",
        "returns": "Processed data in specified format",
        "guidelines": "Validate input data before processing",
        "examples": "See examples below",
        "error_handling": "Handle format errors gracefully",
        "parameters_json": '{"input_data": "any", "format": "string"}',
        "output_json": '{"result": "processed_data"}',
        "parameters_python": 'input_data=data, format="json"',
        "output_description": "Transformed data",
        "parameters_natural": "input data and output format",
        "error_list": "- Invalid format\n- Corrupted data",
        "recovery_strategies": "1. Validate format\n2. Try alternative parser"
    }
    
    # Render composite
    result = composite.render(**variables)
    print("Composite Prompt:")
    print("-" * 50)
    print(result)
    print("-" * 50)
    print()


def demo_prompt_builder_types():
    """Demonstrate different prompt builder types"""
    print("=== Different Prompt Types Demo ===\n")
    
    registry = ToolRegistry()
    builder = PromptBuilder(registry=registry)
    
    context = PromptContext(
        task_description="Manage files and directories",
        include_examples=True
    )
    
    prompt_types = [
        "comprehensive",
        "tool_selection", 
        "few_shot",
        "minimal",
        "tutorial",
        "reference"
    ]
    
    for prompt_type in prompt_types:
        print(f"\n--- {prompt_type.upper()} Prompt ---")
        try:
            prompt = builder.build_prompt(context, prompt_type=prompt_type)
            # Show first 200 chars
            print(prompt[:200] + "..." if len(prompt) > 200 else prompt)
        except Exception as e:
            print(f"Error: {e}")


def demo_documentation_generation():
    """Demonstrate documentation generation"""
    print("=== Documentation Generation Demo ===\n")
    
    registry = ToolRegistry()
    doc_gen = DocumentationGenerator(
        registry=registry,
        output_dir="docs/demo"
    )
    
    print("Documentation generator can create:")
    print("- Individual tool documentation")
    print("- Category documentation")
    print("- API reference")
    print("- Integration guides")
    print("\nExample command:")
    print("doc_gen.generate_all_documentation()")
    print()


def demo_real_world_scenario():
    """Demonstrate a real-world scenario"""
    print("=== Real-World Scenario Demo ===\n")
    print("Scenario: Building a data processing pipeline\n")
    
    registry = ToolRegistry()
    builder = PromptBuilder(registry=registry)
    
    # Step 1: Initial task prompt
    context1 = PromptContext(
        task_description=(
            "I need to build a data processing pipeline that:\n"
            "1. Reads CSV files from a directory\n"
            "2. Validates the data format\n"
            "3. Transforms the data\n"
            "4. Saves results to a database"
        ),
        model_capabilities={
            ModelCapability.ADVANCED,
            ModelCapability.FUNCTION_CALLING
        },
        style_preference=PromptStyle.DETAILED
    )
    
    prompt1 = builder.build_prompt(context1, prompt_type="tool_selection")
    print("Step 1 - Tool Selection:")
    print(prompt1[:300] + "...\n")
    
    # Step 2: Error handling
    adapter = ToolAIAdapter(registry=registry)
    error_prompt = adapter.generate_error_recovery_prompt(
        error_type="ValidationError",
        error_message="CSV format invalid: missing required columns",
        tool_name="csv_reader",
        context={"file": "data.csv", "missing_columns": ["id", "timestamp"]}
    )
    
    print("Step 2 - Error Recovery:")
    print(error_prompt[:300] + "...\n")
    
    # Step 3: Few-shot examples for transformation
    transform_examples = adapter.generate_few_shot_examples(
        num_examples=2,
        include_errors=False
    )
    
    print("Step 3 - Transformation Examples:")
    print(transform_examples[:300] + "...")


def run_all_demos():
    """Run all demonstration functions"""
    demos = [
        demo_basic_prompt_generation,
        demo_tool_specific_prompt,
        demo_few_shot_examples,
        demo_tool_selection_prompt,
        demo_error_recovery_prompt,
        demo_adaptive_prompting,
        demo_different_prompt_styles,
        demo_model_capability_adaptation,
        demo_composite_prompts,
        demo_prompt_builder_types,
        demo_documentation_generation,
        demo_real_world_scenario
    ]
    
    for demo in demos:
        try:
            demo()
            print("\n" + "=" * 60 + "\n")
        except Exception as e:
            print(f"Error in {demo.__name__}: {e}")
            print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    print("Tool Prompt Engineering Demonstrations")
    print("=====================================\n")
    
    # Check if specific demo requested
    if len(sys.argv) > 1:
        demo_name = sys.argv[1]
        if demo_name in globals():
            globals()[demo_name]()
        else:
            print(f"Demo '{demo_name}' not found.")
            print("\nAvailable demos:")
            for name, obj in globals().items():
                if name.startswith("demo_") and callable(obj):
                    print(f"  - {name}")
    else:
        # Run all demos
        run_all_demos()
        
        print("\nTo run a specific demo, use:")
        print("  python prompt_demo.py demo_name")
        print("\nAvailable demos:")
        for name, obj in globals().items():
            if name.startswith("demo_") and callable(obj):
                print(f"  - {name}")