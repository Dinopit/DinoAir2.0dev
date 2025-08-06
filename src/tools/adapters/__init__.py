"""
Model Adapters Module

This module provides adapters for various AI model providers
to work with the tool system's abstraction layer.
"""

from .base_adapter import (
    BaseModelAdapter, AdapterConfig, AdapterType, StreamChunk
)
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .ollama_adapter import OllamaAdapter

__all__ = [
    'BaseModelAdapter',
    'AdapterConfig',
    'AdapterType',
    'StreamChunk',
    'OpenAIAdapter',
    'AnthropicAdapter',
    'OllamaAdapter'
]


# Factory function for creating adapters
def create_adapter(
    adapter_type: AdapterType,
    config: AdapterConfig
) -> BaseModelAdapter:
    """
    Factory function to create the appropriate adapter
    
    Args:
        adapter_type: Type of adapter to create
        config: Adapter configuration
        
    Returns:
        Configured adapter instance
        
    Raises:
        ValueError: If adapter type is not supported
    """
    adapters = {
        AdapterType.OPENAI: OpenAIAdapter,
        AdapterType.ANTHROPIC: AnthropicAdapter,
        AdapterType.OLLAMA: OllamaAdapter
    }
    
    adapter_class = adapters.get(adapter_type)
    if not adapter_class:
        raise ValueError(f"Unsupported adapter type: {adapter_type}")
        
    return adapter_class(config)