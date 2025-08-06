"""
Math Tool Example

A comprehensive mathematical operations tool that demonstrates
advanced tool features including parameter validation, progress
reporting, and complex operations.
"""

import math
import logging
from typing import Any, List, Optional, Union
import cmath

from src.tools.base import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolStatus, ToolCategory, ParameterType, ToolProgress
)


logger = logging.getLogger(__name__)


class MathTool(BaseTool):
    """
    Mathematical operations tool
    
    This tool provides various mathematical operations including:
    - Basic arithmetic
    - Trigonometric functions
    - Statistical calculations
    - Complex number operations
    - Matrix operations (basic)
    """
    
    SUPPORTED_OPERATIONS = {
        # Basic arithmetic
        'add': 'Addition',
        'subtract': 'Subtraction',
        'multiply': 'Multiplication',
        'divide': 'Division',
        'power': 'Exponentiation',
        'sqrt': 'Square root',
        'abs': 'Absolute value',
        
        # Trigonometric
        'sin': 'Sine',
        'cos': 'Cosine',
        'tan': 'Tangent',
        'asin': 'Arc sine',
        'acos': 'Arc cosine',
        'atan': 'Arc tangent',
        
        # Statistical
        'mean': 'Mean/Average',
        'median': 'Median',
        'mode': 'Mode',
        'std': 'Standard deviation',
        'variance': 'Variance',
        
        # Complex
        'complex_add': 'Complex addition',
        'complex_multiply': 'Complex multiplication',
        'complex_conjugate': 'Complex conjugate',
        
        # Advanced
        'factorial': 'Factorial',
        'gcd': 'Greatest common divisor',
        'lcm': 'Least common multiple',
        'prime_check': 'Check if prime',
        'prime_factors': 'Prime factorization'
    }
    
    def _create_metadata(self) -> ToolMetadata:
        """Create tool metadata"""
        return ToolMetadata(
            name="math_tool",
            version="2.0.0",
            description="Comprehensive mathematical operations tool",
            author="DinoAir Team",
            category=ToolCategory.ANALYSIS,
            tags=["mathematics", "calculation", "statistics", "complex"],
            documentation_url="https://github.com/dinoair/tools/math",
            license="MIT",
            parameters=[
                ToolParameter(
                    name="operation",
                    type=ParameterType.ENUM,
                    description="Mathematical operation to perform",
                    required=True,
                    enum_values=list(self.SUPPORTED_OPERATIONS.keys()),
                    example="add"
                ),
                ToolParameter(
                    name="operands",
                    type=ParameterType.ARRAY,
                    description="Numeric operands for the operation",
                    required=True,
                    example=[5, 3]
                ),
                ToolParameter(
                    name="precision",
                    type=ParameterType.INTEGER,
                    description="Decimal precision for results",
                    required=False,
                    default=4,
                    min_value=0,
                    max_value=15,
                    example=4
                ),
                ToolParameter(
                    name="angle_unit",
                    type=ParameterType.ENUM,
                    description="Unit for trigonometric operations",
                    required=False,
                    default="radians",
                    enum_values=["radians", "degrees"],
                    example="degrees"
                ),
                ToolParameter(
                    name="allow_complex",
                    type=ParameterType.BOOLEAN,
                    description="Allow complex number results",
                    required=False,
                    default=False,
                    example=True
                ),
                ToolParameter(
                    name="return_steps",
                    type=ParameterType.BOOLEAN,
                    description="Return calculation steps",
                    required=False,
                    default=False,
                    example=True
                )
            ],
            capabilities={
                "async_support": False,
                "streaming": False,
                "cancellable": True,
                "progress_reporting": True,
                "batch_processing": True,
                "caching": True,
                "stateful": False
            },
            examples=[
                {
                    "name": "Basic addition",
                    "description": "Add two numbers",
                    "parameters": {
                        "operation": "add",
                        "operands": [10, 5]
                    },
                    "expected_output": 15
                },
                {
                    "name": "Calculate mean",
                    "description": "Calculate mean of numbers",
                    "parameters": {
                        "operation": "mean",
                        "operands": [2, 4, 6, 8, 10],
                        "precision": 2
                    },
                    "expected_output": 6.00
                },
                {
                    "name": "Trigonometric calculation",
                    "description": "Calculate sine in degrees",
                    "parameters": {
                        "operation": "sin",
                        "operands": [30],
                        "angle_unit": "degrees"
                    },
                    "expected_output": 0.5
                }
            ]
        )
    
    def initialize(self):
        """Initialize the tool"""
        logger.info("MathTool initialized")
        self._calculation_cache = {}
        self._operation_count = 0
        
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute mathematical operation
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            ToolResult with calculation result
        """
        try:
            # Extract parameters
            operation = kwargs.get('operation')
            operands = kwargs.get('operands', [])
            precision = kwargs.get('precision', 4)
            angle_unit = kwargs.get('angle_unit', 'radians')
            allow_complex = kwargs.get('allow_complex', False)
            return_steps = kwargs.get('return_steps', False)
            
            # Report progress
            self._report_progress(ToolProgress(
                percentage=0,
                message=f"Starting {operation} operation",
                current_step="validation"
            ))
            
            # Validate operation
            if operation not in self.SUPPORTED_OPERATIONS:
                return ToolResult(
                    success=False,
                    errors=[f"Unsupported operation: {operation}"],
                    status=ToolStatus.FAILED
                )
            
            # Validate operands
            validation_error = self._validate_operands(operation, operands)
            if validation_error:
                return ToolResult(
                    success=False,
                    errors=[validation_error],
                    status=ToolStatus.FAILED
                )
            
            # Check cache
            cache_key = f"{operation}:{operands}:{precision}:{angle_unit}"
            if cache_key in self._calculation_cache:
                logger.debug(f"Using cached result for {cache_key}")
                cached_result = self._calculation_cache[cache_key]
                return ToolResult(
                    success=True,
                    output=cached_result['result'],
                    metadata={
                        **cached_result['metadata'],
                        'cached': True
                    }
                )
            
            # Report calculation progress
            self._report_progress(ToolProgress(
                percentage=50,
                message=f"Performing {self.SUPPORTED_OPERATIONS[operation]}",
                current_step="calculation"
            ))
            
            # Perform calculation
            steps = []
            result = self._perform_operation(
                operation, operands, angle_unit, allow_complex, steps
            )
            
            # Format result
            if isinstance(result, complex):
                if not allow_complex:
                    return ToolResult(
                        success=False,
                        errors=["Complex result not allowed"],
                        warnings=[
                            "Enable allow_complex parameter for "
                            "complex results"
                        ],
                        status=ToolStatus.FAILED
                    )
                formatted_result = self._format_complex(result, precision)
            elif isinstance(result, (int, float)):
                formatted_result = round(result, precision)
            elif isinstance(result, bool):
                formatted_result = result
            elif isinstance(result, list):
                # For lists (mode, prime factors)
                formatted_result = result
            else:
                formatted_result = result
            
            # Build metadata
            metadata = {
                'operation': operation,
                'operation_description': self.SUPPORTED_OPERATIONS[operation],
                'operands': operands,
                'precision': precision,
                'angle_unit': angle_unit,
                'operation_count': self._operation_count + 1
            }
            
            if return_steps and steps:
                metadata['calculation_steps'] = steps
            
            # Cache result
            self._calculation_cache[cache_key] = {
                'result': formatted_result,
                'metadata': metadata
            }
            
            # Update operation count
            self._operation_count += 1
            
            # Report completion
            self._report_progress(ToolProgress(
                percentage=100,
                message="Calculation complete",
                current_step="complete"
            ))
            
            return ToolResult(
                success=True,
                output=formatted_result,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Math operation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
    
    def _validate_operands(
        self, operation: str, operands: List[Any]
    ) -> Optional[str]:
        """Validate operands for operation"""
        # Check if operands are numeric
        for op in operands:
            if not isinstance(op, (int, float, complex)):
                return f"Non-numeric operand: {op}"
        
        # Operation-specific validation
        if operation in ['add', 'subtract', 'multiply', 'complex_add',
                         'complex_multiply', 'gcd', 'lcm']:
            if len(operands) < 2:
                return f"Operation {operation} requires at least 2 operands"
                
        elif operation in ['divide', 'power']:
            if len(operands) != 2:
                return f"Operation {operation} requires exactly 2 operands"
            if operation == 'divide' and operands[1] == 0:
                return "Division by zero"
                
        elif operation in ['sqrt', 'abs', 'sin', 'cos', 'tan', 'asin',
                           'acos', 'atan', 'factorial', 'prime_check',
                           'prime_factors', 'complex_conjugate']:
            if len(operands) != 1:
                return f"Operation {operation} requires exactly 1 operand"
                
        elif operation in ['mean', 'median', 'std', 'variance']:
            if len(operands) < 1:
                return f"Statistical operation {operation} requires data"
                
        elif operation == 'mode':
            if len(operands) < 2:
                return "Mode requires at least 2 values"
        
        # Special validations
        if operation == 'factorial':
            if operands[0] < 0 or operands[0] != int(operands[0]):
                return "Factorial requires non-negative integer"
                
        if operation in ['asin', 'acos']:
            if abs(operands[0]) > 1:
                return f"{operation} requires value in [-1, 1]"
                
        if operation in ['prime_check', 'prime_factors']:
            if operands[0] <= 1 or operands[0] != int(operands[0]):
                return f"{operation} requires integer > 1"
        
        return None
    
    def _perform_operation(
        self,
        operation: str,
        operands: List[Union[int, float, complex]],
        angle_unit: str,
        allow_complex: bool,
        steps: List[str]
    ) -> Any:
        """Perform the mathematical operation"""
        # Convert angles if needed
        if operation in ['sin', 'cos', 'tan'] and angle_unit == 'degrees':
            # Only convert real numbers for trig operations
            operands = [math.radians(float(op.real)) if isinstance(op, complex)
                        else math.radians(op) for op in operands]
            steps.append("Converted angles to radians")
        
        # Basic arithmetic
        if operation == 'add':
            result = sum(operands)
            steps.append(f"Sum: {' + '.join(map(str, operands))} = {result}")
            
        elif operation == 'subtract':
            result = operands[0]
            for op in operands[1:]:
                result -= op
            steps.append(
                f"Subtraction: {' - '.join(map(str, operands))} = {result}"
            )
            
        elif operation == 'multiply':
            result = 1
            for op in operands:
                result *= op
            steps.append(
                f"Product: {' × '.join(map(str, operands))} = {result}"
            )
            
        elif operation == 'divide':
            result = operands[0] / operands[1]
            steps.append(f"Division: {operands[0]} ÷ {operands[1]} = {result}")
            
        elif operation == 'power':
            result = operands[0] ** operands[1]
            steps.append(f"Power: {operands[0]} ^ {operands[1]} = {result}")
            
        elif operation == 'sqrt':
            op = operands[0]
            if isinstance(op, complex) or (op < 0 and allow_complex):
                result = cmath.sqrt(op)
            else:
                result = math.sqrt(float(op))
            steps.append(f"Square root: √{operands[0]} = {result}")
            
        elif operation == 'abs':
            result = abs(operands[0])
            steps.append(f"Absolute value: |{operands[0]}| = {result}")
            
        # Trigonometric
        elif operation == 'sin':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.sin(op)
        elif operation == 'cos':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.cos(op)
        elif operation == 'tan':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.tan(op)
        elif operation == 'asin':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.asin(op)
            if angle_unit == 'degrees':
                result = math.degrees(result)
        elif operation == 'acos':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.acos(op)
            if angle_unit == 'degrees':
                result = math.degrees(result)
        elif operation == 'atan':
            op = (operands[0].real if isinstance(operands[0], complex)
                  else operands[0])
            result = math.atan(op)
            if angle_unit == 'degrees':
                result = math.degrees(result)
                
        # Statistical
        elif operation == 'mean':
            result = sum(operands) / len(operands)
            steps.append(f"Mean: {sum(operands)} ÷ {len(operands)} = {result}")
            
        elif operation == 'median':
            # Filter out complex numbers for median
            real_ops = [float(op) for op in operands
                        if not isinstance(op, complex)]
            sorted_ops = sorted(real_ops)
            n = len(sorted_ops)
            if n % 2 == 0:
                result = (sorted_ops[n//2 - 1] + sorted_ops[n//2]) / 2
            else:
                result = sorted_ops[n//2]
            steps.append(f"Median of {sorted_ops} = {result}")
            
        elif operation == 'mode':
            from collections import Counter
            counts = Counter(operands)
            max_count = max(counts.values())
            modes = [k for k, v in counts.items() if v == max_count]
            result = modes[0] if len(modes) == 1 else modes
            steps.append(f"Mode(s): {result}")
            
        elif operation == 'std':
            mean = sum(operands) / len(operands)
            variance = sum((x - mean) ** 2 for x in operands) / len(operands)
            if isinstance(variance, complex):
                result = cmath.sqrt(variance)
            else:
                result = math.sqrt(float(variance))
            steps.append(f"Standard deviation = {result}")
            
        elif operation == 'variance':
            mean = sum(operands) / len(operands)
            result = sum((x - mean) ** 2 for x in operands) / len(operands)
            steps.append(f"Variance = {result}")
            
        # Complex operations
        elif operation == 'complex_add':
            result = sum(complex(op) if not isinstance(op, complex) else op
                         for op in operands)
                        
        elif operation == 'complex_multiply':
            result = complex(1)
            for op in operands:
                result *= complex(op) if not isinstance(op, complex) else op
                
        elif operation == 'complex_conjugate':
            op = (complex(operands[0])
                  if not isinstance(operands[0], complex)
                  else operands[0])
            result = op.conjugate()
            
        # Advanced operations
        elif operation == 'factorial':
            try:
                n_float = float(operands[0].real if isinstance(operands[0], complex)
                              else operands[0])
                if not math.isfinite(n_float) or n_float < 0 or n_float > 1000:
                    raise ValueError("Invalid factorial input")
                n = int(n_float)
                result = math.factorial(n)
            except (ValueError, OverflowError) as e:
                raise ValueError(f"Factorial error: {e}")
            steps.append(f"{n}! = {result}")
            
        elif operation == 'gcd':
            from math import gcd
            int_ops = []
            for op in operands:
                val = float(op.real if isinstance(op, complex) else op)
                if not math.isfinite(val):
                    raise ValueError("GCD requires finite numbers")
                int_ops.append(int(val))
            result = int_ops[0]
            for op in int_ops[1:]:
                result = gcd(result, op)
            steps.append(f"GCD of {int_ops} = {result}")
            
        elif operation == 'lcm':
            from math import gcd
            
            def lcm(a, b):
                return abs(a * b) // gcd(a, b)
            
            int_ops = []
            for op in operands:
                val = float(op.real if isinstance(op, complex) else op)
                if not math.isfinite(val):
                    raise ValueError("LCM requires finite numbers")
                int_ops.append(int(val))
            result = int_ops[0]
            for op in int_ops[1:]:
                result = lcm(result, op)
            steps.append(f"LCM of {int_ops} = {result}")
            
        elif operation == 'prime_check':
            val = float(operands[0].real if isinstance(operands[0], complex)
                        else operands[0])
            if not math.isfinite(val) or val < 0:
                raise ValueError("Prime check requires finite positive numbers")
            n = int(val)
            result = self._is_prime(n)
            steps.append(f"{n} is {'prime' if result else 'not prime'}")
            
        elif operation == 'prime_factors':
            val = float(operands[0].real if isinstance(operands[0], complex)
                        else operands[0])
            if not math.isfinite(val) or val < 2:
                raise ValueError("Prime factorization requires finite numbers >= 2")
            n = int(val)
            result = self._prime_factors(n)
            steps.append(f"Prime factors of {n}: {result}")
            
        else:
            raise ValueError(f"Unknown operation: {operation}")
            
        return result
    
    def _is_prime(self, n: int) -> bool:
        """Check if number is prime"""
        if n < 2:
            return False
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0:
                return False
        return True
    
    def _prime_factors(self, n: int) -> List[int]:
        """Get prime factors of a number"""
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        return factors
    
    def _format_complex(self, c: complex, precision: int) -> str:
        """Format complex number"""
        real = round(c.real, precision)
        imag = round(c.imag, precision)
        
        if imag == 0:
            return str(real)
        elif real == 0:
            return f"{imag}j"
        elif imag > 0:
            return f"{real}+{imag}j"
        else:
            return f"{real}{imag}j"
    
    def shutdown(self):
        """Cleanup resources"""
        logger.info(
            f"MathTool shutting down. "
            f"Performed {self._operation_count} operations"
        )
        self._calculation_cache.clear()