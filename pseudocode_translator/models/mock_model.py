"""
Mock Model Implementation for Testing

This module provides a mock model implementation for testing the
translation system without requiring actual model resources.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import random
import time

from .base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult,
    validate_instruction
)
from .model_factory import register_model, ModelPriority

logger = logging.getLogger(__name__)


@register_model(
    name="mock",
    aliases=["test", "dummy"],
    priority=ModelPriority.FALLBACK
)
class MockModel(BaseTranslationModel):
    """
    Mock model implementation for testing
    
    This model generates predictable outputs for testing purposes
    without requiring actual model loading or computation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize mock model with configuration
        
        Args:
            config: Model configuration dictionary
        """
        super().__init__(config)
        
        # Mock-specific configuration
        self.config.setdefault('delay_ms', 100)
        self.config.setdefault('error_rate', 0.0)
        self.config.setdefault('mock_style', 'simple')
        self.config.setdefault('deterministic', True)
        
        # Language templates for mock generation
        self.templates = {
            OutputLanguage.PYTHON: {
                'function': 'def {name}():\n    """Mock function"""\n    pass',
                'variable': '{name} = None  # Mock variable',
                'class': 'class {name}:\n    """Mock class"""\n    pass',
                'default': '# Mock implementation for: {instruction}'
            },
            OutputLanguage.JAVASCRIPT: {
                'function': 'function {name}() {{\n    // Mock function\n}}',
                'variable': 'let {name} = null;  // Mock variable',
                'class': 'class {name} {{\n    // Mock class\n}}',
                'default': '// Mock implementation for: {instruction}'
            },
            OutputLanguage.JAVA: {
                'function': 'public void {name}() {{\n    // Mock method\n}}',
                'variable': 'Object {name} = null;  // Mock variable',
                'class': 'public class {name} {{\n    // Mock class\n}}',
                'default': '// Mock implementation for: {instruction}'
            }
        }
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        return ModelMetadata(
            name="mock",
            version="1.0.0",
            supported_languages=list(OutputLanguage),  # Supports all languages
            description=(
                "Mock model for testing purposes. Generates predictable "
                "outputs without requiring actual model resources."
            ),
            author="PseudocodeTranslator Team",
            license="MIT",
            model_type="mock",
            size_gb=0.0,  # No actual model files
            requires_gpu=False,
            supports_streaming=True,
            max_context_length=10000  # Arbitrary large value
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
            tokens_per_second=1000.0,  # Very fast (it's mock)
            max_batch_size=100,
            optimal_temperature=0.0,  # Deterministic by default
            min_memory_gb=0.1,  # Minimal requirements
            recommended_memory_gb=0.5
        )
    
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """
        Initialize the mock model
        
        Args:
            model_path: Ignored for mock model
            **kwargs: Additional initialization parameters
        """
        logger.info("Initializing mock model")
        
        # Simulate initialization delay
        if self.config['delay_ms'] > 0:
            time.sleep(self.config['delay_ms'] / 1000)
        
        self._initialized = True
        logger.info("Mock model initialized")
    
    def translate(self,
                  instruction: str,
                  config: Optional[TranslationConfig] = None,
                  context: Optional[Dict[str, Any]] = None
                  ) -> TranslationResult:
        """
        Generate mock translation
        
        Args:
            instruction: Natural language instruction
            config: Translation configuration
            context: Optional context
            
        Returns:
            TranslationResult with mock code
        """
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        # Use default config if not provided
        if config is None:
            config = TranslationConfig()
        
        # Simulate processing delay
        if self.config['delay_ms'] > 0:
            time.sleep(self.config['delay_ms'] / 1000)
        
        # Simulate random errors
        if (self.config['error_rate'] > 0 and
                random.random() < self.config['error_rate']):
            return TranslationResult(
                success=False,
                code=None,
                language=config.target_language,
                errors=["Mock error: Simulated translation failure"]
            )
        
        # Generate mock code
        code = self._generate_mock_code(instruction, config, context)
        
        # Calculate mock confidence
        confidence = (0.95 if self.config['deterministic']
                      else random.uniform(0.7, 0.99))
        
        return TranslationResult(
            success=True,
            code=code,
            language=config.target_language,
            confidence=confidence,
            metadata={
                'model': 'mock',
                'mock_style': self.config['mock_style'],
                'instruction_length': len(instruction)
            }
        )
    
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """
        Validate input instruction
        
        Args:
            instruction: The instruction to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use base validation
        is_valid, error = validate_instruction(instruction)
        
        if not is_valid:
            return is_valid, error
        
        # Mock-specific validation
        if instruction.lower() == "fail":
            return False, "Mock validation failure (instruction was 'fail')"
        
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get detailed model capabilities
        
        Returns:
            Dictionary describing model capabilities
        """
        return {
            "model_name": "mock",
            "version": "1.0.0",
            "type": "testing",
            "supported_languages": [lang.value for lang in OutputLanguage],
            "features": {
                "deterministic": self.config['deterministic'],
                "error_simulation": self.config['error_rate'] > 0,
                "delay_simulation": self.config['delay_ms'] > 0
            },
            "configuration": {
                "delay_ms": self.config['delay_ms'],
                "error_rate": self.config['error_rate'],
                "mock_style": self.config['mock_style']
            }
        }
    
    def _generate_mock_code(self,
                            instruction: str,
                            config: TranslationConfig,
                            context: Optional[Dict[str, Any]]) -> str:
        """
        Generate mock code based on instruction
        
        Args:
            instruction: The instruction
            config: Translation config
            context: Optional context
            
        Returns:
            Generated mock code
        """
        lang = config.target_language
        
        # Get language templates
        lang_templates = self.templates.get(
            lang,
            self.templates[OutputLanguage.PYTHON]  # Default to Python
        )
        
        # Determine code type from instruction
        instruction_lower = instruction.lower()
        
        if self.config['mock_style'] == 'simple':
            # Simple mock - just use default template
            code = lang_templates['default'].format(
                instruction=instruction
            )
        elif self.config['mock_style'] == 'smart':
            # Smart mock - try to detect intent
            if ('function' in instruction_lower or
                    'method' in instruction_lower):
                name = self._extract_name(instruction, 'function')
                code = lang_templates['function'].format(name=name)
            elif 'class' in instruction_lower:
                name = self._extract_name(instruction, 'class')
                code = lang_templates['class'].format(name=name)
            elif 'variable' in instruction_lower or 'var' in instruction_lower:
                name = self._extract_name(instruction, 'variable')
                code = lang_templates['variable'].format(name=name)
            else:
                code = lang_templates['default'].format(
                    instruction=instruction)
        else:
            # Echo style - just echo the instruction
            code = f"# Instruction: {instruction}\n# Mock output"
        
        # Add context if provided
        if context and context.get('code'):
            code = f"# Context provided\n{code}"
        
        # Add comments if requested
        if config.include_comments:
            header = self._get_language_comment(lang)
            code = (f"{header} Mock generated code\n"
                    f"{header} Model: mock v1.0.0\n\n{code}")
        
        return code
    
    def _extract_name(self, instruction: str, code_type: str) -> str:
        """Extract a name from instruction"""
        words = instruction.split()
        
        # Look for common patterns
        for i, word in enumerate(words):
            if word.lower() in ['called', 'named', 'name']:
                if i + 1 < len(words):
                    return words[i + 1].strip('.,!?"\'-')
        
        # Default names
        defaults = {
            'function': 'mock_function',
            'class': 'MockClass',
            'variable': 'mock_var'
        }
        
        return defaults.get(code_type, 'mock_item')
    
    def _get_language_comment(self, language: OutputLanguage) -> str:
        """Get comment character for language"""
        comment_chars = {
            OutputLanguage.PYTHON: '#',
            OutputLanguage.JAVASCRIPT: '//',
            OutputLanguage.TYPESCRIPT: '//',
            OutputLanguage.JAVA: '//',
            OutputLanguage.CPP: '//',
            OutputLanguage.CSHARP: '//',
            OutputLanguage.GO: '//',
            OutputLanguage.RUST: '//',
            OutputLanguage.RUBY: '#',
            OutputLanguage.PHP: '//',
            OutputLanguage.KOTLIN: '//',
            OutputLanguage.SWIFT: '//',
            OutputLanguage.SQL: '--',
            OutputLanguage.BASH: '#'
        }
        return comment_chars.get(language, '#')