"""
Tool Abstraction Layer

This module provides the abstraction layer for separating tool logic
from AI model implementations, ensuring tools can function independently
of specific AI models.
"""

from .model_interface import (
    ModelInterface,
    StandardModelAdapter,
    ModelCapabilities,
    ModelRequest,
    ModelResponse
)

__all__ = [
    'ModelInterface',
    'StandardModelAdapter', 
    'ModelCapabilities',
    'ModelRequest',
    'ModelResponse'
]