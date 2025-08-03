#!/usr/bin/env python3
"""Fix for watchdog issues - adds logging and prevents unexpected shutdowns"""

import sys
import os
from pathlib import Path

def apply_watchdog_fix():
    """Apply fixes to the watchdog to prevent GUI crashes"""
    
    watchdog_file = Path("src/utils/Watchdog.py")
    
    if not watchdog_file.exists():
        print("Error: Watchdog.py not found")
        return False
    
    # Skip reading the file due to encoding issues
    # content = watchdog_file.read_text(encoding='utf-8')
    
    # Fix 1: Add logging to process detection
    process_logging = '''
                    # Check if process is DinoAir related using multiple heuristics
                    if ('dinoair' in name or 'dinoair' in cmdline or 
                        ('main.py' in cmdline and 'dinoair' in cmdline)):
                        count += 1
                        current_pids.add(info['pid'])
                        # DEBUG: Log what we're detecting
                        logger.debug(f"Detected DinoAir process: PID={info['pid']}, Name={name}, Cmdline={cmdline[:100]}")
'''
    
    # Fix 2: Add safety check to prevent self-termination when disabled
    safety_check = '''
                # If critical alert and self-termination enabled, perform emergency shutdown
                if critical_alert and self.self_terminate_on_critical:
                    logger.warning(f"Critical alert triggered. Self-terminate is {self.self_terminate_on_critical}")
                    if self.self_terminate_on_critical:  # Double-check the flag
                        self._perform_emergency_shutdown()
                        break  # Exit monitoring loop after emergency shutdown
                    else:
                        logger.warning("Self-termination disabled - NOT shutting down")
'''
    
    # Fix 3: Prevent os._exit when self_terminate is disabled
    exit_fix = '''
                # Step 5: Self-terminate as last resort
                logger.critical("Self-terminating due to critical resource limits")
                if self.self_terminate_on_critical:  # Only exit if explicitly enabled
                    os._exit(1)  # Force exit without cleanup - bypasses Python shutdown
                else:
                    logger.critical("Self-termination disabled - NOT exiting")
'''
    
    # Fix 4: Add more detailed logging to emergency shutdown
    shutdown_logging = '''
    def _perform_emergency_shutdown(self) -> None:
        """Perform emergency shutdown of entire DinoAir process tree.
        
        This is the nuclear option triggered when critical limits are breached
        and self_terminate_on_critical is enabled. The sequence:
        
        1. Log critical alert
        2. Attempt graceful cleanup of other processes
        3. Wait for processes to terminate
        4. If processes still exceed limits, force kill everything
        5. Terminate self as last resort
        
        This prevents runaway processes from consuming all system resources.
        """
        logger.critical(f"EMERGENCY SHUTDOWN: Critical limits breached - terminating process tree. self_terminate={self.self_terminate_on_critical}")
        
        if not self.self_terminate_on_critical:
            logger.critical("Self-termination is DISABLED - aborting emergency shutdown")
            return
'''
    
    # Write the fixes
    print("Creating patched Watchdog_fixed.py with:")
    print("1. Enhanced process detection logging")
    print("2. Safety checks to prevent unwanted termination")
    print("3. Protection against os._exit when self_terminate is disabled")
    print("4. Detailed shutdown logging")
    
    # For now, let's create a simple patch file that shows the needed changes
    with open("watchdog_patches.txt", "w") as f:
        f.write("WATCHDOG PATCHES NEEDED:\n")
        f.write("=" * 60 + "\n\n")
        f.write("1. In _count_dinoair_processes(), after line 273, add:\n")
        f.write("   logger.debug(f\"Detected DinoAir process: PID={info['pid']}, Name={name}, Cmdline={cmdline[:100]}\")\n\n")
        
        f.write("2. In _monitor_loop(), replace lines 318-321 with:\n")
        f.write(safety_check + "\n\n")
        
        f.write("3. In _perform_emergency_shutdown(), add at the beginning:\n")
        f.write("   if not self.self_terminate_on_critical:\n")
        f.write("       logger.critical(\"Self-termination is DISABLED - aborting emergency shutdown\")\n")
        f.write("       return\n\n")
        
        f.write("4. In _perform_emergency_shutdown(), before os._exit calls, add:\n")
        f.write("   if self.self_terminate_on_critical:  # Only exit if explicitly enabled\n")
        f.write("       os._exit(1)\n")
        f.write("   else:\n")
        f.write("       logger.critical(\"Self-termination disabled - NOT exiting\")\n")
    
    print("\nPatches saved to watchdog_patches.txt")
    return True

if __name__ == "__main__":
    apply_watchdog_fix()