"""Test suite for watchdog stability and Qt threading compatibility.

This test file focuses on:
- Qt threading compatibility (no QBasicTimer errors)
- Long-running stability test (5+ minutes without crashes)
- Process detection accuracy
- Circuit breaker functionality under load
- Graceful shutdown and restart cycles
- Configuration change handling without restart
"""

import sys
import time
import threading
import multiprocessing
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import queue

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from PySide6.QtCore import QObject, QThread, QCoreApplication, QTimer, Signal
from PySide6.QtWidgets import QApplication

from src.utils.logger import Logger
from src.utils.watchdog_qt import (
    WatchdogController, WatchdogConfig, WatchdogSignals,
    SystemMetrics, AlertLevel, CircuitBreaker, CircuitBreakerOpen
)
from src.utils.watchdog_compat import create_watchdog_adapter, FallbackConfig
from src.utils.Watchdog import SystemWatchdog

logger = Logger()


class TestMetricsCollector(QObject):
    """Collects metrics and alerts during tests."""
    
    metrics_collected = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.metrics_history = []
        self.alerts_history = []
        self.errors_history = []
        self.status_changes = []
        self.circuit_breaker_events = []
        
    def on_metrics_ready(self, metrics: SystemMetrics):
        """Handle metrics updates."""
        self.metrics_history.append({
            'timestamp': datetime.now(),
            'metrics': metrics
        })
        
    def on_alert_triggered(self, level: AlertLevel, message: str):
        """Handle alerts."""
        self.alerts_history.append({
            'timestamp': datetime.now(),
            'level': level,
            'message': message
        })
        
    def on_error_occurred(self, error: str):
        """Handle errors."""
        self.errors_history.append({
            'timestamp': datetime.now(),
            'error': error
        })
        
    def on_circuit_breaker_opened(self, reason: str):
        """Handle circuit breaker events."""
        self.circuit_breaker_events.append({
            'timestamp': datetime.now(),
            'event': 'opened',
            'reason': reason
        })
        
    def on_circuit_breaker_closed(self):
        """Handle circuit breaker recovery."""
        self.circuit_breaker_events.append({
            'timestamp': datetime.now(),
            'event': 'closed'
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        return {
            'metrics_count': len(self.metrics_history),
            'alerts_count': len(self.alerts_history),
            'errors_count': len(self.errors_history),
            'circuit_breaker_events': len(self.circuit_breaker_events),
            'last_metrics': (
                self.metrics_history[-1] if self.metrics_history else None
            )
        }


class WatchdogStabilityTester:
    """Main test class for watchdog stability."""
    
    def __init__(self):
        self.test_results = []
        self.app = None
        self.controller = None
        self.collector = None
        
    def setup_qt_application(self):
        """Setup Qt application for testing."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def cleanup_qt_application(self):
        """Cleanup Qt application."""
        if self.app:
            self.app.quit()
            
    def run_all_tests(self):
        """Run all stability tests."""
        print("=" * 60)
        print("WATCHDOG STABILITY TEST SUITE")
        print("=" * 60)
        print()
        
        # Setup Qt application
        self.setup_qt_application()
        
        tests = [
            self.test_qt_threading_compatibility,
            self.test_long_running_stability,
            self.test_process_detection_accuracy,
            self.test_circuit_breaker_under_load,
            self.test_graceful_shutdown_restart,
            self.test_configuration_changes,
            self.test_no_qbasictimer_errors,
            self.test_memory_leak_detection
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
                error_msg = f"Exception: {e}\n{traceback.format_exc()}"
                self.test_results.append(
                    (test_func.__name__, False, error_msg)
                )
                print(f"❌ ERROR: {error_msg}")
                
        self._print_summary()
        self.cleanup_qt_application()
        
    def test_qt_threading_compatibility(self):
        """Test Qt threading compatibility - no QBasicTimer errors."""
        print("Testing Qt threading compatibility...")
        
        # Create Qt-based watchdog
        config = WatchdogConfig(
            check_interval=2,  # Fast checks for testing
            vram_threshold=80.0,
            max_processes=5
        )
        
        self.controller = WatchdogController(config)
        self.collector = TestMetricsCollector()
        
        # Connect signals
        self.controller.signals.metrics_ready.connect(
            self.collector.on_metrics_ready
        )
        self.controller.signals.error_occurred.connect(
            self.collector.on_error_occurred
        )
        
        # Start watchdog
        self.controller.start_watchdog()
        
        # Run for 10 seconds
        print("Running watchdog for 10 seconds...")
        start_time = time.time()
        error_count = 0
        
        # Process events for 10 seconds
        while time.time() - start_time < 10:
            self.app.processEvents()
            time.sleep(0.1)
            
            # Check for QBasicTimer errors
            for error in self.collector.errors_history:
                if "QBasicTimer" in error['error']:
                    error_count += 1
                    print(f"❌ QBasicTimer error detected: {error['error']}")
                    
        # Stop watchdog
        self.controller.stop_watchdog()
        
        summary = self.collector.get_summary()
        print(f"Collected {summary['metrics_count']} metrics")
        print(f"Encountered {error_count} QBasicTimer errors")
        
        if error_count == 0 and summary['metrics_count'] > 0:
            return True, (
                f"Qt threading working correctly with "
                f"{summary['metrics_count']} metrics collected"
            )
        else:
            return False, (
                f"Qt threading issues: {error_count} QBasicTimer errors"
            )
            
    def test_long_running_stability(self):
        """Test long-running stability (5+ minutes)."""
        print("Testing long-running stability...")
        
        # Create watchdog with production-like settings
        config = WatchdogConfig(
            check_interval=30,  # Normal interval
            vram_threshold=95.0,
            max_processes=5,
            circuit_breaker_config={
                'failure_threshold': 5,
                'recovery_timeout': 60,
                'success_threshold': 3
            }
        )
        
        self.controller = WatchdogController(config)
        self.collector = TestMetricsCollector()
        
        # Connect all signals
        self._connect_all_signals()
        
        # Start watchdog
        self.controller.start_watchdog()
        start_time = time.time()
        test_duration = 300  # 5 minutes
        
        print(f"Running stability test for {test_duration} seconds...")
        print("Progress: ", end='', flush=True)
        
        last_progress = 0
        crashes = 0
        
        while time.time() - start_time < test_duration:
            try:
                self.app.processEvents()
                time.sleep(0.5)
                
                # Show progress every 30 seconds
                elapsed = time.time() - start_time
                progress = int(elapsed / 30)
                if progress > last_progress:
                    print(".", end='', flush=True)
                    last_progress = progress
                    
                # Check if watchdog is still running
                status = self.controller.get_status()
                if status and not status.is_running:
                    crashes += 1
                    print(f"\n❌ Watchdog crashed after {elapsed:.0f} seconds")
                    # Try to restart
                    self.controller.start_watchdog()
                    
            except Exception as e:
                crashes += 1
                print(f"\n❌ Exception after {elapsed:.0f} seconds: {e}")
                
        print()  # New line after progress dots
        
        # Stop watchdog
        self.controller.stop_watchdog()
        
        # Analyze results
        summary = self.collector.get_summary()
        runtime = time.time() - start_time
        
        print(f"\nStability test results:")
        print(f"  Runtime: {runtime:.0f} seconds")
        print(f"  Metrics collected: {summary['metrics_count']}")
        print(f"  Errors: {summary['errors_count']}")
        print(f"  Crashes: {crashes}")
        print(f"  Circuit breaker events: {summary['circuit_breaker_events']}")
        
        # Success criteria
        expected_metrics = int(runtime / config.check_interval) * 0.8
        if (crashes == 0 and 
            summary['metrics_count'] >= expected_metrics and
            runtime >= test_duration * 0.95):
            return True, (
                f"Stable for {runtime:.0f}s with "
                f"{summary['metrics_count']} metrics"
            )
        else:
            return False, (
                f"Stability issues: {crashes} crashes in {runtime:.0f}s"
            )
            
    def test_process_detection_accuracy(self):
        """Test accurate process detection without false positives."""
        print("Testing process detection accuracy...")
        
        # Create some test processes
        test_processes = []
        
        def dummy_process():
            """Dummy process for testing."""
            time.sleep(10)
            
        try:
            # Start a few dummy processes
            for i in range(3):
                p = multiprocessing.Process(
                    target=dummy_process,
                    name=f"test_process_{i}"
                )
                p.start()
                test_processes.append(p)
                
            # Let processes stabilize
            time.sleep(3)
            
            # Test process detection
            watchdog = SystemWatchdog()
            
            # Multiple detection rounds
            detection_results = []
            for i in range(5):
                metrics = watchdog.get_current_metrics()
                detection_results.append(metrics.dinoair_processes)
                time.sleep(1)
                
            # Cleanup test processes
            for p in test_processes:
                p.terminate()
                p.join(timeout=2)
                
            # Analyze detection consistency
            min_detected = min(detection_results)
            max_detected = max(detection_results)
            avg_detected = sum(detection_results) / len(detection_results)
            
            print(f"Process detection results: {detection_results}")
            print(f"Range: {min_detected} - {max_detected}")
            print(f"Average: {avg_detected:.1f}")
            
            # Should detect at least 1 (this test process)
            # and be consistent
            variance = max_detected - min_detected
            if min_detected >= 1 and variance <= 1:
                return True, (
                    f"Accurate detection: {avg_detected:.1f} processes "
                    f"(variance: {variance})"
                )
            else:
                return False, (
                    f"Inconsistent detection: {min_detected}-{max_detected} "
                    f"(variance: {variance})"
                )
                
        finally:
            # Ensure cleanup
            for p in test_processes:
                if p.is_alive():
                    p.terminate()
                    
    def test_circuit_breaker_under_load(self):
        """Test circuit breaker functionality under load."""
        print("Testing circuit breaker under load...")
        
        # Create circuit breaker with tight thresholds
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            success_threshold=2
        )
        
        results = {
            'successes': 0,
            'failures': 0,
            'circuit_opens': 0,
            'recoveries': 0
        }
        
        # Simulate varying load
        def unreliable_operation():
            """Operation that fails under load."""
            import random
            if random.random() < 0.6:  # 60% failure rate
                raise Exception("Simulated failure")
            return "Success"
            
        print("Simulating high-load scenario...")
        
        # Run for 30 seconds with varying load
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                result = breaker.call(unreliable_operation)
                results['successes'] += 1
                
                # Check if recovered from open state
                if breaker.get_state() == 'closed' and results['circuit_opens'] > 0:
                    results['recoveries'] += 1
                    
            except CircuitBreakerOpen:
                results['circuit_opens'] += 1
                # Wait a bit before retrying
                time.sleep(1)
                
            except Exception:
                results['failures'] += 1
                
            # Vary the load
            time.sleep(0.1)
            
        print(f"\nCircuit breaker results:")
        print(f"  Total attempts: {sum(results.values())}")
        print(f"  Successes: {results['successes']}")
        print(f"  Failures: {results['failures']}")
        print(f"  Circuit opens: {results['circuit_opens']}")
        print(f"  Recoveries: {results['recoveries']}")
        print(f"  Final state: {breaker.get_state()}")
        
        # Should have opened circuit and recovered
        if (results['circuit_opens'] > 0 and
            results['recoveries'] > 0 and
            results['circuit_opens'] < results['failures']):  # Not opening too often
            return True, (
                f"Circuit breaker working: {results['circuit_opens']} opens, "
                f"{results['recoveries']} recoveries"
            )
        else:
            return False, "Circuit breaker not functioning properly"
            
    def test_graceful_shutdown_restart(self):
        """Test graceful shutdown and restart cycles."""
        print("Testing graceful shutdown and restart cycles...")
        
        config = WatchdogConfig(
            check_interval=2,
            vram_threshold=90.0
        )
        
        cycles_completed = 0
        target_cycles = 5
        
        for cycle in range(target_cycles):
            print(f"\nCycle {cycle + 1}/{target_cycles}")
            
            try:
                # Create new controller
                controller = WatchdogController(config)
                collector = TestMetricsCollector()
                
                # Connect signals
                controller.signals.metrics_ready.connect(
                    collector.on_metrics_ready
                )
                
                # Start
                controller.start_watchdog()
                print("  Started watchdog")
                
                # Run briefly
                start = time.time()
                while time.time() - start < 3:
                    self.app.processEvents()
                    time.sleep(0.1)
                    
                # Check metrics were collected
                if len(collector.metrics_history) == 0:
                    print("  ❌ No metrics collected")
                    break
                    
                # Stop with timeout
                stopped = controller.stop_watchdog(timeout_ms=5000)
                if stopped:
                    print("  Stopped gracefully")
                    cycles_completed += 1
                else:
                    print("  ❌ Failed to stop gracefully")
                    break
                    
                # Brief pause between cycles
                time.sleep(1)
                
            except Exception as e:
                print(f"  ❌ Exception during cycle: {e}")
                break
                
        print(f"\nCompleted {cycles_completed}/{target_cycles} cycles")
        
        if cycles_completed == target_cycles:
            return True, f"All {target_cycles} shutdown/restart cycles completed"
        else:
            return False, (
                f"Only {cycles_completed}/{target_cycles} cycles completed"
            )
            
    def test_configuration_changes(self):
        """Test configuration changes without restart."""
        print("Testing configuration change handling...")
        
        # Initial configuration
        initial_config = WatchdogConfig(
            check_interval=5,
            vram_threshold=90.0,
            max_processes=5
        )
        
        controller = WatchdogController(initial_config)
        collector = TestMetricsCollector()
        
        controller.signals.metrics_ready.connect(collector.on_metrics_ready)
        controller.signals.alert_triggered.connect(collector.on_alert_triggered)
        
        # Start with initial config
        controller.start_watchdog()
        print("Started with initial configuration")
        
        # Collect some metrics
        start = time.time()
        while time.time() - start < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        initial_metrics_count = len(collector.metrics_history)
        
        # Change configuration
        new_config = WatchdogConfig(
            check_interval=2,  # Faster checks
            vram_threshold=70.0,  # Lower threshold
            max_processes=3
        )
        
        print("Updating configuration...")
        controller.update_config(new_config)
        
        # Clear history to track new metrics
        collector.metrics_history.clear()
        collector.alerts_history.clear()
        
        # Run with new config
        start = time.time()
        while time.time() - start < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        new_metrics_count = len(collector.metrics_history)
        
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nConfiguration change results:")
        print(f"  Initial metrics (5s): {initial_metrics_count}")
        print(f"  New config metrics (5s): {new_metrics_count}")
        print(f"  Alerts triggered: {len(collector.alerts_history)}")
        
        # With faster interval, should have more metrics
        if new_metrics_count > initial_metrics_count:
            return True, (
                f"Config changes applied: {initial_metrics_count} -> "
                f"{new_metrics_count} metrics/5s"
            )
        else:
            return False, "Configuration changes not properly applied"
            
    def test_no_qbasictimer_errors(self):
        """Specific test for QBasicTimer threading errors."""
        print("Testing for QBasicTimer threading errors...")
        
        # Create adapter to test compatibility layer
        adapter = create_watchdog_adapter(
            use_qt=True,
            check_interval_seconds=2,
            vram_threshold_percent=80.0
        )
        
        error_queue = queue.Queue()
        
        def error_callback(level: AlertLevel, message: str):
            """Capture errors."""
            if "QBasicTimer" in message or "thread" in message.lower():
                error_queue.put(message)
                
        adapter.alert_callback = error_callback
        
        # Start monitoring
        adapter.start_monitoring()
        print("Monitoring started, checking for threading errors...")
        
        # Monitor for 15 seconds
        start_time = time.time()
        qt_errors = []
        
        while time.time() - start_time < 15:
            self.app.processEvents()
            time.sleep(0.1)
            
            # Check for errors
            try:
                error = error_queue.get_nowait()
                qt_errors.append(error)
                print(f"  ❌ Threading error: {error}")
            except queue.Empty:
                pass
                
        # Stop monitoring
        adapter.stop_monitoring()
        
        if len(qt_errors) == 0:
            return True, "No QBasicTimer or threading errors detected"
        else:
            return False, f"Found {len(qt_errors)} threading errors"
            
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        print("Testing for memory leaks...")
        
        import psutil
        import gc
        
        # Get initial memory usage
        process = psutil.Process()
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        config = WatchdogConfig(
            check_interval=1,  # Fast checks to stress test
            vram_threshold=90.0
        )
        
        # Run multiple start/stop cycles
        memory_samples = [initial_memory]
        
        for i in range(10):
            controller = WatchdogController(config)
            controller.start_watchdog()
            
            # Run briefly
            start = time.time()
            while time.time() - start < 2:
                self.app.processEvents()
                time.sleep(0.1)
                
            controller.stop_watchdog()
            
            # Force garbage collection and measure memory
            gc.collect()
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory)
            
        # Calculate memory growth
        memory_growth = memory_samples[-1] - memory_samples[0]
        avg_growth_per_cycle = memory_growth / 10
        
        print(f"\nMemory usage:")
        print(f"  Initial: {memory_samples[0]:.1f} MB")
        print(f"  Final: {memory_samples[-1]:.1f} MB")
        print(f"  Total growth: {memory_growth:.1f} MB")
        print(f"  Per cycle: {avg_growth_per_cycle:.1f} MB")
        
        # Allow some growth but not excessive
        if avg_growth_per_cycle < 1.0:  # Less than 1MB per cycle
            return True, f"No significant memory leak ({avg_growth_per_cycle:.1f} MB/cycle)"
        else:
            return False, f"Possible memory leak ({avg_growth_per_cycle:.1f} MB/cycle)"
            
    def _connect_all_signals(self):
        """Connect all watchdog signals to collector."""
        if not self.controller or not self.collector:
            return
            
        signals = self.controller.signals
        
        # Metrics and alerts
        signals.metrics_ready.connect(self.collector.on_metrics_ready)
        signals.alert_triggered.connect(self.collector.on_alert_triggered)
        
        # Errors and recovery
        signals.error_occurred.connect(self.collector.on_error_occurred)
        signals.circuit_breaker_opened.connect(
            self.collector.on_circuit_breaker_opened
        )
        signals.circuit_breaker_closed.connect(
            self.collector.on_circuit_breaker_closed
        )
        
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("STABILITY TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✅ All stability tests passed!")
            print("\nKey validations:")
            print("- No QBasicTimer threading errors")
            print("- Stable operation for 5+ minutes")
            print("- Accurate process detection")
            print("- Circuit breaker protection working")
            print("- Graceful shutdown/restart")
            print("- Dynamic configuration updates")
            print("- No memory leaks detected")
        else:
            print("\n❌ Some stability tests failed:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"  - {test_name}: {message}")


def main():
    """Run the stability test suite."""
    print("Starting Watchdog Stability Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = WatchdogStabilityTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        traceback.print_exc()
    finally:
        print("\nStability test suite completed")


if __name__ == "__main__":
    main()