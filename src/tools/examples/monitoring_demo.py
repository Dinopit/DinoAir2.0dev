"""
Monitoring System Demo

This example demonstrates how to use the comprehensive monitoring system
for tool execution tracking, telemetry, analytics, and health monitoring.
"""

import asyncio
import time
import random
import json
from datetime import datetime, timedelta

# Import monitoring components
from ..monitoring.monitor import (
    ToolMonitor, MetricType, get_monitor
)
from ..monitoring.telemetry import (
    ToolTelemetry, get_telemetry, trace_function
)
from ..monitoring.analytics import (
    ToolAnalytics, TrendDirection
)
from ..monitoring.health import (
    ToolHealthMonitor, HealthStatus, CheckType,
    DependencyInfo, ResourceRequirement, AlertRule,
    get_health_monitor
)

# Import tool components
from ..base import (
    BaseTool, ToolMetadata, ToolParameter, ParameterType,
    ToolResult, ToolCategory
)
from ..registry import ToolRegistry


# Example 1: Create a monitored tool
class DataProcessorTool(BaseTool):
    """A data processing tool with monitoring"""
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="data_processor",
            description="Processes data with monitoring",
            version="1.0.0",
            author="Demo Author",
            category=ToolCategory.DATA_PROCESSING,
            tags=["data", "processing", "monitoring"]
        )
        
    def get_parameters(self) -> dict:
        return {
            "data_size": ToolParameter(
                name="data_size",
                type=ParameterType.INTEGER,
                description="Size of data to process",
                required=True,
                validation=lambda x: x > 0
            ),
            "processing_type": ToolParameter(
                name="processing_type",
                type=ParameterType.ENUM,
                description="Type of processing",
                required=True,
                enum_values=["transform", "aggregate", "filter"]
            ),
            "fail_randomly": ToolParameter(
                name="fail_randomly",
                type=ParameterType.BOOLEAN,
                description="Simulate random failures",
                required=False,
                default=False
            )
        }
        
    def execute(self, **kwargs) -> ToolResult:
        data_size = kwargs["data_size"]
        processing_type = kwargs["processing_type"]
        fail_randomly = kwargs.get("fail_randomly", False)
        
        # Simulate processing time based on data size
        processing_time = data_size * 0.001 + random.uniform(0.01, 0.05)
        time.sleep(processing_time)
        
        # Simulate random failures
        if fail_randomly and random.random() < 0.2:
            error_types = ["DataError", "ProcessingError", "TimeoutError"]
            error_type = random.choice(error_types)
            return ToolResult(
                success=False,
                output={"error": error_type},
                execution_time=processing_time
            )
            
        # Simulate successful processing
        return ToolResult(
            success=True,
            output={
                "processed_items": data_size,
                "processing_type": processing_type,
                "duration": processing_time
            },
            execution_time=processing_time
        )


# Example 2: Basic monitoring setup
def demo_basic_monitoring():
    """Demonstrate basic monitoring setup and usage"""
    print("=== Basic Monitoring Demo ===\n")
    
    # Create monitor instance
    monitor = ToolMonitor(retention_hours=1)
    
    # Create and execute tool
    tool = DataProcessorTool()
    
    # Monitor tool executions
    for i in range(5):
        # Start monitoring execution
        exec_id = f"exec_{i}"
        params = {
            "data_size": random.randint(100, 1000),
            "processing_type": random.choice(["transform", "aggregate", "filter"])
        }
        
        metrics = monitor.start_execution(
            tool.get_metadata().name,
            exec_id,
            params
        )
        
        # Execute tool
        result = tool.execute(**params)
        
        # End monitoring
        monitor.end_execution(
            exec_id,
            success=result.success,
            output=result.output
        )
        
        print(f"Execution {i + 1}: {'Success' if result.success else 'Failed'}")
        
    # Get performance statistics
    stats = monitor.get_performance_stats(tool.get_metadata().name)
    tool_stats = stats.get(tool.get_metadata().name)
    
    if tool_stats:
        print(f"\nPerformance Statistics:")
        print(f"  Total executions: {tool_stats.execution_count}")
        print(f"  Success rate: {tool_stats.success_rate:.1%}")
        print(f"  Average duration: {tool_stats.avg_duration:.3f}s")
        print(f"  P95 duration: {tool_stats.p95_duration:.3f}s")
        
    # Export metrics in Prometheus format
    prometheus_metrics = monitor.export_metrics_prometheus()
    print(f"\nPrometheus Metrics (sample):")
    print(prometheus_metrics[:500] + "...")
    
    return monitor


# Example 3: Telemetry and tracing
def demo_telemetry():
    """Demonstrate telemetry and distributed tracing"""
    print("\n=== Telemetry and Tracing Demo ===\n")
    
    # Create telemetry instance
    telemetry = ToolTelemetry(enable_tracing=True)
    
    # Create traced function
    @trace_function("data_pipeline")
    def process_data_pipeline(data_size):
        """Simulated data pipeline with tracing"""
        with telemetry.trace_operation("validate_input") as span:
            span.set_tag("data_size", data_size)
            time.sleep(0.01)
            
        with telemetry.trace_operation("transform_data") as span:
            span.set_tag("transformation", "normalize")
            time.sleep(0.02)
            
        with telemetry.trace_operation("save_results") as span:
            span.log("save_started", {"location": "database"})
            time.sleep(0.01)
            span.log("save_completed", {"records": data_size})
            
        return {"processed": data_size}
        
    # Execute traced pipeline
    result = process_data_pipeline(1000)
    print(f"Pipeline result: {result}")
    
    # Get active traces
    traces = telemetry.get_active_traces()
    print(f"\nActive traces: {len(traces)}")
    
    # Export traces in Jaeger format
    jaeger_traces = telemetry.export_traces_jaeger()
    print(f"\nJaeger trace export (first trace):")
    if jaeger_traces:
        print(json.dumps(jaeger_traces[0], indent=2)[:500] + "...")
        
    # Log events
    telemetry.log_event(
        "info",
        "pipeline_complete",
        "Data pipeline completed successfully",
        "data_processor",
        {"items_processed": 1000}
    )
    
    # Get event logs
    logs = telemetry.get_event_logs(tool_name="data_processor")
    print(f"\nEvent logs: {len(logs)} events")
    
    return telemetry


# Example 4: Analytics and insights
def demo_analytics():
    """Demonstrate analytics and trend analysis"""
    print("\n=== Analytics Demo ===\n")
    
    # Create monitor and analytics
    monitor = ToolMonitor()
    analytics = ToolAnalytics(monitor)
    
    # Generate sample data over time
    tool = DataProcessorTool()
    tool_name = tool.get_metadata().name
    
    print("Generating sample execution data...")
    
    # Simulate executions with trends
    for hour in range(24):
        # Simulate varying load during the day
        executions_per_hour = 20 if 9 <= hour <= 17 else 5
        
        for i in range(executions_per_hour):
            exec_id = f"exec_{hour}_{i}"
            
            # Simulate degrading performance over time
            base_size = 500
            size_multiplier = 1 + (hour / 24) * 0.5
            data_size = int(base_size * size_multiplier)
            
            # Start execution
            params = {
                "data_size": data_size,
                "processing_type": "transform",
                "fail_randomly": hour > 20  # More failures late
            }
            
            monitor.start_execution(tool_name, exec_id, params)
            result = tool.execute(**params)
            monitor.end_execution(exec_id, result.success, result.output)
            
    # Get tool insights
    insights = analytics.get_tool_insights(hours=24)
    tool_insight = insights.get(tool_name)
    
    if tool_insight:
        print(f"\nTool Insights for {tool_name}:")
        print(f"  Reliability score: {tool_insight.reliability_score:.1f}/100")
        print(f"  Performance score: {tool_insight.performance_score:.1f}/100")
        print(f"  Usage score: {tool_insight.usage_score:.1f}/100")
        print(f"  Overall health: {tool_insight.overall_health:.1f}/100")
        
        if tool_insight.recommendations:
            print(f"\nRecommendations:")
            for rec in tool_insight.recommendations:
                print(f"  - {rec}")
                
    # Analyze trends
    trends = analytics.analyze_trends(tool_name, hours=24)
    
    print(f"\nTrend Analysis:")
    for metric, trend_list in trends.items():
        for trend in trend_list:
            direction = "↑" if trend.direction == TrendDirection.INCREASING else "↓"
            print(f"  {metric}: {direction} {trend.change_percentage:.1f}% - {trend.description}")
            
    # Detect anomalies
    anomalies = analytics.detect_anomalies(tool_name, hours=24)
    
    if anomalies:
        print(f"\nAnomalies Detected:")
        for anomaly in anomalies:
            print(f"  - {anomaly.type.value}: {anomaly.description}")
            print(f"    Severity: {anomaly.severity}, Score: {anomaly.score:.2f}")
            
    # Generate analytics report
    report = analytics.generate_report(hours=24)
    print(f"\nAnalytics Report Summary:")
    print(f"  Report period: {report['period']['start']} to {report['period']['end']}")
    print(f"  Total tools analyzed: {len(report['tools'])}")
    
    return analytics


# Example 5: Health monitoring
def demo_health_monitoring():
    """Demonstrate health monitoring and alerts"""
    print("\n=== Health Monitoring Demo ===\n")
    
    # Create registry and monitoring components
    registry = ToolRegistry()
    monitor = ToolMonitor()
    
    # Create health monitor
    health_monitor = ToolHealthMonitor(
        registry=registry,
        monitor=monitor,
        check_interval_seconds=5,
        enable_auto_checks=False
    )
    
    # Register tool
    registry.register_tool(DataProcessorTool)
    tool_name = "data_processor"
    
    # Register dependencies
    dependencies = [
        DependencyInfo(
            name="database",
            type="service",
            endpoint="localhost:5432",
            required=True
        ),
        DependencyInfo(
            name="cache_service",
            type="service",
            endpoint="localhost:6379",
            required=False
        )
    ]
    
    health_monitor.register_dependencies(tool_name, dependencies)
    
    # Register resource requirements
    resources = [
        ("cpu_available", ResourceRequirement(
            resource_type="cpu",
            minimum=20.0,
            recommended=40.0,
            critical=10.0,
            unit="%"
        )),
        ("memory_available_gb", ResourceRequirement(
            resource_type="memory",
            minimum=2.0,
            recommended=4.0,
            critical=1.0,
            unit="GB"
        ))
    ]
    
    health_monitor.register_resources(tool_name, resources)
    
    # Register alert rules
    alert_rules = [
        AlertRule(
            name="high_failure_rate",
            condition="error_rate > 0.1",
            severity="warning",
            message_template="Tool {tool_name} has high failure rate: {error_rate:.1%}",
            cooldown_minutes=15
        ),
        AlertRule(
            name="performance_degradation",
            condition="avg_duration > baseline * 1.5",
            severity="warning",
            message_template="Tool {tool_name} performance degraded by {degradation:.1%}",
            cooldown_minutes=30
        )
    ]
    
    for rule in alert_rules:
        health_monitor.register_alert_rule(tool_name, rule)
        
    # Perform health check
    print("Performing health check...")
    
    # Run async health check
    async def run_health_check():
        report = await health_monitor.check_tool_health(tool_name)
        return report
        
    report = asyncio.run(run_health_check())
    
    print(f"\nHealth Check Report for {tool_name}:")
    print(f"  Overall status: {report.overall_status.value}")
    print(f"  Check timestamp: {report.timestamp}")
    
    print(f"\nCheck Results:")
    for result in report.check_results:
        status_icon = "✓" if result.status == HealthStatus.HEALTHY else "✗"
        print(f"  {status_icon} {result.check_type.value}: {result.status.value}")
        if result.message:
            print(f"    Message: {result.message}")
            
    # Check system health
    system_health = health_monitor.get_system_health()
    print(f"\nSystem Health Summary:")
    print(f"  Total tools: {system_health['summary']['total_tools']}")
    print(f"  Healthy: {system_health['summary']['healthy']}")
    print(f"  Degraded: {system_health['summary']['degraded']}")
    print(f"  Unhealthy: {system_health['summary']['unhealthy']}")
    
    # Export health dashboard
    dashboard = health_monitor.export_health_dashboard()
    print(f"\nHealth Dashboard Export:")
    print(f"  Dashboard generated at: {dashboard['timestamp']}")
    print(f"  Active alerts: {len(dashboard['alerts'])}")
    
    # Cleanup
    health_monitor.stop()
    registry.shutdown()
    
    return health_monitor


# Example 6: Custom metrics
def demo_custom_metrics():
    """Demonstrate custom metric collection"""
    print("\n=== Custom Metrics Demo ===\n")
    
    monitor = ToolMonitor()
    
    # Record custom metrics
    print("Recording custom metrics...")
    
    # Counter metric
    for i in range(10):
        monitor.record_metric(
            "api_requests_total",
            1,
            MetricType.COUNTER,
            {"endpoint": "/process", "method": "POST"}
        )
        
    # Gauge metric
    monitor.record_metric(
        "active_connections",
        25,
        MetricType.GAUGE,
        {"service": "data_processor"}
    )
    
    # Histogram metric
    response_times = [0.1, 0.15, 0.2, 0.12, 0.18, 0.25, 0.11, 0.3, 0.14, 0.16]
    for rt in response_times:
        monitor.record_metric(
            "response_time_seconds",
            rt,
            MetricType.HISTOGRAM,
            {"endpoint": "/process"}
        )
        
    # Get metrics
    print("\nRecorded Metrics:")
    
    api_metrics = monitor.get_metrics("api_requests_total")
    print(f"  API Requests: {len(api_metrics.get('api_requests_total', []))} samples")
    
    gauge_metrics = monitor.get_metrics("active_connections")
    if gauge_metrics.get("active_connections"):
        latest = gauge_metrics["active_connections"][-1]
        print(f"  Active Connections: {latest.value}")
        
    histogram_metrics = monitor.get_metrics("response_time_seconds")
    if histogram_metrics.get("response_time_seconds"):
        values = [m.value for m in histogram_metrics["response_time_seconds"]]
        avg_response = sum(values) / len(values)
        print(f"  Avg Response Time: {avg_response:.3f}s")
        
    return monitor


# Example 7: Integration with monitoring config
def demo_config_integration():
    """Demonstrate integration with monitoring configuration"""
    print("\n=== Configuration Integration Demo ===\n")
    
    # Load monitoring configuration
    config_path = "../config/monitoring_config.json"
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        print("Loaded monitoring configuration:")
        print(f"  Monitoring enabled: {config['monitoring']['enabled']}")
        print(f"  Retention hours: {config['monitoring']['retention_hours']}")
        print(f"  Telemetry enabled: {config['telemetry']['enabled']}")
        print(f"  Analytics enabled: {config['analytics']['enabled']}")
        print(f"  Health monitoring enabled: {config['health_monitoring']['enabled']}")
        
        # Create components based on config
        if config['monitoring']['enabled']:
            monitor = ToolMonitor(
                retention_hours=config['monitoring']['retention_hours']
            )
            print("\n✓ Monitor created with configuration")
            
        if config['telemetry']['enabled']:
            telemetry = ToolTelemetry(
                enable_tracing=config['telemetry']['tracing']['enabled']
            )
            print("✓ Telemetry created with configuration")
            
        if config['analytics']['enabled']:
            analytics = ToolAnalytics(monitor)
            print("✓ Analytics created with configuration")
            
        # Show configured alert rules
        if config['health_monitoring']['alert_rules']['enabled']:
            print("\nConfigured Alert Rules:")
            for rule in config['health_monitoring']['alert_rules']['rules']:
                print(f"  - {rule['name']} ({rule['severity']}): {rule['condition']}")
                
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        print("Using default configuration...")
        
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")


# Main demo function
def main():
    """Run all monitoring demos"""
    print("=" * 60)
    print("Tool Monitoring System Demo")
    print("=" * 60)
    
    try:
        # Run demos
        monitor = demo_basic_monitoring()
        telemetry = demo_telemetry()
        analytics = demo_analytics()
        health_monitor = demo_health_monitoring()
        custom_monitor = demo_custom_metrics()
        demo_config_integration()
        
        print("\n" + "=" * 60)
        print("Monitoring demo completed successfully!")
        print("=" * 60)
        
        print("\nKey Takeaways:")
        print("1. Use ToolMonitor for execution tracking and metrics")
        print("2. Use ToolTelemetry for distributed tracing and events")
        print("3. Use ToolAnalytics for insights and trend analysis")
        print("4. Use ToolHealthMonitor for health checks and alerts")
        print("5. Configure monitoring via monitoring_config.json")
        print("6. Export metrics in Prometheus/Jaeger formats")
        
    except Exception as e:
        print(f"\nError in demo: {str(e)}")
        raise


if __name__ == "__main__":
    main()