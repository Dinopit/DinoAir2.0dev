# Pseudocode Translator Setup Guide

This comprehensive guide will walk you through installing and configuring the Pseudocode Translator on your system. We'll cover everything from basic requirements to advanced GPU setup.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Methods](#installation-methods)
3. [Platform-Specific Instructions](#platform-specific-instructions)
4. [Model Setup](#model-setup)
5. [Configuration](#configuration)
6. [GPU Acceleration](#gpu-acceleration)
7. [Verification](#verification)
8. [Development Setup](#development-setup)
9. [Troubleshooting Installation](#troubleshooting-installation)
10. [Upgrading](#upgrading)

## System Requirements

### Minimum Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **RAM**: 8GB (16GB recommended)
- **Storage**: 10GB free space
- **CPU**: 4 cores (8 cores recommended)
- **Internet**: Required for initial model download

### Recommended Requirements

- **RAM**: 16GB or more
- **Storage**: 20GB free space (for multiple models)
- **CPU**: 8+ cores with AVX2 support
- **GPU**: NVIDIA GPU with 6GB+ VRAM (optional, for acceleration)

### Python Dependencies

The tool requires these Python packages (automatically installed):
- `llama-cpp-python>=0.2.0`
- `PySide6>=6.5.0`
- `numpy>=1.21.0`
- `pydantic>=2.0.0`
- `requests>=2.28.0`
- `tqdm>=4.65.0`

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
# Create virtual environment (recommended)
python -m venv pseudocode-env
source pseudocode-env/bin/activate  # On Windows: pseudocode-env\Scripts\activate

# Install the package
pip install pseudocode-translator

# Verify installation
pseudocode-translator --version
```

### Method 2: Install from Source

```bash
# Clone repository
git clone https://github.com/yourusername/pseudocode-translator.git
cd pseudocode-translator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### Method 3: Using Docker

```dockerfile
# Dockerfile provided in repository
docker build -t pseudocode-translator .
docker run -it -v $(pwd):/workspace pseudocode-translator
```

## Platform-Specific Instructions

### Windows

#### Prerequisites

1. **Install Python 3.8+**:
   ```powershell
   # Using Windows Package Manager
   winget install Python.Python.3.11
   
   # Or download from python.org
   ```

2. **Install Visual C++ Redistributables**:
   - Download from [Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)
   - Required for llama-cpp-python

3. **Install Build Tools** (for GPU support):
   ```powershell
   # Install Visual Studio Build Tools
   winget install Microsoft.VisualStudio.2022.BuildTools
   ```

#### Installation Steps

```powershell
# Open PowerShell as Administrator
# Create installation directory
mkdir C:\PseudocodeTranslator
cd C:\PseudocodeTranslator

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install package
pip install pseudocode-translator

# Add to PATH (optional)
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\PseudocodeTranslator\venv\Scripts", [EnvironmentVariableTarget]::User)
```

### macOS

#### Prerequisites

1. **Install Homebrew** (if not installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python**:
   ```bash
   brew install python@3.11
   ```

3. **Install Xcode Command Line Tools**:
   ```bash
   xcode-select --install
   ```

#### Installation Steps

```bash
# Create installation directory
mkdir -p ~/pseudocode-translator
cd ~/pseudocode-translator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install pseudocode-translator

# Create alias (optional)
echo 'alias pseudocode="~/pseudocode-translator/venv/bin/pseudocode-translator"' >> ~/.zshrc
source ~/.zshrc
```

### Linux (Ubuntu/Debian)

#### Prerequisites

```bash
# Update package list
sudo apt update

# Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip build-essential

# Install additional libraries
sudo apt install -y libopenblas-dev liblapack-dev
```

#### Installation Steps

```bash
# Create installation directory
mkdir -p ~/pseudocode-translator
cd ~/pseudocode-translator

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package
pip install pseudocode-translator

# Create system-wide command (optional)
sudo ln -s ~/pseudocode-translator/venv/bin/pseudocode-translator /usr/local/bin/
```

## Model Setup

### Automatic Model Download

The default Qwen model downloads automatically on first use:

```bash
# First translation triggers download
pseudocode-translator translate -c "print hello world"
# Downloads Qwen-7B model (~4GB)
```

### Manual Model Download

Download specific models:

```bash
# List available models
pseudocode-translator list-models

# Download specific model
pseudocode-translator download-model qwen
pseudocode-translator download-model gpt2
pseudocode-translator download-model codegen

# Download all models
pseudocode-translator download-model --all
```

### Model Storage Locations

Models are stored in:
- **Windows**: `%APPDATA%\pseudocode_translator\models\`
- **macOS**: `~/Library/Application Support/pseudocode_translator/models/`
- **Linux**: `~/.local/share/pseudocode_translator/models/`

### Custom Model Location

Set custom model directory:

```bash
# Set environment variable
export PSEUDOCODE_TRANSLATOR_MODEL_PATH=/path/to/models

# Or in configuration
pseudocode-translator config set llm.model_path /path/to/models
```

### Model Verification

```bash
# Verify model integrity
pseudocode-translator verify-models

# Check specific model
pseudocode-translator verify-models --model qwen

# Re-download corrupted models
pseudocode-translator download-model qwen --force
```

## Configuration

### Initial Configuration

Run the configuration wizard:

```bash
pseudocode-translator config --wizard
```

### Manual Configuration

Edit configuration directly:

```bash
# Open configuration in editor
pseudocode-translator config edit

# Or edit manually
# Windows: %APPDATA%\pseudocode_translator\config.json
# macOS: ~/Library/Application Support/pseudocode_translator/config.json
# Linux: ~/.config/pseudocode_translator/config.json
```

### Essential Configuration

```json
{
  "llm": {
    "model_type": "qwen",
    "model_path": "auto",
    "n_ctx": 2048,
    "n_threads": 8,
    "temperature": 0.3,
    "max_tokens": 1024
  },
  "streaming": {
    "enable_streaming": true,
    "auto_enable_threshold": 102400,
    "chunk_size": 4096
  },
  "validation": {
    "validation_level": "normal",
    "check_undefined_vars": true,
    "validate_imports": true
  },
  "gui": {
    "theme": "dark",
    "font_size": 12,
    "syntax_highlighting": true
  }
}
```

### Environment Variables

Override configuration with environment variables:

```bash
# Model selection
export PSEUDOCODE_TRANSLATOR_LLM_MODEL_TYPE=gpt2

# Performance settings
export PSEUDOCODE_TRANSLATOR_LLM_N_THREADS=16
export PSEUDOCODE_TRANSLATOR_LLM_N_GPU_LAYERS=20

# Validation
export PSEUDOCODE_TRANSLATOR_VALIDATION_LEVEL=strict
```

## GPU Acceleration

### NVIDIA GPU Setup

#### 1. Install CUDA Toolkit

**Windows**:
```powershell
# Download CUDA 11.8 or 12.1 from NVIDIA
# https://developer.nvidia.com/cuda-downloads
```

**Linux**:
```bash
# Ubuntu/Debian
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install cuda-11-8
```

**macOS**: Metal support is automatic, no CUDA needed

#### 2. Install GPU-enabled llama-cpp-python

```bash
# Uninstall CPU version
pip uninstall llama-cpp-python

# Install GPU version
# For CUDA 11.8
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# For CUDA 12.1
CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.1/bin/nvcc" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

#### 3. Configure GPU Layers

```json
{
  "llm": {
    "n_gpu_layers": 30  // Adjust based on GPU memory
  }
}
```

Or via command line:
```bash
pseudocode-translator config set llm.n_gpu_layers 30
```

### AMD GPU Setup (ROCm)

```bash
# Install ROCm (Linux only)
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_5.7.50700-1_all.deb
sudo apt install ./amdgpu-install_5.7.50700-1_all.deb
sudo amdgpu-install --rocm

# Install ROCm-enabled llama-cpp-python
CMAKE_ARGS="-DLLAMA_HIPBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Apple Silicon (M1/M2/M3)

Metal support is automatic:

```bash
# Install with Metal support
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# Configure to use GPU
pseudocode-translator config set llm.n_gpu_layers 1
```

## Verification

### Basic Verification

```bash
# Check installation
pseudocode-translator --version

# Test translation
echo "create a hello world function" | pseudocode-translator

# Run diagnostics
pseudocode-translator diagnose
```

### Comprehensive Test

```python
# test_installation.py
from pseudocode_translator import PseudocodeTranslatorAPI

# Test API
translator = PseudocodeTranslatorAPI()
result = translator.translate("create a function that adds two numbers")
print(f"Success: {result.success}")
print(f"Code: {result.code}")

# Test GUI
from pseudocode_translator.gui import launch_gui
# launch_gui()  # Uncomment to test GUI
```

Run test:
```bash
python test_installation.py
```

### Performance Benchmark

```bash
# Run performance tests
pseudocode-translator benchmark

# Test specific model
pseudocode-translator benchmark --model qwen

# Test with GPU
pseudocode-translator benchmark --gpu
```

## Development Setup

### Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/pseudocode-translator.git
cd pseudocode-translator

# Create development environment
python -m venv venv-dev
source venv-dev/bin/activate  # Windows: venv-dev\Scripts\activate

# Install in editable mode with all dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

### Development Dependencies

```bash
# Testing
pip install pytest pytest-cov pytest-asyncio

# Code quality
pip install black flake8 mypy isort

# Documentation
pip install sphinx sphinx-rtd-theme

# Debugging
pip install ipdb pytest-timeout
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pseudocode_translator

# Run specific tests
pytest tests/test_translator.py

# Run integration tests
pytest tests/integration/
```

## Troubleshooting Installation

### Common Issues

#### 1. Python Version Error

**Error**: `Python 3.8+ is required`

**Solution**:
```bash
# Check Python version
python --version

# Use specific Python version
python3.11 -m pip install pseudocode-translator
```

#### 2. Build Tools Missing

**Error**: `Microsoft Visual C++ 14.0 or greater is required`

**Solution**:
- Windows: Install Visual Studio Build Tools
- Linux: `sudo apt install build-essential`
- macOS: `xcode-select --install`

#### 3. Permission Denied

**Error**: `Permission denied` during installation

**Solution**:
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install pseudocode-translator

# Or user installation
pip install --user pseudocode-translator
```

#### 4. Model Download Fails

**Error**: `Failed to download model`

**Solution**:
```bash
# Check internet connection
ping google.com

# Use alternative download method
wget https://model-url -O ~/.local/share/pseudocode_translator/models/qwen.gguf

# Set proxy if needed
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

#### 5. GPU Not Detected

**Error**: `GPU acceleration not available`

**Solution**:
```bash
# Check CUDA installation
nvidia-smi
nvcc --version

# Reinstall GPU version
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir --verbose
```

### Getting Help

If you encounter issues:

1. **Check logs**:
   ```bash
   pseudocode-translator --debug translate test.txt
   ```

2. **Run diagnostics**:
   ```bash
   pseudocode-translator diagnose --verbose
   ```

3. **Report issue**:
   - Include output of `pseudocode-translator diagnose`
   - Include Python version: `python --version`
   - Include OS information
   - Include error messages

## Upgrading

### Upgrade Package

```bash
# Upgrade to latest version
pip install --upgrade pseudocode-translator

# Upgrade to specific version
pip install pseudocode-translator==1.2.0

# Check for updates
pseudocode-translator check-updates
```

### Migrate Configuration

After major upgrades:

```bash
# Backup current configuration
pseudocode-translator config backup

# Run migration
pseudocode-translator config migrate

# Verify configuration
pseudocode-translator config validate
```

### Update Models

```bash
# Check for model updates
pseudocode-translator list-models --check-updates

# Update specific model
pseudocode-translator download-model qwen --force

# Update all models
pseudocode-translator update-models
```

## Next Steps

Now that you have the Pseudocode Translator installed and configured:

1. **Read the [Quick Start Guide](quick_start.md)** to begin translating
2. **Explore the [User Guide](user_guide.md)** for detailed usage instructions
3. **Check out [Examples](../examples/)** for inspiration
4. **Join our community** for tips and support

Happy translating! 🚀