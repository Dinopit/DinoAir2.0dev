"""
Path traversal attack testing module.

Tests for directory traversal vulnerabilities in DinoAir.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class PathTraversalTester(BaseSecurityTester):
    """Tests for path traversal vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Path Traversal"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get path traversal test payloads."""
        return [
            # Basic traversal
            ("../etc/passwd", "Basic Unix traversal"),
            ("..\\Windows\\system.ini", "Basic Windows traversal"),
            ("../../../../../../../../etc/shadow", "Deep traversal"),
            
            # Double encoding
            ("%252e%252e%252fetc%252fpasswd", "Double URL encoding"),
            ("%252e%252e%255cwindows%255csystem.ini", 
             "Double encoded Windows"),
            
            # Triple encoding
            ("%25252e%25252e%25252fetc%25252fpasswd", 
             "Triple URL encoding"),
            
            # Mixed separators
            ("..//..//etc//passwd", "Mixed separators"),
            ("..\\\\..\\\\windows\\\\system.ini", "Double backslash"),
            ("..\\/\\..\\//etc/passwd", "Mixed slash types"),
            
            # Unicode variations
            ("..%c0%af..%c0%afetc%c0%afpasswd", "Unicode slash"),
            ("..%c1%9c..%c1%9cwindows%c1%9csystem.ini", 
             "Unicode backslash"),
            
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
            ("C:\\Windows\\System32\\drivers\\etc\\hosts", 
             "Windows absolute"),
            ("/etc/passwd", "Unix absolute"),
            ("C:/Windows/System32/config/sam", 
             "Mixed separator absolute"),
            
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