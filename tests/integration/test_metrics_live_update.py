#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test: verifies that watchdog metrics are emitted and update the
bottom metrics widget in real-time.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import os

# Ensure project root in path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.gui.components.metrics_widget import MetricsWidget
from src.utils.watchdog_compat import create_watchdog_adapter


def test_metrics_live_updates():
    if os.getenv("RUN_QT_WATCHDOG_TESTS") != "1":
        pytest.skip("Set RUN_QT_WATCHDOG_TESTS=1 to run this Qt watchdog live update test")
    app = QApplication.instance() or QApplication(sys.argv)

    widget = MetricsWidget()
    updates = {"count": 0}

    def on_metrics_updated(_):
        updates["count"] += 1

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

    adapter.start_monitoring()

    # Connect after start to ensure controller/signals are available
    assert adapter.controller is not None, "Controller not initialized"
    assert adapter.controller.signals is not None, "Signals not initialized"

    adapter.controller.signals.metrics_ready.connect(widget.update_metrics)
    # Also count degraded metrics updates, adapt signature (metrics, reason)
    adapter.controller.signals.metrics_degraded.connect(
        lambda metrics, _reason: widget.update_metrics(metrics)
    )

    # Quit after ~5 seconds to allow multiple update cycles
    QTimer.singleShot(5000, app.quit)

    # Run the Qt event loop briefly to receive updates
    app.exec()

    # Stop watchdog and assert updates occurred
    adapter.stop_monitoring()

    assert updates["count"] >= 2, (
        f"Expected at least 2 metrics updates, got {updates['count']}"
    )
