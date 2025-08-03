"""Test script for demonstrating Watchdog metrics database integration.

This script demonstrates:
- Storing metrics to database
- Retrieving historical data
- Generating usage reports
- Data cleanup functionality
- Metrics analysis utilities
"""

import sys
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.initialize_db import DatabaseManager
from src.models.watchdog_metrics import (
    WatchdogMetric, WatchdogMetricsManager
)
from src.utils.Watchdog import SystemMetrics
from src.utils.logger import Logger

# Initialize logger
logger = Logger()


def generate_mock_metrics(base_time: datetime) -> SystemMetrics:
    """Generate realistic mock metrics for testing."""
    # Simulate varying resource usage throughout the day
    hour = base_time.hour
    
    # Base values with time-based variations
    if 9 <= hour <= 17:  # Business hours - higher usage
        base_vram = 60
        base_cpu = 40
        base_ram = 50
    elif 18 <= hour <= 22:  # Evening - moderate usage
        base_vram = 40
        base_cpu = 30
        base_ram = 40
    else:  # Night - low usage
        base_vram = 20
        base_cpu = 15
        base_ram = 30
    
    # Add random variations
    vram_percent = max(0, min(100, base_vram + random.uniform(-10, 20)))
    cpu_percent = max(0, min(100, base_cpu + random.uniform(-15, 25)))
    ram_percent = max(0, min(100, base_ram + random.uniform(-10, 15)))
    
    # Calculate MB values
    vram_total_mb = 8192  # 8GB GPU
    vram_used_mb = (vram_percent / 100) * vram_total_mb
    
    ram_total_mb = 16384  # 16GB RAM
    ram_used_mb = (ram_percent / 100) * ram_total_mb
    
    # Process counts
    total_processes = random.randint(150, 250)
    dinoair_processes = random.randint(1, 5)
    
    # Simulate occasional spikes
    if random.random() < 0.1:  # 10% chance of spike
        vram_percent = min(100, vram_percent * 1.5)
        vram_used_mb = (vram_percent / 100) * vram_total_mb
        dinoair_processes = random.randint(6, 10)
    
    return SystemMetrics(
        vram_used_mb=vram_used_mb,
        vram_total_mb=vram_total_mb,
        vram_percent=vram_percent,
        cpu_percent=cpu_percent,
        ram_used_mb=ram_used_mb,
        ram_percent=ram_percent,
        process_count=total_processes,
        dinoair_processes=dinoair_processes,
        uptime_seconds=3600  # 1 hour uptime
    )


def populate_historical_data(
    metrics_manager: WatchdogMetricsManager,
    days: int = 7
) -> int:
    """Populate database with historical test data."""
    print(f"\n📊 Generating {days} days of historical metrics...")
    
    count = 0
    now = datetime.now()
    
    # Generate data points every 30 seconds for the specified days
    for day in range(days):
        for hour in range(24):
            for minute in range(0, 60, 5):  # Every 5 minutes
                timestamp = now - timedelta(
                    days=day, hours=hour, minutes=minute
                )
                
                # Generate and store metric
                system_metrics = generate_mock_metrics(timestamp)
                metric = WatchdogMetric.from_system_metrics(system_metrics)
                
                # Override timestamp to simulate historical data
                metric.timestamp = timestamp.isoformat()
                
                metrics_manager.buffer_metric(metric)
                count += 1
                
                # Show progress
                if count % 100 == 0:
                    print(f"  Generated {count} metrics...")
    
    # Flush remaining buffered metrics
    metrics_manager.flush_buffer()
    print(f"✅ Generated {count} historical metrics")
    return count


def test_basic_operations(metrics_manager: WatchdogMetricsManager):
    """Test basic CRUD operations."""
    print("\n🧪 Testing Basic Operations")
    print("-" * 50)
    
    # Test single insert
    print("1. Testing single metric insert...")
    test_metric = WatchdogMetric.from_system_metrics(
        generate_mock_metrics(datetime.now())
    )
    metrics_manager.insert_metric(test_metric)
    print("✅ Single insert successful")
    
    # Test batch insert
    print("\n2. Testing batch insert...")
    batch_metrics = [
        WatchdogMetric.from_system_metrics(
            generate_mock_metrics(datetime.now())
        )
        for _ in range(5)
    ]
    metrics_manager.insert_metrics_batch(batch_metrics)
    print("✅ Batch insert successful")
    
    # Test retrieval
    print("\n3. Testing metric retrieval...")
    latest = metrics_manager.get_latest_metrics(5)
    print(f"✅ Retrieved {len(latest)} latest metrics")
    
    if latest:
        metric = latest[0]
        print(f"   Latest metric: VRAM {metric.vram_percent:.1f}%, "
              f"CPU {metric.cpu_percent:.1f}%, "
              f"Processes {metric.dinoair_processes}")


def test_time_range_queries(metrics_manager: WatchdogMetricsManager):
    """Test time-based queries."""
    print("\n📅 Testing Time Range Queries")
    print("-" * 50)
    
    # Last 24 hours
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    metrics = metrics_manager.get_metrics_by_time_range(start_time, end_time)
    print(f"Last 24 hours: {len(metrics)} metrics")
    
    # Last hour
    start_time = end_time - timedelta(hours=1)
    metrics = metrics_manager.get_metrics_by_time_range(start_time, end_time)
    print(f"Last hour: {len(metrics)} metrics")
    
    # Specific date range with limit
    start_time = end_time - timedelta(days=3)
    metrics = metrics_manager.get_metrics_by_time_range(
        start_time, end_time, limit=50
    )
    print(f"Last 3 days (limited to 50): {len(metrics)} metrics")


def test_summary_statistics(metrics_manager: WatchdogMetricsManager):
    """Test summary statistics calculation."""
    print("\n📈 Testing Summary Statistics")
    print("-" * 50)
    
    # Last 24 hours summary
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    summary = metrics_manager.get_metrics_summary(start_time, end_time)
    
    if summary:
        print("Last 24 Hours Summary:")
        print(f"  VRAM: avg={summary['vram']['avg']:.1f}%, "
              f"max={summary['vram']['max']:.1f}%, "
              f"min={summary['vram']['min']:.1f}%")
        print(f"  CPU:  avg={summary['cpu']['avg']:.1f}%, "
              f"max={summary['cpu']['max']:.1f}%, "
              f"min={summary['cpu']['min']:.1f}%")
        print(f"  RAM:  avg={summary['ram']['avg']:.1f}%, "
              f"max={summary['ram']['max']:.1f}%, "
              f"min={summary['ram']['min']:.1f}%")
        print(f"  DinoAir Processes: avg={summary['processes']['avg']:.1f}, "
              f"max={summary['processes']['max']}")
        print(f"  Total samples: {summary['sample_count']}")


def test_anomaly_detection(metrics_manager: WatchdogMetricsManager):
    """Test anomaly detection functionality."""
    print("\n🚨 Testing Anomaly Detection")
    print("-" * 50)
    
    # Insert some anomalous metrics
    print("Inserting anomalous metrics...")
    for _ in range(3):
        anomaly = WatchdogMetric.from_system_metrics(
            SystemMetrics(
                vram_used_mb=7000,
                vram_total_mb=8192,
                vram_percent=85.4,  # High VRAM usage
                cpu_percent=95.0,   # High CPU
                ram_used_mb=15000,
                ram_percent=91.5,   # High RAM
                process_count=300,
                dinoair_processes=8,  # Too many processes
                uptime_seconds=3600
            )
        )
        metrics_manager.insert_metric(anomaly)
        time.sleep(0.1)
    
    # Detect anomalies
    anomalies = metrics_manager.detect_anomalies(
        threshold_factor=1.5, window_hours=24
    )
    
    print(f"✅ Detected {len(anomalies)} anomalies")
    for i, anomaly in enumerate(anomalies[:3], 1):
        print(f"   Anomaly {i}: VRAM {anomaly.vram_percent:.1f}%, "
              f"CPU {anomaly.cpu_percent:.1f}%, "
              f"Processes {anomaly.dinoair_processes}")


def test_hourly_trends(metrics_manager: WatchdogMetricsManager):
    """Test hourly trend analysis."""
    print("\n📊 Testing Hourly Trends")
    print("-" * 50)
    
    hourly_data = metrics_manager.get_hourly_averages(hours=24)
    
    print("Last 24 Hours - Hourly Averages:")
    print("Hour            | VRAM % | CPU % | RAM % | Processes")
    print("-" * 55)
    
    for data in hourly_data[:10]:  # Show first 10 hours
        hour = data['hour'][-8:-3]  # Extract HH:MM
        print(f"{hour:<15} | {data['avg_vram']:5.1f} | "
              f"{data['avg_cpu']:5.1f} | {data['avg_ram']:5.1f} | "
              f"{data['avg_processes']:9.1f}")


def test_data_export(metrics_manager: WatchdogMetricsManager):
    """Test data export functionality."""
    print("\n💾 Testing Data Export")
    print("-" * 50)
    
    # Export last hour as CSV
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    csv_data = metrics_manager.export_to_csv(start_time, end_time)
    csv_lines = csv_data.strip().split('\n')
    print(f"CSV Export: {len(csv_lines)} lines (including header)")
    print("First few lines:")
    for line in csv_lines[:3]:
        print(f"  {line[:80]}...")
    
    # Export as JSON
    json_data = metrics_manager.export_to_json(start_time, end_time)
    print(f"\nJSON Export: {len(json_data)} characters")
    print(f"Preview: {json_data[:150]}...")


def test_cleanup(db_manager: DatabaseManager, retention_days: int = 5):
    """Test metrics cleanup functionality."""
    print("\n🧹 Testing Data Cleanup")
    print("-" * 50)
    
    # Get metrics manager
    metrics_manager = db_manager.get_watchdog_metrics_manager()
    
    # Count metrics before cleanup
    all_metrics = metrics_manager.get_metrics_by_time_range()
    print(f"Metrics before cleanup: {len(all_metrics)}")
    
    # Perform cleanup
    print(f"Cleaning metrics older than {retention_days} days...")
    deleted = metrics_manager.cleanup_old_metrics(retention_days)
    
    print(f"✅ Deleted {deleted} old metrics")
    
    # Count metrics after cleanup
    all_metrics = metrics_manager.get_metrics_by_time_range()
    print(f"Metrics after cleanup: {len(all_metrics)}")


def main():
    """Main test execution."""
    print("🐕 DinoAir Watchdog Metrics Test Suite")
    print("=" * 60)
    
    # Initialize database manager
    print("\n🔧 Initializing Database...")
    db_manager = DatabaseManager(user_name="test_user")
    db_manager.initialize_all_databases()
    
    # Get metrics manager
    metrics_manager = db_manager.get_watchdog_metrics_manager()
    
    # Run tests
    try:
        # Basic operations
        test_basic_operations(metrics_manager)
        
        # Populate historical data for remaining tests
        populate_historical_data(metrics_manager, days=7)
        
        # Time range queries
        test_time_range_queries(metrics_manager)
        
        # Summary statistics
        test_summary_statistics(metrics_manager)
        
        # Anomaly detection
        test_anomaly_detection(metrics_manager)
        
        # Hourly trends
        test_hourly_trends(metrics_manager)
        
        # Data export
        test_data_export(metrics_manager)
        
        # Cleanup test
        test_cleanup(db_manager, retention_days=5)
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)