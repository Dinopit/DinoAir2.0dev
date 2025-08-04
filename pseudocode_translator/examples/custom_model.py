#!/usr/bin/env python3
"""
Custom Model Example

This example shows how to create and register your own
custom language model for the Pseudocode Translator.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json

from pseudocode_translator.models import BaseModel, register_model, ModelCapabilities
from pseudocode_translator import PseudocodeTranslatorAPI


# Step 1: Create your custom model class
@register_model("my-custom-model")
class MyCustomModel(BaseModel):
    """
    Example custom model implementation
    
    This example shows a simple rule-based translator.
    In practice, you would integrate your actual model here.
    """
    
    @classmethod
    def get_capabilities(cls) -> ModelCapabilities:
        """Define what your model can do"""
        return ModelCapabilities(
            supports_streaming=True,
            supports_batch=True,
            max_context_length=4096,
            supports_gpu=False,  # This example doesn't use GPU
            model_size_mb=1,     # Very small for this example
            description="Simple rule-based pseudocode translator"
        )
    
    def __init__(self, model_path: Path, config: Dict[str, Any]):
        """Initialize your model"""
        super().__init__(model_path, config)
        
        # Load your model here
        # For this example, we'll use simple rules
        self.rules = self._load_rules()
        
        # Store configuration
        self.temperature = config.get('temperature', 0.3)
        self.max_tokens = config.get('max_tokens', 1024)
        
        print(f"Initialized {self.name} model")
    
    def _load_rules(self) -> Dict[str, str]:
        """Load translation rules (simplified for example)"""
        return {
            # Function creation patterns
            r"create a function (?:called |named )?(\w+)": "def {0}():",
            r"that takes? (\w+) as parameter": "def {{FUNC}}({0}):",
            r"(?:that )?returns? (.+)": "    return {0}",
            
            # Class creation patterns  
            r"create a (\w+) class": "class {0}:",
            r"with (\w+) attribute": "    def __init__(self):\n        self.{0} = None",
            
            # Control structures
            r"for each (\w+) in (\w+)": "for {0} in {1}:",
            r"if (.+) is (.+)": "if {0} == {1}:",
            r"while (.+)": "while {0}:",
            
            # Common operations
            r"print (.+)": "print({0})",
            r"add (\w+) to (\w+)": "{1}.append({0})",
            r"remove (\w+) from (\w+)": "{1}.remove({0})",
            r"sort (\w+)": "{0}.sort()",
            
            # Variable operations
            r"set (\w+) to (.+)": "{0} = {1}",
            r"increment (\w+)": "{0} += 1",
            r"decrement (\w+)": "{0} -= 1",
        }
    
    def translate_instruction(self, 
                            instruction: str,
                            context: Optional[Dict[str, Any]] = None) -> str:
        """
        Translate a pseudocode instruction to Python
        
        Args:
            instruction: The pseudocode to translate
            context: Optional context from surrounding code
            
        Returns:
            Generated Python code
        """
        import re
        
        # Start with the original instruction
        code_lines = []
        current_func = None
        
        # Split into lines and process each
        for line in instruction.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            translated = False
            
            # Apply rules
            for pattern, replacement in self.rules.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Extract matched groups
                    groups = match.groups()
                    
                    # Special handling for function definitions
                    if "create a function" in pattern:
                        current_func = groups[0] if groups else "unknown"
                        replacement = replacement.replace("{FUNC}", current_func)
                    
                    # Format replacement with captured groups
                    try:
                        if groups:
                            translated_line = replacement.format(*groups)
                        else:
                            translated_line = replacement
                        
                        # Handle context replacement
                        if "{FUNC}" in translated_line and current_func:
                            translated_line = translated_line.replace(
                                "{FUNC}", current_func
                            )
                        
                        code_lines.append(translated_line)
                        translated = True
                        break
                    except Exception:
                        pass
            
            # If no rule matched, add as comment
            if not translated:
                code_lines.append(f"    # TODO: {line}")
        
        # Join lines and clean up
        code = '\n'.join(code_lines)
        
        # Add imports if needed
        if 'random' in code:
            code = "import random\n\n" + code
        if 'math' in code:
            code = "import math\n\n" + code
        
        return code
    
    def batch_translate(self, instructions: list[str]) -> list[str]:
        """Translate multiple instructions"""
        return [
            self.translate_instruction(inst) 
            for inst in instructions
        ]
    
    def refine_code(self, code: str, error_context: str) -> str:
        """
        Attempt to fix code based on error feedback
        
        This is a simplified example - real implementation would
        use the model to understand and fix the error.
        """
        # Simple fixes based on common errors
        if "IndentationError" in error_context:
            # Fix indentation
            lines = code.split('\n')
            fixed_lines = []
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                if stripped.endswith(':'):
                    fixed_lines.append('    ' * indent_level + stripped)
                    indent_level += 1
                elif stripped in ['pass', 'continue', 'break']:
                    fixed_lines.append('    ' * indent_level + stripped)
                elif stripped.startswith('return'):
                    fixed_lines.append('    ' * indent_level + stripped)
                    indent_level = max(0, indent_level - 1)
                elif stripped:
                    fixed_lines.append('    ' * indent_level + stripped)
                else:
                    fixed_lines.append('')
            
            return '\n'.join(fixed_lines)
        
        # Return original if we can't fix it
        return code
    
    def warmup(self):
        """Warm up the model (not needed for rule-based)"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": self.name,
            "type": "rule-based",
            "rules_count": len(self.rules),
            "capabilities": self.get_capabilities().__dict__,
            "config": {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
        }


# Step 2: Use your custom model
def demo_custom_model():
    """Demonstrate using the custom model"""
    print("=== Custom Model Demo ===\n")
    
    # Create configuration for custom model
    config_path = Path("custom_model_config.json")
    config = {
        "llm": {
            "model_type": "my-custom-model",
            "model_path": "./models",
            "temperature": 0.1,
            "max_tokens": 512
        }
    }
    
    # Save config
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Initialize translator with custom model
    translator = PseudocodeTranslatorAPI(str(config_path))
    
    # Example 1: Simple function
    print("Example 1: Simple Function")
    pseudocode1 = """
    create a function called calculate_area
    that takes radius as parameter
    that returns 3.14159 * radius * radius
    """
    
    result1 = translator.translate(pseudocode1)
    if result1.success:
        print("Generated code:")
        print(result1.code)
    print("\n" + "-" * 50 + "\n")
    
    # Example 2: Class with methods
    print("Example 2: Class Definition")
    pseudocode2 = """
    create a Counter class
    with count attribute
    create a function called increment
    increment count
    create a function called get_count
    return count
    """
    
    result2 = translator.translate(pseudocode2)
    if result2.success:
        print("Generated code:")
        print(result2.code)
    print("\n" + "-" * 50 + "\n")
    
    # Example 3: Control structures
    print("Example 3: Control Structures")
    pseudocode3 = """
    create a function called process_list
    that takes items as parameter
    for each item in items
    if item is valid
    print item
    add item to results
    return results
    """
    
    result3 = translator.translate(pseudocode3)
    if result3.success:
        print("Generated code:")
        print(result3.code)
    
    # Clean up
    config_path.unlink()


# Step 3: Advanced custom model with external integration
class AdvancedCustomModel(BaseModel):
    """
    Advanced example showing integration with external services
    or more sophisticated models
    """
    
    def __init__(self, model_path: Path, config: Dict[str, Any]):
        super().__init__(model_path, config)
        
        # Example: Load a trained model
        # self.model = self._load_neural_model(model_path)
        
        # Example: Connect to API
        # self.api_key = config.get('api_key')
        # self.api_endpoint = config.get('endpoint')
        
    def translate_instruction(self, 
                            instruction: str,
                            context: Optional[Dict[str, Any]] = None) -> str:
        """
        Advanced translation using neural model or API
        """
        # Example: Use neural model
        # tokens = self.tokenizer.encode(instruction)
        # output = self.model.generate(tokens, context=context)
        # return self.tokenizer.decode(output)
        
        # Example: Use external API
        # response = requests.post(
        #     self.api_endpoint,
        #     json={
        #         "instruction": instruction,
        #         "context": context,
        #         "model": self.name
        #     },
        #     headers={"Authorization": f"Bearer {self.api_key}"}
        # )
        # return response.json()["code"]
        
        # For demo, return placeholder
        return f"# Advanced translation of: {instruction}"


def main():
    """Run the custom model demonstration"""
    print("Pseudocode Translator - Custom Model Example")
    print("=" * 60)
    print()
    
    # Run the demo
    demo_custom_model()
    
    print("\n" + "=" * 60)
    print("\nCustom Model Integration Complete!")
    print("\nTo use your custom model:")
    print("1. Create a class inheriting from BaseModel")
    print("2. Implement required methods")
    print("3. Register with @register_model decorator")
    print("4. Configure translator to use your model")
    print("\nSee the code above for detailed implementation.")


if __name__ == "__main__":
    main()