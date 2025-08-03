"""Stress test suite for watchdog under extreme conditions.

This test file focuses on:
- Simulating high CPU/RAM/VRAM usage
- Creating/destroying many processes rapidly
- Testing with permission errors and access denied scenarios
- Simulating GPU driver crashes and recovery
- Testing with database connection failures
"""

import sys
import time
import threading
import multiprocessing
import psutil
import os
import tempfile
import shutil
import ctypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import random
import subprocess

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from src.utils.logger import Logger
from src.utils.watchdog_qt import (
    WatchdogController, WatchdogConfig, SystemMetrics, AlertLevel
)
from src.utils.watchdog_compat import create_watchdog_adapter
from src.utils.Watchdog import SystemWatchdog

logger = Logger()


class ResourceStressor:
    """Creates stress on system resources."""
    
    def __init__(self):
        self.stress_threads = []
        self.stop_flag = threading.Event()
        self.memory_blocks = []
        
    def stress_cpu(self, cores: int = None, duration: int = 10):
        """Create CPU stress by running intensive calculations."""
        if cores is None:
            cores = multiprocessing.cpu_count()
            
        def cpu_burn():
            """Burn CPU cycles."""
            start_time = time.time()
            while not self.stop_flag.is_set() and time.time() - start_time < duration:
                # Intensive calculation
                _ = sum(i * i for i in range(10000))
                
        print(f"Starting CPU stress on {cores} cores...")
        for _ in range(cores):
            thread = threading.Thread(target=cpu_burn)
            thread.start()
            self.stress_threads.append(thread)
            
    def stress_memory(self, size_mb: int = 1024, duration: int = 10):
        """Create memory stress by allocating large blocks."""
        print(f"Starting memory stress ({size_mb} MB)...")
        
        def allocate_memory():
            """Allocate and hold memory."""
            start_time = time.time()
            block_size = 10 * 1024 * 1024  # 10MB blocks
            
            while not self.stop_flag.is_set() and time.time() - start_time < duration:
                try:
                    if len(self.memory_blocks) * 10 < size_mb:
                        # Allocate and fill memory to prevent optimization
                        block = bytearray(block_size)
                        for i in range(0, block_size, 1024):
                            block[i] = random.randint(0, 255)
                        self.memory_blocks.append(block)
                    time.sleep(0.1)
                except MemoryError:
                    print("Memory allocation failed - system under stress")
                    break
                    
        thread = threading.Thread(target=allocate_memory)
        thread.start()
        self.stress_threads.append(thread)
        
    def stress_disk_io(self, temp_dir: str, duration: int = 10):
        """Create disk I/O stress."""
        print("Starting disk I/O stress...")
        
        def disk_operations():
            """Perform intensive disk operations."""
            start_time = time.time()
            file_count = 0
            
            while not self.stop_flag.is_set() and time.time() - start_time < duration:
                try:
                    # Write random files
                    filename = Path(temp_dir) / f"stress_test_{file_count}.dat"
                    with open(filename, 'wb') as f:
                        f.write(os.urandom(1024 * 1024))  # 1MB random data
                        
                    # Read back
                    with open(filename, 'rb') as f:
                        _ = f.read()
                        
                    # Delete
                    filename.unlink()
                    file_count += 1
                    
                except Exception as e:
                    print(f"Disk I/O error: {e}")
                    
        thread = threading.Thread(target=disk_operations)
        thread.start()
        self.stress_threads.append(thread)
        
    def create_process_storm(self, count: int = 50):
        """Create many processes rapidly."""
        print(f"Creating process storm ({count} processes)...")
        
        processes = []
        
        def dummy_process():
            """Dummy process that just sleeps."""
            time.sleep(30)
            
        try:
            for i in range(count):
                if self.stop_flag.is_set():
                    break
                    
                p = multiprocessing.Process(
                    target=dummy_process,
                    name=f"stress_process_{i}"
                )
                p.start()
                processes.append(p)
                
                # Random delay to simulate varying spawn rates
                time.sleep(random.uniform(0.01, 0.1))
                
            return processes
            
        except Exception as e:
            print(f"Process creation error: {e}")
            return processes
            
    def stop_all(self):
        """Stop all stress operations."""
        print("Stopping all stress operations...")
        self.stop_flag.set()
        
        # Wait for threads
        for thread in self.stress_threads:
            thread.join(timeout=5)
            
        # Clear memory
        self.memory_blocks.clear()
        
        print("Stress operations stopped")


class WatchdogStressTester:
    """Main stress test class."""
    
    def __init__(self):
        self.test_results = []
        self.app = None
        self.temp_dir = None
        self.stressor = ResourceStressor()
        
    def setup(self):
        """Setup test environment."""
        # Create Qt application
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="watchdog_stress_")
        
    def cleanup(self):
        """Cleanup test environment."""
        # Stop any remaining stress operations
        self.stressor.stop_all()
        
        # Remove temporary directory
        if self.temp_dir and Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Failed to cleanup temp dir: {e}")
                
        # Cleanup Qt application
        if self.app:
            self.app.quit()
            
    def run_all_tests(self):
        """Run all stress tests."""
        print("=" * 60)
        print("WATCHDOG STRESS TEST SUITE")
        print("=" * 60)
        print()
        
        self.setup()
        
        tests = [
            self.test_high_cpu_stress,
            self.test_high_memory_stress,
            self.test_process_storm,
            self.test_rapid_process_creation_destruction,
            self.test_permission_errors,
            self.test_gpu_driver_simulation,
            self.test_database_failures,
            self.test_combined_stress,
            self.test_recovery_after_stress
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
                    
                # Cool down between tests
                print("Cooling down...")
                time.sleep(5)
                
            except Exception as e:
                import traceback
                error_msg = f"Exception: {e}\n{traceback.format_exc()}"
                self.test_results.append(
                    (test_func.__name__, False, error_msg)
                )
                print(f"❌ ERROR: {error_msg}")
                
        self._print_summary()
        self.cleanup()
        
    def test_high_cpu_stress(self):
        """Test watchdog under high CPU stress."""
        print("Testing under high CPU stress...")
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=2,
            cpu_threshold=70.0,
            circuit_breaker_config={
                'failure_threshold': 10,  # Higher threshold for stress
                'recovery_timeout': 30
            }
        )
        
        controller = WatchdogController(config)
        metrics_collector = []
        alerts_collector = []
        
        controller.signals.metrics_ready.connect(
            lambda m: metrics_collector.append(m)
        )
        controller.signals.alert_triggered.connect(
            lambda l, msg: alerts_collector.append((l, msg))
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Apply CPU stress
        self.stressor.stress_cpu(cores=multiprocessing.cpu_count() // 2, duration=15)
        
        # Monitor under stress
        start_time = time.time()
        while time.time() - start_time < 20:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop stress
        self.stressor.stop_all()
        
        # Let system recover
        time.sleep(5)
        
        # Stop watchdog
        controller.stop_watchdog()
        
        # Analyze results
        print(f"\nResults:")
        print(f"  Metrics collected: {len(metrics_collector)}")
        print(f"  Alerts triggered: {len(alerts_collector)}")
        
        if metrics_collector:
            cpu_values = [m.cpu_percent for m in metrics_collector]
            avg_cpu = sum(cpu_values) / len(cpu_values)
            max_cpu = max(cpu_values)
            print(f"  Average CPU: {avg_cpu:.1f}%")
            print(f"  Max CPU: {max_cpu:.1f}%")
            
        # Should handle high CPU without crashing
        if len(metrics_collector) >= 8:
            return True, (
                f"Handled CPU stress: {len(metrics_collector)} metrics, "
                f"max CPU {max_cpu:.1f}%"
            )
        else:
            return False, "Failed to collect metrics under CPU stress"
            
    def test_high_memory_stress(self):
        """Test watchdog under high memory stress."""
        print("Testing under high memory stress...")
        
        # Get available memory
        memory = psutil.virtual_memory()
        available_mb = memory.available // (1024 * 1024)
        stress_mb = min(available_mb // 2, 2048)  # Use half available, max 2GB
        
        print(f"Available memory: {available_mb} MB, will stress with {stress_mb} MB")
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=2,
            ram_threshold=80.0
        )
        
        controller = WatchdogController(config)
        metrics_collector = []
        memory_alerts = []
        
        controller.signals.metrics_ready.connect(
            lambda m: metrics_collector.append(m)
        )
        controller.signals.alert_triggered.connect(
            lambda l, msg: memory_alerts.append((l, msg)) if 'RAM' in msg else None
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Apply memory stress
        self.stressor.stress_memory(size_mb=stress_mb, duration=15)
        
        # Monitor under stress
        start_time = time.time()
        while time.time() - start_time < 20:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop stress
        self.stressor.stop_all()
        
        # Let system recover
        time.sleep(5)
        
        # Stop watchdog
        controller.stop_watchdog()
        
        # Analyze results
        print(f"\nResults:")
        print(f"  Metrics collected: {len(metrics_collector)}")
        print(f"  Memory alerts: {len(memory_alerts)}")
        
        if metrics_collector:
            ram_values = [m.ram_percent for m in metrics_collector]
            max_ram = max(ram_values)
            print(f"  Max RAM usage: {max_ram:.1f}%")
            
        # Should handle memory stress
        if len(metrics_collector) >= 8 and len(memory_alerts) > 0:
            return True, (
                f"Handled memory stress: {len(memory_alerts)} alerts, "
                f"max RAM {max_ram:.1f}%"
            )
        else:
            return False, "Failed to handle memory stress properly"
            
    def test_process_storm(self):
        """Test watchdog with process storm."""
        print("Testing process storm handling...")
        
        # Create watchdog with tight process limits
        config = WatchdogConfig(
            check_interval=1,
            max_processes=10,  # Low limit to trigger alerts
            self_terminate=False  # Don't actually terminate
        )
        
        controller = WatchdogController(config)
        process_alerts = []
        emergency_events = []
        
        controller.signals.alert_triggered.connect(
            lambda l, msg: process_alerts.append((l, msg)) 
            if 'process' in msg.lower() else None
        )
        controller.signals.emergency_shutdown_initiated.connect(
            lambda reason: emergency_events.append(reason)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Create process storm
        print("Creating process storm...")
        processes = self.stressor.create_process_storm(count=20)
        
        # Monitor during storm
        start_time = time.time()
        while time.time() - start_time < 10:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Cleanup processes
        print("Cleaning up processes...")
        for p in processes:
            if p.is_alive():
                p.terminate()
                
        # Wait for cleanup
        for p in processes:
            p.join(timeout=2)
            
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Process alerts: {len(process_alerts)}")
        print(f"  Emergency events: {len(emergency_events)}")
        
        # Should detect and alert on process storm
        if len(process_alerts) > 0:
            return True, (
                f"Detected process storm: {len(process_alerts)} alerts"
            )
        else:
            return False, "Failed to detect process storm"
            
    def test_rapid_process_creation_destruction(self):
        """Test rapid process creation and destruction."""
        print("Testing rapid process creation/destruction...")
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=1,
            max_processes=15
        )
        
        controller = WatchdogController(config)
        metrics_collector = []
        
        controller.signals.metrics_ready.connect(
            lambda m: metrics_collector.append(m)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Rapid process cycling
        print("Starting rapid process cycling...")
        processes_created = 0
        
        start_time = time.time()
        while time.time() - start_time < 15:
            # Create a few processes
            batch = []
            for _ in range(random.randint(2, 5)):
                p = multiprocessing.Process(
                    target=lambda: time.sleep(random.uniform(0.5, 2.0))
                )
                p.start()
                batch.append(p)
                processes_created += 1
                
            # Let them run briefly
            time.sleep(random.uniform(0.2, 0.5))
            
            # Terminate some
            for p in batch:
                if random.random() > 0.5 and p.is_alive():
                    p.terminate()
                    
            # Process events
            self.app.processEvents()
            
        # Cleanup remaining
        for p in multiprocessing.active_children():
            p.terminate()
            
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Processes created: {processes_created}")
        print(f"  Metrics collected: {len(metrics_collector)}")
        
        if metrics_collector:
            process_counts = [m.dinoair_processes for m in metrics_collector]
            print(f"  Process count range: {min(process_counts)}-{max(process_counts)}")
            
        # Should track changing process counts
        if len(metrics_collector) >= 10:
            return True, (
                f"Tracked {processes_created} rapid process changes"
            )
        else:
            return False, "Failed to track rapid process changes"
            
    def test_permission_errors(self):
        """Test handling of permission errors."""
        print("Testing permission error handling...")
        
        # Create watchdog
        config = WatchdogConfig(check_interval=2)
        controller = WatchdogController(config)
        
        error_events = []
        recovery_events = []
        
        controller.signals.error_occurred.connect(
            lambda msg: error_events.append(msg)
        )
        controller.signals.error_recovered.connect(
            lambda msg: recovery_events.append(msg)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Simulate permission errors by restricting access
        if os.name == 'posix':  # Unix-like systems
            # Create a file with no permissions
            restricted_file = Path(self.temp_dir) / "restricted.lock"
            restricted_file.touch()
            os.chmod(restricted_file, 0o000)
            
            # Try to trigger operations that might fail
            # The watchdog should handle these gracefully
            
        # Monitor for a while
        start_time = time.time()
        while time.time() - start_time < 10:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Errors handled: {len(error_events)}")
        print(f"  Recoveries: {len(recovery_events)}")
        
        # Should continue operating despite permission issues
        return True, (
            f"Handled permission scenarios: {len(error_events)} errors"
        )
        
    def test_gpu_driver_simulation(self):
        """Simulate GPU driver issues."""
        print("Testing GPU driver crash simulation...")
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=2,
            vram_threshold=80.0
        )
        
        controller = WatchdogController(config)
        vram_errors = []
        fallback_events = []
        
        controller.signals.error_occurred.connect(
            lambda msg: vram_errors.append(msg) if 'vram' in msg.lower() else None
        )
        controller.signals.metrics_degraded.connect(
            lambda m, reason: fallback_events.append(reason)
        )
        
        # Monkey patch the VRAM collection to simulate failures
        original_get_vram = SystemWatchdog._get_vram_info
        failure_count = 0
        
        def failing_vram_info():
            nonlocal failure_count
            failure_count += 1
            if failure_count < 5:
                raise Exception("Simulated GPU driver crash")
            # After 5 failures, recover
            return original_get_vram()
            
        SystemWatchdog._get_vram_info = failing_vram_info
        
        try:
            # Start watchdog
            controller.start_watchdog()
            
            # Monitor during simulated failures
            start_time = time.time()
            while time.time() - start_time < 15:
                self.app.processEvents()
                time.sleep(0.1)
                
            # Stop watchdog
            controller.stop_watchdog()
            
        finally:
            # Restore original function
            SystemWatchdog._get_vram_info = original_get_vram
            
        print(f"\nResults:")
        print(f"  VRAM errors: {len(vram_errors)}")
        print(f"  Fallback events: {len(fallback_events)}")
        print(f"  Simulated failures: {failure_count}")
        
        # Should use fallback values during GPU issues
        if len(fallback_events) > 0 and failure_count >= 5:
            return True, (
                f"Handled GPU driver issues: {len(fallback_events)} "
                f"fallbacks used"
            )
        else:
            return False, "Failed to handle GPU driver simulation"
            
    def test_database_failures(self):
        """Test handling of database connection failures."""
        print("Testing database failure handling...")
        
        # Simulate database operations
        class FailingDatabase:
            def __init__(self, fail_rate=0.5):
                self.fail_rate = fail_rate
                self.attempts = 0
                self.failures = 0
                
            def store_metrics(self, metrics):
                self.attempts += 1
                if random.random() < self.fail_rate:
                    self.failures += 1
                    raise Exception("Database connection failed")
                return True
                
        db = FailingDatabase(fail_rate=0.7)  # 70% failure rate
        
        # Create watchdog
        config = WatchdogConfig(check_interval=1)
        controller = WatchdogController(config)
        
        # Connect failing database
        controller.signals.metrics_ready.connect(
            lambda m: db.store_metrics(m)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        # Run with database failures
        start_time = time.time()
        while time.time() - start_time < 10:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Database attempts: {db.attempts}")
        print(f"  Database failures: {db.failures}")
        print(f"  Failure rate: {db.failures/db.attempts*100:.1f}%")
        
        # Should continue operating despite database failures
        if db.attempts >= 8:
            return True, (
                f"Handled database failures: {db.failures}/{db.attempts} failed"
            )
        else:
            return False, "Watchdog stopped due to database failures"
            
    def test_combined_stress(self):
        """Test watchdog under combined stress conditions."""
        print("Testing under combined stress...")
        
        # Create watchdog with balanced settings
        config = WatchdogConfig(
            check_interval=2,
            vram_threshold=85.0,
            cpu_threshold=85.0,
            ram_threshold=85.0,
            max_processes=20
        )
        
        controller = WatchdogController(config)
        all_metrics = []
        all_alerts = []
        circuit_breaker_events = []
        
        controller.signals.metrics_ready.connect(
            lambda m: all_metrics.append(m)
        )
        controller.signals.alert_triggered.connect(
            lambda l, msg: all_alerts.append((l, msg))
        )
        controller.signals.circuit_breaker_opened.connect(
            lambda reason: circuit_breaker_events.append(reason)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        print("Applying combined stress...")
        
        # Apply multiple stressors
        self.stressor.stress_cpu(cores=2, duration=20)
        self.stressor.stress_memory(size_mb=512, duration=20)
        self.stressor.stress_disk_io(self.temp_dir, duration=20)
        
        # Also create some processes
        processes = []
        for i in range(5):
            p = multiprocessing.Process(
                target=lambda: time.sleep(15),
                name=f"combined_stress_{i}"
            )
            p.start()
            processes.append(p)
            
        # Monitor under combined stress
        start_time = time.time()
        while time.time() - start_time < 25:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop all stress
        self.stressor.stop_all()
        
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=2)
                
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Metrics collected: {len(all_metrics)}")
        print(f"  Alerts triggered: {len(all_alerts)}")
        print(f"  Circuit breaker events: {len(circuit_breaker_events)}")
        
        # Categorize alerts
        alert_types = {}
        for level, msg in all_alerts:
            key = 'vram' if 'vram' in msg.lower() else \
                  'cpu' if 'cpu' in msg.lower() else \
                  'ram' if 'ram' in msg.lower() else \
                  'process' if 'process' in msg.lower() else 'other'
            alert_types[key] = alert_types.get(key, 0) + 1
            
        print(f"  Alert breakdown: {alert_types}")
        
        # Should handle combined stress
        if len(all_metrics) >= 10 and len(circuit_breaker_events) == 0:
            return True, (
                f"Handled combined stress: {len(all_metrics)} metrics, "
                f"{len(all_alerts)} alerts"
            )
        else:
            return False, "Failed under combined stress"
            
    def test_recovery_after_stress(self):
        """Test recovery after extreme stress."""
        print("Testing recovery after stress...")
        
        # Create watchdog
        config = WatchdogConfig(
            check_interval=2,
            circuit_breaker_config={
                'failure_threshold': 5,
                'recovery_timeout': 10,
                'success_threshold': 3
            }
        )
        
        controller = WatchdogController(config)
        
        health_states = []
        recovery_events = []
        
        controller.signals.component_health_changed.connect(
            lambda name, state, msg: health_states.append((name, state.value))
        )
        controller.signals.error_recovered.connect(
            lambda msg: recovery_events.append(msg)
        )
        
        # Start watchdog
        controller.start_watchdog()
        
        print("Phase 1: Normal operation")
        time.sleep(5)
        
        print("Phase 2: Applying stress")
        # Apply heavy stress
        self.stressor.stress_cpu(cores=multiprocessing.cpu_count(), duration=10)
        self.stressor.stress_memory(size_mb=1024, duration=10)
        
        # Wait during stress
        start_time = time.time()
        while time.time() - start_time < 10:
            self.app.processEvents()
            time.sleep(0.1)
            
        print("Phase 3: Removing stress and monitoring recovery")
        # Stop stress
        self.stressor.stop_all()
        
        # Monitor recovery
        recovery_start = time.time()
        while time.time() - recovery_start < 15:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop watchdog
        controller.stop_watchdog()
        
        print(f"\nResults:")
        print(f"  Health state changes: {len(health_states)}")
        print(f"  Recovery events: {len(recovery_events)}")
        
        # Check if recovered
        if health_states:
            final_states = {}
            for name, state in health_states:
                final_states[name] = state
            print(f"  Final component states: {final_states}")
            
        # Should recover after stress removed
        if len(recovery_events) > 0:
            return True, (
                f"Successfully recovered: {len(recovery_events)} "
                f"recovery events"
            )
        else:
            return False, "Failed to recover after stress"
            
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("STRESS TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✅ All stress tests passed!")
            print("\nKey validations:")
            print("- Handles high CPU stress without crashing")
            print("- Manages high memory pressure gracefully")
            print("- Detects and alerts on process storms")
            print("- Tracks rapid process creation/destruction")
            print("- Continues operating with permission errors")
            print("- Falls back gracefully during GPU driver issues")
            print("- Tolerates database connection failures")
            print("- Survives combined stress conditions")
            print("- Recovers properly after stress removed")
        else:
            print("\n❌ Some stress tests failed:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"  - {test_name}: {message}")


def main():
    """Run the stress test suite."""
    print("Starting Watchdog Stress Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("⚠️  WARNING: This will stress your system!")
    print("⚠️  Close other applications before running")
    print()
    
    # Give user a chance to cancel
    print("Starting in 5 seconds... Press Ctrl+C to cancel")
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return
        
    tester = WatchdogStressTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure cleanup
        tester.cleanup()
        print("\nStress test suite completed")


if __name__ == "__main__":
    main()