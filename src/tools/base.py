"""
Base Tool System Infrastructure

This module provides the foundation for all tools in the DinoAir system,
including abstract base classes, metadata structures, and common functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Callable, Union,
    TypeVar, Tuple
)
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio
import threading
from pathlib import Path


logger = logging.getLogger(__name__)


# Type variables for generic type support
T = TypeVar('T')
ToolType = TypeVar('ToolType', bound='BaseTool')


class ToolCategory(Enum):
    """Categories for tool classification"""
    TRANSFORMATION = "transformation"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    UTILITY = "utility"
    INTEGRATION = "integration"
    SYSTEM = "system"
    DEBUG = "debug"
    CUSTOM = "custom"


class ToolStatus(Enum):
    """Status of a tool operation"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SHUTTING_DOWN = "shutting_down"


class ParameterType(Enum):
    """Types of tool parameters"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE_PATH = "file_path"
    URL = "url"
    ENUM = "enum"
    ANY = "any"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    example: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate a value against this parameter definition
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if required and None
        if value is None:
            if self.required:
                return False, f"Required parameter '{self.name}' is missing"
            return True, None
            
        # Type validation
        type_validators = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int),
            ParameterType.FLOAT: lambda v: isinstance(v, (int, float)),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.ARRAY: lambda v: isinstance(v, list),
            ParameterType.OBJECT: lambda v: isinstance(v, dict),
            ParameterType.FILE_PATH: lambda v: (
                isinstance(v, str) and Path(v).exists()
            ),
            ParameterType.URL: lambda v: (
                isinstance(v, str) and
                v.startswith(('http://', 'https://'))
            ),
            ParameterType.ANY: lambda v: True
        }
        
        validator = type_validators.get(self.type)
        if validator and not validator(value):
            return False, (
                f"Parameter '{self.name}' must be of type {self.type.value}"
            )
            
        # Enum validation
        if self.enum_values and value not in self.enum_values:
            return False, (
                f"Parameter '{self.name}' must be one of {self.enum_values}"
            )
            
        # Range validation
        if self.min_value is not None and value < self.min_value:
            return False, (
                f"Parameter '{self.name}' must be >= {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            return False, (
                f"Parameter '{self.name}' must be <= {self.max_value}"
            )
            
        return True, None


@dataclass
class ToolResult:
    """Result of a tool operation"""
    success: bool
    output: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ToolStatus = ToolStatus.COMPLETED
    execution_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "success": self.success,
            "output": self.output,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ToolProgress:
    """Progress information for a tool operation"""
    percentage: float
    message: str
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    current_step_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolMetadata:
    """Metadata for a tool"""
    name: str
    version: str
    description: str
    author: str
    category: ToolCategory
    tags: List[str] = field(default_factory=list)
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    repository_url: Optional[str] = None
    license: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parameters: List[ToolParameter] = field(default_factory=list)
    capabilities: Dict[str, bool] = field(default_factory=dict)
    examples: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "tags": self.tags,
            "icon": self.icon,
            "documentation_url": self.documentation_url,
            "repository_url": self.repository_url,
            "license": self.license,
            "dependencies": self.dependencies,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum_values": p.enum_values,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "pattern": p.pattern,
                    "example": p.example,
                    "metadata": p.metadata
                }
                for p in self.parameters
            ],
            "capabilities": self.capabilities,
            "examples": self.examples,
            "metadata": self.metadata
        }
    
    def validate_parameters(
        self, params: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate parameters against metadata definitions
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check required parameters
        for param_def in self.parameters:
            if param_def.required and param_def.name not in params:
                errors.append(
                    f"Required parameter '{param_def.name}' is missing"
                )
                continue
                
            if param_def.name in params:
                is_valid, error = param_def.validate(params[param_def.name])
                if not is_valid:
                    errors.append(error)
                    
        # Check for unknown parameters
        known_params = {p.name for p in self.parameters}
        unknown_params = set(params.keys()) - known_params
        if unknown_params:
            errors.append(f"Unknown parameters: {', '.join(unknown_params)}")
            
        return len(errors) == 0, errors


class ToolEvent:
    """Base class for tool events"""
    def __init__(
        self, tool_name: str, event_type: str,
        data: Optional[Dict[str, Any]] = None
    ):
        self.tool_name = tool_name
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = datetime.now()


class ToolLifecycleEvent(ToolEvent):
    """Events related to tool lifecycle"""
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    STATE_CHANGED = "state_changed"


class BaseTool(ABC):
    """
    Abstract base class for all tools in the DinoAir system
    
    This class provides the foundation for implementing tools with
    standardized interfaces, lifecycle management, and event handling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base tool
        
        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self._status = ToolStatus.INITIALIZING
        self._metadata: Optional[ToolMetadata] = None
        self._lock = threading.RLock()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._progress_callbacks: List[Callable[[ToolProgress], None]] = []
        self._operation_count = 0
        self._start_time = datetime.now()
        
        # Initialize the tool
        self._initialize()
        
    def _initialize(self):
        """Initialize the tool"""
        try:
            # Create metadata
            self._metadata = self._create_metadata()
            
            # Perform tool-specific initialization
            self.initialize()
            
            # Update status
            self._set_status(ToolStatus.READY)
            
            # Emit initialized event
            self._emit_event(ToolLifecycleEvent(
                self.name,
                ToolLifecycleEvent.INITIALIZED,
                {"metadata": self._metadata.to_dict()}
            ))
            
        except Exception as e:
            logger.error(
                f"Failed to initialize tool {self.__class__.__name__}: {e}"
            )
            self._set_status(ToolStatus.FAILED)
            raise
    
    @abstractmethod
    def _create_metadata(self) -> ToolMetadata:
        """
        Create tool metadata
        
        This method must be implemented by subclasses to provide
        tool-specific metadata.
        
        Returns:
            ToolMetadata instance
        """
        pass
    
    @abstractmethod
    def initialize(self):
        """
        Perform tool-specific initialization
        
        This method is called during tool construction and should
        set up any resources needed by the tool.
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool's main operation
        
        This method must be implemented by subclasses to perform
        the tool's primary function.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult instance
        """
        pass
    
    @abstractmethod
    def shutdown(self):
        """
        Cleanup tool resources
        
        This method is called when the tool is being shut down
        and should release any resources held by the tool.
        """
        pass
    
    @property
    def name(self) -> str:
        """Get tool name"""
        return (
            self._metadata.name if self._metadata
            else self.__class__.__name__
        )
    
    @property
    def version(self) -> str:
        """Get tool version"""
        return self._metadata.version if self._metadata else "0.0.0"
    
    @property
    def metadata(self) -> Optional[ToolMetadata]:
        """Get tool metadata"""
        return self._metadata
    
    @property
    def status(self) -> ToolStatus:
        """Get current tool status"""
        with self._lock:
            return self._status
    
    @property
    def is_ready(self) -> bool:
        """Check if tool is ready for use"""
        return self.status == ToolStatus.READY
    
    @property
    def is_running(self) -> bool:
        """Check if tool is currently running"""
        return self.status == ToolStatus.RUNNING
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get tool configuration"""
        return self._config.copy()
    
    def _set_status(self, status: ToolStatus):
        """Set tool status and emit event"""
        with self._lock:
            old_status = self._status
            self._status = status
            
        if old_status != status:
            self._emit_event(ToolLifecycleEvent(
                self.name,
                ToolLifecycleEvent.STATE_CHANGED,
                {"old_status": old_status.value, "new_status": status.value}
            ))
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update tool configuration
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        with self._lock:
            self._config.update(config_updates)
            self._on_config_updated(config_updates)
    
    def _on_config_updated(self, updates: Dict[str, Any]):
        """
        Handle configuration updates
        
        Override this method to respond to configuration changes.
        
        Args:
            updates: Dictionary of configuration updates
        """
        pass
    
    def validate_parameters(
        self, params: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate parameters before execution
        
        Args:
            params: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        if not self._metadata:
            return True, []
        return self._metadata.validate_parameters(params)
    
    def add_progress_callback(self, callback: Callable[[ToolProgress], None]):
        """Add a progress callback"""
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
    
    def remove_progress_callback(
        self, callback: Callable[[ToolProgress], None]
    ):
        """Remove a progress callback"""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def _report_progress(self, progress: ToolProgress):
        """Report progress to all callbacks"""
        for callback in self._progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _emit_event(self, event: ToolEvent):
        """Emit an event to registered handlers"""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def add_event_handler(
        self, event_type: str, handler: Callable[[ToolEvent], None]
    ):
        """Add an event handler"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        if handler not in self._event_handlers[event_type]:
            self._event_handlers[event_type].append(handler)
    
    def remove_event_handler(
        self, event_type: str, handler: Callable[[ToolEvent], None]
    ):
        """Remove an event handler"""
        if (event_type in self._event_handlers and
                handler in self._event_handlers[event_type]):
            self._event_handlers[event_type].remove(handler)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        uptime = (datetime.now() - self._start_time).total_seconds()
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "operation_count": self._operation_count,
            "uptime_seconds": uptime,
            "start_time": self._start_time.isoformat()
        }
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"version='{self.version}', status={self.status.value})"
        )


class AsyncBaseTool(BaseTool):
    """
    Async version of BaseTool for tools that need async operations
    
    This class extends BaseTool to provide async execution capabilities
    while maintaining compatibility with the synchronous interface.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize async base tool"""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._executor = None
        super().__init__(config)
    
    def initialize(self):
        """Initialize async resources"""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create one for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        self._executor = self._loop.run_in_executor
        self.initialize_async()
    
    @abstractmethod
    def initialize_async(self):
        """Perform async tool-specific initialization"""
        pass
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute synchronously by running async method"""
        if self._loop and self._loop.is_running():
            # If we're already in an async context, run in thread pool
            coro = self.execute_async(**kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result()
        else:
            # Otherwise, run in a new event loop
            return asyncio.run(self.execute_async(**kwargs))
    
    @abstractmethod
    async def execute_async(self, **kwargs) -> ToolResult:
        """
        Execute the tool's main operation asynchronously
        
        This method must be implemented by subclasses to perform
        the tool's primary function asynchronously.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult instance
        """
        pass
    
    async def shutdown_async(self):
        """Async cleanup hook"""
        pass
    
    def shutdown(self):
        """Cleanup tool resources"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.shutdown_async(), self._loop
            ).result()
        else:
            asyncio.run(self.shutdown_async())
        
        # Clean up event loop if we created it
        if self._loop and not self._loop.is_running():
            self._loop.close()


class CompositeTool(BaseTool):
    """
    Base class for tools that compose multiple sub-tools
    
    This allows creating complex tools that orchestrate multiple
    simpler tools to accomplish more sophisticated tasks.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize composite tool"""
        self._sub_tools: Dict[str, BaseTool] = {}
        super().__init__(config)
    
    def add_sub_tool(self, name: str, tool: BaseTool):
        """Add a sub-tool"""
        self._sub_tools[name] = tool
    
    def remove_sub_tool(self, name: str):
        """Remove a sub-tool"""
        if name in self._sub_tools:
            self._sub_tools[name].shutdown()
            del self._sub_tools[name]
    
    def get_sub_tool(self, name: str) -> Optional[BaseTool]:
        """Get a sub-tool by name"""
        return self._sub_tools.get(name)
    
    def shutdown(self):
        """Shutdown all sub-tools"""
        for tool in self._sub_tools.values():
            try:
                tool.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down sub-tool: {e}")
        self._sub_tools.clear()