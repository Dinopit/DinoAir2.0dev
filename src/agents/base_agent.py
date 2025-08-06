"""
Base Agent Module

This module provides the base class for all AI agents in the DinoAir system,
ensuring consistent interfaces and functionality across different agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from pathlib import Path
import json

# Import the new abstraction layer
from src.tools.abstraction.model_interface import (
    ModelInterface,
    ModelRequest,
    ModelResponse,
    ModelCapabilities,
    StandardModelAdapter
)
from src.tools.registry import ToolRegistry
from src.tools.ai_adapter import ToolAIAdapter

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an AI agent"""
    name: str
    description: str
    model_config: Dict[str, Any] = field(default_factory=dict)
    tool_config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    max_retries: int = 3
    timeout: float = 300.0
    enable_tools: bool = True
    enable_streaming: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Context for agent operations"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseAgent(ABC):
    """
    Abstract base class for AI agents
    
    This class provides the foundation for all AI agents in the system,
    including support for:
    - Model abstraction through ModelInterface
    - Tool integration through ToolAIAdapter
    - Context management
    - Error handling and retries
    - Async operations
    """
    
    def __init__(
        self,
        config: AgentConfig,
        model: Optional[ModelInterface] = None,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        Initialize the base agent
        
        Args:
            config: Agent configuration
            model: Optional model interface
            tool_registry: Optional tool registry
        """
        self.config = config
        self.model = model
        self._is_initialized = False
        self._context = AgentContext()
        
        # Initialize tool support if enabled
        if config.enable_tools:
            self.tool_adapter = ToolAIAdapter(
                registry=tool_registry or ToolRegistry(),
                enable_policies=True,
                enable_restrictions=True
            )
        else:
            self.tool_adapter = None
            
        # Initialize async support
        self._loop = None
        self._executor = None
        
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the agent
        
        This method must be implemented by subclasses to perform
        agent-specific initialization.
        
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def process_request(
        self,
        request: Union[str, Dict[str, Any]],
        context: Optional[AgentContext] = None
    ) -> Dict[str, Any]:
        """
        Process a request
        
        This method must be implemented by subclasses to handle
        agent-specific request processing.
        
        Args:
            request: User request (string or structured)
            context: Optional context for the request
            
        Returns:
            Response dictionary
        """
        pass
    
    async def initialize_base(self) -> bool:
        """Initialize base agent components"""
        try:
            # Initialize async components with modern pattern
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create one for this thread
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                
            # Initialize model if provided
            if self.model and not self.model._is_initialized:
                model_init = await self.model.initialize()
                if not model_init:
                    logger.error("Failed to initialize model")
                    return False
                    
            # Initialize subclass components
            subclass_init = await self.initialize()
            if not subclass_init:
                logger.error("Failed to initialize agent-specific components")
                return False
                
            self._is_initialized = True
            logger.info(f"Agent '{self.config.name}' initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            return False
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[AgentContext] = None,
        stream: bool = False,
        **kwargs
    ) -> ModelResponse:
        """
        Generate a response using the model
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            context: Optional context
            stream: Whether to stream the response
            **kwargs: Additional model parameters
            
        Returns:
            Model response
        """
        if not self.model:
            return ModelResponse(
                content="",
                success=False,
                error="No model configured"
            )
            
        # Build messages from context
        messages = []
        if context and context.conversation_history:
            messages = context.conversation_history.copy()
        
        # Create model request
        request = ModelRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            messages=messages,
            stream=stream,
            **kwargs
        )
        
        # Add tool information if enabled
        if self.config.enable_tools and self.tool_adapter:
            available_tools = self.tool_adapter.get_available_tools(
                format_type="function_calling"
            )
            if available_tools:
                request.tools = available_tools
                request.tool_choice = "auto"
        
        # Generate response with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                if stream and self.config.enable_streaming:
                    # Handle streaming
                    chunks = []
                    
                    def chunk_callback(chunk: str):
                        chunks.append(chunk)
                        
                    response = await self.model.stream_generate(
                        request, chunk_callback
                    )
                    response.content = "".join(chunks)
                else:
                    # Regular generation
                    response = await self.model.generate(request)
                    
                if response.success:
                    # Handle tool calls if present
                    if response.tool_calls and self.tool_adapter:
                        tool_results = await self._execute_tool_calls(
                            response.tool_calls, context
                        )
                        # Add tool results to response metadata
                        response.metadata["tool_results"] = tool_results
                        
                    return response
                else:
                    last_error = response.error
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Generation attempt {attempt + 1} failed: {e}"
                )
                
            # Wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        return ModelResponse(
            content="",
            success=False,
            error=(
                f"Generation failed after {self.config.max_retries} "
                f"attempts: {last_error}"
            )
        )
    
    async def _execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Optional[AgentContext]
    ) -> List[Dict[str, Any]]:
        """Execute tool calls from model response"""
        if not self.tool_adapter:
            return []
            
        results = []
        for tool_call in tool_calls:
            try:
                # Execute tool - pass as invocation dict, not context
                result = self.tool_adapter.execute_tool(
                    tool_call,
                    track_history=True,
                    validate_params=True
                )
                results.append(result)
                
                # Record in context
                if context:
                    context.tool_history.append({
                        "tool_call": tool_call,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "tool_call": tool_call
                })
                
        return results
    
    def set_context(self, context: AgentContext):
        """Set the agent context"""
        self._context = context
        
    def get_context(self) -> AgentContext:
        """Get the current agent context"""
        return self._context
        
    def update_context(self, updates: Dict[str, Any]):
        """Update context with new information"""
        if "conversation_history" in updates:
            self._context.conversation_history.extend(
                updates["conversation_history"]
            )
        if "metadata" in updates:
            self._context.metadata.update(updates["metadata"])
            
    def clear_context(self):
        """Clear the agent context"""
        self._context = AgentContext()
        
    async def shutdown(self):
        """Shutdown the agent and cleanup resources"""
        logger.info(f"Shutting down agent '{self.config.name}'")
        
        # Shutdown model
        if self.model:
            await self.model.shutdown()
            
        # Clear context
        self.clear_context()
        
        self._is_initialized = False
        logger.info(f"Agent '{self.config.name}' shutdown complete")
        
    @property
    def is_ready(self) -> bool:
        """Check if agent is ready"""
        return (
            self._is_initialized and
            (not self.model or self.model.is_available())
        )
        
    @property
    def capabilities(self) -> List[str]:
        """Get agent capabilities"""
        caps = self.config.capabilities.copy()
        
        # Add model capabilities
        if self.model:
            model_caps = self.model.get_capabilities()
            caps.extend([cap.name for cap in model_caps])
            
        # Add tool capability
        if self.config.enable_tools and self.tool_adapter:
            caps.append("TOOL_USE")
            
        return list(set(caps))  # Remove duplicates
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        info = {
            "name": self.config.name,
            "description": self.config.description,
            "is_ready": self.is_ready,
            "capabilities": self.capabilities,
            "config": {
                "enable_tools": self.config.enable_tools,
                "enable_streaming": self.config.enable_streaming,
                "max_retries": self.config.max_retries,
                "timeout": self.config.timeout
            }
        }
        
        # Add model info
        if self.model:
            info["model"] = self.model.get_model_info()
            
        # Add tool info
        if self.tool_adapter:
            available_tools = self.tool_adapter.get_available_tools()
            info["available_tools"] = len(available_tools)
            info["tool_names"] = [t["name"] for t in available_tools[:10]]
            
        return info
    
    async def save_context(self, filepath: Union[str, Path]):
        """Save context to file"""
        filepath = Path(filepath)
        
        # Convert context to serializable format
        context_data = {
            "user_id": self._context.user_id,
            "session_id": self._context.session_id,
            "conversation_history": self._context.conversation_history,
            "tool_history": self._context.tool_history,
            "metadata": self._context.metadata,
            "timestamp": self._context.timestamp.isoformat()
        }
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(context_data, f, indent=2)
            
        logger.info(f"Context saved to {filepath}")
        
    async def load_context(self, filepath: Union[str, Path]):
        """Load context from file"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.warning(f"Context file not found: {filepath}")
            return
            
        # Load from file
        with open(filepath, 'r') as f:
            context_data = json.load(f)
            
        # Restore context
        self._context = AgentContext(
            user_id=context_data.get("user_id"),
            session_id=context_data.get("session_id"),
            conversation_history=context_data.get("conversation_history", []),
            tool_history=context_data.get("tool_history", []),
            metadata=context_data.get("metadata", {}),
            timestamp=datetime.fromisoformat(
                context_data.get("timestamp", datetime.now().isoformat())
            )
        )
        
        logger.info(f"Context loaded from {filepath}")


class SimpleAgent(BaseAgent):
    """
    Simple implementation of BaseAgent for basic use cases
    
    This agent provides a straightforward implementation that can be
    used directly or as a reference for custom agents.
    """
    
    async def initialize(self) -> bool:
        """Initialize the simple agent"""
        # No additional initialization needed
        return True
        
    async def process_request(
        self,
        request: Union[str, Dict[str, Any]],
        context: Optional[AgentContext] = None
    ) -> Dict[str, Any]:
        """Process a request"""
        # Use provided context or current context
        context = context or self._context
        
        # Convert request to string if needed
        if isinstance(request, dict):
            prompt = request.get("prompt", "") or request.get("message", "")
            system_prompt = request.get("system_prompt")
            kwargs = {
                k: v for k, v in request.items()
                if k not in ["prompt", "message", "system_prompt"]
            }
        else:
            prompt = str(request)
            system_prompt = None
            kwargs = {}
            
        # Generate response
        response = await self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context,
            **kwargs
        )
        
        # Update context with the interaction
        if response.success:
            context.conversation_history.append({
                "role": "user",
                "content": prompt
            })
            context.conversation_history.append({
                "role": "assistant",
                "content": response.content
            })
            
        # Return formatted response
        return {
            "success": response.success,
            "content": response.content,
            "error": response.error,
            "metadata": response.metadata,
            "model": response.model,
            "timestamp": response.timestamp.isoformat()
        }


# Convenience functions

def create_agent(
    name: str,
    model: ModelInterface,
    description: str = "",
    enable_tools: bool = True,
    **kwargs
) -> SimpleAgent:
    """
    Create a simple agent
    
    Args:
        name: Agent name
        model: Model interface
        description: Agent description
        enable_tools: Whether to enable tool support
        **kwargs: Additional configuration
        
    Returns:
        Configured SimpleAgent instance
    """
    config = AgentConfig(
        name=name,
        description=description or f"Simple agent: {name}",
        enable_tools=enable_tools,
        **kwargs
    )
    
    return SimpleAgent(config=config, model=model)


async def create_agent_from_model_name(
    agent_name: str,
    model_name: str,
    model_type: str = "ollama",
    enable_tools: bool = True,
    **kwargs
) -> Optional[SimpleAgent]:
    """
    Create an agent from a model name
    
    Args:
        agent_name: Name for the agent
        model_name: Name of the model
        model_type: Type of model (ollama, openai, etc.)
        enable_tools: Whether to enable tools
        **kwargs: Additional configuration
        
    Returns:
        Configured agent or None if creation fails
    """
    # Import model adapters dynamically
    try:
        if model_type == "ollama":
            from src.agents.ollama_wrapper import OllamaWrapper
            wrapper = OllamaWrapper()
            if wrapper.is_ready:
                model = StandardModelAdapter(
                    wrapper,
                    capabilities=[
                        ModelCapabilities.TEXT_GENERATION,
                        ModelCapabilities.STREAMING,
                        ModelCapabilities.CONTEXT_WINDOW_4K
                    ]
                )
            else:
                logger.error("Ollama not ready")
                return None
                
        elif model_type == "openai":
            # Placeholder for OpenAI adapter
            logger.error("OpenAI adapter not yet implemented")
            return None
        else:
            logger.error(f"Unknown model type: {model_type}")
            return None
            
        # Create agent
        agent = create_agent(
            name=agent_name,
            model=model,
            description=f"{model_type} agent using {model_name}",
            enable_tools=enable_tools,
            **kwargs
        )
        
        # Initialize agent
        if await agent.initialize_base():
            return agent
        else:
            logger.error("Failed to initialize agent")
            return None
            
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        return None