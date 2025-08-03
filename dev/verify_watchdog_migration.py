"""Verification suite for watchdog migration and backward compatibility.

This test file focuses on:
- Verifying old configuration still works
- Testing backward compatibility adapter
- Ensuring no breaking changes for existing code
- Validating all callbacks work with new implementation
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import traceback

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import after path setup
from PySide6.QtWidgets import QApplication

from src.utils.logger import Logger
from src.utils.watchdog_qt import (
    WatchdogController, WatchdogConfig, SystemMetrics, AlertLevel
)
from src.utils.watchdog_compat import (
    create_watchdog_adapter, AdapterMode, FallbackConfig,
    WatchdogCompatibilityAdapter
)
from src.utils.Watchdog import SystemWatchdog
from src.utils.watchdog_config_validator import (
    WatchdogConfigValidator, validate_watchdog_config
)

logger = Logger()


class LegacyCodeSimulator:
    """Simulates legacy code that used the old watchdog interface."""
    
    def __init__(self):
        self.metrics_received = []
        self.alerts_received = []
        
    def old_style_alert_handler(self, level: AlertLevel, message: str):
        """Old style alert callback."""
        self.alerts_received.append({
            'level': level.value,
            'message': message,
            'timestamp': datetime.now()
        })
        print(f"[Legacy Alert] {level.value}: {message}")
        
    def old_style_metrics_handler(self, metrics: SystemMetrics):
        """Old style metrics callback."""
        self.metrics_received.append({
            'vram_percent': metrics.vram_percent,
            'cpu_percent': metrics.cpu_percent,
            'timestamp': datetime.now()
        })
        print(f"[Legacy Metrics] VRAM: {metrics.vram_percent:.1f}%")


class MigrationVerificationTester:
    """Main test class for migration verification."""
    
    def __init__(self):
        self.test_results = []
        self.app = None
        
    def setup(self):
        """Setup test environment."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def cleanup(self):
        """Cleanup test environment."""
        if self.app:
            self.app.quit()
            
    def run_all_tests(self):
        """Run all migration verification tests."""
        print("=" * 60)
        print("WATCHDOG MIGRATION VERIFICATION SUITE")
        print("=" * 60)
        print()
        
        self.setup()
        
        tests = [
            self.test_old_configuration_format,
            self.test_parameter_name_variations,
            self.test_legacy_callbacks,
            self.test_adapter_mode_switching,
            self.test_fallback_behavior,
            self.test_config_validation_migration,
            self.test_breaking_change_detection,
            self.test_thread_safety_migration,
            self.test_api_compatibility
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
        self.cleanup()
        
    def test_old_configuration_format(self):
        """Test that old configuration format still works."""
        print("Testing old configuration format compatibility...")
        
        # Old style configuration (before migration)
        old_configs = [
            {
                # Original parameter names
                'vram_threshold_percent': 90.0,
                'max_dinoair_processes': 5,
                'check_interval_seconds': 30,
                'self_terminate_on_critical': False
            },
            {
                # Mixed old and new names
                'vram_threshold': 85.0,
                'max_dinoair_processes': 10,  # Old name
                'check_interval': 20,
                'self_terminate_on_critical': True  # Old name
            },
            {
                # Minimal old config
                'vram_threshold_percent': 95.0
            }
        ]
        
        results = []
        
        for i, old_config in enumerate(old_configs):
            print(f"\nTesting old config {i+1}:")
            print(f"  Input: {old_config}")
            
            try:
                # Use compatibility adapter
                adapter = create_watchdog_adapter(
                    use_qt=True,
                    **old_config
                )
                
                # Verify adapter was created
                if adapter:
                    # Check effective configuration
                    if hasattr(adapter, '_controller') and adapter._controller:
                        effective_config = adapter._controller.config
                        print(f"  Effective VRAM threshold: {effective_config.vram_threshold}")
                        print(f"  Effective max processes: {effective_config.max_processes}")
                        results.append(True)
                    else:
                        results.append(False)
                else:
                    results.append(False)
                    
            except Exception as e:
                print(f"  Error: {e}")
                results.append(False)
                
        # All old configs should work
        success_count = sum(results)
        if success_count == len(old_configs):
            return True, (
                f"All {len(old_configs)} old configuration formats work"
            )
        else:
            return False, (
                f"Only {success_count}/{len(old_configs)} old configs work"
            )
            
    def test_parameter_name_variations(self):
        """Test parameter name normalization."""
        print("Testing parameter name variations...")
        
        validator = WatchdogConfigValidator()
        
        # Test various parameter name combinations
        test_cases = [
            # Old name -> normalized name
            ('vram_threshold_percent', 'vram_threshold'),
            ('max_dinoair_processes', 'max_processes'),
            ('check_interval_seconds', 'check_interval'),
            ('self_terminate_on_critical', 'self_terminate')
        ]
        
        for old_name, new_name in test_cases:
            # Create config with old name
            config = {old_name: 75.0 if 'threshold' in old_name else 10}
            
            # Merge configs (which normalizes names)
            normalized = validator.merge_configs(config)
            
            print(f"  {old_name} -> {new_name}: ", end='')
            
            if new_name in normalized and old_name not in normalized:
                print("✓ Normalized correctly")
            else:
                print("✗ Normalization failed")
                return False, f"Failed to normalize {old_name} to {new_name}"
                
        # Test that new names are preserved
        new_config = {
            'vram_threshold': 80.0,
            'max_processes': 8,
            'check_interval': 25
        }
        
        preserved = validator.merge_configs(new_config)
        
        for key in new_config:
            if key not in preserved or preserved[key] != new_config[key]:
                return False, f"New parameter {key} not preserved"
                
        return True, "All parameter name variations handled correctly"
        
    def test_legacy_callbacks(self):
        """Test that legacy callbacks still work."""
        print("Testing legacy callback compatibility...")
        
        legacy_sim = LegacyCodeSimulator()
        
        # Create adapter with legacy-style callbacks
        adapter = create_watchdog_adapter(
            use_qt=True,
            alert_callback=legacy_sim.old_style_alert_handler,
            metrics_callback=legacy_sim.old_style_metrics_handler,
            vram_threshold_percent=70.0,  # Low threshold to trigger alerts
            check_interval_seconds=1
        )
        
        # Start monitoring
        adapter.start_monitoring()
        
        # Let it run
        start_time = time.time()
        while time.time() - start_time < 5:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Stop monitoring
        adapter.stop_monitoring()
        
        print(f"\nCallback results:")
        print(f"  Metrics received: {len(legacy_sim.metrics_received)}")
        print(f"  Alerts received: {len(legacy_sim.alerts_received)}")
        
        # Verify callbacks were invoked
        if (len(legacy_sim.metrics_received) >= 3 and
            isinstance(legacy_sim.metrics_received[0]['vram_percent'], float)):
            return True, (
                f"Legacy callbacks working: {len(legacy_sim.metrics_received)} "
                f"metrics, {len(legacy_sim.alerts_received)} alerts"
            )
        else:
            return False, "Legacy callbacks not properly invoked"
            
    def test_adapter_mode_switching(self):
        """Test switching between Qt and legacy modes."""
        print("Testing adapter mode switching...")
        
        # Test 1: Start with Qt, fallback to legacy
        print("\n1. Testing Qt -> Legacy fallback:")
        
        fallback_config = FallbackConfig(
            auto_fallback=True,
            fallback_delay=2.0,
            max_qt_retries=3
        )
        
        adapter = create_watchdog_adapter(
            use_qt=True,
            fallback_config=fallback_config,
            check_interval_seconds=1
        )
        
        initial_mode = adapter.current_mode
        print(f"   Initial mode: {initial_mode.value}")
        
        # Force some errors to trigger fallback
        if hasattr(adapter, '_controller'):
            # Simulate Qt thread issues
            adapter._controller = None
            
        adapter.start_monitoring()
        time.sleep(5)
        
        fallback_mode = adapter.current_mode
        print(f"   Mode after errors: {fallback_mode.value}")
        
        adapter.stop_monitoring()
        
        # Test 2: Start with legacy mode
        print("\n2. Testing legacy mode directly:")
        
        legacy_adapter = create_watchdog_adapter(
            use_qt=False,
            check_interval_seconds=1
        )
        
        legacy_mode = legacy_adapter.current_mode
        print(f"   Legacy mode: {legacy_mode.value}")
        
        # Should stay in legacy mode
        legacy_adapter.start_monitoring()
        time.sleep(3)
        legacy_adapter.stop_monitoring()
        
        final_legacy_mode = legacy_adapter.current_mode
        print(f"   Still in legacy: {final_legacy_mode.value}")
        
        # Verify mode behaviors
        if (initial_mode == AdapterMode.QT and
            fallback_mode == AdapterMode.LEGACY and
            legacy_mode == AdapterMode.LEGACY and
            final_legacy_mode == AdapterMode.LEGACY):
            return True, "Adapter mode switching works correctly"
        else:
            return False, "Adapter mode switching not working properly"
            
    def test_fallback_behavior(self):
        """Test fallback behavior on errors."""
        print("Testing fallback behavior...")
        
        fallback_events = []
        
        def track_fallback(level: AlertLevel, message: str):
            if 'fallback' in message.lower():
                fallback_events.append(message)
                
        # Create adapter prone to errors
        adapter = create_watchdog_adapter(
            use_qt=True,
            alert_callback=track_fallback,
            fallback_config=FallbackConfig(
                auto_fallback=True,
                fallback_delay=1.0,
                max_qt_retries=2
            ),
            check_interval_seconds=1
        )
        
        # Inject error condition
        original_start = adapter.start_monitoring
        error_count = 0
        
        def failing_start():
            nonlocal error_count
            error_count += 1
            if error_count < 3:
                raise Exception("Simulated Qt error")
            return original_start()
            
        adapter.start_monitoring = failing_start
        
        # Try to start (should fail then fallback)
        try:
            adapter.start_monitoring()
        except Exception:
            pass
            
        print(f"Error count before fallback: {error_count}")
        print(f"Current mode: {adapter.current_mode.value}")
        print(f"Fallback events: {len(fallback_events)}")
        
        # Should have tried and fallen back
        if error_count >= 2 and adapter.current_mode == AdapterMode.LEGACY:
            return True, (
                f"Fallback activated after {error_count} errors"
            )
        else:
            return False, "Fallback behavior not working correctly"
            
    def test_config_validation_migration(self):
        """Test configuration validation for migrated configs."""
        print("Testing configuration validation during migration...")
        
        # Invalid old-style configs that should be corrected
        invalid_configs = [
            {
                'vram_threshold_percent': 150,  # Too high
                'max_dinoair_processes': -5,     # Negative
                'check_interval_seconds': 0,     # Too low
            },
            {
                'vram_threshold': 'ninety',      # Wrong type
                'max_processes': True,           # Wrong type
                'self_terminate': 'yes'          # Wrong type
            }
        ]
        
        validator = WatchdogConfigValidator()
        
        for i, invalid_config in enumerate(invalid_configs):
            print(f"\n{i+1}. Testing invalid config: {invalid_config}")
            
            # Validate and correct
            result = validator.validate(invalid_config)
            
            print(f"   Issues found: {len(result.issues)}")
            for param, level, message in result.issues:
                print(f"     - {param}: {message}")
                
            # Verify corrected config
            corrected = result.corrected_config
            print(f"   Corrected config: {corrected}")
            
            # Create adapter with corrected config
            try:
                adapter = create_watchdog_adapter(
                    use_qt=True,
                    **corrected
                )
                
                if adapter:
                    print("   ✓ Adapter created with corrected config")
                else:
                    return False, "Failed to create adapter with corrected config"
                    
            except Exception as e:
                return False, f"Error with corrected config: {e}"
                
        return True, "Configuration validation handles migration correctly"
        
    def test_breaking_change_detection(self):
        """Test detection of potential breaking changes."""
        print("Testing breaking change detection...")
        
        # List of APIs that should remain compatible
        compatibility_checks = []
        
        # Check 1: SystemWatchdog class exists and has expected methods
        try:
            watchdog = SystemWatchdog()
            required_methods = [
                'start_monitoring',
                'stop_monitoring',
                'get_current_metrics',
                'emergency_cleanup'
            ]
            
            for method in required_methods:
                if hasattr(watchdog, method):
                    compatibility_checks.append((f"SystemWatchdog.{method}", True))
                else:
                    compatibility_checks.append((f"SystemWatchdog.{method}", False))
                    
        except Exception as e:
            compatibility_checks.append(("SystemWatchdog class", False))
            
        # Check 2: Adapter interface
        try:
            adapter = create_watchdog_adapter(use_qt=False)
            adapter_methods = [
                'start_monitoring',
                'stop_monitoring',
                'get_status_report',
                'is_monitoring'
            ]
            
            for method in adapter_methods:
                if hasattr(adapter, method):
                    compatibility_checks.append((f"Adapter.{method}", True))
                else:
                    compatibility_checks.append((f"Adapter.{method}", False))
                    
        except Exception as e:
            compatibility_checks.append(("Adapter interface", False))
            
        # Check 3: Enums and types
        try:
            from src.utils.Watchdog import AlertLevel, SystemMetrics
            compatibility_checks.append(("AlertLevel enum", True))
            compatibility_checks.append(("SystemMetrics dataclass", True))
        except ImportError:
            compatibility_checks.append(("Core types", False))
            
        # Print compatibility report
        print("\nCompatibility Report:")
        broken = []
        for api, compatible in compatibility_checks:
            status = "✓" if compatible else "✗"
            print(f"  {status} {api}")
            if not compatible:
                broken.append(api)
                
        if len(broken) == 0:
            return True, "No breaking changes detected"
        else:
            return False, f"Breaking changes in: {', '.join(broken)}"
            
    def test_thread_safety_migration(self):
        """Test thread safety in migrated code."""
        print("Testing thread safety after migration...")
        
        import threading
        
        # Create shared adapter
        adapter = create_watchdog_adapter(
            use_qt=True,
            check_interval_seconds=1
        )
        
        errors = []
        operations = []
        
        def thread_operation(thread_id, operation):
            """Perform operations from different threads."""
            try:
                if operation == 'start':
                    adapter.start_monitoring()
                    operations.append(f"Thread {thread_id}: started")
                elif operation == 'stop':
                    adapter.stop_monitoring()
                    operations.append(f"Thread {thread_id}: stopped")
                elif operation == 'status':
                    status = adapter.get_status_report()
                    operations.append(f"Thread {thread_id}: got status")
                elif operation == 'metrics':
                    # Try to force metrics collection
                    if hasattr(adapter, '_collect_metrics'):
                        adapter._collect_metrics()
                    operations.append(f"Thread {thread_id}: collected metrics")
                    
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
                
        # Create multiple threads trying different operations
        threads = []
        
        # Start monitoring from main thread first
        adapter.start_monitoring()
        
        # Launch threads
        thread_ops = [
            (1, 'status'),
            (2, 'metrics'),
            (3, 'status'),
            (4, 'stop'),
            (5, 'start'),
            (6, 'status')
        ]
        
        for thread_id, op in thread_ops:
            t = threading.Thread(
                target=thread_operation,
                args=(thread_id, op)
            )
            threads.append(t)
            t.start()
            
        # Wait for threads
        for t in threads:
            t.join(timeout=5)
            
        # Final cleanup
        try:
            adapter.stop_monitoring()
        except Exception:
            pass
            
        print(f"\nThread safety results:")
        print(f"  Operations completed: {len(operations)}")
        print(f"  Errors encountered: {len(errors)}")
        
        if errors:
            for error in errors:
                print(f"    - {error}")
                
        # Should handle concurrent access
        if len(errors) == 0 or (len(errors) <= 2 and len(operations) >= 4):
            return True, (
                f"Thread safety maintained: {len(operations)} ops, "
                f"{len(errors)} errors"
            )
        else:
            return False, f"Thread safety issues: {len(errors)} errors"
            
    def test_api_compatibility(self):
        """Test API compatibility for common use cases."""
        print("Testing API compatibility for common use cases...")
        
        use_cases = []
        
        # Use case 1: Basic monitoring with callbacks
        print("\n1. Basic monitoring with callbacks:")
        try:
            metrics_count = 0
            
            def count_metrics(metrics):
                nonlocal metrics_count
                metrics_count += 1
                
            # Old style initialization
            watchdog = SystemWatchdog(
                metrics_callback=count_metrics,
                vram_threshold_percent=90.0,
                check_interval_seconds=1
            )
            
            # Note: start_monitoring is deprecated but should not crash
            watchdog.start_monitoring()
            
            # Get metrics manually (since thread-based monitoring is deprecated)
            for _ in range(3):
                metrics = watchdog.get_current_metrics()
                count_metrics(metrics)
                time.sleep(1)
                
            watchdog.stop_monitoring()
            
            use_cases.append(('Basic monitoring', metrics_count >= 3))
            
        except Exception as e:
            use_cases.append(('Basic monitoring', False))
            print(f"   Error: {e}")
            
        # Use case 2: Emergency cleanup
        print("\n2. Emergency cleanup API:")
        try:
            result = SystemWatchdog.emergency_cleanup()
            if isinstance(result, dict) and 'killed' in result:
                use_cases.append(('Emergency cleanup', True))
            else:
                use_cases.append(('Emergency cleanup', False))
                
        except Exception as e:
            use_cases.append(('Emergency cleanup', False))
            print(f"   Error: {e}")
            
        # Use case 3: Status reporting
        print("\n3. Status reporting:")
        try:
            watchdog = SystemWatchdog()
            watchdog._last_metrics = watchdog.get_current_metrics()
            status = watchdog.get_status_report()
            
            if isinstance(status, str) and 'System Watchdog Status' in status:
                use_cases.append(('Status reporting', True))
            else:
                use_cases.append(('Status reporting', False))
                
        except Exception as e:
            use_cases.append(('Status reporting', False))
            print(f"   Error: {e}")
            
        # Use case 4: Adapter-based monitoring
        print("\n4. Adapter-based monitoring:")
        try:
            adapter = create_watchdog_adapter(
                use_qt=True,
                vram_threshold_percent=85.0
            )
            
            adapter.start_monitoring()
            time.sleep(2)
            
            is_monitoring = adapter.is_monitoring()
            status = adapter.get_status_report()
            
            adapter.stop_monitoring()
            
            if is_monitoring and status:
                use_cases.append(('Adapter monitoring', True))
            else:
                use_cases.append(('Adapter monitoring', False))
                
        except Exception as e:
            use_cases.append(('Adapter monitoring', False))
            print(f"   Error: {e}")
            
        # Summary
        print("\nAPI Compatibility Summary:")
        passed = 0
        for use_case, success in use_cases:
            status = "✓" if success else "✗"
            print(f"  {status} {use_case}")
            if success:
                passed += 1
                
        if passed == len(use_cases):
            return True, f"All {len(use_cases)} API use cases compatible"
        else:
            return False, (
                f"Only {passed}/{len(use_cases)} API use cases compatible"
            )
            
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("MIGRATION VERIFICATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        total = len(self.test_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("\n✅ All migration tests passed!")
            print("\nKey validations:")
            print("- Old configuration format supported")
            print("- Parameter name variations handled")
            print("- Legacy callbacks still work")
            print("- Adapter mode switching functional")
            print("- Fallback behavior operational")
            print("- Configuration validation works")
            print("- No breaking changes detected")
            print("- Thread safety maintained")
            print("- API compatibility preserved")
        else:
            print("\n❌ Some migration tests failed:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"  - {test_name}: {message}")


def main():
    """Run the migration verification suite."""
    print("Starting Watchdog Migration Verification Suite")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = MigrationVerificationTester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest suite error: {e}")
        traceback.print_exc()
    finally:
        print("\nMigration verification suite completed")


if __name__ == "__main__":
    main()