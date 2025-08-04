"""
Models package for the Pseudocode Translator

This package provides a flexible plugin-based architecture for managing
multiple language models. It supports automatic model discovery, registration,
and seamless switching between different model implementations.
"""

# Import existing models.py classes for backward compatibility
import sys
from pathlib import Path

# Get the parent directory and import from models.py
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from models import (  # noqa: F401
        BlockType, CodeBlock, ParseError, ParseResult
    )
    __all__ = ['BlockType', 'CodeBlock', 'ParseError', 'ParseResult']
except ImportError:
    # If models.py doesn't exist in parent, these will be defined here later
    __all__ = []

# Remove the parent from sys.path to avoid conflicts
sys.path.pop(0)

# Future imports for the new model system (will be added as files are created)
try:
    from .base import (  # noqa: F401
        BaseModel, ModelCapabilities, ModelFormat
    )
    __all__.extend(['BaseModel', 'ModelCapabilities', 'ModelFormat'])
except ImportError:
    pass

try:
    from .registry import ModelRegistry, register_model  # noqa: F401
    __all__.extend(['ModelRegistry', 'register_model'])
except ImportError:
    pass

try:
    from .manager import ModelManager  # noqa: F401
    __all__.append('ModelManager')
except ImportError:
    pass

try:
    from .downloader import ModelDownloader  # noqa: F401
    __all__.append('ModelDownloader')
except ImportError:
    pass


# Auto-discover and register all available models (when ready)
def auto_discover_models():
    """Auto-discover and register model implementations"""
    import importlib
    import pkgutil
    import logging
    
    package_dir = Path(__file__).parent
    
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name not in ['base', 'registry', 'manager', 'downloader']:
            try:
                importlib.import_module(f'.{module_name}', package=__name__)
            except ImportError as e:
                logging.debug(f"Model module '{module_name}' not ready: {e}")


# Call auto-discover when registry is available
try:
    from .registry import ModelRegistry  # noqa: F401, F811
    auto_discover_models()
except ImportError:
    pass