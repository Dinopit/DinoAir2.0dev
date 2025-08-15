"""
LLM Interface module for the Pseudocode Translator

This module manages interaction with language models using the new flexible
model management system. It supports multiple models through a plugin
architecture.

The interface maintains backward compatibility while adding support for:
- Multiple model backends (Qwen, GPT-2, CodeGen, etc.)
- Automatic model selection based on configuration
- Model switching at runtime
- Improved resource management
"""

import time
import logging
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import hashlib
import json

from .config import LLMConfig
from .models import BaseModel
# Import ModelManager conditionally to avoid circular import issues
try:
    from .models import ModelManager
except ImportError:
    # Create a mock ModelManager for now to avoid import errors
    class ModelManager:
        def __init__(self, *args, **kwargs):
            """
            No-op initializer for the mock ModelManager used when the real manager cannot be imported.
            
            Accepts arbitrary positional and keyword arguments for API compatibility but performs no initialization or side effects.
            """
            pass
        def get_model(self, *args, **kwargs):
            return None
        def close(self):
            """
            Close the model manager and release any held resources.
            
            In this minimal/mock implementation this method is a no-op and exists only for API compatibility.
            """
            pass
from .models.registry import list_available_models, model_exists


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TranslationCache:
    """Simple cache for translation results"""
    max_size: int = 1000
    ttl_seconds: int = 86400  # 24 hours
    
    def __post_init__(self):
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached translation if available and not expired"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return value
                else:
                    del self._cache[key]
        return None
    
    def put(self, key: str, value: str):
        """Store translation in cache"""
        with self._lock:
            # Simple LRU: remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(),
                                 key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            
            self._cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()


class LLMInterface:
    """
    Handles all LLM operations with caching and optimization
    
    This class now uses the flexible model management system and supports
    multiple model backends.
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize the LLM interface
        
        Args:
            config: LLM configuration object
        """
        self.config = config
        self.cache = TranslationCache(
            max_size=1000 if config.cache_enabled else 0,
            ttl_seconds=config.cache_ttl_hours * 3600
        )
        self._model_lock = threading.Lock()
        self._current_model: Optional[BaseModel] = None
        self._model_name: Optional[str] = None
        
        # Initialize model manager
        manager_config = {
            'model_dir': str(Path(config.model_path).parent),
            'default_model': config.model_type,
            'auto_download': getattr(config, 'auto_download', False),
            'max_loaded_models': 1,  # LLMInterface manages one model at a time
            'model_configs': {
                config.model_type: self._get_model_config()
            }
        }
        self._manager = ModelManager(manager_config)
        
        # Validate configuration
        issues = config.validate()
        if issues:
            logger.warning(f"Configuration issues: {', '.join(issues)}")
    
    def _get_model_config(self) -> Dict[str, Any]:
        """Convert LLMConfig to model-specific configuration"""
        return {
            'n_ctx': self.config.n_ctx,
            'n_batch': self.config.n_batch,
            'n_threads': self.config.n_threads,
            'n_gpu_layers': self.config.n_gpu_layers,
            'temperature': self.config.temperature,
            'top_p': self.config.top_p,
            'top_k': self.config.top_k,
            'repeat_penalty': self.config.repeat_penalty,
            'max_tokens': self.config.max_tokens,
            'seed': -1,
            'validation_level': self.config.validation_level,
        }
    
    def initialize_model(self, model_name: Optional[str] = None) -> None:
        """
        Initialize the language model
        
        Args:
            model_name: Optional model name to load (defaults to config)
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If model loading fails
        """
        model_to_load = model_name or self.config.model_type
        
        # Check if already loaded
        if self._current_model and self._model_name == model_to_load:
            logger.info(f"Model '{model_to_load}' already initialized")
            return
        
        # Check if model exists in registry
        if not model_exists(model_to_load):
            available = ", ".join(list_available_models())
            raise ValueError(
                f"Model '{model_to_load}' not found. "
                f"Available models: {available}"
            )
        
        # Determine model path
        model_path = self.config.get_model_path()
        if model_name and model_name != self.config.model_type:
            # Use a different path for different models
            model_dir = model_path.parent.parent / model_name
            model_path = model_dir / f"{model_name}.gguf"
        
        logger.info(f"Loading model '{model_to_load}' from: {model_path}")
        
        try:
            with self._model_lock:
                # Unload current model if different
                if (self._current_model and
                        self._model_name and
                        self._model_name != model_to_load):
                    self._manager.unload_model(self._model_name)
                
                # Load new model
                self._current_model = self._manager.load_model(
                    model_to_load, model_path
                )
                self._model_name = model_to_load
                
                logger.info(f"Model '{model_to_load}' loaded successfully")
                
        except Exception as e:
            raise RuntimeError(
                f"Failed to load model '{model_to_load}': {str(e)}"
            )
    
    def translate(self,
                  instruction: str,
                  context: Optional[Dict[str, Any]] = None) -> str:
        """
        Translate an English instruction to Python code
        
        Args:
            instruction: English instruction to translate
            context: Optional context information (e.g., surrounding code)
            
        Returns:
            Generated Python code
            
        Raises:
            RuntimeError: If model is not initialized
        """
        if not self._current_model:
            self.initialize_model()
        
        # Create cache key
        cache_key = self._create_cache_key(instruction, context)
        
        # Check cache
        if self.config.cache_enabled:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug("Cache hit for instruction")
                return cached_result
        
        try:
            # Use the model's translate_instruction method
            if self._current_model:
                code = self._current_model.translate_instruction(
                    instruction, context
                )
            else:
                raise RuntimeError("Model not initialized")
            
            # Cache result
            if self.config.cache_enabled and code:
                self.cache.put(cache_key, code)
            
            return code
            
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            raise RuntimeError(f"Failed to translate instruction: {str(e)}")
    
    def batch_translate(self, instructions: List[str]) -> List[str]:
        """
        Translate multiple instructions in batch
        
        Args:
            instructions: List of English instructions
            
        Returns:
            List of generated Python code snippets
        """
        if not self._current_model:
            self.initialize_model()
        
        # Use model's batch_translate if available, otherwise iterate
        if (self._current_model and
                hasattr(self._current_model, 'batch_translate')):
            return self._current_model.batch_translate(instructions)
        
        results = []
        for instruction in instructions:
            try:
                code = self.translate(instruction)
                results.append(code)
            except Exception as e:
                logger.error(
                    f"Failed to translate: {instruction[:50]}... - {str(e)}"
                )
                results.append(f"# Error: Failed to translate - {str(e)}")
        
        return results
    
    def refine_code(self, code: str, error_context: str) -> str:
        """
        Attempt to fix code based on error feedback
        
        Args:
            code: Code that needs fixing
            error_context: Error message or context
            
        Returns:
            Refined Python code
        """
        if not self._current_model:
            self.initialize_model()
        
        try:
            if self._current_model:
                return self._current_model.refine_code(code, error_context)
            else:
                return code
        except Exception as e:
            logger.error(f"Code refinement failed: {str(e)}")
            return code  # Return original code if refinement fails
    
    def switch_model(self, model_name: str) -> None:
        """
        Switch to a different model
        
        Args:
            model_name: Name of the model to switch to
        """
        logger.info(f"Switching from '{self._model_name}' to '{model_name}'")
        self.initialize_model(model_name)
        
        # Clear cache when switching models
        self.cache.clear()
    
    def list_available_models(self) -> List[str]:
        """
        List all available models
        
        Returns:
            List of model names
        """
        return list_available_models()
    
    def get_current_model(self) -> Optional[str]:
        """
        Get the name of the currently loaded model
        
        Returns:
            Model name or None if no model loaded
        """
        return self._model_name
    
    def shutdown(self) -> None:
        """
        Shutdown the model and free resources
        """
        logger.info("Shutting down LLM interface")
        
        with self._model_lock:
            if self._current_model:
                self._manager.shutdown()
                self._current_model = None
                self._model_name = None
        
        # Clear cache
        self.cache.clear()
        
        logger.info("LLM interface shutdown complete")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model
        
        Returns:
            Dictionary with model information
        """
        if not self._current_model:
            return {
                "status": "not_initialized",
                "model_name": None,
                "available_models": self.list_available_models()
            }
        
        model_info = self._current_model.get_info()
        model_info.update({
            "cache_enabled": self.config.cache_enabled,
            "cache_size": (
                len(self.cache._cache) if self.config.cache_enabled else 0
            ),
            "manager_info": self._manager.get_memory_usage()
        })
        
        return model_info
    
    def warmup(self):
        """
        Warm up the model with a simple generation
        This can help with initial latency
        """
        if not self._current_model:
            self.initialize_model()
        
        logger.info("Warming up model...")
        try:
            if self._current_model:
                self._current_model.warmup()
                logger.info("Model warmup complete")
        except Exception as e:
            logger.warning(f"Warmup failed: {e}")
    
    def _create_cache_key(self,
                          instruction: str,
                          context: Optional[Dict[str, Any]]) -> str:
        """Create a unique cache key for instruction + context"""
        key_data = {
            "instruction": instruction,
            "context": context or {},
            "model": self._model_name
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    # Backward compatibility methods
    def _validate_and_clean_code(self, code: str) -> str:
        """
        Backward compatibility method
        
        The new model system handles validation internally
        """
        return code
    
    # Backward compatibility properties for tests
    @property
    def _initialized(self) -> bool:
        """Backward compatibility property"""
        return self._current_model is not None
    
    @_initialized.setter
    def _initialized(self, value: bool):
        """Backward compatibility setter"""
        # This is a no-op for compatibility
        pass
    
    @property
    def model(self):
        """Backward compatibility property"""
        return self._current_model
    
    @model.setter
    def model(self, value):
        """Backward compatibility setter"""
        self._current_model = value
    
    def _attempt_syntax_fix(self, code: str) -> str:
        """
        Backward compatibility method
        
        The new model system handles syntax fixing internally
        """
        return code


# Convenience factory function
def create_llm_interface(config_path: Optional[str] = None,
                         model_name: Optional[str] = None) -> LLMInterface:
    """
    Create an LLM interface with configuration
    
    Args:
        config_path: Optional path to configuration file
        model_name: Optional model name to override config
        
    Returns:
        Initialized LLMInterface
    """
    from .config import ConfigManager
    
    config = ConfigManager.load(config_path)
    
    # Override model type if specified
    if model_name:
        config.llm.model_type = model_name
    
    interface = LLMInterface(config.llm)
    interface.initialize_model()
    
    return interface