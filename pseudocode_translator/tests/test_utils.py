"""
Test utilities and mock helpers for pseudocode_translator tests
"""

from unittest.mock import Mock, MagicMock
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import ast


# Mock LLM Model

class MockLLM:
    """Mock LLM model for testing without requiring actual model"""
    
    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock LLM with optional predefined responses
        
        Args:
            responses: Dictionary mapping instructions to responses
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
        self.default_response = 'def generated_function():\n    return "default"'
    
    def __call__(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Simulate LLM model call"""
        self.call_count += 1
        self.last_prompt = prompt
        
        # Look for matching response
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return {
                    'choices': [{
                        'text': response,
                        'finish_reason': 'stop'
                    }],
                    'usage': {
                        'prompt_tokens': len(prompt.split()),
                        'completion_tokens': len(response.split()),
                        'total_tokens': len(prompt.split()) + len(response.split())
                    }
                }
        
        # Return default response
        return {
            'choices': [{
                'text': self.default_response,
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': len(prompt.split()),
                'completion_tokens': len(self.default_response.split()),
                'total_tokens': len(prompt.split()) + len(self.default_response.split())
            }
        }
    
    def set_response(self, key: str, response: str):
        """Set a specific response for a key"""
        self.responses[key] = response
    
    def reset(self):
        """Reset the mock state"""
        self.call_count = 0
        self.last_prompt = None


# Mock Configuration Builders

def create_mock_llm_config(**overrides):
    """Create a mock LLM configuration with optional overrides"""
    config = Mock()
    
    defaults = {
        'model_type': 'qwen-7b',
        'model_name': 'qwen-7b-q4_k_m.gguf',
        'models_dir': './models',
        'n_ctx': 2048,
        'n_batch': 512,
        'n_threads': 4,
        'n_gpu_layers': 0,
        'max_tokens': 1024,
        'temperature': 0.7,
        'top_p': 0.95,
        'top_k': 40,
        'repeat_penalty': 1.1,
        'cache_enabled': True,
        'cache_ttl_hours': 24,
        'validation_level': 'normal'
    }
    
    # Apply overrides
    for key, value in defaults.items():
        setattr(config, key, overrides.get(key, value))
    
    # Add methods
    config.validate = Mock(return_value=[])
    config.get_model_path = Mock(
        return_value=Path(f"{config.models_dir}/{config.model_type}/model.gguf")
    )
    
    return config


def create_mock_translator_config(**overrides):
    """Create a mock translator configuration with optional overrides"""
    config = Mock()
    
    # Create LLM config
    llm_overrides = overrides.pop('llm', {})
    config.llm = create_mock_llm_config(**llm_overrides)
    
    # Set defaults
    defaults = {
        'validate_imports': True,
        'check_undefined_vars': True,
        'allow_unsafe_operations': False,
        'max_line_length': 79,
        'preserve_comments': True,
        'organize_imports': True,
        'add_type_hints': False,
        'code_style': 'pep8'
    }
    
    # Apply overrides
    for key, value in defaults.items():
        setattr(config, key, overrides.get(key, value))
    
    return config


# Mock Assembler

class MockCodeAssembler:
    """Mock code assembler for testing"""
    
    def __init__(self, config=None):
        self.config = config or Mock()
        self.assembled_count = 0
    
    def assemble(self, blocks: List[Any]) -> str:
        """Mock assembly of code blocks"""
        self.assembled_count += 1
        
        if not blocks:
            return ""
        
        # Simple assembly: join all block contents
        lines = []
        for block in blocks:
            if hasattr(block, 'content'):
                lines.append(block.content)
        
        return '\n\n'.join(lines)
    
    def organize_imports(self, code: str) -> str:
        """Mock import organization"""
        lines = code.split('\n')
        imports = []
        other = []
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                imports.append(line)
            else:
                other.append(line)
        
        # Sort imports
        imports.sort()
        
        return '\n'.join(imports + [''] + other) if imports else code


# Test Data Generators

def generate_code_block(block_type='PYTHON', content='pass', line_start=1):
    """Generate a test code block"""
    from pseudocode_translator.models import CodeBlock, BlockType
    
    line_count = content.count('\n') + 1
    return CodeBlock(
        type=BlockType[block_type],
        content=content,
        line_numbers=(line_start, line_start + line_count - 1),
        metadata={}
    )


def generate_parse_result(blocks=None, errors=None, warnings=None):
    """Generate a test parse result"""
    from pseudocode_translator.models import ParseResult
    
    if blocks is None:
        blocks = [generate_code_block()]
    
    return ParseResult(
        blocks=blocks,
        errors=errors or [],
        warnings=warnings or []
    )


def generate_validation_result(is_valid=True, errors=None, warnings=None):
    """Generate a test validation result"""
    result = Mock()
    result.is_valid = is_valid
    result.errors = errors or []
    result.warnings = warnings or []
    result.line_numbers = []
    result.suggestions = []
    return result


# Test Data Examples

SAMPLE_PSEUDOCODE = {
    'simple': "Create a function that prints hello world",
    
    'with_params': "Create a function called greet that takes name as parameter and prints Hello, name!",
    
    'complex': """Create a Calculator class with methods:
- add(a, b) - returns sum
- subtract(a, b) - returns difference
- multiply(a, b) - returns product
- divide(a, b) - returns quotient (handle division by zero)""",
    
    'mixed': """import math

Create function to calculate circle area

def rectangle_area(length, width):
    return length * width

Now create a main function that asks for shape type"""
}


SAMPLE_PYTHON_CODE = {
    'hello_world': 'def hello():\n    print("Hello, World!")',
    
    'greet': '''def greet(name):
    print(f"Hello, {name}!")''',
    
    'calculator': '''class Calculator:
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
    
    def multiply(self, a, b):
        return a * b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b''',
    
    'invalid_syntax': 'def broken(\n    print("missing closing paren"'
}


# Validation Helpers

def is_valid_python(code: str) -> Tuple[bool, Optional[str]]:
    """Check if code is valid Python syntax"""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def extract_functions(code: str) -> List[str]:
    """Extract function names from code"""
    try:
        tree = ast.parse(code)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    except:
        return []


def extract_classes(code: str) -> List[str]:
    """Extract class names from code"""
    try:
        tree = ast.parse(code)
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    except:
        return []


def extract_imports(code: str) -> List[str]:
    """Extract import statements from code"""
    try:
        tree = ast.parse(code)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        return imports
    except:
        return []


# Response Builders

def build_llm_response(text: str, tokens_used: int = 100) -> Dict[str, Any]:
    """Build a mock LLM response"""
    return {
        'choices': [{
            'text': text,
            'finish_reason': 'stop',
            'index': 0
        }],
        'usage': {
            'prompt_tokens': tokens_used // 2,
            'completion_tokens': tokens_used // 2,
            'total_tokens': tokens_used
        },
        'model': 'mock-model',
        'created': 1234567890
    }


def build_translation_result(success=True, code=None, errors=None, warnings=None):
    """Build a mock translation result"""
    result = Mock()
    result.success = success
    result.code = code or ""
    result.errors = errors or []
    result.warnings = warnings or []
    result.metadata = {
        'duration_ms': 100,
        'blocks_processed': 1,
        'blocks_translated': 1 if success else 0,
        'cache_hits': 0,
        'model_tokens_used': 100,
        'validation_passed': success
    }
    result.has_errors = len(result.errors) > 0
    result.has_warnings = len(result.warnings) > 0
    return result


# File System Mocks

class MockFileSystem:
    """Mock file system for testing"""
    
    def __init__(self):
        self.files = {}
    
    def add_file(self, path: str, content: str):
        """Add a file to the mock file system"""
        self.files[path] = content
    
    def read_file(self, path: str) -> str:
        """Read a file from the mock file system"""
        if path not in self.files:
            raise FileNotFoundError(f"Mock file not found: {path}")
        return self.files[path]
    
    def exists(self, path: str) -> bool:
        """Check if a file exists"""
        return path in self.files
    
    def list_files(self) -> List[str]:
        """List all files in the mock file system"""
        return list(self.files.keys())


# Assertion Helpers

def assert_valid_python(code: str, message: str = "Generated code is not valid Python"):
    """Assert that code is valid Python"""
    valid, error = is_valid_python(code)
    if not valid:
        raise AssertionError(f"{message}: {error}")


def assert_contains_function(code: str, function_name: str):
    """Assert that code contains a specific function"""
    functions = extract_functions(code)
    if function_name not in functions:
        raise AssertionError(
            f"Function '{function_name}' not found. "
            f"Found functions: {functions}"
        )


def assert_contains_class(code: str, class_name: str):
    """Assert that code contains a specific class"""
    classes = extract_classes(code)
    if class_name not in classes:
        raise AssertionError(
            f"Class '{class_name}' not found. "
            f"Found classes: {classes}"
        )


def assert_no_syntax_errors(result):
    """Assert that a result has no syntax errors"""
    syntax_errors = [e for e in result.errors if 'syntax' in e.lower()]
    if syntax_errors:
        raise AssertionError(f"Syntax errors found: {syntax_errors}")


# Performance Testing Helpers

def time_function(func, *args, **kwargs):
    """Time a function execution"""
    import time
    start = time.time()
    result = func(*args, **kwargs)
    duration = time.time() - start
    return result, duration


def generate_large_pseudocode(lines: int = 1000) -> str:
    """Generate large pseudocode for performance testing"""
    code_lines = []
    for i in range(lines):
        if i % 50 == 0:
            code_lines.append(f"# Section {i // 50}")
        if i % 10 == 0:
            code_lines.append(f"Create function func_{i} that returns {i}")
        elif i % 5 == 0:
            code_lines.append(f"x_{i} = {i} * 2")
        else:
            code_lines.append(f"# Process item {i}")
    return '\n'.join(code_lines)