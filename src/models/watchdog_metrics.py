"""Watchdog Metrics Model for storing system resource usage history.

This module provides database models and operations for persisting
SystemMetrics data from the Watchdog monitoring system.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
import csv
import io

# Import SystemMetrics from Watchdog
from ..utils.Watchdog import SystemMetrics


@dataclass
class WatchdogMetric:
    """Individual watchdog metric record with timestamp."""
    id: str
    timestamp: str  # ISO format datetime
    vram_used_mb: float
    vram_total_mb: float
    vram_percent: float
    cpu_percent: float
    ram_used_mb: float
    ram_percent: float
    process_count: int
    dinoair_processes: int
    uptime_seconds: int
    
    @classmethod
    def from_system_metrics(cls, metrics: SystemMetrics) -> 'WatchdogMetric':
        """Create WatchdogMetric from SystemMetrics snapshot."""
        return cls(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            vram_used_mb=metrics.vram_used_mb,
            vram_total_mb=metrics.vram_total_mb,
            vram_percent=metrics.vram_percent,
            cpu_percent=metrics.cpu_percent,
            ram_used_mb=metrics.ram_used_mb,
            ram_percent=metrics.ram_percent,
            process_count=metrics.process_count,
            dinoair_processes=metrics.dinoair_processes,
            uptime_seconds=metrics.uptime_seconds
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchdogMetric':
        """Create from dictionary."""
        return cls(**data)


class MetricsBuffer:
    """Buffer for batch inserting metrics to improve performance."""
    
    def __init__(self, max_size: int = 10):
        self.buffer: List[WatchdogMetric] = []
        self.max_size = max_size
    
    def add(self, metric: WatchdogMetric) -> bool:
        """Add metric to buffer. Returns True if buffer is full."""
        self.buffer.append(metric)
        return len(self.buffer) >= self.max_size
    
    def flush(self) -> List[WatchdogMetric]:
        """Get all metrics and clear buffer."""
        metrics = self.buffer.copy()
        self.buffer.clear()
        return metrics
    
    def __len__(self) -> int:
        return len(self.buffer)


class WatchdogMetricsManager:
    """Manages watchdog metrics database operations."""
    
    def __init__(self, db_connection: sqlite3.Connection):
        self.conn = db_connection
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self._buffer = MetricsBuffer()
    
    def insert_metric(self, metric: WatchdogMetric) -> None:
        """Insert a single metric into the database."""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO watchdog_metrics (
                id, timestamp, vram_used_mb, vram_total_mb, vram_percent,
                cpu_percent, ram_used_mb, ram_percent, process_count,
                dinoair_processes, uptime_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metric.id, metric.timestamp, metric.vram_used_mb,
            metric.vram_total_mb, metric.vram_percent, metric.cpu_percent,
            metric.ram_used_mb, metric.ram_percent, metric.process_count,
            metric.dinoair_processes, metric.uptime_seconds
        ))
        self.conn.commit()
    
    def insert_metrics_batch(self, metrics: List[WatchdogMetric]) -> None:
        """Insert multiple metrics efficiently in a single transaction."""
        if not metrics:
            return
            
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO watchdog_metrics (
                id, timestamp, vram_used_mb, vram_total_mb, vram_percent,
                cpu_percent, ram_used_mb, ram_percent, process_count,
                dinoair_processes, uptime_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            (m.id, m.timestamp, m.vram_used_mb, m.vram_total_mb,
             m.vram_percent, m.cpu_percent, m.ram_used_mb, m.ram_percent,
             m.process_count, m.dinoair_processes, m.uptime_seconds)
            for m in metrics
        ])
        self.conn.commit()
    
    def buffer_metric(self, metric: WatchdogMetric) -> None:
        """Add metric to buffer. Auto-flushes when buffer is full."""
        if self._buffer.add(metric):
            self.flush_buffer()
    
    def flush_buffer(self) -> None:
        """Flush any buffered metrics to database."""
        metrics = self._buffer.flush()
        if metrics:
            self.insert_metrics_batch(metrics)
    
    def get_metrics_by_time_range(
        self, 
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[WatchdogMetric]:
        """Retrieve metrics within a time range."""
        query = "SELECT * FROM watchdog_metrics WHERE 1=1"
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append(WatchdogMetric(
                id=row['id'],
                timestamp=row['timestamp'],
                vram_used_mb=row['vram_used_mb'],
                vram_total_mb=row['vram_total_mb'],
                vram_percent=row['vram_percent'],
                cpu_percent=row['cpu_percent'],
                ram_used_mb=row['ram_used_mb'],
                ram_percent=row['ram_percent'],
                process_count=row['process_count'],
                dinoair_processes=row['dinoair_processes'],
                uptime_seconds=row['uptime_seconds']
            ))
        
        return metrics
    
    def get_latest_metrics(self, count: int = 10) -> List[WatchdogMetric]:
        """Get the most recent N metrics."""
        return self.get_metrics_by_time_range(limit=count)
    
    def get_metrics_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Dict[str, float]]:
        """Calculate summary statistics for metrics in time range."""
        query = '''
            SELECT 
                AVG(vram_percent) as avg_vram,
                MAX(vram_percent) as max_vram,
                MIN(vram_percent) as min_vram,
                AVG(cpu_percent) as avg_cpu,
                MAX(cpu_percent) as max_cpu,
                MIN(cpu_percent) as min_cpu,
                AVG(ram_percent) as avg_ram,
                MAX(ram_percent) as max_ram,
                MIN(ram_percent) as min_ram,
                AVG(dinoair_processes) as avg_processes,
                MAX(dinoair_processes) as max_processes,
                COUNT(*) as sample_count
            FROM watchdog_metrics WHERE 1=1
        '''
        params = []
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if not row or row['sample_count'] == 0:
            return {}
        
        return {
            'vram': {
                'avg': row['avg_vram'] or 0,
                'max': row['max_vram'] or 0,
                'min': row['min_vram'] or 0
            },
            'cpu': {
                'avg': row['avg_cpu'] or 0,
                'max': row['max_cpu'] or 0,
                'min': row['min_cpu'] or 0
            },
            'ram': {
                'avg': row['avg_ram'] or 0,
                'max': row['max_ram'] or 0,
                'min': row['min_ram'] or 0
            },
            'processes': {
                'avg': row['avg_processes'] or 0,
                'max': row['max_processes'] or 0
            },
            'sample_count': row['sample_count']
        }
    
    def detect_anomalies(
        self, 
        threshold_factor: float = 2.0,
        window_hours: int = 24
    ) -> List[WatchdogMetric]:
        """Detect metrics that exceed normal patterns."""
        # Calculate baseline from past window
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=window_hours)
        
        summary = self.get_metrics_summary(start_time, end_time)
        if not summary:
            return []
        
        # Get recent metrics to check
        recent_metrics = self.get_latest_metrics(20)
        anomalies = []
        
        for metric in recent_metrics:
            # Check if any metric exceeds threshold factor times average
            # Check if any metric exceeds threshold factor times average
            vram_anomaly = (
                metric.vram_percent > summary['vram']['avg'] * threshold_factor
            )
            cpu_anomaly = (
                metric.cpu_percent > summary['cpu']['avg'] * threshold_factor
            )
            ram_anomaly = (
                metric.ram_percent > summary['ram']['avg'] * threshold_factor
            )
            proc_anomaly = (
                metric.dinoair_processes >
                summary['processes']['avg'] * threshold_factor
            )
            
            if vram_anomaly or cpu_anomaly or ram_anomaly or proc_anomaly:
                anomalies.append(metric)
        
        return anomalies
    
    def cleanup_old_metrics(self, retention_days: int = 7) -> int:
        """Remove metrics older than retention period."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cursor = self.conn.cursor()
        
        cursor.execute(
            "DELETE FROM watchdog_metrics WHERE timestamp < ?",
            (cutoff_date.isoformat(),)
        )
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        # Vacuum to reclaim space
        cursor.execute("VACUUM")
        
        return deleted_count
    
    def export_to_csv(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """Export metrics to CSV format."""
        metrics = self.get_metrics_by_time_range(start_time, end_time)
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                'timestamp', 'vram_used_mb', 'vram_total_mb', 'vram_percent',
                'cpu_percent', 'ram_used_mb', 'ram_percent', 'process_count',
                'dinoair_processes', 'uptime_seconds'
            ]
        )
        
        writer.writeheader()
        for metric in metrics:
            data = metric.to_dict()
            del data['id']  # Remove ID from export
            writer.writerow(data)
        
        return output.getvalue()
    
    def export_to_json(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> str:
        """Export metrics to JSON format."""
        metrics = self.get_metrics_by_time_range(start_time, end_time)
        
        data = {
            'export_time': datetime.now().isoformat(),
            'metrics_count': len(metrics),
            'metrics': [m.to_dict() for m in metrics]
        }
        
        return json.dumps(data, indent=2)
    
    def get_hourly_averages(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get hourly average metrics for trend analysis."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        query = '''
            SELECT 
                strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                AVG(vram_percent) as avg_vram,
                AVG(cpu_percent) as avg_cpu,
                AVG(ram_percent) as avg_ram,
                AVG(dinoair_processes) as avg_processes,
                COUNT(*) as sample_count
            FROM watchdog_metrics
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY hour
            ORDER BY hour DESC
        '''
        
        cursor = self.conn.cursor()
        cursor.execute(query, (start_time.isoformat(), end_time.isoformat()))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'hour': row['hour'],
                'avg_vram': row['avg_vram'] or 0,
                'avg_cpu': row['avg_cpu'] or 0,
                'avg_ram': row['avg_ram'] or 0,
                'avg_processes': row['avg_processes'] or 0,
                'sample_count': row['sample_count']
            })
        
        return results