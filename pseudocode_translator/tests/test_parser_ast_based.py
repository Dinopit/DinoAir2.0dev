"""
Test cases for parser.py with AST-based block detection
Tests improved block identification and modern Python syntax support
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import ParserModule
from models import BlockType


class TestParserASTBased:
    """Test parser with AST-based block detection"""
    
    def __init__(self):
        self.parser = ParserModule()
    
    def test_basic_block_separation(self):
        """Test basic separation of Python and English blocks"""
        code = '''
# This is a Python comment
import math

Define a function to calculate area
def calculate_area(radius):
    """Calculate the area of a circle"""
    return math.pi * radius ** 2

Now let's use the function
result = calculate_area(5)
print(f"Area: {result}")
'''
        blocks = self.parser.parse(code)
        print(f"Basic separation test - Blocks found: {len(blocks)}")
        
        # Should have multiple blocks
        assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"
        
        # Check block types
        python_blocks = [b for b in blocks if b.type == BlockType.PYTHON]
        english_blocks = [b for b in blocks if b.type == BlockType.ENGLISH]
        
        print(f"Python blocks: {len(python_blocks)}, English blocks: {len(english_blocks)}")
        assert len(python_blocks) > 0, "Should have Python blocks"
        assert len(english_blocks) > 0, "Should have English blocks"
    
    def test_match_statement_parsing(self):
        """Test parsing of match statements"""
        code = '''
def handle_command(cmd):
    match cmd:
        case ["move", x, y]:
            print(f"Moving to {x}, {y}")
        case ["rotate", angle]:
            print(f"Rotating {angle} degrees")
        case _:
            print("Unknown command")
'''
        blocks = self.parser.parse(code)
        print(f"Match statement test - Blocks found: {len(blocks)}")
        
        # Should recognize this as a single Python block
        assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
        assert blocks[0].type == BlockType.PYTHON
        assert "match" in blocks[0].content
    
    def test_walrus_operator_parsing(self):
        """Test parsing of walrus operator"""
        code = '''
# Process data with walrus operator
if (n := len(data)) > 10:
    print(f"Large dataset: {n} items")

# Use in comprehension
filtered = [y for x in items if (y := transform(x)) > 0]
'''
        blocks = self.parser.parse(code)
        print(f"Walrus operator test - Blocks found: {len(blocks)}")
        
        # Should recognize as Python blocks
        for block in blocks:
            if ":=" in block.content:
                assert block.type == BlockType.PYTHON
    
    def test_mixed_block_detection(self):
        """Test detection of mixed English/Python blocks"""
        code = '''
Let's create a function that processes items:
def process_items(items):
    # First, filter out None values
    valid_items = [item for item in items if item is not None]
    
    Then we need to transform each item
    transformed = []
    for item in valid_items:
        # Apply transformation
        result = transform(item)
        transformed.append(result)
    
    Finally return the results
    return transformed
'''
        blocks = self.parser.parse(code)
        print(f"Mixed block test - Blocks found: {len(blocks)}")
        
        # Should identify mixed blocks
        mixed_blocks = [b for b in blocks if b.type == BlockType.MIXED]
        print(f"Mixed blocks found: {len(mixed_blocks)}")
        
        # The function definition with English comments should be mixed
        assert any(b.type == BlockType.MIXED for b in blocks), "Should have mixed blocks"
    
    def test_import_statement_blocks(self):
        """Test that import statements create new blocks"""
        code = '''
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

def process_data():
    pass
'''
        blocks = self.parser.parse(code)
        print(f"Import statement test - Blocks found: {len(blocks)}")
        
        # Import statements should be grouped appropriately
        assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"
    
    def test_class_definition_blocks(self):
        """Test class definition block detection"""
        code = '''
Define a class for data processing
class DataProcessor:
    """A class to process data"""
    
    def __init__(self, config):
        self.config = config
    
    def process(self, data):
        # Process the data
        return data

Now create an instance
processor = DataProcessor(config)
'''
        blocks = self.parser.parse(code)
        print(f"Class definition test - Blocks found: {len(blocks)}")
        
        # Should have separate blocks for English, class def, and usage
        assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"
        
        # Find the class block
        class_blocks = [b for b in blocks if "class DataProcessor" in b.content]
        assert len(class_blocks) == 1, "Should have one class definition block"
        assert class_blocks[0].type == BlockType.PYTHON
    
    def test_multiline_strings(self):
        """Test handling of multiline strings"""
        code = '''
def generate_report():
    """
    Generate a detailed report.
    
    This function creates a multi-page report
    with various sections and formatting.
    """
    report = """
    ANNUAL REPORT 2024
    ==================
    
    Executive Summary
    -----------------
    This year has been productive.
    """
    return report
'''
        blocks = self.parser.parse(code)
        print(f"Multiline string test - Blocks found: {len(blocks)}")
        
        # Should keep multiline strings within their blocks
        assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
        assert '"""' in blocks[0].content
    
    def test_ast_transition_detection(self):
        """Test AST-based transition detection"""
        code = '''
x = 10
y = 20

Calculate the sum of x and y
result = x + y

print(result)
'''
        blocks = self.parser.parse(code)
        print(f"AST transition test - Blocks found: {len(blocks)}")
        
        # Should detect transition from Python to English to Python
        assert len(blocks) >= 3, f"Expected at least 3 blocks, got {len(blocks)}"
        
        # Check the middle block is English
        english_found = False
        for i, block in enumerate(blocks):
            if "Calculate the sum" in block.content:
                assert block.type == BlockType.ENGLISH
                english_found = True
                # Check surrounding blocks are Python
                if i > 0:
                    assert blocks[i-1].type == BlockType.PYTHON
                if i < len(blocks) - 1:
                    assert blocks[i+1].type == BlockType.PYTHON
        
        assert english_found, "Should have found the English instruction"
    
    def test_modern_syntax_classification(self):
        """Test classification of modern Python syntax"""
        code = '''
# Type hints with union
def process(value: int | str) -> str | None:
    match value:
        case int(x) if x > 0:
            return str(x)
        case str(s):
            return s.upper()
        case _:
            return None

# Structural pattern matching
match point:
    case Point(x=0, y=0):
        print("Origin")
    case Point(x=0, y=y):
        print(f"On Y-axis at {y}")
'''
        blocks = self.parser.parse(code)
        print(f"Modern syntax test - Blocks found: {len(blocks)}")
        
        # All should be classified as Python
        for block in blocks:
            assert block.type == BlockType.PYTHON, f"Block should be Python: {block.content[:50]}"
    
    def run_all_tests(self):
        """Run all parser tests"""
        print("=" * 60)
        print("Running Parser AST-Based Tests")
        print("=" * 60)
        
        tests = [
            ("Basic Block Separation", self.test_basic_block_separation),
            ("Match Statement Parsing", self.test_match_statement_parsing),
            ("Walrus Operator Parsing", self.test_walrus_operator_parsing),
            ("Mixed Block Detection", self.test_mixed_block_detection),
            ("Import Statement Blocks", self.test_import_statement_blocks),
            ("Class Definition Blocks", self.test_class_definition_blocks),
            ("Multiline Strings", self.test_multiline_strings),
            ("AST Transition Detection", self.test_ast_transition_detection),
            ("Modern Syntax Classification", self.test_modern_syntax_classification),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\nTesting: {test_name}")
            try:
                test_func()
                print(f"✓ {test_name} passed")
                passed += 1
            except Exception as e:
                print(f"✗ {test_name} failed: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return failed == 0


if __name__ == "__main__":
    tester = TestParserASTBased()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)