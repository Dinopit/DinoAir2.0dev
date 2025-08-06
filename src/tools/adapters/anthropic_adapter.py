"""
Anthropic Model Adapter

This module provides an adapter for Anthropic models (Claude series)
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


class AnthropicAdapter(BaseModelAdapter):
    """
    Adapter for Anthropic Claude models
    
    This adapter provides integration with Anthropic's API, supporting
    the Claude series of models.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize Anthropic adapter
        
        Args:
            config: Adapter configuration
        """
        if config is None:
            config = AdapterConfig(
                adapter_type=AdapterType.ANTHROPIC,
                model_name="claude-3-sonnet-20240229",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                api_base=os.getenv(
                    "ANTHROPIC_API_BASE", "https://api.anthropic.com"
                )
            )
        
        super().__init__(config)
        self._client = None
        
    def _define_capabilities(self) -> List[ModelCapabilities]:
        """Define Anthropic model capabilities"""
        capabilities = [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING,
            ModelCapabilities.CODE_GENERATION,
            ModelCapabilities.REASONING,
            # Claude models support 100K+ context
            ModelCapabilities.CONTEXT_WINDOW_128K
        ]
        
        # Claude 3 models have vision capabilities
        if "claude-3" in self.config.model_name.lower():
            capabilities.append(ModelCapabilities.VISION)
            
        # Tool use is available for newer models
        if ("claude-3" in self.config.model_name.lower() or
                "claude-2.1" in self.config.model_name.lower()):
            capabilities.append(ModelCapabilities.TOOL_USE)
            capabilities.append(ModelCapabilities.FUNCTION_CALLING)
            
        return capabilities
        
    async def _initialize_adapter(self):
        """Initialize Anthropic client"""
        try:
            # Import Anthropic client
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                logger.error(
                    "Anthropic package not installed. "
                    "Run: pip install anthropic"
                )
                raise
                
            # Initialize client
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
            
            logger.info("Anthropic client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise
            
    async def _validate_connection(self) -> bool:
        """Validate Anthropic connection"""
        if not self._client:
            return False
            
        try:
            # Try a minimal request to validate credentials
            # Anthropic doesn't have a list models endpoint, so we'll
            # just try to ensure the client is properly configured
            return True
            
        except Exception as e:
            logger.error(f"Anthropic connection validation failed: {e}")
            return False
            
    async def _prepare_request(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Prepare request for Anthropic API"""
        # Build messages
        messages = []
        
        # Add user messages or prompt
        if request.messages:
            messages.extend(request.messages)
        else:
            messages.append({
                "role": "user",
                "content": request.prompt
            })
            
        # Build request
        anthropic_request = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": request.stream
        }
        
        # Add system prompt separately (Anthropic specific)
        if request.system_prompt:
            anthropic_request["system"] = request.system_prompt
            
        # Add optional parameters
        if request.max_tokens:
            anthropic_request["max_tokens"] = request.max_tokens
        else:
            # Anthropic requires max_tokens
            anthropic_request["max_tokens"] = 4096
            
        if request.temperature is not None:
            anthropic_request["temperature"] = request.temperature
        if request.top_p is not None:
            anthropic_request["top_p"] = request.top_p
        if request.stop_sequences:
            anthropic_request["stop_sequences"] = request.stop_sequences
            
        # Add tools if provided (Claude 3 feature)
        if request.tools:
            anthropic_request["tools"] = self._convert_tools_format(
                request.tools
            )
        if request.tool_choice:
            anthropic_request["tool_choice"] = request.tool_choice
            
        # Add any extra parameters from config
        if self.config.extra_params:
            anthropic_request.update(self.config.extra_params)
            
        return anthropic_request
        
    def _convert_tools_format(
        self, tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Convert tools to Anthropic format"""
        # Anthropic has a slightly different tool format
        converted_tools = []
        for tool in tools:
            converted_tool = {
                "name": tool.get("function", {}).get("name", tool.get("name")),
                "description": tool.get("function", {}).get(
                    "description", tool.get("description")
                ),
                "input_schema": tool.get("function", {}).get(
                    "parameters", tool.get("parameters", {})
                )
            }
            converted_tools.append(converted_tool)
        return converted_tools
        
    async def _generate_internal(
        self, prepared_request: Dict[str, Any]
    ) -> Any:
        """Call Anthropic messages API"""
        if not self._client:
            raise RuntimeError("Anthropic client not initialized")
            
        # Remove stream flag for non-streaming
        prepared_request.pop("stream", None)
        
        response = await self._client.messages.create(**prepared_request)
        return response
        
    async def _stream_internal(
        self, prepared_request: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Call Anthropic streaming API"""
        if not self._client:
            raise RuntimeError("Anthropic client not initialized")
            
        # Ensure streaming is enabled
        prepared_request["stream"] = True
        
        # Create stream
        stream = await self._client.messages.create(**prepared_request)
        
        # Yield chunks
        async for event in stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, 'text'):
                    yield StreamChunk(
                        content=event.delta.text,
                        is_final=False,
                        metadata={
                            "index": event.index,
                            "type": event.type
                        }
                    )
            elif event.type == "message_stop":
                yield StreamChunk(
                    content="",
                    is_final=True,
                    metadata={"type": event.type}
                )
                
    async def _process_response(
        self, raw_response: Any, original_request: ModelRequest
    ) -> ModelResponse:
        """Process Anthropic response into standard format"""
        try:
            # Extract content
            content = ""
            if hasattr(raw_response, 'content') and raw_response.content:
                # Handle text blocks
                for block in raw_response.content:
                    if hasattr(block, 'text'):
                        content += block.text
                    elif hasattr(block, 'type') and block.type == 'text':
                        content += getattr(block, 'text', '')
                        
            # Extract tool use if any
            tool_calls = None
            if hasattr(raw_response, 'content'):
                tool_blocks = [
                    b for b in raw_response.content
                    if hasattr(b, 'type') and b.type == 'tool_use'
                ]
                if tool_blocks:
                    tool_calls = []
                    for block in tool_blocks:
                        tool_calls.append({
                            "id": block.id,
                            "type": "function",
                            "function": {
                                "name": block.name,
                                "arguments": block.input
                            }
                        })
                        
            # Extract usage
            usage = None
            if hasattr(raw_response, 'usage'):
                usage = {
                    "prompt_tokens": raw_response.usage.input_tokens,
                    "completion_tokens": raw_response.usage.output_tokens,
                    "total_tokens": (
                        raw_response.usage.input_tokens +
                        raw_response.usage.output_tokens
                    )
                }
                
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                finish_reason=getattr(raw_response, 'stop_reason', None),
                model=raw_response.model,
                usage=usage,
                metadata={
                    "id": raw_response.id,
                    "type": raw_response.type,
                    "role": raw_response.role,
                    "stop_sequence": getattr(
                        raw_response, 'stop_sequence', None
                    )
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to process Anthropic response: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )
            
    async def _shutdown_adapter(self):
        """Cleanup Anthropic resources"""
        if self._client:
            # Anthropic client doesn't have explicit close method
            self._client = None
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get Anthropic model information"""
        info = super().get_model_info()
        
        # Add Anthropic-specific info
        info.update({
            "provider": "Anthropic",
            "api_base": self.config.api_base,
            "model_family": "Claude",
            "supports_system_messages": True,
            "supports_vision": "claude-3" in self.config.model_name.lower(),
            "context_window": 100000  # Most Claude models support 100K+
        })
        
        return info