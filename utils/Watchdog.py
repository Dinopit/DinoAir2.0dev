"""System watchdog for monitoring VRAM usage and preventing runaway processes.

This module provides monitoring capabilities to ensure DinoAir doesn't consume
excessive system resources or spawn too many processes.
"""

import psutil  # Cross-platform system/process utilities
import time
import sys
import os
from concurrent.futures import ThreadPoolExecutor, Future  # For background monitoring
from typing import Optional, Callable, Dict, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

# Setup logging
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels for resource monitoring."""
    INFO = "info"
    WARNING = "warning"  
    CRITICAL = "critical"  # Triggers emergency actions


@dataclass
class SystemMetrics:
    """Snapshot of current system resource usage.
    
    This dataclass holds all monitored metrics at a specific point in time.
    Used for both real-time monitoring and historical tracking.
    """
    vram_used_mb: float      # GPU memory currently in use
    vram_total_mb: float     # Total GPU memory available
    vram_percent: float      # Percentage of GPU memory used
    cpu_percent: float       # CPU usage percentage
    ram_used_mb: float       # System RAM currently in use
    ram_percent: float       # Percentage of system RAM used
    process_count: int       # Total processes running on system
    dinoair_processes: int   # Number of DinoAir-related processes
    uptime_seconds: int      # How long the watchdog has been running


class SystemWatchdog:
    """Monitor system resources and prevent runaway processes.
    
    This class implements a background monitoring system that:
    1. Tracks VRAM, RAM, and CPU usage
    2. Counts DinoAir processes to detect runaway spawning
    3. Triggers alerts when thresholds are exceeded
    4. Can perform emergency cleanup/shutdown if needed
    
    Uses ThreadPoolExecutor for non-blocking background monitoring.
    """
    
    def __init__(self, 
                 alert_callback: Optional[Callable[[AlertLevel, str], None]] = None,
                 metrics_callback: Optional[Callable[[SystemMetrics], None]] = None,
                 vram_threshold_percent: float = 80.0,
                 max_dinoair_processes: int = 5,
                 check_interval_seconds: int = 10,
                 self_terminate_on_critical: bool = False):
        """Initialize the system watchdog with configurable thresholds.
        
        Args:
            alert_callback: Called when resource limits are exceeded
            metrics_callback: Called with current metrics on each check
            vram_threshold_percent: VRAM usage threshold for alerts (%)
            max_dinoair_processes: Maximum allowed DinoAir processes
            check_interval_seconds: How often to check system metrics
            self_terminate_on_critical: If True, kill entire process tree on critical alerts
        """
        # Store callbacks - alert_callback handles threshold breaches
        self.alert_callback = alert_callback or self._default_alert_handler
        self.metrics_callback = metrics_callback  # Optional live metrics feed
        
        # Configurable thresholds for resource monitoring
        self.vram_threshold = vram_threshold_percent
        self.max_processes = max_dinoair_processes
        self.check_interval = check_interval_seconds
        self.self_terminate_on_critical = self_terminate_on_critical
        
        # Threading infrastructure for background monitoring
        self._monitoring = False  # Flag to control monitoring loop
        self._executor: Optional[ThreadPoolExecutor] = None  # Background thread pool
        self._monitor_future: Optional[Future] = None  # Handle to monitoring task
        self._last_metrics: Optional[SystemMetrics] = None  # Cache latest metrics
        
        # Process tracking for runaway detection
        self._dinoair_pids: set = set()  # Set of known DinoAir process IDs
        self._startup_time = time.time()  # When this watchdog instance started
        self._current_pid = os.getpid()  # Our own PID (don't kill ourselves)
        
    def start_monitoring(self) -> None:
        """Start the background monitoring using ThreadPoolExecutor.
        
        Creates a single-threaded executor that runs the monitoring loop
        in the background without blocking the main application.
        """
        if self._monitoring:
            logger.warning("Watchdog already monitoring")
            return
            
        self._monitoring = True
        # Single worker thread dedicated to monitoring
        self._executor = ThreadPoolExecutor(
            max_workers=1, 
            thread_name_prefix="SystemWatchdog"  # Makes debugging easier
        )
        
        # Submit the monitoring loop to run in background
        self._monitor_future = self._executor.submit(self._monitor_loop)
        logger.info("System watchdog started with ThreadPoolExecutor")
        
    def stop_monitoring(self) -> None:
        """Stop the monitoring and cleanup executor gracefully."""
        self._monitoring = False  # Signal monitoring loop to exit
        
        # Cancel the monitoring task if it's still running
        if self._monitor_future:
            self._monitor_future.cancel()
            
        # Shutdown executor and wait for clean termination
        if self._executor:
            self._executor.shutdown(wait=True, timeout=5.0)
            self._executor = None
            
        logger.info("System watchdog stopped")
        
    def get_current_metrics(self) -> SystemMetrics:
        """Collect current system resource metrics from various sources.
        
        This is the core data collection method that gathers:
        - GPU VRAM usage (via nvidia-smi or estimation)
        - CPU and RAM usage (via psutil)
        - Process counts (total and DinoAir-specific)
        - Uptime calculation
        
        Returns:
            SystemMetrics: Current resource usage snapshot
        """
        try:
            # Get VRAM info - tries nvidia-smi first, falls back to estimation
            vram_used, vram_total, vram_percent = self._get_vram_info()
            
            # Get CPU usage with 0.1s sampling interval for accuracy
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Calculate RAM usage from system memory info
            memory = psutil.virtual_memory()
            ram_used_mb = (memory.total - memory.available) / (1024 * 1024)
            
            # Count all system processes and DinoAir-specific ones
            total_processes = len(psutil.pids())
            dinoair_processes = self._count_dinoair_processes()
            
            # Calculate how long this watchdog instance has been running
            uptime_seconds = int(time.time() - self._startup_time)
            
            return SystemMetrics(
                vram_used_mb=vram_used,
                vram_total_mb=vram_total,
                vram_percent=vram_percent,
                cpu_percent=cpu_percent,
                ram_used_mb=ram_used_mb,
                ram_percent=memory.percent,
                process_count=total_processes,
                dinoair_processes=dinoair_processes,
                uptime_seconds=uptime_seconds
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            # Return safe defaults if metrics collection fails
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop running in ThreadPoolExecutor background thread.
        
        This runs continuously until _monitoring flag is set to False.
        Each iteration:
        1. Collects current system metrics
        2. Calls metrics callback if provided (for live updates)
        3. Checks metrics against thresholds and triggers alerts
        4. Handles emergency shutdown if critical limits breached
        5. Sleeps for check_interval before next iteration
        """
        while self._monitoring:
            try:
                # Collect current system state
                metrics = self.get_current_metrics()
                self._last_metrics = metrics  # Cache for status reports
                
                # Send live metrics to callback if provided (e.g., for GUI updates)
                if self.metrics_callback:
                    try:
                        self.metrics_callback(metrics)
                    except Exception as e:
                        logger.error(f"Error in metrics callback: {e}")
                
                # Check if any metrics exceed thresholds and trigger alerts
                critical_alert = self._check_alerts(metrics)
                
                # If critical alert and self-termination enabled, perform emergency shutdown
                if critical_alert and self.self_terminate_on_critical:
                    self._perform_emergency_shutdown()
                    break  # Exit monitoring loop after emergency shutdown
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                
            # Wait before next check - this controls monitoring frequency
            time.sleep(self.check_interval)
    
    def _get_vram_info(self) -> tuple[float, float, float]:
        """Get GPU VRAM usage information with fallback strategies.
        
        Tries multiple approaches:
        1. nvidia-smi command (most accurate for NVIDIA GPUs)
        2. Estimation based on system RAM (fallback)
        
        Returns:
            tuple: (used_mb, total_mb, percent_used)
        """
        try:
            import subprocess
            
            try:
                # Attempt to use nvidia-smi for accurate VRAM info
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.used,memory.total', 
                     '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        # Parse nvidia-smi output: "used, total" in MB
                        used, total = map(int, lines[0].split(', '))
                        percent = (used / total) * 100 if total > 0 else 0
                        return float(used), float(total), percent
                        
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # nvidia-smi not available or timed out
                pass
                
            # Fallback: estimate VRAM based on system memory
            # Assumes GPU has ~25% of system RAM or 8GB max (rough approximation)
            memory = psutil.virtual_memory()
            estimated_vram = min(memory.total * 0.25, 8 * 1024 * 1024 * 1024)  # 25% or 8GB max
            return 0.0, estimated_vram / (1024 * 1024), 0.0  # No usage data available
            
        except Exception as e:
            logger.debug(f"Could not get VRAM info: {e}")
            return 0.0, 0.0, 0.0  # Return zeros if all methods fail
    
    def _count_dinoair_processes(self) -> int:
        """Count processes related to DinoAir to detect runaway spawning.
        
        Searches all system processes for DinoAir-related indicators:
        - Process name contains 'dinoair'
        - Command line contains 'dinoair'
        - Command line contains 'main.py' AND 'dinoair'
        
        Updates internal PID tracking for emergency cleanup purposes.
        
        Returns:
            int: Number of DinoAir-related processes found
        """
        count = 0
        current_pids = set()  # Track PIDs for potential cleanup
        
        try:
            # Iterate through all system processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    info = proc.info
                    name = info.get('name', '').lower()
                    cmdline = ' '.join(info.get('cmdline', [])).lower()
                    
                    # Check if process is DinoAir related using multiple heuristics
                    if ('dinoair' in name or 'dinoair' in cmdline or 
                        'main.py' in cmdline and 'dinoair' in cmdline):
                        count += 1
                        current_pids.add(info['pid'])
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process disappeared or access denied - skip it
                    continue
                    
            # Update our internal tracking of DinoAir PIDs
            self._dinoair_pids = current_pids
            return count
            
        except Exception as e:
            logger.error(f"Error counting DinoAir processes: {e}")
            return 0
    
    def _check_alerts(self, metrics: SystemMetrics) -> bool:
        """Check metrics against thresholds and trigger appropriate alerts.
        
        Implements a tiered alert system:
        - WARNING: High but manageable resource usage
        - CRITICAL: Dangerous levels that may require emergency action
        
        Args:
            metrics: Current system metrics to check
            
        Returns:
            bool: True if critical alert was triggered (may require emergency action)
        """
        critical_triggered = False
        
        # Check VRAM usage against configured threshold
        if metrics.vram_percent > self.vram_threshold:
            self.alert_callback(
                AlertLevel.WARNING,
                f"High VRAM usage: {metrics.vram_percent:.1f}% "
                f"({metrics.vram_used_mb:.0f}MB / {metrics.vram_total_mb:.0f}MB)"
            )
        
        # Check process count - CRITICAL ALERT (runaway process detection)
        if metrics.dinoair_processes > self.max_processes:
            self.alert_callback(
                AlertLevel.CRITICAL,
                f"Too many DinoAir processes: {metrics.dinoair_processes} "
                f"(limit: {self.max_processes}). Possible runaway processes!"
            )
            critical_triggered = True  # This triggers emergency actions
            
        # Check for extreme resource usage that could destabilize system
        if metrics.ram_percent > 90:
            self.alert_callback(
                AlertLevel.WARNING,
                f"High RAM usage: {metrics.ram_percent:.1f}% "
                f"({metrics.ram_used_mb:.0f}MB)"
            )
            
        if metrics.cpu_percent > 80:
            self.alert_callback(
                AlertLevel.WARNING,
                f"High CPU usage: {metrics.cpu_percent:.1f}%"
            )
            
        # Critical RAM usage - system may become unresponsive
        if metrics.ram_percent > 95:
            self.alert_callback(
                AlertLevel.CRITICAL,
                f"Critical RAM usage: {metrics.ram_percent:.1f}% - System may become unstable"
            )
            critical_triggered = True
            
        return critical_triggered
    
    def _default_alert_handler(self, level: AlertLevel, message: str) -> None:
        """Default alert handler that logs messages with appropriate severity."""
        if level == AlertLevel.CRITICAL:
            logger.critical(f"WATCHDOG ALERT: {message}")
        elif level == AlertLevel.WARNING:
            logger.warning(f"WATCHDOG: {message}")
        else:
            logger.info(f"WATCHDOG: {message}")
    
    def emergency_cleanup(self) -> Dict[str, int]:
        """Emergency cleanup of runaway DinoAir processes.
        
        Attempts to terminate all tracked DinoAir processes except
        the current process (to avoid killing ourselves).
        
        Uses SIGTERM for graceful shutdown where possible.
        
        Returns:
            Dict[str, int]: Statistics of cleanup operation
        """
        killed_count = 0
        failed_count = 0
        
        try:
            # Iterate through all tracked DinoAir PIDs
            for pid in list(self._dinoair_pids):
                try:
                    proc = psutil.Process(pid)
                    # Safety check: don't kill the main process (ourselves)
                    if pid != self._current_pid:
                        proc.terminate()  # Send SIGTERM for graceful shutdown
                        killed_count += 1
                        logger.warning(f"Terminated runaway process {pid}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process already gone or access denied
                    failed_count += 1
                    
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
            
        return {"killed": killed_count, "failed": failed_count}
    
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
        logger.critical("EMERGENCY SHUTDOWN: Critical limits breached - terminating process tree")
        
        try:
            # Step 1: Try graceful cleanup of other processes first
            cleanup_result = self.emergency_cleanup()
            logger.info(f"Emergency cleanup: {cleanup_result}")
            
            # Step 2: Give processes time to terminate gracefully
            time.sleep(2)
            
            # Step 3: Check if we still have too many processes after cleanup
            current_metrics = self.get_current_metrics()
            if current_metrics.dinoair_processes > self.max_processes:
                logger.critical("Force terminating entire process tree")
                
                # Get current process and all its children (subprocess tree)
                current_process = psutil.Process(self._current_pid)
                children = current_process.children(recursive=True)
                
                # Step 4: Terminate all child processes first
                for child in children:
                    try:
                        child.terminate()  # SIGTERM
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Wait briefly then force kill stubborn processes
                time.sleep(1)
                for child in children:
                    try:
                        if child.is_running():
                            child.kill()  # SIGKILL - forceful
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Step 5: Self-terminate as last resort
                logger.critical("Self-terminating due to critical resource limits")
                os._exit(1)  # Force exit without cleanup - bypasses Python shutdown
                
        except Exception as e:
            logger.critical(f"Error during emergency shutdown: {e}")
            os._exit(1)  # Force exit as absolute last resort
    
    def get_status_report(self) -> str:
        """Generate a formatted status report for display/logging.
        
        Returns:
            str: Multi-line status report with current metrics and settings
        """
        if not self._last_metrics:
            return "Watchdog: No metrics available"
            
        m = self._last_metrics
        # Convert uptime to human-readable format
        hours = m.uptime_seconds // 3600
        minutes = (m.uptime_seconds % 3600) // 60
        
        # Show self-terminate status for safety awareness
        terminate_status = "ON" if self.self_terminate_on_critical else "OFF"
        
        return (
            f"🐕 System Watchdog Status\n"
            f"├─ Uptime: {hours}h {minutes}m\n"
            f"├─ VRAM: {m.vram_percent:.1f}% ({m.vram_used_mb:.0f}MB)\n"
            f"├─ RAM: {m.ram_percent:.1f}% ({m.ram_used_mb:.0f}MB)\n"
            f"├─ CPU: {m.cpu_percent:.1f}%\n"
            f"├─ Total Processes: {m.process_count}\n"
            f"├─ DinoAir Processes: {m.dinoair_processes}/{self.max_processes}\n"
            f"└─ Auto-Terminate: {terminate_status}"
        )


# CLI test harness for standalone testing
def main():
    """Test the watchdog from command line with colored output and live metrics."""
    def alert_handler(level: AlertLevel, message: str):
        """Handle alerts with colored console output."""
        color = {"info": "\033[36m", "warning": "\033[33m", "critical": "\033[31m"}
        reset = "\033[0m"
        print(f"{color.get(level.value, '')}{level.value.upper()}: {message}{reset}")
    
    def metrics_handler(metrics: SystemMetrics):
        """Handle live metrics updates with compact display."""
        print(f"📊 Live: VRAM {metrics.vram_percent:.1f}% | "
              f"RAM {metrics.ram_percent:.1f}% | "
              f"CPU {metrics.cpu_percent:.1f}% | "
              f"Procs {metrics.dinoair_processes}")
    
    # Create watchdog with testing-friendly settings
    # Lower thresholds for easier testing, disable self-terminate for safety
    watchdog = SystemWatchdog(
        alert_callback=alert_handler,
        metrics_callback=metrics_handler,
        vram_threshold_percent=70.0,  # Lower threshold for testing
        max_dinoair_processes=3,      # Easier to hit for testing
        check_interval_seconds=5,     # More frequent checks for testing
        self_terminate_on_critical=False  # Disable for testing safety
    )
    
    print("🐕 Starting Enhanced System Watchdog (Ctrl+C to stop)")
    print("🔧 Features: ThreadPoolExecutor, Live Metrics, Self-Terminate Option")
    print("=" * 60)
    
    try:
        # Start background monitoring
        watchdog.start_monitoring()
        
        # Main loop: display status reports every 15 seconds
        while True:
            time.sleep(15)
            print(watchdog.get_status_report())
            print("-" * 40)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping watchdog...")
        watchdog.stop_monitoring()  # Graceful shutdown
        print("✅ Watchdog stopped cleanly")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()