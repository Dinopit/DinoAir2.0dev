"""
Integration tests for parser and validator with modern Python syntax
Ensures the fixes work together correctly in the translation pipeline
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import ParserModule
from validator import Validator
from config import TranslatorConfig
from models import BlockType


class TestIntegrationModernSyntax:
    """Test parser and validator integration with modern syntax"""
    
    def __init__(self):
        self.parser = ParserModule()
        self.config = TranslatorConfig()
        self.validator = Validator(self.config)
    
    def test_full_pipeline_match_statement(self):
        """Test parsing and validation of match statements"""
        code = '''
# Command processor with pattern matching
def process_command(cmd):
    """Process various command patterns"""
    match cmd:
        case ["move", x, y] if x >= 0 and y >= 0:
            return f"Moving to position ({x}, {y})"
        case ["rotate", angle]:
            return f"Rotating {angle} degrees"
        case {"action": "scale", "factor": f}:
            return f"Scaling by factor {f}"
        case Point(x, y):
            return f"Point at ({x}, {y})"
        case [first, *rest]:
            return f"List with first={first}, rest={rest}"
        case _:
            return "Unknown command"

# Test the function
result = process_command(["move", 10, 20])
print(result)
'''
        # Parse the code
        blocks = self.parser.parse(code)
        print(f"Match statement pipeline - Blocks: {len(blocks)}")
        
        # Validate each block
        all_valid = True
        for i, block in enumerate(blocks):
            if block.type == BlockType.PYTHON:
                result = self.validator.validate_syntax(block.content)
                print(f"Block {i} validation: {result.is_valid}")
                if not result.is_valid:
                    print(f"Errors: {result.errors}")
                    all_valid = False
        
        assert all_valid, "All Python blocks should be valid"
    
    def test_full_pipeline_walrus_operator(self):
        """Test parsing and validation of walrus operator usage"""
        code = '''
Let's process some data efficiently using the walrus operator:

data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Filter and transform in one step
results = [y for x in data if (y := x * 2) > 5]

# Use in control flow
while (line := input("Enter command: ")) != "quit":
    if (n := len(line)) > 10:
        print(f"Command too long ({n} chars)")
    else:
        print(f"Processing: {line}")
'''
        # Parse the code
        blocks = self.parser.parse(code)
        print(f"Walrus operator pipeline - Blocks: {len(blocks)}")
        
        # Check block types
        has_english = any(b.type == BlockType.ENGLISH for b in blocks)
        has_python = any(b.type == BlockType.PYTHON for b in blocks)
        
        assert has_english, "Should have English blocks"
        assert has_python, "Should have Python blocks"
        
        # Validate Python blocks
        for block in blocks:
            if block.type == BlockType.PYTHON and ":=" in block.content:
                result = self.validator.validate_syntax(block.content)
                assert result.is_valid, f"Walrus operator block should be valid: {result.errors}"
    
    def test_full_pipeline_type_annotations(self):
        """Test parsing and validation of modern type annotations"""
        code = '''
from typing import TypeAlias, Union, Optional

# Define type aliases
Vector: TypeAlias = list[float]
Matrix: TypeAlias = list[Vector]

# Function with modern type hints
def transform_data(
    data: list[int | float],
    factor: float = 1.0
) -> Vector | None:
    """Transform data with optional scaling"""
    if not data:
        return None
    
    # Use walrus operator for efficiency
    if (n := len(data)) > 1000:
        print(f"Large dataset: {n} items")
    
    return [x * factor for x in data]

# Generic function with new syntax
def first_or_default[T](items: list[T], default: T) -> T:
    """Get first item or default value"""
    return items[0] if items else default
'''
        # Parse the code
        blocks = self.parser.parse(code)
        print(f"Type annotations pipeline - Blocks: {len(blocks)}")
        
        # All should be Python blocks
        for block in blocks:
            assert block.type == BlockType.PYTHON, f"Expected Python block: {block.content[:50]}"
            
            # Validate syntax
            result = self.validator.validate_syntax(block.content)
            # Note: Some syntax might not be valid in older Python versions
            if sys.version_info >= (3, 10) or "def first_or_default[T]" not in block.content:
                assert result.is_valid, f"Block should be valid: {result.errors}"
    
    def test_mixed_pseudocode_modern_syntax(self):
        """Test mixed pseudocode with modern Python features"""
        code = '''
Create a data processor that uses pattern matching:

class DataProcessor:
    def process(self, data):
        match data:
            case {"type": "number", "value": n}:
                return self.process_number(n)
            case {"type": "string", "value": s}:
                return self.process_string(s)
            case {"type": "list", "items": items}:
                # Use walrus operator to check length
                if (count := len(items)) > 100:
                    print(f"Processing large list: {count} items")
                return [self.process(item) for item in items]
            case _:
                return None
    
    Now implement the helper methods:
    
    def process_number(self, n: int | float) -> str:
        return f"Number: {n}"
    
    def process_string(self, s: str) -> str:
        return s.upper()

Finally, test the processor:
processor = DataProcessor()
result = processor.process({"type": "number", "value": 42})
print(result)
'''
        # Parse the code
        blocks = self.parser.parse(code)
        print(f"Mixed pseudocode pipeline - Blocks: {len(blocks)}")
        
        # Should have multiple block types
        block_types = {block.type for block in blocks}
        print(f"Block types found: {block_types}")
        
        # Validate all blocks
        validation_passed = True
        for i, block in enumerate(blocks):
            if block.type != BlockType.ENGLISH:
                result = self.validator.validate_syntax(block.content)
                print(f"Block {i} ({block.type.value}): Valid={result.is_valid}")
                if not result.is_valid and block.type == BlockType.PYTHON:
                    print(f"Validation errors: {result.errors}")
                    validation_passed = False
        
        assert validation_passed, "All non-English blocks should validate"
    
    def test_edge_cases(self):
        """Test edge cases and complex scenarios"""
        code = '''
# Complex pattern matching with guards and nested patterns
def analyze_data(obj):
    match obj:
        case [x, y, *rest] if x > 0 and all(r > 0 for r in rest):
            # All positive numbers
            total = x + y + sum(rest)
            return f"Positive list, sum: {total}"
        
        case {"data": [first, *_], "metadata": {"type": t}} if t == "numeric":
            return f"Numeric data starting with {first}"
        
        case Point(x=0, y=y_val) | Point(x=x_val, y=0):
            # On an axis
            return f"On axis: x={x_val if 'x_val' in locals() else 0}, y={y_val if 'y_val' in locals() else 0}"
        
        case _:
            return "Unknown pattern"

# Type annotations with forward references
class TreeNode:
    def __init__(self, value: int, left: Optional['TreeNode'] = None):
        self.value = value
        self.left = left
        self.right: Optional[TreeNode] = None  # No quotes needed here
'''
        # Parse and validate
        blocks = self.parser.parse(code)
        
        for block in blocks:
            if block.type == BlockType.PYTHON:
                result = self.validator.validate_syntax(block.content)
                # This code has intentional forward reference issues
                # but they should be handled gracefully
                print(f"Edge case validation: Errors={len(result.errors)}")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 60)
        print("Running Integration Tests for Modern Syntax")
        print("=" * 60)
        
        tests = [
            ("Full Pipeline - Match Statement", self.test_full_pipeline_match_statement),
            ("Full Pipeline - Walrus Operator", self.test_full_pipeline_walrus_operator),
            ("Full Pipeline - Type Annotations", self.test_full_pipeline_type_annotations),
            ("Mixed Pseudocode Modern Syntax", self.test_mixed_pseudocode_modern_syntax),
            ("Edge Cases", self.test_edge_cases),
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
    tester = TestIntegrationModernSyntax()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)