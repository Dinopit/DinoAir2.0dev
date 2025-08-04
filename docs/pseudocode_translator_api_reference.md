# Pseudocode Translator API Reference

## Table of Contents
1. [Overview](#overview)
2. [High-Level API](#high-level-api)
3. [Low-Level API](#low-level-api)
4. [Agent and Tool Interfaces](#agent-and-tool-interfaces)
5. [Event System](#event-system)
6. [Plugin Development](#plugin-development)
7. [Type Definitions](#type-definitions)
8. [Exceptions](#exceptions)
9. [Utilities](#utilities)

## Overview

The Pseudocode Translator provides multiple API levels:
- **High-Level API**: Simple, user-friendly interface via `SimpleTranslator`
- **Low-Level API**: Advanced control via `TranslationManager`
- **Agent API**: Integration with AI agents and tools
- **Plugin API**: Extensibility for custom models and validators

## High-Level API

### SimpleTranslator

The main entry point for most users.

```python
from pseudocode_translator import SimpleTranslator
```

#### Constructor

```python
SimpleTranslator(
    config_path: Optional[str] = None,
    profile: Optional[str] = None,
    model: Optional[str] = None,
    enable_cache: bool = True,
    enable_streaming: bool = False,
    debug: bool = False,
    **kwargs
)
```

**Parameters:**
- `config_path`: Path to configuration file
- `profile`: Pre-configured profile name ("minimal", "production", "educational")
- `model`: Model identifier (e.g., "gpt-4", "claude-3")
- `enable_cache`: Enable AST caching
- `enable_streaming`: Enable streaming output
- `debug`: Enable debug logging
- `**kwargs`: Additional configuration options

**Example:**
```python
# Basic usage
translator = SimpleTranslator()

# With configuration
translator = SimpleTranslator(
    profile="production",
    enable_streaming=True,
    timeout=60
)
```

#### Methods

##### translate()
```python
def translate(
    self,
    pseudocode: str,
    target_language: str = "python",
    options: Optional[Dict[str, Any]] = None
) -> TranslationResult
```

Translate pseudocode to target language.

**Parameters:**
- `pseudocode`: Input pseudocode text
- `target_language`: Target programming language
- `options`: Language-specific options

**Returns:** `TranslationResult` object

**Example:**
```python
result = translator.translate(
    "PRINT 'Hello World'",
    target_language="javascript",
    options={"use_semicolons": True}
)
print(result.code)
```

##### translate_stream()
```python
def translate_stream(
    self,
    pseudocode: str,
    target_language: str = "python",
    options: Optional[Dict[str, Any]] = None
) -> Iterator[StreamChunk]
```

Stream translation output.

**Parameters:** Same as `translate()`

**Yields:** `StreamChunk` objects with content and metadata

**Example:**
```python
for chunk in translator.translate_stream(pseudocode):
    print(chunk.content, end='')
    if chunk.metadata.get('progress'):
        update_progress_bar(chunk.metadata['progress'])
```

##### translate_file()
```python
def translate_file(
    self,
    input_path: str,
    output_path: Optional[str] = None,
    target_language: str = "python",
    options: Optional[Dict[str, Any]] = None
) -> TranslationResult
```

Translate a file.

**Parameters:**
- `input_path`: Path to input pseudocode file
- `output_path`: Path for output (auto-generated if None)
- `target_language`: Target programming language
- `options`: Language-specific options

**Example:**
```python
result = translator.translate_file(
    "algorithm.pseudo",
    output_path="algorithm.py"
)
```

##### validate()
```python
def validate(
    self,
    pseudocode: str
) -> ValidationResult
```

Validate pseudocode syntax.

**Returns:** `ValidationResult` with errors and warnings

**Example:**
```python
validation = translator.validate(pseudocode)
if validation.is_valid:
    result = translator.translate(pseudocode)
else:
    for error in validation.errors:
        print(f"Error at line {error.line}: {error.message}")
```

##### set_model()
```python
def set_model(
    self,
    model: str,
    **kwargs
) -> None
```

Change the active model.

**Example:**
```python
translator.set_model("gpt-3.5-turbo", temperature=0.5)
```

## Low-Level API

### TranslationManager

Advanced API for fine-grained control.

```python
from pseudocode_translator.core import TranslationManager
```

#### Constructor

```python
TranslationManager(
    parser: Optional[Parser] = None,
    validator: Optional[Validator] = None,
    assembler: Optional[Assembler] = None,
    cache: Optional[ASTCache] = None,
    event_emitter: Optional[EventEmitter] = None
)
```

**Parameters:**
- `parser`: Custom parser instance
- `validator`: Custom validator instance
- `assembler`: Custom assembler instance
- `cache`: Custom cache instance
- `event_emitter`: Event emitter for callbacks

#### Methods

##### parse()
```python
def parse(
    self,
    pseudocode: str,
    source_file: Optional[str] = None
) -> AST
```

Parse pseudocode into AST.

**Example:**
```python
manager = TranslationManager()
ast = manager.parse(pseudocode)
print(ast.root.type)  # "program"
```

##### validate_ast()
```python
def validate_ast(
    self,
    ast: AST,
    context: Optional[ValidationContext] = None
) -> List[ValidationError]
```

Validate an AST.

**Example:**
```python
errors = manager.validate_ast(ast)
if not errors:
    code = manager.assemble(ast, "python")
```

##### assemble()
```python
def assemble(
    self,
    ast: AST,
    target_language: str,
    options: Optional[Dict[str, Any]] = None
) -> str
```

Generate code from AST.

**Example:**
```python
ast = manager.parse(pseudocode)
python_code = manager.assemble(ast, "python")
js_code = manager.assemble(ast, "javascript")
```

##### translate_with_pipeline()
```python
def translate_with_pipeline(
    self,
    pseudocode: str,
    pipeline: List[TransformStep],
    target_language: str
) -> TranslationResult
```

Use custom transformation pipeline.

**Example:**
```python
from pseudocode_translator.transforms import OptimizeLoops, AddTypeHints

pipeline = [
    OptimizeLoops(),
    AddTypeHints(),
]

result = manager.translate_with_pipeline(
    pseudocode,
    pipeline,
    "python"
)
```

### Parser

Low-level parsing interface.

```python
from pseudocode_translator.parser import Parser

parser = Parser()
ast = parser.parse(pseudocode)

# Access AST nodes
for node in ast.walk():
    if node.type == "function":
        print(f"Function: {node.name}")
```

### Validator

Low-level validation interface.

```python
from pseudocode_translator.validator import Validator

validator = Validator()
errors = validator.validate(pseudocode)

# Custom validation rules
validator.add_rule(
    "no_goto",
    lambda node: node.type != "goto",
    "GOTO statements are not allowed"
)
```

### Assembler

Low-level code generation interface.

```python
from pseudocode_translator.assembler import Assembler

assembler = Assembler()
code = assembler.generate(ast, "python", {
    "indent_size": 4,
    "use_type_hints": True
})
```

## Agent and Tool Interfaces

### PseudocodeAgent

Integration with AI agents.

```python
from pseudocode_translator.agents import PseudocodeAgent
```

#### Methods

##### process_request()
```python
async def process_request(
    self,
    request: AgentRequest
) -> AgentResponse
```

Process agent requests.

**Example:**
```python
agent = PseudocodeAgent()

request = AgentRequest(
    action="translate",
    pseudocode="PRINT 'Hello'",
    target_language="python",
    context={"user_id": "123"}
)

response = await agent.process_request(request)
print(response.result)
```

### ToolInterface

Integration with external tools.

```python
from pseudocode_translator.tools import PseudocodeTool
```

#### Usage with LangChain
```python
from langchain.tools import Tool

tool = Tool(
    name="pseudocode_translator",
    func=PseudocodeTool().run,
    description="Translate pseudocode to programming languages"
)
```

#### Direct Usage
```python
from pseudocode_translator.tools import translate_with_tool

result = translate_with_tool(
    pseudocode="FUNCTION add(a, b): RETURN a + b",
    language="javascript"
)
```

## Event System

### EventEmitter

Subscribe to translation lifecycle events.

```python
from pseudocode_translator.events import EventEmitter
```

#### Available Events

- `parse_start`: Parsing started
- `parse_complete`: Parsing completed
- `parse_error`: Parsing error occurred
- `validate_start`: Validation started
- `validate_complete`: Validation completed
- `validate_error`: Validation error found
- `translate_start`: Translation started
- `translate_progress`: Translation progress update
- `translate_complete`: Translation completed
- `cache_hit`: Cache hit occurred
- `cache_miss`: Cache miss occurred

#### Event Handlers

```python
translator = SimpleTranslator()

# Add event listener
@translator.on("translate_progress")
def on_progress(data):
    print(f"Progress: {data['progress']}%")

@translator.on("validate_error")
def on_error(data):
    print(f"Validation error: {data['error']}")

# Remove listener
translator.off("translate_progress", on_progress)
```

#### Custom Events

```python
# Emit custom events
translator.emit("custom_event", {"data": "value"})

# Listen for custom events
@translator.on("custom_event")
def handle_custom(data):
    print(f"Custom event: {data}")
```

## Plugin Development

### Creating a Custom Model

```python
from pseudocode_translator.models import BaseModel
from typing import Dict, Any, List

class CustomModel(BaseModel):
    """Custom translation model."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model_name", "custom")
    
    def translate(
        self,
        ast: AST,
        target_language: str,
        options: Dict[str, Any]
    ) -> str:
        """Translate AST to target language."""
        # Custom translation logic
        if target_language == "python":
            return self._translate_to_python(ast, options)
        else:
            raise NotImplementedError(f"Language {target_language} not supported")
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return model capabilities."""
        return {
            "languages": ["python", "javascript"],
            "features": ["functions", "classes", "async"],
            "max_tokens": 4096
        }
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate model configuration."""
        errors = []
        if "api_key" not in config:
            errors.append("API key required")
        return errors
```

### Registering a Plugin

```python
from pseudocode_translator.plugins import PluginRegistry

# Register the plugin
registry = PluginRegistry()
registry.register_model("custom", CustomModel)

# Use the plugin
translator = SimpleTranslator(model="custom")
```

### Creating a Custom Validator

```python
from pseudocode_translator.validator import BaseValidator

class SecurityValidator(BaseValidator):
    """Validate for security issues."""
    
    def validate(self, ast: AST) -> List[ValidationError]:
        errors = []
        
        for node in ast.walk():
            if node.type == "file_operation":
                if self._is_dangerous_path(node.path):
                    errors.append(ValidationError(
                        message="Dangerous file path detected",
                        line=node.line,
                        severity="error",
                        suggestion="Use relative paths only"
                    ))
        
        return errors
    
    def _is_dangerous_path(self, path: str) -> bool:
        return path.startswith("/") or ".." in path
```

### Creating a Custom Transform

```python
from pseudocode_translator.transforms import BaseTransform

class OptimizationTransform(BaseTransform):
    """Optimize AST for performance."""
    
    def transform(self, ast: AST) -> AST:
        # Clone AST to avoid modifying original
        new_ast = ast.clone()
        
        # Optimize constant expressions
        for node in new_ast.walk():
            if node.type == "binary_op" and self._are_constants(node):
                node.replace_with(self._evaluate_constant(node))
        
        return new_ast
```

## Type Definitions

### TranslationResult

```python
@dataclass
class TranslationResult:
    code: str                          # Generated code
    language: str                      # Target language
    metadata: Dict[str, Any]          # Additional metadata
    warnings: List[str]               # Non-fatal warnings
    performance: PerformanceMetrics   # Performance data
    ast: Optional[AST]                # Parsed AST (if debug=True)
```

### StreamChunk

```python
@dataclass
class StreamChunk:
    content: str                      # Chunk content
    metadata: Dict[str, Any]         # Chunk metadata
    is_final: bool                   # Is this the final chunk?
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool                   # Overall validity
    errors: List[ValidationError]    # List of errors
    warnings: List[ValidationWarning] # List of warnings
    suggestions: List[str]           # Improvement suggestions
```

### AST

```python
class AST:
    root: ASTNode                    # Root node
    source_file: Optional[str]       # Source file path
    metadata: Dict[str, Any]         # AST metadata
    
    def walk(self) -> Iterator[ASTNode]:
        """Walk all nodes."""
    
    def find_nodes(self, node_type: str) -> List[ASTNode]:
        """Find nodes by type."""
    
    def clone(self) -> 'AST':
        """Create deep copy."""
```

### ASTNode

```python
@dataclass
class ASTNode:
    type: str                        # Node type
    value: Any                       # Node value
    children: List['ASTNode']        # Child nodes
    line: int                        # Source line number
    column: int                      # Source column number
    metadata: Dict[str, Any]         # Additional data
```

## Exceptions

### TranslationError

Base exception for all translation errors.

```python
class TranslationError(Exception):
    def __init__(self, message: str, line: Optional[int] = None):
        self.message = message
        self.line = line
        self.suggestion = None
```

### SyntaxError

Raised for pseudocode syntax errors.

```python
class SyntaxError(TranslationError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message, line)
        self.column = column
```

### ValidationError

Raised for validation failures.

```python
class ValidationError(TranslationError):
    def __init__(self, message: str, line: int, severity: str = "error"):
        super().__init__(message, line)
        self.severity = severity
```

### ModelError

Raised for model-related errors.

```python
class ModelError(TranslationError):
    def __init__(self, message: str, model: str):
        super().__init__(message)
        self.model = model
```

## Utilities

### Configuration Helpers

```python
from pseudocode_translator.utils import load_config, merge_configs

# Load configuration
config = load_config("config.yaml")

# Merge configurations
final_config = merge_configs(default_config, user_config)
```

### Code Formatting

```python
from pseudocode_translator.utils import format_code

# Format generated code
formatted = format_code(
    code,
    language="python",
    formatter="black"
)
```

### Testing Utilities

```python
from pseudocode_translator.testing import assert_translation

# Test translation
assert_translation(
    pseudocode="PRINT 'Hello'",
    expected_python="print('Hello')",
    expected_javascript="console.log('Hello');"
)
```

### Performance Monitoring

```python
from pseudocode_translator.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()

with monitor.track("translation"):
    result = translator.translate(pseudocode)

print(monitor.get_metrics())
# {'translation': {'duration': 1.23, 'memory': 45.6}}
```

## Best Practices

### Error Handling

```python
from pseudocode_translator import SimpleTranslator, TranslationError

translator = SimpleTranslator()

try:
    result = translator.translate(pseudocode)
except SyntaxError as e:
    print(f"Syntax error at line {e.line}: {e.message}")
    if e.suggestion:
        print(f"Suggestion: {e.suggestion}")
except ValidationError as e:
    print(f"Validation failed: {e.message}")
except ModelError as e:
    print(f"Model error: {e.message}")
    # Fall back to different model
    translator.set_model("gpt-3.5-turbo")
    result = translator.translate(pseudocode)
except TranslationError as e:
    print(f"Translation failed: {e.message}")
```

### Resource Management

```python
# Use context manager for automatic cleanup
with SimpleTranslator() as translator:
    result = translator.translate(pseudocode)

# Manual resource management
translator = SimpleTranslator()
try:
    result = translator.translate(pseudocode)
finally:
    translator.close()
```

### Async Usage

```python
import asyncio
from pseudocode_translator import AsyncTranslator

async def translate_async():
    async with AsyncTranslator() as translator:
        result = await translator.translate(pseudocode)
        return result

# Run async translation
result = asyncio.run(translate_async())
```

### Batch Processing

```python
from pseudocode_translator import BatchProcessor

processor = BatchProcessor(workers=4)

# Process multiple files
results = processor.process([
    {"file": "algo1.pseudo", "language": "python"},
    {"file": "algo2.pseudo", "language": "javascript"},
    {"file": "algo3.pseudo", "language": "go"},
])

for result in results:
    if result.success:
        print(f"{result.file}: Success")
    else:
        print(f"{result.file}: {result.error}")
```

This API reference provides comprehensive documentation for all levels of the Pseudocode Translator API. For more examples and use cases, see the [Examples](../pseudocode_translator/examples/) directory.