# API Reference

This document provides a complete reference for developers using the Pseudocode Translator as a Python library.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Core API](#core-api)
   - [PseudocodeTranslatorAPI](#pseudocodetranslatorapi)
   - [TranslationResult](#translationresult)
   - [TranslationStatus](#translationstatus)
4. [Configuration](#configuration)
   - [TranslatorConfig](#translatorconfig)
   - [LLMConfig](#llmconfig)
   - [StreamingConfig](#streamingconfig)
5. [Parser Module](#parser-module)
6. [Model Management](#model-management)
7. [Validation](#validation)
8. [Streaming API](#streaming-api)
9. [GUI Integration](#gui-integration)
10. [Events and Signals](#events-and-signals)
11. [Exceptions](#exceptions)
12. [Examples](#examples)
13. [Best Practices](#best-practices)

## Installation

```bash
pip install pseudocode-translator
```

For development:
```bash
pip install pseudocode-translator[dev]
```

## Quick Start

```python
from pseudocode_translator import PseudocodeTranslatorAPI

# Initialize
translator = PseudocodeTranslatorAPI()

# Translate
result = translator.translate("create a function that adds two numbers")
print(result.code)
```

## Core API

### PseudocodeTranslatorAPI

Main API class for translating pseudocode to Python.

```python
class PseudocodeTranslatorAPI(QObject):
    def __init__(self, config_path: Optional[str] = None, parent: Optional[QObject] = None)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_ready` | `bool` | Whether the translator is ready to process |
| `is_translating` | `bool` | Whether a translation is in progress |

#### Methods

##### translate(pseudocode: str) -> TranslationResult

Synchronous translation method.

```python
result = translator.translate("""
    create a function called fibonacci that:
    - takes n as parameter
    - returns the nth fibonacci number
""")

if result.success:
    print(result.code)
else:
    print(f"Errors: {result.errors}")
```

**Parameters:**
- `pseudocode` (str): Mixed English/Python pseudocode input

**Returns:**
- `TranslationResult`: Object containing translation results

**Raises:**
- `RuntimeError`: If model initialization fails

##### translate_async(pseudocode: str)

Asynchronous translation using Qt signals.

```python
# Connect signals
translator.translation_completed.connect(on_complete)
translator.translation_error.connect(on_error)
translator.translation_progress.connect(on_progress)

# Start translation
translator.translate_async("create a hello world function")
```

**Parameters:**
- `pseudocode` (str): Mixed English/Python pseudocode input

**Emits:**
- `translation_started`: When translation begins
- `translation_progress(int)`: Progress percentage (0-100)
- `translation_status(TranslationStatus)`: Detailed status updates
- `translation_completed(TranslationResult)`: Final result
- `translation_error(str)`: On error

##### translate_streaming(pseudocode: str) -> Iterator[TranslationResult]

Memory-efficient streaming translation for large files.

```python
for chunk_result in translator.translate_streaming(large_pseudocode):
    print(f"Chunk {chunk_result.metadata['chunk_index']}: {chunk_result.code}")
```

**Parameters:**
- `pseudocode` (str): Large pseudocode content
- `chunk_size` (int, optional): Size of chunks (default: 4096)
- `progress_callback` (callable, optional): Progress callback

**Yields:**
- `TranslationResult`: Results for each chunk

##### switch_model(model_name: str)

Switch to a different language model.

```python
translator.switch_model("gpt2")  # Switch to GPT-2
translator.switch_model("codegen")  # Switch to CodeGen
```

**Parameters:**
- `model_name` (str): Name of model to switch to

**Available Models:**
- `qwen`: Default, best for general use
- `gpt2`: Faster, good for simple tasks
- `codegen`: Best for complex algorithms

##### cancel_translation()

Cancel the current translation operation.

```python
translator.cancel_translation()
```

##### get_model_status() -> Dict[str, Any]

Get current model status and health information.

```python
status = translator.get_model_status()
print(f"Model: {status['model_name']}")
print(f"Status: {status['status']}")
print(f"Memory: {status['memory_usage_mb']}MB")
```

**Returns:**
```python
{
    "status": "ready",
    "model_name": "qwen",
    "model_loaded": True,
    "cache_enabled": True,
    "cache_size": 42,
    "available_models": ["qwen", "gpt2", "codegen"]
}
```

##### update_config(config_updates: Dict[str, Any])

Update configuration without restart.

```python
translator.update_config({
    "temperature": 0.5,
    "max_tokens": 2048,
    "validation_level": "strict"
})
```

##### warmup_model()

Warm up the model for better initial performance.

```python
translator.warmup_model()
```

### TranslationResult

Result object returned by translation methods.

```python
@dataclass
class TranslationResult:
    success: bool
    code: Optional[str]
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    parse_result: Optional[ParseResult] = None
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Whether translation succeeded |
| `code` | `Optional[str]` | Generated Python code |
| `errors` | `List[str]` | List of error messages |
| `warnings` | `List[str]` | List of warning messages |
| `metadata` | `Dict[str, Any]` | Additional metadata |
| `has_errors` | `bool` | Whether there are errors |
| `has_warnings` | `bool` | Whether there are warnings |

#### Example Usage

```python
result = translator.translate("create a function to sort a list")

if result.success:
    print("Generated code:")
    print(result.code)
    
    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning}")
    
    print(f"\nMetadata: {result.metadata}")
else:
    print("Translation failed:")
    for error in result.errors:
        print(f"- {error}")
```

### TranslationStatus

Status object for progress updates.

```python
@dataclass
class TranslationStatus:
    phase: str
    progress: int
    message: str
    details: Optional[Dict[str, Any]] = None
```

#### Phases

| Phase | Description |
|-------|-------------|
| `parsing` | Analyzing input pseudocode |
| `translating` | Converting to Python |
| `assembling` | Combining code blocks |
| `validating` | Checking generated code |
| `completed` | Translation finished |
| `cancelled` | Translation cancelled |

## Configuration

### TranslatorConfig

Main configuration class.

```python
from pseudocode_translator.config import TranslatorConfig, ConfigManager

# Load configuration
config = ConfigManager.load("config.json")

# Or create new
config = TranslatorConfig(
    llm=LLMConfig(
        model_type="qwen",
        temperature=0.3,
        max_tokens=1024
    ),
    max_context_length=2048,
    preserve_comments=True
)
```

#### Key Attributes

```python
@dataclass
class TranslatorConfig:
    llm: LLMConfig
    streaming: StreamingConfig
    max_context_length: int = 2048
    preserve_comments: bool = True
    preserve_docstrings: bool = True
    auto_import_common: bool = True
    indent_size: int = 4
    use_type_hints: bool = True
    max_line_length: int = 88
    validate_imports: bool = True
    check_undefined_vars: bool = True
    allow_unsafe_operations: bool = False
    gui_theme: Literal["dark", "light", "auto"] = "dark"
    gui_font_size: int = 12
```

### LLMConfig

Language model configuration.

```python
@dataclass
class LLMConfig:
    model_type: str = "qwen"
    model_path: Path = Path("./models")
    model_file: str = "qwen-7b-q4_k_m.gguf"
    n_ctx: int = 2048
    n_batch: int = 512
    n_threads: int = 4
    n_gpu_layers: int = 0
    temperature: float = 0.3
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    max_tokens: int = 1024
    cache_enabled: bool = True
    cache_size_mb: int = 500
    cache_ttl_hours: int = 24
    timeout_seconds: int = 30
    validation_level: Literal["strict", "normal", "lenient"] = "strict"
```

### StreamingConfig

Streaming configuration for large files.

```python
@dataclass
class StreamingConfig:
    enable_streaming: bool = True
    auto_enable_threshold: int = 102400  # 100KB
    chunk_size: int = 4096
    max_chunk_size: int = 8192
    min_chunk_size: int = 512
    overlap_size: int = 256
    respect_boundaries: bool = True
    max_lines_per_chunk: int = 100
    max_memory_mb: int = 100
    buffer_compression: bool = True
```

## Parser Module

Parse pseudocode into structured blocks.

```python
from pseudocode_translator.parser import ParserModule
from pseudocode_translator.models import BlockType

parser = ParserModule()
result = parser.get_parse_result(pseudocode)

if result.success:
    for block in result.blocks:
        print(f"Type: {block.type}, Lines: {block.line_numbers}")
        print(f"Content: {block.content[:50]}...")
```

### ParseResult

```python
@dataclass
class ParseResult:
    success: bool
    blocks: List[CodeBlock]
    errors: List[ParseError]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    @property
    def block_count(self) -> int:
        return len(self.blocks)
    
    def get_blocks_by_type(self, block_type: BlockType) -> List[CodeBlock]:
        return [b for b in self.blocks if b.type == block_type]
```

### CodeBlock

```python
@dataclass
class CodeBlock:
    type: BlockType
    content: str
    line_numbers: Tuple[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Optional[str] = None
```

### BlockType

```python
class BlockType(Enum):
    ENGLISH = "english"
    PYTHON = "python"
    MIXED = "mixed"
    COMMENT = "comment"
```

## Model Management

Manage language models programmatically.

```python
from pseudocode_translator.models import ModelManager

# Initialize manager
manager = ModelManager({
    'model_dir': './models',
    'default_model': 'qwen',
    'auto_download': True
})

# List available models
models = manager.list_available_models()
print(f"Available: {models}")

# Load model
model = manager.load_model('gpt2')

# Check model info
info = model.get_info()
print(f"Model: {info['name']}, Size: {info['size_mb']}MB")

# Unload model
manager.unload_model('gpt2')
```

### Custom Models

```python
from pseudocode_translator.models import BaseModel, register_model

@register_model("my-custom-model")
class MyCustomModel(BaseModel):
    def __init__(self, model_path: Path, config: Dict[str, Any]):
        super().__init__(model_path, config)
        # Initialize your model
    
    def translate_instruction(self, instruction: str, 
                            context: Optional[Dict[str, Any]] = None) -> str:
        # Your translation logic
        return generated_code
```

## Validation

Validate generated code.

```python
from pseudocode_translator.validator import Validator, ValidationResult

validator = Validator(config)

# Validate syntax
result = validator.validate_syntax(code)
if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")

# Validate logic
logic_result = validator.validate_logic(code)
for warning in logic_result.warnings:
    print(f"Warning: {warning}")

# Get improvement suggestions
suggestions = validator.suggest_improvements(code)
for suggestion in suggestions:
    print(f"Suggestion: {suggestion}")
```

### ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    line_numbers: List[int] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
```

## Streaming API

For processing large files efficiently.

```python
from pseudocode_translator.streaming import StreamingPipeline

pipeline = StreamingPipeline(config)

# Check if streaming is needed
if pipeline.should_use_streaming(pseudocode):
    for chunk_result in pipeline.stream_translate(pseudocode):
        if chunk_result.success:
            print(f"Chunk {chunk_result.chunk_index}: {chunk_result.code}")
```

### StreamingProgress

```python
@dataclass
class StreamingProgress:
    progress_percentage: float
    processed_chunks: int
    total_chunks: int
    bytes_processed: int
    total_bytes: int
    errors: List[str]
    warnings: List[str]
```

## GUI Integration

Integrate with PySide6/PyQt applications.

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton
from pseudocode_translator import PseudocodeTranslatorAPI

class TranslatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.translator = PseudocodeTranslatorAPI()
        
        # Connect signals
        self.translator.translation_completed.connect(self.on_translation_complete)
        self.translator.translation_progress.connect(self.update_progress)
        
    def translate(self):
        pseudocode = self.input_text.toPlainText()
        self.translator.translate_async(pseudocode)
    
    def on_translation_complete(self, result: TranslationResult):
        if result.success:
            self.output_text.setPlainText(result.code)
```

## Events and Signals

Qt signals for GUI integration.

### Translation Signals

| Signal | Parameters | Description |
|--------|------------|-------------|
| `translation_started` | None | Translation began |
| `translation_progress` | `int` | Progress percentage |
| `translation_status` | `TranslationStatus` | Status update |
| `translation_completed` | `TranslationResult` | Translation finished |
| `translation_error` | `str` | Error occurred |

### Model Signals

| Signal | Parameters | Description |
|--------|------------|-------------|
| `model_status_changed` | `str` | Model status message |
| `model_initialized` | None | Model ready |

### Streaming Signals

| Signal | Parameters | Description |
|--------|------------|-------------|
| `streaming_started` | None | Streaming began |
| `streaming_chunk_processed` | `int, str` | Chunk processed |
| `streaming_progress` | `dict` | Progress info |
| `streaming_completed` | `str` | Final code |
| `memory_usage_updated` | `dict` | Memory stats |

### Example

```python
# Connect all signals
translator.translation_started.connect(
    lambda: print("Translation started")
)
translator.translation_progress.connect(
    lambda p: print(f"Progress: {p}%")
)
translator.translation_completed.connect(
    lambda r: print(f"Complete! Success: {r.success}")
)
translator.translation_error.connect(
    lambda e: print(f"Error: {e}")
)
```

## Exceptions

Custom exceptions that may be raised.

```python
class TranslatorError(Exception):
    """Base exception for translator errors"""

class ModelNotFoundError(TranslatorError):
    """Raised when model file is not found"""

class ModelLoadError(TranslatorError):
    """Raised when model fails to load"""

class ValidationError(TranslatorError):
    """Raised when code validation fails"""

class ConfigurationError(TranslatorError):
    """Raised for configuration issues"""

class TranslationTimeoutError(TranslatorError):
    """Raised when translation times out"""
```

### Exception Handling

```python
try:
    result = translator.translate(pseudocode)
except ModelNotFoundError:
    print("Model not found. Downloading...")
    translator.download_model("qwen")
except TranslationTimeoutError:
    print("Translation timed out. Try a shorter input.")
except TranslatorError as e:
    print(f"Translation error: {e}")
```

## Examples

### Basic Translation

```python
from pseudocode_translator import PseudocodeTranslatorAPI

translator = PseudocodeTranslatorAPI()

# Simple function
result = translator.translate("""
    create a function called greet that:
    - takes a name parameter
    - returns a greeting message
""")

print(result.code)
# Output:
# def greet(name):
#     """Takes a name parameter and returns a greeting message."""
#     return f"Hello, {name}!"
```

### Batch Processing

```python
# Process multiple files
pseudocode_files = ["idea1.txt", "idea2.txt", "idea3.txt"]

for file_path in pseudocode_files:
    with open(file_path) as f:
        pseudocode = f.read()
    
    result = translator.translate(pseudocode)
    
    if result.success:
        output_path = file_path.replace('.txt', '.py')
        with open(output_path, 'w') as f:
            f.write(result.code)
```

### Custom Configuration

```python
from pseudocode_translator import PseudocodeTranslatorAPI
from pseudocode_translator.config import TranslatorConfig, LLMConfig

# Create custom config
config = TranslatorConfig(
    llm=LLMConfig(
        model_type="codegen",
        temperature=0.1,  # More deterministic
        max_tokens=2048,
        n_gpu_layers=20  # Use GPU
    ),
    use_type_hints=True,
    validation_level="strict"
)

# Save config
config.save("my_config.json")

# Use custom config
translator = PseudocodeTranslatorAPI("my_config.json")
```

### Streaming Large Files

```python
# For files > 100KB
with open("large_pseudocode.txt") as f:
    pseudocode = f.read()

# Process in chunks
all_code = []
for chunk_result in translator.translate_streaming(pseudocode):
    if chunk_result.success:
        all_code.append(chunk_result.code)
        print(f"Processed chunk: {chunk_result.metadata['chunk_index']}")

# Combine results
final_code = "\n\n".join(all_code)
```

### Error Handling

```python
def safe_translate(pseudocode: str) -> Optional[str]:
    """Translate with comprehensive error handling"""
    try:
        # Ensure model is ready
        if not translator.is_ready:
            print("Waiting for model initialization...")
            # Wait up to 30 seconds
            for _ in range(30):
                if translator.is_ready:
                    break
                time.sleep(1)
            else:
                raise TimeoutError("Model initialization timeout")
        
        # Translate
        result = translator.translate(pseudocode)
        
        if result.success:
            # Log warnings
            for warning in result.warnings:
                logger.warning(warning)
            return result.code
        else:
            # Log errors
            for error in result.errors:
                logger.error(error)
            return None
            
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return None
```

### Custom Model Integration

```python
from pseudocode_translator.models import BaseModel, register_model, ModelCapabilities

@register_model("my-llama-model")
class MyLlamaModel(BaseModel):
    """Custom Llama model implementation"""
    
    @classmethod
    def get_capabilities(cls) -> ModelCapabilities:
        return ModelCapabilities(
            supports_streaming=True,
            supports_batch=True,
            max_context_length=4096,
            supports_gpu=True
        )
    
    def __init__(self, model_path: Path, config: Dict[str, Any]):
        super().__init__(model_path, config)
        # Initialize your model here
        self.model = load_llama_model(model_path)
    
    def translate_instruction(self, instruction: str, 
                            context: Optional[Dict[str, Any]] = None) -> str:
        prompt = self._build_prompt(instruction, context)
        response = self.model.generate(prompt)
        return self._extract_code(response)
```

## Best Practices

### 1. Resource Management

Always clean up resources:

```python
translator = PseudocodeTranslatorAPI()
try:
    # Use translator
    result = translator.translate(pseudocode)
finally:
    # Clean up
    translator.shutdown()
```

Or use context manager (if implemented):

```python
with PseudocodeTranslatorAPI() as translator:
    result = translator.translate(pseudocode)
```

### 2. Error Handling

Always handle potential errors:

```python
def robust_translate(pseudocode: str) -> str:
    try:
        result = translator.translate(pseudocode)
        if not result.success:
            # Fallback to simpler model
            translator.switch_model("gpt2")
            result = translator.translate(pseudocode)
        return result.code if result.success else ""
    except TranslatorError as e:
        logger.error(f"Translation error: {e}")
        return ""
```

### 3. Performance Optimization

For best performance:

```python
# 1. Reuse translator instance
translator = PseudocodeTranslatorAPI()  # Create once

# 2. Use appropriate model
translator.switch_model("gpt2")  # For simple tasks
translator.switch_model("codegen")  # For complex algorithms

# 3. Enable caching
translator.update_config({"cache_enabled": True})

# 4. Use streaming for large files
if len(pseudocode) > 100_000:
    results = translator.translate_streaming(pseudocode)
```

### 4. Testing

Test your integration:

```python
import pytest
from pseudocode_translator import PseudocodeTranslatorAPI

@pytest.fixture
def translator():
    t = PseudocodeTranslatorAPI()
    yield t
    t.shutdown()

def test_basic_translation(translator):
    result = translator.translate("create a function that returns True")
    assert result.success
    assert "def" in result.code
    assert "return True" in result.code
```

### 5. Monitoring

Monitor translation performance:

```python
import time

def monitored_translate(pseudocode: str) -> TranslationResult:
    start_time = time.time()
    
    # Get initial memory
    initial_memory = translator.get_model_status()['memory_usage_mb']
    
    # Translate
    result = translator.translate(pseudocode)
    
    # Calculate metrics
    duration = time.time() - start_time
    final_memory = translator.get_model_status()['memory_usage_mb']
    
    # Log metrics
    logger.info(f"Translation completed in {duration:.2f}s")
    logger.info(f"Memory delta: {final_memory - initial_memory}MB")
    logger.info(f"Tokens processed: {result.metadata.get('tokens', 0)}")
    
    return result
```

---

For more examples and use cases, see the [examples directory](../examples/).