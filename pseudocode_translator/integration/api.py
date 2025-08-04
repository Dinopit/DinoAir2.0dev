"""
High-level API for the Pseudocode Translator

This module provides simplified interfaces for common translation tasks,
making it easy to integrate the translator into applications.
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable
import logging

from ..translator import TranslationManager, TranslationResult
from ..config import TranslatorConfig, ConfigManager
from ..models.base_model import OutputLanguage


logger = logging.getLogger(__name__)


class TranslatorAPI:
    """
    High-level API for the pseudocode translator
    
    This class provides a simplified interface for translation operations
    with sensible defaults and easy-to-use methods.
    """
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the translator API
        
        Args:
            config_path: Optional path to configuration file
        """
        # Load configuration
        if config_path:
            self._config = ConfigManager.load(config_path)
        else:
            self._config = ConfigManager.load()
            
        # Create translator
        self._translator_config = TranslatorConfig(self._config)
        self._translator = TranslationManager(self._translator_config)
        
        # Default settings
        self._default_language = OutputLanguage.PYTHON
        # Auto-enable streaming for large files
        self._streaming_threshold = 50000
        
    def translate(self,
                  pseudocode: str,
                  language: Optional[str] = None,
                  **kwargs) -> Dict[str, Any]:
        """
        Translate pseudocode to the specified language
        
        Args:
            pseudocode: The pseudocode to translate
            language: Target language (e.g., "python", "javascript")
            **kwargs: Additional options
            
        Returns:
            Dictionary with translation results
        """
        # Determine target language
        if language:
            try:
                target_lang = OutputLanguage(language.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported language: {language}. "
                    f"Supported: {[lang.value for lang in OutputLanguage]}"
                )
        else:
            target_lang = self._default_language
            
        # Check if we should use streaming
        use_streaming = kwargs.get('use_streaming', False)
        if not use_streaming and len(pseudocode) > self._streaming_threshold:
            use_streaming = True
            logger.info("Auto-enabling streaming for large input")
            
        # Perform translation
        try:
            if use_streaming:
                # Use streaming translation
                results = list(self._translator.translate_streaming(
                    pseudocode,
                    chunk_size=kwargs.get('chunk_size', 4096)
                ))
                # Return the final result
                result = results[-1] if results else TranslationResult(
                    success=False,
                    code=None,
                    errors=["No results from streaming"],
                    warnings=[],
                    metadata={}
                )
            else:
                # Regular translation
                result = self._translator.translate_pseudocode(
                    pseudocode,
                    target_lang
                )
                
            # Convert to dictionary
            return {
                'success': result.success,
                'code': result.code,
                'language': language or self._default_language.value,
                'errors': result.errors,
                'warnings': result.warnings,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return {
                'success': False,
                'code': None,
                'language': language or self._default_language.value,
                'errors': [str(e)],
                'warnings': [],
                'metadata': {'error_type': type(e).__name__}
            }
            
    def translate_file(self,
                       file_path: Union[str, Path],
                       output_path: Optional[Union[str, Path]] = None,
                       language: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
        """
        Translate pseudocode from a file
        
        Args:
            file_path: Path to input file
            output_path: Optional path to save translated code
            language: Target language
            **kwargs: Additional options
            
        Returns:
            Dictionary with translation results
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                'success': False,
                'code': None,
                'errors': [f"File not found: {file_path}"],
                'warnings': [],
                'metadata': {}
            }
            
        try:
            # Read file
            pseudocode = file_path.read_text(encoding='utf-8')
            
            # Translate
            result = self.translate(pseudocode, language, **kwargs)
            
            # Save output if requested
            if output_path and result['success']:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result['code'], encoding='utf-8')
                result['metadata']['output_file'] = str(output_path)
                
            return result
            
        except Exception as e:
            logger.error(f"File translation failed: {e}")
            return {
                'success': False,
                'code': None,
                'errors': [f"File translation error: {str(e)}"],
                'warnings': [],
                'metadata': {'file': str(file_path)}
            }
            
    def batch_translate(self,
                        items: List[Union[str, Dict[str, Any]]],
                        language: Optional[str] = None,
                        parallel: bool = True,
                        progress_callback: Optional[Callable] = None,
                        **kwargs) -> List[Dict[str, Any]]:
        """
        Translate multiple items in batch
        
        Args:
            items: List of pseudocode strings or dicts with 'code' and options
            language: Default target language for all items
            parallel: Whether to use parallel processing
            progress_callback: Optional callback for progress updates
            **kwargs: Additional options
            
        Returns:
            List of translation results
        """
        results = []
        total = len(items)
        
        for i, item in enumerate(items):
            # Extract code and options
            if isinstance(item, str):
                code = item
                item_lang = language
                item_options = kwargs
            else:
                code = item.get('code', '')
                item_lang = item.get('language', language)
                item_options = {**kwargs, **item.get('options', {})}
                
            # Progress callback
            if progress_callback:
                progress_callback(i, total, f"Translating item {i+1}/{total}")
                
            # Translate
            result = self.translate(code, item_lang, **item_options)
            result['index'] = i
            results.append(result)
            
        # Final progress callback
        if progress_callback:
            progress_callback(total, total, "Batch translation complete")
            
        return results
        
    def set_default_language(self, language: str):
        """
        Set the default output language
        
        Args:
            language: Language name (e.g., "python", "javascript")
        """
        try:
            self._default_language = OutputLanguage(language.lower())
            self._translator.set_target_language(self._default_language)
        except ValueError:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: {[lang.value for lang in OutputLanguage]}"
            )
            
    def switch_model(self, model_name: str):
        """
        Switch to a different translation model
        
        Args:
            model_name: Name of the model to use
        """
        self._translator.switch_model(model_name)
        
    def update_config(self, updates: Dict[str, Any]):
        """
        Update configuration settings
        
        Args:
            updates: Dictionary of configuration updates
        """
        # Update config object
        for key, value in updates.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            elif hasattr(self._config.llm, key):
                setattr(self._config.llm, key, value)
            elif hasattr(self._config.streaming, key):
                setattr(self._config.streaming, key, value)
                
        # Recreate translator with new config
        self._translator_config = TranslatorConfig(self._config)
        self._translator.shutdown()
        self._translator = TranslationManager(self._translator_config)
        
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the translator
        
        Returns:
            Dictionary with translator information
        """
        return {
            'version': '1.0.0',
            'current_model': self._translator.get_current_model(),
            'available_models': self._translator.list_available_models(),
            'default_language': self._default_language.value,
            'supported_languages': [lang.value for lang in OutputLanguage],
            'streaming_threshold': self._streaming_threshold,
            'config': {
                'temperature': self._config.llm.temperature,
                'max_tokens': self._config.llm.max_tokens,
                'streaming_enabled': self._config.streaming.enabled
            }
        }
        
    def warmup(self):
        """Warm up the translation model"""
        logger.info("Warming up translator...")
        result = self.translate("print hello world")
        if result['success']:
            logger.info("Warmup successful")
        else:
            logger.warning("Warmup completed with errors")
            
    def shutdown(self):
        """Shutdown the translator"""
        self._translator.shutdown()
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()


class SimpleTranslator:
    """
    Simplified translator for basic use cases
    
    This class provides the simplest possible interface for translation.
    """
    
    def __init__(self, language: str = "python"):
        """
        Initialize simple translator
        
        Args:
            language: Default output language
        """
        self.api = TranslatorAPI()
        self.api.set_default_language(language)
        
    def translate(self, pseudocode: str) -> Optional[str]:
        """
        Translate pseudocode and return only the code
        
        Args:
            pseudocode: The pseudocode to translate
            
        Returns:
            Translated code or None if failed
        """
        result = self.api.translate(pseudocode)
        return result['code'] if result['success'] else None
        
    def __call__(self, pseudocode: str) -> Optional[str]:
        """Allow using the translator as a function"""
        return self.translate(pseudocode)


# Convenience functions

def translate(pseudocode: str,
              language: str = "python",
              config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to translate pseudocode
    
    Args:
        pseudocode: The pseudocode to translate
        language: Target programming language
        config_path: Optional configuration file path
        
    Returns:
        Dictionary with translation results
    """
    with TranslatorAPI(config_path) as api:
        return api.translate(pseudocode, language)


def translate_file(file_path: Union[str, Path],
                   output_path: Optional[Union[str, Path]] = None,
                   language: str = "python",
                   config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to translate a file
    
    Args:
        file_path: Path to input file
        output_path: Optional path to save translated code
        language: Target programming language
        config_path: Optional configuration file path
        
    Returns:
        Dictionary with translation results
    """
    with TranslatorAPI(config_path) as api:
        return api.translate_file(file_path, output_path, language)


async def translate_async(pseudocode: str,
                          language: str = "python",
                          config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Async function to translate pseudocode
    
    Args:
        pseudocode: The pseudocode to translate
        language: Target programming language
        config_path: Optional configuration file path
        
    Returns:
        Dictionary with translation results
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        translate,
        pseudocode,
        language,
        config_path
    )


def batch_translate(
    items: List[Union[str, Dict[str, Any]]],
    language: str = "python",
    config_path: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> List[Dict[str, Any]]:
    """
    Quick function to batch translate multiple items
    
    Args:
        items: List of pseudocode strings or dicts
        language: Default target language
        config_path: Optional configuration file path
        progress_callback: Optional progress callback
        
    Returns:
        List of translation results
    """
    with TranslatorAPI(config_path) as api:
        return api.batch_translate(
            items, language, progress_callback=progress_callback
        )


# Example usage
"""
Example Usage:

    # Simple one-liner
    from pseudocode_translator.integration.api import translate
    
    result = translate("create a function to calculate factorial")
    if result['success']:
        print(result['code'])
        
    # Using SimpleTranslator
    from pseudocode_translator.integration.api import SimpleTranslator
    
    translator = SimpleTranslator("javascript")
    code = translator("implement bubble sort")
    print(code)
    
    # File translation
    from pseudocode_translator.integration.api import translate_file
    
    result = translate_file(
        "pseudocode.txt",
        "output.py",
        language="python"
    )
    
    # Batch translation with progress
    from pseudocode_translator.integration.api import batch_translate
    
    items = [
        "function to reverse a string",
        {"code": "sort a list", "language": "javascript"},
        "find prime numbers up to n"
    ]
    
    def on_progress(current, total, message):
        print(f"[{current}/{total}] {message}")
        
    results = batch_translate(items, progress_callback=on_progress)
    
    # Using the full API
    from pseudocode_translator.integration.api import TranslatorAPI
    
    with TranslatorAPI() as api:
        # Get info
        info = api.get_info()
        print(f"Available models: {info['available_models']}")
        
        # Warmup
        api.warmup()
        
        # Translate with options
        result = api.translate(
            "implement quicksort",
            language="rust",
            use_streaming=True
        )
"""