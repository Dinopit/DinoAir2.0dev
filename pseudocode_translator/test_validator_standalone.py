#!/usr/bin/env python3
"""Direct test of validator without full module import chain."""

import sys
import os
import ast

# Direct import to avoid the full module chain
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import only what we need
from validator import Validator, ValidationResult
from config import TranslatorConfig, LLMConfig
from models import ModelConfig

def create_test_config():
    """Create a test configuration."""
    # Create a minimal config that bypasses the LLM requirements
    model_config = ModelConfig(
        name="test",
        type="test",
        context_length=1000
    )
    
    llm_config = LLMConfig(
        models={"test": model_config},
        default_model="test",
        validation_level="normal"
    )
    
    config = TranslatorConfig(
        llm=llm_config,
        check_undefined_vars=True,
        validate_imports=True,
        allow_unsafe_operations=False
    )
    
    return config

def run_test(test_name, code, expected_errors=None, expected_no_errors=None):
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print("Code:")
    print(code)
    print("-" * 40)
    
    # Create validator and validate
    config = create_test_config()
    validator = Validator(config)
    result = validator.validate_syntax(code)
    
    print("Errors found:")
    if result.errors:
        for err in result.errors:
            print(f"  - {err}")
    else:
        print("  None")
        
    print("\nWarnings found:")
    if result.warnings:
        for warn in result.warnings:
            print(f"  - {warn}")
    else:
        print("  None")
    
    # Check expectations
    success = True
    if expected_errors:
        for expected in expected_errors:
            found = any(expected in err for err in result.errors)
            if not found:
                print(f"❌ Expected error containing '{expected}' not found")
                success = False
            else:
                print(f"✓ Found expected error: '{expected}'")
                
    if expected_no_errors:
        for not_expected in expected_no_errors:
            found = any(not_expected in err for err in result.errors)
            if found:
                print(f"❌ Unexpected error containing '{not_expected}' found")
                success = False
            else:
                print(f"✓ No error for: '{not_expected}'")
    
    if success:
        print("\n✅ Test PASSED")
    else:
        print("\n❌ Test FAILED")
        
    return success

def main():
    """Run all tests."""
    all_passed = True
    
    # Test 1: Basic undefined variable
    all_passed &= run_test(
        "Basic undefined variable",
        """
x = 5
print(y)  # y is undefined
""",
        expected_errors=["'y'"]
    )
    
    # Test 2: Variable used before definition
    all_passed &= run_test(
        "Variable used before definition",
        """
print(x)  # x used before definition
x = 5
y = z + 1  # z is undefined
""",
        expected_errors=["'x'", "'z'"]
    )
    
    # Test 3: Built-ins should not be flagged
    all_passed &= run_test(
        "Built-ins recognition",
        """
print(len([1, 2, 3]))
x = str(42)
y = isinstance(x, str)
""",
        expected_no_errors=["print", "len", "str", "isinstance"]
    )
    
    # Test 4: Import handling
    all_passed &= run_test(
        "Import handling",
        """
import math
from os import path
import sys as system

result = math.sqrt(16)
file = path.join('a', 'b')
version = system.version
numpy.array([1, 2, 3])  # numpy not imported
""",
        expected_errors=["'numpy'"],
        expected_no_errors=["math", "path", "system"]
    )
    
    # Test 5: Function parameters
    all_passed &= run_test(
        "Function parameters",
        """
def add(a, b):
    return a + b + c  # c is undefined

def multiply(x, y=2):
    return x * y  # both defined
""",
        expected_errors=["'c'"],
        expected_no_errors=["'a'", "'b'", "'x'", "'y'"]
    )
    
    # Test 6: Performance check
    print(f"\n{'='*60}")
    print("Test: Performance - repeated append")
    print("="*60)
    
    perf_code = """
result = []
for i in range(100):
    result.append(i)
    result.append(i * 2)
"""
    
    config = create_test_config()
    validator = Validator(config)
    suggestions = validator.suggest_improvements(perf_code)
    
    print("Code:")
    print(perf_code)
    print("-" * 40)
    print("Suggestions:")
    for sugg in suggestions:
        print(f"  - {sugg}")
    
    if any("list comprehension" in s for s in suggestions):
        print("\n✓ Performance suggestion for repeated append found")
    else:
        print("\n❌ Performance suggestion for repeated append not found")
        all_passed = False
    
    # Test 7: Exception variable scoping
    all_passed &= run_test(
        "Exception variable scoping",
        """
try:
    risky_operation()
except Exception as e:
    print(e)  # e is defined here

print(e)  # e is not accessible outside except block
""",
        expected_errors=["'risky_operation'", "'e'"]
    )
    
    # Test 8: Class and self
    all_passed &= run_test(
        "Class attributes and self",
        """
class MyClass:
    class_var = 42
    
    def method(self):
        return self.class_var
        
    def static_missing_decorator():
        return self.data  # self not available without self parameter
""",
        expected_errors=["'self'"]
    )
    
    # Test 9: Comprehensions
    all_passed &= run_test(
        "Comprehensions scope",
        """
data = [1, 2, 3]
squares = [x**2 for x in data]
filtered = [y for y in squares if y > 2]

# x is not accessible outside comprehension
print(x)
""",
        expected_errors=["'x'"],
        expected_no_errors=["data", "squares"]
    )
    
    # Test 10: Global and nonlocal
    all_passed &= run_test(
        "Global and nonlocal declarations",
        """
x = 10

def outer():
    y = 20
    
    def inner():
        nonlocal y
        global x
        x = 30
        y = 40
        z = 50
        
    def bad_nonlocal():
        nonlocal z  # z not in enclosing scope
        z = 60
""",
        expected_errors=["nonlocal 'z'"]
    )
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed.")
    print("="*60)

if __name__ == "__main__":
    main()