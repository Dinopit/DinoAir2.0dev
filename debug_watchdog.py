#!/usr/bin/env python3
"""Debug script to understand watchdog behavior"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.Watchdog import SystemWatchdog, AlertLevel
from src.utils.config_loader import ConfigLoader

def debug_watchdog():
    """Debug the watchdog configuration and behavior"""
    print("=== WATCHDOG DEBUG ===")
    
    # Load configuration
    config = ConfigLoader()
    print("\n1. Configuration values:")
    print(f"   - watchdog.enabled: {config.get('watchdog.enabled', True)}")
    print(f"   - vram_threshold_percent: {config.get('watchdog.vram_threshold_percent', 95.0)}")
    print(f"   - max_dinoair_processes: {config.get('watchdog.max_dinoair_processes', 3)}")
    print(f"   - check_interval_seconds: {config.get('watchdog.check_interval_seconds', 30)}")
    print(f"   - self_terminate_on_critical: {config.get('watchdog.self_terminate_on_critical', False)}")
    
    # Create watchdog with debug alert handler
    alerts_triggered = []
    
    def debug_alert_handler(level: AlertLevel, message: str):
        """Capture all alerts for analysis"""
        alerts_triggered.append((level, message))
        print(f"\n🚨 ALERT [{level.value}]: {message}")
    
    def debug_metrics_handler(metrics):
        """Show detailed metrics"""
        print(f"\n📊 METRICS:")
        print(f"   - DinoAir processes: {metrics.dinoair_processes}")
        print(f"   - VRAM: {metrics.vram_percent:.1f}%")
        print(f"   - RAM: {metrics.ram_percent:.1f}%")
        print(f"   - CPU: {metrics.cpu_percent:.1f}%")
    
    # Get config values
    vram_threshold = config.get("watchdog.vram_threshold_percent", 95.0)
    max_processes = config.get("watchdog.max_dinoair_processes", 3)
    check_interval = config.get("watchdog.check_interval_seconds", 30)
    self_terminate = config.get("watchdog.self_terminate_on_critical", False)
    
    print(f"\n2. Creating watchdog with:")
    print(f"   - vram_threshold: {vram_threshold}%")
    print(f"   - max_processes: {max_processes}")
    print(f"   - check_interval: {check_interval}s")
    print(f"   - self_terminate: {self_terminate}")
    
    # Create watchdog
    watchdog = SystemWatchdog(
        alert_callback=debug_alert_handler,
        metrics_callback=debug_metrics_handler,
        vram_threshold_percent=vram_threshold,
        max_dinoair_processes=max_processes,
        check_interval_seconds=5,  # Short interval for debugging
        self_terminate_on_critical=False  # NEVER allow termination in debug
    )
    
    # Get initial metrics
    print("\n3. Initial system state:")
    metrics = watchdog.get_current_metrics()
    print(f"   - Current DinoAir processes: {metrics.dinoair_processes}")
    print(f"   - Process detection will trigger CRITICAL if > {max_processes}")
    
    # Test process counting
    print("\n4. Testing process counting logic:")
    count = watchdog._count_dinoair_processes()
    print(f"   - Raw count: {count}")
    print(f"   - PIDs found: {watchdog._dinoair_pids}")
    
    # Check what would happen
    print("\n5. Alert check simulation:")
    critical = watchdog._check_alerts(metrics)
    print(f"   - Would trigger critical alert: {critical}")
    print(f"   - Alerts triggered: {len(alerts_triggered)}")
    for level, msg in alerts_triggered:
        print(f"     - {level.value}: {msg}")
    
    if critical and self_terminate:
        print("\n⚠️  WARNING: Watchdog would TERMINATE the application!")
        print("   Reason: Critical alert + self_terminate_on_critical = True")
    
    print("\n=== END DEBUG ===")

if __name__ == "__main__":
    debug_watchdog()