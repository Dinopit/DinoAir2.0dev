"""
Metrics Display Widget - Real-time system resource monitoring display
"""

from datetime import timedelta

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
    QProgressBar, QFrame, QSizePolicy
)
from PySide6.QtCore import (
    Signal, Slot, QPropertyAnimation,
    QEasingCurve
)

from ...utils.scaling import get_scaling_helper


class AnimatedProgressBar(QProgressBar):
    """Progress bar with smooth animated value transitions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(150)  # Optimized timing for responsiveness
        # Linear is less CPU intensive
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._target_value = 0
        self._last_update_time = 0
        
    def setValue(self, value: int):
        """Override to animate value changes with throttling"""
        import time
        current_time = time.time()
        
        # Throttle updates to max once per 100ms
        if current_time - self._last_update_time < 0.1:
            # Just update target, don't restart animation
            self._target_value = value
            return
            
        self._last_update_time = current_time
        self._target_value = value
        
        # Only animate if change is significant (>5%)
        current = self.value()
        if abs(value - current) > 5:
            self._animation.stop()
            self._animation.setStartValue(current)
            self._animation.setEndValue(value)
            self._animation.start()
        else:
            # Small changes - just set directly
            super().setValue(value)


class MetricDisplay(QFrame):
    """Individual metric display with label, value, and progress bar"""
    
    def __init__(self, label: str, unit: str = "%",
                 show_progress: bool = True, parent=None):
        super().__init__(parent)
        self.label_text = label
        self.unit = unit
        self.show_progress = show_progress
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the metric display UI"""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        
        # Horizontal layout for compact display
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Metric label with scaled typography
        self.label = QLabel(self.label_text + ":")
        label_font_size = self._scaling_helper.get_font_for_role('caption')
        self.label.setStyleSheet(f"""
            QLabel {{
                color: #B0B0B0;
                font-weight: bold;
                font-size: {label_font_size}px;
                background: transparent;
            }}
        """)
        layout.addWidget(self.label)
        
        # Value label with scaled typography
        self.value_label = QLabel("0" + self.unit)
        value_font_size = self._scaling_helper.get_font_for_role(
            'body_secondary'
        )
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: #3498db;
                font-weight: bold;
                font-size: {value_font_size}px;
                background: transparent;
                min-width: 60px;
            }}
        """)
        layout.addWidget(self.value_label)
        
        # Progress bar (if enabled)
        if self.show_progress:
            self.progress_bar = AnimatedProgressBar()
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedHeight(6)
            self.progress_bar.setFixedWidth(80)
            self._update_progress_style(0)
            layout.addWidget(self.progress_bar)
            
    def _update_progress_style(self, value: float):
        """Update progress bar color based on value"""
        if value < 60:
            # Green - safe
            color = "#4CAF50"
        elif value < 80:
            # Yellow - warning
            color = "#FF9800"
        else:
            # Red - critical
            color = "#F44336"
            
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2B3A52;
                border: 1px solid #34495e;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        
    def update_value(self, value: float, suffix: str = ""):
        """Update the metric value and progress bar"""
        # Update value label
        if suffix:
            self.value_label.setText(f"{value:.1f}{self.unit} {suffix}")
        else:
            self.value_label.setText(f"{value:.1f}{self.unit}")
            
        # Update progress bar if shown
        if self.show_progress:
            self.progress_bar.setValue(int(value))
            self._update_progress_style(value)


class ProcessCountDisplay(QFrame):
    """Special display for process count with current/max format"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the process count display UI"""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Label with scaled typography
        self.label = QLabel("Processes:")
        label_font_size = self._scaling_helper.get_font_for_role('caption')
        self.label.setStyleSheet(f"""
            QLabel {{
                color: #B0B0B0;
                font-weight: bold;
                font-size: {label_font_size}px;
                background: transparent;
            }}
        """)
        layout.addWidget(self.label)
        
        # Count display with scaled typography
        self.count_label = QLabel("0 / 0")
        count_font_size = self._scaling_helper.get_font_for_role(
            'body_secondary'
        )
        self.count_label.setStyleSheet(f"""
            QLabel {{
                color: #3498db;
                font-weight: bold;
                font-size: {count_font_size}px;
                background: transparent;
                min-width: 50px;
            }}
        """)
        layout.addWidget(self.count_label)
        
    def update_count(self, current: int, max_allowed: int):
        """Update the process count display"""
        self.count_label.setText(f"{current} / {max_allowed}")
        
        # Update color based on proximity to limit
        ratio = current / max_allowed if max_allowed > 0 else 0
        if ratio < 0.6:
            color = "#4CAF50"  # Green
        elif ratio < 0.9:
            color = "#FF9800"  # Yellow
        else:
            color = "#F44336"  # Red
            
        count_font_size = self._scaling_helper.get_font_for_role(
            'body_secondary'
        )
        self.count_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-weight: bold;
                font-size: {count_font_size}px;
                background: transparent;
                min-width: 50px;
            }}
        """)


class UptimeDisplay(QFrame):
    """Display for watchdog uptime"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scaling_helper = get_scaling_helper()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the uptime display UI"""
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Label with scaled typography
        self.label = QLabel("Uptime:")
        label_font_size = self._scaling_helper.get_font_for_role('caption')
        self.label.setStyleSheet(f"""
            QLabel {{
                color: #B0B0B0;
                font-weight: bold;
                font-size: {label_font_size}px;
                background: transparent;
            }}
        """)
        layout.addWidget(self.label)
        
        # Time display with scaled typography
        self.time_label = QLabel("00:00")
        time_font_size = self._scaling_helper.get_font_for_role(
            'body_secondary'
        )
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: #3498db;
                font-weight: bold;
                font-size: {time_font_size}px;
                font-family: monospace;
                background: transparent;
                min-width: 50px;
            }}
        """)
        layout.addWidget(self.time_label)
        
    def update_uptime(self, seconds: int):
        """Update the uptime display"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        self.time_label.setText(f"{hours:02d}:{minutes:02d}")


class MetricsWidget(QWidget):
    """Main metrics display widget for system resource monitoring"""
    
    # Signal emitted when metrics are updated
    metrics_updated = Signal(object)  # SystemMetrics object
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_processes = 5  # Default, will be updated from watchdog
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the metrics widget UI"""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(0)
        
        # Set background
        self.setStyleSheet("""
            QWidget {
                background-color: #1E2A3A;
                border-top: 2px solid #3498db;
            }
        """)
        
        # Create metric displays
        self.vram_display = MetricDisplay("VRAM", "%")
        self.ram_display = MetricDisplay("RAM", "%")
        self.cpu_display = MetricDisplay("CPU", "%")
        self.process_display = ProcessCountDisplay()
        self.uptime_display = UptimeDisplay()
        
        # Add displays to layout with separators
        layout.addWidget(self.vram_display)
        layout.addWidget(self._create_separator())
        layout.addWidget(self.ram_display)
        layout.addWidget(self._create_separator())
        layout.addWidget(self.cpu_display)
        layout.addWidget(self._create_separator())
        layout.addWidget(self.process_display)
        layout.addWidget(self._create_separator())
        layout.addWidget(self.uptime_display)
        layout.addStretch()
        
        # Set size policy
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        self.setMaximumHeight(40)
    
    def _create_separator(self):
        """Create a vertical separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("""
            QFrame {
                color: #34495e;
                max-width: 1px;
                margin: 5px 10px;
            }
        """)
        return separator
        
    def set_max_processes(self, max_processes: int):
        """Set the maximum allowed processes for display"""
        self._max_processes = max_processes
        
    @Slot(object)
    def update_metrics(self, metrics):
        """Update all metric displays with new data.
        
        This slot is thread-safe and can be called from the watchdog thread.
        
        Args:
            metrics: SystemMetrics object from Watchdog
        """
        try:
            # Update VRAM display
            if metrics.vram_total_mb > 0:
                self.vram_display.update_value(metrics.vram_percent)
            else:
                self.vram_display.update_value(0.0)
                
            # Update RAM display
            self.ram_display.update_value(metrics.ram_percent)
            
            # Update CPU display
            self.cpu_display.update_value(metrics.cpu_percent)
            
            # Update process count
            self.process_display.update_count(
                metrics.dinoair_processes, self._max_processes
            )
            
            # Update uptime
            self.uptime_display.update_uptime(metrics.uptime_seconds)
            
            # Emit signal for any additional processing
            self.metrics_updated.emit(metrics)
            
        except Exception as e:
            # Log error but don't crash on update failures
            print(f"Error updating metrics display: {e}")