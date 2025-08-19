#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify that the metrics signals live-update the bottom stats widget.

- Creates a Qt application and a `MetricsWidget` (not shown)
- Starts the Qt-based watchdog via the compatibility adapter
- Connects `metrics_ready` to `MetricsWidget.update_metrics`
- Counts updates via `metrics_updated` signal for a few seconds
- Stops watchdog, quits Qt, and exits 0 if we received updates

Exit codes:
  0 -> Received >= 2 metrics updates (live updates working)
  1 -> No (or <2) updates received
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.gui.components.metrics_widget import MetricsWidget
from src.utils.watchdog_compat import create_watchdog_adapter


def main() -> int:
    app = QApplication(sys.argv)

    widget = MetricsWidget()
    updates = {"count": 0}

    def on_metrics_updated(_):
        updates["count"] += 1
        # print(f"metrics_updated count={updates['count']}")

    widget.metrics_updated.connect(on_metrics_updated)

    adapter = create_watchdog_adapter(
        use_qt=True,
        alert_callback=None,
        metrics_callback=None,
        check_interval_seconds=1,
        max_dinoair_processes=8,
        vram_threshold_percent=95.0,
        self_terminate_on_critical=False,
    )

    # Start monitoring first so controller and signals are created
    adapter.start_monitoring()

    # Wire controller signal to the widget slot after start
    if adapter.controller and adapter.controller.signals:
        adapter.controller.signals.metrics_ready.connect(widget.update_metrics)
    else:
        print("ERROR: Adapter controller/signals not available after start")
        return 1

    # Stop after ~3.5 seconds
    def shutdown():
        try:
            adapter.stop_monitoring()
        finally:
            app.quit()

    QTimer.singleShot(3500, shutdown)

    exit_code = app.exec()
    # Qt exit code should be 0; evaluate updates
    if updates["count"] >= 2:
        print(f"LIVE_OK updates={updates['count']}")
        return 0
    else:
        print(f"LIVE_FAIL updates={updates['count']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
