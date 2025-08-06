"""
DinoTranslator - Pseudocode Translator Integration for DinoAir 2.0

This module provides a high-level wrapper around the Pseudocode Translator API
to integrate natural language to code translation functionality into the main
DinoAir application.

Features:
- Async and sync translation methods
- Progress tracking with callbacks
- Error handling and fallback mechanisms
- Integration with the existing SimpleTranslator API
- Support for multiple output languages
- Caching for repeated translations
- Validation before translation
- Integration with DinoAir Logger
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Union, Callable
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
import hashlib
from collections import OrderedDict
import time

try:
    from pseudocode_translator.integration.api import (
        SimpleTranslator, TranslatorAPI
    )
    from pseudocode_translator.models.base_model import OutputLanguage
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    SimpleTranslator = None
    TranslatorAPI = None
    OutputLanguage = None
    logging.warning(
        "Pseudocode translator not installed. "
        "Install from the pseudocode_translator directory"
    )


logger = logging.getLogger(__name__)


class TranslatorStatus(Enum):
    """Status of translator service"""
    NOT_INSTALLED = "not_installed"
    NOT_INITIALIZED = "not_initialized"
    READY = "ready"
    TRANSLATING = "translating"
    ERROR = "error"


@dataclass
class TranslationResponse:
    """Response from translation request"""
    success: bool
    code: Optional[str]
    language: str
    error: Optional[str] = None
    warnings: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    translation_time: Optional[float] = None
    cached: bool = False


@dataclass
class ValidationResult:
    """Result from pseudocode validation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    complexity_score: Optional[float] = None


class TranslationCache:
    """LRU cache for translation results"""
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, TranslationResponse] = OrderedDict()
        self._max_size = max_size
        
    def _make_key(self, pseudocode: str, language: str) -> str:
        """Create cache key from pseudocode and language"""
        content = f"{pseudocode}:{language}"
        return hashlib.sha256(content.encode()).hexdigest()
        
    def get(
        self, pseudocode: str, language: str
    ) -> Optional[TranslationResponse]:
        """Get cached translation if available"""
        key = self._make_key(pseudocode, language)
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            response = self._cache[key]
            # Mark as cached
            response.cached = True
            return response
        return None
        
    def put(
        self, pseudocode: str, language: str, response: TranslationResponse
    ):
        """Cache a translation response"""
        key = self._make_key(pseudocode, language)
        self._cache[key] = response
        self._cache.move_to_end(key)
        
        # Remove oldest if over limit
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
            
    def clear(self):
        """Clear all cached translations"""
        self._cache.clear()
        
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


class DinoTranslator:
    """
    Main Pseudocode Translator wrapper class for DinoAir integration
    
    This class provides a high-level interface for translating pseudocode
    to various programming languages with caching and validation support.
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 cache_size: int = 100,
                 default_language: str = "python"):
        """
        Initialize the DinoTranslator
        
        Args:
            config_path: Optional path to configuration file
            cache_size: Maximum number of cached translations
            default_language: Default output language
        """
        self._config_path = config_path
        self._cache = TranslationCache(cache_size)
        self._default_language = default_language
        self._translator: Optional[Any] = None
        self._api: Optional[Any] = None
        self._status = TranslatorStatus.NOT_INITIALIZED
        self._is_initialized = False
        
        # Configuration
        self._config = self._load_configuration()
        
        # Initialize
        self._initialize()
        
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from file or defaults"""
        config = {
            'default_language': self._default_language,
            'validation_enabled': True,
            'cache_enabled': True,
            'max_pseudocode_length': 10000,
            'timeout': 30,
            'temperature': 0.7,
            'max_tokens': 4096,
            'streaming_threshold': 5000,
            'verbose': False
        }
        
        # Try to load from app_config.json
        app_config_path = (
            Path(__file__).parent.parent.parent / "config" / "app_config.json"
        )
        if app_config_path.exists():
            try:
                with open(app_config_path, 'r') as f:
                    app_config = json.load(f)
                    
                # Apply translator-specific settings
                if 'translator' in app_config:
                    translator_config = app_config['translator']
                    config.update(translator_config)
                    
            except Exception as e:
                logger.warning(f"Failed to load app configuration: {e}")
        
        # Load custom config if provided
        if self._config_path and Path(self._config_path).exists():
            try:
                with open(self._config_path, 'r') as f:
                    custom_config = json.load(f)
                    config.update(custom_config)
            except Exception as e:
                logger.warning(f"Failed to load custom configuration: {e}")
        
        return config
        
    def _initialize(self):
        """Initialize the translator API and service"""
        if not TRANSLATOR_AVAILABLE:
            self._status = TranslatorStatus.NOT_INSTALLED
            logger.error("Pseudocode translator not installed")
            return
            
        try:
            # Create API instance
            if TranslatorAPI is not None:
                self._api = TranslatorAPI(self._config_path)
                
            # Create simple translator
            if SimpleTranslator is not None:
                self._translator = SimpleTranslator(self._default_language)
                
            if self._api and self._translator:
                self._status = TranslatorStatus.READY
                self._is_initialized = True
                logger.info("DinoTranslator initialized successfully")
                
                # Warm up the translator
                if self._config.get('warmup_on_init', True):
                    self._warmup()
            else:
                self._status = TranslatorStatus.ERROR
                logger.error("Failed to create translator instances")
                
        except Exception as e:
            self._status = TranslatorStatus.ERROR
            logger.error(f"Failed to initialize translator: {e}")
            
    def _warmup(self):
        """Warm up the translator with a simple translation"""
        try:
            logger.debug("Warming up translator...")
            result = self.translate("print hello", use_cache=False)
            if result.success:
                logger.debug("Translator warmup successful")
            else:
                logger.warning("Translator warmup completed with errors")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
            
    @property
    def is_ready(self) -> bool:
        """Check if the translator is ready to accept requests"""
        return (self._is_initialized and 
                self._status == TranslatorStatus.READY and
                self._translator is not None)
                
    @property
    def status(self) -> TranslatorStatus:
        """Get current translator status"""
        return self._status
        
    @property
    def default_language(self) -> str:
        """Get default output language"""
        return self._default_language
        
    def validate_pseudocode(self, pseudocode: str) -> ValidationResult:
        """
        Validate pseudocode before translation
        
        Args:
            pseudocode: The pseudocode to validate
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        
        # Check if empty
        if not pseudocode or not pseudocode.strip():
            errors.append("Pseudocode is empty")
            return ValidationResult(
                valid=False, errors=errors, warnings=warnings
            )
            
        # Check length
        max_length = self._config.get('max_pseudocode_length', 10000)
        if len(pseudocode) > max_length:
            errors.append(
                f"Pseudocode exceeds maximum length of {max_length} characters"
            )
            
        # Basic structure checks
        lines = pseudocode.strip().split('\n')
        
        # Check for common patterns
        has_function = any(
            'function' in line.lower() or 'def' in line.lower()
            for line in lines
        )
        has_loop = any(
            keyword in line.lower()
            for line in lines
            for keyword in ['for', 'while', 'loop']
        )
        has_condition = any(
            keyword in line.lower()
            for line in lines
            for keyword in ['if', 'else', 'when']
        )
        
        # Calculate complexity score
        complexity_score = 0.0
        if has_function:
            complexity_score += 0.3
        if has_loop:
            complexity_score += 0.3
        if has_condition:
            complexity_score += 0.2
        complexity_score += min(0.2, len(lines) / 100)  # Line count factor
        
        # Warnings for ambiguous constructs
        if 'goto' in pseudocode.lower():
            warnings.append(
                "'goto' statements may not translate well to all languages"
            )
            
        if not has_function and len(lines) > 20:
            warnings.append("Consider organizing long code into functions")
            
        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            complexity_score=complexity_score
        )
        
    def translate(self,
                  pseudocode: str,
                  output_language: Optional[str] = None,
                  use_cache: bool = True,
                  validate: bool = True,
                  progress_callback: Optional[Callable] = None,
                  **kwargs) -> TranslationResponse:
        """
        Translate pseudocode to the specified language
        
        Args:
            pseudocode: The pseudocode to translate
            output_language: Target language (uses default if None)
            use_cache: Whether to use cached results
            validate: Whether to validate before translation
            progress_callback: Optional callback for progress updates
                              Called with (percentage, message)
            **kwargs: Additional translation options
            
        Returns:
            TranslationResponse with the translation result
        """
        if not self.is_ready:
            return TranslationResponse(
                success=False,
                code=None,
                language=output_language or self._default_language,
                error="Translator not ready"
            )
            
        # Use default language if not specified
        output_language = output_language or self._default_language
        
        # Check cache if enabled
        if use_cache and self._config.get('cache_enabled', True):
            cached_result = self._cache.get(pseudocode, output_language)
            if cached_result:
                logger.debug(
                    f"Returning cached translation for {output_language}"
                )
                return cached_result
                
        # Validate if enabled
        if validate and self._config.get('validation_enabled', True):
            validation = self.validate_pseudocode(pseudocode)
            if not validation.valid:
                return TranslationResponse(
                    success=False,
                    code=None,
                    language=output_language,
                    error="; ".join(validation.errors),
                    warnings=validation.warnings
                )
                
        # Update status
        self._status = TranslatorStatus.TRANSLATING
        
        try:
            start_time = time.time()
            
            # Progress callback wrapper
            def _progress_wrapper(percentage: int, message: str):
                if progress_callback:
                    progress_callback(percentage, message)
                    
            # Determine if we should use streaming
            use_streaming = kwargs.get('use_streaming', False)
            streaming_threshold = self._config.get('streaming_threshold', 5000)
            if not use_streaming and len(pseudocode) > streaming_threshold:
                use_streaming = True
                logger.debug("Auto-enabling streaming for large input")
                
            # Perform translation
            if self._api:
                # Use full API for more control
                result = self._api.translate(
                    pseudocode,
                    language=output_language,
                    use_streaming=use_streaming,
                    **kwargs
                )
                
                response = TranslationResponse(
                    success=result['success'],
                    code=result.get('code'),
                    language=output_language,
                    error=("; ".join(result.get('errors', []))
                           if result.get('errors') else None),
                    warnings=result.get('warnings'),
                    metadata=result.get('metadata', {}),
                    translation_time=time.time() - start_time
                )
            else:
                # Fallback to simple translator
                if self._translator:
                    code = self._translator.translate(
                        pseudocode,
                        output_language=output_language,
                        progress_callback=_progress_wrapper
                    )
                else:
                    code = None
                
                response = TranslationResponse(
                    success=code is not None,
                    code=code,
                    language=output_language,
                    error="Translation failed" if code is None else None,
                    translation_time=time.time() - start_time
                )
                
            # Cache successful results
            cache_enabled = self._config.get('cache_enabled', True)
            if response.success and use_cache and cache_enabled:
                self._cache.put(pseudocode, output_language, response)
                
            return response
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResponse(
                success=False,
                code=None,
                language=output_language,
                error=str(e)
            )
        finally:
            self._status = TranslatorStatus.READY
            
    async def translate_async(
        self,
        pseudocode: str,
        output_language: Optional[str] = None,
        **kwargs
    ) -> TranslationResponse:
        """
        Async version of translate method
        
        Args:
            pseudocode: The pseudocode to translate
            output_language: Target language (uses default if None)
            **kwargs: Additional translation options
            
        Returns:
            TranslationResponse with the translation result
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        return await loop.run_in_executor(
            None,
            self.translate,
            pseudocode,
            output_language,
            kwargs.get('use_cache', True),
            kwargs.get('validate', True),
            kwargs.get('progress_callback'),
            **{k: v for k, v in kwargs.items() 
               if k not in ['use_cache', 'validate', 'progress_callback']}
        )
        
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported output languages
        
        Returns:
            List of language names
        """
        if TRANSLATOR_AVAILABLE and OutputLanguage:
            return [lang.value for lang in OutputLanguage]
        else:
            # Fallback list
            return [
                "python", "javascript", "java", "cpp", "csharp",
                "go", "rust", "swift", "kotlin", "typescript",
                "php", "ruby", "scala", "haskell"
            ]
            
    def set_default_language(self, language: str) -> bool:
        """
        Set the default output language
        
        Args:
            language: Language name
            
        Returns:
            True if language was set successfully
        """
        supported = self.get_supported_languages()
        if language.lower() not in supported:
            logger.error(f"Unsupported language: {language}")
            return False
            
        self._default_language = language.lower()
        
        # Update translator if available
        if self._translator:
            try:
                self._translator.api.set_default_language(language)
                logger.info(f"Default language set to: {language}")
                return True
            except Exception as e:
                logger.error(f"Failed to update translator language: {e}")
                return False
                
        return True
        
    def clear_cache(self) -> int:
        """
        Clear the translation cache
        
        Returns:
            Number of cached items cleared
        """
        size = self._cache.size()
        self._cache.clear()
        logger.info(f"Cleared {size} cached translations")
        return size
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'enabled': self._config.get('cache_enabled', True),
            'size': self._cache.size(),
            'max_size': self._cache._max_size
        }
        
    def batch_translate(
        self,
        items: List[Union[str, Dict[str, Any]]],
        output_language: Optional[str] = None,
        parallel: bool = False,
        progress_callback: Optional[Callable] = None,
        **kwargs
    ) -> List[TranslationResponse]:
        """
        Translate multiple items in batch
        
        Args:
            items: List of pseudocode strings or dicts with 'code' and options
            output_language: Default target language for all items
            parallel: Whether to use parallel processing (not implemented)
            progress_callback: Optional callback for batch progress
            **kwargs: Additional options
            
        Returns:
            List of TranslationResponse objects
        """
        results = []
        total = len(items)
        
        for i, item in enumerate(items):
            # Extract code and options
            if isinstance(item, str):
                code = item
                item_lang = output_language
                item_options = kwargs
            else:
                code = item.get('code', '')
                item_lang = item.get('language', output_language)
                item_options = {**kwargs, **item.get('options', {})}
                
            # Progress callback for batch
            if progress_callback:
                progress_callback(i, total, f"Translating item {i+1}/{total}")
                
            # Create item progress callback
            def item_progress(percentage, message):
                if progress_callback:
                    # Scale item progress to batch progress
                    batch_percentage = (i + percentage/100) / total * 100
                    progress_callback(
                        int(batch_percentage),
                        f"Item {i+1}/{total}: {message}"
                    )
                    
            # Translate
            result = self.translate(
                code,
                item_lang,
                progress_callback=item_progress,
                **item_options
            )
            results.append(result)
            
        # Final progress callback
        if progress_callback:
            progress_callback(100, "Batch translation complete")
            
        return results
        
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get current wrapper status and information
        
        Returns:
            Dictionary with status information
        """
        return {
            'initialized': self._is_initialized,
            'status': self._status.value,
            'default_language': self._default_language,
            'supported_languages': self.get_supported_languages(),
            'cache_stats': self.get_cache_stats(),
            'config': {
                'validation_enabled': self._config.get(
                    'validation_enabled', True
                ),
                'max_pseudocode_length': self._config.get(
                    'max_pseudocode_length', 10000
                ),
                'streaming_threshold': self._config.get(
                    'streaming_threshold', 5000
                ),
                'timeout': self._config.get('timeout', 30)
            }
        }
        
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update wrapper configuration
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        self._config.update(config_updates)
        logger.info(f"Updated translator config: {config_updates}")
        
        # Reinitialize API with new config if needed
        if self._api and any(
            key in config_updates
            for key in ['temperature', 'max_tokens']
        ):
            try:
                self._api.update_config(config_updates)
            except Exception as e:
                logger.error(f"Failed to update API config: {e}")
                
    def shutdown(self):
        """Shutdown the translator and cleanup resources"""
        if self._api:
            try:
                self._api.shutdown()
            except Exception as e:
                logger.error(f"Error during API shutdown: {e}")
                
        self._cache.clear()
        self._status = TranslatorStatus.NOT_INITIALIZED
        self._is_initialized = False
        logger.info("DinoTranslator shutdown complete")
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()


# Convenience factory function
def create_dino_translator(
        config_path: Optional[str] = None,
        cache_size: int = 100,
        default_language: str = "python") -> DinoTranslator:
    """
    Factory function to create a DinoTranslator instance
    
    Args:
        config_path: Optional path to configuration file
        cache_size: Maximum number of cached translations
        default_language: Default output language
        
    Returns:
        Configured DinoTranslator instance
    """
    return DinoTranslator(config_path, cache_size, default_language)


# Tool integration support
class DinoTranslatorTool:
    """
    Tool wrapper for integration with DinoAir tool system
    """
    
    def __init__(self, translator: Optional[DinoTranslator] = None):
        """Initialize tool wrapper"""
        self.translator = translator or DinoTranslator()
        
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information for registration"""
        return {
            'name': 'pseudocode_translator',
            'description': 'Translate pseudocode to real code',
            'version': '1.0.0',
            'capabilities': {
                'languages': self.translator.get_supported_languages(),
                'features': [
                    'validation',
                    'caching',
                    'batch_translation',
                    'async_support'
                ]
            }
        }
        
    def execute(
        self, pseudocode: str, language: str = "python", **kwargs
    ) -> Dict[str, Any]:
        """Execute tool with given parameters"""
        result = self.translator.translate(pseudocode, language, **kwargs)
        return {
            'success': result.success,
            'output': result.code,
            'language': result.language,
            'error': result.error,
            'metadata': result.metadata
        }


# Example usage and integration guide
"""
Example Integration:

    from src.agents.dino_translator import DinoTranslator
    
    # Create translator
    translator = DinoTranslator()
    
    # Check if ready
    if translator.is_ready:
        print("Translator ready")
    else:
        print(f"Translator status: {translator.status}")
    
    # Simple translation
    result = translator.translate("create a function to calculate fibonacci")
    if result.success:
        print(f"Generated {result.language} code:")
        print(result.code)
        print(f"Translation time: {result.translation_time:.2f}s")
    
    # Translation with options
    result = translator.translate(
        "implement quicksort algorithm",
        output_language="javascript",
        validate=True,
        progress_callback=lambda p, m: print(f"{p}%: {m}")
    )
    
    # Async translation
    import asyncio
    
    async def translate_async():
        result = await translator.translate_async(
            "create a web server",
            output_language="go"
        )
        return result
    
    # Batch translation
    items = [
        "function to reverse a string",
        {"code": "sort a list", "language": "rust"},
        "find prime numbers up to n"
    ]
    
    results = translator.batch_translate(
        items,
        output_language="python",
        progress_callback=lambda i, t, m: print(f"[{i}/{t}] {m}")
    )
    
    # Get information
    info = translator.get_status_info()
    print(f"Supported languages: {info['supported_languages']}")
    print(f"Cache stats: {info['cache_stats']}")
    
    # Clear cache
    cleared = translator.clear_cache()
    print(f"Cleared {cleared} cached translations")
    
    # Context manager usage
    with DinoTranslator() as translator:
        result = translator.translate("hello world program")
        print(result.code)
"""