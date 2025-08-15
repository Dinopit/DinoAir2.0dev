"""
Configuration Loader for DinoAir
Handles loading and managing application configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


def load_env_file(env_path: Path) -> Dict[str, str]:
    """
    Load environment variables from a .env file into a dictionary.
    
    Given a Path to a dotenv-style file, parse lines of the form KEY=VALUE and return a dict of key→value.
    - Ignores empty lines and lines starting with `#`.
    - Splits on the first `=`; surrounding single or double quotes around values are stripped.
    - If the file does not exist or an I/O error occurs, the function logs the error and returns an empty dict.
    
    Parameters:
        env_path (Path): Path to the .env file to read.
    
    Returns:
        Dict[str, str]: A mapping of environment variable names to their string values.
    """
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
        """
        Initialize the ConfigLoader.
        
        Parameters:
            config_path (Optional[Path]): Optional path to the JSON config file. If omitted, defaults to
                "<project_root>/config/app_config.json" where <project_root> is three levels up from this file.
        
        Behavior:
            - Sets `config_path` and `env_path` (default: "<project_root>/.env").
            - Initializes in-memory stores `config_data` and `env_vars`.
            - Immediately calls `load_config()` to populate `config_data` (this may create defaults or persist the config).
        """
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "app_config.json"
        self.env_path = Path(__file__).parent.parent.parent / ".env"
        self.config_data: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """
        Load configuration from the configured file and apply environment overrides.
        
        Loads environment variables from the instance's env_path into self.env_vars, then attempts to read JSON configuration from self.config_path into self.config_data. If the config file does not exist, a default configuration is created (and persisted). After loading, environment variable overrides are applied to the in-memory configuration. On any read or parse error, the method falls back to creating the default configuration.
        """
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
        """
        Apply configured environment-variable overrides to the in-memory configuration.
        
        Reads known environment variables from self.env_vars and maps them to dotted
        configuration keys (see internal mapping). Values are coerced to appropriate
        types before assignment:
        
        - "true"/"false" (case-insensitive) → bool
        - integer-like strings → int
        - numeric strings with a single dot → float
        - otherwise left as str
        
        Each override is applied via self.set(config_key, value, save=False) so changes
        are stored in self.config_data but not immediately persisted to disk.
        """
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
                
                self.set(config_key, value, save=False)
    
    def create_default_config(self) -> None:
        """
        Set the loader's configuration to the built-in defaults and persist them.
        
        This overwrites self.config_data with the application's default nested configuration (sections: "app", "database", "ai", "ui") — including defaults such as app.name "DinoAir 2.0", auto_save enabled, AI model "gpt-3.5-turbo", and UI dimensions — then calls self.save_config() to write the defaults to disk.
        """
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
        """
        Persist the current in-memory configuration to the configured JSON file.
        
        This creates parent directories as needed and writes `self.config_data` to `self.config_path`
        as pretty-printed JSON (indent=4). On failure the error is logged through the module's Logger;
        exceptions are not propagated.
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            from ..utils.logger import Logger
            logger = Logger()
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Return a configuration value by dot-notated path (e.g., "app.name").
        
        Traverses nested dictionaries in self.config_data following the segments in `key`.
        If any segment is missing or an intermediate value is not a dict, `default` is returned.
        
        Parameters:
            key (str): Dot-notated path to the value.
            default (Any): Value to return if the path does not exist (defaults to None).
        
        Returns:
            Any: The value found at the given path, or `default` if not present.
        """
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default: str = "") -> str:
        """
        Return the value of a loaded environment variable.
        
        Looks up `key` in the configuration loader's in-memory environment variables (those parsed from the configured `.env` file). Does not query the process OS environment; if `key` is not present, returns `default`.
        
        Parameters:
            key (str): Environment variable name.
            default (str): Value to return if `key` is not found.
        
        Returns:
            str: The variable value from the loaded `.env` or `default` if missing.
        """
        return self.env_vars.get(key, default)
    
    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a configuration value identified by a dot-notated key path.
        
        The key may contain dots to address nested dictionaries (e.g. "app.theme.color"); intermediate
        dictionaries are created as needed. The final key's value is overwritten if it already exists.
        
        Parameters:
            key: Dot-notated path to the configuration entry.
            value: Value to assign to the configuration entry.
            save: If True, persist the updated configuration to disk by calling save_config().
        """
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        if save:
            self.save_config()
