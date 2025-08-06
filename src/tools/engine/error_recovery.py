"""
Error Recovery Module

This module provides strategies for recovering from tool execution errors,
ensuring resilient operation without dependency on AI models.
"""

import logging
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RecoveryStrategy(Enum):
    """Available recovery strategies"""
    RETRY = auto()           # Simple retry with backoff
    FALLBACK = auto()        # Use fallback value/tool
    CIRCUIT_BREAKER = auto()  # Circuit breaker pattern
    COMPENSATE = auto()      # Compensating action
    IGNORE = auto()          # Ignore and continue
    ABORT = auto()           # Abort execution


@dataclass
class RecoveryContext:
    """Context for error recovery"""
    error: Exception
    tool_name: str
    parameters: Dict[str, Any]
    attempt: int = 1
    max_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error": str(self.error),
            "error_type": type(self.error).__name__,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "metadata": self.metadata
        }


@dataclass
class RecoveryResult:
    """Result of a recovery attempt"""
    success: bool
    strategy: RecoveryStrategy
    result: Optional[Any] = None
    error: Optional[str] = None
    should_retry: bool = False
    retry_delay: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ErrorHandler(ABC):
    """
    Abstract base class for error handlers
    
    Error handlers implement specific recovery strategies for
    different types of errors.
    """
    
    @abstractmethod
    def can_handle(self, context: RecoveryContext) -> bool:
        """
        Check if this handler can handle the error
        
        Args:
            context: Recovery context
            
        Returns:
            True if handler can handle this error
        """
        pass
    
    @abstractmethod
    def handle(self, context: RecoveryContext) -> RecoveryResult:
        """
        Handle the error
        
        Args:
            context: Recovery context
            
        Returns:
            Recovery result
        """
        pass
    
    def get_strategy(self) -> RecoveryStrategy:
        """Get the recovery strategy this handler implements"""
        return RecoveryStrategy.RETRY


class RetryStrategy(ErrorHandler):
    """
    Retry strategy with exponential backoff
    
    This strategy retries failed operations with increasing delays
    between attempts.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry strategy
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries
            max_delay: Maximum delay between retries
            backoff_factor: Exponential backoff factor
            jitter: Whether to add jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Check if retry is appropriate"""
        # Don't retry if we've exceeded max attempts
        if context.attempt >= self.max_retries:
            return False
            
        # Check if error is retryable
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            IOError,
            OSError
        )
        
        return isinstance(context.error, retryable_errors)
        
    def handle(self, context: RecoveryContext) -> RecoveryResult:
        """Handle with retry strategy"""
        # Calculate delay
        delay = min(
            self.base_delay * (self.backoff_factor ** (context.attempt - 1)),
            self.max_delay
        )
        
        # Add jitter if enabled
        if self.jitter:
            import random
            delay *= (0.5 + random.random())
            
        return RecoveryResult(
            success=False,
            strategy=RecoveryStrategy.RETRY,
            should_retry=True,
            retry_delay=delay,
            metadata={
                "attempt": context.attempt,
                "max_attempts": self.max_retries,
                "delay": delay
            }
        )
        
    def get_strategy(self) -> RecoveryStrategy:
        return RecoveryStrategy.RETRY


class FallbackStrategy(ErrorHandler):
    """
    Fallback strategy using alternative values or tools
    
    This strategy provides fallback options when the primary
    operation fails.
    """
    
    def __init__(
        self,
        fallback_value: Optional[Any] = None,
        fallback_tool: Optional[str] = None,
        fallback_params: Optional[Dict[str, Any]] = None,
        fallback_factory: Optional[Callable[[RecoveryContext], Any]] = None
    ):
        """
        Initialize fallback strategy
        
        Args:
            fallback_value: Static fallback value
            fallback_tool: Alternative tool to use
            fallback_params: Parameters for fallback tool
            fallback_factory: Function to generate fallback value
        """
        self.fallback_value = fallback_value
        self.fallback_tool = fallback_tool
        self.fallback_params = fallback_params or {}
        self.fallback_factory = fallback_factory
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Fallback can handle any error"""
        return True
        
    def handle(self, context: RecoveryContext) -> RecoveryResult:
        """Handle with fallback strategy"""
        # Use factory if provided
        if self.fallback_factory:
            try:
                value = self.fallback_factory(context)
                return RecoveryResult(
                    success=True,
                    strategy=RecoveryStrategy.FALLBACK,
                    result=value,
                    metadata={"source": "factory"}
                )
            except Exception as e:
                logger.error(f"Fallback factory failed: {e}")
                
        # Use fallback tool if specified
        if self.fallback_tool:
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.FALLBACK,
                metadata={
                    "fallback_tool": self.fallback_tool,
                    "fallback_params": self.fallback_params
                }
            )
            
        # Use static fallback value
        return RecoveryResult(
            success=True,
            strategy=RecoveryStrategy.FALLBACK,
            result=self.fallback_value,
            metadata={"source": "static"}
        )
        
    def get_strategy(self) -> RecoveryStrategy:
        return RecoveryStrategy.FALLBACK


class CircuitBreakerStrategy(ErrorHandler):
    """
    Circuit breaker pattern for preventing cascading failures
    
    This strategy temporarily stops attempting operations that are
    likely to fail, allowing the system to recover.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_attempts: int = 3
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Time before attempting recovery
            half_open_attempts: Attempts in half-open state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_attempts = half_open_attempts
        
        # Circuit state
        self._state = "closed"  # closed, open, half-open
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_count = 0
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Check circuit state"""
        # Update state based on time
        self._update_state()
        
        # Can handle if circuit is not open
        return self._state != "open"
        
    def handle(self, context: RecoveryContext) -> RecoveryResult:
        """Handle with circuit breaker"""
        # Record failure
        self._record_failure()
        
        if self._state == "open":
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                error="Circuit breaker is open",
                metadata={
                    "state": self._state,
                    "will_retry_at": (
                        self._last_failure_time + self.recovery_timeout
                        if self._last_failure_time else None
                    )
                }
            )
            
        elif self._state == "half-open":
            # Allow limited attempts
            if self._half_open_count < self.half_open_attempts:
                self._half_open_count += 1
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                    should_retry=True,
                    metadata={
                        "state": self._state,
                        "attempt": self._half_open_count,
                        "max_attempts": self.half_open_attempts
                    }
                )
            else:
                # Too many failures in half-open, reopen circuit
                self._state = "open"
                self._last_failure_time = time.time()
                return RecoveryResult(
                    success=False,
                    strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                    error="Circuit breaker reopened after half-open failures",
                    metadata={"state": self._state}
                )
                
        else:  # closed
            return RecoveryResult(
                success=False,
                strategy=RecoveryStrategy.CIRCUIT_BREAKER,
                should_retry=True,
                metadata={
                    "state": self._state,
                    "failure_count": self._failure_count
                }
            )
            
    def _update_state(self):
        """Update circuit state based on time"""
        if self._state == "open" and self._last_failure_time:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = "half-open"
                self._half_open_count = 0
                logger.info("Circuit breaker moved to half-open state")
                
    def _record_failure(self):
        """Record a failure"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == "closed" and (
            self._failure_count >= self.failure_threshold
        ):
            self._state = "open"
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )
            
    def record_success(self):
        """Record a successful operation"""
        if self._state == "half-open":
            self._state = "closed"
            self._failure_count = 0
            logger.info("Circuit breaker closed after successful recovery")
        elif self._state == "closed":
            self._failure_count = max(0, self._failure_count - 1)
            
    def get_strategy(self) -> RecoveryStrategy:
        return RecoveryStrategy.CIRCUIT_BREAKER


class ErrorRecovery:
    """
    Main error recovery coordinator
    
    This class coordinates multiple error recovery strategies to
    provide comprehensive error handling.
    """
    
    def __init__(self, handlers: Optional[List[ErrorHandler]] = None):
        """
        Initialize error recovery
        
        Args:
            handlers: List of error handlers
        """
        self.handlers = handlers or [
            RetryStrategy(),
            FallbackStrategy(),
            CircuitBreakerStrategy()
        ]
        self._recovery_history: List[Dict[str, Any]] = []
        
    def add_handler(self, handler: ErrorHandler):
        """Add an error handler"""
        self.handlers.append(handler)
        
    def remove_handler(self, handler_type: type):
        """Remove handlers of a specific type"""
        self.handlers = [
            h for h in self.handlers
            if not isinstance(h, handler_type)
        ]
        
    def recover(
        self,
        error: Exception,
        tool_name: str,
        parameters: Dict[str, Any],
        attempt: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """
        Attempt to recover from an error
        
        Args:
            error: The error that occurred
            tool_name: Name of the tool that failed
            parameters: Parameters used
            attempt: Current attempt number
            metadata: Additional metadata
            
        Returns:
            Recovery result
        """
        context = RecoveryContext(
            error=error,
            tool_name=tool_name,
            parameters=parameters,
            attempt=attempt,
            metadata=metadata or {}
        )
        
        # Try each handler
        for handler in self.handlers:
            if handler.can_handle(context):
                try:
                    result = handler.handle(context)
                    
                    # Record recovery attempt
                    self._record_recovery(context, result)
                    
                    return result
                    
                except Exception as e:
                    logger.error(
                        f"Handler {handler.__class__.__name__} failed: {e}"
                    )
                    continue
                    
        # No handler could recover
        return RecoveryResult(
            success=False,
            strategy=RecoveryStrategy.ABORT,
            error="No recovery strategy available",
            metadata={"handlers_tried": len(self.handlers)}
        )
        
    async def recover_async(
        self,
        error: Exception,
        tool_name: str,
        parameters: Dict[str, Any],
        attempt: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RecoveryResult:
        """Async version of recover"""
        # Run recovery in thread pool to avoid blocking
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        return await loop.run_in_executor(
            None,
            self.recover,
            error,
            tool_name,
            parameters,
            attempt,
            metadata
        )
        
    def _record_recovery(
        self,
        context: RecoveryContext,
        result: RecoveryResult
    ):
        """Record recovery attempt in history"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "context": context.to_dict(),
            "result": {
                "success": result.success,
                "strategy": result.strategy.name,
                "error": result.error,
                "should_retry": result.should_retry,
                "retry_delay": result.retry_delay
            }
        }
        
        self._recovery_history.append(record)
        
        # Limit history size
        if len(self._recovery_history) > 1000:
            self._recovery_history = self._recovery_history[-500:]
            
    def get_history(
        self,
        tool_name: Optional[str] = None,
        strategy: Optional[RecoveryStrategy] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recovery history"""
        history = self._recovery_history.copy()
        
        # Filter by tool name
        if tool_name:
            history = [
                r for r in history
                if r["context"]["tool_name"] == tool_name
            ]
            
        # Filter by strategy
        if strategy:
            history = [
                r for r in history
                if r["result"]["strategy"] == strategy.name
            ]
            
        return history[-limit:]
        
    def clear_history(self):
        """Clear recovery history"""
        self._recovery_history.clear()
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        if not self._recovery_history:
            return {
                "total_recoveries": 0,
                "successful_recoveries": 0,
                "success_rate": 0.0,
                "strategies_used": {},
                "error_types": {}
            }
            
        total = len(self._recovery_history)
        successful = sum(
            1 for r in self._recovery_history
            if r["result"]["success"]
        )
        
        # Count strategies
        strategies = {}
        for record in self._recovery_history:
            strategy = record["result"]["strategy"]
            strategies[strategy] = strategies.get(strategy, 0) + 1
            
        # Count error types
        error_types = {}
        for record in self._recovery_history:
            error_type = record["context"]["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
        return {
            "total_recoveries": total,
            "successful_recoveries": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "strategies_used": strategies,
            "error_types": error_types
        }


# Convenience functions

def create_default_recovery() -> ErrorRecovery:
    """Create error recovery with default handlers"""
    return ErrorRecovery([
        RetryStrategy(max_retries=3, base_delay=1.0),
        FallbackStrategy(fallback_value=None),
        CircuitBreakerStrategy(failure_threshold=5)
    ])


def create_custom_recovery(
    max_retries: int = 3,
    fallback_value: Any = None,
    circuit_breaker: bool = True
) -> ErrorRecovery:
    """Create error recovery with custom configuration"""
    handlers = []
    
    if max_retries > 0:
        handlers.append(RetryStrategy(max_retries=max_retries))
        
    if fallback_value is not None:
        handlers.append(FallbackStrategy(fallback_value=fallback_value))
        
    if circuit_breaker:
        handlers.append(CircuitBreakerStrategy())
        
    return ErrorRecovery(handlers)