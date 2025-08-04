#!/usr/bin/env python3
"""
Plugin Development Example

This example demonstrates how to create plugins for the Pseudocode Translator,
including custom models, validators, transforms, and language extensions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
import re

from pseudocode_translator.plugins import (
    BasePlugin, PluginRegistry, PluginMetadata
)
from pseudocode_translator import SimpleTranslator


# =============================================================================
# Example 1: Custom Validator Plugin
# =============================================================================

class SecurityValidator(BasePlugin):
    """Validates pseudocode for security vulnerabilities"""
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="security-validator",
            version="1.0.0",
            author="Security Team",
            description="Validates for common security issues",
            plugin_type="validator"
        )
    
    def __init__(self):
        self.dangerous_patterns = [
            (r'eval\s*\(', "Avoid using eval() - security risk"),
            (r'exec\s*\(', "Avoid using exec() - security risk"),
            (r'__import__', "Dynamic imports can be risky"),
            (r'pickle\.loads', "Pickle can execute arbitrary code"),
            (r'subprocess.*shell=True', "Shell injection risk"),
            (r'os\.system', "Command injection risk"),
        ]
    
    def validate(self, pseudocode: str) -> List[Dict[str, Any]]:
        """Check for security issues"""
        issues = []
        
        lines = pseudocode.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, message in self.dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "line": line_num,
                        "severity": "warning",
                        "message": message,
                        "type": "security"
                    })
        
        # Check for hardcoded credentials
        if re.search(r'password\s*=\s*["\'][^"\']+["\']', pseudocode, re.IGNORECASE):
            issues.append({
                "line": 0,
                "severity": "error",
                "message": "Hardcoded password detected",
                "type": "security"
            })
        
        return issues


# =============================================================================
# Example 2: Custom Transform Plugin
# =============================================================================

class PerformanceOptimizer(BasePlugin):
    """Optimizes generated code for performance"""
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="performance-optimizer",
            version="1.0.0",
            author="Performance Team",
            description="Optimizes code for better performance",
            plugin_type="transform"
        )
    
    def transform(self, ast: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize AST for performance"""
        # Example optimizations
        optimized = self._optimize_loops(ast)
        optimized = self._cache_repeated_calculations(optimized)
        optimized = self._use_comprehensions(optimized)
        return optimized
    
    def _optimize_loops(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize loop structures"""
        # Convert appropriate loops to list comprehensions
        # Hoist invariant calculations out of loops
        # Use enumerate instead of range(len())
        return ast
    
    def _cache_repeated_calculations(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Cache repeated expensive calculations"""
        # Identify repeated function calls
        # Add memoization where appropriate
        return ast
    
    def _use_comprehensions(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """Convert loops to comprehensions where appropriate"""
        # Convert simple loops to list/dict comprehensions
        # Use generator expressions for memory efficiency
        return ast


# =============================================================================
# Example 3: Custom Language Extension Plugin
# =============================================================================

@dataclass
class SQLCodeGenerator(BasePlugin):
    """Generates SQL from pseudocode"""
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="sql-generator",
            version="1.0.0",
            author="Database Team",
            description="Generates SQL queries from pseudocode",
            plugin_type="language",
            supported_languages=["sql", "postgresql", "mysql", "sqlite"]
        )
    
    def generate(self, ast: Dict[str, Any], dialect: str = "sql") -> str:
        """Generate SQL from AST"""
        if ast.get("type") == "query":
            return self._generate_query(ast, dialect)
        elif ast.get("type") == "schema":
            return self._generate_schema(ast, dialect)
        else:
            return self._generate_general_sql(ast, dialect)
    
    def _generate_query(self, ast: Dict[str, Any], dialect: str) -> str:
        """Generate SQL query"""
        query_type = ast.get("query_type", "select")
        
        if query_type == "select":
            return self._generate_select(ast, dialect)
        elif query_type == "insert":
            return self._generate_insert(ast, dialect)
        elif query_type == "update":
            return self._generate_update(ast, dialect)
        elif query_type == "delete":
            return self._generate_delete(ast, dialect)
    
    def _generate_select(self, ast: Dict[str, Any], dialect: str) -> str:
        """Generate SELECT query"""
        columns = ast.get("columns", ["*"])
        table = ast.get("table", "table_name")
        conditions = ast.get("conditions", [])
        
        query = f"SELECT {', '.join(columns)}\nFROM {table}"
        
        if conditions:
            query += f"\nWHERE {' AND '.join(conditions)}"
        
        return query + ";"


# =============================================================================
# Example 4: Custom Model Adapter Plugin
# =============================================================================

class LlamaModelAdapter(BasePlugin):
    """Adapter for LLaMA models"""
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="llama-adapter",
            version="1.0.0",
            author="Model Team",
            description="Adapter for LLaMA family models",
            plugin_type="model_adapter",
            model_names=["llama2", "codellama", "llama-7b", "llama-13b"]
        )
    
    def __init__(self, model_path: str, config: Dict[str, Any]):
        self.model_path = model_path
        self.config = config
        # Initialize model here
        # self.model = self._load_model()
    
    def translate(self, prompt: str, **kwargs) -> str:
        """Translate using LLaMA model"""
        # Format prompt for LLaMA
        formatted_prompt = self._format_prompt(prompt)
        
        # Generate with model
        # response = self.model.generate(formatted_prompt, **kwargs)
        
        # Extract code from response
        # code = self._extract_code(response)
        
        # For demo, return mock response
        return f"# LLaMA generated code for:\n# {prompt[:50]}...\n\ndef example():\n    pass"
    
    def _format_prompt(self, prompt: str) -> str:
        """Format prompt for LLaMA models"""
        return f"[INST] Translate this pseudocode to Python:\n{prompt}\n[/INST]"


# =============================================================================
# Example 5: Composite Plugin (Multiple Features)
# =============================================================================

class EnterprisePlugin(BasePlugin):
    """Enterprise features: logging, metrics, compliance"""
    
    @classmethod
    def get_metadata(cls) -> PluginMetadata:
        return PluginMetadata(
            name="enterprise-features",
            version="2.0.0",
            author="Enterprise Team",
            description="Adds enterprise features to generated code",
            plugin_type="composite",
            features=["logging", "metrics", "compliance", "monitoring"]
        )
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enable_logging = config.get("logging", True)
        self.enable_metrics = config.get("metrics", True)
        self.enable_compliance = config.get("compliance", False)
    
    def enhance_code(self, code: str, language: str) -> str:
        """Add enterprise features to generated code"""
        enhanced = code
        
        if self.enable_logging:
            enhanced = self._add_logging(enhanced, language)
        
        if self.enable_metrics:
            enhanced = self._add_metrics(enhanced, language)
        
        if self.enable_compliance:
            enhanced = self._add_compliance_checks(enhanced, language)
        
        return enhanced
    
    def _add_logging(self, code: str, language: str) -> str:
        """Add logging statements"""
        if language == "python":
            header = "import logging\n\nlogger = logging.getLogger(__name__)\n\n"
            # Add logging to functions
            code = re.sub(
                r'def (\w+)\((.*?)\):',
                r'def \1(\2):\n    logger.debug(f"Calling \1 with args: {\2}")',
                code
            )
            return header + code
        return code
    
    def _add_metrics(self, code: str, language: str) -> str:
        """Add performance metrics"""
        if language == "python":
            header = "import time\nfrom functools import wraps\n\n"
            decorator = """
def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper

"""
            # Add decorator to functions
            code = re.sub(
                r'def (\w+)',
                r'@measure_time\ndef \1',
                code
            )
            return header + decorator + code
        return code
    
    def _add_compliance_checks(self, code: str, language: str) -> str:
        """Add compliance and audit checks"""
        # Add data validation
        # Add audit logging
        # Add access control checks
        return code


# =============================================================================
# Plugin Registration and Usage Examples
# =============================================================================

def example_1_register_and_use_plugins():
    """Example 1: Register and use custom plugins"""
    print("\n=== Example 1: Plugin Registration ===")
    
    # Create plugin registry
    registry = PluginRegistry()
    
    # Register plugins
    registry.register("validator", SecurityValidator)
    registry.register("transform", PerformanceOptimizer)
    registry.register("language", SQLCodeGenerator)
    registry.register("model", LlamaModelAdapter)
    registry.register("composite", EnterprisePlugin)
    
    print("Registered plugins:")
    for plugin_type, plugins in registry.list_plugins().items():
        print(f"\n{plugin_type}:")
        for plugin in plugins:
            metadata = plugin.get_metadata()
            print(f"  - {metadata.name} v{metadata.version}: {metadata.description}")


def example_2_use_security_validator():
    """Example 2: Use security validator plugin"""
    print("\n=== Example 2: Security Validator ===")
    
    validator = SecurityValidator()
    
    # Test with insecure pseudocode
    insecure_code = """
    FUNCTION process_user_input(input)
        # Dangerous: using eval
        SET result TO eval(input)
        
        # Hardcoded password
        SET password TO "admin123"
        
        # Command injection risk
        EXECUTE os.system("rm -rf " + input)
        
        RETURN result
    END FUNCTION
    """
    
    issues = validator.validate(insecure_code)
    
    print("Security issues found:")
    for issue in issues:
        print(f"Line {issue['line']}: {issue['severity'].upper()} - {issue['message']}")


def example_3_use_performance_optimizer():
    """Example 3: Use performance optimizer"""
    print("\n=== Example 3: Performance Optimizer ===")
    
    # Create translator with optimizer plugin
    translator = SimpleTranslator()
    optimizer = PerformanceOptimizer()
    
    pseudocode = """
    FUNCTION process_data(numbers)
        SET result TO empty list
        
        # Inefficient: multiple passes through data
        FOR EACH num IN numbers
            IF num > 0 THEN
                APPEND num * 2 TO result
            END IF
        END FOR
        
        # Inefficient: repeated calculation
        FOR i FROM 0 TO length(numbers)
            SET value TO expensive_calculation(i)
            PRINT value
            SET another TO expensive_calculation(i)
            PRINT another
        END FOR
        
        RETURN result
    END FUNCTION
    """
    
    print("Original pseudocode:")
    print(pseudocode)
    
    # Translate with optimization
    result = translator.translate(
        pseudocode,
        plugins=[optimizer]
    )
    
    print("\nOptimized code:")
    print(result.code)


def example_4_create_sql_queries():
    """Example 4: Generate SQL using custom language plugin"""
    print("\n=== Example 4: SQL Generation ===")
    
    sql_generator = SQLCodeGenerator()
    
    # Example AST for a SELECT query
    select_ast = {
        "type": "query",
        "query_type": "select",
        "columns": ["id", "name", "email"],
        "table": "users",
        "conditions": ["active = true", "created_at > '2024-01-01'"]
    }
    
    sql = sql_generator.generate(select_ast, dialect="postgresql")
    print("Generated SQL:")
    print(sql)


def example_5_enterprise_features():
    """Example 5: Add enterprise features to code"""
    print("\n=== Example 5: Enterprise Features ===")
    
    enterprise = EnterprisePlugin({
        "logging": True,
        "metrics": True,
        "compliance": True
    })
    
    original_code = """
def calculate_discount(price, customer_type):
    if customer_type == "premium":
        return price * 0.8
    elif customer_type == "regular":
        return price * 0.9
    else:
        return price

def process_order(items, customer):
    total = sum(item.price for item in items)
    discount = calculate_discount(total, customer.type)
    return discount
"""
    
    enhanced = enterprise.enhance_code(original_code, "python")
    
    print("Enhanced code with enterprise features:")
    print(enhanced)


def example_6_plugin_chaining():
    """Example 6: Chain multiple plugins together"""
    print("\n=== Example 6: Plugin Chaining ===")
    
    # Create a translation pipeline with multiple plugins
    translator = SimpleTranslator()
    
    # Configure plugin chain
    plugin_chain = [
        SecurityValidator(),        # First, validate security
        PerformanceOptimizer(),    # Then optimize performance
        EnterprisePlugin({         # Finally add enterprise features
            "logging": True,
            "metrics": True
        })
    ]
    
    pseudocode = """
    CREATE a PaymentProcessor class with:
        METHOD process_payment(amount, card_number)
            # Validate amount
            IF amount <= 0 THEN
                RAISE ValueError("Invalid amount")
            END IF
            
            # Process payment (simplified)
            SET transaction_id TO generate_id()
            
            # Log transaction
            SAVE transaction_id, amount TO database
            
            RETURN transaction_id
        END METHOD
        
        METHOD refund_payment(transaction_id, amount)
            # Validate transaction exists
            SET transaction TO get_transaction(transaction_id)
            IF transaction IS None THEN
                RAISE ValueError("Transaction not found")
            END IF
            
            # Process refund
            SET refund_id TO generate_id()
            UPDATE transaction WITH refund_id, amount
            
            RETURN refund_id
        END METHOD
    END CLASS
    """
    
    print("Processing with plugin chain:")
    for plugin in plugin_chain:
        print(f"  - {plugin.get_metadata().name}")
    
    # Translate with all plugins
    result = translator.translate(
        pseudocode,
        plugins=plugin_chain
    )
    
    print("\nFinal result with all plugins applied:")
    print(result.code)


def main():
    """Run all plugin development examples"""
    print("Pseudocode Translator - Plugin Development Examples")
    print("=" * 60)
    
    examples = [
        example_1_register_and_use_plugins,
        example_2_use_security_validator,
        example_3_use_performance_optimizer,
        example_4_create_sql_queries,
        example_5_enterprise_features,
        example_6_plugin_chaining
    ]
    
    for example in examples:
        try:
            example()
            print("\n" + "-" * 60)
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")
    
    print("\nPlugin development examples completed!")
    print("\nKey takeaways:")
    print("- Plugins extend translator functionality")
    print("- Multiple plugin types: validators, transforms, languages, models")
    print("- Plugins can be chained for complex workflows")
    print("- Enterprise features can be added via plugins")
    print("- Custom language support through language plugins")


if __name__ == "__main__":
    main()