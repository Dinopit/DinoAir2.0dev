"""
Unit tests for the validator module
"""

import pytest
from unittest.mock import Mock, MagicMock
from pseudocode_translator.validator import (
    Validator, ValidationResult
)


class TestValidationResult:
    """Test the ValidationResult dataclass"""
    
    def test_creation_valid(self):
        """Test creating a valid ValidationResult"""
        result = ValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.line_numbers == []
        assert result.suggestions == []
    
    def test_add_error(self):
        """Test adding errors to validation result"""
        result = ValidationResult(is_valid=True)
        
        result.add_error("Syntax error")
        assert len(result.errors) == 1
        assert result.errors[0] == "Syntax error"
        assert result.is_valid is False
        
        result.add_error("Another error", line_number=10)
        assert len(result.errors) == 2
        assert len(result.line_numbers) == 1
        assert result.line_numbers[0] == 10
    
    def test_add_warning(self):
        """Test adding warnings to validation result"""
        result = ValidationResult(is_valid=True)
        
        result.add_warning("Code smell detected")
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Code smell detected"
        assert result.is_valid is True  # Warnings don't affect validity
    
    def test_add_suggestion(self):
        """Test adding suggestions to validation result"""
        result = ValidationResult(is_valid=True)
        
        result.add_suggestion("Consider using list comprehension")
        assert len(result.suggestions) == 1
        assert result.suggestions[0] == "Consider using list comprehension"


class TestValidator:
    """Test the Validator class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = Mock()
        config.llm = Mock()
        config.llm.validation_level = "normal"
        config.validate_imports = True
        config.check_undefined_vars = True
        config.allow_unsafe_operations = False
        config.max_line_length = 79
        return config
    
    @pytest.fixture
    def validator(self, mock_config):
        """Create a validator instance with mock config"""
        return Validator(mock_config)
    
    def test_initialization(self, validator, mock_config):
        """Test validator initialization"""
        assert validator.config == mock_config
        assert validator.validation_level == "normal"
        assert validator.check_imports is True
        assert validator.check_undefined is True
        assert validator.allow_unsafe is False
    
    def test_validate_syntax_valid_code(self, validator):
        """Test syntax validation with valid code"""
        code = """def add(a, b):
    return a + b

result = add(5, 3)
print(result)"""
        
        result = validator.validate_syntax(code)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_syntax_invalid_code(self, validator):
        """Test syntax validation with invalid code"""
        code = """def add(a, b)  # Missing colon
    return a + b"""
        
        result = validator.validate_syntax(code)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("syntax" in err.lower() for err in result.errors)
    
    def test_validate_syntax_empty_code(self, validator):
        """Test syntax validation with empty code"""
        result = validator.validate_syntax("")
        
        assert result.is_valid is False
        assert any("empty" in err.lower() for err in result.errors)
    
    def test_mixed_indentation_detection(self, validator):
        """Test detection of mixed tabs and spaces"""
        code = """def func():
\tif True:
        return 1"""
        
        result = validator.validate_syntax(code)
        
        assert any("mixed" in err.lower() and "tabs" in err.lower()
                  for err in result.errors)
    
    def test_undefined_variable_detection(self, validator):
        """Test detection of undefined variables"""
        code = """def func():
    return undefined_var"""
        
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "undefined_var" in err
                  for err in result.errors)
    
    def test_undefined_variable_scopes(self, validator):
        """Test undefined variable detection with different scopes"""
        code = """
global_var = 42

def outer():
    outer_var = 10
    
    def inner():
        # Should be able to access outer_var
        return outer_var + global_var
    
    # This should fail - inner_var not defined here
    return inner_var

# This should fail - outer_var not in global scope
print(outer_var)
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "inner_var" in err
                  for err in result.errors)
        assert any("undefined" in err.lower() and "outer_var" in err
                  and "16" in err  # Line 16
                  for err in result.errors)
    
    def test_builtin_recognition(self, validator):
        """Test that built-ins are recognized"""
        code = """
# These should all be valid
x = len([1, 2, 3])
y = print("hello")
z = int("42")
result = sum([1, 2, 3])
"""
        result = validator.validate_syntax(code)
        
        # Should not have undefined errors for built-ins
        assert not any("undefined" in err.lower() and
                      any(builtin in err for builtin in ["len", "print", "int", "sum"])
                      for err in result.errors)
    
    def test_import_tracking(self, validator):
        """Test that imported names are tracked"""
        code = """
import math
from collections import defaultdict
from typing import List, Dict

# These should be valid
x = math.pi
d = defaultdict(list)
numbers: List[int] = []
mapping: Dict[str, int] = {}

# This should fail - numpy not imported
arr = numpy.array([1, 2, 3])
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "numpy" in err
                  for err in result.errors)
        assert not any("undefined" in err.lower() and
                      any(name in err for name in ["math", "defaultdict", "List", "Dict"])
                      for err in result.errors)
    
    def test_function_parameters(self, validator):
        """Test function parameters are recognized in scope"""
        code = """
def process(data, count=10):
    # These should be valid
    result = data * count
    return result

def decorator(func):
    # func should be valid here
    return func

@decorator
def decorated(x, y, *args, **kwargs):
    # All parameters should be valid
    total = x + y
    for arg in args:
        total += arg
    for key, value in kwargs.items():
        total += value
    return total
"""
        result = validator.validate_syntax(code)
        
        # Should not have undefined errors for parameters
        assert not any("undefined" in err.lower() for err in result.errors)
    
    def test_loop_variables(self, validator):
        """Test loop variables are recognized"""
        code = """
# For loop variables
for i in range(10):
    print(i)  # Valid

for key, value in {'a': 1}.items():
    print(key, value)  # Valid

# While loop doesn't define variables
while condition:  # This should fail - condition undefined
    pass

# List comprehension variables
squares = [x**2 for x in range(10)]  # x is valid in comprehension
# But not outside
print(x)  # This should fail
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "condition" in err
                  for err in result.errors)
        assert any("undefined" in err.lower() and "x" in err and "16" in err
                  for err in result.errors)
    
    def test_class_attributes(self, validator):
        """Test class attribute handling"""
        code = """
class MyClass:
    class_var = 42
    
    def __init__(self):
        self.instance_var = 10
    
    def method(self):
        # self should be valid
        return self.instance_var + self.class_var
    
    @classmethod
    def class_method(cls):
        # cls should be valid
        return cls.class_var
    
    @staticmethod
    def static_method():
        # This should fail - no access to self or cls
        return self.instance_var
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "self" in err and "19" in err
                  for err in result.errors)
    
    def test_exception_variables(self, validator):
        """Test exception variable scoping"""
        code = """
try:
    risky_operation()
except ValueError as e:
    print(e)  # Valid in handler
except (TypeError, KeyError) as err:
    print(err)  # Valid
    
# These should fail - exception vars not available outside
print(e)
print(err)
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "risky_operation" in err
                  for err in result.errors)
        assert any("undefined" in err.lower() and "e" in err and "10" in err
                  for err in result.errors)
        assert any("undefined" in err.lower() and "err" in err and "11" in err
                  for err in result.errors)
    
    def test_context_manager_variables(self, validator):
        """Test with statement variable scoping"""
        code = """
with open('file.txt') as f:
    content = f.read()  # f is valid here

# This should fail - f not available outside with block
print(f)

# Multiple context managers
import contextlib
with contextlib.suppress(Exception) as sup1, open('file2.txt') as f2:
    print(sup1, f2)  # Both valid
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "f" in err and "6" in err
                  for err in result.errors)
    
    def test_global_nonlocal_declarations(self, validator):
        """Test global and nonlocal declarations"""
        code = """
global_var = 42

def outer():
    outer_var = 10
    
    def inner():
        global global_var
        nonlocal outer_var
        
        global_var = 100  # Valid
        outer_var = 20    # Valid
        
        # This should fail - no nonlocal binding for this
        nonlocal nonexistent_var
    
    def another_inner():
        # This should work
        nonlocal outer_var
        return outer_var
"""
        result = validator.validate_syntax(code)
        
        assert any("no binding for nonlocal" in err.lower() and "nonexistent_var" in err
                  for err in result.errors)
    
    def test_lambda_scope(self, validator):
        """Test lambda function scoping"""
        code = """
x = 10
# Lambda parameters should be valid inside lambda
f = lambda a, b: a + b + x  # x from outer scope is valid

# List of lambdas capturing loop variable
funcs = [lambda: i for i in range(5)]  # i is valid in lambda

# Nested lambda
g = lambda x: (lambda y: x + y)  # x from outer lambda is valid
"""
        result = validator.validate_syntax(code)
        
        # Should not have undefined errors
        assert not any("undefined" in err.lower() for err in result.errors)
    
    def test_comprehension_scoping(self, validator):
        """Test comprehension variable scoping"""
        code = """
# List comprehension
squares = [x**2 for x in range(10) if x > 5]

# Dict comprehension
d = {k: v for k, v in [('a', 1), ('b', 2)]}

# Set comprehension
s = {x for x in range(10) if x % 2 == 0}

# Generator expression
gen = (x*2 for x in range(5))

# Nested comprehension
matrix = [[i*j for j in range(3)] for i in range(3)]

# Variables from comprehensions shouldn't leak
print(x)  # Should fail
print(k)  # Should fail
print(i)  # Should fail
"""
        result = validator.validate_syntax(code)
        
        for var in ['x', 'k', 'i']:
            assert any("undefined" in err.lower() and var in err
                      for err in result.errors)
    
    def test_forward_references_in_annotations(self, validator):
        """Test forward references in type annotations"""
        code = """
from typing import Optional

class Node:
    def __init__(self, value: int, next: Optional['Node'] = None):
        # 'Node' as string should be valid forward reference
        self.value = value
        self.next = next
    
    def set_parent(self, parent: 'Node') -> None:
        # Forward reference should be valid
        self.parent = parent

def process(node: Node) -> Node:
    # Regular reference after definition is valid
    return node
"""
        result = validator.validate_syntax(code)
        
        # Should not have errors for forward references
        assert not any("undefined" in err.lower() and "Node" in err
                      for err in result.errors)
    
    def test_async_function_scope(self, validator):
        """Test async function scoping"""
        code = """
import asyncio

async def fetch_data(url):
    # url parameter should be valid
    response = await asyncio.sleep(1)
    return url + " fetched"

async def process_many(*urls):
    # urls should be valid
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results
"""
        result = validator.validate_syntax(code)
        
        # Should not have undefined errors
        assert not any("undefined" in err.lower() for err in result.errors)
    
    def test_order_of_definition(self, validator):
        """Test that order of definition matters"""
        code = """
# Using before definition should fail
print(later_var)

later_var = 42

def func():
    # Using before definition in function
    x = y + 1  # Should fail
    y = 10
    return x

class MyClass:
    # Using method before definition is OK in class
    def method1(self):
        return self.method2()
    
    def method2(self):
        return 42
"""
        result = validator.validate_syntax(code)
        
        assert any("undefined" in err.lower() and "later_var" in err and "3" in err
                  for err in result.errors)
        assert any("undefined" in err.lower() and "y" in err and "9" in err
                  for err in result.errors)
    
    def test_performance_append_detection(self, validator):
        """Test detection of repeated append in loops"""
        code = """
# This should get a performance suggestion
result = []
for i in range(100):
    result.append(i * 2)
    result.append(i * 3)

# Another list with appends
data = []
for item in items:
    if item > 0:
        data.append(item)
        data.append(item ** 2)

# This is fine - list comprehension
squares = [x**2 for x in range(10)]
"""
        suggestions = validator.suggest_improvements(code)
        
        # Should suggest list comprehension for repeated appends
        assert any("list comprehension" in s and "result" in s
                  for s in suggestions)
        assert any("list comprehension" in s and "data" in s
                  for s in suggestions)
    
    def test_import_validation(self, validator):
        """Test import validation"""
        code = """import os
import os  # Duplicate
from sys import *  # Wildcard"""
        
        result = validator.validate_syntax(code)
        
        # Should have warnings about duplicate and wildcard imports
        assert any("duplicate" in warn.lower() for warn in result.warnings)
        assert any("wildcard" in warn.lower() for warn in result.warnings)
    
    def test_unsafe_operations_detection(self, validator):
        """Test detection of unsafe operations"""
        code = """import os
os.system('rm -rf /')  # Dangerous!
eval(user_input)"""
        
        result = validator.validate_syntax(code)
        
        assert result.is_valid is False
        assert any("unsafe" in err.lower() for err in result.errors)
    
    def test_unsafe_operations_allowed(self, mock_config):
        """Test when unsafe operations are allowed"""
        mock_config.allow_unsafe_operations = True
        validator = Validator(mock_config)
        
        code = """eval("2 + 2")"""
        
        result = validator.validate_syntax(code)
        # Should not have errors about unsafe operations
        assert not any("unsafe" in err.lower() for err in result.errors)
    
    def test_validate_logic_valid_code(self, validator):
        """Test logic validation with valid code"""
        code = """def calculate(x, y):
    if x > 0:
        return x + y
    else:
        return x - y"""
        
        result = validator.validate_logic(code)
        
        assert result.is_valid is True
    
    def test_validate_logic_unreachable_code(self, validator):
        """Test detection of unreachable code"""
        code = """def func():
    return 1
    print("This is unreachable")"""
        
        result = validator.validate_logic(code)
        
        assert any("unreachable" in warn.lower() for warn in result.warnings)
    
    def test_validate_logic_infinite_loop(self, validator):
        """Test detection of infinite loops"""
        code = """def func():
    while True:
        print("Forever")"""
        
        result = validator.validate_logic(code)
        
        assert any("infinite" in warn.lower() and "loop" in warn.lower() 
                  for warn in result.warnings)
    
    def test_validate_logic_missing_return(self, validator):
        """Test detection of missing return statements"""
        code = """def calculate(x: int) -> int:
    if x > 0:
        print("Positive")
    # Missing return"""
        
        result = validator.validate_logic(code)
        
        assert any("return" in warn.lower() for warn in result.warnings)
    
    def test_validate_logic_invalid_syntax(self, validator):
        """Test logic validation on syntactically invalid code"""
        code = "def func( invalid syntax"
        
        result = validator.validate_logic(code)
        
        assert result.is_valid is False
        assert any("cannot perform logic validation" in err.lower() 
                  for err in result.errors)
    
    def test_suggest_improvements_basic(self, validator):
        """Test basic improvement suggestions"""
        code = """def MyFunction(x,y):
    if x>0:return x+y
    else:return x-y"""
        
        suggestions = validator.suggest_improvements(code)
        
        # Should suggest PEP 8 improvements
        assert len(suggestions) > 0
        assert any("space" in s.lower() for s in suggestions)
    
    def test_suggest_improvements_performance(self, validator):
        """Test performance improvement suggestions"""
        code = """def process_list(items):
    result = []
    for i in range(len(items)):
        result.append(items[i] * 2)
    return result"""
        
        suggestions = validator.suggest_improvements(code)
        
        assert any("enumerate" in s.lower() or "range(len(" in s 
                  for s in suggestions)
    
    def test_suggest_improvements_best_practices(self, validator):
        """Test best practices suggestions"""
        code = """def func(lst=[]):
    lst.append(1)
    return lst
    
if type(x) == int:
    pass"""
        
        suggestions = validator.suggest_improvements(code)
        
        assert any("mutable default" in s.lower() for s in suggestions)
        assert any("isinstance" in s.lower() for s in suggestions)
    
    def test_suggest_improvements_security(self, validator):
        """Test security suggestions"""
        code = """password = "hardcoded123"
query = "SELECT * FROM users WHERE id = %s" % user_id"""
        
        suggestions = validator.suggest_improvements(code)
        
        assert any("password" in s.lower() for s in suggestions)
        assert any("sql" in s.lower() or "parameterized" in s.lower() 
                  for s in suggestions)
    
    def test_code_smell_detection(self, validator):
        """Test detection of code smells"""
        code = """try:
    risky_operation()
except:  # Bare except
    pass
    
from module import *  # Wildcard import
global some_var  # Global usage"""
        
        result = validator.validate_syntax(code)
        
        assert any("bare except" in warn.lower() for warn in result.warnings)
        assert any("wildcard" in warn.lower() for warn in result.warnings)
        assert any("global" in warn.lower() for warn in result.warnings)
    
    def test_long_line_detection(self, validator):
        """Test detection of long lines"""
        code = 'x = "This is a very long line that definitely exceeds the maximum line length limit set in the configuration"'
        
        result = validator.validate_syntax(code)
        
        assert any("exceeds" in warn and "characters" in warn 
                  for warn in result.warnings)
    
    def test_validation_levels(self, mock_config):
        """Test different validation levels"""
        # Test strict level
        mock_config.llm.validation_level = "strict"
        strict_validator = Validator(mock_config)
        
        code = """def func():
    unused_var = 42
    return 1"""
        
        result = strict_validator.validate_logic(code)
        assert any("unused" in warn.lower() for warn in result.warnings)
        
        # Test lenient level
        mock_config.llm.validation_level = "lenient"
        lenient_validator = Validator(mock_config)
        
        result = lenient_validator.validate_logic(code)
        # Should have fewer warnings in lenient mode
        assert not any("unused" in warn.lower() for warn in result.warnings)


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def validator(self):
        config = Mock()
        config.llm = Mock()
        config.llm.validation_level = "normal"
        config.validate_imports = True
        config.check_undefined_vars = True
        config.allow_unsafe_operations = False
        config.max_line_length = 79
        return Validator(config)
    
    def test_unicode_in_code(self, validator):
        """Test handling of Unicode in code"""
        code = """def greet():
    return "Hello, 世界! 🌍"
    
# Comment with émojis 😊"""
        
        result = validator.validate_syntax(code)
        # Should handle Unicode without crashing
        assert result is not None
    
    def test_very_long_code(self, validator):
        """Test handling of very long code"""
        # Generate a very long but valid code
        code = "x = 1\n" * 10000
        
        result = validator.validate_syntax(code)
        assert result is not None
    
    def test_malformed_python(self, validator):
        """Test handling of severely malformed Python"""
        code = """def (((: ??? !!!
class ]]][ :::: ****"""
        
        result = validator.validate_syntax(code)
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_empty_functions(self, validator):
        """Test handling of empty functions"""
        code = """def empty1():
    
def empty2():
    ...
    
def empty3():
    pass"""
        
        result = validator.validate_syntax(code)
        # Empty functions with pass or ... should be valid
        assert "empty3" not in str(result.errors)
    
    def test_nested_structures(self, validator):
        """Test deeply nested structures"""
        code = """def outer():
    def middle():
        def inner():
            def very_inner():
                return 42
            return very_inner()
        return inner()
    return middle()"""
        
        result = validator.validate_syntax(code)
        assert result.is_valid is True
    
    def test_complex_expressions(self, validator):
        """Test complex expressions"""
        code = """result = (lambda x: (x * 2 + 3) if x > 0 else (x - 1) * -1)(
    sum([i ** 2 for i in range(10) if i % 2 == 0])
)"""
        
        result = validator.validate_syntax(code)
        # Should validate complex but valid expressions
        assert result.is_valid is True
    
    def test_type_annotations(self, validator):
        """Test handling of type annotations"""
        code = """from typing import List, Dict, Optional, Union

def process(
    data: List[Dict[str, Union[int, float]]],
    flag: Optional[bool] = None
) -> Dict[str, Any]:
    return {}"""
        
        result = validator.validate_syntax(code)
        assert result.is_valid is True
    
    def test_async_code(self, validator):
        """Test handling of async code"""
        code = """import asyncio

async def fetch_data():
    await asyncio.sleep(1)
    return "data"
    
async def main():
    result = await fetch_data()
    print(result)"""
        
        result = validator.validate_syntax(code)
        assert result.is_valid is True
    
    def test_decorators(self, validator):
        """Test handling of decorators"""
        code = """from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
@property
def decorated_property(self):
    return self._value"""
        
        result = validator.validate_syntax(code)
        assert result.is_valid is True


@pytest.mark.parametrize("code,expected_valid", [
    ("x = 1", True),
    ("def func(): pass", True),
    ("def func(", False),
    ("class MyClass: pass", True),
    ("import sys; sys.exit()", True),
    ("eval('dangerous')", False),  # Unsafe operation
    ("1 / 0", True),  # Valid syntax, runtime error
])
def test_various_code_snippets(code, expected_valid):
    """Parametrized test for various code snippets"""
    config = Mock()
    config.llm = Mock()
    config.llm.validation_level = "normal"
    config.validate_imports = True
    config.check_undefined_vars = False  # Disable for simple tests
    config.allow_unsafe_operations = False
    config.max_line_length = 79
    
    validator = Validator(config)
    result = validator.validate_syntax(code)
    
    assert result.is_valid == expected_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])