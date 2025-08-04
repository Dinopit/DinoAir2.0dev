# Adding New Models to the Pseudocode Translator

This guide explains how to add support for new language models to the Pseudocode Translator's flexible model management system.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Model Implementation Details](#model-implementation-details)
5. [Testing Your Model](#testing-your-model)
6. [Configuration](#configuration)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The Pseudocode Translator uses a plugin-based architecture that makes it easy to add new language models. Models are automatically discovered and registered at runtime using Python decorators.

### Key Components

- **BaseModel**: Abstract base class that all models must inherit from
- **ModelRegistry**: Central registry for model discovery and management
- **ModelManager**: Handles model lifecycle, loading, and resource management
- **@register_model**: Decorator for automatic model registration

## Quick Start

Here's the minimal code needed to add a new model:

```python
# pseudocode_translator/models/mymodel.py

from pathlib import Path
from typing import Optional, Dict, Any

from .base import BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
from .registry import register_model


@register_model(name="mymodel", aliases=["my-model", "mm"])
class MyModel(BaseModel):
    """My custom model implementation"""
    
    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="mymodel",
            display_name="My Model",
            version="1.0",
            description="My custom model for code generation",
            author="Your Name",
            license="MIT",
            format=ModelFormat.GGUF,  # or PYTORCH, ONNX, etc.
            filename_pattern="mymodel*.gguf",
            download_url="https://example.com/mymodel.gguf",
            sha256_checksum="abc123..."  # Optional but recommended
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supported_languages=["python"],
            max_context_length=4096,
            min_memory_gb=4.0,
            recommended_memory_gb=8.0,
            model_size_gb=3.5,
            supports_gpu=True,
            requires_gpu=False
        )
    
    def initialize(self, model_path: Path, **kwargs) -> None:
        """Load the model from disk"""
        # Your model loading code here
        self._model = load_my_model(model_path)
        self._initialized = True
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        # Your generation code here
        return self._model.generate(prompt, **kwargs)
    
    def translate_instruction(self, instruction: str, 
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Convert natural language to code"""
        prompt = self._build_prompt(instruction, context)
        return self.generate(prompt, max_tokens=512)
```

## Step-by-Step Guide

### 1. Create a New Model File

Create a new Python file in the `pseudocode_translator/models/` directory:

```bash
touch pseudocode_translator/models/mymodel.py
```

### 2. Import Required Components

```python
from pathlib import Path
from typing import Optional, Dict, Any, List

from .base import BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
from .registry import register_model
```

### 3. Define Your Model Class

Your model class must:
- Inherit from `BaseModel`
- Use the `@register_model` decorator
- Implement all required properties and methods

```python
@register_model(name="mymodel", aliases=["my-model", "mm"])
class MyModel(BaseModel):
    """Documentation for your model"""
    pass
```

### 4. Implement Required Properties

#### metadata Property

Provides information about your model:

```python
@property
def metadata(self) -> ModelMetadata:
    return ModelMetadata(
        name="mymodel",                    # Unique identifier
        display_name="My Model v1.0",      # Human-readable name
        version="1.0.0",                   # Version string
        description="Description here",     # What the model does
        author="Your Name",                # Model author(s)
        license="Apache-2.0",              # License type
        homepage="https://...",            # Optional: project URL
        format=ModelFormat.GGUF,           # File format
        filename_pattern="*.gguf",         # File matching pattern
        download_url="https://...",        # Optional: download URL
        sha256_checksum="...",             # Optional: file checksum
        tags=["code", "python"],           # Optional: tags
        citation="@article{...}"           # Optional: citation
    )
```

#### capabilities Property

Defines what your model can do and its requirements:

```python
@property
def capabilities(self) -> ModelCapabilities:
    return ModelCapabilities(
        # Language support
        supported_languages=["python", "javascript"],
        max_context_length=4096,
        
        # Memory requirements
        min_memory_gb=4.0,
        recommended_memory_gb=8.0,
        model_size_gb=3.5,
        
        # GPU support
        supports_gpu=True,
        requires_gpu=False,
        
        # Features
        supports_code_completion=True,
        supports_translation=True,
        supports_refinement=True,
        supports_streaming=False,
        
        # Performance hints (optional)
        tokens_per_second_cpu=20.0,
        tokens_per_second_gpu=100.0
    )
```

### 5. Implement Required Methods

#### initialize Method

Load and prepare your model:

```python
def initialize(self, model_path: Path, **kwargs) -> None:
    """Initialize the model"""
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    # Example: Loading different model types
    if self.metadata.format == ModelFormat.GGUF:
        from llama_cpp import Llama
        self._model = Llama(
            model_path=str(model_path),
            n_ctx=self.capabilities.max_context_length,
            n_threads=kwargs.get('n_threads', 4),
            n_gpu_layers=kwargs.get('n_gpu_layers', 0)
        )
    elif self.metadata.format == ModelFormat.PYTORCH:
        import torch
        self._model = torch.load(model_path)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model.to(self._device)
    
    self._initialized = True
```

#### generate Method

Core text generation functionality:

```python
def generate(self,
             prompt: str,
             max_tokens: int = 512,
             temperature: float = 0.3,
             top_p: float = 0.9,
             top_k: int = 40,
             stop_sequences: Optional[List[str]] = None,
             **kwargs) -> str:
    """Generate text from prompt"""
    if not self._initialized:
        raise RuntimeError("Model not initialized")
    
    # Example implementation
    response = self._model.generate(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        stop=stop_sequences or []
    )
    
    return self._extract_text(response)
```

#### translate_instruction Method

Convert natural language to code:

```python
def translate_instruction(self,
                          instruction: str,
                          context: Optional[Dict[str, Any]] = None) -> str:
    """Translate instruction to code"""
    # Build a prompt for code generation
    prompt = self._build_code_prompt(instruction, context)
    
    # Generate with code-specific parameters
    code = self.generate(
        prompt,
        max_tokens=1024,
        temperature=0.2,  # Lower temperature for code
        stop_sequences=["```", "\n\n\n"]
    )
    
    return self._clean_code_output(code)
```

### 6. Optional Method Overrides

#### refine_code Method

Improve existing code based on feedback:

```python
def refine_code(self,
                code: str,
                error_context: str,
                max_attempts: int = 1) -> str:
    """Fix code based on error feedback"""
    prompt = f"""Fix the following Python code based on the error:

Code:
```python
{code}
```

Error:
{error_context}

Fixed code:
```python
"""
    
    refined = self.generate(prompt, temperature=0.1)
    return self._extract_code(refined)
```

#### Streaming Support

If your model supports streaming:

```python
def supports_streaming(self) -> bool:
    return True

def stream_generate(self,
                    prompt: str,
                    callback: Callable[[str], None],
                    **kwargs) -> None:
    """Stream generation token by token"""
    for token in self._model.generate_stream(prompt, **kwargs):
        callback(token)
```

## Model Implementation Details

### Helper Methods

Add private helper methods for common tasks:

```python
def _build_code_prompt(self, instruction: str, context: Optional[Dict[str, Any]]) -> str:
    """Build a prompt optimized for code generation"""
    prompt_parts = []
    
    # Add system message if supported
    if self._supports_system_message():
        prompt_parts.append(
            "You are an expert Python programmer. "
            "Convert the following instruction to clean, efficient Python code."
        )
    
    # Add context if provided
    if context:
        if "previous_code" in context:
            prompt_parts.append(f"Previous code:\n{context['previous_code']}\n")
        if "imports" in context:
            prompt_parts.append(f"Available imports:\n{context['imports']}\n")
    
    # Add the instruction
    prompt_parts.append(f"Instruction: {instruction}\n")
    prompt_parts.append("Python code:")
    
    return "\n".join(prompt_parts)

def _extract_code(self, response: str) -> str:
    """Extract code from model response"""
    # Remove markdown code blocks if present
    if "```python" in response:
        start = response.find("```python") + 9
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()
    
    # Remove any leading/trailing whitespace
    return response.strip()
```

### Error Handling

Implement robust error handling:

```python
def generate(self, prompt: str, **kwargs) -> str:
    try:
        response = self._model.generate(prompt, **kwargs)
        return response
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        # Optionally retry with different parameters
        if kwargs.get('temperature', 0.3) > 0.1:
            kwargs['temperature'] = 0.1
            return self.generate(prompt, **kwargs)
        raise RuntimeError(f"Model generation failed: {e}")
```

## Testing Your Model

### 1. Unit Tests

Create a test file `tests/test_mymodel.py`:

```python
import pytest
from pathlib import Path
from pseudocode_translator.models.mymodel import MyModel

class TestMyModel:
    def test_metadata(self):
        model = MyModel({})
        meta = model.metadata
        assert meta.name == "mymodel"
        assert meta.format == ModelFormat.GGUF
    
    def test_capabilities(self):
        model = MyModel({})
        caps = model.capabilities
        assert "python" in caps.supported_languages
        assert caps.max_context_length > 0
    
    @patch('path.to.model.loader')
    def test_initialize(self, mock_loader):
        model = MyModel({})
        model.initialize(Path("/test/model.gguf"))
        assert model._initialized
    
    def test_translate_instruction(self):
        model = MyModel({})
        # Mock the model
        model._model = Mock()
        model._initialized = True
        
        code = model.translate_instruction("print hello world")
        assert "print" in code
```

### 2. Integration Testing

Test with the model manager:

```python
from pseudocode_translator.models import ModelManager

manager = ModelManager()
model = manager.load_model("mymodel")
result = model.translate_instruction("create a function that adds two numbers")
print(result)
```

### 3. Manual Testing

```python
# Quick test script
from pseudocode_translator.llm_interface import LLMInterface
from pseudocode_translator.config import LLMConfig

config = LLMConfig(model_type="mymodel")
interface = LLMInterface(config)
interface.initialize_model()

code = interface.translate("print the current date and time")
print(code)
```

## Configuration

### 1. Model-Specific Configuration

Add your model to configuration files:

```yaml
# config.yaml
llm:
  model_type: mymodel
  model_configs:
    mymodel:
      model_path: "./models/mymodel/model.gguf"
      temperature: 0.3
      max_tokens: 1024
      parameters:
        # Model-specific parameters
        rope_freq_base: 10000
        rope_freq_scale: 1.0
```

### 2. Download Configuration

If your model supports auto-download:

```yaml
llm:
  auto_download: true
  model_configs:
    mymodel:
      auto_download: true
      download_url: "https://huggingface.co/..."
      checksum: "sha256:abc123..."
```

## Best Practices

### 1. Memory Management

```python
def shutdown(self) -> None:
    """Clean up resources"""
    if hasattr(self, '_model'):
        # Clean up model resources
        if hasattr(self._model, 'close'):
            self._model.close()
        del self._model
    
    # Clear any caches
    if hasattr(self, '_cache'):
        self._cache.clear()
    
    self._initialized = False
```

### 2. Validation

```python
def validate_config(self) -> List[str]:
    """Validate model configuration"""
    issues = super().validate_config()
    
    # Add model-specific validation
    if 'special_param' in self.config:
        if self.config['special_param'] < 0:
            issues.append("special_param must be positive")
    
    return issues
```

### 3. Performance Optimization

```python
def warmup(self) -> None:
    """Warm up the model"""
    if not self._initialized:
        raise RuntimeError("Model not initialized")
    
    # Generate a short response to warm up caches
    try:
        self.generate("# Hello", max_tokens=1)
    except Exception:
        pass  # Warmup failures are non-critical
```

### 4. Logging

```python
import logging

logger = logging.getLogger(__name__)

class MyModel(BaseModel):
    def initialize(self, model_path: Path, **kwargs) -> None:
        logger.info(f"Initializing {self.metadata.display_name}")
        logger.debug(f"Model path: {model_path}")
        logger.debug(f"Parameters: {kwargs}")
        
        # ... initialization code ...
        
        logger.info("Model initialized successfully")
```

## Troubleshooting

### Common Issues

1. **Model not found in registry**
   - Ensure your file is in the `models/` directory
   - Check that you're using the `@register_model` decorator
   - Verify the model name doesn't conflict with existing models

2. **Import errors**
   - Make sure all dependencies are installed
   - Use relative imports for model components
   - Check that `__init__.py` isn't blocking your module

3. **Model fails to load**
   - Verify the model file exists at the expected path
   - Check file permissions
   - Ensure the file format matches what your code expects

4. **Generation errors**
   - Validate that the model is initialized before use
   - Check that prompts are within context length limits
   - Ensure generation parameters are valid

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pseudocode_translator.models')
```

### Testing Model Registration

```python
from pseudocode_translator.models.registry import list_available_models

print("Available models:", list_available_models())
```

## Example: Complete Model Implementation

Here's a complete example implementing a hypothetical model:

```python
"""
Custom model implementation for the Pseudocode Translator
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
import json

from .base import BaseModel, ModelCapabilities, ModelMetadata, ModelFormat
from .registry import register_model

logger = logging.getLogger(__name__)


@register_model(name="customllm", aliases=["custom", "cllm"])
class CustomLLM(BaseModel):
    """
    Custom LLM implementation for code generation
    
    This model specializes in Python code generation with
    support for multiple programming paradigms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._tokenizer = None
        self._generation_cache = {}
    
    @property
    def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            name="customllm",
            display_name="Custom LLM v2.0",
            version="2.0.0",
            description="Specialized model for Python code generation",
            author="AI Research Team",
            license="Apache-2.0",
            homepage="https://github.com/example/customllm",
            format=ModelFormat.PYTORCH,
            filename_pattern="model.pt",
            download_url="https://example.com/models/customllm-v2.pt",
            sha256_checksum="d2a84f4b23b5c71b3f7c2b9a3e4f5678...",
            tags=["code-generation", "python", "instruction-following"],
            citation="@inproceedings{custom2024,title={CustomLLM},...}"
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supported_languages=["python", "javascript", "java"],
            max_context_length=8192,
            supports_code_completion=True,
            supports_translation=True,
            supports_refinement=True,
            supports_streaming=True,
            min_memory_gb=6.0,
            recommended_memory_gb=12.0,
            supports_gpu=True,
            requires_gpu=False,
            model_size_gb=5.5,
            quantization_bits=16,
            is_instruction_tuned=True,
            tokens_per_second_cpu=15.0,
            tokens_per_second_gpu=150.0
        )
    
    def initialize(self, model_path: Path, **kwargs) -> None:
        """Initialize the model and tokenizer"""
        logger.info(f"Initializing CustomLLM from {model_path}")
        
        try:
            # Example: Load a PyTorch model
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Determine device
            device = kwargs.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Using device: {device}")
            
            # Load model and tokenizer
            model_dir = model_path.parent
            self._model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                torch_dtype=torch.float16 if device == 'cuda' else torch.float32,
                device_map='auto' if device == 'cuda' else None
            )
            self._tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self._device = device
            
            # Set up generation config
            self._generation_config = {
                'max_new_tokens': kwargs.get('max_tokens', 512),
                'temperature': kwargs.get('temperature', 0.3),
                'top_p': kwargs.get('top_p', 0.9),
                'do_sample': True,
                'pad_token_id': self._tokenizer.pad_token_id,
                'eos_token_id': self._tokenizer.eos_token_id,
            }
            
            self._initialized = True
            logger.info("CustomLLM initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise RuntimeError(f"Model initialization failed: {e}")
    
    def generate(self,
                 prompt: str,
                 max_tokens: int = 512,
                 temperature: float = 0.3,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 stop_sequences: Optional[List[str]] = None,
                 **kwargs) -> str:
        """Generate text using the model"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        try:
            # Tokenize input
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
            
            # Update generation config
            gen_config = self._generation_config.copy()
            gen_config.update({
                'max_new_tokens': max_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'top_k': top_k,
            })
            
            # Generate
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    **gen_config
                )
            
            # Decode
            generated = self._tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[1]:],
                skip_special_tokens=True
            )
            
            # Handle stop sequences
            if stop_sequences:
                for stop in stop_sequences:
                    if stop in generated:
                        generated = generated[:generated.index(stop)]
            
            return generated.strip()
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise RuntimeError(f"Text generation failed: {e}")
    
    def translate_instruction(self,
                              instruction: str,
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Translate natural language instruction to code"""
        # Build specialized prompt for code generation
        prompt = self._build_code_generation_prompt(instruction, context)
        
        # Generate with code-optimized parameters
        code = self.generate(
            prompt,
            max_tokens=1024,
            temperature=0.2,  # Lower temperature for more deterministic code
            top_p=0.95,
            stop_sequences=["```", "\n\n\n", "# End"]
        )
        
        # Clean and validate the generated code
        return self._postprocess_code(code)
    
    def refine_code(self,
                    code: str,
                    error_context: str,
                    max_attempts: int = 1) -> str:
        """Refine code based on error feedback"""
        prompt = f"""You are an expert Python programmer. Fix the following code based on the error message.

Original code:
```python
{code}
```

Error message:
{error_context}

Provide the corrected code:
```python
"""
        
        refined = self.generate(
            prompt,
            max_tokens=1024,
            temperature=0.1,  # Very low temperature for fixes
            stop_sequences=["```"]
        )
        
        return self._postprocess_code(refined)
    
    def supports_streaming(self) -> bool:
        """Check if model supports streaming"""
        return True
    
    def stream_generate(self,
                        prompt: str,
                        callback: Callable[[str], None],
                        **kwargs) -> None:
        """Stream generation token by token"""
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        try:
            # Tokenize input
            inputs = self._tokenizer(prompt, return_tensors="pt").to(self._device)
            
            # Stream generation
            from transformers import TextIteratorStreamer
            
            streamer = TextIteratorStreamer(
                self._tokenizer,
                skip_prompt=True,
                skip_special_tokens=True
            )
            
            # Generate in a separate thread
            import threading
            
            gen_kwargs = {
                **inputs,
                'streamer': streamer,
                'max_new_tokens': kwargs.get('max_tokens', 512),
                'temperature': kwargs.get('temperature', 0.3),
                'do_sample': True,
            }
            
            thread = threading.Thread(
                target=self._model.generate,
                kwargs=gen_kwargs
            )
            thread.start()
            
            # Stream tokens
            for token in streamer:
                callback(token)
            
            thread.join()
            
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise RuntimeError(f"Streaming generation failed: {e}")
    
    def _build_code_generation_prompt(self,
                                      instruction: str,
                                      context: Optional[Dict[str, Any]]) -> str:
        """Build an optimized prompt for code generation"""
        prompt_parts = [
            "You are an expert Python programmer. Generate clean, efficient, and well-documented code.",
            ""
        ]
        
        # Add context if available
        if context:
            if "language" in context:
                prompt_parts[0] = prompt_parts[0].replace("Python", context["language"])
            
            if "style_guide" in context:
                prompt_parts.append(f"Follow this style guide: {context['style_guide']}")
            
            if "imports" in context:
                prompt_parts.append(f"Available imports: {', '.join(context['imports'])}")
            
            if "previous_code" in context:
                prompt_parts.append(f"Previous code context:\n```python\n{context['previous_code']}\n```")
            
            prompt_parts.append("")
        
        # Add the instruction
        prompt_parts.extend([
            f"Task: {instruction}",
            "",
            "Generated code:",
            "```python"
        ])
        
        return "\n".join(prompt_parts)
    
    def _postprocess_code(self, code: str) -> str:
        """Clean and validate generated code"""
        # Remove any markdown formatting
        if "```" in code:
            # Extract code from markdown block
            lines = code.split('\n')
            in_code_block = False
            code_lines = []
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or (not line.startswith("```") and code_lines):
                    code_lines.append(line)
            
            code = '\n'.join(code_lines)
        
        # Remove any explanation text before the code
        lines = code.split('\n')
        code_start = 0
        for i, line in enumerate(lines):
            # Detect start of actual code
            if line.strip() and not line.strip().startswith('#'):
                if any(keyword in line for keyword in ['def ', 'class ', 'import ', 'from ']):
                    code_start = i
                    break
        
        if code_start > 0:
            code = '\n'.join(lines[code_start:])
        
        # Basic validation
        code = code.strip()
        if not code:
            raise ValueError("Generated empty code")
        
        # Try to compile it to check for syntax errors
        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            logger.warning(f"Generated code has syntax errors: {e}")
            # Attempt to fix common issues
            code = self._fix_common_syntax_errors(code)
        
        return code
    
    def _fix_common_syntax_errors(self, code: str) -> str:
        """Attempt to fix common syntax errors in generated code"""
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix incomplete lines
            if line.strip() and not line.rstrip().endswith((':',  '\\', ',', ')')):
                # Check if it's likely an incomplete statement
                if any(line.strip().startswith(kw) for kw in ['if ', 'elif ', 'else', 'for ', 'while ', 'def ', 'class ']):
                    if not line.rstrip().endswith(':'):
                        line = line.rstrip() + ':'
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def shutdown(self) -> None:
        """Clean up resources"""
        logger.info("Shutting down CustomLLM")
        
        # Clear model from memory
        if hasattr(self, '_model'):
            del self._model
        
        if hasattr(self, '_tokenizer'):
            del self._tokenizer
        
        # Clear caches
        if hasattr(self, '_generation_cache'):
            self._generation_cache.clear()
        
        self._initialized = False
        
        # Force garbage collection for GPU memory
        if self._device == 'cuda':
            import torch
            torch.cuda.empty_cache()
        
        logger.info("CustomLLM shutdown complete")
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = super().get_info()
        
        # Add custom information
        if self._initialized:
            info['device'] = getattr(self, '_device', 'unknown')
            info['cache_size'] = len(getattr(self, '_generation_cache', {}))
        
        return info
```

## Summary

Adding a new model to the Pseudocode Translator is straightforward:

1. Create a new file in `models/` directory
2. Inherit from `BaseModel`
3. Use `@register_model` decorator
4. Implement required properties and methods
5. Test your implementation
6. Configure the model in your config files

The flexible architecture handles model discovery, registration, and lifecycle management automatically, allowing you to focus on implementing the model-specific logic.

For more examples, look at the existing implementations:
- `qwen.py` - GGUF model using llama-cpp-python
- `gpt2.py` - HuggingFace Transformers model
- `codegen.py` - Specialized code generation model