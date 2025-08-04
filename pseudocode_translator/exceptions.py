"""
Custom exception hierarchy for the Pseudocode Translator

This module defines a comprehensive set of exceptions with rich context
information to provide better error messages and debugging capabilities.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ErrorContext:
    """
    Context information for an error occurrence
    """
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code_snippet: Optional[str] = None
    surrounding_lines: Optional[List[str]] = None
    suggestions: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_suggestion(self, suggestion: str):
        """Add a suggestion for fixing the error"""
        if suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def format_location(self) -> str:
        """Format the error location"""
        if self.line_number is not None:
            if self.column_number is not None:
                return f"line {self.line_number}, column {self.column_number}"
            return f"line {self.line_number}"
        return "unknown location"
    
    def format_code_context(self) -> str:
        """Format the code context with line numbers"""
        if not self.code_snippet:
            return ""
        
        lines = []
        if self.surrounding_lines and self.line_number:
            # Show surrounding lines with line numbers
            start_line = max(
                1, self.line_number - len(self.surrounding_lines) // 2
            )
            
            for i, line in enumerate(self.surrounding_lines):
                line_num = start_line + i
                prefix = ">>>" if line_num == self.line_number else "   "
                lines.append(f"{prefix} {line_num:4d} | {line}")
                
                # Add error pointer if we have column info
                if line_num == self.line_number and self.column_number:
                    pointer = " " * (8 + self.column_number) + "^"
                    lines.append(pointer)
        else:
            # Just show the snippet
            lines.append(self.code_snippet)
        
        return "\n".join(lines)


class TranslatorError(Exception):
    """
    Base exception for all translator errors
    
    Provides rich error context and formatting capabilities
    """
    
    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize the translator error
        
        Args:
            message: Main error message
            context: Optional error context with location and suggestions
            cause: Optional underlying exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        self.cause = cause
    
    def add_suggestion(self, suggestion: str):
        """Add a suggestion for fixing the error"""
        self.context.add_suggestion(suggestion)
    
    def with_context(self, **kwargs) -> 'TranslatorError':
        """
        Add context information to the error
        
        Returns:
            Self for method chaining
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        return self
    
    def format_error(
        self,
        include_suggestions: bool = True,
        include_context: bool = True
    ) -> str:
        """
        Format the error message with full context
        
        Args:
            include_suggestions: Whether to include fix suggestions
            include_context: Whether to include code context
            
        Returns:
            Formatted error message
        """
        parts = [f"{self.__class__.__name__}: {self.message}"]
        
        # Add location
        location = self.context.format_location()
        if location != "unknown location":
            parts.append(f"  Location: {location}")
        
        # Add code context
        if include_context:
            code_context = self.context.format_code_context()
            if code_context:
                parts.append("\n  Code context:")
                parts.append(self._indent(code_context, 4))
        
        # Add suggestions
        if include_suggestions and self.context.suggestions:
            parts.append("\n  Suggestions:")
            for i, suggestion in enumerate(self.context.suggestions, 1):
                parts.append(f"    {i}. {suggestion}")
        
        # Add related errors
        if self.context.related_errors:
            parts.append("\n  Related errors:")
            for error in self.context.related_errors:
                parts.append(f"    - {error}")
        
        # Add cause if present
        if self.cause:
            parts.append(
                f"\n  Caused by: {type(self.cause).__name__}: "
                f"{str(self.cause)}"
            )
        
        return "\n".join(parts)
    
    def _indent(self, text: str, spaces: int) -> str:
        """Indent text by specified spaces"""
        indent = " " * spaces
        return "\n".join(indent + line for line in text.splitlines())
    
    def __str__(self) -> str:
        """String representation of the error"""
        return self.format_error()


class ParsingError(TranslatorError):
    """
    Error during pseudocode parsing
    
    Raised when the parser encounters syntax errors or cannot
    properly identify code blocks
    """
    
    def __init__(
        self,
        message: str,
        block_content: Optional[str] = None,
        block_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize parsing error
        
        Args:
            message: Error message
            block_content: Content of the block that failed to parse
            block_type: Type of block (ENGLISH, PYTHON, MIXED)
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        if block_content:
            self.context.code_snippet = block_content
            self.context.metadata['block_type'] = block_type
            
            # Add common parsing error suggestions
            self._add_parsing_suggestions(block_content, message)
    
    def _add_parsing_suggestions(self, content: str, message: str):
        """Add suggestions based on common parsing errors"""
        message_lower = message.lower()
        
        if "indent" in message_lower:
            self.add_suggestion(
                "Check indentation - ensure consistent use of spaces or tabs"
            )
            self.add_suggestion(
                "Verify that block indentation matches the expected level"
            )
            
        if "syntax" in message_lower:
            keywords = ['if', 'for', 'while', 'def', 'class']
            if (":" not in content and
                    any(kw in content for kw in keywords)):
                self.add_suggestion(
                    "Add missing colon (:) at the end of control statements"
                )
            
            if content.count('(') != content.count(')'):
                self.add_suggestion("Check for mismatched parentheses")
            if content.count('[') != content.count(']'):
                self.add_suggestion("Check for mismatched square brackets")
            if content.count('{') != content.count('}'):
                self.add_suggestion("Check for mismatched curly braces")
                
        if "unexpected" in message_lower:
            self.add_suggestion("Check for missing or extra punctuation")
            self.add_suggestion("Verify that all strings are properly closed")


class ValidationError(TranslatorError):
    """
    Error during code validation
    
    Raised when generated code fails syntax or logic validation
    """
    
    def __init__(
        self,
        message: str,
        validation_type: str = "syntax",
        failed_code: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error
        
        Args:
            message: Error message
            validation_type: Type of validation that failed
                (syntax, logic, security)
            failed_code: Code that failed validation
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        self.validation_type = validation_type
        self.context.metadata['validation_type'] = validation_type
        
        if failed_code:
            self.context.code_snippet = failed_code
            self._add_validation_suggestions(
                failed_code, message, validation_type
            )
    
    def _add_validation_suggestions(
        self, code: str, message: str, val_type: str
    ):
        """Add suggestions based on validation errors"""
        if val_type == "syntax":
            self.add_suggestion("Review Python syntax requirements")
            self.add_suggestion(
                "Check the Python documentation for correct syntax"
            )
            
        elif val_type == "logic":
            if "undefined" in message.lower():
                # Extract variable name if possible
                import re
                match = re.search(r"'(\w+)'", message)
                if match:
                    var_name = match.group(1)
                    self.add_suggestion(f"Define '{var_name}' before using it")
                    self.add_suggestion(
                        f"Check if '{var_name}' is imported from "
                        f"another module"
                    )
                    
                    # Check for common typos
                    common_vars = [
                        'print', 'len', 'range', 'str', 'int',
                        'float', 'list', 'dict'
                    ]
                    for common in common_vars:
                        if self._is_similar(var_name, common):
                            self.add_suggestion(
                                f"Did you mean '{common}' instead of "
                                f"'{var_name}'?"
                            )
            
            if "return" in message.lower():
                self.add_suggestion("Add a return statement to the function")
                self.add_suggestion("Check that all code paths return a value")
                
        elif val_type == "security":
            self.add_suggestion("Review security best practices")
            self.add_suggestion("Consider using safer alternatives")
    
    def _is_similar(self, s1: str, s2: str) -> bool:
        """Check if two strings are similar (simple edit distance)"""
        if abs(len(s1) - len(s2)) > 2:
            return False
        
        # Simple check for one character difference
        if len(s1) == len(s2):
            diff_count = sum(1 for a, b in zip(s1, s2) if a != b)
            return diff_count <= 1
        
        return False


class AssemblyError(TranslatorError):
    """
    Error during code assembly
    
    Raised when the assembler cannot properly combine code blocks
    """
    
    def __init__(
        self,
        message: str,
        blocks_info: Optional[List[Dict[str, Any]]] = None,
        assembly_stage: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize assembly error
        
        Args:
            message: Error message
            blocks_info: Information about blocks being assembled
            assembly_stage: Stage where assembly failed
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        if blocks_info:
            self.context.metadata['blocks_info'] = blocks_info
            self.context.metadata['block_count'] = len(blocks_info)
            
        if assembly_stage:
            self.context.metadata['assembly_stage'] = assembly_stage
            self._add_assembly_suggestions(assembly_stage, message)
    
    def _add_assembly_suggestions(self, stage: str, message: str):
        """Add suggestions based on assembly stage"""
        if stage == "imports":
            self.add_suggestion("Check for conflicting import statements")
            self.add_suggestion("Verify module names are correct")
            
        elif stage == "indentation":
            self.add_suggestion(
                "Ensure consistent indentation across all blocks"
            )
            self.add_suggestion("Check for mixed tabs and spaces")
            
        elif stage == "merging":
            self.add_suggestion(
                "Check for duplicate function or class definitions"
            )
            self.add_suggestion(
                "Verify that code blocks can be logically combined"
            )
            
        elif stage == "dependencies":
            self.add_suggestion(
                "Check that all required variables are defined"
            )
            self.add_suggestion("Verify function call order")


class ConfigurationError(TranslatorError):
    """
    Error in translator configuration
    
    Raised when configuration is invalid or incompatible
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize configuration error
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            config_value: Invalid configuration value
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        if config_key:
            self.context.metadata['config_key'] = config_key
            
        if config_value is not None:
            self.context.metadata['config_value'] = config_value
            
        if config_key:
            self._add_config_suggestions(config_key, config_value, message)
    
    def _add_config_suggestions(
        self, key: Optional[str], value: Any, message: str
    ):
        """Add suggestions for configuration errors"""
        if key == "model_name":
            self.add_suggestion("Check that the model name is supported")
            self.add_suggestion(
                "Verify API credentials if using external models"
            )
            
        elif key == "max_tokens":
            self.add_suggestion("Use a positive integer value for max_tokens")
            self.add_suggestion("Consider model-specific token limits")
            
        elif key == "temperature":
            self.add_suggestion(
                "Use a value between 0.0 and 2.0 for temperature"
            )
            self.add_suggestion(
                "Lower values (0.0-0.3) for more deterministic output"
            )
            
        elif key == "api_key":
            self.add_suggestion(
                "Ensure API key is set in environment variables"
            )
            self.add_suggestion(
                "Check that the API key has proper permissions"
            )


class CacheError(TranslatorError):
    """
    Error in caching operations
    
    Raised when cache operations fail
    """
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        cache_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize cache error
        
        Args:
            message: Error message
            operation: Cache operation that failed (get, set, clear)
            cache_key: Key involved in the operation
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        if operation:
            self.context.metadata['operation'] = operation
            
        if cache_key:
            self.context.metadata['cache_key'] = cache_key
            
        if operation:
            self._add_cache_suggestions(operation, message)
    
    def _add_cache_suggestions(
        self, operation: Optional[str], message: str
    ):
        """Add suggestions for cache errors"""
        if operation == "get":
            self.add_suggestion("Check cache configuration and availability")
            self.add_suggestion("Verify cache key format")
            
        elif operation == "set":
            self.add_suggestion("Check available cache storage space")
            self.add_suggestion("Verify serialization of cached data")
            
        elif operation == "clear":
            self.add_suggestion("Ensure proper cache permissions")
            self.add_suggestion("Check if cache is locked by another process")


class RecoveryError(TranslatorError):
    """
    Error during error recovery attempts
    
    Raised when automatic error recovery fails
    """
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        recovery_attempts: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize recovery error
        
        Args:
            message: Error message
            original_error: The original error that triggered recovery
            recovery_attempts: List of recovery attempts made
            **kwargs: Additional context arguments
        """
        super().__init__(message, cause=original_error, **kwargs)
        
        if recovery_attempts:
            self.context.metadata['recovery_attempts'] = recovery_attempts
            self.context.related_errors.extend(recovery_attempts)
            
        self.add_suggestion("Manual intervention may be required")
        self.add_suggestion("Review the original error for root cause")


class StreamingError(TranslatorError):
    """
    Error during streaming operations
    
    Raised when streaming translation fails or encounters issues
    """
    
    def __init__(
        self,
        message: str,
        stream_position: Optional[int] = None,
        chunk_index: Optional[int] = None,
        stream_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize streaming error
        
        Args:
            message: Error message
            stream_position: Position in stream where error occurred
            chunk_index: Index of chunk being processed
            stream_type: Type of stream (file, socket, pipe, etc.)
            **kwargs: Additional context arguments
        """
        super().__init__(message, **kwargs)
        
        if stream_position is not None:
            self.context.metadata['stream_position'] = stream_position
            
        if chunk_index is not None:
            self.context.metadata['chunk_index'] = chunk_index
            
        if stream_type:
            self.context.metadata['stream_type'] = stream_type
            self._add_streaming_suggestions(stream_type, message)
    
    def _add_streaming_suggestions(self, stream_type: str, message: str):
        """Add suggestions for streaming errors"""
        if "memory" in message.lower():
            self.add_suggestion("Reduce chunk size for processing")
            self.add_suggestion("Enable compression for large streams")
            self.add_suggestion("Use buffer limits to control memory usage")
            
        if "timeout" in message.lower():
            self.add_suggestion("Increase timeout value for slow streams")
            self.add_suggestion(
                "Check network connectivity for remote streams"
            )
            
        if stream_type == "socket":
            self.add_suggestion("Verify socket connection is still active")
            self.add_suggestion("Check for network interruptions")
            
        elif stream_type == "file":
            self.add_suggestion(
                "Ensure file is not being modified during read"
            )
            self.add_suggestion("Check file permissions and accessibility")


# Utility functions for error handling

def format_syntax_error(e: SyntaxError, code: str) -> ParsingError:
    """
    Convert a Python SyntaxError to a ParsingError with context
    
    Args:
        e: The syntax error
        code: The code that caused the error
        
    Returns:
        ParsingError with rich context
    """
    lines = code.splitlines()
    
    # Extract surrounding lines
    surrounding = []
    if e.lineno:
        start = max(0, e.lineno - 3)
        end = min(len(lines), e.lineno + 2)
        surrounding = lines[start:end]
    
    # Create context
    context = ErrorContext(
        line_number=e.lineno,
        column_number=e.offset,
        code_snippet=(
            lines[e.lineno - 1]
            if e.lineno and e.lineno <= len(lines)
            else None
        ),
        surrounding_lines=surrounding
    )
    
    # Create parsing error
    error = ParsingError(
        message=f"Syntax error: {e.msg}",
        context=context,
        cause=e
    )
    
    return error


def aggregate_errors(errors: List[TranslatorError]) -> TranslatorError:
    """
    Aggregate multiple errors into a single error with all context
    
    Args:
        errors: List of errors to aggregate
        
    Returns:
        Single TranslatorError containing all error information
    """
    if not errors:
        return TranslatorError("No errors to aggregate")
    
    if len(errors) == 1:
        return errors[0]
    
    # Create main message
    main_message = f"Multiple errors occurred ({len(errors)} total)"
    
    # Aggregate all suggestions
    all_suggestions = []
    related_messages = []
    
    for i, error in enumerate(errors, 1):
        related_messages.append(f"Error {i}: {error.message}")
        all_suggestions.extend(error.context.suggestions)
    
    # Remove duplicate suggestions
    unique_suggestions = list(dict.fromkeys(all_suggestions))
    
    # Create aggregated error
    context = ErrorContext(
        suggestions=unique_suggestions,
        related_errors=related_messages,
        metadata={'error_count': len(errors)}
    )
    
    return TranslatorError(main_message, context=context)