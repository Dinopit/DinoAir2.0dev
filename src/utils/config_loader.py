"""
Configuration Loader for DinoAir
Handles loading and managing application configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    if env_path.exists():
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip().strip('"').strip("'")
                        env_vars[key.strip()] = value
        except Exception as e:
            from ..utils.logger import Logger
            logger = Logger()
            logger.error(f"Error loading .env file: {e}")
    return env_vars


class ConfigLoader:
    """Loads and manages application configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "app_config.json"
        self.env_path = Path(__file__).parent.parent.parent / ".env"
        self.config_data: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file and environment"""
        # Load .env file first
        self.env_vars = load_env_file(self.env_path)
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                self.create_default_config()
                
            # Override with environment variables
            self._apply_env_overrides()
            
        except Exception as e:
            print(f"Error loading config: {e}")
            self.create_default_config()
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to config"""
        env_mappings = {
            'DEBUG': 'app.debug',
            'LOG_LEVEL': 'logging.level',
            'DISABLE_WATCHDOG': 'app.disable_watchdog',
            'DB_TIMEOUT': 'database.connection_timeout',
            'OLLAMA_HOST': 'ollama.api_base',
            'OLLAMA_TIMEOUT': 'ollama.timeout',
            'DEFAULT_MODEL': 'ollama.default_model',
            'MAX_TOKENS': 'ollama.generation_params.max_tokens',
            'ENABLE_PROFANITY_FILTER': 'input_processing.enable_profanity_filter',
            'ENABLE_PATTERN_DETECTION': 'input_processing.enable_pattern_detection',
            'CACHE_ENABLED': 'pseudocode_translator.cache_enabled',
            'ENABLE_DEBUG_SIGNALS': 'ui.enable_debug_signals'
        }
        
        for env_key, config_key in env_mappings.items():
            if env_key in self.env_vars:
                value = self.env_vars[env_key]
                # Convert string values to appropriate types
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '').isdigit():
                    value = float(value)
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                self.set(config_key, value, save=False)
    
    def create_default_config(self) -> None:
        """Create default configuration"""
        self.config_data = {
            "app": {
                "name": "DinoAir 2.0",
                "version": "2.0.0",
                "theme": "light",
                "auto_save": True,
                "backup_interval": 300
            },
            "database": {
                "backup_on_startup": True,
                "cleanup_interval": 3600,
                "max_backup_files": 10
            },
            "ai": {
                "model": "gpt-3.5-turbo",
                "max_tokens": 2000,
                "temperature": 0.7
            },
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "font_size": 12,
                "show_sidebar": True
            }
        }
        self.save_config()
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            from ..utils.logger import Logger
            logger = Logger()
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'app.name')"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable value"""
        return self.env_vars.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        if save:
            self.save_config()
