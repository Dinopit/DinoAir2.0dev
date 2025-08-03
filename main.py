"""
DinoAir 2.0 - Main Application Entry Point
Modular note-taking application with AI capabilities
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.utils import ConfigLoader, Logger
from src.utils.Watchdog import SystemWatchdog
from src.utils.watchdog_compat import create_watchdog_adapter
from src.database import initialize_user_databases
from src.gui import MainWindow


class DinoAirApp:
    """Main application class"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.config = ConfigLoader()
        self.logger = Logger()
        self.db_manager = None
        self.watchdog = None
        
    def initialize_app(self):
        """Initialize the Qt application"""
        # Enable High DPI scaling before creating QApplication
        if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(
                Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
            )
        
        # Set High DPI scale factor rounding policy
        if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(self.config.get("app.name", "DinoAir 2.0"))
        self.app.setApplicationVersion(self.config.get("app.version", "2.0.0"))
        self.app.setOrganizationName("DinoAir Development")
        
        # Set application style
        if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
            self.app.setAttribute(
                Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True
            )
        
    def initialize_database(self, user_name="default_user"):
        """Initialize user databases"""
        try:
            def gui_feedback(message):
                self.logger.info(message)
                # In future, this could update a splash screen or status bar
                
            self.db_manager = initialize_user_databases(
                user_name, gui_feedback
            )
            self.logger.info("Database initialization completed")
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            # Show error dialog to user
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, 
                "Database Error", 
                f"Failed to initialize databases:\n{str(e)}\n\n"
                f"Please check permissions and try again."
            )
            return False
        return True
        
    def create_main_window(self):
        """Create and show the main window"""
        try:
            self.main_window = MainWindow()
            
            # Set window title to include DinoAir branding
            self.main_window.setWindowTitle(
                "DinoAir 2.0 - Powered by DinoPit Studios"
            )
            
            # Pass configuration and database manager if needed
            if hasattr(self.main_window, 'set_config'):
                self.main_window.set_config(self.config)
            if hasattr(self.main_window, 'set_db_manager'):
                self.main_window.set_db_manager(self.db_manager)
            if hasattr(self.main_window, 'set_logger'):
                self.main_window.set_logger(self.logger)
                
            self.main_window.show()
            
        except Exception as e:
            self.logger.error(f"Failed to create main window: {e}")
            return False
        return True
        
    def initialize_watchdog(self):
        """Initialize the system watchdog if enabled"""
        try:
            # Check if watchdog is disabled via environment variable
            import os
            disable_watchdog = os.environ.get(
                'DINOAIR_DISABLE_WATCHDOG', ''
            ).lower() in ['1', 'true', 'yes']
            if disable_watchdog:
                self.logger.info(
                    "Watchdog monitoring is disabled via environment variable"
                )
                return
                
            # Check if Qt-based watchdog should be used
            use_qt_env = os.environ.get(
                'DINOAIR_USE_QT_WATCHDOG', ''
            ).lower() in ['1', 'true', 'yes']
            use_qt_config = self.config.get(
                "watchdog.use_qt_implementation", True
            )
            use_qt = use_qt_env or use_qt_config
                
            # Check if watchdog is enabled in configuration
            watchdog_enabled = self.config.get("watchdog.enabled", True)
            
            if not watchdog_enabled:
                self.logger.info(
                    "Watchdog monitoring is disabled in configuration"
                )
                return
                
            # Get watchdog configuration values
            vram_threshold = self.config.get(
                "watchdog.vram_threshold_percent", 95.0
            )
            max_processes = self.config.get(
                "watchdog.max_dinoair_processes", 3
            )
            check_interval = self.config.get(
                "watchdog.check_interval_seconds", 30
            )
            self_terminate = self.config.get(
                "watchdog.self_terminate_on_critical", False
            )
            
            # Create alert callback that converts between AlertLevel types
            def gui_alert_callback(level, message):
                """Convert Watchdog AlertLevel to GUI AlertLevel and forward"""
                # Import the GUI AlertLevel locally to avoid circular imports
                from src.gui.components.notification_widget import (
                    AlertLevel as GuiAlertLevel
                )
                
                # Map Watchdog AlertLevel to GUI AlertLevel
                level_map = {
                    "info": GuiAlertLevel.INFO,
                    "warning": GuiAlertLevel.WARNING,
                    "critical": GuiAlertLevel.CRITICAL
                }
                
                # Convert the Watchdog AlertLevel to GUI AlertLevel
                gui_level = level_map.get(level.value, GuiAlertLevel.INFO)
                
                # Forward to the main window if it exists
                if self.main_window:
                    self.main_window.watchdog_alert_handler(gui_level, message)
                else:
                    # Fallback to logger if GUI not ready
                    self.logger.warning(
                        f"GUI not ready for alert: {level.value} - {message}"
                    )
            
            # Forward metrics to GUI and store in database
            def gui_metrics_callback(metrics):
                """Forward metrics to GUI handler and store in database"""
                # Forward to GUI
                if self.main_window:
                    self.main_window.watchdog_metrics_handler(metrics)
                else:
                    # Log if GUI not ready (should rarely happen)
                    self.logger.debug("GUI not ready for metrics update")
                
                # Store metrics in database if enabled
                metrics_storage_enabled = self.config.get(
                    "watchdog.store_metrics", True
                )
                if metrics_storage_enabled and self.db_manager:
                    try:
                        # Get metrics manager and store the metric
                        metrics_manager = (
                            self.db_manager.get_watchdog_metrics_manager()
                        )
                        
                        # Import and create WatchdogMetric from SystemMetrics
                        from src.models.watchdog_metrics import WatchdogMetric
                        metric = WatchdogMetric.from_system_metrics(metrics)
                        
                        # Use buffering for better performance
                        metrics_manager.buffer_metric(metric)
                        
                    except Exception as e:
                        # Log error but don't let it affect monitoring
                        self.logger.debug(f"Failed to store metrics: {e}")
            
            # Create watchdog instance with GUI callbacks
            if use_qt:
                self.logger.info("Using Qt-based watchdog implementation")
                self.watchdog = create_watchdog_adapter(
                    use_qt=True,
                    alert_callback=gui_alert_callback,
                    metrics_callback=gui_metrics_callback,
                    vram_threshold_percent=vram_threshold,
                    max_dinoair_processes=max_processes,
                    check_interval_seconds=check_interval,
                    self_terminate_on_critical=self_terminate
                )
            else:
                self.logger.info("Using legacy ThreadPoolExecutor watchdog")
                self.watchdog = SystemWatchdog(
                    alert_callback=gui_alert_callback,
                    metrics_callback=gui_metrics_callback,
                    vram_threshold_percent=vram_threshold,
                    max_dinoair_processes=max_processes,
                    check_interval_seconds=check_interval,
                    self_terminate_on_critical=self_terminate
                )
            
            # Configure metrics widget with max processes setting
            if self.main_window:
                self.main_window.set_watchdog_config(max_processes)
            
            self.logger.info(
                f"Watchdog initialized with VRAM threshold: "
                f"{vram_threshold}%, max processes: {max_processes}, "
                f"check interval: {check_interval}s, "
                f"type: {'Qt-based' if use_qt else 'Legacy'}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize watchdog: {e}")
            # Continue running without watchdog on initialization failure
            self.watchdog = None
        
    def run(self):
        """Run the application"""
        self.logger.info("Starting DinoAir 2.0...")
        
        # Initialize Qt application
        self.initialize_app()
        
        # Initialize databases
        if not self.initialize_database():
            return 1
            
        # Create main window first (needed for GUI alerts)
        if not self.create_main_window():
            return 1
            
        # Set app instance reference in main window
        if self.main_window and hasattr(self.main_window, 'set_app_instance'):
            self.main_window.set_app_instance(self)
            
        # Initialize watchdog monitoring after GUI is ready
        self.initialize_watchdog()
        
        # Start watchdog monitoring if initialized
        if self.watchdog:
            try:
                self.watchdog.start_monitoring()
                self.logger.info("Watchdog monitoring started")
            except Exception as e:
                self.logger.error(f"Failed to start watchdog monitoring: {e}")
            
        # Start event loop
        self.logger.info("Application started successfully")
        return self.app.exec()
        
    def cleanup(self):
        """Cleanup resources before exit"""
        self.logger.info("Shutting down DinoAir 2.0...")
        
        # Stop watchdog monitoring if running
        if (self.watchdog and
                hasattr(self.watchdog, '_monitoring') and
                self.watchdog._monitoring):
            try:
                self.watchdog.stop_monitoring()
                self.logger.info("Watchdog monitoring stopped")
            except Exception as e:
                self.logger.error(f"Error stopping watchdog: {e}")
        
        # Flush any buffered metrics before cleanup
        if self.db_manager:
            try:
                metrics_manager = (
                    self.db_manager.get_watchdog_metrics_manager()
                )
                metrics_manager.flush_buffer()
                self.logger.info("Flushed buffered metrics to database")
            except Exception as e:
                self.logger.debug(f"Error flushing metrics: {e}")
        
        if self.db_manager:
            try:
                # Get retention period from config
                retention_days = self.config.get(
                    "watchdog.metrics_retention_days", 7
                )
                self.db_manager.clean_memory_database(retention_days)
            except Exception as e:
                self.logger.error(f"Error during database cleanup: {e}")
                
        self.logger.info("Application shutdown complete")


def main():
    """Main entry point"""
    app = DinoAirApp()
    
    try:
        exit_code = app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        exit_code = 0
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit_code = 1
    finally:
        app.cleanup()
        
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
