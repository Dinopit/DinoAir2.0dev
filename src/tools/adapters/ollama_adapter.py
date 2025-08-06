"""
Ollama Model Adapter

This module provides an adapter for Ollama models (local LLMs)
to work with the tool system's abstraction layer.
"""

import logging
import os
from typing import Any, Dict, List, Optional, AsyncIterator
import aiohttp
import json

from .base_adapter import (
    BaseModelAdapter, AdapterConfig, AdapterType, StreamChunk
)
from ..abstraction.model_interface import (
    ModelRequest, ModelResponse, ModelCapabilities
)

logger = logging.getLogger(__name__)


class OllamaAdapter(BaseModelAdapter):
    """
    Adapter for Ollama local models
    
    This adapter provides integration with Ollama's local API, supporting
    various open-source models like Llama, Mistral, etc.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """
        Initialize Ollama adapter
        
        Args:
            config: Adapter configuration
        """
        if config is None:
            config = AdapterConfig(
                adapter_type=AdapterType.OLLAMA,
                model_name="llama2",
                api_base=os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
            )
        
        super().__init__(config)
        self._session = None
        
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
            # Default to 4K for unknown models
            capabilities.append(ModelCapabilities.CONTEXT_WINDOW_4K)
            
        # Vision support for specific models
        if "llava" in model_lower or "bakllava" in model_lower:
            capabilities.append(ModelCapabilities.VISION)
            
        return capabilities
        
    async def _initialize_adapter(self):
        """Initialize Ollama HTTP session"""
        try:
            # Create aiohttp session
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Ollama HTTP session initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama session: {e}")
            raise
            
    async def _validate_connection(self) -> bool:
        """Validate Ollama connection"""
        if not self._session:
            return False
            
        try:
            # Check if Ollama is running
            url = f"{self.config.api_base}/api/tags"
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Check if our model is available
                    models = [
                        m.get("name", "") for m in data.get("models", [])
                    ]
                    if self.config.model_name not in models:
                        logger.warning(
                            f"Model {self.config.model_name} not found. "
                            f"Available models: {models}"
                        )
                    return True
                else:
                    logger.error(f"Ollama API returned status {resp.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ollama connection validation failed: {e}")
            return False
            
    async def _prepare_request(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Prepare request for Ollama API"""
        # Build the prompt
        if request.messages:
            # Convert messages to Ollama format
            prompt = self._messages_to_prompt(
                request.messages, request.system_prompt
            )
        else:
            # Simple prompt with optional system
            if request.system_prompt:
                prompt = f"{request.system_prompt}\n\n{request.prompt}"
            else:
                prompt = request.prompt
                
        # Build request
        ollama_request = {
            "model": self.config.model_name,
            "prompt": prompt,
            "stream": request.stream
        }
        
        # Add options
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.max_tokens:
            options["num_predict"] = request.max_tokens
        if request.stop_sequences:
            options["stop"] = request.stop_sequences
            
        if options:
            ollama_request["options"] = options
            
        # Add any extra parameters from config
        if self.config.extra_params:
            ollama_request.update(self.config.extra_params)
            
        return ollama_request
        
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
        
    async def _generate_internal(
        self, prepared_request: Dict[str, Any]
    ) -> Any:
        """Call Ollama generate API"""
        if not self._session:
            raise RuntimeError("Ollama session not initialized")
            
        # Remove stream flag for non-streaming
        prepared_request["stream"] = False
        
        url = f"{self.config.api_base}/api/generate"
        
        async with self._session.post(url, json=prepared_request) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Ollama API error: {error_text}")
                
            return await resp.json()
            
    async def _stream_internal(
        self, prepared_request: Dict[str, Any]
    ) -> AsyncIterator[StreamChunk]:
        """Call Ollama streaming API"""
        if not self._session:
            raise RuntimeError("Ollama session not initialized")
            
        # Ensure streaming is enabled
        prepared_request["stream"] = True
        
        url = f"{self.config.api_base}/api/generate"
        
        async with self._session.post(url, json=prepared_request) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"Ollama API error: {error_text}")
                
            # Read streaming response
            async for line in resp.content:
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield StreamChunk(
                                content=data["response"],
                                is_final=data.get("done", False),
                                metadata={
                                    "model": data.get("model"),
                                    "done": data.get("done", False),
                                    "context": data.get("context", [])
                                }
                            )
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse streaming response: {line}"
                        )
                        
    async def _process_response(
        self, raw_response: Any, original_request: ModelRequest
    ) -> ModelResponse:
        """Process Ollama response into standard format"""
        try:
            # Extract content
            content = raw_response.get("response", "")
            
            # Extract usage (Ollama provides limited info)
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
                    "context": raw_response.get("context", []),
                    "total_duration": raw_response.get("total_duration"),
                    "load_duration": raw_response.get("load_duration"),
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
        if self._session:
            await self._session.close()
            self._session = None
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get Ollama model information"""
        info = super().get_model_info()
        
        # Add Ollama-specific info
        info.update({
            "provider": "Ollama",
            "api_base": self.config.api_base,
            "model_family": self._get_model_family(),
            "is_local": True,
            "supports_gpu": True  # Ollama can use GPU if available
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