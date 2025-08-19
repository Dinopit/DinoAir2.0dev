#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QTimer
try:
    # Import QApplication for instance checks; optional in headless usage
    from PySide6.QtWidgets import QApplication  # type: ignore
except Exception:  # pragma: no cover
    QApplication = None  # type: ignore

from src.utils.watchdog_compat import create_watchdog_adapter
from src.gui.components.metrics_widget import MetricsWidget


class UpdateCounter:
    def __init__(self) -> None:
        self.count = 0

    def inc(self, *_):
        self.count += 1


def main() -> int:
    print("== Watchdog live metrics update check ==")
    # Reuse an existing Qt application if present; otherwise create a minimal core app
    app = QCoreApplication.instance()
    if app is None:
        try:
            # Prefer core app to avoid GUI requirements
            app = QCoreApplication(sys.argv)
        except RuntimeError:
            # If a QApplication already exists, fallback to its instance
            app = QCoreApplication.instance()

    counter = UpdateCounter()
    widget = MetricsWidget()
    widget.metrics_updated.connect(lambda *_: counter.inc())

    adapter = create_watchdog_adapter(
        use_qt=True,
        alert_callback=lambda *_: None,
        metrics_callback=lambda m: widget.update_metrics(m),
        # Use integer seconds to match Qt watchdog sleep implementation
        check_interval_seconds=1,
    )
    adapter.start_monitoring()

    def finish():
        adapter.stop_monitoring()
        print(f"updates={counter.count}")
        if counter.count >= 2:
            print("LIVE_OK")
            QCoreApplication.quit()
        else:
            print("LIVE_FAIL")
            QCoreApplication.quit()

    QTimer.singleShot(3000, finish)
    # type: ignore[attr-defined]
    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
