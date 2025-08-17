"""
Notes Security Module - Centralized security utilities for the Notes feature.
Provides sanitization, validation, and rate limiting for all notes-related
inputs, including HTML content sanitization for rich text editing.
"""

from typing import Optional, Dict, Any, List, Callable
from functools import wraps
import time
import re
from html.parser import HTMLParser

from src.input_processing.stages.enhanced_sanitizer import (
    EnhancedInputSanitizer
)
from src.utils.logger import Logger


class NotesSecurityConfig:
    """Configuration for Notes security settings."""
    
    # Maximum lengths for different fields
    MAX_TITLE_LENGTH = 255
    MAX_CONTENT_LENGTH = 10 * 1024  # 10KB
    MAX_TAG_LENGTH = 50
    MAX_TAGS_PER_NOTE = 20
    MAX_SEARCH_QUERY_LENGTH = 200
    
    # Rate limiting settings
    MAX_SAVES_PER_MINUTE = 60  # 1 per second average
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Sanitization contexts
    CONTEXT_TITLE = 'plain'
    CONTEXT_CONTENT = 'plain'  # Plain text content
    CONTEXT_HTML = 'html'  # Rich text HTML content
    CONTEXT_TAG = 'plain'
    CONTEXT_SEARCH = 'sql'
    
    # HTML sanitization whitelist
    ALLOWED_HTML_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 's', 'span',
        'ul', 'ol', 'li', 'div'
    }
    
    # Allowed attributes for specific tags
    ALLOWED_ATTRIBUTES = {
        'span': ['style'],
        'p': ['style'],
        'div': ['style']
    }
    
    # Allowed CSS properties in style attribute
    ALLOWED_STYLE_PROPERTIES = {
        'color', 'background-color', 'text-align',
        'font-family', 'font-size', 'font-weight',
        'font-style', 'text-decoration'
    }


class RateLimiter:
    """Simple rate limiter for auto-save operations."""
    
    def __init__(self, max_calls: int, window_seconds: int):
        """Initialize rate limiter.
        
        Args:
            max_calls: Maximum number of calls allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = []
        self.logger = Logger()
        
    def is_allowed(self) -> bool:
        """Check if a call is allowed under the rate limit."""
        now = time.time()
        
        # Remove old calls outside the window
        self.calls = [
            call_time for call_time in self.calls 
            if now - call_time < self.window_seconds
        ]
        
        # Check if we're under the limit
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        else:
            self.logger.warning(
                f"Rate limit exceeded: {len(self.calls)} calls in "
                f"{self.window_seconds} seconds"
            )
            return False
            
    def reset(self):
        """Reset the rate limiter."""
        self.calls.clear()


class HTMLSanitizer(HTMLParser):
    """Custom HTML parser for sanitizing rich text content."""
    
    def __init__(self):
        """Initialize HTML sanitizer."""
        super().__init__(convert_charrefs=True)
        self.reset()  # Initialize parser state
        self.logger = Logger()
        
    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag.lower() in NotesSecurityConfig.ALLOWED_HTML_TAGS:
            # Filter attributes
            safe_attrs = []
            
            for attr_name, attr_value in attrs:
                allowed_attrs = NotesSecurityConfig.ALLOWED_ATTRIBUTES
                if (tag in allowed_attrs and
                        attr_name in allowed_attrs[tag]):
                    
                    if attr_name == 'style' and attr_value:
                        # Sanitize style attribute
                        safe_style = self._sanitize_style(attr_value)
                        if safe_style:
                            safe_attrs.append((attr_name, safe_style))
                    else:
                        safe_attrs.append((attr_name, attr_value))
                        
            # Build safe tag
            attr_str = ' '.join(
                f'{name}="{value}"' for name, value in safe_attrs
            )
            if attr_str:
                self.sanitized_html.append(f'<{tag} {attr_str}>')
            else:
                self.sanitized_html.append(f'<{tag}>')
                
            self.tag_stack.append(tag)
        else:
            # Log stripped tags
            self.stripped_tags.append(tag)
            self.logger.warning(f"Stripped unsafe HTML tag: {tag}")
            
    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag.lower() in NotesSecurityConfig.ALLOWED_HTML_TAGS:
            self.sanitized_html.append(f'</{tag}>')
            if tag in self.tag_stack:
                self.tag_stack.remove(tag)
                
    def handle_data(self, data):
        """Handle text data."""
        # Escape any HTML entities in the data
        escaped = data.replace('&', '&amp;')
        escaped = escaped.replace('<', '&lt;')
        escaped = escaped.replace('>', '&gt;')
        self.sanitized_html.append(escaped)
        
    def _sanitize_style(self, style_value: str) -> Optional[str]:
        """Sanitize CSS style attribute value.
        
        Args:
            style_value: Raw style attribute value
            
        Returns:
            Sanitized style string or None if all properties were removed
        """
        if not style_value:
            return None
            
        # Parse CSS properties
        properties = []
        for prop in style_value.split(';'):
            if ':' in prop:
                name, value = prop.split(':', 1)
                name = name.strip().lower()
                value = value.strip()
                
                # Only allow whitelisted properties
                if name in NotesSecurityConfig.ALLOWED_STYLE_PROPERTIES:
                    # Additional validation for specific properties
                    if name in ('color', 'background-color'):
                        # Validate color values
                        if self._is_safe_color(value):
                            properties.append(f'{name}: {value}')
                    elif name == 'text-align':
                        # Only allow specific alignment values
                        if value in ('left', 'center', 'right', 'justify'):
                            properties.append(f'{name}: {value}')
                    elif name == 'font-size':
                        # Validate font size
                        if self._is_safe_font_size(value):
                            properties.append(f'{name}: {value}')
                    else:
                        # Other allowed properties
                        properties.append(f'{name}: {value}')
                        
        return '; '.join(properties) if properties else None
        
    def _is_safe_color(self, color: str) -> bool:
        """Check if a color value is safe.
        
        Args:
            color: CSS color value
            
        Returns:
            True if color is safe, False otherwise
        """
        # Allow hex colors
        if re.match(r'^#[0-9a-fA-F]{3,6}$', color):
            return True
            
        # Allow rgb/rgba
        rgb_pattern = (r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*'
                       r'(,\s*[\d.]+\s*)?\)$')
        if re.match(rgb_pattern, color):
            return True
            
        # Allow common named colors
        safe_colors = {
            'black', 'white', 'red', 'green', 'blue', 'yellow',
            'orange', 'purple', 'gray', 'grey', 'brown', 'pink',
            'cyan', 'magenta', 'transparent'
        }
        return color.lower() in safe_colors
        
    def _is_safe_font_size(self, size: str) -> bool:
        """Check if a font size value is safe.
        
        Args:
            size: CSS font size value
            
        Returns:
            True if size is safe, False otherwise
        """
        # Allow px, pt, em, rem units with reasonable ranges
        if re.match(r'^\d+(\.\d+)?(px|pt|em|rem)$', size):
            return True
            
        # Allow percentage
        if re.match(r'^\d+%$', size):
            return True
            
        return False
        
    def get_sanitized_html(self) -> str:
        """Get the sanitized HTML string.
        
        Returns:
            Sanitized HTML
        """
        return ''.join(self.sanitized_html)
        
    def get_stripped_tags(self) -> List[str]:
        """Get list of tags that were stripped.
        
        Returns:
            List of stripped tag names
        """
        return self.stripped_tags
        
    def reset(self):
        """Reset the sanitizer for reuse."""
        super().reset()  # Reset parent parser state
        self.sanitized_html = []
        self.tag_stack = []
        self.stripped_tags = []


class NotesSecurity:
    """Centralized security utilities for the Notes feature."""
    
    def __init__(self):
        """Initialize Notes security utilities."""
        self.sanitizer = EnhancedInputSanitizer()
        self.logger = Logger()
        self.rate_limiter = RateLimiter(
            NotesSecurityConfig.MAX_SAVES_PER_MINUTE,
            NotesSecurityConfig.RATE_LIMIT_WINDOW
        )
        
    def sanitize_note_title(self, title: str) -> str:
        """Sanitize note title.
        
        Args:
            title: Raw title input
            
        Returns:
            Sanitized title
        """
        if not title:
            return ""
            
        sanitized = self.sanitizer.sanitize_input(
            title,
            context=NotesSecurityConfig.CONTEXT_TITLE,
            max_length=NotesSecurityConfig.MAX_TITLE_LENGTH,
            strict_mode=True
        )
        
        # Log if significantly modified
        if sanitized != title:
            self.logger.info(
                f"Title sanitized: length={len(title)} -> {len(sanitized)}"
            )
            
        return sanitized
        
    def sanitize_note_content(self, content: str) -> str:
        """Sanitize note content.
        
        Args:
            content: Raw content input
            
        Returns:
            Sanitized content
        """
        if not content:
            return ""
            
        sanitized = self.sanitizer.sanitize_input(
            content,
            context=NotesSecurityConfig.CONTEXT_CONTENT,
            max_length=NotesSecurityConfig.MAX_CONTENT_LENGTH,
            strict_mode=True
        )
        
        # Log if significantly modified
        if sanitized != content:
            self.logger.info(
                f"Content sanitized: length={len(content)} -> {len(sanitized)}"
            )
            
        return sanitized
        
    def sanitize_tag(self, tag: str) -> Optional[str]:
        """Sanitize a single tag.
        
        Args:
            tag: Raw tag input
            
        Returns:
            Sanitized tag or None if invalid
        """
        if not tag or not tag.strip():
            return None
            
        sanitized = self.sanitizer.sanitize_input(
            tag.strip(),
            context=NotesSecurityConfig.CONTEXT_TAG,
            max_length=NotesSecurityConfig.MAX_TAG_LENGTH,
            strict_mode=True
        )
        
        # Reject if tag changed significantly (possible attack)
        if not sanitized or len(sanitized) < len(tag) * 0.5:
            self.logger.warning(
                f"Tag rejected after sanitization: '{tag}' -> '{sanitized}'"
            )
            return None
            
        return sanitized
        
    def sanitize_tags(self, tags: List[str]) -> List[str]:
        """Sanitize a list of tags.
        
        Args:
            tags: List of raw tag inputs
            
        Returns:
            List of sanitized tags
        """
        if not tags:
            return []
            
        # Limit number of tags
        if len(tags) > NotesSecurityConfig.MAX_TAGS_PER_NOTE:
            self.logger.warning(
                f"Too many tags: {len(tags)}, limiting to "
                f"{NotesSecurityConfig.MAX_TAGS_PER_NOTE}"
            )
            tags = tags[:NotesSecurityConfig.MAX_TAGS_PER_NOTE]
            
        # Sanitize each tag
        sanitized_tags = []
        for tag in tags:
            sanitized = self.sanitize_tag(tag)
            if sanitized:
                sanitized_tags.append(sanitized)
                
        return sanitized_tags
        
    def sanitize_search_query(self, query: str) -> str:
        """Sanitize search query for SQL safety.
        
        Args:
            query: Raw search query
            
        Returns:
            Sanitized search query
        """
        if not query:
            return ""
            
        # First apply general sanitization
        sanitized = self.sanitizer.sanitize_input(
            query,
            context=NotesSecurityConfig.CONTEXT_SEARCH,
            max_length=NotesSecurityConfig.MAX_SEARCH_QUERY_LENGTH
        )
        
        # Then escape SQL wildcards for LIKE queries
        sanitized = self.escape_sql_wildcards(sanitized)
        
        return sanitized
        
    def escape_sql_wildcards(self, text: str) -> str:
        """Escape SQL wildcard characters for safe LIKE queries.
        
        Args:
            text: Text that may contain SQL wildcards
            
        Returns:
            Text with escaped wildcards
        """
        if not text:
            return ""
            
        # Escape % and _ characters for SQL LIKE
        text = text.replace('\\', '\\\\')  # Escape backslash first
        text = text.replace('%', '\\%')
        text = text.replace('_', '\\_')
        
        return text
        
    def validate_note_data(
        self, 
        title: str, 
        content: str, 
        tags: List[str]
    ) -> Dict[str, Any]:
        """Validate note data before saving.
        
        Args:
            title: Note title
            content: Note content
            tags: Note tags
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        # Validate title
        if len(title) > NotesSecurityConfig.MAX_TITLE_LENGTH:
            errors.append(
                f"Title too long: {len(title)} characters "
                f"(max {NotesSecurityConfig.MAX_TITLE_LENGTH})"
            )
            
        # Validate content
        if len(content) > NotesSecurityConfig.MAX_CONTENT_LENGTH:
            errors.append(
                f"Content too long: {len(content)} bytes "
                f"(max {NotesSecurityConfig.MAX_CONTENT_LENGTH})"
            )
            
        # Validate tags
        if len(tags) > NotesSecurityConfig.MAX_TAGS_PER_NOTE:
            errors.append(
                f"Too many tags: {len(tags)} "
                f"(max {NotesSecurityConfig.MAX_TAGS_PER_NOTE})"
            )
            
        for tag in tags:
            if len(tag) > NotesSecurityConfig.MAX_TAG_LENGTH:
                errors.append(
                    f"Tag too long: '{tag[:20]}...' "
                    f"({len(tag)} chars, max "
                    f"{NotesSecurityConfig.MAX_TAG_LENGTH})"
                )
                
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
        
    def sanitize_note_data(
        self, 
        title: str, 
        content: str, 
        tags: List[str]
    ) -> Dict[str, Any]:
        """Sanitize all note data.
        
        Args:
            title: Raw title
            content: Raw content
            tags: Raw tags list
            
        Returns:
            Dictionary with sanitized data and validation results
        """
        # Sanitize each field
        sanitized_title = self.sanitize_note_title(title)
        sanitized_content = self.sanitize_note_content(content)
        sanitized_tags = self.sanitize_tags(tags)
        
        # Validate sanitized data
        validation = self.validate_note_data(
            sanitized_title, 
            sanitized_content, 
            sanitized_tags
        )
        
        return {
            'title': sanitized_title,
            'content': sanitized_content,
            'tags': sanitized_tags,
            'valid': validation['valid'],
            'errors': validation['errors'],
            'modified': (
                sanitized_title != title or
                sanitized_content != content or
                sanitized_tags != tags
            )
        }
        
    def rate_limit_auto_save(self, func: Callable) -> Callable:
        """Decorator for rate limiting auto-save operations.
        
        Args:
            func: Function to rate limit
            
        Returns:
            Rate-limited function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.rate_limiter.is_allowed():
                return func(*args, **kwargs)
            else:
                self.logger.warning(
                    "Auto-save rate limit exceeded, skipping save"
                )
                return {
                    'success': False,
                    'error': 'Rate limit exceeded, please wait before '
                             'saving again'
                }
                
        return wrapper
        
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary.
        
        Returns:
            Dictionary with security statistics
        """
        return self.sanitizer.get_security_summary()
        
    def reset_rate_limiter(self):
        """Reset the rate limiter (useful for testing)."""
        self.rate_limiter.reset()


# Singleton instance for consistent security handling
_notes_security_instance = None


def get_notes_security() -> NotesSecurity:
    """Get the singleton NotesSecurity instance.
    
    Returns:
        NotesSecurity instance
    """
    global _notes_security_instance
    if _notes_security_instance is None:
        _notes_security_instance = NotesSecurity()
    return _notes_security_instance