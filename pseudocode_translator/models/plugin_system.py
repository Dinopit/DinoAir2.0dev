"""
Plugin System for the Pseudocode Translator

This module implements a plugin system for dynamically loading external
model implementations, supporting hot-loading and validation.
"""

import sys
import json
import logging
import importlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Type, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

from .base_model import BaseTranslationModel
from .model_factory import ModelFactory, ModelPriority

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    author: str
    description: str
    model_class: str
    requirements: List[str]
    compatible_versions: List[str]
    priority: str = "MEDIUM"
    aliases: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadedPlugin:
    """Information about a loaded plugin"""
    path: Path
    metadata: PluginMetadata
    model_class: Type[BaseTranslationModel]
    loaded_at: datetime
    checksum: str
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


class PluginSystem:
    """
    Plugin system for loading and managing external model implementations
    
    Features:
    - Dynamic plugin discovery and loading
    - Plugin validation and compatibility checking
    - Hot-reloading support
    - Security validation
    - Dependency management
    """
    
    # Default plugin directories
    DEFAULT_PLUGIN_DIRS = [
        Path.home() / ".pseudocode_translator" / "plugins",
        Path("./plugins"),
        Path("/usr/local/share/pseudocode_translator/plugins"),
    ]
    
    # Required plugin files
    PLUGIN_MANIFEST = "plugin.json"
    PLUGIN_MODULE = "model.py"
    
    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        """
        Initialize the plugin system
        
        Args:
            plugin_dirs: Optional list of plugin directories
        """
        self.plugin_dirs = plugin_dirs or self.DEFAULT_PLUGIN_DIRS
        self.loaded_plugins: Dict[str, LoadedPlugin] = {}
        self._plugin_cache: Dict[str, Any] = {}
        
        # Ensure plugin directories exist
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                plugin_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Plugin system initialized with dirs: {self.plugin_dirs}")
    
    def discover_plugins(self) -> List[Path]:
        """
        Discover all available plugins
        
        Returns:
            List of plugin paths
        """
        discovered_plugins = []
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Look for plugin directories
            for item in plugin_dir.iterdir():
                if item.is_dir() and self._is_valid_plugin_dir(item):
                    discovered_plugins.append(item)
            
            # Also check for .ptp (PseudocodeTranslatorPlugin) files
            for ptp_file in plugin_dir.glob("*.ptp"):
                discovered_plugins.append(ptp_file)
        
        logger.info(f"Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins
    
    def load_plugin(self, plugin_path: Path) -> Optional[LoadedPlugin]:
        """
        Load a single plugin
        
        Args:
            plugin_path: Path to the plugin
            
        Returns:
            LoadedPlugin instance or None if loading fails
        """
        try:
            logger.info(f"Loading plugin from: {plugin_path}")
            
            # Check if already loaded
            plugin_key = str(plugin_path)
            if plugin_key in self.loaded_plugins:
                logger.info(f"Plugin already loaded: {plugin_path.name}")
                return self.loaded_plugins[plugin_key]
            
            # Load plugin based on type
            if plugin_path.suffix == ".ptp":
                loaded_plugin = self._load_ptp_plugin(plugin_path)
            else:
                loaded_plugin = self._load_directory_plugin(plugin_path)
            
            if loaded_plugin and loaded_plugin.is_valid:
                # Register with ModelFactory
                self._register_plugin_model(loaded_plugin)
                
                # Cache the plugin
                self.loaded_plugins[plugin_key] = loaded_plugin
                
                logger.info(
                    f"Successfully loaded plugin: "
                    f"{loaded_plugin.metadata.name}"
                )
                return loaded_plugin
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_path}: {e}")
            return None
    
    def load_all_plugins(self) -> int:
        """
        Load all discovered plugins
        
        Returns:
            Number of successfully loaded plugins
        """
        plugins = self.discover_plugins()
        loaded_count = 0
        
        for plugin_path in plugins:
            if self.load_plugin(plugin_path):
                loaded_count += 1
        
        logger.info(f"Loaded {loaded_count} plugins successfully")
        return loaded_count
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Returns:
            True if successful
        """
        # Find plugin by name
        plugin_to_unload = None
        plugin_key = None
        
        for key, plugin in self.loaded_plugins.items():
            if plugin.metadata.name == plugin_name:
                plugin_to_unload = plugin
                plugin_key = key
                break
        
        if not plugin_to_unload:
            logger.warning(f"Plugin not found: {plugin_name}")
            return False
        
        try:
            # Unregister from ModelFactory
            ModelFactory.unregister_model(plugin_name)
            
            # Remove from loaded plugins
            if plugin_key:
                del self.loaded_plugins[plugin_key]
            
            # Clear any cached data
            self._clear_plugin_cache(plugin_name)
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a plugin (useful for development)
        
        Args:
            plugin_name: Name of the plugin to reload
            
        Returns:
            True if successful
        """
        # Find plugin path
        plugin_path = None
        for key, plugin in self.loaded_plugins.items():
            if plugin.metadata.name == plugin_name:
                plugin_path = Path(key)
                break
        
        if not plugin_path:
            logger.warning(f"Plugin not found for reload: {plugin_name}")
            return False
        
        # Unload then load
        if self.unload_plugin(plugin_name):
            return self.load_plugin(plugin_path) is not None
        
        return False
    
    def validate_plugin(self, plugin_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a plugin without loading it
        
        Args:
            plugin_path: Path to the plugin
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check plugin structure
            if plugin_path.suffix == ".ptp":
                # Validate PTP file
                if not plugin_path.exists():
                    errors.append(f"Plugin file not found: {plugin_path}")
                    return False, errors
            else:
                # Validate directory plugin
                if not self._is_valid_plugin_dir(plugin_path):
                    errors.append("Invalid plugin directory structure")
                    return False, errors
            
            # Load and validate metadata
            metadata = self._load_plugin_metadata(plugin_path)
            if not metadata:
                errors.append("Failed to load plugin metadata")
                return False, errors
            
            # Validate metadata fields
            required_fields = ['name', 'version', 'model_class']
            for req_field in required_fields:
                if not getattr(metadata, req_field, None):
                    errors.append(f"Missing required field: {req_field}")
            
            # Check version compatibility
            if not self._check_compatibility(metadata):
                errors.append(
                    f"Plugin requires incompatible version: "
                    f"{metadata.compatible_versions}"
                )
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return False, errors
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a loaded plugin
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin information dictionary
        """
        for plugin in self.loaded_plugins.values():
            if plugin.metadata.name == plugin_name:
                return {
                    "name": plugin.metadata.name,
                    "version": plugin.metadata.version,
                    "author": plugin.metadata.author,
                    "description": plugin.metadata.description,
                    "loaded_at": plugin.loaded_at.isoformat(),
                    "path": str(plugin.path),
                    "is_valid": plugin.is_valid,
                    "validation_errors": plugin.validation_errors,
                    "aliases": plugin.metadata.aliases,
                    "requirements": plugin.metadata.requirements
                }
        
        return None
    
    def list_loaded_plugins(self) -> List[Dict[str, Any]]:
        """
        List all loaded plugins
        
        Returns:
            List of plugin information dictionaries
        """
        plugins = []
        for plugin in self.loaded_plugins.values():
            info = self.get_plugin_info(plugin.metadata.name)
            if info:
                plugins.append(info)
        return plugins
    
    def _is_valid_plugin_dir(self, path: Path) -> bool:
        """Check if a directory contains a valid plugin"""
        manifest_path = path / self.PLUGIN_MANIFEST
        module_path = path / self.PLUGIN_MODULE
        return manifest_path.exists() and module_path.exists()
    
    def _load_plugin_metadata(self,
                              plugin_path: Path) -> Optional[PluginMetadata]:
        """Load plugin metadata from manifest"""
        try:
            if plugin_path.suffix == ".ptp":
                # For PTP files, metadata is embedded
                return self._extract_ptp_metadata(plugin_path)
            else:
                # For directory plugins, load from plugin.json
                manifest_path = plugin_path / self.PLUGIN_MANIFEST
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
                    return PluginMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load plugin metadata: {e}")
            return None
    
    def _load_directory_plugin(self,
                               plugin_path: Path) -> Optional[LoadedPlugin]:
        """Load a plugin from a directory"""
        # Load metadata
        metadata = self._load_plugin_metadata(plugin_path)
        if not metadata:
            return None
        
        # Calculate checksum
        checksum = self._calculate_plugin_checksum(plugin_path)
        
        # Load the module
        module_path = plugin_path / self.PLUGIN_MODULE
        spec = importlib.util.spec_from_file_location(
            f"plugin_{metadata.name}",
            module_path
        )
        
        if not spec or not spec.loader:
            logger.error(f"Failed to create module spec for {module_path}")
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Add plugin directory to sys.path temporarily
        sys.path.insert(0, str(plugin_path))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        
        # Get the model class
        model_class = getattr(module, metadata.model_class, None)
        if not model_class:
            logger.error(
                f"Model class {metadata.model_class} not found in module"
            )
            return None
        
        # Validate model class
        if not issubclass(model_class, BaseTranslationModel):
            logger.error(
                f"Model class {metadata.model_class} must inherit from "
                "BaseTranslationModel"
            )
            return None
        
        # Create LoadedPlugin instance
        loaded_plugin = LoadedPlugin(
            path=plugin_path,
            metadata=metadata,
            model_class=model_class,
            loaded_at=datetime.now(),
            checksum=checksum,
            is_valid=True
        )
        
        return loaded_plugin
    
    def _load_ptp_plugin(self, plugin_path: Path) -> Optional[LoadedPlugin]:
        """Load a plugin from a .ptp file"""
        # PTP files are zip archives with a specific structure
        # This is a placeholder for future implementation
        logger.warning("PTP plugin format not yet implemented")
        return None
    
    def _extract_ptp_metadata(self,
                              ptp_path: Path) -> Optional[PluginMetadata]:
        """Extract metadata from a PTP file"""
        # Placeholder for future implementation
        return None
    
    def _register_plugin_model(self, plugin: LoadedPlugin) -> None:
        """Register a plugin model with the ModelFactory"""
        priority = ModelPriority[plugin.metadata.priority]
        
        ModelFactory.register_model(
            model_class=plugin.model_class,
            name=plugin.metadata.name,
            aliases=plugin.metadata.aliases,
            priority=priority,
            config_overrides={}
        )
    
    def _check_compatibility(self, metadata: PluginMetadata) -> bool:
        """Check if plugin is compatible with current version"""
        # For now, always return True
        # In the future, check against actual version
        return True
    
    def _calculate_plugin_checksum(self, plugin_path: Path) -> str:
        """Calculate checksum for plugin files"""
        hasher = hashlib.sha256()
        
        if plugin_path.is_file():
            # Single file
            with open(plugin_path, 'rb') as f:
                hasher.update(f.read())
        else:
            # Directory - hash manifest and module
            for filename in [self.PLUGIN_MANIFEST, self.PLUGIN_MODULE]:
                file_path = plugin_path / filename
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _clear_plugin_cache(self, plugin_name: str) -> None:
        """Clear any cached data for a plugin"""
        keys_to_remove = [
            key for key in self._plugin_cache
            if key.startswith(f"{plugin_name}:")
        ]
        for key in keys_to_remove:
            del self._plugin_cache[key]


# Global plugin system instance
_plugin_system: Optional[PluginSystem] = None


def get_plugin_system(
        plugin_dirs: Optional[List[Path]] = None) -> PluginSystem:
    """
    Get or create the global plugin system instance
    
    Args:
        plugin_dirs: Optional list of plugin directories
        
    Returns:
        PluginSystem instance
    """
    global _plugin_system
    if _plugin_system is None:
        _plugin_system = PluginSystem(plugin_dirs)
    return _plugin_system


def load_plugins(auto_discover: bool = True) -> int:
    """
    Load all available plugins
    
    Args:
        auto_discover: Whether to automatically discover and load plugins
        
    Returns:
        Number of loaded plugins
    """
    system = get_plugin_system()
    if auto_discover:
        return system.load_all_plugins()
    return 0


def create_plugin_template(plugin_name: str,
                           output_dir: Path,
                           author: str = "Unknown") -> bool:
    """
    Create a plugin template for developers
    
    Args:
        plugin_name: Name of the plugin
        output_dir: Directory to create the plugin in
        author: Plugin author
        
    Returns:
        True if successful
    """
    plugin_dir = output_dir / plugin_name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # Create plugin.json
    manifest = {
        "name": plugin_name,
        "version": "1.0.0",
        "author": author,
        "description": f"A custom model plugin for {plugin_name}",
        "model_class": f"{plugin_name.title()}Model",
        "requirements": [],
        "compatible_versions": ["1.0.0"],
        "priority": "MEDIUM",
        "aliases": []
    }
    
    with open(plugin_dir / "plugin.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Create model.py template
    model_template = f'''"""
{plugin_name.title()} Model Plugin

This is a template for creating custom model plugins.
"""

from pseudocode_translator.models.base_model import (
    BaseTranslationModel, ModelMetadata, ModelCapabilities,
    OutputLanguage, TranslationConfig, TranslationResult
)
from typing import Dict, Any, Optional, Tuple


class {plugin_name.title()}Model(BaseTranslationModel):
    """
    Custom model implementation for {plugin_name}
    """
    
    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata"""
        return ModelMetadata(
            name="{plugin_name}",
            version="1.0.0",
            supported_languages=[OutputLanguage.PYTHON],
            description="Custom model for {plugin_name}",
            author="{author}"
        )
    
    @property
    def capabilities(self) -> ModelCapabilities:
        """Get model capabilities"""
        return ModelCapabilities()
    
    def initialize(self, model_path: Optional[Path] = None, **kwargs) -> None:
        """Initialize the model"""
        # TODO: Implement model initialization
        self._initialized = True
    
    def translate(self,
                  instruction: str,
                  config: Optional[TranslationConfig] = None,
                  context: Optional[Dict[str, Any]] = None
                  ) -> TranslationResult:
        """Translate instruction to code"""
        # TODO: Implement translation logic
        return TranslationResult(
            success=True,
            code="# TODO: Implement translation",
            language=(config.target_language if config
                      else OutputLanguage.PYTHON)
        )
    
    def validate_input(self, instruction: str) -> Tuple[bool, Optional[str]]:
        """Validate input instruction"""
        if not instruction:
            return False, "Instruction cannot be empty"
        return True, None
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get detailed capabilities"""
        return {{
            "model_name": self.metadata.name,
            "version": self.metadata.version,
            "supported_languages": [
                lang.value for lang in self.metadata.supported_languages
            ]
        }}
'''
    
    with open(plugin_dir / "model.py", 'w') as f:
        f.write(model_template)
    
    # Create README
    readme = f"""# {plugin_name.title()} Plugin

## Description
{manifest['description']}

## Installation
1. Copy this directory to your plugins folder
2. The plugin will be automatically discovered and loaded

## Configuration
Add any plugin-specific configuration to your translator config.

## Development
Edit `model.py` to implement your custom model logic.
"""
    
    with open(plugin_dir / "README.md", 'w') as f:
        f.write(readme)
    
    logger.info(f"Created plugin template at: {plugin_dir}")
    return True