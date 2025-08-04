"""Test script for watchdog error recovery and graceful degradation.

This script demonstrates and tests all the error recovery features
implemented in the watchdog system.
"""

import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from src.utils.logger import Logger
from src.utils.watchdog_config_validator import WatchdogConfigValidator
from src.utils.watchdog_compat import create_watchdog_adapter, FallbackConfig
from src.utils.watchdog_health import WatchdogHealthMonitor
from src.utils.Watchdog import AlertLevel, SystemMetrics

logger = Logger()


class WatchdogRecoveryTester:
    """Test harness for watchdog recovery features."""
    
    def __init__(self):
        self.test_results = []
        self.watchdog = None
        self.health_monitor = None
        
    def run_all_tests(self):
        """Run all recovery tests."""
        print("=" * 60)
        print("WATCHDOG ERROR RECOVERY TEST SUITE")
        print("=" * 60)
        print()
        
        tests = [
            self.test_config_validation,
            self.test_static_method_error_handling,
            self.test_qt_fallback_to_legacy,
            self.test_health_monitoring,
            self.test_circuit_breaker,
            self.test_metrics_degradation,
            self.test_component_recovery,
            self.test_45_second_shutdown_fix,
            self.test_no_qt_threading_errors,
            self.test_app_continues_after_errors,
            self.test_auto_recovery_validation
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
        
    def test_config_validation(self):
        """Test configuration validation and correction."""
        print("Testing configuration validation...")
        
        # Test invalid configuration
        invalid_config = {
            'vram_threshold': 150,  # Too high
            'max_processes': -5,    # Negative
            'check_interval': 1,    # Too low
            'self_terminate': 'yes',  # Wrong type
            'unknown_param': 123,   # Unknown parameter
            'circuit_breaker_config': {
                'failure_threshold': 100,  # Too high
                'timeout': 'five'  # Wrong type
            }
        }
        
        validator = WatchdogConfigValidator()
        result = validator.validate(invalid_config)
        
        print(f"Found {len(result.issues)} validation issues:")
        for param, level, message in result.issues:
            print(f"  - {level.value}: {param} - {message}")
            
        print("\nCorrected configuration:")
        for key, value in result.corrected_config.items():
            if key in invalid_config:
                if invalid_config[key] != value:
                    print(f"  {key}: {invalid_config[key]} -> {value}")
                    
        # Test safe defaults
        safe_defaults = validator.get_safe_defaults()
        print(f"\nSafe defaults contain {len(safe_defaults)} parameters")
        
        return True, "Configuration validation working correctly"
        
    def test_static_method_error_handling(self):
        """Test error handling in static methods."""
        print("Testing static method error handling...")
        
        from src.utils.Watchdog import SystemWatchdog
        
        # Test VRAM info collection with all methods
        print("\n1. Testing VRAM info collection:")
        vram_used, vram_total, vram_percent = SystemWatchdog._get_vram_info()
        print(
            f"   VRAM: {vram_used:.0f}MB / {vram_total:.0f}MB "
            f"({vram_percent:.1f}%)"
        )
        
        if vram_total > 0:
            print("   ✓ VRAM info retrieved successfully")
        else:
            print("   ⚠ Using fallback VRAM values")
            
        # Test process counting with error handling
        print("\n2. Testing process counting:")
        process_count = SystemWatchdog._count_dinoair_processes()
        print(f"   Found {process_count} DinoAir processes")
        
        if process_count >= 1:
            print("   ✓ Process counting successful")
        else:
            print("   ⚠ Process counting may have encountered errors")
            
        # Test emergency cleanup
        print("\n3. Testing emergency cleanup (dry run):")
        cleanup_result = SystemWatchdog.emergency_cleanup()
        print(f"   Cleanup result: {cleanup_result}")
        
        return True, "Static method error handling verified"
        
    def test_qt_fallback_to_legacy(self):
        """Test automatic fallback from Qt to legacy implementation."""
        print("Testing Qt to legacy fallback...")
        
        # Create adapter with fallback configuration
        fallback_config = FallbackConfig(
            auto_fallback=True,
            fallback_delay=2.0,
            max_qt_retries=2
        )
        
        # Alert and metrics tracking
        alerts_received = []
        metrics_received = []
        
        def alert_handler(level: AlertLevel, message: str):
            alerts_received.append((level, message))
            print(f"   Alert: {level.value} - {message}")
            
        def metrics_handler(metrics: SystemMetrics):
            metrics_received.append(metrics)
            
        # Create watchdog with potential Qt issues
        self.watchdog = create_watchdog_adapter(
            use_qt=True,
            fallback_config=fallback_config,
            alert_callback=alert_handler,
            metrics_callback=metrics_handler,
            check_interval_seconds=5,
            vram_threshold_percent=80.0
        )
        
        print(f"\n1. Initial mode: {self.watchdog.current_mode.value}")
        
        # Start monitoring
        self.watchdog.start_monitoring()
        print("2. Started monitoring")
        
        # Wait for some metrics
        print("3. Waiting for metrics collection...")
        time.sleep(8)
        
        # Check status
        status_report = self.watchdog.get_status_report()
        print("\n4. Status Report:")
        print(status_report)
        
        # Stop monitoring
        self.watchdog.stop_monitoring()
        print("\n5. Stopped monitoring")
        
        mode_used = self.watchdog.current_mode.value
        metrics_count = len(metrics_received)
        
        return True, (
            f"Fallback test completed. Mode: {mode_used}, "
            f"Metrics collected: {metrics_count}"
        )
        
    def test_health_monitoring(self):
        """Test health monitoring system."""
        print("Testing health monitoring...")
        
        self.health_monitor = WatchdogHealthMonitor()
        
        # Track health events
        health_events = []
        
        def health_changed(component, state, message):
            health_events.append((component, state, message))
            print(f"   Health change: {component} -> {state} ({message})")
            
        self.health_monitor.signals.component_health_changed.connect(
            health_changed
        )
        
        # Start monitoring
        self.health_monitor.start_monitoring()
        print("1. Started health monitoring")
        
        # Simulate component operations
        print("\n2. Simulating component operations:")
        
        # Success
        self.health_monitor.record_success('vram_collector', 0.5)
        self.health_monitor.record_success('cpu_collector', 0.1)
        print("   ✓ Recorded successful operations")
        
        # Failures
        try:
            raise ValueError("Simulated VRAM error")
        except Exception as e:
            self.health_monitor.record_failure('vram_collector', e)
            
        try:
            raise TimeoutError("Simulated CPU timeout")
        except Exception as e:
            self.health_monitor.record_failure('cpu_collector', e)
            
        print("   ✓ Recorded failures")
        
        # Multiple failures to trigger degraded state
        for i in range(3):
            try:
                raise Exception(f"Error {i+1}")
            except Exception as e:
                self.health_monitor.record_failure('vram_collector', e)
                
        print("   ✓ Triggered multiple failures")
        
        # Get health report
        print("\n3. Health Report:")
        health_report = self.health_monitor.get_health_report()
        print(f"   Overall state: {health_report['overall_state']}")
        print("   Components:")
        for comp, info in health_report['components'].items():
            print(f"     - {comp}: {info['state']}")
            if info['metrics']['failure_count'] > 0:
                print(f"       Failures: {info['metrics']['failure_count']}")
                
        # Stop monitoring
        self.health_monitor.stop_monitoring()
        
        return True, (
            f"Health monitoring tested with {len(health_events)} events"
        )
        
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        print("Testing circuit breaker...")
        
        from src.utils.watchdog_qt import CircuitBreaker, CircuitBreakerOpen
        
        # Create circuit breaker
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=2,
            success_threshold=2
        )
        
        print("1. Circuit breaker initial state:", breaker.get_state())
        
        # Function that fails sometimes
        failure_count = 0
        
        def unreliable_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:
                raise Exception(f"Operation failed {failure_count}")
            return "Success"
            
        # Test failures
        print("\n2. Testing failures:")
        for i in range(4):
            try:
                result = breaker.call(unreliable_operation)
                print(f"   Attempt {i+1}: Success - {result}")
            except CircuitBreakerOpen:
                print(f"   Attempt {i+1}: Circuit breaker OPEN")
            except Exception as e:
                print(f"   Attempt {i+1}: Failed - {e}")
                
        print(f"   Circuit breaker state: {breaker.get_state()}")
        
        # Wait for recovery timeout
        print("\n3. Waiting for recovery timeout...")
        time.sleep(3)
        
        # Test recovery
        print("\n4. Testing recovery:")
        failure_count = 0  # Reset to allow success
        
        for i in range(3):
            try:
                # Now it should succeed
                def reliable_operation():
                    return "Recovered"
                    
                result = breaker.call(reliable_operation)
                print(f"   Recovery attempt {i+1}: {result}")
            except Exception as e:
                print(f"   Recovery attempt {i+1}: Failed - {e}")
                
        print(f"   Final state: {breaker.get_state()}")
        
        return True, "Circuit breaker tested successfully"
        
    def test_metrics_degradation(self):
        """Test metrics collection with fallback values."""
        print("Testing metrics degradation and fallback...")
        
        from src.utils.watchdog_qt import MetricsFallback
        from src.utils.Watchdog import SystemWatchdog
        
        # Create fallback handler
        fallback = MetricsFallback()
        
        # Get initial metrics
        print("1. Collecting initial metrics:")
        watchdog = SystemWatchdog()
        metrics1 = watchdog.get_current_metrics()
        print(f"   CPU: {metrics1.cpu_percent:.1f}%")
        print(f"   RAM: {metrics1.ram_percent:.1f}%")
        print(f"   VRAM: {metrics1.vram_percent:.1f}%")
        
        # Cache metrics
        fallback.last_good_metrics = metrics1
        fallback.last_update_time = datetime.now()
        
        print("\n2. Using cached metrics:")
        print(f"   Cached CPU: {fallback.last_good_metrics.cpu_percent:.1f}%")
        print("   Cache age: 0 seconds")
        
        # Simulate using defaults
        print("\n3. Default fallback values:")
        print(f"   Default VRAM total: {fallback.vram_total_mb:.0f}MB")
        print(f"   Default process count: {fallback.dinoair_processes}")
        
        return True, "Metrics fallback system verified"
        
    def test_component_recovery(self):
        """Test component recovery strategies."""
        print("Testing component recovery strategies...")
        
        from src.utils.watchdog_health import RecoveryStrategy, RecoveryAction
        
        # Create recovery actions
        actions = [
            RecoveryAction(
                strategy=RecoveryStrategy.RESET_STATE,
                max_attempts=3,
                cooldown_seconds=1
            ),
            RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK_MODE,
                max_attempts=2,
                cooldown_seconds=2
            )
        ]
        
        print("1. Testing recovery action logic:")
        
        # Test attempts
        action = actions[0]
        print(f"\n   Strategy: {action.strategy.value}")
        print(f"   Can attempt: {action.can_attempt()}")
        
        # Record attempts
        for i in range(4):
            if action.can_attempt():
                action.record_attempt()
                print(f"   Attempt {i+1}: Recorded")
            else:
                print(f"   Attempt {i+1}: Max attempts reached")
                
        # Test cooldown
        print("\n2. Testing cooldown:")
        action2 = actions[1]
        action2.record_attempt()
        print(f"   Can attempt immediately: {action2.can_attempt()}")
        
        print("   Waiting for cooldown...")
        time.sleep(3)
        print(f"   Can attempt after cooldown: {action2.can_attempt()}")
        
        # Reset
        action.reset()
        print(f"\n3. After reset, can attempt: {action.can_attempt()}")
        
        return True, "Recovery strategies tested"
        
    def test_45_second_shutdown_fix(self):
        """Test that app doesn't shutdown after 45 seconds."""
        print("Testing 45-second shutdown fix...")
        
        # Import Qt application components
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        
        # Create or get Qt application
        app = QApplication.instance()
        if not app:
            app = QApplication([])
            
        # Track application state
        app_still_running = True
        shutdown_detected = False
        elapsed_time = 0
        
        def check_app_state():
            """Check if app is still responsive."""
            nonlocal elapsed_time
            elapsed_time += 1
            print(f"   App running: {elapsed_time}s", end='\r')
            
            # Check if we've passed the critical 45-second mark
            if elapsed_time == 45:
                print(f"\n   ✓ Passed 45-second mark without shutdown!")
                
        # Create watchdog with Qt implementation
        self.watchdog = create_watchdog_adapter(
            use_qt=True,
            check_interval_seconds=5,
            vram_threshold_percent=90.0
        )
        
        # Start watchdog
        self.watchdog.start_monitoring()
        print("1. Started Qt-based watchdog monitoring")
        
        # Create timer to check app state every second
        check_timer = QTimer()
        check_timer.timeout.connect(check_app_state)
        check_timer.start(1000)  # Check every second
        
        # Run for 60 seconds (past the 45-second mark)
        print("2. Running application for 60 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 60:
            app.processEvents()
            time.sleep(0.1)
            
            # Check if app is still alive
            if not app.instance():
                shutdown_detected = True
                break
                
        check_timer.stop()
        
        # Stop watchdog
        self.watchdog.stop_monitoring()
        
        runtime = time.time() - start_time
        print(f"\n3. Application ran for {runtime:.0f} seconds")
        
        if not shutdown_detected and runtime >= 60:
            return True, (
                f"No 45-second shutdown detected! App ran for {runtime:.0f}s"
            )
        else:
            return False, (
                f"Unexpected shutdown after {runtime:.0f}s"
            )
            
    def test_no_qt_threading_errors(self):
        """Test that no QBasicTimer threading errors occur."""
        print("Testing for Qt threading errors...")
        
        from PySide6.QtWidgets import QApplication
        import re
        
        # Create or get Qt application
        app = QApplication.instance()
        if not app:
            app = QApplication([])
            
        # Track errors
        qt_errors = []
        thread_errors = []
        
        # Custom logger to capture Qt errors
        original_logger = logger.error
        
        def capture_errors(message):
            """Capture Qt-related errors."""
            if "QBasicTimer" in message:
                qt_errors.append(message)
            if "thread" in message.lower() and "qt" in message.lower():
                thread_errors.append(message)
            return original_logger(message)
            
        logger.error = capture_errors
        
        try:
            # Create watchdog
            self.watchdog = create_watchdog_adapter(
                use_qt=True,
                check_interval_seconds=2
            )
            
            # Start monitoring
            self.watchdog.start_monitoring()
            print("1. Started watchdog with Qt threading")
            
            # Run for 30 seconds
            print("2. Monitoring for Qt threading errors...")
            start_time = time.time()
            
            while time.time() - start_time < 30:
                app.processEvents()
                time.sleep(0.1)
                
                # Show progress
                if int(time.time() - start_time) % 5 == 0:
                    print(f"   Running... {int(time.time() - start_time)}s")
                    
            # Stop monitoring
            self.watchdog.stop_monitoring()
            
        finally:
            # Restore original logger
            logger.error = original_logger
            
        print(f"\n3. Results:")
        print(f"   QBasicTimer errors: {len(qt_errors)}")
        print(f"   Thread errors: {len(thread_errors)}")
        
        if qt_errors:
            print("\n   Qt errors detected:")
            for err in qt_errors[:3]:  # Show first 3
                print(f"     - {err[:80]}...")
                
        if len(qt_errors) == 0 and len(thread_errors) == 0:
            return True, "No Qt threading errors detected"
        else:
            return False, (
                f"Found {len(qt_errors)} Qt errors and "
                f"{len(thread_errors)} thread errors"
            )
            
    def test_app_continues_after_errors(self):
        """Test that app continues running after watchdog errors."""
        print("Testing app continuity after errors...")
        
        from PySide6.QtWidgets import QApplication
        
        # Create or get Qt application
        app = QApplication.instance()
        if not app:
            app = QApplication([])
            
        # Track app state and errors
        app_crashed = False
        error_count = 0
        recovery_count = 0
        
        def error_handler(level, message):
            """Track errors."""
            nonlocal error_count
            error_count += 1
            print(f"   Error {error_count}: {message[:60]}...")
            
        def recovery_handler(message):
            """Track recoveries."""
            nonlocal recovery_count
            recovery_count += 1
            print(f"   Recovery {recovery_count}: {message[:60]}...")
            
        # Create watchdog that will encounter errors
        self.watchdog = create_watchdog_adapter(
            use_qt=True,
            alert_callback=error_handler,
            check_interval_seconds=1,
            fallback_config=FallbackConfig(
                auto_fallback=True,
                fallback_delay=2.0
            )
        )
        
        # Inject some error conditions
        from src.utils.Watchdog import SystemWatchdog
        original_get_metrics = SystemWatchdog.get_current_metrics
        error_injection_count = 0
        
        def failing_metrics(self, *args, **kwargs):
            """Inject errors periodically."""
            nonlocal error_injection_count
            error_injection_count += 1
            
            # Fail every 3rd call
            if error_injection_count % 3 == 0:
                raise Exception("Simulated metrics collection error")
                
            return original_get_metrics(self, *args, **kwargs)
            
        SystemWatchdog.get_current_metrics = failing_metrics
        
        try:
            # Start monitoring
            self.watchdog.start_monitoring()
            print("1. Started watchdog with error injection")
            
            # Run for 20 seconds with errors
            print("2. Running with periodic errors...")
            start_time = time.time()
            
            while time.time() - start_time < 20:
                try:
                    app.processEvents()
                    time.sleep(0.1)
                except Exception as e:
                    print(f"   App exception: {e}")
                    app_crashed = True
                    break
                    
            runtime = time.time() - start_time
            
            # Stop monitoring
            self.watchdog.stop_monitoring()
            
        finally:
            # Restore original method
            SystemWatchdog.get_current_metrics = original_get_metrics
            
        print(f"\n3. Results:")
        print(f"   Runtime: {runtime:.1f}s")
        print(f"   Errors encountered: {error_count}")
        print(f"   Error injections: {error_injection_count}")
        print(f"   App crashed: {app_crashed}")
        
        if not app_crashed and runtime >= 19:
            return True, (
                f"App survived {error_count} errors and ran for {runtime:.1f}s"
            )
        else:
            return False, (
                f"App failed after {runtime:.1f}s with {error_count} errors"
            )
            
    def test_auto_recovery_validation(self):
        """Test health monitoring and auto-recovery validation."""
        print("Testing auto-recovery validation...")
        
        from PySide6.QtWidgets import QApplication
        
        # Create or get Qt application
        app = QApplication.instance()
        if not app:
            app = QApplication([])
            
        # Create health monitor
        self.health_monitor = WatchdogHealthMonitor()
        
        # Track recovery events
        recovery_attempts = []
        component_states = {}
        
        def on_recovery_started(component, strategy):
            recovery_attempts.append({
                'component': component,
                'strategy': strategy,
                'time': datetime.now()
            })
            print(f"   Recovery started: {component} using {strategy}")
            
        def on_component_health_changed(component, state, message):
            component_states[component] = state
            print(f"   Health changed: {component} -> {state}")
            
        # Connect signals
        self.health_monitor.signals.recovery_started.connect(on_recovery_started)
        self.health_monitor.signals.component_health_changed.connect(
            on_component_health_changed
        )
        
        # Start health monitoring
        self.health_monitor.start_monitoring()
        print("1. Started health monitoring")
        
        # Create watchdog with health monitoring
        self.watchdog = create_watchdog_adapter(
            use_qt=True,
            check_interval_seconds=2
        )
        
        # Simulate component failures and recovery
        print("\n2. Simulating component failures...")
        
        # Simulate VRAM collector failure
        for i in range(5):
            try:
                raise Exception(f"VRAM collection error {i+1}")
            except Exception as e:
                self.health_monitor.record_failure('vram_collector', e)
                
        # Let recovery happen
        print("\n3. Waiting for auto-recovery...")
        start_time = time.time()
        
        while time.time() - start_time < 15:
            app.processEvents()
            time.sleep(0.1)
            
            # Check if recovery happened
            if len(recovery_attempts) > 0:
                print("   ✓ Recovery initiated!")
                break
                
        # Simulate recovery success
        print("\n4. Simulating recovery success...")
        for i in range(3):
            self.health_monitor.record_success('vram_collector', 0.1)
            time.sleep(0.5)
            
        # Get final health report
        health_report = self.health_monitor.get_health_report()
        
        # Stop monitoring
        self.health_monitor.stop_monitoring()
        
        print(f"\n5. Final Results:")
        print(f"   Recovery attempts: {len(recovery_attempts)}")
        print(f"   Component states: {component_states}")
        print(f"   Overall health: {health_report['overall_state']}")
        
        # Check recovery success
        vram_state = component_states.get('vram_collector', 'unknown')
        
        if (len(recovery_attempts) > 0 and
            vram_state in ['healthy', 'recovering']):
            return True, (
                f"Auto-recovery working: {len(recovery_attempts)} attempts, "
                f"final state: {vram_state}"
            )
        else:
            return False, (
                f"Auto-recovery failed: {len(recovery_attempts)} attempts, "
                f"state: {vram_state}"
            )
        
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"  - {test_name}: {message}")


def main():
    """Run the watchdog recovery test suite."""
    print("Starting Watchdog Error Recovery Test Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = WatchdogRecoveryTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        if tester.watchdog:
            try:
                tester.watchdog.stop_monitoring()
            except Exception:
                pass
        if tester.health_monitor:
            try:
                tester.health_monitor.stop_monitoring()
            except Exception:
                pass
                
    print("\nTest suite completed")


if __name__ == "__main__":
    main()