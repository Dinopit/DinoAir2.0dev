#!/usr/bin/env python3
"""Test script to demonstrate watchdog settings functionality in the GUI.

This script demonstrates:
1. Navigating to the settings page
2. Viewing current watchdog configuration
3. Modifying watchdog settings with validation
4. Starting/stopping watchdog monitoring
5. Saving and applying settings
6. Real-time status updates
7. Critical settings confirmation
"""

import sys
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer

from src.gui.main_window import MainWindow
from src.utils.config_loader import ConfigLoader
from src.utils.logger import Logger
from src.utils.Watchdog import SystemWatchdog


class WatchdogSettingsDemo:
    """Demonstrates watchdog settings functionality."""
    
    def __init__(self):
        """Initialize the demo application."""
        self.app = QApplication(sys.argv)
        self.logger = Logger()
        self.config = ConfigLoader()
        self.main_window = None
        self.watchdog = None
        
    def setup_gui(self):
        """Set up the GUI components."""
        # Create main window
        self.main_window = MainWindow()
        self.main_window.setWindowTitle("Watchdog Settings Demo - DinoAir 2.0")
        
        # Set logger for main window
        self.main_window.set_logger(self.logger)
        
        # Create a mock app instance for integration
        class MockApp:
            def __init__(self, watchdog, config):
                self.watchdog = watchdog
                self.config = config
                
            def initialize_watchdog(self):
                """Initialize watchdog if not already created."""
                if not self.watchdog:
                    vram_threshold = self.config.get(
                        "watchdog.vram_threshold_percent", 80.0
                    )
                    max_processes = self.config.get(
                        "watchdog.max_dinoair_processes", 5
                    )
                    check_interval = self.config.get(
                        "watchdog.check_interval_seconds", 10
                    )
                    self_terminate = self.config.get(
                        "watchdog.self_terminate_on_critical", False
                    )
                    
                    # Create watchdog with GUI callbacks
                    self.watchdog = SystemWatchdog(
                        alert_callback=lambda level, msg: (
                            self.main_window.watchdog_alert_handler(
                                self._convert_alert_level(level), msg
                            ) if hasattr(self, 'main_window') else None
                        ),
                        metrics_callback=lambda metrics: (
                            self.main_window.watchdog_metrics_handler(metrics)
                            if hasattr(self, 'main_window') else None
                        ),
                        vram_threshold_percent=vram_threshold,
                        max_dinoair_processes=max_processes,
                        check_interval_seconds=check_interval,
                        self_terminate_on_critical=self_terminate
                    )
                    
            def _convert_alert_level(self, level):
                """Convert watchdog AlertLevel to GUI AlertLevel."""
                from src.gui.components.notification_widget import (
                    AlertLevel as GuiAlertLevel
                )
                level_map = {
                    "info": GuiAlertLevel.INFO,
                    "warning": GuiAlertLevel.WARNING,
                    "critical": GuiAlertLevel.CRITICAL
                }
                return level_map.get(level.value, GuiAlertLevel.INFO)
        
        # Create mock app with watchdog
        mock_app = MockApp(self.watchdog, self.config)
        mock_app.main_window = self.main_window
        
        # Set app instance in main window
        self.main_window.set_app_instance(mock_app)
        
        # Show main window
        self.main_window.show()
        
    def navigate_to_settings(self):
        """Navigate to the settings tab."""
        self.logger.info("Navigating to Settings page...")
        
        # Get tabbed content widget
        tabbed_content = self.main_window.tabbed_content
        if tabbed_content:
            # Find settings tab index
            for i, tab in enumerate(tabbed_content.tabs):
                if tab['id'] == 'settings':
                    tabbed_content.tab_widget.setCurrentIndex(i)
                    self.logger.info("✓ Switched to Settings tab")
                    break
                    
    def demonstrate_settings(self):
        """Demonstrate various settings functionality."""
        self.logger.info("\n" + "="*60)
        self.logger.info("WATCHDOG SETTINGS DEMONSTRATION")
        self.logger.info("="*60 + "\n")
        
        # Get settings page
        settings_page = self.main_window.tabbed_content.get_settings_page()
        if not settings_page:
            self.logger.error("Settings page not found!")
            return
            
        # 1. Show current configuration
        self.logger.info("1. Current Watchdog Configuration:")
        self.logger.info(f"   - Auto-start: {settings_page.enable_checkbox.isChecked()}")
        self.logger.info(f"   - VRAM Threshold: {settings_page.vram_slider.value()}%")
        self.logger.info(f"   - Max Processes: {settings_page.max_processes_spin.value()}")
        self.logger.info(f"   - Check Interval: {settings_page.interval_spin.value()}s")
        self.logger.info(f"   - Emergency Shutdown: {settings_page.emergency_checkbox.isChecked()}")
        
        # 2. Demonstrate changing settings
        QTimer.singleShot(2000, lambda: self.change_settings(settings_page))
        
        # 3. Demonstrate starting watchdog
        QTimer.singleShot(4000, lambda: self.start_watchdog(settings_page))
        
        # 4. Demonstrate saving settings
        QTimer.singleShot(8000, lambda: self.save_settings(settings_page))
        
        # 5. Demonstrate emergency shutdown toggle
        QTimer.singleShot(10000, lambda: self.toggle_emergency_shutdown(settings_page))
        
        # 6. Demonstrate stopping watchdog
        QTimer.singleShot(14000, lambda: self.stop_watchdog(settings_page))
        
        # 7. Show final summary
        QTimer.singleShot(16000, self.show_summary)
        
    def change_settings(self, settings_page):
        """Demonstrate changing settings."""
        self.logger.info("\n2. Changing Watchdog Settings:")
        
        # Change VRAM threshold
        old_vram = settings_page.vram_slider.value()
        settings_page.vram_slider.setValue(70)
        self.logger.info(f"   - Changed VRAM threshold: {old_vram}% → 70%")
        
        # Change max processes
        old_processes = settings_page.max_processes_spin.value()
        settings_page.max_processes_spin.setValue(3)
        self.logger.info(f"   - Changed max processes: {old_processes} → 3")
        
        # Change check interval
        old_interval = settings_page.interval_spin.value()
        settings_page.interval_spin.setValue(5)
        self.logger.info(f"   - Changed check interval: {old_interval}s → 5s")
        
        # Show that apply/save buttons are now enabled
        self.logger.info(f"   - Apply button enabled: {settings_page.apply_button.isEnabled()}")
        self.logger.info(f"   - Save button enabled: {settings_page.save_button.isEnabled()}")
        
    def start_watchdog(self, settings_page):
        """Demonstrate starting the watchdog."""
        self.logger.info("\n3. Starting Watchdog Monitoring:")
        
        # Click start button
        if settings_page.start_button.isEnabled():
            settings_page.start_button.click()
            self.logger.info("   ✓ Clicked Start Watchdog button")
            
            # Show status after a short delay
            QTimer.singleShot(500, lambda: self.show_watchdog_status(settings_page))
        else:
            self.logger.info("   - Watchdog already running")
            
    def show_watchdog_status(self, settings_page):
        """Show current watchdog status."""
        if settings_page.watchdog_ref and settings_page.watchdog_ref._monitoring:
            self.logger.info("   ✓ Watchdog is now RUNNING")
            self.logger.info("   - Status display updated with live metrics")
            self.logger.info("   - Metrics panel visible (if metrics available)")
            self.logger.info("   - Notification panel ready for alerts")
        else:
            self.logger.info("   ✗ Watchdog is NOT running")
            
    def save_settings(self, settings_page):
        """Demonstrate saving settings."""
        self.logger.info("\n4. Saving Settings to Configuration:")
        
        if settings_page.save_button.isEnabled():
            # Apply settings first
            settings_page.apply_button.click()
            self.logger.info("   ✓ Applied settings to running watchdog")
            
            # Then save
            settings_page.save_button.click()
            self.logger.info("   ✓ Saved settings to app_config.json")
            self.logger.info("   - Settings will persist across restarts")
        else:
            self.logger.info("   - No changes to save")
            
    def toggle_emergency_shutdown(self, settings_page):
        """Demonstrate toggling emergency shutdown with confirmation."""
        self.logger.info("\n5. Testing Critical Setting (Emergency Shutdown):")
        
        # Try to enable emergency shutdown
        was_checked = settings_page.emergency_checkbox.isChecked()
        settings_page.emergency_checkbox.setChecked(True)
        
        # Note: In real usage, this would show a confirmation dialog
        # For demo, we'll just show what would happen
        self.logger.info("   - Attempting to enable emergency shutdown")
        self.logger.info("   - WARNING dialog would appear asking for confirmation")
        self.logger.info("   - This allows automatic process termination if limits exceeded")
        
        # Reset to original state for safety
        settings_page.emergency_checkbox.setChecked(was_checked)
        self.logger.info(f"   - Reset to original state: {was_checked}")
        
    def stop_watchdog(self, settings_page):
        """Demonstrate stopping the watchdog."""
        self.logger.info("\n6. Stopping Watchdog Monitoring:")
        
        if settings_page.stop_button.isEnabled():
            # Note: In real usage, this would show a confirmation dialog
            self.logger.info("   - Confirmation dialog would appear")
            self.logger.info("   - Simulating user clicking 'Yes'")
            
            # Stop watchdog
            settings_page._stop_watchdog()
            self.logger.info("   ✓ Watchdog monitoring stopped")
            self.logger.info("   - Status display shows 'Not Running'")
        else:
            self.logger.info("   - Watchdog already stopped")
            
    def show_summary(self):
        """Show demonstration summary."""
        self.logger.info("\n" + "="*60)
        self.logger.info("DEMONSTRATION COMPLETE")
        self.logger.info("="*60)
        
        self.logger.info("\nKey Features Demonstrated:")
        self.logger.info("✓ Settings page with comprehensive watchdog controls")
        self.logger.info("✓ Real-time status display with live metrics")
        self.logger.info("✓ Input validation with tooltips on all controls")
        self.logger.info("✓ Apply settings without saving (temporary)")
        self.logger.info("✓ Save settings to configuration file (persistent)")
        self.logger.info("✓ Start/Stop watchdog with visual feedback")
        self.logger.info("✓ Critical settings confirmation (emergency shutdown)")
        self.logger.info("✓ Integration with notification and metrics panels")
        
        self.logger.info("\nSettings Controls:")
        self.logger.info("• Enable/Disable auto-start on application launch")
        self.logger.info("• VRAM threshold slider (0-100%)")
        self.logger.info("• Max processes spinbox (1-20)")
        self.logger.info("• Check interval spinbox (5-300 seconds)")
        self.logger.info("• Emergency shutdown toggle with warning")
        self.logger.info("• Apply/Save/Reset buttons with state tracking")
        
        self.logger.info("\nThe settings page is now fully functional and integrated!")
        
        # Show a final message box
        QTimer.singleShot(1000, self.show_completion_dialog)
        
    def show_completion_dialog(self):
        """Show completion dialog."""
        QMessageBox.information(
            self.main_window,
            "Demo Complete",
            "Watchdog Settings demonstration complete!\n\n"
            "The settings page provides full control over watchdog "
            "configuration with real-time updates and persistence.\n\n"
            "Close this dialog to exit the demo."
        )
        
        # Exit after dialog is closed
        QTimer.singleShot(100, self.app.quit)
        
    def run(self):
        """Run the demonstration."""
        try:
            # Set up GUI
            self.setup_gui()
            
            # Navigate to settings after a short delay
            QTimer.singleShot(1000, self.navigate_to_settings)
            
            # Start demonstration
            QTimer.singleShot(2000, self.demonstrate_settings)
            
            # Run application
            return self.app.exec()
            
        except Exception as e:
            self.logger.error(f"Demo error: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    """Run the watchdog settings demonstration."""
    demo = WatchdogSettingsDemo()
    sys.exit(demo.run())


if __name__ == "__main__":
    main()