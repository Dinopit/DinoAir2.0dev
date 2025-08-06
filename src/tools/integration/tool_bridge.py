"""
Tool Bridge - Integration layer between old and new tool systems

This module provides a bridge to help migrate from the old tool system
to the new abstraction-based system while maintaining backward compatibility.
"""

import logging
from typing import Dict, Any, Optional, Union, List, Callable
from enum import Enum
import inspect
import asyncio
from functools import wraps

from src.tools.base_tool import BaseTool, ToolMetadata, ExecutionMode
from src.tools.abstraction.model_interface import ModelInterface
from src.tools.adapters import create_adapter, AdapterType, AdapterConfig
from src.tools.engine.executor import ToolExecutor


logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Migration status for tools"""
    LEGACY = "legacy"  # Old system only
    MIGRATING = "migrating"  # Both systems supported
    MIGRATED = "migrated"  # New system only


class ToolBridge:
    """
    Bridge between old and new tool systems
    
    Provides utilities for:
    - Converting old tools to new format
    - Maintaining backward compatibility
    - Progressive migration support
    """
    
    def __init__(self):
        """Initialize the tool bridge"""
        self._legacy_tools: Dict[str, Any] = {}
        self._migrated_tools: Dict[str, BaseTool] = {}
        self._migration_status: Dict[str, MigrationStatus] = {}
        self._compatibility_mode = True
        self._executor = ToolExecutor()
        
    def register_legacy_tool(self, name: str, tool_instance: Any):
        """
        Register a legacy tool
        
        Args:
            name: Tool name
            tool_instance: Legacy tool instance
        """
        self._legacy_tools[name] = tool_instance
        self._migration_status[name] = MigrationStatus.LEGACY
        logger.info(f"Registered legacy tool: {name}")
        
    def register_migrated_tool(self, name: str, tool_instance: BaseTool):
        """
        Register a migrated tool
        
        Args:
            name: Tool name
            tool_instance: New BaseTool instance
        """
        self._migrated_tools[name] = tool_instance
        self._migration_status[name] = MigrationStatus.MIGRATED
        logger.info(f"Registered migrated tool: {name}")
        
    def wrap_legacy_tool(
        self, 
        legacy_tool: Any,
        name: str,
        description: str = "",
        version: str = "1.0.0"
    ) -> BaseTool:
        """
        Wrap a legacy tool to work with the new system
        
        Args:
            legacy_tool: Legacy tool instance
            name: Tool name
            description: Tool description
            version: Tool version
            
        Returns:
            Wrapped tool that inherits from BaseTool
        """
        class LegacyToolWrapper(BaseTool):
            """Wrapper for legacy tools"""
            
            def __init__(self, legacy_instance: Any):
                metadata = ToolMetadata(
                    name=name,
                    description=description or f"Legacy {name} tool",
                    version=version,
                    author="Legacy System",
                    supported_modes=[ExecutionMode.STANDALONE],
                    tags=["legacy", "wrapped"]
                )
                super().__init__(metadata)
                self._legacy_tool = legacy_instance
                
            async def execute(self, **kwargs) -> Dict[str, Any]:
                """Execute the legacy tool"""
                try:
                    # Check if legacy tool has execute method
                    if hasattr(self._legacy_tool, 'execute'):
                        result = self._legacy_tool.execute(**kwargs)
                    elif hasattr(self._legacy_tool, 'run'):
                        result = self._legacy_tool.run(**kwargs)
                    elif hasattr(self._legacy_tool, 'process'):
                        result = self._legacy_tool.process(**kwargs)
                    elif callable(self._legacy_tool):
                        result = self._legacy_tool(**kwargs)
                    else:
                        raise AttributeError(
                            f"Legacy tool {name} has no executable method"
                        )
                        
                    # Handle async legacy tools
                    if inspect.iscoroutine(result):
                        result = await result
                        
                    # Normalize result
                    if isinstance(result, dict):
                        return result
                    else:
                        return {
                            'success': True,
                            'output': result,
                            'errors': [],
                            'warnings': ['Using legacy tool wrapper'],
                            'metadata': {'legacy': True}
                        }
                        
                except Exception as e:
                    logger.error(f"Legacy tool {name} failed: {e}")
                    return {
                        'success': False,
                        'output': None,
                        'errors': [str(e)],
                        'warnings': [],
                        'metadata': {'legacy': True, 'error': str(e)}
                    }
                    
            def validate_config(self, config: Dict[str, Any]) -> bool:
                """Validate configuration"""
                # Legacy tools may not have validation
                if hasattr(self._legacy_tool, 'validate_config'):
                    return self._legacy_tool.validate_config(config)
                return True
                
        # Create and return wrapper instance
        wrapper = LegacyToolWrapper(legacy_tool)
        self.register_migrated_tool(name, wrapper)
        self._migration_status[name] = MigrationStatus.MIGRATING
        
        return wrapper
        
    def create_compatibility_layer(
        self, 
        new_tool: BaseTool,
        legacy_interface: Dict[str, str]
    ) -> Any:
        """
        Create a compatibility layer for new tools to work with old systems
        
        Args:
            new_tool: New BaseTool instance
            legacy_interface: Mapping of old method names to new ones
            
        Returns:
            Compatibility wrapper
        """
        class CompatibilityWrapper:
            """Wrapper to make new tools work with old interfaces"""
            
            def __init__(self, tool: BaseTool):
                self._tool = tool
                self._loop = None
                
            def _get_loop(self):
                """Get or create event loop"""
                try:
                    return asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    return loop
                    
            def __getattr__(self, name: str):
                """Proxy method calls with compatibility mapping"""
                # Check if method is mapped
                if name in legacy_interface:
                    new_name = legacy_interface[name]
                    
                    if new_name == 'execute':
                        # Special handling for execute
                        def legacy_execute(**kwargs):
                            loop = self._get_loop()
                            return loop.run_until_complete(
                                self._tool.execute(**kwargs)
                            )
                        return legacy_execute
                        
                # Check if tool has the method
                if hasattr(self._tool, name):
                    attr = getattr(self._tool, name)
                    
                    # Wrap async methods
                    if inspect.iscoroutinefunction(attr):
                        def sync_wrapper(*args, **kwargs):
                            loop = self._get_loop()
                            return loop.run_until_complete(
                                attr(*args, **kwargs)
                            )
                        return sync_wrapper
                    else:
                        return attr
                        
                raise AttributeError(f"Tool has no attribute '{name}'")
                
        return CompatibilityWrapper(new_tool)
        
    def migrate_tool_progressively(
        self,
        tool_name: str,
        migration_steps: List[Callable]
    ):
        """
        Migrate a tool progressively through defined steps
        
        Args:
            tool_name: Name of the tool to migrate
            migration_steps: List of migration functions
        """
        if tool_name not in self._legacy_tools:
            raise ValueError(f"Unknown legacy tool: {tool_name}")
            
        legacy_tool = self._legacy_tools[tool_name]
        
        logger.info(f"Starting progressive migration for {tool_name}")
        
        # Apply each migration step
        current_tool = legacy_tool
        for i, step in enumerate(migration_steps):
            try:
                logger.info(f"Applying migration step {i+1} for {tool_name}")
                current_tool = step(current_tool)
            except Exception as e:
                logger.error(
                    f"Migration step {i+1} failed for {tool_name}: {e}"
                )
                raise
                
        # Register the migrated tool
        if isinstance(current_tool, BaseTool):
            self.register_migrated_tool(tool_name, current_tool)
        else:
            # Wrap if not already a BaseTool
            self.wrap_legacy_tool(
                current_tool,
                tool_name,
                description=f"Migrated {tool_name}"
            )
            
        logger.info(f"Successfully migrated {tool_name}")
        
    def get_tool(
        self, 
        name: str, 
        prefer_new: bool = True
    ) -> Union[BaseTool, Any]:
        """
        Get a tool by name, handling both old and new systems
        
        Args:
            name: Tool name
            prefer_new: Whether to prefer new system if available
            
        Returns:
            Tool instance
        """
        status = self._migration_status.get(name, MigrationStatus.LEGACY)
        
        if status == MigrationStatus.MIGRATED:
            return self._migrated_tools[name]
        elif status == MigrationStatus.LEGACY:
            if name in self._legacy_tools:
                return self._legacy_tools[name]
        elif status == MigrationStatus.MIGRATING:
            # Both available, use preference
            if prefer_new and name in self._migrated_tools:
                return self._migrated_tools[name]
            elif name in self._legacy_tools:
                return self._legacy_tools[name]
                
        raise KeyError(f"Tool '{name}' not found")
        
    def list_tools(self) -> Dict[str, MigrationStatus]:
        """List all registered tools and their migration status"""
        return self._migration_status.copy()
        
    def set_compatibility_mode(self, enabled: bool):
        """Enable or disable backward compatibility mode"""
        self._compatibility_mode = enabled
        status = 'enabled' if enabled else 'disabled'
        logger.info(f"Compatibility mode: {status}")


# Migration utilities

def create_model_adapter_from_config(
    config: Dict[str, Any]
) -> Optional[ModelInterface]:
    """
    Create a model adapter from old-style configuration
    
    Args:
        config: Old configuration format
        
    Returns:
        ModelInterface instance or None
    """
    # Map old config to new adapter config
    model_type = config.get('model_type', config.get('provider', 'openai'))
    
    adapter_type_map = {
        'openai': AdapterType.OPENAI,
        'gpt': AdapterType.OPENAI,
        'anthropic': AdapterType.ANTHROPIC,
        'claude': AdapterType.ANTHROPIC,
        'ollama': AdapterType.OLLAMA,
        'local': AdapterType.OLLAMA
    }
    
    adapter_type = adapter_type_map.get(model_type.lower())
    if not adapter_type:
        logger.warning(f"Unknown model type: {model_type}")
        return None
        
    # Create adapter config
    model_name = config.get('model_name', config.get('model', 'gpt-3.5-turbo'))
    adapter_config = AdapterConfig(
        adapter_type=adapter_type,
        model_name=model_name,
        api_key=config.get('api_key'),
        api_base=config.get('api_base', config.get('base_url')),
        timeout=config.get('timeout', 60),
        extra_params={
            'temperature': config.get('temperature', 0.7),
            'max_tokens': config.get('max_tokens', 2048),
            'top_p': config.get('top_p', 0.9)
        }
    )
    
    # Create and initialize adapter
    try:
        adapter = create_adapter(adapter_type, adapter_config)
        # Initialize synchronously for compatibility
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(adapter.initialize())
        loop.close()
        
        return adapter
    except Exception as e:
        logger.error(f"Failed to create model adapter: {e}")
        return None


def migrate_tool_config(old_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate old tool configuration to new format
    
    Args:
        old_config: Old configuration format
        
    Returns:
        New configuration format
    """
    new_config = {}
    
    # Map common fields
    field_mapping = {
        'name': 'name',
        'description': 'description',
        'version': 'version',
        'enabled': 'enabled',
        'timeout': 'timeout',
        'max_retries': 'max_retries'
    }
    
    for old_key, new_key in field_mapping.items():
        if old_key in old_config:
            new_config[new_key] = old_config[old_key]
            
    # Map AI/model configuration
    if 'ai' in old_config or 'model' in old_config:
        ai_config = old_config.get('ai', old_config.get('model', {}))
        new_config['model_config'] = {
            'provider': ai_config.get('provider', 'openai'),
            'model_name': ai_config.get('model', 'gpt-3.5-turbo'),
            'temperature': ai_config.get('temperature', 0.7),
            'max_tokens': ai_config.get('max_tokens', 2048)
        }
        
    # Map execution settings
    if 'execution' in old_config:
        exec_config = old_config['execution']
        new_config['execution_mode'] = exec_config.get(
            'mode', 
            'ai_assisted' if new_config.get('model_config') else 'standalone'
        )
        
    return new_config


# Decorator for backward compatibility
def backward_compatible(legacy_name: Optional[str] = None):
    """
    Decorator to maintain backward compatibility for tool methods
    
    Args:
        legacy_name: Optional legacy method name
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Log usage of legacy method
            method_name = legacy_name or func.__name__
            logger.debug(f"Legacy method called: {method_name}")
            
            # Check if we need to adapt parameters
            if 'config' in kwargs and isinstance(kwargs['config'], dict):
                # Migrate old config format
                kwargs['config'] = migrate_tool_config(kwargs['config'])
                
            # Call the actual method
            result = func(self, *args, **kwargs)
            
            # Handle async methods
            if inspect.iscoroutine(result):
                import asyncio
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(result)
                loop.close()
                
            return result
            
        # Add legacy name as alias
        if legacy_name and legacy_name != func.__name__:
            setattr(wrapper, '_legacy_name', legacy_name)
            
        return wrapper
    return decorator


# Global bridge instance
_bridge = ToolBridge()


def get_tool_bridge() -> ToolBridge:
    """Get the global tool bridge instance"""
    return _bridge


# Example migration
"""
Example Usage:

    from src.tools.integration.tool_bridge import get_tool_bridge
    from src.tools.pseudocode_tool import PseudocodeTool
    from src.tools.pseudocode_tool_refactored import (
        PseudocodeTool as NewPseudocodeTool
    )
    
    # Get bridge
    bridge = get_tool_bridge()
    
    # Register legacy tool
    legacy_tool = PseudocodeTool()
    bridge.register_legacy_tool('pseudocode_legacy', legacy_tool)
    
    # Wrap legacy tool for new system
    wrapped_tool = bridge.wrap_legacy_tool(
        legacy_tool,
        'pseudocode_wrapped',
        description='Wrapped pseudocode translator'
    )
    
    # Use wrapped tool with new system
    result = await wrapped_tool.execute(
        pseudocode="print hello world",
        target_language="python"
    )
    
    # Create compatibility layer for new tool
    new_tool = NewPseudocodeTool()
    compat_tool = bridge.create_compatibility_layer(
        new_tool,
        {
            'translate': 'execute',
            'translate_sync': 'execute',
            'translate_async': 'execute'
        }
    )
    
    # Use new tool with old interface
    result = compat_tool.translate("print hello", language="python")
"""