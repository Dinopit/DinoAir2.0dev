"""
OllamaWrapper - Ollama Integration for DinoAir 2.0

This module provides a high-level wrapper around the Ollama API to
integrate local LLM functionality into the main DinoAir application.

Features:
- Service availability checks
- Model management (list, download, verify)
- Standard and streaming generation
- Chat interface with context management
- Advanced error handling
- Progress reporting for model downloads
- Configuration integration
"""

import os
import json
import logging
import subprocess
import platform
from typing import Optional, Dict, Any, List, Iterator, Union, Callable
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
import time

try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    Client = None  # Type hint for when ollama is not available
    logging.warning(
        "Ollama library not installed. Install with: pip install ollama"
    )


logger = logging.getLogger(__name__)


class OllamaStatus(Enum):
    """Status of Ollama service"""
    NOT_INSTALLED = "not_installed"
    NOT_RUNNING = "not_running"
    READY = "ready"
    ERROR = "error"
    CHECKING = "checking"


class ModelStatus(Enum):
    """Status of a model"""
    NOT_AVAILABLE = "not_available"
    DOWNLOADING = "downloading"
    READY = "ready"
    ERROR = "error"


@dataclass
class GenerationResponse:
    """Response from generation request"""
    success: bool
    content: str
    model: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tokens_generated: Optional[int] = None
    generation_time: Optional[float] = None


@dataclass
class ChatMessage:
    """Chat message structure"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ModelInfo:
    """Information about an Ollama model"""
    name: str
    tag: str
    size: int
    digest: str
    modified: str
    details: Optional[Dict[str, Any]] = None


class OllamaWrapper:
    """
    Main Ollama wrapper class for DinoAir integration
    
    This class provides a high-level interface for interacting with Ollama,
    including service management, model operations, and text generation.
    """
    
    def __init__(self, 
                 host: Optional[str] = None,
                 timeout: int = 300,
                 config_path: Optional[str] = None):
        """
        Initialize the OllamaWrapper
        
        Args:
            host: Ollama host URL (default: http://localhost:11434)
            timeout: Request timeout in seconds
            config_path: Optional path to configuration file
        """
        self._host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self._timeout = timeout
        self._config_path = config_path
        self._client: Optional[Any] = None  # Use Any to avoid type issues
        self._service_status = OllamaStatus.CHECKING
        self._current_model: Optional[str] = None
        self._model_cache: Dict[str, ModelInfo] = {}
        self._chat_context: List[ChatMessage] = []
        self._is_initialized = False
        
        # Configuration
        self._config = self._load_configuration()
        
        # Initialize
        self._initialize()
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load configuration from file or defaults"""
        config = {
            'default_model': 'llama3.2',
            'temperature': 0.7,
            'max_tokens': 2048,
            'timeout': self._timeout,
            'context_window': 4096,
            'num_ctx': 4096,
            'num_predict': -1,
            'top_p': 0.9,
            'top_k': 40,
            'repeat_penalty': 1.1,
            'stream': True,
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
                    
                # Map app config to Ollama config
                if 'ai' in app_config:
                    ai_config = app_config['ai']
                    if 'temperature' in ai_config:
                        config['temperature'] = ai_config['temperature']
                    if 'max_tokens' in ai_config:
                        config['max_tokens'] = ai_config['max_tokens']
                        
                # Apply Ollama-specific settings
                if 'ollama' in app_config:
                    ollama_config = app_config['ollama']
                    config.update(ollama_config)
                    
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
        """Initialize the Ollama client and check service status"""
        if not OLLAMA_AVAILABLE:
            self._service_status = OllamaStatus.NOT_INSTALLED
            logger.error("Ollama Python library not installed")
            return
        
        try:
            # Create client
            if Client is not None:
                self._client = Client(host=self._host, timeout=self._timeout)
            else:
                self._service_status = OllamaStatus.NOT_INSTALLED
                return
            
            # Check if service is running
            if self._check_service():
                self._service_status = OllamaStatus.READY
                self._is_initialized = True
                logger.info(f"Ollama service ready at {self._host}")
                
                # Set default model
                self._current_model = self._config.get(
                    'default_model', 'llama3.2'
                )
                
                # Ensure default model is available
                if self._current_model and not self.ensure_model(
                    self._current_model
                ):
                    logger.warning(
                        f"Default model {self._current_model} not available"
                    )
            else:
                self._service_status = OllamaStatus.NOT_RUNNING
                logger.warning("Ollama service not running")
                
        except Exception as e:
            self._service_status = OllamaStatus.ERROR
            logger.error(f"Failed to initialize Ollama client: {e}")
    
    def _check_service(self) -> bool:
        """Check if Ollama service is running"""
        if not self._client:
            logger.debug("_check_service: No client available")
            return False
            
        try:
            # Try to list models as a health check
            logger.debug(f"_check_service: Attempting to connect to {self._host}")
            response = self._client.list()
            logger.info(f"_check_service: Successfully connected, found {len(response.get('models', []))} models")
            return True
        except Exception as e:
            logger.warning(f"_check_service: Service check failed - {type(e).__name__}: {e}")
            return False
    
    def check_service(self) -> OllamaStatus:
        """Public method to check service status and return status enum"""
        if self._check_service():
            self._service_status = OllamaStatus.READY
            return OllamaStatus.READY
        else:
            self._service_status = OllamaStatus.ERROR
            return OllamaStatus.ERROR
    
    @property
    def is_ready(self) -> bool:
        """Check if the wrapper is ready to accept requests"""
        return (self._is_initialized and 
                self._service_status == OllamaStatus.READY and
                self._client is not None)
    
    @property
    def service_status(self) -> OllamaStatus:
        """Get current service status"""
        return self._service_status
    
    @property
    def current_model(self) -> Optional[str]:
        """Get current model name"""
        return self._current_model
    
    def get_current_model(self) -> Optional[str]:
        """Get current model name (method version for compatibility)"""
        return self._current_model
    
    def start_service(self) -> bool:
        """
        Attempt to start the Ollama service
        
        Returns:
            True if service was started successfully
        """
        logger.info("start_service: Attempting to start Ollama service")
        
        if self._service_status == OllamaStatus.READY:
            logger.info("start_service: Service already ready")
            return True
            
        try:
            system = platform.system().lower()
            logger.debug(f"start_service: Detected platform: {system}")
            
            if system == "darwin":  # macOS
                # Check if Ollama.app is running
                result = subprocess.run(
                    ["pgrep", "-x", "Ollama"],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.info("start_service: Starting Ollama.app on macOS")
                    # Try to start Ollama.app
                    subprocess.run(["open", "-a", "Ollama"])
                    time.sleep(3)  # Give it time to start
                else:
                    logger.debug("start_service: Ollama already running on macOS")
                    
            elif system == "linux":
                # Check if ollama service is running
                result = subprocess.run(
                    ["systemctl", "is-active", "ollama"],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip() != "active":
                    logger.info("start_service: Starting ollama systemd service")
                    # Try to start the service
                    subprocess.run(["systemctl", "start", "ollama"])
                    time.sleep(2)
                else:
                    logger.debug("start_service: Ollama service already active on Linux")
                    
            elif system == "windows":
                # First check if Ollama is already running
                logger.debug("start_service: Checking if Ollama is already running on Windows")
                # Try a quick service check first
                if self._check_service():
                    logger.info("start_service: Ollama already running on Windows")
                    self._service_status = OllamaStatus.READY
                    return True
                
                # Try multiple methods to start Ollama on Windows
                logger.info("start_service: Attempting to start Ollama on Windows")
                started = False
                
                # Method 1: Try direct command
                try:
                    logger.debug("start_service: Method 1 - Direct ollama serve")
                    subprocess.Popen(
                        ["ollama", "serve"],
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        shell=True
                    )
                    started = True
                except Exception as e1:
                    logger.debug(f"start_service: Method 1 failed - {e1}")
                    
                    # Method 2: Try with full path
                    try:
                        import shutil
                        ollama_path = shutil.which("ollama")
                        if ollama_path:
                            logger.debug(f"start_service: Method 2 - Full path {ollama_path}")
                            subprocess.Popen(
                                [ollama_path, "serve"],
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            started = True
                    except Exception as e2:
                        logger.debug(f"start_service: Method 2 failed - {e2}")
                        
                        # Method 3: Try common installation paths
                        common_paths = [
                            r"C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe",
                            r"C:\Program Files\Ollama\ollama.exe",
                            r"C:\Program Files (x86)\Ollama\ollama.exe"
                        ]
                        
                        for path in common_paths:
                            expanded_path = os.path.expandvars(path)
                            if os.path.exists(expanded_path):
                                try:
                                    logger.debug(f"start_service: Method 3 - Found at {expanded_path}")
                                    subprocess.Popen(
                                        [expanded_path, "serve"],
                                        creationflags=subprocess.CREATE_NO_WINDOW
                                    )
                                    started = True
                                    break
                                except Exception as e3:
                                    logger.debug(f"start_service: Method 3 failed for {expanded_path} - {e3}")
                
                if started:
                    logger.info("start_service: Ollama process started, waiting for service to be ready")
                    time.sleep(5)  # Give more time on Windows
                else:
                    logger.error("start_service: Could not start Ollama service on Windows - not found in PATH or common locations")
            
            # Reinitialize to check if service is now running
            logger.debug("start_service: Reinitializing to check service status")
            self._initialize()
            
            success = self._service_status == OllamaStatus.READY
            logger.info(f"start_service: Service start {'successful' if success else 'failed'}, status: {self._service_status}")
            return success
            
        except Exception as e:
            logger.error(f"start_service: Failed to start Ollama service - {type(e).__name__}: {e}")
            return False
    
    def list_models(self) -> List[ModelInfo]:
        """
        List all available models
        
        Returns:
            List of ModelInfo objects
        """
        if not self.is_ready:
            logger.warning("Ollama not ready, cannot list models")
            return []
            
        try:
            logger.debug("list_models: Calling API to list models")
            response = self._client.list()
            logger.info(f"list_models: Raw API response: {response}")
            
            models = []
            model_list = response.get('models', [])
            logger.info(f"list_models: Found {len(model_list)} models in response")
            
            for idx, model_data in enumerate(model_list):
                logger.debug(f"list_models: Processing model {idx}: {model_data}")
                # Handle both dict and Model object formats
                if hasattr(model_data, 'model'):
                    # It's a Model object from the Ollama library
                    name = model_data.model
                    size = model_data.size if hasattr(model_data, 'size') else 0
                    digest = model_data.digest if hasattr(model_data, 'digest') else ''
                    modified = str(model_data.modified_at) if hasattr(model_data, 'modified_at') else ''
                    details = model_data.details.__dict__ if hasattr(model_data, 'details') else {}
                else:
                    # It's a dictionary (fallback for compatibility)
                    name = model_data.get('name', '')
                    size = model_data.get('size', 0)
                    digest = model_data.get('digest', '')
                    modified = model_data.get('modified_at', '')
                    details = model_data.get('details', {})
                
                # Parse model name and tag
                if ':' in name:
                    model_name = name.split(':')[0]
                    model_tag = name.split(':')[1]
                else:
                    model_name = name
                    model_tag = 'latest'
                
                logger.debug(f"list_models: Parsed name='{model_name}', tag='{model_tag}' from '{name}'")
                
                model_info = ModelInfo(
                    name=model_name,
                    tag=model_tag,
                    size=size,
                    digest=digest,
                    modified=modified,
                    details=details
                )
                models.append(model_info)
                # Cache model info
                self._model_cache[name] = model_info
                
            logger.info(f"list_models: Returning {len(models)} parsed models")
            return models
            
        except Exception as e:
            logger.error(f"list_models: Failed with exception - {type(e).__name__}: {e}")
            import traceback
            logger.error(f"list_models: Traceback:\n{traceback.format_exc()}")
            return []
    
    def model_exists(self, model_name: str) -> bool:
        """
        Check if a model exists locally
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model exists
        """
        models = self.list_models()
        model_names = [m.name for m in models] + [
            f"{m.name}:{m.tag}" for m in models
        ]
        return (model_name in model_names or
                model_name.split(':')[0] in model_names)
    
    def download_model(
            self,
            model_name: str,
            progress_callback: Optional[Callable] = None) -> bool:
        """
        Download a model from Ollama library
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates
                              Called with (downloaded_bytes, total_bytes,
                              status_message)
            
        Returns:
            True if download was successful
        """
        if not self.is_ready:
            logger.error("Ollama not ready, cannot download model")
            return False
            
        try:
            logger.info(f"Downloading model: {model_name}")
            
            # Pull the model
            stream = self._client.pull(model_name, stream=True)
            
            total_size = 0
            downloaded = 0
            
            for chunk in stream:
                if 'total' in chunk:
                    total_size = chunk['total']
                if 'completed' in chunk:
                    downloaded = chunk['completed']
                    
                status = chunk.get('status', 'downloading')
                
                if progress_callback:
                    progress_callback(downloaded, total_size, status)
                    
                # Log progress periodically
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    logger.debug(
                        f"Download progress: {percent:.1f}% - {status}"
                    )
            
            logger.info(f"Model {model_name} downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model {model_name}: {e}")
            return False
    
    def ensure_model(
            self,
            model_name: str,
            progress_callback: Optional[Callable] = None) -> bool:
        """
        Ensure a model is available, downloading if necessary
        
        Args:
            model_name: Name of the model
            progress_callback: Optional callback for download progress
            
        Returns:
            True if model is available
        """
        if self.model_exists(model_name):
            logger.debug(f"Model {model_name} already available")
            return True
            
        logger.info(f"Model {model_name} not found, attempting to download")
        return self.download_model(model_name, progress_callback)
    
    def remove_model(self, model_name: str) -> bool:
        """
        Remove a model from local storage
        
        Args:
            model_name: Name of the model to remove
            
        Returns:
            True if removal was successful
        """
        if not self.is_ready:
            logger.error("Ollama not ready, cannot remove model")
            return False
            
        try:
            # Check if model exists
            if not self.model_exists(model_name):
                logger.warning(f"Model {model_name} not found")
                return False
                
            logger.info(f"Removing model: {model_name}")
            
            # Delete the model
            self._client.delete(model_name)
            
            # Clear from cache
            if model_name in self._model_cache:
                del self._model_cache[model_name]
                
            logger.info(f"Model {model_name} removed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove model {model_name}: {e}")
            return False
    
    def pull_model(
            self,
            model_name: str,
            progress_callback: Optional[Callable] = None) -> bool:
        """
        Pull a model from Ollama library (alias for download_model)
        
        Args:
            model_name: Name of the model to pull
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if pull was successful
        """
        return self.download_model(model_name, progress_callback)
    
    def set_model(self, model_name: str) -> bool:
        """
        Set the current model for generation
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if model was set successfully
        """
        logger.info(f"[OllamaWrapper] set_model called with: '{model_name}'")
        logger.info(f"[OllamaWrapper] model_name type: {type(model_name)}")
        logger.info(f"[OllamaWrapper] model_name length: {len(model_name)}")
        logger.info(f"[OllamaWrapper] model_name repr: {repr(model_name)}")
        
        if not self.ensure_model(model_name):
            logger.error(f"Cannot set model {model_name}: not available")
            return False
            
        self._current_model = model_name
        logger.info(f"[OllamaWrapper] _current_model set to: '{self._current_model}'")
        logger.info(f"Current model set to: {model_name}")
        return True
    
    def generate(self, prompt: str,
                 model: Optional[str] = None,
                 **kwargs) -> GenerationResponse:
        """
        Generate text from a prompt
        
        Args:
            prompt: Input prompt
            model: Model to use (uses current model if None)
            **kwargs: Additional generation parameters
                     (temperature, max_tokens, top_p, top_k, etc.)
            
        Returns:
            GenerationResponse with the result
        """
        if not self.is_ready:
            return GenerationResponse(
                success=False,
                content="",
                model="",
                error="Ollama service not ready"
            )
            
        model = model or self._current_model
        if not model:
            return GenerationResponse(
                success=False,
                content="",
                model="",
                error="No model specified"
            )
            
        # Merge kwargs with config
        options = {
            'temperature': self._config.get('temperature', 0.7),
            'num_predict': kwargs.get(
                'max_tokens', self._config.get('max_tokens', 2048)
            ),
            'top_p': self._config.get('top_p', 0.9),
            'top_k': self._config.get('top_k', 40),
            'repeat_penalty': self._config.get('repeat_penalty', 1.1),
            'num_ctx': self._config.get('num_ctx', 4096),
        }
        
        # Update with any provided kwargs
        for key in ['temperature', 'top_p', 'top_k', 'repeat_penalty']:
            if key in kwargs:
                options[key] = kwargs[key]
        
        try:
            start_time = time.time()
            
            response = self._client.generate(
                model=model,
                prompt=prompt,
                options=options,
                stream=False
            )
            
            generation_time = time.time() - start_time
            
            return GenerationResponse(
                success=True,
                content=response['response'],
                model=model,
                metadata={
                    'model': response.get('model', model),
                    'created_at': response.get('created_at', ''),
                    'done_reason': response.get('done_reason', ''),
                    'context': response.get('context', []),
                    'total_duration': response.get('total_duration', 0),
                    'load_duration': response.get('load_duration', 0),
                    'prompt_eval_duration': response.get(
                        'prompt_eval_duration', 0
                    ),
                    'eval_duration': response.get('eval_duration', 0),
                },
                tokens_generated=response.get('eval_count', 0),
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return GenerationResponse(
                success=False,
                content="",
                model=model,
                error=str(e)
            )
    
    def stream_generate(self, prompt: str,
                        model: Optional[str] = None,
                        **kwargs) -> Iterator[str]:
        """
        Generate text from a prompt with streaming
        
        Args:
            prompt: Input prompt
            model: Model to use (uses current model if None)
            **kwargs: Additional generation parameters
            
        Yields:
            Generated text chunks
        """
        if not self.is_ready:
            yield "Error: Ollama service not ready"
            return
            
        model = model or self._current_model
        if not model:
            yield "Error: No model specified"
            return
            
        # Merge kwargs with config
        options = {
            'temperature': self._config.get('temperature', 0.7),
            'num_predict': kwargs.get(
                'max_tokens', self._config.get('max_tokens', 2048)
            ),
            'top_p': self._config.get('top_p', 0.9),
            'top_k': self._config.get('top_k', 40),
            'repeat_penalty': self._config.get('repeat_penalty', 1.1),
            'num_ctx': self._config.get('num_ctx', 4096),
        }
        
        # Update with any provided kwargs
        for key in ['temperature', 'top_p', 'top_k', 'repeat_penalty']:
            if key in kwargs:
                options[key] = kwargs[key]
        
        try:
            stream = self._client.generate(
                model=model,
                prompt=prompt,
                options=options,
                stream=True
            )
            
            for chunk in stream:
                if chunk.get('done', False):
                    break
                    
                text = chunk.get('response', '')
                if text:
                    yield text
                    
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"Error: {str(e)}"
    
    def chat(self,
             messages: Union[str, List[ChatMessage], List[Dict[str, str]]],
             model: Optional[str] = None,
             use_context: bool = True,
             **kwargs) -> GenerationResponse:
        """
        Chat with the model
        
        Args:
            messages: Either a single message string or list of
                     ChatMessage/dicts
            model: Model to use (uses current model if None)
            use_context: Whether to use previous chat context
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResponse with the assistant's reply
        """
        if not self.is_ready:
            return GenerationResponse(
                success=False,
                content="",
                model="",
                error="Ollama service not ready"
            )
            
        model = model or self._current_model
        if not model:
            return GenerationResponse(
                success=False,
                content="",
                model="",
                error="No model specified"
            )
            
        # Convert messages to proper format
        if isinstance(messages, str):
            # Single user message
            chat_messages = [{'role': 'user', 'content': messages}]
            if use_context:
                # Add to context
                self._chat_context.append(
                    ChatMessage(role='user', content=messages)
                )
        else:
            # List of messages
            chat_messages = []
            for msg in messages:
                if isinstance(msg, ChatMessage):
                    chat_messages.append({
                        'role': msg.role, 'content': msg.content
                    })
                elif isinstance(msg, dict):
                    chat_messages.append(msg)
        
        # Add context if requested
        if use_context and self._chat_context:
            context_messages = [
                {'role': m.role, 'content': m.content}
                for m in self._chat_context[:-1]  # Exclude last if just added
            ]
            chat_messages = context_messages + chat_messages
        
        # Merge kwargs with config
        options = {
            'temperature': self._config.get('temperature', 0.7),
            'num_predict': kwargs.get(
                'max_tokens', self._config.get('max_tokens', 2048)
            ),
            'top_p': self._config.get('top_p', 0.9),
            'top_k': self._config.get('top_k', 40),
            'repeat_penalty': self._config.get('repeat_penalty', 1.1),
            'num_ctx': self._config.get('num_ctx', 4096),
        }
        
        # Update with any provided kwargs
        for key in ['temperature', 'top_p', 'top_k', 'repeat_penalty']:
            if key in kwargs:
                options[key] = kwargs[key]
        
        try:
            start_time = time.time()
            
            response = self._client.chat(
                model=model,
                messages=chat_messages,
                options=options,
                stream=False
            )
            
            generation_time = time.time() - start_time
            
            # Extract assistant's response
            assistant_message = response.get('message', {})
            content = assistant_message.get('content', '')
            
            # Add to context if requested
            if use_context and content:
                self._chat_context.append(
                    ChatMessage(role='assistant', content=content)
                )
            
            return GenerationResponse(
                success=True,
                content=content,
                model=model,
                metadata={
                    'model': response.get('model', model),
                    'created_at': response.get('created_at', ''),
                    'done_reason': response.get('done_reason', ''),
                    'total_duration': response.get('total_duration', 0),
                    'load_duration': response.get('load_duration', 0),
                    'prompt_eval_duration': response.get(
                        'prompt_eval_duration', 0
                    ),
                    'eval_duration': response.get('eval_duration', 0),
                },
                tokens_generated=response.get('eval_count', 0),
                generation_time=generation_time
            )
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return GenerationResponse(
                success=False,
                content="",
                model=model,
                error=str(e)
            )
    
    def stream_chat(
            self,
            messages: Union[str, List[ChatMessage],
                            List[Dict[str, str]]],
            model: Optional[str] = None,
            use_context: bool = True,
            **kwargs) -> Iterator[str]:
        """
        Chat with the model using streaming
        
        Args:
            messages: Either a single message string or list of
                     ChatMessage/dicts
            model: Model to use (uses current model if None)
            use_context: Whether to use previous chat context
            **kwargs: Additional generation parameters
            
        Yields:
            Assistant's response chunks
        """
        if not self.is_ready:
            yield "Error: Ollama service not ready"
            return
            
        model = model or self._current_model
        if not model:
            yield "Error: No model specified"
            return
            
        # Convert messages to proper format
        if isinstance(messages, str):
            # Single user message
            chat_messages = [{'role': 'user', 'content': messages}]
            if use_context:
                # Add to context
                self._chat_context.append(
                    ChatMessage(role='user', content=messages)
                )
        else:
            # List of messages
            chat_messages = []
            for msg in messages:
                if isinstance(msg, ChatMessage):
                    chat_messages.append({
                        'role': msg.role, 'content': msg.content
                    })
                elif isinstance(msg, dict):
                    chat_messages.append(msg)
        
        # Add context if requested
        if use_context and self._chat_context:
            context_messages = [
                {'role': m.role, 'content': m.content}
                for m in self._chat_context[:-1]  # Exclude last if just added
            ]
            chat_messages = context_messages + chat_messages
        
        # Merge kwargs with config
        options = {
            'temperature': self._config.get('temperature', 0.7),
            'num_predict': kwargs.get(
                'max_tokens', self._config.get('max_tokens', 2048)
            ),
            'top_p': self._config.get('top_p', 0.9),
            'top_k': self._config.get('top_k', 40),
            'repeat_penalty': self._config.get('repeat_penalty', 1.1),
            'num_ctx': self._config.get('num_ctx', 4096),
        }
        
        # Update with any provided kwargs
        for key in ['temperature', 'top_p', 'top_k', 'repeat_penalty']:
            if key in kwargs:
                options[key] = kwargs[key]
        
        try:
            stream = self._client.chat(
                model=model,
                messages=chat_messages,
                options=options,
                stream=True
            )
            
            full_response = ""
            
            for chunk in stream:
                if chunk.get('done', False):
                    break
                    
                message = chunk.get('message', {})
                content = message.get('content', '')
                
                if content:
                    full_response += content
                    yield content
            
            # Add complete response to context if requested
            if use_context and full_response:
                self._chat_context.append(
                    ChatMessage(role='assistant', content=full_response)
                )
                    
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}")
            yield f"Error: {str(e)}"
    
    def clear_chat_context(self):
        """Clear the chat conversation context"""
        self._chat_context.clear()
        logger.debug("Chat context cleared")
    
    def get_chat_context(self) -> List[ChatMessage]:
        """Get the current chat context"""
        return self._chat_context.copy()
    
    def set_chat_context(self, context: List[ChatMessage]):
        """Set the chat context"""
        self._chat_context = context
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a model
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo object or None if not found
        """
        # Check cache first
        if model_name in self._model_cache:
            return self._model_cache[model_name]
            
        # Refresh model list
        models = self.list_models()
        for model in models:
            full_name = f"{model.name}:{model.tag}"
            if model.name == model_name or full_name == model_name:
                return model
                
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current wrapper status and health information
        
        Returns:
            Dictionary with status information
        """
        return {
            'initialized': self._is_initialized,
            'service_status': self._service_status.value,
            'current_model': self._current_model,
            'available_models': [m.name for m in self.list_models()],
            'host': self._host,
            'chat_context_length': len(self._chat_context),
            'config': {
                'temperature': self._config.get('temperature'),
                'max_tokens': self._config.get('max_tokens'),
                'timeout': self._timeout
            }
        }
    
    def is_service_running(self) -> bool:
        """
        Check if the Ollama service is currently running
        
        Returns:
            True if service is running
        """
        logger.debug("is_service_running: Checking service status")
        # Try a quick check first without full reinitialize
        if self._check_service():
            self._service_status = OllamaStatus.READY
            return True
        
        # If quick check fails, do full reinitialize
        logger.debug("is_service_running: Quick check failed, reinitializing")
        self._initialize()
        return self._service_status == OllamaStatus.READY
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update wrapper configuration
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        self._config.update(config_updates)
        logger.info(f"Updated Ollama config: {config_updates}")
    
    def test_connection(self) -> bool:
        """
        Test the connection to Ollama service
        
        Returns:
            True if connection is successful
        """
        return self._check_service()


# Convenience factory function
def create_ollama_wrapper(
        host: Optional[str] = None,
        timeout: int = 300,
        config_path: Optional[str] = None) -> OllamaWrapper:
    """
    Factory function to create an OllamaWrapper instance
    
    Args:
        host: Ollama host URL
        timeout: Request timeout in seconds
        config_path: Optional path to configuration file
        
    Returns:
        Configured OllamaWrapper instance
    """
    return OllamaWrapper(host, timeout, config_path)


# Example usage and integration guide
"""
Example Integration:

    from src.agents.ollama_wrapper import OllamaWrapper
    
    # Create wrapper
    ollama = OllamaWrapper()
    
    # Check if service is ready
    if not ollama.is_ready:
        print("Ollama not ready, attempting to start service...")
        if ollama.start_service():
            print("Service started successfully")
        else:
            print("Failed to start service")
    
    # List available models
    models = ollama.list_models()
    for model in models:
        print(f"Model: {model.name}:{model.tag} ({model.size} bytes)")
    
    # Ensure a model is available
    if ollama.ensure_model("llama3.2"):
        print("Model ready")
    
    # Generate text
    response = ollama.generate("Write a haiku about Python programming")
    if response.success:
        print(f"Response: {response.content}")
        print(f"Tokens: {response.tokens_generated}")
        print(f"Time: {response.generation_time:.2f}s")
    
    # Stream generation
    print("Streaming response:")
    for chunk in ollama.stream_generate("Tell me a joke"):
        print(chunk, end='', flush=True)
    print()
    
    # Chat interface
    chat_response = ollama.chat("Hello! How are you?")
    if chat_response.success:
        print(f"Assistant: {chat_response.content}")
    
    # Continue conversation
    followup = ollama.chat("What's your favorite programming language?")
    if followup.success:
        print(f"Assistant: {followup.content}")
    
    # Stream chat
    print("Streaming chat:")
    msg = "Explain quantum computing in simple terms"
    for chunk in ollama.stream_chat(msg):
        print(chunk, end='', flush=True)
    print()
    
    # Clear context for new conversation
    ollama.clear_chat_context()
"""