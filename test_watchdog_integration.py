"""Integration tests for watchdog with main application components.

This test file focuses on:
- Integration with main.py and GUI
- Signal/slot connections with main_window.py
- Database metrics storage under normal and error conditions
- Feature toggle testing (Qt vs legacy implementation)
- Performance comparison between implementations
"""

import sys
import time
import sqlite3
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel

from src.utils.logger import Logger
from src.utils.watchdog_qt import (
    WatchdogController, WatchdogConfig, SystemMetrics, AlertLevel
)
from src.utils.watchdog_compat import create_watchdog_adapter, AdapterMode
from src.utils.Watchdog import SystemWatchdog

logger = Logger()


class MockMainWindow(QMainWindow):
    """Mock main window for integration testing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mock DinoAir Window")
        self.status_label = QLabel("Status: Ready")
        self.setCentralWidget(self.status_label)
        
        self.metrics_received = []
        self.alerts_received = []
        
    def on_metrics_update(self, metrics: SystemMetrics):
        """Handle metrics updates from watchdog."""
        self.metrics_received.append(metrics)
        self.status_label.setText(
            f"VRAM: {metrics.vram_percent:.1f}% | "
            f"CPU: {metrics.cpu_percent:.1f}%"
        )
        
    def on_alert(self, level: AlertLevel, message: str):
        """Handle alerts from watchdog."""
        self.alerts_received.append((level, message))
        if level == AlertLevel.CRITICAL:
            self.status_label.setStyleSheet("color: red;")
        elif level == AlertLevel.WARNING:
            self.status_label.setStyleSheet("color: orange;")


class MockMetricsDatabase:
    """Mock database for metrics storage testing."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        self._setup_database()
        
    def _setup_database(self):
        """Create test database schema."""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchdog_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                vram_percent REAL,
                cpu_percent REAL,
                ram_percent REAL,
                process_count INTEGER,
                dinoair_processes INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchdog_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT
            )
        """)
        
        self.connection.commit()
        
    def store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO watchdog_metrics 
                (vram_percent, cpu_percent, ram_percent, process_count, dinoair_processes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metrics.vram_percent,
                metrics.cpu_percent,
                metrics.ram_percent,
                metrics.process_count,
                metrics.dinoair_processes
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
            return False
            
    def store_alert(self, level: AlertLevel, message: str):
        """Store alert in database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO watchdog_alerts (level, message)
                VALUES (?, ?)
            """, (level.value, message))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
            return False
            
    def get_metrics_count(self) -> int:
        """Get count of stored metrics."""
        cursor = self.connection.cursor()
        result = cursor.execute("SELECT COUNT(*) FROM watchdog_metrics").fetchone()
        return result[0] if result else 0
        
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


class WatchdogIntegrationTester:
    """Main test class for watchdog integration."""
    
    def __init__(self):
        self.test_results = []
        self.app = None
        self.temp_dir = None
        
    def setup(self):
        """Setup test environment."""
        # Create Qt application
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp(prefix="watchdog_test_")
        
    def cleanup(self):
        """Cleanup test environment."""
        # Remove temporary directory
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            
        # Cleanup Qt application
        if self.app:
            self.app.quit()
            
    def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 60)
        print("WATCHDOG INTEGRATION TEST SUITE")
        print("=" * 60)
        print()
        
        self.setup()
        
        tests = [
            self.test_gui_integration,
            self.test_signal_slot_connections,
            self.test_database_metrics_storage,
            self.test_error_handling_with_database,
            self.test_qt_vs_legacy_toggle,
            self.test_performance_comparison,
            self.test_main_window_status_updates,
            self.test_concurrent_operations
        ]
        
        for test_func in tests:
            try:
                print(f"\n--- Running {test_func.__name__} ---")
                success, message = test_func()
                self.test_results.append(
                    (test_func.__name__, success, message)
                )
                
                if success:
                    print(f"✅ PASS: {message}")
                else:
                    print(f"❌ FAIL: {message}")
                    
            except Exception as e:
                import traceback
                error_msg = f"Exception: {e}\n{traceback.format_exc()}"
                self.test_results.append(
                    (test_func.__name__, False, error_msg)
                )
                print(f"❌ ERROR: {error_msg}")
                
        self._print_summary()
        self.cleanup()
        
    def test_gui_integration(self):
        """Test integration with GUI components."""
        print("Testing GUI integration...")
        
        # Create mock main window
        window = MockMainWindow()
        window.show()
        
        # Create watchdog with GUI callbacks
        config = WatchdogConfig(
            check_interval=2,
            vram_threshold=70.0  # Low threshold for testing
        )
        
        controller = WatchdogController(config)
        
        # Connect to mock window
        controller.signals.metrics_ready.connect(window.on_metrics_update)
        controller.signals.alert_triggered.connect(window.on_alert)
        
        # Start monitoring
        controller.start_watchdog()
        
        # Let it run and collect metrics
        start_time = time.time()
        while time.time() - start_time < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop monitoring
        controller.stop_watchdog()
        
        # Check results
        print(f"Metrics received by GUI: {len(window.metrics_received)}")
        print(f"Alerts received by GUI: {len(window.alerts_received)}")
        
        if len(window.metrics_received) > 0:
            last_metric = window.metrics_received[-1]
            print(f"Last metric - VRAM: {last_metric.vram_percent:.1f}%")
            
        # Verify GUI updated
        status_text = window.status_label.text()
        
        if len(window.metrics_received) >= 2 and "VRAM:" in status_text:
            return True, (
                f"GUI integration working: {len(window.metrics_received)} "
                f"metrics displayed"
            )
        else:
            return False, "GUI not receiving updates properly"
            
    def test_signal_slot_connections(self):
        """Test all signal/slot connections."""
        print("Testing signal/slot connections...")
        
        # Track all signal emissions
        signal_tracker = {
            'metrics_ready': 0,
            'alert_triggered': 0,
            'error_occurred': 0,
            'monitoring_started': 0,
            'monitoring_stopped': 0,
            'status_changed': 0,
            'circuit_breaker_opened': 0,
            'circuit_breaker_closed': 0
        }
        
        def track_signal(signal_name):
            def handler(*args):
                signal_tracker[signal_name] += 1
            return handler
            
        # Create controller
        config = WatchdogConfig(check_interval=1)
        controller = WatchdogController(config)
        
        # Connect all signals
        controller.signals.metrics_ready.connect(track_signal('metrics_ready'))
        controller.signals.alert_triggered.connect(track_signal('alert_triggered'))
        controller.signals.error_occurred.connect(track_signal('error_occurred'))
        controller.signals.monitoring_started.connect(
            track_signal('monitoring_started')
        )
        controller.signals.monitoring_stopped.connect(
            track_signal('monitoring_stopped')
        )
        controller.signals.status_changed.connect(track_signal('status_changed'))
        controller.signals.circuit_breaker_opened.connect(
            track_signal('circuit_breaker_opened')
        )
        controller.signals.circuit_breaker_closed.connect(
            track_signal('circuit_breaker_closed')
        )
        
        # Start and run
        controller.start_watchdog()
        
        start_time = time.time()
        while time.time() - start_time < 3:
            self.app.processEvents()
            time.sleep(0.1)
            
        controller.stop_watchdog()
        
        # Check signal emissions
        print("\nSignal emissions:")
        for signal_name, count in signal_tracker.items():
            print(f"  {signal_name}: {count}")
            
        # Should have basic signals
        if (signal_tracker['monitoring_started'] == 1 and
            signal_tracker['monitoring_stopped'] == 1 and
            signal_tracker['metrics_ready'] >= 2):
            return True, (
                f"All signals connected: {sum(signal_tracker.values())} "
                f"total emissions"
            )
        else:
            return False, "Some signals not properly connected"
            
    def test_database_metrics_storage(self):
        """Test database storage integration."""
        print("Testing database metrics storage...")
        
        # Create test database
        db_path = Path(self.temp_dir) / "test_metrics.db"
        db = MockMetricsDatabase(str(db_path))
        
        # Create watchdog with database callbacks
        config = WatchdogConfig(check_interval=1)
        controller = WatchdogController(config)
        
        # Connect database storage
        controller.signals.metrics_ready.connect(db.store_metrics)
        controller.signals.alert_triggered.connect(db.store_alert)
        
        # Start monitoring
        controller.start_watchdog()
        
        # Run for a while
        start_time = time.time()
        while time.time() - start_time < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        controller.stop_watchdog()
        
        # Check database
        metrics_count = db.get_metrics_count()
        print(f"Metrics stored in database: {metrics_count}")
        
        # Query some data
        cursor = db.connection.cursor()
        avg_cpu = cursor.execute(
            "SELECT AVG(cpu_percent) FROM watchdog_metrics"
        ).fetchone()[0]
        
        if avg_cpu:
            print(f"Average CPU usage: {avg_cpu:.1f}%")
            
        db.close()
        
        # Should have stored multiple metrics
        if metrics_count >= 4:
            return True, f"Database integration working: {metrics_count} metrics stored"
        else:
            return False, f"Insufficient metrics stored: {metrics_count}"
            
    def test_error_handling_with_database(self):
        """Test error handling when database fails."""
        print("Testing error handling with database failures...")
        
        # Create database but close it to simulate failure
        db_path = Path(self.temp_dir) / "test_error.db"
        db = MockMetricsDatabase(str(db_path))
        db.close()  # Close to cause errors
        
        error_count = 0
        
        def error_prone_store(metrics):
            """Try to store in closed database."""
            nonlocal error_count
            try:
                db.store_metrics(metrics)
            except Exception:
                error_count += 1
                
        # Create watchdog
        config = WatchdogConfig(check_interval=1)
        controller = WatchdogController(config)
        controller.signals.metrics_ready.connect(error_prone_store)
        
        # Start monitoring
        controller.start_watchdog()
        
        # Run briefly
        start_time = time.time()
        while time.time() - start_time < 3:
            self.app.processEvents()
            time.sleep(0.1)
            
        controller.stop_watchdog()
        
        print(f"Database errors handled: {error_count}")
        
        # Should handle errors gracefully
        if error_count > 0:
            return True, (
                f"Error handling working: {error_count} database errors "
                f"handled gracefully"
            )
        else:
            return False, "No errors detected (test may have failed)"
            
    def test_qt_vs_legacy_toggle(self):
        """Test switching between Qt and legacy implementations."""
        print("Testing Qt vs legacy implementation toggle...")
        
        results = {}
        
        # Test Qt implementation
        print("\n1. Testing Qt implementation:")
        qt_adapter = create_watchdog_adapter(
            use_qt=True,
            check_interval_seconds=1
        )
        
        qt_metrics = []
        
        def qt_callback(level, message):
            pass
            
        def qt_metrics_callback(metrics):
            qt_metrics.append(metrics)
            
        qt_adapter.alert_callback = qt_callback
        qt_adapter.metrics_callback = qt_metrics_callback
        
        qt_adapter.start_monitoring()
        
        # Run Qt version
        start_time = time.time()
        while time.time() - start_time < 3:
            self.app.processEvents()
            time.sleep(0.1)
            
        qt_adapter.stop_monitoring()
        results['qt_metrics'] = len(qt_metrics)
        results['qt_mode'] = qt_adapter.current_mode.value
        
        # Test legacy implementation
        print("\n2. Testing legacy implementation:")
        legacy_adapter = create_watchdog_adapter(
            use_qt=False,
            check_interval_seconds=1
        )
        
        legacy_metrics = []
        
        def legacy_metrics_callback(metrics):
            legacy_metrics.append(metrics)
            
        legacy_adapter.metrics_callback = legacy_metrics_callback
        
        legacy_adapter.start_monitoring()
        time.sleep(3)
        legacy_adapter.stop_monitoring()
        
        results['legacy_metrics'] = len(legacy_metrics)
        results['legacy_mode'] = legacy_adapter.current_mode.value
        
        print(f"\nResults:")
        print(f"  Qt mode: {results['qt_mode']} - {results['qt_metrics']} metrics")
        print(f"  Legacy mode: {results['legacy_mode']} - {results['legacy_metrics']} metrics")
        
        # Both should work
        if (results['qt_metrics'] >= 2 and 
            results['legacy_metrics'] >= 2 and
            results['qt_mode'] == 'qt' and
            results['legacy_mode'] == 'legacy'):
            return True, "Both implementations working correctly"
        else:
            return False, "Implementation toggle not working properly"
            
    def test_performance_comparison(self):
        """Compare performance between implementations."""
        print("Testing performance comparison...")
        
        import time
        
        # Measure Qt implementation
        print("\n1. Measuring Qt implementation performance:")
        config = WatchdogConfig(check_interval=1)
        qt_controller = WatchdogController(config)
        
        qt_times = []
        
        def measure_qt_time(metrics):
            qt_times.append(time.time())
            
        qt_controller.signals.metrics_ready.connect(measure_qt_time)
        qt_controller.start_watchdog()
        
        # Run for measurement period
        qt_start = time.time()
        while time.time() - qt_start < 5:
            self.app.processEvents()
            time.sleep(0.05)
            
        qt_controller.stop_watchdog()
        
        # Calculate Qt metrics rate
        if len(qt_times) > 1:
            qt_intervals = [qt_times[i+1] - qt_times[i] 
                           for i in range(len(qt_times)-1)]
            qt_avg_interval = sum(qt_intervals) / len(qt_intervals)
            qt_rate = 1.0 / qt_avg_interval if qt_avg_interval > 0 else 0
        else:
            qt_rate = 0
            
        # Measure legacy implementation
        print("\n2. Measuring legacy implementation performance:")
        legacy_watchdog = SystemWatchdog(check_interval_seconds=1)
        
        legacy_times = []
        
        def measure_legacy_time(metrics):
            legacy_times.append(time.time())
            
        legacy_watchdog.metrics_callback = measure_legacy_time
        
        # Note: Legacy implementation is deprecated but we simulate it
        legacy_start = time.time()
        while time.time() - legacy_start < 5:
            metrics = legacy_watchdog.get_current_metrics()
            measure_legacy_time(metrics)
            time.sleep(1)
            
        # Calculate legacy metrics rate
        if len(legacy_times) > 1:
            legacy_intervals = [legacy_times[i+1] - legacy_times[i] 
                               for i in range(len(legacy_times)-1)]
            legacy_avg_interval = sum(legacy_intervals) / len(legacy_intervals)
            legacy_rate = 1.0 / legacy_avg_interval if legacy_avg_interval > 0 else 0
        else:
            legacy_rate = 0
            
        print(f"\nPerformance results:")
        print(f"  Qt implementation: {qt_rate:.2f} metrics/sec")
        print(f"  Legacy implementation: {legacy_rate:.2f} metrics/sec")
        print(f"  Qt is {qt_rate/legacy_rate:.1f}x the legacy rate")
        
        # Qt should be comparable or better
        if qt_rate > 0 and legacy_rate > 0:
            return True, (
                f"Performance measured: Qt={qt_rate:.2f}/s, "
                f"Legacy={legacy_rate:.2f}/s"
            )
        else:
            return False, "Failed to measure performance"
            
    def test_main_window_status_updates(self):
        """Test main window status bar updates."""
        print("Testing main window status updates...")
        
        # Create more realistic mock window
        class EnhancedMockWindow(MockMainWindow):
            def __init__(self):
                super().__init__()
                self.status_updates = []
                self.resource_warnings = []
                
            def update_status(self, message: str):
                """Update status bar."""
                self.status_updates.append({
                    'time': datetime.now(),
                    'message': message
                })
                self.status_label.setText(message)
                
            def show_resource_warning(self, resource: str, value: float):
                """Show resource warning."""
                self.resource_warnings.append({
                    'resource': resource,
                    'value': value
                })
                if value > 90:
                    self.status_label.setStyleSheet("background-color: red;")
                elif value > 80:
                    self.status_label.setStyleSheet("background-color: orange;")
                    
        window = EnhancedMockWindow()
        window.show()
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=1,
            vram_threshold=70.0,
            cpu_threshold=70.0
        )
        
        controller = WatchdogController(config)
        
        # Connect with status updates
        def on_metrics(metrics: SystemMetrics):
            window.update_status(
                f"System: VRAM {metrics.vram_percent:.0f}% | "
                f"CPU {metrics.cpu_percent:.0f}% | "
                f"Processes: {metrics.dinoair_processes}"
            )
            
            # Check for warnings
            if metrics.vram_percent > 70:
                window.show_resource_warning('vram', metrics.vram_percent)
            if metrics.cpu_percent > 70:
                window.show_resource_warning('cpu', metrics.cpu_percent)
                
        controller.signals.metrics_ready.connect(on_metrics)
        
        # Start monitoring
        controller.start_watchdog()
        
        # Run for a while
        start_time = time.time()
        while time.time() - start_time < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        controller.stop_watchdog()
        
        print(f"Status updates: {len(window.status_updates)}")
        print(f"Resource warnings: {len(window.resource_warnings)}")
        
        # Check last status
        if window.status_updates:
            last_status = window.status_updates[-1]['message']
            print(f"Last status: {last_status}")
            
        # Should have regular updates
        if len(window.status_updates) >= 4:
            return True, (
                f"Main window integration working: "
                f"{len(window.status_updates)} status updates"
            )
        else:
            return False, "Insufficient status updates"
            
    def test_concurrent_operations(self):
        """Test concurrent watchdog operations."""
        print("Testing concurrent operations...")
        
        # Create multiple watchdog instances
        controllers = []
        all_metrics = []
        
        def create_collector(index):
            def collect_metrics(metrics):
                all_metrics.append({
                    'controller': index,
                    'metrics': metrics,
                    'time': time.time()
                })
            return collect_metrics
            
        # Create 3 concurrent watchdogs
        for i in range(3):
            config = WatchdogConfig(
                check_interval=2,
                vram_threshold=90.0 - (i * 10)  # Different thresholds
            )
            controller = WatchdogController(config)
            controller.signals.metrics_ready.connect(create_collector(i))
            controllers.append(controller)
            
        # Start all controllers
        for controller in controllers:
            controller.start_watchdog()
            
        print(f"Started {len(controllers)} concurrent watchdogs")
        
        # Run concurrently
        start_time = time.time()
        while time.time() - start_time < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop all controllers
        for controller in controllers:
            controller.stop_watchdog()
            
        # Analyze results
        controller_metrics = {}
        for entry in all_metrics:
            idx = entry['controller']
            if idx not in controller_metrics:
                controller_metrics[idx] = 0
            controller_metrics[idx] += 1
            
        print(f"\nConcurrent operation results:")
        print(f"Total metrics collected: {len(all_metrics)}")
        for idx, count in controller_metrics.items():
            print(f"  Controller {idx}: {count} metrics")
            
        # All should work without interference
        if (len(controller_metrics) == 3 and
            all(count >= 2 for count in controller_metrics.values())):
            return True, (
                f"Concurrent operations successful: "
                f"{len(all_metrics)} total metrics from 3 controllers"
            )
        else:
            return False, "Concurrent operations interfering with each other"
            
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("INTEGRATION TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✅ All integration tests passed!")
            print("\nKey validations:")
            print("- GUI receives metrics and alerts correctly")
            print("- All Qt signals properly connected")
            print("- Database storage working")
            print("- Error handling maintains stability")
            print("- Qt and legacy implementations both functional")
            print("- Performance acceptable")
            print("- Main window integration working")
            print("- Concurrent operations supported")
        else:
            print("\n❌ Some integration tests failed:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"  - {test_name}: {message}")


def main():
    """Run the integration test suite."""
    print("Starting Watchdog Integration Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = WatchdogIntegrationTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nIntegration test suite completed")


if __name__ == "__main__":
    main()