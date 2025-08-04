"""
DinoTranslate - Pseudocode Translator Integration for DinoAir 2.0

This module provides a wrapper around the new pseudocode translator to
integrate the pseudocode translation functionality into the main DinoAir
application.

Features:
- Multi-language output support
- Streaming translation for large files
- Model selection and switching
- Advanced error handling
- Progress reporting and cancellation
- Configuration integration
"""

import sys
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum
import json

from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer

# Add pseudocode_translator to path if needed
translator_path = Path(__file__).parent.parent.parent / "pseudocode_translator"
if str(translator_path) not in sys.path:
    sys.path.insert(0, str(translator_path))

try:
    from pseudocode_translator import (
        TranslationManager,
        TranslatorConfig,
        ConfigManager
    )
    from pseudocode_translator.models.base_model import OutputLanguage
    from pseudocode_translator.exceptions import TranslatorError
except ImportError as e:
    logging.error(f"Failed to import pseudocode translator: {e}")
    raise ImportError(
        "Pseudocode translator module not found. "
        "Please ensure it's installed."
    ) from e


logger = logging.getLogger(__name__)


class TranslationStatus(Enum):
    """Status of a translation operation"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PARSING = "parsing"
    TRANSLATING = "translating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class TranslationWorker(QThread):
    """Worker thread for asynchronous translation"""
    
    # Signals
    progress = Signal(int)  # Progress percentage
    status_changed = Signal(str)  # Status message
    result_ready = Signal(dict)  # Translation result
    error_occurred = Signal(str)  # Error message
    
    def __init__(self, 
                 translator: TranslationManager,
                 pseudocode: str,
                 target_language: OutputLanguage,
                 use_streaming: bool = False):
        super().__init__()
        self.translator = translator
        self.pseudocode = pseudocode
        self.target_language = target_language
        self.use_streaming = use_streaming
        self._cancelled = False
        
    def run(self):
        """Run the translation in a separate thread"""
        try:
            self.status_changed.emit("Starting translation...")
            self.progress.emit(10)
            
            if self.use_streaming:
                # Streaming translation
                self._run_streaming_translation()
            else:
                # Regular translation
                self._run_regular_translation()
                
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            self.error_occurred.emit(str(e))
            self.status_changed.emit("Translation failed")
            
    def _run_regular_translation(self):
        """Run regular (non-streaming) translation"""
        # Set target language
        self.translator.set_target_language(self.target_language)
        
        self.status_changed.emit("Parsing pseudocode...")
        self.progress.emit(30)
        
        # Translate
        result = self.translator.translate_pseudocode(
            self.pseudocode,
            self.target_language
        )
        
        if self._cancelled:
            self.status_changed.emit("Translation cancelled")
            return
            
        self.progress.emit(80)
        self.status_changed.emit("Validating code...")
        
        # Convert result
        result_dict = {
            'success': result.success,
            'code': result.code,
            'errors': result.errors,
            'warnings': result.warnings,
            'metadata': result.metadata,
            'language': self.target_language.value
        }
        
        self.progress.emit(100)
        self.status_changed.emit("Translation completed")
        self.result_ready.emit(result_dict)
        
    def _run_streaming_translation(self):
        """Run streaming translation for large files"""
        self.status_changed.emit("Starting streaming translation...")
        
        # Collect chunks
        all_code_parts = []
        chunk_count = 0
        
        def progress_callback(progress_info):
            if self._cancelled:
                return False
            # Update progress
            percent = progress_info.get('percentage', 0)
            # Reserve 20% for final steps
            self.progress.emit(int(percent * 0.8))
            return True
            
        try:
            chunk_result = None
            for chunk_result in self.translator.translate_streaming(
                self.pseudocode,
                progress_callback=progress_callback
            ):
                if self._cancelled:
                    self.status_changed.emit("Translation cancelled")
                    return
                    
                chunk_count += 1
                self.status_changed.emit(f"Processing chunk {chunk_count}...")
                
                if chunk_result.success and chunk_result.code:
                    all_code_parts.append(chunk_result.code)
                    
            # Final result should be the last chunk
            if chunk_result and chunk_result.success:
                self.progress.emit(90)
                self.status_changed.emit("Finalizing translation...")
                
                result_dict = {
                    'success': True,
                    'code': chunk_result.code,  # Final assembled code
                    'errors': chunk_result.errors,
                    'warnings': chunk_result.warnings,
                    'metadata': {
                        **chunk_result.metadata,
                        'chunks_processed': chunk_count,
                        'streaming': True
                    },
                    'language': self.target_language.value
                }
                
                self.progress.emit(100)
                self.status_changed.emit("Streaming translation completed")
                self.result_ready.emit(result_dict)
            else:
                raise TranslatorError("Streaming translation failed")
                
        except Exception as e:
            logger.error(f"Streaming translation error: {e}")
            self.error_occurred.emit(str(e))
            
    def cancel(self):
        """Cancel the translation"""
        self._cancelled = True


class DinoTranslate(QObject):
    """
    Main translator class for DinoAir integration
    
    This class wraps the TranslationManager and provides a clean interface
    for translating pseudocode to various programming languages within the
    DinoAir application.
    
    Signals:
        translation_started: Emitted when translation begins
        translation_progress: Emitted with progress percentage (0-100)
        translation_status: Emitted with detailed status updates
        translation_completed: Emitted when translation completes with result
        translation_error: Emitted when an error occurs
        model_ready: Emitted when the language model is initialized
        language_changed: Emitted when output language changes
        model_changed: Emitted when the translation model changes
    """
    
    # Signals
    translation_started = Signal()
    translation_progress = Signal(int)  # Progress percentage
    translation_status = Signal(dict)  # Status information
    translation_completed = Signal(dict)  # Translation result
    translation_error = Signal(str)  # Error message
    model_ready = Signal()
    language_changed = Signal(str)  # New language
    model_changed = Signal(str)  # New model name
    
    def __init__(self, config_path: Optional[str] = None,
                 parent: Optional[QObject] = None):
        """
        Initialize the DinoTranslate wrapper
        
        Args:
            config_path: Optional path to translator configuration file
            parent: Optional parent QObject for Qt hierarchy
        """
        super().__init__(parent)
        
        self._translator: Optional[TranslationManager] = None
        self._config_path = config_path
        self._is_initialized = False
        self._current_translation_id = 0
        self._current_worker: Optional[TranslationWorker] = None
        self._current_language = OutputLanguage.PYTHON
        self._available_languages = list(OutputLanguage)
        
        # Load configuration
        self._load_configuration()
        
        # Initialize in a thread-safe manner
        self._initialize_translator()
        
    def _load_configuration(self):
        """Load and merge configuration from app_config.json"""
        try:
            # Load translator config
            if self._config_path:
                self._config = ConfigManager.load(self._config_path)
            else:
                self._config = ConfigManager.load()
                
            # Try to merge with app config
            app_config_path = (
                Path(__file__).parent.parent.parent /
                "config" / "app_config.json"
            )
            if app_config_path.exists():
                with open(app_config_path, 'r') as f:
                    app_config = json.load(f)
                    
                # Map app config to translator config
                if 'ai' in app_config:
                    ai_config = app_config['ai']
                    # Update temperature if specified
                    if 'temperature' in ai_config:
                        self._config.llm.temperature = ai_config['temperature']
                    # Update max_tokens if specified
                    if 'max_tokens' in ai_config:
                        self._config.llm.max_tokens = ai_config['max_tokens']
                        
                # Apply any translator-specific settings
                if 'pseudocode_translator' in app_config:
                    trans_config = app_config['pseudocode_translator']
                    if 'model' in trans_config:
                        self._config.llm.model_type = trans_config['model']
                    if 'streaming_enabled' in trans_config:
                        self._config.streaming.enabled = (
                            trans_config['streaming_enabled']
                        )
                        
        except Exception as e:
            logger.warning(f"Failed to load/merge configuration: {e}")
            # Use default config
            self._config = ConfigManager.load()
    
    def _initialize_translator(self):
        """Initialize the translator with error handling"""
        try:
            logger.info("Initializing pseudocode translator...")
            
            # Create TranslatorConfig wrapper
            translator_config = TranslatorConfig(self._config)
            
            # Create the translator instance
            self._translator = TranslationManager(translator_config)
            
            # Mark as initialized
            self._is_initialized = True
            logger.info("Pseudocode translator initialized successfully")
            
            # Emit model ready signal
            QTimer.singleShot(100, self.model_ready.emit)
            
        except Exception as e:
            logger.error(f"Failed to initialize translator: {e}")
            self._is_initialized = False
            self.translation_error.emit(
                f"Translator initialization failed: {str(e)}"
            )
    
    @property
    def is_ready(self) -> bool:
        """Check if the translator is ready to accept requests"""
        return (self._is_initialized and 
                self._translator is not None)
    
    @property
    def is_translating(self) -> bool:
        """Check if a translation is currently in progress"""
        return (self._current_worker is not None and 
                self._current_worker.isRunning())
    
    @property
    def current_language(self) -> str:
        """Get the current output language"""
        return self._current_language.value
    
    @property
    def available_languages(self) -> List[str]:
        """Get list of available output languages"""
        return [lang.value for lang in OutputLanguage]
    
    @property
    def available_models(self) -> List[str]:
        """Get list of available translation models"""
        if self._translator:
            return self._translator.list_available_models()
        return []
    
    @property
    def current_model(self) -> Optional[str]:
        """Get the current model name"""
        if self._translator:
            return self._translator.get_current_model()
        return None
    
    def set_language(self, language: str) -> bool:
        """
        Set the output programming language
        
        Args:
            language: Language name (e.g., "python", "javascript")
            
        Returns:
            True if language was set successfully
        """
        try:
            # Convert string to enum
            lang_enum = OutputLanguage(language.lower())
            self._current_language = lang_enum
            
            if self._translator:
                self._translator.set_target_language(lang_enum)
                
            self.language_changed.emit(language)
            logger.info(f"Output language set to: {language}")
            return True
            
        except ValueError:
            logger.error(f"Unsupported language: {language}")
            self.translation_error.emit(
                f"Unsupported language: {language}. "
                f"Available: {', '.join(self.available_languages)}"
            )
            return False
    
    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different translation model
        
        Args:
            model_name: Name of the model to switch to
            
        Returns:
            True if model was switched successfully
        """
        if not self._translator:
            return False
            
        try:
            self._translator.switch_model(model_name)
            self.model_changed.emit(model_name)
            logger.info(f"Switched to model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch model: {e}")
            self.translation_error.emit(
                f"Failed to switch to model '{model_name}': {str(e)}"
            )
            return False
    
    def translate(self, pseudocode: str,
                  language: Optional[str] = None,
                  use_streaming: bool = False) -> Optional[int]:
        """
        Translate pseudocode to code asynchronously
        
        Args:
            pseudocode: The mixed English/Python pseudocode to translate
            language: Target programming language (uses current if None)
            use_streaming: Whether to use streaming mode for large files
            
        Returns:
            Translation ID for tracking, or None if translation couldn't start
            
        Emits:
            translation_started: When translation begins
            translation_progress: During translation with percentage
            translation_status: With detailed status updates
            translation_completed: When done with result dictionary
            translation_error: If an error occurs
        """
        if not self.is_ready:
            error_msg = "Translator not ready. Please wait for initialization."
            logger.warning(error_msg)
            self.translation_error.emit(error_msg)
            return None
        
        if self.is_translating:
            error_msg = ("Translation already in progress. "
                         "Please wait or cancel.")
            logger.warning(error_msg)
            self.translation_error.emit(error_msg)
            return None
        
        # Validate input
        if not pseudocode or not pseudocode.strip():
            error_msg = "No pseudocode provided for translation"
            logger.warning(error_msg)
            self.translation_error.emit(error_msg)
            return None
        
        # Set language if specified
        if language:
            if not self.set_language(language):
                return None
        
        try:
            # Increment translation ID
            self._current_translation_id += 1
            
            # Determine if we should use streaming
            if not use_streaming and len(pseudocode) > 50000:
                use_streaming = True
                logger.info("Auto-enabling streaming for large input")
            
            logger.info(
                f"Starting translation {self._current_translation_id} "
                f"(language: {self._current_language.value}, "
                f"streaming: {use_streaming}, "
                f"size: {len(pseudocode)} bytes)"
            )
            
            # Create worker thread
            if self._translator is None:
                raise RuntimeError("Translator not initialized")
                
            self._current_worker = TranslationWorker(
                self._translator,
                pseudocode,
                self._current_language,
                use_streaming
            )
            
            # Connect signals
            self._current_worker.progress.connect(self._on_progress)
            self._current_worker.status_changed.connect(
                self._on_status_changed
            )
            self._current_worker.result_ready.connect(self._on_result_ready)
            self._current_worker.error_occurred.connect(self._on_error)
            self._current_worker.finished.connect(self._on_worker_finished)
            
            # Start translation
            self._current_worker.start()
            self.translation_started.emit()
            
            # Emit initial status
            self.translation_status.emit({
                'phase': 'started',
                'progress': 0,
                'message': 'Translation started',
                'translation_id': self._current_translation_id
            })
            
            return self._current_translation_id
            
        except Exception as e:
            logger.error(f"Failed to start translation: {e}")
            self.translation_error.emit(
                f"Failed to start translation: {str(e)}"
            )
            return None
    
    @Slot(int)
    def _on_progress(self, percentage: int):
        """Handle progress updates"""
        self.translation_progress.emit(percentage)
        
    @Slot(str)
    def _on_status_changed(self, message: str):
        """Handle status changes"""
        self.translation_status.emit({
            'phase': 'processing',
            'message': message,
            'translation_id': self._current_translation_id
        })
        
    @Slot(dict)
    def _on_result_ready(self, result: Dict[str, Any]):
        """Handle translation result"""
        # Add translation ID
        result['translation_id'] = self._current_translation_id
        self.translation_completed.emit(result)
        
    @Slot(str)
    def _on_error(self, error_message: str):
        """Handle translation error"""
        self.translation_error.emit(error_message)
        self.translation_status.emit({
            'phase': 'error',
            'message': error_message,
            'translation_id': self._current_translation_id
        })
        
    @Slot()
    def _on_worker_finished(self):
        """Handle worker thread completion"""
        self._current_worker = None
    
    def translate_sync(self, pseudocode: str,
                       language: Optional[str] = None) -> Dict[str, Any]:
        """
        Translate pseudocode synchronously (blocks until complete)
        
        Args:
            pseudocode: The mixed English/Python pseudocode to translate
            language: Target programming language
            
        Returns:
            Dictionary with translation result
            
        Note:
            This method blocks the calling thread.
            Use translate() for GUI applications.
        """
        if not self.is_ready:
            return {
                'success': False,
                'code': None,
                'errors': ['Translator not ready'],
                'warnings': [],
                'metadata': {}
            }
        
        if not self._translator:
            return {
                'success': False,
                'code': None,
                'errors': ['Translator not initialized'],
                'warnings': [],
                'metadata': {}
            }
        
        # Set language if specified
        if language:
            try:
                lang_enum = OutputLanguage(language.lower())
                self._translator.set_target_language(lang_enum)
            except ValueError:
                return {
                    'success': False,
                    'code': None,
                    'errors': [f'Unsupported language: {language}'],
                    'warnings': [],
                    'metadata': {}
                }
        
        try:
            result = self._translator.translate_pseudocode(
                pseudocode,
                self._current_language
            )
            return {
                'success': result.success,
                'code': result.code,
                'errors': result.errors,
                'warnings': result.warnings,
                'metadata': result.metadata,
                'language': self._current_language.value
            }
        except Exception as e:
            logger.error(f"Synchronous translation failed: {e}")
            return {
                'success': False,
                'code': None,
                'errors': [str(e)],
                'warnings': [],
                'metadata': {'error': str(e)}
            }
    
    def cancel_translation(self):
        """Cancel the current translation operation"""
        if self._current_worker and self._current_worker.isRunning():
            logger.info("Cancelling translation...")
            self._current_worker.cancel()
            self._current_worker.quit()
            self._current_worker.wait(5000)  # Wait up to 5 seconds
            
            self.translation_status.emit({
                'phase': 'cancelled',
                'message': 'Translation cancelled',
                'translation_id': self._current_translation_id
            })
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Get current model status and health information
        
        Returns:
            Dictionary with model status information
        """
        if not self._translator:
            return {
                'initialized': False,
                'error': 'Translator not initialized'
            }
        
        try:
            # Get current model info
            current_model = self._translator.get_current_model()
            
            return {
                'initialized': self._is_initialized,
                'current_model': current_model,
                'available_models': self.available_models,
                'current_language': self.current_language,
                'supported_languages': self.available_languages,
                'is_translating': self.is_translating
            }
        except Exception as e:
            logger.error(f"Failed to get model status: {e}")
            return {
                'initialized': self._is_initialized,
                'error': str(e)
            }
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update translator configuration
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        if not self._translator:
            return
            
        try:
            # Update internal config
            for key, value in config_updates.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                elif hasattr(self._config.llm, key):
                    setattr(self._config.llm, key, value)
                elif hasattr(self._config.streaming, key):
                    setattr(self._config.streaming, key, value)
            
            # Reinitialize translator with new config
            self._translator.shutdown()
            translator_config = TranslatorConfig(self._config)
            self._translator = TranslationManager(translator_config)
            
            logger.info(f"Updated translator config: {config_updates}")
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            self.translation_error.emit(
                f"Configuration update failed: {str(e)}"
            )
    
    def warmup_model(self):
        """Warm up the model for better initial performance"""
        if self._translator and self._is_initialized:
            logger.info("Warming up translation model...")
            try:
                # Simple warmup translation
                warmup_result = self._translator.translate_pseudocode(
                    "print hello world",
                    OutputLanguage.PYTHON
                )
                if warmup_result.success:
                    logger.info("Model warmup completed successfully")
                else:
                    logger.warning("Model warmup completed with warnings")
            except Exception as e:
                logger.error(f"Model warmup failed: {e}")
    
    def get_error_suggestions(self, error_message: str) -> List[str]:
        """
        Get suggestions for fixing an error
        
        Args:
            error_message: The error message
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        error_lower = error_message.lower()
        
        if "initialization" in error_lower:
            suggestions.extend([
                "Check that model files are present",
                "Verify configuration settings",
                "Ensure sufficient memory is available"
            ])
        elif "syntax" in error_lower:
            suggestions.extend([
                "Check pseudocode syntax",
                "Ensure proper indentation",
                "Verify statement completeness"
            ])
        elif "language" in error_lower:
            suggestions.extend([
                f"Available languages: {', '.join(self.available_languages)}",
                "Use set_language() to change output language"
            ])
        elif "model" in error_lower:
            suggestions.extend([
                f"Available models: {', '.join(self.available_models)}",
                "Check model file paths",
                "Verify model compatibility"
            ])
            
        return suggestions
    
    def shutdown(self):
        """Clean shutdown of the translator"""
        logger.info("Shutting down translator...")
        
        # Cancel any ongoing translations
        if self.is_translating:
            self.cancel_translation()
        
        # Clean up the translator
        if self._translator:
            try:
                self._translator.shutdown()
            except Exception as e:
                logger.error(f"Error during translator shutdown: {e}")
            
            self._translator = None
        
        self._is_initialized = False
        logger.info("Translator shutdown complete")
    
    def __del__(self):
        """Ensure cleanup on deletion"""
        self.shutdown()


# Convenience factory function
def create_translator(config_path: Optional[str] = None,
                      parent: Optional[QObject] = None) -> DinoTranslate:
    """
    Factory function to create a DinoTranslate instance
    
    Args:
        config_path: Optional path to configuration file
        parent: Optional parent QObject
        
    Returns:
        Configured DinoTranslate instance
    """
    return DinoTranslate(config_path, parent)


# Example usage and integration guide
"""
Example Integration:

    # In your main window or controller:
    from src.agents.translator import DinoTranslate
    
    class MainController(QObject):
        def __init__(self):
            super().__init__()
            
            # Create translator
            self.translator = DinoTranslate()
            
            # Connect signals
            self.translator.translation_completed.connect(self.on_translation_done)
            self.translator.translation_progress.connect(self.on_progress)
            self.translator.translation_error.connect(self.on_error)
            self.translator.model_ready.connect(self.on_model_ready)
            
        def translate_code(self, pseudocode, language="python"):
            # Start translation
            translation_id = self.translator.translate(
                pseudocode, 
                language=language,
                use_streaming=len(pseudocode) > 10000
            )
            if translation_id:
                print(f"Started translation {translation_id}")
        
        def on_translation_done(self, result):
            if result['success']:
                print(f"Translation complete: {result['code']}")
                print(f"Language: {result['language']}")
            else:
                print(f"Translation failed: {result['errors']}")
        
        def on_progress(self, percentage):
            print(f"Progress: {percentage}%")
        
        def on_error(self, error):
            print(f"Error: {error}")
            suggestions = self.translator.get_error_suggestions(error)
            for suggestion in suggestions:
                print(f"  - {suggestion}")
                
        def on_model_ready(self):
            print("Model ready!")
            print(
                f"Available languages: {self.translator.available_languages}"
            )
            print(f"Available models: {self.translator.available_models}")
"""