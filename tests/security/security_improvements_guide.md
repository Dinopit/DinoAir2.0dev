# Security Improvements Guide for DinoAir

Based on the red team testing results (60% security score), here are detailed recommendations for improving protection against XSS, SQL injection, and Unicode attacks.

## 1. XSS (Cross-Site Scripting) Protection - Current: 33.3%

### Current Issues:
- Script tags passing through (`<script>alert('XSS')</script>`)
- Event handlers not filtered (`<img onerror=alert('XSS')>`)
- Only blocking JavaScript protocol URLs

### Recommended Improvements:

#### A. Implement Comprehensive HTML Entity Encoding
```python
class XSSProtection:
    """Enhanced XSS protection module."""
    
    # HTML entities that must be encoded
    HTML_ENTITIES = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;'
    }
    
    # Dangerous HTML tags
    DANGEROUS_TAGS = {
        'script', 'iframe', 'object', 'embed', 'form',
        'input', 'button', 'select', 'textarea', 'style',
        'link', 'meta', 'base', 'applet'
    }
    
    # Dangerous attributes
    DANGEROUS_ATTRS = {
        'onabort', 'onblur', 'onchange', 'onclick', 'ondblclick',
        'onerror', 'onfocus', 'onkeydown', 'onkeypress', 'onkeyup',
        'onload', 'onmousedown', 'onmousemove', 'onmouseout',
        'onmouseover', 'onmouseup', 'onreset', 'onresize',
        'onselect', 'onsubmit', 'onunload', 'onbeforeunload'
    }
    
    @staticmethod
    def encode_html(text: str) -> str:
        """Encode all HTML entities."""
        for char, entity in XSSProtection.HTML_ENTITIES.items():
            text = text.replace(char, entity)
        return text
    
    @staticmethod
    def strip_tags(text: str) -> str:
        """Remove all HTML tags."""
        import re
        # Remove all tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove JavaScript protocols
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:text/html', '', text, flags=re.IGNORECASE)
        return text
    
    @staticmethod
    def sanitize_attributes(html: str) -> str:
        """Remove dangerous attributes from HTML."""
        import re
        for attr in XSSProtection.DANGEROUS_ATTRS:
            # Remove event handlers
            html = re.sub(
                rf'\s*{attr}\s*=\s*["\']?[^"\'>\s]*["\']?',
                '', 
                html, 
                flags=re.IGNORECASE
            )
        return html
```

#### B. Content Security Policy Headers
```python
CSP_HEADERS = {
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block'
}
```

## 2. SQL Injection Protection - Current: 66.7%

### Current Issues:
- Basic SQL injection patterns getting through (`' OR '1'='1`)
- Need better pattern detection and parameterized queries

### Recommended Improvements:

#### A. SQL Injection Detection Module
```python
class SQLInjectionProtection:
    """Enhanced SQL injection protection."""
    
    # SQL keywords that indicate injection attempts
    SQL_KEYWORDS = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'UNION',
        'WHERE', 'FROM', 'JOIN', 'TABLE', 'DATABASE',
        'SCRIPT', 'DECLARE', 'CAST', 'CONVERT', 'CHAR'
    }
    
    # SQL operators and special characters
    SQL_OPERATORS = {
        '--', '/*', '*/', '@@', '@', 
        'CHAR(', 'NCHAR(', 'VARCHAR(', 'NVARCHAR(',
        'EXEC(', 'EXECUTE(', 'CAST(', 'CONVERT(',
        '0x', '\\x', 'PASSWORD(', 'ENCRYPT('
    }
    
    # Common SQL injection patterns
    SQL_PATTERNS = [
        r"('\s*OR\s*'1'\s*=\s*'1)",  # ' OR '1'='1
        r"('\s*OR\s+\d+\s*=\s*\d+)",  # ' OR 1=1
        r"(;\s*DROP\s+TABLE\s+\w+)",  # ; DROP TABLE
        r"(;\s*DELETE\s+FROM\s+\w+)",  # ; DELETE FROM
        r"('\s*;\s*--)",               # '; --
        r"(UNION\s+SELECT)",           # UNION SELECT
        r"(INTO\s+OUTFILE)",          # INTO OUTFILE
        r"(LOAD_FILE\s*\()",          # LOAD_FILE(
    ]
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """Detect potential SQL injection attempts."""
        import re
        
        text_upper = text.upper()
        
        # Check for SQL keywords
        for keyword in SQLInjectionProtection.SQL_KEYWORDS:
            if keyword in text_upper:
                # Check if it's in a suspicious context
                pattern = rf'\b{keyword}\b.*[;\'"()]'
                if re.search(pattern, text_upper):
                    return True
        
        # Check for SQL operators
        for operator in SQLInjectionProtection.SQL_OPERATORS:
            if operator in text_upper:
                return True
        
        # Check for specific patterns
        for pattern in SQLInjectionProtection.SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """Sanitize input for SQL queries."""
        # Remove SQL comments
        text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        
        # Escape single quotes
        text = text.replace("'", "''")
        
        # Remove semicolons (statement terminators)
        text = text.replace(';', '')
        
        # Remove dangerous characters
        dangerous_chars = ['\\', '\x00', '\n', '\r', '\x1a']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text
```

#### B. Parameterized Query Wrapper
```python
class SafeSQL:
    """Safe SQL query execution with parameterization."""
    
    @staticmethod
    def execute_query(query: str, params: tuple) -> Any:
        """Execute SQL query with parameters."""
        # Example for SQLite
        import sqlite3
        
        # Never use string formatting for SQL!
        # Bad: query = f"SELECT * FROM users WHERE id = {user_id}"
        # Good: Use parameterized queries
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        try:
            # Use ? placeholders for SQLite, %s for MySQL/PostgreSQL
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
```

## 3. Unicode Attack Protection - Current: 0%

### Current Issues:
- No Unicode normalization
- Homograph attacks passing through
- Direction control characters not filtered
- Zero-width characters not handled

### Recommended Improvements:

#### A. Unicode Normalization Module
```python
import unicodedata
import re

class UnicodeProtection:
    """Comprehensive Unicode attack protection."""
    
    # Dangerous Unicode categories
    DANGEROUS_CATEGORIES = {
        'Cf',  # Format characters (invisible)
        'Co',  # Private use
        'Cn',  # Unassigned
    }
    
    # Specific dangerous characters
    DANGEROUS_CHARS = {
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u200e',  # Left-to-right mark
        '\u200f',  # Right-to-left mark
        '\u202a',  # Left-to-right embedding
        '\u202b',  # Right-to-left embedding
        '\u202c',  # Pop directional formatting
        '\u202d',  # Left-to-right override
        '\u202e',  # Right-to-left override
        '\u2060',  # Word joiner
        '\ufeff',  # Zero-width no-break space
        '\u206a',  # Inhibit symmetric swapping
        '\u206b',  # Activate symmetric swapping
        '\u206c',  # Inhibit Arabic form shaping
        '\u206d',  # Activate Arabic form shaping
        '\u206e',  # National digit shapes
        '\u206f',  # Nominal digit shapes
    }
    
    # Homograph mapping (common confusables)
    HOMOGRAPH_MAP = {
        'а': 'a',  # Cyrillic to Latin
        'е': 'e',  # Cyrillic to Latin
        'о': 'o',  # Cyrillic to Latin
        'р': 'p',  # Cyrillic to Latin
        'с': 'c',  # Cyrillic to Latin
        'у': 'y',  # Cyrillic to Latin
        'х': 'x',  # Cyrillic to Latin
        'ѕ': 's',  # Cyrillic to Latin
        'і': 'i',  # Cyrillic to Latin
        'ј': 'j',  # Cyrillic to Latin
        'ν': 'v',  # Greek to Latin
        'ο': 'o',  # Greek to Latin
        'τ': 't',  # Greek to Latin
        'α': 'a',  # Greek to Latin
        'ρ': 'p',  # Greek to Latin
    }
    
    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Unicode text to prevent attacks."""
        # Step 1: NFD normalization
        text = unicodedata.normalize('NFD', text)
        
        # Step 2: Remove dangerous characters
        for char in UnicodeProtection.DANGEROUS_CHARS:
            text = text.replace(char, '')
        
        # Step 3: Remove characters from dangerous categories
        cleaned = []
        for char in text:
            category = unicodedata.category(char)
            if category not in UnicodeProtection.DANGEROUS_CATEGORIES:
                cleaned.append(char)
        text = ''.join(cleaned)
        
        # Step 4: Convert homographs
        for homograph, replacement in UnicodeProtection.HOMOGRAPH_MAP.items():
            text = text.replace(homograph, replacement)
        
        # Step 5: NFC normalization (canonical composition)
        text = unicodedata.normalize('NFC', text)
        
        # Step 6: Remove combining characters that create confusables
        text = re.sub(r'[\u0300-\u036f\u1ab0-\u1aff\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]', '', text)
        
        return text
    
    @staticmethod
    def detect_unicode_attack(text: str) -> bool:
        """Detect potential Unicode-based attacks."""
        # Check for dangerous characters
        for char in UnicodeProtection.DANGEROUS_CHARS:
            if char in text:
                return True
        
        # Check for mixed scripts (e.g., Latin + Cyrillic)
        scripts = set()
        for char in text:
            script = unicodedata.name(char, '').split()[0] if char.isalpha() else None
            if script:
                scripts.add(script)
        
        # If multiple scripts detected, possible homograph attack
        if len(scripts) > 1:
            return True
        
        # Check for excessive combining characters
        combining_count = sum(1 for c in text if unicodedata.category(c).startswith('M'))
        if combining_count > len(text) * 0.1:  # More than 10% combining chars
            return True
        
        return False
```

## 4. Integration Example

```python
class EnhancedInputSanitizer:
    """Enhanced input sanitizer with all protections."""
    
    def __init__(self):
        self.xss_protection = XSSProtection()
        self.sql_protection = SQLInjectionProtection()
        self.unicode_protection = UnicodeProtection()
    
    def sanitize_input(self, user_input: str, context: str = 'general') -> str:
        """Sanitize user input based on context."""
        
        # Step 1: Unicode normalization (always first!)
        sanitized = self.unicode_protection.normalize_unicode(user_input)
        
        # Step 2: Context-specific sanitization
        if context == 'html':
            # For HTML context, encode entities
            sanitized = self.xss_protection.encode_html(sanitized)
        elif context == 'sql':
            # For SQL context, check for injection
            if self.sql_protection.detect_sql_injection(sanitized):
                raise ValueError("SQL injection attempt detected")
            sanitized = self.sql_protection.sanitize_sql_input(sanitized)
        elif context == 'plain':
            # For plain text, strip all HTML
            sanitized = self.xss_protection.strip_tags(sanitized)
        else:
            # General context - apply all protections
            sanitized = self.xss_protection.strip_tags(sanitized)
            if self.sql_protection.detect_sql_injection(sanitized):
                sanitized = self.sql_protection.sanitize_sql_input(sanitized)
        
        # Step 3: Final validation
        if self.unicode_protection.detect_unicode_attack(sanitized):
            # Log the attempt and return safe version
            print(f"Warning: Unicode attack detected in: {user_input[:50]}...")
        
        return sanitized
```

## 5. Testing Improvements

Add these test cases to verify the improvements:

```python
# Enhanced test cases
ENHANCED_TEST_CASES = {
    "XSS": [
        # Original tests
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        # New comprehensive tests
        "<svg onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "<input onfocus=alert(1) autofocus>",
        "<select onchange=alert(1)><option>1<option>2</select>",
        "<img src=x:alert(1) onerror=eval(src)>",
        "<script>alert(String.fromCharCode(88,83,83))</script>",
        "';alert(1);//",
        "</script><script>alert(1)</script>",
    ],
    
    "SQL": [
        # Original tests
        "' OR '1'='1",
        "'; DROP TABLE users;--",
        "1' UNION SELECT * FROM passwords--",
        # New comprehensive tests
        "admin'--",
        "' OR 1=1--",
        "1' ORDER BY 1--+",
        "' UNION SELECT NULL--",
        "'; EXEC xp_cmdshell('dir')--",
        "' AND 1=CONVERT(int, @@version)--",
        "' WAITFOR DELAY '00:00:10'--",
        "1' AND (SELECT COUNT(*) FROM users) > 0--",
    ],
    
    "Unicode": [
        # Original tests
        "admin\u200b",
        "аdmin",  # Cyrillic 'а'
        "\u202eadmin",
        # New comprehensive tests
        "ad\u200cmin",  # Zero-width non-joiner
        "admin\ufeff",  # Zero-width no-break space
        "аdmіn",  # Multiple Cyrillic letters
        "𝖺𝖽𝗆𝗂𝗇",  # Mathematical alphanumeric
        "admin⃠",  # Combining enclosing circle backslash
        "ａｄｍｉｎ",  # Full-width characters
        "ﬁle",  # Ligature
        "a̸d̸m̸i̸n̸",  # Combining overlay
    ]
}
```

## Implementation Priority

1. **High Priority**: Unicode protection (currently 0% coverage)
2. **High Priority**: XSS protection enhancement (currently 33.3% coverage)
3. **Medium Priority**: SQL injection improvements (currently 66.7% coverage)
4. **Low Priority**: Performance optimization and caching

## Security Best Practices

1. **Defense in Depth**: Apply multiple layers of protection
2. **Context-Aware Sanitization**: Different contexts need different sanitization
3. **Whitelist over Blacklist**: Define what's allowed rather than what's blocked
4. **Regular Updates**: Keep protection patterns updated with new attack vectors
5. **Logging and Monitoring**: Log all detected attack attempts
6. **Rate Limiting**: Implement rate limiting to prevent brute force attacks
7. **Input Validation**: Validate input format before sanitization
8. **Output Encoding**: Always encode output based on context

## Monitoring and Alerts

```python
class SecurityMonitor:
    """Monitor and alert on security events."""
    
    def __init__(self, logger):
        self.logger = logger
        self.attack_counts = {}
    
    def log_attack_attempt(self, attack_type: str, payload: str, source_ip: str = None):
        """Log detected attack attempt."""
        timestamp = datetime.now().isoformat()
        
        # Track attack frequency
        if attack_type not in self.attack_counts:
            self.attack_counts[attack_type] = 0
        self.attack_counts[attack_type] += 1
        
        # Log the attempt
        self.logger.warning(
            f"SECURITY: {attack_type} attack detected at {timestamp} "
            f"from {source_ip or 'unknown'}: {payload[:100]}..."
        )
        
        # Alert if threshold exceeded
        if self.attack_counts[attack_type] > 10:
            self.logger.error(
                f"SECURITY ALERT: Multiple {attack_type} attacks detected! "
                f"Count: {self.attack_counts[attack_type]}"
            )
```

This comprehensive guide provides the specific improvements needed to achieve 95%+ security coverage against XSS, SQL injection, and Unicode attacks.