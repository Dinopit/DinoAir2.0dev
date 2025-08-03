"""
Test script for Watchdog GUI notifications
Demonstrates that alerts appear in the GUI notification panel
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QPushButton, QVBoxLayout, QWidget
)
from PySide6.QtCore import QTimer  # noqa: E402

from src.gui.components.notification_widget import AlertLevel  # noqa: E402
from src.gui import MainWindow  # noqa: E402


class TestNotificationWindow(MainWindow):
    """Extended MainWindow with test controls"""
    
    def __init__(self):
        super().__init__()
        self.setup_test_controls()
        
        # Show notification panel by default for testing
        self.notification_widget.show()
        
    def setup_test_controls(self):
        """Add test buttons to trigger different alert levels"""
        # Create test control widget
        test_widget = QWidget()
        test_layout = QVBoxLayout(test_widget)
        
        # Create test buttons
        info_btn = QPushButton("Trigger INFO Alert")
        info_btn.clicked.connect(self.trigger_info_alert)
        
        warning_btn = QPushButton("Trigger WARNING Alert")
        warning_btn.clicked.connect(self.trigger_warning_alert)
        
        critical_btn = QPushButton("Trigger CRITICAL Alert")
        critical_btn.clicked.connect(self.trigger_critical_alert)
        
        simulate_btn = QPushButton("Simulate Watchdog Monitoring")
        simulate_btn.clicked.connect(self.simulate_watchdog)
        
        # Add buttons to layout
        test_layout.addWidget(info_btn)
        test_layout.addWidget(warning_btn)
        test_layout.addWidget(critical_btn)
        test_layout.addWidget(simulate_btn)
        test_layout.addStretch()
        
        # Add test widget to main layout
        self.content_layout.addWidget(test_widget)
        
    def trigger_info_alert(self):
        """Trigger an INFO level alert"""
        self.watchdog_alert_handler(
            AlertLevel.INFO,
            "System resources are within normal parameters"
        )
        
    def trigger_warning_alert(self):
        """Trigger a WARNING level alert"""
        self.watchdog_alert_handler(
            AlertLevel.WARNING,
            "High VRAM usage detected: 78.5% (6280MB / 8000MB)"
        )
        
    def trigger_critical_alert(self):
        """Trigger a CRITICAL level alert"""
        self.watchdog_alert_handler(
            AlertLevel.CRITICAL,
            "Too many DinoAir processes: 6 (limit: 3). "
            "Possible runaway processes!"
        )
        
    def simulate_watchdog(self):
        """Simulate a sequence of watchdog alerts"""
        # Schedule alerts to appear over time
        QTimer.singleShot(1000, lambda: self.watchdog_alert_handler(
            AlertLevel.INFO,
            "Watchdog monitoring started - System check initiated"
        ))
        
        QTimer.singleShot(3000, lambda: self.watchdog_alert_handler(
            AlertLevel.INFO,
            "CPU usage: 45.2% | RAM: 62.3% | VRAM: 55.0%"
        ))
        
        QTimer.singleShot(5000, lambda: self.watchdog_alert_handler(
            AlertLevel.WARNING,
            "VRAM usage increasing: 88.5% (7080MB / 8000MB)"
        ))
        
        QTimer.singleShot(7000, lambda: self.watchdog_alert_handler(
            AlertLevel.WARNING,
            "High CPU usage detected: 85.7%"
        ))
        
        QTimer.singleShot(9000, lambda: self.watchdog_alert_handler(
            AlertLevel.CRITICAL,
            "Critical RAM usage: 96.2% - System may become unstable"
        ))
        
        QTimer.singleShot(11000, lambda: self.watchdog_alert_handler(
            AlertLevel.INFO,
            "System resources stabilized - All metrics within normal range"
        ))


def main():
    """Run the test application"""
    print("=== DinoAir Watchdog Notification Test ===")
    print("This test demonstrates the GUI notification system "
          "for Watchdog alerts.")
    print("Alerts will appear in the notification panel at the "
          "bottom of the window.")
    print()
    print("Test Controls:")
    print("- Click buttons to trigger individual alerts")
    print("- Click 'Simulate Watchdog Monitoring' for an automated sequence")
    print("- INFO alerts auto-dismiss after 5 seconds")
    print("- WARNING and CRITICAL alerts stay until manually dismissed")
    print()
    
    app = QApplication(sys.argv)
    app.setApplicationName("DinoAir Notification Test")
    
    # Create and show test window
    window = TestNotificationWindow()
    window.setWindowTitle("DinoAir 2.0 - Watchdog Notification Test")
    window.resize(1400, 900)
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()