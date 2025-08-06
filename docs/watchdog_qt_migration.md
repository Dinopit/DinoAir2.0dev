# Watchdog Qt Migration Guide

## Overview
This document describes the migration of DinoAir 2.0's watchdog system from ThreadPoolExecutor to Qt-based implementation to resolve "QBasicTimer can only be used with threads started with QThread" errors.

## Migration Strategy
The migration uses the `WatchdogCompatibilityAdapter` from `src/utils/watchdog_compat.py` which provides:
- Seamless API compatibility with the original `SystemWatchdog`
- Automatic fallback to legacy implementation if Qt fails
- Signal-based communication instead of direct callbacks
- Thread-safe metrics updates via Qt's event system

## Changes Made

### 1. Main Application (main.py)
- Added `watchdog` attribute to `DinoAirApp` class
- Created `initialize_watchdog()` method that:
  - Uses `WatchdogCompatibilityAdapter` instead of `SystemWatchdog`
  - Connects Qt signals to MainWindow handlers
  - Provides automatic fallback if Qt initialization fails
- Updated `create_main_window()` to initialize watchdog after GUI creation
- Added watchdog cleanup in `cleanup()` method

### 2. MainWindow (src/gui/main_window.py)
- Updated `watchdog_alert_handler` and `watchdog_metrics_handler` documentation to reflect Qt signal connections
- Modified `handle_watchdog_config_change` to support both Qt and legacy configurations
- Enhanced `_start_watchdog` and `_stop_watchdog` with Qt-aware monitoring checks
- Made the system compatible with both implementations transparently

### 3. Settings Page (src/gui/pages/settings_page.py)
- Updated `_update_status_display` to check monitoring status for both implementations
- Added display of current implementation mode (qt/legacy/fallback)
- Modified status checking to support Qt-based watchdog controller
- Maintained full compatibility with existing UI

## Benefits

1. **Thread Safety**: All metrics updates now go through Qt's signal/slot system
2. **No Timer Conflicts**: Eliminates QBasicTimer errors by using QThread
3. **Automatic Fallback**: Falls back to legacy implementation if Qt initialization fails
4. **Enhanced Monitoring**: Additional signals for error handling and status updates
5. **Circuit Breaker**: Built-in fault tolerance with automatic recovery
6. **Zero Breaking Changes**: Maintains 100% API compatibility

## Configuration
The watchdog configuration remains unchanged:
```json
{
  "watchdog": {
    "enabled": true,
    "vram_threshold_percent": 95.0,
    "max_dinoair_processes": 5,
    "check_interval_seconds": 30,
    "self_terminate_on_critical": false
  }
}
```

## Testing
Run the included test script to verify the migration:
```bash
python test_watchdog_migration.py
```

## Implementation Details

### WatchdogCompatibilityAdapter
The adapter provides:
- Transparent API compatibility with `SystemWatchdog`
- Automatic mode detection and switching
- Three operational modes:
  - **Qt Mode**: Uses Qt-based threading (default)
  - **Legacy Mode**: Falls back to ThreadPoolExecutor
  - **Fallback Mode**: Simplified monitoring as last resort

### Qt Signal Connections
Instead of direct callbacks, the Qt implementation uses signals:
- `alert_triggered(AlertLevel, str)`: For watchdog alerts
- `metrics_ready(SystemMetrics)`: For metrics updates
- `error_occurred(str)`: For error reporting
- `monitoring_started/stopped()`: For status updates

### Error Recovery
The system includes multiple layers of error recovery:
1. Circuit breaker pattern for fault tolerance
2. Automatic fallback to legacy implementation
3. Metrics caching for temporary failures
4. Health monitoring for all components

## Rollback
If issues occur, the system automatically falls back to the legacy implementation. To force legacy mode:
```python
# In main.py, replace WatchdogCompatibilityAdapter with:
from src.utils.Watchdog import SystemWatchdog
self.watchdog = SystemWatchdog(...)
```

## Future Improvements
1. Remove legacy implementation once Qt version is stable
2. Add more granular health monitoring signals
3. Implement watchdog configuration hot-reload
4. Add performance metrics for the watchdog itself

## Troubleshooting

### Common Issues
1. **Qt not available**: System automatically falls back to legacy mode
2. **Signal connection errors**: Check Qt event loop is running
3. **Metrics not updating**: Verify signal connections in main.py

### Debug Mode
To enable debug logging for the watchdog:
```python
# In watchdog initialization
logger.setLevel(logging.DEBUG)
```

## Migration Checklist
- [x] Update main.py to use WatchdogCompatibilityAdapter
- [x] Connect Qt signals in DinoAirApp
- [x] Update MainWindow handlers documentation
- [x] Make settings page compatible with both implementations
- [x] Test automatic fallback mechanism
- [x] Document all changes

The migration is complete and maintains 100% backwards compatibility while resolving the QBasicTimer threading issues.