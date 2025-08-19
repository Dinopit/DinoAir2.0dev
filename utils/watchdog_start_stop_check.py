#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.watchdog_compat import create_watchdog_adapter
from src.utils.Watchdog import AlertLevel, SystemMetrics


def alert_cb(level: AlertLevel, message: str) -> None:
    print(f"[ALERT:{level.name}] {message}")


def metrics_cb(metrics: SystemMetrics) -> None:
    print(
        f"[METRICS] cpu={metrics.cpu_percent:.1f}% ram={metrics.ram_percent:.1f}% vram={metrics.vram_percent:.1f}%"
    )


def non_daemon_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if not t.daemon]


def main() -> int:
    print("== Watchdog start/stop lifecycle check ==")
    base_threads = non_daemon_threads()
    print(f"Base non-daemon threads: {[t.name for t in base_threads]}")

    adapter = create_watchdog_adapter(
        use_qt=True,
        alert_callback=alert_cb,
        metrics_callback=metrics_cb,
        vram_threshold_percent=95.0,
        max_dinoair_processes=8,
        check_interval_seconds=1,
        self_terminate_on_critical=False,
    )

    print("-- Cycle 1: start -> wait -> stop")
    adapter.start_monitoring()
    time.sleep(2.5)
    adapter.stop_monitoring()

    time.sleep(0.5)

    print("-- Cycle 2: restart -> wait -> stop")
    adapter.start_monitoring()
    time.sleep(2.0)
    adapter.stop_monitoring()

    time.sleep(0.75)

    lingering = [t for t in non_daemon_threads() if t.name != "MainThread"]
    if lingering:
        print("!! Lingering non-daemon threads detected:", [t.name for t in lingering])
        return 1

    print("CLEAN_EXIT_OK (no lingering non-daemon threads)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
