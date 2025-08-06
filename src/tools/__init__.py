"""
Tools Package - Core tool system infrastructure

This package provides the foundation for creating and managing tools
in the DinoAir system, including:
- Base classes for tool implementation
- Tool registry for discovery and management
- Dynamic tool discovery and loading
- AI adapter for model integration
- Schema validation utilities
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Core infrastructure
from .base import (
    BaseTool,
    AsyncBaseTool,
    CompositeTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolProgress,
    ToolStatus,
    ToolCategory,
    ParameterType,
    ToolEvent,
    ToolLifecycleEvent
)

# Registry system
from .registry import (
    ToolRegistry,
    ToolRegistration,
    registry  # Global registry instance
)

# Discovery and loading
from .discovery import (
    ToolDiscovery,
    DiscoveryResult,
    discover_tools
)

from .loader import (
    ToolLoader,
    ValidationResult,
    LoaderError,
    load_tool,
    validate_tool
)

# AI integration
from .ai_adapter import (
    ToolAIAdapter,
    ToolSchema,
    ToolFormatter,
    StandardToolFormatter,
    create_tool_context,
    execute_ai_tool_request
)

# Existing tools (keep for backward compatibility)
try:
    from .pseudocode_tool import PseudocodeTool
except ImportError:
    PseudocodeTool = None

__all__ = [
    # Base classes
    'BaseTool',
    'AsyncBaseTool',
    'CompositeTool',
    'ToolMetadata',
    'ToolParameter',
    'ToolResult',
    'ToolProgress',
    'ToolStatus',
    'ToolCategory',
    'ParameterType',
    'ToolEvent',
    'ToolLifecycleEvent',
    
    # Registry
    'ToolRegistry',
    'ToolRegistration',
    'registry',
    
    # Discovery and Loading
    'ToolDiscovery',
    'DiscoveryResult',
    'discover_tools',
    'ToolLoader',
    'ValidationResult',
    'LoaderError',
    'load_tool',
    'validate_tool',
    
    # AI Adapter
    'ToolAIAdapter',
    'ToolSchema',
    'ToolFormatter',
    'StandardToolFormatter',
    'create_tool_context',
    'execute_ai_tool_request',
    
    # Tools
    'PseudocodeTool',
    
    # Auto-discovery function
    'auto_discover_tools'
]

# Version information
__version__ = '2.0.0'

# Setup logging
logger = logging.getLogger(__name__)


def auto_discover_tools(
    config_path: Optional[str] = None,
    discover_examples: bool = True,
    discover_packages: bool = True,
    auto_register: bool = True
) -> Dict[str, Any]:
    """
    Automatically discover and register tools
    
    Args:
        config_path: Optional path to configuration file
        discover_examples: Whether to discover example tools
        discover_packages: Whether to discover from installed packages
        auto_register: Whether to automatically register discovered tools
        
    Returns:
        Summary of discovered and registered tools
    """
    summary = {
        'config': None,
        'examples': None,
        'packages': None,
        'total': {'discovered': 0, 'registered': 0, 'failed': 0}
    }
    
    # Load from configuration file
    if config_path and Path(config_path).exists():
        logger.info(f"Loading tools from config: {config_path}")
        summary['config'] = registry.load_tools_from_config(
            config_path, auto_register=auto_register
        )
        summary['total']['discovered'] += summary['config'].get(
            'discovered', 0
        )
        summary['total']['registered'] += summary['config'].get(
            'registered', 0
        )
        summary['total']['failed'] += summary['config'].get('failed', 0)
    
    # Discover example tools
    if discover_examples:
        examples_path = Path(__file__).parent / 'examples'
        if examples_path.exists():
            logger.info(f"Discovering example tools from: {examples_path}")
            summary['examples'] = registry.discover_tools_from_paths(
                [str(examples_path)],
                patterns=['*_tool.py'],
                recursive=True,
                auto_register=auto_register
            )
            summary['total']['discovered'] += summary['examples'].get(
                'discovered', 0
            )
            summary['total']['registered'] += summary['examples'].get(
                'registered', 0
            )
            summary['total']['failed'] += summary['examples'].get('failed', 0)
    
    # Discover from installed packages
    if discover_packages:
        logger.info("Discovering tools from installed packages")
        summary['packages'] = registry.discover_tools_from_packages(
            auto_register=auto_register
        )
        summary['total']['discovered'] += summary['packages'].get(
            'discovered', 0
        )
        summary['total']['registered'] += summary['packages'].get(
            'registered', 0
        )
        summary['total']['failed'] += summary['packages'].get('failed', 0)
    
    logger.info(
        f"Tool discovery complete: "
        f"{summary['total']['discovered']} discovered, "
        f"{summary['total']['registered']} registered, "
        f"{summary['total']['failed']} failed"
    )
    
    return summary


# Optional: Auto-discover tools on import
# Controlled by environment variable
if os.environ.get('DINOAIR_AUTO_DISCOVER_TOOLS', '').lower() == 'true':
    logger.info("Auto-discovering tools on import")
    auto_discover_tools()
