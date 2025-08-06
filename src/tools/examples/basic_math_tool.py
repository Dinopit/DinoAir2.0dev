"""
Basic Math Tool - Simple mathematical operations

This tool provides basic arithmetic operations like addition, subtraction,
multiplication, and division for AI-assisted tasks.
"""

import logging
from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType
)

logger = logging.getLogger(__name__)


class BasicMathTool(BaseTool):
    """
    Basic mathematical operations tool
    
    This tool provides simple arithmetic operations including:
    - Addition
    - Subtraction  
    - Multiplication
    - Division
    """
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="basic_math_tool",
            version="1.0.0",
            description="Basic mathematical operations",
            author="DinoAir Team",
            category=ToolCategory.UTILITY,
            tags=["math", "arithmetic", "calculator"],
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.ENUM,
                    description="Mathematical operation to perform",
                    required=True,
                    enum_values=["add", "subtract", "multiply", "divide"],
                    example="add"
                ),
                ToolParameter(
                    name="a",
                    type=ParameterType.FLOAT,
                    description="First number",
                    required=True,
                    example=10.5
                ),
                ToolParameter(
                    name="b",
                    type=ParameterType.FLOAT,
                    description="Second number",
                    required=True,
                    example=5.2
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": False,
                "progress_reporting": False,
                "batch_processing": False,
                "caching": True,
                "stateful": False
            },
            examples=[
                {
                    "name": "Addition",
                    "description": "Add two numbers",
                    "parameters": {
                        "operation": "add",
                        "a": 10,
                        "b": 5
                    },
                    "expected_output": 15
                },
                {
                    "name": "Division",
                    "description": "Divide two numbers",
                    "parameters": {
                        "operation": "divide",
                        "a": 20,
                        "b": 4
                    },
                    "expected_output": 5.0
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("BasicMathTool initialized")
        self._operation_count = 0
        
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute mathematical operation
        
        Args:
            operation: Operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number
            
        Returns:
            ToolResult with calculation result
        """
        try:
            operation = kwargs.get('operation')
            a = float(kwargs.get('a', 0))
            b = float(kwargs.get('b', 0))
            
            # Validate operation
            if operation not in ['add', 'subtract', 'multiply', 'divide']:
                return ToolResult(
                    success=False,
                    errors=[f"Unsupported operation: {operation}"],
                    status=ToolStatus.FAILED
                )
            
            # Perform calculation
            result = 0.0
            if operation == 'add':
                result = a + b
            elif operation == 'subtract':
                result = a - b
            elif operation == 'multiply':
                result = a * b
            elif operation == 'divide':
                if b == 0:
                    return ToolResult(
                        success=False,
                        errors=["Division by zero"],
                        status=ToolStatus.FAILED
                    )
                result = a / b
            
            self._operation_count += 1
            
            return ToolResult(
                success=True,
                output=result,
                metadata={
                    'operation': operation,
                    'operand_a': a,
                    'operand_b': b,
                    'operation_count': self._operation_count
                }
            )
            
        except Exception as e:
            logger.error(f"Math operation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def shutdown(self):
        """Cleanup tool resources"""
        logger.info(
            f"BasicMathTool shutting down. "
            f"Performed {self._operation_count} operations"
        )