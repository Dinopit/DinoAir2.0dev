"""
Model Interface Abstraction

This module provides the core abstraction layer for AI models,
allowing tools to work independently of specific model implementations.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ModelCapabilities(Enum):
    """Capabilities that a model might support"""
    TEXT_GENERATION = auto()
    FUNCTION_CALLING = auto()
    STREAMING = auto()
    EMBEDDINGS = auto()
    VISION = auto()
    AUDIO = auto()
    CODE_GENERATION = auto()
    REASONING = auto()
    TOOL_USE = auto()
    CONTEXT_WINDOW_4K = auto()
    CONTEXT_WINDOW_8K = auto()
    CONTEXT_WINDOW_16K = auto()
    CONTEXT_WINDOW_32K = auto()
    CONTEXT_WINDOW_128K = auto()
    CONTEXT_WINDOW_UNLIMITED = auto()


@dataclass
class ModelRequest:
    """Standard request format for model interactions"""
    prompt: str
    system_prompt: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    messages: Optional[List[Dict[str, str]]] = None
    stream: bool = False
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary"""
        data = {
            "prompt": self.prompt,
            "parameters": self.parameters,
            "stream": self.stream,
            "metadata": self.metadata
        }
        
        # Add optional fields
        optional_fields = [
            "system_prompt", "tools", "tool_choice", "messages",
            "max_tokens", "temperature", "top_p", "stop_sequences"
        ]
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
                
        return data


@dataclass
class ModelResponse:
    """Standard response format from model interactions"""
    content: str
    success: bool = True
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None  # tokens used
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        return {
            "content": self.content,
            "success": self.success,
            "error": self.error,
            "usage": self.usage,
            "tool_calls": self.tool_calls,
            "finish_reason": self.finish_reason,
            "model": self.model,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class ModelInterface(ABC):
    """
    Abstract interface for AI models
    
    This interface defines the contract that all model implementations
    must follow, ensuring tools can work with any AI model that
    implements this interface.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the model interface
        
        Args:
            config: Model-specific configuration
        """
        self.config = config or {}
        self._capabilities: List[ModelCapabilities] = []
        self._is_initialized = False
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the model connection/resources
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate a response from the model
        
        Args:
            request: Standard model request
            
        Returns:
            Standard model response
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self, 
        request: ModelRequest,
        callback: Callable[[str], None]
    ) -> ModelResponse:
        """
        Generate a streaming response from the model
        
        Args:
            request: Standard model request
            callback: Function to call with each chunk
            
        Returns:
            Final model response
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ModelCapabilities]:
        """
        Get the capabilities supported by this model
        
        Returns:
            List of supported capabilities
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the model is available and ready
        
        Returns:
            True if model is available
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        
        Returns:
            Dictionary with model information
        """
        pass
    
    async def shutdown(self):
        """Cleanup model resources"""
        self._is_initialized = False
    
    def supports_capability(self, capability: ModelCapabilities) -> bool:
        """Check if model supports a specific capability"""
        return capability in self.get_capabilities()
    
    def validate_request(self, request: ModelRequest) -> bool:
        """
        Validate a request against model capabilities
        
        Args:
            request: Request to validate
            
        Returns:
            True if request is valid for this model
        """
        # Check streaming support
        if request.stream and not self.supports_capability(
            ModelCapabilities.STREAMING
        ):
            logger.warning("Model does not support streaming")
            return False
            
        # Check tool use
        if request.tools and not self.supports_capability(
            ModelCapabilities.TOOL_USE
        ):
            logger.warning("Model does not support tool use")
            return False
            
        # Check function calling
        if request.tool_choice and not self.supports_capability(
            ModelCapabilities.FUNCTION_CALLING
        ):
            logger.warning("Model does not support function calling")
            return False
            
        return True


class StandardModelAdapter(ModelInterface):
    """
    Standard adapter for wrapping model-specific implementations
    
    This adapter provides a standard way to wrap existing model
    implementations (like Ollama, OpenAI, etc.) to conform to
    the ModelInterface.
    """
    
    def __init__(
        self,
        model_impl: Any,
        config: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[ModelCapabilities]] = None
    ):
        """
        Initialize the adapter
        
        Args:
            model_impl: The underlying model implementation
            config: Model configuration
            capabilities: List of model capabilities
        """
        super().__init__(config)
        self.model = model_impl
        self._capabilities = capabilities or [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING
        ]
        self._adapter_funcs: Dict[str, Callable] = {}
        
    def set_adapter_function(self, name: str, func: Callable):
        """
        Set an adapter function for translating between interfaces
        
        Args:
            name: Function name ('request_to_model', 'response_from_model')
            func: Adapter function
        """
        self._adapter_funcs[name] = func
        
    async def initialize(self) -> bool:
        """Initialize the model"""
        try:
            # Try common initialization patterns
            if hasattr(self.model, 'initialize'):
                result = await self.model.initialize()
                self._is_initialized = bool(result)
            elif hasattr(self.model, 'start'):
                result = await self.model.start()
                self._is_initialized = bool(result)
            elif hasattr(self.model, 'connect'):
                result = await self.model.connect()
                self._is_initialized = bool(result)
            else:
                # Assume model is ready if no init method
                self._is_initialized = True
                
            return self._is_initialized
            
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return False
            
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response"""
        if not self.validate_request(request):
            return ModelResponse(
                content="",
                success=False,
                error="Invalid request for model capabilities"
            )
            
        try:
            # Convert request if adapter function provided
            if 'request_to_model' in self._adapter_funcs:
                model_request = self._adapter_funcs['request_to_model'](
                    request
                )
            else:
                model_request = self._default_request_adapter(request)
                
            # Call the underlying model
            if hasattr(self.model, 'generate'):
                model_response = await self.model.generate(**model_request)
            elif hasattr(self.model, 'complete'):
                model_response = await self.model.complete(**model_request)
            elif hasattr(self.model, 'chat'):
                model_response = await self.model.chat(**model_request)
            else:
                raise AttributeError("Model has no generation method")
                
            # Convert response if adapter function provided
            if 'response_from_model' in self._adapter_funcs:
                return self._adapter_funcs['response_from_model'](
                    model_response
                )
            else:
                return self._default_response_adapter(model_response)
                
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
        """Generate a streaming response"""
        if not self.supports_capability(ModelCapabilities.STREAMING):
            # Fall back to non-streaming
            response = await self.generate(request)
            if response.success:
                callback(response.content)
            return response
            
        try:
            # Convert request
            if 'request_to_model' in self._adapter_funcs:
                model_request = self._adapter_funcs['request_to_model'](
                    request
                )
            else:
                model_request = self._default_request_adapter(request)
                
            # Stream from model
            full_content = []
            
            if hasattr(self.model, 'stream_generate'):
                async for chunk in self.model.stream_generate(**model_request):
                    content = self._extract_chunk_content(chunk)
                    full_content.append(content)
                    callback(content)
            elif hasattr(self.model, 'stream'):
                async for chunk in self.model.stream(**model_request):
                    content = self._extract_chunk_content(chunk)
                    full_content.append(content)
                    callback(content)
            else:
                # No streaming support, use regular generation
                response = await self.generate(request)
                if response.success:
                    callback(response.content)
                return response
                
            return ModelResponse(
                content="".join(full_content),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=str(e)
            )
            
    def get_capabilities(self) -> List[ModelCapabilities]:
        """Get model capabilities"""
        return self._capabilities.copy()
        
    def is_available(self) -> bool:
        """Check if model is available"""
        if hasattr(self.model, 'is_available'):
            return self.model.is_available()
        elif hasattr(self.model, 'is_ready'):
            return self.model.is_ready()
        elif hasattr(self.model, 'health_check'):
            try:
                return self.model.health_check()
            except Exception:
                return False
        else:
            # Assume available if initialized
            return self._is_initialized
            
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = {
            "adapter": "StandardModelAdapter",
            "initialized": self._is_initialized,
            "capabilities": [cap.name for cap in self._capabilities]
        }
        
        # Try to get info from underlying model
        if hasattr(self.model, 'get_info'):
            info["model_info"] = self.model.get_info()
        elif hasattr(self.model, 'info'):
            info["model_info"] = self.model.info()
        elif hasattr(self.model, '__dict__'):
            # Extract basic info from model attributes
            model_attrs = {}
            for key, value in self.model.__dict__.items():
                if not key.startswith('_') and isinstance(
                    value, (str, int, float, bool)
                ):
                    model_attrs[key] = value
            if model_attrs:
                info["model_attributes"] = model_attrs
                
        return info
        
    def _default_request_adapter(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Default adapter for converting ModelRequest to model format"""
        # Start with basic fields that most models support
        adapted = {
            "prompt": request.prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": request.stream
        }
        
        # Add system prompt if supported
        if request.system_prompt:
            adapted["system"] = request.system_prompt
            
        # Handle messages format (for chat models)
        if request.messages:
            adapted["messages"] = request.messages
        elif request.system_prompt:
            # Convert to messages format
            adapted["messages"] = [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt}
            ]
        else:
            # Simple prompt format
            adapted["messages"] = [
                {"role": "user", "content": request.prompt}
            ]
            
        # Add other parameters
        if request.top_p is not None:
            adapted["top_p"] = request.top_p
        if request.stop_sequences:
            adapted["stop"] = request.stop_sequences
            
        # Tools and function calling
        if request.tools:
            adapted["tools"] = request.tools
        if request.tool_choice:
            adapted["tool_choice"] = request.tool_choice
            
        # Filter out None values
        return {k: v for k, v in adapted.items() if v is not None}
        
    def _default_response_adapter(self, model_response: Any) -> ModelResponse:
        """Default adapter for converting model response to ModelResponse"""
        # Handle different response types
        if isinstance(model_response, str):
            return ModelResponse(content=model_response)
            
        if isinstance(model_response, dict):
            return ModelResponse(
                content=(
                    model_response.get("content", "") or
                    model_response.get("text", "") or
                    model_response.get("response", "") or
                    model_response.get("message", {}).get("content", "") or
                    str(model_response)
                ),
                success=model_response.get("success", True),
                error=model_response.get("error"),
                usage=model_response.get("usage"),
                tool_calls=model_response.get("tool_calls"),
                finish_reason=model_response.get("finish_reason"),
                model=model_response.get("model"),
                metadata=model_response.get("metadata", {})
            )
            
        # Handle object with attributes
        if hasattr(model_response, '__dict__'):
            return ModelResponse(
                content=(
                    getattr(model_response, 'content', '') or
                    getattr(model_response, 'text', '') or
                    getattr(model_response, 'response', '') or
                    str(model_response)
                ),
                success=getattr(model_response, 'success', True),
                error=getattr(model_response, 'error', None),
                usage=getattr(model_response, 'usage', None),
                tool_calls=getattr(model_response, 'tool_calls', None),
                finish_reason=getattr(model_response, 'finish_reason', None),
                model=getattr(model_response, 'model', None)
            )
            
        # Fallback to string representation
        return ModelResponse(content=str(model_response))
        
    def _extract_chunk_content(self, chunk: Any) -> str:
        """Extract content from a streaming chunk"""
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, dict):
            return (
                chunk.get("content", "") or
                chunk.get("text", "") or
                chunk.get("delta", {}).get("content", "") or
                chunk.get("response", "") or
                ""
            )
        elif hasattr(chunk, 'content'):
            return getattr(chunk, 'content', '')
        elif hasattr(chunk, 'text'):
            return getattr(chunk, 'text', '')
        elif hasattr(chunk, 'delta'):
            delta = getattr(chunk, 'delta')
            if hasattr(delta, 'content'):
                return getattr(delta, 'content', '')
            elif isinstance(delta, dict):
                return delta.get('content', '')
        return str(chunk)


class ModelAgnosticToolExecutor:
    """
    Executes tools without dependency on specific AI models
    
    This class provides a way to execute tools using any model
    that implements the ModelInterface.
    """
    
    def __init__(self, model: Optional[ModelInterface] = None):
        """
        Initialize the executor
        
        Args:
            model: Optional model interface for AI-assisted execution
        """
        self.model = model
        self._execution_history: List[Dict[str, Any]] = []
        
    async def execute_tool(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        use_ai_assistance: bool = False,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with optional AI assistance
        
        Args:
            tool: Tool instance to execute
            parameters: Tool parameters
            use_ai_assistance: Whether to use AI for parameter enhancement
            context: Additional context for AI assistance
            
        Returns:
            Execution result
        """
        try:
            # Enhance parameters with AI if requested and model available
            if use_ai_assistance and self.model and self.model.is_available():
                parameters = await self._enhance_parameters_with_ai(
                    tool, parameters, context
                )
                
            # Execute the tool
            result = tool.execute(**parameters)
            
            # Record execution
            self._execution_history.append({
                "tool": tool.name if hasattr(tool, 'name') else str(tool),
                "parameters": parameters,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "ai_assisted": use_ai_assistance
            })
            
            return {
                "success": True,
                "result": result,
                "parameters_used": parameters
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "parameters_attempted": parameters
            }
            
            # Try to get AI assistance for error recovery
            if use_ai_assistance and self.model and self.model.is_available():
                recovery = await self._get_ai_error_recovery(
                    tool, parameters, str(e), context
                )
                if recovery:
                    error_result["recovery_suggestions"] = recovery
                    
            return error_result
            
    async def _enhance_parameters_with_ai(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        context: Optional[str]
    ) -> Dict[str, Any]:
        """Use AI to enhance or validate parameters"""
        prompt = f"""
Given the following tool and parameters, enhance or correct the parameters:

Tool: {getattr(tool, 'name', 'Unknown')}
Description: {getattr(tool, 'description', 'No description')}
Current Parameters: {json.dumps(parameters, indent=2)}
Context: {context or 'No additional context'}

Please provide the enhanced parameters as valid JSON.
"""
        
        request = ModelRequest(
            prompt=prompt,
            system_prompt="You enhance tool parameters.",
            temperature=0.3,
            max_tokens=500
        )
        
        if not self.model:
            return parameters
            
        response = await self.model.generate(request)
        
        if response.success:
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    enhanced = json.loads(json_match.group())
                    # Merge with original parameters
                    parameters.update(enhanced)
            except Exception:
                # If parsing fails, use original parameters
                pass
                
        return parameters
        
    async def _get_ai_error_recovery(
        self,
        tool: Any,
        parameters: Dict[str, Any],
        error: str,
        context: Optional[str]
    ) -> Optional[List[str]]:
        """Get AI suggestions for error recovery"""
        prompt = f"""
A tool execution failed with an error. Please provide recovery suggestions:

Tool: {getattr(tool, 'name', 'Unknown')}
Parameters Used: {json.dumps(parameters, indent=2)}
Error: {error}
Context: {context or 'No additional context'}

Provide 3-5 specific, actionable recovery suggestions.
"""
        
        request = ModelRequest(
            prompt=prompt,
            system_prompt="You are an expert at debugging and error recovery.",
            temperature=0.5,
            max_tokens=300
        )
        
        if not self.model:
            return None
            
        response = await self.model.generate(request)
        
        if response.success:
            # Parse suggestions from response
            suggestions = []
            lines = response.content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and (
                    line[0].isdigit() or
                    line.startswith('-') or
                    line.startswith('*')
                ):
                    # Remove bullet points/numbers
                    suggestion = re.sub(r'^[\d\-\*\.\)]+\s*', '', line)
                    if suggestion:
                        suggestions.append(suggestion)
            return suggestions[:5]  # Return up to 5 suggestions
            
        return None
        
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get the history of tool executions"""
        return self._execution_history.copy()
        
    def clear_history(self):
        """Clear execution history"""
        self._execution_history.clear()