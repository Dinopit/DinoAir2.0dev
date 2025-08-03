#!/usr/bin/env python3
"""Test demonstration script for Watchdog commands in DinoAir InputSanitizer.

This script demonstrates all watchdog commands available through the chat
interface, showing proper usage, expected responses, and error handling.

Run this to see how the watchdog integration works with natural language
commands in the chat interface.
"""

import sys
import os
import sqlite3
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import necessary modules
from src.input_processing.input_sanitizer import InputPipeline
from src.utils.Watchdog import SystemWatchdog, AlertLevel
from src.models.watchdog_metrics import WatchdogMetric, WatchdogMetricsManager


class MockMainWindow:
    """Mock main window for testing watchdog commands."""
    
    def __init__(self):
        self.watchdog = SystemWatchdog(
            alert_callback=self._alert_callback,
            vram_threshold_percent=80.0,
            max_dinoair_processes=5,
            check_interval_seconds=30,
            self_terminate_on_critical=False
        )
        self.app_instance = self
        self.metrics_manager = None  # Will be set in _setup_metrics_db
        self._setup_metrics_db()
        
    def _alert_callback(self, level: AlertLevel, message: str):
        """Mock alert callback."""
        print(f"[ALERT] {level.value.upper()}: {message}")
        
    def _setup_metrics_db(self):
        """Setup mock metrics database."""
        # Create in-memory database for testing
        self.db_conn = sqlite3.connect(':memory:')
        cursor = self.db_conn.cursor()
        
        # Create metrics table
        cursor.execute('''
            CREATE TABLE watchdog_metrics (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                vram_used_mb REAL,
                vram_total_mb REAL,
                vram_percent REAL,
                cpu_percent REAL,
                ram_used_mb REAL,
                ram_percent REAL,
                process_count INTEGER,
                dinoair_processes INTEGER,
                uptime_seconds INTEGER
            )
        ''')
        self.db_conn.commit()
        
        # Initialize metrics manager
        self.metrics_manager = WatchdogMetricsManager(self.db_conn)
        
        # Add some sample metrics for history
        self._generate_sample_metrics()
        
    def _generate_sample_metrics(self):
        """Generate sample metrics for testing history commands."""
        now = datetime.now()
        
        # Generate 48 hours of sample data (every 30 minutes)
        for hours_ago in range(48, 0, -1):
            for minutes in [0, 30]:
                timestamp = now - timedelta(hours=hours_ago, minutes=minutes)
                
                # Create varied but realistic metrics
                metric = WatchdogMetric(
                    id=f"test-{hours_ago}-{minutes}",
                    timestamp=timestamp.isoformat(),
                    vram_used_mb=2000 + (hours_ago * 10) % 500,
                    vram_total_mb=8192,
                    vram_percent=25 + (hours_ago * 2) % 30,
                    cpu_percent=20 + (hours_ago * 3) % 40,
                    ram_used_mb=8000 + (hours_ago * 100) % 4000,
                    ram_percent=50 + (hours_ago * 2) % 25,
                    process_count=150 + hours_ago % 50,
                    dinoair_processes=2 + hours_ago % 3,
                    uptime_seconds=hours_ago * 3600
                )
                
                if self.metrics_manager:
                    self.metrics_manager.insert_metric(metric)
        
    def handle_watchdog_control(self, action: str):
        """Mock watchdog control handler."""
        print(f"[MAIN WINDOW] Watchdog control: {action}")
        if action == 'start':
            self.watchdog.start_monitoring()
        elif action == 'stop':
            self.watchdog.stop_monitoring()
        elif action == 'restart':
            self.watchdog.stop_monitoring()
            self.watchdog.start_monitoring()
            
    def handle_watchdog_config_change(self, config: dict):
        """Mock config change handler."""
        print(f"[MAIN WINDOW] Config change: {config}")
        for key, value in config.items():
            if key == 'vram_threshold_percent':
                self.watchdog.vram_threshold = value
            elif key == 'max_dinoair_processes':
                self.watchdog.max_processes = value
            elif key == 'check_interval_seconds':
                self.watchdog.check_interval = value
            elif key == 'self_terminate_on_critical':
                self.watchdog.self_terminate_on_critical = value


def test_gui_feedback(message: str):
    """Mock GUI feedback function."""
    print(f"[GUI FEEDBACK] {message}")


def run_command_test(pipeline: InputPipeline, command: str, description: str, delay: float = 0.2):
    """Run a single command test and display results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"COMMAND: {command}")
    print("-" * 60)
    
    try:
        result, intent = pipeline.run(command)
        print(f"INTENT: {intent.name}")
        print(f"RESULT:\n{result}")
    except Exception as e:
        print(f"ERROR: {e}")
    
    print("=" * 60)
    
    # Add delay to avoid rate limiting
    time.sleep(delay)


def main():
    """Run comprehensive watchdog command tests."""
    print("🐕 DinoAir Watchdog Command Test Suite")
    print("=====================================")
    print("This demonstrates all watchdog commands available in the "
          "chat interface.\n")
    
    # Setup mock environment
    mock_window = MockMainWindow()
    
    # Create input pipeline with watchdog references
    pipeline = InputPipeline(
        gui_feedback_hook=test_gui_feedback,
        skip_empty_feedback=True,
        model_type="default",
        cooldown_seconds=0,  # Disable rate limiting for testing
        watchdog_ref=mock_window.watchdog,
        main_window_ref=mock_window
    )
    
    # Test 1: Help command
    run_command_test(
        pipeline,
        "watchdog help",
        "Show watchdog help and available commands"
    )
    
    # Test 2: Status command (before starting)
    run_command_test(
        pipeline,
        "watchdog status",
        "Check watchdog status (not started yet)"
    )
    
    # Test 3: Start watchdog
    run_command_test(
        pipeline,
        "watchdog start",
        "Start watchdog monitoring"
    )
    
    # Test 4: Status command (after starting)
    run_command_test(
        pipeline,
        "watchdog status",
        "Check watchdog status (after starting)"
    )
    
    # Test 5: Current metrics
    run_command_test(
        pipeline,
        "watchdog metrics",
        "Show current system metrics"
    )
    
    # Test 6: Configuration display
    run_command_test(
        pipeline,
        "watchdog config",
        "Show current watchdog configuration"
    )
    
    # Test 7: Metrics history (default 24 hours)
    run_command_test(
        pipeline,
        "watchdog history",
        "Show metrics history (default 24 hours)"
    )
    
    # Test 8: Metrics history (custom period)
    run_command_test(
        pipeline,
        "watchdog history 48",
        "Show metrics history (48 hours)"
    )
    
    # Test 9: Set configuration value
    run_command_test(
        pipeline,
        "watchdog set vram_threshold 90",
        "Update VRAM threshold to 90%"
    )
    
    # Test 10: Invalid set command
    run_command_test(
        pipeline,
        "watchdog set invalid_setting 100",
        "Try to set invalid configuration"
    )
    
    # Test 11: Recent alerts (empty)
    run_command_test(
        pipeline,
        "watchdog alerts",
        "Show recent alerts (none recorded yet)"
    )
    
    # Test 12: Add some alerts for testing
    print("\n[SIMULATING ALERTS...]")
    pipeline.record_watchdog_alert("info", "Test info alert")
    pipeline.record_watchdog_alert("warning", "High memory usage detected")
    pipeline.record_watchdog_alert("critical", "Process limit exceeded!")
    
    # Test 13: Recent alerts (with data)
    run_command_test(
        pipeline,
        "watchdog alerts",
        "Show recent alerts (after adding test alerts)"
    )
    
    # Test 14: Generate report
    run_command_test(
        pipeline,
        "watchdog report",
        "Generate comprehensive watchdog report"
    )
    
    # Test 15: Cleanup command (without confirmation)
    run_command_test(
        pipeline,
        "watchdog cleanup",
        "Emergency cleanup (will ask for confirmation)"
    )
    
    # Test 16: Stop watchdog
    run_command_test(
        pipeline,
        "watchdog stop",
        "Stop watchdog monitoring"
    )
    
    # Test 17: Using alias
    run_command_test(
        pipeline,
        "wd status",
        "Check status using 'wd' alias"
    )
    
    # Test 18: Invalid command
    run_command_test(
        pipeline,
        "watchdog invalid",
        "Try invalid watchdog command"
    )
    
    # Test 19: Command with no arguments
    run_command_test(
        pipeline,
        "watchdog",
        "Watchdog command with no arguments"
    )
    
    # Edge cases and error handling
    print("\n\n🧪 EDGE CASES AND ERROR HANDLING")
    print("=" * 60)
    
    # Test with no watchdog reference
    pipeline_no_watchdog = InputPipeline(
        gui_feedback_hook=test_gui_feedback,
        skip_empty_feedback=True
    )
    
    run_command_test(
        pipeline_no_watchdog,
        "watchdog status",
        "Status command with no watchdog reference"
    )
    
    # Test set command with invalid values
    run_command_test(
        pipeline,
        "watchdog set vram_threshold 150",
        "Set VRAM threshold out of range"
    )
    
    run_command_test(
        pipeline,
        "watchdog set max_processes -5",
        "Set max processes to negative value"
    )
    
    run_command_test(
        pipeline,
        "watchdog set",
        "Set command with no arguments"
    )
    
    # Test intent classification
    print("\n\n🎯 INTENT CLASSIFICATION TESTS")
    print("=" * 60)
    
    test_inputs = [
        "watchdog status please",
        "wd metrics",
        "show me the watchdog status",
        "can you start the watchdog",
        "watchdog help me",
    ]
    
    for test_input in test_inputs:
        try:
            _, intent = pipeline.run(test_input)
            print(f"Input: '{test_input}' → Intent: {intent.name}")
        except Exception as e:
            print(f"Input: '{test_input}' → ERROR: {e}")
        time.sleep(0.1)  # Small delay between tests
    
    print("\n\n✅ Test suite completed!")
    print("All watchdog commands have been demonstrated.")
    
    # Cleanup
    mock_window.watchdog.stop_monitoring()
    mock_window.db_conn.close()


if __name__ == "__main__":
    main()