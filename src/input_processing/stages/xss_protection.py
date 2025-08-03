"""
XSS (Cross-Site Scripting) Protection Module.

Provides comprehensive protection against XSS attacks.
"""

import re
import html
from urllib.parse import unquote
from typing import Dict, Set


class XSSProtection:
    """Enhanced XSS protection module."""
    
    # HTML entities that must be encoded
    HTML_ENTITIES: Dict[str, str] = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    # Dangerous HTML tags
    DANGEROUS_TAGS: Set[str] = {
        'script', 'iframe', 'object', 'embed', 'form',
        'input', 'button', 'select', 'textarea', 'style',
        'link', 'meta', 'base', 'applet'
    }
    
    # Dangerous attributes
    DANGEROUS_ATTRS: Set[str] = {
        'onabort', 'onblur', 'onchange', 'onclick', 'ondblclick',
        'onerror', 'onfocus', 'onkeydown', 'onkeypress', 'onkeyup',
        'onload', 'onmousedown', 'onmousemove', 'onmouseout',
        'onmouseover', 'onmouseup', 'onreset', 'onresize',
        'onselect', 'onsubmit', 'onunload', 'onbeforeunload',
        'onhashchange', 'onmessage', 'onoffline', 'ononline',
        'onpopstate', 'onredo', 'onstorage', 'onundo',
        'onunhandledrejection', 'oncopy', 'oncut', 'onpaste'
    }
    
    # Dangerous protocols
    DANGEROUS_PROTOCOLS: Set[str] = {
        'javascript:', 'vbscript:', 'data:text/html',
        'data:application/x-javascript', 'mhtml:', 'x-schema:',
        'filesystem:', 'res:', 'wss:', 'ws:'
    }
    
    @staticmethod
    def encode_html(text: str) -> str:
        """Encode all HTML entities."""
        if not text:
            return text
            
        for char, entity in XSSProtection.HTML_ENTITIES.items():
            text = text.replace(char, entity)
        return text
    
    @staticmethod
    def strip_tags(text: str) -> str:
        """Remove all HTML tags and dangerous content."""
        if not text:
            return text
            
        # Remove all HTML comments
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # Remove all script tags and their content
        text = re.sub(
            r'<script[^>]*>.*?</script>', 
            '', 
            text, 
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Remove all style tags and their content
        text = re.sub(
            r'<style[^>]*>.*?</style>', 
            '', 
            text, 
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Remove all remaining tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove dangerous protocols
        for protocol in XSSProtection.DANGEROUS_PROTOCOLS:
            text = re.sub(
                rf'{re.escape(protocol)}[^"\'\s]*', 
                '', 
                text, 
                flags=re.IGNORECASE
            )
        
        return text.strip()
    
    @staticmethod
    def sanitize_attributes(html: str) -> str:
        """Remove dangerous attributes from HTML."""
        if not html:
            return html
            
        # Remove all event handlers
        for attr in XSSProtection.DANGEROUS_ATTRS:
            # Match various attribute formats
            patterns = [
                rf'\s*{attr}\s*=\s*"[^"]*"',  # Double quotes
                rf'\s*{attr}\s*=\s*\'[^\']*\'',  # Single quotes
                rf'\s*{attr}\s*=\s*[^\s>]+',  # No quotes
                rf'\s*{attr}(?=\s|>)',  # Boolean attribute
            ]
            
            for pattern in patterns:
                html = re.sub(pattern, '', html, flags=re.IGNORECASE)
        
        # Remove dangerous protocols in href/src attributes
        for protocol in XSSProtection.DANGEROUS_PROTOCOLS:
            html = re.sub(
                rf'(href|src)\s*=\s*["\']?'
                rf'{re.escape(protocol)}[^"\'>\s]*["\']?',
                r'\1=""',
                html,
                flags=re.IGNORECASE
            )
        
        return html
    
    @staticmethod
    def sanitize_css(css: str) -> str:
        """Sanitize CSS to prevent XSS."""
        if not css:
            return css
            
        # Remove JavaScript from CSS
        css = re.sub(
            r'javascript:[^;}\s]*', 
            '', 
            css, 
            flags=re.IGNORECASE
        )
        
        # Remove expression() calls (IE)
        css = re.sub(
            r'expression\s*\([^)]*\)', 
            '', 
            css, 
            flags=re.IGNORECASE
        )
        
        # Remove @import with dangerous URLs
        css = re.sub(
            r'@import\s+["\']?[^"\';\s]+["\']?', 
            '', 
            css, 
            flags=re.IGNORECASE
        )
        
        # Remove behavior property (IE)
        css = re.sub(
            r'behavior\s*:\s*[^;}\s]+', 
            '', 
            css, 
            flags=re.IGNORECASE
        )
        
        return css
    
    @staticmethod
    def detect_xss_attempt(text: str) -> bool:
        """Detect potential XSS attack patterns."""
        if not text:
            return False
            
        # Check for script tags
        if re.search(r'<script[^>]*>', text, re.IGNORECASE):
            return True
            
        # Check for event handlers
        for attr in XSSProtection.DANGEROUS_ATTRS:
            if re.search(rf'\b{attr}\s*=', text, re.IGNORECASE):
                return True
        
        # Check for dangerous protocols
        for protocol in XSSProtection.DANGEROUS_PROTOCOLS:
            if protocol.lower() in text.lower():
                return True
        
        # Check for encoded script tags
        encoded_patterns = [
            r'%3Cscript',  # URL encoded
            r'&lt;script',  # HTML encoded
            r'\\x3cscript',  # Hex encoded
            r'\\u003cscript',  # Unicode encoded
        ]
        
        for pattern in encoded_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def decode_all_encodings(text: str) -> str:
        """Decode URL encoding and HTML entities."""
        if not text:
            return text
            
        # URL decode (handle multiple levels of encoding)
        prev_text = ""
        while prev_text != text:
            prev_text = text
            try:
                text = unquote(text)
            except Exception:
                break
                
        # HTML entity decode
        text = html.unescape(text)
        
        # Decode common numeric entities
        text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
        text = re.sub(
            r'&#x([0-9a-fA-F]+);',
            lambda m: chr(int(m.group(1), 16)),
            text
        )
        
        return text
    
    @staticmethod
    def sanitize(text: str, allow_html: bool = False) -> str:
        """Main sanitization method."""
        if not text:
            return text
            
        # First decode all possible encodings to detect hidden attacks
        decoded_text = XSSProtection.decode_all_encodings(text)
        
        # Check if decoded text contains XSS attempts
        if XSSProtection.detect_xss_attempt(decoded_text):
            # If XSS detected in decoded form, strip everything
            text = XSSProtection.strip_tags(decoded_text)
            text = XSSProtection.encode_html(text)
            return text
            
        if allow_html:
            # Allow some HTML but sanitize dangerous parts
            text = XSSProtection.sanitize_attributes(text)
            text = XSSProtection.sanitize_css(text)
            
            # Remove dangerous tags
            for tag in XSSProtection.DANGEROUS_TAGS:
                text = re.sub(
                    rf'<{tag}[^>]*>.*?</{tag}>',
                    '',
                    text,
                    flags=re.DOTALL | re.IGNORECASE
                )
                text = re.sub(
                    rf'<{tag}[^>]*/?>', 
                    '', 
                    text,
                    flags=re.IGNORECASE
                )
        else:
            # Strip all HTML
            text = XSSProtection.strip_tags(text)
            # Then encode any remaining special characters
            text = XSSProtection.encode_html(text)
        
        return text