"""
Tool Loader System

This module provides lazy loading and validation of tools, ensuring that
tools are only instantiated when needed and that they meet all requirements
before being registered.
"""

import logging
import importlib
import importlib.util
import inspect
import sys
from typing import Dict, List, Optional, Type, Any, Callable, Tuple, TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass, field
import threading
from contextlib import contextmanager
import traceback

from .base import BaseTool, ToolMetadata, ToolStatus

if TYPE_CHECKING:
    from .registry import ToolRegistry


logger = logging.getLogger(__name__)


@dataclass
class LoaderError:
    """Information about a loading error"""
    tool_name: str
    error_type: str
    message: str
    traceback: Optional[str] = None
    source: Optional[str] = None


@dataclass 
class ValidationResult:
    """Result of tool validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Optional[ToolMetadata] = None


class ToolLoader:
    """
    Tool loader with lazy loading and validation capabilities
    
    This class handles:
    - Lazy loading of tool classes
    - Validation before registration
    - Import error handling
    - Dependency checking
    - Safe instantiation
    """
    
    def __init__(self, registry: Optional['ToolRegistry'] = None):
        """
        Initialize tool loader
        
        Args:
            registry: Optional ToolRegistry to use
        """
        self.registry = registry
        self._loaded_modules: Dict[str, Any] = {}
        self._loading_errors: List[LoaderError] = []
        self._validators: List[
            Callable[[Type[BaseTool]], ValidationResult]
        ] = []
        self._lock = threading.RLock()
        
        # Register default validators
        self._register_default_validators()
        
    def _register_default_validators(self):
        """Register default tool validators"""
        self.add_validator(self._validate_base_class)
        self.add_validator(self._validate_metadata)
        self.add_validator(self._validate_required_methods)
        self.add_validator(self._validate_initialization)
        
    def add_validator(
        self, 
        validator: Callable[[Type[BaseTool]], ValidationResult]
    ):
        """Add a custom validator"""
        if validator not in self._validators:
            self._validators.append(validator)
            
    def remove_validator(
        self,
        validator: Callable[[Type[BaseTool]], ValidationResult]
    ):
        """Remove a validator"""
        if validator in self._validators:
            self._validators.remove(validator)
            
    def load_tool_class(
        self,
        module_path: str,
        class_name: Optional[str] = None,
        reload: bool = False
    ) -> Optional[Type[BaseTool]]:
        """
        Load a tool class from module path
        
        Args:
            module_path: Module path or file path
            class_name: Optional specific class name
            reload: Whether to reload if already loaded
            
        Returns:
            Tool class or None if loading failed
        """
        try:
            if module_path.endswith('.py'):
                # Load from file
                return self._load_from_file(module_path, class_name)
            else:
                # Load from module
                return self._load_from_module(module_path, class_name, reload)
                
        except Exception as e:
            self._record_error(
                tool_name=class_name or module_path,
                error_type="LoadError",
                message=str(e),
                traceback=traceback.format_exc(),
                source=module_path
            )
            logger.error(f"Failed to load tool from {module_path}: {e}")
            return None
            
    def _load_from_file(
        self,
        file_path: str,
        class_name: Optional[str] = None
    ) -> Optional[Type[BaseTool]]:
        """Load tool class from Python file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Tool file not found: {file_path}")
            
        # Create module spec
        module_name = f"_tool_module_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        
        if not spec or not spec.loader:
            raise ImportError(f"Cannot create module spec for {file_path}")
            
        # Load module
        module = importlib.util.module_from_spec(spec)
        
        # Temporarily add to sys.modules
        sys.modules[module_name] = module
        
        try:
            # Execute module
            spec.loader.exec_module(module)
            
            # Find tool class
            return self._find_tool_class(module, class_name)
            
        finally:
            # Clean up sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]
                
    def _load_from_module(
        self,
        module_path: str,
        class_name: Optional[str] = None,
        reload: bool = False
    ) -> Optional[Type[BaseTool]]:
        """Load tool class from module path"""
        with self._lock:
            # Check cache
            if not reload and module_path in self._loaded_modules:
                module = self._loaded_modules[module_path]
            else:
                # Import module
                if reload and module_path in sys.modules:
                    module = importlib.reload(sys.modules[module_path])
                else:
                    module = importlib.import_module(module_path)
                    
                # Cache module
                self._loaded_modules[module_path] = module
                
        # Find tool class
        return self._find_tool_class(module, class_name)
        
    def _find_tool_class(
        self,
        module: Any,
        class_name: Optional[str] = None
    ) -> Optional[Type[BaseTool]]:
        """Find tool class in module"""
        tool_classes = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BaseTool) and 
                    obj != BaseTool and
                    obj.__module__ == module.__name__):
                
                if class_name and name == class_name:
                    return obj
                    
                tool_classes.append(obj)
                
        # Return first tool class if no specific name given
        if tool_classes and not class_name:
            return tool_classes[0]
            
        return None
        
    def validate_tool(
        self,
        tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """
        Validate a tool class
        
        Args:
            tool_class: Tool class to validate
            
        Returns:
            Validation result
        """
        all_errors = []
        all_warnings = []
        metadata = None
        
        # Run all validators
        for validator in self._validators:
            try:
                result = validator(tool_class)
                
                if not result.is_valid:
                    all_errors.extend(result.errors)
                    
                all_warnings.extend(result.warnings)
                
                if result.metadata:
                    metadata = result.metadata
                    
            except Exception as e:
                all_errors.append(
                    f"Validator error: {validator.__name__} - {str(e)}"
                )
                
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            metadata=metadata
        )
        
    def _validate_base_class(
        self, tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """Validate tool inherits from BaseTool"""
        if not issubclass(tool_class, BaseTool):
            return ValidationResult(
                is_valid=False,
                errors=[f"{tool_class.__name__} must inherit from BaseTool"]
            )
            
        return ValidationResult(is_valid=True)
        
    def _validate_metadata(
        self, tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """Validate tool has proper metadata"""
        errors = []
        warnings = []
        metadata = None
        
        try:
            # Try to create temporary instance
            with self._safe_instantiation(tool_class) as instance:
                if instance:
                    metadata = instance.metadata
                    
                    if not metadata:
                        errors.append("Tool has no metadata")
                    else:
                        # Validate metadata fields
                        if not metadata.name:
                            errors.append("Tool metadata missing 'name'")
                        if not metadata.version:
                            warnings.append("Tool metadata missing 'version'")
                        if not metadata.description:
                            warnings.append(
                                "Tool metadata missing 'description'"
                            )
                            
        except Exception as e:
            errors.append(f"Cannot validate metadata: {str(e)}")
            
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata=metadata
        )
        
    def _validate_required_methods(
        self, tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """Validate tool implements required methods"""
        errors = []
        
        # Check for required abstract methods
        abstract_methods = [
            '_create_metadata',
            'initialize', 
            'execute',
            'shutdown'
        ]
        
        for method_name in abstract_methods:
            method = getattr(tool_class, method_name, None)
            
            if not method:
                errors.append(f"Missing required method: {method_name}")
            elif getattr(method, '__isabstractmethod__', False):
                errors.append(
                    f"Abstract method not implemented: {method_name}"
                )
                
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
        
    def _validate_initialization(
        self, tool_class: Type[BaseTool]
    ) -> ValidationResult:
        """Validate tool can be initialized"""
        errors = []
        warnings = []
        
        try:
            # Try to create instance
            with self._safe_instantiation(tool_class) as instance:
                if not instance:
                    errors.append("Tool failed to initialize")
                elif instance.status == ToolStatus.FAILED:
                    errors.append("Tool initialization failed")
                elif not instance.is_ready:
                    warnings.append("Tool not ready after initialization")
                    
        except Exception as e:
            errors.append(f"Initialization error: {str(e)}")
            
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
        
    @contextmanager
    def _safe_instantiation(self, tool_class: Type[BaseTool]):
        """Safely instantiate a tool for validation"""
        instance = None
        
        try:
            # Create instance with empty config
            instance = tool_class({})
            yield instance
            
        except Exception as e:
            logger.debug(f"Failed to instantiate {tool_class.__name__}: {e}")
            yield None
            
        finally:
            # Always cleanup
            if instance:
                try:
                    instance.shutdown()
                except Exception:
                    pass
                    
    def load_and_validate(
        self,
        module_path: str,
        class_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Type[BaseTool]], ValidationResult]:
        """
        Load and validate a tool
        
        Args:
            module_path: Module or file path
            class_name: Optional class name
            config: Optional configuration
            
        Returns:
            Tuple of (tool_class, validation_result)
        """
        # Load tool class
        tool_class = self.load_tool_class(module_path, class_name)
        
        if not tool_class:
            return None, ValidationResult(
                is_valid=False,
                errors=[f"Failed to load tool from {module_path}"]
            )
            
        # Validate tool
        validation_result = self.validate_tool(tool_class)
        
        return tool_class, validation_result
        
    def load_and_register(
        self,
        module_path: str,
        class_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None
    ) -> bool:
        """
        Load, validate, and register a tool
        
        Args:
            module_path: Module or file path
            class_name: Optional class name
            config: Optional configuration
            tool_name: Optional name override
            
        Returns:
            True if successfully registered
        """
        if not self.registry:
            logger.error("No registry available for registration")
            return False
            
        # Load and validate
        tool_class, validation_result = self.load_and_validate(
            module_path, class_name, config
        )
        
        if not tool_class or not validation_result.is_valid:
            logger.error(
                f"Tool validation failed: "
                f"{', '.join(validation_result.errors)}"
            )
            return False
            
        # Log warnings
        for warning in validation_result.warnings:
            logger.warning(f"Tool warning: {warning}")
            
        # Register tool
        name = tool_name or (
            validation_result.metadata.name 
            if validation_result.metadata 
            else tool_class.__name__
        )
        
        return self.registry.register_tool(
            tool_class,
            name=name,
            config=config
        )
        
    def _record_error(
        self,
        tool_name: str,
        error_type: str,
        message: str,
        traceback: Optional[str] = None,
        source: Optional[str] = None
    ):
        """Record a loading error"""
        error = LoaderError(
            tool_name=tool_name,
            error_type=error_type,
            message=message,
            traceback=traceback,
            source=source
        )
        
        with self._lock:
            self._loading_errors.append(error)
            
    def get_errors(self) -> List[LoaderError]:
        """Get all loading errors"""
        with self._lock:
            return self._loading_errors.copy()
            
    def clear_errors(self):
        """Clear all loading errors"""
        with self._lock:
            self._loading_errors.clear()
            
    def clear_cache(self):
        """Clear module cache"""
        with self._lock:
            self._loaded_modules.clear()


# Convenience functions
def load_tool(
    module_path: str,
    class_name: Optional[str] = None,
    registry: Optional['ToolRegistry'] = None
) -> Optional[Type[BaseTool]]:
    """
    Quick tool loading function
    
    Args:
        module_path: Module or file path
        class_name: Optional class name
        registry: Optional registry for validation context
        
    Returns:
        Tool class or None
    """
    loader = ToolLoader(registry)
    return loader.load_tool_class(module_path, class_name)


def validate_tool(
    tool_class: Type[BaseTool],
    registry: Optional['ToolRegistry'] = None
) -> ValidationResult:
    """
    Quick tool validation function
    
    Args:
        tool_class: Tool class to validate
        registry: Optional registry for validation context
        
    Returns:
        Validation result
    """
    loader = ToolLoader(registry)
    return loader.validate_tool(tool_class)