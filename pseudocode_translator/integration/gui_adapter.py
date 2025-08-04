"""
GUI Adapter for the Pseudocode Translator

This module provides adapters and helpers for integrating the pseudocode
translator with GUI frameworks, particularly Qt-based applications.
"""

from typing import Optional, Dict, Any, Callable, Protocol
from dataclasses import dataclass
import logging
import threading

try:
    from PySide6.QtCore import (
        QObject as QtObject,
        Signal as QtSignal,
        Slot,
        QThread as QtThread
    )
    HAS_QT = True
except ImportError:
    HAS_QT = False
    # Create dummy classes for type hints
    
    class QtObject:
        def __init__(self, parent=None):
            pass
    
    class QtSignal:
        def __init__(self, *args):
            pass
            
        def emit(self, *args):
            pass
    
    class QtThread:
        pass
        
    def Slot(*args):
        """Dummy Slot decorator"""
        def decorator(func):
            return func
        return decorator

from .api import TranslatorAPI
from .callbacks import CallbackManager, CallbackType, CallbackData
from .events import EventDispatcher, EventType


logger = logging.getLogger(__name__)


class GUIUpdateProtocol(Protocol):
    """Protocol for GUI update methods"""
    
    def update_progress(self, percentage: int, message: str) -> None:
        """Update progress display"""
        ...
        
    def update_status(self, status: str, details: Dict[str, Any]) -> None:
        """Update status display"""
        ...
        
    def show_result(self, code: str, language: str) -> None:
        """Display translation result"""
        ...
        
    def show_error(self, error: str, details: Dict[str, Any]) -> None:
        """Display error message"""
        ...


@dataclass
class TranslationTask:
    """Represents a translation task"""
    id: int
    pseudocode: str
    language: str
    options: Dict[str, Any]
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class GUITranslatorAdapter:
    """
    Adapter for integrating the translator with GUI applications
    
    This class provides a high-level interface that handles threading,
    progress updates, and error handling for GUI applications.
    """
    
    def __init__(self,
                 config_path: Optional[str] = None,
                 gui_updater: Optional[GUIUpdateProtocol] = None):
        """
        Initialize GUI adapter
        
        Args:
            config_path: Optional path to configuration file
            gui_updater: Object implementing GUI update methods
        """
        self.api = TranslatorAPI(config_path)
        self.gui_updater = gui_updater
        self.callback_manager = CallbackManager()
        self.event_dispatcher = EventDispatcher()
        
        self._current_task: Optional[TranslationTask] = None
        self._task_counter = 0
        self._lock = threading.Lock()
        
        # Setup callbacks
        self._setup_callbacks()
        
    def _setup_callbacks(self):
        """Setup internal callbacks"""
        # Progress callback
        def on_progress(data: CallbackData):
            if data.type == CallbackType.PROGRESS and self.gui_updater:
                percentage = data.data.get('percentage', 0)
                message = data.message or "Processing..."
                self.gui_updater.update_progress(percentage, message)
                
        self.callback_manager.register(on_progress, CallbackType.PROGRESS)
        
        # Status callback
        def on_status(data: CallbackData):
            if data.type == CallbackType.STATUS and self.gui_updater:
                self.gui_updater.update_status(
                    data.message or "Unknown",
                    data.data
                )
                
        self.callback_manager.register(on_status, CallbackType.STATUS)
        
        # Error callback
        def on_error(data: CallbackData):
            if data.type == CallbackType.ERROR and self.gui_updater:
                self.gui_updater.show_error(
                    data.message or "Unknown error",
                    data.data
                )
                
        self.callback_manager.register(on_error, CallbackType.ERROR)
        
    def translate(self,
                  pseudocode: str,
                  language: str = "python",
                  async_mode: bool = True,
                  **options) -> Optional[int]:
        """
        Start a translation task
        
        Args:
            pseudocode: The pseudocode to translate
            language: Target programming language
            async_mode: Whether to run asynchronously
            **options: Additional translation options
            
        Returns:
            Task ID if async, None if sync
        """
        with self._lock:
            self._task_counter += 1
            task = TranslationTask(
                id=self._task_counter,
                pseudocode=pseudocode,
                language=language,
                options=options
            )
            self._current_task = task
            
        if async_mode:
            # Run in thread
            thread = threading.Thread(
                target=self._run_translation,
                args=(task,)
            )
            thread.start()
            return task.id
        else:
            # Run synchronously
            self._run_translation(task)
            return None
            
    def _run_translation(self, task: TranslationTask):
        """Run the translation task"""
        try:
            # Emit start event
            self.event_dispatcher.dispatch_event(
                EventType.TRANSLATION_STARTED,
                task_id=task.id,
                language=task.language
            )
            
            # Update status
            task.status = "running"
            self.callback_manager.trigger_status(
                "Starting translation...",
                task_id=task.id
            )
            
            # Perform translation
            result = self.api.translate(
                task.pseudocode,
                task.language,
                **task.options
            )
            
            # Update task
            task.result = result
            task.status = "completed" if result['success'] else "failed"
            
            if result['success']:
                # Show result
                if self.gui_updater:
                    self.gui_updater.show_result(
                        result['code'],
                        result['language']
                    )
                    
                # Emit completion event
                self.event_dispatcher.dispatch_event(
                    EventType.TRANSLATION_COMPLETED,
                    task_id=task.id,
                    code=result['code'],
                    language=result['language']
                )
            else:
                # Handle error
                task.error = "; ".join(result['errors'])
                
                # Emit error event
                self.event_dispatcher.dispatch_event(
                    EventType.TRANSLATION_FAILED,
                    task_id=task.id,
                    errors=result['errors']
                )
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            task.status = "error"
            task.error = str(e)
            
            # Show error
            if self.gui_updater:
                self.gui_updater.show_error(
                    str(e),
                    {'task_id': task.id}
                )
                
    def cancel_current(self):
        """Cancel the current translation task"""
        if self._current_task and self._current_task.status == "running":
            self._current_task.status = "cancelled"
            self.event_dispatcher.dispatch_event(
                EventType.TRANSLATION_CANCELLED,
                task_id=self._current_task.id
            )
            
    def get_current_task(self) -> Optional[TranslationTask]:
        """Get the current translation task"""
        return self._current_task
        
    def set_language(self, language: str):
        """Set the default output language"""
        self.api.set_default_language(language)
        self.event_dispatcher.dispatch_event(
            EventType.LANGUAGE_CHANGED,
            language=language
        )
        
    def switch_model(self, model_name: str):
        """Switch to a different model"""
        self.api.switch_model(model_name)
        self.event_dispatcher.dispatch_event(
            EventType.MODEL_CHANGED,
            model=model_name
        )
        
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration"""
        self.api.update_config(updates)
        self.event_dispatcher.dispatch_event(
            EventType.CONFIG_CHANGED,
            updates=updates
        )


if HAS_QT:
    class QtTranslatorWidget(QtObject):
        """
        Qt widget adapter for the pseudocode translator
        
        This class provides Qt signals for GUI integration.
        """
        
        # Qt signals
        progressUpdated = QtSignal(int, str)  # percentage, message
        statusUpdated = QtSignal(str, dict)  # status, details
        translationCompleted = QtSignal(str, str)  # code, language
        errorOccurred = QtSignal(str, dict)  # error, details
        
        def __init__(self,
                     config_path: Optional[str] = None,
                     parent: Optional[QtObject] = None):
            """
            Initialize Qt translator widget
            
            Args:
                config_path: Optional configuration file path
                parent: Parent QObject
            """
            super().__init__(parent)
            
            # Create adapter with self as GUI updater
            self.adapter = GUITranslatorAdapter(config_path, self)
            
            # Translation thread
            self._worker_thread: Optional[QtThread] = None
            
        def update_progress(self, percentage: int, message: str):
            """Update progress (implements GUIUpdateProtocol)"""
            self.progressUpdated.emit(percentage, message)
            
        def update_status(self, status: str, details: Dict[str, Any]):
            """Update status (implements GUIUpdateProtocol)"""
            self.statusUpdated.emit(status, details)
            
        def show_result(self, code: str, language: str):
            """Show result (implements GUIUpdateProtocol)"""
            self.translationCompleted.emit(code, language)
            
        def show_error(self, error: str, details: Dict[str, Any]):
            """Show error (implements GUIUpdateProtocol)"""
            self.errorOccurred.emit(error, details)
            
        @Slot(str, str)
        def translate(self, pseudocode: str, language: str = "python"):
            """
            Translate pseudocode (Qt slot)
            
            Args:
                pseudocode: The pseudocode to translate
                language: Target language
            """
            self.adapter.translate(pseudocode, language, async_mode=True)
            
        @Slot()
        def cancel(self):
            """Cancel current translation (Qt slot)"""
            self.adapter.cancel_current()
            
        @Slot(str)
        def setLanguage(self, language: str):
            """Set output language (Qt slot)"""
            self.adapter.set_language(language)
            
        @Slot(str)
        def switchModel(self, model_name: str):
            """Switch model (Qt slot)"""
            self.adapter.switch_model(model_name)
            
        def get_available_languages(self) -> list:
            """Get list of available languages"""
            info = self.adapter.api.get_info()
            return info['supported_languages']
            
        def get_available_models(self) -> list:
            """Get list of available models"""
            info = self.adapter.api.get_info()
            return info['available_models']


def create_progress_reporter(
    progress_bar=None,
    status_label=None,
    console_output=None
) -> Callable[[int, str], None]:
    """
    Create a progress reporter function for GUI elements
    
    Args:
        progress_bar: Progress bar widget (should have setValue method)
        status_label: Status label widget (should have setText method)
        console_output: Console/text widget (should have append method)
        
    Returns:
        Progress reporter function
    """
    def report_progress(percentage: int, message: str):
        """Report progress to GUI elements"""
        if progress_bar:
            progress_bar.setValue(percentage)
        if status_label:
            status_label.setText(message)
        if console_output:
            console_output.append(f"[{percentage}%] {message}")
            
    return report_progress


def create_result_handler(
    code_editor=None,
    language_label=None,
    save_dialog_func: Optional[Callable] = None
) -> Callable[[str, str], None]:
    """
    Create a result handler function for GUI elements
    
    Args:
        code_editor: Code editor widget (should have setText method)
        language_label: Language label widget (should have setText method)
        save_dialog_func: Function to show save dialog
        
    Returns:
        Result handler function
    """
    def handle_result(code: str, language: str):
        """Handle translation result"""
        if code_editor:
            code_editor.setText(code)
        if language_label:
            language_label.setText(f"Language: {language}")
        if save_dialog_func:
            if save_dialog_func():  # If user wants to save
                # Save logic would go here
                pass
                
    return handle_result


# Example usage
"""
Example Usage:

    # Basic GUI adapter usage
    from pseudocode_translator.integration.gui_adapter import (
        GUITranslatorAdapter
    )
    
    class MyGUI:
        def __init__(self):
            self.adapter = GUITranslatorAdapter(gui_updater=self)
            
        def update_progress(self, percentage, message):
            self.progress_bar.set_value(percentage)
            self.status_label.set_text(message)
            
        def show_result(self, code, language):
            self.code_editor.set_text(code)
            
        def translate_clicked(self):
            pseudocode = self.input_editor.get_text()
            self.adapter.translate(pseudocode, "python")
            
    # Qt integration
    if HAS_QT:
        from pseudocode_translator.integration.gui_adapter import (
            QtTranslatorWidget
        )
        
        class MainWindow(QMainWindow):
            def __init__(self):
                super().__init__()
                
                # Create translator widget
                self.translator = QtTranslatorWidget(self)
                
                # Connect signals
                self.translator.progressUpdated.connect(
                    self.on_progress_update
                )
                self.translator.translationCompleted.connect(
                    self.on_translation_complete
                )
                
            def on_translate_button(self):
                code = self.input_text.toPlainText()
                lang = self.language_combo.currentText()
                self.translator.translate(code, lang)
                
            def on_progress_update(self, percentage, message):
                self.progress_bar.setValue(percentage)
                self.status_bar.showMessage(message)
                
            def on_translation_complete(self, code, language):
                self.output_text.setPlainText(code)
"""