"""Watchdog health monitoring system for DinoAir 2.0.

This module provides comprehensive health monitoring and automatic recovery
capabilities for the watchdog system. It tracks the health of individual
components and orchestrates recovery strategies.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from collections import deque
from PySide6.QtCore import (
    QObject, Signal, QTimer, QMutex, QMutexLocker
)

from .logger import Logger

logger = Logger()


class RecoveryStrategy(Enum):
    """Available recovery strategies for components."""
    RESTART = "restart"              # Restart the component
    RESET_STATE = "reset_state"      # Reset component state
    CLEAR_CACHE = "clear_cache"      # Clear cached data
    FALLBACK_MODE = "fallback_mode"  # Switch to fallback implementation
    ESCALATE = "escalate"            # Escalate to parent handler
    NONE = "none"                    # No recovery action


@dataclass
class ComponentMetrics:
    """Metrics for a monitored component."""
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    recovery_attempts: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_types: Dict[str, int] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """Action to take for recovery."""
    strategy: RecoveryStrategy
    callback: Optional[Callable[[], bool]] = None
    max_attempts: int = 3
    cooldown_seconds: int = 60
    last_attempt: Optional[datetime] = None
    attempt_count: int = 0
    
    def can_attempt(self) -> bool:
        """Check if recovery can be attempted."""
        if self.attempt_count >= self.max_attempts:
            return False
            
        if self.last_attempt:
            elapsed = (datetime.now() - self.last_attempt).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
                
        return True
        
    def record_attempt(self) -> None:
        """Record a recovery attempt."""
        self.attempt_count += 1
        self.last_attempt = datetime.now()
        
    def reset(self) -> None:
        """Reset recovery action state."""
        self.attempt_count = 0
        self.last_attempt = None


class WatchdogHealthSignals(QObject):
    """Signals for health monitoring events."""
    
    # Health state changes
    component_health_changed = Signal(str, str, str)  # name, state, message
    overall_health_changed = Signal(str, dict)  # state, component_states
    
    # Recovery events
    recovery_started = Signal(str, str)  # component, strategy
    recovery_succeeded = Signal(str, str)  # component, message
    recovery_failed = Signal(str, str)  # component, reason
    
    # Alerts
    health_alert = Signal(str, str)  # level, message
    component_degraded = Signal(str, dict)  # component, metrics
    system_degraded = Signal(dict)  # degraded_components


class WatchdogHealthMonitor(QObject):
    """Monitors health of watchdog components and manages recovery."""
    
    def __init__(self, parent=None):
        """Initialize health monitor."""
        super().__init__(parent)
        
        self.signals = WatchdogHealthSignals()
        self._mutex = QMutex()
        
        # Component tracking
        self.components: Dict[str, Dict[str, Any]] = {}
        self.component_metrics: Dict[str, ComponentMetrics] = {}
        self.recovery_actions: Dict[str, List[RecoveryAction]] = {}
        
        # Health check configuration
        self.health_check_interval = 30000  # 30 seconds
        self.metrics_window = 300  # 5 minutes for metrics analysis
        
        # Thresholds
        self.failure_threshold = 5
        self.degraded_threshold = 0.8  # 80% success rate
        self.response_time_threshold = 5.0  # seconds
        
        # Health check timer
        self._health_timer = QTimer()
        self._health_timer.timeout.connect(self._perform_health_check)
        
        # Recovery timer
        self._recovery_timer = QTimer()
        self._recovery_timer.timeout.connect(self._check_recovery_needed)
        self._recovery_timer.setInterval(10000)  # Check every 10 seconds
        
        # Initialize default components
        self._initialize_default_components()
        
    def _initialize_default_components(self):
        """Initialize monitoring for default watchdog components."""
        # Register core components
        self.register_component(
            "vram_collector",
            recovery_strategies=[
                RecoveryAction(RecoveryStrategy.CLEAR_CACHE),
                RecoveryAction(RecoveryStrategy.FALLBACK_MODE),
                RecoveryAction(RecoveryStrategy.ESCALATE)
            ]
        )
        
        self.register_component(
            "cpu_collector",
            recovery_strategies=[
                RecoveryAction(RecoveryStrategy.RESET_STATE),
                RecoveryAction(RecoveryStrategy.FALLBACK_MODE)
            ]
        )
        
        self.register_component(
            "process_counter",
            recovery_strategies=[
                RecoveryAction(RecoveryStrategy.RESET_STATE),
                RecoveryAction(RecoveryStrategy.ESCALATE)
            ]
        )
        
        self.register_component(
            "metrics_aggregator",
            recovery_strategies=[
                RecoveryAction(RecoveryStrategy.RESTART),
                RecoveryAction(RecoveryStrategy.ESCALATE)
            ]
        )
        
    def start_monitoring(self):
        """Start health monitoring."""
        logger.info("Starting watchdog health monitoring")
        self._health_timer.start(self.health_check_interval)
        self._recovery_timer.start()
        
    def stop_monitoring(self):
        """Stop health monitoring."""
        logger.info("Stopping watchdog health monitoring")
        self._health_timer.stop()
        self._recovery_timer.stop()
        
    def register_component(self,
                           name: str,
                           recovery_strategies: Optional[
                               List[RecoveryAction]
                           ] = None,
                           health_check: Optional[Callable[[], bool]] = None):
        """Register a component for health monitoring.
        
        Args:
            name: Component name
            recovery_strategies: List of recovery actions in priority order
            health_check: Optional custom health check function
        """
        with QMutexLocker(self._mutex):
            self.components[name] = {
                'state': 'unknown',
                'health_check': health_check,
                'last_check': None
            }
            
            self.component_metrics[name] = ComponentMetrics()
            
            if recovery_strategies:
                self.recovery_actions[name] = recovery_strategies
            else:
                self.recovery_actions[name] = [
                    RecoveryAction(RecoveryStrategy.ESCALATE)
                ]
                
            logger.info(f"Registered component '{name}' for health monitoring")
            
    def record_success(self, component: str,
                       response_time: Optional[float] = None):
        """Record successful operation for a component.
        
        Args:
            component: Component name
            response_time: Optional response time in seconds
        """
        with QMutexLocker(self._mutex):
            if component not in self.component_metrics:
                return
                
            metrics = self.component_metrics[component]
            metrics.success_count += 1
            metrics.consecutive_failures = 0
            metrics.last_success = datetime.now()
            
            if response_time is not None:
                metrics.response_times.append(response_time)
                
            # Check if component was recovering
            if component in self.components:
                comp_info = self.components[component]
                if comp_info['state'] in ('failed', 'degraded', 'recovering'):
                    self._update_component_state(
                        component, 'healthy',
                        "Component recovered successfully"
                    )
                    
                    # Reset recovery actions
                    for action in self.recovery_actions.get(component, []):
                        action.reset()
                        
    def record_failure(self, component: str, error: Exception):
        """Record failed operation for a component.
        
        Args:
            component: Component name
            error: Exception that occurred
        """
        with QMutexLocker(self._mutex):
            if component not in self.component_metrics:
                return
                
            metrics = self.component_metrics[component]
            metrics.failure_count += 1
            metrics.consecutive_failures += 1
            metrics.last_failure = datetime.now()
            
            # Track error types
            error_type = type(error).__name__
            metrics.error_types[error_type] = (
                metrics.error_types.get(error_type, 0) + 1
            )
            
            # Check if component needs state update
            if metrics.consecutive_failures >= self.failure_threshold:
                self._update_component_state(
                    component, 'failed',
                    f"Component failed after {metrics.consecutive_failures} "
                    f"consecutive failures: {error}"
                )
            elif metrics.consecutive_failures > 1:
                self._update_component_state(
                    component, 'degraded',
                    f"Component experiencing failures: {error}"
                )
                
    def _update_component_state(self, component: str, state: str,
                                message: str):
        """Update component state and emit signals."""
        if component in self.components:
            old_state = self.components[component]['state']
            self.components[component]['state'] = state
            
            if old_state != state:
                logger.info(
                    f"Component '{component}' state changed: "
                    f"{old_state} -> {state} ({message})"
                )
                self.signals.component_health_changed.emit(
                    component, state, message
                )
                
                # Check overall system health
                self._check_overall_health()
                
    def _check_overall_health(self):
        """Check overall system health based on component states."""
        with QMutexLocker(self._mutex):
            component_states = {
                name: info['state']
                for name, info in self.components.items()
            }
            
            # Determine overall state
            failed_states = [s for s in component_states.values()
                             if s == 'failed']
            degraded_states = [s for s in component_states.values()
                               if s == 'degraded']
            healthy_states = [s for s in component_states.values()
                              if s == 'healthy']
            
            if failed_states:
                overall_state = 'critical'
            elif degraded_states:
                overall_state = 'degraded'
            elif len(healthy_states) == len(component_states):
                overall_state = 'healthy'
            else:
                overall_state = 'unknown'
                
            self.signals.overall_health_changed.emit(
                overall_state, component_states
            )
            
    def _perform_health_check(self):
        """Perform periodic health check on all components."""
        try:
            with QMutexLocker(self._mutex):
                current_time = datetime.now()
                degraded_components = {}
                
                for component, info in self.components.items():
                    # Run custom health check if available
                    if info['health_check']:
                        try:
                            is_healthy = info['health_check']()
                            if not is_healthy:
                                self._update_component_state(
                                    component, 'degraded',
                                    "Health check failed"
                                )
                        except Exception as e:
                            logger.error(
                                f"Health check failed for {component}: {e}"
                            )
                            self._update_component_state(
                                component, 'failed',
                                f"Health check error: {e}"
                            )
                            
                    # Analyze metrics
                    if component in self.component_metrics:
                        metrics = self.component_metrics[component]
                        analysis = self._analyze_component_metrics(
                            component, metrics
                        )
                        
                        if analysis['needs_attention']:
                            degraded_components[component] = analysis
                            
                    info['last_check'] = current_time
                    
                # Emit degraded components signal if any
                if degraded_components:
                    self.signals.system_degraded.emit(degraded_components)
                    
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            
    def _analyze_component_metrics(
            self,
            component: str,
            metrics: ComponentMetrics) -> Dict[str, Any]:
        """Analyze component metrics for health issues.
        
        Returns:
            Dict with analysis results
        """
        analysis = {
            'needs_attention': False,
            'issues': [],
            'success_rate': 0.0,
            'avg_response_time': 0.0
        }
        
        # Calculate success rate
        total_ops = metrics.success_count + metrics.failure_count
        if total_ops > 0:
            analysis['success_rate'] = metrics.success_count / total_ops
            
            if analysis['success_rate'] < self.degraded_threshold:
                analysis['needs_attention'] = True
                analysis['issues'].append(
                    f"Low success rate: {analysis['success_rate']:.1%}"
                )
                
        # Check consecutive failures
        if metrics.consecutive_failures >= self.failure_threshold:
            analysis['needs_attention'] = True
            analysis['issues'].append(
                f"High consecutive failures: {metrics.consecutive_failures}"
            )
            
        # Analyze response times
        if metrics.response_times:
            total_time = sum(metrics.response_times)
            avg_response = total_time / len(metrics.response_times)
            analysis['avg_response_time'] = avg_response
            
            if avg_response > self.response_time_threshold:
                analysis['needs_attention'] = True
                analysis['issues'].append(
                    f"Slow response time: {avg_response:.2f}s"
                )
                
        # Check staleness
        if metrics.last_success:
            time_since_success = (
                datetime.now() - metrics.last_success
            ).total_seconds()
            
            if time_since_success > self.metrics_window:
                analysis['needs_attention'] = True
                analysis['issues'].append(
                    f"No recent success: {time_since_success:.0f}s ago"
                )
                
        return analysis
        
    def _check_recovery_needed(self):
        """Check if any components need recovery."""
        try:
            with QMutexLocker(self._mutex):
                for component, info in self.components.items():
                    if info['state'] in ('failed', 'degraded'):
                        self._attempt_recovery(component)
                        
        except Exception as e:
            logger.error(f"Error checking recovery: {e}")
            
    def _attempt_recovery(self, component: str):
        """Attempt recovery for a component."""
        if component not in self.recovery_actions:
            return
            
        # Try recovery strategies in order
        for action in self.recovery_actions[component]:
            if not action.can_attempt():
                continue
                
            logger.info(
                f"Attempting {action.strategy.value} recovery "
                f"for component '{component}'"
            )
            
            self.signals.recovery_started.emit(
                component, action.strategy.value
            )
            
            action.record_attempt()
            
            try:
                success = False
                
                if action.strategy == RecoveryStrategy.RESTART:
                    success = self._recovery_restart(component)
                elif action.strategy == RecoveryStrategy.RESET_STATE:
                    success = self._recovery_reset_state(component)
                elif action.strategy == RecoveryStrategy.CLEAR_CACHE:
                    success = self._recovery_clear_cache(component)
                elif action.strategy == RecoveryStrategy.FALLBACK_MODE:
                    success = self._recovery_fallback_mode(component)
                elif action.strategy == RecoveryStrategy.ESCALATE:
                    success = self._recovery_escalate(component)
                    
                # Custom callback if provided
                if action.callback and not success:
                    success = action.callback()
                    
                if success:
                    self._update_component_state(
                        component, 'recovering',
                        f"Recovery {action.strategy.value} initiated"
                    )
                    self.signals.recovery_succeeded.emit(
                        component, 
                        f"Recovery strategy {action.strategy.value} succeeded"
                    )
                    break  # Stop trying other strategies
                    
            except Exception as e:
                logger.error(
                    f"Recovery {action.strategy.value} failed "
                    f"for {component}: {e}"
                )
                self.signals.recovery_failed.emit(
                    component, 
                    f"Recovery {action.strategy.value} failed: {e}"
                )
                
    def _recovery_restart(self, component: str) -> bool:
        """Restart component recovery strategy."""
        logger.info(f"Restarting component '{component}'")
        # Component-specific restart logic would go here
        # For now, just reset metrics
        if component in self.component_metrics:
            self.component_metrics[component] = ComponentMetrics()
            return True
        return False
        
    def _recovery_reset_state(self, component: str) -> bool:
        """Reset state recovery strategy."""
        logger.info(f"Resetting state for component '{component}'")
        # Reset component state
        if component in self.components:
            self.components[component]['state'] = 'unknown'
            return True
        return False
        
    def _recovery_clear_cache(self, component: str) -> bool:
        """Clear cache recovery strategy."""
        logger.info(f"Clearing cache for component '{component}'")
        # Component-specific cache clearing would go here
        return True
        
    def _recovery_fallback_mode(self, component: str) -> bool:
        """Switch to fallback mode recovery strategy."""
        logger.info(f"Switching '{component}' to fallback mode")
        # Signal that component should use fallback implementation
        self.signals.health_alert.emit(
            'warning',
            f"Component '{component}' switched to fallback mode"
        )
        return True
        
    def _recovery_escalate(self, component: str) -> bool:
        """Escalate recovery strategy."""
        logger.warning(
            f"Escalating recovery for component '{component}' - "
            f"manual intervention may be required"
        )
        self.signals.health_alert.emit(
            'critical',
            f"Component '{component}' requires manual intervention"
        )
        return False  # Escalation doesn't fix the issue
        
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report.
        
        Returns:
            Dict containing health information for all components
        """
        with QMutexLocker(self._mutex):
            report = {
                'timestamp': datetime.now().isoformat(),
                'components': {},
                'overall_state': 'unknown',
                'statistics': {
                    'total_components': len(self.components),
                    'healthy': 0,
                    'degraded': 0,
                    'failed': 0,
                    'unknown': 0
                }
            }
            
            # Collect component information
            for name, info in self.components.items():
                state = info['state']
                metrics = self.component_metrics.get(name)
                
                # Update statistics
                report['statistics'][state] = (
                    report['statistics'].get(state, 0) + 1
                )
                
                # Component details
                component_report = {
                    'state': state,
                    'last_check': (
                        info['last_check'].isoformat()
                        if info['last_check'] else None
                    )
                }
                
                if metrics:
                    component_report['metrics'] = {
                        'success_count': metrics.success_count,
                        'failure_count': metrics.failure_count,
                        'consecutive_failures': metrics.consecutive_failures,
                        'recovery_attempts': metrics.recovery_attempts,
                        'last_success': (
                            metrics.last_success.isoformat()
                            if metrics.last_success else None
                        ),
                        'error_types': metrics.error_types
                    }
                    
                    # Add analysis
                    analysis = self._analyze_component_metrics(name, metrics)
                    component_report['analysis'] = analysis
                    
                report['components'][name] = component_report
                
            # Determine overall state
            if report['statistics']['failed'] > 0:
                report['overall_state'] = 'critical'
            elif report['statistics']['degraded'] > 0:
                report['overall_state'] = 'degraded'
            elif report['statistics']['healthy'] == len(self.components):
                report['overall_state'] = 'healthy'
                
            return report