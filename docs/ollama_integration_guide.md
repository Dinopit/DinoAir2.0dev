# Ollama Integration Guide for DinoAir 2.0

## Overview

DinoAir 2.0 now includes full integration with Ollama, enabling local AI model execution for enhanced privacy and performance. This integration allows you to run powerful language models directly on your machine without sending data to external servers.

## Installation

### Prerequisites

1. **Install Ollama**
   - Visit [https://ollama.ai](https://ollama.ai) and download the installer for your operating system
   - Windows: Run the installer and follow the setup wizard
   - macOS: `brew install ollama` or download from the website
   - Linux: `curl -fsSL https://ollama.ai/install.sh | sh`

2. **Verify Installation**
   ```bash
   ollama --version
   ```

3. **Start Ollama Service**
   ```bash
   ollama serve
   ```
   The service will run on `http://localhost:11434` by default.

## Accessing the Model Tab in DinoAir

1. Launch DinoAir 2.0
2. Navigate to the **Model** tab in the main interface
3. The Ollama integration will automatically detect if the Ollama service is running
4. If auto-start is enabled (default), DinoAir will attempt to start the Ollama service automatically

## Basic Usage

### Loading a Model

1. In the Model tab, select a model from the dropdown list
2. Click "Download" if the model isn't already available locally
3. Wait for the model to download (first time only)
4. The model will automatically load once downloaded

### Example Usage

```python
# The integration handles all the complexity for you
# Simply select a model and start chatting!

# Available through DinoAir's interface:
- Text generation
- Code completion
- Question answering
- Creative writing
- Technical explanations
```

## Recommended Models

Here are some models optimized for different use cases:

### General Purpose
- **llama3.2** - Latest Llama model, excellent for general tasks
- **llama3.2:1b** - Smaller, faster variant for quick responses

### Code Generation
- **qwen2.5** - Specialized in code and technical content
- **mistral** - Strong reasoning and code capabilities

### Lightweight Options
- **phi3** - Microsoft's efficient small model
- **gemma2** - Google's optimized small model

### Model Selection Tips
- Start with `llama3.2:1b` for testing
- Use `llama3.2` for better quality responses
- Try `qwen2.5` for programming tasks
- Use `phi3` on systems with limited resources

## Configuration

The Ollama integration can be customized in `config/app_config.json`:

```json
"ollama": {
    "enabled": true,
    "default_model": "llama3.2",
    "api_base": "http://localhost:11434",
    "timeout": 300,
    "generation_params": {
        "temperature": 0.7,
        "max_tokens": 2048,
        "top_p": 0.9,
        "top_k": 40
    }
}
```

### Key Parameters
- **temperature**: Controls randomness (0.0-1.0)
- **max_tokens**: Maximum response length
- **top_p**: Nucleus sampling threshold
- **top_k**: Limits token selection pool

## Troubleshooting

### Common Issues

1. **"Ollama service not found"**
   - Ensure Ollama is installed: `ollama --version`
   - Start the service manually: `ollama serve`
   - Check if port 11434 is available

2. **"Model download failed"**
   - Check internet connection
   - Verify disk space (models can be 1-10GB)
   - Try manual download: `ollama pull llama3.2`

3. **"Slow response times"**
   - Use smaller models (e.g., llama3.2:1b)
   - Check available RAM (minimum 8GB recommended)
   - Close other applications to free resources

4. **"Connection refused"**
   - Ensure Ollama service is running
   - Check firewall settings for port 11434
   - Verify api_base URL in configuration

### Performance Tips

1. **GPU Acceleration**
   - Ollama automatically uses GPU if available
   - NVIDIA GPUs: Ensure CUDA drivers are installed
   - AMD GPUs: ROCm support varies by model

2. **Memory Management**
   - Each model requires 4-8GB RAM minimum
   - Close unused models: `ollama stop <model>`
   - Monitor usage with system tools

3. **Response Speed**
   - Smaller models respond faster
   - First response after loading is slower
   - Keep frequently used models loaded

### Debug Commands

```bash
# List downloaded models
ollama list

# Check model info
ollama show llama3.2

# Test model directly
ollama run llama3.2 "Hello, world!"

# Monitor resource usage
ollama ps
```

## Advanced Features

### Model Customization
Create custom model variants with different parameters:

```bash
# Create a custom modelfile
echo "FROM llama3.2
PARAMETER temperature 0.3
PARAMETER top_k 20" > mymodel.modelfile

# Create custom model
ollama create mymodel -f mymodel.modelfile
```

### API Integration
The Ollama integration uses the standard Ollama API:
- Endpoint: `http://localhost:11434/api/generate`
- Streaming responses supported
- Full compatibility with Ollama's features

## Support

For issues specific to:
- **DinoAir Integration**: Check the DinoAir logs in the application
- **Ollama Service**: Visit [https://github.com/ollama/ollama](https://github.com/ollama/ollama)
- **Model Issues**: Consult the model's documentation on Ollama's website

## Security Notes

- All models run locally - no data leaves your machine
- Models are stored in your user directory
- No API keys or authentication required
- Full privacy and data control

Enjoy using local AI models with DinoAir 2.0!