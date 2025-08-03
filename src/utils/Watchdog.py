"""System watchdog for monitoring VRAM usage and preventing runaway processes.

This module provides monitoring capabilities to ensure DinoAir doesn't consume
excessive system resources or spawn too many processes.
It uses psutil for system metrics and subprocess for GPU VRAM info.
It provides monitoring capabilities for system resources.
🚨 SAFETY NOTES:
- self_terminate_on_critical=False by default for safety
- Emergency shutdown only triggers on runaway process detection
- Current process (self) is excluded from cleanup operations
- All operations have exception handling with fallbacks
"""
import psutil  # Cross-platform system/process utilities
import time
import sys
import os
from typing import Optional, Callable, Dict
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Handle both direct execution and package import
try:
    from .logger import Logger
except ImportError:
    # When running directly, add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.utils.logger import Logger

# Setup logging
logger = Logger()

# Process detection configuration constants
DINOAIR_PROCESS_WHITELIST = [
    # Exact process names or patterns that are legitimate DinoAir processes
    "dinoair",
    "dinoair.exe",
    "python main.py",  # When running directly
    "python.exe main.py",  # Windows variant
]

DINOAIR_PROCESS_BLACKLIST = [
    # Patterns to exclude (development tools, IDEs, etc.)
    "pycharm", "vscode", "code", "code.exe",
    "pylsp", "pyright", "python-language-server",
    "pytest", "unittest", "debugpy",
    "pip", "setup.py", "conda", "mamba",
    "jupyter", "notebook", "ipython",
    "git", "gitk", "git-gui",
    "browser", "chrome", "firefox", "edge",
    "explorer.exe", "finder",  # File explorers
    "terminal", "cmd.exe", "powershell", "bash", "sh",
    "winpty", "conhost", "mintty",  # Terminal emulators
    # Test and development related
    "test_", "_test", "debug_", "_debug",
    "benchmark", "profile", "trace",
]

# Minimum process age in seconds before counting (filters transient processes)
DINOAIR_MIN_PROCESS_AGE = 2.0

# Expected DinoAir executable patterns (used for path verification)
DINOAIR_EXECUTABLE_PATTERNS = [
    "main.py",
    "dinoair",
    "dinoair.exe",
    "DinoAir",
    "DinoAir.exe"
]


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
                 alert_callback: Optional[
                     Callable[[AlertLevel, str], None]
                 ] = None,
                 metrics_callback: Optional[
                     Callable[[SystemMetrics], None]
                 ] = None,
                 vram_threshold_percent: float = 95.0,
                 max_dinoair_processes: int = 5,
                 check_interval_seconds: int = 30,
                 self_terminate_on_critical: bool = False):
        """Initialize the system watchdog.
        
        Args:
            alert_callback: Function called when alerts are triggered
            metrics_callback: Function called with live metrics updates
            vram_threshold_percent: VRAM usage % that triggers warnings
            max_dinoair_processes: Max DinoAir processes before critical alert
            check_interval_seconds: How often to check system metrics
            self_terminate_on_critical: Whether to perform emergency shutdown
        """
        # Callback functions for integration
        self.alert_callback = alert_callback or self._default_alert_handler
        self.metrics_callback = metrics_callback
        
        # Monitoring thresholds
        self.vram_threshold = vram_threshold_percent
        self.max_processes = max_dinoair_processes
        self.check_interval = check_interval_seconds
        self.self_terminate_on_critical = self_terminate_on_critical
        
        # Internal state
        self._monitoring = False
        self._startup_time = time.time()
        self._last_metrics: Optional[SystemMetrics] = None
        # Class variables for static methods
        SystemWatchdog._dinoair_pids = set()  # Track PIDs for cleanup
        SystemWatchdog._current_pid = os.getpid()  # Track current process ID
        
    def start_monitoring(self) -> None:
        """Deprecated: Use Qt-based watchdog instead.
        
        This method is kept for backward compatibility but does nothing.
        """
        logger.warning(
            "ThreadPoolExecutor-based monitoring is deprecated. "
            "Use Qt-based watchdog instead."
        )
        
    def stop_monitoring(self) -> None:
        """Deprecated: Use Qt-based watchdog instead.
        
        This method is kept for backward compatibility but does nothing.
        """
        logger.warning(
            "ThreadPoolExecutor-based monitoring is deprecated. "
            "Use Qt-based watchdog instead."
        )
        
    def get_current_metrics(
            self,
            startup_time: Optional[float] = None
    ) -> SystemMetrics:
        """Collect current system resource metrics from various sources.
        
        This is the core data collection method that gathers:
        - GPU VRAM usage (via nvidia-smi or estimation)
        - CPU and RAM usage (via psutil)
        - Process counts (total and DinoAir-specific)
        - Uptime calculation
        
        Args:
            startup_time: Optional startup time for uptime calculation
            
        Returns:
            SystemMetrics: Current resource usage snapshot
        """
        try:
            # Get VRAM info with error handling
            try:
                vram_used, vram_total, vram_percent = (
                    SystemWatchdog._get_vram_info()
                )
            except Exception as e:
                logger.error(f"Failed to get VRAM info: {e}")
                vram_used, vram_total, vram_percent = 0.0, 8192.0, 0.0
            
            # Get CPU usage with error handling
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
            except Exception as e:
                logger.error(f"Failed to get CPU usage: {e}")
                cpu_percent = 0.0
            
            # Get RAM usage with error handling
            try:
                memory = psutil.virtual_memory()
                ram_used_mb = (memory.total - memory.available) / (1024 * 1024)
                ram_percent = memory.percent
            except Exception as e:
                logger.error(f"Failed to get memory info: {e}")
                ram_used_mb = 0.0
                ram_percent = 0.0
            
            # Count processes with error handling
            try:
                total_processes = len(psutil.pids())
            except Exception as e:
                logger.error(f"Failed to count total processes: {e}")
                total_processes = 0
                
            try:
                dinoair_processes = SystemWatchdog._count_dinoair_processes()
            except Exception as e:
                logger.error(f"Failed to count DinoAir processes: {e}")
                dinoair_processes = 1  # At least this process
            
            # Calculate how long this watchdog instance has been running
            if hasattr(self, '_startup_time'):
                uptime_seconds = int(time.time() - self._startup_time)
            elif startup_time:
                uptime_seconds = int(time.time() - startup_time)
            else:
                uptime_seconds = 0
            
            return SystemMetrics(
                vram_used_mb=vram_used,
                vram_total_mb=vram_total,
                vram_percent=vram_percent,
                cpu_percent=cpu_percent,
                ram_used_mb=ram_used_mb,
                ram_percent=ram_percent,
                process_count=total_processes,
                dinoair_processes=dinoair_processes,
                uptime_seconds=uptime_seconds
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            # Return safe defaults if metrics collection fails
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    @staticmethod
    def _get_vram_info() -> tuple[float, float, float]:
        """Get GPU VRAM usage information with fallback strategies.
        
        Tries multiple approaches:
        1. nvidia-smi command (most accurate for NVIDIA GPUs)
        2. AMD rocm-smi command (for AMD GPUs)
        3. Windows WMI (for Windows systems)
        4. Estimation based on system RAM (final fallback)
        
        Returns:
            tuple: (used_mb, total_mb, percent_used)
        """
        # Track which method succeeded for logging
        method_used = None
        
        try:
            import subprocess
            import platform
            
            # Strategy 1: Try nvidia-smi for NVIDIA GPUs
            try:
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=memory.used,memory.total',
                     '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=5,
                    stderr=subprocess.DEVNULL  # Suppress error output
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    if lines and lines[0]:
                        try:
                            # Parse nvidia-smi output: "used, total" in MB
                            parts = lines[0].split(', ')
                            if len(parts) == 2:
                                used = float(parts[0])
                                total = float(parts[1])
                                if total > 0:
                                    percent = (used / total) * 100
                                    method_used = "nvidia-smi"
                                    logger.debug(
                                        f"VRAM info via {method_used}: "
                                        f"{used}MB/{total}MB ({percent:.1f}%)"
                                    )
                                    return used, total, percent
                        except (ValueError, IndexError):
                            logger.debug("Failed to parse nvidia-smi output")
                            
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                # nvidia-smi not available or timed out
                pass
            
            # Strategy 2: Try AMD rocm-smi for AMD GPUs
            try:
                result = subprocess.run(
                    ['rocm-smi', '--showmeminfo', 'vram'],
                    capture_output=True, text=True, timeout=5,
                    stderr=subprocess.DEVNULL
                )
                
                if result.returncode == 0 and result.stdout:
                    # Parse rocm-smi output (format varies)
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'VRAM Total' in line and 'VRAM Used' in line:
                            # Extract values from line
                            import re
                            used_match = re.search(r'VRAM Used.*?(\d+)', line)
                            total_match = re.search(
                                r'VRAM Total.*?(\d+)', line
                            )
                            if used_match and total_match:
                                used = float(used_match.group(1))
                                total = float(total_match.group(1))
                                if total > 0:
                                    percent = (used / total) * 100
                                    method_used = "rocm-smi"
                                    logger.debug(
                                        f"VRAM info via {method_used}: "
                                        f"{used}MB/{total}MB ({percent:.1f}%)"
                                    )
                                    return used, total, percent
                                    
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
                
            # Strategy 3: Windows WMI for integrated graphics
            if platform.system() == 'Windows':
                try:
                    # Try importing wmi (may not be installed)
                    try:
                        import wmi  # type: ignore
                    except ImportError:
                        wmi = None
                        
                    if wmi:
                        c = wmi.WMI()
                        for gpu in c.Win32_VideoController():
                            if gpu.AdapterRAM:
                                # AdapterRAM is in bytes
                                total = gpu.AdapterRAM / (1024 * 1024)
                                # Can't get usage from WMI, estimate
                                used = 0.0
                                percent = 0.0
                                method_used = "Windows WMI"
                                logger.debug(
                                    f"VRAM info via {method_used}: "
                                    f"{total}MB total (usage unknown)"
                                )
                                return used, total, percent
                except Exception as e:
                    logger.debug(f"WMI query failed: {e}")
                    
            # Strategy 4: Fallback estimation based on system memory
            memory = psutil.virtual_memory()
            # Estimate: ~25% of system RAM or 8GB max
            estimated_vram = min(memory.total * 0.25, 8 * 1024 * 1024 * 1024)
            total_mb = estimated_vram / (1024 * 1024)
            
            # Try to make a reasonable usage estimate
            # If system RAM is heavily used, GPU might be too
            if memory.percent > 80:
                # Estimate higher GPU usage
                used_mb = total_mb * 0.6
                percent = 60.0
            else:
                # Conservative estimate
                used_mb = total_mb * 0.3
                percent = 30.0
                
            method_used = "estimation"
            logger.debug(
                f"VRAM info via {method_used}: "
                f"{used_mb:.0f}MB/{total_mb:.0f}MB ({percent:.1f}%) "
                f"- based on system RAM"
            )
            return used_mb, total_mb, percent
            
        except Exception as e:
            logger.error(f"Unexpected error getting VRAM info: {e}")
            # Return safe defaults
            return 0.0, 8192.0, 0.0  # 8GB default total
    
    @staticmethod
    def _count_dinoair_processes() -> int:
        """Count processes related to DinoAir to detect runaway spawning.
        
        Uses a sophisticated detection algorithm with:
        - Whitelist/blacklist filtering
        - Executable path verification
        - Working directory checking
        - Process age filtering
        - Detailed logging for debugging
        - Enhanced error recovery for permission issues
        
        Updates internal PID tracking for emergency cleanup purposes.
        
        Returns:
            int: Number of legitimate DinoAir-related processes found
        """
        count = 0
        current_pids = set()  # Track PIDs for potential cleanup
        current_time = time.time()
        permission_errors = 0
        zombie_processes = 0
        
        # Get the expected DinoAir directory path
        try:
            dinoair_dir = Path(__file__).parent.parent.parent.resolve()
            dinoair_dir_str = str(dinoair_dir).lower()
        except Exception as e:
            logger.error(f"Failed to determine DinoAir directory: {e}")
            # Use a reasonable default
            dinoair_dir_str = "dinoair"
        
        try:
            # Get process iterator
            process_iter = psutil.process_iter(
                ['pid', 'name', 'cmdline', 'create_time', 'exe', 'cwd']
            )
            
            # Iterate through all system processes
            for proc in process_iter:
                try:
                    info = proc.info
                    pid = info.get('pid')
                    name = info.get('name', '').lower()
                    
                    # Skip if process is too young (transient process)
                    create_time = info.get('create_time', 0)
                    process_age = current_time - create_time
                    if create_time and process_age < DINOAIR_MIN_PROCESS_AGE:
                        logger.debug(
                            f"Skipping process {pid} ({name}) - too young: "
                            f"{current_time - create_time:.1f}s"
                        )
                        continue
                    
                    # Safely handle cmdline - might be None or non-strings
                    cmdline_raw = info.get('cmdline')
                    if cmdline_raw is None or not cmdline_raw:
                        cmdline = ''
                        cmdline_original = []
                    else:
                        try:
                            # Keep original for path checking
                            cmdline_original = [
                                str(item) for item in cmdline_raw
                                if item is not None
                            ]
                            cmdline = ' '.join(cmdline_original).lower()
                        except (TypeError, ValueError):
                            cmdline = ''
                            cmdline_original = []
                    
                    # Get executable path and working directory
                    exe_path = info.get('exe', '')
                    cwd = info.get('cwd', '')
                    
                    # Normalize paths for comparison
                    if exe_path:
                        exe_path_lower = exe_path.lower()
                    else:
                        exe_path_lower = ''
                    
                    if cwd:
                        cwd_lower = cwd.lower()
                    else:
                        cwd_lower = ''
                    
                    # Check blacklist first (early exclusion)
                    blacklisted = False
                    blacklist_reason = ""
                    for pattern in DINOAIR_PROCESS_BLACKLIST:
                        if pattern in name or pattern in cmdline:
                            blacklisted = True
                            blacklist_reason = (
                                f"matches blacklist pattern '{pattern}'"
                            )
                            break
                    
                    if blacklisted:
                        logger.debug(
                            f"Excluded process {pid} ({name}): "
                            f"{blacklist_reason}"
                        )
                        continue
                    
                    # Now check if it's a DinoAir process
                    is_dinoair = False
                    reason = ""
                    confidence = 0  # 0-100 confidence score
                    
                    # Check 1: Whitelist patterns (highest confidence)
                    for pattern in DINOAIR_PROCESS_WHITELIST:
                        if pattern in name or pattern in cmdline:
                            is_dinoair = True
                            reason = f"matches whitelist pattern '{pattern}'"
                            confidence = 90
                            break
                    
                    # Check 2: Executable path verification
                    if not is_dinoair and exe_path_lower:
                        for exe_pattern in DINOAIR_EXECUTABLE_PATTERNS:
                            if exe_pattern.lower() in exe_path_lower:
                                # Verify it's in the DinoAir directory
                                if dinoair_dir_str in exe_path_lower:
                                    is_dinoair = True
                                    reason = (
                                        f"executable path '{exe_path}' "
                                        f"in DinoAir directory"
                                    )
                                    confidence = 95
                                    break
                    
                    # Check 3: Working directory verification
                    if not is_dinoair and cwd_lower:
                        if dinoair_dir_str in cwd_lower:
                            # Check if it's running a DinoAir-related script
                            if 'main.py' in cmdline or 'dinoair' in cmdline:
                                is_dinoair = True
                                reason = (
                                    f"running from DinoAir directory: {cwd}"
                                )
                                confidence = 85
                    
                    # Check 4: Command line analysis (lower confidence)
                    if not is_dinoair:
                        # Look for main.py with full path
                        if cmdline_original:
                            for arg in cmdline_original:
                                arg_lower = arg.lower()
                                if ('main.py' in arg and
                                        dinoair_dir_str in arg_lower):
                                    is_dinoair = True
                                    reason = (
                                        f"running main.py from DinoAir "
                                        f"path: {arg}"
                                    )
                                    confidence = 80
                                    break
                    
                    # Check 5: Name-based detection (lowest confidence)
                    if not is_dinoair and 'dinoair' in name:
                        # Additional verification needed
                        if exe_path and os.path.exists(exe_path):
                            # Check if it's a legitimate executable
                            try:
                                exe_stat = os.stat(exe_path)
                                if exe_stat.st_size > 100:  # Not an empty file
                                    is_dinoair = True
                                    reason = (
                                        f"process name '{name}' with "
                                        f"valid executable"
                                    )
                                    confidence = 70
                            except Exception:
                                pass
                    
                    if is_dinoair:
                        count += 1
                        current_pids.add(pid)
                        
                        # Enhanced logging with all available information
                        logger.info(
                            f"Detected DinoAir process #{count}:\n"
                            f"  PID: {pid}\n"
                            f"  Name: {name}\n"
                            f"  Reason: {reason}\n"
                            f"  Confidence: {confidence}%\n"
                            f"  Executable: {exe_path or 'N/A'}\n"
                            f"  Working Dir: {cwd or 'N/A'}\n"
                            f"  Age: {current_time - create_time:.1f}s\n"
                            f"  Command: {cmdline[:200]}"
                        )
                    else:
                        # Debug logging for relevant processes not counted
                        if ('dinoair' in name or 'dinoair' in cmdline or
                                'main.py' in cmdline):
                            logger.debug(
                                f"Process {pid} ({name}) NOT counted "
                                f"as DinoAir:\n"
                                f"  Executable: {exe_path or 'N/A'}\n"
                                f"  Working Dir: {cwd or 'N/A'}\n"
                                f"  Command: {cmdline[:100]}"
                            )
                        
                except psutil.NoSuchProcess:
                    # Process disappeared or zombie - normal behavior
                    # Note: ZombieProcess is a subclass of NoSuchProcess
                    continue
                except psutil.AccessDenied:
                    # Access denied - track but continue
                    permission_errors += 1
                    # Try to at least check the process name
                    try:
                        basic_info = proc.as_dict(attrs=['pid', 'name'])
                        name_lower = basic_info.get('name', '').lower()
                        if basic_info and 'dinoair' in name_lower:
                            logger.debug(
                                f"Possible DinoAir process "
                                f"{basic_info['pid']} "
                                f"({basic_info['name']}) - "
                                f"access denied for details"
                            )
                    except Exception:
                        pass
                    continue
                except psutil.TimeoutExpired:
                    # Process info timeout - skip this process
                    logger.debug(
                        f"Timeout getting info for process {proc.pid}"
                    )
                    continue
                except Exception as e:
                    # Log other unexpected errors but continue processing
                    logger.debug(f"Error processing process {proc.pid}: {e}")
                    continue
                    
            # Update our internal tracking of DinoAir PIDs
            SystemWatchdog._dinoair_pids = current_pids
            
            # Log summary including any issues
            summary_parts = [
                f"{count} DinoAir processes found"
            ]
            if current_pids:
                summary_parts.append(f"PIDs: {sorted(current_pids)}")
            if permission_errors > 0:
                summary_parts.append(f"{permission_errors} permission errors")
            if zombie_processes > 0:
                summary_parts.append(f"{zombie_processes} zombie processes")
                
            logger.info(
                f"Process detection complete: {', '.join(summary_parts)}"
            )
            
            return count
            
        except psutil.Error as e:
            # Specific psutil error
            logger.error(f"psutil error counting processes: {e}")
            # Return at least 1 to indicate this process is running
            return 1
        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error counting DinoAir processes: {e}")
            # Return at least 1 to indicate this process is running
            return 1
    
    def _monitor_loop(self) -> None:
        """Deprecated: This method is no longer used.
        
        The monitoring loop is now handled by Qt-based watchdog.
        """
        logger.warning(
            "_monitor_loop is deprecated. "
            "Use Qt-based watchdog instead."
        )
    
    def _check_alerts(self, metrics: SystemMetrics) -> bool:
        """Check metrics against thresholds and trigger appropriate alerts.
        
        Implements a tiered alert system:
        - WARNING: High but manageable resource usage
        - CRITICAL: Dangerous levels that may require emergency action
        
        Args:
            metrics: Current system metrics to check
            
        Returns:
            bool: True if critical alert was triggered
        """
        critical_triggered = False
        
        # Check VRAM usage against configured threshold
        if metrics.vram_percent > self.vram_threshold:
            self.alert_callback(
                AlertLevel.WARNING,
                f"High VRAM usage: {metrics.vram_percent:.1f}% "
                f"({metrics.vram_used_mb:.0f}MB / "
                f"{metrics.vram_total_mb:.0f}MB)"
            )
        
        # Check process count - CRITICAL ALERT (runaway process detection)
        if metrics.dinoair_processes > self.max_processes:
            # Log detailed info about what triggered the alert
            logger.warning(
                f"CRITICAL ALERT TRIGGERED: Process count "
                f"{metrics.dinoair_processes} > {self.max_processes}"
            )
            logger.warning(f"Detected PIDs: {list(self._dinoair_pids)}")
            
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
                f"Critical RAM usage: {metrics.ram_percent:.1f}% - "
                f"System may become unstable"
            )
            critical_triggered = True
            
        return critical_triggered
    
    def _default_alert_handler(self, level: AlertLevel, message: str):
        """Default alert handler that logs to console."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level.value.upper()}: {message}")
    
    @staticmethod
    def emergency_cleanup() -> Dict[str, int]:
        """Emergency cleanup of runaway DinoAir processes.
        
        Attempts to terminate all tracked DinoAir processes except
        the current process (to avoid killing ourselves).
        
        Uses SIGTERM for graceful shutdown where possible, with timeout
        protection and enhanced error handling.
        
        Returns:
            Dict[str, int]: Statistics of cleanup operation
        """
        killed_count = 0
        failed_count = 0
        skipped_count = 0
        current_pid = os.getpid()  # Initialize before try block
        
        try:
            
            # Iterate through all tracked DinoAir PIDs
            for pid in list(SystemWatchdog._dinoair_pids):
                try:
                    # Safety check: don't kill the main process (ourselves)
                    if pid == current_pid:
                        skipped_count += 1
                        logger.debug(f"Skipping current process {pid}")
                        continue
                        
                    proc = psutil.Process(pid)
                    
                    # Double-check it's still a DinoAir process
                    try:
                        proc_name = proc.name().lower()
                        if ('dinoair' not in proc_name and
                                'python' not in proc_name):
                            logger.warning(
                                f"Process {pid} no longer appears to be "
                                f"DinoAir-related: {proc_name}"
                            )
                            skipped_count += 1
                            continue
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # Can't verify, proceed with caution
                        pass
                    
                    # Try graceful termination first
                    proc.terminate()
                    
                    # Wait briefly for termination
                    try:
                        proc.wait(timeout=2)
                        killed_count += 1
                        logger.warning(
                            f"Successfully terminated process {pid}"
                        )
                    except psutil.TimeoutExpired:
                        # Process didn't terminate gracefully, try force kill
                        logger.warning(
                            f"Process {pid} didn't terminate gracefully, "
                            f"attempting force kill"
                        )
                        try:
                            proc.kill()
                            proc.wait(timeout=1)
                            killed_count += 1
                            logger.warning(f"Force killed process {pid}")
                        except Exception:
                            failed_count += 1
                            logger.error(
                                f"Failed to force kill process {pid}"
                            )
                            
                except psutil.NoSuchProcess:
                    # Process already gone - that's fine
                    logger.debug(f"Process {pid} no longer exists")
                    pass
                    
                except psutil.AccessDenied:
                    # Can't kill due to permissions
                    failed_count += 1
                    logger.error(
                        f"Access denied when trying to terminate "
                        f"process {pid}"
                    )
                    
                except Exception as e:
                    # Unexpected error
                    failed_count += 1
                    logger.error(
                        f"Unexpected error terminating process {pid}: {e}"
                    )
                    
        except Exception as e:
            logger.error(f"Critical error during emergency cleanup: {e}")
            
        # Clear the PID set for terminated processes
        if killed_count > 0:
            SystemWatchdog._dinoair_pids = {
                pid for pid in SystemWatchdog._dinoair_pids
                if pid == current_pid or psutil.pid_exists(pid)
            }
            
        return {
            "killed": killed_count,
            "failed": failed_count,
            "skipped": skipped_count
        }
    
    def _perform_emergency_shutdown(self,
                                    self_terminate_on_critical: bool = False,
                                    max_processes: int = 5) -> None:
        """Perform emergency shutdown of entire DinoAir process tree.
        
        This is the nuclear option triggered when critical limits are breached
        and self_terminate_on_critical is enabled. The sequence:
        
        1. Log critical alert
        2. Attempt graceful cleanup of other processes
        3. Wait for processes to terminate
        4. If processes still exceed limits, force kill everything
        5. Terminate self as last resort
        
        This prevents runaway processes from consuming all system resources.
        
        Args:
            self_terminate_on_critical: Whether to actually terminate
            max_processes: Maximum allowed processes before shutdown
        """
        logger.critical(
            f"EMERGENCY SHUTDOWN: Critical limits breached - "
            f"terminating process tree. "
            f"self_terminate={self_terminate_on_critical}"
        )
        
        # Safety check - only proceed if self-termination is explicitly enabled
        if not self_terminate_on_critical:
            logger.critical(
                "Self-termination is DISABLED - aborting emergency shutdown"
            )
            return
        
        try:
            # Step 1: Try graceful cleanup of other processes first
            cleanup_result = SystemWatchdog.emergency_cleanup()
            logger.info(f"Emergency cleanup: {cleanup_result}")
            
            # Step 2: Give processes time to terminate gracefully
            time.sleep(2)
            
            # Step 3: Check if we still have too many processes after cleanup
            # Create temporary instance just for metrics collection
            temp_watchdog = SystemWatchdog()
            current_metrics = temp_watchdog.get_current_metrics()
            if current_metrics.dinoair_processes > max_processes:
                logger.critical("Force terminating entire process tree")
                
                # Get current process and all its children (subprocess tree)
                current_process = psutil.Process(SystemWatchdog._current_pid)
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
                logger.critical(
                    "Self-terminating due to critical resource limits"
                )
                if self_terminate_on_critical:  # Double-check the flag
                    os._exit(1)  # Force exit without cleanup
                else:
                    logger.critical("Self-termination disabled - NOT exiting")
                
        except Exception as e:
            logger.critical(f"Error during emergency shutdown: {e}")
            if self_terminate_on_critical:
                os._exit(1)  # Force exit as absolute last resort
            else:
                logger.critical(
                    "Self-termination disabled - NOT exiting on error"
                )
    
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
            f"├─ DinoAir Processes: "
            f"{m.dinoair_processes}/{self.max_processes}\n"
            f"└─ Auto-Terminate: {terminate_status}"
        )


def main():
    """Test the watchdog from command line."""
    import signal
    import threading
    
    # Global flag for clean shutdown
    shutdown_requested = threading.Event()
    watchdog = None
    
    def signal_handler(signum, frame):
        """Handle signals gracefully."""
        print(f"\n🛑 Received signal {signum}, initiating shutdown...")
        shutdown_requested.set()
    
    def alert_handler(level: AlertLevel, message: str):
        """Handle alerts with colored console output."""
        color = {
            "info": "\033[36m",
            "warning": "\033[33m",
            "critical": "\033[31m"
        }
        reset = "\033[0m"
        timestamp = time.strftime("%H:%M:%S")
        level_color = color.get(level.value, '')
        print(
            f"[{timestamp}] {level_color}"
            f"{level.value.upper()}: {message}{reset}"
        )
    
    def metrics_handler(metrics: SystemMetrics):
        """Handle live metrics updates with compact display."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] 📊 VRAM {metrics.vram_percent:.1f}% | "
              f"RAM {metrics.ram_percent:.1f}% | "
              f"CPU {metrics.cpu_percent:.1f}% | "
              f"Procs {metrics.dinoair_processes}")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create watchdog with testing-friendly settings
        watchdog = SystemWatchdog(
            alert_callback=alert_handler,
            metrics_callback=metrics_handler,
            vram_threshold_percent=70.0,  # Lower threshold for testing
            max_dinoair_processes=3,      # Easier to hit for testing
            check_interval_seconds=5,     # More frequent checks for testing
            self_terminate_on_critical=False  # Disable for testing safety
        )
        
        print("🐕 Starting Enhanced System Watchdog")
        print("🔧 Features: ThreadPoolExecutor, Live Metrics, Self-Contained")
        print("💡 Press Ctrl+C to stop gracefully")
        print("=" * 60)
        
        # Start background monitoring
        watchdog.start_monitoring()
        
        # Non-blocking main loop with status reports every 15 seconds
        status_counter = 0
        while not shutdown_requested.is_set():
            # Use Event.wait() for responsive shutdown handling
            if shutdown_requested.wait(timeout=1.0):
                break
                
            status_counter += 1
            if status_counter >= 15:  # Show status every 15 seconds
                try:
                    print("\n" + watchdog.get_status_report())
                    print("-" * 40)
                    status_counter = 0
                except Exception as e:
                    logger.error(f"Error getting status report: {e}")
                    
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        
    finally:
        # Ensure clean shutdown
        print("\n🧹 Cleaning up...")
        if watchdog:
            try:
                watchdog.stop_monitoring()
                print("✅ Watchdog stopped cleanly")
            except Exception as e:
                logger.error(f"Error stopping watchdog: {e}")
        print("🏁 Test completed")


if __name__ == "__main__":
    # DinoAir's Logger handles its own configuration
    main()