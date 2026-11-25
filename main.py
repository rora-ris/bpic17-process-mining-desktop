"""Main entrypoint for the BPIC17 Event Log Analysis Desktop Application."""

from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("PM4PY_SHOW_CONSOLE_MESSAGE", "0")

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from src.gui import MainWindow


def _apply_light_palette(app: QApplication) -> None:
    """Forces a crisp light palette so Windows Dark Mode never bleeds into Fusion widgets."""
    pal = QPalette()
    pal.setColor(QPalette.Window, QColor("#f8fafc"))
    pal.setColor(QPalette.WindowText, QColor("#0f172a"))
    pal.setColor(QPalette.Base, QColor("#ffffff"))
    pal.setColor(QPalette.AlternateBase, QColor("#f8fafc"))
    pal.setColor(QPalette.Text, QColor("#0f172a"))
    pal.setColor(QPalette.Button, QColor("#ffffff"))
    pal.setColor(QPalette.ButtonText, QColor("#0f172a"))
    pal.setColor(QPalette.Highlight, QColor("#dbeafe"))
    pal.setColor(QPalette.HighlightedText, QColor("#1e3a8a"))
    app.setPalette(pal)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aplikasi Desktop Analisis Event Log BPIC17 (Latihan Bab 11 FBPM — Python & PM4Py)"
    )
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        default=None,
        help="Path opsional ke berkas XES (.xes / .xes.gz) untuk langsung dimuat saat aplikasi dibuka.",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Muat log sintetis pengujian edge cases (10 case) saat aplikasi dibuka.",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _apply_light_palette(app)
    app.setApplicationName("ProcessMine Studio — Loan Process Analytics")
    window = MainWindow()
    window.show()

    if args.synthetic:
        window.on_load_synthetic_log()
    elif args.file and os.path.exists(args.file):
        window.start_analysis(args.file)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
