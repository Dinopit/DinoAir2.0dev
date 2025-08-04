"""
Pseudocode Tool - Tool wrapper for the pseudocode translator

This module provides a tool interface for the pseudocode translator,
enabling integration with the DinoAir tool system. It supports both
synchronous and asynchronous operations with progress reporting and
cancellation capabilities.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from enum import Enum

from src.agents.translator import create_translator


logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Status of the tool operation"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """Result of a tool operation"""
    success: bool
    output: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ToolStatus = ToolStatus.COMPLETED


@dataclass
class ToolProgress:
    """Progress information for a tool operation"""
    percentage: int
    message: str
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PseudocodeTool:
    """
    Tool wrapper for the pseudocode translator
    
    This class provides a standardized tool interface for the pseudocode
    translator, making it easy to integrate with the DinoAir tool system.
    
    Features:
    - Synchronous and asynchronous translation
    - Progress reporting
    - Cancellation support
    - Error handling with recovery suggestions
    - Multi-language support
    - Model switching
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the pseudocode tool
        
        Args:
            config_path: Optional path to configuration file
        """
        self.translator = create_translator(config_path)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._current_task: Optional[asyncio.Task] = None
        self._progress_callbacks: List[Callable[[ToolProgress], None]] = []
        self._status = ToolStatus.IDLE
        self._lock = threading.Lock()
        
        # Connect translator signals to tool callbacks
        self._setup_signal_handlers()
        
        # Tool metadata
        self.name = "pseudocode_translator"
        self.description = (
            "Translate pseudocode to various programming languages"
        )
        self.version = "1.0.0"
        self.author = "DinoAir Team"
        
    def _setup_signal_handlers(self):
        """Setup signal handlers for progress and status updates"""
        self.translator.translation_progress.connect(self._on_progress)
        self.translator.translation_status.connect(self._on_status)
        self.translator.translation_error.connect(self._on_error)
        self.translator.model_ready.connect(self._on_model_ready)
        
    def _on_progress(self, percentage: int):
        """Handle progress updates from translator"""
        progress = ToolProgress(
            percentage=percentage,
            message=f"Translation progress: {percentage}%",
            current_step="translating"
        )
        self._notify_progress(progress)
        
    def _on_status(self, status_info: Dict[str, Any]):
        """Handle status updates from translator"""
        progress = ToolProgress(
            percentage=status_info.get('progress', 0),
            message=status_info.get('message', 'Processing...'),
            current_step=status_info.get('phase', 'unknown'),
            metadata=status_info
        )
        self._notify_progress(progress)
        
    def _on_error(self, error_message: str):
        """Handle errors from translator"""
        logger.error(f"Translation error: {error_message}")
        with self._lock:
            self._status = ToolStatus.FAILED
            
    def _on_model_ready(self):
        """Handle model ready signal"""
        logger.info("Translation model is ready")
        
    def _notify_progress(self, progress: ToolProgress):
        """Notify all registered progress callbacks"""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
                
    def add_progress_callback(self, callback: Callable[[ToolProgress], None]):
        """
        Add a progress callback
        
        Args:
            callback: Function to call with progress updates
        """
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
            
    def remove_progress_callback(
        self, callback: Callable[[ToolProgress], None]
    ):
        """
        Remove a progress callback
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
            
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get tool capabilities
        
        Returns:
            Dictionary describing tool capabilities
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "features": {
                "async_support": True,
                "progress_reporting": True,
                "cancellation": True,
                "multi_language": True,
                "streaming": True,
                "model_switching": True
            },
            "supported_languages": self.translator.available_languages,
            "available_models": self.translator.available_models,
            "current_model": self.translator.current_model,
            "current_language": self.translator.current_language,
            "status": self._status.value,
            "is_ready": self.translator.is_ready
        }
        
    def translate(self,
                  pseudocode: str,
                  language: str = "python",
                  use_streaming: bool = False,
                  timeout: Optional[float] = None) -> ToolResult:
        """
        Translate pseudocode synchronously
        
        Args:
            pseudocode: The pseudocode to translate
            language: Target programming language
            use_streaming: Whether to use streaming for large files
            timeout: Optional timeout in seconds
            
        Returns:
            ToolResult with the translation
        """
        with self._lock:
            if self._status == ToolStatus.RUNNING:
                return ToolResult(
                    success=False,
                    errors=["Translation already in progress"],
                    status=ToolStatus.FAILED
                )
            self._status = ToolStatus.RUNNING
            
        try:
            # Validate input
            if not pseudocode or not pseudocode.strip():
                return ToolResult(
                    success=False,
                    errors=["No pseudocode provided"],
                    status=ToolStatus.FAILED
                )
                
            # Perform translation
            result = self.translator.translate_sync(pseudocode, language)
            
            # Convert to ToolResult
            tool_result = ToolResult(
                success=result['success'],
                output=result.get('code'),
                errors=result.get('errors', []),
                warnings=result.get('warnings', []),
                metadata=result.get('metadata', {}),
                status=(
                    ToolStatus.COMPLETED if result['success']
                    else ToolStatus.FAILED
                )
            )
            
            return tool_result
            
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
        finally:
            with self._lock:
                if self._status == ToolStatus.RUNNING:
                    self._status = ToolStatus.IDLE
                    
    async def translate_async(self,
                              pseudocode: str,
                              language: str = "python",
                              use_streaming: bool = False,
                              timeout: Optional[float] = None) -> ToolResult:
        """
        Translate pseudocode asynchronously
        
        Args:
            pseudocode: The pseudocode to translate
            language: Target programming language
            use_streaming: Whether to use streaming for large files
            timeout: Optional timeout in seconds
            
        Returns:
            ToolResult with the translation
        """
        # Check if already running
        with self._lock:
            if self._status == ToolStatus.RUNNING:
                return ToolResult(
                    success=False,
                    errors=["Translation already in progress"],
                    status=ToolStatus.FAILED
                )
            self._status = ToolStatus.RUNNING
            
        try:
            # Create event to wait for completion
            completion_event = asyncio.Event()
            result_container: Dict[str, Any] = {"result": None}
            
            def on_completion(result):
                """Handle translation completion"""
                result_container["result"] = result
                completion_event.set()
                
            def on_error(error):
                """Handle translation error"""
                result_container["result"] = {
                    "success": False,
                    "errors": [error],
                    "code": None,
                    "warnings": [],
                    "metadata": {}
                }
                completion_event.set()
                
            # Connect completion handlers
            self.translator.translation_completed.connect(on_completion)
            self.translator.translation_error.connect(on_error)
            
            try:
                # Start translation
                translation_id = self.translator.translate(
                    pseudocode,
                    language=language,
                    use_streaming=use_streaming
                )
                
                if translation_id is None:
                    return ToolResult(
                        success=False,
                        errors=["Failed to start translation"],
                        status=ToolStatus.FAILED
                    )
                
                # Wait for completion with timeout
                if timeout:
                    await asyncio.wait_for(completion_event.wait(), timeout)
                else:
                    await completion_event.wait()
                    
                # Get result
                result = result_container["result"]
                if result:
                    return ToolResult(
                        success=result.get('success', False),
                        output=result.get('code'),
                        errors=result.get('errors', []),
                        warnings=result.get('warnings', []),
                        metadata=result.get('metadata', {}),
                        status=(
                            ToolStatus.COMPLETED if result.get('success')
                            else ToolStatus.FAILED
                        )
                    )
                else:
                    return ToolResult(
                        success=False,
                        errors=["No result received"],
                        status=ToolStatus.FAILED
                    )
                    
            finally:
                # Disconnect handlers
                self.translator.translation_completed.disconnect(on_completion)
                self.translator.translation_error.disconnect(on_error)
                
        except asyncio.TimeoutError:
            self.cancel()
            return ToolResult(
                success=False,
                errors=[f"Translation timed out after {timeout} seconds"],
                status=ToolStatus.CANCELLED
            )
        except Exception as e:
            logger.error(f"Async translation failed: {e}")
            return ToolResult(
                success=False,
                errors=[str(e)],
                status=ToolStatus.FAILED
            )
        finally:
            with self._lock:
                if self._status == ToolStatus.RUNNING:
                    self._status = ToolStatus.IDLE
                    
    def cancel(self):
        """Cancel the current translation operation"""
        with self._lock:
            if self._status == ToolStatus.RUNNING:
                self._status = ToolStatus.CANCELLED
                
        self.translator.cancel_translation()
        logger.info("Translation cancelled")
        
    def set_language(self, language: str) -> bool:
        """
        Set the output programming language
        
        Args:
            language: Language name (e.g., "python", "javascript")
            
        Returns:
            True if successful
        """
        return self.translator.set_language(language)
        
    def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different translation model
        
        Args:
            model_name: Name of the model to switch to
            
        Returns:
            True if successful
        """
        return self.translator.switch_model(model_name)
        
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update tool configuration
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        self.translator.update_config(config_updates)
        
    def get_model_status(self) -> Dict[str, Any]:
        """
        Get current model status
        
        Returns:
            Dictionary with model status information
        """
        return self.translator.get_model_status()
        
    def warmup(self):
        """Warm up the translation model"""
        self.translator.warmup_model()
        
    def get_error_suggestions(self, error_message: str) -> List[str]:
        """
        Get suggestions for fixing an error
        
        Args:
            error_message: The error message
            
        Returns:
            List of suggestions
        """
        return self.translator.get_error_suggestions(error_message)
        
    def shutdown(self):
        """Shutdown the tool and cleanup resources"""
        logger.info("Shutting down pseudocode tool...")
        
        # Cancel any running operations
        if self._status == ToolStatus.RUNNING:
            self.cancel()
            
        # Shutdown translator
        self.translator.shutdown()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        self._status = ToolStatus.IDLE
        logger.info("Pseudocode tool shutdown complete")
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()
        
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.shutdown()
        except Exception:
            pass


# Convenience functions for quick usage

def translate_pseudocode(pseudocode: str,
                         language: str = "python",
                         config_path: Optional[str] = None) -> ToolResult:
    """
    Quick function to translate pseudocode
    
    Args:
        pseudocode: The pseudocode to translate
        language: Target programming language
        config_path: Optional configuration file path
        
    Returns:
        ToolResult with the translation
    """
    with PseudocodeTool(config_path) as tool:
        return tool.translate(pseudocode, language)


async def translate_pseudocode_async(
    pseudocode: str,
    language: str = "python",
    config_path: Optional[str] = None,
    progress_callback: Optional[Callable] = None
) -> ToolResult:
    """
    Quick async function to translate pseudocode
    
    Args:
        pseudocode: The pseudocode to translate
        language: Target programming language
        config_path: Optional configuration file path
        progress_callback: Optional progress callback
        
    Returns:
        ToolResult with the translation
    """
    tool = PseudocodeTool(config_path)
    try:
        if progress_callback:
            tool.add_progress_callback(progress_callback)
        return await tool.translate_async(pseudocode, language)
    finally:
        tool.shutdown()


# Example usage
"""
Example Usage:

    # Synchronous usage
    from src.tools.pseudocode_tool import PseudocodeTool
    
    tool = PseudocodeTool()
    result = tool.translate(
        "create a function that sorts a list",
        language="python"
    )
    
    if result.success:
        print(f"Generated code:\\n{result.output}")
    else:
        print(f"Translation failed: {result.errors}")
        
    # Asynchronous usage with progress
    import asyncio
    
    async def main():
        tool = PseudocodeTool()
        
        def on_progress(progress):
            print(f"Progress: {progress.percentage}% - {progress.message}")
            
        tool.add_progress_callback(on_progress)
        
        result = await tool.translate_async(
            "implement quicksort algorithm",
            language="javascript"
        )
        
        if result.success:
            print(f"Generated code:\\n{result.output}")
            
        tool.shutdown()
        
    asyncio.run(main())
    
    # Quick one-liner
    from src.tools.pseudocode_tool import translate_pseudocode
    
    result = translate_pseudocode("print fibonacci sequence", "python")
    print(result.output)
"""