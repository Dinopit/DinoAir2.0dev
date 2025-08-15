"""
Models package for the Pseudocode Translator

This package provides a flexible plugin-based architecture for managing
multiple language models. It supports automatic model discovery, registration,
and seamless switching between different model implementations.
"""

# Import existing models.py classes for backward compatibility
import sys
import os
from pathlib import Path

try:
    # Try importing from the parent directory's models.py
    parent_path = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, parent_path)
    from models import (  # noqa: F401
        BlockType, CodeBlock, ParseError, ParseResult
    )
    __all__ = ['BlockType', 'CodeBlock', 'ParseError', 'ParseResult']
except ImportError:
    # If import fails, create placeholder classes to prevent crashes
    from enum import Enum
    from dataclasses import dataclass
    from typing import Optional, Dict, Any, Tuple, List
    
    class BlockType(Enum):
        ENGLISH = "english"
        PYTHON = "python"
        MIXED = "mixed"
        COMMENT = "comment"
    
    @dataclass
    class CodeBlock:
        type: BlockType
        content: str
        line_numbers: Tuple[int, int]
        metadata: Dict[str, Any]
        context: Optional[str] = None
    
    @dataclass
    class ParseError:
        message: str
        line_number: Optional[int] = None
        block_content: Optional[str] = None
        suggestion: Optional[str] = None
    
    @dataclass
    class ParseResult:
        blocks: List[CodeBlock]
        errors: List[ParseError]
        warnings: List[str]
    
    __all__ = ['BlockType', 'CodeBlock', 'ParseError', 'ParseResult']
finally:
    # Clean up sys.path
    if parent_path in [os.path.normpath(p) for p in sys.path]:
        sys.path.remove(parent_path)

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
except ImportError as e:
    # Log the import error for debugging but don't fail
    import logging
    logging.debug(f"ModelManager import failed: {e}")
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


# Call auto-discover when registry is available (only if needed)
# Comment out for now to avoid import issues
# try:
#     from .registry import ModelRegistry  # noqa: F401, F811
#     auto_discover_models()
# except ImportError:
#     pass