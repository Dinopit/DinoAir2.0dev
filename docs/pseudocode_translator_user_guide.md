# Pseudocode Translator User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Pseudocode Syntax](#pseudocode-syntax)
4. [Language Output Options](#language-output-options)
5. [Model Selection and Configuration](#model-selection-and-configuration)
6. [Streaming and Performance](#streaming-and-performance)
7. [Error Handling and Recovery](#error-handling-and-recovery)
8. [Advanced Features](#advanced-features)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

## Introduction

The Pseudocode Translator is a powerful tool that converts human-readable algorithmic descriptions into production-ready code. It supports modern programming constructs, multiple output languages, and enterprise-grade features like streaming and parallel processing.

### Key Benefits
- Write algorithms in natural, readable pseudocode
- Generate code in 14+ programming languages
- Automatic syntax validation and error detection
- Real-time streaming translation
- Integration with DinoAir 2.0 GUI

## Getting Started

### Basic Usage

1. **Using the GUI**:
   - Open DinoAir 2.0
   - Navigate to Tools → Pseudocode Translator
   - Enter your pseudocode in the input panel
   - Select target language
   - Click "Translate"

2. **Using the CLI**:
   ```bash
   python -m pseudocode_translator translate input.pseudo -o output.py
   ```

3. **Using the API**:
   ```python
   from pseudocode_translator import SimpleTranslator
   
   translator = SimpleTranslator()
   code = translator.translate(pseudocode_text, target_language="python")
   ```

## Pseudocode Syntax

### Basic Constructs

#### Variables and Assignment
```
SET variable TO value
variable = value
DECLARE variable AS type
```

#### Input/Output
```
INPUT variable
OUTPUT expression
PRINT "Hello, World!"
READ filename INTO variable
WRITE data TO filename
```

#### Control Structures

**If-Then-Else**:
```
IF condition THEN
    statements
ELSE IF another_condition THEN
    statements
ELSE
    statements
END IF
```

**Loops**:
```
# For loop
FOR i FROM 1 TO 10
    statements
END FOR

FOR EACH item IN collection
    statements
END FOR

# While loop
WHILE condition
    statements
END WHILE

# Do-while loop
DO
    statements
WHILE condition
```

**Switch/Case**:
```
SWITCH variable
    CASE value1:
        statements
    CASE value2:
        statements
    DEFAULT:
        statements
END SWITCH
```

### Functions and Procedures

#### Function Definition
```
FUNCTION functionName(parameter1, parameter2)
    statements
    RETURN value
END FUNCTION
```

#### Procedure Definition
```
PROCEDURE procedureName(parameters)
    statements
END PROCEDURE
```

#### Function Call
```
result = functionName(arg1, arg2)
CALL procedureName(arguments)
```

### Data Structures

#### Arrays
```
DECLARE array[size] AS type
array[index] = value
value = array[index]

# Dynamic arrays
APPEND value TO array
REMOVE index FROM array
```

#### Lists
```
CREATE LIST myList
ADD item TO myList
REMOVE item FROM myList
```

#### Dictionaries/Maps
```
CREATE DICTIONARY myDict
myDict[key] = value
value = myDict[key]
```

### Modern Syntax Support

#### Type Hints
```
FUNCTION calculate(x: INTEGER, y: FLOAT) -> FLOAT
    RETURN x + y
END FUNCTION
```

#### Pattern Matching
```
MATCH value
    CASE pattern1:
        action1
    CASE pattern2:
        action2
    CASE _:
        default_action
END MATCH
```

#### Lambda Functions
```
square = LAMBDA x: x * x
filtered = FILTER(LAMBDA x: x > 0, numbers)
```

#### Async/Await
```
ASYNC FUNCTION fetchData(url)
    data = AWAIT fetch(url)
    RETURN data
END FUNCTION
```

### Comments
```
# Single line comment
// Alternative single line comment

/* Multi-line
   comment */
```

## Language Output Options

### Supported Languages

1. **Python** - Default, with type hints and modern syntax
2. **JavaScript** - ES6+ syntax with optional TypeScript
3. **TypeScript** - Full type safety
4. **Java** - Object-oriented with generics
5. **C++** - Modern C++ (C++17/20)
6. **C#** - .NET Core compatible
7. **Go** - Idiomatic Go with error handling
8. **Rust** - Memory-safe with ownership
9. **Ruby** - Clean, expressive syntax
10. **Swift** - Type-safe with optionals
11. **Kotlin** - Null-safe with coroutines
12. **Scala** - Functional and OO features
13. **PHP** - Modern PHP 8+
14. **R** - Statistical computing focus

### Language-Specific Options

```python
translator = SimpleTranslator()

# Python with specific style
result = translator.translate(
    pseudocode,
    target_language="python",
    options={
        "style_guide": "pep8",
        "type_hints": True,
        "docstring_style": "google"
    }
)

# JavaScript with specific version
result = translator.translate(
    pseudocode,
    target_language="javascript",
    options={
        "version": "es2022",
        "use_semicolons": False,
        "module_system": "esm"
    }
)
```

## Model Selection and Configuration

### Available Models

1. **OpenAI Models**:
   - GPT-4: Best quality, slower
   - GPT-3.5-turbo: Good balance of speed and quality

2. **Anthropic Models**:
   - Claude-3: High quality with large context
   - Claude-2: Faster, good for simple translations

3. **Local Models**:
   - CodeLlama: Privacy-focused, offline capable
   - Custom models via plugin system

### Configuration Examples

```yaml
# config.yaml
model:
  provider: "openai"
  name: "gpt-4"
  api_key_env: "OPENAI_API_KEY"
  temperature: 0.3
  max_tokens: 2048
  timeout: 30

# For local models
model:
  provider: "local"
  name: "codellama"
  model_path: "./models/codellama-7b"
  device: "cuda"  # or "cpu"
```

### Switching Models at Runtime

```python
# Use different models for different tasks
translator = SimpleTranslator()

# High-quality translation
translator.set_model("gpt-4")
complex_code = translator.translate(complex_pseudocode)

# Fast translation
translator.set_model("gpt-3.5-turbo")
simple_code = translator.translate(simple_pseudocode)
```

## Streaming and Performance

### Streaming Translation

Enable real-time translation with progress tracking:

```python
translator = SimpleTranslator(enable_streaming=True)

for chunk in translator.translate_stream(pseudocode):
    print(chunk.content, end='', flush=True)
    
    # Access metadata
    progress = chunk.metadata.get('progress', 0)
    tokens_used = chunk.metadata.get('tokens_used', 0)
```

### Parallel Processing

Process multiple files concurrently:

```python
from pseudocode_translator import ParallelProcessor

processor = ParallelProcessor(workers=4)

# Batch translation
results = processor.translate_batch([
    "file1.pseudo",
    "file2.pseudo",
    "file3.pseudo"
], target_language="python")

# With progress callback
def progress_callback(file, progress):
    print(f"{file}: {progress}%")

results = processor.translate_batch(
    files,
    progress_callback=progress_callback
)
```

### Caching

Enable caching for repeated translations:

```python
translator = SimpleTranslator(
    enable_cache=True,
    cache_ttl=3600  # 1 hour
)

# First translation - hits the model
result1 = translator.translate(pseudocode)

# Second translation - uses cache
result2 = translator.translate(pseudocode)  # Instant!
```

### Performance Optimization

```python
# Optimize for large files
translator = SimpleTranslator(
    chunk_size=1000,  # Process in chunks
    enable_cache=True,
    parallel_workers=8,
    timeout=60
)

# Memory-efficient streaming
with translator.translate_file_stream("large.pseudo") as stream:
    for chunk in stream:
        process_chunk(chunk)
```

## Error Handling and Recovery

### Common Errors and Solutions

#### Syntax Errors
```python
try:
    result = translator.translate(pseudocode)
except SyntaxError as e:
    print(f"Syntax error at line {e.line}: {e.message}")
    print(f"Suggestion: {e.suggestion}")
    
    # Show context
    print(e.get_context(lines_before=2, lines_after=2))
```

#### Validation Errors
```python
from pseudocode_translator import Validator

validator = Validator()
errors = validator.validate(pseudocode)

for error in errors:
    print(f"{error.severity}: {error.message} at line {error.line}")
    if error.suggestion:
        print(f"  Suggestion: {error.suggestion}")
```

### Error Recovery

The translator includes intelligent error recovery:

```python
translator = SimpleTranslator(
    error_recovery=True,
    strict_mode=False  # Continue on non-critical errors
)

result = translator.translate(pseudocode_with_errors)

# Check for recovered errors
if result.has_warnings:
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

### Custom Error Handlers

```python
def custom_error_handler(error):
    if error.type == "undefined_variable":
        # Auto-declare undefined variables
        return f"var {error.variable} = null;"
    return None  # Use default handling

translator = SimpleTranslator(
    error_handler=custom_error_handler
)
```

## Advanced Features

### Template System

Use templates for consistent code generation:

```python
translator = SimpleTranslator()

# Define a template
template = """
class {class_name}:
    def __init__(self):
        {init_code}
    
    {methods}
"""

result = translator.translate_with_template(
    pseudocode,
    template=template,
    context={"class_name": "MyAlgorithm"}
)
```

### Custom Validators

Add domain-specific validation:

```python
from pseudocode_translator import Validator

class MathValidator(Validator):
    def validate_custom(self, ast_node):
        if ast_node.type == "division":
            if ast_node.divisor == 0:
                self.add_error("Division by zero", ast_node.line)
```

### Plugin Development

Create custom language models:

```python
from pseudocode_translator.models import BaseModel

class CustomModel(BaseModel):
    def translate(self, ast, target_language, options):
        # Custom translation logic
        return generated_code
    
    def get_capabilities(self):
        return {
            "languages": ["custom_lang"],
            "features": ["async", "generics"]
        }
```

### Integration with External Tools

```python
# Integration with code formatters
result = translator.translate(pseudocode)
formatted = translator.format_code(result, formatter="black")

# Integration with linters
issues = translator.lint_output(result, linter="pylint")
```

## Best Practices

### Writing Clear Pseudocode

1. **Use Consistent Naming**:
   ```
   # Good
   FUNCTION calculateTotalPrice(items, taxRate)
   
   # Avoid
   FUNCTION calc_ttl(i, t)
   ```

2. **Add Comments for Complex Logic**:
   ```
   # Calculate compound interest using the formula A = P(1 + r/n)^(nt)
   FUNCTION calculateCompoundInterest(principal, rate, time, n)
   ```

3. **Use Meaningful Variable Names**:
   ```
   # Good
   FOR EACH student IN classList
       IF student.grade >= passingGrade THEN
   
   # Avoid
   FOR EACH s IN cl
       IF s.g >= pg THEN
   ```

### Optimization Tips

1. **Batch Similar Translations**:
   ```python
   # Efficient
   results = translator.translate_batch(files, target_language="python")
   
   # Less efficient
   for file in files:
       result = translator.translate_file(file, target_language="python")
   ```

2. **Use Appropriate Models**:
   - Simple algorithms: Use faster models (GPT-3.5-turbo)
   - Complex logic: Use powerful models (GPT-4)
   - Privacy-sensitive: Use local models

3. **Enable Caching for Development**:
   ```python
   # During development
   translator = SimpleTranslator(
       enable_cache=True,
       cache_ttl=86400  # 24 hours
   )
   ```

## Troubleshooting

### Common Issues

#### Model Connection Errors
```python
# Test connection
from pseudocode_translator import test_model_connection

if not test_model_connection():
    # Check API keys
    print("Verify OPENAI_API_KEY is set")
    
    # Try alternative model
    translator.set_model("local/codellama")
```

#### Memory Issues with Large Files
```python
# Use streaming for large files
translator = SimpleTranslator(
    streaming_threshold=1000  # Stream files > 1000 lines
)

# Process in chunks
for chunk in translator.process_large_file("huge.pseudo"):
    save_chunk(chunk)
```

#### Translation Quality Issues
```python
# Adjust model parameters
translator = SimpleTranslator(
    model_config={
        "temperature": 0.2,  # Lower = more deterministic
        "top_p": 0.9,
        "frequency_penalty": 0.1
    }
)

# Use validation before translation
if translator.validate(pseudocode):
    result = translator.translate(pseudocode)
```

### Debug Mode

Enable detailed logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

translator = SimpleTranslator(debug=True)

# Get detailed translation info
result = translator.translate_with_debug(pseudocode)
print(result.debug_info)
```

### Getting Help

1. **Check Validation Errors**: Always validate pseudocode before translation
2. **Use Error Messages**: Error messages include helpful suggestions
3. **Enable Debug Mode**: Get detailed information about the translation process
4. **Check Examples**: Review working examples in the examples directory
5. **Community Support**: Ask questions in the DinoAir community forums

## Next Steps

- Explore the [API Reference](pseudocode_translator_api_reference.md) for detailed API documentation
- Check out [Examples](../pseudocode_translator/examples/) for working code samples
- Read the [Developer Guide](pseudocode_translator_api_reference.md#plugin-development) to create custom plugins
- Join our community to share feedback and get support