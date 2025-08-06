"""
Tool Control System Simple Demonstration

This is a simplified version that avoids circular imports by using
direct imports and creating a minimal test setup.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# flake8: noqa: E402
from tools.base import BaseTool, ToolMetadata, ToolCategory, ToolResult
from tools.policies.tool_policy import (
    AllowListPolicy, DenyListPolicy, CategoryPolicy,
    CapabilityPolicy, CompositePolicy
)
from tools.control.tool_context import (
    UserContext, TaskContext, EnvironmentContext,
    ExecutionContext, UserRole, TaskType, Environment
)
from tools.control.restrictions import (
    RateLimiter, ResourceLimiter,
    TimeWindowRestriction, UsageQuotaManager
)


# Simple demo tools
class DemoFileTool(BaseTool):
    """Demo file tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="demo_file_tool",
            version="1.0.0",
            description="Demo file operations",
            author="Demo",
            category=ToolCategory.UTILITY,
            capabilities={"file_read": True}
        )
    
    def initialize(self):
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            output="File operation completed"
        )
    
    def shutdown(self):
        pass


class DemoNetworkTool(BaseTool):
    """Demo network tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="demo_network_tool",
            version="1.0.0",
            description="Demo network operations",
            author="Demo",
            category=ToolCategory.INTEGRATION,
            capabilities={"network_access": True}
        )
    
    def initialize(self):
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        return ToolResult(
            success=True,
            output="Network operation completed"
        )
    
    def shutdown(self):
        pass


def demo_policies():
    """Demonstrate policy functionality"""
    print("=== Tool Policy Demonstration ===\n")
    
    # Create demo tools
    file_tool = DemoFileTool()
    network_tool = DemoNetworkTool()
    
    # Test AllowListPolicy
    print("1. Allow List Policy:")
    allow_policy = AllowListPolicy(
        ["demo_file_tool"],
        name="FileOnlyPolicy"
    )
    
    allowed = allow_policy.check_tool(file_tool, {}).allowed
    print(f"  File tool allowed: {allowed}")
    allowed = allow_policy.check_tool(network_tool, {}).allowed
    print(f"  Network tool allowed: {allowed}")
    
    # Test DenyListPolicy
    print("\n2. Deny List Policy:")
    deny_policy = DenyListPolicy(
        ["demo_network_tool"],
        name="NoNetworkPolicy"
    )
    
    allowed = deny_policy.check_tool(file_tool, {}).allowed
    print(f"  File tool allowed: {allowed}")
    allowed = deny_policy.check_tool(network_tool, {}).allowed
    print(f"  Network tool allowed: {allowed}")
    
    # Test CategoryPolicy
    print("\n3. Category Policy:")
    category_policy = CategoryPolicy(
        allowed_categories=[ToolCategory.UTILITY],
        name="UtilityOnlyPolicy"
    )
    
    allowed = category_policy.check_tool(file_tool, {}).allowed
    print(f"  File tool (UTILITY) allowed: {allowed}")
    allowed = category_policy.check_tool(network_tool, {}).allowed
    print(f"  Network tool (INTEGRATION) allowed: {allowed}")
    
    # Test CapabilityPolicy
    print("\n4. Capability Policy:")
    capability_policy = CapabilityPolicy(
        forbidden_capabilities=["network_access"],
        name="NoNetworkAccessPolicy"
    )
    
    allowed = capability_policy.check_tool(file_tool, {}).allowed
    print(f"  File tool allowed: {allowed}")
    allowed = capability_policy.check_tool(network_tool, {}).allowed
    print(f"  Network tool allowed: {allowed}")
    
    # Test CompositePolicy (ALL mode)
    print("\n5. Composite Policy (ALL mode - all must pass):")
    composite_all = CompositePolicy(
        policies=[
            CategoryPolicy(
                allowed_categories=[
                    ToolCategory.UTILITY, ToolCategory.INTEGRATION
                ]
            ),
            CapabilityPolicy(forbidden_capabilities=["network_access"])
        ],
        mode=CompositePolicy.CombineMode.ALL,
        name="SecurePolicy"
    )
    
    allowed = composite_all.check_tool(file_tool, {}).allowed
    print(f"  File tool allowed: {allowed}")
    allowed = composite_all.check_tool(network_tool, {}).allowed
    print(f"  Network tool allowed: {allowed}")
    
    # Test CompositePolicy (ANY mode)
    print("\n6. Composite Policy (ANY mode - any can pass):")
    composite_any = CompositePolicy(
        policies=[
            AllowListPolicy(["demo_file_tool"]),
            CategoryPolicy(allowed_categories=[ToolCategory.INTEGRATION])
        ],
        mode=CompositePolicy.CombineMode.ANY,
        name="FlexiblePolicy"
    )
    
    allowed = composite_any.check_tool(file_tool, {}).allowed
    print(f"  File tool allowed: {allowed}")
    allowed = composite_any.check_tool(network_tool, {}).allowed
    print(f"  Network tool allowed: {allowed}")


def demo_context_system():
    """Demonstrate context system"""
    print("\n\n=== Context System Demonstration ===\n")
    
    # Create contexts
    admin_context = ExecutionContext(
        user=UserContext(
            user_id="admin123",
            role=UserRole.ADMIN,
            permissions={"read", "write", "debug"}
        ),
        task=TaskContext(
            task_id="task1",
            task_type=TaskType.DATA_PROCESSING,
            description="System maintenance"
        ),
        environment=EnvironmentContext(
            environment=Environment.PRODUCTION,
            resources={"cpu": 50, "memory": 60}
        )
    )
    
    user_context = ExecutionContext(
        user=UserContext(
            user_id="user456",
            role=UserRole.USER,
            permissions={"read"}
        ),
        task=TaskContext(
            task_id="task2",
            task_type=TaskType.FILE_OPERATION,
            description="Read files"
        ),
        environment=EnvironmentContext(
            environment=Environment.DEVELOPMENT
        )
    )
    
    # Display contexts
    print("1. Admin Context:")
    user_info = f"{admin_context.user.user_id} (Role: {admin_context.user.role.value})"
    print(f"  User: {user_info}")
    print(f"  Task: {admin_context.task.description}")
    print(f"  Environment: {admin_context.environment.environment.value}")
    
    print("\n2. User Context:")
    user_info = f"{user_context.user.user_id} (Role: {user_context.user.role.value})"
    print(f"  User: {user_info}")
    print(f"  Task: {user_context.task.description}")
    print(f"  Environment: {user_context.environment.environment.value}")


def demo_restrictions():
    """Demonstrate restrictions"""
    print("\n\n=== Restrictions Demonstration ===\n")
    
    # Rate limiter demo
    print("1. Rate Limiter (0.5 requests/second, burst of 2):")
    rate_limiter = RateLimiter(
        rate=0.5,  # 0.5 requests per second
        burst=2,   # Allow 2 burst requests
        per_user=False
    )
    
    context = ExecutionContext()
    for i in range(4):
        result = rate_limiter.check_limit("demo_tool", context)
        status = '✓' if result.allowed else '✗'
        print(f"  Attempt {i+1}: {status} - {result.reason}")
        if i < 3:
            time.sleep(1)
    
    # Resource limiter demo
    print("\n2. Resource Limiter:")
    resource_limiter = ResourceLimiter(
        max_memory_percent=70.0,
        max_cpu_percent=80.0
    )
    
    result = resource_limiter.check_resources("demo_tool")
    status = '✓' if result.allowed else '✗'
    print(f"  Resource check: {status} - {result.reason}")
    if result.metadata:
        print(f"    CPU: {result.metadata.get('cpu_percent', 0):.1f}%")
        print(f"    Memory: {result.metadata.get('memory_percent', 0):.1f}%")
    
    # Time window demo
    print("\n3. Time Window Restriction:")
    time_restriction = TimeWindowRestriction()
    time_restriction.add_tool_window("demo_tool", 9, 17)  # 9 AM - 5 PM
    
    current_hour = datetime.now().hour
    
    # Create a mock tool
    tool = DemoFileTool()
    result = time_restriction.check_time_window(tool)
    status = '✓' if result.allowed else '✗'
    hour_info = f"({current_hour}:00)"
    print(f"  Current hour {hour_info}: {status} - {result.reason}")
    
    # Usage quota demo
    print("\n4. Usage Quota Manager:")
    quota_manager = UsageQuotaManager()
    quota_manager.set_tool_quota("demo_tool", 3)
    
    tool = DemoFileTool()
    # Create new tool with correct name
    tool = DemoFileTool()
    
    for i in range(5):
        result = quota_manager.check_quota(tool)
        status = '✓' if result.allowed else '✗'
        print(f"  Usage {i+1}: {status} - {result.reason}")
        if result.metadata:
            print(f"    Remaining: {result.metadata.get('remaining', 0)}")


def main():
    """Run all demonstrations"""
    print("=" * 60)
    print("Tool Control System Simple Demo")
    print("=" * 60)
    
    demo_policies()
    demo_context_system()
    demo_restrictions()
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()