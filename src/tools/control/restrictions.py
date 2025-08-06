"""
Tool Usage Restrictions

This module provides various restriction mechanisms for controlling
tool usage including rate limiting, resource constraints, and permissions.
"""

import logging
import time
import threading
from typing import Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import psutil
import os
from math import isfinite

from ..base import BaseTool
from .tool_context import ExecutionContext, UserRole


logger = logging.getLogger(__name__)


class RestrictionType(Enum):
    """Types of restrictions"""
    RATE_LIMIT = "rate_limit"
    RESOURCE_LIMIT = "resource_limit"
    PERMISSION = "permission"
    TIME_WINDOW = "time_window"
    USAGE_QUOTA = "usage_quota"


@dataclass
class RestrictionResult:
    """Result of a restriction check"""
    allowed: bool
    restriction_type: RestrictionType
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_after: Optional[float] = None  # Seconds until retry allowed


class RateLimiter:
    """
    Rate limiter for tool usage frequency
    
    Implements token bucket algorithm for smooth rate limiting.
    """
    
    def __init__(
        self,
        rate: float,  # Requests per second
        burst: int,   # Maximum burst size
        per_user: bool = True
    ):
        """
        Initialize rate limiter
        
        Args:
            rate: Allowed requests per second
            burst: Maximum burst size
            per_user: Whether to track per user or globally
        """
        # Validate parameters
        if rate <= 0:
            logger.warning(f"Invalid rate {rate}, using default of 10.0")
            rate = 10.0
        if burst <= 0:
            logger.warning(f"Invalid burst {burst}, using default of 20")
            burst = 20
            
        self.rate = rate
        self.burst = burst
        self.per_user = per_user
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()
        
    def check_limit(
        self,
        tool_name: str,
        context: Optional[ExecutionContext] = None
    ) -> RestrictionResult:
        """Check if request is within rate limit"""
        # Determine bucket key
        if self.per_user and context and context.user:
            key = f"{context.user.user_id}:{tool_name}"
        else:
            key = tool_name
            
        with self._lock:
            current_time = time.time()
            
            if key in self._buckets:
                tokens, last_update = self._buckets[key]
                
                # Calculate tokens accumulated since last update
                elapsed = current_time - last_update
                tokens = min(self.burst, tokens + elapsed * self.rate)
            else:
                # New bucket starts full
                tokens = self.burst
                
            if tokens >= 1:
                # Consume a token
                self._buckets[key] = (tokens - 1, current_time)
                return RestrictionResult(
                    allowed=True,
                    restriction_type=RestrictionType.RATE_LIMIT,
                    reason="Within rate limit",
                    metadata={
                        "tokens_remaining": tokens - 1,
                        "rate": self.rate,
                        "burst": self.burst
                    }
                )
            else:
                # Calculate retry time
                if self.rate > 0:
                    retry_after = (1 - tokens) / self.rate
                else:
                    retry_after = 60.0  # Default to 60 seconds if rate is 0
                    
                return RestrictionResult(
                    allowed=False,
                    restriction_type=RestrictionType.RATE_LIMIT,
                    reason=f"Rate limit exceeded ({self.rate} req/s)",
                    metadata={
                        "rate": self.rate,
                        "burst": self.burst
                    },
                    retry_after=retry_after
                )
                
    def reset(self, tool_name: str, user_id: Optional[str] = None):
        """Reset rate limit for a tool/user"""
        if self.per_user and user_id:
            key = f"{user_id}:{tool_name}"
        else:
            key = tool_name
            
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


class ResourceLimiter:
    """
    Resource limiter for memory/CPU constraints
    
    Prevents tools from being used when system resources are constrained.
    """
    
    def __init__(
        self,
        max_memory_percent: float = 80.0,
        max_cpu_percent: float = 90.0,
        check_interval: float = 1.0
    ):
        """
        Initialize resource limiter
        
        Args:
            max_memory_percent: Maximum memory usage percentage
            max_cpu_percent: Maximum CPU usage percentage
            check_interval: How often to check resources (seconds)
        """
        self.max_memory_percent = max_memory_percent
        self.max_cpu_percent = max_cpu_percent
        self.check_interval = check_interval
        self._last_check = 0
        self._last_result = None
        self._lock = threading.Lock()
        
    def check_resources(
        self,
        tool_name: str,
        context: Optional[ExecutionContext] = None
    ) -> RestrictionResult:
        """Check if resources are available"""
        with self._lock:
            current_time = time.time()
            
            # Use cached result if recent
            if (self._last_result and 
                current_time - self._last_check < self.check_interval):
                return self._last_result
                
            # Check current resources
            try:
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                if memory_percent > self.max_memory_percent:
                    result = RestrictionResult(
                        allowed=False,
                        restriction_type=RestrictionType.RESOURCE_LIMIT,
                        reason=(
                            f"Memory usage too high: "
                            f"{memory_percent:.1f}% > {self.max_memory_percent}%"
                        ),
                        metadata={
                            "memory_percent": memory_percent,
                            "max_memory_percent": self.max_memory_percent
                        },
                        retry_after=5.0  # Check again in 5 seconds
                    )
                elif cpu_percent > self.max_cpu_percent:
                    result = RestrictionResult(
                        allowed=False,
                        restriction_type=RestrictionType.RESOURCE_LIMIT,
                        reason=(
                            f"CPU usage too high: "
                            f"{cpu_percent:.1f}% > {self.max_cpu_percent}%"
                        ),
                        metadata={
                            "cpu_percent": cpu_percent,
                            "max_cpu_percent": self.max_cpu_percent
                        },
                        retry_after=5.0
                    )
                else:
                    result = RestrictionResult(
                        allowed=True,
                        restriction_type=RestrictionType.RESOURCE_LIMIT,
                        reason="Resources available",
                        metadata={
                            "memory_percent": memory_percent,
                            "cpu_percent": cpu_percent
                        }
                    )
                    
                self._last_check = current_time
                self._last_result = result
                return result
                
            except Exception as e:
                logger.error(f"Error checking resources: {e}")
                # Allow on error but log it
                return RestrictionResult(
                    allowed=True,
                    restriction_type=RestrictionType.RESOURCE_LIMIT,
                    reason="Resource check failed, allowing",
                    metadata={"error": str(e)}
                )


class PermissionChecker:
    """
    Permission checker for user-based restrictions
    
    Controls tool access based on user roles and permissions.
    """
    
    def __init__(self):
        """Initialize permission checker"""
        # Default role permissions
        self._role_permissions: Dict[UserRole, Set[str]] = {
            UserRole.ADMIN: {
                "use_all_tools",
                "use_system_tools",
                "use_debug_tools",
                "modify_files",
                "execute_commands",
                "network_access"
            },
            UserRole.DEVELOPER: {
                "use_most_tools",
                "use_debug_tools",
                "modify_files",
                "execute_commands",
                "network_access"
            },
            UserRole.USER: {
                "use_basic_tools",
                "read_files",
                "limited_network"
            },
            UserRole.GUEST: {
                "use_safe_tools",
                "read_only"
            }
        }
        
        # Tool-specific permissions
        self._tool_permissions: Dict[str, Set[str]] = {}
        
    def check_permission(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext] = None
    ) -> RestrictionResult:
        """Check if user has permission to use tool"""
        if not context or not context.user:
            # No user context, check if tool is public
            if self._is_public_tool(tool):
                return RestrictionResult(
                    allowed=True,
                    restriction_type=RestrictionType.PERMISSION,
                    reason="Public tool allowed",
                    metadata={"public": True}
                )
            else:
                return RestrictionResult(
                    allowed=False,
                    restriction_type=RestrictionType.PERMISSION,
                    reason="Authentication required",
                    metadata={"public": False}
                )
                
        user = context.user
        
        # Check role-based permissions
        role_perms = self._role_permissions.get(user.role, set())
        
        # Admin can use everything
        if "use_all_tools" in role_perms:
            return RestrictionResult(
                allowed=True,
                restriction_type=RestrictionType.PERMISSION,
                reason="Admin access granted",
                metadata={"role": user.role.value}
            )
            
        # Check specific tool permissions
        tool_perms = self._tool_permissions.get(tool.name, set())
        required_perms = self._get_required_permissions(tool)
        
        # Combine user permissions
        user_perms = role_perms | user.permissions
        
        # Check if user has all required permissions
        missing_perms = required_perms - user_perms
        
        if not missing_perms:
            return RestrictionResult(
                allowed=True,
                restriction_type=RestrictionType.PERMISSION,
                reason="All permissions granted",
                metadata={
                    "role": user.role.value,
                    "permissions": list(user_perms)
                }
            )
        else:
            return RestrictionResult(
                allowed=False,
                restriction_type=RestrictionType.PERMISSION,
                reason=f"Missing permissions: {', '.join(missing_perms)}",
                metadata={
                    "role": user.role.value,
                    "missing": list(missing_perms),
                    "required": list(required_perms)
                }
            )
            
    def _is_public_tool(self, tool: BaseTool) -> bool:
        """Check if tool is public"""
        if not tool.metadata:
            return False
            
        # Check capabilities
        caps = tool.metadata.capabilities
        return (
            caps.get("public", False) or
            caps.get("safe", False) or
            caps.get("read_only", False)
        )
        
    def _get_required_permissions(self, tool: BaseTool) -> Set[str]:
        """Get required permissions for a tool"""
        perms = set()
        
        if not tool.metadata:
            return {"use_basic_tools"}
            
        # Check tool category
        category = tool.metadata.category.value
        if category == "system":
            perms.add("use_system_tools")
        elif category == "debug":
            perms.add("use_debug_tools")
        else:
            perms.add("use_basic_tools")
            
        # Check capabilities
        caps = tool.metadata.capabilities
        if caps.get("file_write", False):
            perms.add("modify_files")
        elif caps.get("file_read", False):
            perms.add("read_files")
            
        if caps.get("execute", False):
            perms.add("execute_commands")
            
        if caps.get("network", False):
            perms.add("network_access")
            
        # Check specific tool permissions
        if tool.name in self._tool_permissions:
            perms.update(self._tool_permissions[tool.name])
            
        return perms
        
    def add_tool_permission(self, tool_name: str, permission: str):
        """Add a required permission for a tool"""
        if tool_name not in self._tool_permissions:
            self._tool_permissions[tool_name] = set()
        self._tool_permissions[tool_name].add(permission)
        
    def add_role_permission(self, role: UserRole, permission: str):
        """Add a permission to a role"""
        if role in self._role_permissions:
            self._role_permissions[role].add(permission)


class TimeWindowRestriction:
    """
    Time window restrictions for time-based access control
    
    Allows tools to be used only during specific time windows.
    """
    
    def __init__(self):
        """Initialize time window restrictions"""
        # Tool-specific time windows
        self._tool_windows: Dict[str, List[Tuple[int, int]]] = {}
        # Category-specific time windows
        self._category_windows: Dict[str, List[Tuple[int, int]]] = {}
        # Blackout periods (no tools allowed)
        self._blackout_periods: List[Tuple[datetime, datetime]] = []
        
    def check_time_window(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext] = None
    ) -> RestrictionResult:
        """Check if current time is within allowed window"""
        current_time = datetime.now()
        
        # Check blackout periods first
        for start, end in self._blackout_periods:
            if start <= current_time <= end:
                return RestrictionResult(
                    allowed=False,
                    restriction_type=RestrictionType.TIME_WINDOW,
                    reason="Tool usage blocked during blackout period",
                    metadata={
                        "blackout_start": start.isoformat(),
                        "blackout_end": end.isoformat()
                    },
                    retry_after=(end - current_time).total_seconds()
                )
                
        # Check tool-specific windows
        if tool.name in self._tool_windows:
            windows = self._tool_windows[tool.name]
            current_hour = current_time.hour
            
            allowed = any(
                start <= current_hour < end
                for start, end in windows
            )
            
            if not allowed:
                # Find next available window
                next_window = self._find_next_window(current_hour, windows)
                retry_after = self._calculate_retry_after(
                    current_time, next_window
                )
                
                return RestrictionResult(
                    allowed=False,
                    restriction_type=RestrictionType.TIME_WINDOW,
                    reason=(
                        f"Tool '{tool.name}' not available at this time"
                    ),
                    metadata={
                        "current_hour": current_hour,
                        "allowed_windows": windows
                    },
                    retry_after=retry_after
                )
                
        # Check category-specific windows
        if tool.metadata:
            category = tool.metadata.category.value
            if category in self._category_windows:
                windows = self._category_windows[category]
                current_hour = current_time.hour
                
                allowed = any(
                    start <= current_hour < end
                    for start, end in windows
                )
                
                if not allowed:
                    next_window = self._find_next_window(current_hour, windows)
                    retry_after = self._calculate_retry_after(
                        current_time, next_window
                    )
                    
                    return RestrictionResult(
                        allowed=False,
                        restriction_type=RestrictionType.TIME_WINDOW,
                        reason=(
                            f"Category '{category}' not available at this time"
                        ),
                        metadata={
                            "current_hour": current_hour,
                            "allowed_windows": windows
                        },
                        retry_after=retry_after
                    )
                    
        # No restrictions apply
        return RestrictionResult(
            allowed=True,
            restriction_type=RestrictionType.TIME_WINDOW,
            reason="Within allowed time window",
            metadata={"current_time": current_time.isoformat()}
        )
        
    def _find_next_window(
        self,
        current_hour: int,
        windows: List[Tuple[int, int]]
    ) -> Optional[int]:
        """Find the next available window start hour"""
        # Sort windows by start time
        sorted_windows = sorted(windows, key=lambda w: w[0])
        
        # Find next window after current hour
        for start, _ in sorted_windows:
            if start > current_hour:
                return start
                
        # If no window found today, return first window tomorrow
        if sorted_windows:
            return sorted_windows[0][0]
        return None
        
    def _calculate_retry_after(
        self,
        current_time: datetime,
        next_hour: Optional[int]
    ) -> float:
        """Calculate seconds until next available window"""
        if next_hour is None:
            return 3600.0  # Default to 1 hour
            
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_second = current_time.second
        
        if next_hour > current_hour:
            # Same day
            hours_diff = next_hour - current_hour
        else:
            # Next day
            hours_diff = (24 - current_hour) + next_hour
            
        seconds_diff = (hours_diff * 3600) - (current_minute * 60) - current_second
        return max(0.0, seconds_diff)
        
    def add_tool_window(self, tool_name: str, start_hour: int, end_hour: int):
        """Add an allowed time window for a tool"""
        if tool_name not in self._tool_windows:
            self._tool_windows[tool_name] = []
        self._tool_windows[tool_name].append((start_hour, end_hour))
        
    def add_category_window(
        self,
        category: str,
        start_hour: int,
        end_hour: int
    ):
        """Add an allowed time window for a category"""
        if category not in self._category_windows:
            self._category_windows[category] = []
        self._category_windows[category].append((start_hour, end_hour))
        
    def add_blackout_period(self, start: datetime, end: datetime):
        """Add a blackout period"""
        self._blackout_periods.append((start, end))


class UsageQuotaManager:
    """
    Usage quota manager for limiting total tool usage
    
    Tracks and enforces quotas on tool usage counts.
    """
    
    def __init__(self):
        """Initialize quota manager"""
        # User quotas
        self._user_quotas: Dict[str, Dict[str, int]] = {}
        # Tool quotas
        self._tool_quotas: Dict[str, int] = {}
        # Usage tracking
        self._usage_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # Reset periods
        self._reset_periods: Dict[str, timedelta] = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30)
        }
        self._last_reset: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        
    def check_quota(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext] = None
    ) -> RestrictionResult:
        """Check if usage is within quota"""
        with self._lock:
            # Check for quota reset
            self._check_reset_quotas()
            
            # Check tool quota
            if tool.name in self._tool_quotas:
                tool_usage = sum(
                    counts.get(tool.name, 0)
                    for counts in self._usage_counts.values()
                )
                if tool_usage >= self._tool_quotas[tool.name]:
                    return RestrictionResult(
                        allowed=False,
                        restriction_type=RestrictionType.USAGE_QUOTA,
                        reason=f"Tool quota exceeded ({self._tool_quotas[tool.name]})",
                        metadata={
                            "tool": tool.name,
                            "usage": tool_usage,
                            "quota": self._tool_quotas[tool.name]
                        }
                    )
                    
            # Check user quota
            if context and context.user:
                user_id = context.user.user_id
                if user_id in self._user_quotas:
                    user_quota = self._user_quotas[user_id].get(
                        tool.name,
                        self._user_quotas[user_id].get("default", float('inf'))
                    )
                    user_usage = self._usage_counts[user_id].get(tool.name, 0)
                    
                    if user_usage >= user_quota:
                        return RestrictionResult(
                            allowed=False,
                            restriction_type=RestrictionType.USAGE_QUOTA,
                            reason=f"User quota exceeded ({user_quota})",
                            metadata={
                                "user": user_id,
                                "tool": tool.name,
                                "usage": user_usage,
                                "quota": user_quota
                            }
                        )
                        
            # Track usage
            if context and context.user:
                self._usage_counts[context.user.user_id][tool.name] += 1
            else:
                self._usage_counts["anonymous"][tool.name] += 1
                
            return RestrictionResult(
                allowed=True,
                restriction_type=RestrictionType.USAGE_QUOTA,
                reason="Within quota limits",
                metadata={
                    "tool": tool.name,
                    "remaining": self._get_remaining_quota(tool, context)
                }
            )
            
    def _check_reset_quotas(self):
        """Check if quotas need to be reset"""
        current_time = datetime.now()
        
        for period_name, period_delta in self._reset_periods.items():
            if period_name not in self._last_reset:
                self._last_reset[period_name] = current_time
                continue
                
            if current_time - self._last_reset[period_name] >= period_delta:
                # Reset quotas for this period
                logger.info(f"Resetting {period_name} quotas")
                self._usage_counts.clear()
                self._last_reset[period_name] = current_time
                
    def _get_remaining_quota(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext]
    ) -> int:
        """Get remaining quota for a tool"""
        # Tool quota
        if tool.name in self._tool_quotas:
            tool_usage = sum(
                counts.get(tool.name, 0)
                for counts in self._usage_counts.values()
            )
            tool_remaining = self._tool_quotas[tool.name] - tool_usage
        else:
            tool_remaining = float('inf')
            
        # User quota
        if context and context.user:
            user_id = context.user.user_id
            if user_id in self._user_quotas:
                user_quota = self._user_quotas[user_id].get(
                    tool.name,
                    self._user_quotas[user_id].get("default", float('inf'))
                )
                user_usage = self._usage_counts[user_id].get(tool.name, 0)
                user_remaining = user_quota - user_usage
            else:
                user_remaining = float('inf')
        else:
            user_remaining = float('inf')
            
        remaining = min(tool_remaining, user_remaining)
        
        # Handle infinity case
        if not isfinite(remaining):
            return 999999999  # Large but finite number
        
        return int(remaining)
        
    def set_tool_quota(self, tool_name: str, quota: int):
        """Set quota for a tool"""
        self._tool_quotas[tool_name] = quota
        
    def set_user_quota(
        self,
        user_id: str,
        tool_name: str,
        quota: int
    ):
        """Set quota for a user/tool combination"""
        if user_id not in self._user_quotas:
            self._user_quotas[user_id] = {}
        self._user_quotas[user_id][tool_name] = quota
        
    def set_default_user_quota(self, user_id: str, quota: int):
        """Set default quota for a user"""
        if user_id not in self._user_quotas:
            self._user_quotas[user_id] = {}
        self._user_quotas[user_id]["default"] = quota


class RestrictionManager:
    """
    Manager that combines all restriction types
    
    Provides a unified interface for checking all restrictions.
    """
    
    def __init__(self):
        """Initialize restriction manager"""
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.resource_limiter = ResourceLimiter()
        self.permission_checker = PermissionChecker()
        self.time_restriction = TimeWindowRestriction()
        self.quota_manager = UsageQuotaManager()
        self._enabled = True
        
    def check_all_restrictions(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext] = None
    ) -> List[RestrictionResult]:
        """Check all restrictions for a tool"""
        if not self._enabled:
            return [RestrictionResult(
                allowed=True,
                restriction_type=RestrictionType.PERMISSION,
                reason="Restrictions disabled"
            )]
            
        results = []
        
        # Check rate limits
        for name, limiter in self.rate_limiters.items():
            result = limiter.check_limit(tool.name, context)
            if not result.allowed:
                results.append(result)
                
        # Check resources
        resource_result = self.resource_limiter.check_resources(
            tool.name, context
        )
        if not resource_result.allowed:
            results.append(resource_result)
            
        # Check permissions
        perm_result = self.permission_checker.check_permission(tool, context)
        if not perm_result.allowed:
            results.append(perm_result)
            
        # Check time windows
        time_result = self.time_restriction.check_time_window(tool, context)
        if not time_result.allowed:
            results.append(time_result)
            
        # Check quotas
        quota_result = self.quota_manager.check_quota(tool, context)
        if not quota_result.allowed:
            results.append(quota_result)
            
        return results
        
    def is_allowed(
        self,
        tool: BaseTool,
        context: Optional[ExecutionContext] = None
    ) -> Tuple[bool, Optional[RestrictionResult]]:
        """
        Check if tool usage is allowed
        
        Returns:
            Tuple of (is_allowed, first_restriction_that_failed)
        """
        restrictions = self.check_all_restrictions(tool, context)
        
        if restrictions:
            # Return first restriction that failed
            return False, restrictions[0]
        else:
            # All checks passed
            return True, None
            
    def add_rate_limiter(
        self,
        name: str,
        rate: float,
        burst: int,
        per_user: bool = True
    ):
        """Add a rate limiter"""
        self.rate_limiters[name] = RateLimiter(rate, burst, per_user)
        
    def enable(self):
        """Enable all restrictions"""
        self._enabled = True
        
    def disable(self):
        """Disable all restrictions"""
        self._enabled = False