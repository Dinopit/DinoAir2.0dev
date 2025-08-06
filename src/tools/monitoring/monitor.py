"""
Tool Monitoring System

This module provides comprehensive monitoring capabilities for tools,
including execution tracking, performance metrics, error analysis,
and usage statistics aggregation.
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
from pathlib import Path
import statistics
import traceback

from ..base import (
    BaseTool, ToolResult, ToolStatus, ToolEvent,
    ToolLifecycleEvent, ToolCategory
)
from ..registry import ToolRegistry


logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class ExecutionMetrics:
    """Metrics for a single tool execution"""
    tool_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_size: Optional[int] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorInfo:
    """Information about an error"""
    error_type: str
    error_message: str
    stack_trace: str
    tool_name: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    count: int = 1


@dataclass
class PerformanceStats:
    """Performance statistics for a tool"""
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration: float = 0.0
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    avg_duration: float = 0.0
    p50_duration: Optional[float] = None
    p95_duration: Optional[float] = None
    p99_duration: Optional[float] = None
    last_execution: Optional[datetime] = None
    durations: List[float] = field(default_factory=list)


@dataclass
class Metric:
    """A single metric value"""
    name: str
    value: float
    type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None


class ToolMonitor:
    """
    Monitor for tracking tool executions and collecting metrics
    
    This class provides comprehensive monitoring capabilities including:
    - Execution tracking with timing
    - Performance metrics collection
    - Error tracking and categorization
    - Usage statistics aggregation
    - Real-time metrics export
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        retention_hours: int = 24,
        max_executions_per_tool: int = 1000,
        enable_memory_tracking: bool = True,
        enable_cpu_tracking: bool = True
    ):
        """
        Initialize the tool monitor
        
        Args:
            registry: Optional tool registry to monitor
            retention_hours: Hours to retain execution data
            max_executions_per_tool: Max executions to store per tool
            enable_memory_tracking: Enable memory usage tracking
            enable_cpu_tracking: Enable CPU usage tracking
        """
        self.registry = registry or ToolRegistry()
        self.retention_hours = retention_hours
        self.max_executions_per_tool = max_executions_per_tool
        self.enable_memory_tracking = enable_memory_tracking
        self.enable_cpu_tracking = enable_cpu_tracking
        
        # Storage
        self._executions: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_executions_per_tool)
        )
        self._performance_stats: Dict[str, PerformanceStats] = {}
        self._errors: Dict[str, List[ErrorInfo]] = defaultdict(list)
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._active_executions: Dict[str, ExecutionMetrics] = {}
        
        # Locks for thread safety
        self._lock = threading.RLock()
        self._stats_lock = threading.RLock()
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()
        
        # Hook into registry events
        self._register_event_handlers()
        
    def _register_event_handlers(self):
        """Register handlers for tool events"""
        if self.registry:
            self.registry.add_event_handler(
                ToolLifecycleEvent.STARTED,
                self._on_tool_started
            )
            self.registry.add_event_handler(
                ToolLifecycleEvent.COMPLETED,
                self._on_tool_completed
            )
            self.registry.add_event_handler(
                ToolLifecycleEvent.ERROR,
                self._on_tool_error
            )
            
    def _on_tool_started(self, event: ToolEvent):
        """Handle tool start event"""
        execution_id = event.data.get('execution_id')
        if execution_id:
            self.start_execution(
                event.tool_name,
                execution_id,
                event.data.get('params', {})
            )
            
    def _on_tool_completed(self, event: ToolEvent):
        """Handle tool completion event"""
        execution_id = event.data.get('execution_id')
        if execution_id:
            self.end_execution(
                execution_id,
                success=event.data.get('success', True),
                output=event.data.get('output')
            )
            
    def _on_tool_error(self, event: ToolEvent):
        """Handle tool error event"""
        self.record_error(
            event.tool_name,
            event.data.get('error_type', 'UnknownError'),
            event.data.get('error_message', 'No message'),
            event.data.get('stack_trace', ''),
            event.data
        )
        
    def start_execution(
        self,
        tool_name: str,
        execution_id: str,
        params: Dict[str, Any]
    ) -> ExecutionMetrics:
        """
        Start tracking a tool execution
        
        Args:
            tool_name: Name of the tool
            execution_id: Unique execution identifier
            params: Input parameters
            
        Returns:
            ExecutionMetrics instance
        """
        with self._lock:
            metrics = ExecutionMetrics(
                tool_name=tool_name,
                start_time=datetime.now(),
                input_params=params.copy()
            )
            
            self._active_executions[execution_id] = metrics
            
            # Update counters
            self.record_metric(
                f"{tool_name}_executions_started",
                1,
                MetricType.COUNTER,
                {"tool": tool_name}
            )
            
            return metrics
            
    def end_execution(
        self,
        execution_id: str,
        success: bool,
        output: Any = None,
        error_info: Optional[Tuple[str, str, str]] = None
    ):
        """
        End tracking a tool execution
        
        Args:
            execution_id: Execution identifier
            success: Whether execution succeeded
            output: Tool output
            error_info: Optional (type, message, trace) tuple
        """
        with self._lock:
            if execution_id not in self._active_executions:
                logger.warning(f"Unknown execution ID: {execution_id}")
                return
                
            metrics = self._active_executions.pop(execution_id)
            metrics.end_time = datetime.now()
            metrics.duration = (
                metrics.end_time - metrics.start_time
            ).total_seconds()
            metrics.success = success
            
            if error_info:
                metrics.error_type = error_info[0]
                metrics.error_message = error_info[1]
                
            # Calculate output size
            if output is not None:
                try:
                    metrics.output_size = len(str(output))
                except Exception:
                    pass
                    
            # Track resource usage if enabled
            if self.enable_memory_tracking:
                metrics.memory_usage = self._get_memory_usage()
            if self.enable_cpu_tracking:
                metrics.cpu_usage = self._get_cpu_usage()
                
            # Store execution
            self._executions[metrics.tool_name].append(metrics)
            
            # Update statistics
            self._update_performance_stats(metrics)
            
            # Record metrics
            labels = {"tool": metrics.tool_name, "success": str(success)}
            self.record_metric(
                f"{metrics.tool_name}_execution_duration",
                metrics.duration,
                MetricType.HISTOGRAM,
                labels
            )
            
            if success:
                self.record_metric(
                    f"{metrics.tool_name}_executions_success",
                    1,
                    MetricType.COUNTER,
                    labels
                )
            else:
                self.record_metric(
                    f"{metrics.tool_name}_executions_failed",
                    1,
                    MetricType.COUNTER,
                    labels
                )
                
    def record_error(
        self,
        tool_name: str,
        error_type: str,
        error_message: str,
        stack_trace: str = "",
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Record a tool error
        
        Args:
            tool_name: Name of the tool
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
            context: Optional error context
        """
        with self._lock:
            # Check if similar error exists
            error_key = f"{tool_name}:{error_type}:{error_message}"
            existing_errors = self._errors.get(error_key, [])
            
            if existing_errors and len(existing_errors) > 0:
                # Increment count of existing error
                existing_errors[-1].count += 1
            else:
                # Create new error entry
                error_info = ErrorInfo(
                    error_type=error_type,
                    error_message=error_message,
                    stack_trace=stack_trace or traceback.format_exc(),
                    tool_name=tool_name,
                    timestamp=datetime.now(),
                    context=context or {}
                )
                self._errors[error_key].append(error_info)
                
            # Record error metric
            self.record_metric(
                f"{tool_name}_errors",
                1,
                MetricType.COUNTER,
                {"tool": tool_name, "error_type": error_type}
            )
            
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]] = None,
        description: Optional[str] = None
    ):
        """
        Record a custom metric
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels
            description: Optional description
        """
        metric = Metric(
            name=name,
            value=value,
            type=metric_type,
            labels=labels or {},
            description=description
        )
        
        with self._lock:
            self._metrics[name].append(metric)
            
    def _update_performance_stats(self, metrics: ExecutionMetrics):
        """Update performance statistics for a tool"""
        with self._stats_lock:
            tool_name = metrics.tool_name
            
            if tool_name not in self._performance_stats:
                self._performance_stats[tool_name] = PerformanceStats()
                
            stats = self._performance_stats[tool_name]
            
            # Update counts
            stats.execution_count += 1
            if metrics.success:
                stats.success_count += 1
            else:
                stats.failure_count += 1
                
            # Update duration stats
            if metrics.duration is not None:
                stats.total_duration += metrics.duration
                stats.durations.append(metrics.duration)
                
                # Keep only recent durations for percentile calculation
                if len(stats.durations) > 1000:
                    stats.durations = stats.durations[-1000:]
                    
                # Update min/max
                if stats.min_duration is None or metrics.duration < stats.min_duration:
                    stats.min_duration = metrics.duration
                if stats.max_duration is None or metrics.duration > stats.max_duration:
                    stats.max_duration = metrics.duration
                    
                # Calculate statistics
                stats.avg_duration = stats.total_duration / stats.execution_count
                
                if len(stats.durations) >= 10:
                    sorted_durations = sorted(stats.durations)
                    stats.p50_duration = self._percentile(sorted_durations, 0.5)
                    stats.p95_duration = self._percentile(sorted_durations, 0.95)
                    stats.p99_duration = self._percentile(sorted_durations, 0.99)
                    
            stats.last_execution = metrics.end_time
            
    def _percentile(self, sorted_list: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not sorted_list:
            return 0.0
            
        index = int(len(sorted_list) * percentile)
        if index >= len(sorted_list):
            index = len(sorted_list) - 1
            
        return sorted_list[index]
        
    def get_performance_stats(
        self,
        tool_name: Optional[str] = None
    ) -> Dict[str, PerformanceStats]:
        """
        Get performance statistics
        
        Args:
            tool_name: Optional specific tool name
            
        Returns:
            Performance statistics by tool
        """
        with self._stats_lock:
            if tool_name:
                stats = self._performance_stats.get(tool_name)
                return {tool_name: stats} if stats else {}
            else:
                return self._performance_stats.copy()
                
    def get_recent_executions(
        self,
        tool_name: Optional[str] = None,
        limit: int = 100,
        success_only: Optional[bool] = None
    ) -> List[ExecutionMetrics]:
        """
        Get recent executions
        
        Args:
            tool_name: Optional tool name filter
            limit: Maximum number of results
            success_only: Optional success filter
            
        Returns:
            List of recent executions
        """
        with self._lock:
            executions = []
            
            if tool_name:
                tool_executions = list(self._executions.get(tool_name, []))
                executions.extend(tool_executions)
            else:
                for tool_execs in self._executions.values():
                    executions.extend(list(tool_execs))
                    
            # Sort by start time (newest first)
            executions.sort(key=lambda e: e.start_time, reverse=True)
            
            # Apply filters
            if success_only is not None:
                executions = [
                    e for e in executions
                    if e.success == success_only
                ]
                
            return executions[:limit]
            
    def get_error_summary(
        self,
        tool_name: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, List[ErrorInfo]]:
        """
        Get error summary
        
        Args:
            tool_name: Optional tool name filter
            hours: Optional time window in hours
            
        Returns:
            Errors grouped by key
        """
        with self._lock:
            cutoff_time = None
            if hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                
            result = {}
            
            for key, errors in self._errors.items():
                if tool_name and not key.startswith(f"{tool_name}:"):
                    continue
                    
                filtered_errors = errors
                if cutoff_time:
                    filtered_errors = [
                        e for e in errors
                        if e.timestamp > cutoff_time
                    ]
                    
                if filtered_errors:
                    result[key] = filtered_errors
                    
            return result
            
    def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, List[Metric]]:
        """
        Get metrics
        
        Args:
            metric_name: Optional metric name filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Metrics grouped by name
        """
        with self._lock:
            result = {}
            
            metrics_to_check = (
                {metric_name: self._metrics.get(metric_name, [])}
                if metric_name
                else self._metrics
            )
            
            for name, metrics in metrics_to_check.items():
                filtered_metrics = metrics
                
                if start_time:
                    filtered_metrics = [
                        m for m in filtered_metrics
                        if m.timestamp >= start_time
                    ]
                    
                if end_time:
                    filtered_metrics = [
                        m for m in filtered_metrics
                        if m.timestamp <= end_time
                    ]
                    
                if filtered_metrics:
                    result[name] = filtered_metrics
                    
            return result
            
    def export_metrics_prometheus(self) -> str:
        """
        Export metrics in Prometheus format
        
        Returns:
            Prometheus-formatted metrics
        """
        lines = []
        
        with self._lock:
            # Export performance stats
            for tool_name, stats in self._performance_stats.items():
                safe_name = tool_name.replace("-", "_").replace(" ", "_")
                
                # Execution counts
                lines.append(
                    f"# HELP {safe_name}_total Total executions\n"
                    f"# TYPE {safe_name}_total counter\n"
                    f"{safe_name}_total {stats.execution_count}"
                )
                
                lines.append(
                    f"# HELP {safe_name}_success Successful executions\n"
                    f"# TYPE {safe_name}_success counter\n"
                    f"{safe_name}_success {stats.success_count}"
                )
                
                lines.append(
                    f"# HELP {safe_name}_failed Failed executions\n"
                    f"# TYPE {safe_name}_failed counter\n"
                    f"{safe_name}_failed {stats.failure_count}"
                )
                
                # Duration metrics
                if stats.avg_duration is not None:
                    lines.append(
                        f"# HELP {safe_name}_duration_seconds Execution duration\n"
                        f"# TYPE {safe_name}_duration_seconds summary\n"
                        f"{safe_name}_duration_seconds{{quantile=\"0.5\"}} "
                        f"{stats.p50_duration or 0}\n"
                        f"{safe_name}_duration_seconds{{quantile=\"0.95\"}} "
                        f"{stats.p95_duration or 0}\n"
                        f"{safe_name}_duration_seconds{{quantile=\"0.99\"}} "
                        f"{stats.p99_duration or 0}\n"
                        f"{safe_name}_duration_seconds_sum {stats.total_duration}\n"
                        f"{safe_name}_duration_seconds_count {stats.execution_count}"
                    )
                    
            # Export custom metrics
            for metric_name, metrics in self._metrics.items():
                if metrics:
                    latest = metrics[-1]
                    metric_type = latest.type.value
                    
                    lines.append(
                        f"# HELP {metric_name} {latest.description or metric_name}\n"
                        f"# TYPE {metric_name} {metric_type}"
                    )
                    
                    # Aggregate by labels
                    label_values = defaultdict(float)
                    label_counts = defaultdict(int)
                    
                    for metric in metrics:
                        label_str = self._format_labels(metric.labels)
                        if metric.type == MetricType.COUNTER:
                            label_values[label_str] += metric.value
                        else:
                            label_values[label_str] = metric.value
                        label_counts[label_str] += 1
                        
                    for label_str, value in label_values.items():
                        lines.append(f"{metric_name}{label_str} {value}")
                        
        return "\n".join(lines)
        
    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format labels for Prometheus export"""
        if not labels:
            return ""
            
        label_parts = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(label_parts) + "}"
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
            
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
            
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                time.sleep(3600)  # Run hourly
                self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    def _cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        cutoff_time = datetime.now() - timedelta(hours=self.retention_hours)
        
        with self._lock:
            # Clean up old executions
            for tool_name, executions in self._executions.items():
                while executions and executions[0].start_time < cutoff_time:
                    executions.popleft()
                    
            # Clean up old errors
            for key, errors in list(self._errors.items()):
                self._errors[key] = [
                    e for e in errors
                    if e.timestamp > cutoff_time
                ]
                if not self._errors[key]:
                    del self._errors[key]
                    
            # Clean up old metrics
            for name, metrics in list(self._metrics.items()):
                self._metrics[name] = [
                    m for m in metrics
                    if m.timestamp > cutoff_time
                ]
                if not self._metrics[name]:
                    del self._metrics[name]
                    
    def save_report(self, path: Path):
        """Save monitoring report to file"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "performance_stats": {
                name: {
                    "execution_count": stats.execution_count,
                    "success_count": stats.success_count,
                    "failure_count": stats.failure_count,
                    "avg_duration": stats.avg_duration,
                    "min_duration": stats.min_duration,
                    "max_duration": stats.max_duration,
                    "p95_duration": stats.p95_duration,
                    "last_execution": (
                        stats.last_execution.isoformat()
                        if stats.last_execution else None
                    )
                }
                for name, stats in self._performance_stats.items()
            },
            "recent_errors": {
                key: [
                    {
                        "type": e.error_type,
                        "message": e.error_message,
                        "count": e.count,
                        "timestamp": e.timestamp.isoformat()
                    }
                    for e in errors[-10:]  # Last 10 errors per type
                ]
                for key, errors in self._errors.items()
            }
        }
        
        with open(path, 'w') as f:
            json.dump(report, f, indent=2)


# Global monitor instance
_monitor_instance: Optional[ToolMonitor] = None
_monitor_lock = threading.Lock()


def get_monitor(
    registry: Optional[ToolRegistry] = None,
    **kwargs
) -> ToolMonitor:
    """
    Get or create global monitor instance
    
    Args:
        registry: Optional tool registry
        **kwargs: Additional monitor arguments
        
    Returns:
        ToolMonitor instance
    """
    global _monitor_instance
    
    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = ToolMonitor(registry, **kwargs)
        return _monitor_instance


# Export main components
__all__ = [
    'MetricType',
    'ExecutionMetrics',
    'ErrorInfo',
    'PerformanceStats',
    'Metric',
    'ToolMonitor',
    'get_monitor'
]