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
        
    def initialize_app(self):
        """Initialize the Qt application"""
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(self.config.get("app.name", "DinoAir 2.0"))
        self.app.setApplicationVersion(self.config.get("app.version", "2.0.0"))
        self.app.setOrganizationName("DinoAir Development")
        
        # Set application style
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
    def initialize_database(self, user_name="default_user"):
        """Initialize user databases"""
        try:
            def gui_feedback(message):
                self.logger.info(message)
                # In future, this could update a splash screen or status bar
                
            self.db_manager = initialize_user_databases(user_name, gui_feedback)
            self.logger.info("Database initialization completed")
            
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
        
    def create_main_window(self):
        """Create and show the main window"""
        try:
            self.main_window = MainWindow()
            
            # Set references after creation
            if hasattr(self.main_window, 'set_logger'):
                self.main_window.set_logger(self.logger)
            if hasattr(self.main_window, 'set_database_manager'):
                self.main_window.set_database_manager(self.db_manager)
            
            self.main_window.show()
            
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
            
        # Create main window
        if not self.create_main_window():
            return 1
            
        # Start event loop
        self.logger.info("Application started successfully")
        return self.app.exec()
        
    def cleanup(self):
        """Cleanup resources before exit"""
        self.logger.info("Shutting down DinoAir 2.0...")
        
        if self.db_manager:
            try:
                self.db_manager.clean_memory_database()
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
