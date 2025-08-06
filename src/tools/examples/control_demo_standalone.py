"""
Tool Control System Standalone Demonstration

This is a completely standalone demo that demonstrates the tool control
system concepts without relying on the circular import structure.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass


# ============= Enums =============
class ToolCategory(Enum):
    """Tool categories"""
    UTILITY = "utility"
    INTEGRATION = "integration"
    DEBUG = "debug"


class UserRole(Enum):
    """User roles"""
    ADMIN = "admin"
    USER = "user"
    DEVELOPER = "developer"


class TaskType(Enum):
    """Task types"""
    DATA_PROCESSING = "data_processing"
    FILE_OPERATION = "file_operation"
    GENERAL = "general"


class Environment(Enum):
    """Environment types"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"


# ============= Data Classes =============
@dataclass
class ToolMetadata:
    """Tool metadata"""
    name: str
    version: str
    description: str
    author: str
    category: ToolCategory
    capabilities: Dict[str, bool]


@dataclass
class ToolResult:
    """Tool execution result"""
    success: bool
    output: Any
    errors: List[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class PolicyResult:
    """Policy check result"""
    allowed: bool
    reason: str = ""
    policy_name: str = ""


@dataclass
class RestrictionResult:
    """Restriction check result"""
    allowed: bool
    reason: str = ""
    restriction_type: str = ""
    metadata: Optional[Dict[str, Any]] = None


# ============= Demo Tools =============
class DemoTool:
    """Base demo tool"""
    def __init__(self, metadata: ToolMetadata):
        self.metadata = metadata
        self.name = metadata.name
        
    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            output=f"Executed {self.name}"
        )


# ============= Policy System =============
class BasePolicy:
    """Base policy class"""
    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        
    def check_tool(self, tool: DemoTool, context: Dict[str, Any]) -> PolicyResult:
        """Check if tool is allowed"""
        raise NotImplementedError


class AllowListPolicy(BasePolicy):
    """Allow only specific tools"""
    def __init__(self, allowed_tools: List[str], name: str = ""):
        super().__init__(name)
        self.allowed_tools = set(allowed_tools)
        
    def check_tool(self, tool: DemoTool, context: Dict[str, Any]) -> PolicyResult:
        allowed = tool.name in self.allowed_tools
        reason = (
            f"Tool {tool.name} is in allow list" if allowed
            else f"Tool {tool.name} is not in allow list"
        )
        return PolicyResult(allowed=allowed, reason=reason, policy_name=self.name)


class DenyListPolicy(BasePolicy):
    """Deny specific tools"""
    def __init__(self, denied_tools: List[str], name: str = ""):
        super().__init__(name)
        self.denied_tools = set(denied_tools)
        
    def check_tool(self, tool: DemoTool, context: Dict[str, Any]) -> PolicyResult:
        allowed = tool.name not in self.denied_tools
        reason = (
            f"Tool {tool.name} is not in deny list" if allowed
            else f"Tool {tool.name} is in deny list"
        )
        return PolicyResult(allowed=allowed, reason=reason, policy_name=self.name)


class CategoryPolicy(BasePolicy):
    """Allow tools by category"""
    def __init__(self, allowed_categories: List[ToolCategory], name: str = ""):
        super().__init__(name)
        self.allowed_categories = set(allowed_categories)
        
    def check_tool(self, tool: DemoTool, context: Dict[str, Any]) -> PolicyResult:
        allowed = tool.metadata.category in self.allowed_categories
        reason = (
            f"Category {tool.metadata.category.value} is allowed" if allowed
            else f"Category {tool.metadata.category.value} is not allowed"
        )
        return PolicyResult(allowed=allowed, reason=reason, policy_name=self.name)


class CapabilityPolicy(BasePolicy):
    """Filter tools by capabilities"""
    def __init__(self, forbidden_capabilities: List[str], name: str = ""):
        super().__init__(name)
        self.forbidden_capabilities = set(forbidden_capabilities)
        
    def check_tool(self, tool: DemoTool, context: Dict[str, Any]) -> PolicyResult:
        tool_caps = set(k for k, v in tool.metadata.capabilities.items() if v)
        forbidden = tool_caps & self.forbidden_capabilities
        allowed = not forbidden
        reason = (
            "No forbidden capabilities" if allowed
            else f"Has forbidden capabilities: {forbidden}"
        )
        return PolicyResult(allowed=allowed, reason=reason, policy_name=self.name)


# ============= Restriction System =============
class RateLimiter:
    """Rate limiting"""
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        
    def check_limit(self, tool_name: str) -> RestrictionResult:
        """Check rate limit"""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return RestrictionResult(
                allowed=True,
                reason="Within rate limit",
                restriction_type="rate_limit"
            )
        else:
            return RestrictionResult(
                allowed=False,
                reason=f"Rate limit exceeded (rate: {self.rate}/sec)",
                restriction_type="rate_limit"
            )


class TimeWindowRestriction:
    """Time-based restrictions"""
    def __init__(self):
        self.tool_windows = {}
        
    def add_tool_window(self, tool_name: str, start_hour: int, end_hour: int):
        """Add time window for tool"""
        self.tool_windows[tool_name] = (start_hour, end_hour)
        
    def check_time_window(self, tool: DemoTool) -> RestrictionResult:
        """Check if current time is within allowed window"""
        if tool.name not in self.tool_windows:
            return RestrictionResult(
                allowed=True,
                reason="No time restrictions",
                restriction_type="time_window"
            )
            
        start, end = self.tool_windows[tool.name]
        current_hour = datetime.now().hour
        
        if start <= current_hour < end:
            return RestrictionResult(
                allowed=True,
                reason=f"Within allowed hours ({start}-{end})",
                restriction_type="time_window"
            )
        else:
            return RestrictionResult(
                allowed=False,
                reason=f"Outside allowed hours ({start}-{end})",
                restriction_type="time_window"
            )


# ============= Demo Functions =============
def demo_policies():
    """Demonstrate policy functionality"""
    print("=== Tool Policy Demonstration ===\n")
    
    # Create demo tools
    file_tool = DemoTool(ToolMetadata(
        name="file_tool",
        version="1.0.0",
        description="File operations",
        author="Demo",
        category=ToolCategory.UTILITY,
        capabilities={"file_read": True}
    ))
    
    network_tool = DemoTool(ToolMetadata(
        name="network_tool",
        version="1.0.0",
        description="Network operations",
        author="Demo",
        category=ToolCategory.INTEGRATION,
        capabilities={"network_access": True}
    ))
    
    debug_tool = DemoTool(ToolMetadata(
        name="debug_tool",
        version="1.0.0",
        description="Debug operations",
        author="Demo",
        category=ToolCategory.DEBUG,
        capabilities={"debug": True, "system_access": True}
    ))
    
    tools = [file_tool, network_tool, debug_tool]
    
    # Test policies
    print("1. Allow List Policy (only file_tool):")
    policy = AllowListPolicy(["file_tool"], "FileOnlyPolicy")
    for tool in tools:
        result = policy.check_tool(tool, {})
        print(f"  {tool.name}: {'✓' if result.allowed else '✗'} - {result.reason}")
    
    print("\n2. Deny List Policy (no network_tool):")
    policy = DenyListPolicy(["network_tool"], "NoNetworkPolicy")
    for tool in tools:
        result = policy.check_tool(tool, {})
        print(f"  {tool.name}: {'✓' if result.allowed else '✗'} - {result.reason}")
    
    print("\n3. Category Policy (UTILITY only):")
    policy = CategoryPolicy([ToolCategory.UTILITY], "UtilityOnlyPolicy")
    for tool in tools:
        result = policy.check_tool(tool, {})
        print(f"  {tool.name}: {'✓' if result.allowed else '✗'} - {result.reason}")
    
    print("\n4. Capability Policy (no system_access):")
    policy = CapabilityPolicy(["system_access"], "NoSystemAccessPolicy")
    for tool in tools:
        result = policy.check_tool(tool, {})
        print(f"  {tool.name}: {'✓' if result.allowed else '✗'} - {result.reason}")


def demo_restrictions():
    """Demonstrate restrictions"""
    print("\n\n=== Restrictions Demonstration ===\n")
    
    # Rate limiting demo
    print("1. Rate Limiting (0.5 requests/second, burst of 2):")
    rate_limiter = RateLimiter(rate=0.5, burst=2)
    
    for i in range(4):
        result = rate_limiter.check_limit("test_tool")
        status = '✓' if result.allowed else '✗'
        print(f"  Attempt {i+1}: {status} - {result.reason}")
        if i < 3:
            time.sleep(1)
    
    # Time window demo
    print("\n2. Time Window Restriction (9 AM - 5 PM):")
    time_restriction = TimeWindowRestriction()
    time_restriction.add_tool_window("business_tool", 9, 17)
    
    tool = DemoTool(ToolMetadata(
        name="business_tool",
        version="1.0.0",
        description="Business hours tool",
        author="Demo",
        category=ToolCategory.UTILITY,
        capabilities={}
    ))
    
    result = time_restriction.check_time_window(tool)
    current_hour = datetime.now().hour
    status = '✓' if result.allowed else '✗'
    print(f"  Current hour ({current_hour}:00): {status} - {result.reason}")


def demo_context_system():
    """Demonstrate context system concepts"""
    print("\n\n=== Context System Demonstration ===\n")
    
    # Create example contexts
    contexts = [
        {
            "name": "Admin in Production",
            "user_role": UserRole.ADMIN,
            "task_type": TaskType.DATA_PROCESSING,
            "environment": Environment.PRODUCTION
        },
        {
            "name": "User in Development",
            "user_role": UserRole.USER,
            "task_type": TaskType.FILE_OPERATION,
            "environment": Environment.DEVELOPMENT
        },
        {
            "name": "Developer in Testing",
            "user_role": UserRole.DEVELOPER,
            "task_type": TaskType.GENERAL,
            "environment": Environment.TESTING
        }
    ]
    
    for ctx in contexts:
        print(f"{ctx['name']}:")
        print(f"  Role: {ctx['user_role'].value}")
        print(f"  Task: {ctx['task_type'].value}")
        print(f"  Environment: {ctx['environment'].value}")
        print()


def main():
    """Run all demonstrations"""
    print("=" * 60)
    print("Tool Control System Standalone Demo")
    print("=" * 60)
    
    demo_policies()
    demo_restrictions()
    demo_context_system()
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    
    print("\n📝 Summary:")
    print("- Created policy system with Allow/Deny/Category/Capability policies")
    print("- Implemented rate limiting and time window restrictions")
    print("- Demonstrated context-aware concepts with roles and environments")
    print("- All components work together to control tool access and usage")


if __name__ == "__main__":
    main()