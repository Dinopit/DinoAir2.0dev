"""Rate limiting module for preventing abuse and spam.

Provides configurable rate limiting with different strategies
and time windows to prevent abuse while maintaining good UX.
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import time
from enum import Enum


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"      # Traditional fixed time windows
    SLIDING_WINDOW = "sliding_window"   # More accurate sliding window
    TOKEN_BUCKET = "token_bucket"       # Allows bursts with overall limit


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 60              # Max requests per window
    window_seconds: int = 60            # Time window in seconds
    burst_size: int = 10                # Max burst for token bucket
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    # Penalties and cooldowns
    penalty_threshold: int = 3          # Violations before penalty
    penalty_duration: int = 300         # Penalty duration in seconds
    
    # Different limits for different actions
    action_limits: Dict[str, int] = field(default_factory=lambda: {
        'default': 60,
        'command': 30,
        'query': 100,
        'code': 20,
        'file_operation': 10
    })


@dataclass
class RateLimitStatus:
    """Status of rate limiting for a user/key."""
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    violations: int = 0
    penalty_until: Optional[datetime] = None
    message: str = ""


class RateLimiter:
    """Advanced rate limiter with multiple strategies.
    
    This class provides flexible rate limiting with support for
    different strategies, user-specific limits, and penalties.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize with configuration.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        
        # Storage for different strategies
        self.fixed_windows: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.sliding_windows: Dict[str, deque] = defaultdict(deque)
        self.token_buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {
                'tokens': float(self.config.burst_size),
                'last_update': time.time()
            }
        )
        
        # Violation tracking
        self.violations: Dict[str, List[datetime]] = defaultdict(list)
        self.penalties: Dict[str, datetime] = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'unique_users': set(),
            'violations_issued': 0
        }
    
    def check_rate_limit(self, key: str, action: str = 'default') -> RateLimitStatus:
        """Check if a request is allowed under rate limits.
        
        Args:
            key: Unique identifier (user_id, IP, etc.)
            action: Type of action being performed
            
        Returns:
            RateLimitStatus with result and details
        """
        self.stats['total_requests'] += 1
        self.stats['unique_users'].add(key)
        
        # Check if user is in penalty
        if key in self.penalties:
            if datetime.now() < self.penalties[key]:
                self.stats['blocked_requests'] += 1
                return RateLimitStatus(
                    allowed=False,
                    remaining_requests=0,
                    reset_time=self.penalties[key],
                    violations=len(self.violations[key]),
                    penalty_until=self.penalties[key],
                    message=f"Rate limit penalty until {self.penalties[key].strftime('%H:%M:%S')}"
                )
            else:
                # Penalty expired
                del self.penalties[key]
                self.violations[key].clear()
        
        # Get action-specific limit
        limit = self.config.action_limits.get(action, self.config.max_requests)
        
        # Check rate limit based on strategy
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            status = self._check_fixed_window(key, limit)
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            status = self._check_sliding_window(key, limit)
        else:  # TOKEN_BUCKET
            status = self._check_token_bucket(key, limit)
        
        # Handle violations
        if not status.allowed:
            self._record_violation(key)
            status.violations = len(self.violations[key])
            
            # Check if penalty should be applied
            if status.violations >= self.config.penalty_threshold:
                penalty_until = datetime.now() + timedelta(seconds=self.config.penalty_duration)
                self.penalties[key] = penalty_until
                status.penalty_until = penalty_until
                status.message = f"Too many violations. Penalty applied until {penalty_until.strftime('%H:%M:%S')}"
                self.stats['violations_issued'] += 1
        
        if not status.allowed:
            self.stats['blocked_requests'] += 1
            
        return status
    
    def _check_fixed_window(self, key: str, limit: int) -> RateLimitStatus:
        """Check rate limit using fixed window strategy.
        
        Args:
            key: User identifier
            limit: Request limit
            
        Returns:
            RateLimitStatus
        """
        current_window = int(time.time() / self.config.window_seconds)
        window_key = f"{current_window}"
        
        # Clean old windows
        windows_to_remove = []
        for window in self.fixed_windows[key]:
            if int(window) < current_window - 1:
                windows_to_remove.append(window)
        for window in windows_to_remove:
            del self.fixed_windows[key][window]
        
        # Check current window
        current_count = self.fixed_windows[key][window_key]
        
        if current_count >= limit:
            reset_time = datetime.fromtimestamp(
                (current_window + 1) * self.config.window_seconds
            )
            return RateLimitStatus(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                message=f"Rate limit exceeded. Reset at {reset_time.strftime('%H:%M:%S')}"
            )
        
        # Increment counter
        self.fixed_windows[key][window_key] += 1
        
        reset_time = datetime.fromtimestamp(
            (current_window + 1) * self.config.window_seconds
        )
        
        return RateLimitStatus(
            allowed=True,
            remaining_requests=limit - current_count - 1,
            reset_time=reset_time
        )
    
    def _check_sliding_window(self, key: str, limit: int) -> RateLimitStatus:
        """Check rate limit using sliding window strategy.
        
        Args:
            key: User identifier
            limit: Request limit
            
        Returns:
            RateLimitStatus
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.config.window_seconds)
        
        # Remove old entries
        window = self.sliding_windows[key]
        while window and window[0] < window_start:
            window.popleft()
        
        # Check limit
        if len(window) >= limit:
            oldest_request = window[0]
            reset_time = oldest_request + timedelta(seconds=self.config.window_seconds)
            return RateLimitStatus(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                message=f"Rate limit exceeded. Next request available at {reset_time.strftime('%H:%M:%S')}"
            )
        
        # Add current request
        window.append(now)
        
        # Calculate reset time (when oldest request expires)
        if window:
            reset_time = window[0] + timedelta(seconds=self.config.window_seconds)
        else:
            reset_time = now + timedelta(seconds=self.config.window_seconds)
        
        return RateLimitStatus(
            allowed=True,
            remaining_requests=limit - len(window),
            reset_time=reset_time
        )
    
    def _check_token_bucket(self, key: str, limit: int) -> RateLimitStatus:
        """Check rate limit using token bucket strategy.
        
        Args:
            key: User identifier
            limit: Request limit (used as refill rate)
            
        Returns:
            RateLimitStatus
        """
        bucket = self.token_buckets[key]
        now = time.time()
        
        # Refill tokens based on time passed
        time_passed = now - bucket['last_update']
        refill_rate = limit / self.config.window_seconds
        new_tokens = time_passed * refill_rate
        
        bucket['tokens'] = min(
            bucket['tokens'] + new_tokens,
            self.config.burst_size
        )
        bucket['last_update'] = now
        
        # Check if token available
        if bucket['tokens'] < 1:
            # Calculate when next token will be available
            tokens_needed = 1 - bucket['tokens']
            seconds_until_token = tokens_needed / refill_rate
            reset_time = datetime.now() + timedelta(seconds=seconds_until_token)
            
            return RateLimitStatus(
                allowed=False,
                remaining_requests=0,
                reset_time=reset_time,
                message=f"No tokens available. Next token at {reset_time.strftime('%H:%M:%S')}"
            )
        
        # Consume token
        bucket['tokens'] -= 1
        
        # Calculate reset time (when bucket will be full)
        tokens_to_full = self.config.burst_size - bucket['tokens']
        seconds_to_full = tokens_to_full / refill_rate
        reset_time = datetime.now() + timedelta(seconds=seconds_to_full)
        
        return RateLimitStatus(
            allowed=True,
            remaining_requests=int(bucket['tokens']),
            reset_time=reset_time
        )
    
    def _record_violation(self, key: str):
        """Record a rate limit violation.
        
        Args:
            key: User identifier
        """
        now = datetime.now()
        violations = self.violations[key]
        
        # Clean old violations (older than penalty duration)
        cutoff = now - timedelta(seconds=self.config.penalty_duration)
        self.violations[key] = [v for v in violations if v > cutoff]
        
        # Add new violation
        self.violations[key].append(now)
    
    def reset_user(self, key: str):
        """Reset rate limits for a specific user.
        
        Args:
            key: User identifier
        """
        # Clear all tracking for this user
        if key in self.fixed_windows:
            del self.fixed_windows[key]
        if key in self.sliding_windows:
            del self.sliding_windows[key]
        if key in self.token_buckets:
            del self.token_buckets[key]
        if key in self.violations:
            del self.violations[key]
        if key in self.penalties:
            del self.penalties[key]
    
    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics.
        
        Returns:
            Dictionary of statistics
        """
        return {
            'total_requests': self.stats['total_requests'],
            'blocked_requests': self.stats['blocked_requests'],
            'block_rate': (
                self.stats['blocked_requests'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            ),
            'unique_users': len(self.stats['unique_users']),
            'violations_issued': self.stats['violations_issued'],
            'active_penalties': len(self.penalties),
            'strategy': self.config.strategy.value
        }
    
    def set_user_limit(self, key: str, limit: int):
        """Set a custom limit for a specific user.
        
        Args:
            key: User identifier
            limit: Custom limit
        """
        # This would need additional storage for user-specific limits
        # For now, just reset their state
        self.reset_user(key)
    
    def is_rate_limited(self, key: str, action: str = 'default') -> bool:
        """Quick check if user is rate limited.
        
        Args:
            key: User identifier
            action: Action type
            
        Returns:
            True if rate limited
        """
        status = self.check_rate_limit(key, action)
        return not status.allowed


# Global rate limiter instance
_global_limiter = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create global rate limiter instance.
    
    Args:
        config: Optional configuration
        
    Returns:
        RateLimiter instance
    """
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter(config)
    return _global_limiter


# Convenience functions
def check_rate_limit(key: str, action: str = 'default') -> bool:
    """Check if request is allowed.
    
    Args:
        key: User identifier
        action: Action type
        
    Returns:
        True if allowed
    """
    limiter = get_rate_limiter()
    return not limiter.is_rate_limited(key, action)


def reset_rate_limit(key: str):
    """Reset rate limit for a user.
    
    Args:
        key: User identifier
    """
    limiter = get_rate_limiter()
    limiter.reset_user(key)