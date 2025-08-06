"""
Tool Telemetry and Observability

This module provides telemetry and observability features for tools,
including execution tracing, distributed tracing support, event logging,
and metrics export for various monitoring systems.
"""

import logging
import uuid
import time
import json
import threading
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from collections import deque
import traceback as tb
from functools import wraps

from ..base import BaseTool, ToolResult, ToolEvent
from .monitor import ToolMonitor, get_monitor, Metric, MetricType


logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    """Represents a trace span"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    status: str = "in_progress"
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def finish(self, status: str = "success"):
        """Finish the span"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
        
    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        self.tags[key] = value
        
    def log(self, event: str, **kwargs):
        """Add a log entry to the span"""
        log_entry = {
            "timestamp": time.time(),
            "event": event,
            **kwargs
        }
        self.logs.append(log_entry)
        
    def set_baggage(self, key: str, value: str):
        """Set baggage item"""
        self.baggage[key] = value
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "baggage": self.baggage
        }


@dataclass
class EventLog:
    """Represents an event log entry"""
    timestamp: datetime
    level: str
    event_type: str
    message: str
    tool_name: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "event_type": self.event_type,
            "message": self.message,
            "tool_name": self.tool_name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "metadata": self.metadata
        }


class TracingContext:
    """Thread-local tracing context"""
    
    def __init__(self):
        self._local = threading.local()
        
    @property
    def current_trace(self) -> Optional[str]:
        """Get current trace ID"""
        return getattr(self._local, 'trace_id', None)
        
    @property
    def current_span(self) -> Optional[TraceSpan]:
        """Get current span"""
        return getattr(self._local, 'current_span', None)
        
    @property
    def span_stack(self) -> List[TraceSpan]:
        """Get span stack"""
        if not hasattr(self._local, 'span_stack'):
            self._local.span_stack = []
        return self._local.span_stack
        
    def set_trace(self, trace_id: str):
        """Set current trace ID"""
        self._local.trace_id = trace_id
        
    def push_span(self, span: TraceSpan):
        """Push span to stack"""
        self.span_stack.append(span)
        self._local.current_span = span
        
    def pop_span(self) -> Optional[TraceSpan]:
        """Pop span from stack"""
        if self.span_stack:
            span = self.span_stack.pop()
            self._local.current_span = (
                self.span_stack[-1] if self.span_stack else None
            )
            return span
        return None
        
    def clear(self):
        """Clear context"""
        self._local.trace_id = None
        self._local.current_span = None
        self._local.span_stack = []


class ToolTelemetry:
    """
    Telemetry system for tools
    
    Provides comprehensive telemetry capabilities including:
    - Distributed tracing
    - Event logging
    - Metrics collection
    - Trace correlation
    - Export to various backends
    """
    
    def __init__(
        self,
        monitor: Optional[ToolMonitor] = None,
        enable_tracing: bool = True,
        enable_logging: bool = True,
        enable_metrics: bool = True,
        max_spans_per_trace: int = 1000,
        max_logs_per_tool: int = 10000
    ):
        """
        Initialize telemetry system
        
        Args:
            monitor: Optional tool monitor instance
            enable_tracing: Enable distributed tracing
            enable_logging: Enable event logging
            enable_metrics: Enable metrics collection
            max_spans_per_trace: Maximum spans per trace
            max_logs_per_tool: Maximum logs per tool
        """
        self.monitor = monitor or get_monitor()
        self.enable_tracing = enable_tracing
        self.enable_logging = enable_logging
        self.enable_metrics = enable_metrics
        self.max_spans_per_trace = max_spans_per_trace
        self.max_logs_per_tool = max_logs_per_tool
        
        # Storage
        self._traces: Dict[str, List[TraceSpan]] = {}
        self._event_logs: Dict[str, deque] = {}
        self._context = TracingContext()
        self._exporters: List[Callable] = []
        
        # Locks
        self._lock = threading.RLock()
        
        # Start export thread
        self._export_thread = threading.Thread(
            target=self._export_loop,
            daemon=True
        )
        self._export_thread.start()
        
    def start_trace(
        self,
        operation_name: str,
        trace_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        """
        Start a new trace
        
        Args:
            operation_name: Name of the operation
            trace_id: Optional trace ID (generated if not provided)
            tags: Optional tags
            
        Returns:
            Root span of the trace
        """
        if not self.enable_tracing:
            return self._create_noop_span()
            
        trace_id = trace_id or str(uuid.uuid4())
        self._context.set_trace(trace_id)
        
        return self.start_span(operation_name, tags)
        
    def start_span(
        self,
        operation_name: str,
        tags: Optional[Dict[str, Any]] = None,
        child_of: Optional[TraceSpan] = None
    ) -> TraceSpan:
        """
        Start a new span
        
        Args:
            operation_name: Name of the operation
            tags: Optional tags
            child_of: Optional parent span
            
        Returns:
            New span
        """
        if not self.enable_tracing:
            return self._create_noop_span()
            
        trace_id = self._context.current_trace
        if not trace_id:
            # Start new trace if none exists
            trace_id = str(uuid.uuid4())
            self._context.set_trace(trace_id)
            
        parent_span = child_of or self._context.current_span
        parent_span_id = parent_span.span_id if parent_span else None
        
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {}
        )
        
        # Inherit baggage from parent
        if parent_span:
            span.baggage.update(parent_span.baggage)
            
        # Store span
        with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = []
            self._traces[trace_id].append(span)
            
            # Limit spans per trace
            if len(self._traces[trace_id]) > self.max_spans_per_trace:
                self._traces[trace_id] = (
                    self._traces[trace_id][-self.max_spans_per_trace:]
                )
                
        self._context.push_span(span)
        
        return span
        
    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        tags: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing an operation
        
        Args:
            operation_name: Name of the operation
            tags: Optional tags
            
        Yields:
            TraceSpan
        """
        span = self.start_span(operation_name, tags)
        try:
            yield span
            span.finish("success")
        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.type", type(e).__name__)
            span.set_tag("error.message", str(e))
            span.log("error", exception=str(e), stack=tb.format_exc())
            span.finish("error")
            raise
        finally:
            self.finish_span(span)
            
    def finish_span(self, span: TraceSpan):
        """Finish a span"""
        if not self.enable_tracing or not span:
            return
            
        # Ensure span is finished
        if span.end_time is None:
            span.finish()
            
        # Pop from context if current
        current = self._context.current_span
        if current and current.span_id == span.span_id:
            self._context.pop_span()
            
    def log_event(
        self,
        level: str,
        event_type: str,
        message: str,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an event
        
        Args:
            level: Log level (info, warning, error, etc.)
            event_type: Type of event
            message: Event message
            tool_name: Optional tool name
            metadata: Optional metadata
        """
        if not self.enable_logging:
            return
            
        event = EventLog(
            timestamp=datetime.now(),
            level=level,
            event_type=event_type,
            message=message,
            tool_name=tool_name,
            trace_id=self._context.current_trace,
            span_id=(
                self._context.current_span.span_id
                if self._context.current_span else None
            ),
            metadata=metadata or {}
        )
        
        # Store event
        with self._lock:
            key = tool_name or "global"
            if key not in self._event_logs:
                self._event_logs[key] = deque(maxlen=self.max_logs_per_tool)
            self._event_logs[key].append(event)
            
        # Also log to standard logger
        log_msg = f"[{event_type}] {message}"
        if tool_name:
            log_msg = f"[{tool_name}] {log_msg}"
            
        getattr(logger, level, logger.info)(log_msg)
        
    def record_tool_metric(
        self,
        tool_name: str,
        metric_name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a tool-specific metric
        
        Args:
            tool_name: Tool name
            metric_name: Metric name
            value: Metric value
            metric_type: Type of metric
            tags: Optional tags
        """
        if not self.enable_metrics:
            return
            
        labels = {"tool": tool_name}
        if tags:
            labels.update(tags)
            
        self.monitor.record_metric(
            f"tool_{metric_name}",
            value,
            metric_type,
            labels
        )
        
    def instrument_tool(self, tool: BaseTool):
        """
        Instrument a tool for telemetry
        
        Args:
            tool: Tool to instrument
        """
        # Wrap execute method
        original_execute = tool.execute
        
        @wraps(original_execute)
        def traced_execute(**kwargs):
            with self.trace_operation(
                f"tool.{tool.name}.execute",
                tags={
                    "tool.name": tool.name,
                    "tool.version": tool.version,
                    "tool.category": (
                        tool.metadata.category.value
                        if tool.metadata else "unknown"
                    )
                }
            ) as span:
                # Log start
                self.log_event(
                    "info",
                    "tool_execution_started",
                    f"Starting execution of {tool.name}",
                    tool.name,
                    {"parameters": kwargs}
                )
                
                try:
                    # Execute tool
                    result = original_execute(**kwargs)
                    
                    # Record success
                    span.set_tag("tool.success", result.success)
                    if not result.success:
                        span.set_tag("tool.errors", result.errors)
                        
                    # Log completion
                    self.log_event(
                        "info" if result.success else "warning",
                        "tool_execution_completed",
                        f"Completed execution of {tool.name}",
                        tool.name,
                        {
                            "success": result.success,
                            "execution_time": span.duration
                        }
                    )
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    self.log_event(
                        "error",
                        "tool_execution_failed",
                        f"Failed to execute {tool.name}: {str(e)}",
                        tool.name,
                        {"exception": str(e), "traceback": tb.format_exc()}
                    )
                    raise
                    
        tool.execute = traced_execute
        
        # Add event handler for tool events
        def on_tool_event(event: ToolEvent):
            self.log_event(
                "info",
                event.event_type,
                f"Tool event: {event.event_type}",
                event.tool_name,
                event.data
            )
            
        tool.add_event_handler("*", on_tool_event)
        
    def get_trace(self, trace_id: str) -> Optional[List[TraceSpan]]:
        """Get all spans for a trace"""
        with self._lock:
            return self._traces.get(trace_id, []).copy()
            
    def get_active_traces(self) -> List[str]:
        """Get list of active trace IDs"""
        with self._lock:
            return list(self._traces.keys())
            
    def get_event_logs(
        self,
        tool_name: Optional[str] = None,
        level: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[EventLog]:
        """
        Get event logs
        
        Args:
            tool_name: Optional tool name filter
            level: Optional level filter
            event_type: Optional event type filter
            limit: Maximum number of logs
            
        Returns:
            List of event logs
        """
        with self._lock:
            logs = []
            
            if tool_name:
                tool_logs = list(self._event_logs.get(tool_name, []))
                logs.extend(tool_logs)
            else:
                for tool_logs in self._event_logs.values():
                    logs.extend(list(tool_logs))
                    
            # Apply filters
            if level:
                logs = [l for l in logs if l.level == level]
            if event_type:
                logs = [l for l in logs if l.event_type == event_type]
                
            # Sort by timestamp (newest first)
            logs.sort(key=lambda l: l.timestamp, reverse=True)
            
            return logs[:limit]
            
    def export_traces_jaeger(self) -> List[Dict[str, Any]]:
        """Export traces in Jaeger format"""
        traces = []
        
        with self._lock:
            for trace_id, spans in self._traces.items():
                trace = {
                    "traceID": trace_id,
                    "spans": []
                }
                
                for span in spans:
                    jaeger_span = {
                        "traceID": span.trace_id,
                        "spanID": span.span_id,
                        "operationName": span.operation_name,
                        "references": [],
                        "startTime": int(span.start_time * 1_000_000),
                        "duration": int((span.duration or 0) * 1_000_000),
                        "tags": [
                            {"key": k, "type": "string", "value": str(v)}
                            for k, v in span.tags.items()
                        ],
                        "logs": [
                            {
                                "timestamp": int(log["timestamp"] * 1_000_000),
                                "fields": [
                                    {"key": k, "value": str(v)}
                                    for k, v in log.items()
                                    if k != "timestamp"
                                ]
                            }
                            for log in span.logs
                        ],
                        "process": {
                            "serviceName": "dinoair-tools",
                            "tags": []
                        }
                    }
                    
                    if span.parent_span_id:
                        jaeger_span["references"].append({
                            "refType": "CHILD_OF",
                            "traceID": span.trace_id,
                            "spanID": span.parent_span_id
                        })
                        
                    trace["spans"].append(jaeger_span)
                    
                traces.append(trace)
                
        return traces
        
    def export_traces_zipkin(self) -> List[Dict[str, Any]]:
        """Export traces in Zipkin format"""
        spans = []
        
        with self._lock:
            for trace_spans in self._traces.values():
                for span in trace_spans:
                    zipkin_span = {
                        "traceId": span.trace_id,
                        "id": span.span_id,
                        "name": span.operation_name,
                        "timestamp": int(span.start_time * 1_000_000),
                        "duration": int((span.duration or 0) * 1_000_000),
                        "localEndpoint": {
                            "serviceName": "dinoair-tools"
                        },
                        "tags": {
                            str(k): str(v) for k, v in span.tags.items()
                        }
                    }
                    
                    if span.parent_span_id:
                        zipkin_span["parentId"] = span.parent_span_id
                        
                    # Add logs as annotations
                    if span.logs:
                        zipkin_span["annotations"] = [
                            {
                                "timestamp": int(log["timestamp"] * 1_000_000),
                                "value": log.get("event", "log")
                            }
                            for log in span.logs
                        ]
                        
                    spans.append(zipkin_span)
                    
        return spans
        
    def export_logs_json(self) -> List[Dict[str, Any]]:
        """Export logs in JSON format"""
        logs = []
        
        with self._lock:
            for tool_logs in self._event_logs.values():
                for log in tool_logs:
                    logs.append(log.to_dict())
                    
        return logs
        
    def add_exporter(self, exporter: Callable[[Dict[str, Any]], None]):
        """
        Add a custom exporter
        
        Args:
            exporter: Function that receives telemetry data
        """
        self._exporters.append(exporter)
        
    def _export_loop(self):
        """Background export loop"""
        while True:
            try:
                time.sleep(60)  # Export every minute
                self._export_data()
            except Exception as e:
                logger.error(f"Error in export loop: {e}")
                
    def _export_data(self):
        """Export data to all registered exporters"""
        if not self._exporters:
            return
            
        # Prepare export data
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "traces": {
                "jaeger": self.export_traces_jaeger(),
                "zipkin": self.export_traces_zipkin()
            },
            "logs": self.export_logs_json(),
            "metrics": self.monitor.export_metrics_prometheus()
        }
        
        # Call exporters
        for exporter in self._exporters:
            try:
                exporter(export_data)
            except Exception as e:
                logger.error(f"Error in exporter: {e}")
                
    def _create_noop_span(self) -> TraceSpan:
        """Create a no-op span when tracing is disabled"""
        return TraceSpan(
            span_id="noop",
            trace_id="noop",
            parent_span_id=None,
            operation_name="noop",
            start_time=time.time()
        )
        
    def clear_old_data(self, hours: int = 24):
        """Clear data older than specified hours"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self._lock:
            # Clear old traces
            for trace_id, spans in list(self._traces.items()):
                # Keep only recent spans
                recent_spans = [
                    s for s in spans
                    if s.start_time > cutoff_time
                ]
                
                if recent_spans:
                    self._traces[trace_id] = recent_spans
                else:
                    del self._traces[trace_id]
                    
            # Event logs are automatically limited by deque maxlen


# Global telemetry instance
_telemetry_instance: Optional[ToolTelemetry] = None
_telemetry_lock = threading.Lock()


def get_telemetry(
    monitor: Optional[ToolMonitor] = None,
    **kwargs
) -> ToolTelemetry:
    """
    Get or create global telemetry instance
    
    Args:
        monitor: Optional tool monitor
        **kwargs: Additional telemetry arguments
        
    Returns:
        ToolTelemetry instance
    """
    global _telemetry_instance
    
    with _telemetry_lock:
        if _telemetry_instance is None:
            _telemetry_instance = ToolTelemetry(monitor, **kwargs)
        return _telemetry_instance


# Decorator for tracing functions
def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to trace function execution
    
    Args:
        operation_name: Optional operation name (uses function name if not provided)
    """
    def decorator(func):
        op_name = operation_name or f"function.{func.__name__}"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = get_telemetry()
            with telemetry.trace_operation(op_name) as span:
                span.set_tag("function.name", func.__name__)
                span.set_tag("function.module", func.__module__)
                return func(*args, **kwargs)
                
        return wrapper
    return decorator


# Export main components
__all__ = [
    'TraceSpan',
    'EventLog',
    'TracingContext',
    'ToolTelemetry',
    'get_telemetry',
    'trace_function'
]