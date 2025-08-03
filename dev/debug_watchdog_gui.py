#!/usr/bin/env python3
"""Debug watchdog behavior when GUI is running"""

import sys
import time
import psutil
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.Watchdog import SystemWatchdog, AlertLevel
from src.utils.config_loader import ConfigLoader


def debug_process_detection():
    """Debug how the watchdog detects processes"""
    print("=== PROCESS DETECTION DEBUG ===")
    
    # Show current process info
    current_pid = os.getpid()
    current_proc = psutil.Process(current_pid)
    
    print(f"\n1. Current process:")
    print(f"   - PID: {current_pid}")
    print(f"   - Name: {current_proc.name()}")
    print(f"   - Cmdline: {' '.join(current_proc.cmdline())}")
    
    # Check all Python processes
    print(f"\n2. All Python processes:")
    python_count = 0
    dinoair_like = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            info = proc.info
            name = info.get('name', '').lower()
            cmdline_raw = info.get('cmdline')
            
            if cmdline_raw is None or not cmdline_raw:
                cmdline = ''
            else:
                cmdline_parts = [str(item) for item in cmdline_raw if item is not None]
                cmdline = ' '.join(cmdline_parts).lower()
            
            # Check if it's a Python process
            if 'python' in name:
                python_count += 1
                
                # Check if it looks like DinoAir
                if ('dinoair' in cmdline or 'main.py' in cmdline):
                    dinoair_like.append({
                        'pid': info['pid'],
                        'name': name,
                        'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                    })
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print(f"   - Total Python processes: {python_count}")
    print(f"   - Processes that look like DinoAir: {len(dinoair_like)}")
    
    for i, proc in enumerate(dinoair_like):
        print(f"\n   Process {i+1}:")
        print(f"     - PID: {proc['pid']}")
        print(f"     - Name: {proc['name']}")
        print(f"     - Cmdline: {proc['cmdline']}")


def simulate_watchdog_with_gui():
    """Simulate what happens when watchdog runs with GUI"""
    print("\n\n=== WATCHDOG SIMULATION WITH GUI ===")
    
    config = ConfigLoader()
    
    # Track what happens
    events = []
    shutdown_triggered = False
    
    def track_alert(level: AlertLevel, message: str):
        """Track all alerts"""
        events.append(f"ALERT[{level.value}]: {message}")
        print(f"\n🚨 {level.value.upper()}: {message}")
        
    def track_metrics(metrics):
        """Track metrics"""
        if metrics.dinoair_processes > 0:
            events.append(f"METRICS: {metrics.dinoair_processes} DinoAir processes")
    
    # Create watchdog with actual config
    watchdog = SystemWatchdog(
        alert_callback=track_alert,
        metrics_callback=track_metrics,
        vram_threshold_percent=config.get("watchdog.vram_threshold_percent", 80.0),
        max_dinoair_processes=config.get("watchdog.max_dinoair_processes", 5),
        check_interval_seconds=2,  # Faster for testing
        self_terminate_on_critical=config.get("watchdog.self_terminate_on_critical", False)
    )
    
    print("\nStarting simulation (10 seconds)...")
    print(f"Config: max_processes={watchdog.max_processes}, self_terminate={watchdog.self_terminate_on_critical}")
    
    # Start monitoring
    watchdog.start_monitoring()
    
    # Run for 10 seconds
    start_time = time.time()
    while time.time() - start_time < 10:
        time.sleep(1)
        
    # Stop monitoring
    watchdog.stop_monitoring()
    
    print("\n\nEvents summary:")
    for event in events:
        print(f"  - {event}")
    
    if not events:
        print("  - No events triggered")


def check_watchdog_restart_issue():
    """Check if the watchdog restart logic has issues"""
    print("\n\n=== WATCHDOG START/RESTART DEBUG ===")
    
    # Look at the main window restart logic
    print("The watchdog restart logic in main_window.py:")
    print("1. _stop_watchdog() is called")
    print("2. QTimer.singleShot(100, self._start_watchdog) - 100ms delay")
    print("3. _start_watchdog() creates new watchdog if needed")
    print("\nPotential issue: If the watchdog detects too many processes")
    print("immediately on start, it might trigger shutdown before the")
    print("GUI has time to stabilize.")


if __name__ == "__main__":
    debug_process_detection()
    simulate_watchdog_with_gui()
    check_watchdog_restart_issue()