"""
Validator module for the Pseudocode Translator

This module handles validation of generated Python code, including
syntax validation, logic checks, and improvement suggestions.
"""

import ast
import re
import tokenize
from io import StringIO
from functools import lru_cache
from typing import List, Dict, Any, Optional
import logging
import threading
from dataclasses import dataclass, field

from ast_cache import parse_cached  # used by _check_imports_cached
from exceptions import ValidationError, ErrorContext  # used by existing checks


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
    
    def __init__(self, config: Any):
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
        """Conservative undefined name check that won't raise."""
        errors: List[str] = []
        try:
            class _UndefinedVarVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.defined = set()
                    self.errors: List[str] = []
                    # Builtins safe set
                    try:
                        self._builtins = set(dir(__builtins__))  # type: ignore
                    except Exception:
                        self._builtins = set()

                def visit_FunctionDef(self, node: ast.FunctionDef):
                    # Parameters are definitions
                    for arg in getattr(node.args, "args", []) or []:
                        self.defined.add(arg.arg)
                    if node.args.vararg:
                        self.defined.add(node.args.vararg.arg)
                    if node.args.kwarg:
                        self.defined.add(node.args.kwarg.arg)
                    # Visit defaults and body
                    for d in getattr(node.args, "defaults", []) or []:
                        if d:
                            self.visit(d)
                    for d in getattr(node.args, "kw_defaults", []) or []:
                        if d:
                            self.visit(d)
                    for stmt in node.body:
                        self.visit(stmt)

                def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                    self.visit_FunctionDef(node)  # same handling

                def visit_ClassDef(self, node: ast.ClassDef):
                    # Define class name then visit bases/body
                    self.defined.add(node.name)
                    for base in node.bases:
                        self.visit(base)
                    for stmt in node.body:
                        self.visit(stmt)

                def visit_Import(self, node: ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split(".")[0]
                        self.defined.add(name)

                def visit_ImportFrom(self, node: ast.ImportFrom):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        if name != "*":
                            self.defined.add(name)

                def visit_Assign(self, node: ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.defined.add(target.id)
                    self.generic_visit(node)

                def visit_AnnAssign(self, node: ast.AnnAssign):
                    if isinstance(node.target, ast.Name):
                        self.defined.add(node.target.id)
                    if node.value:
                        self.visit(node.value)

                def visit_Name(self, node: ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        name = node.id
                        if name not in self.defined and name not in self._builtins:
                            self.errors.append(f"Line {node.lineno}: Name '{name}' might be undefined")
                    self.generic_visit(node)

            visitor = _UndefinedVarVisitor()
            visitor.visit(tree)
            errors.extend(visitor.errors)
        except Exception:
            # Fail-safe: return empty list on any unexpected error
            return []
        return errors
    
    @lru_cache(maxsize=128)
    def _check_imports_cached(self, code_hash: str) -> List[str]:
        """Cached version of import checking"""
        # Parse the code
        tree = parse_cached(code_hash)
        return self._check_imports(tree)

    def _check_imports(self, tree: ast.AST) -> List[str]:
        """Check for import-related issues (safe/minimal)."""
        issues: List[str] = []
        try:
            seen: set = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name
                        root = (name or '').split(".")[0]
                        if root:
                            if root in seen:
                                issues.append(f"Duplicate import detected: '{root}'")
                            else:
                                seen.add(root)
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "*":
                            mod = node.module or ""
                            issues.append(f"Avoid wildcard import: from {mod} import *")
        except Exception:
            return []
        return issues

    def _check_common_issues(self, code: str) -> List[str]:
        """Check for common code issues"""
        issues: List[str] = []
        try:
            for pattern, message in getattr(self, "code_smells", {}).items():
                try:
                    if pattern.search(code):
                        issues.append(message)
                except Exception:
                    continue
            max_len = getattr(self.config, "max_line_length", 120)
            for i, line in enumerate(code.splitlines(), 1):
                if len(line) > max_len:
                    issues.append(f"Line {i}: exceeds maximum line length of {max_len} characters")
        except Exception:
            return []
        return issues

    def _check_style(self, code: str) -> List[str]:
        """Check PEP 8 style guidelines (minimal, safe)."""
        suggestions: List[str] = []
        try:
            lines = code.splitlines()
            func_name_re = re.compile(r'^\s*def\s+([A-Za-z_]\w*)\s*\(')
            class_name_re = re.compile(r'^\s*class\s+([A-Za-z_]\w*)\s*[:\(]')
            for i, line in enumerate(lines, 1):
                # space after comma
                if re.search(r',[^\s\W]', line):
                    suggestions.append(f"Line {i}: Add a space after ','")
                # spaces around operators (minimal heuristic)
                if re.search(r'\w[+\-*/=<>]\w', line):
                    suggestions.append(f"Line {i}: Add spaces around operators")
                # function snake_case
                m = func_name_re.match(line)
                if m and re.search(r'[A-Z]', m.group(1)):
                    suggestions.append("Function names should be snake_case")
                # class PascalCase
                m = class_name_re.match(line)
                if m and not re.match(r'[A-Z][A-Za-z0-9]+$', m.group(1)):
                    suggestions.append("Class names should use PascalCase")
        except Exception:
            return []
        return suggestions

    def _find_unreachable_code(self, tree: ast.AST) -> List[str]:
        """Detect simple unreachable code after return/raise in functions."""
        issues: List[str] = []
        try:
            def scan_body(body: List[ast.stmt]):
                terminated = False
                for stmt in body:
                    if terminated:
                        issues.append(f"Line {getattr(stmt, 'lineno', '?')}: statement after return/raise")
                    if isinstance(stmt, (ast.Return, ast.Raise)):
                        terminated = True
                    # Scan nested blocks
                    for child in ast.iter_child_nodes(stmt):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                            sub_bodies = []
                            if hasattr(child, 'body'):
                                sub_bodies.append(child.body)
                            if hasattr(child, 'orelse'):
                                sub_bodies.append(child.orelse)
                            if hasattr(child, 'finalbody'):
                                sub_bodies.append(child.finalbody)
                            for b in sub_bodies:
                                scan_body(b)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scan_body(node.body)
        except Exception:
            return []
        return issues

    def _find_unused_variables(self, tree: ast.AST) -> List[str]:
        """Very conservative unused variable check within functions."""
        unused: List[str] = []
        try:
            class UsageVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.assigned: Dict[str, int] = {}
                    self.used: set = set()

                def visit_FunctionDef(self, node: ast.FunctionDef):
                    for arg in node.args.args or []:
                        self.assigned[arg.arg] = self.assigned.get(arg.arg, 0) + 1
                        self.used.add(arg.arg)  # treat params as used
                    self.generic_visit(node)

                def visit_Assign(self, node: ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.assigned[t.id] = self.assigned.get(t.id, 0) + 1
                    self.generic_visit(node)

                def visit_Name(self, node: ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        self.used.add(node.id)

            v = UsageVisitor()
            v.visit(tree)
            for name in v.assigned:
                if name not in v.used and not name.startswith('_'):
                    unused.append(name)
        except Exception:
            return []
        return unused

    def _detect_infinite_loops(self, tree: ast.AST) -> List[str]:
        """Detect while True loops without a break (simple heuristic)."""
        loops: List[str] = []
        try:
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    if isinstance(node.test, ast.Constant) and node.test.value is True:
                        has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                        if not has_break:
                            lineno = getattr(node, 'lineno', '?')
                            loops.append(f"while True at line {lineno}")
        except Exception:
            return []
        return loops

    def _check_missing_returns(self, tree: ast.AST) -> List[str]:
        """Detect typed functions that may miss a return."""
        missing: List[str] = []
        try:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
                    has_return_with_value = any(
                        isinstance(n, ast.Return) and n.value is not None
                        for n in ast.walk(node)
                    )
                    if not has_return_with_value:
                        missing.append(node.name)
        except Exception:
            return []
        return missing

    def _check_basic_type_consistency(self, tree: ast.AST) -> List[str]:
        """Placeholder for basic type checks."""
        return []

    def _check_runtime_risks(self, tree: ast.AST) -> List[str]:
        """Placeholder for runtime risk checks."""
        return []

    def _cache_result(self, cache_key: str, result: ValidationResult):
        """Cache validation result with simple LRU eviction."""
        with self._cache_lock:
            if len(self._validation_cache) >= self._max_cache_size:
                try:
                    oldest_key = next(iter(self._validation_cache))
                    del self._validation_cache[oldest_key]
                except StopIteration:
                    pass
            self._validation_cache[cache_key] = result