# DinoAir 2.0

A modular, AI-powered desktop application with note-taking, task management, and advanced code generation capabilities. Built with PySide6 and Python.

**Open Source | No Fees | No Hidden Code | Completely Yours**

## Key Features

### 🎯 Core Functionality
- **Modern GUI**: Clean PySide6 interface with horizontal tab navigation
- **Multi-Database System**: Separate databases for notes, memory cache, and user tools
- **User Isolation**: Per-user database and configuration isolation
- **Resilient Storage**: Automatic error recovery and backup systems

### 🔧 Integrated Tools
- **Pseudocode Translator**: Convert natural language algorithms into production-ready code
  - Supports 14+ programming languages (Python, JavaScript, Java, C++, Go, Rust, etc.)
  - Modern syntax support (async/await, pattern matching, type hints)
  - Streaming translation with progress tracking
  - Parallel processing for multiple files
  - Extensible plugin architecture

### 📝 Productivity Features
- **Notes Management**: Create, edit, and organize notes with rich text support
- **Task Tracking**: Manage tasks and to-do lists
- **Calendar Integration**: Schedule and track appointments
- **File Search**: Advanced file searching capabilities
- **Input Processing**: Multi-stage validation with pattern detection

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/Dinopit/DinoAir2.0dev.git
cd DinoAir2.0dev

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Using the Pseudocode Translator

### In the GUI
1. Launch DinoAir 2.0
2. Navigate to the "Tools" tab
3. Select "Pseudocode Translator"
4. Enter your pseudocode and select target language
5. Click "Translate" to generate code

### Programmatically
```python
from pseudocode_translator import SimpleTranslator

translator = SimpleTranslator()
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

## Project Structure
```
DinoAir2.0dev/
├── main.py                    # Application entry point
├── config/                    # Configuration files
├── src/                       # Main source code
│   ├── gui/                   # User interface components
│   ├── database/              # Database management
│   ├── models/                # Data models
│   ├── agents/                # AI agents
│   ├── tools/                 # Integrated tools
│   └── utils/                 # Utilities
├── pseudocode_translator/     # Pseudocode translator module
│   ├── models/                # Language models
│   ├── streaming/             # Streaming support
│   └── examples/              # Usage examples
├── docs/                      # Documentation
└── user_data/                 # User-specific data (auto-created)
```

## Configuration

Edit `config/app_config.json` to customize:
- Database settings
- UI preferences
- Input processing rules
- Logging levels

## Documentation

- [Pseudocode Translator User Guide](docs/pseudocode_translator_user_guide.md)
- [API Reference](docs/pseudocode_translator_api_reference.md)
- [Examples](pseudocode_translator/examples/)

## Current Status

✅ **Fully Functional**
- Modular architecture with clean separation of concerns
- Complete GUI with all navigation features
- Database management with automatic backups
- Pseudocode translator with enterprise features
- Input processing pipeline
- Configuration and logging systems

🚧 **In Development**
- Additional AI agent integrations
- Extended file management features
- Plugin marketplace

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Follow the modular architecture principles and include proper documentation.

## License

This project is licensed under the MIT License with Ethical Use Clause.

- **Free for individuals and small teams** (≤10 employees)
- **Organizations with >10 employees** must contact the author for approval
- See [LICENSE](LICENSE) file for full terms
