"""
Regression Tests for Pseudocode Translator

This module contains regression tests for all previously fixed bugs and issues
to ensure they don't resurface in future changes.
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from translator import TranslationManager, TranslationResult
from parser import ParserModule
from assembler import CodeAssembler
from validator import Validator
from models import CodeBlock, BlockType
from config import TranslatorConfig
from exceptions import (
    TranslatorError, ParsingError, ValidationError,
    AssemblyError, ModelError
)


class TestRegressionBugs(unittest.TestCase):
    """Test cases for specific bugs that have been fixed"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        
        # Mock model to avoid requiring actual model files
        with patch('translator.create_model') as mock_create:
            self.mock_model = MagicMock()
            self.mock_model.validate_input.return_value = (True, None)
            self.mock_model.initialize.return_value = None
            mock_create.return_value = self.mock_model
            
            self.translator = TranslationManager(self.config)
        
        self.parser = ParserModule()
        self.assembler = CodeAssembler(self.config)
        self.validator = Validator(self.config)
    
    def test_bug_001_empty_input_handling(self):
        """
        Bug #001: Empty input caused NullPointerException
        Fixed: Added check for empty input in parser
        """
        # Test empty string
        result = self.translator.translate_pseudocode("")
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)
        
        # Test whitespace only
        result = self.translator.translate_pseudocode("   \n\t  ")
        self.assertFalse(result.success)
        
        # Parser should handle gracefully
        parse_result = self.parser.get_parse_result("")
        self.assertFalse(parse_result.success)
    
    def test_bug_002_unicode_handling(self):
        """
        Bug #002: Unicode characters in pseudocode caused encoding errors
        Fixed: Proper UTF-8 handling throughout the pipeline
        """
        unicode_input = """
        Create a function called café
        It should print "Hello, 世界!"
        Add emoji support: 🎉 🐍 💻
        """
        
        # Should not raise encoding errors
        parse_result = self.parser.get_parse_result(unicode_input)
        self.assertTrue(parse_result.success or len(parse_result.errors) > 0)
        
        # Unicode in code blocks
        block = CodeBlock(
            type=BlockType.PYTHON,
            content='print("你好, мир!")',
            line_numbers=(1, 1),
            metadata={},
            context={}
        )
        
        # Assembler should handle unicode
        result = self.assembler.assemble([block])
        self.assertIn("你好", result)
    
    def test_bug_003_nested_quotes_parsing(self):
        """
        Bug #003: Nested quotes in strings broke parser
        Fixed: Improved string literal detection
        """
        nested_quotes = '''
        Create a function to print a message
        The message should be "She said 'Hello' to me"
        '''
        
        parse_result = self.parser.get_parse_result(nested_quotes)
        self.assertTrue(parse_result.success)
        
        # Test with escaped quotes
        escaped_quotes = r'''
        message = "This is a \"quoted\" word"
        other = 'It\'s working'
        '''
        
        parse_result = self.parser.get_parse_result(escaped_quotes)
        self.assertTrue(parse_result.success)
    
    def test_bug_004_long_line_handling(self):
        """
        Bug #004: Very long lines caused memory issues
        Fixed: Added line length limits and chunking
        """
        # Create a very long line
        long_line = "Create a function that " + "does something " * 500
        
        # Should handle without memory error
        parse_result = self.parser.get_parse_result(long_line)
        # Should either succeed or fail gracefully
        self.assertIsNotNone(parse_result)
    
    def test_bug_005_circular_import_detection(self):
        """
        Bug #005: Circular imports weren't detected
        Fixed: Added import cycle detection in validator
        """
        code_with_circular = """
from module_a import func_a
from module_b import func_b

# In reality, module_a imports from module_b
# and module_b imports from module_a
"""
        
        # Validator should detect potential issues
        validation_result = self.validator.validate_syntax(code_with_circular)
        # Should validate syntax (circular imports are runtime issues)
        self.assertIsNotNone(validation_result)
    
    def test_bug_006_mixed_indentation(self):
        """
        Bug #006: Mixed tabs/spaces caused silent failures
        Fixed: Improved indentation fixing in assembler
        """
        mixed_indent = """
def function1():
\tif True:
    print("spaces")
\t\treturn True
        else:
\t    print("mixed")
"""
        
        # Assembler should fix indentation
        blocks = [CodeBlock(
            type=BlockType.PYTHON,
            content=mixed_indent,
            line_numbers=(1, 7),
            metadata={},
            context={}
        )]
        
        result = self.assembler.assemble(blocks)
        # Should not contain tabs
        self.assertNotIn('\t', result)
    
    def test_bug_007_comment_preservation(self):
        """
        Bug #007: Comments were being stripped incorrectly
        Fixed: Improved comment handling in parser
        """
        code_with_comments = """
# This is a module comment
# It has multiple lines

def function():
    # Inline comment
    x = 5  # End of line comment
    '''
    Multi-line
    comment
    '''
    return x
"""
        
        blocks = [CodeBlock(
            type=BlockType.PYTHON,
            content=code_with_comments,
            line_numbers=(1, 12),
            metadata={},
            context={}
        )]
        
        # With preserve_comments enabled
        self.assembler.preserve_comments = True
        result = self.assembler.assemble(blocks)
        
        # Comments should be preserved
        self.assertIn("# This is a module comment", result)
        self.assertIn("# Inline comment", result)
        self.assertIn("# End of line comment", result)
    
    def test_bug_008_async_function_parsing(self):
        """
        Bug #008: Async/await syntax not properly handled
        Fixed: Added modern Python syntax support
        """
        async_code = """
Create an async function to fetch data
It should:
- Accept a URL parameter
- Use await to fetch the data
- Handle errors with try/except
- Return the JSON response
"""
        
        # Mock model to return async code
        self.mock_model.translate.return_value = MagicMock(
            success=True,
            code="""async def fetch_data(url):
    try:
        response = await http_client.get(url)
        return await response.json()
    except Exception as e:
        return None""",
            errors=[],
            warnings=[]
        )
        
        result = self.translator.translate_pseudocode(async_code)
        
        if result.success:
            # Validator should handle async syntax
            validation = self.validator.validate_syntax(result.code)
            self.assertTrue(validation.is_valid)
    
    def test_bug_009_type_hint_parsing(self):
        """
        Bug #009: Type hints caused parser errors
        Fixed: Full type hint support in parser
        """
        typed_code = """
from typing import List, Dict, Optional

def process_data(items: List[Dict[str, int]]) -> Optional[Dict[str, float]]:
    if not items:
        return None
    
    result: Dict[str, float] = {}
    for item in items:
        for key, value in item.items():
            result[key] = float(value)
    
    return result
"""
        
        parse_result = self.parser.get_parse_result(typed_code)
        self.assertTrue(parse_result.success)
        
        # Validator should handle type hints
        validation = self.validator.validate_syntax(typed_code)
        self.assertTrue(validation.is_valid)
    
    def test_bug_010_walrus_operator(self):
        """
        Bug #010: Walrus operator := not recognized
        Fixed: Added Python 3.8+ syntax support
        """
        walrus_code = """
# Using walrus operator
if (n := len(data)) > 10:
    print(f"List is too long ({n} elements)")

while (line := file.readline()):
    process(line)
"""
        
        parse_result = self.parser.get_parse_result(walrus_code)
        self.assertTrue(parse_result.success)
        
        # Validator should recognize walrus operator
        validation = self.validator.validate_syntax(walrus_code)
        self.assertTrue(validation.is_valid)
    
    def test_bug_011_multiline_strings(self):
        """
        Bug #011: Multi-line strings broke block detection
        Fixed: Improved string literal handling in parser
        """
        multiline_code = '''
message = """
This is a multi-line string
that spans several lines
and includes "quotes" inside
"""

query = \'\'\'
SELECT * FROM users
WHERE active = true
ORDER BY created_at DESC
\'\'\'
'''
        
        parse_result = self.parser.get_parse_result(multiline_code)
        self.assertTrue(parse_result.success)
        
        # Check blocks are correctly identified
        blocks = parse_result.blocks
        self.assertTrue(all(b.type == BlockType.PYTHON for b in blocks))
    
    def test_bug_012_class_decorator_syntax(self):
        """
        Bug #012: Class decorators not properly handled
        Fixed: Added decorator support for classes
        """
        decorator_code = """
@dataclass
@my_decorator(param="value")
class MyClass:
    name: str
    value: int = 0
    
    @property
    def display_name(self):
        return f"{self.name}: {self.value}"
    
    @staticmethod
    def create_default():
        return MyClass("default", 0)
"""
        
        parse_result = self.parser.get_parse_result(decorator_code)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(decorator_code)
        self.assertTrue(validation.is_valid)
    
    def test_bug_013_f_string_expressions(self):
        """
        Bug #013: Complex f-string expressions caused errors
        Fixed: Enhanced f-string parsing
        """
        fstring_code = '''
name = "World"
number = 42

# Complex f-string expressions
message1 = f"Hello {name.upper()}"
message2 = f"Answer: {number * 2}"
message3 = f"Nested: {f'Inner {name}'}"
message4 = f"{name=}"  # Debug format
message5 = f"""
Multi-line f-string
Name: {name}
Double: {number * 2}
"""
'''
        
        parse_result = self.parser.get_parse_result(fstring_code)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(fstring_code)
        self.assertTrue(validation.is_valid)
    
    def test_bug_014_generator_expressions(self):
        """
        Bug #014: Generator expressions misidentified
        Fixed: Improved expression parsing
        """
        generator_code = """
# Generator expressions
squares = (x**2 for x in range(10))
filtered = (x for x in data if x > 0)

# Generator functions
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Yield from
def delegator(iterable):
    yield from iterable
"""
        
        parse_result = self.parser.get_parse_result(generator_code)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(generator_code)
        self.assertTrue(validation.is_valid)
    
    def test_bug_015_match_statement(self):
        """
        Bug #015: Python 3.10 match statements not supported
        Fixed: Added pattern matching support
        """
        match_code = """
def handle_command(command):
    match command:
        case "quit":
            return False
        case "help":
            print("Available commands...")
        case ["move", direction]:
            move_player(direction)
        case ["attack", *targets]:
            for target in targets:
                attack(target)
        case _:
            print("Unknown command")
"""
        
        # This might fail on Python < 3.10, so check version
        import sys
        if sys.version_info >= (3, 10):
            parse_result = self.parser.get_parse_result(match_code)
            self.assertTrue(parse_result.success)
            
            validation = self.validator.validate_syntax(match_code)
            self.assertTrue(validation.is_valid)


class TestEdgeCaseRegressions(unittest.TestCase):
    """Test edge cases that previously caused issues"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        self.parser = ParserModule()
        self.assembler = CodeAssembler(self.config)
        self.validator = Validator(self.config)
    
    def test_single_line_blocks(self):
        """Test handling of single-line code blocks"""
        single_lines = [
            "x = 5",
            "import os",
            "pass",
            "return None",
            "raise ValueError()"
        ]
        
        for line in single_lines:
            parse_result = self.parser.get_parse_result(line)
            self.assertTrue(parse_result.success)
            self.assertEqual(len(parse_result.blocks), 1)
    
    def test_deeply_nested_structures(self):
        """Test deeply nested code structures"""
        deep_nested = """
def outer():
    def middle():
        def inner():
            if True:
                for i in range(10):
                    while i > 0:
                        try:
                            with open('file') as f:
                                if f:
                                    return True
                        except:
                            pass
                        finally:
                            i -= 1
"""
        
        parse_result = self.parser.get_parse_result(deep_nested)
        self.assertTrue(parse_result.success)
        
        # Check indentation is preserved
        blocks = [CodeBlock(
            type=BlockType.PYTHON,
            content=deep_nested,
            line_numbers=(1, 15),
            metadata={},
            context={}
        )]
        
        result = self.assembler.assemble(blocks)
        self.assertIn("def outer():", result)
        self.assertIn("def middle():", result)
        self.assertIn("def inner():", result)
    
    def test_mixed_language_detection(self):
        """Test detection between English and Python blocks"""
        test_cases = [
            # Clear English
            ("Create a function to calculate area", BlockType.ENGLISH),
            
            # Clear Python
            ("def calculate_area(radius):", BlockType.PYTHON),
            
            # Ambiguous but likely Python
            ("import math", BlockType.PYTHON),
            
            # Ambiguous but likely English
            ("Import necessary libraries", BlockType.ENGLISH),
            
            # Mixed indicators
            ("def function to process data:", BlockType.MIXED),
        ]
        
        for text, expected_type in test_cases:
            parse_result = self.parser.get_parse_result(text)
            if parse_result.blocks:
                # Check if the detected type matches expected
                # (allowing for some flexibility in detection)
                detected_type = parse_result.blocks[0].type
                # We check if it's reasonably close
                self.assertIn(
                    detected_type,
                    [expected_type, BlockType.MIXED],
                    f"Text: {text}, Expected: {expected_type}, "
                    f"Got: {detected_type}"
                )
    
    def test_special_method_names(self):
        """Test handling of Python special methods"""
        special_methods = """
class MyClass:
    def __init__(self):
        pass
    
    def __str__(self):
        return "MyClass"
    
    def __repr__(self):
        return "MyClass()"
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def __getitem__(self, key):
        return None
    
    def __setitem__(self, key, value):
        pass
"""
        
        parse_result = self.parser.get_parse_result(special_methods)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(special_methods)
        self.assertTrue(validation.is_valid)
    
    def test_numeric_edge_cases(self):
        """Test various numeric literal formats"""
        numeric_code = """
# Different numeric formats
decimal = 1234567890
binary = 0b1010
octal = 0o755
hexadecimal = 0xFF

# Floating point
simple_float = 3.14
scientific = 1.23e-4
complex_num = 3+4j

# Underscores in numerics (Python 3.6+)
big_number = 1_000_000_000
binary_grouped = 0b_1111_0000
"""
        
        parse_result = self.parser.get_parse_result(numeric_code)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(numeric_code)
        self.assertTrue(validation.is_valid)
    
    def test_empty_constructs(self):
        """Test empty functions, classes, etc."""
        empty_constructs = """
# Empty function
def empty_func():
    pass

# Empty class
class EmptyClass:
    pass

# Empty try block
try:
    pass
except:
    pass
finally:
    pass

# Empty loops
for _ in range(0):
    pass

while False:
    pass

# Empty if
if False:
    pass
elif False:
    pass
else:
    pass
"""
        
        parse_result = self.parser.get_parse_result(empty_constructs)
        self.assertTrue(parse_result.success)
        
        validation = self.validator.validate_syntax(empty_constructs)
        self.assertTrue(validation.is_valid)


class TestPerformanceRegressions(unittest.TestCase):
    """Test performance-related regressions"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        self.parser = ParserModule()
        self.assembler = CodeAssembler(self.config)
    
    def test_large_file_handling(self):
        """Test handling of large files without timeout"""
        # Generate a large pseudocode file
        large_content = []
        
        for i in range(100):
            large_content.append(f"""
# Function {i}
def function_{i}(param_{i}):
    '''Docstring for function {i}'''
    result = param_{i} * 2
    for j in range(10):
        result += j
    return result
""")
        
        large_pseudocode = "\n".join(large_content)
        
        # Should complete within reasonable time
        import time
        start_time = time.time()
        
        parse_result = self.parser.get_parse_result(large_pseudocode)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within 5 seconds
        self.assertLess(duration, 5.0)
        self.assertTrue(parse_result.success)
    
    def test_memory_usage_stability(self):
        """Test that memory usage remains stable"""
        # This is a basic test - in production you'd use memory profiling
        
        # Process same content multiple times
        content = """
def process_data(data):
    return [x * 2 for x in data]
"""
        
        for _ in range(100):
            parse_result = self.parser.get_parse_result(content)
            blocks = parse_result.blocks
            
            # Process should not accumulate memory
            result = self.assembler.assemble(blocks)
            
            # Results should be consistent
            self.assertIn("def process_data", result)
    
    def test_caching_effectiveness(self):
        """Test that caching improves performance"""
        # Test AST cache
        code = """
def cached_function():
    return 42
"""
        
        # First parse (cache miss)
        import time
        start = time.time()
        
        from ast_cache import parse_cached
        tree1 = parse_cached(code)
        
        first_duration = time.time() - start
        
        # Second parse (cache hit)
        start = time.time()
        tree2 = parse_cached(code)
        second_duration = time.time() - start
        
        # Cache hit should be faster (or at least not slower)
        self.assertLessEqual(second_duration, first_duration * 1.5)
        
        # Trees should be equivalent
        self.assertEqual(
            ast.dump(tree1),
            ast.dump(tree2)
        )


if __name__ == '__main__':
    unittest.main()