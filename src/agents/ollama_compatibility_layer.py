"""
Ollama Compatibility Layer

This module provides backward compatibility wrappers for the existing
OllamaModelAdapter and OllamaAdapter interfaces, ensuring zero breaking
changes when transitioning to the UnifiedOllamaInterface.

Key Features:
- Drop-in replacement for OllamaModelAdapter
- Drop-in replacement for OllamaAdapter from tools/adapters
- Maintains all existing API signatures
- Delegates to UnifiedOllamaInterface internally
- Preserves existing behavior and data formats
"""

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from ..tools.abstraction.model_interface import (
    ModelInterface,
    ModelRequest, 
    ModelResponse,
    ModelCapabilities
)
from ..tools.adapters.base_adapter import (
    BaseModelAdapter,
    AdapterConfig,
    AdapterType,
    StreamChunk
)
from .unified_ollama_interface import UnifiedOllamaInterface
from .ollama_wrapper import OllamaWrapper

logger = logging.getLogger(__name__)


class OllamaModelAdapterCompat(ModelInterface):
    """
    Backward compatibility wrapper for OllamaModelAdapter
    
    This class maintains the exact same interface as the original
    OllamaModelAdapter while internally using the UnifiedOllamaInterface
    for improved performance and consolidation.
    """
    
    def __init__(self, 
                 ollama_wrapper: Optional[OllamaWrapper] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize compatibility adapter
        
        Args:
            ollama_wrapper: Optional existing OllamaWrapper instance
            config: Model configuration
        """
        super().__init__(config or {})
        
        # Create unified interface
        self._unified_interface = UnifiedOllamaInterface(
            ollama_wrapper=ollama_wrapper,
            config=self.config
        )
        
        # Expose wrapper for backward compatibility
        self.ollama = self._unified_interface.ollama_wrapper
        
        # Tool state
        self._available_tools: List[Dict[str, Any]] = []
        self._tool_execution_callback: Optional[Callable] = None

    async def initialize(self) -> bool:
        """Initialize the adapter"""
        success = await self._unified_interface.initialize()
        if success:
            self._is_initialized = True
        return success

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response using Ollama"""
        return await self._unified_interface.generate(request)

    async def stream_generate(
        self, 
        request: ModelRequest,
        callback: Callable[[str], None]
    ) -> ModelResponse:
        """Generate a streaming response using Ollama"""
        return await self._unified_interface.stream_generate(request, callback)

    def get_capabilities(self) -> List[ModelCapabilities]:
        """Get model capabilities"""
        return self._unified_interface.get_capabilities()

    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        return self._unified_interface.is_available()

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = self._unified_interface.get_model_info()
        # Add adapter-specific info for compatibility
        info["adapter"] = "OllamaModelAdapter"
        return info

    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set available tools for the model"""
        self._available_tools = tools
        self._unified_interface.set_tools(tools)
        logger.info(f"Set {len(tools)} tools for OllamaModelAdapter")

    def set_tool_execution_callback(self, callback: Callable):
        """Set callback for tool execution"""
        self._tool_execution_callback = callback
        self._unified_interface.set_tool_execution_callback(callback)

    async def shutdown(self):
        """Shutdown the adapter"""
        await self._unified_interface.shutdown()
        self._is_initialized = False

    # Legacy methods for compatibility

    def _convert_request_to_ollama(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Convert ModelRequest to Ollama format (legacy method)"""
        return self._unified_interface._convert_request_to_wrapper(request)

    def _add_tools_to_request(
        self, 
        ollama_request: Dict[str, Any], 
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add tool information to the Ollama request (legacy method)"""
        return self._unified_interface._add_tools_to_wrapper_request(
            ollama_request, tools
        )

    def _convert_response_from_ollama(
        self, 
        ollama_response: Any, 
        generation_time: float
    ) -> ModelResponse:
        """Convert Ollama response to ModelResponse (legacy method)"""
        return self._unified_interface._convert_wrapper_response(
            ollama_response, generation_time
        )

    def _extract_chunk_content(self, chunk: Any) -> str:
        """Extract content from a streaming chunk (legacy method)"""
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, dict):
            return chunk.get("response", "")
        elif hasattr(chunk, 'content'):
            return getattr(chunk, 'content', '')
        elif hasattr(chunk, 'response'):
            return getattr(chunk, 'response', '')
        return str(chunk)

    def _extract_tool_calls(
        self, content: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from model response (legacy method)"""
        return self._unified_interface._extract_tool_calls(content)


class OllamaAdapterCompat(BaseModelAdapter):
    """
    Backward compatibility wrapper for OllamaAdapter from tools/adapters
    
    This class maintains the exact same interface as the original
    OllamaAdapter while internally using the UnifiedOllamaInterface.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize Ollama adapter compatibility layer
        
        Args:
            config: Adapter configuration
        """
        if config is None:
            config = AdapterConfig(
                adapter_type=AdapterType.OLLAMA,
                model_name="llama2",
                api_base="http://localhost:11434"
            )
        
        super().__init__(config)
        
        # Create unified interface with config conversion
        unified_config = {
            'host': config.api_base,
            'timeout': config.timeout,
            'use_http_fallback': True,
            'prefer_http_streaming': True
        }
        
        self._unified_interface = UnifiedOllamaInterface(config=unified_config)
        
        # Set model if specified
        if config.model_name:
            try:
                wrapper = self._unified_interface.ollama_wrapper
                wrapper.set_model(config.model_name)
            except Exception as e:
                logger.warning(f"Failed to set initial model: {e}")

    def _define_capabilities(self) -> List[ModelCapabilities]:
        """Define Ollama model capabilities"""
        capabilities = [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING,
            ModelCapabilities.CODE_GENERATION
        ]
        
        # Context window depends on the model
        model_lower = self.config.model_name.lower()
        if "codellama" in model_lower:
            capabilities.append(ModelCapabilities.CODE_GENERATION)
            capabilities.append(ModelCapabilities.CONTEXT_WINDOW_16K)
        elif "llama2:70b" in model_lower or "mixtral" in model_lower:
            capabilities.append(ModelCapabilities.CONTEXT_WINDOW_32K)
            capabilities.append(ModelCapabilities.REASONING)
        elif "llama2:13b" in model_lower or "llama2:7b" in model_lower:
            capabilities.append(ModelCapabilities.CONTEXT_WINDOW_4K)
        else:
            capabilities.append(ModelCapabilities.CONTEXT_WINDOW_4K)
            
        # Vision support for specific models
        if "llava" in model_lower or "bakllava" in model_lower:
            capabilities.append(ModelCapabilities.VISION)
            
        return capabilities

    async def _initialize_adapter(self):
        """Initialize Ollama adapter"""
        await self._unified_interface.initialize()

    async def _validate_connection(self) -> bool:
        """Validate Ollama connection"""
        return self._unified_interface.is_available()

    async def _prepare_request(self, request: ModelRequest) -> Dict[str, Any]:
        """Prepare request for Ollama API"""
        # Convert to unified interface format
        return self._unified_interface._convert_request_to_wrapper(request)

    async def _generate_internal(
        self, prepared_request: Dict[str, Any]
    ) -> Any:
        """Call Ollama generate API via unified interface"""
        # Create a ModelRequest from prepared request
        model_request = self._convert_prepared_to_model_request(
            prepared_request
        )
        response = await self._unified_interface.generate(model_request)
        
        # Convert back to expected format
        eval_count = 0
        if response.usage:
            eval_count = response.usage.get("tokens_generated", 0)
            
        return {
            "response": response.content,
            "model": response.model,
            "done": True,
            "eval_count": eval_count
        }

    async def _stream_internal(
        self,
        prepared_request: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Call Ollama streaming API via unified interface"""
        model_request = self._convert_prepared_to_model_request(
            prepared_request
        )
        
        # Collect chunks
        chunks = []
        
        def collect_chunk(content: str):
            chunks.append(content)
        
        await self._unified_interface.stream_generate(
            model_request, collect_chunk
        )
        
        # Yield collected chunks as StreamChunk objects
        for i, content in enumerate(chunks):
            yield StreamChunk(
                content=content,
                is_final=(i == len(chunks) - 1),
                metadata={"model": self.config.model_name}
            )

    async def _process_response(
        self, 
        raw_response: Any, 
        original_request: ModelRequest
    ) -> ModelResponse:
        """Process Ollama response into standard format"""
        try:
            # Extract content
            content = raw_response.get("response", "")
            
            # Extract usage information
            usage = None
            if "eval_count" in raw_response:
                usage = {
                    "prompt_tokens": raw_response.get("prompt_eval_count", 0),
                    "completion_tokens": raw_response.get("eval_count", 0),
                    "total_tokens": (
                        raw_response.get("prompt_eval_count", 0) +
                        raw_response.get("eval_count", 0)
                    )
                }
                
            return ModelResponse(
                content=content,
                success=True,
                model=raw_response.get("model", self.config.model_name),
                usage=usage,
                metadata={
                    "done": raw_response.get("done", True),
                    "total_duration": raw_response.get("total_duration"),
                    "eval_duration": raw_response.get("eval_duration")
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process Ollama response: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )

    async def _shutdown_adapter(self):
        """Cleanup Ollama resources"""
        await self._unified_interface.shutdown()

    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information"""
        info = super().get_model_info()
        
        # Add Ollama-specific info
        info.update({
            "provider": "Ollama",
            "api_base": self.config.api_base,
            "model_family": self._get_model_family(),
            "is_local": True,
            "supports_gpu": True
        })
        
        return info

    def _get_model_family(self) -> str:
        """Determine model family from model name"""
        model_lower = self.config.model_name.lower()
        if "llama" in model_lower:
            return "Llama"
        elif "mistral" in model_lower:
            return "Mistral"
        elif "mixtral" in model_lower:
            return "Mixtral"
        elif "phi" in model_lower:
            return "Phi"
        elif "gemma" in model_lower:
            return "Gemma"
        elif "vicuna" in model_lower:
            return "Vicuna"
        else:
            return "Unknown"

    def _convert_prepared_to_model_request(
        self, 
        prepared: Dict[str, Any]
    ) -> ModelRequest:
        """Convert prepared request back to ModelRequest"""
        # Extract options
        options = prepared.get('options', {})
        
        return ModelRequest(
            prompt=prepared.get('prompt', ''),
            temperature=options.get('temperature'),
            top_p=options.get('top_p'),
            max_tokens=options.get('num_predict'),
            stop_sequences=options.get('stop'),
            stream=prepared.get('stream', False)
        )

    def _messages_to_prompt(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """Convert messages format to Ollama prompt"""
        prompt_parts = []
        
        # Add system prompt if provided
        if system_prompt:
            prompt_parts.append(f"System: {system_prompt}")
            
        # Convert messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
                
        # Add final Assistant prompt
        prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)


# Factory functions for backward compatibility

def create_ollama_model_adapter(
    ollama_wrapper: Optional[OllamaWrapper] = None,
    config: Optional[Dict[str, Any]] = None
) -> OllamaModelAdapterCompat:
    """
    Create OllamaModelAdapter with backward compatibility
    
    Args:
        ollama_wrapper: Optional existing OllamaWrapper instance
        config: Model configuration
        
    Returns:
        Compatible OllamaModelAdapter instance
    """
    return OllamaModelAdapterCompat(ollama_wrapper, config)


def create_ollama_adapter(
    config: Optional[AdapterConfig] = None
) -> OllamaAdapterCompat:
    """
    Create OllamaAdapter with backward compatibility
    
    Args:
        config: Adapter configuration
        
    Returns:
        Compatible OllamaAdapter instance
    """
    return OllamaAdapterCompat(config)