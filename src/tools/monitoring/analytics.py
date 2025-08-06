"""
Tool Analytics Dashboard

This module provides analytics capabilities for tool usage,
including performance trends, error patterns, resource usage,
and predictive insights.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import re
from enum import Enum

from .monitor import (
    ToolMonitor, get_monitor, ExecutionMetrics,
    PerformanceStats, ErrorInfo
)
from .telemetry import ToolTelemetry, get_telemetry


logger = logging.getLogger(__name__)


class TrendDirection(Enum):
    """Direction of a trend"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnomalyType(Enum):
    """Types of anomalies"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_SPIKE = "error_spike"
    UNUSUAL_PATTERN = "unusual_pattern"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    AVAILABILITY_ISSUE = "availability_issue"


@dataclass
class Trend:
    """Represents a trend in metrics"""
    metric_name: str
    direction: TrendDirection
    change_percentage: float
    start_value: float
    end_value: float
    time_window: timedelta
    confidence: float
    data_points: int
    
    @property
    def is_significant(self) -> bool:
        """Check if trend is significant"""
        return (
            abs(self.change_percentage) > 10 and
            self.confidence > 0.8 and
            self.data_points >= 10
        )


@dataclass
class Anomaly:
    """Represents an anomaly in tool behavior"""
    type: AnomalyType
    tool_name: str
    timestamp: datetime
    severity: str  # low, medium, high, critical
    description: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "description": self.description,
            "metrics": self.metrics,
            "recommendations": self.recommendations
        }


@dataclass
class ToolInsight:
    """Insights about a tool"""
    tool_name: str
    usage_score: float  # 0-100
    reliability_score: float  # 0-100
    performance_score: float  # 0-100
    overall_health: str  # excellent, good, fair, poor
    top_errors: List[Tuple[str, int]]
    usage_pattern: str  # constant, periodic, sporadic, declining
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsagePattern:
    """Usage pattern analysis"""
    pattern_type: str  # hourly, daily, weekly
    peak_times: List[Tuple[int, float]]  # (hour/day, usage)
    low_times: List[Tuple[int, float]]
    average_usage: float
    variance: float
    predictability_score: float  # 0-1


class ToolAnalytics:
    """
    Analytics engine for tool monitoring data
    
    Provides comprehensive analytics including:
    - Usage patterns and trends
    - Performance analysis
    - Error pattern detection
    - Resource usage tracking
    - Predictive insights
    - Anomaly detection
    """
    
    def __init__(
        self,
        monitor: Optional[ToolMonitor] = None,
        telemetry: Optional[ToolTelemetry] = None,
        anomaly_threshold: float = 2.0,  # Standard deviations
        trend_window_hours: int = 24,
        min_data_points: int = 10
    ):
        """
        Initialize analytics engine
        
        Args:
            monitor: Tool monitor instance
            telemetry: Tool telemetry instance
            anomaly_threshold: Threshold for anomaly detection
            trend_window_hours: Default window for trend analysis
            min_data_points: Minimum data points for analysis
        """
        self.monitor = monitor or get_monitor()
        self.telemetry = telemetry or get_telemetry()
        self.anomaly_threshold = anomaly_threshold
        self.trend_window_hours = trend_window_hours
        self.min_data_points = min_data_points
        
        # Cache for computed analytics
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
        
    def get_tool_insights(
        self,
        tool_name: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, ToolInsight]:
        """
        Get comprehensive insights for tools
        
        Args:
            tool_name: Optional specific tool name
            hours: Time window in hours
            
        Returns:
            Tool insights by name
        """
        insights = {}
        
        # Get performance stats
        stats = self.monitor.get_performance_stats(tool_name)
        
        for name, tool_stats in stats.items():
            if not tool_stats or tool_stats.execution_count == 0:
                continue
                
            # Calculate scores
            usage_score = self._calculate_usage_score(tool_stats, hours)
            reliability_score = self._calculate_reliability_score(tool_stats)
            performance_score = self._calculate_performance_score(tool_stats)
            
            # Determine overall health
            avg_score = (usage_score + reliability_score + performance_score) / 3
            if avg_score >= 90:
                health = "excellent"
            elif avg_score >= 75:
                health = "good"
            elif avg_score >= 50:
                health = "fair"
            else:
                health = "poor"
                
            # Get top errors
            errors = self.monitor.get_error_summary(name, hours)
            top_errors = self._get_top_errors(errors)
            
            # Analyze usage pattern
            usage_pattern = self._analyze_usage_pattern(name, hours)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                name, tool_stats, reliability_score, performance_score
            )
            
            insights[name] = ToolInsight(
                tool_name=name,
                usage_score=usage_score,
                reliability_score=reliability_score,
                performance_score=performance_score,
                overall_health=health,
                top_errors=top_errors,
                usage_pattern=usage_pattern,
                recommendations=recommendations,
                metadata={
                    "total_executions": tool_stats.execution_count,
                    "avg_duration": tool_stats.avg_duration,
                    "success_rate": (
                        tool_stats.success_count / tool_stats.execution_count
                        if tool_stats.execution_count > 0 else 0
                    )
                }
            )
            
        return insights
        
    def analyze_trends(
        self,
        tool_name: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        hours: Optional[int] = None
    ) -> Dict[str, List[Trend]]:
        """
        Analyze trends in tool metrics
        
        Args:
            tool_name: Optional tool name filter
            metrics: Optional specific metrics to analyze
            hours: Time window (uses default if not specified)
            
        Returns:
            Trends by metric name
        """
        hours = hours or self.trend_window_hours
        trends = defaultdict(list)
        
        # Get recent executions
        executions = self.monitor.get_recent_executions(
            tool_name=tool_name,
            limit=1000
        )
        
        if len(executions) < self.min_data_points:
            return dict(trends)
            
        # Filter by time window
        cutoff_time = datetime.now() - timedelta(hours=hours)
        executions = [
            e for e in executions
            if e.start_time > cutoff_time
        ]
        
        # Analyze specific metrics
        if not metrics:
            metrics = ["duration", "success_rate", "error_rate"]
            
        for metric in metrics:
            trend = self._analyze_metric_trend(executions, metric, hours)
            if trend:
                trends[metric].append(trend)
                
        return dict(trends)
        
    def _analyze_metric_trend(
        self,
        executions: List[ExecutionMetrics],
        metric: str,
        hours: int
    ) -> Optional[Trend]:
        """Analyze trend for a specific metric"""
        if not executions:
            return None
            
        # Extract metric values with timestamps
        data_points = []
        
        for execution in executions:
            timestamp = execution.start_time
            value = None
            
            if metric == "duration" and execution.duration:
                value = execution.duration
            elif metric == "success_rate":
                value = 1.0 if execution.success else 0.0
            elif metric == "error_rate":
                value = 0.0 if execution.success else 1.0
            elif metric == "output_size" and execution.output_size:
                value = execution.output_size
                
            if value is not None:
                data_points.append((timestamp, value))
                
        if len(data_points) < self.min_data_points:
            return None
            
        # Sort by timestamp
        data_points.sort(key=lambda x: x[0])
        
        # Split into first and second half
        mid_point = len(data_points) // 2
        first_half = [v for _, v in data_points[:mid_point]]
        second_half = [v for _, v in data_points[mid_point:]]
        
        # Calculate averages
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        # Calculate trend
        if first_avg == 0:
            change_percentage = 100 if second_avg > 0 else 0
        else:
            change_percentage = ((second_avg - first_avg) / first_avg) * 100
            
        # Determine direction
        if abs(change_percentage) < 5:
            direction = TrendDirection.STABLE
        elif change_percentage > 0:
            direction = TrendDirection.INCREASING
        else:
            direction = TrendDirection.DECREASING
            
        # Check for volatility
        all_values = [v for _, v in data_points]
        if statistics.stdev(all_values) > statistics.mean(all_values) * 0.5:
            direction = TrendDirection.VOLATILE
            
        # Calculate confidence
        confidence = min(1.0, len(data_points) / 100)
        
        return Trend(
            metric_name=metric,
            direction=direction,
            change_percentage=change_percentage,
            start_value=first_avg,
            end_value=second_avg,
            time_window=timedelta(hours=hours),
            confidence=confidence,
            data_points=len(data_points)
        )
        
    def detect_anomalies(
        self,
        tool_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Anomaly]:
        """
        Detect anomalies in tool behavior
        
        Args:
            tool_name: Optional tool name filter
            hours: Time window for analysis
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Get performance stats
        stats = self.monitor.get_performance_stats(tool_name)
        
        for name, tool_stats in stats.items():
            if not tool_stats or tool_stats.execution_count < self.min_data_points:
                continue
                
            # Check for performance degradation
            perf_anomaly = self._check_performance_anomaly(name, tool_stats)
            if perf_anomaly:
                anomalies.append(perf_anomaly)
                
            # Check for error spikes
            error_anomaly = self._check_error_anomaly(name, hours)
            if error_anomaly:
                anomalies.append(error_anomaly)
                
            # Check for unusual patterns
            pattern_anomaly = self._check_pattern_anomaly(name, hours)
            if pattern_anomaly:
                anomalies.append(pattern_anomaly)
                
        return anomalies
        
    def _check_performance_anomaly(
        self,
        tool_name: str,
        stats: PerformanceStats
    ) -> Optional[Anomaly]:
        """Check for performance anomalies"""
        if not stats.durations or len(stats.durations) < self.min_data_points:
            return None
            
        # Calculate statistics
        mean_duration = statistics.mean(stats.durations)
        stdev_duration = statistics.stdev(stats.durations)
        
        # Check recent executions
        recent_executions = self.monitor.get_recent_executions(
            tool_name=tool_name,
            limit=10
        )
        
        recent_durations = [
            e.duration for e in recent_executions
            if e.duration is not None
        ]
        
        if not recent_durations:
            return None
            
        recent_avg = statistics.mean(recent_durations)
        
        # Check if recent average is anomalous
        if recent_avg > mean_duration + (self.anomaly_threshold * stdev_duration):
            severity = "high" if recent_avg > mean_duration * 2 else "medium"
            
            return Anomaly(
                type=AnomalyType.PERFORMANCE_DEGRADATION,
                tool_name=tool_name,
                timestamp=datetime.now(),
                severity=severity,
                description=(
                    f"Tool {tool_name} showing performance degradation. "
                    f"Recent average: {recent_avg:.2f}s, "
                    f"Historical average: {mean_duration:.2f}s"
                ),
                metrics={
                    "recent_avg_duration": recent_avg,
                    "historical_avg_duration": mean_duration,
                    "degradation_factor": recent_avg / mean_duration
                },
                recommendations=[
                    "Check for increased load or data volume",
                    "Review recent code changes",
                    "Monitor resource utilization",
                    "Consider performance profiling"
                ]
            )
            
        return None
        
    def _check_error_anomaly(
        self,
        tool_name: str,
        hours: int
    ) -> Optional[Anomaly]:
        """Check for error anomalies"""
        # Get error summary
        errors = self.monitor.get_error_summary(tool_name, hours)
        
        if not errors:
            return None
            
        # Count total errors
        total_errors = sum(
            sum(e.count for e in error_list)
            for error_list in errors.values()
        )
        
        # Get historical error rate
        stats = self.monitor.get_performance_stats(tool_name)
        historical_error_rate = 0
        
        if tool_name in stats:
            tool_stats = stats[tool_name]
            if tool_stats.execution_count > 0:
                historical_error_rate = (
                    tool_stats.failure_count / tool_stats.execution_count
                )
                
        # Check recent error rate
        recent_executions = self.monitor.get_recent_executions(
            tool_name=tool_name,
            limit=100
        )
        
        recent_failures = sum(
            1 for e in recent_executions
            if not e.success
        )
        
        if len(recent_executions) > 0:
            recent_error_rate = recent_failures / len(recent_executions)
            
            # Check if error rate is anomalous
            if (recent_error_rate > 0.3 and 
                recent_error_rate > historical_error_rate * 2):
                
                # Find most common error
                error_types = Counter()
                for error_list in errors.values():
                    for error in error_list:
                        error_types[error.error_type] += error.count
                        
                most_common = error_types.most_common(1)
                
                return Anomaly(
                    type=AnomalyType.ERROR_SPIKE,
                    tool_name=tool_name,
                    timestamp=datetime.now(),
                    severity="critical" if recent_error_rate > 0.5 else "high",
                    description=(
                        f"Tool {tool_name} experiencing error spike. "
                        f"Recent error rate: {recent_error_rate:.1%}, "
                        f"Historical: {historical_error_rate:.1%}"
                    ),
                    metrics={
                        "recent_error_rate": recent_error_rate,
                        "historical_error_rate": historical_error_rate,
                        "total_recent_errors": total_errors,
                        "most_common_error": (
                            most_common[0][0] if most_common else "Unknown"
                        )
                    },
                    recommendations=[
                        "Investigate recent changes",
                        "Check external dependencies",
                        "Review error logs for patterns",
                        "Consider rollback if critical"
                    ]
                )
                
        return None
        
    def _check_pattern_anomaly(
        self,
        tool_name: str,
        hours: int
    ) -> Optional[Anomaly]:
        """Check for unusual usage patterns"""
        # This is a placeholder for more sophisticated pattern detection
        # Could use time series analysis, ML models, etc.
        return None
        
    def get_usage_patterns(
        self,
        tool_name: Optional[str] = None,
        pattern_type: str = "hourly",
        days: int = 7
    ) -> Dict[str, UsagePattern]:
        """
        Analyze usage patterns
        
        Args:
            tool_name: Optional tool name filter
            pattern_type: Type of pattern (hourly, daily, weekly)
            days: Number of days to analyze
            
        Returns:
            Usage patterns by tool
        """
        patterns = {}
        
        # Get executions
        executions = self.monitor.get_recent_executions(
            tool_name=tool_name,
            limit=10000
        )
        
        # Filter by time
        cutoff_time = datetime.now() - timedelta(days=days)
        executions = [
            e for e in executions
            if e.start_time > cutoff_time
        ]
        
        # Group by tool
        tool_executions = defaultdict(list)
        for execution in executions:
            tool_executions[execution.tool_name].append(execution)
            
        # Analyze each tool
        for name, tool_execs in tool_executions.items():
            if len(tool_execs) < self.min_data_points:
                continue
                
            pattern = self._analyze_usage_pattern_detail(
                tool_execs,
                pattern_type
            )
            
            if pattern:
                patterns[name] = pattern
                
        return patterns
        
    def _analyze_usage_pattern_detail(
        self,
        executions: List[ExecutionMetrics],
        pattern_type: str
    ) -> Optional[UsagePattern]:
        """Analyze usage pattern details"""
        if not executions:
            return None
            
        # Count executions by time bucket
        buckets = defaultdict(int)
        
        for execution in executions:
            if pattern_type == "hourly":
                bucket = execution.start_time.hour
            elif pattern_type == "daily":
                bucket = execution.start_time.weekday()
            else:  # weekly
                bucket = execution.start_time.isocalendar()[1]
                
            buckets[bucket] += 1
            
        if not buckets:
            return None
            
        # Calculate statistics
        counts = list(buckets.values())
        avg_usage = statistics.mean(counts)
        variance = statistics.variance(counts) if len(counts) > 1 else 0
        
        # Find peaks and lows
        sorted_buckets = sorted(
            buckets.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        peak_times = sorted_buckets[:3]
        low_times = sorted_buckets[-3:]
        
        # Calculate predictability
        if avg_usage > 0:
            cv = (variance ** 0.5) / avg_usage  # Coefficient of variation
            predictability = max(0, 1 - cv)
        else:
            predictability = 0
            
        return UsagePattern(
            pattern_type=pattern_type,
            peak_times=peak_times,
            low_times=low_times,
            average_usage=avg_usage,
            variance=variance,
            predictability_score=predictability
        )
        
    def _calculate_usage_score(
        self,
        stats: PerformanceStats,
        hours: int
    ) -> float:
        """Calculate usage score (0-100)"""
        # Base score on execution count relative to time
        expected_executions = hours * 10  # Arbitrary baseline
        
        if stats.execution_count >= expected_executions:
            usage_score = 100
        else:
            usage_score = (stats.execution_count / expected_executions) * 100
            
        # Adjust for recency
        if stats.last_execution:
            hours_since_last = (
                datetime.now() - stats.last_execution
            ).total_seconds() / 3600
            
            if hours_since_last > 24:
                usage_score *= 0.8
            elif hours_since_last > 72:
                usage_score *= 0.5
                
        return min(100, max(0, usage_score))
        
    def _calculate_reliability_score(self, stats: PerformanceStats) -> float:
        """Calculate reliability score (0-100)"""
        if stats.execution_count == 0:
            return 50  # No data
            
        success_rate = stats.success_count / stats.execution_count
        
        # Base score on success rate
        reliability_score = success_rate * 100
        
        # Adjust for volume (more executions = more confidence)
        if stats.execution_count < 10:
            reliability_score *= 0.8
        elif stats.execution_count > 100:
            reliability_score = min(100, reliability_score * 1.1)
            
        return min(100, max(0, reliability_score))
        
    def _calculate_performance_score(self, stats: PerformanceStats) -> float:
        """Calculate performance score (0-100)"""
        if not stats.avg_duration or stats.avg_duration == 0:
            return 100  # No duration data or instant execution
            
        # Score based on average duration
        # Assume 1 second is good, 10 seconds is poor
        if stats.avg_duration <= 1:
            performance_score = 100
        elif stats.avg_duration >= 10:
            performance_score = 20
        else:
            # Linear interpolation
            performance_score = 100 - ((stats.avg_duration - 1) / 9) * 80
            
        # Adjust for consistency (lower variance is better)
        if stats.durations and len(stats.durations) > 1:
            cv = statistics.stdev(stats.durations) / stats.avg_duration
            if cv < 0.2:  # Low variance
                performance_score = min(100, performance_score * 1.1)
            elif cv > 0.5:  # High variance
                performance_score *= 0.9
                
        return min(100, max(0, performance_score))
        
    def _get_top_errors(
        self,
        errors: Dict[str, List[ErrorInfo]],
        limit: int = 5
    ) -> List[Tuple[str, int]]:
        """Get top errors by count"""
        error_counts = Counter()
        
        for error_list in errors.values():
            for error in error_list:
                error_counts[error.error_type] += error.count
                
        return error_counts.most_common(limit)
        
    def _analyze_usage_pattern(
        self,
        tool_name: str,
        hours: int
    ) -> str:
        """Analyze and categorize usage pattern"""
        executions = self.monitor.get_recent_executions(
            tool_name=tool_name,
            limit=1000
        )
        
        if len(executions) < 5:
            return "sporadic"
            
        # Calculate time between executions
        executions.sort(key=lambda e: e.start_time)
        intervals = []
        
        for i in range(1, len(executions)):
            interval = (
                executions[i].start_time - executions[i-1].start_time
            ).total_seconds()
            intervals.append(interval)
            
        if not intervals:
            return "sporadic"
            
        avg_interval = statistics.mean(intervals)
        
        # Categorize based on average interval
        if avg_interval < 300:  # Less than 5 minutes
            return "constant"
        elif avg_interval < 3600:  # Less than 1 hour
            return "periodic"
        elif avg_interval < 86400:  # Less than 1 day
            return "sporadic"
        else:
            return "declining"
            
    def _generate_recommendations(
        self,
        tool_name: str,
        stats: PerformanceStats,
        reliability_score: float,
        performance_score: float
    ) -> List[str]:
        """Generate recommendations for a tool"""
        recommendations = []
        
        # Reliability recommendations
        if reliability_score < 50:
            recommendations.append(
                "Critical: Tool has high failure rate. "
                "Investigate root causes immediately."
            )
        elif reliability_score < 75:
            recommendations.append(
                "Consider implementing retry logic for transient failures"
            )
            
        # Performance recommendations
        if performance_score < 50:
            recommendations.append(
                "Tool performance is poor. Consider optimization or scaling"
            )
        elif performance_score < 75 and stats.p95_duration:
            if stats.p95_duration > stats.avg_duration * 2:
                recommendations.append(
                    "High performance variance detected. "
                    "Investigate outliers and edge cases"
                )
                
        # Usage recommendations
        if stats.execution_count < 10:
            recommendations.append(
                "Low usage detected. Consider if tool is still needed"
            )
        elif stats.last_execution:
            days_since_last = (
                datetime.now() - stats.last_execution
            ).days
            if days_since_last > 7:
                recommendations.append(
                    f"Tool hasn't been used in {days_since_last} days. "
                    "Review if still required"
                )
                
        return recommendations
        
    def generate_report(
        self,
        output_format: str = "json",
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report
        
        Args:
            output_format: Report format (json, html, markdown)
            hours: Time window for analysis
            
        Returns:
            Analytics report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "time_window_hours": hours,
            "insights": {},
            "trends": {},
            "anomalies": [],
            "usage_patterns": {},
            "summary": {}
        }
        
        # Get insights
        insights = self.get_tool_insights(hours=hours)
        report["insights"] = {
            name: {
                "usage_score": insight.usage_score,
                "reliability_score": insight.reliability_score,
                "performance_score": insight.performance_score,
                "overall_health": insight.overall_health,
                "recommendations": insight.recommendations
            }
            for name, insight in insights.items()
        }
        
        # Get trends
        trends = self.analyze_trends(hours=hours)
        report["trends"] = {
            metric: [
                {
                    "direction": trend.direction.value,
                    "change_percentage": trend.change_percentage,
                    "confidence": trend.confidence
                }
                for trend in trend_list
            ]
            for metric, trend_list in trends.items()
        }
        
        # Get anomalies
        anomalies = self.detect_anomalies(hours=hours)
        report["anomalies"] = [a.to_dict() for a in anomalies]
        
        # Get usage patterns
        patterns = self.get_usage_patterns(days=7)
        report["usage_patterns"] = {
            name: {
                "pattern_type": pattern.pattern_type,
                "predictability_score": pattern.predictability_score,
                "peak_times": pattern.peak_times[:3]
            }
            for name, pattern in patterns.items()
        }
        
        # Generate summary
        report["summary"] = self._generate_summary(
            insights, trends, anomalies, patterns
        )
        
        return report
        
    def _generate_summary(
        self,
        insights: Dict[str, ToolInsight],
        trends: Dict[str, List[Trend]],
        anomalies: List[Anomaly],
        patterns: Dict[str, UsagePattern]
    ) -> Dict[str, Any]:
        """Generate report summary"""
        total_tools = len(insights)
        
        # Health distribution
        health_counts = Counter(
            insight.overall_health for insight in insights.values()
        )
        
        # Critical issues
        critical_issues = [
            a for a in anomalies
            if a.severity in ["critical", "high"]
        ]
        
        # Trending metrics
        significant_trends = []
        for metric, trend_list in trends.items():
            for trend in trend_list:
                if trend.is_significant:
                    significant_trends.append({
                        "metric": metric,
                        "direction": trend.direction.value,
                        "change": trend.change_percentage
                    })
                    
        return {
            "total_tools_analyzed": total_tools,
            "health_distribution": dict(health_counts),
            "critical_issues_count": len(critical_issues),
            "anomalies_detected": len(anomalies),
            "significant_trends": significant_trends[:5],
            "tools_needing_attention": [
                name for name, insight in insights.items()
                if insight.overall_health in ["poor", "fair"]
            ]
        }


# Export main components
__all__ = [
    'TrendDirection',
    'AnomalyType',
    'Trend',
    'Anomaly',
    'ToolInsight',
    'UsagePattern',
    'ToolAnalytics'
]