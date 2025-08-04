"""
OpenAI Model Implementation for the Pseudocode Translator

This module provides an OpenAI API-based model implementation supporting
GPT-3.5 and GPT-4 models for multi-language code generation.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from .base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult,
    validate_instruction
)
from .model_factory import register_model, ModelPriority

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False


@register_model(
    name="openai",
    aliases=["gpt", "gpt-3.5", "gpt-4", "chatgpt"],
    priority=ModelPriority.HIGH
)
class OpenAIModel(BaseTranslationModel):
    """
    OpenAI API-based model implementation
    
    Supports GPT-3.5 and GPT-4 models for code generation
    with multi-language output capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAI model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        super().__init__(config)
        
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )
        
        # Set default configuration
        self.config.setdefault('model_name', 'gpt-3.5-turbo')
        self.config.setdefault('api_key', os.getenv('OPENAI_API_KEY'))
        self.config.setdefault('organization', os.getenv('OPENAI_ORG_ID'))
        self.config.setdefault('temperature', 0.3)
        self.config.setdefault('top_p', 0.9)
        self.config.setdefault('max_tokens', 2048)
        self.config.setdefault('timeout', 30)
        self.config.setdefault('max_retries', 3)
        
        # Language-specific system prompts
        self.language_prompts = {
            OutputLanguage.PYTHON: (
                "You are an expert Python programmer. Generate clean, "
                "idiomatic Python code following PEP 8 conventions."
            ),
            OutputLanguage.JAVASCRIPT: (
                "You are an expert JavaScript developer. Generate modern, "
                "clean JavaScript code using ES6+ features."
            ),
            OutputLanguage.TYPESCRIPT: (
                "You are an expert TypeScript developer. Generate type-safe, "
                "clean TypeScript code with proper type annotations."
            ),
            OutputLanguage.JAVA: (
                "You are an expert Java developer. Generate clean, "
                "object-oriented Java code following best practices."
            ),
            OutputLanguage.CPP: (
                "You are an expert C++ programmer. Generate efficient, "
                "modern C++ code using appropriate STL features."
            ),
            OutputLanguage.CSHARP: (
                "You are an expert C# developer. Generate clean, "
                "object-oriented C# code following .NET conventions."
            ),
            OutputLanguage.GO: (
                "You are an expert Go developer. Generate idiomatic, "
                "concurrent Go code following Go conventions."
            ),
            OutputLanguage.RUST: (
                "You are an expert Rust developer. Generate safe, "
                "efficient Rust code with proper ownership handling."
            ),
            OutputLanguage.RUBY: (
                "You are an expert Ruby developer. Generate clean, "
                "expressive Ruby code following Ruby conventions."
            ),
            OutputLanguage.PHP: (
                "You are an expert PHP developer. Generate modern, "
                "secure PHP code following PSR standards."
            ),
            OutputLanguage.KOTLIN: (
                "You are an expert Kotlin developer. Generate concise, "
                "null-safe Kotlin code using modern features."
            ),
            OutputLanguage.SWIFT: (
                "You are an expert Swift developer. Generate safe, "
                "expressive Swift code following Swift conventions."
            ),
            OutputLanguage.SQL: (
                "You are an expert SQL developer. Generate efficient, "
                "portable SQL queries following ANSI standards."
            ),
            OutputLanguage.BASH: (
                "You are an expert Bash scripter. Generate robust, "
                "portable shell scripts with proper error handling."
            )
        }
        
        self._client = None
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        model_name = self.config['model_name']
        return ModelMetadata(
            name="openai",
            version=model_name,
            supported_languages=list(OutputLanguage),
            description=(
                f"OpenAI {model_name} model for multi-language code "
                "generation. Requires API key for access."
            ),
            author="OpenAI",
            license="OpenAI Terms",
            model_type="api",
            size_gb=0.0,  # Cloud-based
            requires_gpu=False,
            supports_streaming=True,
            max_context_length=self._get_context_length()
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
            tokens_per_second=50.0,  # Approximate
            max_batch_size=20,
            optimal_temperature=0.3,
            min_memory_gb=0.1,  # Minimal local requirements
            recommended_memory_gb=0.5
        )
    
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """
        Initialize the OpenAI client
        
        Args:
            model_path: Not used for API models
            **kwargs: Additional initialization parameters
        """
        logger.info(f"Initializing OpenAI model: {self.config['model_name']}")
        
        # Validate API key
        api_key = self.config.get('api_key') or kwargs.get('api_key')
        if not api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY "
                "environment variable or provide in config."
            )
        
        # Initialize client
        self._client = openai.OpenAI(
            api_key=api_key,
            organization=self.config.get('organization'),
            timeout=self.config['timeout'],
            max_retries=self.config['max_retries']
        )
        
        self._initialized = True
        logger.info("OpenAI model initialized successfully")
    
    def translate(self,
                  instruction: str,
                  config: Optional[TranslationConfig] = None,
                  context: Optional[Dict[str, Any]] = None
                  ) -> TranslationResult:
        """
        Translate instruction using OpenAI API
        
        Args:
            instruction: Natural language instruction
            config: Translation configuration
            context: Optional context
            
        Returns:
            TranslationResult with generated code
        """
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        # Use default config if not provided
        if config is None:
            config = TranslationConfig()
        
        try:
            # Build messages
            messages = self._build_messages(instruction, config, context)
            
            # Call OpenAI API
            response = self._client.chat.completions.create(
                model=self.config['model_name'],
                messages=messages,
                temperature=config.temperature,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
                stop=config.stop_sequences
            )
            
            # Extract code from response
            generated_text = response.choices[0].message.content
            code = self._extract_code(generated_text, config.target_language)
            
            # Calculate confidence based on response
            confidence = self._calculate_confidence(response)
            
            return TranslationResult(
                success=True,
                code=code,
                language=config.target_language,
                confidence=confidence,
                metadata={
                    'model': self.config['model_name'],
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens
                    },
                    'finish_reason': response.choices[0].finish_reason
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return TranslationResult(
                success=False,
                code=None,
                language=config.target_language,
                errors=[f"API error: {str(e)}"]
            )
    
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """
        Validate input instruction
        
        Args:
            instruction: The instruction to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation
        is_valid, error = validate_instruction(
            instruction, max_length=2000
        )
        
        if not is_valid:
            return is_valid, error
        
        # Check for potential prompt injection
        suspicious_patterns = [
            "ignore previous instructions",
            "disregard all prior",
            "system prompt",
            "you are now"
        ]
        
        instruction_lower = instruction.lower()
        for pattern in suspicious_patterns:
            if pattern in instruction_lower:
                return False, f"Suspicious pattern detected: {pattern}"
        
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get detailed model capabilities"""
        return {
            "model_name": self.config['model_name'],
            "api_based": True,
            "supported_languages": [lang.value for lang in OutputLanguage],
            "features": {
                "streaming": True,
                "function_calling": "gpt-4" in self.config['model_name'],
                "context_length": self._get_context_length(),
                "multi_language": True
            },
            "requirements": {
                "api_key": bool(self.config.get('api_key')),
                "internet": True,
                "local_storage": False
            }
        }
    
    def _build_messages(self,
                        instruction: str,
                        config: TranslationConfig,
                        context: Optional[Dict[str, Any]]
                        ) -> List[Dict[str, str]]:
        """Build messages for OpenAI API"""
        messages = []
        
        # System prompt based on target language
        system_prompt = self.language_prompts.get(
            config.target_language,
            "You are an expert programmer. Generate clean, efficient code."
        )
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add context if provided
        if context and context.get('code'):
            messages.append({
                "role": "user",
                "content": f"Context code:\n```\n{context['code']}\n```"
            })
        
        # Main instruction
        user_prompt = (
            f"Generate {config.target_language.value} code for the "
            f"following instruction:\n\n{instruction}\n\n"
            f"Provide only the code without explanations."
        )
        
        if config.include_comments:
            user_prompt += " Include helpful comments."
        
        if config.follow_conventions:
            user_prompt += (
                f" Follow {config.target_language.value} "
                "best practices and conventions."
            )
        
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        return messages
    
    def _extract_code(self, response: str, language: OutputLanguage) -> str:
        """Extract code from API response"""
        # Remove markdown code blocks if present
        if "```" in response:
            # Find code block
            lines = response.split('\n')
            in_code = False
            code_lines = []
            
            for line in lines:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    code_lines.append(line)
            
            if code_lines:
                return '\n'.join(code_lines)
        
        # Otherwise, assume entire response is code
        return response.strip()
    
    def _calculate_confidence(self, response: Any) -> float:
        """Calculate confidence based on API response"""
        # Base confidence for OpenAI models
        base_confidence = 0.85
        
        # Adjust based on finish reason
        if response.choices[0].finish_reason == "stop":
            base_confidence += 0.1
        elif response.choices[0].finish_reason == "length":
            base_confidence -= 0.1
        
        # Adjust based on model
        if "gpt-4" in self.config['model_name']:
            base_confidence += 0.05
        
        return min(0.99, max(0.5, base_confidence))
    
    def _get_context_length(self) -> int:
        """Get context length for current model"""
        model_name = self.config['model_name']
        
        context_lengths = {
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000
        }
        
        # Default to 4k if model not recognized
        return context_lengths.get(model_name, 4096)