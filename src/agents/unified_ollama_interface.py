"""
Unified Ollama Interface

This module provides a consolidated interface that combines the functionality
of OllamaModelAdapter and OllamaAdapter, providing both ModelInterface
implementation and direct API access in a single, optimized component.

Key Features:
- Consolidated adapter functionality from multiple layers
- Full ModelInterface implementation with tool integration
- Direct Ollama API access via HTTP and Python client
- Streaming support with thread-safe callbacks
- Async and sync operation modes
- Comprehensive error handling and recovery
- Performance optimizations and reduced overhead
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

# Optional aiohttp import for HTTP fallback
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from ..tools.abstraction.model_interface import (
    ModelInterface,
    ModelRequest,
    ModelResponse,
    ModelCapabilities
)
from .ollama_wrapper import OllamaWrapper, OllamaStatus, GenerationResponse

logger = logging.getLogger(__name__)


class UnifiedOllamaInterface(ModelInterface):
    """
    Unified interface that consolidates OllamaModelAdapter and OllamaAdapter
    functionality
    
    This class provides a single, optimized interface for Ollama interactions:
    - Implements the ModelInterface for tool integration
    - Provides direct API access capabilities
    - Supports both HTTP client and Python library approaches
    - Optimizes performance through intelligent method selection
    - Maintains thread safety and signal compatibility
    """
    
    def __init__(self, 
                 ollama_wrapper: Optional[OllamaWrapper] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified Ollama interface
        
        Args:
            ollama_wrapper: Optional existing OllamaWrapper instance
            config: Configuration dictionary
        """
        super().__init__(config or {})
        
        # Initialize core wrapper
        if ollama_wrapper:
            self.ollama_wrapper = ollama_wrapper
        else:
            # Create wrapper with configuration
            host = self.config.get('host', 'http://localhost:11434')
            timeout = self.config.get('timeout', 300)
            self.ollama_wrapper = OllamaWrapper(host=host, timeout=timeout)
        
        # HTTP session for direct API access
        if AIOHTTP_AVAILABLE:
            self._http_session = None
        else:
            self._http_session = None
        self._use_http_fallback = self.config.get('use_http_fallback', True)
        
        # Tool integration
        self._available_tools: List[Dict[str, Any]] = []
        self._tool_execution_callback: Optional[Callable] = None
        
        # Performance optimization flags
        http_streaming = self.config.get('prefer_http_streaming', False)
        self._prefer_http_for_streaming = http_streaming
        self._batch_size = self.config.get('batch_size', 1)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Define capabilities
        self._capabilities = [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING,
            ModelCapabilities.CODE_GENERATION,
            ModelCapabilities.REASONING,
            ModelCapabilities.TOOL_USE,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.CONTEXT_WINDOW_32K,
        ]
        
        # Connection state
        self._connection_validated = False
        self._last_health_check = 0
        self._health_check_interval = 30  # seconds

    async def initialize(self) -> bool:
        """Initialize the unified interface"""
        try:
            # Initialize HTTP session
            if self._use_http_fallback:
                await self._initialize_http_session()
            
            # Validate Ollama service
            if not await self._validate_service():
                logger.error("Ollama service validation failed")
                return False
            
            # Test connectivity
            if not await self._test_connectivity():
                msg = ("Connectivity test failed, but proceeding with "
                       "initialization")
                logger.warning(msg)
            
            self._is_initialized = True
            self._connection_validated = True
            self._last_health_check = time.time()
            
            logger.info("UnifiedOllamaInterface initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize UnifiedOllamaInterface: {e}")
            return False

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response using the most appropriate method"""
        if not self._is_initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Interface not initialized"
            )
        
        if not self.validate_request(request):
            return ModelResponse(
                content="",
                success=False,
                error="Invalid request for model capabilities"
            )
        
        # Check service health periodically
        await self._check_service_health()
        
        try:
            # Choose optimal generation method
            if request.stream:
                return await self.stream_generate(request, lambda x: None)
            
            # For non-streaming, prefer wrapper method for consistency
            start_time = datetime.now()
            
            # Convert request to wrapper format
            wrapper_params = self._convert_request_to_wrapper(request)
            
            # Add tool context if tools are provided
            if request.tools:
                wrapper_params = self._add_tools_to_wrapper_request(
                    wrapper_params, request.tools
                )
            
            # Generate using wrapper
            has_messages = request.messages
            has_context = len(self.ollama_wrapper.get_chat_context()) > 0
            
            if has_messages or has_context:
                # Use chat mode
                if isinstance(wrapper_params.get('messages'), str):
                    # Single message
                    msg_params = {
                        k: v for k, v in wrapper_params.items()
                        if k != 'messages'
                    }
                    response = await self._safe_wrapper_call(
                        self.ollama_wrapper.chat,
                        wrapper_params['messages'],
                        **msg_params
                    )
                else:
                    # Message list
                    msg_params = {
                        k: v for k, v in wrapper_params.items()
                        if k != 'messages'
                    }
                    response = await self._safe_wrapper_call(
                        self.ollama_wrapper.chat,
                        wrapper_params.get('messages', request.prompt),
                        **msg_params
                    )
            else:
                # Use generate mode
                gen_params = {
                    k: v for k, v in wrapper_params.items()
                    if k != 'prompt'
                }
                response = await self._safe_wrapper_call(
                    self.ollama_wrapper.generate,
                    wrapper_params.get('prompt', request.prompt),
                    **gen_params
                )
            
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()
            
            # Convert wrapper response to ModelResponse
            return self._convert_wrapper_response(response, generation_time)
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            
            # Try HTTP fallback if enabled
            if self._use_http_fallback and self._http_session:
                try:
                    return await self._generate_via_http(request)
                except Exception as fallback_error:
                    logger.error(
                        f"HTTP fallback also failed: {fallback_error}"
                    )
            
            return ModelResponse(
                content="",
                success=False,
                error=f"Generation failed: {str(e)}"
            )

    async def stream_generate(
        self, 
        request: ModelRequest,
        callback: Callable[[str], None]
    ) -> ModelResponse:
        """Generate a streaming response"""
        if not self._is_initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Interface not initialized"
            )
        
        try:
            start_time = datetime.now()
            full_content = []
            
            # Choose streaming method based on configuration and availability
            use_http = (
                self._prefer_http_for_streaming and
                self._http_session and
                await self._is_http_available()
            )
            
            if use_http:
                # Use HTTP streaming
                async for chunk in self._stream_via_http(request):
                    content = chunk.get('content', '')
                    if content:
                        full_content.append(content)
                        callback(content)
            else:
                # Use wrapper streaming with thread safety
                wrapper_params = self._convert_request_to_wrapper(request)
                
                if request.tools:
                    wrapper_params = self._add_tools_to_wrapper_request(
                        wrapper_params, request.tools
                    )
                
                # Use thread-safe streaming
                await self._stream_via_wrapper(
                    wrapper_params, callback, full_content
                )
            
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()
            
            final_content = "".join(full_content)
            tool_calls = self._extract_tool_calls(final_content)
            
            streaming_method = "http" if use_http else "wrapper"
            return ModelResponse(
                content=final_content,
                success=True,
                tool_calls=tool_calls,
                usage={"generation_time": int(generation_time * 1000)},  # ms
                model=self.ollama_wrapper.get_current_model(),
                metadata={"streaming": True, "method": streaming_method}
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
        """Check if the interface is available"""
        try:
            return (
                self._is_initialized and
                self.ollama_wrapper.check_service() == OllamaStatus.READY
            )
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get comprehensive model information"""
        info = {
            "adapter": "UnifiedOllamaInterface",
            "initialized": self._is_initialized,
            "capabilities": [cap.name for cap in self._capabilities],
            "available_tools": len(self._available_tools),
            "http_session_active": self._http_session is not None,
            "connection_validated": self._connection_validated
        }
        
        try:
            # Get wrapper status
            wrapper_status = self.ollama_wrapper.get_status()
            info.update({
                "service_status": wrapper_status.get("service_status"),
                "current_model": wrapper_status.get("current_model"),
                "available_models": wrapper_status.get("available_models", []),
                "host": wrapper_status.get("host")
            })
            
        except Exception as e:
            info["status_error"] = str(e)
        
        return info

    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set available tools"""
        with self._lock:
            self._available_tools = tools
            logger.info(f"Set {len(tools)} tools for UnifiedOllamaInterface")

    def set_tool_execution_callback(self, callback: Callable):
        """Set tool execution callback"""
        self._tool_execution_callback = callback

    async def shutdown(self):
        """Shutdown the interface"""
        try:
            if self._http_session:
                await self._http_session.close()
                self._http_session = None
            
            # OllamaWrapper doesn't have shutdown method
            pass
            
            self._is_initialized = False
            logger.info("UnifiedOllamaInterface shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    # Private helper methods

    async def _initialize_http_session(self):
        """Initialize HTTP session for direct API access"""
        if not AIOHTTP_AVAILABLE or not aiohttp:
            logger.warning("aiohttp not available - HTTP fallback disabled")
            return
            
        try:
            timeout_val = self.config.get('timeout', 300)
            timeout = aiohttp.ClientTimeout(total=timeout_val)
            self._http_session = aiohttp.ClientSession(timeout=timeout)
            logger.debug("HTTP session initialized for direct API access")
        except Exception as e:
            logger.warning(f"Failed to initialize HTTP session: {e}")

    async def _validate_service(self) -> bool:
        """Validate Ollama service availability"""
        try:
            # Try wrapper first
            status = self.ollama_wrapper.check_service()
            if status == OllamaStatus.READY:
                return True
            
            # Try HTTP fallback
            if self._http_session:
                return await self._is_http_available()
            
            return False
            
        except Exception as e:
            logger.error(f"Service validation failed: {e}")
            return False

    async def _test_connectivity(self) -> bool:
        """Test connectivity with a simple request"""
        try:
            # Try to list models as a connectivity test
            models = self.ollama_wrapper.list_models()
            return len(models) >= 0  # Even 0 models is a successful connection
            
        except Exception as e:
            logger.warning(f"Connectivity test failed: {e}")
            return False

    async def _check_service_health(self):
        """Periodically check service health"""
        current_time = time.time()
        time_diff = current_time - self._last_health_check
        interval_exceeded = time_diff > self._health_check_interval
        
        if interval_exceeded:
            try:
                is_healthy = await self._validate_service()
                if not is_healthy and self._connection_validated:
                    logger.warning(
                        "Service health check failed - connection may be lost"
                    )
                    self._connection_validated = False
                elif is_healthy and not self._connection_validated:
                    logger.info("Service health restored")
                    self._connection_validated = True
                
                self._last_health_check = current_time
                
            except Exception as e:
                logger.warning(f"Health check error: {e}")

    async def _is_http_available(self) -> bool:
        """Check if HTTP API is available"""
        if not self._http_session:
            return False
        
        try:
            base_url = self.ollama_wrapper._host
            url = f"{base_url}/api/tags"
            async with self._http_session.get(url) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def _safe_wrapper_call(self, method, *args, **kwargs):
        """Safely call wrapper method with async conversion"""
        try:
            # Run wrapper method in thread since it's synchronous
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, lambda: method(*args, **kwargs)
            )
        except Exception as e:
            logger.error(f"Wrapper call failed: {e}")
            raise

    def _convert_request_to_wrapper(
        self, request: ModelRequest
    ) -> Dict[str, Any]:
        """Convert ModelRequest to wrapper parameters"""
        params = {}
        
        # Basic parameters
        if request.temperature is not None:
            params['temperature'] = request.temperature
        if request.top_p is not None:
            params['top_p'] = request.top_p
        if request.max_tokens is not None:
            params['max_tokens'] = request.max_tokens
        
        # Handle messages vs prompt
        if request.messages:
            params['messages'] = request.messages
            if request.prompt:
                # Append current prompt as user message
                user_msg = {"role": "user", "content": request.prompt}
                params['messages'].append(user_msg)
        else:
            params['prompt'] = request.prompt
            
        # System prompt
        if request.system_prompt:
            params['system_prompt'] = request.system_prompt
        
        # Model selection - ModelRequest doesn't have model attribute
        # This would be handled by the wrapper's current model setting
        
        return params

    def _generate_tool_descriptions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate structured tool descriptions for AI model context
        
        Args:
            tools: List of tool definitions
            
        Returns:
            List of formatted tool descriptions
        """
        formatted_tools = []
        
        for tool in tools:
            tool_name = tool.get('name', 'unknown_tool')
            description = tool.get('description', 'No description available')
            
            # Extract parameters with proper typing
            parameters = {}
            returns_info = "mixed"
            
            if 'parameters' in tool:
                schema = tool['parameters']
                properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                for param_name, param_info in properties.items():
                    param_type = param_info.get('type', 'any')
                    param_desc = param_info.get('description', '')
                    is_required = param_name in required
                    
                    # Format parameter with type and requirement info
                    if is_required:
                        param_display = f"{param_type} (required)"
                    else:
                        param_display = f"{param_type} (optional)"
                    
                    if param_desc:
                        param_display += f" - {param_desc}"
                    
                    parameters[param_name] = param_display
            
            # Check for return type information
            if 'returns' in tool:
                returns_info = tool['returns']
            
            formatted_tool = {
                "name": tool_name,
                "description": description,
                "parameters": parameters,
                "returns": returns_info
            }
            
            formatted_tools.append(formatted_tool)
        
        return formatted_tools

    def _create_tool_system_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """
        Create comprehensive system prompt with tool information
        
        Args:
            tools: List of tool definitions
            
        Returns:
            Formatted system prompt with tool context
        """
        if not tools:
            return ""
        
        tool_descriptions = self._generate_tool_descriptions(tools)
        
        # Build tool listing
        tool_list = []
        for i, tool in enumerate(tool_descriptions, 1):
            tool_entry = f"{i}. **{tool['name']}**: {tool['description']}"
            
            if tool['parameters']:
                params_list = []
                for param_name, param_info in tool['parameters'].items():
                    params_list.append(f"{param_name} ({param_info})")
                
                if params_list:
                    params_str = ", ".join(params_list)
                    tool_entry += f"\n   Parameters: {params_str}"
            
            if tool['returns'] != "mixed":
                tool_entry += f"\n   Returns: {tool['returns']}"
            
            tool_list.append(tool_entry)
        
        tools_section = "\n\n".join(tool_list)
        
        # Create comprehensive system prompt
        system_prompt = f"""You are a smart assistant with access to external tools. Here are the tools you can use:

{tools_section}

TOOL USAGE INSTRUCTIONS:
You can respond in two ways:
1. Direct answer: Provide a direct response when no tools are needed
2. Tool call: Use tools when they can help accomplish the user's request

To call a tool, respond with JSON in this EXACT format:
{{
  "tool": "<tool_name>",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}

IMPORTANT RULES:
- Use tools when they can provide accurate, helpful information
- Always choose the most appropriate tool for the task
- Provide clear explanations of what you're doing
- When using tools, respond ONLY with the JSON format above
- Do not add extra text when making tool calls
- After receiving tool results, provide a comprehensive response to the user

EXAMPLES:
User: "What time is it?"
Response: {{"tool": "get_current_time", "parameters": {{}}}}

User: "Add 15 and 27"
Response: {{"tool": "add_two_numbers", "parameters": {{"a": 15, "b": 27}}}}

User: "List files in the current directory"
Response: {{"tool": "list_directory_contents", "parameters": {{"path": "."}}}}"""

        return system_prompt

    def _add_tools_to_wrapper_request(
        self,
        params: Dict[str, Any],
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add comprehensive tool information to wrapper request"""
        if not tools:
            return params
        
        # Generate comprehensive tool context
        tool_context = self._create_tool_system_prompt(tools)
        
        # Add tool context to system prompt
        if 'system_prompt' in params and params['system_prompt']:
            # Prepend tool context to existing system prompt
            current_prompt = params['system_prompt']
            params['system_prompt'] = f"{tool_context}\n\n---\n\nADDITIONAL CONTEXT:\n{current_prompt}"
        else:
            params['system_prompt'] = tool_context
        
        # Log tool context injection for debugging
        tool_names = [tool.get('name', 'unknown') for tool in tools]
        logger.info(f"Injected tool context for {len(tools)} tools: {tool_names}")
        
        return params

    def _convert_wrapper_response(
        self, 
        response: GenerationResponse, 
        generation_time: float
    ) -> ModelResponse:
        """Convert wrapper response to ModelResponse"""
        if isinstance(response, GenerationResponse):
            tool_calls = self._extract_tool_calls(response.content)
            
            # Convert usage to proper format
            usage_info = {}
            if response.tokens_generated:
                usage_info["tokens_generated"] = int(response.tokens_generated)
            usage_info["generation_time"] = int(generation_time * 1000)  # ms
            
            return ModelResponse(
                content=response.content,
                success=response.success,
                error=response.error,
                tool_calls=tool_calls,
                model=response.model,
                usage=usage_info,
                metadata=response.metadata or {}
            )
        else:
            # Handle dict response
            if isinstance(response, dict):
                content = response.get("response", "")
            else:
                content = str(response)
            tool_calls = self._extract_tool_calls(content)
            
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                usage={"generation_time": int(generation_time * 1000)}  # ms
            )

    async def _stream_via_wrapper(
        self, 
        params: Dict[str, Any], 
        callback: Callable[[str], None],
        full_content: List[str]
    ):
        """Stream via wrapper with thread safety"""
        def sync_stream():
            try:
                if 'messages' in params:
                    # Chat streaming
                    for chunk in self.ollama_wrapper.stream_chat(
                        params['messages'], 
                        **{k: v for k, v in params.items() if k != 'messages'}
                    ):
                        if chunk:
                            full_content.append(chunk)
                            callback(chunk)
                else:
                    # Generate streaming
                    for chunk in self.ollama_wrapper.stream_generate(
                        params['prompt'],
                        **{k: v for k, v in params.items() if k != 'prompt'}
                    ):
                        if chunk:
                            full_content.append(chunk)
                            callback(chunk)
            except Exception as e:
                logger.error(f"Wrapper streaming failed: {e}")
        
        # Run in thread
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sync_stream)

    async def _generate_via_http(self, request: ModelRequest) -> ModelResponse:
        """Generate response via HTTP API as fallback"""
        if not self._http_session:
            raise RuntimeError("HTTP session not available")
        
        # Prepare HTTP request
        base_url = self.ollama_wrapper._host
        url = f"{base_url}/api/generate"
        
        # Convert request to Ollama API format
        data = {
            "model": self.ollama_wrapper.get_current_model(),
            "prompt": request.prompt,
            "stream": False
        }
        
        if request.system_prompt:
            sys_prompt = request.system_prompt
            user_prompt = request.prompt
            data["prompt"] = f"System: {sys_prompt}\n\nUser: {user_prompt}"
        
        # Add options
        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        
        if options:
            data["options"] = options
        
        async with self._http_session.post(url, json=data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"HTTP API error: {error_text}")
            
            response_data = await resp.json()
            content = response_data.get("response", "")
            tool_calls = self._extract_tool_calls(content)
            
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                model=response_data.get("model"),
                metadata={"method": "http_fallback"}
            )

    async def _stream_via_http(
        self, request: ModelRequest
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream response via HTTP API"""
        if not self._http_session:
            raise RuntimeError("HTTP session not available")
        
        base_url = self.ollama_wrapper._host
        url = f"{base_url}/api/generate"
        
        data = {
            "model": self.ollama_wrapper.get_current_model(),
            "prompt": request.prompt,
            "stream": True
        }
        
        async with self._http_session.post(url, json=data) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise RuntimeError(f"HTTP streaming error: {error_text}")
            
            async for line in resp.content:
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield {"content": data["response"]}
                    except json.JSONDecodeError:
                        continue

    def _extract_tool_calls(
        self, content: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Extract tool calls from model response with enhanced parsing
        
        Supports multiple formats:
        - New format: {"tool": "tool_name", "parameters": {...}}
        - Legacy format: {"tool_call": {"name": "tool_name", "parameters": {...}}}
        """
        if not content:
            return None
        
        tool_calls = []
        
        try:
            # Find JSON patterns in the content
            brace_count = 0
            start_pos = -1
            
            for i, char in enumerate(content):
                if char == '{':
                    if brace_count == 0:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        json_candidate = content[start_pos:i+1]
                        
                        # Look for tool indicators
                        has_tool_indicators = (
                            '"tool"' in json_candidate or
                            '"tool_call"' in json_candidate
                        )
                        
                        if has_tool_indicators:
                            try:
                                parsed = json.loads(json_candidate)
                                if not isinstance(parsed, dict):
                                    continue
                                
                                # Handle new format: {"tool": "name", "parameters": {...}}
                                if "tool" in parsed and isinstance(parsed["tool"], str):
                                    tool_name = parsed["tool"]
                                    parameters = parsed.get("parameters", {})
                                    
                                    if tool_name:  # Ensure tool name is not empty
                                        tool_calls.append({
                                            "name": tool_name,
                                            "parameters": parameters if isinstance(parameters, dict) else {}
                                        })
                                        logger.debug(f"Parsed tool call: {tool_name} with parameters: {parameters}")
                                
                                # Handle legacy format: {"tool_call": {"name": "...", "parameters": {...}}}
                                elif "tool_call" in parsed:
                                    tool_call = parsed["tool_call"]
                                    if isinstance(tool_call, dict) and "name" in tool_call:
                                        tool_name = tool_call["name"]
                                        parameters = tool_call.get("parameters", {})
                                        
                                        if tool_name:
                                            tool_calls.append({
                                                "name": tool_name,
                                                "parameters": parameters if isinstance(parameters, dict) else {}
                                            })
                                            logger.debug(f"Parsed legacy tool call: {tool_name}")
                                
                            except json.JSONDecodeError as e:
                                logger.debug(f"Failed to parse JSON candidate: {json_candidate[:50]}... Error: {e}")
                                continue
                        
                        # Reset for next potential JSON
                        start_pos = -1
            
            # Also try to parse the entire content as JSON (in case it's a pure JSON response)
            if not tool_calls:
                try:
                    parsed = json.loads(content.strip())
                    if isinstance(parsed, dict):
                        # Check for direct tool format
                        if "tool" in parsed and isinstance(parsed["tool"], str):
                            tool_name = parsed["tool"]
                            parameters = parsed.get("parameters", {})
                            
                            if tool_name:
                                tool_calls.append({
                                    "name": tool_name,
                                    "parameters": parameters if isinstance(parameters, dict) else {}
                                })
                                logger.debug(f"Parsed full JSON tool call: {tool_name}")
                
                except json.JSONDecodeError:
                    # Content is not pure JSON, that's fine
                    pass
            
        except Exception as e:
            logger.warning(f"Error extracting tool calls: {e}")
        
        if tool_calls:
            logger.info(f"Successfully extracted {len(tool_calls)} tool calls")
        
        return tool_calls if tool_calls else None