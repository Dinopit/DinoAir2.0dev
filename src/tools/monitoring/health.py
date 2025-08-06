"""
Tool Health Check System

This module provides health monitoring capabilities for tools,
including dependency verification, resource checks, availability
monitoring, and automated alerting.
"""

import logging
import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import socket
import psutil
import importlib.util

from ..base import BaseTool, ToolStatus
from ..registry import ToolRegistry
from .monitor import ToolMonitor, get_monitor
from .analytics import ToolAnalytics, Anomaly, AnomalyType


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Types of health checks"""
    LIVENESS = "liveness"
    READINESS = "readiness"
    STARTUP = "startup"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    PERFORMANCE = "performance"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    check_name: str
    check_type: CheckType
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "check_name": self.check_name,
            "check_type": self.check_type.value,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "metadata": self.metadata
        }


@dataclass
class DependencyInfo:
    """Information about a dependency"""
    name: str
    type: str  # python_package, service, file, network
    required: bool = True
    version_requirement: Optional[str] = None
    endpoint: Optional[str] = None
    timeout: float = 5.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceRequirement:
    """Resource requirement definition"""
    resource_type: str  # cpu, memory, disk, network
    minimum: Optional[float] = None
    recommended: Optional[float] = None
    critical: Optional[float] = None
    unit: str = ""
    
    def check_availability(self, current_value: float) -> HealthStatus:
        """Check if current resource value meets requirements"""
        if self.critical and current_value < self.critical:
            return HealthStatus.CRITICAL
        elif self.minimum and current_value < self.minimum:
            return HealthStatus.UNHEALTHY
        elif self.recommended and current_value < self.recommended:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    condition: str  # Expression to evaluate
    severity: str  # info, warning, error, critical
    message_template: str
    cooldown_minutes: int = 15
    max_alerts_per_hour: int = 4
    actions: List[str] = field(default_factory=list)  # log, email, webhook
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def should_trigger(self, context: Dict[str, Any]) -> bool:
        """Check if alert should trigger"""
        try:
            # Evaluate condition
            result = eval(self.condition, {"__builtins__": {}}, context)
            
            if not result:
                return False
                
            # Check cooldown
            if self.last_triggered:
                cooldown_end = (
                    self.last_triggered + 
                    timedelta(minutes=self.cooldown_minutes)
                )
                if datetime.now() < cooldown_end:
                    return False
                    
            # Check rate limit
            if self.trigger_count >= self.max_alerts_per_hour:
                # Reset counter if hour has passed
                if self.last_triggered:
                    hour_ago = datetime.now() - timedelta(hours=1)
                    if self.last_triggered < hour_ago:
                        self.trigger_count = 0
                    else:
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False


@dataclass
class ToolHealthReport:
    """Comprehensive health report for a tool"""
    tool_name: str
    overall_status: HealthStatus
    check_results: List[HealthCheckResult]
    dependencies: Dict[str, HealthStatus]
    resources: Dict[str, HealthStatus]
    alerts_triggered: List[str]
    last_check: datetime
    next_check: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "overall_status": self.overall_status.value,
            "check_results": [r.to_dict() for r in self.check_results],
            "dependencies": {
                k: v.value for k, v in self.dependencies.items()
            },
            "resources": {
                k: v.value for k, v in self.resources.items()
            },
            "alerts_triggered": self.alerts_triggered,
            "last_check": self.last_check.isoformat(),
            "next_check": self.next_check.isoformat(),
            "metadata": self.metadata
        }


class HealthChecker:
    """Base class for health check implementations"""
    
    def __init__(self, name: str, check_type: CheckType):
        self.name = name
        self.check_type = check_type
        
    async def check(self, tool: BaseTool) -> HealthCheckResult:
        """Perform health check"""
        raise NotImplementedError


class LivenessCheck(HealthChecker):
    """Check if tool is alive and responding"""
    
    def __init__(self):
        super().__init__("liveness", CheckType.LIVENESS)
        
    async def check(self, tool: BaseTool) -> HealthCheckResult:
        """Check tool liveness"""
        start_time = time.time()
        
        try:
            # Check tool status
            if tool.status == ToolStatus.READY:
                status = HealthStatus.HEALTHY
                message = "Tool is alive and ready"
            elif tool.status == ToolStatus.RUNNING:
                status = HealthStatus.HEALTHY
                message = "Tool is alive and running"
            elif tool.status in [ToolStatus.FAILED, ToolStatus.SHUTTING_DOWN]:
                status = HealthStatus.CRITICAL
                message = f"Tool is in {tool.status.value} state"
            else:
                status = HealthStatus.DEGRADED
                message = f"Tool is in {tool.status.value} state"
                
            duration = time.time() - start_time
            
            return HealthCheckResult(
                check_name=self.name,
                check_type=self.check_type,
                status=status,
                message=message,
                duration=duration,
                metadata={"tool_status": tool.status.value}
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                check_type=self.check_type,
                status=HealthStatus.CRITICAL,
                message=f"Liveness check failed: {str(e)}",
                duration=time.time() - start_time
            )


class ReadinessCheck(HealthChecker):
    """Check if tool is ready to accept work"""
    
    def __init__(self):
        super().__init__("readiness", CheckType.READINESS)
        
    async def check(self, tool: BaseTool) -> HealthCheckResult:
        """Check tool readiness"""
        start_time = time.time()
        
        try:
            # Check if tool is ready
            if tool.is_ready:
                # Try a simple operation
                test_params = {}
                is_valid, errors = tool.validate_parameters(test_params)
                
                if is_valid or not errors:
                    status = HealthStatus.HEALTHY
                    message = "Tool is ready to accept work"
                else:
                    status = HealthStatus.DEGRADED
                    message = "Tool validation indicates issues"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Tool is not ready"
                
            duration = time.time() - start_time
            
            return HealthCheckResult(
                check_name=self.name,
                check_type=self.check_type,
                status=status,
                message=message,
                duration=duration
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=self.name,
                check_type=self.check_type,
                status=HealthStatus.CRITICAL,
                message=f"Readiness check failed: {str(e)}",
                duration=time.time() - start_time
            )


class DependencyChecker:
    """Check tool dependencies"""
    
    @staticmethod
    async def check_dependency(dep: DependencyInfo) -> HealthCheckResult:
        """Check a single dependency"""
        start_time = time.time()
        
        try:
            if dep.type == "python_package":
                return await DependencyChecker._check_python_package(dep)
            elif dep.type == "service":
                return await DependencyChecker._check_service(dep)
            elif dep.type == "file":
                return await DependencyChecker._check_file(dep)
            elif dep.type == "network":
                return await DependencyChecker._check_network(dep)
            else:
                return HealthCheckResult(
                    check_name=f"dependency_{dep.name}",
                    check_type=CheckType.DEPENDENCY,
                    status=HealthStatus.UNKNOWN,
                    message=f"Unknown dependency type: {dep.type}",
                    duration=time.time() - start_time
                )
                
        except Exception as e:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.CRITICAL,
                message=f"Dependency check failed: {str(e)}",
                duration=time.time() - start_time
            )
            
    @staticmethod
    async def _check_python_package(dep: DependencyInfo) -> HealthCheckResult:
        """Check Python package dependency"""
        try:
            # Try to import the package
            spec = importlib.util.find_spec(dep.name)
            if spec is None:
                return HealthCheckResult(
                    check_name=f"dependency_{dep.name}",
                    check_type=CheckType.DEPENDENCY,
                    status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                    message=f"Package {dep.name} not found"
                )
                
            # Check version if specified
            if dep.version_requirement:
                module = importlib.import_module(dep.name)
                version = getattr(module, "__version__", None)
                if version:
                    # Simple version check (could be enhanced)
                    return HealthCheckResult(
                        check_name=f"dependency_{dep.name}",
                        check_type=CheckType.DEPENDENCY,
                        status=HealthStatus.HEALTHY,
                        message=f"Package {dep.name} v{version} available",
                        metadata={"version": version}
                    )
                    
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.HEALTHY,
                message=f"Package {dep.name} available"
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                message=f"Package check failed: {str(e)}"
            )
            
    @staticmethod
    async def _check_service(dep: DependencyInfo) -> HealthCheckResult:
        """Check service dependency"""
        if not dep.endpoint:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.UNKNOWN,
                message="No endpoint specified for service check"
            )
            
        try:
            # Parse endpoint
            if dep.endpoint.startswith("http"):
                # HTTP health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        dep.endpoint,
                        timeout=aiohttp.ClientTimeout(total=dep.timeout)
                    ) as response:
                        if response.status == 200:
                            status = HealthStatus.HEALTHY
                            message = f"Service {dep.name} is healthy"
                        else:
                            status = HealthStatus.UNHEALTHY
                            message = f"Service {dep.name} returned {response.status}"
            else:
                # TCP socket check
                host, port = dep.endpoint.split(":")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(dep.timeout)
                result = sock.connect_ex((host, int(port)))
                sock.close()
                
                if result == 0:
                    status = HealthStatus.HEALTHY
                    message = f"Service {dep.name} is reachable"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Service {dep.name} is not reachable"
                    
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=status,
                message=message
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                message=f"Service check failed: {str(e)}"
            )
            
    @staticmethod
    async def _check_file(dep: DependencyInfo) -> HealthCheckResult:
        """Check file dependency"""
        try:
            path = Path(dep.endpoint or dep.name)
            if path.exists():
                return HealthCheckResult(
                    check_name=f"dependency_{dep.name}",
                    check_type=CheckType.DEPENDENCY,
                    status=HealthStatus.HEALTHY,
                    message=f"File {path} exists",
                    metadata={"size": path.stat().st_size}
                )
            else:
                return HealthCheckResult(
                    check_name=f"dependency_{dep.name}",
                    check_type=CheckType.DEPENDENCY,
                    status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                    message=f"File {path} not found"
                )
                
        except Exception as e:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                message=f"File check failed: {str(e)}"
            )
            
    @staticmethod
    async def _check_network(dep: DependencyInfo) -> HealthCheckResult:
        """Check network connectivity"""
        try:
            # Simple ping-like check
            host = dep.endpoint or "8.8.8.8"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(dep.timeout)
            
            # Try common ports
            for port in [80, 443, 53]:
                result = sock.connect_ex((host, port))
                if result == 0:
                    sock.close()
                    return HealthCheckResult(
                        check_name=f"dependency_{dep.name}",
                        check_type=CheckType.DEPENDENCY,
                        status=HealthStatus.HEALTHY,
                        message=f"Network connectivity to {host} confirmed"
                    )
                    
            sock.close()
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot reach {host}"
            )
            
        except Exception as e:
            return HealthCheckResult(
                check_name=f"dependency_{dep.name}",
                check_type=CheckType.DEPENDENCY,
                status=HealthStatus.CRITICAL if dep.required else HealthStatus.DEGRADED,
                message=f"Network check failed: {str(e)}"
            )


class ResourceChecker:
    """Check system resources"""
    
    @staticmethod
    def get_current_resources() -> Dict[str, float]:
        """Get current resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_available": 100 - cpu_percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent_free": 100 - memory.percent,
                "disk_available_gb": disk.free / (1024**3),
                "disk_percent_free": 100 - disk.percent
            }
        except Exception as e:
            logger.error(f"Failed to get resource info: {e}")
            return {}
            
    @staticmethod
    async def check_resource(
        name: str,
        requirement: ResourceRequirement,
        current_value: float
    ) -> HealthCheckResult:
        """Check a resource requirement"""
        status = requirement.check_availability(current_value)
        
        if status == HealthStatus.HEALTHY:
            message = f"{name} is sufficient: {current_value:.2f}{requirement.unit}"
        elif status == HealthStatus.DEGRADED:
            message = (
                f"{name} below recommended: {current_value:.2f}{requirement.unit} "
                f"(recommended: {requirement.recommended}{requirement.unit})"
            )
        elif status == HealthStatus.UNHEALTHY:
            message = (
                f"{name} below minimum: {current_value:.2f}{requirement.unit} "
                f"(minimum: {requirement.minimum}{requirement.unit})"
            )
        else:  # CRITICAL
            message = (
                f"{name} critically low: {current_value:.2f}{requirement.unit} "
                f"(critical: {requirement.critical}{requirement.unit})"
            )
            
        return HealthCheckResult(
            check_name=f"resource_{name}",
            check_type=CheckType.RESOURCE,
            status=status,
            message=message,
            metadata={
                "current": current_value,
                "minimum": requirement.minimum,
                "recommended": requirement.recommended,
                "critical": requirement.critical,
                "unit": requirement.unit
            }
        )


class ToolHealthMonitor:
    """
    Comprehensive health monitoring system for tools
    
    Features:
    - Periodic health checks
    - Dependency verification
    - Resource monitoring
    - Alert management
    - Health reporting
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        monitor: Optional[ToolMonitor] = None,
        analytics: Optional[ToolAnalytics] = None,
        check_interval_seconds: int = 60,
        enable_auto_checks: bool = True
    ):
        """
        Initialize health monitor
        
        Args:
            registry: Tool registry
            monitor: Tool monitor
            analytics: Tool analytics
            check_interval_seconds: Interval between checks
            enable_auto_checks: Enable automatic checking
        """
        self.registry = registry or ToolRegistry()
        self.monitor = monitor or get_monitor()
        self.analytics = analytics or ToolAnalytics(self.monitor)
        self.check_interval = check_interval_seconds
        self.enable_auto_checks = enable_auto_checks
        
        # Storage
        self._health_reports: Dict[str, ToolHealthReport] = {}
        self._dependencies: Dict[str, List[DependencyInfo]] = {}
        self._resources: Dict[str, List[ResourceRequirement]] = {}
        self._alert_rules: Dict[str, List[AlertRule]] = {}
        self._checkers: List[HealthChecker] = [
            LivenessCheck(),
            ReadinessCheck()
        ]
        
        # Alert handlers
        self._alert_handlers: Dict[str, Callable] = {
            "log": self._handle_log_alert,
            "email": self._handle_email_alert,
            "webhook": self._handle_webhook_alert
        }
        
        # Threading
        self._lock = threading.RLock()
        self._check_thread = None
        self._stop_event = threading.Event()
        
        if enable_auto_checks:
            self.start()
            
    def start(self):
        """Start health monitoring"""
        if self._check_thread and self._check_thread.is_alive():
            return
            
        self._stop_event.clear()
        self._check_thread = threading.Thread(
            target=self._check_loop,
            daemon=True
        )
        self._check_thread.start()
        logger.info("Health monitoring started")
        
    def stop(self):
        """Stop health monitoring"""
        self._stop_event.set()
        if self._check_thread:
            self._check_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
        
    def register_dependencies(
        self,
        tool_name: str,
        dependencies: List[DependencyInfo]
    ):
        """Register tool dependencies"""
        with self._lock:
            self._dependencies[tool_name] = dependencies
            
    def register_resources(
        self,
        tool_name: str,
        resources: List[Tuple[str, ResourceRequirement]]
    ):
        """Register resource requirements"""
        with self._lock:
            self._resources[tool_name] = resources
            
    def register_alert_rule(self, tool_name: str, rule: AlertRule):
        """Register an alert rule"""
        with self._lock:
            if tool_name not in self._alert_rules:
                self._alert_rules[tool_name] = []
            self._alert_rules[tool_name].append(rule)
            
    def add_health_checker(self, checker: HealthChecker):
        """Add a custom health checker"""
        self._checkers.append(checker)
        
    async def check_tool_health(self, tool_name: str) -> ToolHealthReport:
        """
        Perform comprehensive health check for a tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Health report
        """
        # Get tool instance
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return ToolHealthReport(
                tool_name=tool_name,
                overall_status=HealthStatus.UNKNOWN,
                check_results=[],
                dependencies={},
                resources={},
                alerts_triggered=[],
                last_check=datetime.now(),
                next_check=datetime.now() + timedelta(seconds=self.check_interval)
            )
            
        check_results = []
        
        # Run standard health checks
        for checker in self._checkers:
            result = await checker.check(tool)
            check_results.append(result)
            
        # Check dependencies
        dep_status = {}
        if tool_name in self._dependencies:
            for dep in self._dependencies[tool_name]:
                result = await DependencyChecker.check_dependency(dep)
                check_results.append(result)
                dep_status[dep.name] = result.status
                
        # Check resources
        resource_status = {}
        if tool_name in self._resources:
            current_resources = ResourceChecker.get_current_resources()
            for res_name, requirement in self._resources[tool_name]:
                if res_name in current_resources:
                    result = await ResourceChecker.check_resource(
                        res_name,
                        requirement,
                        current_resources[res_name]
                    )
                    check_results.append(result)
                    resource_status[res_name] = result.status
                    
        # Determine overall status
        statuses = [r.status for r in check_results]
        if any(s == HealthStatus.CRITICAL for s in statuses):
            overall_status = HealthStatus.CRITICAL
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.UNKNOWN
            
        # Check alerts
        alerts_triggered = await self._check_alerts(
            tool_name,
            overall_status,
            check_results
        )
        
        # Create report
        report = ToolHealthReport(
            tool_name=tool_name,
            overall_status=overall_status,
            check_results=check_results,
            dependencies=dep_status,
            resources=resource_status,
            alerts_triggered=alerts_triggered,
            last_check=datetime.now(),
            next_check=datetime.now() + timedelta(seconds=self.check_interval)
        )
        
        # Store report
        with self._lock:
            self._health_reports[tool_name] = report
            
        return report
        
    async def _check_alerts(
        self,
        tool_name: str,
        status: HealthStatus,
        results: List[HealthCheckResult]
    ) -> List[str]:
        """Check and trigger alerts"""
        triggered = []
        
        if tool_name not in self._alert_rules:
            return triggered
            
        # Build context for alert evaluation
        context = {
            "tool_name": tool_name,
            "status": status.value,
            "is_healthy": status == HealthStatus.HEALTHY,
            "is_degraded": status == HealthStatus.DEGRADED,
            "is_unhealthy": status == HealthStatus.UNHEALTHY,
            "is_critical": status == HealthStatus.CRITICAL,
            "check_results": {r.check_name: r.status.value for r in results},
            "failed_checks": [
                r.check_name for r in results
                if r.status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]
            ]
        }
        
        # Add performance metrics
        stats = self.monitor.get_performance_stats(tool_name)
        if tool_name in stats:
            tool_stats = stats[tool_name]
            context.update({
                "error_rate": (
                    tool_stats.failure_count / tool_stats.execution_count
                    if tool_stats.execution_count > 0 else 0
                ),
                "avg_duration": tool_stats.avg_duration or 0,
                "execution_count": tool_stats.execution_count
            })
            
        # Check each rule
        for rule in self._alert_rules[tool_name]:
            if rule.should_trigger(context):
                # Trigger alert
                message = rule.message_template.format(**context)
                await self._trigger_alert(rule, message, context)
                
                # Update rule state
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1
                
                triggered.append(rule.name)
                
        return triggered
        
    async def _trigger_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ):
        """Trigger an alert"""
        for action in rule.actions:
            handler = self._alert_handlers.get(action)
            if handler:
                try:
                    await handler(rule, message, context)
                except Exception as e:
                    logger.error(f"Failed to handle alert action {action}: {e}")
                    
    async def _handle_log_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ):
        """Handle log alert action"""
        log_level = {
            "info": logger.info,
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical
        }.get(rule.severity, logger.warning)
        
        log_level(f"[ALERT] {rule.name}: {message}")
        
    async def _handle_email_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ):
        """Handle email alert action (placeholder)"""
        # This would integrate with email service
        logger.info(f"Email alert would be sent: {message}")
        
    async def _handle_webhook_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ):
        """Handle webhook alert action (placeholder)"""
        # This would make HTTP POST to webhook URL
        logger.info(f"Webhook alert would be sent: {message}")
        
    def _check_loop(self):
        """Background health check loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not self._stop_event.is_set():
            try:
                # Get all registered tools
                tools = self.registry.list_tools()
                
                # Check each tool
                for tool_info in tools:
                    if self._stop_event.is_set():
                        break
                        
                    tool_name = tool_info["name"]
                    loop.run_until_complete(self.check_tool_health(tool_name))
                    
                # Wait for next interval
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                self._stop_event.wait(10)  # Brief pause on error
                
    def get_health_report(
        self,
        tool_name: Optional[str] = None
    ) -> Dict[str, ToolHealthReport]:
        """Get health reports"""
        with self._lock:
            if tool_name:
                report = self._health_reports.get(tool_name)
                return {tool_name: report} if report else {}
            else:
                return self._health_reports.copy()
                
    def get_unhealthy_tools(self) -> List[str]:
        """Get list of unhealthy tools"""
        with self._lock:
            return [
                name for name, report in self._health_reports.items()
                if report.overall_status in [
                    HealthStatus.UNHEALTHY,
                    HealthStatus.CRITICAL
                ]
            ]
            
    def export_health_dashboard(self) -> Dict[str, Any]:
        """Export health dashboard data"""
        with self._lock:
            healthy_count = sum(
                1 for r in self._health_reports.values()
                if r.overall_status == HealthStatus.HEALTHY
            )
            degraded_count = sum(
                1 for r in self._health_reports.values()
                if r.overall_status == HealthStatus.DEGRADED
            )
            unhealthy_count = sum(
                1 for r in self._health_reports.values()
                if r.overall_status == HealthStatus.UNHEALTHY
            )
            critical_count = sum(
                1 for r in self._health_reports.values()
                if r.overall_status == HealthStatus.CRITICAL
            )
            
            return {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tools": len(self._health_reports),
                    "healthy": healthy_count,
                    "degraded": degraded_count,
                    "unhealthy": unhealthy_count,
                    "critical": critical_count
                },
                "tools": {
                    name: report.to_dict()
                    for name, report in self._health_reports.items()
                },
                "alerts": {
                    tool: [
                        {
                            "name": rule.name,
                            "severity": rule.severity,
                            "last_triggered": (
                                rule.last_triggered.isoformat()
                                if rule.last_triggered else None
                            ),
                            "trigger_count": rule.trigger_count
                        }
                        for rule in rules
                    ]
                    for tool, rules in self._alert_rules.items()
                }
            }


# Global health monitor instance
_health_monitor: Optional[ToolHealthMonitor] = None
_health_lock = threading.Lock()


def get_health_monitor(
    registry: Optional[ToolRegistry] = None,
    **kwargs
) -> ToolHealthMonitor:
    """
    Get or create global health monitor instance
    
    Args:
        registry: Optional tool registry
        **kwargs: Additional monitor arguments
        
    Returns:
        ToolHealthMonitor instance
    """
    global _health_monitor
    
    with _health_lock:
        if _health_monitor is None:
            _health_monitor = ToolHealthMonitor(registry, **kwargs)
        return _health_monitor


# Export main components
__all__ = [
    'HealthStatus',
    'CheckType',
    'HealthCheckResult',
    'DependencyInfo',
    'ResourceRequirement',
    'AlertRule',
    'ToolHealthReport',
    'HealthChecker',
    'LivenessCheck',
    'ReadinessCheck',
    'DependencyChecker',
    'ResourceChecker',
    'ToolHealthMonitor',
    'get_health_monitor'
]