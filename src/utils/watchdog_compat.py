"""Compatibility layer for ThreadPoolExecutor to Qt-based watchdog migration.

This module provides an adapter that maintains the old SystemWatchdog API
while using the new Qt-based implementation internally. This allows for
gradual migration without breaking existing code.

Enhanced with automatic fallback to legacy implementation if Qt fails.
"""

import threading
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .Watchdog import SystemMetrics, AlertLevel
from .logger import Logger

logger = Logger()


class WatchdogMode(Enum):
    """Available watchdog implementation modes."""
    QT = "qt"          # Qt-based implementation
    LEGACY = "legacy"  # ThreadPoolExecutor-based
    FALLBACK = "fallback"  # Simplified fallback


@dataclass
class FallbackConfig:
    """Configuration for fallback behavior."""
    auto_fallback: bool = True
    fallback_delay: float = 5.0  # Seconds to wait before fallback
    max_qt_retries: int = 3
    health_check_interval: int = 60  # Seconds between health checks


class WatchdogCompatibilityAdapter:
    """Adapter that provides old SystemWatchdog API with automatic fallback.
    
    This class mimics the interface of the original SystemWatchdog but uses
    the Qt-based WatchdogController internally when possible. It handles the
    translation between callback-based and signal-based approaches and
    automatically falls back to legacy implementation if Qt fails.
    """
    
    def __init__(self,
                 alert_callback: Optional[
                     Callable[[AlertLevel, str], None]
                 ] = None,
                 metrics_callback: Optional[
                     Callable[[SystemMetrics], None]
                 ] = None,
                 vram_threshold_percent: float = 95.0,
                 max_dinoair_processes: int = 5,
                 check_interval_seconds: int = 30,
                 self_terminate_on_critical: bool = False,
                 fallback_config: Optional[FallbackConfig] = None):
        """Initialize compatibility adapter with old SystemWatchdog parameters.
        
        Args:
            alert_callback: Function called when alerts are triggered
            metrics_callback: Function called with live metrics updates
            vram_threshold_percent: VRAM usage % that triggers warnings
            max_dinoair_processes: Max DinoAir processes before critical alert
            check_interval_seconds: How often to check system metrics
            self_terminate_on_critical: Whether to perform emergency shutdown
        """
        # Store callbacks and configuration
        self.alert_callback = alert_callback
        self.metrics_callback = metrics_callback
        self.vram_threshold = vram_threshold_percent
        self.max_processes = max_dinoair_processes
        self.check_interval = check_interval_seconds
        self.self_terminate = self_terminate_on_critical
        
        # Fallback configuration
        self.fallback_config = fallback_config or FallbackConfig()
        
        # Implementation tracking
        self.current_mode = WatchdogMode.QT
        self.qt_failures = 0
        self.controller = None
        self.legacy_watchdog = None
        self._monitoring = False
        self._health_check_thread = None
        self._startup_time = time.time()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Try to initialize Qt controller
        self._initialize_qt_controller()
        
    def _initialize_qt_controller(self):
        """Initialize Qt-based controller with error handling."""
        try:
            from .watchdog_qt import WatchdogController, WatchdogConfig
            
            # Create Qt-based configuration
            self.config = WatchdogConfig(
                vram_threshold=self.vram_threshold,
                max_processes=self.max_processes,
                check_interval=self.check_interval,
                self_terminate=self.self_terminate
            )
            
            # Create controller
            self.controller = WatchdogController(self.config)
            
            logger.info("Qt-based watchdog controller initialized")
            return True
            
        except ImportError as e:
            logger.warning(f"Qt modules not available: {e}")
            self._fallback_to_legacy("Qt modules not available")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize Qt controller: {e}")
            self.qt_failures += 1
            
            if self.qt_failures >= self.fallback_config.max_qt_retries:
                self._fallback_to_legacy(f"Qt initialization failed: {e}")
            return False
            
    def _fallback_to_legacy(self, reason: str):
        """Fall back to legacy implementation."""
        logger.warning(f"Falling back to legacy watchdog: {reason}")
        
        if self.controller:
            try:
                self.controller.stop_watchdog()
            except Exception:
                pass
            self.controller = None
            
        # Switch to legacy mode
        self.current_mode = WatchdogMode.LEGACY
        
        # Initialize legacy watchdog
        try:
            from .Watchdog import SystemWatchdog
            self.legacy_watchdog = SystemWatchdog(
                alert_callback=self.alert_callback,
                metrics_callback=self.metrics_callback,
                vram_threshold_percent=self.vram_threshold,
                max_dinoair_processes=self.max_processes,
                check_interval_seconds=self.check_interval,
                self_terminate_on_critical=self.self_terminate
            )
            logger.info("Legacy watchdog initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize legacy watchdog: {e}")
            # Last resort - use simplified fallback
            self.current_mode = WatchdogMode.FALLBACK
            self._start_fallback_monitoring()
            
    def _start_fallback_monitoring(self):
        """Start simplified fallback monitoring."""
        logger.warning("Using simplified fallback monitoring")
        
        def fallback_monitor():
            """Simplified monitoring loop."""
            while True:
                with self._lock:
                    if not self._monitoring:
                        break
                try:
                    # Collect basic metrics
                    from .Watchdog import SystemWatchdog
                    watchdog = SystemWatchdog()
                    metrics = watchdog.get_current_metrics(self._startup_time)
                    
                    # Call metrics callback
                    if self.metrics_callback:
                        self.metrics_callback(metrics)
                        
                    # Basic threshold checking
                    if metrics.vram_percent > self.vram_threshold:
                        if self.alert_callback:
                            self.alert_callback(
                                AlertLevel.WARNING,
                                f"High VRAM usage: {metrics.vram_percent:.1f}%"
                            )
                            
                    if metrics.dinoair_processes > self.max_processes:
                        if self.alert_callback:
                            self.alert_callback(
                                AlertLevel.CRITICAL,
                                f"Too many processes: "
                                f"{metrics.dinoair_processes}"
                            )
                            
                except Exception as e:
                    logger.error(f"Error in fallback monitoring: {e}")
                    
                # Sleep
                time.sleep(self.check_interval)
                
        # Start fallback thread
        self._fallback_thread = threading.Thread(
            target=fallback_monitor,
            daemon=True
        )
        self._fallback_thread.start()
        
    def _connect_signals(self):
        """Connect Qt signals to callback functions."""
        if not self.controller or not self.controller.signals:
            return
            
        try:
            from PySide6.QtCore import Qt
            
            # Connect alert signal to callback
            if self.alert_callback:
                self.controller.signals.alert_triggered.connect(
                    self._handle_alert, Qt.ConnectionType.QueuedConnection
                )
                
            # Connect metrics signal to callback
            if self.metrics_callback:
                self.controller.signals.metrics_ready.connect(
                    self._handle_metrics, Qt.ConnectionType.QueuedConnection
                )
                
            # Connect error signals for fallback detection
            self.controller.signals.error_occurred.connect(
                self._handle_qt_error, Qt.ConnectionType.QueuedConnection
            )
            
        except Exception as e:
            logger.error(f"Failed to connect Qt signals: {e}")
            
    def _handle_alert(self, level: AlertLevel, message: str):
        """Handle alert signal and forward to callback."""
        if self.alert_callback:
            try:
                self.alert_callback(level, message)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
                
    def _handle_metrics(self, metrics: SystemMetrics):
        """Handle metrics signal and forward to callback."""
        if self.metrics_callback:
            try:
                self.metrics_callback(metrics)
            except Exception as e:
                logger.error(f"Error in metrics callback: {e}")
                
    def _handle_qt_error(self, error_msg: str):
        """Handle Qt errors and consider fallback."""
        self.qt_failures += 1
        logger.error(f"Qt watchdog error ({self.qt_failures}): {error_msg}")
        
        if (self.fallback_config.auto_fallback and
                self.qt_failures >= self.fallback_config.max_qt_retries):
            # Stop current monitoring and fallback
            self.stop_monitoring()
            self._fallback_to_legacy(f"Too many Qt errors: {error_msg}")
            
            # Restart monitoring with fallback
            if self._monitoring:
                self.start_monitoring()
                
    def start_monitoring(self) -> None:
        """Start watchdog monitoring with appropriate implementation."""
        with self._lock:
            if self._monitoring:
                logger.warning("Watchdog already monitoring")
                return
                
            self._monitoring = True
            logger.info(
                f"Starting watchdog monitoring ({self.current_mode.value} mode)"
            )
        
        # Start health check thread if auto-fallback is enabled
        if self.fallback_config.auto_fallback:
            self._start_health_check()
        
        if self.current_mode == WatchdogMode.QT:
            # Try Qt-based monitoring
            try:
                from PySide6.QtCore import QCoreApplication
                
                # Ensure Qt application exists
                if not QCoreApplication.instance():
                    logger.warning("No Qt application found. Creating one.")
                    import sys
                    app = QCoreApplication(sys.argv)
                    self._qt_app = app
                    
                    # Start event loop in background thread
                    def run_qt_loop():
                        try:
                            app.exec()
                        except Exception as e:
                            logger.error(f"Qt event loop error: {e}")
                            
                    self._qt_thread = threading.Thread(
                        target=run_qt_loop,
                        daemon=True
                    )
                    self._qt_thread.start()
                
                # Start the controller
                if self.controller:
                    self.controller.start_watchdog()
                    
                    # Connect signals after controller is started
                    self._connect_signals()
                else:
                    raise Exception("Controller not initialized")
                
            except Exception as e:
                logger.error(f"Failed to start Qt monitoring: {e}")
                self._fallback_to_legacy(f"Qt start failed: {e}")
                
                # Restart with fallback
                if self._monitoring:
                    self.start_monitoring()
                    
        elif self.current_mode == WatchdogMode.LEGACY:
            # Use legacy implementation
            if self.legacy_watchdog:
                try:
                    self.legacy_watchdog.start_monitoring()
                except Exception as e:
                    logger.error(f"Legacy monitoring failed: {e}")
                    self.current_mode = WatchdogMode.FALLBACK
                    self._start_fallback_monitoring()
                    
        elif self.current_mode == WatchdogMode.FALLBACK:
            # Already started in _fallback_to_legacy
            pass
        
    def stop_monitoring(self) -> None:
        """Stop watchdog monitoring."""
        with self._lock:
            logger.info(
                f"Stopping watchdog monitoring ({self.current_mode.value} mode)"
            )
            
            if not self._monitoring:
                logger.warning("Watchdog not monitoring")
                return
                
            self._monitoring = False
        
        # Stop health check thread
        if self._health_check_thread:
            self._health_check_thread = None
            
        if self.current_mode == WatchdogMode.QT and self.controller:
            try:
                self.controller.stop_watchdog()
            except Exception as e:
                logger.error(f"Error stopping Qt watchdog: {e}")
                
            # Clean up Qt app if we created it
            if hasattr(self, '_qt_app'):
                try:
                    self._qt_app.quit()
                    if hasattr(self, '_qt_thread'):
                        self._qt_thread.join(timeout=2.0)
                except Exception as e:
                    logger.error(f"Error cleaning up Qt app: {e}")
                    
        elif self.current_mode == WatchdogMode.LEGACY and self.legacy_watchdog:
            try:
                self.legacy_watchdog.stop_monitoring()
            except Exception as e:
                logger.error(f"Error stopping legacy watchdog: {e}")
                
        elif self.current_mode == WatchdogMode.FALLBACK:
            # Fallback thread will stop due to _monitoring flag
            pass
                
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics (for compatibility).
        
        Returns:
            SystemMetrics: Current resource usage snapshot
        """
        try:
            # Use the static method from original SystemWatchdog
            from .Watchdog import SystemWatchdog
            return SystemWatchdog().get_current_metrics(self._startup_time)
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            # Return safe defaults
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
        
    def emergency_cleanup(self) -> Dict[str, int]:
        """Perform emergency cleanup of runaway processes.
        
        Returns:
            Dict[str, int]: Statistics of cleanup operation
        """
        from .Watchdog import SystemWatchdog
        return SystemWatchdog.emergency_cleanup()
        
    def get_status_report(self) -> str:
        """Generate a status report for display/logging.
        
        Returns:
            str: Multi-line status report with current metrics
        """
        # Get current metrics
        metrics = self.get_current_metrics()
        
        # Format uptime
        uptime_seconds = int(time.time() - self._startup_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        # Show self-terminate status
        terminate_status = "ON" if self.self_terminate else "OFF"
        
        # Build status based on current mode
        status_lines = [
            f"🐕 System Watchdog Status ({self.current_mode.value} mode)",
            f"├─ Implementation: {self.current_mode.value.upper()}"
        ]
        
        if self.current_mode == WatchdogMode.QT and self.controller:
            status = self.controller.get_status()
            if status:
                status_lines.extend([
                    f"├─ State: {status.circuit_breaker_state}",
                    f"├─ Error Count: {status.error_count}"
                ])
                
        status_lines.extend([
            f"├─ Uptime: {hours}h {minutes}m",
            f"├─ VRAM: {metrics.vram_percent:.1f}% "
            f"({metrics.vram_used_mb:.0f}MB)",
            f"├─ RAM: {metrics.ram_percent:.1f}% "
            f"({metrics.ram_used_mb:.0f}MB)",
            f"├─ CPU: {metrics.cpu_percent:.1f}%",
            f"├─ Total Processes: {metrics.process_count}",
            f"├─ DinoAir Processes: "
            f"{metrics.dinoair_processes}/{self.max_processes}",
            f"├─ Qt Failures: {self.qt_failures}",
            f"└─ Auto-Terminate: {terminate_status}"
        ])
        
        return "\n".join(status_lines)
        
    def _start_health_check(self):
        """Start periodic health check thread."""
        def health_check_loop():
            """Periodic health check for automatic recovery."""
            while True:
                with self._lock:
                    if not self._monitoring:
                        break
                try:
                    # Check current implementation health
                    if self.current_mode == WatchdogMode.QT:
                        if self.controller:
                            status = self.controller.get_status()
                            if not status or not status.is_running:
                                logger.warning("Qt watchdog not running")
                                self._handle_qt_error("Qt watchdog stopped")
                                
                except Exception as e:
                    logger.error(f"Health check error: {e}")
                    
                # Sleep
                time.sleep(self.fallback_config.health_check_interval)
                
        self._health_check_thread = threading.Thread(
            target=health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()


def create_watchdog_adapter(use_qt: bool = True,
                            fallback_config: Optional[FallbackConfig] = None,
                            **kwargs) -> Any:
    """Factory function to create appropriate watchdog implementation.
    
    Args:
        use_qt: If True, use Qt-based implementation via adapter.
                If False, use original SystemWatchdog.
        fallback_config: Configuration for fallback behavior
        **kwargs: Arguments passed to watchdog constructor
        
    Returns:
        Either WatchdogCompatibilityAdapter or SystemWatchdog instance
    """
    if use_qt:
        logger.info("Creating Qt-based watchdog with automatic fallback")
        return WatchdogCompatibilityAdapter(
            fallback_config=fallback_config,
            **kwargs
        )
    else:
        logger.info("Creating legacy ThreadPoolExecutor-based watchdog")
        from .Watchdog import SystemWatchdog
        return SystemWatchdog(**kwargs)