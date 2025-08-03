"""
Window state persistence manager for saving and restoring window geometry,
state, and splitter positions across application sessions.
"""

import json
import os
from typing import Dict, Any, Optional, List
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QWidget, QSplitter

from .logger import Logger
from .scaling import ScalingHelper


class WindowStateManager:
    """Manages window state persistence for application sessions."""
    
    def __init__(self):
        """Initialize the WindowStateManager."""
        self.config_dir = "config"
        self.state_file = os.path.join(self.config_dir, "window_state.json")
        self._ensure_config_dir()
        self.state_data = self._load_state()
        self.logger = Logger()
    
    def _ensure_config_dir(self):
        """Ensure the config directory exists."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except Exception as e:
                self.logger.error(f"Failed to create config directory: {e}")
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from JSON file or return default state."""
        default_state = {
            "window": {
                "geometry": [100, 100, 1200, 800],  # x, y, width, height
                "maximized": False,
                "zoom_level": 1.0
            },
            "splitters": {
                "main_bottom": [70, 30],  # percentages
                "notes_content": [30, 70],
                "notes_tag_panel": 250  # scaled width
            }
        }
        
        if not os.path.exists(self.state_file):
            return default_state
        
        try:
            with open(self.state_file, 'r') as f:
                loaded_state = json.load(f)
                # Merge with default to ensure all keys exist
                for key in default_state:
                    if key not in loaded_state:
                        loaded_state[key] = default_state[key]
                    elif isinstance(default_state[key], dict):
                        for subkey in default_state[key]:
                            if subkey not in loaded_state[key]:
                                loaded_state[key][subkey] = \
                                    default_state[key][subkey]
                return loaded_state
        except Exception as e:
            self.logger.error(f"Failed to load window state: {e}")
            return default_state
    
    def _save_state(self):
        """Save current state to JSON file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save window state: {e}")
    
    def save_window_state(self, window: QWidget):
        """
        Save window geometry and state.
        
        Args:
            window: The main window widget
        """
        try:
            # Only save geometry if window is not maximized
            if not window.isMaximized():
                geometry = window.geometry()
                self.state_data["window"]["geometry"] = [
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height()
                ]
            
            # Save maximized state
            self.state_data["window"]["maximized"] = window.isMaximized()
            
            self._save_state()
            self.logger.info("Window state saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save window state: {e}")
    
    def restore_window_state(self, window: QWidget):
        """
        Restore window geometry and state.
        
        Args:
            window: The main window widget
        """
        try:
            # Restore geometry
            geometry = self.state_data["window"]["geometry"]
            window.setGeometry(QRect(
                geometry[0], geometry[1], 
                geometry[2], geometry[3]
            ))
            
            # Restore maximized state
            if self.state_data["window"]["maximized"]:
                window.showMaximized()
            
            self.logger.info("Window state restored successfully")
        except Exception as e:
            self.logger.error(f"Failed to restore window state: {e}")
    
    def save_zoom_level(self, zoom_level: float):
        """
        Save user zoom preference.
        
        Args:
            zoom_level: The zoom level to save
        """
        try:
            self.state_data["window"]["zoom_level"] = zoom_level
            self._save_state()
            self.logger.info(f"Zoom level saved: {zoom_level}")
        except Exception as e:
            self.logger.error(f"Failed to save zoom level: {e}")
    
    def get_zoom_level(self) -> float:
        """
        Retrieve saved zoom level.
        
        Returns:
            The saved zoom level, or 1.0 if not found
        """
        return self.state_data["window"].get("zoom_level", 1.0)
    
    def save_splitter_state(self, splitter_name: str, sizes: List[int]):
        """
        Save splitter sizes as percentages or scaled values.
        
        Args:
            splitter_name: Identifier for the splitter
            sizes: List of sizes from the splitter
        """
        try:
            if splitter_name == "notes_tag_panel":
                # For tag panel, save the scaled width directly
                # For tag panel, save the scaled width directly
                if sizes:
                    self.state_data["splitters"][splitter_name] = sizes[0]
                else:
                    self.state_data["splitters"][splitter_name] = 250
            else:
                # For other splitters, save as percentages
                total = sum(sizes)
                if total > 0:
                    percentages = [int(size * 100 / total) for size in sizes]
                    self.state_data["splitters"][splitter_name] = percentages
            
            self._save_state()
            self.logger.info(f"Splitter state saved: {splitter_name}")
        except Exception as e:
            self.logger.error(f"Failed to save splitter state: {e}")
    
    def get_splitter_state(self, splitter_name: str) -> Optional[List[int]]:
        """
        Get saved splitter state.
        
        Args:
            splitter_name: Identifier for the splitter
            
        Returns:
            List of sizes/percentages, or None if not found
        """
        return self.state_data["splitters"].get(splitter_name)
    
    def save_splitter_from_widget(self, splitter_name: str,
                                  splitter: QSplitter):
        """
        Save splitter state directly from a QSplitter widget.
        
        Args:
            splitter_name: Identifier for the splitter
            splitter: The QSplitter widget
        """
        sizes = splitter.sizes()
        self.save_splitter_state(splitter_name, sizes)
    
    def restore_splitter_to_widget(self, splitter_name: str,
                                   splitter: QSplitter):
        """
        Restore splitter state directly to a QSplitter widget.
        
        Args:
            splitter_name: Identifier for the splitter
            splitter: The QSplitter widget
        """
        try:
            saved_state = self.get_splitter_state(splitter_name)
            if saved_state:
                if splitter_name == "notes_tag_panel":
                    # For tag panel, saved_state is a single value
                    scaling_helper = ScalingHelper()
                    # Ensure saved_state is an int, not a list
                    # Ensure saved_state is an int, not a list
                    if isinstance(saved_state, int):
                        width_value = saved_state
                    else:
                        width_value = saved_state[0]
                    scaled_width = scaling_helper.scaled_size(width_value)
                    # Get current sizes and update first panel
                    current_sizes = splitter.sizes()
                    if len(current_sizes) >= 2:
                        remaining = sum(current_sizes) - scaled_width
                        splitter.setSizes([scaled_width, remaining])
                else:
                    # For percentage-based splitters
                    # Get total size based on orientation
                    if splitter.orientation() == 1:  # Horizontal
                        total_size = splitter.width()
                    else:  # Vertical
                        total_size = splitter.height()
                    # Convert percentages to actual sizes
                    sizes = [int(total_size * pct / 100)
                             for pct in saved_state]
                    splitter.setSizes(sizes)
                self.logger.info(f"Splitter state restored: {splitter_name}")
        except Exception as e:
            self.logger.error(f"Failed to restore splitter state: {e}")


# Global instance for easy access
window_state_manager = WindowStateManager()