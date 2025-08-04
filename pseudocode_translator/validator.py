"""
Validator module for the Pseudocode Translator

This module handles validation of generated Python code, including
syntax validation, logic checks, and improvement suggestions.
"""

import ast
import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
import tokenize
from io import StringIO
from functools import lru_cache
import threading

from .config import TranslatorConfig
from .ast_cache import parse_cached
from .exceptions import ValidationError, ErrorContext


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    line_numbers: List[int] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_error(self, error: str, line_number: Optional[int] = None):
        """Add an error to the validation result"""
        self.errors.append(error)
        if line_number is not None:
            self.line_numbers.append(line_number)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the validation result"""
        self.warnings.append(warning)
    
    def add_suggestion(self, suggestion: str):
        """Add an improvement suggestion"""
        self.suggestions.append(suggestion)


class Validator:
    """
    Validates Python code syntax and basic semantics
    """
    
    def __init__(self, config: TranslatorConfig):
        """
        Initialize the Validator
        
        Args:
            config: Translator configuration object
        """
        self.config = config
        self.validation_level = config.llm.validation_level
        self.check_imports = config.validate_imports
        self.check_undefined = config.check_undefined_vars
        self.allow_unsafe = config.allow_unsafe_operations
        
        # Common unsafe operations
        self.unsafe_patterns = [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\b__import__\s*\(',
            r'\bcompile\s*\(',
            r'\bopen\s*\([^,)]*["\']w["\']',  # Writing files
            r'\bos\.(system|popen|exec)',
            r'\bsubprocess\.(run|call|Popen)',
            r'\bshutil\.rmtree',
            r'\bos\.remove',
        ]
        
        # Common code smells (compiled patterns for performance)
        self.code_smells = {
            re.compile(r'except\s*:'):
                "Bare except clause - specify exception types",
            re.compile(r'import\s+\*'):
                "Wildcard imports - consider explicit imports",
            re.compile(r'global\s+'):
                "Global variable usage - consider refactoring",
            re.compile(r'pass\s*$'):
                "Empty code block - add implementation or remove",
            re.compile(r'TODO|FIXME|XXX'):
                "Unfinished code markers found",
            re.compile(r'print\s*\(.*\)\s*#\s*debug'):
                "Debug print statements found",
        }
        
        # Pre-compile common patterns for performance
        self._import_pattern = re.compile(r'^\s*(import|from)\s+')
        self._function_pattern = re.compile(r'^\s*def\s+([A-Za-z_]\w*)')
        self._class_pattern = re.compile(r'^\s*class\s+([A-Za-z_]\w*)')
        
        # Cache for validation results
        self._validation_cache = {}
        self._cache_lock = threading.Lock()
        self._max_cache_size = 100
    
    def validate_syntax(self, code: str) -> ValidationResult:
        """
        Validate Python code syntax
        
        Args:
            code: Python code to validate
            
        Returns:
            ValidationResult with syntax validation details
        """
        # Check cache first
        cache_key = self._get_cache_key(code, 'syntax')
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        result = ValidationResult(is_valid=True)
        
        if not code or not code.strip():
            result.add_error("Empty code provided")
            self._cache_result(cache_key, result)
            return result
        
        # Step 1: Basic syntax validation using ast
        try:
            tree = parse_cached(code)
            logger.debug("AST parsing successful")
        except SyntaxError as e:
            # Create ValidationError with rich context
            lines = code.splitlines()
            context = ErrorContext(
                line_number=e.lineno,
                column_number=e.offset,
                code_snippet=(
                    lines[e.lineno - 1]
                    if e.lineno and e.lineno <= len(lines)
                    else None
                ),
                surrounding_lines=(
                    self._get_surrounding_lines(lines, e.lineno)
                    if e.lineno else []
                )
            )
            
            error = ValidationError(
                f"Syntax error: {e.msg}",
                validation_type="syntax",
                failed_code=code,
                context=context,
                cause=e
            )
            
            # Add automatic suggestions
            self._add_syntax_suggestions(error, e, code)
            
            result.add_error(error.format_error())
            return result
        except Exception as e:
            error = ValidationError(
                f"Failed to parse code: {str(e)}",
                validation_type="syntax",
                failed_code=code,
                cause=e
            )
            error.add_suggestion("Check for severe syntax errors")
            error.add_suggestion("Ensure the code is valid Python")
            
            result.add_error(error.format_error())
            return result
        
        # Step 2: Check for indentation errors
        indentation_errors = self._check_indentation(code)
        for error in indentation_errors:
            result.add_error(error)
        
        # Step 3: Check for undefined names (if enabled)
        if self.check_undefined:
            undefined_errors = self._check_undefined_names(tree, code)
            for error in undefined_errors:
                result.add_error(error)
        
        # Step 4: Check imports (if enabled)
        if self.check_imports:
            import_errors = self._check_imports(tree)
            for error in import_errors:
                result.add_warning(error)
        
        # Step 5: Check for common issues based on validation level
        if self.validation_level in ["strict", "normal"]:
            common_issues = self._check_common_issues(code)
            for issue in common_issues:
                result.add_warning(issue)
        
        # Step 6: Check for unsafe operations (if not allowed)
        if not self.allow_unsafe:
            unsafe_ops = self._check_unsafe_operations(code)
            for op in unsafe_ops:
                result.add_error(f"Unsafe operation detected: {op}")
        
        # Step 7: Tokenization check for additional issues
        tokenization_errors = self._check_tokenization(code)
        for error in tokenization_errors:
            result.add_error(error)
        
        # Cache the result
        self._cache_result(cache_key, result)
        return result
    
    def validate_logic(self, code: str) -> ValidationResult:
        """
        Validate code logic and potential runtime issues
        
        Args:
            code: Python code to validate
            
        Returns:
            ValidationResult with logic validation details
        """
        # Check cache first
        cache_key = self._get_cache_key(code, 'logic')
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
            
        result = ValidationResult(is_valid=True)
        
        try:
            tree = parse_cached(code)
        except (SyntaxError, ValueError):
            # If syntax is invalid, can't do logic validation
            error = ValidationError(
                "Cannot perform logic validation on "
                "syntactically invalid code",
                validation_type="logic"
            )
            error.add_suggestion("Fix syntax errors first")
            error.add_suggestion(
                "Run syntax validation to see specific errors"
            )
            
            result.add_error(error.format_error())
            return result
        
        # Check for common logic issues
        logic_issues = []
        
        # 1. Unreachable code
        unreachable = self._find_unreachable_code(tree)
        for issue in unreachable:
            logic_issues.append(f"Unreachable code detected: {issue}")
        
        # 2. Unused variables
        if self.validation_level == "strict":
            unused = self._find_unused_variables(tree)
            for var in unused:
                logic_issues.append(f"Unused variable: {var}")
        
        # 3. Infinite loops
        infinite_loops = self._detect_infinite_loops(tree)
        for loop in infinite_loops:
            logic_issues.append(f"Potential infinite loop detected: {loop}")
        
        # 4. Missing return statements
        missing_returns = self._check_missing_returns(tree)
        for func in missing_returns:
            logic_issues.append(
                f"Function '{func}' may be missing return statement"
            )
        
        # 5. Type inconsistencies (basic check)
        type_issues = self._check_basic_type_consistency(tree)
        for issue in type_issues:
            logic_issues.append(issue)
        
        # Add all issues as warnings
        for issue in logic_issues:
            result.add_warning(issue)
        
        # Check for potential runtime errors
        runtime_risks = self._check_runtime_risks(tree)
        for risk in runtime_risks:
            result.add_warning(f"Potential runtime error: {risk}")
        
        # Cache the result
        self._cache_result(cache_key, result)
        return result
    
    def suggest_improvements(self, code: str) -> List[str]:
        """
        Suggest improvements for the code
        
        Args:
            code: Python code to analyze
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        try:
            tree = parse_cached(code)
        except (SyntaxError, ValueError):
            return ["Fix syntax errors before requesting improvements"]
        
        # 1. PEP 8 style suggestions
        style_suggestions = self._check_style(code)
        suggestions.extend(style_suggestions)
        
        # 2. Performance suggestions
        perf_suggestions = self._check_performance(tree, code)
        suggestions.extend(perf_suggestions)
        
        # 3. Readability suggestions
        readability_suggestions = self._check_readability(tree, code)
        suggestions.extend(readability_suggestions)
        
        # 4. Best practices suggestions
        best_practices = self._check_best_practices(tree, code)
        suggestions.extend(best_practices)
        
        # 5. Security suggestions
        security_suggestions = self._check_security(code)
        suggestions.extend(security_suggestions)
        
        # Remove duplicates and return
        return list(dict.fromkeys(suggestions))
    
    def _check_indentation(self, code: str) -> List[str]:
        """Check for indentation errors with detailed context"""
        errors = []
        lines = code.splitlines()
        
        # Track indentation levels
        indent_stack = [0]
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Get indentation level
            indent = len(line) - len(line.lstrip())
            
            # Check for mixed tabs and spaces
            if '\t' in line and ' ' in line[:indent]:
                context = ErrorContext(
                    line_number=i,
                    code_snippet=line,
                    surrounding_lines=self._get_surrounding_lines(lines, i)
                )
                
                error = ValidationError(
                    "Mixed tabs and spaces in indentation",
                    validation_type="syntax",
                    context=context
                )
                error.add_suggestion(
                    "Use only spaces for indentation "
                    "(PEP 8 recommendation)"
                )
                error.add_suggestion(
                    "Configure your editor to convert tabs to spaces"
                )
                
                errors.append(error.format_error(include_context=False))
            
            # Check for inconsistent indentation
            if stripped.endswith(':'):
                indent_stack.append(indent + self.config.indent_size)
            elif indent not in indent_stack:
                if indent < indent_stack[-1]:
                    # Dedent - find matching level
                    while indent_stack and indent < indent_stack[-1]:
                        indent_stack.pop()
                    if not indent_stack or indent != indent_stack[-1]:
                        context = ErrorContext(
                            line_number=i,
                            code_snippet=line,
                            surrounding_lines=self._get_surrounding_lines(
                                lines, i
                            )
                        )
                        
                        error = ValidationError(
                            "Inconsistent indentation",
                            validation_type="syntax",
                            context=context
                        )
                        error.add_suggestion(
                            f"Use {self.config.indent_size} spaces per "
                            f"indentation level"
                        )
                        error.add_suggestion(
                            "Check that dedent aligns with a previous "
                            "indentation level"
                        )
                        
                        errors.append(
                            error.format_error(include_context=False)
                        )
                else:
                    context = ErrorContext(
                        line_number=i,
                        code_snippet=line,
                        surrounding_lines=self._get_surrounding_lines(
                            lines, i
                        )
                    )
                    
                    error = ValidationError(
                        "Unexpected indentation level",
                        validation_type="syntax",
                        context=context
                    )
                    error.add_suggestion(
                        "Ensure proper nesting of code blocks"
                    )
                    error.add_suggestion("Check for missing or extra colons")
                    
                    errors.append(error.format_error(include_context=False))
        
        return errors
    
    def _get_surrounding_lines(
        self, lines: List[str], line_no: int,
        context_size: int = 2
    ) -> List[str]:
        """Get surrounding lines for error context"""
        if not line_no or line_no <= 0:
            return []
        
        start = max(0, line_no - 1 - context_size)
        end = min(len(lines), line_no + context_size)
        return lines[start:end]
    
    def _add_syntax_suggestions(
        self, error: ValidationError,
        syntax_error: SyntaxError,
        code: str
    ):
        """Add suggestions based on the syntax error"""
        msg = syntax_error.msg.lower()
        
        if "invalid syntax" in msg:
            suggestion = self._suggest_syntax_fix(code, syntax_error)
            if suggestion:
                error.add_suggestion(suggestion)
        
        if "unexpected indent" in msg:
            error.add_suggestion("Check indentation consistency")
            error.add_suggestion("Ensure all blocks are properly aligned")
        
        if "expected an indented block" in msg:
            error.add_suggestion("Add indented code after the colon (:)")
            error.add_suggestion("Use 'pass' if the block should be empty")
    
    def _check_undefined_names(self, tree: ast.AST, code: str) -> List[str]:
        """
        Check for undefined variable names with proper scope tracking
        
        This implementation handles:
        - Different scopes (global, function, class)
        - Order of definition and usage
        - Built-in functions and variables
        - Imported names
        - Function parameters and decorators
        - Loop variables
        - Class attributes
        - Comprehension variables
        - Exception variables
        - Context manager variables
        """
        errors = []
        
        # Built-in names that are always available
        builtins = set(dir(__builtins__))
        
        # Additional common built-ins that might not be in dir(__builtins__)
        builtins.update({
            'self', 'cls', '__name__', '__file__', '__doc__', '__package__',
            '__loader__', '__spec__', '__annotations__', '__cached__'
        })
        
        # Add modern type annotation names (Python 3.9+)
        builtins.update({
            'Union', 'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet',
            'Type', 'Callable', 'Any', 'TypeVar', 'Generic', 'Protocol',
            'Literal', 'Final', 'TypedDict', 'NotRequired', 'Required',
            'Annotated', 'TypeAlias', 'ParamSpec', 'TypeVarTuple', 'Unpack',
            'Self', 'Never', 'assert_type', 'assert_never', 'reveal_type'
        })
        
        class Scope:
            """Represents a scope in the code"""
            def __init__(self, name: str, parent: Optional['Scope'] = None):
                self.name = name
                self.parent = parent
                self.defined: Dict[str, int] = {}  # name -> line defined
                self.used: Dict[str, List[int]] = {}  # name -> lines used
                self.imported: Set[str] = set()
                self.nonlocal_vars: Set[str] = set()
                self.global_vars: Set[str] = set()
                
            def define(self, name: str, line: int):
                """Mark a variable as defined in this scope"""
                if name not in self.defined or line < self.defined[name]:
                    self.defined[name] = line
                    
            def use(self, name: str, line: int):
                """Mark a variable as used in this scope"""
                if name not in self.used:
                    self.used[name] = []
                self.used[name].append(line)
                
            def is_defined(self, name: str, line: int) -> bool:
                """Check if a name is defined at a given line"""
                # Check if it's a global or nonlocal declaration
                if name in self.global_vars:
                    return self._check_global(name, line)
                if name in self.nonlocal_vars:
                    return self._check_nonlocal(name, line)
                    
                # Check local scope
                if name in self.defined and self.defined[name] <= line:
                    return True
                if name in self.imported:
                    return True
                    
                # Check parent scopes for closure variables
                if self.parent:
                    return self.parent.is_defined(name, line)
                    
                return False
                
            def _check_global(self, name: str, line: int) -> bool:
                """Check if a global variable is defined"""
                scope = self
                while scope.parent:
                    scope = scope.parent
                return name in scope.defined and scope.defined[name] <= line
                
            def _check_nonlocal(self, name: str, line: int) -> bool:
                """Check if nonlocal variable is defined in enclosing scope"""
                scope = self.parent
                while scope:
                    if name in scope.defined and scope.defined[name] <= line:
                        return True
                    scope = scope.parent
                return False
        
        class UndefinedVariableChecker(ast.NodeVisitor):
            def __init__(self):
                self.current_scope = Scope("module")
                self.errors: List[Tuple[str, int]] = []
                self.in_annotation = False
                
            def visit_Module(self, node):
                # Process imports first to ensure they're available throughout
                for child in node.body:
                    if isinstance(child, (ast.Import, ast.ImportFrom)):
                        self.visit(child)
                        
                # Then process the rest
                for child in node.body:
                    if not isinstance(child, (ast.Import, ast.ImportFrom)):
                        self.visit(child)
                        
            def visit_FunctionDef(self, node):
                # Define function name in current scope
                self.current_scope.define(node.name, node.lineno)
                
                # Visit decorators in current scope
                for decorator in node.decorator_list:
                    self.visit(decorator)
                
                # Create new scope for function body
                func_scope = Scope(f"function:{node.name}", self.current_scope)
                old_scope = self.current_scope
                self.current_scope = func_scope
                
                # Add function parameters to the function scope
                for arg in node.args.args:
                    func_scope.define(arg.arg, node.lineno)
                for arg in node.args.posonlyargs:
                    func_scope.define(arg.arg, node.lineno)
                for arg in node.args.kwonlyargs:
                    func_scope.define(arg.arg, node.lineno)
                if node.args.vararg:
                    func_scope.define(node.args.vararg.arg, node.lineno)
                if node.args.kwarg:
                    func_scope.define(node.args.kwarg.arg, node.lineno)
                    
                # Visit parameter defaults in parent scope
                self.current_scope = old_scope
                for default in node.args.defaults:
                    self.visit(default)
                for default in node.args.kw_defaults:
                    if default:
                        self.visit(default)
                        
                # Visit return annotation in function scope
                self.current_scope = func_scope
                if node.returns:
                    old_in_annotation = self.in_annotation
                    self.in_annotation = True
                    self.visit(node.returns)
                    self.in_annotation = old_in_annotation
                    
                # Visit function body
                for stmt in node.body:
                    self.visit(stmt)
                    
                self.current_scope = old_scope
                
            def visit_AsyncFunctionDef(self, node):
                # Handle async functions the same as regular functions
                # Define function name in current scope
                self.current_scope.define(node.name, node.lineno)
                
                # Visit decorators in current scope
                for decorator in node.decorator_list:
                    self.visit(decorator)
                
                # Create new scope for function body
                func_scope = Scope(f"function:{node.name}", self.current_scope)
                old_scope = self.current_scope
                self.current_scope = func_scope
                
                # Add function parameters to the function scope
                for arg in node.args.args:
                    func_scope.define(arg.arg, node.lineno)
                for arg in node.args.posonlyargs:
                    func_scope.define(arg.arg, node.lineno)
                for arg in node.args.kwonlyargs:
                    func_scope.define(arg.arg, node.lineno)
                if node.args.vararg:
                    func_scope.define(node.args.vararg.arg, node.lineno)
                if node.args.kwarg:
                    func_scope.define(node.args.kwarg.arg, node.lineno)
                    
                # Visit parameter defaults in parent scope
                self.current_scope = old_scope
                for default in node.args.defaults:
                    self.visit(default)
                for default in node.args.kw_defaults:
                    if default:
                        self.visit(default)
                        
                # Visit return annotation in function scope
                self.current_scope = func_scope
                if node.returns:
                    old_in_annotation = self.in_annotation
                    self.in_annotation = True
                    self.visit(node.returns)
                    self.in_annotation = old_in_annotation
                    
                # Visit function body
                for stmt in node.body:
                    self.visit(stmt)
                    
                self.current_scope = old_scope
                
            def visit_Match(self, node):
                """Handle match statements (Python 3.10+)"""
                # Visit the subject expression
                self.visit(node.subject)
                
                # Visit each case
                for case in node.cases:
                    # Create a new scope for the case
                    case_scope = Scope("match_case", self.current_scope)
                    old_scope = self.current_scope
                    self.current_scope = case_scope
                    
                    # Extract variables from the pattern
                    self._extract_pattern_vars(case.pattern, node.lineno)
                    
                    # Visit the guard if present
                    if case.guard:
                        self.visit(case.guard)
                    
                    # Visit the case body
                    for stmt in case.body:
                        self.visit(stmt)
                    
                    self.current_scope = old_scope
                    
            def _extract_pattern_vars(self, pattern, line: int):
                """Extract variables defined in match patterns"""
                if (hasattr(ast, 'MatchAs') and
                        isinstance(pattern, ast.MatchAs)):
                    # as pattern: pattern as name
                    if pattern.name:
                        self.current_scope.define(pattern.name, line)
                    if pattern.pattern:
                        self._extract_pattern_vars(pattern.pattern, line)
                        
                elif (hasattr(ast, 'MatchOr') and
                        isinstance(pattern, ast.MatchOr)):
                    # or pattern: pattern | pattern
                    # Variables must be the same in all alternatives
                    # Just check the first one
                    if pattern.patterns:
                        self._extract_pattern_vars(pattern.patterns[0], line)
                        
                elif (hasattr(ast, 'MatchSequence') and
                        isinstance(pattern, ast.MatchSequence)):
                    # sequence pattern: [pattern, ...]
                    for p in pattern.patterns:
                        self._extract_pattern_vars(p, line)
                        
                elif (hasattr(ast, 'MatchMapping') and
                        isinstance(pattern, ast.MatchMapping)):
                    # mapping pattern: {key: pattern, ...}
                    for p in pattern.patterns:
                        self._extract_pattern_vars(p, line)
                    # Rest captures remaining items
                    if pattern.rest:
                        self.current_scope.define(pattern.rest, line)
                        
                elif (hasattr(ast, 'MatchClass') and
                        isinstance(pattern, ast.MatchClass)):
                    # class pattern: Class(pattern, ...)
                    for p in pattern.patterns:
                        self._extract_pattern_vars(p, line)
                    for kwd_pattern in pattern.kwd_patterns:
                        self._extract_pattern_vars(kwd_pattern, line)
                        
                elif (hasattr(ast, 'MatchStar') and
                        isinstance(pattern, ast.MatchStar)):
                    # star pattern: *name
                    if pattern.name:
                        self.current_scope.define(pattern.name, line)
                        
                elif (hasattr(ast, 'MatchValue') and
                        isinstance(pattern, ast.MatchValue)):
                    # value pattern: just a value, no variables
                    pass
                    
                elif (hasattr(ast, 'MatchSingleton') and
                        isinstance(pattern, ast.MatchSingleton)):
                    # singleton pattern: None, True, False
                    pass
                    
            def visit_NamedExpr(self, node):
                """Handle walrus operator := (Python 3.8+)"""
                # First visit the value
                self.visit(node.value)
                
                # Then define the target
                if isinstance(node.target, ast.Name):
                    self.current_scope.define(node.target.id, node.lineno)
                    # Also mark it as used since it's an expression
                    self.current_scope.use(node.target.id, node.lineno)
                
            def visit_ClassDef(self, node):
                # Define class name in current scope
                self.current_scope.define(node.name, node.lineno)
                
                # Visit decorators and base classes in current scope
                for decorator in node.decorator_list:
                    self.visit(decorator)
                for base in node.bases:
                    self.visit(base)
                for keyword in node.keywords:
                    self.visit(keyword.value)
                    
                # Create new scope for class body
                class_scope = Scope(f"class:{node.name}", self.current_scope)
                old_scope = self.current_scope
                self.current_scope = class_scope
                
                # Visit class body
                for stmt in node.body:
                    self.visit(stmt)
                    
                self.current_scope = old_scope
                
            def visit_Lambda(self, node):
                # Create scope for lambda
                lambda_scope = Scope("lambda", self.current_scope)
                old_scope = self.current_scope
                self.current_scope = lambda_scope
                
                # Add lambda parameters
                for arg in node.args.args:
                    lambda_scope.define(arg.arg, node.lineno)
                if node.args.vararg:
                    lambda_scope.define(node.args.vararg.arg, node.lineno)
                if node.args.kwarg:
                    lambda_scope.define(node.args.kwarg.arg, node.lineno)
                    
                # Visit body
                self.visit(node.body)
                
                self.current_scope = old_scope
                
            def visit_ListComp(self, node):
                self._visit_comprehension("listcomp", node)
                
            def visit_SetComp(self, node):
                self._visit_comprehension("setcomp", node)
                
            def visit_DictComp(self, node):
                self._visit_comprehension("dictcomp", node)
                
            def visit_GeneratorExp(self, node):
                self._visit_comprehension("genexp", node)
                
            def _visit_comprehension(self, comp_type: str, node):
                # Create new scope for comprehension
                comp_scope = Scope(comp_type, self.current_scope)
                old_scope = self.current_scope
                self.current_scope = comp_scope
                
                # Process generators - each creates its own scope
                for generator in node.generators:
                    # Visit iterator in parent scope
                    self.current_scope = old_scope
                    self.visit(generator.iter)
                    self.current_scope = comp_scope
                    
                    # Define target variables in comprehension scope
                    self._define_target(generator.target, node.lineno)
                    
                    # Visit conditions in comprehension scope
                    for condition in generator.ifs:
                        self.visit(condition)
                        
                # Visit element/key/value in comprehension scope
                if isinstance(node, ast.DictComp):
                    self.visit(node.key)
                    self.visit(node.value)
                else:
                    self.visit(node.elt)
                    
                self.current_scope = old_scope
                
            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    # For "import x.y.z", only "x" is defined
                    base_name = name.split('.')[0]
                    self.current_scope.define(base_name, node.lineno)
                    self.current_scope.imported.add(base_name)
                    
            def visit_ImportFrom(self, node):
                for alias in node.names:
                    if alias.name == '*':
                        # Can't track star imports precisely
                        continue
                    name = alias.asname if alias.asname else alias.name
                    self.current_scope.define(name, node.lineno)
                    self.current_scope.imported.add(name)
                    
            def visit_Assign(self, node):
                # Visit value first
                self.visit(node.value)
                
                # Then define targets
                for target in node.targets:
                    self._define_target(target, node.lineno)
                    
            def visit_AnnAssign(self, node):
                # Visit annotation
                if node.annotation:
                    old_in_annotation = self.in_annotation
                    self.in_annotation = True
                    self.visit(node.annotation)
                    self.in_annotation = old_in_annotation
                    
                # Visit value if present
                if node.value:
                    self.visit(node.value)
                    
                # Define target
                if isinstance(node.target, ast.Name):
                    self.current_scope.define(node.target.id, node.lineno)
                    
            def visit_AugAssign(self, node):
                # Visit target (it's being read and written)
                self.visit(node.target)
                # Visit value
                self.visit(node.value)
                
            def visit_For(self, node):
                # Visit iterator
                self.visit(node.iter)
                
                # Define loop variable
                self._define_target(node.target, node.lineno)
                
                # Visit body and else
                for stmt in node.body:
                    self.visit(stmt)
                for stmt in node.orelse:
                    self.visit(stmt)
                    
            def visit_AsyncFor(self, node):
                # Visit iterator
                self.visit(node.iter)
                
                # Define loop variable
                self._define_target(node.target, node.lineno)
                
                # Visit body and else
                for stmt in node.body:
                    self.visit(stmt)
                for stmt in node.orelse:
                    self.visit(stmt)
                
            def visit_While(self, node):
                # Visit condition
                self.visit(node.test)
                
                # Visit body and else
                for stmt in node.body:
                    self.visit(stmt)
                for stmt in node.orelse:
                    self.visit(stmt)
                    
            def visit_If(self, node):
                # Visit condition
                self.visit(node.test)
                
                # Visit body and else
                for stmt in node.body:
                    self.visit(stmt)
                for stmt in node.orelse:
                    self.visit(stmt)
                    
            def visit_With(self, node):
                # Visit context expressions
                for item in node.items:
                    self.visit(item.context_expr)
                    
                # Define optional variables
                for item in node.items:
                    if item.optional_vars:
                        self._define_target(item.optional_vars, node.lineno)
                        
                # Visit body
                for stmt in node.body:
                    self.visit(stmt)
                    
            def visit_AsyncWith(self, node):
                # Visit context expressions
                for item in node.items:
                    self.visit(item.context_expr)
                    
                # Define optional variables
                for item in node.items:
                    if item.optional_vars:
                        self._define_target(item.optional_vars, node.lineno)
                        
                # Visit body
                for stmt in node.body:
                    self.visit(stmt)
                
            def visit_ExceptHandler(self, node):
                # Visit exception type
                if node.type:
                    self.visit(node.type)
                    
                # Create new scope for exception handler
                handler_scope = Scope("except", self.current_scope)
                old_scope = self.current_scope
                self.current_scope = handler_scope
                
                # Define exception variable if present
                if node.name:
                    handler_scope.define(node.name, node.lineno)
                    
                # Visit handler body
                for stmt in node.body:
                    self.visit(stmt)
                    
                self.current_scope = old_scope
                
            def visit_Global(self, node):
                for name in node.names:
                    self.current_scope.global_vars.add(name)
                    
            def visit_Nonlocal(self, node):
                for name in node.names:
                    self.current_scope.nonlocal_vars.add(name)
                    # Check that the variable exists in an enclosing scope
                    if not self._check_nonlocal_exists(name):
                        self.errors.append((
                            f"No binding for nonlocal '{name}' found",
                            node.lineno
                        ))
                        
            def _check_nonlocal_exists(self, name: str) -> bool:
                """Check if a nonlocal variable exists in an enclosing scope"""
                scope = self.current_scope.parent
                while scope:
                    if name in scope.defined:
                        return True
                    scope = scope.parent
                return False
                
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    self.current_scope.define(node.id, node.lineno)
                elif isinstance(node.ctx, ast.Load):
                    # Check if the name is defined
                    name_undefined = (
                        node.id not in builtins and
                        not self.current_scope.is_defined(node.id, node.lineno)
                    )
                    if name_undefined:
                        # Don't report errors for forward references
                        is_forward_ref = (
                            self.in_annotation and
                            self._could_be_forward_ref(node.id)
                        )
                        # Also check if it might be a type alias
                        is_type_name = (
                            self.in_annotation and
                            # Type names usually capitalized
                            node.id[0].isupper()
                        )
                        if not is_forward_ref and not is_type_name:
                            self.errors.append((
                                f"Undefined name '{node.id}'",
                                node.lineno
                            ))
                    self.current_scope.use(node.id, node.lineno)
                    
            def _could_be_forward_ref(self, name: str) -> bool:
                """Check if name could be forward reference"""
                # Check if it might be defined later
                scope = self.current_scope
                while scope:
                    # Check class names that might be defined later
                    if (scope.name.startswith("class:") or
                            scope.name == "module"):
                        return True
                    scope = scope.parent
                return False
                    
            def _define_target(self, target, line: int):
                """Define all names in an assignment target"""
                if isinstance(target, ast.Name):
                    self.current_scope.define(target.id, line)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for elt in target.elts:
                        self._define_target(elt, line)
                elif isinstance(target, ast.Starred):
                    self._define_target(target.value, line)
                # For attribute access, subscripts etc., visit them normally
                elif isinstance(target, (ast.Attribute, ast.Subscript)):
                    self.visit(target)
                    
            def visit_TypeAlias(self, node):
                """Handle type alias statements (Python 3.12+)"""
                if hasattr(ast, 'TypeAlias'):
                    # Define the alias name
                    if isinstance(node.name, ast.Name):
                        self.current_scope.define(node.name.id, node.lineno)
                    # Visit the value with annotation flag
                    old_in_annotation = self.in_annotation
                    self.in_annotation = True
                    self.visit(node.value)
                    self.in_annotation = old_in_annotation
                    
        # Run the checker
        checker = UndefinedVariableChecker()
        checker.visit(tree)
        
        # Convert errors to ValidationError format
        lines = code.splitlines()
        
        for error_msg, line_no in checker.errors:
            # Extract variable name if present
            var_match = re.search(r"'(\w+)'", error_msg)
            var_name = var_match.group(1) if var_match else None
            
            context = ErrorContext(
                line_number=line_no,
                code_snippet=(
                    lines[line_no - 1]
                    if line_no and line_no <= len(lines)
                    else None
                ),
                surrounding_lines=self._get_surrounding_lines(lines, line_no)
            )
            
            val_error = ValidationError(
                error_msg,
                validation_type="logic",
                failed_code=code,
                context=context
            )
            
            # Add specific suggestions for undefined names
            if var_name:
                val_error.add_suggestion(
                    f"Define '{var_name}' before using it"
                )
                val_error.add_suggestion(
                    f"Import '{var_name}' if it's from another module"
                )
                
                # Check for common typos
                common_names = [
                    'print', 'len', 'range', 'str', 'int',
                    'float', 'list', 'dict', 'open', 'input'
                ]
                for common in common_names:
                    if self._is_similar_name(var_name, common):
                        val_error.add_suggestion(
                            f"Did you mean '{common}' instead of "
                            f"'{var_name}'?"
                        )
            
            errors.append(val_error.format_error(include_context=False))
            
        return errors
    
    def _is_similar_name(self, name1: str, name2: str) -> bool:
        """Check if two names are similar (for typo detection)"""
        if abs(len(name1) - len(name2)) > 2:
            return False
        
        # Simple edit distance check
        if len(name1) == len(name2):
            diff_count = sum(1 for a, b in zip(name1, name2) if a != b)
            return diff_count <= 1
        
        return False
    
    @lru_cache(maxsize=128)
    def _check_imports_cached(self, code_hash: str) -> List[str]:
        """Cached version of import checking"""
        # Parse the code
        tree = parse_cached(code_hash)
        return self._check_imports(tree)
    
    def _check_imports(self, tree: ast.AST) -> List[str]:
        """Check for import-related issues"""
        issues = []
        imported_modules = set()
        
        # Use generator for better memory efficiency
        nodes = (node for node in ast.walk(tree))
        
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in imported_modules:
                        issues.append(f"Duplicate import: {alias.name}")
                    imported_modules.add(alias.name)
                    
                    # Check for suspicious imports
                    unsafe_modules = ['os', 'sys', 'subprocess']
                    if (alias.name in unsafe_modules and
                            not self.allow_unsafe):
                        issues.append(
                            f"Potentially unsafe import: {alias.name}"
                        )
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if module in imported_modules:
                    issues.append(f"Duplicate import from: {module}")
                
                # Check for wildcard imports
                if any(alias.name == '*' for alias in node.names):
                    issues.append(
                        f"Wildcard import from {module} - use explicit imports"
                    )
        
        return issues
    
    def _check_common_issues(self, code: str) -> List[str]:
        """Check for common code issues"""
        issues = []
        
        # Check for code smells (using pre-compiled patterns)
        for pattern, message in self.code_smells.items():
            if pattern.search(code):
                issues.append(message)
        
        # Check for long lines
        for i, line in enumerate(code.splitlines(), 1):
            if len(line) > self.config.max_line_length:
                issues.append(
                    f"Line {i} exceeds {self.config.max_line_length} chars"
                )
        
        return issues
    
    def _check_unsafe_operations(self, code: str) -> List[str]:
        """Check for unsafe operations with detailed context"""
        unsafe_found = []
        lines = code.splitlines()
        
        for pattern in self.unsafe_patterns:
            matches = re.finditer(pattern, code, re.MULTILINE)
            for match in matches:
                # Find line number
                line_no = code[:match.start()].count('\n') + 1
                
                context = ErrorContext(
                    line_number=line_no,
                    code_snippet=(
                        lines[line_no - 1]
                        if line_no <= len(lines)
                        else None
                    ),
                    metadata={'pattern': pattern, 'match': match.group(0)}
                )
                
                error = ValidationError(
                    f"Unsafe operation detected: {match.group(0)}",
                    validation_type="security",
                    context=context
                )
                
                # Add specific suggestions based on the operation
                if 'eval' in match.group(0):
                    error.add_suggestion(
                        "Use ast.literal_eval() for safe evaluation"
                    )
                    error.add_suggestion(
                        "Consider parsing data instead of evaluating code"
                    )
                elif 'exec' in match.group(0):
                    error.add_suggestion("Avoid dynamic code execution")
                    error.add_suggestion("Use functions or classes instead")
                elif 'open.*w' in pattern:
                    error.add_suggestion("Validate file paths before writing")
                    error.add_suggestion(
                        "Use context managers (with statement)"
                    )
                
                unsafe_found.append(error.format_error(include_context=False))
        
        return unsafe_found
    
    def _check_tokenization(self, code: str) -> List[str]:
        """Check for tokenization issues"""
        errors = []
        
        try:
            list(tokenize.generate_tokens(StringIO(code).readline))
        except tokenize.TokenError as e:
            errors.append(f"Tokenization error: {str(e)}")
        
        return errors
    
    def _find_unreachable_code(self, tree: ast.AST) -> List[str]:
        """Find unreachable code"""
        unreachable = []
        
        class UnreachableChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Check for code after return
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return):
                        if i < len(node.body) - 1:
                            unreachable.append(
                                f"Code after return in '{node.name}'"
                            )
                self.generic_visit(node)
        
        checker = UnreachableChecker()
        checker.visit(tree)
        
        return unreachable
    
    def _find_unused_variables(self, tree: ast.AST) -> List[str]:
        """Find unused variables"""
        # Simplified check - full impl needs scope tracking
        defined_vars = set()
        used_vars = set()
        
        class VarTracker(ast.NodeVisitor):
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_vars.add(target.id)
                self.generic_visit(node)
            
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
                self.generic_visit(node)
        
        tracker = VarTracker()
        tracker.visit(tree)
        
        unused = defined_vars - used_vars
        # Filter out common intentionally unused vars
        unused = [v for v in unused if not v.startswith('_')]
        
        return list(unused)
    
    def _detect_infinite_loops(self, tree: ast.AST) -> List[str]:
        """Detect potential infinite loops"""
        infinite_loops = []
        
        class LoopChecker(ast.NodeVisitor):
            def visit_While(self, node):
                # Check for while True without break
                is_while_true = (
                    isinstance(node.test, ast.Constant) and
                    node.test.value is True
                )
                if is_while_true:
                    has_break = any(
                        isinstance(stmt, ast.Break)
                        for stmt in ast.walk(node)
                    )
                    if not has_break:
                        infinite_loops.append(
                            "while True without break statement"
                        )
                self.generic_visit(node)
        
        checker = LoopChecker()
        checker.visit(tree)
        
        return infinite_loops
    
    def _check_missing_returns(self, tree: ast.AST) -> List[str]:
        """Check for functions that might be missing return statements"""
        missing_returns = []
        
        class ReturnChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Skip __init__ methods
                if node.name == '__init__':
                    return
                
                # Check if function has type hint suggesting return value
                if node.returns:
                    # Function should return something
                    has_return = any(
                        isinstance(stmt, ast.Return)
                        for stmt in ast.walk(node)
                    )
                    if not has_return:
                        missing_returns.append(node.name)
                
                self.generic_visit(node)
        
        checker = ReturnChecker()
        checker.visit(tree)
        
        return missing_returns
    
    def _check_basic_type_consistency(self, tree: ast.AST) -> List[str]:
        """Basic type consistency checks with detailed errors"""
        issues = []
        
        # This is a very basic check - full type checking would require mypy
        class TypeChecker(ast.NodeVisitor):
            def __init__(self, parent):
                self.parent = parent
                
            def visit_BinOp(self, node):
                # Check for string + number
                if isinstance(node.op, ast.Add):
                    left_is_str = (
                        isinstance(node.left, ast.Constant) and
                        isinstance(node.left.value, str)
                    )
                    right_is_num = (
                        isinstance(node.right, ast.Constant) and
                        isinstance(node.right.value, (int, float))
                    )
                    
                    if ((left_is_str and right_is_num) or
                            (right_is_num and left_is_str)):
                        context = ErrorContext(
                            line_number=node.lineno,
                            metadata={
                                'operation': 'addition',
                                'types': 'string and number'
                            }
                        )
                        
                        error = ValidationError(
                            "Type mismatch: cannot add string and number",
                            validation_type="logic",
                            context=context
                        )
                        error.add_suggestion(
                            "Convert the number to string using str()"
                        )
                        error.add_suggestion(
                            "Use f-strings for string formatting"
                        )
                        error.add_suggestion(
                            "Use .format() method for string formatting"
                        )
                        
                        issues.append(
                            error.format_error(include_context=False)
                        )
                
                self.generic_visit(node)
        
        checker = TypeChecker(self)
        checker.visit(tree)
        
        return issues
    
    def _check_runtime_risks(self, tree: ast.AST) -> List[str]:
        """Check for potential runtime errors"""
        risks = []
        
        class RiskChecker(ast.NodeVisitor):
            def visit_Subscript(self, node):
                # Check for potential index errors
                if isinstance(node.slice, ast.Constant):
                    if isinstance(node.slice.value, int):
                        # Flag large indices
                        if abs(node.slice.value) > 1000:
                            risks.append(
                                f"Large index {node.slice.value} at line "
                                f"{node.lineno}"
                            )
                self.generic_visit(node)
            
            def visit_BinOp(self, node):
                # Check for division by zero
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    if (isinstance(node.right, ast.Constant) and
                            node.right.value == 0):
                        context = ErrorContext(
                            line_number=node.lineno,
                            metadata={'operation': 'division'}
                        )
                        
                        error = ValidationError(
                            "Division by zero detected",
                            validation_type="logic",
                            context=context
                        )
                        error.add_suggestion(
                            "Add a check for zero before division"
                        )
                        error.add_suggestion(
                            "Use try/except to handle ZeroDivisionError"
                        )
                        
                        risks.append(error.format_error(include_context=False))
                self.generic_visit(node)
        
        checker = RiskChecker()
        checker.visit(tree)
        
        return risks
    
    @lru_cache(maxsize=64)
    def _check_style(self, code: str) -> List[str]:
        """Check PEP 8 style guidelines"""
        suggestions = []
        
        lines = code.splitlines()
        
        # Function and class naming
        for i, line in enumerate(lines, 1):
            # Check function names (using pre-compiled pattern)
            func_match = self._function_pattern.match(line)
            if func_match:
                func_name = func_match.group(1)
                if (not re.match(r'^[a-z_][a-z0-9_]*$', func_name) and
                        func_name != '__init__'):
                    suggestions.append(
                        f"Function '{func_name}' should use "
                        f"lowercase_with_underscores"
                    )
            
            # Check class names (using pre-compiled pattern)
            class_match = self._class_pattern.match(line)
            if class_match:
                class_name = class_match.group(1)
                if not re.match(r'^[A-Z][A-Za-z0-9]*$', class_name):
                    suggestions.append(
                        f"Class '{class_name}' should use CapWords convention"
                    )
            
            # Check for space after comma
            if ',' in line and not re.search(r',\s', line):
                suggestions.append(f"Line {i}: Add space after comma")
            
            # Check for space around operators
            if re.search(r'\w[+\-*/=<>]\w', line):
                suggestions.append(f"Line {i}: Add spaces around operators")
        
        return suggestions
    
    def _check_performance(self, tree: ast.AST, code: str) -> List[str]:
        """Check for performance improvements"""
        suggestions = []
        
        class PerfChecker(ast.NodeVisitor):
            def __init__(self):
                self.in_loop = False
                self.append_calls_in_loops = []
                
            def visit_For(self, node):
                # Check for range(len()) pattern
                if isinstance(node.iter, ast.Call):
                    if (isinstance(node.iter.func, ast.Name) and
                            node.iter.func.id == 'range'):
                        if (node.iter.args and
                                isinstance(node.iter.args[0], ast.Call)):
                            if (isinstance(node.iter.args[0].func,
                                           ast.Name) and
                                    node.iter.args[0].func.id == 'len'):
                                suggestions.append(
                                    "Use enumerate() instead of range(len())"
                                )
                
                # Track that we're in a loop for append detection
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop
                
            def visit_While(self, node):
                old_in_loop = self.in_loop
                self.in_loop = True
                self.generic_visit(node)
                self.in_loop = old_in_loop
                
            def visit_ListComp(self, node):
                # List comprehensions are generally good
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Check for repeated append in loops
                if (isinstance(node.func, ast.Attribute) and
                        node.func.attr == 'append' and self.in_loop):
                    # Track append calls in loops
                    # Get the object being appended to
                    obj = node.func.value
                    if isinstance(obj, ast.Name):
                        list_name = obj.id
                        self.append_calls_in_loops.append(
                            (list_name, node.lineno)
                        )
                self.generic_visit(node)
        
        checker = PerfChecker()
        checker.visit(tree)
        
        # Check if there were append calls in loops
        if checker.append_calls_in_loops:
            # Group by list name
            from collections import defaultdict
            appends_by_list = defaultdict(list)
            for list_name, line_no in checker.append_calls_in_loops:
                appends_by_list[list_name].append(line_no)
            
            # Suggest list comprehension for lists with multiple appends
            for list_name, line_numbers in appends_by_list.items():
                if len(line_numbers) >= 2:
                    suggestions.append(
                        f"Consider using list comprehension instead of "
                        f"repeated append() for '{list_name}'"
                    )
        
        # Check for string concatenation in loops
        if re.search(r'for.*:\s*\n.*\+=\s*["\']', code, re.MULTILINE):
            suggestions.append(
                "Use join() for string concatenation in loops"
            )
        
        return suggestions
    
    def _check_readability(self, tree: ast.AST, code: str) -> List[str]:
        """Check for readability improvements"""
        suggestions = []
        
        # Check for missing docstrings
        class DocstringChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                if not ast.get_docstring(node) and len(node.body) > 5:
                    suggestions.append(
                        f"Function '{node.name}' is missing a docstring"
                    )
                self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                if not ast.get_docstring(node):
                    suggestions.append(
                        f"Class '{node.name}' is missing a docstring"
                    )
                self.generic_visit(node)
        
        checker = DocstringChecker()
        checker.visit(tree)
        
        # Check for overly complex expressions
        for node in ast.walk(tree):
            if isinstance(node, ast.BoolOp) and len(node.values) > 3:
                suggestions.append(
                    "Consider breaking down complex boolean expressions"
                )
            
            if isinstance(node, ast.Lambda):
                suggestions.append(
                    "Consider using a named function instead of lambda "
                    "for clarity"
                )
        
        # Check for magic numbers
        if (re.search(r'\b\d{2,}\b', code) and
                not re.search(r'^\s*\w+\s*=\s*\d+', code, re.MULTILINE)):
            suggestions.append("Consider defining constants for magic numbers")
        
        return suggestions
    
    def _check_best_practices(self, tree: ast.AST, code: str) -> List[str]:
        """Check for Python best practices"""
        suggestions = []
        
        # Check for mutable default arguments
        class DefaultArgChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        suggestions.append(
                            f"Function '{node.name}' has mutable "
                            f"default argument"
                        )
                self.generic_visit(node)
        
        checker = DefaultArgChecker()
        checker.visit(tree)
        
        # Check for explicit type comparisons
        if re.search(r'type\([^)]+\)\s*==\s*', code):
            suggestions.append(
                "Use isinstance() instead of type() == for type checking"
            )
        
        # Check for manual file closing
        if 'open(' in code and 'with' not in code:
            suggestions.append("Use 'with' statement for file operations")
        
        # Check for == None
        if re.search(r'==\s*None|!=\s*None', code):
            suggestions.append(
                "Use 'is None' or 'is not None' instead of == None"
            )
        
        return suggestions
    
    def _check_security(self, code: str) -> List[str]:
        """Check for security issues"""
        suggestions = []
        
        # Check for hardcoded passwords
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', code, re.IGNORECASE):
            suggestions.append(
                "Avoid hardcoding passwords - use environment variables "
                "or config files"
            )
        
        # Check for SQL injection risks
        if 'sql' in code.lower() and '%s' in code:
            suggestions.append(
                "Use parameterized queries to prevent SQL injection"
            )
        
        # Check for path traversal risks
        if '../' in code or '..\\' in code:
            suggestions.append(
                "Validate file paths to prevent directory traversal attacks"
            )
        
        return suggestions
    
    def _suggest_syntax_fix(self, code: str, error: SyntaxError) -> str:
        """Suggest fix for syntax error"""
        if error.lineno:
            lines = code.splitlines()
            if 0 < error.lineno <= len(lines):
                problem_line = lines[error.lineno - 1]
                
                # Common syntax errors and fixes
                keywords = ['if', 'for', 'while', 'def', 'class']
                if (':' not in problem_line and
                        any(kw in problem_line for kw in keywords)):
                    return "Missing colon (:) at end of statement"
                elif problem_line.count('(') != problem_line.count(')'):
                    return "Mismatched parentheses"
                elif problem_line.count('[') != problem_line.count(']'):
                    return "Mismatched square brackets"
                elif problem_line.count('{') != problem_line.count('}'):
                    return "Mismatched curly braces"
                elif (problem_line.count('"') % 2 != 0 or
                        problem_line.count("'") % 2 != 0):
                    return "Unclosed string literal"
        
        return "Check for missing colons, parentheses, or quotes"
    
    def _get_cache_key(self, code: str, validation_type: str) -> str:
        """Generate cache key for validation results"""
        import hashlib
        code_hash = hashlib.md5(code.encode()).hexdigest()
        return f"{validation_type}:{code_hash}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[ValidationResult]:
        """Get cached validation result"""
        with self._cache_lock:
            return self._validation_cache.get(cache_key)
    
    def _cache_result(self, cache_key: str, result: ValidationResult):
        """Cache validation result"""
        with self._cache_lock:
            # Implement simple LRU by removing oldest if cache is full
            if len(self._validation_cache) >= self._max_cache_size:
                # Remove oldest entry (first in dict)
                oldest_key = next(iter(self._validation_cache))
                del self._validation_cache[oldest_key]
            
            self._validation_cache[cache_key] = result