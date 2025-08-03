"""
Configuration Loader for DinoAir
Handles loading and managing application configuration
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Loads and manages application configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "app_config.json"
        self.config_data: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                self.create_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            self.create_default_config()
    
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
            print(f"Error saving config: {e}")
    
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
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        self.save_config()
