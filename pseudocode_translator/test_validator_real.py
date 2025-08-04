#!/usr/bin/env python3
"""Test the actual validator implementation."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pseudocode_translator.validator import Validator
from pseudocode_translator.config import TranslatorConfig, LLMConfig

def run_test(test_name, code, expected_errors=None, expected_no_errors=None):
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print("Code:")
    print(code)
    print("-" * 40)
    
    # Create config
    llm_config = LLMConfig(
        provider="test",
        model="test",
        api_key="test",
        validation_level="normal"
    )
    config = TranslatorConfig(
        llm=llm_config,
        check_undefined_vars=True,
        validate_imports=True,
        allow_unsafe_operations=False
    )
    
    # Create validator and validate
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

# Run tests
def main():
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
    all_passed &= run_test(
        "Performance - repeated append",
        """
result = []
for i in range(100):
    result.append(i)
    result.append(i * 2)
""",
        expected_no_errors=["undefined"]
    )
    
    # Check if performance suggestion was made
    llm_config = LLMConfig(
        provider="test",
        model="test",
        api_key="test",
        validation_level="normal"
    )
    config = TranslatorConfig(
        llm=llm_config,
        check_undefined_vars=True
    )
    validator = Validator(config)
    suggestions = validator.suggest_improvements("""
result = []
for i in range(100):
    result.append(i)
    result.append(i * 2)
""")
    
    if any("list comprehension" in s for s in suggestions):
        print("✓ Performance suggestion for repeated append found")
    else:
        print("❌ Performance suggestion for repeated append not found")
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed.")
    print("="*60)

if __name__ == "__main__":
    main()