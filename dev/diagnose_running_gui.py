#!/usr/bin/env python3
"""Run this while the GUI is running to diagnose the watchdog issue"""

import sys
import time
import psutil
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.Watchdog import SystemWatchdog


def diagnose_running_processes():
    """Check what processes the watchdog would see right now"""
    print("=== DIAGNOSING RUNNING PROCESSES ===")
    print("Run this while main.py is running to see what the watchdog detects\n")
    
    watchdog = SystemWatchdog()
    
    # Get process count
    count = watchdog._count_dinoair_processes()
    print(f"DinoAir processes detected: {count}")
    print(f"PIDs found: {watchdog._dinoair_pids}")
    
    # Show details of each detected process
    if watchdog._dinoair_pids:
        print("\nDetailed process info:")
        for pid in watchdog._dinoair_pids:
            try:
                proc = psutil.Process(pid)
                print(f"\n  PID {pid}:")
                print(f"    Name: {proc.name()}")
                print(f"    Status: {proc.status()}")
                cmdline = proc.cmdline()
                if cmdline:
                    print(f"    Command: {' '.join(cmdline[:3])}...")
                print(f"    Create time: {time.ctime(proc.create_time())}")
                
                # Check if it's the main app
                cmdline_str = ' '.join(cmdline).lower()
                if 'main.py' in cmdline_str:
                    print("    ⚠️  This is the main DinoAir app!")
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(f"    (Process {pid} no longer accessible)")
    
    # Check what would happen with current config
    print(f"\n\nConfiguration check:")
    print(f"  Max allowed processes: 5")
    print(f"  Current count: {count}")
    print(f"  Would trigger CRITICAL alert: {count > 5}")
    
    # Monitor for changes
    print("\n\nMonitoring for 30 seconds (press Ctrl+C to stop)...")
    print("This will show if process count changes over time")
    
    start_time = time.time()
    last_count = count
    
    try:
        while time.time() - start_time < 30:
            time.sleep(2)
            new_count = watchdog._count_dinoair_processes()
            if new_count != last_count:
                print(f"\n⚠️  Process count changed: {last_count} → {new_count}")
                print(f"   New PIDs: {watchdog._dinoair_pids}")
                last_count = new_count
            else:
                print(".", end="", flush=True)
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    
    print("\n\nDiagnosis complete!")


if __name__ == "__main__":
    diagnose_running_processes()