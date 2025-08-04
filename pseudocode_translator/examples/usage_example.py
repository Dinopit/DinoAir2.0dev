"""
Example usage of the Pseudocode Translator with the new model management system

This demonstrates various ways to use the flexible model system
programmatically.
"""

from pseudocode_translator.llm_interface import (
    LLMInterface, create_llm_interface
)
from pseudocode_translator.config import (
    LLMConfig, TranslatorConfig, ConfigManager
)
from pseudocode_translator.models.registry import list_available_models


def example_basic_usage():
    """Basic usage with default configuration"""
    print("=== Basic Usage ===")
    
    # Create interface with default config
    interface = create_llm_interface()
    
    # Translate a simple instruction
    code = interface.translate("create a function that adds two numbers")
    print(f"Generated code:\n{code}\n")
    
    # Clean up
    interface.shutdown()


def example_model_switching():
    """Demonstrate switching between models"""
    print("=== Model Switching ===")
    
    # Create config
    config = LLMConfig(model_type="qwen")
    interface = LLMInterface(config)
    interface.initialize_model()
    
    # List available models
    print(f"Available models: {interface.list_available_models()}")
    
    # Generate with Qwen
    print(f"\nUsing {interface.get_current_model()}:")
    code1 = interface.translate("print hello world")
    print(code1)
    
    # Switch to GPT-2 if available
    if "gpt2" in interface.list_available_models():
        interface.switch_model("gpt2")
        print(f"\nSwitched to {interface.get_current_model()}:")
        code2 = interface.translate("print hello world")
        print(code2)
    
    interface.shutdown()


def example_custom_config():
    """Use custom configuration"""
    print("=== Custom Configuration ===")
    
    # Load config from file
    config = TranslatorConfig.load_from_file(
        "examples/config_multi_model.yaml"
    )
    
    # Modify config programmatically
    config.llm.temperature = 0.1  # Very deterministic
    config.llm.max_tokens = 2048  # Allow longer outputs
    config.llm.model_type = "codegen"  # Use CodeGen model
    
    # Create interface
    interface = LLMInterface(config.llm)
    interface.initialize_model()
    
    # Generate complex code
    instruction = """
    Create a Python class for a binary search tree with methods for:
    - insert
    - search
    - delete
    - in-order traversal
    Include proper error handling and type hints.
    """
    
    code = interface.translate(instruction)
    print(f"Generated BST implementation:\n{code}\n")
    
    interface.shutdown()


def example_batch_processing():
    """Process multiple instructions in batch"""
    print("=== Batch Processing ===")
    
    config = LLMConfig(
        model_type="qwen",
        cache_enabled=True,  # Enable caching for efficiency
        temperature=0.2
    )
    
    interface = LLMInterface(config)
    interface.initialize_model()
    
    instructions = [
        "create a function to calculate factorial",
        "write a function to check if a number is prime",
        "implement bubble sort algorithm",
        "create a function to reverse a string",
        "write a function to find fibonacci numbers"
    ]
    
    results = interface.batch_translate(instructions)
    
    for instruction, code in zip(instructions, results):
        print(f"\nInstruction: {instruction}")
        print(f"Code:\n{code}")
        print("-" * 50)
    
    interface.shutdown()


def example_code_refinement():
    """Demonstrate code refinement capabilities"""
    print("=== Code Refinement ===")
    
    interface = create_llm_interface()
    
    # Initial code with an error
    buggy_code = """
def divide_numbers(a, b):
    return a / b
"""
    
    error_context = "ZeroDivisionError: division by zero when b is 0"
    
    # Refine the code
    fixed_code = interface.refine_code(buggy_code, error_context)
    print(f"Original code:\n{buggy_code}")
    print(f"\nError: {error_context}")
    print(f"\nFixed code:\n{fixed_code}")
    
    interface.shutdown()


def example_context_aware_translation():
    """Translate with context information"""
    print("=== Context-Aware Translation ===")
    
    interface = create_llm_interface()
    
    # Provide context
    context = {
        "previous_code": """
import pandas as pd
import numpy as np

df = pd.read_csv('data.csv')
""",
        "imports": ["pandas", "numpy", "matplotlib.pyplot"],
        "variables": ["df"],
        "style_guide": "Use descriptive variable names and add comments"
    }
    
    instruction = (
        "create a bar chart showing the top 10 values in the 'sales' column"
    )
    
    code = interface.translate(instruction, context)
    print(f"Context-aware code generation:\n{code}")
    
    interface.shutdown()


def example_model_info():
    """Get information about loaded models"""
    print("=== Model Information ===")
    
    interface = create_llm_interface(model_name="qwen")
    
    # Get model info
    info = interface.get_model_info()
    print("Model information:")
    for key, value in info.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")
    
    interface.shutdown()


def example_multi_model_config():
    """Use configuration with multiple models"""
    print("=== Multi-Model Configuration ===")
    
    # Create config with multiple models
    config = TranslatorConfig()
    
    # Configure multiple models
    ConfigManager.add_model_config(
        config,
        model_name="qwen",
        parameters={
            "temperature": 0.3,
            "max_tokens": 1024
        }
    )
    
    ConfigManager.add_model_config(
        config,
        model_name="gpt2",
        parameters={
            "temperature": 0.5,
            "max_tokens": 512,
            "device": "auto"
        },
        auto_download=True
    )
    
    ConfigManager.add_model_config(
        config,
        model_name="codegen",
        parameters={
            "temperature": 0.2,
            "max_tokens": 2048,
            "device": "cuda"
        },
        auto_download=True
    )
    
    # Save configuration
    ConfigManager.save(config, "my_config.yaml")
    print("Configuration saved to my_config.yaml")
    
    # Use the config
    interface = LLMInterface(config.llm)
    interface.initialize_model()
    
    # Try each model
    for model_name in ["qwen", "gpt2", "codegen"]:
        if model_name in list_available_models():
            interface.switch_model(model_name)
            print(f"\nUsing {model_name}:")
            code = interface.translate("print the current date and time")
            print(code[:100] + "..." if len(code) > 100 else code)
    
    interface.shutdown()


def example_advanced_features():
    """Demonstrate advanced features"""
    print("=== Advanced Features ===")
    
    # Create config with advanced settings
    config = LLMConfig(
        model_type="qwen",
        n_gpu_layers=20,  # Use GPU
        cache_enabled=True,
        max_loaded_models=3,
        model_ttl_minutes=120,
        validation_level="lenient"
    )
    
    interface = LLMInterface(config)
    interface.initialize_model()
    
    # Warm up the model for better performance
    interface.warmup()
    print("Model warmed up")
    
    # Generate with custom parameters
    instruction = (
        "implement a recursive merge sort algorithm with detailed comments"
    )
    
    # The interface will use model-specific optimal parameters
    code = interface.translate(instruction)
    print(f"\nGenerated code:\n{code}")
    
    # Check cache hit rate if using multiple times
    for _ in range(3):
        # Same instruction should hit cache
        _ = interface.translate(instruction)
        
    print(f"\nCache info: {interface.cache._cache.__len__()} entries")
    
    interface.shutdown()


if __name__ == "__main__":
    # Run examples
    examples = [
        example_basic_usage,
        example_model_switching,
        example_custom_config,
        example_batch_processing,
        example_code_refinement,
        example_context_aware_translation,
        example_model_info,
        example_multi_model_config,
        example_advanced_features
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "="*60 + "\n")
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            print("\n" + "="*60 + "\n")