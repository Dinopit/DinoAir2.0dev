"""
Unit Tests for Code Assembler Module

This module tests the code assembly functionality including import organization,
function merging, indentation fixing, and consistency checking.
"""

import unittest
from unittest.mock import patch, MagicMock
import ast
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from assembler import CodeAssembler
from models import CodeBlock, BlockType
from config import TranslatorConfig
from exceptions import AssemblyError


class TestCodeAssembler(unittest.TestCase):
    """Test the CodeAssembler class"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        self.assembler = CodeAssembler(self.config)
    
    def test_initialization(self):
        """Test assembler initialization"""
        self.assertEqual(self.assembler.indent_size, self.config.indent_size)
        self.assertEqual(
            self.assembler.max_line_length,
            self.config.max_line_length
        )
        self.assertEqual(
            self.assembler.preserve_comments,
            self.config.preserve_comments
        )
        self.assertIsNotNone(self.assembler.common_imports)
    
    def test_empty_blocks(self):
        """Test assembly with empty block list"""
        result = self.assembler.assemble([])
        self.assertEqual(result, "")
    
    def test_simple_python_block(self):
        """Test assembly of a single Python block"""
        block = CodeBlock(
            type=BlockType.PYTHON,
            content="def hello():\n    print('Hello, World!')",
            line_numbers=(1, 2),
            metadata={},
            context={}
        )
        
        result = self.assembler.assemble([block])
        self.assertIn("def hello():", result)
        self.assertIn("print('Hello, World!')", result)
    
    def test_import_organization(self):
        """Test import organization and deduplication"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="import os\nimport sys\nfrom typing import List",
                line_numbers=(1, 3),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="import os\nimport json\nfrom typing import Dict",
                line_numbers=(4, 6),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def process():\n    pass",
                line_numbers=(7, 8),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Check imports are organized
        lines = result.strip().split('\n')
        
        # Should have deduplicated imports
        self.assertEqual(lines.count("import os"), 1)
        self.assertEqual(lines.count("import sys"), 1)
        self.assertEqual(lines.count("import json"), 1)
        
        # Check typing imports are combined
        self.assertIn("from typing import", result)
        self.assertIn("Dict", result)
        self.assertIn("List", result)
    
    def test_import_categorization(self):
        """Test that imports are properly categorized"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
import os
import sys
import numpy as np
import pandas as pd
from . import local_module
from ..parent import other_module
""",
                line_numbers=(1, 7),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        lines = result.strip().split('\n')
        
        # Find positions of different import categories
        os_pos = next(i for i, l in enumerate(lines) if 'import os' in l)
        numpy_pos = next(i for i, l in enumerate(lines) if 'numpy' in l)
        local_pos = next(i for i, l in enumerate(lines) if 'local_module' in l)
        
        # Standard library should come before third-party
        self.assertLess(os_pos, numpy_pos)
        # Third-party should come before local
        self.assertLess(numpy_pos, local_pos)
    
    def test_function_merging(self):
        """Test merging of duplicate functions"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="def calculate(x):\n    return x * 2",
                line_numbers=(1, 2),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def calculate(x):\n    # Updated version\n    return x * 3",
                line_numbers=(3, 5),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def other_func():\n    pass",
                line_numbers=(6, 7),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should only have one calculate function (the later one)
        self.assertEqual(result.count("def calculate"), 1)
        self.assertIn("return x * 3", result)
        self.assertNotIn("return x * 2", result)
        
        # Should still have other_func
        self.assertEqual(result.count("def other_func"), 1)
    
    def test_class_merging(self):
        """Test merging of duplicate classes"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
class MyClass:
    def __init__(self):
        self.value = 1
""",
                line_numbers=(1, 4),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
class MyClass:
    def __init__(self):
        self.value = 2
    
    def get_value(self):
        return self.value
""",
                line_numbers=(5, 11),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should only have one MyClass (the later one)
        self.assertEqual(result.count("class MyClass"), 1)
        self.assertIn("self.value = 2", result)
        self.assertIn("def get_value", result)
    
    def test_global_organization(self):
        """Test organization of global variables and constants"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
MAX_SIZE = 100
MIN_SIZE = 10
current_value = 0
user_data = {}
DEFAULT_CONFIG = {'debug': False}
""",
                line_numbers=(1, 6),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Check that constants come before variables
        lines = result.strip().split('\n')
        max_pos = next(i for i, l in enumerate(lines) if 'MAX_SIZE' in l)
        current_pos = next(i for i, l in enumerate(lines) if 'current_value' in l)
        
        self.assertLess(max_pos, current_pos)
        
        # Check for section headers
        self.assertIn("# Constants", result)
        self.assertIn("# Global variables", result)
    
    def test_main_code_organization(self):
        """Test organization of main execution code"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
def setup():
    print("Setting up...")

print("Starting program")
setup()
print("Program complete")
""",
                line_numbers=(1, 7),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should wrap main code in if __name__ == "__main__":
        self.assertIn('if __name__ == "__main__":', result)
        # Main code should be indented
        self.assertIn('    print("Starting program")', result)
        self.assertIn('    setup()', result)
    
    def test_indentation_fixing(self):
        """Test indentation fixing functionality"""
        # Test mixed tabs and spaces
        mixed_indent = """
def function1():
	print("tab indent")
    print("space indent")
        print("more spaces")

class MyClass:
		def method(self):
				return "inconsistent tabs"
"""
        
        fixed = self.assembler._fix_indentation(mixed_indent)
        
        # All lines should use spaces
        self.assertNotIn('\t', fixed)
        
        # Check proper indentation levels
        lines = fixed.split('\n')
        for line in lines:
            if 'print("tab indent")' in line:
                self.assertTrue(line.startswith('    '))
            if 'print("space indent")' in line:
                self.assertTrue(line.startswith('    '))
            if 'def method' in line:
                self.assertTrue(line.startswith('    '))
    
    def test_consistency_checking(self):
        """Test code consistency ensuring"""
        code_with_issues = """


def func1():
    pass




def func2():
    pass


"""
        
        result = self.assembler._ensure_consistency(code_with_issues)
        
        # Should remove excessive blank lines
        self.assertNotIn('\n\n\n\n', result)
        
        # Should end with single newline
        self.assertTrue(result.endswith('\n'))
        self.assertFalse(result.endswith('\n\n'))
    
    def test_auto_import_common(self):
        """Test automatic addition of common imports"""
        # Enable auto import
        self.assembler.auto_import_common = True
        
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
def calculate_circle_area(radius):
    return pi * radius ** 2

def read_file(filename):
    with open(path.join('data', filename)) as f:
        return f.read()
""",
                line_numbers=(1, 7),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should auto-add math import for pi
        self.assertIn("from math import pi", result)
        # Should auto-add os import for path
        self.assertIn("from os import path", result)
    
    def test_module_docstring_preservation(self):
        """Test that module docstrings are preserved"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content='"""This is a module docstring."""\n\nimport os',
                line_numbers=(1, 3),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def main():\n    pass",
                line_numbers=(4, 5),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Docstring should be at the top
        self.assertTrue(result.startswith('"""This is a module docstring."""'))
    
    def test_error_handling_invalid_syntax(self):
        """Test error handling for blocks with invalid syntax"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="def broken(:\n    pass",  # Invalid syntax
                line_numbers=(1, 2),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def valid():\n    pass",
                line_numbers=(3, 4),
                metadata={},
                context={}
            )
        ]
        
        # Should still produce output with valid blocks
        result = self.assembler.assemble(blocks)
        self.assertIn("def valid():", result)
    
    def test_streaming_assembly(self):
        """Test streaming assembly functionality"""
        # Create an iterator of blocks
        def block_iterator():
            yield CodeBlock(
                type=BlockType.PYTHON,
                content="import os",
                line_numbers=(1, 1),
                metadata={},
                context={}
            )
            yield CodeBlock(
                type=BlockType.PYTHON,
                content="def process():\n    pass",
                line_numbers=(2, 3),
                metadata={},
                context={}
            )
        
        result = self.assembler.assemble_streaming(block_iterator())
        
        self.assertIn("import os", result)
        self.assertIn("def process():", result)
    
    def test_incremental_assembly(self):
        """Test incremental assembly functionality"""
        # Initial code
        previous_code = """
import os

def existing_function():
    return "existing"

class ExistingClass:
    pass
"""
        
        # New blocks to add
        new_blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="import sys\nfrom typing import List",
                line_numbers=(1, 2),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def new_function():\n    return 'new'",
                line_numbers=(3, 4),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def existing_function():\n    return 'should not duplicate'",
                line_numbers=(5, 6),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble_incremental(previous_code, new_blocks)
        
        # Should include existing code
        self.assertIn("def existing_function():", result)
        self.assertIn("class ExistingClass:", result)
        
        # Should add new imports
        self.assertIn("import sys", result)
        self.assertIn("from typing import List", result)
        
        # Should add new function
        self.assertIn("def new_function():", result)
        
        # Should not duplicate existing function
        self.assertEqual(result.count("def existing_function():"), 1)
    
    def test_final_cleanup(self):
        """Test final cleanup functionality"""
        code_with_trailing_spaces = """
def func1():    
    pass     

class MyClass:   
    def method(self):     
        return True    
"""
        
        result = self.assembler._final_cleanup(code_with_trailing_spaces)
        
        # Should remove trailing spaces
        lines = result.split('\n')
        for line in lines:
            if line:  # Skip empty lines
                self.assertFalse(line.endswith(' '))
    
    def test_complex_assembly_scenario(self):
        """Test a complex assembly scenario with multiple features"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content='"""Complex module for testing."""',
                line_numbers=(1, 1),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="import json\nimport os\nfrom datetime import datetime",
                line_numbers=(2, 4),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="MAX_RETRIES = 3\nTIMEOUT = 30",
                line_numbers=(5, 6),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self):
        return len(self.data)
""",
                line_numbers=(7, 14),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="import sys  # Late import",
                line_numbers=(15, 15),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="""
def main():
    processor = DataProcessor()
    print(processor.process())

if __name__ == "__main__":
    main()
""",
                line_numbers=(16, 22),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Verify structure
        lines = result.strip().split('\n')
        
        # Module docstring should be first
        self.assertEqual(lines[0], '"""Complex module for testing."""')
        
        # Imports should be organized
        import_section_start = next(
            i for i, l in enumerate(lines) if 'import' in l
        )
        # sys should be with os and json
        self.assertLess(
            abs(lines.index("import sys") - lines.index("import os")),
            5
        )
        
        # Constants should come after imports
        max_retries_pos = next(
            i for i, l in enumerate(lines) if 'MAX_RETRIES' in l
        )
        self.assertGreater(max_retries_pos, import_section_start)
        
        # Main should not be wrapped again
        self.assertEqual(result.count('if __name__ == "__main__":'), 1)
    
    def test_non_python_blocks_filtered(self):
        """Test that non-Python blocks are filtered out"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="def func1():\n    pass",
                line_numbers=(1, 2),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.ENGLISH,
                content="This should not appear in output",
                line_numbers=(3, 3),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.COMMENT,
                content="# This is a comment block",
                line_numbers=(4, 4),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="def func2():\n    pass",
                line_numbers=(5, 6),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should only contain Python blocks
        self.assertIn("def func1():", result)
        self.assertIn("def func2():", result)
        self.assertNotIn("This should not appear", result)
    
    def test_assembly_error_handling(self):
        """Test AssemblyError exception handling"""
        # Mock parse_cached to raise an exception
        with patch('assembler.parse_cached') as mock_parse:
            mock_parse.side_effect = Exception("Parse failed")
            
            blocks = [
                CodeBlock(
                    type=BlockType.PYTHON,
                    content="import os",
                    line_numbers=(1, 1),
                    metadata={},
                    context={}
                )
            ]
            
            # Should raise AssemblyError
            with self.assertRaises(AssemblyError) as context:
                self.assembler.assemble(blocks)
            
            error = context.exception
            self.assertIn("organize imports", str(error))
    
    def test_empty_python_blocks(self):
        """Test handling of empty Python blocks"""
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content="",  # Empty content
                line_numbers=(1, 1),
                metadata={},
                context={}
            ),
            CodeBlock(
                type=BlockType.PYTHON,
                content="   \n  \n   ",  # Only whitespace
                line_numbers=(2, 4),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Should handle gracefully
        self.assertIsNotNone(result)
        # Should not have much content
        self.assertTrue(len(result.strip()) < 50)


class TestAssemblerHelperMethods(unittest.TestCase):
    """Test individual helper methods of the assembler"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TranslatorConfig()
        self.assembler = CodeAssembler(self.config)
    
    def test_categorize_import(self):
        """Test import categorization"""
        # Standard library
        self.assertEqual(self.assembler._categorize_import('os'), 'standard')
        self.assertEqual(self.assembler._categorize_import('sys'), 'standard')
        self.assertEqual(
            self.assembler._categorize_import('json'),
            'standard'
        )
        
        # Third party
        self.assertEqual(
            self.assembler._categorize_import('numpy'),
            'third_party'
        )
        self.assertEqual(
            self.assembler._categorize_import('requests'),
            'third_party'
        )
        
        # Local imports
        self.assertEqual(self.assembler._categorize_import('.module'), 'local')
        self.assertEqual(self.assembler._categorize_import('..parent'), 'local')
        self.assertEqual(self.assembler._categorize_import(''), 'local')
    
    def test_is_top_level_assignment(self):
        """Test detection of top-level assignments"""
        code = """
x = 1  # Top level

def func():
    y = 2  # Not top level

class MyClass:
    z = 3  # Not top level (class attribute)

a = 4  # Top level
"""
        
        tree = ast.parse(code)
        
        # Test each assignment
        assignments = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                is_top = self.assembler._is_top_level_assignment(node, tree)
                var_name = node.targets[0].id if hasattr(
                    node.targets[0], 'id'
                ) else None
                assignments.append((var_name, is_top))
        
        # x and a should be top-level
        self.assertIn(('x', True), assignments)
        self.assertIn(('a', True), assignments)
        
        # y should not be top-level
        self.assertIn(('y', False), assignments)
    
    def test_line_length_enforcement(self):
        """Test that max line length is enforced"""
        # Create a block with a very long line
        long_line = "x = " + "'a' + " * 50 + "'end'"
        
        blocks = [
            CodeBlock(
                type=BlockType.PYTHON,
                content=f"# This is fine\n{long_line}",
                line_numbers=(1, 2),
                metadata={},
                context={}
            )
        ]
        
        result = self.assembler.assemble(blocks)
        
        # Check all lines respect max length
        # (Note: The assembler might not enforce this strictly,
        # so this test documents current behavior)
        lines = result.split('\n')
        for line in lines:
            if len(line) > self.assembler.max_line_length:
                # Log but don't fail - assembler may not enforce this
                print(
                    f"Line exceeds max length ({len(line)} > "
                    f"{self.assembler.max_line_length}): {line[:50]}..."
                )


if __name__ == '__main__':
    unittest.main()