# Configuration Guide for Pseudocode Translator

This guide covers the configuration system for the Pseudocode Translator, including all available options, validation, migration, and management tools.

## Table of Contents

1. [Overview](#overview)
2. [Configuration File Formats](#configuration-file-formats)
3. [Configuration Options](#configuration-options)
4. [Environment Variables](#environment-variables)
5. [Configuration Validation](#configuration-validation)
6. [Configuration Migration](#configuration-migration)
7. [Configuration Management Tool](#configuration-management-tool)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## Overview

The Pseudocode Translator uses a comprehensive configuration system built on Pydantic for type safety and validation. The configuration system supports:

- **YAML and JSON formats** for configuration files
- **Automatic validation** with helpful error messages
- **Environment variable overrides** for deployment flexibility
- **Automatic migration** from older configuration formats
- **Hot-reloading** for development
- **Type safety** with Pydantic schemas

## Configuration File Formats

### Default Locations

The system looks for configuration files in the following locations (in order):

1. Path specified via command line or API
2. `~/.pseudocode_translator/config.yaml` (user home directory)
3. `./config.yaml` (current directory)

### Supported Formats

- **YAML** (`.yaml`, `.yml`) - Recommended for human editing
- **JSON** (`.json`) - For programmatic generation

### Pre-built Templates

The `configs/` directory contains three templates:

- `default.yaml` - Sensible defaults for most use cases
- `minimal.yaml` - Minimal configuration (only essential settings)
- `advanced.yaml` - All options with documentation

## Configuration Options

### Language Model Configuration (`llm`)

Controls the language model behavior and parameters.

```yaml
llm:
  # Primary model to use
  model_type: qwen  # Options: qwen, gpt2, codegen, custom
  
  # Base directory for models
  model_path: ./models
  
  # Model loading parameters
  n_ctx: 2048          # Context window size (512-32768)
  n_batch: 512         # Batch size (1-2048)
  n_threads: 4         # CPU threads (1-32)
  n_gpu_layers: 0      # GPU layers (0=CPU only)
  
  # Generation parameters
  temperature: 0.3     # Sampling temperature (0.0-2.0)
  top_p: 0.9          # Nucleus sampling (0.0-1.0)
  top_k: 40           # Top-k sampling (0-200)
  repeat_penalty: 1.1  # Repetition penalty (0.1-2.0)
  max_tokens: 1024    # Max generation length
  
  # Performance settings
  cache_enabled: true
  cache_size_mb: 500
  cache_ttl_hours: 24
  
  # Model management
  auto_download: false
  max_loaded_models: 1
  model_ttl_minutes: 60
  
  # Validation
  validation_level: strict  # strict, normal, lenient
  timeout_seconds: 30
  
  # Model-specific configurations
  model_configs:
    qwen:
      name: qwen
      enabled: true
      parameters:
        temperature: 0.3
```

### Streaming Configuration (`streaming`)

Controls how large files are processed in chunks.

```yaml
streaming:
  enable_streaming: true
  auto_enable_threshold: 102400  # 100KB
  
  # Chunk settings
  chunk_size: 4096
  max_chunk_size: 8192
  min_chunk_size: 512
  overlap_size: 256
  respect_boundaries: true
  max_lines_per_chunk: 100
  
  # Memory settings
  max_memory_mb: 100
  buffer_compression: true
  eviction_policy: lru  # lru or fifo
  
  # Pipeline settings
  max_concurrent_chunks: 3
  chunk_timeout: 30.0
  enable_backpressure: true
  max_queue_size: 10
  
  # Progress monitoring
  progress_callback_interval: 0.5
  enable_memory_monitoring: true
  
  # Context management
  maintain_context_window: true
  context_window_size: 1024
```

### Translation Settings

Controls the translation behavior.

```yaml
max_context_length: 2048
preserve_comments: true
preserve_docstrings: true
auto_import_common: true
```

### Code Style Preferences

Controls the style of generated Python code.

```yaml
indent_size: 4
use_type_hints: true
max_line_length: 88  # Black's default
```

### Validation Settings

Controls code validation and safety.

```yaml
validate_imports: true
check_undefined_vars: true
allow_unsafe_operations: false
```

### GUI Preferences

Settings for the graphical interface.

```yaml
gui_theme: dark  # dark, light, auto
gui_font_size: 12
syntax_highlighting: true
```

## Environment Variables

Any configuration option can be overridden using environment variables. The naming convention is:

```
PSEUDOCODE_TRANSLATOR_<SECTION>_<KEY>
```

### Examples

```bash
# Override model type
export PSEUDOCODE_TRANSLATOR_LLM_MODEL_TYPE=gpt2

# Override temperature
export PSEUDOCODE_TRANSLATOR_LLM_TEMPERATURE=0.5

# Disable streaming
export PSEUDOCODE_TRANSLATOR_STREAMING_ENABLE_STREAMING=false

# Change chunk size
export PSEUDOCODE_TRANSLATOR_STREAMING_CHUNK_SIZE=8192

# Disable import validation
export PSEUDOCODE_TRANSLATOR_VALIDATE_IMPORTS=false
```

### Boolean Values

For boolean settings, the following values are recognized:
- True: `true`, `1`, `yes`, `on`
- False: `false`, `0`, `no`, `off`

## Configuration Validation

The configuration system uses Pydantic for comprehensive validation:

### Automatic Validation

- Configurations are validated when loaded
- Type checking ensures correct data types
- Range validation for numeric values
- Path validation for file/directory settings
- Relationship validation between settings

### Validation Levels

1. **Strict** - Fail on any validation issue
2. **Normal** - Fail on errors, warn on issues
3. **Lenient** - Only fail on critical errors

### Common Validation Errors

- `Temperature must be between 0 and 2` - Temperature out of range
- `Model directory does not exist` - Model path not found
- `chunk_size cannot exceed max_chunk_size` - Invalid chunk settings

## Configuration Migration

The system automatically migrates old configuration formats:

### Supported Versions

- **1.0** - Flat structure without sections
- **1.1** - Has `llm` section but no streaming
- **1.2** - Has streaming but old format
- **2.0** - Current format with Pydantic schemas

### Automatic Migration

When loading an old configuration:
1. Version is detected automatically
2. Configuration is migrated to current format
3. Backup is created (`.bak` extension)
4. Migration log is saved

### Manual Migration

```bash
# Check if migration is needed
python -m pseudocode_translator.config_tool check config.yaml

# Migrate configuration
python -m pseudocode_translator.config_tool migrate config.yaml

# Dry run (preview changes)
python -m pseudocode_translator.config_tool migrate config.yaml --dry-run
```

## Configuration Management Tool

The `config_tool` provides command-line configuration management:

### Installation

```bash
# Run from project directory
python -m pseudocode_translator.config_tool --help
```

### Commands

#### Validate Configuration

```bash
# Validate with normal level
python -m pseudocode_translator.config_tool validate config.yaml

# Strict validation
python -m pseudocode_translator.config_tool validate config.yaml -l strict

# Attempt to fix issues
python -m pseudocode_translator.config_tool validate config.yaml --fix
```

#### Generate Configuration

```bash
# Generate default configuration
python -m pseudocode_translator.config_tool generate

# Generate minimal configuration
python -m pseudocode_translator.config_tool generate -t minimal

# Generate advanced configuration
python -m pseudocode_translator.config_tool generate -t advanced -o my_config.yaml
```

#### Interactive Wizard

```bash
# Start configuration wizard
python -m pseudocode_translator.config_tool wizard

# Specify output file
python -m pseudocode_translator.config_tool wizard -o custom_config.yaml
```

#### Check Environment

```bash
# Check configuration and environment
python -m pseudocode_translator.config_tool check

# Check specific config file
python -m pseudocode_translator.config_tool check config.yaml

# Check models
python -m pseudocode_translator.config_tool check --models

# Check environment variables
python -m pseudocode_translator.config_tool check --env
```

#### Show Configuration Info

```bash
# Display configuration details
python -m pseudocode_translator.config_tool info config.yaml
```

## Examples

### Example 1: Basic Configuration

```yaml
# Basic configuration for CPU-only usage
llm:
  model_type: qwen
  model_path: ./models
  n_threads: 4
  temperature: 0.3

streaming:
  enable_streaming: true
  chunk_size: 4096
```

### Example 2: GPU-Accelerated Configuration

```yaml
# Configuration for GPU acceleration
llm:
  model_type: codegen
  n_gpu_layers: 20
  n_threads: 8
  n_ctx: 4096
  
  model_configs:
    codegen:
      enabled: true
      auto_download: true
      parameters:
        temperature: 0.2
        max_tokens: 2048
```

### Example 3: Multi-Model Configuration

```yaml
# Configuration with multiple models
llm:
  model_type: qwen  # Default model
  max_loaded_models: 2
  
  model_configs:
    qwen:
      enabled: true
      parameters:
        temperature: 0.3
    
    gpt2:
      enabled: true
      auto_download: true
      parameters:
        temperature: 0.5
    
    codegen:
      enabled: true
      auto_download: true
      parameters:
        temperature: 0.2
```

### Example 4: Production Configuration

```yaml
# Production-ready configuration
llm:
  model_type: qwen
  validation_level: strict
  timeout_seconds: 60
  
  # Performance tuning
  cache_enabled: true
  cache_size_mb: 1000
  cache_ttl_hours: 48
  
  # Resource limits
  max_loaded_models: 1
  model_ttl_minutes: 30

streaming:
  # Conservative settings
  chunk_size: 2048
  max_concurrent_chunks: 2
  max_memory_mb: 50

# Safety settings
validate_imports: true
check_undefined_vars: true
allow_unsafe_operations: false
```

## Troubleshooting

### Configuration Not Found

**Problem**: "Configuration file not found"

**Solution**:
1. Check file path is correct
2. Ensure file has correct extension (.yaml or .json)
3. Use absolute path if relative path fails

### Validation Errors

**Problem**: "Invalid configuration: Temperature must be between 0 and 2"

**Solution**:
1. Check the specific parameter mentioned
2. Ensure value is within valid range
3. Use `config_tool validate --fix` to attempt auto-fix

### Migration Issues

**Problem**: "Unknown configuration format"

**Solution**:
1. Ensure configuration file is valid YAML/JSON
2. Check for syntax errors
3. Try manual migration with known version

### Model Not Found

**Problem**: "Model file not found"

**Solution**:
1. Check model_path directory exists
2. Ensure model file is downloaded
3. Enable auto_download if appropriate
4. Verify model_type matches available models

### Memory Issues with Streaming

**Problem**: "Out of memory during streaming"

**Solution**:
1. Reduce chunk_size
2. Decrease max_concurrent_chunks
3. Lower max_memory_mb limit
4. Enable buffer_compression

### Environment Variable Not Working

**Problem**: Environment variable override not applied

**Solution**:
1. Check variable name follows convention
2. Ensure variable is exported (not just set)
3. Verify boolean values are correct format
4. Check for typos in variable name

## Best Practices

1. **Start with Templates**: Use provided templates as starting points
2. **Validate Early**: Always validate configuration before deployment
3. **Use Environment Variables**: For deployment-specific settings
4. **Keep Backups**: Before making major changes
5. **Document Changes**: Add comments explaining non-default values
6. **Test Incrementally**: Change one setting at a time
7. **Monitor Performance**: Use memory monitoring for large files
8. **Security First**: Keep validation enabled in production

## Advanced Topics

### Custom Model Integration

To add a custom model:

1. Add model configuration:
```yaml
llm:
  model_configs:
    my_custom_model:
      name: my_custom_model
      enabled: true
      model_path: /path/to/model.gguf
      parameters:
        temperature: 0.4
```

2. Register in model registry (if using model management system)

### Configuration Hot-Reload

For development, configurations can be hot-reloaded:

```python
from pseudocode_translator.config import ConfigManager

# Enable file watching
config = ConfigManager.load()
config.enable_hot_reload()  # If implemented
```

### Programmatic Configuration

Create configurations programmatically:

```python
from pseudocode_translator.config_schema import TranslatorConfigSchema

config = TranslatorConfigSchema(
    llm={
        'model_type': 'qwen',
        'temperature': 0.3
    },
    streaming={
        'enable_streaming': True
    }
)

# Validate
errors = config.validate()
if not errors:
    config.save_to_file('my_config.yaml')
```

## Security Considerations

1. **Path Validation**: All file paths are validated to prevent directory traversal
2. **Import Validation**: Checks imports against known modules
3. **Unsafe Operations**: `eval`, `exec` are disabled by default
4. **Environment Variables**: Sanitized before use
5. **File Permissions**: Configuration files should be readable only by the user

## Version History

- **2.0** (Current) - Pydantic-based validation, environment variables
- **1.2** - Added streaming configuration
- **1.1** - Introduced LLM section
- **1.0** - Initial flat configuration

For more information, see the [API documentation](api_reference.md) or [examples directory](../examples/).