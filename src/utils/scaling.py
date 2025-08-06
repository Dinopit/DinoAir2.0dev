"""
DinoAir 2.0 - Scaling Helper Utility
Provides DPI-aware scaling functionality for GUI elements
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontMetrics, QFont
from PySide6.QtCore import QObject, Signal
from typing import Optional
import logging


class ScalingHelper(QObject):
    """Helper class for DPI-aware scaling of GUI elements"""
    
    # Standard baseline DPI (Windows/Linux default)
    BASELINE_DPI = 96
    
    # Zoom constraints
    MIN_ZOOM = 0.5  # 50%
    MAX_ZOOM = 3.0  # 300%
    DEFAULT_ZOOM = 1.0  # 100%
    ZOOM_STEP = 0.1  # 10%
    
    # Signal emitted when zoom level changes
    zoom_changed = Signal(float)
    
    def __init__(self):
        """Initialize the scaling helper"""
        super().__init__()
        self._scale_factor = None
        self._font_metrics = None
        self._zoom_level = self.DEFAULT_ZOOM
        self.logger = logging.getLogger(__name__)
        
    def get_scale_factor(self) -> float:
        """
        Get the DPI scale factor relative to 96 DPI baseline
        
        Returns:
            float: Scale factor (e.g., 1.0 for 96 DPI, 2.0 for 192 DPI)
        """
        if self._scale_factor is not None:
            return self._scale_factor
            
        try:
            app = QApplication.instance()
            if app is None:
                self.logger.warning(
                    "No QApplication instance available, "
                    "using default scale factor"
                )
                self._scale_factor = 1.0
                return self._scale_factor
            
            # Cast to QApplication for proper type checking
            qapp = app if isinstance(app, QApplication) else None
            if qapp is None:
                self._scale_factor = 1.0
                return self._scale_factor
                
            # Try to get the primary screen
            screen = qapp.primaryScreen()
            if screen is None:
                # Fallback: try to get any available screen
                screens = qapp.screens()
                if screens:
                    screen = screens[0]
                else:
                    self.logger.warning(
                        "No screens available, using default scale factor"
                    )
                    self._scale_factor = 1.0
                    return self._scale_factor
                    
            # Get logical DPI from the screen
            logical_dpi = screen.logicalDotsPerInch()
            
            # Calculate scale factor
            self._scale_factor = logical_dpi / self.BASELINE_DPI
            
            self.logger.info(
                f"Detected DPI: {logical_dpi}, "
                f"Scale factor: {self._scale_factor:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating scale factor: {e}")
            self._scale_factor = 1.0
            
        return self._scale_factor
        
    def set_zoom_level(self, zoom_level: float) -> None:
        """
        Set the user-controlled zoom level
        
        Args:
            zoom_level: Zoom level multiplier (1.0 = 100%, 2.0 = 200%, etc.)
        """
        # Clamp zoom level to constraints
        zoom_level = max(self.MIN_ZOOM, min(zoom_level, self.MAX_ZOOM))
        
        if zoom_level != self._zoom_level:
            self._zoom_level = zoom_level
            # Reset font metrics cache as it may be affected by zoom
            self._font_metrics = None
            self.logger.info(f"Zoom level set to: {zoom_level:.0%}")
            # Emit signal to notify listeners
            self.zoom_changed.emit(zoom_level)
    
    def get_current_zoom_level(self) -> float:
        """
        Get the current user-controlled zoom level
        
        Returns:
            float: Current zoom level (1.0 = 100%)
        """
        return self._zoom_level
    
    def scaled_font_size(self, base_size: int) -> int:
        """
        Scale a font size based on the current DPI and zoom level
        
        Args:
            base_size: Base font size in points
            
        Returns:
            int: Scaled font size in points
        """
        scale_factor = self.get_scale_factor()
        # Apply both DPI scaling and user zoom
        scaled_size = int(round(base_size * scale_factor * self._zoom_level))
        
        # Apply minimum and maximum constraints
        # Default constraints - config will be loaded from app_config.json
        scaled_size = max(8, min(scaled_size, 48))
            
        return scaled_size
        
    def scaled_size(self, base_size: int) -> int:
        """
        Scale a pixel size based on the current DPI and zoom level
        
        Args:
            base_size: Base size in pixels
            
        Returns:
            int: Scaled size in pixels
        """
        scale_factor = self.get_scale_factor()
        # Apply both DPI scaling and user zoom
        return int(round(base_size * scale_factor * self._zoom_level))
        
    def get_font_metrics(self, font: Optional[QFont] = None) -> QFontMetrics:
        """
        Get QFontMetrics for spacing calculations
        
        Args:
            font: Optional font to get metrics for.
                  If None, uses default application font
            
        Returns:
            QFontMetrics: Font metrics object for spacing calculations
        """
        if font is None:
            # Use cached metrics if available and no specific font requested
            if self._font_metrics is not None:
                return self._font_metrics
                
            app = QApplication.instance()
            if app and isinstance(app, QApplication):
                font = app.font()
            else:
                # Create a default font if no app instance
                font = QFont()
        
        # Ensure font is not None before creating metrics
        if font is None:
            font = QFont()
            
        font_metrics = QFontMetrics(font)
        
        # Cache default font metrics
        if self._font_metrics is None:
            self._font_metrics = font_metrics
            
        return font_metrics
        
    def reset_cache(self):
        """Reset cached values (useful when DPI changes)"""
        self._scale_factor = None
        self._font_metrics = None
        self.logger.debug("Scaling cache reset")
    
    def zoom_in(self) -> None:
        """Increase zoom level by one step"""
        new_zoom = self._zoom_level + self.ZOOM_STEP
        self.set_zoom_level(new_zoom)
    
    def zoom_out(self) -> None:
        """Decrease zoom level by one step"""
        new_zoom = self._zoom_level - self.ZOOM_STEP
        self.set_zoom_level(new_zoom)
    
    def reset_zoom(self) -> None:
        """Reset zoom level to default (100%)"""
        self.set_zoom_level(self.DEFAULT_ZOOM)
    
    def get_font_scale(self) -> dict:
        """Return systematic font scale for consistent typography
        
        Returns:
            dict: Font scale mapping with xs, sm, base, lg, xl, 2xl sizes
        """
        base_size = 16  # Increased from 14 to 16 for better readability
        return {
            'xs': self.scaled_font_size(10),
            'sm': self.scaled_font_size(12),
            'base': self.scaled_font_size(base_size),
            'lg': self.scaled_font_size(18),
            'xl': self.scaled_font_size(20),
            '2xl': self.scaled_font_size(24)
        }
    
    def get_dpi_scale(self) -> float:
        """Get the current DPI scale factor"""
        return self._scale_factor

    def get_font_for_role(self, role: str) -> int:
        """Get appropriate font size for UI role
        
        Args:
            role: UI role identifier (e.g., 'heading_primary', 'body_primary')
            
        Returns:
            int: Scaled font size for the specified role
        """
        scale = self.get_font_scale()
        role_map = {
            'heading_primary': scale['2xl'],
            'heading_secondary': scale['xl'],
            'heading_tertiary': scale['lg'],
            'body_primary': scale['base'],
            'body_secondary': scale['sm'],
            'caption': scale['xs']
        }
        return role_map.get(role, scale['base'])


# Global instance for easy access
_scaling_helper = None


def get_scaling_helper() -> ScalingHelper:
    """
    Get the global ScalingHelper instance
    
    Returns:
        ScalingHelper: The global scaling helper instance
    """
    global _scaling_helper
    if _scaling_helper is None:
        _scaling_helper = ScalingHelper()
    return _scaling_helper