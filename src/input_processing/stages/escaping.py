"""Character escaping module for LLM safety.

Escapes special characters based on the target LLM model
to prevent prompt injection and formatting issues.
"""

from typing import Protocol, Dict
from abc import ABC, abstractmethod


class EscapeStrategy(ABC):
    """Abstract base for escaping strategies."""
    
    @abstractmethod
    def escape(self, text: str) -> str:
        """Escape text for safe LLM consumption.
        
        Args:
            text: Input text to escape
            
        Returns:
            Escaped text safe for the target model
        """
        pass


class ClaudeEscaper(EscapeStrategy):
    """Escaping strategy for Claude models.
    
    Claude uses XML-like tags, so we need to escape
    XML special characters to prevent tag injection.
    """
    
    def escape(self, text: str) -> str:
        """Escape XML-like tags for Claude.
        
        Args:
            text: Input text to escape
            
        Returns:
            Text with XML entities escaped
        """
        # Order matters - escape & first to avoid double escaping
        replacements = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&apos;'
        }
        
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
            
        return result


class GPTEscaper(EscapeStrategy):
    """Escaping strategy for GPT models.
    
    GPT models are sensitive to markdown and code blocks,
    so we escape those patterns.
    """
    
    def escape(self, text: str) -> str:
        """Escape markdown and code blocks for GPT.
        
        Args:
            text: Input text to escape
            
        Returns:
            Text with markdown patterns escaped
        """
        import re
        
        # Escape triple backticks first
        text = text.replace('```', '\\`\\`\\`')
        
        # Escape markdown special chars if at line start
        # This prevents unintended formatting
        patterns = [
            (r'^#', r'\\#'),      # Headers
            (r'^\*', r'\\*'),     # Lists/emphasis
            (r'^-', r'\\-'),      # Lists
            (r'^\+', r'\\+'),     # Lists
            (r'^>', r'\\>'),      # Quotes
            (r'^\|', r'\\|'),     # Tables
            (r'^`', r'\\`'),      # Inline code at line start
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
            
        # Escape inline markdown patterns that could break formatting
        # But be careful not to over-escape normal text
        if text.count('*') >= 2:  # Only escape if there are pairs
            text = re.sub(r'(\*+)', r'\\\1', text)
        if text.count('_') >= 2:  # Only escape if there are pairs
            text = re.sub(r'(_+)', r'\\\1', text)
            
        return text


class DefaultEscaper(EscapeStrategy):
    """Default escaping for general safety.
    
    Provides minimal escaping that works across most models.
    """
    
    def escape(self, text: str) -> str:
        """Minimal escaping for general use.
        
        Args:
            text: Input text to escape
            
        Returns:
            Text with basic HTML entities escaped
        """
        # Just handle basic HTML entities for safety
        # Order matters - escape & first
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Also escape common prompt injection patterns
        # These work across most models
        text = text.replace('[[', '\\[\\[')
        text = text.replace(']]', '\\]\\]')
        text = text.replace('{{', '\\{\\{')
        text = text.replace('}}', '\\}\\}')
        
        return text


class TextEscaper:
    """Main escaper that delegates to appropriate strategy.
    
    This class manages different escaping strategies based on
    the target LLM model, ensuring text is properly escaped
    for safe consumption.
    """
    
    def __init__(self, model_type: str = "default"):
        """Initialize with specified model type.
        
        Args:
            model_type: Type of model ('claude', 'gpt', 'default')
        """
        self.strategies: Dict[str, EscapeStrategy] = {
            'claude': ClaudeEscaper(),
            'gpt': GPTEscaper(),
            'default': DefaultEscaper()
        }
        self.set_model(model_type)
    
    def set_model(self, model_type: str) -> None:
        """Set the escaping strategy based on model type.
        
        Args:
            model_type: Type of model to escape for
        """
        self.model_type = model_type.lower()
        self.current_strategy = self.strategies.get(
            self.model_type, 
            self.strategies['default']
        )
    
    def escape(self, text: str) -> str:
        """Escape text using current strategy.
        
        Args:
            text: Input text to escape
            
        Returns:
            Escaped text safe for the current model
        """
        if not text:
            return text
            
        return self.current_strategy.escape(text)
    
    def get_model_type(self) -> str:
        """Get the current model type.
        
        Returns:
            Current model type string
        """
        return self.model_type
    
    def add_custom_strategy(self, name: str, strategy: EscapeStrategy) -> None:
        """Add a custom escaping strategy.
        
        Args:
            name: Name for the strategy
            strategy: EscapeStrategy implementation
        """
        self.strategies[name.lower()] = strategy


# Convenience function for direct use
def escape_for_model(text: str, model_type: str = "default") -> str:
    """Escape text for a specific model type.
    
    Args:
        text: Text to escape
        model_type: Target model type
        
    Returns:
        Escaped text
    """
    escaper = TextEscaper(model_type)
    return escaper.escape(text)