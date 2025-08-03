"""Qt-based watchdog threading system for DinoAir 2.0.

This module provides a Qt-compatible watchdog implementation that replaces
the ThreadPoolExecutor-based system with QThread to avoid threading conflicts.

Enhanced with comprehensive error recovery and graceful degradation.
"""

import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass, field
from collections import deque
from PySide6.QtCore import (
    QObject, Signal, QThread, Qt, QMutex, QWaitCondition, QMutexLocker,
    QTimer
)

# Import the existing Watchdog module for SystemMetrics and AlertLevel
from .Watchdog import SystemMetrics, AlertLevel
from .logger import Logger

logger = Logger()


class ComponentHealth(Enum):
    """Component health states."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass
class MetricsFallback:
    """Fallback values for metrics when collection fails."""
    vram_used_mb: float = 0.0
    vram_total_mb: float = 8192.0  # 8GB default
    vram_percent: float = 0.0
    cpu_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_percent: float = 0.0
    process_count: int = 0
    dinoair_processes: int = 1  # Assume at least one
    uptime_seconds: int = 0
    
    # Cache of last known good values
    last_good_metrics: Optional[SystemMetrics] = None
    last_update_time: Optional[datetime] = None
    

@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class HealthCheckResult:
    """Result of a component health check."""
    component: str
    status: ComponentHealth
    message: str
    last_success: Optional[datetime] = None
    failure_count: int = 0
    recovery_attempts: int = 0


class BreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class WatchdogStatus:
    """Status information for the watchdog system."""
    is_running: bool
    is_paused: bool
    last_check: Optional[datetime]
    error_count: int
    circuit_breaker_state: str
    component_health: Dict[str, ComponentHealth] = field(default_factory=dict)
    metrics_cache_age: Optional[int] = None  # Seconds since last update


@dataclass
class WatchdogConfig:
    """Configuration for the watchdog system."""
    vram_threshold: float = 95.0
    max_processes: int = 5
    check_interval: int = 30
    self_terminate: bool = False
    circuit_breaker_config: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.circuit_breaker_config is None:
            self.circuit_breaker_config = {
                'failure_threshold': 5,
                'recovery_timeout': 60,
                'success_threshold': 3,
                'timeout': 5.0
            }


class WatchdogSignals(QObject):
    """Qt signals for thread-safe communication from watchdog thread."""
    
    # Metrics updates
    metrics_ready = Signal(SystemMetrics)  # Regular metrics updates
    metrics_degraded = Signal(SystemMetrics, str)  # Degraded metrics w/reason
    
    # Alert notifications
    alert_triggered = Signal(AlertLevel, str)  # Alert level and message
    
    # Error handling
    error_occurred = Signal(str)  # Error message
    error_recovered = Signal(str)  # Recovery message
    circuit_breaker_opened = Signal(str)  # Reason for opening
    circuit_breaker_closed = Signal()  # Circuit breaker recovered
    
    # Status updates
    status_changed = Signal(WatchdogStatus)  # Overall status
    monitoring_started = Signal()
    monitoring_stopped = Signal()
    monitoring_paused = Signal()
    monitoring_resumed = Signal()
    
    # Health monitoring
    health_check_completed = Signal(dict)  # Component health statuses
    # Component health: name, status, message
    component_health_changed = Signal(str, ComponentHealth, str)
    
    # Process management
    cleanup_started = Signal(int)  # Number of processes to clean
    cleanup_completed = Signal(dict)  # Cleanup results
    emergency_shutdown_initiated = Signal(str)  # Reason


class CircuitBreaker:
    """Circuit breaker pattern implementation for fault tolerance."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 success_threshold: int = 3,
                 timeout: float = 5.0):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Successes needed to close from half-open
            timeout: Max time for protected operations
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        # State tracking
        self._state = BreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._mutex = QMutex()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func if successful
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: If func raises an exception
        """
        with QMutexLocker(self._mutex):
            # Check if we should attempt recovery
            if self._state == BreakerState.OPEN:
                if self._should_attempt_recovery():
                    self._state = BreakerState.HALF_OPEN
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise CircuitBreakerOpen("Circuit breaker is open")
        
        # Try to execute the function
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise
            
    def record_success(self):
        """Record a successful operation."""
        with QMutexLocker(self._mutex):
            self._failure_count = 0
            
            if self._state == BreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = BreakerState.CLOSED
                    self._success_count = 0
                    logger.info("Circuit breaker closed after recovery")
                    
    def record_failure(self):
        """Record a failed operation."""
        with QMutexLocker(self._mutex):
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            
            if self._failure_count >= self.failure_threshold:
                self._state = BreakerState.OPEN
                logger.warning(
                    f"Circuit breaker opened after "
                    f"{self._failure_count} failures"
                )
                
            # Reset success count on any failure in half-open state
            if self._state == BreakerState.HALF_OPEN:
                self._success_count = 0
                
    def reset(self):
        """Reset circuit breaker to initial state."""
        with QMutexLocker(self._mutex):
            self._state = BreakerState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        with QMutexLocker(self._mutex):
            return self._state == BreakerState.OPEN
            
    def get_state(self) -> str:
        """Get current state as string."""
        with QMutexLocker(self._mutex):
            return self._state.value
            
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
            
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class WatchdogThread(QThread):
    """Qt thread for system monitoring with circuit breaker protection."""
    
    def __init__(self, config: WatchdogConfig, parent=None):
        """Initialize watchdog thread.
        
        Args:
            config: Watchdog configuration
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.config = config
        self.signals = WatchdogSignals()
        
        # Thread control
        self._monitoring = False
        self._paused = False
        self._pause_mutex = QMutex()
        self._pause_condition = QWaitCondition()
        
        # Circuit breaker for fault tolerance
        cb_config = config.circuit_breaker_config or {}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=cb_config.get('failure_threshold', 5),
            recovery_timeout=cb_config.get('recovery_timeout', 60),
            success_threshold=cb_config.get('success_threshold', 3),
            timeout=cb_config.get('timeout', 5.0)
        )
        
        # Monitoring state
        self.error_count = 0
        self.consecutive_failures = 0
        self.last_check_time = None
        self._startup_time = time.time()
        
        # Retry configuration
        self.retry_config = RetryConfig()
        self._retry_delays = {}  # Track retry delays per operation
        
        # Metrics fallback and caching
        self.fallback = MetricsFallback()
        self._metrics_history = deque(maxlen=10)  # Keep last 10 metrics
        
        # Component health tracking
        self.component_health = {
            'vram_collector': HealthCheckResult(
                'vram_collector', ComponentHealth.UNKNOWN, 'Not checked'
            ),
            'cpu_collector': HealthCheckResult(
                'cpu_collector', ComponentHealth.UNKNOWN, 'Not checked'
            ),
            'process_counter': HealthCheckResult(
                'process_counter', ComponentHealth.UNKNOWN, 'Not checked'
            ),
            'metrics_aggregator': HealthCheckResult(
                'metrics_aggregator', ComponentHealth.UNKNOWN, 'Not checked'
            )
        }
        
        # Import SystemWatchdog for metrics collection
        from .Watchdog import SystemWatchdog
        self._watchdog_instance = SystemWatchdog()
        
        # Health check timer
        self._health_check_timer = QTimer()
        self._health_check_timer.timeout.connect(self._perform_health_check)
        self._health_check_timer.start(60000)  # Health check every minute
        
    def run(self):
        """Main monitoring loop running in the Qt thread."""
        logger.info("Qt watchdog thread started")
        self._monitoring = True
        self.signals.monitoring_started.emit()
        
        while self._monitoring:
            # Check if paused
            with QMutexLocker(self._pause_mutex):
                while self._paused and self._monitoring:
                    self._pause_condition.wait(self._pause_mutex)
                    
            if not self._monitoring:
                break
                
            try:
                # Collect metrics with circuit breaker protection
                metrics = self._collect_metrics_with_protection()
                
                if metrics:
                    self.last_check_time = datetime.now()
                    
                    # Emit metrics for GUI update
                    self.signals.metrics_ready.emit(metrics)
                    
                    # Check thresholds and emit alerts
                    self._check_thresholds(metrics)
                    
                    # Update status
                    self._emit_status_update()
                    
            except CircuitBreakerOpen:
                logger.warning(
                    "Circuit breaker is open, skipping metrics collection"
                )
                self.signals.circuit_breaker_opened.emit(
                    "Too many errors collecting metrics"
                )
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Error in watchdog thread: {e}")
                self.signals.error_occurred.emit(str(e))
                
            # Interruptible sleep
            if not self._interruptible_sleep(self.config.check_interval):
                break
                
        self.signals.monitoring_stopped.emit()
        logger.info("Qt watchdog thread stopped")
        
    def _collect_metrics_with_protection(self) -> Optional[SystemMetrics]:
        """Collect metrics with protection and graceful degradation."""
        try:
            # Use circuit breaker to protect metrics collection
            metrics = self.circuit_breaker.call(
                self._collect_metrics_with_retry
            )
            
            # Update uptime based on thread's startup time
            uptime_seconds = int(time.time() - self._startup_time)
            metrics.uptime_seconds = uptime_seconds
            
            # Cache successful metrics
            self.fallback.last_good_metrics = metrics
            self.fallback.last_update_time = datetime.now()
            self._metrics_history.append(metrics)
            
            # Reset error counters on success
            if self.error_count > 0 or self.consecutive_failures > 0:
                self.error_count = 0
                self.consecutive_failures = 0
                self.signals.circuit_breaker_closed.emit()
                self.signals.error_recovered.emit(
                    "Metrics collection recovered"
                )
                
            # Update component health
            self._update_component_health(
                'metrics_aggregator', ComponentHealth.HEALTHY,
                "All metrics collected successfully"
            )
                
            return metrics
            
        except CircuitBreakerOpen:
            # Re-raise to handle at higher level
            raise
            
        except Exception as e:
            # Circuit breaker will record failure
            logger.error(f"Failed to collect metrics: {e}")
            self.error_count += 1
            self.consecutive_failures += 1
            
            # Try to use cached or estimated metrics
            return self._get_fallback_metrics(str(e))
            
    def _collect_metrics_with_retry(self) -> SystemMetrics:
        """Collect metrics with retry and per-component error handling."""
        retry_count = 0
        last_error = None
        
        while retry_count < self.retry_config.max_retries:
            try:
                # Collect each metric type with individual error handling
                vram_info = self._collect_vram_with_fallback()
                cpu_info = self._collect_cpu_with_fallback()
                ram_info = self._collect_ram_with_fallback()
                process_info = self._collect_processes_with_fallback()
                
                # Aggregate into SystemMetrics
                metrics = SystemMetrics(
                    vram_used_mb=vram_info[0],
                    vram_total_mb=vram_info[1],
                    vram_percent=vram_info[2],
                    cpu_percent=cpu_info,
                    ram_used_mb=ram_info[0],
                    ram_percent=ram_info[1],
                    process_count=process_info[0],
                    dinoair_processes=process_info[1],
                    uptime_seconds=int(time.time() - self._startup_time)
                )
                
                return metrics
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count < self.retry_config.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self._calculate_retry_delay(
                        'metrics_collection', retry_count
                    )
                    logger.warning(
                        f"Metrics collection attempt {retry_count} failed, "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)
                    
        # All retries failed
        raise Exception(
            f"Metrics collection failed after {retry_count} "
            f"attempts: {last_error}"
        )
        
    def _collect_vram_with_fallback(self) -> tuple[float, float, float]:
        """Collect VRAM info with error handling and fallback."""
        try:
            result = self._watchdog_instance._get_vram_info()
            vram_used, vram_total, vram_percent = result
            self._update_component_health(
                'vram_collector', ComponentHealth.HEALTHY,
                "VRAM metrics collected"
            )
            return vram_used, vram_total, vram_percent
            
        except Exception as e:
            self._update_component_health(
                'vram_collector', ComponentHealth.DEGRADED,
                f"VRAM collection failed: {e}"
            )
            
            # Use cached values if available
            if self.fallback.last_good_metrics:
                logger.warning("Using cached VRAM values")
                m = self.fallback.last_good_metrics
                return m.vram_used_mb, m.vram_total_mb, m.vram_percent
            else:
                # Use safe defaults
                logger.warning("Using default VRAM values")
                return (self.fallback.vram_used_mb,
                        self.fallback.vram_total_mb,
                        self.fallback.vram_percent)
                       
    def _collect_cpu_with_fallback(self) -> float:
        """Collect CPU info with error handling and fallback."""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self._update_component_health(
                'cpu_collector', ComponentHealth.HEALTHY,
                "CPU metrics collected"
            )
            return cpu_percent
            
        except Exception as e:
            self._update_component_health(
                'cpu_collector', ComponentHealth.DEGRADED,
                f"CPU collection failed: {e}"
            )
            
            # Try to estimate from historical data
            if self._metrics_history:
                total_cpu = sum(m.cpu_percent for m in self._metrics_history)
                avg_cpu = total_cpu / len(self._metrics_history)
                logger.warning(f"Using estimated CPU value: {avg_cpu:.1f}%")
                return avg_cpu
            else:
                return self.fallback.cpu_percent
                
    def _collect_ram_with_fallback(self) -> tuple[float, float]:
        """Collect RAM info with error handling and fallback."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            ram_used_mb = (memory.total - memory.available) / (1024 * 1024)
            ram_percent = memory.percent
            return ram_used_mb, ram_percent
            
        except Exception as e:
            logger.error(f"RAM collection failed: {e}")
            
            if self.fallback.last_good_metrics:
                m = self.fallback.last_good_metrics
                return m.ram_used_mb, m.ram_percent
            else:
                return self.fallback.ram_used_mb, self.fallback.ram_percent
                
    def _collect_processes_with_fallback(self) -> tuple[int, int]:
        """Collect process info with error handling and fallback."""
        try:
            import psutil
            total_processes = len(psutil.pids())
            dinoair_count = self._watchdog_instance._count_dinoair_processes()
            
            self._update_component_health(
                'process_counter', ComponentHealth.HEALTHY,
                "Process count successful"
            )
            return total_processes, dinoair_count
            
        except Exception as e:
            self._update_component_health(
                'process_counter', ComponentHealth.DEGRADED,
                f"Process counting failed: {e}"
            )
            
            # Use last known values or safe defaults
            if self.fallback.last_good_metrics:
                m = self.fallback.last_good_metrics
                return m.process_count, m.dinoair_processes
            else:
                return (self.fallback.process_count,
                        self.fallback.dinoair_processes)
                
    def _calculate_retry_delay(self, operation: str,
                               retry_count: int) -> float:
        """Calculate retry delay with exponential backoff and jitter."""
        base_delay = self.retry_config.initial_delay * (
            self.retry_config.backoff_factor ** (retry_count - 1)
        )
        
        # Cap at max delay
        delay = min(base_delay, self.retry_config.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            import random
            jitter = random.uniform(0, delay * 0.1)  # Up to 10% jitter
            delay += jitter
            
        # Track delay for this operation
        self._retry_delays[operation] = delay
        
        return delay
        
    def _get_fallback_metrics(self,
                              error_reason: str) -> Optional[SystemMetrics]:
        """Get fallback metrics when collection fails."""
        # Check if we have cached metrics
        if self.fallback.last_good_metrics and self.fallback.last_update_time:
            delta = datetime.now() - self.fallback.last_update_time
            age_seconds = delta.total_seconds()
            
            if age_seconds < 300:  # Use cache if less than 5 minutes old
                logger.warning(
                    f"Using cached metrics (age: {age_seconds:.0f}s) "
                    f"due to: {error_reason}"
                )
                
                # Update uptime with current value
                cached = self.fallback.last_good_metrics
                current_uptime = int(time.time() - self._startup_time)
                
                # Create new metrics with updated uptime
                metrics = SystemMetrics(
                    vram_used_mb=cached.vram_used_mb,
                    vram_total_mb=cached.vram_total_mb,
                    vram_percent=cached.vram_percent,
                    cpu_percent=cached.cpu_percent,
                    ram_used_mb=cached.ram_used_mb,
                    ram_percent=cached.ram_percent,
                    process_count=cached.process_count,
                    dinoair_processes=cached.dinoair_processes,
                    uptime_seconds=current_uptime
                )
                
                self.signals.metrics_degraded.emit(
                    metrics,
                    f"Using cached data due to error: {error_reason}"
                )
                return metrics
                
        # No cache or cache too old - use safe defaults
        logger.warning(f"Using default metrics due to: {error_reason}")
        
        default_metrics = SystemMetrics(
            vram_used_mb=self.fallback.vram_used_mb,
            vram_total_mb=self.fallback.vram_total_mb,
            vram_percent=self.fallback.vram_percent,
            cpu_percent=self.fallback.cpu_percent,
            ram_used_mb=self.fallback.ram_used_mb,
            ram_percent=self.fallback.ram_percent,
            process_count=self.fallback.process_count,
            dinoair_processes=self.fallback.dinoair_processes,
            uptime_seconds=int(time.time() - self._startup_time)
        )
        
        self.signals.metrics_degraded.emit(
            default_metrics,
            f"Using default values due to error: {error_reason}"
        )
        return default_metrics
        
    def _update_component_health(self, component: str,
                                 status: ComponentHealth, message: str):
        """Update health status of a component."""
        if component in self.component_health:
            health_result = self.component_health[component]
            old_status = health_result.status
            
            health_result.status = status
            health_result.message = message
            
            if status == ComponentHealth.HEALTHY:
                health_result.last_success = datetime.now()
                health_result.failure_count = 0
                health_result.recovery_attempts = 0
            elif status in (ComponentHealth.DEGRADED, ComponentHealth.FAILED):
                health_result.failure_count += 1
            elif status == ComponentHealth.RECOVERING:
                health_result.recovery_attempts += 1
                
            # Emit signal if status changed
            if old_status != status:
                self.signals.component_health_changed.emit(
                    component, status, message
                )
                
    def _perform_health_check(self):
        """Perform comprehensive health check of all components."""
        try:
            health_summary = {}
            
            for component, health in self.component_health.items():
                health_summary[component] = {
                    'status': health.status.value,
                    'message': health.message,
                    'failure_count': health.failure_count,
                    'last_success': (health.last_success.isoformat()
                                     if health.last_success else None)
                }
                
            self.signals.health_check_completed.emit(health_summary)
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            
    def _check_thresholds(self, metrics: SystemMetrics):
        """Check metrics against configured thresholds."""
        # Check VRAM usage
        if metrics.vram_percent > self.config.vram_threshold:
            self.signals.alert_triggered.emit(
                AlertLevel.WARNING,
                f"High VRAM usage: {metrics.vram_percent:.1f}% "
                f"({metrics.vram_used_mb:.0f}MB / "
                f"{metrics.vram_total_mb:.0f}MB)"
            )
            
        # Check process count - CRITICAL
        if metrics.dinoair_processes > self.config.max_processes:
            self.signals.alert_triggered.emit(
                AlertLevel.CRITICAL,
                f"Too many DinoAir processes: {metrics.dinoair_processes} "
                f"(limit: {self.config.max_processes})"
            )
            
            # Handle emergency shutdown if configured
            if self.config.self_terminate:
                self._handle_emergency_shutdown(metrics)
                
        # Check RAM usage
        if metrics.ram_percent > 90:
            self.signals.alert_triggered.emit(
                AlertLevel.WARNING,
                f"High RAM usage: {metrics.ram_percent:.1f}% "
                f"({metrics.ram_used_mb:.0f}MB)"
            )
            
        # Critical RAM usage
        if metrics.ram_percent > 95:
            self.signals.alert_triggered.emit(
                AlertLevel.CRITICAL,
                f"Critical RAM usage: {metrics.ram_percent:.1f}% - "
                f"System may become unstable"
            )
            
        # Check CPU usage
        if metrics.cpu_percent > 80:
            self.signals.alert_triggered.emit(
                AlertLevel.WARNING,
                f"High CPU usage: {metrics.cpu_percent:.1f}%"
            )
            
    def _handle_emergency_shutdown(self, metrics: SystemMetrics):
        """Handle emergency shutdown for runaway processes."""
        logger.critical(
            f"Emergency shutdown triggered: "
            f"{metrics.dinoair_processes} processes"
        )
        self.signals.emergency_shutdown_initiated.emit(
            f"Process limit exceeded: {metrics.dinoair_processes}"
        )
        
        # Emit cleanup started signal
        self.signals.cleanup_started.emit(metrics.dinoair_processes)
        
        try:
            # Perform cleanup using existing watchdog instance
            cleanup_result = self._watchdog_instance.emergency_cleanup()
            self.signals.cleanup_completed.emit(cleanup_result)
            
            # If still over limit after cleanup, perform full shutdown
            time.sleep(2)  # Give processes time to terminate
            
            # Re-check process count
            new_metrics = self._watchdog_instance.get_current_metrics()
            if new_metrics.dinoair_processes > self.config.max_processes:
                logger.critical(
                    "Emergency cleanup failed, performing full shutdown"
                )
                self._watchdog_instance._perform_emergency_shutdown()
                
        except Exception as e:
            logger.error(f"Error during emergency shutdown: {e}")
            
    def _emit_status_update(self):
        """Emit current watchdog status."""
        # Calculate metrics cache age
        cache_age = None
        if self.fallback.last_update_time:
            delta = datetime.now() - self.fallback.last_update_time
            cache_age = int(delta.total_seconds())
            
        # Collect component health states
        component_health_states = {
            name: health.status
            for name, health in self.component_health.items()
        }
        
        status = WatchdogStatus(
            is_running=self._monitoring,
            is_paused=self._paused,
            last_check=self.last_check_time,
            error_count=self.error_count,
            circuit_breaker_state=self.circuit_breaker.get_state(),
            component_health=component_health_states,
            metrics_cache_age=cache_age
        )
        self.signals.status_changed.emit(status)
        
    def _interruptible_sleep(self, seconds: int) -> bool:
        """Sleep that can be interrupted by thread termination.
        
        Args:
            seconds: Number of seconds to sleep
            
        Returns:
            True if sleep completed normally, False if interrupted
        """
        # Use QThread's sleep with interruption checking
        for _ in range(seconds):
            if not self._monitoring or self.isInterruptionRequested():
                return False
            self.sleep(1)  # Sleep 1 second at a time
        return True
        
    def stop_monitoring(self):
        """Stop the monitoring thread gracefully."""
        logger.info("Stopping Qt watchdog thread...")
        self._monitoring = False
        
        # Stop health check timer
        if hasattr(self, '_health_check_timer'):
            self._health_check_timer.stop()
        
        # Wake up if paused
        with QMutexLocker(self._pause_mutex):
            self._paused = False
            self._pause_condition.wakeAll()
            
        # Request interruption to wake from sleep
        self.requestInterruption()
        
    def pause_monitoring(self):
        """Pause monitoring without stopping the thread."""
        with QMutexLocker(self._pause_mutex):
            if not self._paused:
                self._paused = True
                self.signals.monitoring_paused.emit()
                logger.info("Watchdog monitoring paused")
                
    def resume_monitoring(self):
        """Resume monitoring after pause."""
        with QMutexLocker(self._pause_mutex):
            if self._paused:
                self._paused = False
                self._pause_condition.wakeAll()
                self.signals.monitoring_resumed.emit()
                logger.info("Watchdog monitoring resumed")
                
    def is_monitoring(self) -> bool:
        """Check if actively monitoring (not paused)."""
        with QMutexLocker(self._pause_mutex):
            return self._monitoring and not self._paused


class WatchdogController(QObject):
    """High-level controller for the watchdog system."""
    
    def __init__(self, config: Optional[WatchdogConfig] = None, parent=None):
        """Initialize watchdog controller.
        
        Args:
            config: Watchdog configuration (uses defaults if None)
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.config = config or WatchdogConfig()
        self._thread: Optional[WatchdogThread] = None
        self.signals: Optional[WatchdogSignals] = None
        
        # Metrics buffering for performance
        self._metrics_buffer = []
        self._buffer_size = 10
        
    def start_watchdog(self):
        """Start the watchdog monitoring thread."""
        if self._thread and self._thread.isRunning():
            logger.warning("Watchdog already running")
            return
            
        logger.info("Starting Qt-based watchdog controller")
        
        # Create and configure thread
        self._thread = WatchdogThread(self.config)
        self.signals = self._thread.signals
        
        # Connect internal handlers
        self._thread.signals.metrics_ready.connect(
            self._buffer_metrics, Qt.ConnectionType.QueuedConnection
        )
        
        # Start the thread
        self._thread.start()
        
    def stop_watchdog(self, timeout_ms: int = 5000) -> bool:
        """Stop the watchdog monitoring thread.
        
        Args:
            timeout_ms: Maximum time to wait for thread to stop
            
        Returns:
            True if stopped successfully, False if timeout
        """
        if not self._thread:
            return True
            
        logger.info("Stopping watchdog controller")
        
        # Signal thread to stop
        self._thread.stop_monitoring()
        
        # Wait for thread to finish
        if self._thread.wait(timeout_ms):
            logger.info("Watchdog thread stopped successfully")
            self._thread = None
            self.signals = None
            return True
        else:
            logger.error("Watchdog thread failed to stop within timeout")
            # Force terminate as last resort
            self._thread.terminate()
            self._thread.wait()
            self._thread = None
            self.signals = None
            return False
            
    def restart_watchdog(self):
        """Restart the watchdog (stop and start)."""
        logger.info("Restarting watchdog")
        self.stop_watchdog()
        self.start_watchdog()
        
    def update_config(self, config: WatchdogConfig):
        """Update watchdog configuration.
        
        Args:
            config: New configuration to apply
        """
        self.config = config
        
        # If running, restart with new config
        if self._thread and self._thread.isRunning():
            self.restart_watchdog()
            
    def get_status(self) -> Optional[WatchdogStatus]:
        """Get current watchdog status.
        
        Returns:
            Current status or None if not running
        """
        if not self._thread:
            return None
            
        return WatchdogStatus(
            is_running=self._thread.isRunning(),
            is_paused=not self._thread.is_monitoring(),
            last_check=self._thread.last_check_time,
            error_count=self._thread.error_count,
            circuit_breaker_state=self._thread.circuit_breaker.get_state()
        )
        
    def pause_monitoring(self):
        """Pause monitoring without stopping thread."""
        if self._thread:
            self._thread.pause_monitoring()
            
    def resume_monitoring(self):
        """Resume monitoring after pause."""
        if self._thread:
            self._thread.resume_monitoring()
            
    def _buffer_metrics(self, metrics: SystemMetrics):
        """Buffer metrics for batch processing.
        
        Args:
            metrics: Metrics to buffer
        """
        self._metrics_buffer.append(metrics)
        
        # Flush buffer if full
        if len(self._metrics_buffer) >= self._buffer_size:
            self._flush_metrics_buffer()
            
    def _flush_metrics_buffer(self):
        """Flush buffered metrics."""
        if not self._metrics_buffer:
            return
            
        # Process buffered metrics (e.g., save to database)
        # This is where you would integrate with the metrics storage
        
        self._metrics_buffer.clear()