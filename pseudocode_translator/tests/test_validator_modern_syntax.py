"""
Test cases for validator.py with modern Python syntax support
Tests Python 3.10+ match statements, walrus operator, and modern type annotations
"""

import ast
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from validator import Validator, ValidationResult
from config import TranslatorConfig


class TestValidatorModernSyntax:
    """Test validator with modern Python syntax"""
    
    def __init__(self):
        self.config = TranslatorConfig()
        self.validator = Validator(self.config)
    
    def test_match_statement_variables(self):
        """Test that match statement pattern variables are recognized"""
        code = '''
def process_command(command):
    match command:
        case ["move", x, y]:
            # x and y should be recognized as defined
            return f"Moving to {x}, {y}"
        case ["rotate", angle]:
            # angle should be recognized as defined
            return f"Rotating by {angle} degrees"
        case {"action": action, "value": value}:
            # action and value should be recognized as defined
            return f"{action}: {value}"
        case Point(x, y) as point:
            # x, y, and point should be recognized as defined
            return f"Point at {x}, {y}: {point}"
        case [*items]:
            # items should be recognized as defined
            return f"Items: {items}"
        case _:
            return "Unknown command"
'''
        result = self.validator.validate_syntax(code)
        print(f"Match statement test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        assert result.is_valid, f"Match statement validation failed: {result.errors}"
    
    def test_walrus_operator(self):
        """Test that walrus operator assignments are recognized"""
        code = '''
def process_data(data):
    # Walrus operator in if statement
    if (n := len(data)) > 10:
        print(f"Large dataset with {n} items")
        
    # Walrus operator in while loop
    while (line := input()) != "quit":
        print(f"Processing: {line}")
        
    # Walrus operator in list comprehension
    results = [y for x in data if (y := x * 2) > 5]
    
    # Walrus operator in function call
    print(f"Total: {(total := sum(data))}")
    return total
'''
        result = self.validator.validate_syntax(code)
        print(f"Walrus operator test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        assert result.is_valid, f"Walrus operator validation failed: {result.errors}"
    
    def test_modern_type_annotations(self):
        """Test modern type annotation syntax"""
        code = '''
from typing import Union, Optional, List, Dict, TypeAlias, Literal, TypedDict

# Type alias (Python 3.10+)
Vector: TypeAlias = List[float]

# Union types with | (Python 3.10+)
def process(value: int | str | None) -> str | int:
    if isinstance(value, str):
        return value.upper()
    elif isinstance(value, int):
        return str(value)
    return "None"

# TypedDict
class Config(TypedDict):
    name: str
    value: int
    optional: NotRequired[str]

# Generic with new syntax
def first[T](items: List[T]) -> T | None:
    return items[0] if items else None

# Self type (Python 3.11+)
class Node:
    def connect(self, other: Self) -> Self:
        return self

# ParamSpec and TypeVarTuple
from typing import ParamSpec, TypeVarTuple

P = ParamSpec('P')
Ts = TypeVarTuple('Ts')

def decorator[**P](func: Callable[P, Any]) -> Callable[P, Any]:
    return func
'''
        result = self.validator.validate_syntax(code)
        print(f"Modern type annotations test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        # Note: Some syntax might not be valid in older Python versions
        if sys.version_info >= (3, 10):
            assert result.is_valid, f"Type annotation validation failed: {result.errors}"
    
    def test_pattern_matching_edge_cases(self):
        """Test edge cases in pattern matching"""
        code = '''
def complex_patterns(obj):
    match obj:
        case [x, y, *rest] if x > 0:
            # x, y, and rest should be defined
            return f"First: {x}, Second: {y}, Rest: {rest}"
            
        case {"key": value, **extras}:
            # value and extras should be defined
            return f"Value: {value}, Extras: {extras}"
            
        case Point(x=0, y=y_coord):
            # y_coord should be defined (x is a literal)
            return f"On Y-axis at {y_coord}"
            
        case [first, *middle, last]:
            # first, middle, and last should be defined
            return f"{first} ... {middle} ... {last}"
'''
        result = self.validator.validate_syntax(code)
        print(f"Pattern matching edge cases test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        if sys.version_info >= (3, 10):
            assert result.is_valid, f"Pattern matching edge cases failed: {result.errors}"
    
    def test_undefined_variables_still_caught(self):
        """Test that genuinely undefined variables are still caught"""
        code = '''
def buggy_function():
    # This should be caught as undefined
    print(undefined_var)
    
    # This should be caught
    result = x + y
    
    # But this should be OK
    x = 10
    y = 20
    result = x + y
    
    return result
'''
        result = self.validator.validate_syntax(code)
        print(f"Undefined variables test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        assert not result.is_valid, "Should have caught undefined variables"
        assert any("undefined_var" in error for error in result.errors)
        assert any("x" in error for error in result.errors)
        assert any("y" in error for error in result.errors)
    
    def test_forward_references_in_annotations(self):
        """Test that forward references in type annotations work"""
        code = '''
from typing import Optional

class TreeNode:
    def __init__(self, value: int, left: Optional['TreeNode'] = None, 
                 right: Optional['TreeNode'] = None):
        self.value = value
        self.left = left
        self.right = right
    
    def add_child(self, child: 'TreeNode') -> None:
        if self.value > child.value:
            self.left = child
        else:
            self.right = child
'''
        result = self.validator.validate_syntax(code)
        print(f"Forward references test - Valid: {result.is_valid}")
        print(f"Errors: {result.errors}")
        assert result.is_valid, f"Forward reference validation failed: {result.errors}"
    
    def run_all_tests(self):
        """Run all validator tests"""
        print("=" * 60)
        print("Running Validator Modern Syntax Tests")
        print("=" * 60)
        
        tests = [
            ("Match Statement Variables", self.test_match_statement_variables),
            ("Walrus Operator", self.test_walrus_operator),
            ("Modern Type Annotations", self.test_modern_type_annotations),
            ("Pattern Matching Edge Cases", self.test_pattern_matching_edge_cases),
            ("Undefined Variables Still Caught", self.test_undefined_variables_still_caught),
            ("Forward References", self.test_forward_references_in_annotations),
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
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"Results: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return failed == 0


if __name__ == "__main__":
    tester = TestValidatorModernSyntax()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)