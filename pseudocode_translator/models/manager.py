"""
Model manager for the Pseudocode Translator

This module provides centralized management of language models, including
model selection, lazy loading, health checks, and memory management.
"""

import logging
import threading
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base import BaseModel
from .registry import ModelRegistry, model_exists
from .downloader import ModelDownloader


logger = logging.getLogger(__name__)


@dataclass
class ModelInstance:
    """Container for a loaded model instance with metadata"""
    model: BaseModel
    loaded_at: datetime
    last_used: datetime
    usage_count: int = 0
    model_path: Optional[Path] = None
    
    def update_usage(self):
        """Update usage statistics"""
        self.last_used = datetime.now()
        self.usage_count += 1


class ModelManager:
    """
    Manages model lifecycle including loading, caching, and resource management
    
    This class provides:
    - Lazy loading of models
    - Model instance caching
    - Automatic resource management
    - Model health checks
    - Configuration-based model selection
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the model manager
        
        Args:
            config: Manager configuration
        """
        self.config = config or {}
        self._instances: Dict[str, ModelInstance] = {}
        self._lock = threading.Lock()
        self._downloader = ModelDownloader(
            download_dir=self.config.get('model_dir', './models')
        )
        
        # Configuration
        self.max_loaded_models = self.config.get('max_loaded_models', 3)
        self.auto_download = self.config.get('auto_download', False)
        self.model_ttl_minutes = self.config.get('model_ttl_minutes', 60)
        self.default_model = self.config.get('default_model', 'qwen')
        self.model_configs = self.config.get('model_configs', {})
        
        # Memory thresholds
        self.min_available_memory_gb = self.config.get(
            'min_available_memory_gb', 2.0
        )
        
    def get_model(self, 
                  name: Optional[str] = None,
                  auto_load: bool = True) -> BaseModel:
        """
        Get a model instance by name
        
        Args:
            name: Model name (uses default if not specified)
            auto_load: Whether to automatically load the model
            
        Returns:
            Model instance
            
        Raises:
            KeyError: If model not found
            RuntimeError: If model loading fails
        """
        model_name = name or self.default_model
        
        with self._lock:
            # Check if already loaded
            if model_name in self._instances:
                instance = self._instances[model_name]
                instance.update_usage()
                logger.debug(f"Using cached model: {model_name}")
                return instance.model
            
            # Load model if requested
            if auto_load:
                return self._load_model(model_name)
            else:
                raise RuntimeError(
                    f"Model '{model_name}' not loaded. "
                    f"Call load_model() first."
                )
    
    def load_model(self,
                   name: str,
                   model_path: Optional[Path] = None) -> BaseModel:
        """
        Explicitly load a model
        
        Args:
            name: Model name
            model_path: Optional path to model file
            
        Returns:
            Loaded model instance
        """
        with self._lock:
            return self._load_model(name, model_path)
    
    def _load_model(self, 
                    name: str, 
                    model_path: Optional[Path] = None) -> BaseModel:
        """
        Internal method to load a model
        
        Args:
            name: Model name
            model_path: Optional path to model file
            
        Returns:
            Loaded model instance
        """
        # Check if model exists in registry
        if not model_exists(name):
            raise KeyError(f"Model '{name}' not found in registry")
        
        # Check memory before loading
        self._check_memory_availability(name)
        
        # Evict old models if needed
        self._evict_old_models()
        
        logger.info(f"Loading model: {name}")
        
        # Get model configuration
        model_config = self.model_configs.get(name, {})
        
        # Create model instance
        model = ModelRegistry.create_model(name, model_config)
        
        # Determine model path
        if not model_path:
            model_path = self._get_model_path(name, model)
        
        # Download if needed and enabled
        if not model_path.exists() and self.auto_download:
            logger.info("Model file not found, attempting download...")
            try:
                if model.metadata.download_url:
                    model_path = self._downloader.download_model(
                        model.metadata.download_url,
                        model.metadata.name,
                        model.metadata.sha256_checksum
                    )
                else:
                    raise RuntimeError(
                        f"No download URL provided for model '{name}'"
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to download model: {e}")
        
        # Initialize the model
        if model_path is None:
            raise RuntimeError("Model path is None")
            
        try:
            model.initialize(model_path)
            
            # Warm up model if configured
            if self.config.get('warmup_on_load', True):
                model.warmup()
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize model '{name}': {e}")
        
        # Cache the instance
        self._instances[name] = ModelInstance(
            model=model,
            loaded_at=datetime.now(),
            last_used=datetime.now(),
            model_path=model_path
        )
        
        logger.info(f"Model '{name}' loaded successfully")
        return model
    
    def unload_model(self, name: str) -> None:
        """
        Unload a model from memory
        
        Args:
            name: Model name to unload
        """
        with self._lock:
            if name in self._instances:
                instance = self._instances[name]
                try:
                    instance.model.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down model '{name}': {e}")
                
                del self._instances[name]
                logger.info(f"Model '{name}' unloaded")
    
    def list_loaded_models(self) -> List[Dict[str, Any]]:
        """
        List all currently loaded models
        
        Returns:
            List of model information dictionaries
        """
        with self._lock:
            return [
                {
                    'name': name,
                    'loaded_at': instance.loaded_at.isoformat(),
                    'last_used': instance.last_used.isoformat(),
                    'usage_count': instance.usage_count,
                    'model_path': (
                        str(instance.model_path)
                        if instance.model_path else None
                    )
                }
                for name, instance in self._instances.items()
            ]
    
    def get_model_health(self, name: str) -> Dict[str, Any]:
        """
        Check health status of a model
        
        Args:
            name: Model name
            
        Returns:
            Health status dictionary
        """
        if name not in self._instances:
            return {
                'status': 'not_loaded',
                'model': name
            }
        
        instance = self._instances[name]
        try:
            # Try a simple generation to test model
            instance.model.generate("test", max_tokens=1)
            status = 'healthy'
            error = None
        except Exception as e:
            status = 'unhealthy'
            error = str(e)
        
        return {
            'status': status,
            'model': name,
            'loaded_at': instance.loaded_at.isoformat(),
            'last_used': instance.last_used.isoformat(),
            'usage_count': instance.usage_count,
            'error': error
        }
    
    def check_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health of all loaded models
        
        Returns:
            Dictionary mapping model names to health status
        """
        with self._lock:
            return {
                name: self.get_model_health(name)
                for name in self._instances.keys()
            }
    
    def _check_memory_availability(self, model_name: str) -> None:
        """
        Check if there's enough memory to load a model
        
        Args:
            model_name: Name of model to load
            
        Raises:
            RuntimeError: If insufficient memory
        """
        # Get model requirements
        model_class = ModelRegistry.get_model_class(model_name)
        temp_instance = model_class({})
        capabilities = temp_instance.capabilities
        
        # Check available memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024 ** 3)
        
        if available_gb < capabilities.min_memory_gb:
            raise RuntimeError(
                f"Insufficient memory for model '{model_name}'. "
                f"Available: {available_gb:.1f}GB, "
                f"Required: {capabilities.min_memory_gb}GB"
            )
        
        # Warn if below recommended
        if available_gb < capabilities.recommended_memory_gb:
            logger.warning(
                f"Memory below recommended for model '{model_name}'. "
                f"Available: {available_gb:.1f}GB, "
                f"Recommended: {capabilities.recommended_memory_gb}GB"
            )
    
    def _evict_old_models(self) -> None:
        """
        Evict old models if we're at capacity
        """
        if len(self._instances) < self.max_loaded_models:
            return
        
        # Find least recently used model
        lru_name = min(
            self._instances.keys(),
            key=lambda k: self._instances[k].last_used
        )
        
        logger.info(f"Evicting LRU model: {lru_name}")
        self.unload_model(lru_name)
    
    def _get_model_path(self, name: str, model: BaseModel) -> Path:
        """
        Get the path to a model file
        
        Args:
            name: Model name
            model: Model instance
            
        Returns:
            Path to model file
        """
        # Check configured paths
        if name in self.config.get('model_paths', {}):
            return Path(self.config['model_paths'][name])
        
        # Use default pattern
        model_dir = Path(self.config.get('model_dir', './models'))
        pattern = model.metadata.filename_pattern
        
        # Look for matching files
        for file in model_dir.rglob(pattern):
            return file
        
        # Return expected path (even if doesn't exist)
        return model_dir / name / pattern.replace('*', name)
    
    def cleanup_old_models(self) -> int:
        """
        Clean up models that haven't been used recently
        
        Returns:
            Number of models unloaded
        """
        if self.model_ttl_minutes <= 0:
            return 0
        
        cutoff_time = (
            datetime.now() - timedelta(minutes=self.model_ttl_minutes)
        )
        models_to_unload = []
        
        with self._lock:
            for name, instance in self._instances.items():
                if instance.last_used < cutoff_time:
                    models_to_unload.append(name)
        
        for name in models_to_unload:
            logger.info(f"Unloading idle model: {name}")
            self.unload_model(name)
        
        return len(models_to_unload)
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get memory usage information
        
        Returns:
            Memory usage statistics
        """
        memory = psutil.virtual_memory()
        
        # Estimate model memory usage (rough estimate)
        model_memory_gb = 0.0
        for name, instance in self._instances.items():
            caps = instance.model.capabilities
            model_memory_gb += caps.model_size_gb
        
        return {
            'total_gb': memory.total / (1024 ** 3),
            'available_gb': memory.available / (1024 ** 3),
            'used_percent': memory.percent,
            'models_loaded': len(self._instances),
            'estimated_model_usage_gb': model_memory_gb,
            'min_required_gb': self.min_available_memory_gb
        }
    
    def switch_default_model(self, name: str) -> None:
        """
        Switch the default model
        
        Args:
            name: New default model name
        """
        if not model_exists(name):
            raise KeyError(f"Model '{name}' not found in registry")
        
        self.default_model = name
        logger.info(f"Default model switched to: {name}")
    
    def shutdown(self) -> None:
        """
        Shutdown all models and cleanup resources
        """
        logger.info("Shutting down model manager...")
        
        with self._lock:
            for name in list(self._instances.keys()):
                self.unload_model(name)
        
        logger.info("Model manager shutdown complete")


# Singleton instance for convenient access
_manager: Optional[ModelManager] = None


def get_manager(config: Optional[Dict[str, Any]] = None) -> ModelManager:
    """
    Get or create the global model manager instance
    
    Args:
        config: Configuration (only used on first call)
        
    Returns:
        ModelManager instance
    """
    global _manager
    if _manager is None:
        _manager = ModelManager(config)
    return _manager