"""
OpenAI Model Adapter

This module provides an adapter for OpenAI models (GPT-3.5, GPT-4, etc.)
to work with the tool system's abstraction layer.
"""

import logging
import os
from typing import Any, Dict, List, Optional, AsyncIterator

from .base_adapter import (
    BaseModelAdapter, AdapterConfig, AdapterType, StreamChunk
)
from ..abstraction.model_interface import (
    ModelRequest, ModelResponse, ModelCapabilities
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseModelAdapter):
    """
    Adapter for OpenAI models
    
    This adapter provides integration with OpenAI's API, supporting
    models like GPT-3.5-turbo, GPT-4, and their variants.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize OpenAI adapter
        
        Args:
            config: Adapter configuration
        """
        if config is None:
            config = AdapterConfig(
                adapter_type=AdapterType.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key=os.getenv("OPENAI_API_KEY"),
                api_base=os.getenv(
                    "OPENAI_API_BASE", "https://api.openai.com/v1"
                )
            )
        
        super().__init__(config)
        self._client = None
        
    def _define_capabilities(self) -> List[ModelCapabilities]:
        """Define OpenAI model capabilities"""
        capabilities = [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.TOOL_USE,
            ModelCapabilities.CODE_GENERATION,
            ModelCapabilities.REASONING
        ]
        
        # Add context window based on model
        if "gpt-4" in self.config.model_name.lower():
            if "32k" in self.config.model_name:
                capabilities.append(ModelCapabilities.CONTEXT_WINDOW_32K)
            elif "turbo" in self.config.model_name:
                capabilities.append(ModelCapabilities.CONTEXT_WINDOW_128K)
            else:
                capabilities.append(ModelCapabilities.CONTEXT_WINDOW_8K)
        else:  # GPT-3.5
            if "16k" in self.config.model_name:
                capabilities.append(ModelCapabilities.CONTEXT_WINDOW_16K)
            else:
                capabilities.append(ModelCapabilities.CONTEXT_WINDOW_4K)
                
        # Vision support for GPT-4V
        if ("vision" in self.config.model_name or
                "gpt-4v" in self.config.model_name):
            capabilities.append(ModelCapabilities.VISION)
            
        return capabilities
        
    async def _initialize_adapter(self):
        """Initialize OpenAI client"""
        try:
            # Import OpenAI client
            try:
                from openai import AsyncOpenAI
            except ImportError:
                logger.error(
                    "OpenAI package not installed. Run: pip install openai"
                )
                raise
                
            # Initialize client
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
            
            logger.info("OpenAI client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
            
    async def _validate_connection(self) -> bool:
        """Validate OpenAI connection"""
        if not self._client:
            return False
            
        try:
            # Try to list models to validate connection
            models = await self._client.models.list()
            
            # Check if our model is available
            model_ids = [m.id for m in models.data]
            if self.config.model_name not in model_ids:
                logger.warning(
                    f"Model {self.config.model_name} not found in "
                    f"available models"
                )
                
            return True
            
        except Exception as e:
            logger.error(f"OpenAI connection validation failed: {e}")
            return False
            
    async def _prepare_request(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Prepare request for OpenAI API"""
        # Build messages
        messages = []
        
        # Add system prompt if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })
            
        # Add user messages or prompt
        if request.messages:
            messages.extend(request.messages)
        else:
            messages.append({
                "role": "user",
                "content": request.prompt
            })
            
        # Build request
        openai_request = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": request.stream
        }
        
        # Add optional parameters
        if request.max_tokens:
            openai_request["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            openai_request["temperature"] = request.temperature
        if request.top_p is not None:
            openai_request["top_p"] = request.top_p
        if request.stop_sequences:
            openai_request["stop"] = request.stop_sequences
            
        # Add tools/functions if provided
        if request.tools:
            openai_request["tools"] = request.tools
        if request.tool_choice:
            openai_request["tool_choice"] = request.tool_choice
            
        # Add any extra parameters from config
        if self.config.extra_params:
            openai_request.update(self.config.extra_params)
            
        return openai_request
        
    async def _generate_internal(
        self, prepared_request: Dict[str, Any]
    ) -> Any:
        """Call OpenAI completion API"""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
            
        # Remove stream flag for non-streaming
        prepared_request.pop("stream", None)
        
        response = await self._client.chat.completions.create(
            **prepared_request
        )
        return response
        
    async def _stream_internal(
        self, prepared_request: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Call OpenAI streaming API"""
        if not self._client:
            raise RuntimeError("OpenAI client not initialized")
            
        # Ensure streaming is enabled
        prepared_request["stream"] = True
        
        # Create stream
        stream = await self._client.chat.completions.create(**prepared_request)
        
        # Yield chunks
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield StreamChunk(
                    content=chunk.choices[0].delta.content,
                    is_final=chunk.choices[0].finish_reason is not None,
                    metadata={
                        "finish_reason": chunk.choices[0].finish_reason,
                        "index": chunk.choices[0].index
                    }
                )
                
    async def _process_response(
        self, raw_response: Any, original_request: ModelRequest
    ) -> ModelResponse:
        """Process OpenAI response into standard format"""
        try:
            # Extract content
            choice = raw_response.choices[0]
            content = choice.message.content or ""
            
            # Extract tool calls if any
            tool_calls = None
            if (hasattr(choice.message, 'tool_calls') and
                    choice.message.tool_calls):
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in choice.message.tool_calls
                ]
                
            # Extract usage
            usage = None
            if hasattr(raw_response, 'usage'):
                usage = {
                    "prompt_tokens": raw_response.usage.prompt_tokens,
                    "completion_tokens": raw_response.usage.completion_tokens,
                    "total_tokens": raw_response.usage.total_tokens
                }
                
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                model=raw_response.model,
                usage=usage,
                metadata={
                    "id": raw_response.id,
                    "created": raw_response.created,
                    "system_fingerprint": getattr(
                        raw_response, 'system_fingerprint', None
                    )
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process OpenAI response: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )
            
    async def _shutdown_adapter(self):
        """Cleanup OpenAI resources"""
        if self._client:
            await self._client.close()
            self._client = None
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        info = super().get_model_info()
        
        # Add OpenAI-specific info
        info.update({
            "provider": "OpenAI",
            "api_base": self.config.api_base,
            "model_family": (
                "GPT" if "gpt" in self.config.model_name else "Unknown"
            ),
            "supports_functions": True,
            "supports_vision": (
                "vision" in self.config.model_name or
                "gpt-4v" in self.config.model_name
            )
        })
        
        return info