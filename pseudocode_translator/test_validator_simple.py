"""Simple test script for validator module to verify our implementation"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pseudocode_translator.validator import Validator, ValidationResult
from pseudocode_translator.config import TranslatorConfig, LLMConfig

# Create test config
llm_config = LLMConfig(validation_level="normal")
config = TranslatorConfig(
    llm=llm_config,
    validate_imports=True,
    check_undefined_vars=True,
    allow_unsafe_operations=False,
    max_line_length=79
)

# Create validator
validator = Validator(config)

print("Testing undefined variable detection...")

# Test 1: Basic undefined variable
code1 = """def func():
    return undefined_var"""

result1 = validator.validate_syntax(code1)
print(f"Test 1 - Undefined variable: {any('undefined' in err.lower() for err in result1.errors)}")

# Test 2: Scoping
code2 = """
x = 10  # Global

def outer():
    y = 20  # Local to outer
    
    def inner():
        return x + y  # Should be able to access both
    
    return inner()

# This should fail
print(y)
"""

result2 = validator.validate_syntax(code2)
errors2 = [err for err in result2.errors if 'undefined' in err.lower() and 'y' in err]
print(f"Test 2 - Scoping: {len(errors2) > 0}")

# Test 3: Built-ins
code3 = """
# These should all be valid
x = len([1, 2, 3])
y = print("hello")
z = int("42")
"""

result3 = validator.validate_syntax(code3)
print(f"Test 3 - Built-ins recognized: {not any('undefined' in err.lower() for err in result3.errors)}")

# Test 4: Imports
code4 = """
import math
from collections import defaultdict

x = math.pi  # Valid
d = defaultdict(list)  # Valid

# This should fail
arr = numpy.array([1, 2, 3])
"""

result4 = validator.validate_syntax(code4)
numpy_err = any('undefined' in err.lower() and 'numpy' in err for err in result4.errors)
math_ok = not any('undefined' in err.lower() and 'math' in err for err in result4.errors)
print(f"Test 4 - Import tracking: numpy error={numpy_err}, math ok={math_ok}")

# Test 5: Function parameters
code5 = """
def process(data, count=10):
    result = data * count  # Both should be valid
    return result
"""

result5 = validator.validate_syntax(code5)
print(f"Test 5 - Function parameters: {not any('undefined' in err.lower() for err in result5.errors)}")

# Test 6: Loop variables
code6 = """
for i in range(10):
    print(i)  # Valid inside loop

# This should fail - i not available outside loop
print(i)
"""

result6 = validator.validate_syntax(code6)
loop_err = any('undefined' in err.lower() and 'i' in err for err in result6.errors)
print(f"Test 6 - Loop variable scoping: {loop_err}")

# Test 7: Class attributes
code7 = """
class MyClass:
    def method(self):
        return self.value  # self should be valid
    
    @staticmethod
    def static_method():
        # This should fail - no self in static method
        return self.value
"""

result7 = validator.validate_syntax(code7)
static_err = any('undefined' in err.lower() and 'self' in err for err in result7.errors)
print(f"Test 7 - Class self in static method fails: {static_err}")

# Test 8: Global/nonlocal
code8 = """
x = 10

def outer():
    y = 20
    
    def inner():
        global x
        nonlocal y
        x = 100  # Valid
        y = 200  # Valid
        
        # This should fail
        nonlocal z
"""

result8 = validator.validate_syntax(code8)
nonlocal_err = any('no binding' in err.lower() and 'z' in err for err in result8.errors)
print(f"Test 8 - Nonlocal without binding fails: {nonlocal_err}")

# Test 9: Exception variables
code9 = """
try:
    risky()
except ValueError as e:
    print(e)  # Valid in handler
    
# This should fail - e not available outside
print(e)
"""

result9 = validator.validate_syntax(code9)
except_err = any('undefined' in err.lower() and 'e' in err and '8' in err for err in result9.errors)
risky_err = any('undefined' in err.lower() and 'risky' in err for err in result9.errors)
print(f"Test 9 - Exception variable scoping: except_var={except_err}, risky={risky_err}")

# Test 10: Performance - append detection
code10 = """
result = []
for i in range(100):
    result.append(i * 2)
    result.append(i * 3)
"""

suggestions = validator.suggest_improvements(code10)
append_sugg = any('list comprehension' in s and 'result' in s for s in suggestions)
print(f"Test 10 - Append in loop detection: {append_sugg}")

print("\nAll tests completed!")