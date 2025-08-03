# Qt-Compatible Threading Architecture for DinoAir 2.0 Watchdog System

## Executive Summary

This document presents a comprehensive architectural design to replace the current ThreadPoolExecutor-based watchdog implementation with a Qt-compatible QThread-based architecture. This resolves the threading conflicts that cause "QBasicTimer can only be used with threads started with QThread" errors while maintaining all current monitoring capabilities.

## Problem Analysis

### Current Issues
1. **Threading Conflict**: ThreadPoolExecutor creates standard Python threads that are incompatible with Qt's event loop
2. **Unsafe GUI Updates**: Direct callbacks from non-Qt threads can cause race conditions
3. **No Circuit Breaker**: Current implementation lacks protection against cascading failures
4. **Limited Error Recovery**: No automatic recovery mechanism for monitoring failures

### Current Implementation Overview
- Uses `concurrent.futures.ThreadPoolExecutor` for background monitoring
- Direct callbacks to GUI from worker thread
- Monitors: VRAM usage, CPU/RAM usage, DinoAir process count
- Emergency shutdown capability for runaway processes

## Proposed Architecture

### Core Design Principles
1. **Qt-Native Threading**: All background operations use QThread
2. **Signal/Slot Communication**: Thread-safe communication via Qt signals
3. **Graceful Degradation**: Circuit breaker pattern prevents cascading failures
4. **Automatic Recovery**: Self-healing mechanisms for transient failures
5. **Zero GUI Blocking**: All operations are fully asynchronous

## Class Architecture

```mermaid
classDiagram
    class QThread {
        <<Qt Framework>>
        +run()
        +start()
        +quit()
        +wait()
        +isRunning()
    }
    
    class WatchdogThread {
        -monitoring: bool
        -check_interval: int
        -circuit_breaker: CircuitBreaker
        -error_count: int
        +run()
        +stop_monitoring()
        +pause_monitoring()
        +resume_monitoring()
        +is_monitoring()
    }
    
    class WatchdogController {
        -thread: WatchdogThread
        -config: WatchdogConfig
        -metrics_buffer: MetricsBuffer
        +start_watchdog()
        +stop_watchdog()
        +restart_watchdog()
        +update_config()
        +get_status()
    }
    
    class CircuitBreaker {
        -state: BreakerState
        -failure_threshold: int
        -recovery_timeout: int
        -failure_count: int
        -last_failure_time: datetime
        +call()
        +record_success()
        +record_failure()
        +reset()
        +is_open()
    }
    
    class WatchdogSignals {
        <<QObject>>
        +metrics_ready: Signal[SystemMetrics]
        +alert_triggered: Signal[AlertLevel, str]
        +error_occurred: Signal[str]
        +status_changed: Signal[WatchdogStatus]
        +monitoring_started: Signal[]
        +monitoring_stopped: Signal[]
    }
    
    class MetricsCollector {
        -vram_monitor: VRAMMonitor
        -cpu_monitor: CPUMonitor
        -process_monitor: ProcessMonitor
        +collect_metrics()
        +get_vram_info()
        +get_cpu_info()
        +count_processes()
    }
    
    class WatchdogConfig {
        +vram_threshold: float
        +max_processes: int
        +check_interval: int
        +self_terminate: bool
        +circuit_breaker_config: dict
    }
    
    class WatchdogStatus {
        +is_running: bool
        +is_paused: bool
        +last_check: datetime
        +error_count: int
        +circuit_breaker_state: str
    }
    
    QThread <|-- WatchdogThread
    WatchdogThread --> WatchdogSignals : emits
    WatchdogThread --> MetricsCollector : uses
    WatchdogThread --> CircuitBreaker : uses
    WatchdogController --> WatchdogThread : manages
    WatchdogController --> WatchdogConfig : uses
    WatchdogController --> WatchdogSignals : connects
```

## Signal/Slot Interface Design

### Signal Definitions

```python
class WatchdogSignals(QObject):
    """Qt signals for thread-safe communication"""
    
    # Metrics updates
    metrics_ready = Signal(SystemMetrics)  # Regular metrics updates
    
    # Alert notifications
    alert_triggered = Signal(AlertLevel, str)  # Alert level and message
    
    # Error handling
    error_occurred = Signal(str)  # Error message
    circuit_breaker_opened = Signal(str)  # Reason for opening
    circuit_breaker_closed = Signal()  # Circuit breaker recovered
    
    # Status updates
    status_changed = Signal(WatchdogStatus)  # Overall status
    monitoring_started = Signal()
    monitoring_stopped = Signal()
    monitoring_paused = Signal()
    monitoring_resumed = Signal()
    
    # Process management
    cleanup_started = Signal(int)  # Number of processes to clean
    cleanup_completed = Signal(dict)  # Cleanup results
    emergency_shutdown_initiated = Signal(str)  # Reason
```

### Connection Pattern

```python
# In MainWindow or Controller
watchdog_controller.signals.metrics_ready.connect(
    self.metrics_widget.update_metrics, 
    Qt.QueuedConnection  # Ensures thread-safe GUI updates
)

watchdog_controller.signals.alert_triggered.connect(
    self.notification_widget.add_notification,
    Qt.QueuedConnection
)
```

## Sequence Diagrams

### Monitoring Loop Sequence

```mermaid
sequenceDiagram
    participant GUI as MainWindow
    participant Controller as WatchdogController
    participant Thread as WatchdogThread
    participant CB as CircuitBreaker
    participant Collector as MetricsCollector
    participant Signals as WatchdogSignals
    
    GUI->>Controller: start_watchdog()
    Controller->>Thread: start()
    Thread->>Signals: monitoring_started
    Signals-->>GUI: Update UI (queued)
    
    loop Monitoring Loop
        Thread->>CB: call(collect_metrics)
        CB->>CB: Check state
        alt Circuit Breaker Open
            CB-->>Thread: Raise CircuitBreakerOpen
            Thread->>Signals: circuit_breaker_opened
            Thread->>Thread: Wait recovery timeout
        else Circuit Breaker Closed
            CB->>Collector: collect_metrics()
            Collector-->>CB: SystemMetrics
            CB-->>Thread: SystemMetrics
            Thread->>Thread: Check thresholds
            alt Threshold Exceeded
                Thread->>Signals: alert_triggered
                Signals-->>GUI: Show alert (queued)
            end
            Thread->>Signals: metrics_ready
            Signals-->>GUI: Update metrics (queued)
            CB->>CB: record_success()
        end
        Thread->>Thread: Sleep(check_interval)
    end
```

### Error Handling Sequence

```mermaid
sequenceDiagram
    participant Thread as WatchdogThread
    participant CB as CircuitBreaker
    participant Signals as WatchdogSignals
    participant GUI as MainWindow
    
    Thread->>CB: call(collect_metrics)
    CB->>CB: Execute with protection
    alt Collection Fails
        CB->>CB: record_failure()
        CB->>CB: Check failure_threshold
        alt Threshold Reached
            CB->>CB: Open circuit breaker
            CB-->>Thread: CircuitBreakerOpen
            Thread->>Signals: circuit_breaker_opened
            Signals-->>GUI: Show error notification
            Thread->>Thread: Enter recovery mode
            Thread->>Thread: Wait recovery_timeout
            Thread->>CB: Attempt reset
            alt Recovery Successful
                CB->>CB: Close circuit breaker
                Thread->>Signals: circuit_breaker_closed
                Thread->>Thread: Resume normal monitoring
            else Recovery Failed
                Thread->>Thread: Extend recovery timeout
            end
        else Below Threshold
            CB-->>Thread: Exception
            Thread->>Signals: error_occurred
            Thread->>Thread: Continue monitoring
        end
    end
```

### Graceful Shutdown Sequence

```mermaid
sequenceDiagram
    participant GUI as MainWindow
    participant Controller as WatchdogController
    participant Thread as WatchdogThread
    participant Signals as WatchdogSignals
    
    GUI->>Controller: stop_watchdog()
    Controller->>Thread: stop_monitoring()
    Thread->>Thread: Set monitoring=False
    Thread->>Thread: Break monitoring loop
    alt Currently collecting metrics
        Thread->>Thread: Wait for collection to complete
    end
    Thread->>Signals: monitoring_stopped
    Signals-->>GUI: Update UI (queued)
    Thread->>Thread: Cleanup resources
    Thread-->>Controller: Thread finished
    Controller->>Thread: wait(timeout=5000)
    alt Thread exits cleanly
        Controller-->>GUI: Success
    else Timeout
        Controller->>Thread: terminate()
        Controller-->>GUI: Forced termination
    end
```

## Circuit Breaker Pattern Implementation

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Closed: Initial State
    Closed --> Open: Failure threshold reached
    Open --> HalfOpen: Recovery timeout elapsed
    HalfOpen --> Closed: Test request succeeds
    HalfOpen --> Open: Test request fails
    Open --> Open: Request rejected
    Closed --> Closed: Request succeeds
```

### Configuration

```python
class CircuitBreakerConfig:
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before trying again
    success_threshold: int = 3  # Successes to fully close
    timeout: float = 5.0  # Operation timeout
```

## Thread-Safe Shutdown Mechanism

### Design Features

1. **Graceful Termination**: Stop flag checked between operations
2. **Timeout Protection**: Maximum wait time for thread termination
3. **Resource Cleanup**: Ensures all resources are properly released
4. **State Persistence**: Save current state before shutdown

### Implementation Strategy

```python
class WatchdogThread(QThread):
    def __init__(self):
        super().__init__()
        self._monitoring = False
        self._pause_event = QEvent()
        self._stop_event = QEvent()
        
    def stop_monitoring(self):
        """Thread-safe stop mechanism"""
        self._monitoring = False
        self._stop_event.set()
        # Wake up if sleeping
        self.requestInterruption()
        
    def run(self):
        while self._monitoring:
            if self.isInterruptionRequested():
                break
            # Monitoring logic here
            # Use interruptible sleep
            if not self._stop_event.wait(self.check_interval):
                continue
```

## Error Recovery Strategy

### Recovery Levels

1. **Transient Errors**: Automatic retry with exponential backoff
2. **Persistent Errors**: Circuit breaker activation
3. **Critical Errors**: Graceful degradation with limited functionality
4. **Fatal Errors**: Clean shutdown with state preservation

### Recovery Actions

```python
class ErrorRecoveryStrategy:
    def handle_vram_error(self):
        # Fall back to estimation
        return self.estimate_vram_usage()
        
    def handle_process_count_error(self):
        # Use cached value with warning
        return self.last_known_process_count
        
    def handle_critical_error(self):
        # Save state and prepare for restart
        self.save_monitoring_state()
        self.signals.error_occurred.emit("Critical error - preparing restart")
```

## Migration Strategy

### Phase 1: Preparation
1. Create new QThread-based classes alongside existing code
2. Implement signal/slot interface
3. Add compatibility layer for existing callbacks

### Phase 2: Parallel Implementation
1. Implement WatchdogThread with same interface
2. Add feature toggle for new implementation
3. Run both implementations in test environment

### Phase 3: Migration
1. Update MainWindow to use new signal connections
2. Replace ThreadPoolExecutor initialization with WatchdogController
3. Update configuration handling
4. Migrate callbacks to signal/slot connections

### Phase 4: Cleanup
1. Remove old ThreadPoolExecutor implementation
2. Remove compatibility layer
3. Update documentation and tests

### Code Changes Required

1. **src/utils/Watchdog.py**
   - Keep SystemMetrics and AlertLevel
   - Remove ThreadPoolExecutor usage
   - Add QThread base class imports

2. **src/utils/watchdog_qt.py** (new file)
   - Implement WatchdogThread
   - Implement WatchdogController
   - Implement CircuitBreaker

3. **src/gui/main_window.py**
   - Update watchdog initialization
   - Connect signals instead of callbacks
   - Remove direct callback methods

4. **src/gui/components/metrics_widget.py**
   - Already has @Slot decorator - no changes needed

## Configuration Interface

```python
# Backward compatible configuration
watchdog_config = {
    'vram_threshold_percent': 95.0,
    'max_dinoair_processes': 5,
    'check_interval_seconds': 30,
    'self_terminate_on_critical': False,
    # New circuit breaker config
    'circuit_breaker': {
        'failure_threshold': 5,
        'recovery_timeout': 60,
        'success_threshold': 3
    },
    # New recovery config
    'error_recovery': {
        'max_retries': 3,
        'retry_delay': 5,
        'fallback_mode': True
    }
}
```

## Benefits of New Architecture

1. **Thread Safety**: All GUI updates through Qt's signal/slot mechanism
2. **Reliability**: Circuit breaker prevents cascade failures
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Easy to mock signals for unit testing
5. **Performance**: Non-blocking operations with proper event handling
6. **Flexibility**: Easy to add new metrics or alerts
7. **Debugging**: Better error messages and state tracking

## Summary

This architecture provides a robust, Qt-compatible solution that:
- Eliminates threading conflicts with Qt's event loop
- Provides thread-safe communication via signals/slots
- Implements circuit breaker pattern for fault tolerance
- Includes comprehensive error recovery mechanisms
- Supports graceful shutdown and restart
- Maintains backward compatibility during migration
- Improves overall system reliability and maintainability

The design ensures the watchdog system can monitor resources effectively while integrating seamlessly with the Qt-based GUI, providing a superior user experience with real-time updates and proper error handling.