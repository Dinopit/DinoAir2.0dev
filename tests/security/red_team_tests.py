"""
Red Team Security Testing Suite for DinoAir InputSanitizer and GUI

This module implements comprehensive security testing including:
- Path traversal attacks
- Command injection attempts
- XSS payloads
- Unicode/encoding attacks
- Null byte injection
- Rate limiting bypass attempts
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Any
from pathlib import Path
from urllib.parse import quote, quote_plus
import unicodedata

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.input_processing.input_sanitizer import InputPipeline, InputPipelineError
from src.input_processing.stages import (
    InputValidator, ThreatLevel,
    IntentType, ValidationError
)


class RedTeamTester:
    """Comprehensive security testing framework for DinoAir."""
    
    def __init__(self, verbose: bool = True):
        """Initialize the red team tester.
        
        Args:
            verbose: Whether to print detailed results
        """
        self.verbose = verbose
        self.results = {
            'total_tests': 0,
            'blocked': 0,
            'passed': 0,
            'errors': 0,
            'bypasses': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Initialize test pipeline
        self.pipeline = InputPipeline(
            gui_feedback_hook=self._mock_gui_feedback,
            skip_empty_feedback=False,
            model_type="claude"
        )
        
        # Direct validator for focused testing
        self.validator = InputValidator()
        
        self.gui_feedback_log = []
    
    def _mock_gui_feedback(self, message: str):
        """Mock GUI feedback for testing."""
        self.gui_feedback_log.append(message)
        if self.verbose:
            print(f"[GUI] {message}")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all security tests and return results."""
        print("🛡️ DinoAir Red Team Security Testing Suite")
        print("=" * 60)
        
        # Test categories
        self._test_path_traversal()
        self._test_command_injection()
        self._test_xss_payloads()
        self._test_unicode_attacks()
        self._test_null_bytes()
        self._test_overflow_attacks()
        self._test_rate_limiting()
        self._test_encoding_bypasses()
        self._test_gui_specific_attacks()
        self._test_combined_attacks()
        
        # Generate report
        self._generate_report()
        
        return self.results
    
    def _test_path_traversal(self):
        """Test path traversal attack vectors."""
        print("\n🔍 Testing Path Traversal Attacks...")
        
        payloads = [
            # Basic traversal
            ("../etc/passwd", "Basic Unix traversal"),
            ("..\\Windows\\system.ini", "Basic Windows traversal"),
            ("../../../../../../../../etc/shadow", "Deep traversal"),
            
            # Double encoding
            ("%252e%252e%252fetc%252fpasswd", "Double URL encoding"),
            ("%252e%252e%255cwindows%255csystem.ini", "Double encoded Windows"),
            
            # Triple encoding
            ("%25252e%25252e%25252fetc%25252fpasswd", "Triple URL encoding"),
            
            # Mixed separators
            ("..//..//etc//passwd", "Mixed separators"),
            ("..\\\\..\\\\windows\\\\system.ini", "Double backslash"),
            ("..\\/\\..\\//etc/passwd", "Mixed slash types"),
            
            # Unicode variations
            ("..%c0%af..%c0%afetc%c0%afpasswd", "Unicode slash"),
            ("..%c1%9c..%c1%9cwindows%c1%9csystem.ini", "Unicode backslash"),
            
            # Null bytes (legacy Python 2)
            ("../etc/passwd\x00", "Null byte termination"),
            ("../etc/passwd%00.jpg", "Null byte with extension"),
            
            # URL encoded variations
            ("%2e%2e%2fetc%2fpasswd", "URL encoded dots"),
            ("%2e%2e%5cetc%5cpasswd", "URL encoded backslash"),
            ("..%252f..%252fetc%252fpasswd", "Mixed encoding levels"),
            
            # Windows UNC paths
            ("\\\\server\\share\\file", "UNC path"),
            ("//server/share/file", "Unix UNC style"),
            
            # Absolute paths
            ("C:\\Windows\\System32\\drivers\\etc\\hosts", "Windows absolute"),
            ("/etc/passwd", "Unix absolute"),
            ("C:/Windows/System32/config/sam", "Mixed separator absolute"),
            
            # Special encodings
            ("..%u002f..%u002fetc%u002fpasswd", "IIS Unicode"),
            ("..%uFF0F..%uFF0Fetc%uFF0Fpasswd", "Full-width slash"),
            
            # Overlong UTF-8
            ("\xc0\xae\xc0\xae/etc/passwd", "Overlong UTF-8"),
            
            # Case variations
            ("..%2F..%2Fetc%2Fpasswd", "Mixed case encoding"),
            
            # Special files
            ("../../../../../dev/null", "Device file access"),
            ("..\\..\\..\\..\\CON", "Windows reserved name"),
            ("../../../../proc/self/environ", "Process info access"),
        ]
        
        self._run_payload_tests(payloads, "Path Traversal")
    
    def _test_command_injection(self):
        """Test command injection attack vectors."""
        print("\n🔍 Testing Command Injection Attacks...")
        
        payloads = [
            # Basic injection
            ("; ls -la", "Semicolon command separator"),
            ("| whoami", "Pipe command"),
            ("& net user", "Ampersand command"),
            ("&& id", "Double ampersand"),
            ("|| cat /etc/passwd", "Double pipe"),
            
            # Backticks and substitution
            ("`cat /etc/passwd`", "Backtick substitution"),
            ("$(whoami)", "Dollar substitution"),
            ("${USER}", "Variable expansion"),
            
            # Newline injection
            ("\ncat /etc/passwd", "Newline injection"),
            ("\r\ndir c:\\", "CRLF injection"),
            
            # Encoded variations
            ("%3B%20ls%20-la", "URL encoded semicolon"),
            ("%7C%20whoami", "URL encoded pipe"),
            
            # Process substitution
            ("<(cat /etc/passwd)", "Process input substitution"),
            (">(malicious.sh)", "Process output substitution"),
            
            # Null byte injection
            ("test\x00; cat /etc/passwd", "Null byte separator"),
            
            # Unicode variations
            ("；ls", "Full-width semicolon"),
            ("｜whoami", "Full-width pipe"),
            
            # Combined with paths
            ("../../../bin/sh -c 'id'", "Path with command"),
            
            # Environment variable injection
            ("$PATH", "PATH variable"),
            ("${IFS}cat${IFS}/etc/passwd", "IFS abuse"),
            
            # Time-based
            ("; sleep 10", "Sleep command"),
            ("& ping -n 10 127.0.0.1", "Windows ping delay"),
        ]
        
        self._run_payload_tests(payloads, "Command Injection")
    
    def _test_xss_payloads(self):
        """Test XSS attack vectors."""
        print("\n🔍 Testing XSS Payloads...")
        
        payloads = [
            # Basic XSS
            ("<script>alert('XSS')</script>", "Basic script tag"),
            ("<img src=x onerror=alert('XSS')>", "Image tag XSS"),
            ("<svg onload=alert('XSS')>", "SVG tag XSS"),
            
            # Event handlers
            ("<body onload=alert('XSS')>", "Body onload"),
            ("<input onfocus=alert('XSS') autofocus>", "Input autofocus"),
            
            # JavaScript URLs
            ("javascript:alert('XSS')", "JavaScript protocol"),
            ("data:text/html,<script>alert('XSS')</script>", "Data URL"),
            
            # Encoded XSS
            ("%3Cscript%3Ealert('XSS')%3C/script%3E", "URL encoded"),
            ("&#60;script&#62;alert('XSS')&#60;/script&#62;", "HTML entities"),
            
            # Case variations
            ("<ScRiPt>alert('XSS')</ScRiPt>", "Mixed case"),
            ("<SCRIPT>alert('XSS')</SCRIPT>", "Upper case"),
            
            # Broken tags
            ("<script>alert('XSS')", "Unclosed tag"),
            ("<<script>alert('XSS')//", "Double bracket"),
            
            # Unicode XSS
            ("\u003cscript\u003ealert('XSS')\u003c/script\u003e", "Unicode escape"),
            
            # Bypass attempts
            ("<scr<script>ipt>alert('XSS')</scr</script>ipt>", "Nested tags"),
            ("<img src='x' onerror='alert`XSS`'>", "Template literals"),
        ]
        
        self._run_payload_tests(payloads, "XSS")
    
    def _test_unicode_attacks(self):
        """Test Unicode normalization attacks."""
        print("\n🔍 Testing Unicode Attacks...")
        
        payloads = [
            # Homoglyphs
            ("раyраl.com", "Cyrillic 'a' homoglyph"),
            ("gооgle.com", "Cyrillic 'o' homoglyph"),
            
            # Zero-width characters
            ("test\u200Bmalicious", "Zero-width space"),
            ("normal\uFEFFhidden", "Zero-width no-break space"),
            
            # Right-to-left override
            ("test\u202Egnivres", "Right-to-left override"),
            ("\u202Dpassword\u202C", "Left-to-right override"),
            
            # Normalization attacks
            ("ﬁle.txt", "Ligature 'fi'"),
            ("Ⅷ.txt", "Roman numeral VIII"),
            
            # Full-width forms
            ("ｆｕｌｌｗｉｄｔｈ", "Full-width Latin"),
            
            # Combining characters
            ("e\u0301vil", "e with combining acute"),
            
            # Invalid UTF-8
            ("\xc0\xae\xc0\xae", "Overlong encoding"),
            ("\xed\xa0\x80", "UTF-16 surrogate"),
        ]
        
        self._run_payload_tests(payloads, "Unicode")
    
    def _test_null_bytes(self):
        """Test null byte injection."""
        print("\n🔍 Testing Null Byte Attacks...")
        
        payloads = [
            # Direct null bytes
            ("file.txt\x00.jpg", "Null byte extension bypass"),
            ("admin\x00.php", "Null byte in filename"),
            
            # Encoded null bytes
            ("file.txt%00.jpg", "URL encoded null"),
            ("file.txt%2500.jpg", "Double encoded null"),
            
            # Multiple null bytes
            ("test\x00\x00\x00", "Multiple nulls"),
            
            # Null in different positions
            ("\x00admin", "Leading null"),
            ("ad\x00min", "Middle null"),
            ("admin\x00", "Trailing null"),
        ]
        
        self._run_payload_tests(payloads, "Null Byte")
    
    def _test_overflow_attacks(self):
        """Test buffer overflow attempts."""
        print("\n🔍 Testing Overflow Attacks...")
        
        payloads = [
            # Length attacks
            ("A" * 10000, "10K character input"),
            ("A" * 100000, "100K character input"),
            ("/" * 5000, "5K slashes"),
            
            # Deep nesting
            ("../" * 1000 + "etc/passwd", "Deep path traversal"),
            ("<" * 1000 + "script>", "Deep tag nesting"),
            
            # Unicode floods
            ("🔥" * 5000, "Emoji flood"),
            ("\u0301" * 10000, "Combining character flood"),
        ]
        
        self._run_payload_tests(payloads, "Overflow")
    
    def _test_encoding_bypasses(self):
        """Test various encoding bypass techniques."""
        print("\n🔍 Testing Encoding Bypasses...")
        
        payloads = [
            # Mixed encoding
            ("..%2f..%5c..%2f..%5cwindows", "Mixed slash encoding"),
            ("%2e%2e%252f%2e%2e%252f", "Mixed encoding levels"),
            
            # UTF-7
            ("+ADw-script+AD4-alert(1)+ADw-/script+AD4-", "UTF-7 XSS"),
            
            # Base64
            ("Li4vZXRjL3Bhc3N3ZA==", "Base64 traversal"),
            
            # Hex encoding
            ("0x2e2e2f6574632f706173737764", "Hex encoded"),
            
            # Octal
            ("\056\056\057\145\164\143", "Octal encoding"),
            
            # HTML5 entities
            ("&period;&period;&sol;", "HTML5 entities"),
        ]
        
        self._run_payload_tests(payloads, "Encoding Bypass")
    
    def _test_rate_limiting(self):
        """Test rate limiting effectiveness."""
        print("\n🔍 Testing Rate Limiting...")
        
        # Reset rate limiter
        self.pipeline.reset_rate_limit()
        
        rapid_fire_count = 0
        blocked_count = 0
        
        # Attempt rapid requests
        for i in range(100):
            try:
                self.pipeline.run(f"Test request {i}")
                rapid_fire_count += 1
            except InputPipelineError as e:
                if "rate limit" in str(e).lower() or "cooldown" in str(e).lower():
                    blocked_count += 1
            time.sleep(0.01)  # 10ms between requests
        
        print(f"  Rapid requests: {rapid_fire_count} allowed, {blocked_count} blocked")
        
        if blocked_count > 0:
            self.results['blocked'] += 1
            print("  ✓ Rate limiting is active")
        else:
            self.results['bypasses'].append({
                'type': 'Rate Limiting',
                'description': 'No rate limiting detected',
                'severity': 'HIGH'
            })
            print("  ✗ Rate limiting bypass detected!")
        
        self.results['total_tests'] += 1
    
    def _test_gui_specific_attacks(self):
        """Test GUI-specific attack vectors."""
        print("\n🔍 Testing GUI-Specific Attacks...")
        
        payloads = [
            # Qt/PySide6 specific
            ("<style>*{display:none}</style>", "CSS injection"),
            ("\\\\?\\C:\\Windows\\System32", "Windows device path"),
            
            # Emoji attacks
            ("🔥" * 1000 + "💣", "Emoji rendering overload"),
            
            # RTL/LTR mixing
            ("Hello \u202eworld", "RTL override in GUI"),
            
            # Control characters
            ("\x07\x08\x0C", "Bell/backspace/form feed"),
            
            # Format string attempts
            ("%s%s%s%s%s", "Format string"),
            ("{0}{1}{2}", "Format brackets"),
            
            # Path expansion
            ("~/../../../etc/passwd", "Tilde expansion"),
            ("$HOME/../../../", "Environment variable"),
        ]
        
        self._run_payload_tests(payloads, "GUI-Specific")
    
    def _test_combined_attacks(self):
        """Test combined/chained attack vectors."""
        print("\n🔍 Testing Combined Attacks...")
        
        payloads = [
            # Path traversal + command injection
            ("../../../bin/sh; cat /etc/passwd", "Path + command"),
            
            # XSS + path traversal
            ("<script>fetch('../../etc/passwd')</script>", "XSS + path"),
            
            # Unicode + command injection
            ("test\u202E; tac drowssap/cte/", "RTL + command"),
            
            # Null byte + XSS
            ("test.html\x00<script>alert(1)</script>", "Null + XSS"),
            
            # Multiple encoding layers
            ("%252e%252e%252f%3Bcat%20/etc/passwd", "Multi-encoded"),
        ]
        
        self._run_payload_tests(payloads, "Combined")
    
    def _run_payload_tests(self, payloads: List[Tuple[str, str]], 
                           category: str):
        """Run a set of payload tests.
        
        Args:
            payloads: List of (payload, description) tuples
            category: Category name for reporting
        """
        category_blocked = 0
        category_passed = 0
        
        for payload, description in payloads:
            self.results['total_tests'] += 1
            
            try:
                # Test through full pipeline
                result, intent = self.pipeline.run(payload)
                
                # Also test validator directly
                validation = self.validator.validate(payload)
                
                # Check if payload was modified/sanitized
                if (result != payload or 
                    validation.threat_level.value >= ThreatLevel.MEDIUM.value):
                    self.results['blocked'] += 1
                    category_blocked += 1
                    if self.verbose:
                        print(f"  ✓ Blocked: {description}")
                else:
                    self.results['passed'] += 1
                    category_passed += 1
                    self.results['bypasses'].append({
                        'category': category,
                        'payload': payload,
                        'description': description,
                        'threat_level': validation.threat_level.name
                    })
                    print(f"  ✗ BYPASS: {description}")
                    print(f"    Payload: {repr(payload)}")
                    
            except (InputPipelineError, ValidationError) as e:
                self.results['blocked'] += 1
                category_blocked += 1
                if self.verbose:
                    print(f"  ✓ Blocked: {description} - {str(e)}")
            except Exception as e:
                self.results['errors'] += 1
                print(f"  ⚠️ ERROR: {description} - {type(e).__name__}: {str(e)}")
        
        print(f"  {category} Summary: {category_blocked} blocked, "
              f"{category_passed} passed")
    
    def _generate_report(self):
        """Generate final security report."""
        print("\n" + "=" * 60)
        print("📊 SECURITY TEST SUMMARY")
        print("=" * 60)
        
        total = self.results['total_tests']
        blocked = self.results['blocked']
        passed = self.results['passed']
        errors = self.results['errors']
        
        if total > 0:
            block_rate = (blocked / total) * 100
            print(f"Total Tests: {total}")
            print(f"Blocked: {blocked} ({block_rate:.1f}%)")
            print(f"Passed: {passed}")
            print(f"Errors: {errors}")
            
            if self.results['bypasses']:
                print(f"\n⚠️ SECURITY BYPASSES DETECTED: {len(self.results['bypasses'])}")
                for bypass in self.results['bypasses'][:5]:  # Show first 5
                    print(f"  - {bypass['category']}: {bypass['description']}")
                if len(self.results['bypasses']) > 5:
                    print(f"  ... and {len(self.results['bypasses']) - 5} more")
            else:
                print("\n✅ No security bypasses detected!")
            
            # Security grade
            if block_rate >= 99:
                grade = "A+"
            elif block_rate >= 95:
                grade = "A"
            elif block_rate >= 90:
                grade = "B"
            elif block_rate >= 80:
                grade = "C"
            elif block_rate >= 70:
                grade = "D"
            else:
                grade = "F"
            
            print(f"\nSecurity Grade: {grade}")
            
            # Save detailed report
            self._save_report()
    
    def _save_report(self):
        """Save detailed report to file."""
        report_dir = Path("tests/security/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"red_team_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")


def main():
    """Run the red team security tests."""
    tester = RedTeamTester(verbose=True)
    results = tester.run_all_tests()
    
    # Return non-zero exit code if bypasses found
    if results['bypasses']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()