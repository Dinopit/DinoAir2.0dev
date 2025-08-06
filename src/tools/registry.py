"""
Tool Registry System

This module provides a centralized registry for managing tools in the
DinoAir system. It supports tool discovery, registration, lifecycle
management, and dependency resolution.
"""

import logging
from typing import Dict, List, Optional, Type, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
import importlib
import importlib.util
import threading
from pathlib import Path
import json
from collections import defaultdict

from .base import (
    BaseTool, ToolMetadata, ToolCategory,
    ToolEvent, ToolLifecycleEvent
)
from .discovery import ToolDiscovery
from .loader import ToolLoader, ValidationResult
from .control.tool_controller import ToolController
from .control.tool_context import ExecutionContext


logger = logging.getLogger(__name__)


@dataclass
class ToolRegistration:
    """Information about a registered tool"""
    tool_class: Type[BaseTool]
    metadata: ToolMetadata
    instance: Optional[BaseTool] = None
    config: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    use_count: int = 0
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    is_singleton: bool = True
    is_enabled: bool = True
    tags: Set[str] = field(default_factory=set)


class ToolRegistry:
    """
    Centralized registry for managing tools
    
    This class provides a singleton registry for discovering, registering,
    and managing tools throughout their lifecycle. It supports:
    
    - Tool registration and discovery
    - Lazy instantiation and singleton management
    - Dependency resolution
    - Event broadcasting
    - Tool categorization and searching
    - Configuration management
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the registry"""
        if not hasattr(self, '_initialized'):
            self._tools: Dict[str, ToolRegistration] = {}
            self._categories: Dict[ToolCategory, Set[str]] = defaultdict(set)
            self._tags: Dict[str, Set[str]] = defaultdict(set)
            self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
            self._discovery_paths: List[Path] = []
            self._lock = threading.RLock()
            self._initialized = True
            
            # Initialize discovery and loader
            self._discovery = ToolDiscovery(self)
            self._loader = ToolLoader(self)
            
            # Initialize tool controller for policy enforcement
            self._controller: Optional[ToolController] = None
            
            # Register for tool lifecycle events
            self._setup_event_handling()
            
            # Auto-register function-based tools from basic_tools
            self._auto_register_basic_tools()
    
    def _setup_event_handling(self):
        """Setup internal event handling"""
        self.add_event_handler(
            ToolLifecycleEvent.INITIALIZED,
            self._on_tool_initialized
        )
        self.add_event_handler(
            ToolLifecycleEvent.STATE_CHANGED,
            self._on_tool_state_changed
        )
    
    def _on_tool_initialized(self, event: ToolEvent):
        """Handle tool initialization events"""
        logger.info(f"Tool '{event.tool_name}' initialized")
    
    def _on_tool_state_changed(self, event: ToolEvent):
        """Handle tool state change events"""
        old_status = event.data.get('old_status')
        new_status = event.data.get('new_status')
        logger.debug(
            f"Tool '{event.tool_name}' state changed: "
            f"{old_status} -> {new_status}"
        )
    
    def register_tool(
        self,
        tool_class: Type[BaseTool],
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_singleton: bool = True,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Register a tool class
        
        Args:
            tool_class: The tool class to register
            name: Optional name override (uses class metadata by default)
            config: Optional configuration for the tool
            is_singleton: Whether to maintain a single instance
            tags: Optional tags for categorization
            
        Returns:
            True if successfully registered
        """
        try:
            # Create a temporary instance to get metadata
            temp_instance = tool_class()
            metadata = temp_instance.metadata
            
            if not metadata:
                logger.error(
                    f"Tool {tool_class.__name__} has no metadata"
                )
                return False
            
            # Use provided name or metadata name
            tool_name = name or metadata.name
            
            # Check if already registered
            if tool_name in self._tools:
                logger.warning(
                    f"Tool '{tool_name}' is already registered"
                )
                return False
            
            # Create registration
            registration = ToolRegistration(
                tool_class=tool_class,
                metadata=metadata,
                config=config or {},
                is_singleton=is_singleton,
                tags=set(tags or [])
            )
            
            # Add metadata tags
            registration.tags.update(metadata.tags)
            
            # Register the tool
            with self._lock:
                self._tools[tool_name] = registration
                self._categories[metadata.category].add(tool_name)
                
                # Update tag index
                for tag in registration.tags:
                    self._tags[tag].add(tool_name)
            
            # Clean up temporary instance
            temp_instance.shutdown()
            
            logger.info(
                f"Registered tool '{tool_name}' "
                f"(category: {metadata.category.value})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool_class}: {e}")
            return False
    
    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            name: Name of the tool to unregister
            
        Returns:
            True if successfully unregistered
        """
        with self._lock:
            if name not in self._tools:
                return False
            
            registration = self._tools[name]
            
            # Shutdown instance if exists
            if registration.instance:
                try:
                    registration.instance.shutdown()
                except Exception as e:
                    logger.error(
                        f"Error shutting down tool '{name}': {e}"
                    )
            
            # Remove from indices
            self._categories[registration.metadata.category].discard(name)
            for tag in registration.tags:
                self._tags[tag].discard(name)
            
            # Remove registration
            del self._tools[name]
            
        logger.info(f"Unregistered tool '{name}'")
        return True
    
    def get_tool(
        self,
        name: str,
        config_override: Optional[Dict[str, Any]] = None,
        context: Optional[ExecutionContext] = None
    ) -> Optional[BaseTool]:
        """
        Get a tool instance
        
        Args:
            name: Name of the tool
            config_override: Optional config to override defaults
            context: Optional execution context for policy checks
            
        Returns:
            Tool instance or None if not found or not allowed
        """
        with self._lock:
            if name not in self._tools:
                logger.error(f"Tool '{name}' not found")
                return None
            
            registration = self._tools[name]
            
            # Check if tool is enabled
            if not registration.is_enabled:
                logger.warning(f"Tool '{name}' is disabled")
                return None
            
            # Check policies if controller is configured
            if self._controller and context:
                # Convert ExecutionContext to dict for controller
                context_dict = {
                    "user": context.user.__dict__ if context.user else {},
                    "task": context.task.__dict__ if context.task else {},
                    "environment": (
                        context.environment.__dict__
                        if context.environment else {}
                    )
                }
                # Use can_use_tool method which takes tool name
                is_allowed, reason = self._controller.can_use_tool(
                    name, context_dict
                )
                if not is_allowed:
                    logger.warning(
                        f"Tool '{name}' not allowed by policy: {reason}"
                    )
                    return None
            
            # Update usage statistics
            registration.use_count += 1
            registration.last_used = datetime.now()
            
            # Check if singleton instance exists
            if registration.is_singleton and registration.instance:
                # Update config if override provided
                if config_override:
                    registration.instance.update_config(config_override)
                return registration.instance
            
            # Create new instance
            config = registration.config.copy()
            if config_override:
                config.update(config_override)
            
            try:
                instance = registration.tool_class(config)
                
                # Store singleton instance
                if registration.is_singleton:
                    registration.instance = instance
                
                # Connect to registry events
                self._connect_tool_events(instance)
                
                return instance
                
            except Exception as e:
                logger.error(f"Failed to create tool '{name}': {e}")
                return None
    
    def _connect_tool_events(self, tool: BaseTool):
        """Connect tool events to registry handlers"""
        for event_type, handlers in self._event_handlers.items():
            for handler in handlers:
                tool.add_event_handler(event_type, handler)
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        enabled_only: bool = True,
        context: Optional[ExecutionContext] = None,
        check_policies: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List registered tools
        
        Args:
            category: Filter by category
            tags: Filter by tags (matches any)
            enabled_only: Only show enabled tools
            context: Optional execution context for policy checks
            check_policies: Whether to check policies for each tool
            
        Returns:
            List of tool information dictionaries
        """
        results = []
        
        with self._lock:
            for name, registration in self._tools.items():
                # Apply filters
                if enabled_only and not registration.is_enabled:
                    continue
                
                if category and registration.metadata.category != category:
                    continue
                
                if tags and not any(tag in registration.tags for tag in tags):
                    continue
                
                # Check policies if requested
                is_allowed = True
                policy_reason = None
                if check_policies and self._controller and context:
                    # Convert ExecutionContext to dict for controller
                    context_dict = {
                        "user": context.user.__dict__ if context.user else {},
                        "task": context.task.__dict__ if context.task else {},
                        "environment": (
                            context.environment.__dict__
                            if context.environment else {}
                        )
                    }
                    is_allowed, policy_reason = self._controller.can_use_tool(
                        name, context_dict
                    )
                
                # Build tool info
                info = {
                    "name": name,
                    "version": registration.metadata.version,
                    "description": registration.metadata.description,
                    "category": registration.metadata.category.value,
                    "tags": list(registration.tags),
                    "is_singleton": registration.is_singleton,
                    "is_enabled": registration.is_enabled,
                    "is_instantiated": registration.instance is not None,
                    "use_count": registration.use_count,
                    "registered_at": registration.registered_at.isoformat(),
                    "last_used": (
                        registration.last_used.isoformat()
                        if registration.last_used else None
                    )
                }
                
                # Add policy info if checked
                if check_policies:
                    info["is_allowed"] = is_allowed
                    if not is_allowed:
                        info["policy_reason"] = policy_reason
                
                # Add instance status if available
                if registration.instance:
                    info["status"] = registration.instance.status.value
                    info["is_ready"] = registration.instance.is_ready
                
                results.append(info)
        
        return results
    
    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool"""
        with self._lock:
            if name in self._tools:
                return self._tools[name].metadata
        return None
    
    def discover_tools_from_paths(
        self,
        paths: List[str],
        patterns: Optional[List[str]] = None,
        recursive: bool = True,
        auto_register: bool = True
    ) -> Dict[str, Any]:
        """
        Discover tools from filesystem paths
        
        Args:
            paths: List of directory paths to search
            patterns: File patterns to match
            recursive: Whether to search recursively
            auto_register: Whether to automatically register discovered tools
            
        Returns:
            Discovery summary
        """
        results = self._discovery.discover_from_paths(
            paths, patterns, recursive
        )
        
        if auto_register:
            registered, failed = self._discovery.register_discovered_tools(
                results
            )
            return {
                'discovered': len(results),
                'registered': registered,
                'failed': failed,
                'paths': paths
            }
        
        return {
            'discovered': len(results),
            'results': results
        }
    
    def discover_tools_from_packages(
        self,
        entry_point_group: Optional[str] = None,
        auto_register: bool = True
    ) -> Dict[str, Any]:
        """
        Discover tools from installed packages
        
        Args:
            entry_point_group: Entry point group name
            auto_register: Whether to automatically register
            
        Returns:
            Discovery summary
        """
        results = self._discovery.discover_from_packages(entry_point_group)
        
        if auto_register:
            registered, failed = self._discovery.register_discovered_tools(
                results
            )
            return {
                'discovered': len(results),
                'registered': registered,
                'failed': failed
            }
        
        return {
            'discovered': len(results),
            'results': results
        }
    
    def load_tools_from_config(
        self,
        config_path: str,
        base_path: Optional[str] = None,
        auto_register: bool = True
    ) -> Dict[str, Any]:
        """
        Load tools from configuration file
        
        Args:
            config_path: Path to configuration file
            base_path: Base path for relative imports
            auto_register: Whether to automatically register
            
        Returns:
            Discovery summary
        """
        results = self._discovery.discover_from_config(
            config_path, base_path
        )
        
        if auto_register:
            registered, failed = self._discovery.register_discovered_tools(
                results
            )
            return {
                'discovered': len(results),
                'registered': registered,
                'failed': failed,
                'config_path': config_path
            }
        
        return {
            'discovered': len(results),
            'results': results
        }
    
    def discover_all(
        self,
        paths: Optional[List[str]] = None,
        discover_packages: bool = True,
        config_files: Optional[List[str]] = None,
        auto_register: bool = True
    ) -> Dict[str, Any]:
        """
        Discover tools from all sources
        
        Args:
            paths: Filesystem paths to search
            discover_packages: Whether to discover from packages
            config_files: Configuration files to load
            auto_register: Whether to automatically register
            
        Returns:
            Combined discovery summary
        """
        return self._discovery.discover_and_register_all(
            paths=paths,
            discover_packages=discover_packages,
            config_files=config_files,
            auto_enable=auto_register
        )
    
    def validate_tool_class(
        self,
        tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """
        Validate a tool class before registration
        
        Args:
            tool_class: Tool class to validate
            
        Returns:
            Validation result
        """
        return self._loader.validate_tool(tool_class)
    
    def load_and_register_tool(
        self,
        module_path: str,
        class_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> bool:
        """
        Load and register a tool from module path
        
        Args:
            module_path: Module or file path
            class_name: Optional class name
            config: Optional configuration
            tool_name: Optional name override
            
        Returns:
            True if successfully registered
        """
        return self._loader.load_and_register(
            module_path, class_name, config, tool_name
        )
    
    # Keep the old discover_tools method for backward compatibility
    def discover_tools(self, path: Path, pattern: str = "*_tool.py"):
        """
        Discover and register tools from a directory (legacy method)
        
        Args:
            path: Directory to search
            pattern: File pattern to match
        """
        logger.warning(
            "discover_tools is deprecated. "
            "Use discover_tools_from_paths instead"
        )
        self.discover_tools_from_paths(
            [str(path)], [pattern], recursive=True, auto_register=True
        )
    
    def enable_tool(self, name: str) -> bool:
        """Enable a tool"""
        with self._lock:
            if name in self._tools:
                self._tools[name].is_enabled = True
                return True
        return False
    
    def disable_tool(self, name: str) -> bool:
        """Disable a tool"""
        with self._lock:
            if name in self._tools:
                self._tools[name].is_enabled = False
                # Shutdown instance if exists
                reg = self._tools[name]
                if reg.instance:
                    try:
                        reg.instance.shutdown()
                        reg.instance = None
                    except Exception as e:
                        logger.error(
                            f"Error shutting down tool '{name}': {e}"
                        )
                return True
        return False
    
    def add_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[ToolEvent], None]
    ):
        """Add a global event handler"""
        self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[ToolEvent], None]
    ):
        """Remove a global event handler"""
        if event_type in self._event_handlers:
            handlers = self._event_handlers[event_type]
            if handler in handlers:
                handlers.remove(handler)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        with self._lock:
            total_tools = len(self._tools)
            enabled_tools = sum(
                1 for r in self._tools.values() if r.is_enabled
            )
            instantiated_tools = sum(
                1 for r in self._tools.values() if r.instance
            )
            
            category_counts = {
                cat.value: len(tools) 
                for cat, tools in self._categories.items()
            }
            
            most_used = sorted(
                self._tools.items(),
                key=lambda x: x[1].use_count,
                reverse=True
            )[:5]
            
            return {
                "total_tools": total_tools,
                "enabled_tools": enabled_tools,
                "instantiated_tools": instantiated_tools,
                "categories": category_counts,
                "most_used_tools": [
                    {
                        "name": name,
                        "use_count": reg.use_count,
                        "last_used": (
                            reg.last_used.isoformat() 
                            if reg.last_used else None
                        )
                    }
                    for name, reg in most_used
                ],
                "discovery_paths": [str(p) for p in self._discovery_paths],
                "loader_errors": len(self._loader.get_errors())
            }
    
    def export_config(self, path: Path):
        """Export registry configuration"""
        config = {
            "tools": {},
            "discovery_paths": [str(p) for p in self._discovery_paths]
        }
        
        with self._lock:
            for name, registration in self._tools.items():
                config["tools"][name] = {
                    "class": (
                        f"{registration.tool_class.__module__}."
                        f"{registration.tool_class.__name__}"
                    ),
                    "config": registration.config,
                    "is_singleton": registration.is_singleton,
                    "is_enabled": registration.is_enabled,
                    "tags": list(registration.tags)
                }
        
        with open(path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def import_config(self, path: Path):
        """Import registry configuration"""
        with open(path, 'r') as f:
            config = json.load(f)
        
        # Add discovery paths
        for path_str in config.get("discovery_paths", []):
            self._discovery_paths.append(Path(path_str))
        
        # Register tools
        for name, tool_config in config.get("tools", {}).items():
            try:
                # Import tool class
                module_path, class_name = tool_config["class"].rsplit('.', 1)
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                
                # Register tool
                self.register_tool(
                    tool_class,
                    name=name,
                    config=tool_config.get("config", {}),
                    is_singleton=tool_config.get("is_singleton", True),
                    tags=tool_config.get("tags", [])
                )
                
                # Set enabled state
                if not tool_config.get("is_enabled", True):
                    self.disable_tool(name)
                    
            except Exception as e:
                logger.error(f"Failed to import tool '{name}': {e}")
    
    def shutdown(self):
        """Shutdown all tools and cleanup"""
        logger.info("Shutting down tool registry...")
        
        with self._lock:
            # Shutdown all tool instances
            for name, registration in self._tools.items():
                if registration.instance:
                    try:
                        registration.instance.shutdown()
                    except Exception as e:
                        logger.error(
                            f"Error shutting down tool '{name}': {e}"
                        )
            
            # Clear registry
            self._tools.clear()
            self._categories.clear()
            self._tags.clear()
            self._event_handlers.clear()
            self._discovery_paths.clear()
        
        logger.info("Tool registry shutdown complete")
    
    def _auto_register_basic_tools(self):
        """
        Automatically register function-based tools from basic_tools module
        
        This method bridges the gap between legacy function-based tools
        and the new class-based tool system by automatically wrapping
        and registering all tools from basic_tools.AVAILABLE_TOOLS.
        """
        try:
            # Import function wrapper and basic tools
            from .function_wrapper import wrap_available_tools
            from .basic_tools import AVAILABLE_TOOLS
            
            logger.info(
                f"Auto-registering {len(AVAILABLE_TOOLS)} "
                f"function-based tools..."
            )
            
            # Wrap all available tools
            wrapped_tools = wrap_available_tools(AVAILABLE_TOOLS)
            
            # Register each wrapped tool
            registered_count = 0
            for tool_name, wrapped_tool in wrapped_tools.items():
                try:
                    # Register the wrapped tool instance directly
                    success = self.register_tool_instance(
                        wrapped_tool,
                        name=tool_name
                    )
                    if success:
                        registered_count += 1
                        logger.debug(f"Auto-registered tool: {tool_name}")
                    else:
                        logger.warning(
                            f"Failed to auto-register tool: {tool_name}"
                        )
                except Exception as e:
                    logger.error(
                        f"Error auto-registering tool '{tool_name}': {e}"
                    )
            
            logger.info(
                f"Successfully auto-registered {registered_count}/"
                f"{len(AVAILABLE_TOOLS)} function-based tools"
            )
            
        except ImportError as e:
            logger.warning(
                f"Could not import basic_tools for auto-registration: {e}"
            )
        except Exception as e:
            logger.error(f"Error during auto-registration: {e}")
    
    def register_tool_instance(
        self,
        tool_instance: BaseTool,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Register an already instantiated tool
        
        Args:
            tool_instance: The tool instance to register
            name: Optional name override
            tags: Optional additional tags
            
        Returns:
            True if successfully registered
        """
        try:
            if not tool_instance.metadata:
                logger.error(
                    f"Tool instance {tool_instance.__class__.__name__} "
                    f"has no metadata"
                )
                return False
            
            # Use provided name or metadata name
            tool_name = name or tool_instance.metadata.name
            
            # Check if already registered
            if tool_name in self._tools:
                logger.warning(
                    f"Tool '{tool_name}' is already registered"
                )
                return False
            
            # Create registration with existing instance
            registration = ToolRegistration(
                tool_class=tool_instance.__class__,
                metadata=tool_instance.metadata,
                instance=tool_instance,  # Use existing instance
                config={},
                is_singleton=True,  # Mark as singleton since we have instance
                tags=set(tags or [])
            )
            
            # Add metadata tags
            registration.tags.update(tool_instance.metadata.tags)
            
            # Register the tool
            with self._lock:
                self._tools[tool_name] = registration
                category = tool_instance.metadata.category
                self._categories[category].add(tool_name)
                
                # Update tag index
                for tag in registration.tags:
                    self._tags[tag].add(tool_name)
            
            # Connect tool events
            self._connect_tool_events(tool_instance)
            
            logger.info(
                f"Registered tool instance '{tool_name}' "
                f"(category: {tool_instance.metadata.category.value})"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to register tool instance "
                f"{tool_instance.__class__.__name__}: {e}"
            )
            return False

    def set_controller(self, controller: Optional[ToolController]):
        """
        Set the tool controller for policy enforcement
        
        Args:
            controller: ToolController instance or None to disable
        """
        self._controller = controller
        logger.info(
            f"Tool controller {'set' if controller else 'removed'} "
            f"for registry"
        )
    
    def get_controller(self) -> Optional[ToolController]:
        """Get the current tool controller"""
        return self._controller
    
    def get_tools_for_context(
        self,
        context: ExecutionContext,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get tools allowed for a specific context
        
        Args:
            context: Execution context
            category: Optional category filter
            tags: Optional tag filter
            
        Returns:
            List of allowed tool information
        """
        # Get all tools with policy checking enabled
        all_tools = self.list_tools(
            category=category,
            tags=tags,
            enabled_only=True,
            context=context,
            check_policies=True
        )
        
        # Filter to only allowed tools
        return [
            tool for tool in all_tools
            if tool.get("is_allowed", True)
        ]
    
    def get_tool_recommendations(
        self,
        context: ExecutionContext,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get tool recommendations for a context
        
        Args:
            context: Execution context
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended tools with scores
        """
        if not self._controller:
            # Without controller, return most used tools
            with self._lock:
                sorted_tools = sorted(
                    self._tools.items(),
                    key=lambda x: x[1].use_count,
                    reverse=True
                )[:limit]
                
                return [
                    {
                        "name": name,
                        "score": 1.0,
                        "reason": f"Used {reg.use_count} times",
                        "metadata": {
                            "category": reg.metadata.category.value,
                            "description": reg.metadata.description
                        }
                    }
                    for name, reg in sorted_tools
                    if reg.is_enabled
                ]
        
        # Get recommendations from controller
        # Build context dict from ExecutionContext
        context_dict = {
            "user": context.user.__dict__ if context.user else {},
            "task": context.task.__dict__ if context.task else {},
            "environment": (
                context.environment.__dict__ if context.environment else {}
            )
        }
        
        # Get task description
        task_description = ""
        if context.task:
            task_description = getattr(
                context.task, 'description',
                getattr(context.task, 'name', '')
            )
        
        # Get recommendations
        result = self._controller.recommend_tools(
            task_description or "General task",
            context_dict,
            max_recommendations=limit
        )
        
        # Format recommendations
        recommendations = []
        for tool_name in result.selected_tools:
            if tool_name in result.scores:
                score_info = result.scores[tool_name]
                reg = self._tools.get(tool_name)
                if reg:
                    recommendations.append({
                        "name": tool_name,
                        "score": score_info.total_score,
                        "reason": ", ".join(score_info.reasons),
                        "metadata": {
                            "category": reg.metadata.category.value,
                            "description": reg.metadata.description
                        }
                    })
        
        return recommendations


# Global registry instance
registry = ToolRegistry()