#!/usr/bin/env python3
"""Direct test of undefined variable checking without full module imports."""

import sys
import os
import ast

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Directly copy the Scope and UndefinedVariableChecker classes to test them
class Scope:
    """Represents a scope (module, function, class, etc.)."""
    
    def __init__(self, parent=None, name='<module>'):
        self.parent = parent
        self.name = name
        self.definitions = set()
        self.usages = {}  # {name: [(line, col)]}
        self.imports = set()
        self.nonlocals = set()
        self.globals = set()
        
    def define(self, name):
        """Mark a name as defined in this scope."""
        self.definitions.add(name)
        
    def use(self, name, line, col):
        """Record usage of a name."""
        if name not in self.usages:
            self.usages[name] = []
        self.usages[name].append((line, col))
        
    def is_defined_locally(self, name):
        """Check if name is defined in this scope."""
        return name in self.definitions
        
    def is_defined(self, name):
        """Check if name is defined in this or any parent scope."""
        if self.is_defined_locally(name):
            return True
        if self.parent:
            return self.parent.is_defined(name)
        return False
        
    def mark_nonlocal(self, name):
        """Mark a name as nonlocal."""
        self.nonlocals.add(name)
        
    def mark_global(self, name):
        """Mark a name as global."""
        self.globals.add(name)

class UndefinedVariableChecker(ast.NodeVisitor):
    """AST visitor to check for undefined variables."""
    
    def __init__(self):
        self.current_scope = Scope()
        self.errors = []
        self.builtins = {
            'print', 'len', 'range', 'str', 'int', 'float', 'bool',
            'list', 'dict', 'set', 'tuple', 'type', 'isinstance',
            'hasattr', 'getattr', 'setattr', 'delattr', 'dir',
            'help', 'abs', 'all', 'any', 'bin', 'hex', 'oct',
            'chr', 'ord', 'min', 'max', 'sum', 'round', 'sorted',
            'reversed', 'enumerate', 'zip', 'map', 'filter',
            'open', 'input', 'eval', 'exec', 'compile', 'globals',
            'locals', 'vars', 'id', 'hash', 'iter', 'next',
            'callable', 'classmethod', 'staticmethod', 'property',
            'super', 'object', 'Exception', 'BaseException',
            'True', 'False', 'None', '__name__', '__file__',
            '__doc__', '__import__', '__builtins__'
        }
        self.in_function_signature = False
        self.in_annotation = False
        
    def push_scope(self, name='<scope>'):
        """Enter a new scope."""
        self.current_scope = Scope(self.current_scope, name)
        
    def pop_scope(self):
        """Exit current scope and check for undefined names."""
        # Check all usages in this scope
        for name, locations in self.current_scope.usages.items():
            if name in self.builtins:
                continue
                
            # Skip if it's defined locally
            if self.current_scope.is_defined_locally(name):
                continue
                
            # For nonlocal/global, check parent scopes
            if name in self.current_scope.nonlocals:
                if not (self.current_scope.parent and 
                       self.current_scope.parent.is_defined(name)):
                    for line, col in locations:
                        self.errors.append(
                            f"Line {line}: SyntaxError: no binding for "
                            f"nonlocal '{name}' found"
                        )
                continue
                
            if name in self.current_scope.globals:
                # Check if defined at module level
                scope = self.current_scope
                while scope.parent:
                    scope = scope.parent
                if not scope.is_defined_locally(name):
                    for line, col in locations:
                        self.errors.append(
                            f"Line {line}: NameError: name '{name}' is "
                            f"not defined (marked as global but not "
                            f"defined at module level)"
                        )
                continue
                
            # Check parent scopes
            if not self.current_scope.is_defined(name):
                for line, col in locations:
                    self.errors.append(
                        f"Line {line}: NameError: name '{name}' is "
                        f"not defined"
                    )
                    
        # Return to parent scope
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
    
    def visit_Import(self, node):
        """Handle import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            # Handle 'import x.y.z as name' - only 'name' is defined
            # Handle 'import x.y.z' - only 'x' is defined
            if alias.asname:
                self.current_scope.define(alias.asname)
            else:
                self.current_scope.define(alias.name.split('.')[0])
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        """Handle from...import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.current_scope.define(name)
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        """Handle function definitions."""
        # Define function name in current scope
        self.current_scope.define(node.name)
        
        # Process decorators in current scope
        for decorator in node.decorator_list:
            self.visit(decorator)
            
        # Enter function scope
        self.push_scope(f'function {node.name}')
        
        # Process parameters
        self.in_function_signature = True
        for arg in node.args.args:
            self.current_scope.define(arg.arg)
            if arg.annotation:
                self.in_annotation = True
                self.visit(arg.annotation)
                self.in_annotation = False
                
        if node.args.vararg:
            self.current_scope.define(node.args.vararg.arg)
            if node.args.vararg.annotation:
                self.in_annotation = True
                self.visit(node.args.vararg.annotation)
                self.in_annotation = False
                
        if node.args.kwarg:
            self.current_scope.define(node.args.kwarg.arg)
            if node.args.kwarg.annotation:
                self.in_annotation = True  
                self.visit(node.args.kwarg.annotation)
                self.in_annotation = False
                
        # Process defaults in parent scope
        self.in_function_signature = False
        parent_scope = self.current_scope.parent
        self.current_scope = parent_scope
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default:
                self.visit(default)
        self.current_scope = parent_scope
        
        # Process return annotation
        if node.returns:
            self.in_annotation = True
            self.visit(node.returns)
            self.in_annotation = False
            
        # Process body
        for stmt in node.body:
            self.visit(stmt)
            
        self.pop_scope()
        
    def visit_AsyncFunctionDef(self, node):
        """Handle async function definitions."""
        self.visit_FunctionDef(node)  # Same logic
        
    def visit_ClassDef(self, node):
        """Handle class definitions."""
        # Define class name in current scope
        self.current_scope.define(node.name)
        
        # Process decorators in current scope
        for decorator in node.decorator_list:
            self.visit(decorator)
            
        # Process bases in current scope  
        for base in node.bases:
            self.visit(base)
            
        # Enter class scope
        self.push_scope(f'class {node.name}')
        
        # Process body
        for stmt in node.body:
            self.visit(stmt)
            
        self.pop_scope()
        
    def visit_Name(self, node):
        """Handle name references."""
        if isinstance(node.ctx, ast.Store):
            self.current_scope.define(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Don't check undefined names in annotations (forward refs)
            if not self.in_annotation:
                self.current_scope.use(node.id, node.lineno, 
                                     node.col_offset)
        self.generic_visit(node)
        
    def visit_For(self, node):
        """Handle for loops."""
        # Visit iterator first
        self.visit(node.iter)
        # Then define loop variable
        self.visit(node.target)
        # Then body
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
            
    def visit_comprehension(self, node):
        """Handle comprehensions."""
        # Visit iterator first
        self.visit(node.iter)
        # Then define loop variable
        self.visit(node.target)
        # Then conditions
        for cond in node.ifs:
            self.visit(cond)
            
    def visit_ListComp(self, node):
        """Handle list comprehensions."""
        self.push_scope('<listcomp>')
        # Process generators
        for gen in node.generators:
            self.visit_comprehension(gen)
        # Process element
        self.visit(node.elt)
        self.pop_scope()
        
    def visit_SetComp(self, node):
        """Handle set comprehensions."""
        self.push_scope('<setcomp>')
        for gen in node.generators:
            self.visit_comprehension(gen)
        self.visit(node.elt)
        self.pop_scope()
        
    def visit_DictComp(self, node):
        """Handle dict comprehensions."""
        self.push_scope('<dictcomp>')
        for gen in node.generators:
            self.visit_comprehension(gen)
        self.visit(node.key)
        self.visit(node.value)
        self.pop_scope()
        
    def visit_GeneratorExp(self, node):
        """Handle generator expressions."""
        self.push_scope('<genexpr>')
        for gen in node.generators:
            self.visit_comprehension(gen)
        self.visit(node.elt)
        self.pop_scope()
        
    def visit_Lambda(self, node):
        """Handle lambda expressions."""
        self.push_scope('<lambda>')
        # Define parameters
        for arg in node.args.args:
            self.current_scope.define(arg.arg)
        if node.args.vararg:
            self.current_scope.define(node.args.vararg.arg)
        if node.args.kwarg:
            self.current_scope.define(node.args.kwarg.arg)
        # Visit body
        self.visit(node.body)
        self.pop_scope()
        
    def visit_ExceptHandler(self, node):
        """Handle exception handlers."""
        if node.type:
            self.visit(node.type)
        if node.name:
            # Exception variable is local to except block
            old_scope = self.current_scope
            self.push_scope('<except>')
            self.current_scope.define(node.name)
            for stmt in node.body:
                self.visit(stmt)
            self.pop_scope()
        else:
            for stmt in node.body:
                self.visit(stmt)
                
    def visit_With(self, node):
        """Handle with statements."""
        for item in node.items:
            self.visit(item.context_expr)
            if item.optional_vars:
                self.visit(item.optional_vars)
        for stmt in node.body:
            self.visit(stmt)
            
    def visit_Global(self, node):
        """Handle global statements."""
        for name in node.names:
            self.current_scope.mark_global(name)
            
    def visit_Nonlocal(self, node):
        """Handle nonlocal statements."""
        for name in node.names:
            self.current_scope.mark_nonlocal(name)

def check_undefined_names(code_str):
    """Check for undefined variable names in code."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]
        
    checker = UndefinedVariableChecker()
    checker.visit(tree)
    checker.pop_scope()  # Final check for module scope
    
    return checker.errors

def run_test(test_name, code, expected_errors=None, expected_no_errors=None):
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    print("Code:")
    print(code)
    print("-" * 40)
    
    errors = check_undefined_names(code)
    
    print("Errors found:")
    if errors:
        for err in errors:
            print(f"  - {err}")
    else:
        print("  None")
    
    # Check expectations
    success = True
    if expected_errors:
        for expected in expected_errors:
            found = any(expected in err for err in errors)
            if not found:
                print(f"❌ Expected error containing '{expected}' not found")
                success = False
            else:
                print(f"✓ Found expected error: '{expected}'")
                
    if expected_no_errors:
        for not_expected in expected_no_errors:
            found = any(not_expected in err for err in errors)
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
        expected_errors=["'y' is not defined"]
    )
    
    # Test 2: Variable used before definition
    all_passed &= run_test(
        "Variable used before definition",
        """
print(x)  # x used before definition
x = 5
y = z + 1  # z is undefined
""",
        expected_errors=["'x' is not defined", "'z' is not defined"]
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
        expected_errors=["'numpy' is not defined"],
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
        expected_errors=["'c' is not defined"],
        expected_no_errors=["'a'", "'b'", "'x'", "'y'"]
    )
    
    # Test 6: Loop variables
    all_passed &= run_test(
        "Loop variables",
        """
for i in range(10):
    print(i)  # i is defined
    
print(i)  # i still accessible after loop
print(j)  # j is undefined
""",
        expected_errors=["'j' is not defined"],
        expected_no_errors=["'i'"]
    )
    
    # Test 7: Class attributes
    all_passed &= run_test(
        "Class attributes",
        """
class MyClass:
    class_var = 42
    
    def method(self):
        return self.class_var
        
    def static():  # missing @staticmethod, self undefined
        return self.data
""",
        expected_errors=["'self' is not defined"]
    )
    
    # Test 8: Global and nonlocal
    all_passed &= run_test(
        "Global and nonlocal",
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
        expected_errors=["no binding for nonlocal 'z'"]
    )
    
    # Test 9: Exception variables
    all_passed &= run_test(
        "Exception variable scoping",
        """
try:
    risky_operation()
except Exception as e:
    print(e)  # e is defined here
    
print(e)  # e is not accessible outside except block
""",
        expected_errors=["'risky_operation' is not defined", "'e' is not defined"],
    )
    
    # Test 10: Comprehensions
    all_passed &= run_test(
        "Comprehensions",
        """
data = [1, 2, 3]
squares = [x**2 for x in data]
filtered = [y for y in squares if y > 2]

# x is not accessible outside comprehension
print(x)  
""",
        expected_errors=["'x' is not defined"],
        expected_no_errors=["data", "squares"]
    )
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed.")
    print("="*60)

if __name__ == "__main__":
    main()