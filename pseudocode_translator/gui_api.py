"""
PySide6 Integration API for Pseudocode Translator

This module provides a clean, signal-based API for integrating the
pseudocode translator with PySide6 GUI applications.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import logging

from PySide6.QtCore import QObject, Signal, Slot, QThread
from PySide6.QtWidgets import QApplication

from .models import ParseResult, CodeBlock, BlockType
from .parser import ParserModule
from .llm_interface import LLMInterface
from .config import TranslatorConfig, ConfigManager
from .gui_worker import TranslationWorker, TranslationStatus, TranslationResult
from .assembler import CodeAssembler
from .validator import Validator


logger = logging.getLogger(__name__)




class PseudocodeTranslatorAPI(QObject):
    """
    Main API class for PySide6 integration
    
    Provides both synchronous and asynchronous translation methods with
    Qt signals for progress updates and status notifications.
    
    Example usage:
        translator = PseudocodeTranslatorAPI()
        translator.translation_completed.connect(on_translation_done)
        translator.translate_async("create a function that adds two numbers")
    """
    
    # Qt Signals for GUI communication
    translation_started = Signal()
    translation_progress = Signal(int)  # Progress percentage (0-100)
    translation_status = Signal(TranslationStatus)  # Detailed status
    translation_completed = Signal(TranslationResult)  # Final result
    translation_error = Signal(str)  # Error message
    model_status_changed = Signal(str)  # Model status message
    model_initialized = Signal()  # Model ready
    
    # Streaming signals
    streaming_started = Signal()
    streaming_chunk_processed = Signal(int, str)  # chunk_index, chunk_code
    streaming_progress = Signal(dict)  # Progress info with memory usage
    streaming_completed = Signal(str)  # Final assembled code
    memory_usage_updated = Signal(dict)  # Memory usage stats
    
    def __init__(self, config_path: Optional[str] = None, parent: Optional[QObject] = None):
        """
        Initialize the translator API
        
        Args:
            config_path: Optional path to configuration file
            parent: Optional parent QObject
        """
        super().__init__(parent)
        
        # Load configuration
        self.config = ConfigManager.load(config_path)
        
        # Initialize components
        self.parser = ParserModule()
        self.llm_interface = LLMInterface(self.config.llm)
        self.assembler = CodeAssembler(self.config)
        self.validator = Validator(self.config)
        
        # Worker thread management
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[TranslationWorker] = None
        
        # State tracking
        self._is_translating = False
        self._model_initialized = False
        self._is_streaming = False
        self._streaming_pipeline = None
        
        # Auto-initialize model in background
        self._init_model_async()
    
    @property
    def is_ready(self) -> bool:
        """Check if the translator is ready to process requests"""
        return self._model_initialized and not self._is_translating and not self._is_streaming
    
    @property
    def is_translating(self) -> bool:
        """Check if a translation is currently in progress"""
        return self._is_translating
    
    def translate(self, pseudocode: str) -> TranslationResult:
        """
        Synchronous translation method
        
        Args:
            pseudocode: Mixed English/Python pseudocode input
            
        Returns:
            TranslationResult object with code and metadata
            
        Note:
            This method blocks until translation is complete.
            For GUI applications, use translate_async() instead.
        """
        try:
            # Ensure model is initialized
            if not self._model_initialized:
                self.model_status_changed.emit("Initializing model...")
                self.llm_interface.initialize_model()
                self._model_initialized = True
                self.model_initialized.emit()
            
            # Parse the pseudocode
            self.translation_status.emit(TranslationStatus(
                phase="parsing",
                progress=10,
                message="Parsing pseudocode..."
            ))
            
            parse_result = self.parser.get_parse_result(pseudocode)
            
            if not parse_result.success:
                return TranslationResult(
                    success=False,
                    code=None,
                    errors=[str(e) for e in parse_result.errors],
                    warnings=parse_result.warnings,
                    metadata={"phase": "parsing"},
                    parse_result=parse_result
                )
            
            # Translate English blocks
            self.translation_status.emit(TranslationStatus(
                phase="translating",
                progress=30,
                message="Translating instructions to Python..."
            ))
            
            translated_blocks = []
            english_blocks = parse_result.get_blocks_by_type(BlockType.ENGLISH)
            
            for i, block in enumerate(english_blocks):
                progress = 30 + int((i / len(english_blocks)) * 40)
                self.translation_progress.emit(progress)
                
                # Get context from surrounding blocks
                context = {
                    'code': block.context,
                    'metadata': block.metadata
                }
                
                try:
                    python_code = self.llm_interface.translate(
                        block.content,
                        context
                    )
                    translated_blocks.append(python_code)
                except Exception as e:
                    logger.error(f"Translation failed for block: {e}")
                    translated_blocks.append(f"# Translation failed: {str(e)}")
            
            # Assemble final code
            self.translation_status.emit(TranslationStatus(
                phase="assembling",
                progress=80,
                message="Assembling final code..."
            ))
            
            # Create CodeBlock objects for assembly
            assembled_blocks = self._create_code_blocks_for_assembly(parse_result, translated_blocks)
            
            # Use CodeAssembler for sophisticated assembly
            final_code = self.assembler.assemble(assembled_blocks)
            
            # Validate
            self.translation_status.emit(TranslationStatus(
                phase="validating",
                progress=90,
                message="Validating generated code..."
            ))
            
            # Use Validator for comprehensive validation
            validation_result = self.validator.validate_syntax(final_code)
            validation_errors = validation_result.errors if not validation_result.is_valid else []
            
            # Create result
            result = TranslationResult(
                success=len(validation_errors) == 0,
                code=final_code,
                errors=validation_errors,
                warnings=parse_result.warnings,
                metadata={
                    "blocks_processed": parse_result.block_count,
                    "english_blocks": len(english_blocks),
                    "model_info": self.llm_interface.get_model_info()
                },
                parse_result=parse_result
            )
            
            self.translation_progress.emit(100)
            return result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return TranslationResult(
                success=False,
                code=None,
                errors=[str(e)],
                warnings=[],
                metadata={"error": str(e)}
            )
    
    @Slot(str)
    def translate_async(self, pseudocode: str):
        """
        Asynchronous translation method using worker thread
        
        Args:
            pseudocode: Mixed English/Python pseudocode input
            
        Emits:
            translation_started: When translation begins
            translation_progress: Progress updates (0-100)
            translation_status: Detailed status updates
            translation_completed: When done with TranslationResult
            translation_error: If an error occurs
        """
        if self._is_translating:
            self.translation_error.emit("Translation already in progress")
            return
        
        # Clean up previous worker if exists
        self._cleanup_worker()
        
        # Create new worker thread
        self._worker_thread = QThread()
        self._worker = TranslationWorker(
            pseudocode,
            self.config,
            self.parser,
            self.llm_interface
        )
        
        # Move worker to thread
        self._worker.moveToThread(self._worker_thread)
        
        # Connect signals
        self._worker_thread.started.connect(self._worker.run)
        self._worker.started.connect(self._on_translation_started)
        self._worker.progress.connect(self.translation_progress)
        self._worker.status.connect(self.translation_status)
        self._worker.completed.connect(self._on_translation_completed)
        self._worker.error.connect(self._on_translation_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        
        # Start translation
        self._is_translating = True
        self._worker_thread.start()
    
    @Slot()
    def cancel_translation(self):
        """Cancel the current translation operation"""
        if self._worker and self._is_translating:
            self._worker.cancel()
            self.translation_status.emit(TranslationStatus(
                phase="cancelled",
                progress=0,
                message="Translation cancelled by user"
            ))
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Get current model status and health information
        
        Returns:
            Dictionary with model status information
        """
        return self.llm_interface.get_model_info()
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update configuration without restart
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        # Update config fields
        for key, value in config_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
            elif hasattr(self.config.llm, key):
                setattr(self.config.llm, key, value)
        
        # Re-initialize if model config changed
        if any(key in config_updates for key in ['model_path', 'model_file']):
            self._model_initialized = False
            self._init_model_async()
    
    def warmup_model(self):
        """Warm up the model for better initial performance"""
        if self._model_initialized:
            thread = QThread()
            thread.run = self.llm_interface.warmup
            thread.start()
    
    @Slot(str)
    def translate_streaming(self, pseudocode: str):
        """
        Translate using streaming for memory-efficient processing
        
        Args:
            pseudocode: Mixed English/Python pseudocode input
            
        Emits:
            streaming_started: When streaming begins
            streaming_chunk_processed: For each processed chunk
            streaming_progress: Progress with memory usage info
            streaming_completed: When done with final code
            translation_error: If an error occurs
        """
        if self._is_streaming or self._is_translating:
            self.translation_error.emit("Translation already in progress")
            return
        
        # Check if streaming should be used
        code_size = len(pseudocode.encode('utf-8'))
        if code_size < self.config.streaming.auto_enable_threshold:
            # File too small, use regular translation
            self.translate_async(pseudocode)
            return
        
        self._is_streaming = True
        
        def run_streaming():
            try:
                from .streaming.pipeline import StreamingPipeline, StreamingProgress
                
                self.streaming_started.emit()
                
                # Create streaming pipeline
                self._streaming_pipeline = StreamingPipeline(self.config)
                
                # Progress callback
                def on_progress(progress: StreamingProgress):
                    progress_info = {
                        'progress': progress.progress_percentage,
                        'chunks_processed': progress.processed_chunks,
                        'total_chunks': progress.total_chunks,
                        'bytes_processed': progress.bytes_processed,
                        'total_bytes': progress.total_bytes,
                        'errors': progress.errors,
                        'warnings': progress.warnings
                    }
                    self.streaming_progress.emit(progress_info)
                    
                    # Update memory usage
                    if self._streaming_pipeline:
                        memory_stats = self._streaming_pipeline.get_memory_usage()
                        self.memory_usage_updated.emit(memory_stats)
                
                # Process with streaming
                chunk_results = []
                for chunk_result in self._streaming_pipeline.stream_translate(
                    pseudocode,
                    progress_callback=on_progress
                ):
                    if chunk_result.success and chunk_result.translated_blocks:
                        # Emit chunk processed signal
                        chunk_code = self.assembler.assemble(
                            chunk_result.translated_blocks
                        )
                        self.streaming_chunk_processed.emit(
                            chunk_result.chunk_index,
                            chunk_code
                        )
                    chunk_results.append(chunk_result)
                
                # Assemble final code
                final_code = self._streaming_pipeline.assemble_streamed_code()
                
                # Validate final code
                validation_result = self.validator.validate_syntax(final_code)
                
                # Create translation result
                result = TranslationResult(
                    success=validation_result.is_valid,
                    code=final_code,
                    errors=validation_result.errors,
                    warnings=validation_result.warnings,
                    metadata={
                        'streaming': True,
                        'chunks_processed': len(chunk_results),
                        'memory_usage': self._streaming_pipeline.get_memory_usage()
                    }
                )
                
                self.streaming_completed.emit(final_code)
                self.translation_completed.emit(result)
                
            except ImportError:
                self.translation_error.emit(
                    "Streaming module not available. Using regular translation."
                )
                self._is_streaming = False
                self.translate_async(pseudocode)
                
            except Exception as e:
                logger.error(f"Streaming translation failed: {e}")
                self.translation_error.emit(str(e))
                
            finally:
                self._is_streaming = False
                if self._streaming_pipeline:
                    self._streaming_pipeline.cancel_streaming()
                    self._streaming_pipeline = None
        
        # Run in thread
        thread = QThread()
        thread.run = run_streaming
        thread.start()
    
    @Slot()
    def cancel_streaming(self):
        """Cancel ongoing streaming operation"""
        if self._streaming_pipeline:
            self._streaming_pipeline.cancel_streaming()
            self.translation_status.emit(TranslationStatus(
                phase="cancelled",
                progress=0,
                message="Streaming translation cancelled"
            ))
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage statistics
        
        Returns:
            Dictionary with memory usage information
        """
        if self._streaming_pipeline:
            return self._streaming_pipeline.get_memory_usage()
        return {
            'buffer_size': 0,
            'context_window_size': 0,
            'queue_size': 0
        }
    
    # Private methods
    
    def _init_model_async(self):
        """Initialize model in background thread"""
        def init_model():
            try:
                self.model_status_changed.emit("Loading language model...")
                self.llm_interface.initialize_model()
                self._model_initialized = True
                self.model_status_changed.emit("Model ready")
                self.model_initialized.emit()
            except Exception as e:
                self.model_status_changed.emit(f"Model initialization failed: {e}")
                self.translation_error.emit(f"Failed to initialize model: {e}")
        
        thread = QThread()
        thread.run = init_model
        thread.start()
    
    def _create_code_blocks_for_assembly(self, parse_result: ParseResult, translated_blocks: List[str]) -> List[CodeBlock]:
        """
        Create CodeBlock objects for assembly by combining original blocks with translations
        
        Args:
            parse_result: The parse result containing all blocks
            translated_blocks: List of translated Python code for English blocks
            
        Returns:
            List of CodeBlock objects ready for assembly
        """
        assembled_blocks = []
        translation_index = 0
        
        for block in parse_result.blocks:
            if block.type == BlockType.ENGLISH:
                # Replace English block with translated Python code
                if translation_index < len(translated_blocks):
                    translated_code = translated_blocks[translation_index]
                    # Create a new CodeBlock with the translated content
                    python_block = CodeBlock(
                        type=BlockType.PYTHON,
                        content=translated_code,
                        line_numbers=block.line_numbers,
                        context=block.context,
                        metadata=block.metadata
                    )
                    assembled_blocks.append(python_block)
                    translation_index += 1
            else:
                # Keep other blocks as-is (Python, Comment, Mixed)
                assembled_blocks.append(block)
        
        return assembled_blocks
    
    def _cleanup_worker(self):
        """Clean up worker thread resources"""
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait()
        
        self._worker = None
        self._worker_thread = None
    
    # Slot handlers
    
    @Slot()
    def _on_translation_started(self):
        """Handle translation start"""
        self.translation_started.emit()
    
    @Slot(TranslationResult)
    def _on_translation_completed(self, result: TranslationResult):
        """Handle translation completion"""
        self._is_translating = False
        self.translation_completed.emit(result)
    
    @Slot(str)
    def _on_translation_error(self, error: str):
        """Handle translation error"""
        self._is_translating = False
        self.translation_error.emit(error)
    
    # Cleanup
    
    def __del__(self):
        """Cleanup on deletion"""
        self._cleanup_worker()
        if hasattr(self, 'llm_interface'):
            self.llm_interface.shutdown()


# Convenience factory function
def create_translator_api(config_path: Optional[str] = None) -> PseudocodeTranslatorAPI:
    """
    Create a translator API instance
    
    Args:
        config_path: Optional configuration file path
        
    Returns:
        Configured PseudocodeTranslatorAPI instance
    """
    return PseudocodeTranslatorAPI(config_path)