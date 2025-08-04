"""Input sanitization pipeline for processing user input before sending to LLM.

This module provides a pipeline that validates, escapes, normalizes, filters,
and classifies user input to ensure clean and safe interaction with the
LLM model.
"""

from typing import Tuple, Protocol, Optional, Any, List
from datetime import datetime

# Import all modular components from stages
from .stages import (
    # Validation
    InputValidator, ThreatLevel,
    # Escaping
    TextEscaper,
    # Pattern normalization
    PatternNormalizer,
    # Profanity filtering
    ProfanityFilter, Severity,
    # Intent classification
    IntentClassifier, IntentType,
    # Rate limiting
    RateLimiter, RateLimitConfig, RateLimitStrategy,
    # Enhanced security
    EnhancedInputSanitizer
)

# Import command handlers
from .command_handlers import WatchdogCommandHandler


class InputPipelineError(Exception):
    """Custom exception for input pipeline errors."""
    pass


class GUIFeedback(Protocol):
    """Protocol for GUI feedback callback."""
    def __call__(self, message: str) -> None:
        """Display feedback message to the user."""
        ...


class ContextManager:
    """Manage conversation context history."""
    
    def __init__(self, history_limit=5):
        """Initialize context manager with history limit."""
        self.history = []  # list of past prompts or intents
        self.limit = history_limit
    
    def add_entry(self, entry: str):
        """Add entry to context history."""
        self.history.append(entry)
        if len(self.history) > self.limit:
            self.history.pop(0)
    
    def get_context(self) -> str:
        """Get context as concatenated string."""
        return " ".join(self.history)


class InputPipeline:
    """Pipeline for processing and sanitizing user input.
    
    This class orchestrates the input sanitization process through multiple
    stages: validation, escaping, pattern normalization, profanity filtering,
    and intent classification.
    
    Optimized for chat interface usage with graceful error handling.
    
    Attributes:
        gui_feedback: Callback function to send feedback to the GUI.
        skip_empty_feedback: Whether to skip feedback for empty inputs.
    """
    
    def __init__(self, gui_feedback_hook: GUIFeedback,
                 skip_empty_feedback: bool = True,
                 model_type: str = "default", cooldown_seconds: float = 1.5,
                 watchdog_ref: Optional[Any] = None,
                 main_window_ref: Optional[Any] = None,
                 enable_enhanced_security: bool = True) -> None:
        """Initialize the input pipeline.
        
        Args:
            gui_feedback_hook: Callable that accepts a string message to
                display feedback in the GUI (e.g., status bar updates).
            skip_empty_feedback: If True, don't show feedback for empty inputs.
            model_type: Type of LLM model for specific escaping
                ("claude", "gpt", "default").
            cooldown_seconds: Cooldown period for rate limiting.
            watchdog_ref: Reference to the watchdog instance for command
                handling.
            main_window_ref: Reference to main window for accessing app
                components.
            enable_enhanced_security: Enable comprehensive XSS, SQL injection,
                and Unicode protection.
        """
        self.gui_feedback = gui_feedback_hook
        self.skip_empty_feedback = skip_empty_feedback
        
        # Initialize modular components
        self.validator = InputValidator()
        self.escaper = TextEscaper(model_type)
        self.pattern_normalizer = PatternNormalizer()
        self.profanity_filter = ProfanityFilter()
        self.intent_classifier = IntentClassifier()
        
        # Initialize enhanced security if enabled
        self.enable_enhanced_security = enable_enhanced_security
        if enable_enhanced_security:
            from src.utils.logger import Logger
            logger = Logger() if watchdog_ref else None
            self.enhanced_sanitizer = EnhancedInputSanitizer(logger)
        else:
            self.enhanced_sanitizer = None
        
        # Configure rate limiter
        rate_config = RateLimitConfig(
            max_requests=60,
            window_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        self.rate_limiter = RateLimiter(rate_config)
        
        # Initialize context manager (kept from original)
        self.context = ContextManager()
        
        # Initialize watchdog command handler
        self.watchdog_handler = WatchdogCommandHandler(
            watchdog=watchdog_ref,
            chat_callback=gui_feedback_hook
        )
        
        # Store references for legacy compatibility
        self.watchdog_ref = watchdog_ref
        self.main_window_ref = main_window_ref
        
        # Store alerts history for legacy compatibility
        self.watchdog_alerts_history: List[Tuple[str, str, datetime]] = []
        
        # User identifier for rate limiting
        self.user_id = "default_user"  # Could use actual user ID

    def run(self, raw: str) -> Tuple[str, IntentType]:
        """Process raw input through the sanitization pipeline.
        
        Args:
            raw: Raw user input string.
            
        Returns:
            A tuple containing:
                - Sanitized text string ready for LLM processing
                - Classified intent enum value
                
        Raises:
            InputPipelineError: If any stage of the pipeline fails.
        """
        try:
            # Stage 0: Rate limiting check
            rate_status = self.rate_limiter.check_rate_limit(
                self.user_id, action='default'
            )
            if not rate_status.allowed:
                self.gui_feedback(f"⏱️ {rate_status.message}")
                raise InputPipelineError(rate_status.message)
            
            # Stage 1: Enhanced security processing (if enabled)
            if self.enable_enhanced_security and self.enhanced_sanitizer:
                try:
                    # Apply comprehensive security sanitization
                    text = self.enhanced_sanitizer.sanitize_input(
                        raw,
                        context='general',
                        allow_unicode=True,
                        strict_mode=False
                    )
                    
                    # Check security summary for attacks
                    security_summary = self.enhanced_sanitizer.get_security_summary()
                    total_attacks = security_summary.get('total_attacks', 0)
                    if total_attacks > 0:
                        self.gui_feedback(
                            f"🛡️ Security: Blocked {total_attacks} attack(s)"
                        )
                except ValueError as e:
                    # Strict mode rejection
                    self.gui_feedback(f"🚨 Security: {str(e)}")
                    raise InputPipelineError(str(e))
            else:
                # Original validation path
                validation_result = self.validator.validate(raw)
                
                if not validation_result.is_valid:
                    # Create message from issues
                    issues = validation_result.issues
                    message = '; '.join(issues) if issues else "Invalid input"
                    
                    # Handle validation failures based on threat level
                    if validation_result.threat_level == ThreatLevel.HIGH:
                        self.gui_feedback(f"🚨 {message}")
                        raise InputPipelineError(message)
                    elif validation_result.threat_level == ThreatLevel.MEDIUM:
                        self.gui_feedback(f"⚠️ {message}")
                        # Continue with sanitized text
                    else:
                        self.gui_feedback(f"ℹ️ {message}")
                
                text = validation_result.cleaned_text
            
            # Handle empty input gracefully
            if not text:
                if not self.skip_empty_feedback:
                    self.gui_feedback("Empty input - please enter a message")
                return "", IntentType.UNCLEAR
            
            # Stage 2: Pattern normalization
            text, pattern_metadata = self.pattern_normalizer.normalize(text)
            if pattern_metadata.get('changed'):
                self.gui_feedback("✨ Input normalized")
            
            # Stage 3: LLM-specific escaping
            text = self.escaper.escape(text)
            
            # Stage 4: Profanity filtering
            filter_result = self.profanity_filter.filter(text)
            if filter_result.has_profanity:
                severity_emoji = {
                    Severity.MILD: "😅",
                    Severity.MODERATE: "⚠️",
                    Severity.SEVERE: "🚨",
                    Severity.HATE: "🛑"
                }
                if filter_result.max_severity:
                    emoji = severity_emoji.get(
                        filter_result.max_severity, "⚠️"
                    )
                    self.gui_feedback(
                        f"{emoji} Content filtered (severity: "
                        f"{filter_result.max_severity.name})"
                    )
                else:
                    self.gui_feedback("⚠️ Content filtered")
                text = filter_result.filtered_text
            
            # Stage 5: Intent classification
            intent_result = self.intent_classifier.classify(text)
            intent = intent_result.primary_intent
            
            # Stage 5b: Handle watchdog commands if detected
            if (intent == IntentType.COMMAND and
                    self.watchdog_handler.can_handle(text)):
                command_result = self.watchdog_handler.handle_command(text)
                if command_result.should_display_in_chat:
                    # Return the command result as processed text
                    return command_result.message, IntentType.COMMAND
            
            # Stage 6: Add to context history
            self.context.add_entry(text)
            
            # Final feedback
            confidence_emoji = "🎯" if intent_result.confidence > 0.8 else "🤔"
            self.gui_feedback(
                f"{confidence_emoji} Intent: {intent.value} "
                f"({intent_result.confidence:.0%} confident)"
            )
            
            return text, intent
            
        except InputPipelineError as e:
            self.gui_feedback(f"Input error: {e}")
            raise
        except Exception as e:
            error_msg = f"Unexpected error in input pipeline: {e}"
            self.gui_feedback(error_msg)
            raise InputPipelineError(error_msg) from e
    
    def get_conversation_context(self) -> str:
        """Get the current conversation context."""
        return self.context.get_context()
    
    def clear_context(self) -> None:
        """Clear the conversation context history."""
        self.context.history.clear()
        self.gui_feedback("🧹 Conversation context cleared")
    
    def update_model_type(self, model_type: str) -> None:
        """Update the LLM model type for escaping."""
        self.escaper.set_model(model_type)
        self.gui_feedback(f"🔧 Model type updated to: {model_type}")
    
    def record_watchdog_alert(self, level: str, message: str):
        """Record a watchdog alert for history tracking.
        
        Args:
            level: Alert level (info/warning/critical)
            message: Alert message
        """
        self.watchdog_alerts_history.append(
            (level, message, datetime.now())
        )
        # Keep only last 100 alerts
        if len(self.watchdog_alerts_history) > 100:
            self.watchdog_alerts_history.pop(0)
    
    # Convenience methods for rate limiting control
    def reset_rate_limit(self):
        """Reset rate limit for current user."""
        self.rate_limiter.reset_user(self.user_id)
        self.gui_feedback("🔄 Rate limit reset")
    
    def get_rate_limit_stats(self) -> dict:
        """Get rate limiting statistics."""
        return self.rate_limiter.get_stats()
    
    # Methods for updating component configurations
    def update_profanity_settings(self, min_severity: Severity = Severity.MILD,
                                  mask_style: str = "stars"):
        """Update profanity filter settings."""
        self.profanity_filter.set_mask_style(mask_style)
        self.gui_feedback("🔧 Profanity settings updated")
    
    def add_custom_profanity_word(self, word: str, severity: Severity):
        """Add a custom word to the profanity filter."""
        self.profanity_filter.add_custom_word(word, severity)
        self.gui_feedback(f"➕ Added '{word}' to profanity filter")
    
    def get_profanity_report(self) -> dict:
        """Get profanity filtering statistics."""
        return self.profanity_filter.get_report()
    
    def get_security_report(self) -> dict:
        """Get comprehensive security report."""
        if self.enhanced_sanitizer:
            return self.enhanced_sanitizer.get_security_summary()
        return {'enabled': False, 'message': 'Enhanced security disabled'}
    
    def reset_security_monitoring(self):
        """Reset security monitoring counters."""
        if self.enhanced_sanitizer:
            self.enhanced_sanitizer.reset_security_monitoring()
            self.gui_feedback("🔒 Security monitoring reset")


# Maintain backward compatibility by re-exporting IntentType as Intent
Intent = IntentType

# Maintain backward compatibility for InputSanitizer
InputSanitizer = InputPipeline


# Example: Integration with PySide6 GUI
# =====================================
"""
# In gui/chat_window.py:
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QWidget
from input_processing.input_sanitizer import InputPipeline, IntentType

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize pipeline with status bar feedback and model-specific
        # settings
        self.pipeline = InputPipeline(
            gui_feedback_hook=self.setStatusBarMessage,
            model_type="claude",  # or "gpt" for different escaping
            cooldown_seconds=2.0,  # Adjust rate limiting as needed
            watchdog_ref=self.watchdog,
            main_window_ref=self
        )
    
    @Slot(str)
    def on_user_enter(self, text: str) -> None:
        try:
            clean_prompt, intent = self.pipeline.run(text)
            
            # Handle different intents appropriately
            if intent == IntentType.COMMAND:
                # Command was already handled by pipeline
                pass
            else:
                # Send to LLM with context
                context = self.pipeline.get_conversation_context()
                self.llm_adapter.send(clean_prompt, intent, context)
                
        except Exception as e:
            # Errors already displayed in status bar by pipeline
            print(f"Pipeline error: {e}")
    
    def setStatusBarMessage(self, message: str) -> None:
        # Implementation to update status bar
        self.status_bar.showMessage(message)
    
    def clear_conversation(self):
        # Clear context when starting new conversation
        self.pipeline.clear_context()
    
    def get_pipeline_stats(self):
        # Get statistics from various components
        stats = {
            'rate_limit': self.pipeline.get_rate_limit_stats(),
            'profanity': self.pipeline.get_profanity_report()
        }
        return stats
"""


# Example: Unit Testing with New Modules
# ======================================
"""
import pytest
from input_processing.input_sanitizer import (
    InputPipeline, 
    InputPipelineError, 
    IntentType
)

def test_pipeline_validation():
    '''Test input validation functionality with new validator.'''
    feedback_messages = []
    pipeline = InputPipeline(lambda msg: feedback_messages.append(msg))
    
    # Test empty input
    result, intent = pipeline.run("")
    assert result == ""
    assert intent == IntentType.UNCLEAR
    
    # Test dangerous input (path traversal)
    with pytest.raises(InputPipelineError):
        pipeline.run("../../etc/passwd")
    
    # Test valid input
    result, intent = pipeline.run("Create a new note")
    assert isinstance(result, str)
    assert len(feedback_messages) > 0

def test_pipeline_escaping():
    '''Test model-specific escaping functionality.'''
    feedback_messages = []
    
    # Test Claude escaping
    pipeline = InputPipeline(
        lambda msg: feedback_messages.append(msg),
        model_type="claude"
    )
    result, _ = pipeline.run('Test <tag>content</tag>')
    assert '&lt;tag&gt;' in result
    
    # Test GPT escaping
    pipeline.update_model_type("gpt")
    result, _ = pipeline.run('```code block```')
    assert '\\`\\`\\`' in result

def test_intent_classification():
    '''Test improved intent classification.'''
    pipeline = InputPipeline(lambda msg: None)
    
    test_cases = [
        ("watchdog status", IntentType.COMMAND),
        ("what is the weather?", IntentType.QUERY),
        ("hello there!", IntentType.CONVERSATION),
        ("def hello(): print('hi')", IntentType.CODE),
        ("random gibberish", IntentType.UNCLEAR),
    ]
    
    for text, expected_intent in test_cases:
        _, intent = pipeline.run(text)
        assert intent == expected_intent

def test_profanity_filtering():
    '''Test profanity filtering with severity levels.'''
    feedback_messages = []
    pipeline = InputPipeline(lambda msg: feedback_messages.append(msg))
    
    # Add custom test word
    from input_processing.stages import Severity
    pipeline.add_custom_profanity_word("testbadword", Severity.MODERATE)
    
    result, _ = pipeline.run("This contains testbadword in it")
    assert "testbadword" not in result
    assert any("filtered" in msg for msg in feedback_messages)

def test_rate_limiting():
    '''Test rate limiting functionality.'''
    pipeline = InputPipeline(lambda msg: None)
    
    # Should allow first request
    result1, _ = pipeline.run("First request")
    assert isinstance(result1, str)
    
    # Rapid requests should eventually be rate limited
    # (depends on configuration)
    pipeline.reset_rate_limit()  # Ensure clean state
    
    stats = pipeline.get_rate_limit_stats()
    assert 'total_requests' in stats
"""
