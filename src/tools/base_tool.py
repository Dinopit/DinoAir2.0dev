"""
Base Tool Module

This module provides the base class and metadata for all tools in the system.
Tools can be executed with or without AI assistance.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional

from .abstraction.model_interface import ModelInterface


class ExecutionMode(Enum):
    """Tool execution modes"""
    STANDALONE = "standalone"  # No AI assistance
    AI_ASSISTED = "ai_assisted"  # AI helps with execution
    AI_GUIDED = "ai_guided"  # AI guides the process
    HYBRID = "hybrid"  # Mix of AI and standalone


@dataclass
class ToolMetadata:
    """Metadata for a tool"""
    name: str
    description: str
    version: str
    author: str
    supported_modes: List[ExecutionMode]
    tags: Optional[List[str]] = None
    documentation_url: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BaseTool(ABC):
    """
    Abstract base class for all tools
    
    Tools can operate independently or with AI assistance based on
    the execution mode and availability of model interface.
    """
    
    def __init__(self, 
                 metadata: ToolMetadata,
                 model_interface: Optional[ModelInterface] = None):
        """
        Initialize base tool
        
        Args:
            metadata: Tool metadata
            model_interface: Optional AI model interface
        """
        self.metadata = metadata
        self.model_interface = model_interface
        self._config = {}
        
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Execution result dictionary
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate tool configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        pass
    
    def set_model_interface(self, model_interface: ModelInterface):
        """Set or update the model interface"""
        self.model_interface = model_interface
        
    def update_config(self, config: Dict[str, Any]):
        """Update tool configuration"""
        self._config.update(config)
        
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return self.metadata
        
    def supports_mode(self, mode: ExecutionMode) -> bool:
        """Check if tool supports a specific execution mode"""
        return mode in self.metadata.supported_modes
        
    def can_execute_standalone(self) -> bool:
        """Check if tool can execute without AI"""
        return ExecutionMode.STANDALONE in self.metadata.supported_modes
        
    def requires_ai(self) -> bool:
        """Check if tool requires AI to function"""
        return (ExecutionMode.STANDALONE not in
                self.metadata.supported_modes and
                len(self.metadata.supported_modes) > 0)