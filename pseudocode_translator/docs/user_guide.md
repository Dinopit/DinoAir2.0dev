# Pseudocode Translator User Guide

Welcome to the comprehensive guide for using the Pseudocode Translator. This guide will help you master the art of transforming your ideas into working Python code using natural language.

## Table of Contents

1. [Introduction](#introduction)
2. [How It Works](#how-it-works)
3. [Writing Effective Pseudocode](#writing-effective-pseudocode)
4. [Using the GUI](#using-the-gui)
5. [Command Line Usage](#command-line-usage)
6. [Working with Models](#working-with-models)
7. [Advanced Features](#advanced-features)
8. [Configuration Options](#configuration-options)
9. [Best Practices](#best-practices)
10. [Tips and Tricks](#tips-and-tricks)

## Introduction

The Pseudocode Translator bridges the gap between human thinking and code. Instead of worrying about syntax, you can focus on describing what you want your code to do in plain English, mixed with whatever Python syntax you're comfortable with.

### Key Concepts

- **Natural Language Processing**: The tool understands English instructions and programming intent
- **Context Awareness**: It considers surrounding code and maintains consistency
- **Local-First**: All processing happens on your machine - no cloud required
- **Validation**: Generated code is checked for syntax and logic errors

## How It Works

### The Translation Pipeline

1. **Parsing**: Your input is analyzed to identify English instructions, Python code, and mixed content
2. **Context Building**: The system examines surrounding code to understand the context
3. **Translation**: English instructions are converted to Python using the selected language model
4. **Assembly**: All pieces are combined into a coherent code structure
5. **Validation**: The final code is checked for errors and potential issues
6. **Output**: Clean, formatted Python code ready to run

### Understanding Block Types

The translator recognizes four types of content:

- **English Blocks**: Pure natural language instructions
- **Python Blocks**: Valid Python code that passes through unchanged
- **Mixed Blocks**: Combination of English and Python
- **Comment Blocks**: Documentation and comments preserved as-is

## Writing Effective Pseudocode

### Basic Syntax

The translator is flexible and understands many ways to express the same idea:

```text
# All of these work:
create a function that adds two numbers
make a function to add two numbers
define a function for adding two numbers
function that takes two numbers and returns their sum
```

### Describing Functions

Be clear about:
- Function purpose
- Parameters
- Return values
- Any special behavior

**Good:**
```text
create a function called calculate_discount that:
- takes price and discount_percentage as parameters
- validates that discount_percentage is between 0 and 100
- returns the discounted price
- handles negative prices by raising ValueError
```

**Less Clear:**
```text
make discount function
```

### Describing Classes

Include:
- Class name and purpose
- Attributes
- Methods and their behavior
- Any inheritance

**Example:**
```text
Create a BankAccount class that:
- has balance and account_number attributes
- balance starts at 0
- has deposit method that adds money
- has withdraw method that checks for sufficient funds
- has get_balance method that returns current balance
- raises exception if withdrawal amount exceeds balance
```

### Mixing Python and English

You can seamlessly mix languages:

```python
def process_data(data):
    # validate that data is not empty
    
    results = []
    for item in data:
        # if item is valid number, square it and add to results
        # skip invalid items with a warning
    
    return sorted(results)
```

### Control Structures

Express loops and conditions naturally:

```text
for each student in the class:
    if their grade is above 90:
        add them to honor roll
    otherwise if grade is below 60:
        mark for extra help
```

## Using the GUI

### Launching the GUI

```bash
pseudocode-translator-gui
```

Or from Python:
```python
from pseudocode_translator.gui import launch_gui
launch_gui()
```

### GUI Features

#### Main Editor
- **Syntax Highlighting**: Automatic detection of Python vs English
- **Line Numbers**: Easy reference for debugging
- **Auto-indent**: Smart indentation for Python blocks
- **Find/Replace**: Standard text editing features

#### Translation Panel
- **Real-time Preview**: See translated code as you type
- **Validation Indicators**: Green checkmark for valid code, red X for errors
- **Progress Bar**: Track translation progress for large files
- **Cancel Button**: Stop long-running translations

#### Model Selection
- **Dropdown Menu**: Switch between available models
- **Model Status**: Shows loading state and readiness
- **Performance Metrics**: Display translation speed and resource usage

#### Configuration
- **Settings Button**: Access all configuration options
- **Theme Toggle**: Switch between light and dark modes
- **Font Size**: Adjust for readability
- **Auto-save**: Enable automatic saving of translations

### Keyboard Shortcuts

- `Ctrl+Enter`: Translate current selection or entire document
- `Ctrl+S`: Save current file
- `Ctrl+O`: Open file
- `Ctrl+N`: New file
- `Ctrl+Shift+P`: Open command palette
- `F5`: Refresh translation
- `Esc`: Cancel current operation

## Command Line Usage

### Basic Commands

```bash
# Translate a file
pseudocode-translator translate input.txt -o output.py

# Translate from stdin
echo "create a hello world function" | pseudocode-translator

# Use specific model
pseudocode-translator translate input.txt --model gpt2

# Enable verbose output
pseudocode-translator translate input.txt -v

# Validate without translating
pseudocode-translator validate input.txt
```

### Advanced Options

```bash
# Streaming mode for large files
pseudocode-translator translate large_file.txt --stream

# Custom configuration
pseudocode-translator translate input.txt --config my_config.json

# Batch processing
pseudocode-translator batch-translate *.txt --output-dir ./translated/

# Model management
pseudocode-translator list-models
pseudocode-translator download-model codegen
pseudocode-translator verify-models
```

### Output Formats

```bash
# Python file (default)
pseudocode-translator translate input.txt -o output.py

# Jupyter notebook
pseudocode-translator translate input.txt -o output.ipynb

# Markdown with code blocks
pseudocode-translator translate input.txt -o output.md

# JSON with metadata
pseudocode-translator translate input.txt --format json
```

## Working with Models

### Available Models

#### Qwen-7B (Default)
- **Best for**: General purpose translation
- **Strengths**: Excellent understanding of context, handles complex instructions
- **Size**: 4GB
- **Speed**: Moderate

#### GPT-2
- **Best for**: Quick translations, simple tasks
- **Strengths**: Fast inference, low resource usage
- **Size**: 1.5GB
- **Speed**: Fast

#### CodeGen
- **Best for**: Complex algorithms, technical code
- **Strengths**: Strong code generation, understands programming patterns
- **Size**: 2.5GB
- **Speed**: Moderate

### Switching Models

**GUI**: Use the model dropdown in the toolbar

**CLI**: 
```bash
pseudocode-translator translate input.txt --model codegen
```

**API**:
```python
translator.switch_model("codegen")
```

### Model Configuration

Each model can be configured individually:

```json
{
  "model_configs": {
    "qwen": {
      "temperature": 0.3,
      "max_tokens": 2048,
      "top_p": 0.9
    },
    "gpt2": {
      "temperature": 0.5,
      "max_tokens": 1024,
      "top_p": 0.95
    }
  }
}
```

## Advanced Features

### Streaming for Large Files

Streaming automatically activates for files over 100KB:

```python
# Manual streaming
for chunk in translator.translate_streaming(large_content):
    print(f"Progress: {chunk.metadata['progress']}%")
    process_chunk(chunk.code)
```

Features:
- Memory-efficient processing
- Progress callbacks
- Cancellable operations
- Maintains context between chunks

### Validation Levels

Choose validation strictness:

1. **Strict**: Full syntax, logic, style, and security checks
2. **Normal**: Standard syntax and logic validation (default)
3. **Lenient**: Basic syntax checking only

```bash
# Set validation level
pseudocode-translator translate input.txt --validation-level strict
```

### Batch Processing

Process multiple files efficiently:

```python
from pseudocode_translator import BatchProcessor

processor = BatchProcessor()
results = processor.process_directory(
    "pseudocode/",
    output_dir="python/",
    pattern="*.txt",
    max_workers=4
)
```

### Custom Prompts

Fine-tune translation behavior:

```python
translator.set_custom_prompt("""
Generate Python code following PEP 8 style guide.
Use type hints for all functions.
Include comprehensive docstrings.
""")
```

### Caching

Translation results are cached for efficiency:

```python
# Clear cache
translator.clear_cache()

# Disable caching
translator.config.llm.cache_enabled = False

# Set cache size
translator.config.llm.cache_size_mb = 1000
```

## Configuration Options

### Essential Settings

```json
{
  "llm": {
    "model_type": "qwen",          // Model selection
    "temperature": 0.3,            // Creativity (0.0-2.0)
    "max_tokens": 1024,           // Max output length
    "n_gpu_layers": 20            // GPU acceleration
  },
  "translation": {
    "preserve_comments": true,     // Keep original comments
    "auto_import_common": true,    // Add common imports
    "use_type_hints": true        // Generate type annotations
  }
}
```

### Performance Tuning

```json
{
  "streaming": {
    "chunk_size": 4096,           // Bytes per chunk
    "max_concurrent_chunks": 3,    // Parallel processing
    "memory_limit_mb": 500        // Memory cap
  },
  "llm": {
    "n_batch": 512,               // Batch size
    "n_threads": 8,               // CPU threads
    "cache_ttl_hours": 24         // Cache expiration
  }
}
```

### Validation Settings

```json
{
  "validation": {
    "check_undefined_vars": true,
    "check_imports": true,
    "allow_unsafe_operations": false,
    "max_line_length": 88,
    "validation_level": "normal"
  }
}
```

## Best Practices

### 1. Be Specific

**Good:**
```text
create a function that validates email addresses using regex
it should check for @ symbol and domain
return True if valid, False otherwise
```

**Better:**
```text
create a function called validate_email that:
- takes an email string as parameter
- uses regex to check format: username@domain.extension
- ensures there's exactly one @ symbol
- validates domain has at least one dot
- returns True if valid email format, False otherwise
- handles None/empty strings by returning False
```

### 2. Provide Context

When translating parts of a larger program:
```text
# Context: This is part of a web scraping tool

create a function that extracts all links from HTML:
- use BeautifulSoup for parsing
- return list of absolute URLs
- handle relative URLs by combining with base_url parameter
- skip mailto: and javascript: links
```

### 3. Use Consistent Naming

The translator learns from your naming patterns:
```text
# If you use camelCase:
create calculateTotalPrice function

# If you use snake_case:
create calculate_total_price function
```

### 4. Describe Edge Cases

Be explicit about error handling:
```text
create a divide function that:
- takes numerator and denominator
- returns the division result
- if denominator is zero, raise ZeroDivisionError with message "Cannot divide by zero"
- if inputs are not numbers, raise TypeError
```

### 5. Structure Complex Code

Break down complex requirements:
```text
Create a TodoList class:

First, the attributes:
- tasks: list to store todo items
- completed_tasks: list for finished items

Then the methods:
- add_task(description, priority='normal'): adds new task
- complete_task(index): moves task to completed
- get_pending(): returns uncompleted tasks
- get_stats(): returns dict with counts
```

## Tips and Tricks

### 1. Interactive Development

Use the GUI's real-time preview to refine your pseudocode:
1. Write initial description
2. Check generated code
3. Refine description based on output
4. Repeat until satisfied

### 2. Template System

Create reusable templates:

```python
# Save common patterns
template = """
create a REST API endpoint for {resource}:
- GET method to list all {resource}s
- POST method to create new {resource}
- PUT method to update existing {resource}
- DELETE method to remove {resource}
- include proper error handling
- return JSON responses
"""

result = translator.translate(template.format(resource="user"))
```

### 3. Learning from Examples

Study the generated code to improve your descriptions:
- Note how the model interprets certain phrases
- Identify patterns that produce better code
- Build a personal style guide

### 4. Debugging Translations

If translation isn't working as expected:

1. **Check block detection**:
   ```bash
   pseudocode-translator parse input.txt --show-blocks
   ```

2. **Increase verbosity**:
   ```bash
   pseudocode-translator translate input.txt -vv
   ```

3. **Try different models**:
   ```bash
   pseudocode-translator translate input.txt --model gpt2 --compare
   ```

4. **Adjust temperature**:
   ```bash
   # More creative/varied output
   pseudocode-translator translate input.txt --temperature 0.8
   
   # More deterministic output
   pseudocode-translator translate input.txt --temperature 0.1
   ```

### 5. Performance Optimization

For faster translations:

1. **Use GPU acceleration**:
   ```json
   {
     "llm": {
       "n_gpu_layers": 30  // Adjust based on GPU memory
     }
   }
   ```

2. **Enable caching for repeated content**:
   ```json
   {
     "llm": {
       "cache_enabled": true,
       "cache_size_mb": 1000
     }
   }
   ```

3. **Choose appropriate model**:
   - GPT-2 for simple, fast translations
   - Qwen for complex, context-aware translations
   - CodeGen for algorithm-heavy code

### 6. Integration Workflows

**VS Code Integration**:
```bash
# Add as external tool
pseudocode-translator translate "${file}" -o "${file}.py"
```

**Git Pre-commit Hook**:
```bash
#!/bin/bash
# Validate pseudocode files before commit
pseudocode-translator validate *.pseudo
```

**CI/CD Pipeline**:
```yaml
- name: Translate Pseudocode
  run: |
    pseudocode-translator batch-translate ./specs/ --output-dir ./src/
    pytest ./src/  # Test generated code
```

## Conclusion

The Pseudocode Translator empowers you to think in concepts rather than syntax. By following this guide, you'll be able to:

- Write clear, translatable pseudocode
- Leverage advanced features for complex projects
- Optimize performance for your workflow
- Integrate seamlessly into your development process

Remember: the tool is designed to augment your creativity, not replace your expertise. Use it to accelerate development, prototype ideas quickly, and bridge the gap between thought and implementation.

Happy coding! 🚀