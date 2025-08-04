"""
Qwen Model Implementation for the Pseudocode Translator

This module provides a Qwen 7B model implementation using the new
BaseTranslationModel interface, supporting multi-language output.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
    
from ..prompts import PromptEngineer, PromptLibrary
from .base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult,
    validate_instruction, format_code_block
)
from .model_factory import register_model, ModelPriority

logger = logging.getLogger(__name__)


@register_model(
    name="qwen",
    aliases=["qwen-7b", "qwen-7b-chat", "qwen-default"],
    priority=ModelPriority.HIGH,
    is_default=True
)
class QwenModel(BaseTranslationModel):
    """
    Qwen 7B Chat model implementation
    
    This model uses the GGUF format and is optimized for code generation
    from natural language instructions. It supports multiple output languages.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Qwen model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        super().__init__(config)
        
        # Check if llama-cpp-python is available
        if Llama is None:
            raise ImportError(
                "llama-cpp-python is required for Qwen model support. "
                "Install with: pip install llama-cpp-python"
            )
        
        self.prompt_engineer = PromptEngineer()
        
        # Set default configuration values
        self.config.setdefault('model_path', None)
        self.config.setdefault('n_ctx', 2048)
        self.config.setdefault('n_batch', 512)
        self.config.setdefault('n_threads', 4)
        self.config.setdefault('n_gpu_layers', 0)
        self.config.setdefault('temperature', 0.3)
        self.config.setdefault('top_p', 0.9)
        self.config.setdefault('top_k', 40)
        self.config.setdefault('repeat_penalty', 1.1)
        self.config.setdefault('max_tokens', 1024)
        self.config.setdefault('seed', -1)
        
        # Language-specific settings
        self.language_prompts = {
            OutputLanguage.PYTHON: "Generate Python code:",
            OutputLanguage.JAVASCRIPT: "Generate JavaScript code:",
            OutputLanguage.TYPESCRIPT: "Generate TypeScript code:",
            OutputLanguage.JAVA: "Generate Java code:",
            OutputLanguage.CPP: "Generate C++ code:",
            OutputLanguage.CSHARP: "Generate C# code:",
            OutputLanguage.GO: "Generate Go code:",
            OutputLanguage.RUST: "Generate Rust code:",
            OutputLanguage.RUBY: "Generate Ruby code:",
            OutputLanguage.PHP: "Generate PHP code:",
            OutputLanguage.KOTLIN: "Generate Kotlin code:",
            OutputLanguage.SWIFT: "Generate Swift code:",
            OutputLanguage.SQL: "Generate SQL code:",
            OutputLanguage.BASH: "Generate Bash script:"
        }
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        return ModelMetadata(
            name="qwen",
            version="7B-Chat-Q4_K_M",
            supported_languages=[
                OutputLanguage.PYTHON,
                OutputLanguage.JAVASCRIPT,
                OutputLanguage.TYPESCRIPT,
                OutputLanguage.JAVA,
                OutputLanguage.CPP,
                OutputLanguage.CSHARP,
                OutputLanguage.GO,
                OutputLanguage.RUST,
                OutputLanguage.RUBY,
                OutputLanguage.PHP,
                OutputLanguage.KOTLIN,
                OutputLanguage.SWIFT,
                OutputLanguage.SQL,
                OutputLanguage.BASH
            ],
            description=(
                "Qwen 7B is a large language model developed by Alibaba "
                "Cloud. This implementation supports multi-language code "
                "generation with optimized prompts for each language."
            ),
            author="Alibaba Cloud",
            license="Tongyi Qianwen License Agreement",
            model_type="transformer",
            size_gb=4.5,  # Q4_K_M quantization
            requires_gpu=False,
            supports_streaming=False,
            max_context_length=self.config['n_ctx']
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Get model capabilities"""
        return ModelCapabilities(
            translate_instruction=True,
            validate_input=True,
            get_capabilities=True,
            supports_refinement=True,
            supports_batch_processing=True,
            supports_context_aware=True,
            supports_code_completion=True,
            supports_error_correction=True,
            tokens_per_second=(10.0 if self.config['n_gpu_layers'] == 0
                               else 50.0),
            max_batch_size=10,
            optimal_temperature=0.3,
            min_memory_gb=4.0,
            recommended_memory_gb=8.0
        )
    
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """
        Initialize/load the Qwen model
        
        Args:
            model_path: Path to the GGUF model file
            **kwargs: Additional initialization parameters
        """
        # Use provided path or config path
        if model_path is None:
            model_path = self.config.get('model_path')
            if model_path:
                model_path = Path(model_path)
        
        if not model_path:
            raise ValueError(
                "Model path must be provided either in config or as parameter"
            )
        
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Please download the Qwen 7B GGUF model."
            )
        
        logger.info(f"Loading Qwen model from: {model_path}")
        
        try:
            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self.config['n_ctx'],
                n_batch=self.config['n_batch'],
                n_threads=self.config['n_threads'],
                n_gpu_layers=self.config['n_gpu_layers'],
                verbose=kwargs.get('verbose', False),
                seed=self.config['seed'],
            )
            self._initialized = True
            logger.info("Qwen model loaded successfully")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Qwen model: {str(e)}")
    
    def translate(self,
                  instruction: str,
                  config: Optional[TranslationConfig] = None,
                  context: Optional[Dict[str, Any]] = None
                  ) -> TranslationResult:
        """
        Translate an instruction to code in the target language
        
        Args:
            instruction: Natural language instruction
            config: Translation configuration
            context: Optional context (e.g., surrounding code, variables)
            
        Returns:
            TranslationResult containing the generated code
        """
        if not self._initialized:
            raise RuntimeError(
                "Model not initialized. Call initialize() first."
            )
        
        # Use default config if not provided
        if config is None:
            config = TranslationConfig()
        
        # Validate config
        validation_issues = self.validate_config(config)
        if validation_issues:
            return TranslationResult(
                success=False,
                code=None,
                language=config.target_language,
                errors=validation_issues
            )
        
        try:
            # Extract code context if provided
            code_context = context.get('code', '') if context else ''
            
            # Build language-specific prompt
            lang_prompt = self.language_prompts.get(
                config.target_language,
                f"Generate {config.target_language.value} code:"
            )
            
            # Select best prompting style
            prompt_style = self.prompt_engineer.select_best_style(
                instruction, code_context
            )
            
            # Create prompt with language specification
            base_prompt = self.prompt_engineer.create_prompt(
                instruction=instruction,
                style=prompt_style,
                context=code_context
            )
            
            # Combine with language prompt
            full_prompt = (
                f"{PromptLibrary.SYSTEM_PROMPT}\n\n"
                f"{lang_prompt}\n\n"
                f"{base_prompt}"
            )
            
            # Generate code
            logger.debug(
                f"Translating to {config.target_language.value}: "
                f"{instruction[:50]}..."
            )
            
            generated_text = self._generate(
                prompt=full_prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                stop_sequences=(config.stop_sequences or
                                self._get_stop_sequences())
            )
            
            # Extract code from response
            code = self.prompt_engineer.extract_code_from_response(
                generated_text
            )
            
            # Validate and clean code
            code = self._validate_and_clean_code(code, config.target_language)
            
            # Format code if requested
            if config.include_comments:
                code = format_code_block(code, config.target_language)
            
            # Calculate confidence based on validation
            confidence = self._calculate_confidence(
                code, config.target_language
            )
            
            return TranslationResult(
                success=True,
                code=code,
                language=config.target_language,
                confidence=confidence,
                metadata={
                    'model': 'qwen',
                    'prompt_style': prompt_style,
                    'tokens_generated': len(generated_text.split())
                }
            )
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return TranslationResult(
                success=False,
                code=None,
                language=config.target_language,
                errors=[f"Translation error: {str(e)}"]
            )
    
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the input instruction is suitable for translation
        
        Args:
            instruction: The instruction to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use helper function for basic validation
        is_valid, error = validate_instruction(
            instruction, min_length=3, max_length=1000
        )
        
        if not is_valid:
            return is_valid, error
        
        # Additional Qwen-specific validation
        # Check for unsupported characters or patterns
        if '\x00' in instruction:
            return False, "Instruction contains null characters"
        
        # Check instruction complexity
        if instruction.count(';') > 20:
            return False, "Instruction is too complex (too many statements)"
        
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get detailed model capabilities as a dictionary
        
        Returns:
            Dictionary describing model capabilities
        """
        caps = self.capabilities
        return {
            "model_name": self.metadata.name,
            "version": self.metadata.version,
            "supported_languages": [
                lang.value for lang in self.metadata.supported_languages
            ],
            "max_context_length": self.metadata.max_context_length,
            "features": {
                "multi_language": True,
                "code_completion": caps.supports_code_completion,
                "error_correction": caps.supports_error_correction,
                "context_aware": caps.supports_context_aware,
                "batch_processing": caps.supports_batch_processing,
                "refinement": caps.supports_refinement
            },
            "performance": {
                "tokens_per_second": caps.tokens_per_second,
                "max_batch_size": caps.max_batch_size,
                "optimal_temperature": caps.optimal_temperature
            },
            "requirements": {
                "min_memory_gb": caps.min_memory_gb,
                "recommended_memory_gb": caps.recommended_memory_gb,
                "gpu_required": False,
                "gpu_supported": True
            }
        }
    
    def _generate(self,
                  prompt: str,
                  max_tokens: int,
                  temperature: float,
                  top_p: float,
                  top_k: int,
                  stop_sequences: List[str]) -> str:
        """
        Internal method to generate text using the model
        
        Args:
            prompt: The input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            stop_sequences: List of sequences to stop generation
            
        Returns:
            Generated text
        """
        generation_params = {
            'max_tokens': max_tokens,
            'temperature': temperature,
            'top_p': top_p,
            'top_k': top_k,
            'repeat_penalty': self.config.get('repeat_penalty', 1.1),
            'stop': stop_sequences,
        }
        
        response = self._model(prompt, **generation_params)
        return response['choices'][0]['text']
    
    def _get_stop_sequences(self) -> List[str]:
        """Get default stop sequences"""
        return ["```", "\n\n\n", "Instruction:", "```\n", "\n---"]
    
    def _validate_and_clean_code(self,
                                 code: str,
                                 language: OutputLanguage) -> str:
        """
        Validate and clean generated code for the target language
        
        Args:
            code: Generated code to validate
            language: Target output language
            
        Returns:
            Cleaned and validated code
        """
        if not code or not code.strip():
            return ""
        
        # Remove any remaining markdown artifacts
        code = code.replace("```python", "").replace("```", "")
        code = code.replace(f"```{language.value}", "")
        
        # Language-specific validation
        if language == OutputLanguage.PYTHON:
            try:
                compile(code, '<generated>', 'exec')
            except SyntaxError as e:
                logger.warning(f"Generated Python code has syntax error: {e}")
                code = self._attempt_python_fix(code)
        
        return code.strip()
    
    def _attempt_python_fix(self, code: str) -> str:
        """
        Attempt to fix common syntax issues in Python code
        
        Args:
            code: Code with potential syntax errors
            
        Returns:
            Potentially fixed code
        """
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix incomplete function/class definitions
            if (line.strip() and
                    line.strip().endswith(':') and
                    i + 1 < len(lines) and
                    not lines[i + 1].strip()):
                fixed_lines.append(line)
                fixed_lines.append("    pass  # TODO: Implement")
                continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _calculate_confidence(self,
                              code: str,
                              language: OutputLanguage) -> float:
        """
        Calculate confidence score for generated code
        
        Args:
            code: Generated code
            language: Target language
            
        Returns:
            Confidence score between 0 and 1
        """
        if not code:
            return 0.0
        
        confidence = 0.8  # Base confidence for Qwen
        
        # Adjust based on code characteristics
        if len(code) < 10:
            confidence -= 0.2
        elif len(code) > 500:
            confidence -= 0.1
        
        # Check for common patterns
        if language == OutputLanguage.PYTHON:
            if 'def ' in code or 'class ' in code:
                confidence += 0.1
            if 'import ' in code:
                confidence += 0.05
        
        # Ensure confidence is in valid range
        return max(0.0, min(1.0, confidence))