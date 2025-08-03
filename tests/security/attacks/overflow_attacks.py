"""
Overflow attack testing module.

Tests for buffer overflow and memory exhaustion vulnerabilities.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class OverflowAttackTester(BaseSecurityTester):
    """Tests for overflow vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Overflow Attacks"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get overflow attack test payloads."""
        return [
            # Basic buffer overflow attempts
            ("A" * 100, "100 character overflow"),
            ("A" * 1000, "1K character overflow"),
            ("A" * 10000, "10K character overflow"),
            ("A" * 100000, "100K character overflow"),
            
            # Integer overflow
            ("2147483647", "Max 32-bit integer"),
            ("2147483648", "32-bit integer overflow"),
            ("9223372036854775807", "Max 64-bit integer"),
            ("9223372036854775808", "64-bit integer overflow"),
            
            # Format string attacks
            ("%s" * 10, "Format string %s"),
            ("%x" * 10, "Format string %x"),
            ("%n" * 10, "Format string %n"),
            ("%p" * 10, "Format string %p"),
            
            # Deep nesting
            ("[" * 1000 + "]" * 1000, "Deep bracket nesting"),
            ("{" * 1000 + "}" * 1000, "Deep brace nesting"),
            ("(" * 1000 + ")" * 1000, "Deep parenthesis nesting"),
            
            # Recursive patterns
            ("a" * 50 + "(" * 50 + ")" * 50, "Recursive pattern"),
            ("{{" * 100 + "}}" * 100, "Double bracket recursion"),
            
            # Memory exhaustion
            ("X" * 1048576, "1MB payload"),
            ("Y" * 10485760, "10MB payload"),
            
            # Stack overflow patterns
            ("PATTERN" * 10000, "Repeated pattern"),
            ("\\x41" * 10000, "Hex pattern"),
            
            # Null byte injections
            ("data\x00overflow", "Null byte injection"),
            ("\x00" * 100, "Multiple null bytes"),
            
            # Unicode overflow
            ("𝕏" * 10000, "Unicode character overflow"),
            ("🔥" * 10000, "Emoji overflow"),
            
            # Mixed overflow attempts
            ("A" * 500 + "\x00" + "B" * 500, "Mixed with null"),
            ("START" + "X" * 10000 + "END", "Wrapped overflow"),
            
            # Special characters overflow
            ("\n" * 10000, "Newline overflow"),
            ("\t" * 10000, "Tab overflow"),
            ("\r\n" * 5000, "CRLF overflow"),
            
            # Command injection with overflow
            (";" * 1000 + "whoami", "Semicolon overflow + cmd"),
            ("|" * 1000 + "id", "Pipe overflow + cmd"),
            
            # XML/JSON overflow
            ("<tag>" * 1000 + "</tag>" * 1000, "XML tag overflow"),
            ('{"key":"' + "A" * 10000 + '"}', "JSON value overflow"),
        ]
    
    def test_memory_limit(
        self,
        target_func,
        max_size: int = 100 * 1024 * 1024
    ):
        """Test memory limits with progressively larger payloads."""
        results = []
        sizes = [1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
        
        for size in sizes:
            if size > max_size:
                break
                
            payload = "M" * size
            try:
                result = target_func(payload)
                results.append({
                    "size": size,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "size": size,
                    "success": False,
                    "error": str(e)
                })
                
        return results