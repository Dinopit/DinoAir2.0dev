"""
Refactored Red Team Security Testing Suite for DinoAir.

Uses modular attack components and sandbox for safe execution.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import modular attack testers
from tests.security.attacks import (
    PathTraversalTester,
    CommandInjectionTester,
    XSSTester,
    UnicodeAttackTester,
    RateLimitingTester,
    OverflowAttackTester,
    CombinedAttackTester
)

# Import sandbox for secure execution
from tests.security.core.sandbox import SecuritySandbox

# Import targets
from src.input_processing.input_sanitizer import InputSanitizer
from src.utils.Logger import Logger


class RedTeamTestSuite:
    """Orchestrates modular security tests with sandbox protection."""
    
    def __init__(self, use_sandbox: bool = True):
        """
        Initialize test suite.
        
        Args:
            use_sandbox: Whether to use sandbox for test execution
        """
        self.use_sandbox = use_sandbox
        self.logger = Logger()
        self.results = []
        
        # Initialize all attack testers
        self.testers = [
            PathTraversalTester(),
            CommandInjectionTester(),
            XSSTester(),
            UnicodeAttackTester(),
            RateLimitingTester(),
            OverflowAttackTester(),
            CombinedAttackTester()
        ]
        
        # Initialize sandbox if enabled
        self.sandbox = SecuritySandbox() if use_sandbox else None
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests and return results."""
        self.logger.info("Starting Red Team Security Tests")
        
        start_time = time.time()
        
        # Test InputSanitizer
        sanitizer_results = self._test_input_sanitizer()
        
        # Test GUI components (if available)
        gui_results = self._test_gui_security()
        
        # Calculate overall security score
        security_score = self._calculate_security_score(
            sanitizer_results + gui_results
        )
        
        duration = time.time() - start_time
        
        # Compile final report
        report = {
            "test_date": datetime.now().isoformat(),
            "duration": duration,
            "sandbox_enabled": self.use_sandbox,
            "security_score": security_score,
            "components": {
                "input_sanitizer": self._summarize_results(sanitizer_results),
                "gui": self._summarize_results(gui_results)
            },
            "detailed_results": sanitizer_results + gui_results,
            "recommendations": self._generate_recommendations(
                sanitizer_results + gui_results
            )
        }
        
        # Save report
        self._save_report(report)
        
        # Clean up sandbox
        if self.sandbox:
            self.sandbox.cleanup_sandbox()
            
        return report
        
    def _test_input_sanitizer(self) -> List[Dict[str, Any]]:
        """Test InputSanitizer with all attack modules."""
        results = []
        sanitizer = InputSanitizer()
        
        for tester in self.testers:
            self.logger.info(f"Running {tester.get_test_name()} tests")
            
            if self.use_sandbox and self.sandbox:
                # Run in sandbox
                result = self.sandbox.execute_in_sandbox(
                    self._run_tester_on_target,
                    args=(tester, sanitizer.sanitize_input)
                )
            else:
                # Run directly
                result = self._run_tester_on_target(
                    tester, 
                    sanitizer.sanitize_input
                )
                
            results.append({
                "component": "InputSanitizer",
                "test_type": tester.get_test_name(),
                "result": result
            })
            
        return results
        
    def _test_gui_security(self) -> List[Dict[str, Any]]:
        """Test GUI components for security vulnerabilities."""
        results = []
        
        # GUI tests would go here
        # For now, return placeholder
        results.append({
            "component": "GUI",
            "test_type": "Rendering Security",
            "result": {
                "success": True,
                "message": "GUI tests not yet implemented"
            }
        })
        
        return results
        
    def _run_tester_on_target(
        self, 
        tester, 
        target_func
    ) -> Dict[str, Any]:
        """Run a specific tester against a target function."""
        try:
            # Get test payloads
            payloads = tester.get_payloads()
            
            # Run tests
            passed = 0
            failed = 0
            errors = []
            
            for payload, description in payloads:
                try:
                    # Validate input before testing
                    if self.sandbox and not self.sandbox.validate_test_input(
                        payload
                    ):
                        errors.append({
                            "payload": payload,
                            "description": description,
                            "error": "Dangerous payload blocked by sandbox"
                        })
                        continue
                        
                    # Test the payload
                    result = target_func(payload)
                    
                    # Check if attack was blocked
                    if self._is_attack_blocked(result, payload):
                        passed += 1
                    else:
                        failed += 1
                        errors.append({
                            "payload": payload,
                            "description": description,
                            "result": result
                        })
                        
                except Exception as e:
                    errors.append({
                        "payload": payload,
                        "description": description,
                        "error": str(e)
                    })
                    
            return {
                "total_tests": len(payloads),
                "passed": passed,
                "failed": failed,
                "errors": errors[:10],  # Limit errors in report
                "success_rate": passed / len(payloads) if payloads else 0
            }
            
        except Exception as e:
            return {
                "error": f"Test execution failed: {str(e)}",
                "success": False
            }
            
    def _is_attack_blocked(self, result: Any, payload: str) -> bool:
        """Check if an attack payload was successfully blocked."""
        # Attack is blocked if:
        # 1. Result is empty or sanitized
        # 2. Dangerous patterns are removed
        # 3. No error occurred
        
        if not result:
            return True
            
        # Check for common attack patterns
        dangerous_patterns = [
            '../', '..\\', '<script', 'javascript:',
            '; ', '&&', '||', '|', '\x00'
        ]
        
        result_str = str(result).lower()
        payload_lower = payload.lower()
        
        # If dangerous patterns were in payload but not in result, blocked
        for pattern in dangerous_patterns:
            if pattern in payload_lower and pattern not in result_str:
                return True
                
        # If result is significantly different from payload, likely sanitized
        if len(result_str) < len(payload_lower) * 0.5:
            return True
            
        return False
        
    def _calculate_security_score(
        self, 
        results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall security score from test results."""
        total_score = 0
        test_count = 0
        
        for result in results:
            if "result" in result and isinstance(result["result"], dict):
                test_result = result["result"]
                if "success_rate" in test_result:
                    total_score += test_result["success_rate"]
                    test_count += 1
                    
        if test_count == 0:
            return 0.0
            
        # Convert to percentage
        return round((total_score / test_count) * 100, 2)
        
    def _summarize_results(
        self, 
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create summary of test results."""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for result in results:
            if "result" in result and isinstance(result["result"], dict):
                test_result = result["result"]
                total_tests += test_result.get("total_tests", 0)
                total_passed += test_result.get("passed", 0)
                total_failed += test_result.get("failed", 0)
                
        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": (total_passed / total_tests
                           if total_tests > 0 else 0)
        }
        
    def _generate_recommendations(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate security recommendations based on test results."""
        recommendations = []
        
        for result in results:
            if "result" not in result:
                continue
                
            test_result = result["result"]
            test_type = result.get("test_type", "Unknown")
            
            if (isinstance(test_result, dict) and
                test_result.get("failed", 0) > 0):
                if test_type == "Path Traversal":
                    recommendations.append(
                        "Strengthen path validation to prevent directory "
                        "traversal attacks"
                    )
                elif test_type == "Command Injection":
                    recommendations.append(
                        "Implement strict command sanitization and consider "
                        "using parameterized commands"
                    )
                elif test_type == "XSS":
                    recommendations.append(
                        "Enhance HTML escaping and implement Content Security "
                        "Policy (CSP)"
                    )
                elif test_type == "Unicode Attacks":
                    recommendations.append(
                        "Implement Unicode normalization and validate "
                        "character encodings"
                    )
                elif test_type == "Rate Limiting":
                    recommendations.append(
                        "Implement or strengthen rate limiting to prevent DoS "
                        "attacks"
                    )
                    
        return list(set(recommendations))  # Remove duplicates
        
    def _save_report(self, report: Dict[str, Any]):
        """Save security test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"security_report_{timestamp}.json"
        filepath = Path("tests/security/reports") / filename
        
        # Create directory if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save report
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
            
        self.logger.info(f"Security report saved to {filepath}")
        
        # Also save encrypted copy if sandbox available
        if self.sandbox:
            encrypted_path = self.sandbox.store_result_securely(
                f"red_team_test_{timestamp}",
                report
            )
            self.logger.info(f"Encrypted report saved to {encrypted_path}")


def main():
    """Run security tests."""
    # Create test suite
    suite = RedTeamTestSuite(use_sandbox=True)
    
    # Run tests
    report = suite.run_all_tests()
    
    # Print summary
    print(f"\n{'='*60}")
    print("Red Team Security Test Results")
    print(f"{'='*60}")
    print(f"Security Score: {report['security_score']}%")
    print(f"Duration: {report['duration']:.2f} seconds")
    print("\nComponent Results:")
    
    for component, summary in report['components'].items():
        print(f"\n{component}:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Success Rate: {summary['success_rate']*100:.1f}%")
        
    if report['recommendations']:
        print(f"\n{'='*60}")
        print("Security Recommendations:")
        print(f"{'='*60}")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
            
            
if __name__ == "__main__":
    main()