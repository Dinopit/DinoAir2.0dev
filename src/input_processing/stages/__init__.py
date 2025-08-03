"""
Input processing stages package for DinoAir InputSanitizer.

This package contains modular components for processing user input
through various security and enhancement stages.
"""

# Validation module
from .validation import (
    ValidationError,
    ThreatLevel,
    ValidationResult,
    InputValidator
)

# Escaping module
from .escaping import (
    EscapeStrategy,
    ClaudeEscaper,
    GPTEscaper,
    DefaultEscaper,
    TextEscaper,
    escape_for_model
)

# Pattern normalization module
from .pattern import (
    PatternNormalizer,
    FuzzyMatcher,
    normalize_input,
    fuzzy_match
)

# Profanity filtering module
from .profanity import (
    Severity,
    ProfanityMatch,
    FilterResult,
    ProfanityFilter,
    filter_profanity
)

# Intent classification module
from .intent import (
    IntentType,
    IntentClassification,
    IntentClassifier,
    classify_intent
)

# Rate limiting module
from .rate_limiter import (
    RateLimitStrategy,
    RateLimitConfig,
    RateLimitStatus,
    RateLimiter,
    get_rate_limiter,
    check_rate_limit,
    reset_rate_limit
)

# Enhanced security modules
from .enhanced_sanitizer import (
    EnhancedInputSanitizer,
    SecurityMonitor
)

__all__ = [
    # Validation
    'ValidationError',
    'ThreatLevel',
    'ValidationResult',
    'InputValidator',
    
    # Escaping
    'EscapeStrategy',
    'ClaudeEscaper',
    'GPTEscaper',
    'DefaultEscaper',
    'TextEscaper',
    'escape_for_model',
    
    # Pattern normalization
    'PatternNormalizer',
    'FuzzyMatcher',
    'normalize_input',
    'fuzzy_match',
    
    # Profanity filtering
    'Severity',
    'ProfanityMatch',
    'FilterResult',
    'ProfanityFilter',
    'filter_profanity',
    
    # Intent classification
    'IntentType',
    'IntentClassification',
    'IntentClassifier',
    'classify_intent',
    
    # Rate limiting
    'RateLimitStrategy',
    'RateLimitConfig',
    'RateLimitStatus',
    'RateLimiter',
    'get_rate_limiter',
    'check_rate_limit',
    'reset_rate_limit',
    
    # Enhanced security
    'EnhancedInputSanitizer',
    'SecurityMonitor'
]