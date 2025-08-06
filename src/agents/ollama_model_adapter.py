"""
Ollama Model Adapter

This module provides an adapter that wraps the OllamaWrapper to implement
the ModelInterface, enabling tool integration and standardized model interactions.
"""

import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime

from ..tools.abstraction.model_interface import (
    ModelInterface,
    ModelRequest,
    ModelResponse,
    ModelCapabilities,
    StandardModelAdapter
)
from .ollama_wrapper import OllamaWrapper, OllamaStatus, GenerationResponse

logger = logging.getLogger(__name__)


class OllamaModelAdapter(ModelInterface):
    """
    Model adapter that wraps OllamaWrapper to implement ModelInterface
    
    This adapter enables the OllamaWrapper to work with the tool system
    and provides a standardized interface for AI model interactions.
    """
    
    def __init__(self, 
                 ollama_wrapper: Optional[OllamaWrapper] = None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Ollama model adapter
        
        Args:
            ollama_wrapper: Optional existing OllamaWrapper instance
            config: Model configuration
        """
        super().__init__(config)
        
        # Create or use provided wrapper
        if ollama_wrapper:
            self.ollama = ollama_wrapper
        else:
            # Extract connection settings from config
            host = self.config.get('host', 'http://localhost:11434')
            timeout = self.config.get('timeout', 300)
            self.ollama = OllamaWrapper(host=host, timeout=timeout)
        
        # Set model capabilities
        self._capabilities = [
            ModelCapabilities.TEXT_GENERATION,
            ModelCapabilities.STREAMING,
            ModelCapabilities.CODE_GENERATION,
            ModelCapabilities.REASONING,
            ModelCapabilities.TOOL_USE,
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.CONTEXT_WINDOW_32K,  # Most Ollama models support this
        ]
        
        # Tool-related state
        self._available_tools: List[Dict[str, Any]] = []
        self._tool_execution_callback: Optional[Callable] = None
        
    async def initialize(self) -> bool:
        """Initialize the Ollama connection"""
        try:
            # Check service status
            status = self.ollama.check_service()
            if status != OllamaStatus.READY:
                logger.error(f"Ollama service not ready: {status}")
                return False
            
            # Verify we have models available
            models = self.ollama.list_models()
            if not models:
                logger.warning("No models available in Ollama")
                # Don't fail initialization - user might pull models later
            
            self._is_initialized = True
            logger.info("OllamaModelAdapter initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OllamaModelAdapter: {e}")
            return False
    
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response using Ollama"""
        if not self._is_initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Model adapter not initialized"
            )
        
        if not self.validate_request(request):
            return ModelResponse(
                content="",
                success=False,
                error="Invalid request for model capabilities"
            )
        
        try:
            # Convert ModelRequest to Ollama format
            ollama_request = self._convert_request_to_ollama(request)
            
            # Add tool information if tools are provided
            if request.tools:
                ollama_request = self._add_tools_to_request(ollama_request, request.tools)
            
            # Generate response
            start_time = datetime.now()
            
            if request.stream:
                # Handle streaming in the stream_generate method instead
                return await self.stream_generate(request, lambda x: None)
            else:
                # Non-streaming generation
                if 'messages' in ollama_request:
                    # Chat mode
                    if hasattr(self.ollama, 'chat_async'):
                        response = await self.ollama.chat_async(**ollama_request)
                    else:
                        # Fallback to sync chat
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        messages = ollama_request.pop('messages')
                        response = await loop.run_in_executor(
                            None, 
                            lambda: self.ollama.chat(messages, **ollama_request)
                        )
                else:
                    # Generate mode
                    if hasattr(self.ollama, 'generate_async'):
                        response = await self.ollama.generate_async(**ollama_request)
                    else:
                        # Fallback to sync generation in thread
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        # Extract prompt as positional argument
                        prompt = ollama_request.pop('prompt', '')
                        response = await loop.run_in_executor(
                            None, 
                            lambda: self.ollama.generate(prompt, **ollama_request)
                        )
            
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()
            
            # Convert Ollama response to ModelResponse
            return self._convert_response_from_ollama(response, generation_time)
            
        except ConnectionError as e:
            logger.error(f"Generation failed - Ollama service unavailable: {e}")
            return ModelResponse(
                content="",
                success=False,
                error="Ollama service is not available. Please ensure Ollama is running."
            )
        except TimeoutError as e:
            logger.error(f"Generation failed - timeout: {e}")
            return ModelResponse(
                content="",
                success=False,
                error="Request timed out. The model may be too large or busy."
            )
        except ValueError as e:
            logger.error(f"Generation failed - invalid parameters: {e}")
            return ModelResponse(
                content="",
                success=False,
                error=f"Invalid request parameters: {e}"
            )
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            return ModelResponse(
                content="",
                success=False,
                error=f"Unexpected generation error: {str(e)}"
            )
    
    async def stream_generate(
        self, 
        request: ModelRequest,
        callback: Callable[[str], None]
    ) -> ModelResponse:
        """Generate a streaming response using Ollama"""
        if not self._is_initialized:
            return ModelResponse(
                content="",
                success=False,
                error="Model adapter not initialized"
            )
        
        try:
            # Convert request
            ollama_request = self._convert_request_to_ollama(request)
            ollama_request['stream'] = True
            
            # Add tool information if tools are provided
            if request.tools:
                ollama_request = self._add_tools_to_request(ollama_request, request.tools)
            
            # Stream generation
            full_content = []
            start_time = datetime.now()
            
            # Check if this is chat mode (has messages) or generate mode (has prompt)
            if 'messages' in ollama_request:
                # Chat mode - use stream_chat
                if hasattr(self.ollama, 'stream_chat_async'):
                    async for chunk in self.ollama.stream_chat_async(**ollama_request):
                        content = self._extract_chunk_content(chunk)
                        if content:
                            full_content.append(content)
                            callback(content)
                else:
                    # Fallback to sync chat streaming - run in thread but call callback directly
                    import threading
                    
                    def sync_stream():
                        try:
                            messages = ollama_request.pop('messages')
                            logger.info(f"[OllamaModelAdapter] Starting sync chat streaming with {len(messages)} messages")
                            for i, chunk in enumerate(self.ollama.stream_chat(messages, **ollama_request)):
                                content = self._extract_chunk_content(chunk)
                                if content:
                                    full_content.append(content)
                                    logger.debug(f"[OllamaModelAdapter] Streaming chunk {i}: '{content[:20]}...'")
                                    # Call callback immediately during streaming
                                    try:
                                        callback(content)
                                    except Exception as e:
                                        logger.warning(f"Stream callback failed: {e}")
                            logger.info(f"[OllamaModelAdapter] Sync chat streaming complete, {len(full_content)} chunks")
                        except Exception as e:
                            logger.error(f"Sync streaming failed: {e}")
                    
                    # Run in thread and wait for completion
                    thread = threading.Thread(target=sync_stream, daemon=True)
                    thread.start()
                    thread.join()  # Wait for streaming to complete
            else:
                # Generate mode - use stream_generate
                if hasattr(self.ollama, 'stream_generate_async'):
                    # Extract prompt as positional argument
                    prompt = ollama_request.pop('prompt', '')
                    async for chunk in self.ollama.stream_generate_async(prompt, **ollama_request):
                        content = self._extract_chunk_content(chunk)
                        if content:
                            full_content.append(content)
                            callback(content)
                else:
                    # Fallback to sync streaming - run in thread but call callback directly
                    import threading
                    
                    def sync_stream():
                        try:
                            # Extract prompt as positional argument
                            prompt = ollama_request.pop('prompt', '')
                            logger.info(f"[OllamaModelAdapter] Starting sync generate streaming with prompt: '{prompt[:50]}...'")
                            for i, chunk in enumerate(self.ollama.stream_generate(prompt, **ollama_request)):
                                content = self._extract_chunk_content(chunk)
                                if content:
                                    full_content.append(content)
                                    logger.debug(f"[OllamaModelAdapter] Streaming chunk {i}: '{content[:20]}...'")
                                    # Call callback immediately during streaming
                                    try:
                                        callback(content)
                                    except Exception as e:
                                        logger.warning(f"Stream callback failed: {e}")
                            logger.info(f"[OllamaModelAdapter] Sync generate streaming complete, {len(full_content)} chunks")
                        except Exception as e:
                            logger.error(f"Sync streaming failed: {e}")
                
                    # Run in thread and wait for completion
                    thread = threading.Thread(target=sync_stream, daemon=True)
                    thread.start()
                    thread.join()  # Wait for streaming to complete
            
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()
            
            final_content = "".join(full_content)
            
            # Check for tool calls in the response
            tool_calls = self._extract_tool_calls(final_content)
            
            return ModelResponse(
                content=final_content,
                success=True,
                tool_calls=tool_calls,
                usage={"generation_time": generation_time},
                model=self.ollama.get_current_model(),
                metadata={"streaming": True}
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
        """Check if Ollama service is available"""
        try:
            return self.ollama.check_service() == OllamaStatus.READY
        except Exception:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = {
            "adapter": "OllamaModelAdapter",
            "initialized": self._is_initialized,
            "capabilities": [cap.name for cap in self._capabilities],
            "service_status": self.ollama.check_service().value,
            "available_tools": len(self._available_tools)
        }
        
        try:
            # Get current model info
            current_model = self.ollama.get_current_model()
            if current_model:
                info["current_model"] = current_model
                
            # Get available models
            models = self.ollama.list_models()
            info["available_models"] = [
                {"name": model.name, "size": model.size} 
                for model in models
            ]
            
            # Get service info
            info["ollama_host"] = getattr(self.ollama, 'host', 'unknown')
            
        except Exception as e:
            info["info_error"] = str(e)
        
        return info
    
    def set_tools(self, tools: List[Dict[str, Any]]):
        """Set available tools for the model"""
        self._available_tools = tools
        logger.info(f"Set {len(tools)} tools for OllamaModelAdapter")
    
    def set_tool_execution_callback(self, callback: Callable):
        """Set callback for tool execution"""
        self._tool_execution_callback = callback
    
    def _convert_request_to_ollama(self, request: ModelRequest) -> Dict[str, Any]:
        """Convert ModelRequest to Ollama API format"""
        ollama_request = {
            "stream": request.stream,
        }
        
        # Add generation parameters
        options = {}
        if request.temperature is not None:
            options["temperature"] = float(request.temperature)
        if request.top_p is not None:
            options["top_p"] = float(request.top_p)
        if request.max_tokens is not None:
            options["num_predict"] = int(request.max_tokens)
        if request.stop_sequences:
            options["stop"] = request.stop_sequences
        
        if options:
            ollama_request["options"] = options
        
        # Handle messages format (for chat)
        if request.messages:
            # Convert to Ollama chat format
            messages = request.messages.copy()
            
            # If there's a current prompt, append it as a user message
            if request.prompt:
                messages.append({
                    "role": "user",
                    "content": request.prompt
                })
            
            ollama_request["messages"] = messages
        else:
            # Generate mode - use prompt
            prompt = request.prompt
            
            # Add system prompt if provided
            if request.system_prompt:
                prompt = f"System: {request.system_prompt}\n\nUser: {prompt}"
            
            ollama_request["prompt"] = prompt
        
        return ollama_request
    
    def _add_tools_to_request(
        self, 
        ollama_request: Dict[str, Any], 
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add tool information to the Ollama request"""
        # For Ollama, we add tool information to the system prompt
        tool_descriptions = []
        for tool in tools:
            name = tool['name']
            desc = tool.get('description', 'No description')
            tool_desc = f"- **{name}**: {desc}"
            
            if 'parameters' in tool:
                params = tool['parameters'].get('properties', {})
                required = tool['parameters'].get('required', [])
                
                if params:
                    param_details = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        required_marker = ' (required)' if param_name in required else ' (optional)'
                        param_details.append(f"{param_name}: {param_type}{required_marker} - {param_desc}")
                    
                    if param_details:
                        tool_desc += f"\n  Parameters: {', '.join(param_details)}"
            
            # Add usage example if available
            if 'examples' in tool and tool['examples']:
                example = tool['examples'][0]
                if 'parameters' in example:
                    tool_desc += f"\n  Example: {json.dumps(example['parameters'])}"
                    
            tool_descriptions.append(tool_desc)
        
        tools_text = "\n".join(tool_descriptions)
        
        # Add tools context to the prompt
        if "messages" in ollama_request:
            # Add system message with tools
            system_msg = {
                "role": "system",
                "content": f"""You are a helpful AI assistant with access to powerful tools that can help you complete various tasks. Available tools:

{tools_text}

IMPORTANT TOOL USAGE INSTRUCTIONS:
- When a user asks for something that would benefit from using tools, identify which tools could help
- Use tools by responding with JSON in this EXACT format: {{"tool_call": {{"name": "tool_name", "parameters": {{"param1": "value1", "param2": "value2"}}}}}}
- You can use multiple tools in sequence if needed
- Always explain what you're doing when using tools
- Provide clear, helpful responses based on tool results
- You can also respond normally without using tools when appropriate

Examples of when to use tools:
- File operations: Use file_tool for reading/writing files, listing directories
- Math calculations: Use math_tool for complex calculations
- System information: Use system_info_tool to check system status
- Text processing: Use echo_tool for text transformations"""
            }
            
            # Insert system message at the beginning
            if ollama_request["messages"] and ollama_request["messages"][0]["role"] == "system":
                # Merge with existing system message
                ollama_request["messages"][0]["content"] += f"\n\n{system_msg['content']}"
            else:
                ollama_request["messages"].insert(0, system_msg)
        else:
            # Add to prompt
            tools_context = f"""You are a helpful AI assistant with access to powerful tools. Available tools:
{tools_text}

TOOL USAGE: When appropriate, use tools by responding with JSON in this format:
{{"tool_call": {{"name": "tool_name", "parameters": {{"param1": "value1"}}}}}}

Always explain what you're doing and provide helpful responses based on tool results.

"""
            ollama_request["prompt"] = tools_context + ollama_request["prompt"]
        
        return ollama_request
    
    def _convert_response_from_ollama(
        self, 
        ollama_response: Union[GenerationResponse, Dict[str, Any]], 
        generation_time: float
    ) -> ModelResponse:
        """Convert Ollama response to ModelResponse"""
        if isinstance(ollama_response, GenerationResponse):
            # Handle our custom GenerationResponse
            tool_calls = self._extract_tool_calls(ollama_response.content)
            
            return ModelResponse(
                content=ollama_response.content,
                success=ollama_response.success,
                error=ollama_response.error,
                tool_calls=tool_calls,
                model=ollama_response.model,
                usage={
                    "tokens_generated": ollama_response.tokens_generated,
                    "generation_time": generation_time
                },
                metadata=ollama_response.metadata or {}
            )
        elif isinstance(ollama_response, dict):
            # Handle raw Ollama API response
            content = ollama_response.get("response", "")
            tool_calls = self._extract_tool_calls(content)
            
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                model=ollama_response.get("model"),
                usage={
                    "generation_time": generation_time,
                    "total_duration": ollama_response.get("total_duration"),
                    "prompt_eval_count": ollama_response.get("prompt_eval_count"),
                    "eval_count": ollama_response.get("eval_count")
                },
                metadata={"ollama_response": ollama_response}
            )
        else:
            # Fallback for other response types
            content = str(ollama_response)
            tool_calls = self._extract_tool_calls(content)
            
            return ModelResponse(
                content=content,
                success=True,
                tool_calls=tool_calls,
                usage={"generation_time": generation_time}
            )
    
    def _extract_chunk_content(self, chunk: Any) -> str:
        """Extract content from a streaming chunk"""
        if isinstance(chunk, str):
            return chunk
        elif isinstance(chunk, dict):
            return chunk.get("response", "")
        elif hasattr(chunk, 'content'):
            return getattr(chunk, 'content', '')
        elif hasattr(chunk, 'response'):
            return getattr(chunk, 'response', '')
        return str(chunk)
    
    def _extract_tool_calls(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from model response"""
        if not content:
            return None
        
        tool_calls = []
        
        # Look for JSON tool call patterns - use simpler, safer approach
        import re
        
        try:
            # Look for any JSON-like structure containing "tool_call"
            # Use a more robust approach to find JSON blocks
            json_blocks = []
            
            # Find potential JSON blocks (balanced braces)
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
                        if '"tool_call"' in json_candidate:
                            json_blocks.append(json_candidate)
            
            # Parse each JSON block
            for json_str in json_blocks:
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, dict) and "tool_call" in parsed:
                        tool_call = parsed["tool_call"]
                        if isinstance(tool_call, dict) and "name" in tool_call:
                            tool_calls.append({
                                "name": tool_call["name"],
                                "parameters": tool_call.get("parameters", {})
                            })
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"Error parsing tool call JSON: {e}")
                    continue
            
        except Exception as e:
            logger.warning(f"Error in tool call extraction: {e}")
        
        return tool_calls if tool_calls else None
    
    async def shutdown(self):
        """Shutdown the adapter"""
        try:
            if hasattr(self.ollama, 'shutdown'):
                await self.ollama.shutdown()
            self._is_initialized = False
            logger.info("OllamaModelAdapter shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")