"""
Enhanced Validation Framework for DinoAir 2.0
Comprehensive code validation including syntax, style, security, and performance analysis.
"""

import ast
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pseudocode_translator.validator import Validator, ValidationResult


class ValidationLevel(Enum):
    """Validation severity levels"""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    ENTERPRISE = "enterprise"


class CheckType(Enum):
    """Types of validation checks"""
    SYNTAX = "syntax"
    STYLE = "style"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOGIC = "logic"
    IMPORTS = "imports"


@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    code: str
    validation_level: ValidationLevel
    timestamp: float = field(default_factory=time.time)
    
    syntax_result: Optional[ValidationResult] = None
    style_result: Optional[Dict[str, Any]] = None
    security_result: Optional[Dict[str, Any]] = None
    performance_result: Optional[Dict[str, Any]] = None
    
    overall_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        """Check if code passes all validation"""
        if self.syntax_result and not self.syntax_result.is_valid:
            return False
        
        # Check for critical security issues
        if self.security_result and self.security_result.get('critical_issues', 0) > 0:
            return False
        
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            "valid": self.is_valid(),
            "overall_score": self.overall_score,
            "syntax_valid": self.syntax_result.is_valid if self.syntax_result else True,
            "style_score": self.style_result.get('score', 100) if self.style_result else 100,
            "security_score": self.security_result.get('score', 100) if self.security_result else 100,
            "performance_score": self.performance_result.get('score', 100) if self.performance_result else 100,
            "recommendations": len(self.recommendations)
        }


class EnhancedValidator:
    """Enhanced validation framework with comprehensive checks"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        
        # Try to create a basic config if available
        try:
            from pseudocode_translator.config import TranslatorConfig
            self.base_validator = Validator(TranslatorConfig())
        except Exception:
            # Fallback: create validator without config dependency
            self.base_validator = None
        
        # Configure validation based on level
        self._configure_validation_level()
    
    def _configure_validation_level(self):
        """Configure validation based on selected level"""
        if self.validation_level == ValidationLevel.BASIC:
            self.enabled_checks = {CheckType.SYNTAX}
        elif self.validation_level == ValidationLevel.STANDARD:
            self.enabled_checks = {CheckType.SYNTAX, CheckType.STYLE, CheckType.SECURITY}
        elif self.validation_level == ValidationLevel.STRICT:
            self.enabled_checks = {CheckType.SYNTAX, CheckType.STYLE, CheckType.SECURITY, CheckType.LOGIC}
        else:  # ENTERPRISE
            self.enabled_checks = set(CheckType)
    
    def validate_code(self, code: str, filename: Optional[str] = None) -> ValidationReport:
        """Perform comprehensive code validation"""
        report = ValidationReport(
            code=code,
            validation_level=self.validation_level
        )
        
        # 1. Syntax validation (always enabled)
        if CheckType.SYNTAX in self.enabled_checks:
            report.syntax_result = self.validate_syntax(code)
        
        # 2. Style validation (PEP8)
        if CheckType.STYLE in self.enabled_checks:
            report.style_result = self.validate_style(code, filename)
        
        # 3. Security validation
        if CheckType.SECURITY in self.enabled_checks:
            report.security_result = self.validate_security(code)
        
        # 4. Performance validation
        if CheckType.PERFORMANCE in self.enabled_checks:
            report.performance_result = self.validate_performance(code)
        
        # 5. Logic validation
        if CheckType.LOGIC in self.enabled_checks:
            if self.base_validator:
                logic_result = self.base_validator.validate_logic(code)
                # Convert to dict format for consistency
                if logic_result:
                    if not hasattr(report, 'logic_result'):
                        report.logic_result = {
                            'valid': logic_result.is_valid,
                            'errors': logic_result.errors,
                            'warnings': logic_result.warnings
                        }
            else:
                # Basic logic validation without full validator
                report.logic_result = self._basic_logic_validation(code)
        
        # Calculate overall score and recommendations
        self._calculate_overall_score(report)
        self._generate_recommendations(report)
        
        return report
    
    def validate_syntax(self, code: str) -> ValidationResult:
        """Enhanced syntax validation with Python 3.8+ support"""
        # Create a basic validation result
        result = ValidationResult(is_valid=True)
        
        # Basic syntax check using ast.parse
        try:
            ast.parse(code)
            result.is_valid = True
        except SyntaxError as e:
            result.is_valid = False
            result.add_error(f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            result.is_valid = False
            result.add_error(f"Parse error: {str(e)}")
        
        # Add Python 3.8+ specific checks if syntax is valid
        if result.is_valid:
            self._check_python38_features(code, result)
        
        return result
    
    def _check_python38_features(self, code: str, result: ValidationResult):
        """Check for Python 3.8+ specific features and compatibility"""
        # Check for walrus operator (:=)
        if ':=' in code:
            result.add_warning("Walrus operator (:=) requires Python 3.8+")
        
        # Check for positional-only parameters
        if re.search(r'def\s+\w+\([^)]*\/[^)]*\)', code):
            result.add_warning("Positional-only parameters require Python 3.8+")
        
        # Check for f-string = specifier
        if re.search(r'f["\'][^"\']*=.*["\']', code):
            result.add_warning("f-string = specifier requires Python 3.8+")
    
    def validate_style(self, code: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """PEP8 style validation using flake8 or custom checks"""
        style_result = {
            "score": 100,
            "issues": [],
            "line_issues": {},
            "summary": {}
        }
        
        try:
            # Try using flake8 if available
            result = self._run_flake8(code, filename)
            if result:
                return result
        except Exception:
            pass
        
        # Fallback to custom style checks
        return self._custom_style_checks(code, style_result)
    
    def _run_flake8(self, code: str, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run flake8 style checking"""
        try:
            # Create temporary file if needed
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Run flake8
            result = subprocess.run(
                ['flake8', '--format=json', temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up
            Path(temp_file).unlink(missing_ok=True)
            
            if result.returncode == 0:
                return {"score": 100, "issues": [], "summary": {"flake8": "passed"}}
            
            # Parse flake8 output
            issues = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    issues.append(line.strip())
            
            score = max(0, 100 - len(issues) * 5)  # Deduct 5 points per issue
            
            return {
                "score": score,
                "issues": issues,
                "summary": {"flake8": f"{len(issues)} issues found"}
            }
            
        except Exception:
            return None
    
    def _custom_style_checks(self, code: str, style_result: Dict[str, Any]) -> Dict[str, Any]:
        """Custom PEP8 style checks"""
        lines = code.split('\n')
        issues = []
        
        for i, line in enumerate(lines, 1):
            # Check line length (PEP8: max 79 characters)
            if len(line) > 79:
                issues.append(f"Line {i}: Line too long ({len(line)}/79)")
                style_result["line_issues"][i] = style_result["line_issues"].get(i, [])
                style_result["line_issues"][i].append("line_too_long")
            
            # Check for trailing whitespace
            if line.rstrip() != line:
                issues.append(f"Line {i}: Trailing whitespace")
                style_result["line_issues"][i] = style_result["line_issues"].get(i, [])
                style_result["line_issues"][i].append("trailing_whitespace")
            
            # Check indentation (should be 4 spaces)
            if line.startswith(' ') and not line.startswith('    '):
                if len(line) - len(line.lstrip()) % 4 != 0:
                    issues.append(f"Line {i}: Indentation is not a multiple of 4")
            
            # Check for tabs
            if '\t' in line:
                issues.append(f"Line {i}: Contains tabs, use spaces")
        
        # Check for multiple blank lines
        blank_line_count = 0
        for i, line in enumerate(lines, 1):
            if not line.strip():
                blank_line_count += 1
                if blank_line_count > 2:
                    issues.append(f"Line {i}: Too many blank lines")
            else:
                blank_line_count = 0
        
        # Check imports
        import_issues = self._check_import_style(code)
        issues.extend(import_issues)
        
        # Check function/class naming
        naming_issues = self._check_naming_conventions(code)
        issues.extend(naming_issues)
        
        # Calculate score
        score = max(0, 100 - len(issues) * 3)  # Deduct 3 points per issue
        
        style_result.update({
            "score": score,
            "issues": issues,
            "summary": {
                "total_issues": len(issues),
                "line_length_issues": len([i for i in issues if "Line too long" in i]),
                "whitespace_issues": len([i for i in issues if "whitespace" in i]),
                "indentation_issues": len([i for i in issues if "Indentation" in i])
            }
        })
        
        return style_result
    
    def _check_import_style(self, code: str) -> List[str]:
        """Check import statement style"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for import *
            if re.match(r'from\s+\w+\s+import\s+\*', stripped):
                issues.append(f"Line {i}: Avoid 'from module import *'")
            
            # Check import order (should be: standard library, third-party, local)
            if stripped.startswith('import ') or stripped.startswith('from '):
                # This is a simplified check
                pass
        
        return issues
    
    def _check_naming_conventions(self, code: str) -> List[str]:
        """Check naming conventions (PEP8)"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            class NamingChecker(ast.NodeVisitor):
                def visit_FunctionDef(self, node):
                    # Function names should be lowercase with underscores
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                        issues.append(f"Function '{node.name}' should use snake_case")
                    self.generic_visit(node)
                
                def visit_ClassDef(self, node):
                    # Class names should be PascalCase
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                        issues.append(f"Class '{node.name}' should use PascalCase")
                    self.generic_visit(node)
                
                def visit_Name(self, node):
                    # Check for all uppercase (constants should be in module level)
                    if node.id.isupper() and len(node.id) > 1:
                        # This is likely a constant, which is OK
                        pass
                    self.generic_visit(node)
            
            checker = NamingChecker()
            checker.visit(tree)
            
        except SyntaxError:
            # Can't check naming if syntax is invalid
            pass
        
        return issues
    
    def validate_security(self, code: str) -> Dict[str, Any]:
        """Security vulnerability scanning"""
        security_result = {
            "score": 100,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
            "issues": [],
            "categories": {
                "injection": [],
                "unsafe_functions": [],
                "hardcoded_secrets": [],
                "file_operations": [],
                "network_security": []
            }
        }
        
        # Check for dangerous functions
        dangerous_patterns = [
            (r'\beval\s*\(', "critical", "injection", "Use of eval() can execute arbitrary code"),
            (r'\bexec\s*\(', "critical", "injection", "Use of exec() can execute arbitrary code"),
            (r'\b__import__\s*\(', "high", "injection", "Dynamic imports can be dangerous"),
            (r'pickle\.loads?', "high", "unsafe_functions", "Pickle can execute arbitrary code"),
            (r'subprocess.*shell=True', "high", "injection", "Shell injection risk"),
            (r'os\.system', "high", "injection", "Command injection risk"),
            (r'password\s*=\s*["\'][^"\']+["\']', "medium", "hardcoded_secrets", "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "medium", "hardcoded_secrets", "Hardcoded API key detected"),
            (r'open\s*\([^)]*["\'][^"\']*\.\./.*["\']', "medium", "file_operations", "Path traversal vulnerability"),
        ]
        
        for pattern, severity, category, message in dangerous_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                issue = {
                    "line": line_num,
                    "severity": severity,
                    "category": category,
                    "message": message,
                    "code_snippet": match.group()
                }
                
                security_result["issues"].append(issue)
                security_result["categories"][category].append(issue)
                security_result[f"{severity}_issues"] += 1
        
        # Calculate security score
        critical_penalty = security_result["critical_issues"] * 30
        high_penalty = security_result["high_issues"] * 20
        medium_penalty = security_result["medium_issues"] * 10
        low_penalty = security_result["low_issues"] * 5
        
        security_result["score"] = max(0, 100 - critical_penalty - high_penalty - medium_penalty - low_penalty)
        
        return security_result
    
    def validate_performance(self, code: str) -> Dict[str, Any]:
        """Performance analysis and optimization suggestions"""
        performance_result = {
            "score": 100,
            "issues": [],
            "suggestions": [],
            "complexity_score": 0,
            "potential_bottlenecks": []
        }
        
        # Check for performance anti-patterns
        performance_patterns = [
            (r'for\s+\w+\s+in\s+range\(len\([^)]+\)\)', "Use enumerate() instead of range(len())"),
            (r'\+\s*=.*["\']', "String concatenation in loop can be slow, use list and join()"),
            (r'\.append\([^)]*\)\s*$', "Consider list comprehension for better performance"),
            (r'global\s+\w+', "Global variables can impact performance"),
        ]
        
        for pattern, suggestion in performance_patterns:
            if re.search(pattern, code, re.MULTILINE):
                performance_result["suggestions"].append(suggestion)
        
        # Analyze code complexity (simplified)
        complexity = self._calculate_complexity(code)
        performance_result["complexity_score"] = complexity
        
        if complexity > 10:
            performance_result["issues"].append("High cyclomatic complexity detected")
            performance_result["score"] -= 20
        
        # Check for potential bottlenecks
        bottlenecks = self._identify_bottlenecks(code)
        performance_result["potential_bottlenecks"] = bottlenecks
        
        return performance_result
    
    def _calculate_complexity(self, code: str) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        complexity = 1  # Base complexity
        
        # Count decision points
        decision_keywords = ['if', 'elif', 'while', 'for', 'except', 'and', 'or']
        
        for keyword in decision_keywords:
            complexity += len(re.findall(r'\b' + keyword + r'\b', code))
        
        return complexity
    
    def _identify_bottlenecks(self, code: str) -> List[str]:
        """Identify potential performance bottlenecks"""
        bottlenecks = []
        
        # Check for nested loops
        if re.search(r'for.*:\s*.*for.*:', code, re.DOTALL):
            bottlenecks.append("Nested loops detected - consider optimization")
        
        # Check for file operations in loops
        if re.search(r'for.*:.*open\(', code, re.DOTALL):
            bottlenecks.append("File operations in loop - consider batch processing")
        
        # Check for database operations patterns
        if re.search(r'for.*:.*\.execute\(', code, re.DOTALL):
            bottlenecks.append("Database operations in loop - consider batch operations")
        
        return bottlenecks
    
    def _basic_logic_validation(self, code: str) -> Dict[str, Any]:
        """Basic logic validation without full validator"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check for basic logic issues
        if 'while True:' in code and 'break' not in code:
            result['warnings'].append("Potential infinite loop detected")
        
        # Check for unreachable code after return
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'return' in line and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('#'):
                    result['warnings'].append(f"Unreachable code after return at line {i + 1}")
        
        return result
    
    def _calculate_overall_score(self, report: ValidationReport):
        """Calculate overall validation score"""
        scores = []
        weights = []
        
        if report.syntax_result:
            scores.append(100 if report.syntax_result.is_valid else 0)
            weights.append(0.4)  # Syntax is most important
        
        if report.style_result:
            scores.append(report.style_result["score"])
            weights.append(0.2)
        
        if report.security_result:
            scores.append(report.security_result["score"])
            weights.append(0.3)
        
        if report.performance_result:
            scores.append(report.performance_result["score"])
            weights.append(0.1)
        
        if scores:
            report.overall_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        else:
            report.overall_score = 0
    
    def _generate_recommendations(self, report: ValidationReport):
        """Generate improvement recommendations"""
        recommendations = []
        
        if report.syntax_result and not report.syntax_result.is_valid:
            recommendations.append("Fix syntax errors before proceeding with other improvements")
        
        if report.style_result and report.style_result["score"] < 80:
            recommendations.append("Improve code style to follow PEP8 guidelines")
        
        if report.security_result and report.security_result["critical_issues"] > 0:
            recommendations.append("Address critical security vulnerabilities immediately")
        
        if report.performance_result and report.performance_result["complexity_score"] > 10:
            recommendations.append("Consider refactoring to reduce code complexity")
        
        if report.overall_score < 70:
            recommendations.append("Overall code quality is below acceptable threshold")
        
        report.recommendations = recommendations


# Test the enhanced validator
def test_enhanced_validator():
    """Test the enhanced validation framework"""
    validator = EnhancedValidator(ValidationLevel.STRICT)
    
    # Test code with various issues
    test_code = """
import os
def test_function():
    password = "hardcoded_password"
    x=1+2+3+4+5+6+7+8+9+10  # Long line that exceeds PEP8 limit of 79 characters
    eval("print('hello')")
    for i in range(len([1,2,3])):
        print(i)
"""
    
    report = validator.validate_code(test_code)
    
    print("Enhanced Validation Results:")
    print("=" * 50)
    print(f"Overall Score: {report.overall_score:.1f}")
    print(f"Valid: {report.is_valid()}")
    
    if report.syntax_result:
        print(f"Syntax Valid: {report.syntax_result.is_valid}")
    
    if report.style_result:
        print(f"Style Score: {report.style_result['score']}")
        print(f"Style Issues: {len(report.style_result['issues'])}")
    
    if report.security_result:
        print(f"Security Score: {report.security_result['score']}")
        print(f"Critical Issues: {report.security_result['critical_issues']}")
    
    if report.performance_result:
        print(f"Performance Score: {report.performance_result['score']}")
        print(f"Complexity: {report.performance_result['complexity_score']}")
    
    print(f"Recommendations: {len(report.recommendations)}")
    for rec in report.recommendations:
        print(f"  - {rec}")


if __name__ == "__main__":
    test_enhanced_validator()