"""
Base Translation Model for the Pseudocode Translator

This module defines the abstract base class that all translation models must
implement, providing a standard interface for multi-language output
capabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging


logger = logging.getLogger(__name__)


class OutputLanguage(Enum):
    """Supported output programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"
    PHP = "php"
    KOTLIN = "kotlin"
    SWIFT = "swift"
    SQL = "sql"
    BASH = "bash"


@dataclass
class ModelMetadata:
    """Metadata about a translation model"""
    name: str
    version: str
    supported_languages: List[OutputLanguage]
    description: str
    author: str = "Unknown"
    license: str = "MIT"
    model_type: str = "transformer"
    size_gb: float = 0.0
    requires_gpu: bool = False
    supports_streaming: bool = False
    max_context_length: int = 2048
    
    def supports_language(self, language: OutputLanguage) -> bool:
        """Check if model supports a specific output language"""
        return language in self.supported_languages


@dataclass
class ModelCapabilities:
    """Defines what a model can do"""
    # Core capabilities
    translate_instruction: bool = True
    validate_input: bool = True
    get_capabilities: bool = True
    
    # Advanced capabilities
    supports_refinement: bool = True
    supports_batch_processing: bool = True
    supports_context_aware: bool = True
    supports_code_completion: bool = False
    supports_error_correction: bool = True
    
    # Performance characteristics
    tokens_per_second: float = 0.0
    max_batch_size: int = 1
    optimal_temperature: float = 0.3
    
    # Memory requirements
    min_memory_gb: float = 4.0
    recommended_memory_gb: float = 8.0


@dataclass
class TranslationConfig:
    """Configuration for a translation request"""
    target_language: OutputLanguage = OutputLanguage.PYTHON
    temperature: float = 0.3
    max_tokens: int = 1024
    top_p: float = 0.9
    top_k: int = 40
    stop_sequences: List[str] = field(default_factory=list)
    include_comments: bool = True
    follow_conventions: bool = True
    optimization_level: int = 0  # 0=none, 1=basic, 2=aggressive


@dataclass
class TranslationResult:
    """Result of a translation operation"""
    success: bool
    code: Optional[str]
    language: OutputLanguage
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """Check if translation has errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if translation has warnings"""
        return len(self.warnings) > 0


class BaseTranslationModel(ABC):
    """
    Abstract base class for all translation models
    
    This class defines the standard interface that all translation models
    must implement for multi-language code generation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the model with configuration
        
        Args:
            config: Model-specific configuration dictionary
        """
        self.config = config
        self._initialized = False
        self._model = None
        
    @property
    @abstractmethod
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """Get model capabilities"""
        pass
    
    @abstractmethod
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """
        Initialize/load the model
        
        Args:
            model_path: Optional path to model file/directory
            **kwargs: Additional initialization parameters
            
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If model loading fails
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the input instruction is suitable for translation
        
        Args:
            instruction: The instruction to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get detailed model capabilities as a dictionary
        
        Returns:
            Dictionary describing model capabilities
        """
        pass
    
    def batch_translate(self,
                        instructions: List[str],
                        config: Optional[TranslationConfig] = None,
                        show_progress: bool = True) -> List[TranslationResult]:
        """
        Translate multiple instructions in batch
        
        Args:
            instructions: List of instructions to translate
            config: Translation configuration
            show_progress: Whether to show progress
            
        Returns:
            List of TranslationResult objects
        """
        results = []
        total = len(instructions)
        
        for i, instruction in enumerate(instructions):
            if show_progress:
                logger.info(f"Processing {i+1}/{total}: {instruction[:50]}...")
            
            try:
                result = self.translate(instruction, config)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to translate instruction {i+1}: {e}")
                language = (config.target_language if config
                            else OutputLanguage.PYTHON)
                results.append(TranslationResult(
                    success=False,
                    code=None,
                    language=language,
                    errors=[str(e)]
                ))
        
        return results
    
    def refine_code(self,
                    code: str,
                    error_context: str,
                    config: Optional[TranslationConfig] = None
                    ) -> TranslationResult:
        """
        Attempt to fix code based on error feedback
        
        Args:
            code: Code that needs fixing
            error_context: Error message or context
            config: Translation configuration
            
        Returns:
            TranslationResult with refined code
        """
        # Default implementation - can be overridden
        refinement_instruction = (
            f"Fix the following code based on the error:\n\n"
            f"Code:\n```\n{code}\n```\n\n"
            f"Error:\n{error_context}\n\n"
            f"Provide the corrected code."
        )
        
        return self.translate(refinement_instruction, config)
    
    def switch_language(self, language: OutputLanguage) -> bool:
        """
        Switch the default output language
        
        Args:
            language: The target output language
            
        Returns:
            True if language is supported, False otherwise
        """
        if not self.metadata.supports_language(language):
            logger.warning(
                f"Language {language.value} not supported by "
                f"{self.metadata.name}"
            )
            return False
        
        return True
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported output languages
        
        Returns:
            List of language names
        """
        return [lang.value for lang in self.metadata.supported_languages]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the model
        
        Returns:
            Dictionary with model information
        """
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "initialized": self._initialized,
            "supported_languages": self.get_supported_languages(),
            "capabilities": self.get_capabilities(),
            "metadata": {
                "author": self.metadata.author,
                "license": self.metadata.license,
                "model_type": self.metadata.model_type,
                "size_gb": self.metadata.size_gb,
                "requires_gpu": self.metadata.requires_gpu,
                "supports_streaming": self.metadata.supports_streaming,
                "max_context_length": self.metadata.max_context_length
            }
        }
    
    def validate_config(self, config: TranslationConfig) -> List[str]:
        """
        Validate translation configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        # Check language support
        if not self.metadata.supports_language(config.target_language):
            issues.append(
                f"Language {config.target_language.value} not supported. "
                f"Supported: {', '.join(self.get_supported_languages())}"
            )
        
        # Validate parameters
        if not 0 <= config.temperature <= 2:
            issues.append(
                f"Temperature {config.temperature} out of range [0, 2]"
            )
        
        if config.max_tokens < 1:
            issues.append(
                f"max_tokens must be positive, got {config.max_tokens}"
            )
        
        if not 0 <= config.top_p <= 1:
            issues.append(f"top_p {config.top_p} out of range [0, 1]")
        
        if config.top_k < 0:
            issues.append(f"top_k must be non-negative, got {config.top_k}")
        
        return issues
    
    def warmup(self) -> None:
        """
        Warm up the model with a simple generation
        
        This can help reduce initial latency
        """
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        
        try:
            logger.info(f"Warming up {self.metadata.name}...")
            simple_instruction = "print hello world"
            config = TranslationConfig(
                target_language=self.metadata.supported_languages[0],
                max_tokens=50
            )
            self.translate(simple_instruction, config)
            logger.info("Warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    def shutdown(self) -> None:
        """
        Cleanup model resources
        
        Override this method if your model needs cleanup
        """
        self._model = None
        self._initialized = False
        logger.info(f"Model {self.metadata.name} shut down")
    
    def __repr__(self) -> str:
        """String representation of the model"""
        return (f"{self.__class__.__name__}("
                f"name='{self.metadata.name}', "
                f"version='{self.metadata.version}', "
                f"initialized={self._initialized})")
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        langs = ", ".join(self.get_supported_languages())
        return (f"{self.metadata.name} v{self.metadata.version} "
                f"(supports: {langs})")


# Helper functions for model implementations
def create_default_config() -> TranslationConfig:
    """Create a default translation configuration"""
    return TranslationConfig()


def validate_instruction(instruction: str,
                         min_length: int = 3,
                         max_length: int = 1000) -> Tuple[bool, Optional[str]]:
    """
    Basic instruction validation helper
    
    Args:
        instruction: The instruction to validate
        min_length: Minimum instruction length
        max_length: Maximum instruction length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not instruction or not instruction.strip():
        return False, "Instruction cannot be empty"
    
    instruction = instruction.strip()
    
    if len(instruction) < min_length:
        return False, f"Instruction too short (min {min_length} characters)"
    
    if len(instruction) > max_length:
        return False, f"Instruction too long (max {max_length} characters)"
    
    # Check for basic validity
    if instruction.count('\n') > 50:
        return False, "Instruction has too many lines (max 50)"
    
    return True, None


def format_code_block(code: str, language: OutputLanguage) -> str:
    """
    Format code with appropriate comment style
    
    Args:
        code: The code to format
        language: The target language
        
    Returns:
        Formatted code with language-appropriate comments
    """
    comment_styles = {
        OutputLanguage.PYTHON: "#",
        OutputLanguage.JAVASCRIPT: "//",
        OutputLanguage.TYPESCRIPT: "//",
        OutputLanguage.JAVA: "//",
        OutputLanguage.CPP: "//",
        OutputLanguage.CSHARP: "//",
        OutputLanguage.GO: "//",
        OutputLanguage.RUST: "//",
        OutputLanguage.RUBY: "#",
        OutputLanguage.PHP: "//",
        OutputLanguage.KOTLIN: "//",
        OutputLanguage.SWIFT: "//",
        OutputLanguage.SQL: "--",
        OutputLanguage.BASH: "#"
    }
    
    comment_char = comment_styles.get(language, "#")
    
    # Add header comment
    header = f"{comment_char} Generated by Pseudocode Translator\n"
    header += f"{comment_char} Language: {language.value}\n\n"
    
    return header + code