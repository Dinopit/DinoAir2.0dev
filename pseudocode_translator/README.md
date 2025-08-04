# Pseudocode Translator

A modern, enterprise-grade pseudocode translator that converts human-readable algorithmic descriptions into production-ready code across 14+ programming languages. Built with advanced features like streaming translation, parallel processing, and intelligent caching.

## 🚀 Features

### Core Capabilities
- **Multi-Language Output**: Generate code in Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, Ruby, Swift, Kotlin, Scala, PHP, and R
- **Modern Syntax Support**: Full support for Python 3.10+ features including match statements, walrus operators, and type hints
- **Intelligent Parsing**: AST-based parser with semantic validation and error recovery
- **Enterprise Performance**: Built-in caching, parallel processing, and streaming capabilities

### Advanced Features
- **Streaming Translation**: Real-time code generation with progress tracking
- **Parallel Processing**: Batch translate multiple files concurrently
- **Smart Caching**: AST-level caching for instant re-translations
- **Error Recovery**: Graceful handling with detailed error messages and suggestions
- **Plugin Architecture**: Extensible model system for custom language models
- **GUI Integration**: Seamless integration with DinoAir 2.0 application

### Developer Experience
- **Simple API**: High-level interface for quick integration
- **Configuration Profiles**: Pre-configured settings for common use cases
- **Interactive Wizard**: Step-by-step configuration helper
- **Comprehensive Validation**: Catch errors before translation
- **Event System**: Hook into translation lifecycle events

## 📦 Installation

### Basic Installation
```bash
# Install as part of DinoAir 2.0
pip install -r requirements.txt
```

### Development Installation
```bash
# Clone the repository
git clone https://github.com/your-org/dinoair2.0dev.git
cd dinoair2.0dev/pseudocode_translator

# Install in development mode
pip install -e .
```

## 🎯 Quick Start

### Simple Translation
```python
from pseudocode_translator import SimpleTranslator

# Create translator instance
translator = SimpleTranslator()

# Translate pseudocode to Python
pseudocode = """
FUNCTION calculateFactorial(n)
    IF n <= 1 THEN
        RETURN 1
    ELSE
        RETURN n * calculateFactorial(n - 1)
    END IF
END FUNCTION
"""

python_code = translator.translate(pseudocode, target_language="python")
print(python_code)
```

### Streaming Translation
```python
from pseudocode_translator import SimpleTranslator

translator = SimpleTranslator(enable_streaming=True)

# Stream translation with progress
for chunk in translator.translate_stream(pseudocode, target_language="javascript"):
    print(chunk.content, end='', flush=True)
    # Progress available in chunk.metadata['progress']
```

### GUI Integration
```python
from src.gui.main_window import MainWindow
# The pseudocode translator is integrated into the Tools menu
# Access via: Tools > Pseudocode Translator
```

## ⚙️ Configuration

### Configuration File
Create a `config.yaml` file:
```yaml
model:
  provider: "openai"
  name: "gpt-4"
  temperature: 0.3
  max_tokens: 2048

translation:
  target_language: "python"
  style_guide: "pep8"
  include_comments: true
  type_hints: true

performance:
  enable_cache: true
  cache_ttl: 3600
  parallel_workers: 4
  streaming_enabled: true
```

### Configuration Profiles
Use pre-configured settings:
```python
# For quick prototyping
translator = SimpleTranslator(profile="minimal")

# For production use
translator = SimpleTranslator(profile="production")

# For educational purposes
translator = SimpleTranslator(profile="educational")
```

### Interactive Configuration
```bash
# Run the configuration wizard
python -m pseudocode_translator.config_wizard
```

## 📖 Documentation

- **[User Guide](../docs/pseudocode_translator_user_guide.md)**: Detailed usage instructions and pseudocode syntax
- **[API Reference](../docs/pseudocode_translator_api_reference.md)**: Complete API documentation and examples
- **[Examples](examples/)**: Working examples for various use cases
- **[Changelog](../docs/pseudocode_translator_changelog.md)**: Version history and migration guides

## 🔧 Troubleshooting

### Common Issues

**Translation Errors**
```python
# Enable debug mode for detailed error information
translator = SimpleTranslator(debug=True)

try:
    result = translator.translate(pseudocode)
except TranslationError as e:
    print(f"Error: {e}")
    print(f"Suggestion: {e.suggestion}")
    print(f"Line: {e.line_number}")
```

**Performance Issues**
```python
# Optimize for large files
translator = SimpleTranslator(
    enable_cache=True,
    parallel_workers=8,
    chunk_size=1000
)
```

**Model Configuration**
```python
# Test model connection
from pseudocode_translator import test_model_connection

if not test_model_connection():
    print("Check your API keys and network connection")
```

### Getting Help

1. Check the [User Guide](../docs/pseudocode_translator_user_guide.md) for detailed instructions
2. Review [API Reference](../docs/pseudocode_translator_api_reference.md) for code examples
3. Look at [Examples](examples/) for working implementations
4. Check existing issues in the project repository
5. Contact support through the DinoAir 2.0 application

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines in the main project repository.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 pseudocode_translator/
black pseudocode_translator/
```

## 📄 License

This project is part of DinoAir 2.0 and follows the same licensing terms.

## 🙏 Acknowledgments

Built with ❤️ by the DinoAir team. Special thanks to all contributors and testers who helped make this tool production-ready.