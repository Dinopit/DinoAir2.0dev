"""
Tool Control System Demonstration

This module provides comprehensive examples of using the tool control
system, including policies, context-aware selection, restrictions,
and integration with the registry.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# flake8: noqa: E402
from tools.base import BaseTool, ToolMetadata, ToolCategory, ToolResult
from tools.registry import ToolRegistry
from tools.control.tool_controller import (
    ToolController, PolicyBasedToolController
)
from tools.control.tool_context import (
    UserContext, TaskContext, EnvironmentContext,
    ExecutionContext, ContextualToolSelector,
    UserRole, Environment, TaskType
)
from tools.control.restrictions import (
    RateLimiter, ResourceLimiter,
    TimeWindowRestriction, UsageQuotaManager
)
from tools.policies.tool_policy import (
    AllowListPolicy, DenyListPolicy, CategoryPolicy,
    CapabilityPolicy, CompositePolicy
)
from tools.ai_adapter import ToolAIAdapter


# Example tools for demonstration
class FileReaderTool(BaseTool):
    """Example file reading tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="file_reader",
            version="1.0.0",
            description="Reads files from the filesystem",
            author="Demo System",
            category=ToolCategory.UTILITY,
            capabilities={
                "file_read": True,
                "encoding": True
            }
        )
    
    def initialize(self):
        """Initialize the tool"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Simulate file reading"""
        filepath = kwargs.get("filepath", "example.txt")
        return ToolResult(
            success=True,
            output=f"Content of {filepath}: [simulated content]"
        )
    
    def shutdown(self):
        """Cleanup resources"""
        pass


class NetworkTool(BaseTool):
    """Example network tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="network_tool",
            version="1.0.0",
            description="Makes network requests",
            author="Demo System",
            category=ToolCategory.INTEGRATION,
            capabilities={
                "http": True,
                "network_access": True
            }
        )
    
    def initialize(self):
        """Initialize the tool"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Simulate network request"""
        url = kwargs.get("url", "https://example.com")
        return ToolResult(
            success=True,
            output=f"Response from {url}: [simulated response]"
        )
    
    def shutdown(self):
        """Cleanup resources"""
        pass


class DatabaseTool(BaseTool):
    """Example database tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="database_tool",
            version="1.0.0",
            description="Queries databases",
            author="Demo System",
            category=ToolCategory.INTEGRATION,
            capabilities={
                "sql": True,
                "write": True
            }
        )
    
    def initialize(self):
        """Initialize the tool"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Simulate database query"""
        query = kwargs.get("query", "SELECT * FROM users")
        return ToolResult(
            success=True,
            output=f"Query result for '{query}': [simulated data]"
        )
    
    def shutdown(self):
        """Cleanup resources"""
        pass


class DebugTool(BaseTool):
    """Example debug tool"""
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="debug_tool",
            version="1.0.0",
            description="Debugging utilities",
            author="Demo System",
            category=ToolCategory.DEBUG,
            capabilities={
                "debug": True,
                "system_access": True
            }
        )
    
    def initialize(self):
        """Initialize the tool"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Simulate debugging"""
        return ToolResult(
            success=True,
            output="Debug info: [simulated debug output]"
        )
    
    def shutdown(self):
        """Cleanup resources"""
        pass


def setup_demo_tools():
    """Register demo tools in the registry"""
    registry = ToolRegistry()
    
    # Register tools
    registry.register_tool(FileReaderTool)
    registry.register_tool(NetworkTool)
    registry.register_tool(DatabaseTool)
    registry.register_tool(DebugTool)
    
    print("✓ Registered 4 demo tools")
    return registry


def demo_basic_policies():
    """Demonstrate basic policy usage"""
    print("\n=== Basic Policy Demonstration ===")
    
    registry = setup_demo_tools()
    controller = ToolController(registry)
    
    # Example 1: Allow list policy
    print("\n1. Allow List Policy:")
    allow_policy = AllowListPolicy(
        ["file_reader", "database_tool"],
        name="BasicAllowPolicy"
    )
    controller.add_policy(allow_policy)
    
    # Test tool access
    tools = ["file_reader", "network_tool", "database_tool", "debug_tool"]
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 2: Deny list policy
    print("\n2. Deny List Policy:")
    controller.set_policies([])  # Clear policies
    deny_policy = DenyListPolicy(
        ["debug_tool", "network_tool"],
        name="SecurityDenyPolicy"
    )
    controller.add_policy(deny_policy)
    
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 3: Category policy
    print("\n3. Category Policy:")
    controller.set_policies([])
    category_policy = CategoryPolicy(
        allowed_categories=[ToolCategory.UTILITY, ToolCategory.INTEGRATION],
        name="DataOnlyPolicy"
    )
    controller.add_policy(category_policy)
    
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 4: Capability policy
    print("\n4. Capability Policy:")
    controller.set_policies([])
    capability_policy = CapabilityPolicy(
        forbidden_capabilities=["network_access", "system_access"],
        name="NoSystemAccessPolicy"
    )
    controller.add_policy(capability_policy)
    
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")


def demo_composite_policies():
    """Demonstrate composite policy combinations"""
    print("\n=== Composite Policy Demonstration ===")
    
    registry = setup_demo_tools()
    controller = ToolController(registry)
    
    # Example 1: AND composite (all must pass)
    print("\n1. AND Composite Policy:")
    and_policy = CompositePolicy(
        policies=[
            CategoryPolicy(
                allowed_categories=[
                    ToolCategory.UTILITY, ToolCategory.INTEGRATION,
                    ToolCategory.ANALYSIS
                ]
            ),
            CapabilityPolicy(forbidden_capabilities=["system_access"])
        ],
        mode=CompositePolicy.CombineMode.ALL,
        name="SecureDataPolicy"
    )
    controller.add_policy(and_policy)
    
    tools = ["file_reader", "network_tool", "database_tool", "debug_tool"]
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 2: OR composite (any can pass)
    print("\n2. OR Composite Policy:")
    controller.set_policies([])
    or_policy = CompositePolicy(
        policies=[
            AllowListPolicy(["file_reader"]),
            CategoryPolicy(allowed_categories=[ToolCategory.INTEGRATION])
        ],
        mode=CompositePolicy.CombineMode.ANY,
        name="FileOrDataPolicy"
    )
    controller.add_policy(or_policy)
    
    for tool_name in tools:
        can_use, reason = controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")


def demo_context_aware_selection():
    """Demonstrate context-aware tool selection"""
    print("\n=== Context-Aware Tool Selection ===")
    
    setup_demo_tools()
    
    # Create different contexts
    contexts = [
        {
            "name": "Admin User",
            "context": ExecutionContext(
                user=UserContext(
                    user_id="admin123",
                    role=UserRole.ADMIN,
                    permissions={"read", "write", "debug"}
                ),
                task=TaskContext(
                    task_id="task1",
                    task_type=TaskType.DATA_PROCESSING,
                    description="System Maintenance",
                    priority=8,
                    metadata={"category": "system"}
                ),
                environment=EnvironmentContext(
                    environment=Environment.PRODUCTION,
                    resources={"cpu": 80, "memory": 70}
                )
            )
        },
        {
            "name": "Regular User",
            "context": ExecutionContext(
                user=UserContext(
                    user_id="user456",
                    role=UserRole.USER,
                    permissions={"read"}
                ),
                task=TaskContext(
                    task_id="task2",
                    task_type=TaskType.FILE_OPERATION,
                    description="Read Files",
                    priority=5
                ),
                environment=EnvironmentContext(
                    environment=Environment.PRODUCTION
                )
            )
        }
    ]
    
    # Use contextual selector
    selector = ContextualToolSelector()
    
    # Demonstrate selection for each context
    for ctx_info in contexts:
        print(f"\n{ctx_info['name']} Context:")
        print(f"  Role: {ctx_info['context'].user.role.value}")
        env = ctx_info['context'].environment.environment
        print(f"  Environment: {env.value}")
        
        # Get tool recommendations
        recommendations = selector.select_tools(
            ctx_info['context'],
            max_tools=4
        )
        
        print("  Tool Recommendations:")
        for tool_name, score in recommendations:
            print(f"    - {tool_name}: {score:.2f}")


async def demo_restrictions():
    """Demonstrate tool usage restrictions"""
    print("\n=== Tool Usage Restrictions ===")
    
    registry = setup_demo_tools()
    
    # Example 1: Rate limiting
    print("\n1. Rate Limiting:")
    rate_limiter = RateLimiter(
        rate=0.5,  # 0.5 requests per second
        burst=2,   # Allow 2 burst requests
        per_user=False
    )
    
    tool_name = "file_reader"
    for i in range(5):
        context = ExecutionContext()
        result = rate_limiter.check_limit(tool_name, context)
        status = '✓' if result.allowed else '✗'
        print(f"  Attempt {i+1}: {status} ({result.reason})")
        await asyncio.sleep(1)
    
    # Example 2: Resource limiting
    print("\n2. Resource Limiting:")
    resource_limiter = ResourceLimiter(
        max_memory_percent=70.0,
        max_cpu_percent=80.0
    )
    
    result = resource_limiter.check_resources("database_tool")
    status = '✓' if result.allowed else '✗'
    print(f"  Resource check: {status} ({result.reason})")
    if result.metadata:
        print(f"    CPU: {result.metadata.get('cpu_percent', 0):.1f}%")
        print(f"    Memory: {result.metadata.get('memory_percent', 0):.1f}%")
    
    # Example 3: Time window restrictions
    print("\n3. Time Window Restrictions:")
    time_restriction = TimeWindowRestriction()
    # Add business hours restriction (9 AM - 5 PM)
    time_restriction.add_tool_window("network_tool", 9, 17)
    
    tool = registry.get_tool("network_tool")
    if tool:
        result = time_restriction.check_time_window(tool)
        current_hour = datetime.now().hour
        print(
            f"  Current hour ({current_hour}:00): "
            f"{'✓' if result.allowed else '✗'} ({result.reason})"
        )
    
    # Example 4: Usage quotas
    print("\n4. Usage Quotas:")
    quota_manager = UsageQuotaManager()
    quota_manager.set_tool_quota("file_reader", 100)
    
    # Simulate usage
    tool = registry.get_tool("file_reader")
    if tool:
        for i in range(3):
            result = quota_manager.check_quota(tool)
            status = '✓' if result.allowed else '✗'
            print(f"  Usage {i+1}: {status} ({result.reason})")
            if result.metadata:
                print(f"    Remaining: {result.metadata.get('remaining', 0)}")


def demo_policy_controller():
    """Demonstrate the PolicyBasedToolController"""
    print("\n=== Policy-Based Tool Controller ===")
    
    registry = setup_demo_tools()
    
    # Example 1: Safe mode
    print("\n1. Safe Mode Controller:")
    safe_controller = PolicyBasedToolController(
        registry,
        safe_mode=True
    )
    
    tools = ["file_reader", "network_tool", "database_tool", "debug_tool"]
    for tool_name in tools:
        can_use, reason = safe_controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 2: Custom allow/deny lists
    print("\n2. Custom Allow/Deny Lists:")
    custom_controller = PolicyBasedToolController(
        registry,
        safe_mode=False,
        allowed_tools=["file_reader", "database_tool"],
        denied_tools=["debug_tool"]
    )
    
    for tool_name in tools:
        can_use, reason = custom_controller.can_use_tool(tool_name)
        print(f"  - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    # Example 3: Mode switching
    print("\n3. Mode Switching:")
    mode_controller = PolicyBasedToolController(registry, safe_mode=True)
    
    print("  Production Mode:")
    mode_controller.enable_production_mode()
    for tool_name in ["file_reader", "debug_tool"]:
        can_use, reason = mode_controller.can_use_tool(tool_name)
        print(f"    - {tool_name}: {'✓' if can_use else '✗'} ({reason})")
    
    print("  Developer Mode:")
    mode_controller.enable_developer_mode()
    for tool_name in ["file_reader", "debug_tool"]:
        can_use, reason = mode_controller.can_use_tool(tool_name)
        print(f"    - {tool_name}: {'✓' if can_use else '✗'} ({reason})")


def demo_tool_recommendations():
    """Demonstrate tool recommendation system"""
    print("\n=== Tool Recommendation System ===")
    
    registry = setup_demo_tools()
    controller = ToolController(registry)
    
    # Test different task descriptions
    tasks = [
        "I need to read configuration files",
        "Query the user database for analytics",
        "Make an API request to external service",
        "Debug application performance issues"
    ]
    
    for task in tasks:
        print(f"\nTask: '{task}'")
        result = controller.recommend_tools(
            task,
            context={
                "user": {"role": "developer"},
                "environment": {"type": "development"}
            },
            max_recommendations=3
        )
        
        print("  Recommendations:")
        for tool_name in result.selected_tools:
            score_info = result.scores[tool_name]
            print(f"    - {tool_name} (score: {score_info.total_score:.2f})")
            for reason in score_info.reasons[:2]:  # Show top 2 reasons
                print(f"      • {reason}")


def demo_registry_integration():
    """Demonstrate registry integration with policies"""
    print("\n=== Registry Integration with Policies ===")
    
    registry = setup_demo_tools()
    
    # Create and set controller
    controller = PolicyBasedToolController(registry, safe_mode=True)
    registry.set_controller(controller)
    
    # Create contexts
    admin_context = ExecutionContext(
        user=UserContext(user_id="admin", role=UserRole.ADMIN),
        environment=EnvironmentContext(environment=Environment.PRODUCTION)
    )
    
    user_context = ExecutionContext(
        user=UserContext(user_id="user", role=UserRole.USER),
        environment=EnvironmentContext(environment=Environment.PRODUCTION)
    )
    
    # Example 1: Get tools with policy checking
    print("\n1. List Tools with Policy Checks:")
    print("  Admin context:")
    admin_tools = registry.list_tools(
        enabled_only=True,
        context=admin_context,
        check_policies=True
    )
    for tool in admin_tools:
        allowed = "✓" if tool.get("is_allowed", True) else "✗"
        print(f"    - {tool['name']}: {allowed}")
    
    print("  User context:")
    user_tools = registry.list_tools(
        enabled_only=True,
        context=user_context,
        check_policies=True
    )
    for tool in user_tools:
        allowed = "✓" if tool.get("is_allowed", True) else "✗"
        print(f"    - {tool['name']}: {allowed}")
    
    # Example 2: Get tool with context
    print("\n2. Get Tool with Context:")
    tool_name = "debug_tool"
    
    print(f"  Admin getting {tool_name}:")
    admin_tool = registry.get_tool(tool_name, context=admin_context)
    print(f"    Result: {'✓ Got tool' if admin_tool else '✗ Denied'}")
    
    print(f"  User getting {tool_name}:")
    user_tool = registry.get_tool(tool_name, context=user_context)
    print(f"    Result: {'✓ Got tool' if user_tool else '✗ Denied'}")


def demo_configuration_loading():
    """Demonstrate loading control configuration"""
    print("\n=== Configuration Loading ===")
    
    # Load configuration
    config_path = (
        Path(__file__).parent.parent / "config" / "control_config.json"
    )
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        
        print("Loaded configuration:")
        print(f"  - Environments: {list(config['environments'].keys())}")
        print(f"  - Roles: {list(config['role_permissions'].keys())}")
        print(f"  - Tool configs: {len(config['tool_configs'])}")
        
        # Show example environment config
        prod_config = config['environments']['production']
        print("\nProduction environment policies:")
        for policy in prod_config['policies']:
            print(f"  - {policy['type']}: {policy.get('name', 'unnamed')}")
    else:
        print(f"Configuration file not found at {config_path}")


async def demo_ai_adapter_integration():
    """Demonstrate AI adapter with tool control"""
    print("\n=== AI Adapter Integration ===")
    
    registry = setup_demo_tools()
    
    # Create controller with policies
    controller = PolicyBasedToolController(
        registry,
        safe_mode=True,
        allowed_tools=["file_reader", "database_tool"]
    )
    
    # Create AI adapter
    adapter = ToolAIAdapter(registry)
    
    # Set the controller on the registry
    registry.set_controller(controller)
    
    # Get available tools
    print("\n1. Available Tools for AI:")
    tools = adapter.get_available_tools()
    for tool in tools:
        print(f"  - {tool['name']}")
    
    # Try to execute tools
    print("\n2. Tool Execution:")
    test_tools = [
        ("file_reader", {"filepath": "config.json"}),
        ("network_tool", {"url": "https://api.example.com"}),
        ("database_tool", {"query": "SELECT * FROM users"})
    ]
    
    for tool_name, params in test_tools:
        print(f"\n  Executing {tool_name}:")
        invocation = {
            "name": tool_name,
            "parameters": params
        }
        result = adapter.execute_tool(
            invocation=invocation,
            track_history=True,
            validate_params=True
        )
        if result["success"]:
            print(f"    ✓ Success: {result.get('output', 'No output')}")
        else:
            print(f"    ✗ Failed: {result['error']}")


async def main():
    """Run all demonstrations"""
    print("=" * 60)
    print("Tool Control System Comprehensive Demo")
    print("=" * 60)
    
    # Run synchronous demos
    demo_basic_policies()
    demo_composite_policies()
    demo_context_aware_selection()
    demo_policy_controller()
    demo_tool_recommendations()
    demo_registry_integration()
    demo_configuration_loading()
    
    # Run async demos
    await demo_restrictions()
    await demo_ai_adapter_integration()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())