"""
Ollama Agent

This module provides a concrete agent implementation that combines
OllamaWrapper with tool integration capabilities, enabling AI-assisted
tasks with access to the full tool ecosystem.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent, AgentConfig, AgentContext
from .ollama_wrapper import OllamaWrapper, OllamaStatus
from .unified_ollama_interface import UnifiedOllamaInterface
from ..tools.abstraction.model_interface import ModelRequest, ModelResponse
from ..tools.registry import ToolRegistry
from ..tools.ai_adapter import ToolAIAdapter
from ..tools.control.tool_context import (
    ExecutionContext, UserContext, TaskContext, EnvironmentContext,
    TaskType, Environment, UserRole
)

logger = logging.getLogger(__name__)


class OllamaAgent(BaseAgent):
    """
    Ollama-powered AI agent with tool integration
    
    This agent combines the power of local Ollama models with the
    comprehensive tool system to provide AI assistance with access
    to file operations, code execution, web access, and more.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        ollama_wrapper: Optional[OllamaWrapper] = None,
        tool_registry: Optional[ToolRegistry] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize the Ollama agent
        
        Args:
            config: Agent configuration
            ollama_wrapper: Optional existing OllamaWrapper
            tool_registry: Optional tool registry
            model_name: Optional model name to use
        """
        # Create default config if not provided
        if config is None:
            config = AgentConfig(
                name="OllamaAgent",
                description="AI agent powered by local Ollama models with tool integration",
                enable_tools=True,
                enable_streaming=True,
                capabilities=["text_generation", "code_generation", "tool_use", "reasoning"]
            )
        
        # Create or use provided Ollama wrapper
        if ollama_wrapper:
            self.ollama_wrapper = ollama_wrapper
        else:
            host = config.model_config.get('host', 'http://localhost:11434')
            timeout = config.model_config.get('timeout', 300)
            self.ollama_wrapper = OllamaWrapper(host=host, timeout=timeout)
        
        # Create unified interface (consolidates OllamaModelAdapter functionality)
        model_adapter = UnifiedOllamaInterface(
            ollama_wrapper=self.ollama_wrapper,
            config=config.model_config
        )
        
        # Initialize base agent with unified interface
        super().__init__(config, model=model_adapter, tool_registry=tool_registry)
        
        # Set initial model if provided
        if model_name:
            self.set_model(model_name)
        
        # Tool execution state
        self._execution_context: Optional[ExecutionContext] = None
        self._conversation_history: List[Dict[str, str]] = []
        
    async def initialize(self) -> bool:
        """Initialize the agent and its components"""
        try:
            # Initialize the model adapter
            if not await self.model.initialize():
                logger.error("Failed to initialize Ollama model adapter")
                return False
            
            # Initialize tool adapter if enabled
            if self.tool_adapter:
                logger.info("Tool adapter available, starting tool discovery...")
                
                # Discover and register tools
                await self._discover_and_register_tools()
                
                # Set up tool integration with model
                available_tools = self.tool_adapter.get_available_tools()
                logger.info(f"Setting up model with {len(available_tools)} tools")
                
                if hasattr(self.model, 'set_tools'):
                    self.model.set_tools(available_tools)
                    logger.info("Tools set on model successfully")
                else:
                    logger.warning("Model does not have set_tools method")
                
                # Set tool execution callback
                if hasattr(self.model, 'set_tool_execution_callback'):
                    self.model.set_tool_execution_callback(self._execute_tool)
                    logger.info("Tool execution callback set on model")
                else:
                    logger.warning("Model does not have set_tool_execution_callback method")
            else:
                logger.warning("No tool adapter available - tools will not be enabled")
            
            self._is_initialized = True
            logger.info(f"OllamaAgent '{self.config.name}' initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OllamaAgent: {e}")
            return False
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        use_tools: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Have a conversation with the agent
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            context: Optional context information
            use_tools: Whether to enable tool use
            stream_callback: Optional callback for streaming responses
            
        Returns:
            Chat response with metadata
        """
        if not self._is_initialized:
            return {
                "success": False,
                "error": "Agent not initialized",
                "response": ""
            }
        
        try:
            logger.info(f"[OllamaAgent] Starting chat with message: '{message[:50]}...'")
            logger.info(f"[OllamaAgent] use_tools: {use_tools}, stream_callback: {stream_callback is not None}")
            
            # Update conversation history
            self._conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Create execution context if needed
            if use_tools and self.tool_adapter:
                execution_context = self._create_execution_context(context)
                self._execution_context = execution_context
                
                # Get available tools for this context
                available_tools = self.tool_adapter.get_available_tools(
                    context=execution_context,
                    apply_policies=True,
                    format_type="standard"
                )
                
                # Convert tools to proper format for model interface
                available_tools = self._convert_tools_to_model_format(available_tools)
            else:
                available_tools = []
            
            # Debug logging for tool availability
            if available_tools:
                tool_names = [tool.get('name', 'unnamed') for tool in available_tools]
                logger.info(f"Chat request using {len(available_tools)} tools: {tool_names}")
            else:
                logger.info("Chat request without tools")
            
            # Generate tool awareness system prompt if none provided but tools are available
            effective_system_prompt = system_prompt
            if not system_prompt and available_tools and use_tools:
                # Create tool awareness system prompt
                effective_system_prompt = self._create_tool_awareness_prompt(available_tools)
                logger.info(f"Generated tool awareness system prompt ({len(effective_system_prompt)} chars)")
            
            # Create model request
            request = ModelRequest(
                prompt=message,
                system_prompt=effective_system_prompt,
                tools=available_tools if use_tools else None,
                stream=bool(stream_callback),
                temperature=self.config.model_config.get('temperature'),
                max_tokens=self.config.model_config.get('max_tokens'),
                messages=self._get_conversation_messages(effective_system_prompt)
            )
            
            # Generate response
            logger.info(f"[OllamaAgent] Generating response with stream: {bool(stream_callback)}")
            if stream_callback:
                response = await self.model.stream_generate(request, stream_callback)
            else:
                response = await self.model.generate(request)
            logger.info(f"[OllamaAgent] Response generated successfully")
            
            # Handle tool calls if present
            final_response = response.content
            tool_results = []
            
            if response.tool_calls and use_tools:
                # Limit tool calls to prevent runaway execution
                max_tool_calls = 5  # Limit to 5 tool calls per message
                if len(response.tool_calls) > max_tool_calls:
                    logger.warning(f"Too many tool calls ({len(response.tool_calls)}), limiting to {max_tool_calls}")
                    response.tool_calls = response.tool_calls[:max_tool_calls]
                
                tool_results = await self._handle_tool_calls(response.tool_calls)
                
                # If tools were executed, generate a follow-up response
                if tool_results:
                    tool_context = self._format_tool_results(tool_results)
                    follow_up_request = ModelRequest(
                        prompt=f"Based on the tool results: {tool_context}\n\nPlease provide a comprehensive response to the user.",
                        system_prompt=system_prompt,
                        tools=None,  # Disable tools for follow-up to prevent infinite loops
                        messages=self._get_conversation_messages(system_prompt, include_tool_results=True)
                    )
                    
                    follow_up_response = await self.model.generate(follow_up_request)
                    if follow_up_response.success:
                        final_response = follow_up_response.content
            
            # Update conversation history
            self._conversation_history.append({
                "role": "assistant",
                "content": final_response,
                "timestamp": datetime.now().isoformat(),
                "tool_calls": response.tool_calls,
                "tool_results": tool_results
            })
            
            return {
                "success": response.success,
                "response": final_response,
                "error": response.error,
                "tool_calls": response.tool_calls,
                "tool_results": tool_results,
                "model": response.model,
                "usage": response.usage,
                "metadata": {
                    **response.metadata,
                    "tools_used": len(tool_results),
                    "conversation_length": len(self._conversation_history)
                }
            }
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": ""
            }
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_tools: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response to a prompt
        
        Args:
            prompt: The prompt to generate from
            system_prompt: Optional system prompt
            use_tools: Whether to enable tool use
            **kwargs: Additional generation parameters
            
        Returns:
            Generation result
        """
        return await self.chat(
            message=prompt,
            system_prompt=system_prompt,
            use_tools=use_tools,
            **kwargs
        )
    
    def set_model(self, model_name: str) -> bool:
        """
        Set the active Ollama model
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if model was set successfully
        """
        try:
            self.ollama_wrapper.set_model(model_name)
            logger.info(f"Set model to: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set model {model_name}: {e}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available Ollama models"""
        try:
            models = self.ollama_wrapper.list_models()
            return [
                {
                    "name": model.name,
                    "tag": model.tag,
                    "size": model.size,
                    "modified": model.modified
                }
                for model in models
            ]
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
    
    def get_current_model(self) -> Optional[str]:
        """Get the currently active model"""
        try:
            return self.ollama_wrapper.get_current_model()
        except Exception:
            return None
    
    def clear_conversation(self):
        """Clear the conversation history"""
        self._conversation_history.clear()
        logger.info("Conversation history cleared")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the conversation history"""
        return self._conversation_history.copy()
    
    def is_service_ready(self) -> bool:
        """Check if Ollama service is ready"""
        try:
            return self.ollama_wrapper.check_service() == OllamaStatus.READY
        except Exception:
            return False
    
    async def _discover_and_register_tools(self):
        """Discover and register available tools"""
        if not self.tool_adapter:
            logger.warning("No tool adapter available for tool discovery")
            return
        
        try:
            # Discover tools from default locations
            discovery_paths = [
                "src/tools/examples",
                "src/tools/integration"
            ]
            
            # Add optional user tools directory if it exists
            user_tools_dir = Path("tools")
            if user_tools_dir.exists() and user_tools_dir.is_dir():
                discovery_paths.append(str(user_tools_dir))
            
            logger.info(f"Starting tool discovery in paths: {discovery_paths}")
            
            # Use tool registry to discover tools
            registry = self.tool_adapter.registry
            
            # Only discover if no tools are registered yet
            if registry.list_tools():
                logger.info(f"Tools already discovered: {len(registry.list_tools())} tools available")
                summary = {"discovered": len(registry.list_tools()), "errors": []}
            else:
                summary = registry.discover_all(
                    paths=discovery_paths,
                    discover_packages=True,
                    auto_register=True
                )
            
            logger.info(f"Tool discovery completed: {summary}")
            
            # Log available tools for debugging
            available_tools = self.tool_adapter.get_available_tools()
            logger.info(f"Available tools after discovery: {[tool.get('name', 'unnamed') for tool in available_tools]}")
            
        except Exception as e:
            logger.warning(f"Tool discovery failed: {e}")
    
    def _create_execution_context(self, context: Optional[Dict[str, Any]]) -> ExecutionContext:
        """Create execution context for tool operations"""
        # Extract context information
        user_info = context.get('user', {}) if context else {}
        task_info = context.get('task', {}) if context else {}
        env_info = context.get('environment', {}) if context else {}
        
        # Create context objects
        user_context = UserContext(
            user_id=user_info.get('id', 'default'),
            role=UserRole.USER,  # Use UserRole enum
            preferences=user_info.get('preferences', {})
        )
        
        task_context = TaskContext(
            task_id=task_info.get('task_id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            task_type=TaskType.GENERAL,
            description=task_info.get('description', 'General assistance'),
            priority=task_info.get('priority', 5),  # Use numeric priority
            metadata=task_info.get('metadata', {})
        )
        
        environment_context = EnvironmentContext(
            environment=Environment.LOCAL,  # Use Environment enum
            resources=env_info.get('resources', {}),
            restrictions=set(env_info.get('restrictions', [])),
            capabilities=set(env_info.get('capabilities', [])),
            metadata=env_info.get('metadata', {})
        )
        
        return ExecutionContext(
            user=user_context,
            task=task_context,
            environment=environment_context
        )
    
    def _get_conversation_messages(
        self, 
        system_prompt: Optional[str] = None,
        include_tool_results: bool = False
    ) -> List[Dict[str, str]]:
        """Get conversation messages in the correct format"""
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation history
        for msg in self._conversation_history:
            # Basic message
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
            # Add tool results if requested and available
            if include_tool_results and msg.get("tool_results"):
                tool_context = self._format_tool_results(msg["tool_results"])
                messages.append({
                    "role": "system",
                    "content": f"Tool execution results: {tool_context}"
                })
        
        return messages
    
    async def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle tool calls from the model"""
        if not self.tool_adapter or not self._execution_context:
            return []
        
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("name")
                parameters = tool_call.get("parameters", {})
                
                if not tool_name:
                    continue
                
                # Execute the tool with timeout protection
                import asyncio
                try:
                    # Create invocation dict for execute_tool
                    invocation = {
                        "name": tool_name,
                        "parameters": parameters
                    }
                    
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.tool_adapter.execute_tool,
                            invocation=invocation,
                            context=self._execution_context
                        ),
                        timeout=30.0  # 30 second timeout per tool
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Tool {tool_name} timed out")
                    result = {"error": "Tool execution timed out", "success": False}
                
                results.append({
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "result": result,
                    "success": result.get("success", False)
                })
                
            except Exception as e:
                logger.error(f"Tool execution failed for {tool_call}: {e}")
                results.append({
                    "tool_name": tool_call.get("name", "unknown"),
                    "parameters": tool_call.get("parameters", {}),
                    "result": {"error": str(e)},
                    "success": False
                })
        
        return results
    
    def _convert_tools_to_model_format(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert tool registry format to model interface format
        
        Args:
            tools: Tools in registry format
            
        Returns:
            Tools in model interface format
        """
        converted_tools = []
        
        for tool in tools:
            # Handle different tool formats
            if isinstance(tool, dict):
                # Check if it's already in the right format
                if 'name' in tool and 'description' in tool:
                    converted_tools.append(tool)
                    continue
                
                # Try to extract from other formats
                tool_name = tool.get('tool_name') or tool.get('name', 'unknown_tool')
                description = tool.get('description', 'No description available')
                
                # Build parameters from metadata if available
                parameters = {"type": "object", "properties": {}, "required": []}
                
                if 'metadata' in tool and tool['metadata']:
                    metadata = tool['metadata']
                    if hasattr(metadata, 'parameters') and metadata.parameters:
                        props = {}
                        required = []
                        
                        for param in metadata.parameters:
                            param_name = getattr(param, 'name', str(param))
                            param_type = getattr(param, 'type', 'string')
                            param_desc = getattr(param, 'description', '')
                            is_required = getattr(param, 'required', False)
                            
                            # Map parameter types
                            type_map = {
                                'ParameterType.STRING': 'string',
                                'ParameterType.INTEGER': 'integer',
                                'ParameterType.FLOAT': 'number',
                                'ParameterType.BOOLEAN': 'boolean',
                                'ParameterType.ENUM': 'string'
                            }
                            
                            param_type_str = str(param_type)
                            mapped_type = type_map.get(param_type_str, 'string')
                            
                            props[param_name] = {
                                "type": mapped_type,
                                "description": param_desc
                            }
                            
                            if is_required:
                                required.append(param_name)
                        
                        parameters["properties"] = props
                        parameters["required"] = required
                
                converted_tool = {
                    "name": tool_name,
                    "description": description,
                    "parameters": parameters
                }
                
                converted_tools.append(converted_tool)
            
        logger.debug(f"Converted {len(tools)} tools to model format")
        return converted_tools

    def _create_tool_awareness_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """Create a simple, natural tool awareness system prompt"""
        if not tools:
            return ""
        
        # Extract actual tool names
        tool_names = []
        for tool in tools:
            name = tool.get('name', tool.get('tool_name', 'unknown'))
            tool_names.append(name)
        
        # Sort tool names for consistency
        tool_names.sort()
        
        # Create a simple, natural system prompt
        if len(tool_names) <= 10:
            # Show all tools if there are 10 or fewer
            tools_list = ', '.join(tool_names)
            system_prompt = f"""I am an AI assistant with access to these tools: {tools_list}.

I can use these tools to help you with various tasks. When you ask about my capabilities, I'll mention the specific tools I can use rather than giving generic responses.

I have real, actionable capabilities through these tools - I can actually perform tasks, not just provide information."""
        else:
            # Show first 8 tools and indicate there are more
            featured_tools = ', '.join(tool_names[:8])
            remaining_count = len(tool_names) - 8
            system_prompt = f"""I am an AI assistant with access to tools including: {featured_tools}, and {remaining_count} others.

I can use these tools to help you with various tasks. When you ask about my capabilities, I'll mention the specific tools I can use rather than giving generic responses.

I have real, actionable capabilities through these tools - I can actually perform tasks, not just provide information."""
        
        return system_prompt

    def _format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool results for context"""
        formatted_results = []
        
        for result in tool_results:
            tool_name = result.get("tool_name", "unknown")
            success = result.get("success", False)
            result_data = result.get("result", {})
            
            if success:
                formatted_results.append(f"{tool_name}: {result_data}")
            else:
                error = result_data.get("error", "Unknown error")
                formatted_results.append(f"{tool_name} (failed): {error}")
        
        return "; ".join(formatted_results)
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a generic request (required by BaseAgent)
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        # Extract message from request
        message = request.get('message', request.get('prompt', ''))
        if not message:
            return {
                "success": False,
                "error": "No message provided",
                "response": ""
            }
        
        # Forward to chat method
        return await self.chat(
            message=message,
            system_prompt=request.get('system_prompt'),
            context=request.get('context'),
            use_tools=request.get('use_tools', True),
            stream_callback=request.get('stream_callback')
        )
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool (callback for model adapter)"""
        if not self.tool_adapter or not self._execution_context:
            return {"error": "Tool execution not available"}
        
        try:
            # Create invocation dict for execute_tool
            invocation = {
                "name": tool_name,
                "parameters": parameters
            }
            
            # execute_tool is synchronous, so run it in a thread
            return await asyncio.to_thread(
                self.tool_adapter.execute_tool,
                invocation=invocation,
                context=self._execution_context
            )
        except Exception as e:
            logger.error(f"Tool execution callback failed: {e}")
            return {"error": str(e)}


def create_ollama_agent(
    model_name: Optional[str] = None,
    enable_tools: bool = True,
    config_overrides: Optional[Dict[str, Any]] = None
) -> OllamaAgent:
    """
    Factory function to create a configured Ollama agent
    
    Args:
        model_name: Optional model name to use
        enable_tools: Whether to enable tool integration
        config_overrides: Optional configuration overrides
        
    Returns:
        Configured OllamaAgent instance
    """
    # Create agent config
    config = AgentConfig(
        name="OllamaAgent",
        description="Local AI agent with tool integration",
        enable_tools=enable_tools,
        enable_streaming=True,
        capabilities=["text_generation", "code_generation", "tool_use", "reasoning"]
    )
    
    # Apply overrides
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # Create agent
    agent = OllamaAgent(config=config, model_name=model_name)
    
    return agent