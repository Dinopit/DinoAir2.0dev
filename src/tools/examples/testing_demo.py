"""
Testing Framework Demo

This example demonstrates how to use the comprehensive testing framework
for tool development, including test generation, execution, and reporting.
"""

import asyncio
from typing import Dict, Any

# Import testing framework components
from ..testing.test_framework import (
    ToolTestCase, AsyncToolTestCase, ToolTestRunner,
    MockTool, create_test_suite
)
from ..testing.test_generator import (
    ToolTestGenerator, TestScenario, ParameterValueGenerator
)

# Import tool components
from ..base import (
    BaseTool, AsyncBaseTool, ToolMetadata, ToolParameter,
    ParameterType, ToolResult, ToolStatus
)
from ..registry import ToolRegistry


# Example 1: Create a simple tool for testing
class CalculatorTool(BaseTool):
    """A simple calculator tool for demonstration"""
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calculator",
            description="Performs basic mathematical operations",
            version="1.0.0",
            author="Demo Author",
            category="math",
            tags=["calculator", "math", "demo"]
        )
        
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "operation": ToolParameter(
                name="operation",
                type=ParameterType.ENUM,
                description="Mathematical operation to perform",
                required=True,
                enum_values=["add", "subtract", "multiply", "divide"]
            ),
            "a": ToolParameter(
                name="a",
                type=ParameterType.FLOAT,
                description="First number",
                required=True
            ),
            "b": ToolParameter(
                name="b",
                type=ParameterType.FLOAT,
                description="Second number",
                required=True
            )
        }
        
    def execute(self, **kwargs) -> ToolResult:
        operation = kwargs["operation"]
        a = kwargs["a"]
        b = kwargs["b"]
        
        try:
            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    raise ValueError("Division by zero")
                result = a / b
            else:
                raise ValueError(f"Unknown operation: {operation}")
                
            return ToolResult(
                success=True,
                data={"result": result, "operation": operation},
                message=f"{a} {operation} {b} = {result}"
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Calculation failed: {str(e)}"
            )


# Example 2: Create custom test cases
class CalculatorToolTests(ToolTestCase):
    """Custom test cases for the calculator tool"""
    
    def get_tool_name(self) -> str:
        return "calculator"
        
    def create_tool(self) -> BaseTool:
        return CalculatorTool()
        
    def test_addition(self):
        """Test addition operation"""
        result = self.execute_tool(
            operation="add",
            a=5,
            b=3
        )
        
        self.assert_success(result)
        self.assertEqual(result.data["result"], 8)
        
    def test_division_by_zero(self):
        """Test division by zero handling"""
        result = self.execute_tool(
            operation="divide",
            a=10,
            b=0
        )
        
        self.assert_failure(result)
        self.assertIn("Division by zero", result.error)
        
    def test_invalid_operation(self):
        """Test invalid operation handling"""
        # This should fail parameter validation
        with self.assertRaises(ValueError):
            self.execute_tool(
                operation="power",  # Not a valid operation
                a=2,
                b=3
            )


# Example 3: Use automatic test generation
def demo_test_generation():
    """Demonstrate automatic test generation"""
    print("=== Automatic Test Generation Demo ===\n")
    
    # Create test generator
    generator = ToolTestGenerator()
    
    # Create tool instance
    tool = CalculatorTool()
    
    # Generate test scenarios
    scenarios = generator.generate_test_scenarios(tool, count=5)
    
    print(f"Generated {len(scenarios)} test scenarios:\n")
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"Scenario {i}: {scenario.name}")
        print(f"  Description: {scenario.description}")
        print(f"  Parameters: {scenario.parameters}")
        print(f"  Expected success: {scenario.expected_success}")
        print()
        
    # Generate edge cases
    edge_cases = generator.generate_edge_cases(tool)
    
    print(f"\nGenerated {len(edge_cases)} edge case scenarios:")
    for scenario in edge_cases:
        print(f"  - {scenario.name}: {scenario.description}")
        
    return scenarios


# Example 4: Create async tool and tests
class AsyncDataFetcher(AsyncBaseTool):
    """An async tool that simulates data fetching"""
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="async_fetcher",
            description="Fetches data asynchronously",
            version="1.0.0",
            author="Demo Author",
            category="data"
        )
        
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "url": ToolParameter(
                name="url",
                type=ParameterType.STRING,
                description="URL to fetch data from",
                required=True
            ),
            "timeout": ToolParameter(
                name="timeout",
                type=ParameterType.FLOAT,
                description="Timeout in seconds",
                required=False,
                default=5.0
            )
        }
        
    async def execute_async(self, **kwargs) -> ToolResult:
        url = kwargs["url"]
        timeout = kwargs.get("timeout", 5.0)
        
        # Simulate async data fetching
        await asyncio.sleep(0.1)  # Simulate network delay
        
        if "error" in url:
            return ToolResult(
                success=False,
                error="Failed to fetch data",
                message=f"Error fetching from {url}"
            )
            
        return ToolResult(
            success=True,
            data={"url": url, "content": f"Data from {url}"},
            message=f"Successfully fetched data from {url}"
        )


class AsyncFetcherTests(AsyncToolTestCase):
    """Test cases for async data fetcher"""
    
    def get_tool_name(self) -> str:
        return "async_fetcher"
        
    def create_tool(self) -> AsyncBaseTool:
        return AsyncDataFetcher()
        
    async def test_successful_fetch(self):
        """Test successful data fetching"""
        result = await self.execute_tool_async(
            url="https://example.com/data"
        )
        
        self.assert_success(result)
        self.assertIn("example.com", result.data["content"])
        
    async def test_error_handling(self):
        """Test error URL handling"""
        result = await self.execute_tool_async(
            url="https://error.com/fail"
        )
        
        self.assert_failure(result)
        self.assertEqual(result.error, "Failed to fetch data")


# Example 5: Run tests with the test runner
def demo_test_execution():
    """Demonstrate test execution with the test runner"""
    print("\n=== Test Execution Demo ===\n")
    
    # Create test runner
    runner = ToolTestRunner(verbose=True)
    
    # Create and run calculator tests
    print("Running calculator tool tests:")
    calc_suite = create_test_suite(CalculatorToolTests)
    calc_result = runner.run_suite(calc_suite)
    
    print(f"\nCalculator test results:")
    print(f"  Total tests: {calc_result.tests_run}")
    print(f"  Passed: {len(calc_result.successes)}")
    print(f"  Failed: {len(calc_result.failures)}")
    print(f"  Errors: {len(calc_result.errors)}")
    
    # Generate report
    report = runner.generate_report()
    print(f"\nTest Report Summary:")
    print(f"  Total duration: {report['summary']['total_duration']:.2f}s")
    print(f"  Success rate: {report['summary']['success_rate']:.1%}")
    
    return report


# Example 6: Mock tool usage
def demo_mock_tool():
    """Demonstrate using mock tools for testing"""
    print("\n=== Mock Tool Demo ===\n")
    
    # Create a mock tool
    mock = MockTool("mock_calculator")
    
    # Configure mock behavior
    mock.set_result(ToolResult(
        success=True,
        data={"result": 42},
        message="Mock result"
    ))
    
    # Use mock in tests
    result = mock.execute(operation="add", a=20, b=22)
    print(f"Mock execution result: {result.message}")
    print(f"Mock was called {mock.call_count} times")
    print(f"Last call args: {mock.last_call_args}")
    
    # Configure mock to fail
    mock.set_result(ToolResult(
        success=False,
        error="Mock error",
        message="Simulated failure"
    ))
    
    result = mock.execute(operation="divide", a=10, b=0)
    print(f"\nMock failure result: {result.message}")
    
    return mock


# Example 7: Test with registry integration
def demo_registry_testing():
    """Demonstrate testing with tool registry"""
    print("\n=== Registry Integration Testing ===\n")
    
    # Create test registry
    registry = ToolRegistry()
    
    # Register tools
    registry.register_tool(CalculatorTool)
    registry.register_tool(AsyncDataFetcher)
    
    # Create test runner with registry
    runner = ToolTestRunner(registry=registry)
    
    # Run tests for all registered tools
    print("Running tests for all registered tools...")
    
    # Generate tests for registered tools
    generator = ToolTestGenerator()
    
    for tool_name in registry.list_tools():
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"\nTesting {tool_name}:")
            
            # Generate and run tests
            scenarios = generator.generate_test_scenarios(tool, count=3)
            
            for scenario in scenarios:
                try:
                    # Execute test scenario
                    if hasattr(tool, 'execute_async'):
                        # Async tool
                        asyncio.run(tool.execute_async(**scenario.parameters))
                    else:
                        # Sync tool
                        result = tool.execute(**scenario.parameters)
                        
                    print(f"  ✓ {scenario.name}: Passed")
                    
                except Exception as e:
                    print(f"  ✗ {scenario.name}: Failed - {str(e)}")
                    
    # Cleanup
    registry.shutdown()


# Example 8: Performance testing
def demo_performance_testing():
    """Demonstrate performance testing capabilities"""
    print("\n=== Performance Testing Demo ===\n")
    
    class PerformanceTest(ToolTestCase):
        """Performance test for calculator tool"""
        
        def get_tool_name(self) -> str:
            return "calculator_perf"
            
        def create_tool(self) -> BaseTool:
            return CalculatorTool()
            
        def test_performance_benchmark(self):
            """Benchmark tool performance"""
            import time
            
            iterations = 100
            start_time = time.time()
            
            for i in range(iterations):
                self.execute_tool(
                    operation="multiply",
                    a=i,
                    b=i + 1
                )
                
            duration = time.time() - start_time
            avg_time = duration / iterations
            
            print(f"  Average execution time: {avg_time * 1000:.2f}ms")
            print(f"  Operations per second: {iterations / duration:.0f}")
            
            # Assert performance requirements
            self.assertLess(avg_time, 0.01)  # Should be under 10ms
            
    # Run performance test
    runner = ToolTestRunner()
    suite = create_test_suite(PerformanceTest)
    runner.run_suite(suite)


# Main demo function
def main():
    """Run all testing demos"""
    print("=" * 60)
    print("Tool Testing Framework Demo")
    print("=" * 60)
    
    # Run demos
    try:
        # 1. Test generation
        scenarios = demo_test_generation()
        
        # 2. Test execution
        report = demo_test_execution()
        
        # 3. Mock tools
        mock = demo_mock_tool()
        
        # 4. Registry testing
        demo_registry_testing()
        
        # 5. Performance testing
        demo_performance_testing()
        
        # 6. Async tests
        print("\n=== Async Tool Testing ===")
        async_runner = ToolTestRunner()
        async_suite = create_test_suite(AsyncFetcherTests)
        
        # Run async tests
        async def run_async_tests():
            return await async_runner.run_suite_async(async_suite)
            
        async_result = asyncio.run(run_async_tests())
        print(f"Async test results: {async_result.tests_run} tests run")
        
        print("\n" + "=" * 60)
        print("Testing demo completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError in demo: {str(e)}")
        raise


if __name__ == "__main__":
    main()