"""
Simplified configuration management for Pseudocode Translator

This module provides a simple, user-friendly configuration system with:
- Sensible defaults that work out of the box
- Clear validation with helpful error messages
- Environment variable support
- Configuration profiles (development, production, testing)
- Simple version handling without complex migrations
"""

import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ConfigProfile(Enum):
    """Configuration profiles for different use cases"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    enabled: bool = True
    model_path: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1024
    auto_download: bool = False
    
    def validate(self) -> List[str]:
        """Validate model configuration"""
        errors = []
        
        if not self.name:
            errors.append("Model name cannot be empty")
        
        if not 0.0 <= self.temperature <= 2.0:
            errors.append(
                f"Temperature must be between 0.0 and 2.0, "
                f"got {self.temperature}"
            )
        
        if not 1 <= self.max_tokens <= 32768:
            errors.append(
                f"max_tokens must be between 1 and 32768, "
                f"got {self.max_tokens}"
            )
        
        return errors


@dataclass
class LLMConfig:
    """Language model configuration"""
    model_type: str = "qwen"
    model_path: str = "./models"
    n_ctx: int = 2048
    n_threads: int = 4
    n_gpu_layers: int = 0
    temperature: float = 0.3
    max_tokens: int = 1024
    cache_enabled: bool = True
    timeout_seconds: int = 30
    models: Dict[str, ModelConfig] = field(default_factory=dict)
    
    # For backward compatibility
    model_file: str = "qwen-7b-q4_k_m.gguf"
    model_configs: Dict[str, Any] = field(default_factory=dict)
    available_models: List[str] = field(default_factory=list)
    validation_level: str = "strict"
    cache_size_mb: int = 500
    cache_ttl_hours: int = 24
    auto_download: bool = False
    max_loaded_models: int = 1
    model_ttl_minutes: int = 60
    
    def __post_init__(self):
        """Initialize with default model if none provided"""
        if not self.models:
            self.models[self.model_type] = ModelConfig(
                name=self.model_type,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        
        # Backward compatibility: convert model_configs to models
        if self.model_configs and not self.models:
            for name, config in self.model_configs.items():
                if isinstance(config, dict):
                    self.models[name] = ModelConfig(
                        name=name,
                        enabled=config.get('enabled', True),
                        model_path=config.get('model_path'),
                        temperature=config.get('parameters', {}).get(
                            'temperature', self.temperature
                        ),
                        max_tokens=config.get('parameters', {}).get(
                            'max_tokens', self.max_tokens
                        ),
                        auto_download=config.get('auto_download', False)
                    )
    
    def validate(self) -> List[str]:
        """Validate LLM configuration"""
        errors = []
        
        # Validate basic settings
        if not self.model_type:
            errors.append("model_type cannot be empty")
        
        if not 512 <= self.n_ctx <= 32768:
            errors.append(
                f"n_ctx must be between 512 and 32768, got {self.n_ctx}"
            )
        
        if not 1 <= self.n_threads <= 32:
            errors.append(
                f"n_threads must be between 1 and 32, got {self.n_threads}"
            )
        
        if not 0 <= self.n_gpu_layers <= 100:
            errors.append(
                f"n_gpu_layers must be between 0 and 100, "
                f"got {self.n_gpu_layers}"
            )
        
        if not 0.0 <= self.temperature <= 2.0:
            errors.append(
                f"temperature must be between 0.0 and 2.0, "
                f"got {self.temperature}"
            )
        
        if not 1 <= self.timeout_seconds <= 600:
            errors.append(
                f"timeout_seconds must be between 1 and 600, "
                f"got {self.timeout_seconds}"
            )
        
        # Validate model configurations
        if self.model_type not in self.models:
            errors.append(
                f"Primary model '{self.model_type}' not found in "
                f"models configuration"
            )
        
        for name, model in self.models.items():
            model_errors = model.validate()
            errors.extend([f"Model '{name}': {e}" for e in model_errors])
        
        return errors
    
    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a specific model"""
        if model_name not in self.models:
            # Return default config
            return ModelConfig(name=model_name)
        return self.models[model_name]
    
    def get_model_path(self, model_name: Optional[str] = None) -> Path:
        """Get the full path to a model file (backward compatibility)"""
        name = model_name or self.model_type
        
        # Check if there's a specific path configured
        if name in self.models:
            model_config = self.models[name]
            if model_config.model_path:
                return Path(model_config.model_path)
        
        # Use default path structure
        base_path = Path(self.model_path)
        
        # For backward compatibility with the old structure
        if name == "qwen" and self.model_file:
            return base_path / "qwen-7b" / self.model_file
        
        # New structure: models/{model_name}/{model_name}.gguf
        return base_path / name / f"{name}.gguf"
    
    def add_model_config(self, model_config):
        """Add or update a model configuration (backward compatibility)"""
        if hasattr(model_config, 'name'):
            self.models[model_config.name] = ModelConfig(
                name=model_config.name,
                enabled=getattr(model_config, 'enabled', True),
                model_path=getattr(model_config, 'model_path', None),
                temperature=getattr(model_config, 'temperature', 0.3),
                max_tokens=getattr(model_config, 'max_tokens', 1024),
                auto_download=getattr(model_config, 'auto_download', False)
            )


@dataclass
class StreamingConfig:
    """Streaming configuration for large files"""
    enabled: bool = True
    enable_streaming: bool = True  # Backward compatibility alias
    chunk_size: int = 4096
    max_memory_mb: int = 100
    
    # Additional fields for backward compatibility
    auto_enable_threshold: int = 102400
    max_chunk_size: int = 8192
    min_chunk_size: int = 512
    overlap_size: int = 256
    respect_boundaries: bool = True
    max_lines_per_chunk: int = 100
    buffer_compression: bool = True
    eviction_policy: str = "lru"
    max_concurrent_chunks: int = 3
    chunk_timeout: float = 30.0
    enable_backpressure: bool = True
    max_queue_size: int = 10
    progress_callback_interval: float = 0.5
    enable_memory_monitoring: bool = True
    maintain_context_window: bool = True
    context_window_size: int = 1024
    
    def __post_init__(self):
        """Handle backward compatibility"""
        if hasattr(self, 'enable_streaming'):
            self.enabled = self.enable_streaming
    
    def validate(self) -> List[str]:
        """Validate streaming configuration"""
        errors = []
        
        if not 512 <= self.chunk_size <= 65536:
            errors.append(
                f"chunk_size must be between 512 and 65536, "
                f"got {self.chunk_size}"
            )
        
        if not 10 <= self.max_memory_mb <= 1000:
            errors.append(
                f"max_memory_mb must be between 10 and 1000, "
                f"got {self.max_memory_mb}"
            )
        
        return errors


@dataclass
class Config:
    """Main configuration class"""
    # Core settings
    llm: LLMConfig = field(default_factory=LLMConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    
    # Translation settings
    preserve_comments: bool = True
    preserve_docstrings: bool = True
    use_type_hints: bool = True
    indent_size: int = 4
    max_line_length: int = 88
    max_context_length: int = 2048
    auto_import_common: bool = True
    
    # Validation settings
    validate_imports: bool = True
    check_undefined_vars: bool = True
    allow_unsafe_operations: bool = False
    
    # GUI settings (for backward compatibility)
    gui_theme: str = "dark"
    gui_font_size: int = 12
    syntax_highlighting: bool = True
    
    # Version (for compatibility checking)
    version: str = "3.0"
    _version: str = "3.0"  # Backward compatibility
    
    def validate(self) -> List[str]:
        """Validate entire configuration"""
        errors = []
        
        # Validate nested configs
        errors.extend(self.llm.validate())
        errors.extend(self.streaming.validate())
        
        # Validate basic settings
        if self.indent_size not in [2, 4, 8]:
            errors.append(
                f"indent_size should be 2, 4, or 8, got {self.indent_size}"
            )
        
        if not 50 <= self.max_line_length <= 120:
            errors.append(
                f"max_line_length should be between 50 and 120, "
                f"got {self.max_line_length}"
            )
        
        return errors
    
    def apply_env_overrides(self):
        """Apply environment variable overrides"""
        # LLM overrides
        if val := os.getenv("PSEUDOCODE_LLM_MODEL_TYPE"):
            self.llm.model_type = val
        if val := os.getenv("PSEUDOCODE_LLM_TEMPERATURE"):
            try:
                self.llm.temperature = float(val)
            except ValueError:
                logger.warning(f"Invalid temperature value from env: {val}")
        if val := os.getenv("PSEUDOCODE_LLM_THREADS"):
            try:
                self.llm.n_threads = int(val)
            except ValueError:
                logger.warning(f"Invalid threads value from env: {val}")
        if val := os.getenv("PSEUDOCODE_LLM_GPU_LAYERS"):
            try:
                self.llm.n_gpu_layers = int(val)
            except ValueError:
                logger.warning(f"Invalid GPU layers value from env: {val}")
        
        # Streaming overrides
        if val := os.getenv("PSEUDOCODE_STREAMING_ENABLED"):
            self.streaming.enabled = val.lower() in ("true", "1", "yes", "on")
        if val := os.getenv("PSEUDOCODE_STREAMING_CHUNK_SIZE"):
            try:
                self.streaming.chunk_size = int(val)
            except ValueError:
                logger.warning(f"Invalid chunk size value from env: {val}")
        
        # Validation overrides
        if val := os.getenv("PSEUDOCODE_VALIDATE_IMPORTS"):
            self.validate_imports = val.lower() in ("true", "1", "yes", "on")
        if val := os.getenv("PSEUDOCODE_CHECK_UNDEFINED_VARS"):
            self.check_undefined_vars = val.lower() in (
                "true", "1", "yes", "on"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Ensure Path objects are converted to strings
        if 'llm' in data and 'model_path' in data['llm']:
            data['llm']['model_path'] = str(data['llm']['model_path'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create from dictionary"""
        # Handle nested dataclasses
        if 'llm' in data and isinstance(data['llm'], dict):
            models = data['llm'].pop('models', {})
            data['llm'] = LLMConfig(**data['llm'])
            # Recreate model configs
            for name, model_data in models.items():
                data['llm'].models[name] = ModelConfig(**model_data)
        
        if 'streaming' in data and isinstance(data['streaming'], dict):
            data['streaming'] = StreamingConfig(**data['streaming'])
        
        return cls(**data)


class ConfigManager:
    """Simple configuration manager"""
    
    DEFAULT_CONFIG_PATH = (
        Path.home() / ".pseudocode_translator" / "config.yaml"
    )
    
    @staticmethod
    def create_profile(profile: ConfigProfile) -> Config:
        """Create configuration from profile"""
        config = Config()
        
        if profile == ConfigProfile.DEVELOPMENT:
            # Development: Fast iteration, more verbose
            config.llm.temperature = 0.5
            config.llm.n_threads = os.cpu_count() or 4
            config.llm.timeout_seconds = 60
            config.streaming.enabled = True
            config.validate_imports = False  # Faster development
            
        elif profile == ConfigProfile.PRODUCTION:
            # Production: Stable, optimized
            config.llm.temperature = 0.3
            config.llm.n_gpu_layers = 20  # Use GPU if available
            config.llm.cache_enabled = True
            config.streaming.max_memory_mb = 200
            config.validate_imports = True
            config.check_undefined_vars = True
            
        elif profile == ConfigProfile.TESTING:
            # Testing: Minimal, fast
            config.llm.n_ctx = 512
            config.llm.max_tokens = 256
            config.llm.timeout_seconds = 10
            config.streaming.enabled = False
            config.llm.cache_enabled = False
        
        return config
    
    @staticmethod
    def load(path: Optional[Union[str, Path]] = None) -> Config:
        """Load configuration from file or create default"""
        config_path = Path(path) if path else ConfigManager.DEFAULT_CONFIG_PATH
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    if config_path.suffix in ['.yaml', '.yml']:
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
                
                config = Config.from_dict(data)
                
                # Handle version upgrades
                if 'version' not in data or data['version'] != config.version:
                    old_ver = data.get('version', '1.0')
                    logger.info(
                        f"Upgrading configuration from version {old_ver} "
                        f"to {config.version}"
                    )
                    ConfigManager._upgrade_config(config, old_ver)
                
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                logger.info("Using default configuration")
                config = Config()
        else:
            # Create default config
            config = Config()
            logger.info("No configuration file found, using defaults")
        
        # Apply environment overrides
        config.apply_env_overrides()
        
        # Validate
        errors = config.validate()
        if errors:
            logger.warning("Configuration has validation errors:")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return config
    
    @staticmethod
    def save(config: Config, path: Optional[Union[str, Path]] = None):
        """Save configuration to file"""
        config_path = Path(path) if path else ConfigManager.DEFAULT_CONFIG_PATH
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save based on file extension
        with open(config_path, 'w') as f:
            if config_path.suffix in ['.yaml', '.yml']:
                yaml.dump(
                    config.to_dict(), f, 
                    default_flow_style=False, 
                    sort_keys=False
                )
            else:
                json.dump(config.to_dict(), f, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
    
    @staticmethod
    def _upgrade_config(config: Config, old_version: str):
        """Simple config upgrade logic"""
        # Version 1.0 -> 3.0: Move flat settings to nested structure
        if old_version == "1.0" or old_version == "2.0":
            # Most settings should already be loaded correctly
            # Just ensure we have default models
            if not config.llm.models:
                config.llm.models[config.llm.model_type] = ModelConfig(
                    name=config.llm.model_type,
                    temperature=config.llm.temperature,
                    max_tokens=config.llm.max_tokens
                )
    
    @staticmethod
    def create_wizard() -> Config:
        """Interactive configuration wizard"""
        print("=== Pseudocode Translator Configuration Wizard ===\n")
        
        # Ask for profile
        print("Select a configuration profile:")
        print("1. Development (fast iteration, relaxed validation)")
        print("2. Production (optimized, strict validation)")
        print("3. Testing (minimal, fast)")
        print("4. Custom (configure everything)")
        
        choice = input("\nEnter choice [1-4] (default: 1): ").strip() or "1"
        
        profile_map = {
            "1": ConfigProfile.DEVELOPMENT,
            "2": ConfigProfile.PRODUCTION,
            "3": ConfigProfile.TESTING,
            "4": ConfigProfile.CUSTOM
        }
        
        profile = profile_map.get(choice, ConfigProfile.DEVELOPMENT)
        config = ConfigManager.create_profile(profile)
        
        if profile == ConfigProfile.CUSTOM:
            # Custom configuration
            print("\n--- LLM Configuration ---")
            default_model = config.llm.model_type
            config.llm.model_type = (
                input(f"Model type [{default_model}]: ").strip() 
                or default_model
            )
            
            try:
                threads = input(
                    f"CPU threads [{config.llm.n_threads}]: "
                ).strip()
                if threads:
                    config.llm.n_threads = int(threads)
            except ValueError:
                print("Invalid value, using default")
            
            try:
                gpu_layers = input(
                    f"GPU layers (0 for CPU only) "
                    f"[{config.llm.n_gpu_layers}]: "
                ).strip()
                if gpu_layers:
                    config.llm.n_gpu_layers = int(gpu_layers)
            except ValueError:
                print("Invalid value, using default")
            
            try:
                temp = input(
                    f"Temperature (0.0-2.0) [{config.llm.temperature}]: "
                ).strip()
                if temp:
                    config.llm.temperature = float(temp)
            except ValueError:
                print("Invalid value, using default")
            
            print("\n--- Code Style ---")
            default_hints = 'y' if config.use_type_hints else 'n'
            use_hints = input(
                f"Use type hints? (y/n) [{default_hints}]: "
            ).strip().lower()
            if use_hints:
                config.use_type_hints = use_hints == 'y'
            
            default_validate = 'y' if config.validate_imports else 'n'
            validate = input(
                f"Validate imports? (y/n) [{default_validate}]: "
            ).strip().lower()
            if validate:
                config.validate_imports = validate == 'y'
        
        print("\n--- Configuration Summary ---")
        print(f"Profile: {profile.value}")
        print(f"Model: {config.llm.model_type}")
        print(f"Threads: {config.llm.n_threads}")
        print(f"GPU Layers: {config.llm.n_gpu_layers}")
        print(f"Temperature: {config.llm.temperature}")
        print(f"Type Hints: {config.use_type_hints}")
        print(f"Validate Imports: {config.validate_imports}")
        
        return config
    
    @staticmethod
    def get_config_info(config_path: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a configuration file"""
        path = Path(config_path or ConfigManager.DEFAULT_CONFIG_PATH)
        
        info = {
            'path': str(path),
            'exists': path.exists(),
            'version': 'unknown',
            'is_valid': False,
            'issues': [],
            'needs_migration': False
        }
        
        if not path.exists():
            info['issues'].append("Configuration file does not exist")
            return info
        
        try:
            with open(path, 'r') as f:
                if path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            version = data.get('version', data.get('_version', '1.0'))
            info['version'] = version
            info['needs_migration'] = version not in ['3.0']
            
            # Try to validate
            config = Config.from_dict(data)
            errors = config.validate()
            info['is_valid'] = len(errors) == 0
            info['issues'].extend(errors)
            
        except Exception as e:
            info['issues'].append(f"Error loading config: {str(e)}")
        
        return info
    
    @staticmethod
    def create_default_config_file():
        """Create a default configuration file"""
        config = ConfigManager.create_profile(ConfigProfile.DEVELOPMENT)
        ConfigManager.save(config)
        return ConfigManager.DEFAULT_CONFIG_PATH
    
    @staticmethod
    def add_model_config(
        config: Config,
        model_name: str,
        model_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        auto_download: bool = False
    ) -> None:
        """Add or update a model configuration"""
        model_config = ModelConfig(
            name=model_name,
            model_path=model_path,
            temperature=(parameters.get('temperature', 0.3)
                         if parameters else 0.3),
            max_tokens=(parameters.get('max_tokens', 1024)
                        if parameters else 1024),
            auto_download=auto_download
        )
        config.llm.models[model_name] = model_config
    
    @staticmethod
    def validate(config: Config) -> List[str]:
        """Validate configuration (backward compatibility)"""
        return config.validate()


# Backward compatibility wrapper
class TranslatorConfig:
    """Wrapper for backward compatibility with old config system"""
    
    def __init__(self, config: Optional[Config] = None):
        self._config = config or Config()
        # Create nested structure for compatibility
        self.llm = self._config.llm
        self.streaming = self._config.streaming
    
    @property
    def preserve_comments(self) -> bool:
        return self._config.preserve_comments
    
    @property
    def preserve_docstrings(self) -> bool:
        return self._config.preserve_docstrings
    
    @property
    def use_type_hints(self) -> bool:
        return self._config.use_type_hints
    
    @property
    def indent_size(self) -> int:
        return self._config.indent_size
    
    @property
    def max_line_length(self) -> int:
        return self._config.max_line_length
    
    @property
    def validate_imports(self) -> bool:
        return self._config.validate_imports
    
    @property
    def check_undefined_vars(self) -> bool:
        return self._config.check_undefined_vars
    
    @property
    def allow_unsafe_operations(self) -> bool:
        return self._config.allow_unsafe_operations
    
    @property
    def max_context_length(self) -> int:
        return self._config.max_context_length
    
    @property
    def auto_import_common(self) -> bool:
        return self._config.auto_import_common
    
    @property
    def gui_theme(self) -> str:
        return self._config.gui_theme
    
    @property
    def gui_font_size(self) -> int:
        return self._config.gui_font_size
    
    @property
    def syntax_highlighting(self) -> bool:
        return self._config.syntax_highlighting
    
    @classmethod
    def load_from_file(cls, path: str) -> 'TranslatorConfig':
        """Load from file (backward compatibility)"""
        config = ConfigManager.load(path)
        return cls(config)
    
    def save_to_file(self, path: str):
        """Save to file (backward compatibility)"""
        ConfigManager.save(self._config, path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (backward compatibility)"""
        return self._config.to_dict()
    
    def validate_config(self) -> tuple[bool, List[str]]:
        """Validate configuration (backward compatibility)"""
        errors = self._config.validate()
        return len(errors) == 0, errors
    
    def update_available_models(self):
        """Update available models (backward compatibility stub)"""
        pass
    
    def get_model_path(self, model_name: Optional[str] = None) -> Path:
        """Get model path (backward compatibility)"""
        return self.llm.get_model_path(model_name)
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """Get model config (backward compatibility)"""
        model = self.llm.get_model_config(model_name)
        return {
            'name': model.name,
            'enabled': model.enabled,
            'temperature': model.temperature,
            'max_tokens': model.max_tokens,
            'auto_download': model.auto_download
        }


# Backward compatibility types and imports
try:
    from .config_schema import (
        ModelConfigSchema, LLMConfigSchema, StreamingConfigSchema
    )
except ImportError:
    # Fallback if old modules don't exist
    ModelConfigSchema = ModelConfig
    LLMConfigSchema = LLMConfig
    StreamingConfigSchema = StreamingConfig


# Backward compatibility functions
def load_config(path: Optional[str] = None) -> TranslatorConfig:
    """Deprecated: Use ConfigManager.load() instead"""
    config = ConfigManager.load(path)
    return TranslatorConfig(config)


def save_config(config: TranslatorConfig, path: Optional[str] = None):
    """Deprecated: Use ConfigManager.save() instead"""
    ConfigManager.save(config._config, path)


def validate_config(config: TranslatorConfig) -> List[str]:
    """Deprecated: Use ConfigManager.validate() instead"""
    return ConfigManager.validate(config._config)


# Stub classes for backward compatibility
@dataclass
class PromptConfig:
    """Configuration for prompt templates (backward compatibility)"""
    system_prompt: str = (
        "You are an expert Python programmer. Your task is to convert "
        "English instructions into clean, efficient Python code."
    )
    instruction_template: str = "Convert: {instruction}"
    refinement_template: str = "Fix: {code}"
    code_style: str = "pep8"
    include_type_hints: bool = True
    include_docstrings: bool = True
    
    def format_instruction(
        self, instruction: str, context: Optional[str] = None
    ) -> str:
        return self.instruction_template.format(instruction=instruction)
    
    def format_refinement(self, code: str, error: str) -> str:
        return self.refinement_template.format(code=code)


# Export simplified API
__all__ = [
    'Config',
    'LLMConfig', 
    'StreamingConfig',
    'ModelConfig',
    'ConfigManager',
    'ConfigProfile',
    'TranslatorConfig',  # For backward compatibility
    'PromptConfig',  # For backward compatibility
    'load_config',  # Deprecated
    'save_config',  # Deprecated
    'validate_config',  # Deprecated
    'ModelConfigSchema',  # For backward compatibility
    'LLMConfigSchema',  # For backward compatibility
    'StreamingConfigSchema'  # For backward compatibility
]