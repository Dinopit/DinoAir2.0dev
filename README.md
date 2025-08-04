# DinoAir 2.0

A modular, AI-powered note-taking application built with PySide6 and Python.

## Architecture Overview

DinoAir 2.0 follows a highly modular architecture with clear separation of concerns:

```
src/
├── models/          # Data models and business logic
├── database/        # Database management and operations  
├── gui/            # PySide6 user interface components
│   ├── components/ # Reusable UI widgets
│   └── pages/      # Application pages/views
├── agents/         # AI agents and orchestration
├── tools/          # Utility tools and helpers
├── input_processing/ # Input sanitization and processing
└── utils/          # Core utilities (config, logging, enums)
```

## Features

### Core Functionality
- **Modular Architecture**: Highly modular design for easy maintenance and extension
- **Resilient Database**: Automatic error recovery and backup systems
- **Multi-Database Support**: Separate databases for notes, memory cache, and user tools
- **User Isolation**: Per-user database and configuration isolation

### GUI Components
- **Modern Interface**: Clean PySide6-based interface
- **Responsive Layout**: Resizable panes and adaptive UI
- **Navigation Sidebar**: Easy switching between different app sections
- **Status Monitoring**: Real-time database and system status

### AI Integration (Planned)
- **LLM Wrapper**: Modular AI agent system
- **Orchestrator**: Intelligent task coordination
- **Translation**: Multi-language support
- **Intent Classification**: Smart input understanding

### Input Processing
- **Sanitization Pipeline**: Multi-stage input validation and cleaning
- **Pattern Detection**: Automated pattern recognition
- **Profanity Filtering**: Content moderation capabilities
- **Intent Classification**: Smart categorization of user input

### Pseudocode Translator
- **Natural Language to Code**: Convert human-readable pseudocode into production-ready code
- **Multi-Language Output**: Support for 14+ programming languages including Python, JavaScript, Java, C++, Go, Rust, and more
- **Modern Syntax Support**: Handles modern programming constructs like async/await, pattern matching, and type hints
- **Enterprise Features**: Built-in caching, parallel processing, and streaming capabilities
- **Intelligent Validation**: AST-based parsing with semantic validation and error recovery
- **GUI Integration**: Seamlessly integrated into DinoAir 2.0's Tools menu
- **Extensible Architecture**: Plugin system for custom models and language extensions

## Installation

### Prerequisites
- Python 3.8 or higher
- PySide6
- SQLite3

### Setup
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Project Structure

```
DinoAir2.0dev/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config/
│   └── app_config.json    # Application configuration
├── src/                   # Main source code
│   ├── __init__.py
│   ├── models/            # Data models
│   │   ├── __init__.py
│   │   └── note.py       # Note and NoteList classes
│   ├── database/          # Database layer
│   │   ├── __init__.py
│   │   ├── initialize_db.py  # Database manager
│   │   └── resilient_db.py   # Resilient DB wrapper
│   ├── gui/               # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py # Main application window
│   │   ├── components/    # Reusable UI components
│   │   │   ├── __init__.py
│   │   │   ├── topbar.py
│   │   │   ├── sidebar.py
│   │   │   ├── statusbar.py
│   │   │   ├── artifact_panel.py
│   │   │   └── chat_input.py
│   │   └── pages/         # Application pages
│   │       ├── __init__.py
│   │       ├── notes_page.py
│   │       ├── calendar_page.py
│   │       ├── tasks_page.py
│   │       ├── settings_page.py
│   │       └── file_search_page.py
│   ├── agents/            # AI agents (planned)
│   │   └── __init__.py
│   ├── tools/             # Utility tools
│   │   ├── __init__.py
│   │   └── pseudocode_tool.py
│   ├── input_processing/  # Input processing pipeline
│   │   ├── __init__.py
│   │   └── input_sanitizer.py
│   └── utils/             # Core utilities
│       ├── __init__.py
│       ├── config_loader.py
│       ├── logger.py
│       └── enums.py
├── pseudocode_translator/ # Pseudocode to code translator
│   ├── __init__.py
│   ├── translator.py      # Main translator interface
│   ├── parser.py          # AST-based parser
│   ├── validator.py       # Syntax validation
│   ├── assembler.py       # Code generation
│   ├── models/            # Language models
│   ├── streaming/         # Streaming support
│   ├── integration/       # DinoAir integration
│   ├── configs/           # Configuration profiles
│   ├── examples/          # Example scripts and pseudocode
│   └── tests/             # Translator tests
├── tests/                 # Unit tests (planned)
├── docs/                  # Documentation
│   ├── pseudocode_translator_user_guide.md
│   ├── pseudocode_translator_api_reference.md
│   └── pseudocode_translator_changelog.md
├── logs/                  # Application logs (auto-created)
└── user_data/             # User-specific data (auto-created)
    └── {username}/
        ├── databases/     # User databases
        ├── exports/       # Exported files
        ├── backups/       # Database backups
        └── temp/          # Temporary files
```

## Configuration

The application uses a JSON-based configuration system located in `config/app_config.json`. Key configuration sections include:

- **app**: General application settings
- **database**: Database connection and backup settings
- **ai**: AI model configuration (when implemented)
- **ui**: User interface preferences
- **input_processing**: Input validation settings
- **logging**: Logging configuration

## Database Architecture

DinoAir 2.0 uses a multi-database approach:

1. **Notes Database** (`notes.db`): Stores user notes and content
2. **Memory Database** (`memory.db`): Caches and temporary data
3. **User Tools Database** (`user_tools.db`): User preferences and application logs

Each user gets their own isolated database environment in `user_data/{username}/databases/`.

## Pseudocode Translator

The integrated pseudocode translator allows you to convert natural language algorithmic descriptions into production-ready code.

### Quick Start

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

### Features
- Support for 14+ programming languages
- Modern syntax including async/await, pattern matching, type hints
- Streaming translation with progress tracking
- Parallel file processing
- Intelligent error recovery
- Extensible plugin system

### Documentation
- [User Guide](docs/pseudocode_translator_user_guide.md) - Complete usage instructions
- [API Reference](docs/pseudocode_translator_api_reference.md) - Detailed API documentation
- [Examples](pseudocode_translator/examples/) - Working code examples

## Development

### Adding New Modules
1. Create the module directory under `src/`
2. Add `__init__.py` with appropriate imports
3. Update the main `src/__init__.py` to include new modules
4. Add any new dependencies to `requirements.txt`

### Testing
```bash
# Run tests (when implemented)
pytest tests/

# Code formatting
black src/

# Linting
flake8 src/
```

## Contributing

1. Follow the modular architecture principles
2. Add proper docstrings to all classes and functions
3. Update configuration files when adding new features
4. Include appropriate error handling and logging
5. Write tests for new functionality

## License

[Add your license information here]

## Status

🚧 **Currently in Development** 🚧

- ✅ Modular architecture setup
- ✅ Database management system
- ✅ Basic GUI framework
- ✅ Configuration system
- ✅ Logging utilities
- ✅ Pseudocode translator
- 🔄 Input processing pipeline
- 🔄 AI agent integration
- ⏳ Advanced features and tools
- ⏳ Comprehensive testing suite

## Roadmap

### Phase 1: Core Foundation (Current)
- [x] Project structure and modularity
- [x] Database management
- [x] Basic GUI framework
- [ ] Input processing pipeline
- [ ] Configuration system finalization

### Phase 2: AI Integration
- [x] Pseudocode translator implementation
- [ ] LLM wrapper implementation
- [ ] Agent orchestration system
- [ ] Advanced translation services
- [ ] Intent classification

### Phase 3: Advanced Features
- [ ] Advanced note organization
- [ ] File management system
- [ ] Export/import capabilities
- [ ] Plugin system

### Phase 4: Polish and Testing
- [ ] Comprehensive test suite
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] User experience refinement
