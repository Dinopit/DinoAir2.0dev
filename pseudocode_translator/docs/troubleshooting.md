# Troubleshooting Guide

This guide covers common issues you might encounter with the Pseudocode Translator and their solutions. If your issue isn't covered here, please check our [GitHub Issues](https://github.com/yourusername/pseudocode-translator/issues).

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Model-Related Problems](#model-related-problems)
3. [Translation Errors](#translation-errors)
4. [Performance Issues](#performance-issues)
5. [GUI Problems](#gui-problems)
6. [Configuration Issues](#configuration-issues)
7. [Memory and Resource Problems](#memory-and-resource-problems)
8. [API and Integration Issues](#api-and-integration-issues)
9. [Common Error Messages](#common-error-messages)
10. [FAQ](#faq)

## Installation Issues

### Python Version Error

**Problem**: `Python 3.8 or higher is required`

**Solution**:
```bash
# Check your Python version
python --version

# If below 3.8, install a newer version:
# Windows: Download from python.org
# macOS: brew install python@3.11
# Linux: sudo apt install python3.11

# Use specific Python version
python3.11 -m pip install pseudocode-translator
```

### Build Tools Missing

**Problem**: `Microsoft Visual C++ 14.0 or greater is required`

**Solutions**:

**Windows**:
1. Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
2. Install with "Desktop development with C++" workload
3. Restart terminal and retry installation

**macOS**:
```bash
xcode-select --install
```

**Linux**:
```bash
sudo apt update
sudo apt install build-essential python3-dev
```

### Permission Denied During Installation

**Problem**: `Permission denied` or `Access is denied`

**Solutions**:

1. **Use virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install pseudocode-translator
   ```

2. **User installation**:
   ```bash
   pip install --user pseudocode-translator
   ```

3. **Fix permissions** (Linux/macOS):
   ```bash
   sudo chown -R $USER:$USER ~/.local
   ```

### Package Conflicts

**Problem**: `ERROR: pip's dependency resolver does not currently take into account all the packages that are installed`

**Solution**:
```bash
# Create clean environment
python -m venv clean_env
source clean_env/bin/activate
pip install --upgrade pip
pip install pseudocode-translator
```

## Model-Related Problems

### Model Download Fails

**Problem**: `Failed to download model` or `Connection timeout`

**Solutions**:

1. **Check internet connection**:
   ```bash
   ping google.com
   curl -I https://huggingface.co
   ```

2. **Use proxy** (if behind firewall):
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   pseudocode-translator download-model qwen
   ```

3. **Manual download**:
   ```bash
   # Download manually
   wget https://model-url/qwen-7b-q4_k_m.gguf
   
   # Move to model directory
   mkdir -p ~/.local/share/pseudocode_translator/models
   mv qwen-7b-q4_k_m.gguf ~/.local/share/pseudocode_translator/models/
   ```

4. **Use alternative mirror**:
   ```bash
   pseudocode-translator download-model qwen --mirror china
   ```

### Model Not Found

**Problem**: `Model file not found` or `No such file or directory`

**Solutions**:

1. **Verify model exists**:
   ```bash
   pseudocode-translator list-models --installed
   ```

2. **Check model path**:
   ```bash
   # Show model directory
   pseudocode-translator config get llm.model_path
   
   # List files
   ls -la ~/.local/share/pseudocode_translator/models/
   ```

3. **Re-download model**:
   ```bash
   pseudocode-translator download-model qwen --force
   ```

### Model Loading Errors

**Problem**: `Failed to load model` or `Invalid model file`

**Solutions**:

1. **Verify file integrity**:
   ```bash
   pseudocode-translator verify-models
   ```

2. **Check file size**:
   ```bash
   # Qwen should be ~4GB
   ls -lh ~/.local/share/pseudocode_translator/models/qwen*.gguf
   ```

3. **Clear corrupted downloads**:
   ```bash
   rm ~/.local/share/pseudocode_translator/models/*.tmp
   pseudocode-translator download-model qwen --force
   ```

## Translation Errors

### Empty or No Output

**Problem**: Translation returns empty result or no code

**Solutions**:

1. **Check input format**:
   ```bash
   # Ensure file has content
   cat input.txt
   
   # Check encoding
   file -i input.txt
   ```

2. **Increase verbosity**:
   ```bash
   pseudocode-translator translate input.txt -vv
   ```

3. **Try different model**:
   ```bash
   pseudocode-translator translate input.txt --model gpt2
   ```

### Syntax Errors in Generated Code

**Problem**: Generated Python code has syntax errors

**Solutions**:

1. **Use stricter validation**:
   ```bash
   pseudocode-translator translate input.txt --validation-level strict
   ```

2. **Provide clearer instructions**:
   ```text
   # Instead of: "make function"
   # Use: "create a function called process_data that takes a list parameter and returns the sorted list"
   ```

3. **Lower temperature for more deterministic output**:
   ```bash
   pseudocode-translator translate input.txt --temperature 0.1
   ```

### Incomplete Translations

**Problem**: Translation stops mid-way or truncates output

**Solutions**:

1. **Increase max tokens**:
   ```bash
   pseudocode-translator config set llm.max_tokens 2048
   ```

2. **Enable streaming for large files**:
   ```bash
   pseudocode-translator translate large_file.txt --stream
   ```

3. **Split input into smaller chunks**:
   ```bash
   split -l 50 large_file.txt chunk_
   for f in chunk_*; do
     pseudocode-translator translate "$f" -o "${f}.py"
   done
   ```

## Performance Issues

### Slow Translation Speed

**Problem**: Translations take too long

**Solutions**:

1. **Use GPU acceleration**:
   ```bash
   # Check GPU availability
   nvidia-smi
   
   # Enable GPU layers
   pseudocode-translator config set llm.n_gpu_layers 30
   ```

2. **Switch to faster model**:
   ```bash
   # GPT-2 is faster for simple tasks
   pseudocode-translator translate input.txt --model gpt2
   ```

3. **Reduce context size**:
   ```bash
   pseudocode-translator config set llm.n_ctx 1024
   ```

4. **Use more CPU threads**:
   ```bash
   pseudocode-translator config set llm.n_threads 8
   ```

### High Memory Usage

**Problem**: `Out of memory` or system becomes unresponsive

**Solutions**:

1. **Enable streaming**:
   ```bash
   pseudocode-translator translate large_file.txt --stream
   ```

2. **Reduce batch size**:
   ```bash
   pseudocode-translator config set llm.n_batch 256
   ```

3. **Use CPU-only mode**:
   ```bash
   pseudocode-translator config set llm.n_gpu_layers 0
   ```

4. **Limit memory usage**:
   ```bash
   pseudocode-translator config set streaming.max_memory_mb 500
   ```

### GUI Freezing

**Problem**: GUI becomes unresponsive during translation

**Solutions**:

1. **Enable progress updates**:
   ```python
   translator.translation_progress.connect(update_progress_bar)
   ```

2. **Use async translation**:
   ```python
   translator.translate_async(pseudocode)
   ```

3. **Reduce GUI update frequency**:
   ```bash
   pseudocode-translator config set gui.update_interval_ms 500
   ```

## GUI Problems

### GUI Won't Launch

**Problem**: `pseudocode-translator-gui` fails to start

**Solutions**:

1. **Check display** (Linux):
   ```bash
   echo $DISPLAY
   # If empty:
   export DISPLAY=:0
   ```

2. **Install GUI dependencies**:
   ```bash
   # Reinstall with GUI support
   pip install pseudocode-translator[gui]
   
   # Linux: Install Qt dependencies
   sudo apt install libxcb-xinerama0 libxcb-cursor0
   ```

3. **Try fallback mode**:
   ```bash
   pseudocode-translator-gui --no-gpu --safe-mode
   ```

### Black or Corrupted Display

**Problem**: GUI shows black screen or corrupted graphics

**Solutions**:

1. **Disable hardware acceleration**:
   ```bash
   export QT_QUICK_BACKEND=software
   pseudocode-translator-gui
   ```

2. **Update graphics drivers**:
   - Windows: Update via Device Manager
   - Linux: `sudo apt install mesa-utils`
   - macOS: Update system

3. **Use different rendering backend**:
   ```bash
   pseudocode-translator-gui --renderer software
   ```

### Font or Scaling Issues

**Problem**: Text too small/large or fonts missing

**Solutions**:

1. **Adjust DPI settings**:
   ```bash
   export QT_SCALE_FACTOR=1.5
   pseudocode-translator-gui
   ```

2. **Change font size**:
   ```bash
   pseudocode-translator config set gui.font_size 14
   ```

3. **Install missing fonts** (Linux):
   ```bash
   sudo apt install fonts-dejavu-core
   ```

## Configuration Issues

### Configuration Not Saving

**Problem**: Changes to configuration don't persist

**Solutions**:

1. **Check file permissions**:
   ```bash
   ls -la ~/.config/pseudocode_translator/
   chmod 644 ~/.config/pseudocode_translator/config.json
   ```

2. **Validate JSON syntax**:
   ```bash
   pseudocode-translator config validate
   ```

3. **Reset to defaults**:
   ```bash
   pseudocode-translator config reset
   ```

### Invalid Configuration

**Problem**: `Configuration validation failed`

**Solutions**:

1. **Fix specific errors**:
   ```bash
   # Show validation errors
   pseudocode-translator config validate --verbose
   ```

2. **Use configuration wizard**:
   ```bash
   pseudocode-translator config --wizard
   ```

3. **Restore from backup**:
   ```bash
   cp ~/.config/pseudocode_translator/config.json.bak ~/.config/pseudocode_translator/config.json
   ```

## Memory and Resource Problems

### Memory Leaks

**Problem**: Memory usage grows over time

**Solutions**:

1. **Enable automatic cleanup**:
   ```python
   translator.config.llm.model_ttl_minutes = 30
   ```

2. **Manually free resources**:
   ```python
   translator.shutdown()
   ```

3. **Monitor memory usage**:
   ```bash
   pseudocode-translator translate input.txt --monitor-memory
   ```

### Disk Space Issues

**Problem**: `No space left on device`

**Solutions**:

1. **Clean cache**:
   ```bash
   pseudocode-translator cache clean
   ```

2. **Remove old models**:
   ```bash
   pseudocode-translator list-models --installed
   pseudocode-translator remove-model old-model
   ```

3. **Change model directory**:
   ```bash
   pseudocode-translator config set llm.model_path /larger/disk/models
   ```

## API and Integration Issues

### Import Errors

**Problem**: `ImportError: cannot import name 'PseudocodeTranslatorAPI'`

**Solutions**:

1. **Verify installation**:
   ```python
   import pseudocode_translator
   print(pseudocode_translator.__version__)
   ```

2. **Check Python path**:
   ```python
   import sys
   print(sys.path)
   ```

3. **Reinstall package**:
   ```bash
   pip uninstall pseudocode-translator
   pip install pseudocode-translator
   ```

### API Response Errors

**Problem**: API calls fail or return errors

**Solutions**:

1. **Check initialization**:
   ```python
   translator = PseudocodeTranslatorAPI()
   # Wait for model to load
   translator.model_initialized.wait()
   ```

2. **Handle errors properly**:
   ```python
   result = translator.translate(pseudocode)
   if not result.success:
       print(f"Errors: {result.errors}")
   ```

3. **Use debug mode**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Common Error Messages

### "CUDA out of memory"

**Solution**:
```bash
# Reduce GPU layers
pseudocode-translator config set llm.n_gpu_layers 10

# Or use CPU only
pseudocode-translator config set llm.n_gpu_layers 0
```

### "Tokenization error"

**Solution**:
```bash
# Reduce input size
head -n 100 input.txt > smaller_input.txt
pseudocode-translator translate smaller_input.txt

# Or enable streaming
pseudocode-translator translate input.txt --stream
```

### "SSL certificate verify failed"

**Solution**:
```bash
# Update certificates
pip install --upgrade certifi

# Or disable verification (not recommended)
export PYTHONHTTPSVERIFY=0
```

### "Module 'llama_cpp' has no attribute"

**Solution**:
```bash
# Reinstall llama-cpp-python
pip uninstall llama-cpp-python
pip install llama-cpp-python --no-cache-dir
```

## FAQ

### Q: Why is my translation different each time?

**A**: Language models have randomness. To get consistent results:
```bash
pseudocode-translator translate input.txt --temperature 0.0 --seed 42
```

### Q: Can I use custom models?

**A**: Yes! Place your GGUF model in the models directory and configure:
```bash
pseudocode-translator config set llm.model_type custom
pseudocode-translator config set llm.model_file your-model.gguf
```

### Q: How do I speed up translations?

**A**: Try these optimizations:
1. Use GPU: `config set llm.n_gpu_layers 30`
2. Use faster model: `--model gpt2`
3. Enable caching: `config set llm.cache_enabled true`
4. Increase threads: `config set llm.n_threads 16`

### Q: Is my code sent to the cloud?

**A**: No! Everything runs locally on your machine. No data leaves your computer.

### Q: Can I translate to languages other than Python?

**A**: Currently, only Python is supported. Other languages are planned for future releases.

### Q: How do I report bugs?

**A**: 
1. Run diagnostics: `pseudocode-translator diagnose > diagnostic.txt`
2. Create issue on [GitHub](https://github.com/yourusername/pseudocode-translator/issues)
3. Include diagnostic.txt and steps to reproduce

### Q: Can I contribute?

**A**: Yes! See our [Contributing Guide](https://github.com/yourusername/pseudocode-translator/blob/main/CONTRIBUTING.md)

## Still Need Help?

If your issue isn't resolved:

1. **Search existing issues**: [GitHub Issues](https://github.com/yourusername/pseudocode-translator/issues)
2. **Join our community**: [Discord Server](https://discord.gg/pseudocode)
3. **Check the wiki**: [GitHub Wiki](https://github.com/yourusername/pseudocode-translator/wiki)
4. **Contact support**: support@pseudocode-translator.dev

Remember to include:
- Your OS and Python version
- Output of `pseudocode-translator diagnose`
- Complete error messages
- Steps to reproduce the issue

Happy coding! 🚀