"""
SQL Injection Protection Module.

Provides comprehensive protection against SQL injection attacks.
"""

import re
from typing import Set, List, Any


class SQLInjectionProtection:
    """Enhanced SQL injection protection."""
    
    # SQL keywords that indicate injection attempts
    SQL_KEYWORDS: Set[str] = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'UNION',
        'WHERE', 'FROM', 'JOIN', 'TABLE', 'DATABASE',
        'SCRIPT', 'DECLARE', 'CAST', 'CONVERT', 'CHAR',
        'TRUNCATE', 'REPLACE', 'MERGE', 'CALL', 'EXPLAIN',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK', 'SAVEPOINT',
        'PROCEDURE', 'FUNCTION', 'TRIGGER', 'VIEW', 'INDEX'
    }
    
    # SQL operators and special characters
    SQL_OPERATORS: Set[str] = {
        '--', '/*', '*/', '@@', '@', 
        'CHAR(', 'NCHAR(', 'VARCHAR(', 'NVARCHAR(',
        'EXEC(', 'EXECUTE(', 'CAST(', 'CONVERT(',
        '0x', '\\x', 'PASSWORD(', 'ENCRYPT(',
        'CONCAT(', 'SUBSTRING(', 'LENGTH(', 'ASCII(',
        'MD5(', 'SHA1(', 'SHA2(', 'ENCODE(', 'DECODE(',
        'BENCHMARK(', 'SLEEP(', 'WAITFOR'
    }
    
    # Common SQL injection patterns
    SQL_PATTERNS: List[str] = [
        r"('\s*OR\s*'?\d*'?\s*=\s*'?\d*'?)",  # ' OR '1'='1' variations
        r"('\s*OR\s+\d+\s*=\s*\d+)",          # ' OR 1=1
        r"(;\s*DROP\s+TABLE\s+\w+)",          # ; DROP TABLE
        r"(;\s*DELETE\s+FROM\s+\w+)",         # ; DELETE FROM
        r"('\s*;\s*--)",                      # '; --
        r"(UNION\s+ALL\s+SELECT)",            # UNION ALL SELECT
        r"(UNION\s+SELECT)",                  # UNION SELECT
        r"(INTO\s+OUTFILE)",                  # INTO OUTFILE
        r"(LOAD_FILE\s*\()",                  # LOAD_FILE(
        r"(INTO\s+DUMPFILE)",                 # INTO DUMPFILE
        r"('\s*AND\s*SLEEP\s*\()",            # Time-based injection
        r"('\s*AND\s*BENCHMARK\s*\()",        # Benchmark injection
        r"(INFORMATION_SCHEMA)",              # Information schema access
        r"(sys\.databases)",                  # System tables
        r"(xp_cmdshell)",                     # Command execution
        r"('\s*HAVING\s+\d+\s*=\s*\d+)",      # HAVING clause injection
        r"('\s*GROUP\s+BY\s+\w+\s*--)",       # GROUP BY injection
        r"('\s*ORDER\s+BY\s+\d+\s*--)",       # ORDER BY injection
    ]
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """Detect potential SQL injection attempts."""
        if not text:
            return False
            
        text_upper = text.upper()
        
        # Check for SQL comments
        if '--' in text or '/*' in text or '*/' in text:
            return True
        
        # Check for multiple SQL keywords in suspicious context
        keyword_count = 0
        for keyword in SQLInjectionProtection.SQL_KEYWORDS:
            if f' {keyword} ' in f' {text_upper} ':
                keyword_count += 1
                if keyword_count >= 2:  # Multiple SQL keywords
                    return True
        
        # Check for SQL operators
        for operator in SQLInjectionProtection.SQL_OPERATORS:
            if operator.upper() in text_upper:
                return True
        
        # Check for specific injection patterns
        for pattern in SQLInjectionProtection.SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for hex-encoded SQL
        if re.search(r'0x[0-9a-fA-F]+', text):
            # Could be hex-encoded SQL
            return True
        
        # Check for string concatenation attempts
        if any(op in text for op in ['||', 'CONCAT', '+', 'CHR(']):
            # Check if it's in SQL context
            if any(kw in text_upper for kw in ['SELECT', 'WHERE', 'AND', 'OR']):
                return True
        
        return False
    
    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """Sanitize input for SQL queries."""
        if not text:
            return text
            
        # Remove SQL comments
        text = re.sub(r'--.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        
        # Escape single quotes (double them for SQL)
        text = text.replace("'", "''")
        
        # Remove/escape other dangerous characters
        dangerous_chars = {
            ';': '',  # Remove semicolons
            '\\': '\\\\',  # Escape backslashes
            '\x00': '',  # Remove null bytes
            '\n': ' ',  # Replace newlines with spaces
            '\r': ' ',  # Replace carriage returns
            '\x1a': '',  # Remove SUB character
            '"': '""',  # Escape double quotes
        }
        
        for char, replacement in dangerous_chars.items():
            text = text.replace(char, replacement)
        
        # Remove any remaining control characters
        text = re.sub(r'[\x00-\x1f\x7f]', '', text)
        
        return text.strip()
    
    @staticmethod
    def validate_identifier(identifier: str) -> bool:
        """Validate database identifiers (table/column names)."""
        if not identifier:
            return False
            
        # Only allow alphanumeric and underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            return False
            
        # Check length (most DBs have limits)
        if len(identifier) > 64:
            return False
            
        # Check against SQL keywords
        if identifier.upper() in SQLInjectionProtection.SQL_KEYWORDS:
            return False
            
        return True
    
    @staticmethod
    def escape_like_wildcards(text: str) -> str:
        """Escape wildcards for LIKE queries."""
        if not text:
            return text
            
        # Escape LIKE wildcards
        text = text.replace('\\', '\\\\')  # Escape backslash first
        text = text.replace('%', '\\%')
        text = text.replace('_', '\\_')
        text = text.replace('[', '\\[')
        
        return text
    
    @staticmethod
    def generate_parameterized_query(
        query_template: str, 
        params: dict
    ) -> tuple:
        """Generate a parameterized query with placeholders."""
        # Example: Convert "SELECT * FROM users WHERE name = {name}"
        # to ("SELECT * FROM users WHERE name = ?", ['value'])
        
        param_values = []
        param_index = 1
        
        def replace_param(match):
            nonlocal param_index
            param_name = match.group(1)
            if param_name in params:
                param_values.append(params[param_name])
                placeholder = f'${param_index}'  # PostgreSQL style
                # placeholder = '?'  # SQLite style
                # placeholder = '%s'  # MySQL style
                param_index += 1
                return placeholder
            return match.group(0)
        
        # Replace {param} with placeholders
        query = re.sub(r'\{(\w+)\}', replace_param, query_template)
        
        return query, tuple(param_values)


class SafeSQL:
    """Safe SQL query execution with parameterization."""
    
    @staticmethod
    def execute_query(
        connection: Any,
        query: str, 
        params: tuple = None,
        fetch_one: bool = False
    ) -> Any:
        """Execute SQL query with parameters safely."""
        cursor = connection.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESC')):
                return cursor.fetchone() if fetch_one else cursor.fetchall()
            else:
                connection.commit()
                return cursor.rowcount
                
        except Exception as e:
            connection.rollback()
            raise Exception(f"SQL execution error: {str(e)}")
        finally:
            cursor.close()
    
    @staticmethod
    def build_where_clause(conditions: dict, operator: str = 'AND') -> tuple:
        """Build a safe WHERE clause from conditions."""
        if not conditions:
            return '', ()
            
        clauses = []
        params = []
        
        for field, value in conditions.items():
            # Validate field name
            if not SQLInjectionProtection.validate_identifier(field):
                raise ValueError(f"Invalid field name: {field}")
            
            if isinstance(value, (list, tuple)):
                # IN clause
                placeholders = ', '.join(['?' for _ in value])
                clauses.append(f"{field} IN ({placeholders})")
                params.extend(value)
            elif value is None:
                clauses.append(f"{field} IS NULL")
            else:
                clauses.append(f"{field} = ?")
                params.append(value)
        
        where_clause = f" {operator} ".join(clauses)
        return where_clause, tuple(params)