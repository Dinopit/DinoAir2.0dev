"""
Base Model Adapter

This module provides the base class for all model adapters,
defining the common interface and functionality.
"""

import logging
from abc import abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..abstraction.model_interface import (
    ModelInterface, ModelRequest, ModelResponse,
    ModelCapabilities
)

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    """Chunk of streaming response"""
    content: str
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdapterType(Enum):
    """Types of model adapters"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class AdapterConfig:
    """Configuration for model adapters"""
    adapter_type: AdapterType
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_name: str = "default"
    max_retries: int = 3
    timeout: float = 30.0
    extra_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize extra params if not provided"""
        if self.extra_params is None:
            self.extra_params = {}


class BaseModelAdapter(ModelInterface):
    """
    Base class for all model adapters
    
    This class provides common functionality for adapting various
    AI models to work with the tool system's abstraction layer.
    """
    
    def __init__(self, config: AdapterConfig):
        """
        Initialize the adapter
        
        Args:
            config: Adapter configuration
        """
        self.config = config
        self._initialized = False
        self._capabilities: List[ModelCapabilities] = (
            self._define_capabilities()
        )
        logger.info(
            f"Initializing {self.__class__.__name__} with model "
            f"{config.model_name}"
        )
        
    @abstractmethod
    def _define_capabilities(self) -> List[ModelCapabilities]:
        """
        Define model capabilities
        
        This method must be implemented by subclasses to specify
        what capabilities the model supports.
        
        Returns:
            Model capabilities
        """
        pass
        
    async def initialize(self) -> bool:
        """Initialize the model adapter"""
        try:
            # Perform adapter-specific initialization
            await self._initialize_adapter()
            
            # Validate connection/credentials
            if await self._validate_connection():
                self._initialized = True
                logger.info(
                    f"{self.__class__.__name__} initialized successfully"
                )
                return True
            else:
                logger.error(
                    f"{self.__class__.__name__} connection validation failed"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Failed to initialize {self.__class__.__name__}: {e}"
            )
            return False
            
    @abstractmethod
    async def _initialize_adapter(self):
        """
        Perform adapter-specific initialization
        
        This method should set up any required clients, connections,
        or resources needed by the adapter.
        """
        pass
        
    @abstractmethod
    async def _validate_connection(self) -> bool:
        """
        Validate the connection to the model service
        
        Returns:
            True if connection is valid
        """
        pass
        
    def is_available(self) -> bool:
        """Check if the model is available"""
        return self._initialized
        
    def get_capabilities(self) -> List[ModelCapabilities]:
        """Get model capabilities"""
        return self._capabilities.copy()
        
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate a response from the model
        
        Args:
            request: Model request
            
        Returns:
            Model response
        """
        if not self._initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Adapter not initialized"
            )
            
        try:
            # Validate request
            validation_error = self._validate_request(request)
            if validation_error:
                return ModelResponse(
                    content="",
                    success=False,
                    error=validation_error
                )
                
            # Prepare request for specific model
            prepared_request = await self._prepare_request(request)
            
            # Call model-specific generation
            response = await self._generate_internal(prepared_request)
            
            # Process response
            return await self._process_response(response, request)
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )
            
    async def stream_generate(
        self,
        request: ModelRequest,
        callback: Callable[[str], None]
    ) -> ModelResponse:
        """
        Stream generate a response
        
        Args:
            request: Model request
            callback: Function to call with each chunk
            
        Returns:
            Final model response
        """
        if not self._initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Adapter not initialized"
            )
            
        if not self.supports_capability(ModelCapabilities.STREAMING):
            # Fallback to non-streaming
            response = await self.generate(request)
            if response.success:
                callback(response.content)
            return response
            
        try:
            # Validate request
            validation_error = self._validate_request(request)
            if validation_error:
                return ModelResponse(
                    content="",
                    success=False,
                    error=validation_error
                )
                
            # Prepare request
            prepared_request = await self._prepare_request(request)
            
            # Stream from model
            full_content = []
            async for chunk in self._stream_internal(prepared_request):
                full_content.append(chunk.content)
                callback(chunk.content)
                
            return ModelResponse(
                content="".join(full_content),
                success=True
            )
                
        except Exception as e:
            logger.error(f"Stream generation failed: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )
            
    def _validate_request(self, request: ModelRequest) -> Optional[str]:
        """
        Validate a model request
        
        Args:
            request: Request to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        if not request.prompt:
            return "Prompt is required"
            
        max_token_caps = [
            c for c in self._capabilities
            if c.name.startswith("CONTEXT_WINDOW_")
        ]
        
        if request.max_tokens and max_token_caps:
            # Check against largest context window
            max_allowed = 128000  # Default max
            for cap in max_token_caps:
                if "128K" in cap.name:
                    max_allowed = 128000
                elif "32K" in cap.name:
                    max_allowed = 32000
                elif "16K" in cap.name:
                    max_allowed = 16000
                elif "8K" in cap.name:
                    max_allowed = 8000
                elif "4K" in cap.name:
                    max_allowed = 4000
                    
            if request.max_tokens > max_allowed:
                return (
                    f"Max tokens {request.max_tokens} exceeds model limit "
                    f"{max_allowed}"
                )
            
        if request.temperature and (
            request.temperature < 0 or request.temperature > 2
        ):
            return "Temperature must be between 0 and 2"
            
        return None
        
    @abstractmethod
    async def _prepare_request(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """
        Prepare request for the specific model API
        
        Args:
            request: Standard model request
            
        Returns:
            Model-specific request format
        """
        pass
        
    @abstractmethod
    async def _generate_internal(
        self, prepared_request: Dict[str, Any]
    ) -> Any:
        """
        Call the model's generation API
        
        Args:
            prepared_request: Model-specific request
            
        Returns:
            Raw model response
        """
        pass
        
    async def _stream_internal(
        self, prepared_request: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """
        Call the model's streaming API
        
        Args:
            prepared_request: Model-specific request
            
        Yields:
            Stream chunks
        """
        # Default implementation - subclasses should override
        response = await self._generate_internal(prepared_request)
        yield StreamChunk(
            content=str(response),
            is_final=True
        )
        
    @abstractmethod
    async def _process_response(
        self, raw_response: Any, original_request: ModelRequest
    ) -> ModelResponse:
        """
        Process raw model response into standard format
        
        Args:
            raw_response: Raw response from model
            original_request: Original request
            
        Returns:
            Standard model response
        """
        pass
        
    async def shutdown(self):
        """Shutdown the adapter"""
        if self._initialized:
            await self._shutdown_adapter()
            self._initialized = False
            logger.info(f"{self.__class__.__name__} shut down")
            
    @abstractmethod
    async def _shutdown_adapter(self):
        """
        Perform adapter-specific shutdown
        
        This method should clean up any resources, close connections, etc.
        """
        pass
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "adapter_type": self.config.adapter_type.value,
            "model_name": self.config.model_name,
            "initialized": self._initialized,
            "capabilities": {
                "supports_streaming": self.supports_capability(
                    ModelCapabilities.STREAMING
                ),
                "supports_functions": self.supports_capability(
                    ModelCapabilities.FUNCTION_CALLING
                ),
                "supports_vision": self.supports_capability(
                    ModelCapabilities.VISION
                ),
                "supports_system_prompt": True  # Most models support this
            }
        }
        
    async def _retry_with_backoff(
        self, func, *args, **kwargs
    ) -> Any:
        """
        Retry a function with exponential backoff
        
        Args:
            func: Function to retry
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
        """
        import asyncio
        
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {self.config.max_retries} attempts failed"
                    )
                    
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("Unknown error in retry")
        
    def supports_capability(self, capability: ModelCapabilities) -> bool:
        """Check if model supports a specific capability"""
        return capability in self._capabilities
        
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"{self.__class__.__name__}("
            f"model='{self.config.model_name}', "
            f"initialized={self._initialized})"
        )