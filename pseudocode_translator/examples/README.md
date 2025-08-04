# Pseudocode Translator Examples

This directory contains practical examples demonstrating various features and use cases of the Pseudocode Translator.

## Example Categories

### Basic Examples
- [`basic_translation.py`](basic_translation.py) - Simple translation examples
- [`hello_world.txt`](hello_world.txt) - Classic hello world in pseudocode
- [`calculator.txt`](calculator.txt) - Basic calculator class

### Advanced Examples
- [`gui_integration.py`](gui_integration.py) - Integrating with PySide6 GUI
- [`batch_processing.py`](batch_processing.py) - Processing multiple files
- [`custom_model.py`](custom_model.py) - Using custom language models
- [`streaming_large_files.py`](streaming_large_files.py) - Handling large pseudocode files

### Pseudocode Samples
- [`web_scraper.txt`](web_scraper.txt) - Web scraping tool in pseudocode
- [`data_processor.txt`](data_processor.txt) - Data processing pipeline
- [`game_logic.txt`](game_logic.txt) - Simple game logic
- [`api_server.txt`](api_server.txt) - REST API server
- [`machine_learning.txt`](machine_learning.txt) - ML model training

### Integration Examples
- [`vscode_extension.py`](vscode_extension.py) - VS Code integration example
- [`cli_wrapper.py`](cli_wrapper.py) - Custom CLI wrapper
- [`jupyter_notebook.ipynb`](jupyter_notebook.ipynb) - Using in Jupyter notebooks

## Quick Start

1. **Basic Translation**:
   ```bash
   python basic_translation.py
   ```

2. **Translate a Sample**:
   ```bash
   pseudocode-translator translate calculator.txt -o calculator.py
   ```

3. **Batch Processing**:
   ```bash
   python batch_processing.py ./pseudocode_samples/
   ```

## Example Descriptions

### basic_translation.py
Shows the simplest way to use the API for translating pseudocode strings.

### gui_integration.py
Demonstrates how to build a complete GUI application with real-time translation.

### batch_processing.py
Processes an entire directory of pseudocode files with progress tracking.

### custom_model.py
Shows how to implement and register your own language model.

### streaming_large_files.py
Handles files larger than 100KB using the streaming API.

### Pseudocode Samples
Various real-world examples written in pseudocode that can be translated:
- Web scraping with BeautifulSoup
- Data processing with pandas
- Game logic with classes
- REST API with Flask
- Machine learning with scikit-learn

## Running the Examples

Most examples can be run directly:

```bash
cd examples
python example_name.py
```

For pseudocode files, use the translator:

```bash
pseudocode-translator translate example.txt -o example.py
python example.py
```

## Contributing Examples

Feel free to contribute your own examples! Guidelines:
1. Keep examples focused on demonstrating specific features
2. Include comments explaining key concepts
3. Provide both the pseudocode input and expected output
4. Test that examples work with the latest version

## Learning Path

1. Start with `basic_translation.py`
2. Try translating the `.txt` pseudocode samples
3. Explore `gui_integration.py` for building applications
4. Learn batch processing for automation
5. Advanced: Create custom models and integrations