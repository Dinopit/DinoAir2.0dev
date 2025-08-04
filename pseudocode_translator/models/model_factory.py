"""
Model Factory for the Pseudocode Translator

This module implements a factory pattern for dynamic model loading,
supporting model registration, discovery, and configuration-based selection.
"""

import logging
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Type, Optional, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_model import BaseTranslationModel, OutputLanguage

logger = logging.getLogger(__name__)


class ModelPriority(Enum):
    """Priority levels for model selection"""
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    FALLBACK = 4


@dataclass
class ModelRegistration:
    """Registration entry for a model"""
    model_class: Type[BaseTranslationModel]
    name: str
    aliases: List[str]
    priority: ModelPriority = ModelPriority.MEDIUM
    is_default: bool = False
    config_overrides: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.config_overrides is None:
            self.config_overrides = {}


class ModelFactory:
    """
    Factory class for creating and managing translation models
    
    This class provides:
    - Dynamic model registration and discovery
    - Configuration-based model selection
    - Fallback mechanisms for unavailable models
    - Plugin support
    """
    
    # Class-level registry
    _registry: Dict[str, ModelRegistration] = {}
    _aliases: Dict[str, str] = {}
    _initialized: bool = False
    _default_model: Optional[str] = None
    _fallback_chain: List[str] = []
    
    @classmethod
    def initialize(cls, auto_discover: bool = True) -> None:
        """
        Initialize the factory
        
        Args:
            auto_discover: Whether to automatically discover models
        """
        if cls._initialized:
            return
        
        logger.info("Initializing ModelFactory")
        
        if auto_discover:
            cls.discover_models()
        
        cls._initialized = True
        logger.info(
            f"ModelFactory initialized with {len(cls._registry)} models"
        )
    
    @classmethod
    def register_model(cls,
                       model_class: Type[BaseTranslationModel],
                       name: Optional[str] = None,
                       aliases: Optional[List[str]] = None,
                       priority: ModelPriority = ModelPriority.MEDIUM,
                       is_default: bool = False,
                       config_overrides: Optional[Dict[str, Any]] = None
                       ) -> None:
        """
        Register a model with the factory
        
        Args:
            model_class: The model class to register
            name: Optional name override (defaults to class name)
            aliases: Optional list of aliases
            priority: Model priority for selection
            is_default: Whether this is the default model
            config_overrides: Optional config overrides
        """
        # Get model name
        if name is None:
            name = model_class.__name__.lower().replace('model', '')
        
        # Check if already registered
        if name in cls._registry:
            logger.warning(f"Model '{name}' already registered, overwriting")
        
        # Create registration
        registration = ModelRegistration(
            model_class=model_class,
            name=name,
            aliases=aliases or [],
            priority=priority,
            is_default=is_default,
            config_overrides=config_overrides or {}
        )
        
        # Register the model
        cls._registry[name] = registration
        
        # Register aliases
        for alias in registration.aliases:
            cls._aliases[alias] = name
        
        # Update default if needed
        if is_default or cls._default_model is None:
            cls._default_model = name
        
        aliases_str = ', '.join(aliases or [])
        logger.info(f"Registered model: {name} (aliases: {aliases_str})")
    
    @classmethod
    def unregister_model(cls, name: str) -> None:
        """
        Unregister a model
        
        Args:
            name: Model name to unregister
        """
        # Resolve alias if needed
        actual_name = cls._aliases.get(name, name)
        
        if actual_name not in cls._registry:
            logger.warning(f"Model '{name}' not found in registry")
            return
        
        # Get registration for cleanup
        registration = cls._registry[actual_name]
        
        # Remove from registry
        del cls._registry[actual_name]
        
        # Remove aliases
        for alias in registration.aliases:
            if alias in cls._aliases:
                del cls._aliases[alias]
        
        # Update default if needed
        if cls._default_model == actual_name:
            cls._default_model = next(iter(cls._registry.keys()), None)
        
        logger.info(f"Unregistered model: {actual_name}")
    
    @classmethod
    def create_model(cls,
                     name: Optional[str] = None,
                     config: Optional[Dict[str, Any]] = None,
                     fallback_enabled: bool = True) -> BaseTranslationModel:
        """
        Create a model instance
        
        Args:
            name: Model name (uses default if not specified)
            config: Model configuration
            fallback_enabled: Whether to use fallback models
            
        Returns:
            Model instance
            
        Raises:
            ValueError: If no model found and fallback disabled
        """
        # Initialize if needed
        if not cls._initialized:
            cls.initialize()
        
        # Use default if no name specified
        model_name = name or cls._default_model
        
        if not model_name:
            raise ValueError("No model name specified and no default set")
        
        # Try to create the requested model
        try:
            return cls._create_model_instance(model_name, config)
        except Exception as e:
            logger.error(f"Failed to create model '{model_name}': {e}")
            
            if not fallback_enabled:
                raise
            
            # Try fallback models
            for fallback_name in cls._get_fallback_chain(model_name):
                try:
                    logger.info(f"Trying fallback model: {fallback_name}")
                    return cls._create_model_instance(fallback_name, config)
                except Exception as fallback_e:
                    logger.error(
                        f"Fallback '{fallback_name}' failed: {fallback_e}"
                    )
                    continue
            
            raise ValueError(
                f"No suitable model found (tried {model_name} and fallbacks)"
            )
    
    @classmethod
    def _create_model_instance(cls,
                               name: str,
                               config: Optional[Dict[str, Any]] = None
                               ) -> BaseTranslationModel:
        """
        Internal method to create a model instance
        
        Args:
            name: Model name
            config: Model configuration
            
        Returns:
            Model instance
        """
        # Resolve alias
        actual_name = cls._aliases.get(name, name)
        
        if actual_name not in cls._registry:
            raise KeyError(f"Model '{name}' not found in registry")
        
        registration = cls._registry[actual_name]
        
        # Merge configurations
        final_config = {}
        if registration.config_overrides:
            final_config.update(registration.config_overrides)
        if config:
            final_config.update(config)
        
        # Create instance
        return registration.model_class(final_config)
    
    @classmethod
    def list_models(cls,
                    include_aliases: bool = False) -> List[str]:
        """
        List all registered models
        
        Args:
            include_aliases: Whether to include aliases
            
        Returns:
            List of model names
        """
        models = list(cls._registry.keys())
        
        if include_aliases:
            models.extend(cls._aliases.keys())
        
        return sorted(models)
    
    @classmethod
    def get_model_info(cls, name: str) -> Dict[str, Any]:
        """
        Get information about a model
        
        Args:
            name: Model name or alias
            
        Returns:
            Model information dictionary
        """
        # Resolve alias
        actual_name = cls._aliases.get(name, name)
        
        if actual_name not in cls._registry:
            raise KeyError(f"Model '{name}' not found")
        
        registration = cls._registry[actual_name]
        
        # Create temporary instance for metadata
        temp_instance = registration.model_class({})
        metadata = temp_instance.metadata
        
        return {
            "name": registration.name,
            "class": registration.model_class.__name__,
            "aliases": registration.aliases,
            "priority": registration.priority.name,
            "is_default": registration.is_default,
            "metadata": {
                "version": metadata.version,
                "author": metadata.author,
                "description": metadata.description,
                "supported_languages": [
                    lang.value for lang in metadata.supported_languages
                ]
            }
        }
    
    @classmethod
    def find_models_by_language(cls,
                                language: OutputLanguage) -> List[str]:
        """
        Find models that support a specific output language
        
        Args:
            language: The output language to check
            
        Returns:
            List of model names supporting the language
        """
        supporting_models = []
        
        for name, registration in cls._registry.items():
            try:
                temp_instance = registration.model_class({})
                if temp_instance.metadata.supports_language(language):
                    supporting_models.append(name)
            except Exception as e:
                logger.warning(
                    f"Error checking language support for {name}: {e}"
                )
        
        return sorted(supporting_models)
    
    @classmethod
    def set_default_model(cls, name: str) -> None:
        """
        Set the default model
        
        Args:
            name: Model name to set as default
        """
        # Resolve alias
        actual_name = cls._aliases.get(name, name)
        
        if actual_name not in cls._registry:
            raise KeyError(f"Model '{name}' not found")
        
        # Update previous default
        if cls._default_model and cls._default_model in cls._registry:
            cls._registry[cls._default_model].is_default = False
        
        # Set new default
        cls._default_model = actual_name
        cls._registry[actual_name].is_default = True
        
        logger.info(f"Default model set to: {actual_name}")
    
    @classmethod
    def set_fallback_chain(cls, models: List[str]) -> None:
        """
        Set the fallback model chain
        
        Args:
            models: Ordered list of fallback model names
        """
        # Validate all models exist
        for model in models:
            actual_name = cls._aliases.get(model, model)
            if actual_name not in cls._registry:
                raise KeyError(f"Model '{model}' not found")
        
        cls._fallback_chain = models
        logger.info(f"Fallback chain set to: {', '.join(models)}")
    
    @classmethod
    def _get_fallback_chain(cls, failed_model: str) -> List[str]:
        """
        Get fallback models for a failed model
        
        Args:
            failed_model: The model that failed
            
        Returns:
            List of fallback model names
        """
        # Use configured fallback chain if available
        if cls._fallback_chain:
            return [m for m in cls._fallback_chain if m != failed_model]
        
        # Otherwise, build chain based on priority
        fallbacks = []
        failed_priority = ModelPriority.LOW
        
        # Get failed model priority
        if failed_model in cls._registry:
            failed_priority = cls._registry[failed_model].priority
        
        # Sort models by priority
        sorted_models = sorted(
            cls._registry.items(),
            key=lambda x: (x[1].priority.value, x[0])
        )
        
        # Add models with same or better priority
        for name, registration in sorted_models:
            if (name != failed_model and
                    registration.priority.value <= failed_priority.value):
                fallbacks.append(name)
        
        return fallbacks
    
    @classmethod
    def discover_models(cls,
                        package_path: Optional[Path] = None) -> int:
        """
        Discover and register models from a package
        
        Args:
            package_path: Path to models package (uses current package if None)
            
        Returns:
            Number of models discovered
        """
        if package_path is None:
            package_path = Path(__file__).parent
        
        discovered_count = 0
        
        # Skip these modules
        skip_modules = {
            'base_model', 'model_factory', 'plugin_system', '__init__'
        }
        
        logger.info(f"Discovering models in: {package_path}")
        
        for finder, module_name, ispkg in pkgutil.iter_modules(
                [str(package_path)]):
            if module_name in skip_modules or ispkg:
                continue
            
            try:
                # Import the module
                module = importlib.import_module(
                    f'.{module_name}',
                    package='pseudocode_translator.models'
                )
                
                # Look for BaseTranslationModel subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                            issubclass(attr, BaseTranslationModel) and
                            attr != BaseTranslationModel):
                        
                        # Check if it has a register decorator or auto-register
                        if not cls._is_model_registered(attr):
                            cls.register_model(attr)
                        
                        discovered_count += 1
                
            except Exception as e:
                logger.warning(
                    f"Failed to import model module '{module_name}': {e}"
                )
        
        logger.info(f"Discovered {discovered_count} models")
        return discovered_count
    
    @classmethod
    def _is_model_registered(cls,
                             model_class: Type[BaseTranslationModel]) -> bool:
        """Check if a model class is already registered"""
        for registration in cls._registry.values():
            if registration.model_class == model_class:
                return True
        return False
    
    @classmethod
    def validate_configuration(cls,
                               model_name: str,
                               config: Dict[str, Any]
                               ) -> Tuple[bool, List[str]]:
        """
        Validate a configuration for a specific model
        
        Args:
            model_name: Model name
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        try:
            # Create temporary instance
            model = cls._create_model_instance(model_name, config)
            
            # Let model validate its own config
            if hasattr(model, 'validate_config'):
                from .base_model import TranslationConfig
                # Create a translation config from dict
                translation_config = TranslationConfig(**config)
                issues = model.validate_config(translation_config)
                return len(issues) == 0, issues
            
            return True, []
            
        except Exception as e:
            return False, [f"Failed to validate: {str(e)}"]
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered models (mainly for testing)"""
        cls._registry.clear()
        cls._aliases.clear()
        cls._default_model = None
        cls._fallback_chain = []
        cls._initialized = False
        logger.info("Model registry cleared")


# Decorator for model registration
def register_model(name: Optional[str] = None,
                   aliases: Optional[List[str]] = None,
                   priority: ModelPriority = ModelPriority.MEDIUM,
                   is_default: bool = False,
                   config_overrides: Optional[Dict[str, Any]] = None):
    """
    Decorator to register a model with the factory
    
    Usage:
        @register_model(name="my_model", aliases=["mymodel", "mm"])
        class MyModel(BaseTranslationModel):
            ...
    
    Args:
        name: Optional model name
        aliases: Optional list of aliases
        priority: Model priority
        is_default: Whether this is the default model
        config_overrides: Optional config overrides
        
    Returns:
        Decorator function
    """
    def decorator(
            model_class: Type[BaseTranslationModel]
    ) -> Type[BaseTranslationModel]:
        ModelFactory.register_model(
            model_class,
            name=name,
            aliases=aliases,
            priority=priority,
            is_default=is_default,
            config_overrides=config_overrides
        )
        return model_class
    
    return decorator


# Convenience functions
def create_model(name: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None
                 ) -> BaseTranslationModel:
    """
    Create a model instance
    
    Args:
        name: Model name (uses default if not specified)
        config: Model configuration
        
    Returns:
        Model instance
    """
    return ModelFactory.create_model(name, config)


def list_available_models() -> List[str]:
    """Get list of available model names"""
    return ModelFactory.list_models()


def get_default_model() -> Optional[str]:
    """Get the default model name"""
    return ModelFactory._default_model


# Initialize factory on import
ModelFactory.initialize(auto_discover=False)