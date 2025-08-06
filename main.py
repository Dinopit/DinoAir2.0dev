"""
DinoAir 2.0 - Main Application Entry Point
Modular note-taking application with AI capabilities
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings, Qt

from src.utils import ConfigLoader, Logger
from src.utils.resource_manager import get_resource_manager, ResourceType
from src.utils.dependency_container import get_container
from src.utils.state_machine import get_state_machine, ApplicationState, transition_to_state
from src.database import initialize_user_databases
from src.gui import MainWindow
from src.tools.registry import ToolRegistry


class DinoAirApp:
    """Main application class"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.config = ConfigLoader()
        self.logger = Logger()
        self.db_manager = None
        self.watchdog = None
        self.tool_registry = None
        self.resource_manager = get_resource_manager()
        self.container = get_container()
        self.state_machine = get_state_machine()
        
        # Register basic dependencies
        self._register_core_dependencies()
        
        # Set up state machine callbacks
        self._setup_state_callbacks()
        
    def _register_core_dependencies(self):
        """Register core application dependencies."""
        # Register config and logger as instances
        self.container.register_instance("config", self.config)
        self.container.register_instance("logger", self.logger)
        self.container.register_instance("resource_manager", self.resource_manager)
        
        # Register application services
        self.container.register_singleton(
            "tool_registry", 
            ToolRegistry,
            initialization_order=20
        )
        
        # Register state machine
        self.container.register_instance("state_machine", self.state_machine)
        
    def _setup_state_callbacks(self):
        """Set up state machine callbacks for logging and monitoring."""
        def log_state_entry(state, from_state, context):
            self.logger.info(f"Entered state: {state.value} (from {from_state.value})")
            
        def log_state_exit(state, to_state, context):
            self.logger.debug(f"Exiting state: {state.value} (to {to_state.value})")
            
        # Register callbacks for all states
        for state in ApplicationState:
            self.state_machine.on_enter(state, log_state_entry)
            self.state_machine.on_exit(state, log_state_exit)
        
    def initialize_app(self):
        """Initialize the Qt application"""
        transition_to_state(ApplicationState.STARTING)
        
        # Enable GPU acceleration before creating QApplication
        # Use desktop OpenGL for better performance on Windows
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
        
        # Note: AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps are deprecated in Qt 6
        # High DPI scaling is now enabled by default in Qt 6
        
        # Disable animations on slow systems (optional)
        # QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton)
        
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(self.config.get("app.name", "DinoAir 2.0"))
        self.app.setApplicationVersion(self.config.get("app.version", "2.0.0"))
        self.app.setOrganizationName("DinoAir Development")
        
        # Register Qt application with resource manager
        self.resource_manager.register_resource(
            "qt_application",
            self.app,
            ResourceType.GUI_COMPONENT,
            cleanup_func=lambda: self.app.quit(),
            priority=10
        )
        
    def initialize_database(self, user_name="default_user"):
        """Initialize user databases"""
        try:
            def gui_feedback(message):
                self.logger.info(message)
                # In future, this could update a splash screen or status bar
                
            self.db_manager = initialize_user_databases(user_name, gui_feedback)
            self.logger.info("Database initialization completed")
            
            # Register database manager with dependency container and resource manager
            self.container.register_instance("database_manager", self.db_manager)
            
            self.resource_manager.register_resource(
                "database_manager",
                self.db_manager,
                ResourceType.DATABASE,
                cleanup_func=self.db_manager._cleanup_connections,
                priority=70
            )
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            # Show error dialog to user
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                None, 
                "Database Error", 
                f"Failed to initialize databases:\n{str(e)}\n\nPlease check permissions and try again."
            )
            return False
        return True
        
    def initialize_tools(self):
        """Initialize the tool registry and discover tools"""
        try:
            self.logger.info("Initializing tool registry...")
            # Use dependency container to get tool registry
            self.tool_registry = self.container.resolve("tool_registry")
            
            # Discover tools from the tools directory
            from pathlib import Path
            tools_dir = Path(__file__).parent / "src" / "tools" / "examples"
            
            if tools_dir.exists():
                summary = self.tool_registry.discover_tools_from_paths(
                    [str(tools_dir)],
                    patterns=["*_tool.py"],
                    recursive=True,
                    auto_register=True
                )
                self.logger.info(f"Tool discovery summary: {summary}")
                
                # Log registered tools
                tools = self.tool_registry.list_tools()
                self.logger.info(f"Registered {len(tools)} tools")
                for tool in tools:
                    self.logger.info(f"  - {tool['name']}: {tool['description']}")
            else:
                self.logger.warning(f"Tools directory not found: {tools_dir}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize tools: {e}")
            # Non-critical, continue without tools
        
    def initialize_watchdog(self):
        """Initialize the system watchdog with GUI integration using Qt implementation."""
        try:
            # Import compatibility adapter for seamless migration
            from src.utils.watchdog_compat import WatchdogCompatibilityAdapter
            
            # Create Qt-based watchdog via compatibility adapter
            self.watchdog = WatchdogCompatibilityAdapter(
                alert_callback=None,  # Will connect via Qt signals
                metrics_callback=None,  # Will connect via Qt signals
                vram_threshold_percent=self.config.get(
                    'watchdog.vram_threshold_percent', 95.0
                ),
                max_dinoair_processes=self.config.get(
                    'watchdog.max_dinoair_processes', 5
                ),
                check_interval_seconds=self.config.get(
                    'watchdog.check_interval_seconds', 30
                ),
                self_terminate_on_critical=self.config.get(
                    'watchdog.self_terminate_on_critical', False
                )
            )
            
            # Connect Qt signals to MainWindow handlers if available
            if self.main_window and self.watchdog.controller and self.watchdog.controller.signals:
                self.watchdog.controller.signals.alert_triggered.connect(
                    self.main_window.watchdog_alert_handler,
                    Qt.ConnectionType.QueuedConnection
                )
                self.watchdog.controller.signals.metrics_ready.connect(
                    self.main_window.watchdog_metrics_handler,
                    Qt.ConnectionType.QueuedConnection
                )
                
                # Optional: Connect additional signals for enhanced monitoring
                self.watchdog.controller.signals.error_occurred.connect(
                    lambda msg: self.logger.error(f"Watchdog error: {msg}"),
                    Qt.ConnectionType.QueuedConnection
                )
                self.watchdog.controller.signals.monitoring_started.connect(
                    lambda: self.logger.info("Watchdog monitoring started"),
                    Qt.ConnectionType.QueuedConnection
                )
                self.watchdog.controller.signals.monitoring_stopped.connect(
                    lambda: self.logger.info("Watchdog monitoring stopped"),
                    Qt.ConnectionType.QueuedConnection
                )
            
            # Pass max processes config to main window for metrics display
            if self.main_window:
                self.main_window.set_watchdog_config(
                    max_processes=self.config.get(
                        'watchdog.max_dinoair_processes', 5
                    )
                )
            
            # Start monitoring
            self.watchdog.start_monitoring()
            self.logger.info("Qt-based watchdog initialized and monitoring started")
            
            # Register watchdog with dependency container and resource manager
            self.container.register_instance("watchdog", self.watchdog)
            
            self.resource_manager.register_resource(
                "system_watchdog",
                self.watchdog,
                ResourceType.WATCHDOG,
                cleanup_func=self.watchdog.stop_monitoring,
                priority=30
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize watchdog: {e}")
            # Continue without watchdog - not critical for app functionality
    
    def create_main_window(self):
        """Create and show the main window"""
        try:
            self.main_window = MainWindow()
            
            # Set references after creation
            if hasattr(self.main_window, 'set_logger'):
                self.main_window.set_logger(self.logger)
            if hasattr(self.main_window, 'set_database_manager'):
                self.main_window.set_database_manager(self.db_manager)
            if hasattr(self.main_window, 'set_app_instance'):
                self.main_window.set_app_instance(self)
            if hasattr(self.main_window, 'set_tool_registry'):
                self.main_window.set_tool_registry(self.tool_registry)
            
            self.main_window.show()
            
            # Register main window with dependency container and resource manager
            self.container.register_instance("main_window", self.main_window)
            
            self.resource_manager.register_resource(
                "main_window",
                self.main_window,
                ResourceType.GUI_COMPONENT,
                cleanup_func=self.main_window.close,
                priority=15
            )
            
            # Initialize watchdog after main window is created
            self.initialize_watchdog()
            
        except Exception as e:
            self.logger.error(f"Failed to create main window: {e}")
            return False
        return True
        
    def run(self):
        """Run the application"""
        self.logger.info("Starting DinoAir 2.0...")
        
        # Initialize Qt application
        self.initialize_app()
        
        # Initialize databases
        if not self.initialize_database():
            return 1
            
        # Initialize tool registry
        self.initialize_tools()
            
        # Create main window
        if not self.create_main_window():
            return 1
            
        # Transition to running state
        transition_to_state(ApplicationState.RUNNING)
        
        # Start event loop
        self.logger.info("Application started successfully")
        return self.app.exec()
        
    def cleanup(self):
        """Cleanup resources before exit"""
        transition_to_state(ApplicationState.SHUTTING_DOWN)
        self.logger.info("Shutting down DinoAir 2.0...")
        
        try:
            # Use resource manager for proper shutdown sequencing
            shutdown_success = self.resource_manager.shutdown_all_resources(timeout=30.0)
            
            if not shutdown_success:
                self.logger.warning("Some resources did not shutdown cleanly")
                
            # Dispose all dependencies
            self.container.dispose_all()
                
            # Final database cleanup
            if self.db_manager:
                try:
                    self.db_manager.clean_memory_database()
                except Exception as e:
                    self.logger.error(f"Error during final database cleanup: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")
            transition_to_state(ApplicationState.ERROR, {"error": str(e)})
            
        transition_to_state(ApplicationState.SHUTDOWN)
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
