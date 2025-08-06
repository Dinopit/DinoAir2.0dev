"""
Agent Manager

This module provides centralized management of AI agents, including
initialization, configuration, and coordination between different
agent types and the GUI.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .ollama_agent import OllamaAgent, create_ollama_agent
from .ollama_wrapper import OllamaWrapper, OllamaStatus
from .base_agent import AgentConfig, AgentContext
from ..tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Centralized manager for AI agents
    
    This class handles:
    - Agent initialization and lifecycle
    - Tool integration setup
    - Communication between GUI and agents
    - Agent configuration and state management
    """
    
    def __init__(self):
        """Initialize the agent manager"""
        self._agents: Dict[str, Any] = {}
        self._tool_registry: Optional[ToolRegistry] = None
        self._current_agent: Optional[str] = None
        self._initialized = False
        
        # Event callbacks
        self._status_callbacks: List[Callable] = []
        self._message_callbacks: List[Callable] = []
        
    async def initialize(self) -> bool:
        """Initialize the agent manager and discovery system"""
        try:
            # Initialize tool registry
            self._tool_registry = ToolRegistry()
            
            # Discover tools
            logger.info("Starting tool discovery...")
            # Prepare discovery paths
            from pathlib import Path
            discovery_paths = ["src/tools/examples"]
            
            # Add optional user tools directory if it exists
            user_tools_dir = Path("tools")
            if user_tools_dir.exists() and user_tools_dir.is_dir():
                discovery_paths.append(str(user_tools_dir))
            
            summary = self._tool_registry.discover_all(
                paths=discovery_paths,
                discover_packages=True,
                auto_register=True
            )
            logger.info(f"Tool discovery complete: {summary}")
            
            # Debug: Log discovered tools
            discovered_tools = self._tool_registry.list_tools()
            tool_names = [tool.get('name', 'unnamed') for tool in discovered_tools]
            logger.info(f"Discovered tools: {tool_names}")
            
            self._initialized = True
            logger.info("AgentManager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentManager: {e}")
            return False
    
    async def create_ollama_agent(
        self,
        name: str = "default_ollama",
        model_name: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create and register an Ollama agent
        
        Args:
            name: Agent identifier
            model_name: Optional model name to use
            config_overrides: Optional configuration overrides
            
        Returns:
            True if agent was created successfully
        """
        if not self._initialized:
            logger.error("AgentManager not initialized")
            return False
        
        try:
            # Create agent config
            config = AgentConfig(
                name=name,
                description=f"Ollama agent with model {model_name or 'default'}",
                enable_tools=True,
                enable_streaming=True,
                capabilities=["text_generation", "code_generation", "tool_use", "reasoning"]
            )
            
            # Apply overrides
            if config_overrides:
                for key, value in config_overrides.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            # Create agent
            agent = OllamaAgent(
                config=config,
                tool_registry=self._tool_registry,
                model_name=model_name
            )
            
            # Initialize agent
            if await agent.initialize():
                self._agents[name] = agent
                self._current_agent = name
                logger.info(f"Created Ollama agent '{name}' with model {model_name}")
                self._notify_status_change(f"Agent '{name}' created")
                return True
            else:
                logger.error(f"Failed to initialize agent '{name}'")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create Ollama agent '{name}': {e}")
            return False
    
    def get_agent(self, name: Optional[str] = None) -> Optional[Any]:
        """
        Get an agent by name or the current agent
        
        Args:
            name: Agent name, or None for current agent
            
        Returns:
            Agent instance or None
        """
        if name is None:
            name = self._current_agent
        
        if name and name in self._agents:
            return self._agents[name]
        
        return None
    
    def get_current_agent(self) -> Optional[Any]:
        """Get the current active agent"""
        return self.get_agent()
    
    def set_current_agent(self, name: str) -> bool:
        """
        Set the current active agent
        
        Args:
            name: Agent name
            
        Returns:
            True if agent was set successfully
        """
        if name in self._agents:
            self._current_agent = name
            logger.info(f"Set current agent to '{name}'")
            self._notify_status_change(f"Switched to agent '{name}'")
            return True
        else:
            logger.error(f"Agent '{name}' not found")
            return False
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Get list of all agents with their info"""
        agents = []
        for name, agent in self._agents.items():
            agent_info = {
                "name": name,
                "type": type(agent).__name__,
                "is_current": name == self._current_agent,
                "initialized": getattr(agent, '_is_initialized', False)
            }
            
            # Add agent-specific info
            if hasattr(agent, 'get_current_model'):
                agent_info["current_model"] = agent.get_current_model()
            
            if hasattr(agent, 'is_service_ready'):
                agent_info["service_ready"] = agent.is_service_ready()
            
            agents.append(agent_info)
        
        return agents
    
    async def chat_with_current_agent(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        use_tools: bool = True,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Chat with the current agent
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            context: Optional context information
            use_tools: Whether to enable tool use
            stream_callback: Optional callback for streaming
            
        Returns:
            Chat response
        """
        agent = self.get_current_agent()
        if not agent:
            return {
                "success": False,
                "error": "No active agent",
                "response": ""
            }
        
        if not hasattr(agent, 'chat'):
            return {
                "success": False,
                "error": "Agent does not support chat",
                "response": ""
            }
        
        try:
            response = await agent.chat(
                message=message,
                system_prompt=system_prompt,
                context=context,
                use_tools=use_tools,
                stream_callback=stream_callback
            )
            
            # Notify message callbacks
            self._notify_message_callbacks(message, response)
            
            return response
            
        except ImportError as e:
            logger.error(f"Chat failed due to missing dependency: {e}")
            return {
                "success": False,
                "error": f"Missing dependency: {e}",
                "response": ""
            }
        except ConnectionError as e:
            logger.error(f"Chat failed due to connection error: {e}")
            return {
                "success": False,
                "error": f"Connection error: {e}",
                "response": ""
            }
        except TimeoutError as e:
            logger.error(f"Chat failed due to timeout: {e}")
            return {
                "success": False,
                "error": "Request timed out",
                "response": ""
            }
        except Exception as e:
            logger.error(f"Chat with agent failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "response": ""
            }
    
    def get_available_models(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available models for an agent"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'get_available_models'):
            return agent.get_available_models()
        return []
    
    def set_model(self, model_name: str, agent_name: Optional[str] = None) -> bool:
        """Set model for an agent"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'set_model'):
            return agent.set_model(model_name)
        return False
    
    def get_current_model(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get current model for an agent"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'get_current_model'):
            return agent.get_current_model()
        return None
    
    def is_service_ready(self, agent_name: Optional[str] = None) -> bool:
        """Check if agent service is ready"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'is_service_ready'):
            return agent.is_service_ready()
        return False
    
    def clear_conversation(self, agent_name: Optional[str] = None):
        """Clear conversation history for an agent"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'clear_conversation'):
            agent.clear_conversation()
    
    def get_conversation_history(self, agent_name: Optional[str] = None) -> List[Dict[str, str]]:
        """Get conversation history for an agent"""
        agent = self.get_agent(agent_name)
        if agent and hasattr(agent, 'get_conversation_history'):
            return agent.get_conversation_history()
        return []
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get information about available tools"""
        if not self._tool_registry:
            return {"error": "Tool registry not initialized"}
        
        try:
            stats = self._tool_registry.get_statistics()
            tools = self._tool_registry.list_tools()
            
            return {
                "statistics": stats,
                "available_tools": tools,
                "registry_initialized": True
            }
        except Exception as e:
            return {"error": str(e)}
    
    def add_status_callback(self, callback: Callable[[str], None]):
        """Add a callback for status changes"""
        self._status_callbacks.append(callback)
    
    def add_message_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add a callback for message events"""
        self._message_callbacks.append(callback)
    
    def _notify_status_change(self, status: str):
        """Notify all status callbacks of a change"""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Status callback failed: {e}")
    
    def _notify_message_callbacks(self, message: str, response: Dict[str, Any]):
        """Notify all message callbacks"""
        for callback in self._message_callbacks:
            try:
                callback(message, response)
            except Exception as e:
                logger.error(f"Message callback failed: {e}")
    
    async def shutdown(self):
        """Shutdown all agents and cleanup"""
        logger.info("Shutting down AgentManager...")
        
        for name, agent in self._agents.items():
            try:
                if hasattr(agent, 'shutdown'):
                    await agent.shutdown()
                logger.info(f"Agent '{name}' shutdown complete")
            except Exception as e:
                logger.error(f"Error shutting down agent '{name}': {e}")
        
        self._agents.clear()
        self._current_agent = None
        
        # Shutdown tool registry
        if self._tool_registry:
            try:
                self._tool_registry.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down tool registry: {e}")
        
        self._initialized = False
        logger.info("AgentManager shutdown complete")


# Global agent manager instance
_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


async def initialize_agent_system() -> bool:
    """Initialize the global agent system"""
    manager = get_agent_manager()
    return await manager.initialize()


def sync_chat_with_agent(
    message: str,
    system_prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    use_tools: bool = True,
    stream_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for chatting with the current agent
    
    This function handles the async/sync bridge for GUI integration
    """
    manager = get_agent_manager()
    
    # Use modern asyncio pattern for thread-safe execution
    try:
        # Check if we're already in an async context
        loop = asyncio.get_running_loop()
        # If we are, we can't use run_until_complete - need different approach
        import threading
        import concurrent.futures
        
        result = {}
        exception = {}
        
        def run_in_thread():
            try:
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result['value'] = new_loop.run_until_complete(
                        manager.chat_with_current_agent(
                            message=message,
                            system_prompt=system_prompt,
                            context=context,
                            use_tools=use_tools,
                            stream_callback=stream_callback
                        )
                    )
                finally:
                    new_loop.close()
            except Exception as e:
                exception['error'] = e
        
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        # Add timeout to prevent indefinite blocking
        thread.join(timeout=60.0)  # 60 second timeout
        
        if thread.is_alive():
            # Thread is still running - likely stuck
            logger.error("Chat thread timed out - agent may be stuck")
            return {
                "success": False,
                "error": "Request timed out - agent may be stuck in a loop",
                "response": ""
            }
        
        if 'error' in exception:
            raise exception['error']
        return result['value']
        
    except RuntimeError:
        # No event loop running, safe to create one
        return asyncio.run(
            manager.chat_with_current_agent(
                message=message,
                system_prompt=system_prompt,
                context=context,
                use_tools=use_tools,
                stream_callback=stream_callback
            )
        )