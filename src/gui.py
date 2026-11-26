"""PySide6 Desktop GUI for BPIC17 Event Log Analysis (FBPM Chapter 11 Exercises).

Redesigned according to the unified design specification (Dark Theme reference, 4 tabs,
single visual focus per screen, giant answer numbers, and Lampiran A checklist drawer).
"""

from __future__ import annotations

import os
import re
import threading
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPoint,
    QRect,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTabWidget,
    QTableView,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .analyzer import (
    Exercise117Result,
    Exercise1115Result,
    Exercise1118Result,
    Exercise1122Result,
    OverviewResult,
    analyze_exercise_11_7,
    analyze_exercise_11_15,
    analyze_exercise_11_18,
    analyze_exercise_11_22,
    analyze_overview,
)
from .core import (
    EventLogContext,
    ValidationReport,
    get_environment_info,
    is_valid_resource,
    load_and_validate_xes,
)
from .exporter import (
    build_summary_dataframe,
    export_all_to_directory,
    generate_html_report,
)
from .synthetic import generate_synthetic_xes_file

# ======================================================================
# DESIGN TOKENS (LIGHT MODE SPECIFICATION)
# ======================================================================
NAVY = "#0B1F5C"
YELLOW = "#FFC700"
BG_CANVAS = "#F5F7FB"
BG_CARD = "#FFFFFF"
BG_SURFACE_MUTED = "#F8FAFC"
BORDER = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"
GREEN = "#16A34A"
GREEN_BG = "#DCFCE7"
GREEN_BORDER = "#86EFAC"
RED = "#DC2626"
RED_BG = "#FEE2E2"
RED_BORDER = "#FCA5A5"
AMBER_BG = "#FEF3C7"
AMBER_TEXT = "#92400E"
AMBER_BORDER = "#FCD34D"
SELECTION_BG = "#EEF2FF"
SELECTION_TEXT = "#1E3A8A"
BLUE_LINK = "#2563EB"
BLUE_BG = "#EFF6FF"
BLUE_BORDER = "#BFDBFE"

APP_STYLESHEET = f"""
QMainWindow {{
    background-color: {BG_CANVAS};
    color: {TEXT_PRIMARY};
}}

QWidget {{
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
    color: {TEXT_PRIMARY};
}}

/* Universal Label reset: strictly transparent with zero borders */
QLabel {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}}

/* Tab Bar */
QTabWidget::pane {{
    border: none;
    background-color: {BG_CANVAS};
}}

QTabBar {{
    background-color: {BG_CANVAS};
    qproperty-drawBase: 0;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED};
    font-size: 15px;
    font-weight: 500;
    padding: 10px 20px;
    margin-right: 8px;
    border: none;
    border-bottom: 3px solid transparent;
}}

QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    font-weight: 700;
    border-bottom: 3px solid {BLUE_LINK};
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_PRIMARY};
}}

/* Push Buttons */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 500;
    font-size: 13px;
}}

QPushButton:hover {{
    background-color: #F1F5F9;
    border-color: #94A3B8;
}}

QPushButton:pressed {{
    background-color: #E2E8F0;
}}

QPushButton:disabled {{
    color: #94A3B8;
    border-color: #E2E8F0;
    background-color: #F8FAFC;
}}

/* Form Controls */
QLineEdit, QComboBox {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
}}

QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {BLUE_LINK};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {SELECTION_BG};
    selection-color: {SELECTION_TEXT};
    padding: 4px;
}}

/* Tables */
QTableView {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    gridline-color: transparent;
    selection-background-color: {SELECTION_BG};
    selection-color: {SELECTION_TEXT};
    outline: none;
    font-size: 13px;
}}

QTableView::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}

QTableView::item:selected {{
    background-color: {SELECTION_BG};
    color: {SELECTION_TEXT};
}}

QHeaderView::section {{
    background-color: {BG_SURFACE_MUTED};
    color: {TEXT_MUTED};
    font-size: 12px;
    font-weight: 600;
    text-align: left;
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 8px 10px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Status Bar */
QStatusBar {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 12px;
}}
"""


# ======================================================================
# HELPER FUNCTIONS
# ======================================================================
_ID_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def fmt_int(val: int) -> str:
    """Formats an integer with Indonesian dot thousand separators."""
    return f"{int(val):,}".replace(",", ".")


def fmt_num(val: float, decimals: int = 2) -> str:
    """Formats a float with Indonesian decimal comma and dot thousands."""
    formatted = f"{float(val):,.{decimals}f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


def format_case_id_middle(full_id: str, max_len: int = 40) -> str:
    """Preserves original Case ID; truncates in the middle only if longer than max_len."""
    if not full_id:
        return "—"
    s = str(full_id)
    if len(s) <= max_len:
        return s
    head = (max_len - 1) // 2
    tail = max_len - 1 - head
    return f"{s[:head]}…{s[-tail:]}"


def shorten_case_id(full_id: str) -> str:
    """Alias preserving original Case ID with middle truncation only for very long IDs."""
    return format_case_id_middle(full_id, max_len=40)


def format_short_date(ts_str: str) -> str:
    """Formats timestamp string to compact Indonesian date like '5 Jan'."""
    if not ts_str or ts_str in ("NaT", "None", "-", "—"):
        return ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(ts_str).strip())
    if m:
        month_idx = int(m.group(2)) - 1
        day = int(m.group(3))
        if 0 <= month_idx < 12:
            return f"{day} {_ID_MONTHS[month_idx]}"
    return str(ts_str)[:10]


def shorten_activity_name(act: str) -> str:
    """Shortens long activity names for clean chip display."""
    if not act:
        return "-"
    if "Assess potential fraud" in act or "Assess Potential Fraud" in act:
        return "W_Assess"
    if "Validate application" in act:
        return "W_Validate"
    if "Call after offers" in act:
        return "W_Call"
    return act


def format_timestamp_compact(ts_str: str) -> str:
    """Formats full timestamp string to compact readable format."""
    if not ts_str or ts_str in ("NaT", "None", "-"):
        return "-"
    clean = re.sub(r"\+00:00$", "", ts_str)
    parts = clean.split()
    if len(parts) == 2:
        date_part, time_part = parts
        time_part = time_part[:5]  # HH:MM
        return f"{date_part} {time_part}"
    return clean[:16]


# ======================================================================
# REUSABLE BASE WIDGETS
# ======================================================================
class KartuAngka(QFrame):
    """Reusable metric card: giant number + optional percentage, and single-line label below."""

    clicked = Signal()

    def __init__(
        self,
        code: str = "",
        value: str = "—",
        pct: str = "",
        label: str = "",
        height: int = 104,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.code = code
        self.value = value
        self.pct = pct
        self.label = label
        self.is_active = False

        self.setFixedHeight(height)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setObjectName("KartuAngka")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Center row: Giant value + percentage
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(8)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;")
        val_row.addWidget(self.lbl_val)

        self.lbl_pct = QLabel(pct)
        self.lbl_pct.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 15px; font-weight: 500;")
        self.lbl_pct.setVisible(bool(pct))
        val_row.addWidget(self.lbl_pct)
        val_row.addStretch()
        layout.addLayout(val_row)

        # Bottom row: Single-line label ("11.7 C Berhasil" or "Case")
        combined_label = f"{code} {label}".strip() if code else label
        self.lbl_desc = QLabel(combined_label)
        self.lbl_desc.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; font-weight: 500;")
        layout.addWidget(self.lbl_desc)

        self._update_style()

    def set_content(self, value: str, pct: str = "", label: Optional[str] = None, show_dot: bool = False) -> None:
        self.value = value
        self.pct = pct
        self.lbl_val.setText(value)
        self.lbl_pct.setText(pct)
        self.lbl_pct.setVisible(bool(pct))
        if label is not None:
            self.label = label
            combined_label = f"{self.code} {label}".strip() if self.code else label
            self.lbl_desc.setText(combined_label)

    def set_selected(self, selected: bool) -> None:
        self.is_active = selected
        self._update_style()

    def _update_style(self) -> None:
        if self.is_active:
            self.setStyleSheet(
                f"QFrame#KartuAngka {{ background-color: {SELECTION_BG}; "
                f"border: 1.5px solid {BLUE_LINK}; border-radius: 12px; }}"
                f"QLabel {{ background: transparent; border: none; }}"
            )
        else:
            self.setStyleSheet(
                f"QFrame#KartuAngka {{ background-color: {BG_CARD}; "
                f"border: 1px solid {BORDER}; border-radius: 12px; }}"
                f"QFrame#KartuAngka:hover {{ border: 1px solid #CBD5E1; background-color: #F8FAFC; }}"
                f"QLabel {{ background: transparent; border: none; }}"
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ChipStatus(QFrame):
    """Validation attribute chip showing status icon and attribute name."""

    def __init__(self, name: str, is_required: bool = True, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.name = name
        self.is_required = is_required

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.lbl_icon = QLabel("✓")
        self.lbl_icon.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 700; color: {GREEN};")
        layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel(name)
        self.lbl_text.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 500; color: {GREEN};")
        layout.addWidget(self.lbl_text)

        self.set_state(True)

    def set_state(self, present: bool) -> None:
        if present:
            self.lbl_icon.setText("✓")
            self.lbl_icon.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 700; color: {GREEN};")
            self.lbl_text.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 500; color: {GREEN};")
            self.setStyleSheet(
                f"background-color: {GREEN_BG}; border: 1px solid {GREEN_BORDER}; border-radius: 8px;"
            )
        else:
            if self.is_required:
                self.lbl_icon.setText("✕")
                self.lbl_icon.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 700; color: {RED};")
                self.lbl_text.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 500; color: {RED};")
                self.setStyleSheet(
                    f"background-color: {RED_BG}; border: 1px solid {RED_BORDER}; border-radius: 8px;"
                )
            else:
                self.lbl_icon.setText("—")
                self.lbl_icon.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 700; color: {TEXT_MUTED};")
                self.lbl_text.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 500; color: {TEXT_MUTED};")
                self.setStyleSheet(
                    f"background-color: {BG_SURFACE_MUTED}; border: 1px solid {BORDER}; border-radius: 8px;"
                )


class BadgeStatus(QLabel):
    """Status badge for data import status (Valid / Memuat / Gagal)."""

    def __init__(self, text: str = "Valid", status: str = "valid", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setAlignment(Qt.AlignCenter)
        self.set_status(status, text)

    def set_status(self, status: str, text: str) -> None:
        self.setText(text)
        if status == "valid":
            self.setStyleSheet(
                f"background-color: {GREEN_BG}; color: {GREEN}; "
                f"border: 1px solid {GREEN_BORDER}; border-radius: 8px; "
                f"padding: 4px 14px; font-size: 13px; font-weight: 700;"
            )
        elif status == "busy":
            self.setStyleSheet(
                f"background-color: {BLUE_BG}; color: {BLUE_LINK}; "
                f"border: 1px solid {BLUE_BORDER}; border-radius: 8px; "
                f"padding: 4px 14px; font-size: 13px; font-weight: 700;"
            )
        else:
            self.setStyleSheet(
                f"background-color: {RED_BG}; color: {RED}; "
                f"border: 1px solid {RED_BORDER}; border-radius: 8px; "
                f"padding: 4px 14px; font-size: 13px; font-weight: 700;"
            )


class BarAktivitas(QWidget):
    """Horizontal proportional activity frequency bar row (height 28px)."""

    def __init__(self, name: str, count: int, max_count: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(28)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)

        self.lbl_name = QLabel(name)
        self.lbl_name.setFixedWidth(180)
        self.lbl_name.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px;")
        self.lbl_name.setToolTip(name)
        layout.addWidget(self.lbl_name)

        # Bar canvas
        ratio = count / max(max_count, 1)
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(10)
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0, 100)
        self.pbar.setValue(int(ratio * 100))
        self.pbar.setStyleSheet(
            f"QProgressBar {{ background-color: {BORDER}; border: none; border-radius: 5px; }} "
            f"QProgressBar::chunk {{ background-color: {NAVY}; border-radius: 5px; }}"
        )
        layout.addWidget(self.pbar, stretch=1)

        self.lbl_cnt = QLabel(fmt_int(count))
        self.lbl_cnt.setFixedWidth(76)
        self.lbl_cnt.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_cnt.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.lbl_cnt)


class StripAlur(QFrame):
    """Horizontal trace evidence flow showing events and highlight chips."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("StripAlur")
        self.setStyleSheet(
            f"QFrame#StripAlur {{ background: transparent; border: none; "
            f"border-top: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; }}"
        )
        self.setFixedHeight(62)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 6, 0, 6)
        main_layout.setSpacing(12)

        self.lbl_title = QLabel("Bukti:")
        self.lbl_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-weight: 600; font-size: 14px;")
        main_layout.addWidget(self.lbl_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(48)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.flow_container = QWidget()
        self.flow_container.setStyleSheet("background: transparent;")
        self.flow_layout = QHBoxLayout(self.flow_container)
        self.flow_layout.setContentsMargins(0, 0, 0, 0)
        self.flow_layout.setSpacing(8)
        self.flow_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        scroll.setWidget(self.flow_container)
        main_layout.addWidget(scroll, stretch=1)

    def set_trace(
        self,
        case_id: str,
        events: List[Dict[str, Any]],
        highlights: List[int],
        show_resource_and_date: bool = False,
    ) -> None:
        short_id = format_case_id_middle(case_id, max_len=40) if case_id else "—"
        self.lbl_title.setText(f"Bukti {short_id}:")
        self.lbl_title.setToolTip(str(case_id) if case_id else "")

        # Clear existing chips immediately so old widgets never ghost over new ones
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        if not events:
            lbl = QLabel("Tidak ada event pada case ini.")
            lbl.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
            self.flow_layout.addWidget(lbl)
            return

        hl_set = set(highlights)
        n_ev = len(events)
        if n_ev > 18:
            keep = {0, n_ev - 1} | hl_set
            sorted_keep = sorted(i for i in keep if 0 <= i < n_ev)
            render_items: List[Tuple[str, Any]] = []
            prev = -1
            for idx in sorted_keep:
                gap = idx - prev - 1
                if gap == 1:
                    render_items.append(("event", prev + 1))
                elif gap > 1:
                    render_items.append(("gap", gap))
                render_items.append(("event", idx))
                prev = idx
        else:
            render_items = [("event", i) for i in range(n_ev)]

        for pos_idx, (kind, payload) in enumerate(render_items):
            if kind == "gap":
                chip = QFrame()
                chip_layout = QHBoxLayout(chip)
                chip_layout.setContentsMargins(10, 4, 10, 4)
                chip.setStyleSheet(
                    f"background-color: {BG_SURFACE_MUTED}; border: 1px dashed {BORDER}; border-radius: 6px;"
                )
                lbl_gap = QLabel(f"... {payload} event lain ...")
                lbl_gap.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
                chip_layout.addWidget(lbl_gap)
                self.flow_layout.addWidget(chip)
            else:
                i = int(payload)
                ev = events[i]
                act = str(ev.get("concept:name", "—"))
                lc_raw = ev.get("lifecycle:transition", "")
                lc = "" if pd.isna(lc_raw) else str(lc_raw).strip()
                res_raw = ev.get("org:resource", "")
                res = "" if pd.isna(res_raw) else str(res_raw).strip()
                dt = format_short_date(str(ev.get("time:timestamp", "")))
                is_hl = i in hl_set
                short_act = shorten_activity_name(act)

                chip = QFrame()
                chip_layout = QHBoxLayout(chip)
                chip_layout.setContentsMargins(10, 4, 10, 4)

                parts = [short_act]
                if lc:
                    parts.append(lc)
                if show_resource_and_date or is_hl:
                    if res and res.lower() not in ("nan", "none", "null"):
                        parts.append(res)
                    elif show_resource_and_date:
                        parts.append("tanpa resource")
                    if dt:
                        parts.append(dt)
                txt = ", ".join(parts)

                if is_hl:
                    chip.setStyleSheet(
                        f"background-color: {AMBER_BG}; border: 1px solid {AMBER_BORDER}; border-radius: 6px;"
                    )
                    lbl_ev = QLabel(txt)
                    lbl_ev.setStyleSheet(f"background: transparent; border: none; color: {AMBER_TEXT}; font-weight: 600; font-size: 12px;")
                else:
                    chip.setStyleSheet(
                        f"background-color: {BG_SURFACE_MUTED}; border: 1px solid {BORDER}; border-radius: 6px;"
                    )
                    lbl_ev = QLabel(txt)
                    lbl_ev.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 12px;")

                chip_layout.addWidget(lbl_ev)
                self.flow_layout.addWidget(chip)

            # Arrow connector (pengecualian tunggal StripAlur)
            if pos_idx < len(render_items) - 1:
                lbl_arrow = QLabel("→")
                lbl_arrow.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 14px; font-weight: 700;")
                self.flow_layout.addWidget(lbl_arrow)

        self.flow_layout.addStretch()


# ======================================================================
# DATA MODELS & CUSTOM GRAPHICS FOR TABLES / CHARTS
# ======================================================================
class VirtualColumnTableModel(QAbstractTableModel):
    """Zero-copy virtual Qt TableModel backed by columnar arrays/lists for 31,509+ rows."""

    def __init__(
        self,
        headers: List[str],
        columns: List[Sequence[Any]],
        formatters: Optional[List[Optional[Callable[[Any], str]]]] = None,
        tooltips_col0: Optional[Sequence[Any]] = None,
        bold_col0: bool = True,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._headers = headers
        self._columns = columns
        self._formatters = formatters or [None] * len(headers)
        self._tooltips_col0 = tooltips_col0
        self._bold_col0 = bold_col0
        self._row_count = len(columns[0]) if columns else 0

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self._row_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole and 0 <= section < len(self._headers):
                return self._headers[section]
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if not (0 <= r < self._row_count and 0 <= c < len(self._columns)):
            return None

        raw = self._columns[c][r]
        if role == Qt.DisplayRole:
            fmt = self._formatters[c]
            return fmt(raw) if fmt is not None else str(raw)
        if role == Qt.ToolTipRole:
            if c == 0 and self._tooltips_col0 is not None:
                return str(self._tooltips_col0[r])
            fmt = self._formatters[c]
            return fmt(raw) if fmt is not None else str(raw)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.FontRole and c == 0 and self._bold_col0:
            f = QFont()
            f.setBold(True)
            return f
        return None


class Simple3ColTableModel(QAbstractTableModel):
    """Generic table model supporting left-aligned headers/cells, tooltips, backgrounds, and optional subtexts."""

    def __init__(
        self,
        headers: List[str],
        rows: List[List[Any]],
        parent: Optional[QObject] = None,
        subtexts: Optional[Dict[Tuple[int, int], str]] = None,
        tooltips: Optional[Dict[Tuple[int, int], str]] = None,
        highlight_rows: Optional[set] = None,
    ):
        super().__init__(parent)
        self._headers = headers
        self._rows = rows
        self._subtexts = subtexts or {}
        self._tooltips = tooltips or {}
        self._highlight_rows = highlight_rows or set()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole and 0 <= section < len(self._headers):
                return self._headers[section]
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        r, c = index.row(), index.column()
        val = self._rows[r][c]

        if role == Qt.DisplayRole:
            return str(val)
        if role == Qt.UserRole:
            return self._subtexts.get((r, c), "")
        if role == Qt.ToolTipRole:
            return self._tooltips.get((r, c), str(val))
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.FontRole and c == 0:
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.BackgroundRole and r in self._highlight_rows:
            return QColor(AMBER_BG)
        if role == Qt.ForegroundRole:
            s_val = str(val)
            if s_val == "Ya":
                return QColor(GREEN)
            if "kosong" in s_val.lower() or "ditolak" in s_val.lower():
                return QColor("#B45309")
            if s_val == "Tidak":
                return QColor(TEXT_MUTED)
        return None


class ActivityLifecycleDelegate(QStyledItemDelegate):
    """Draws activity name on top and lifecycle as subtle smaller text below in the same cell."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        bg_val = index.data(Qt.BackgroundRole)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(SELECTION_BG))
            text_color = QColor(SELECTION_TEXT)
        elif isinstance(bg_val, QColor):
            painter.fillRect(option.rect, bg_val)
            text_color = QColor(AMBER_TEXT)
        else:
            text_color = QColor(TEXT_PRIMARY)

        act_text = str(index.data(Qt.DisplayRole) or "")
        lc_text = str(index.data(Qt.UserRole) or "")

        rect = option.rect.adjusted(10, 4, -10, -4)
        f_main = QFont(option.font)
        f_main.setPixelSize(13)
        painter.setFont(f_main)
        painter.setPen(text_color)

        if lc_text:
            top_rect = QRect(rect.left(), rect.top(), rect.width(), 18)
            bot_rect = QRect(rect.left(), rect.top() + 18, rect.width(), 16)
            painter.drawText(top_rect, Qt.AlignLeft | Qt.AlignVCenter, act_text)

            f_sub = QFont(option.font)
            f_sub.setPixelSize(12)
            painter.setFont(f_sub)
            painter.setPen(QColor(AMBER_TEXT if isinstance(bg_val, QColor) and not (option.state & QStyle.State_Selected) else TEXT_MUTED))
            painter.drawText(bot_rect, Qt.AlignLeft | Qt.AlignVCenter, lc_text)
        else:
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, act_text)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        lc_text = str(index.data(Qt.UserRole) or "")
        return QSize(200, 42 if lc_text else 30)


class HistogramDurasiWidget(QWidget):
    """Simple histogram of case durations (days) with a vertical threshold line at day 45."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self._durations: np.ndarray = np.array([], dtype=float)
        self._threshold: float = 45.0

    def set_durations(self, durations: List[float] | np.ndarray) -> None:
        arr = np.asarray(durations, dtype=float)
        arr = arr[~np.isnan(arr)]
        self._durations = arr
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 8, 8, 18, 22
        plot_w = max(w - pad_l - pad_r, 10)
        plot_h = max(h - pad_t - pad_b, 10)

        if len(self._durations) == 0:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "Belum ada data durasi")
            return

        max_val = max(float(np.max(self._durations)), 50.0)
        bins = 15
        counts, edges = np.histogram(self._durations, bins=bins, range=(0.0, max_val))
        max_cnt = max(int(np.max(counts)), 1)
        bar_w = plot_w / bins

        for i, cnt in enumerate(counts):
            bh = (cnt / max_cnt) * plot_h
            bx = pad_l + i * bar_w + 1.5
            bw = max(bar_w - 3.0, 2.0)
            by = pad_t + plot_h - bh
            mid_edge = (edges[i] + edges[i + 1]) / 2.0
            color = QColor(NAVY) if mid_edge < self._threshold else QColor("#94A3B8")
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            if cnt > 0:
                painter.drawRoundedRect(int(bx), int(by), int(bw), max(int(bh), 2), 2, 2)

        # Baseline
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawLine(pad_l, pad_t + plot_h, pad_l + plot_w, pad_t + plot_h)

        # Vertical dashed threshold line at 45 days
        tx = pad_l + (self._threshold / max_val) * plot_w
        pen_dash = QPen(QColor(RED), 1.5, Qt.DashLine)
        painter.setPen(pen_dash)
        painter.drawLine(int(tx), pad_t - 4, int(tx), pad_t + plot_h)

        f = painter.font()
        f.setPixelSize(12)
        painter.setFont(f)
        painter.setPen(QColor(RED))
        if int(tx) + 58 <= w - pad_r:
            label_x = int(tx) + 4
        else:
            label_x = max(pad_l, int(tx) - 52)
        painter.drawText(label_x, pad_t + 8, "45 hari")

        painter.setPen(QColor(TEXT_MUTED))
        painter.drawText(pad_l, h - 4, "0")
        max_lbl = f"{int(round(max_val))} hari"
        painter.drawText(w - pad_r - 54, h - 4, max_lbl)


class Corong1115Widget(QWidget):
    """Clean 3-step horizontal funnel showing All Cases -> 11.15 -> 11.18."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("Corong penyaringan pengulangan dan resource")
        title.setStyleSheet(f"background: transparent; border: none; font-size: 14px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        self._rows: List[Tuple[QLabel, QProgressBar, QLabel]] = []
        row_names = ["Seluruh case", "11.15 Fraud 2x", "11.18 Resource sama"]
        for name in row_names:
            r_layout = QHBoxLayout()
            r_layout.setSpacing(12)
            lbl_n = QLabel(name)
            lbl_n.setFixedWidth(160)
            lbl_n.setStyleSheet(f"background: transparent; border: none; font-size: 13px; color: {TEXT_PRIMARY};")
            r_layout.addWidget(lbl_n)

            pbar = QProgressBar()
            pbar.setFixedHeight(12)
            pbar.setTextVisible(False)
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.setStyleSheet(
                f"QProgressBar {{ background-color: {BORDER}; border: none; border-radius: 6px; }} "
                f"QProgressBar::chunk {{ background-color: {NAVY}; border-radius: 6px; }}"
            )
            r_layout.addWidget(pbar, stretch=1)

            lbl_v = QLabel("—")
            lbl_v.setMinimumWidth(160)
            lbl_v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_v.setStyleSheet(f"background: transparent; border: none; font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY};")
            r_layout.addWidget(lbl_v)

            layout.addLayout(r_layout)
            self._rows.append((lbl_n, pbar, lbl_v))

    def set_values(self, total: int, c15: int, c18: int, dec: int = 1) -> None:
        denom = max(total, 1)
        vals = [
            (total, 100.0),
            (c15, c15 / denom * 100.0),
            (c18, c18 / denom * 100.0),
        ]
        for (_, pbar, lbl_v), (cnt, pct) in zip(self._rows, vals):
            pbar.setValue(int(round(cnt / denom * 100.0)) if cnt == 0 or cnt / denom * 100.0 >= 1 else 1)
            if cnt == 0:
                pbar.setValue(0)
            lbl_v.setText(f"{fmt_int(cnt)} ({fmt_num(pct, dec)}%)")


# ======================================================================
# DIALOGS (INFO, ABOUT, ACTIVITIES, FAST/SLOW, EXPORT)
# ======================================================================
class AboutDialog(QDialog):
    """About dialog showing environment versions (PDF Section 7.1)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Tentang BPIC17 Analyzer")
        self.setFixedSize(480, 360)
        self.setStyleSheet(f"background-color: {BG_CARD}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("BPIC17 Event Log Analyzer")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        desc = QLabel(
            "Aplikasi Desktop Process Mining untuk menjawab Latihan Bab 11 "
            "Buku Fundamentals of Business Process Management (FBPM) menggunakan Python & PM4Py.\n\n"
            "Tugas Proyek Tahap 1 Penambangan Data."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc)

        env = get_environment_info()
        env_box = QFrame()
        env_box.setStyleSheet(f"background-color: {BG_SURFACE_MUTED}; border: 1px solid {BORDER}; border-radius: 8px; padding: 12px;")
        eb_layout = QVBoxLayout(env_box)
        eb_layout.setSpacing(6)

        for k, v in env.items():
            row = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
            lbl_v = QLabel(str(v))
            lbl_v.setStyleSheet(f"color: {TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            eb_layout.addLayout(row)
        layout.addWidget(env_box)

        layout.addStretch()
        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class ActivityListDialog(QDialog):
    """Dialog showing complete table of all activities."""

    def __init__(self, df: pd.DataFrame, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Daftar Lengkap Frekuensi Aktivitas")
        self.resize(720, 480)
        self.setStyleSheet(f"background-color: {BG_CARD}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel(f"Seluruh Aktivitas ({len(df)} Aktivitas Unik)")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        table = QTableView()
        headers = ["Aktivitas", "Jml Event", "Event Complete", "% Event", "Jml Case", "% Case"]
        rows = []
        for r in df.itertuples(index=False):
            rows.append([
                str(getattr(r, "activity", "—")),
                fmt_int(getattr(r, "event_count", 0)),
                fmt_int(getattr(r, "complete_event_count", 0)),
                f"{fmt_num(float(getattr(r, 'event_pct', 0)), 2)}%",
                fmt_int(getattr(r, "case_count", 0)),
                f"{fmt_num(float(getattr(r, 'case_pct', 0)), 2)}%",
            ])
        model = Simple3ColTableModel(headers, rows, self)
        table.setModel(model)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        layout.addWidget(table)

        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class CaseDurationDialog(QDialog):
    """Dialog showing table of cases and durations with search filter."""

    case_double_clicked = Signal(str)

    def __init__(self, df: pd.DataFrame, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Daftar Case dan Durasi")
        self.resize(760, 520)
        self.setStyleSheet(f"background-color: {BG_CARD}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        title = QLabel("Daftar Case dan Durasi")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};")
        top_row.addWidget(title)
        top_row.addStretch()

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(lambda: self._on_search(self.search.text()))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Cari Case ID...")
        self.search.setFixedWidth(240)
        self.search.textChanged.connect(lambda _: self._search_timer.start())
        top_row.addWidget(self.search)
        layout.addLayout(top_row)

        self.table = QTableView()
        self._raw_df = df
        self._populate_table(df)
        self.table.doubleClicked.connect(self._on_row_double_click)
        layout.addWidget(self.table)

        hint = QLabel("Klik ganda baris case untuk membuka detailnya di Case Explorer.")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(hint)

        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _populate_table(self, df: pd.DataFrame) -> None:
        headers = ["Case ID", "Jml Event", "Durasi (Hari)", "Durasi (Jam)", "Aktivitas Awal", "Aktivitas Akhir"]
        if df.empty:
            columns: List[Sequence[Any]] = [[] for _ in headers]
            cids: Sequence[Any] = []
        else:
            cids = df["case_id"].astype(str).tolist()
            columns = [
                cids,
                df["event_count"].to_numpy(),
                df["duration_days"].to_numpy(),
                df["duration_hours"].to_numpy(),
                df["first_activity"].astype(str).tolist(),
                df["last_activity"].astype(str).tolist(),
            ]
        formatters: List[Optional[Callable[[Any], str]]] = [
            None,
            lambda v: fmt_int(int(v)),
            lambda v: f"{fmt_num(float(v), 2)} hari",
            lambda v: f"{fmt_num(float(v), 2)} jam",
            None,
            None,
        ]
        model = VirtualColumnTableModel(
            headers,
            columns,
            formatters=formatters,
            tooltips_col0=cids,
            parent=self,
        )
        self.table.setModel(model)
        hh = self.table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for col_idx, w in enumerate((220, 80, 115, 110, 145)):
            hh.setSectionResizeMode(col_idx, QHeaderView.Interactive)
            self.table.setColumnWidth(col_idx, w)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

    def _on_search(self, q: str) -> None:
        if not q.strip():
            self._populate_table(self._raw_df)
        else:
            filtered = self._raw_df[self._raw_df["case_id"].astype(str).str.contains(q.strip(), case=False, na=False)]
            self._populate_table(filtered)

    def _on_row_double_click(self, idx: QModelIndex) -> None:
        model = self.table.model()
        if model and idx.isValid():
            cid = model.data(model.index(idx.row(), 0), Qt.DisplayRole)
            if cid:
                self.case_double_clicked.emit(str(cid))
                self.accept()


class FastSlowDialog(QDialog):
    """Dialog showing Fast Cases (< 45 hr) vs Slow Cases (>= 45 hr)."""

    def __init__(self, ov: OverviewResult, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Analisis Fast Cases vs Slow Cases (45 Hari)")
        self.setFixedSize(500, 320)
        self.setStyleSheet(f"background-color: {BG_CARD}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Fast Cases vs Slow Cases (Threshold: 45 Hari)")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        desc = QLabel(
            "Mengacu pada Bab 11 FBPM (Example 11.10), kasus dikelompokkan menjadi:\n"
            "Fast Cases: cycle time < 45 hari\n"
            "Slow Cases: cycle time >= 45 hari"
        )
        desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px; line-height: 1.4;")
        layout.addWidget(desc)

        box = QFrame()
        box.setStyleSheet(f"background-color: {BG_SURFACE_MUTED}; border: 1px solid {BORDER}; border-radius: 8px; padding: 14px;")
        blayout = QGridLayout(box)
        blayout.setSpacing(12)

        blayout.addWidget(QLabel("Fast Cases (< 45 hari):"), 0, 0)
        lbl_fast = QLabel(
            f"<b>{fmt_int(ov.fast_cases_count)} case</b> ({fmt_num(ov.fast_cases_pct, 1)}%, rata-rata {fmt_num(ov.fast_cases_mean_days, 2)} hari)"
        )
        lbl_fast.setStyleSheet(f"color: {GREEN};")
        blayout.addWidget(lbl_fast, 0, 1)

        blayout.addWidget(QLabel("Slow Cases (>= 45 hari):"), 1, 0)
        lbl_slow = QLabel(
            f"<b>{fmt_int(ov.slow_cases_count)} case</b> ({fmt_num(ov.slow_cases_pct, 1)}%, rata-rata {fmt_num(ov.slow_cases_mean_days, 2)} hari)"
        )
        lbl_slow.setStyleSheet(f"color: {AMBER_TEXT};")
        blayout.addWidget(lbl_slow, 1, 1)

        blayout.addWidget(QLabel("Total Denominator:"), 2, 0)
        blayout.addWidget(QLabel(f"{fmt_int(ov.total_cases)} case (100%)"), 2, 1)

        layout.addWidget(box)
        layout.addStretch()

        btn = QPushButton("Tutup")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignRight)


class ExportDialog(QDialog):
    """Export modal dialog with 3 choices (Summary CSV, Selected Cases CSV, HTML Report)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Ekspor Hasil Analisis")
        self.setFixedWidth(480)
        self.setStyleSheet(f"background-color: {BG_CARD}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Pilih Jenis Ekspor")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(title)

        desc = QLabel("Pilih format berkas yang ingin diekspor dari hasil analisis saat ini:")
        desc.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(desc)

        self.btn_group = QButtonGroup(self)

        self.r1 = QRadioButton("Ringkasan jawaban latihan (CSV)")
        self.r1.setChecked(True)
        self.r1.setStyleSheet(f"font-size: 14px; font-weight: 500; padding: 6px;")
        self.btn_group.addButton(self.r1, 1)
        layout.addWidget(self.r1)

        self.r2 = QRadioButton("Daftar case terpilih per soal (CSV)")
        self.r2.setStyleSheet(f"font-size: 14px; font-weight: 500; padding: 6px;")
        self.btn_group.addButton(self.r2, 2)
        layout.addWidget(self.r2)

        self.r3 = QRadioButton("Laporan lengkap & analitis (HTML)")
        self.r3.setStyleSheet(f"font-size: 14px; font-weight: 500; padding: 6px;")
        self.btn_group.addButton(self.r3, 3)
        layout.addWidget(self.r3)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        self.btn_save = QPushButton("Simpan...")
        self.btn_save.setStyleSheet(
            f"background-color: {YELLOW}; color: {NAVY}; font-weight: 700; border: none;"
        )
        self.btn_save.clicked.connect(self.accept)
        btn_row.addWidget(self.btn_save)
        layout.addLayout(btn_row)

    def get_selected_option(self) -> int:
        return self.btn_group.checkedId()


# ======================================================================
# CHECKLIST DRAWER (LAMPIRAN A)
# ======================================================================
class ChecklistDrawer(QFrame):
    """Right-side sliding drawer panel for Lampiran A demonstration checklist."""

    navigate_to_tab = Signal(int)
    progress_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(360)
        self.setObjectName("ChecklistDrawer")
        self.setStyleSheet(
            f"QFrame#ChecklistDrawer {{ background-color: {BG_CARD}; "
            f"border-left: 1px solid {BORDER}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header: Title + Close button
        header = QHBoxLayout()
        title = QLabel("Checklist demo")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY};")
        header.addWidget(title)

        header.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; color: {TEXT_MUTED}; "
            f"font-size: 16px; font-weight: 700; }} QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
        )
        btn_close.clicked.connect(self.hide)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Progress bar + ratio label
        self.lbl_progress = QLabel("0 dari 10 item selesai")
        self.lbl_progress.setStyleSheet(f"color: {GREEN}; font-size: 13px; font-weight: 600;")
        layout.addWidget(self.lbl_progress)

        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setTextVisible(False)
        self.pbar.setRange(0, 10)
        self.pbar.setValue(0)
        self.pbar.setStyleSheet(
            f"QProgressBar {{ background-color: {BORDER}; border: none; border-radius: 4px; }} "
            f"QProgressBar::chunk {{ background-color: {GREEN}; border-radius: 4px; }}"
        )
        layout.addWidget(self.pbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        # 10 checklist items (tanpa penomoran dekoratif)
        self.items_data = [
            ("Aplikasi dibuka tanpa modifikasi kode", True, 0),
            ("BPIC17 XES diimpor dan overview tampil", False, 0),
            ("11.7 A dan B terjawab", False, 1),
            ("11.7 C, D, E menampilkan filter, jumlah, durasi", False, 1),
            ("11.15 menampilkan case dengan fraud 2x complete", False, 2),
            ("11.18 menampilkan bukti resource sama", False, 2),
            ("11.22 menampilkan count, persentase, order", False, 3),
            ("Case Explorer dan ekspor CSV berfungsi", False, 4),
            ("Log sintetis edge cases dimuat", False, 0),
            ("Seluruh anggota dapat menjelaskan bagiannya", False, 0),
        ]

        self.checkboxes: List[QCheckBox] = []
        for i, (text, default_val, target_tab) in enumerate(self.items_data):
            row = QHBoxLayout()
            cb = QCheckBox(text)
            cb.setChecked(default_val)
            cb.setStyleSheet(f"QCheckBox {{ color: {TEXT_PRIMARY}; font-size: 13px; spacing: 8px; }}")
            if i < 9:
                cb.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                cb.setFocusPolicy(Qt.NoFocus)
            else:
                cb.stateChanged.connect(lambda _: self._recompute_progress())

            row.addWidget(cb, stretch=1)

            if i in (1, 2, 3, 4, 5, 6, 7):
                btn_goto = QPushButton("Buka")
                btn_goto.setFixedSize(50, 24)
                btn_goto.setStyleSheet(
                    f"background-color: transparent; border: none; color: {BLUE_LINK}; font-size: 12px; font-weight: 600;"
                )
                btn_goto.clicked.connect(lambda _, t=target_tab: self.navigate_to_tab.emit(t))
                row.addWidget(btn_goto)

            self.checkboxes.append(cb)
            c_layout.addLayout(row)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self._recompute_progress()

    def update_states(
        self,
        has_data: bool = False,
        has_analysis: bool = False,
        is_bpic17: bool = False,
        is_synthetic: bool = False,
        exported: bool = False,
    ) -> None:
        self.checkboxes[0].setChecked(True)  # Item 1 always true
        self.checkboxes[1].setChecked(has_data and (is_bpic17 or self.checkboxes[1].isChecked()))
        self.checkboxes[2].setChecked(has_analysis)
        self.checkboxes[3].setChecked(has_analysis)
        self.checkboxes[4].setChecked(has_analysis)
        self.checkboxes[5].setChecked(has_analysis)
        self.checkboxes[6].setChecked(has_analysis)
        if exported:
            self.checkboxes[7].setChecked(True)
        self.checkboxes[8].setChecked(is_synthetic or self.checkboxes[8].isChecked())
        self._recompute_progress()

    def _recompute_progress(self) -> None:
        done = sum(1 for cb in self.checkboxes if cb.isChecked())
        total = len(self.checkboxes)
        self.pbar.setValue(done)
        self.lbl_progress.setText(f"{done} dari {total} item selesai")
        self.progress_changed.emit(f"{done}/{total}")

    def get_progress_text(self) -> str:
        done = sum(1 for cb in self.checkboxes if cb.isChecked())
        return f"{done}/10"


# ======================================================================
# DATA CONTAINER BUNDLE & WORKER THREAD
# ======================================================================
@dataclass
class FullAnalysisBundle:
    """Immutable bundle containing all analysis results for FBPM Chapter 11."""

    context: EventLogContext
    report: ValidationReport
    overview: OverviewResult
    ex117: Exercise117Result
    ex1115: Exercise1115Result
    ex1118: Exercise1118Result
    ex1122: Exercise1122Result
    case_category_tags: Dict[str, str] = field(default_factory=dict)


def _compute_case_category_tags(
    ov: OverviewResult,
    r117: Exercise117Result,
    r1115: Exercise1115Result,
    r1118: Exercise1118Result,
    r1122: Exercise1122Result,
) -> Dict[str, str]:
    """Precomputes 'Lolos di' tags per case_id in O(N)."""
    c_set = set(r117.sub_c.case_df["case_id"].astype(str)) if not r117.sub_c.case_df.empty else set()
    d_set = set(r117.sub_d.case_df["case_id"].astype(str)) if not r117.sub_d.case_df.empty else set()
    e_set = set(r117.sub_e.case_df["case_id"].astype(str)) if not r117.sub_e.case_df.empty else set()
    s15_set = set(r1115.case_summary_df["case_id"].astype(str)) if not r1115.case_summary_df.empty else set()
    s18_set = set(r1118.case_resource_summary_df["case_id"].astype(str)) if not r1118.case_resource_summary_df.empty else set()
    s22_set = set(r1122.case_summary_df["case_id"].astype(str)) if not r1122.case_summary_df.empty else set()

    tags_map: Dict[str, str] = {}
    for cid in ov.case_table["case_id"].astype(str).tolist():
        t = []
        if cid in c_set:
            t.append("C")
        if cid in d_set:
            t.append("D")
        if cid in e_set:
            t.append("E")
        if cid in s15_set:
            t.append("15")
        if cid in s18_set:
            t.append("18")
        if cid in s22_set:
            t.append("22")
        if t:
            tags_map[cid] = ", ".join(t)
    return tags_map


class AnalysisWorker(QThread):
    """Background worker thread so XES import and analysis never freeze the desktop UI."""

    progress_changed = Signal(int, str)
    finished_bundle = Signal(object)
    failed_error = Signal(str)

    def __init__(self, file_path: str, existing_context: Optional[EventLogContext] = None):
        super().__init__()
        self.file_path = file_path
        self.existing_context = existing_context

    def run(self) -> None:
        try:
            if self.existing_context is None:
                self.progress_changed.emit(15, "Membaca XES...")
                ctx, report = load_and_validate_xes(
                    self.file_path,
                    progress_callback=lambda msg: self.progress_changed.emit(40, msg),
                )
                if not report.is_valid or ctx is None:
                    self.failed_error.emit(report.error_message or "Gagal memvalidasi berkas XES.")
                    return
            else:
                ctx = self.existing_context
                report = ctx.report

            self.progress_changed.emit(60, "Menghitung ringkasan...")
            ov = analyze_overview(ctx)

            self.progress_changed.emit(75, "Menghitung Exercise 11.7...")
            r117 = analyze_exercise_11_7(ctx)

            self.progress_changed.emit(85, "Menghitung Exercise 11.15...")
            r1115 = analyze_exercise_11_15(ctx)

            self.progress_changed.emit(92, "Menghitung Exercise 11.18...")
            r1118 = analyze_exercise_11_18(ctx, res_1115=r1115)

            self.progress_changed.emit(97, "Menghitung Exercise 11.22...")
            r1122 = analyze_exercise_11_22(ctx)

            tags_map = _compute_case_category_tags(ov, r117, r1115, r1118, r1122)

            bundle = FullAnalysisBundle(
                context=ctx,
                report=report,
                overview=ov,
                ex117=r117,
                ex1115=r1115,
                ex1118=r1118,
                ex1122=r1122,
                case_category_tags=tags_map,
            )
            self.progress_changed.emit(100, "Siap")
            self.finished_bundle.emit(bundle)
        except Exception as exc:
            self.failed_error.emit(f"Kesalahan saat analisis: {str(exc)}\n{traceback.format_exc()}")


# ======================================================================
# MAIN APPLICATION WINDOW
# ======================================================================
class MainWindow(QMainWindow):
    """Main Application Window for BPIC17 Analyzer (PySide6 Desktop)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BPIC17 Event Log Desktop Analyzer")
        self.resize(1280, 800)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(APP_STYLESHEET)

        self.bundle: Optional[FullAnalysisBundle] = None
        self.worker: Optional[AnalysisWorker] = None
        self.has_exported: bool = False
        self.seen_bpic17: bool = False
        self.seen_synthetic: bool = False
        self.f02_unit: str = "hari"  # "hari", "jam", "detik"
        self.f02_precision: int = 2
        self.selected_117_sub: str = "11.7 A"
        self.selected_1518_sub: str = "11.15"

        self._setup_ui()
        QTimer.singleShot(150, self._prewarm_pm4py)

    @staticmethod
    def _do_prewarm_pm4py() -> None:
        try:
            import pm4py  # noqa: F401
        except Exception:
            pass

    def _prewarm_pm4py(self) -> None:
        threading.Thread(target=self._do_prewarm_pm4py, daemon=True).start()

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(5000)
        super().closeEvent(event)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main vertical content container
        content_container = QWidget()
        c_layout = QVBoxLayout(content_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        # 1. Header (height 64px, deep navy #0B1F5C)
        self._setup_header(c_layout)

        # 2. Main Tabs (Data, Exercise 11.7, Exercise 11.15 & 11.18, Exercise 11.22, Case Explorer)
        c_layout.addWidget(self._setup_tab_bar())

        # Area isi tab (Stacked or QTabWidget content)
        self.body_stack = QTabWidget()
        self.body_stack.setObjectName("BodyStack")
        self.body_stack.tabBar().setVisible(False)  # custom tab bar above
        self.body_stack.setStyleSheet(f"QTabWidget#BodyStack {{ background-color: {BG_CANVAS}; border: none; }}")

        self.tab_data = self._create_tab_data()
        self.tab_117 = self._create_tab_117()
        self.tab_1518 = self._create_tab_1115_1118()
        self.tab_1122 = self._create_tab_1122()
        self.tab_explorer = self._create_tab_explorer()

        self.body_stack.addTab(self.tab_data, "Data")
        self.body_stack.addTab(self.tab_117, "Exercise 11.7")
        self.body_stack.addTab(self.tab_1518, "Exercise 11.15 & 11.18")
        self.body_stack.addTab(self.tab_1122, "Exercise 11.22")
        self.body_stack.addTab(self.tab_explorer, "Case Explorer")

        c_layout.addWidget(self.body_stack, stretch=1)

        root_layout.addWidget(content_container, stretch=1)

        # 3. Right Checklist Drawer (Lampiran A)
        self.drawer = ChecklistDrawer(self)
        self.drawer.navigate_to_tab.connect(self._on_navigate_from_drawer)
        self.drawer.progress_changed.connect(lambda p: self.btn_checklist_chip.setText(f"Checklist {p}"))
        self.drawer.hide()
        root_layout.addWidget(self.drawer)
        self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")

        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Siap. Silakan muat berkas XES.")

    # ------------------------------------------------------------------
    # HEADER (Height 64px, #0B1F5C)
    # ------------------------------------------------------------------
    def _setup_header(self, parent_layout: QVBoxLayout) -> None:
        header = QFrame()
        header.setObjectName("MainHeader")
        header.setFixedHeight(64)
        header.setStyleSheet(
            f"QFrame#MainHeader {{ background-color: {NAVY}; border: none; }}"
        )

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        h_layout.setSpacing(16)

        # Left: Title + Filename
        left_box = QVBoxLayout()
        left_box.setSpacing(2)
        left_box.setAlignment(Qt.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        lbl_title = QLabel("BPIC17 Analyzer")
        lbl_title.setStyleSheet("background: transparent; border: none; font-size: 18px; font-weight: 700; color: #FFFFFF;")
        title_row.addWidget(lbl_title)

        btn_about = QPushButton("ⓘ")
        btn_about.setFixedSize(22, 22)
        btn_about.setCursor(QCursor(Qt.PointingHandCursor))
        btn_about.setToolTip("Tentang Aplikasi & Informasi Lingkungan")
        btn_about.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.3); "
            "border-radius: 11px; color: #FFFFFF; font-size: 12px; font-weight: 700; padding: 0; } "
            "QPushButton:hover { background: rgba(255,255,255,0.15); }"
        )
        btn_about.clicked.connect(self._show_about_dialog)
        title_row.addWidget(btn_about)
        title_row.addStretch()
        left_box.addLayout(title_row)

        self.lbl_header_file = QLabel("Belum ada berkas dimuat")
        self.lbl_header_file.setStyleSheet("background: transparent; border: none; font-size: 12px; color: #CBD5E1;")
        left_box.addWidget(self.lbl_header_file)
        h_layout.addLayout(left_box)

        h_layout.addStretch()

        # Right: Checklist Chip, Ganti Data Dropdown, Ekspor Button
        self.btn_checklist_chip = QPushButton("Checklist 0/10")
        self.btn_checklist_chip.setFixedHeight(34)
        self.btn_checklist_chip.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_checklist_chip.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 0.08); "
            "border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; "
            "color: #FFFFFF; font-size: 13px; font-weight: 600; padding: 0 14px; } "
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); }"
        )
        self.btn_checklist_chip.clicked.connect(self._toggle_drawer)
        h_layout.addWidget(self.btn_checklist_chip)

        self.btn_ganti_data = QPushButton("Ganti data ▾")
        self.btn_ganti_data.setFixedHeight(34)
        self.btn_ganti_data.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ganti_data.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 0.12); "
            "border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 8px; "
            "color: #FFFFFF; font-size: 13px; font-weight: 600; padding: 0 14px; } "
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); }"
        )
        self.btn_ganti_data.clicked.connect(self._show_ganti_data_menu)
        h_layout.addWidget(self.btn_ganti_data)

        self.btn_ekspor = QPushButton("Ekspor")
        self.btn_ekspor.setFixedHeight(34)
        self.btn_ekspor.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_ekspor.setStyleSheet(
            f"QPushButton {{ background-color: {YELLOW}; color: {NAVY}; "
            f"border: none; border-radius: 8px; font-size: 13px; font-weight: 700; padding: 0 18px; }} "
            f"QPushButton:hover {{ background-color: #E6B300; }}"
        )
        self.btn_ekspor.clicked.connect(self.on_export_dialog)
        h_layout.addWidget(self.btn_ekspor)

        parent_layout.addWidget(header)

    def _setup_tab_bar(self) -> QWidget:
        bar_widget = QFrame()
        bar_widget.setFixedHeight(44)
        bar_widget.setStyleSheet(
            f"background-color: {BG_CANVAS}; border-bottom: 1px solid {BORDER};"
        )

        layout = QHBoxLayout(bar_widget)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self.tab_buttons: List[QPushButton] = []
        tab_names = ["Data", "Exercise 11.7", "Exercise 11.15 && 11.18", "Exercise 11.22", "Case Explorer"]

        for i, name in enumerate(tab_names):
            btn = QPushButton(name)
            btn.setFixedHeight(44)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.clicked.connect(lambda _, idx=i: self._set_active_tab(idx))
            self.tab_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        self._update_tab_button_styles(0)
        return bar_widget

    def _set_active_tab(self, idx: int) -> None:
        self.body_stack.setCurrentIndex(idx)
        self._update_tab_button_styles(idx)

    def _update_tab_button_styles(self, active_idx: int) -> None:
        for i, btn in enumerate(self.tab_buttons):
            if i == active_idx:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; border: none; "
                    f"border-bottom: 3px solid {BLUE_LINK}; color: {TEXT_PRIMARY}; "
                    f"font-size: 15px; font-weight: 700; padding: 0 16px; border-radius: 0; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background: transparent; border: none; "
                    f"border-bottom: 3px solid transparent; color: {TEXT_MUTED}; "
                    f"font-size: 15px; font-weight: 500; padding: 0 16px; border-radius: 0; }} "
                    f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
                )

    # ------------------------------------------------------------------
    # TAB 1: DATA (F01 & F02 — Bagian Dhimas)
    # ------------------------------------------------------------------
    def _create_tab_data(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Top: Status row (Badge + Progress Bar + Dimuat X dtk)
        status_card = QFrame()
        status_card.setStyleSheet(f"background-color: transparent;")
        s_layout = QHBoxLayout(status_card)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(14)

        self.badge_status = BadgeStatus("Valid", "valid")
        s_layout.addWidget(self.badge_status)

        self.pbar_load = QProgressBar()
        self.pbar_load.setFixedHeight(8)
        self.pbar_load.setTextVisible(False)
        self.pbar_load.setRange(0, 100)
        self.pbar_load.setValue(100)
        self.pbar_load.setStyleSheet(
            f"QProgressBar {{ background-color: {BORDER}; border: none; border-radius: 4px; }} "
            f"QProgressBar::chunk {{ background-color: {GREEN}; border-radius: 4px; }}"
        )
        s_layout.addWidget(self.pbar_load, stretch=1)

        self.lbl_load_time = QLabel("Belum ada data dimuat.")
        self.lbl_load_time.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; font-weight: 500;")
        s_layout.addWidget(self.lbl_load_time)
        layout.addWidget(status_card)

        # Error notification box (hidden by default)
        self.box_error = QFrame()
        self.box_error.setStyleSheet(
            f"background-color: {RED_BG}; border: 1px solid {RED_BORDER}; "
            f"border-radius: 10px; padding: 14px;"
        )
        err_l = QVBoxLayout(self.box_error)
        err_l.setSpacing(4)
        self.lbl_err_title = QLabel("Impor atau Validasi XES Gagal")
        self.lbl_err_title.setStyleSheet(f"background: transparent; border: none; color: {RED}; font-weight: 700; font-size: 14px;")
        err_l.addWidget(self.lbl_err_title)
        self.lbl_err_msg = QLabel("Pesan kesalahan akan tampil di sini.")
        self.lbl_err_msg.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px;")
        err_l.addWidget(self.lbl_err_msg)
        self.box_error.setVisible(False)
        layout.addWidget(self.box_error)

        # Center: 5 Kartu Angka Besar (termasuk Resource unik)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_cases = KartuAngka(value="—", label="Case", height=96)
        self.card_events = KartuAngka(value="—", label="Event", height=96)
        self.card_acts = KartuAngka(value="—", label="Aktivitas", height=96)
        self.card_resources = KartuAngka(value="—", label="Resource unik", height=96)
        self.card_dur = KartuAngka(value="—", label="Rata-rata durasi", height=96)

        cards_row.addWidget(self.card_cases)
        cards_row.addWidget(self.card_events)
        cards_row.addWidget(self.card_acts)
        cards_row.addWidget(self.card_resources)
        cards_row.addWidget(self.card_dur)
        layout.addLayout(cards_row)

        # Attribute validation row: Deretan ChipStatus
        chips_row = QHBoxLayout()
        chips_row.setSpacing(10)
        self.chip_case_id = ChipStatus("Case ID", is_required=True)
        self.chip_concept_name = ChipStatus("concept:name", is_required=True)
        self.chip_timestamp = ChipStatus("timestamp", is_required=True)
        self.chip_lifecycle = ChipStatus("lifecycle", is_required=False)
        self.chip_resource = ChipStatus("resource", is_required=False)

        chips_row.addWidget(self.chip_case_id)
        chips_row.addWidget(self.chip_concept_name)
        chips_row.addWidget(self.chip_timestamp)
        chips_row.addWidget(self.chip_lifecycle)
        chips_row.addWidget(self.chip_resource)
        chips_row.addStretch()
        layout.addLayout(chips_row)

        # Validation warnings banner (hidden when warnings list is empty)
        self.box_warnings = QFrame()
        self.box_warnings.setObjectName("BoxWarnings")
        self.box_warnings.setStyleSheet(
            f"QFrame#BoxWarnings {{ background-color: {AMBER_BG}; border: 1px solid {AMBER_BORDER}; "
            f"border-radius: 8px; padding: 8px 12px; }}"
        )
        warn_l = QVBoxLayout(self.box_warnings)
        warn_l.setContentsMargins(0, 0, 0, 0)
        self.lbl_warnings_msg = QLabel("")
        self.lbl_warnings_msg.setWordWrap(True)
        self.lbl_warnings_msg.setStyleSheet(f"background: transparent; border: none; color: {AMBER_TEXT}; font-size: 12px;")
        warn_l.addWidget(self.lbl_warnings_msg)
        self.box_warnings.setVisible(False)
        layout.addWidget(self.box_warnings)

        # Horizontal 1 px divider separating top summary from bottom details
        h_div = QFrame()
        h_div.setFixedHeight(1)
        h_div.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(h_div)

        # Bottom: Two borderless sections separated by 24px space and 1px vertical line
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(24)

        # Left Section: Aktivitas terbanyak (tanpa bingkai kartu)
        card_left = QWidget()
        cl_layout = QVBoxLayout(card_left)
        cl_layout.setContentsMargins(0, 8, 0, 0)
        cl_layout.setSpacing(10)

        cl_title = QLabel("Aktivitas terbanyak")
        cl_title.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};")
        cl_layout.addWidget(cl_title)

        self.box_act_bars = QVBoxLayout()
        self.box_act_bars.setSpacing(6)
        cl_layout.addLayout(self.box_act_bars)

        self.btn_see_all_acts = QPushButton("Lihat semua aktivitas")
        self.btn_see_all_acts.setStyleSheet(
            f"background: transparent; border: none; color: {BLUE_LINK}; "
            f"font-size: 13px; font-weight: 600; text-align: left; padding: 0;"
        )
        self.btn_see_all_acts.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_see_all_acts.clicked.connect(self._show_all_activities_dialog)
        cl_layout.addWidget(self.btn_see_all_acts)

        lc_title = QLabel("Distribusi lifecycle")
        lc_title.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY}; margin-top: 8px;")
        cl_layout.addWidget(lc_title)

        self.box_lc_bars = QVBoxLayout()
        self.box_lc_bars.setSpacing(5)
        cl_layout.addLayout(self.box_lc_bars)
        cl_layout.addStretch()

        bottom_row.addWidget(card_left, stretch=6)

        v_div = QFrame()
        v_div.setFixedWidth(1)
        v_div.setStyleSheet(f"background-color: {BORDER}; border: none;")
        bottom_row.addWidget(v_div)

        # Right Section: Durasi case (tanpa bingkai kartu)
        card_right = QWidget()
        cr_layout = QVBoxLayout(card_right)
        cr_layout.setContentsMargins(0, 8, 0, 0)
        cr_layout.setSpacing(10)

        cr_top = QHBoxLayout()
        cr_title = QLabel("Durasi case")
        cr_title.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};")
        cr_top.addWidget(cr_title)
        cr_top.addStretch()

        # Segmented unit toggle: [Hari] [Jam] [Detik]
        self.btn_unit_day = QPushButton("Hari")
        self.btn_unit_hour = QPushButton("Jam")
        self.btn_unit_sec = QPushButton("Detik")
        for b in (self.btn_unit_day, self.btn_unit_hour, self.btn_unit_sec):
            b.setFixedHeight(26)
            b.setCursor(QCursor(Qt.PointingHandCursor))

        self.btn_unit_day.clicked.connect(lambda: self._set_f02_unit("hari"))
        self.btn_unit_hour.clicked.connect(lambda: self._set_f02_unit("jam"))
        self.btn_unit_sec.clicked.connect(lambda: self._set_f02_unit("detik"))
        self._update_unit_buttons()

        cr_top.addWidget(self.btn_unit_day)
        cr_top.addWidget(self.btn_unit_hour)
        cr_top.addWidget(self.btn_unit_sec)
        cr_layout.addLayout(cr_top)

        # Tiga baris label-nilai terpisah untuk Min, Median, Maks + Std dev & Rentang waktu
        dur_grid = QGridLayout()
        dur_grid.setContentsMargins(0, 4, 0, 4)
        dur_grid.setHorizontalSpacing(16)
        dur_grid.setVerticalSpacing(6)

        self.lbl_dur_min = QLabel("—")
        self.lbl_dur_med = QLabel("—")
        self.lbl_dur_max = QLabel("—")
        self.lbl_std_dev = QLabel("—")
        self.lbl_time_range = QLabel("—")

        dur_rows = [
            ("Minimum", self.lbl_dur_min),
            ("Median", self.lbl_dur_med),
            ("Maksimum", self.lbl_dur_max),
            ("Simpangan baku", self.lbl_std_dev),
            ("Rentang waktu", self.lbl_time_range),
        ]
        for row_idx, (k_txt, val_lbl) in enumerate(dur_rows):
            k_lbl = QLabel(k_txt)
            k_lbl.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
            val_lbl.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
            dur_grid.addWidget(k_lbl, row_idx, 0)
            dur_grid.addWidget(val_lbl, row_idx, 1)
        dur_grid.setColumnStretch(1, 1)
        cr_layout.addLayout(dur_grid)

        # Precision selector
        prec_row = QHBoxLayout()
        prec_row.setSpacing(8)
        lbl_prec = QLabel("Ketelitian:")
        lbl_prec.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        prec_row.addWidget(lbl_prec)

        self.cmb_prec = QComboBox()
        self.cmb_prec.addItems(["2 desimal", "4 desimal"])
        self.cmb_prec.currentIndexChanged.connect(self._on_precision_changed)
        prec_row.addWidget(self.cmb_prec)
        prec_row.addStretch()
        cr_layout.addLayout(prec_row)

        # Histogram durasi case + batas 45 hari (Example 11.10 / Bagian 12 PDF)
        hist_title = QLabel("Sebaran durasi case (batas 45 hari)")
        hist_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600; margin-top: 4px;")
        cr_layout.addWidget(hist_title)

        self.hist_durasi = HistogramDurasiWidget()
        cr_layout.addWidget(self.hist_durasi)

        self.lbl_fast_slow_summary = QLabel("Fast (< 45 hari): —, Slow (>= 45 hari): —")
        self.lbl_fast_slow_summary.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
        cr_layout.addWidget(self.lbl_fast_slow_summary)

        cr_layout.addStretch()

        links_row = QHBoxLayout()
        self.btn_see_cases = QPushButton("Daftar case dan durasi")
        self.btn_see_cases.setStyleSheet(
            f"background: transparent; border: none; color: {BLUE_LINK}; "
            f"font-size: 13px; font-weight: 600; text-align: left; padding: 0;"
        )
        self.btn_see_cases.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_see_cases.clicked.connect(self._show_case_duration_dialog)
        links_row.addWidget(self.btn_see_cases)

        links_row.addStretch()

        self.btn_fast_slow = QPushButton("Rincian Fast vs Slow")
        self.btn_fast_slow.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_MUTED}; "
            f"font-size: 12px; font-weight: 500; text-align: right; padding: 0;"
        )
        self.btn_fast_slow.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_fast_slow.clicked.connect(self._show_fast_slow_dialog)
        links_row.addWidget(self.btn_fast_slow)
        cr_layout.addLayout(links_row)

        bottom_row.addWidget(card_right, stretch=4)
        layout.addLayout(bottom_row, stretch=1)

        return widget

    def _set_f02_unit(self, unit: str) -> None:
        self.f02_unit = unit
        self._update_unit_buttons()
        if self.bundle:
            self._update_f02_durations(self.bundle.overview)

    def _update_unit_buttons(self) -> None:
        for u, b in (("hari", self.btn_unit_day), ("jam", self.btn_unit_hour), ("detik", self.btn_unit_sec)):
            if self.f02_unit == u:
                b.setStyleSheet(
                    f"background-color: {NAVY}; color: #FFFFFF; font-weight: 700; "
                    f"border: 1px solid {NAVY}; border-radius: 6px; padding: 2px 10px;"
                )
            else:
                b.setStyleSheet(
                    f"background-color: {BG_SURFACE_MUTED}; color: {TEXT_MUTED}; font-weight: 500; "
                    f"border: 1px solid {BORDER}; border-radius: 6px; padding: 2px 10px;"
                )

    def _on_precision_changed(self, idx: int) -> None:
        self.f02_precision = 4 if idx == 1 else 2
        if self.bundle:
            self._refresh_all_numbers_precision()

    # ------------------------------------------------------------------
    # TAB 2: EXERCISE 11.7 (A–E)
    # ------------------------------------------------------------------
    def _create_tab_117(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 5 Answer Cards in 1 row (11.7 A - E)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.cards_117: Dict[str, KartuAngka] = {}
        defs_117 = [
            ("11.7 A", "Total case"),
            ("11.7 B", "Rata-rata durasi"),
            ("11.7 C", "Berhasil"),
            ("11.7 D", "Tidak berhasil"),
            ("11.7 E", "Dibatalkan"),
        ]
        for code, label in defs_117:
            c = KartuAngka(code=code, value="—", label=label, height=100)
            c.clicked.connect(lambda q=code: self._select_117_sub(q))
            self.cards_117[code] = c
            cards_row.addWidget(c)
        layout.addLayout(cards_row)

        # Overlap C/D & Endpoint E note
        self.lbl_117_notes = QLabel("Klik salah satu kartu di atas untuk melihat rincian dan bukti case.")
        self.lbl_117_notes.setWordWrap(True)
        self.lbl_117_notes.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(self.lbl_117_notes)

        # Selected sub-question header + rule + mean duration badge
        rule_row = QHBoxLayout()
        rule_row.setSpacing(10)
        self.lbl_117_rule = QLabel("Aturan filter 11.7 A:")
        self.lbl_117_rule.setStyleSheet(f"background: transparent; border: none; font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        rule_row.addWidget(self.lbl_117_rule)
        rule_row.addStretch()

        self.lbl_117_dur_badge = QLabel("")
        self.lbl_117_dur_badge.setStyleSheet(
            f"background-color: {BLUE_BG}; color: {BLUE_LINK}; "
            f"border: 1px solid {BLUE_BORDER}; border-radius: 6px; padding: 4px 10px; font-size: 13px; font-weight: 600;"
        )
        self.lbl_117_dur_badge.setVisible(False)
        rule_row.addWidget(self.lbl_117_dur_badge)
        layout.addLayout(rule_row)

        self.table_117 = QTableView()
        self.table_117.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table_117.horizontalHeader().setStretchLastSection(True)
        self.table_117.verticalHeader().setVisible(False)
        self.table_117.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_117.clicked.connect(lambda idx: self._on_tab_table_clicked(idx, "_raw_ids_117", self.strip_117, self.selected_117_sub))
        layout.addWidget(self.table_117, stretch=1)

        self.strip_117 = StripAlur()
        layout.addWidget(self.strip_117)

        act_row = QHBoxLayout()
        act_row.setSpacing(10)
        btn_exp = QPushButton("Buka di Case Explorer")
        btn_exp.clicked.connect(lambda: self._open_table_selection_in_explorer(self.table_117, "_raw_ids_117"))
        act_row.addWidget(btn_exp)

        btn_csv = QPushButton("Ekspor CSV soal ini")
        btn_csv.clicked.connect(lambda: self._export_table_csv(self.table_117, self.selected_117_sub))
        act_row.addWidget(btn_csv)

        btn_rerun = QPushButton("Jalankan ulang")
        btn_rerun.clicked.connect(self.on_rerun_all)
        act_row.addWidget(btn_rerun)
        act_row.addStretch()
        layout.addLayout(act_row)

        self._update_117_card_selection()
        return widget

    def _select_117_sub(self, code: str) -> None:
        self.selected_117_sub = code
        self._update_117_card_selection()
        if self.bundle:
            self._render_tab_117()

    def _update_117_card_selection(self) -> None:
        for c, card in self.cards_117.items():
            card.set_selected(c == self.selected_117_sub)

    def _render_tab_117(self) -> None:
        b = self.bundle
        if not b:
            return
        p = self.f02_precision
        ov = b.overview

        # Update 5 cards
        self.cards_117["11.7 A"].set_content(fmt_int(b.ex117.sub_a.case_count))
        self.cards_117["11.7 B"].set_content(f"{fmt_num(b.ex117.sub_b.mean_duration_days, p)} hari")
        self.cards_117["11.7 C"].set_content(
            fmt_int(b.ex117.sub_c.case_count),
            f"{fmt_num(b.ex117.sub_c.case_percentage, p)}%",
            label=f"Berhasil (rata-rata {fmt_num(b.ex117.sub_c.mean_duration_days, p)} hari)",
        )
        self.cards_117["11.7 D"].set_content(
            fmt_int(b.ex117.sub_d.case_count),
            f"{fmt_num(b.ex117.sub_d.case_percentage, p)}%",
            label=f"Tidak berhasil (rata-rata {fmt_num(b.ex117.sub_d.mean_duration_days, p)} hari)",
        )
        self.cards_117["11.7 E"].set_content(
            fmt_int(b.ex117.sub_e.case_count),
            f"{fmt_num(b.ex117.sub_e.case_percentage, p)}%",
            label=f"Dibatalkan (rata-rata {fmt_num(b.ex117.sub_e.mean_duration_days, p)} hari)",
        )

        # Overlap C & D + 11.7 E note (Section 3d)
        ov_ids = b.ex117.overlap_c_and_d_case_ids
        if b.ex117.overlap_c_and_d_count > 0:
            ex_txt = ", ".join(format_case_id_middle(x, 40) for x in ov_ids[:2])
            if len(ov_ids) > 2:
                ex_txt += ", ..."
            cd_note = f"{fmt_int(b.ex117.overlap_c_and_d_count)} case masuk C dan D ({ex_txt})"
        else:
            cd_note = "0 case masuk C dan D"

        e_note = (
            f"11.7 E: {fmt_int(b.ex117.sub_e.case_count)} dari {fmt_int(b.ex117.contains_cancelled_anywhere_count)} "
            f"case yang memuat O_Cancelled"
        )
        self.lbl_117_notes.setText(f"{cd_note}.   {e_note}.")

        # Render selected sub-question table (Virtual zero-copy model — all rows, <5ms)
        code = self.selected_117_sub
        self.lbl_117_dur_badge.setVisible(False)
        headers: List[str] = ["Case", "Durasi", "Status"]
        columns: List[Sequence[Any]] = [[], [], []]
        formatters: List[Optional[Callable[[Any], str]]] = [None, lambda v: f"{fmt_num(float(v), p)} hari", None]
        raw_ids: List[str] = []

        if code == "11.7 A":
            self.lbl_117_rule.setText("11.7 A: Hitung seluruh unique case/trace dari keseluruhan event log aktif")
            headers = ["Case", "Jml Event", "Durasi"]
            df_src = ov.case_table.sort_values(by="duration_days", ascending=False)
            raw_ids = df_src["case_id"].astype(str).tolist()
            columns = [raw_ids, df_src["event_count"].to_numpy(), df_src["duration_days"].to_numpy()]
            formatters = [None, lambda v: f"{fmt_int(int(v))} event", lambda v: f"{fmt_num(float(v), p)} hari"]
        elif code == "11.7 B":
            dur = b.ex117.sub_b.mean_duration_days
            self.lbl_117_rule.setText("11.7 B: Rata-rata cycle time seluruh case (event terakhir - event pertama)")
            self.lbl_117_dur_badge.setText(f"Rata-rata {fmt_num(dur, p)} hari ({fmt_num(b.ex117.sub_b.mean_duration_hours, p)} jam)")
            self.lbl_117_dur_badge.setVisible(True)
            headers = ["Case", "Durasi", "Event Terakhir"]
            df_src = ov.case_table
            raw_ids = df_src["case_id"].astype(str).tolist()
            columns = [raw_ids, df_src["duration_days"].to_numpy(), df_src["last_activity"].astype(str).tolist()]
        elif code == "11.7 C":
            sub = b.ex117.sub_c
            self.lbl_117_rule.setText("11.7 C: Case memuat setidaknya satu event O_Accepted (dihitung 1x per case)")
            self.lbl_117_dur_badge.setText(f"Rata-rata {fmt_num(sub.mean_duration_days, p)} hari")
            self.lbl_117_dur_badge.setVisible(True)
            headers = ["Case", "Durasi", "Berakhir di"]
            df_src = sub.case_df
            raw_ids = df_src["case_id"].astype(str).tolist()
            columns = [raw_ids, df_src["duration_days"].to_numpy(), df_src["last_activity"].astype(str).tolist()]
        elif code == "11.7 D":
            sub = b.ex117.sub_d
            self.lbl_117_rule.setText("11.7 D: Case memuat setidaknya satu event O_Refused (tidak saling eksklusif)")
            self.lbl_117_dur_badge.setText(f"Rata-rata {fmt_num(sub.mean_duration_days, p)} hari")
            self.lbl_117_dur_badge.setVisible(True)
            headers = ["Case", "Durasi", "Berakhir di"]
            df_src = sub.case_df
            raw_ids = df_src["case_id"].astype(str).tolist()
            columns = [raw_ids, df_src["duration_days"].to_numpy(), df_src["last_activity"].astype(str).tolist()]
        elif code == "11.7 E":
            sub = b.ex117.sub_e
            self.lbl_117_rule.setText("11.7 E: Event TERAKHIR pada trace adalah O_Cancelled (Endpoint filter)")
            self.lbl_117_dur_badge.setText(f"Rata-rata {fmt_num(sub.mean_duration_days, p)} hari")
            self.lbl_117_dur_badge.setVisible(True)
            headers = ["Case", "Durasi", "Berakhir di"]
            df_src = sub.case_df
            raw_ids = df_src["case_id"].astype(str).tolist()
            columns = [raw_ids, df_src["duration_days"].to_numpy(), ["O_Cancelled"] * len(raw_ids)]

        self._raw_ids_117 = raw_ids
        model = VirtualColumnTableModel(
            headers,
            columns,
            formatters=formatters,
            tooltips_col0=raw_ids,
            parent=self,
        )
        self.table_117.setModel(model)
        hh = self.table_117.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_117.setColumnWidth(0, 260)
        self.table_117.setColumnWidth(1, 140)

        if raw_ids:
            self.table_117.selectRow(0)
            self._update_evidence_strip(self.strip_117, raw_ids[0], code)
        else:
            self.strip_117.set_trace("", [], [])

    # ------------------------------------------------------------------
    # TAB 3: EXERCISE 11.15 & 11.18
    # ------------------------------------------------------------------
    def _create_tab_1115_1118(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Top row: 2 Answer Cards on left + Corong 11.15 -> 11.18 on right
        top_row = QHBoxLayout()
        top_row.setSpacing(24)

        cards_col = QHBoxLayout()
        cards_col.setSpacing(12)
        self.card_1115 = KartuAngka(code="11.15", value="—", label="Fraud 2x", height=104)
        self.card_1118 = KartuAngka(code="11.18", value="—", label="Resource sama", height=104)
        self.card_1115.clicked.connect(lambda: self._select_1518_sub("11.15"))
        self.card_1118.clicked.connect(lambda: self._select_1518_sub("11.18"))
        cards_col.addWidget(self.card_1115)
        cards_col.addWidget(self.card_1118)
        top_row.addLayout(cards_col, stretch=5)

        self.corong_1115 = Corong1115Widget()
        top_row.addWidget(self.corong_1115, stretch=5)
        layout.addLayout(top_row)

        h_div = QFrame()
        h_div.setFixedHeight(1)
        h_div.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(h_div)

        # Rule + Toggle "Tampilkan case yang tidak lolos"
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)
        self.lbl_1518_rule = QLabel("11.15: W_Assess Potential Fraud selesai (complete) minimal 2 kali")
        self.lbl_1518_rule.setStyleSheet(f"background: transparent; border: none; font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        ctrl_row.addWidget(self.lbl_1518_rule)
        ctrl_row.addStretch()

        self.chk_show_excluded_1518 = QCheckBox("Tampilkan case yang tidak lolos")
        self.chk_show_excluded_1518.setStyleSheet(f"font-size: 13px; color: {TEXT_PRIMARY}; font-weight: 500;")
        self.chk_show_excluded_1518.stateChanged.connect(lambda _: self._render_tab_1518())
        ctrl_row.addWidget(self.chk_show_excluded_1518)
        layout.addLayout(ctrl_row)

        self.lbl_1518_notice = QLabel("")
        self.lbl_1518_notice.setStyleSheet(f"background: transparent; border: none; font-size: 13px; color: {TEXT_MUTED};")
        self.lbl_1518_notice.setVisible(False)
        layout.addWidget(self.lbl_1518_notice)

        self.table_1518 = QTableView()
        self.table_1518.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table_1518.horizontalHeader().setStretchLastSection(True)
        self.table_1518.verticalHeader().setVisible(False)
        self.table_1518.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_1518.clicked.connect(lambda idx: self._on_tab_table_clicked(idx, "_raw_ids_1518", self.strip_1518, self.selected_1518_sub))
        layout.addWidget(self.table_1518, stretch=1)

        self.strip_1518 = StripAlur()
        layout.addWidget(self.strip_1518)

        act_row = QHBoxLayout()
        act_row.setSpacing(10)
        btn_exp = QPushButton("Buka di Case Explorer")
        btn_exp.clicked.connect(lambda: self._open_table_selection_in_explorer(self.table_1518, "_raw_ids_1518"))
        act_row.addWidget(btn_exp)

        btn_csv = QPushButton("Ekspor CSV soal ini")
        btn_csv.clicked.connect(lambda: self._export_table_csv(self.table_1518, self.selected_1518_sub))
        act_row.addWidget(btn_csv)

        btn_rerun = QPushButton("Jalankan ulang")
        btn_rerun.clicked.connect(self.on_rerun_all)
        act_row.addWidget(btn_rerun)
        act_row.addStretch()
        layout.addLayout(act_row)

        self._update_1518_card_selection()
        return widget

    def _select_1518_sub(self, code: str) -> None:
        self.selected_1518_sub = code
        self._update_1518_card_selection()
        if self.bundle:
            self._render_tab_1518()

    def _update_1518_card_selection(self) -> None:
        self.card_1115.set_selected(self.selected_1518_sub == "11.15")
        self.card_1118.set_selected(self.selected_1518_sub == "11.18")

    def _render_tab_1518(self) -> None:
        b = self.bundle
        if not b:
            return
        p = self.f02_precision
        ov = b.overview
        r15 = b.ex1115
        r18 = b.ex1118

        self.card_1115.set_content(fmt_int(r15.matching_case_count), f"{fmt_num(r15.matching_percentage, p)}%")
        self.card_1118.set_content(fmt_int(r18.matching_case_count), f"{fmt_num(r18.matching_percentage, p)}%")
        self.corong_1115.set_values(ov.total_cases, r15.matching_case_count, r18.matching_case_count, dec=p)

        self.lbl_1518_notice.setVisible(False)
        rows: List[List[Any]] = []
        raw_ids: List[str] = []
        tooltips: Dict[Tuple[int, int], str] = {}
        code = self.selected_1518_sub

        if code == "11.15":
            self.lbl_1518_rule.setText("11.15: W_Assess Potential Fraud selesai (complete) minimal 2 kali")
            if self.chk_show_excluded_1518.isChecked():
                self.lbl_1518_notice.setText(
                    f"Menampilkan {fmt_int(r15.excluded_by_lifecycle_count)} case yang memiliki >= 2 event W_Assess "
                    f"di seluruh lifecycle tetapi < 2 berstatus complete (tereliminasi filter complete-only)."
                )
                self.lbl_1518_notice.setVisible(True)
                headers = ["Case (Tidak Lolos)", "Complete / Total", "Alasan Ditolak"]
                excl_df = r15.excluded_summary_df
                if not excl_df.empty:
                    for idx_r, r in enumerate(excl_df.head(200).itertuples(index=False)):
                        cid = str(r.case_id)
                        raw_ids.append(cid)
                        tooltips[(idx_r, 0)] = cid
                        rows.append([
                            format_case_id_middle(cid),
                            f"{int(r.complete_occurrences)}x / {int(r.all_lifecycle_occurrences)}x",
                            "Ditolak: < 2 complete",
                        ])
            else:
                headers = ["Case", "Jumlah complete", "Resource sama"]
                same_res_cids = set(r18.case_resource_summary_df["case_id"].astype(str)) if not r18.case_resource_summary_df.empty else set()
                for idx_r, r in enumerate(r15.case_summary_df.itertuples(index=False)):
                    cid = str(r.case_id)
                    raw_ids.append(cid)
                    tooltips[(idx_r, 0)] = cid
                    res_str = str(getattr(r, "resources_involved", ""))
                    if cid in same_res_cids:
                        res_status = "Ya"
                    elif not res_str or res_str.strip() in ("", ",", "-"):
                        res_status = "Resource kosong"
                    else:
                        res_status = "Tidak"
                    rows.append([format_case_id_middle(cid), f"{r.complete_occurrences}x", res_status])
        else:
            self.lbl_1518_rule.setText("11.18: W_Assess Potential Fraud complete >= 2x oleh org:resource yang SAMA")
            if self.chk_show_excluded_1518.isChecked():
                excl = r18.cases_from_1115_excluded_diff_resource
                self.lbl_1518_notice.setText(
                    f"Menampilkan {fmt_int(len(excl))} case yang lolos 11.15 tetapi ditolak 11.18 karena resource berbeda atau kosong."
                )
                self.lbl_1518_notice.setVisible(True)
                headers = ["Case (Tidak Lolos)", "Resource Terlibat", "Alasan Ditolak"]
                df15 = r15.case_summary_df
                res_map = dict(zip(df15["case_id"].astype(str), df15["resources_involved"].astype(str))) if not df15.empty else {}
                for idx_r, cid in enumerate(excl[:200]):
                    raw_ids.append(cid)
                    tooltips[(idx_r, 0)] = cid
                    r_inv = res_map.get(cid, "—")
                    reason = "Ditolak: Resource kosong" if r_inv.strip() in ("", "-", "nan") else "Ditolak: Resource berbeda"
                    rows.append([format_case_id_middle(cid), r_inv, reason])
            else:
                headers = ["Case", "Resource", "Jumlah selesai"]
                for idx_r, r in enumerate(r18.case_resource_summary_df.itertuples(index=False)):
                    cid = str(r.case_id)
                    raw_ids.append(cid)
                    tooltips[(idx_r, 0)] = cid
                    rows.append([format_case_id_middle(cid), str(getattr(r, "resource_id", "—")), f"{r.same_resource_completions}x"])

        self._raw_ids_1518 = raw_ids
        model = Simple3ColTableModel(headers, rows, self, tooltips=tooltips)
        self.table_1518.setModel(model)
        hh = self.table_1518.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_1518.setColumnWidth(0, 260)
        self.table_1518.setColumnWidth(1, 180)

        if rows:
            self.table_1518.selectRow(0)
            self._update_evidence_strip(self.strip_1518, raw_ids[0], code)
        else:
            self.strip_1518.set_trace("", [], [])

    # ------------------------------------------------------------------
    # TAB 4: EXERCISE 11.22
    # ------------------------------------------------------------------
    def _create_tab_1122(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        ans_row = QHBoxLayout()
        ans_row.setSpacing(12)
        ans_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.lbl_22_ans = QLabel("—")
        self.lbl_22_ans.setStyleSheet(f"background: transparent; border: none; font-size: 38px; font-weight: 700; color: {TEXT_PRIMARY};")
        ans_row.addWidget(self.lbl_22_ans)

        self.lbl_22_pct = QLabel("")
        self.lbl_22_pct.setStyleSheet(f"background: transparent; border: none; font-size: 20px; font-weight: 500; color: {TEXT_MUTED};")
        ans_row.addWidget(self.lbl_22_pct)

        self.lbl_22_badge = QLabel("—")
        self.lbl_22_badge.setStyleSheet(
            f"background-color: {BG_SURFACE_MUTED}; color: {TEXT_PRIMARY}; "
            f"border: 1px solid {BORDER}; border-radius: 6px; padding: 4px 10px; font-size: 13px; font-weight: 600;"
        )
        ans_row.addWidget(self.lbl_22_badge)
        ans_row.addStretch()
        layout.addLayout(ans_row)

        self.lbl_22_rule = QLabel("Case memuat O_Cancelled lalu kemudian diikuti O_Accepted (posisi i < j, tidak harus bersebelahan)")
        self.lbl_22_rule.setStyleSheet(f"background: transparent; border: none; font-size: 14px; font-weight: 600; color: {TEXT_PRIMARY};")
        layout.addWidget(self.lbl_22_rule)

        self.table_22 = QTableView()
        self.table_22.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table_22.horizontalHeader().setStretchLastSection(True)
        self.table_22.verticalHeader().setVisible(False)
        self.table_22.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_22.clicked.connect(lambda idx: self._on_tab_table_clicked(idx, "_raw_ids_1122", self.strip_22, "11.22"))
        layout.addWidget(self.table_22, stretch=1)

        self.strip_22 = StripAlur()
        layout.addWidget(self.strip_22)

        self.lbl_22_offer_extra = QLabel("Analisis tambahan (Level OfferID): —")
        self.lbl_22_offer_extra.setWordWrap(True)
        self.lbl_22_offer_extra.setStyleSheet(f"background: transparent; border: none; font-size: 13px; color: {TEXT_MUTED};")
        layout.addWidget(self.lbl_22_offer_extra)

        act_row = QHBoxLayout()
        act_row.setSpacing(10)
        btn_exp = QPushButton("Buka di Case Explorer")
        btn_exp.clicked.connect(lambda: self._open_table_selection_in_explorer(self.table_22, "_raw_ids_1122"))
        act_row.addWidget(btn_exp)

        btn_csv = QPushButton("Ekspor CSV soal ini")
        btn_csv.clicked.connect(lambda: self._export_table_csv(self.table_22, "11.22"))
        act_row.addWidget(btn_csv)

        btn_rerun = QPushButton("Jalankan ulang")
        btn_rerun.clicked.connect(self.on_rerun_all)
        act_row.addWidget(btn_rerun)
        act_row.addStretch()
        layout.addLayout(act_row)

        return widget

    def _render_tab_1122(self) -> None:
        b = self.bundle
        if not b:
            return
        p = self.f02_precision
        total = b.overview.total_cases
        r22 = b.ex1122

        ans_txt = f"Ya, {fmt_int(r22.matching_case_count)} case" if r22.matching_case_count > 0 else "0 case"
        self.lbl_22_ans.setText(ans_txt)
        self.lbl_22_pct.setText(f"{fmt_num(r22.matching_percentage, p)}%")
        self.lbl_22_badge.setText(f"{fmt_int(r22.matching_case_count)} dari {fmt_int(total)} case")

        headers = ["Case", "Posisi O_Cancelled (i)", "Posisi O_Accepted (j)"]
        if not r22.case_summary_df.empty:
            raw_ids = r22.case_summary_df["case_id"].astype(str).tolist()
            columns: List[Sequence[Any]] = [
                raw_ids,
                r22.case_summary_df["cancelled_trace_pos"].to_numpy(),
                r22.case_summary_df["accepted_trace_pos"].to_numpy(),
            ]
        else:
            raw_ids = []
            columns = [[], [], []]

        formatters: List[Optional[Callable[[Any], str]]] = [
            None,
            lambda v: f"Posisi {int(v)} (i)",
            lambda v: f"Posisi {int(v)} (j)",
        ]

        self.lbl_22_offer_extra.setText(
            f"Analisis tambahan (Level OfferID): {fmt_int(r22.same_offer_id_matching_count)} case memiliki OfferID identik "
            f"antara penawaran yang dibatalkan dan penawaran yang diterima (Penjelasan 7.3 PDF)."
        )

        self._raw_ids_1122 = raw_ids
        model = VirtualColumnTableModel(
            headers,
            columns,
            formatters=formatters,
            tooltips_col0=raw_ids,
            parent=self,
        )
        self.table_22.setModel(model)
        hh = self.table_22.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_22.setColumnWidth(0, 260)
        self.table_22.setColumnWidth(1, 180)

        if raw_ids:
            self.table_22.selectRow(0)
            self._update_evidence_strip(self.strip_22, raw_ids[0], "11.22")
        else:
            self.strip_22.set_trace("", [], [])

    # ------------------------------------------------------------------
    # SHARED EVIDENCE & ACTION HELPERS FOR EXERCISE TABS
    # ------------------------------------------------------------------
    def _on_tab_table_clicked(self, idx: QModelIndex, ids_attr: str, strip: StripAlur, code: str) -> None:
        raw_ids = getattr(self, ids_attr, [])
        if not idx.isValid() or not raw_ids:
            return
        r = idx.row()
        if 0 <= r < len(raw_ids):
            self._update_evidence_strip(strip, raw_ids[r], code)

    def _update_evidence_strip(self, strip: StripAlur, case_id: str, code: str) -> None:
        b = self.bundle
        if not b or not case_id:
            return
        events_df = b.context.get_case_events(case_id)
        if events_df.empty:
            strip.set_trace(case_id, [], [])
            return

        ev_list = events_df.to_dict(orient="records")
        hl_indices = self._compute_highlight_indices(ev_list, code, has_lifecycle=b.report.has_lifecycle)

        strip.set_trace(
            case_id,
            ev_list,
            hl_indices,
            show_resource_and_date=(code in ("11.15", "11.18")),
        )

    @staticmethod
    def _compute_highlight_indices(
        ev_list: List[Dict[str, Any]],
        code: str,
        *,
        has_lifecycle: bool = True,
    ) -> List[int]:
        """Determines which event indices in a trace are evidence for the given exercise code."""
        hl_indices: List[int] = []
        if code == "11.7 C":
            hl_indices = [i for i, ev in enumerate(ev_list) if str(ev.get("concept:name", "")).strip() == "O_Accepted"]
        elif code == "11.7 D":
            hl_indices = [i for i, ev in enumerate(ev_list) if str(ev.get("concept:name", "")).strip() == "O_Refused"]
        elif code == "11.7 E":
            if ev_list and str(ev_list[-1].get("concept:name", "")).strip() == "O_Cancelled":
                hl_indices = [len(ev_list) - 1]
        elif code in ("11.15", "11.18"):
            fraud_comp_indices: List[int] = []
            res_counts: Dict[str, List[int]] = {}
            for i, ev in enumerate(ev_list):
                act_ok = str(ev.get("concept:name", "")).strip().lower() == "w_assess potential fraud"
                if not act_ok:
                    continue
                if has_lifecycle:
                    lc_ok = str(ev.get("lifecycle:transition", "")).strip().lower() == "complete"
                else:
                    lc_ok = True
                if lc_ok:
                    fraud_comp_indices.append(i)
                    res_val = ev.get("org:resource")
                    if is_valid_resource(res_val):
                        r_clean = str(res_val).strip()
                        res_counts.setdefault(r_clean, []).append(i)
            if code == "11.18":
                same_res_indices = [i for idxs in res_counts.values() if len(idxs) >= 2 for i in idxs]
                hl_indices = sorted(same_res_indices) if same_res_indices else fraud_comp_indices
            else:
                hl_indices = fraud_comp_indices
        elif code == "11.22":
            for i, ev in enumerate(ev_list):
                if str(ev.get("concept:name", "")).strip() in ("O_Cancelled", "O_Accepted"):
                    hl_indices.append(i)
        return hl_indices

    def _open_table_selection_in_explorer(self, table_view: QTableView, ids_attr: str) -> None:
        raw_ids = getattr(self, ids_attr, [])
        if not raw_ids:
            return
        row = table_view.currentIndex().row()
        if row < 0:
            row = 0
        self._select_case_in_explorer(raw_ids[row])

    def _get_full_export_df_for_label(self, label: str) -> Optional[pd.DataFrame]:
        """Returns the full untruncated DataFrame corresponding to an exercise tab export."""
        b = self.bundle
        if not b:
            return None
        if label in ("11.7 A", "11.7 B"):
            return b.overview.case_table
        if label == "11.7 C":
            return b.ex117.sub_c.case_df
        if label == "11.7 D":
            return b.ex117.sub_d.case_df
        if label == "11.7 E":
            return b.ex117.sub_e.case_df
        if label == "11.15":
            if self.chk_show_excluded_1518.isChecked():
                return b.ex1115.excluded_summary_df
            return b.ex1115.case_summary_df
        if label == "11.18":
            if self.chk_show_excluded_1518.isChecked():
                excl = b.ex1118.cases_from_1115_excluded_diff_resource
                df15 = b.ex1115.case_summary_df
                res_map = dict(zip(df15["case_id"].astype(str), df15["resources_involved"].astype(str))) if not df15.empty else {}
                rows = [
                    {
                        "case_id": cid,
                        "resources_involved": res_map.get(cid, "-"),
                        "reason": "Resource kosong" if res_map.get(cid, "").strip() in ("", "-", "nan") else "Resource berbeda",
                    }
                    for cid in excl
                ]
                return pd.DataFrame(rows)
            return b.ex1118.case_resource_summary_df
        if label == "11.22":
            return b.ex1122.case_summary_df
        return None

    def _export_table_csv(self, table_view: QTableView, label: str) -> None:
        if not self.bundle:
            return
        safe_lbl = label.replace(" ", "_").replace(".", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, f"Ekspor CSV {label}", f"hasil_{safe_lbl}.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            full_df = self._get_full_export_df_for_label(label)
            if full_df is not None:
                full_df.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                model = table_view.model()
                if isinstance(model, Simple3ColTableModel):
                    df = pd.DataFrame(model._rows, columns=model._headers)
                    df.to_csv(path, index=False, encoding="utf-8-sig")
            self.has_exported = True
            is_bpic = not ("synthetic" in self.bundle.report.file_name.lower())
            self.drawer.update_states(
                has_data=True,
                has_analysis=True,
                is_bpic17=self.seen_bpic17 or is_bpic,
                is_synthetic=self.seen_synthetic or (not is_bpic),
                exported=True,
            )
            self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")
            QMessageBox.information(self, "Ekspor Berhasil", f"Tabel soal {label} disimpan ke:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Ekspor Gagal", str(exc))

    # ------------------------------------------------------------------
    # TAB 4: CASE EXPLORER (F07)
    # ------------------------------------------------------------------
    def _create_tab_explorer(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(24)

        # Left panel (width 430px so full BPIC17 Case IDs are readable without ellipsis)
        left_box = QWidget()
        left_box.setFixedWidth(430)
        ll = QVBoxLayout(left_box)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)

        self._exp_search_timer = QTimer(self)
        self._exp_search_timer.setSingleShot(True)
        self._exp_search_timer.setInterval(180)
        self._exp_search_timer.timeout.connect(self._apply_explorer_filter)

        self.exp_search = QLineEdit()
        self.exp_search.setPlaceholderText("Cari Case ID...")
        self.exp_search.textChanged.connect(lambda _: self._exp_search_timer.start())
        ll.addWidget(self.exp_search)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.cmb_exp_group = QComboBox()
        self.cmb_exp_group.addItems([
            "Semua case",
            "11.7 C (Berhasil)",
            "11.7 D (Tidak berhasil)",
            "11.7 E (Dibatalkan)",
            "11.15 (Fraud 2x)",
            "11.18 (Resource sama)",
            "11.22 (Cancelled lalu Accepted)",
        ])
        self.cmb_exp_group.currentIndexChanged.connect(self._on_explorer_group_changed)
        filter_row.addWidget(self.cmb_exp_group, stretch=1)

        btn_reset = QPushButton("Reset")
        btn_reset.clicked.connect(self._on_explorer_reset)
        filter_row.addWidget(btn_reset)
        ll.addLayout(filter_row)

        self.lbl_exp_group_info = QLabel("Memuat daftar case...")
        self.lbl_exp_group_info.setWordWrap(True)
        self.lbl_exp_group_info.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
        ll.addWidget(self.lbl_exp_group_info)

        self.table_exp_cases = QTableView()
        self.table_exp_cases.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table_exp_cases.horizontalHeader().setStretchLastSection(True)
        self.table_exp_cases.verticalHeader().setVisible(False)
        self.table_exp_cases.clicked.connect(self._on_exp_case_clicked)
        ll.addWidget(self.table_exp_cases, stretch=1)

        layout.addWidget(left_box)

        v_div = QFrame()
        v_div.setFixedWidth(1)
        v_div.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(v_div)

        # Right panel (tanpa bingkai kartu)
        right_box = QWidget()
        rl = QVBoxLayout(right_box)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(10)

        # Summary line
        self.lbl_exp_summary = QLabel("Pilih sebuah case untuk melihat alur event-nya.")
        self.lbl_exp_summary.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};")
        rl.addWidget(self.lbl_exp_summary)

        self.lbl_exp_flow = QLabel("—")
        self.lbl_exp_flow.setStyleSheet(f"background: transparent; border: none; font-size: 13px; color: {TEXT_MUTED};")
        rl.addWidget(self.lbl_exp_flow)

        # Trace Events Table (Waktu, Aktivitas + lifecycle subtext, Resource)
        self.table_exp_events = QTableView()
        self.table_exp_events.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table_exp_events.horizontalHeader().setStretchLastSection(True)
        self.table_exp_events.verticalHeader().setVisible(False)
        self.table_exp_events.setItemDelegateForColumn(1, ActivityLifecycleDelegate(self.table_exp_events))
        rl.addWidget(self.table_exp_events, stretch=1)

        # Checkbox: Tampilkan detail (Offer ID, Event ID)
        self.chk_exp_detail = QCheckBox("Tampilkan detail (Offer ID, Event ID)")
        self.chk_exp_detail.setStyleSheet(f"font-size: 13px; color: {TEXT_MUTED};")
        self.chk_exp_detail.stateChanged.connect(self._on_exp_detail_toggled)
        rl.addWidget(self.chk_exp_detail)

        layout.addWidget(right_box, stretch=1)

        return widget

    def _on_explorer_group_changed(self) -> None:
        if not self.bundle:
            return
        idx = self.cmb_exp_group.currentIndex()
        b = self.bundle
        total = b.overview.total_cases

        if idx == 0:
            df = b.overview.case_table
            info = f"Menampilkan {fmt_int(len(df))} dari {fmt_int(total)} case (100,00%)"
        elif idx == 1:
            df = b.ex117.sub_c.case_df
            info = f"11.7 C (Contains O_Accepted): {fmt_int(len(df))} dari {fmt_int(total)} case ({fmt_num(b.ex117.sub_c.case_percentage, self.f02_precision)}%)"
        elif idx == 2:
            df = b.ex117.sub_d.case_df
            info = f"11.7 D (Contains O_Refused): {fmt_int(len(df))} dari {fmt_int(total)} case ({fmt_num(b.ex117.sub_d.case_percentage, self.f02_precision)}%)"
        elif idx == 3:
            df = b.ex117.sub_e.case_df
            info = f"11.7 E (Endpoint O_Cancelled): {fmt_int(len(df))} dari {fmt_int(total)} case ({fmt_num(b.ex117.sub_e.case_percentage, self.f02_precision)}%)"
        elif idx == 4:
            df = b.ex1115.case_summary_df
            info = f"11.15 (Fraud >= 2x complete): {fmt_int(len(df))} dari {fmt_int(total)} case ({fmt_num(b.ex1115.matching_percentage, self.f02_precision)}%)"
        elif idx == 5:
            df = b.ex1118.case_resource_summary_df
            info = f"11.18 (Resource sama): {fmt_int(b.ex1118.matching_case_count)} dari {fmt_int(total)} case ({fmt_num(b.ex1118.matching_percentage, self.f02_precision)}%)"
        else:
            df = b.ex1122.case_summary_df
            info = f"11.22 (O_Cancelled -> O_Accepted): {fmt_int(len(df))} dari {fmt_int(total)} case ({fmt_num(b.ex1122.matching_percentage, self.f02_precision)}%)"

        self.lbl_exp_group_info.setText(info)
        self._exp_current_df = df
        self._apply_explorer_filter()

    def _apply_explorer_filter(self) -> None:
        self._on_explorer_filter(self.exp_search.text())

    def _on_explorer_filter(self, text: str) -> None:
        if not hasattr(self, "_exp_current_df") or self._exp_current_df is None:
            return
        if not text.strip():
            self._populate_explorer_case_list(self._exp_current_df)
        else:
            filtered = self._exp_current_df[
                self._exp_current_df["case_id"].astype(str).str.contains(text.strip(), case=False, na=False)
            ]
            self._populate_explorer_case_list(filtered)

    def _on_explorer_reset(self) -> None:
        self.exp_search.clear()
        self.cmb_exp_group.setCurrentIndex(0)
        if self.bundle:
            self._on_explorer_group_changed()

    def _populate_explorer_case_list(self, df: pd.DataFrame) -> None:
        headers = ["Case ID", "Event", "Lolos di"]
        tags_map = self.bundle.case_category_tags if self.bundle else getattr(self, "_case_category_tags", {})
        cids = df["case_id"].astype(str).tolist() if not df.empty else []
        if df.empty:
            ecnts: Sequence[Any] = []
        elif "event_count" in df.columns:
            ecnts = df["event_count"].to_numpy()
        elif "case_total_events" in df.columns:
            ecnts = df["case_total_events"].to_numpy()
        elif self.bundle is not None and not self.bundle.overview.case_table.empty:
            ev_map = self.bundle.overview.case_table["event_count"]
            ecnts = [int(ev_map.get(cid, 0)) if cid in ev_map.index else "—" for cid in cids]
        else:
            ecnts = ["—"] * len(cids)

        self._exp_raw_cids = cids
        model = VirtualColumnTableModel(
            headers,
            [cids, ecnts, cids],
            formatters=[
                None,
                None,
                lambda cid: tags_map.get(str(cid), "—"),
            ],
            tooltips_col0=cids,
            parent=self,
        )
        self.table_exp_cases.setModel(model)
        # Interactive fixed widths keep 31.509+ rows instantaneous without freezing UI
        hh = self.table_exp_cases.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_exp_cases.setColumnWidth(0, 235)
        self.table_exp_cases.setColumnWidth(1, 55)

        if cids:
            self.table_exp_cases.selectRow(0)
            self._display_explorer_case_events(cids[0])
        else:
            self.lbl_exp_summary.setText("Tidak ada case yang cocok dengan filter.")
            self.lbl_exp_flow.setText("—")
            self._current_exp_ev_df = pd.DataFrame()
            self.table_exp_events.setModel(Simple3ColTableModel(["Waktu", "Aktivitas", "Resource"], [], self))

    def _on_exp_case_clicked(self, idx: QModelIndex) -> None:
        if not idx.isValid() or not hasattr(self, "_exp_raw_cids"):
            return
        row = idx.row()
        if 0 <= row < len(self._exp_raw_cids):
            cid = self._exp_raw_cids[row]
            self._display_explorer_case_events(cid)

    def _display_explorer_case_events(self, case_id: str) -> None:
        b = self.bundle
        if not b or not case_id:
            return
        ev_df = b.context.get_case_events(case_id)
        if ev_df.empty:
            return

        # Case metadata
        cs = b.context.case_summary_df
        dur_d = 0.0
        f_act = "-"
        l_act = "-"
        if case_id in cs.index:
            row = cs.loc[case_id]
            dur_d = float(row["duration_days"])
            f_act = str(row["first_activity"])
            l_act = str(row["last_activity"])

        self.lbl_exp_summary.setText(
            f"{format_case_id_middle(case_id, max_len=45)}: {fmt_int(len(ev_df))} event, durasi {fmt_num(dur_d, self.f02_precision)} hari"
        )
        self.lbl_exp_summary.setToolTip(str(case_id))
        self.lbl_exp_flow.setText(f"Aktivitas awal: {f_act}, aktivitas akhir: {l_act}")

        self._current_exp_ev_df = ev_df
        self._render_explorer_events_table()

    def _on_exp_detail_toggled(self, _) -> None:
        self._render_explorer_events_table()

    def _render_explorer_events_table(self) -> None:
        if not hasattr(self, "_current_exp_ev_df") or self._current_exp_ev_df.empty:
            return
        df = self._current_exp_ev_df
        show_detail = self.chk_exp_detail.isChecked()

        if show_detail:
            headers = ["Waktu", "Aktivitas", "Resource", "Offer ID", "Event ID"]
        else:
            headers = ["Waktu", "Aktivitas", "Resource"]

        rows: List[List[Any]] = []
        subtexts: Dict[Tuple[int, int], str] = {}
        ev_list = df.to_dict(orient="records")
        for idx_r, rec in enumerate(ev_list):
            ts_str = format_timestamp_compact(str(rec.get("time:timestamp", "—")))
            act = str(rec.get("concept:name", "—"))
            lc_raw = rec.get("lifecycle:transition", "")
            lc = "" if pd.isna(lc_raw) else str(lc_raw).strip()
            if lc:
                subtexts[(idx_r, 1)] = f"lifecycle: {lc}"

            res_raw = rec.get("org:resource", "")
            res = "—" if pd.isna(res_raw) or not str(res_raw).strip() else str(res_raw).strip()
            if show_detail:
                off_raw = rec.get("OfferID", "")
                off = "—" if pd.isna(off_raw) or not str(off_raw).strip() else str(off_raw).strip()
                eid_raw = rec.get("EventID", "")
                eid = "—" if pd.isna(eid_raw) or not str(eid_raw).strip() else str(eid_raw).strip()
                rows.append([ts_str, act, res, off, eid])
            else:
                rows.append([ts_str, act, res])

        group_code_map = {1: "11.7 C", 2: "11.7 D", 3: "11.7 E", 4: "11.15", 5: "11.18", 6: "11.22"}
        code = group_code_map.get(self.cmb_exp_group.currentIndex(), "")
        has_lc = self.bundle.report.has_lifecycle if self.bundle else True
        hl_rows = set(self._compute_highlight_indices(ev_list, code, has_lifecycle=has_lc)) if code else set()

        model = Simple3ColTableModel(headers, rows, self, subtexts=subtexts, highlight_rows=hl_rows)
        self.table_exp_events.setModel(model)
        self.table_exp_events.verticalHeader().setDefaultSectionSize(44 if subtexts else 32)
        self.table_exp_events.resizeRowsToContents()
        hh = self.table_exp_events.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        self.table_exp_events.setColumnWidth(0, 145)
        self.table_exp_events.setColumnWidth(1, 240)
        if show_detail:
            self.table_exp_events.setColumnWidth(2, 110)
            self.table_exp_events.setColumnWidth(3, 140)
            hh.setSectionResizeMode(4, QHeaderView.Stretch)
        else:
            hh.setSectionResizeMode(2, QHeaderView.Stretch)

    def _select_case_in_explorer(self, case_id: str) -> None:
        self._set_active_tab(4)  # Switch to Case Explorer
        self.cmb_exp_group.setCurrentIndex(0)
        self.exp_search.setText(case_id)
        self._display_explorer_case_events(case_id)

    # ------------------------------------------------------------------
    # ACTIONS & LOGIC HANDLERS
    # ------------------------------------------------------------------
    def _toggle_drawer(self) -> None:
        if self.drawer.isVisible():
            self.drawer.hide()
        else:
            self.drawer.show()

    def _on_navigate_from_drawer(self, tab_idx: int) -> None:
        self._set_active_tab(tab_idx)
        self.drawer.hide()

    def _show_about_dialog(self) -> None:
        dlg = AboutDialog(self)
        dlg.exec()

    def _show_all_activities_dialog(self) -> None:
        if not self.bundle:
            return
        dlg = ActivityListDialog(self.bundle.overview.activity_table, self)
        dlg.exec()

    def _show_case_duration_dialog(self) -> None:
        if not self.bundle:
            return
        dlg = CaseDurationDialog(self.bundle.overview.case_table, self)
        dlg.case_double_clicked.connect(self._select_case_in_explorer)
        dlg.exec()

    def _show_fast_slow_dialog(self) -> None:
        if not self.bundle:
            return
        dlg = FastSlowDialog(self.bundle.overview, self)
        dlg.exec()

    def _show_ganti_data_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color: {BG_CARD}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 6px; }} "
            f"QMenu::item {{ padding: 6px 14px; border-radius: 4px; }} "
            f"QMenu::item:selected {{ background-color: {SELECTION_BG}; color: {SELECTION_TEXT}; }}"
        )

        act_browse = menu.addAction("Impor Berkas XES (.xes / .xes.gz)...")
        act_browse.triggered.connect(self.on_browse_xes)

        act_bpic = menu.addAction("Muat Dataset Utama BPIC17 (.xes.gz)")
        act_bpic.triggered.connect(self.on_load_bpic17)

        act_syn = menu.addAction("Muat Log Sintetis Edge Cases (10 Case)")
        act_syn.triggered.connect(self.on_load_synthetic_log)

        menu.addSeparator()

        act_rerun = menu.addAction("Jalankan Ulang Semua Analisis")
        act_rerun.triggered.connect(self.on_rerun_all)

        pos = self.btn_ganti_data.mapToGlobal(QPoint(0, self.btn_ganti_data.height()))
        menu.exec(pos)

    def on_browse_xes(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Berkas Event Log XES", os.getcwd(), "XES Files (*.xes *.xes.gz)"
        )
        if path:
            self.start_analysis(path)

    def on_load_bpic17(self) -> None:
        proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rel_candidates = (
            "data/BPI Challenge 2017.xes.gz",
            "BPI Challenge 2017.xes.gz",
            "data/BPI_Challenge_2017.xes.gz",
            "BPI_Challenge_2017.xes.gz",
            "data/BPI Challenge 2017.xes",
            "BPI Challenge 2017.xes",
        )
        for base_dir in (os.getcwd(), proj_root):
            for rel in rel_candidates:
                cand = os.path.join(base_dir, rel)
                if os.path.exists(cand):
                    self.start_analysis(cand)
                    return
        QMessageBox.warning(
            self,
            "Berkas BPIC17 Tidak Ditemukan",
            "Unduh dataset BPI Challenge 2017 (.xes.gz) dan letakkan di folder proyek atau data/.",
        )

    def on_load_synthetic_log(self) -> None:
        syn_path = os.path.join(os.getcwd(), "data", "synthetic_edge_cases.xes")
        try:
            generate_synthetic_xes_file(syn_path)
            self.start_analysis(syn_path)
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Membuat Log Sintetis", str(exc))

    def on_rerun_all(self) -> None:
        if not self.bundle:
            return
        self.start_analysis(self.bundle.report.file_path, existing_context=self.bundle.context)

    def start_analysis(self, file_path: str, existing_context: Optional[EventLogContext] = None) -> None:
        if self.worker is not None and self.worker.isRunning():
            return

        self.lbl_header_file.setText(os.path.basename(file_path))
        self.badge_status.set_status("busy", "Memuat...")
        self.pbar_load.setValue(5)
        self.lbl_load_time.setText("Membaca XES...")
        self.box_error.setVisible(False)
        self.box_warnings.setVisible(False)
        self.btn_ganti_data.setEnabled(False)
        self.btn_ekspor.setEnabled(False)
        self.status_bar.showMessage("Memuat dan menganalisis event log...")

        self.worker = AnalysisWorker(file_path=file_path, existing_context=existing_context)
        self.worker.progress_changed.connect(self._on_analysis_progress)
        self.worker.finished_bundle.connect(self._on_analysis_finished)
        self.worker.failed_error.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_analysis_progress(self, pct: int, msg: str) -> None:
        self.pbar_load.setValue(pct)
        self.lbl_load_time.setText(msg)

    def _on_analysis_failed(self, err_msg: str) -> None:
        self.btn_ganti_data.setEnabled(True)
        self.btn_ekspor.setEnabled(self.bundle is not None)
        self.badge_status.set_status("failed", "✕ Gagal")
        self.pbar_load.setValue(0)
        self.lbl_load_time.setText("Gagal memuat berkas.")
        self.box_error.setVisible(True)
        self.lbl_err_msg.setText(err_msg)
        self.status_bar.showMessage("Gagal memuat berkas XES.")
        QMessageBox.critical(self, "Kesalahan Impor / Validasi XES", err_msg)

    def _on_analysis_finished(self, bundle: FullAnalysisBundle) -> None:
        self.btn_ganti_data.setEnabled(True)
        self.btn_ekspor.setEnabled(True)
        self.bundle = bundle
        rep = bundle.report
        ov = bundle.overview

        self.badge_status.set_status("valid", "✓ Valid")
        self.pbar_load.setValue(100)
        self.lbl_load_time.setText(f"Data dimuat dalam {fmt_num(rep.load_time_seconds, 2)} detik.")
        self.lbl_header_file.setText(rep.file_name)
        self.status_bar.showMessage("Siap.")

        if rep.warnings:
            self.lbl_warnings_msg.setText("Peringatan validasi: " + " | ".join(rep.warnings))
            self.box_warnings.setVisible(True)
        else:
            self.box_warnings.setVisible(False)

        if bundle.case_category_tags:
            self._case_category_tags = bundle.case_category_tags
        else:
            self._case_category_tags = _compute_case_category_tags(
                ov, bundle.ex117, bundle.ex1115, bundle.ex1118, bundle.ex1122
            )

        # 1. Update Tab Data
        self.card_cases.set_content(fmt_int(rep.total_cases), label="Case")
        self.card_events.set_content(fmt_int(rep.total_events), label="Event")
        self.card_acts.set_content(fmt_int(ov.unique_activities), label="Aktivitas")
        self.card_resources.set_content(fmt_int(ov.unique_resources), label="Resource unik")

        # Chips
        has_cid = "case:concept:name" not in rep.missing_required and rep.is_valid
        has_act = "concept:name" not in rep.missing_required and rep.is_valid
        has_ts = "time:timestamp" not in rep.missing_required and rep.is_valid
        self.chip_case_id.set_state(has_cid)
        self.chip_concept_name.set_state(has_act)
        self.chip_timestamp.set_state(has_ts)
        self.chip_lifecycle.set_state(rep.has_lifecycle)
        self.chip_resource.set_state(rep.has_resource)

        # Activity Bars (top 5)
        while self.box_act_bars.count():
            item = self.box_act_bars.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        top5 = ov.activity_table.head(5)
        max_cnt = top5["event_count"].max() if not top5.empty else 1
        for _, r in top5.iterrows():
            act_bar = BarAktivitas(str(r["activity"]), int(r["event_count"]), max_cnt)
            self.box_act_bars.addWidget(act_bar)

        self.btn_see_all_acts.setText(f"Lihat semua {ov.unique_activities} aktivitas")

        # Lifecycle Distribution Bars (Section 3a)
        while self.box_lc_bars.count():
            item = self.box_lc_bars.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        if ov.lifecycle_counts:
            max_lc = max(ov.lifecycle_counts.values())
            for lc_name, lc_cnt in ov.lifecycle_counts.items():
                self.box_lc_bars.addWidget(BarAktivitas(lc_name, lc_cnt, max_lc))
        else:
            lbl_nolc = QLabel("Atribut lifecycle:transition tidak tersedia pada log ini.")
            lbl_nolc.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
            self.box_lc_bars.addWidget(lbl_nolc)

        # Time range & Histogram
        t_start = format_timestamp_compact(str(ov.log_start_time))
        t_end = format_timestamp_compact(str(ov.log_end_time))
        self.lbl_time_range.setText(f"{t_start} – {t_end}")
        if not ov.case_table.empty:
            self.hist_durasi.set_durations(ov.case_table["duration_days"].to_numpy())
        else:
            self.hist_durasi.set_durations([])

        # Refresh all precision-dependent numbers across Data, Jawaban, Detail
        self._refresh_all_numbers_precision()

        # 3. Update Case Explorer
        self._on_explorer_group_changed()

        # 4. Update Checklist Drawer
        is_syn = "synthetic" in rep.file_name.lower()
        if is_syn:
            self.seen_synthetic = True
        else:
            self.seen_bpic17 = True
        self.drawer.update_states(
            has_data=True,
            has_analysis=True,
            is_bpic17=self.seen_bpic17,
            is_synthetic=self.seen_synthetic,
            exported=self.has_exported,
        )
        self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")

    def _refresh_all_numbers_precision(self) -> None:
        b = self.bundle
        if not b:
            return
        p = self.f02_precision
        ov = b.overview
        self._update_f02_durations(ov)

        # Fast vs Slow summary
        self.lbl_fast_slow_summary.setText(
            f"Fast (< 45 hari): {fmt_int(ov.fast_cases_count)} ({fmt_num(ov.fast_cases_pct, p)}%), "
            f"Slow (>= 45 hari): {fmt_int(ov.slow_cases_count)} ({fmt_num(ov.slow_cases_pct, p)}%)"
        )

        # Refresh Exercise 11.7, 11.15 & 11.18, and 11.22 tabs
        self._render_tab_117()
        self._render_tab_1518()
        self._render_tab_1122()

    def _update_f02_durations(self, ov: OverviewResult) -> None:
        p = self.f02_precision
        if self.f02_unit == "hari":
            unit_s = "hari"
            mean_val = f"{fmt_num(ov.mean_cycle_time_days, p)} hari"
            min_v = fmt_num(ov.min_cycle_time_days, p)
            med_v = fmt_num(ov.median_cycle_time_days, p)
            max_v = fmt_num(ov.max_cycle_time_days, p)
            std_v = f"{fmt_num(ov.std_cycle_time_days, p)} hari"
        elif self.f02_unit == "jam":
            unit_s = "jam"
            mean_val = f"{fmt_num(ov.mean_cycle_time_hours, p)} jam"
            min_v = fmt_num(ov.min_cycle_time_days * 24, p)
            med_v = fmt_num(ov.median_cycle_time_days * 24, p)
            max_v = fmt_num(ov.max_cycle_time_days * 24, p)
            std_v = f"{fmt_num(ov.std_cycle_time_days * 24, p)} jam"
        else:
            unit_s = "dtk"
            mean_val = f"{fmt_int(round(ov.mean_cycle_time_days * 86400))} dtk"
            min_v = fmt_int(round(ov.min_cycle_time_days * 86400))
            med_v = fmt_int(round(ov.median_cycle_time_days * 86400))
            max_v = fmt_int(round(ov.max_cycle_time_days * 86400))
            std_v = f"{fmt_int(round(ov.std_cycle_time_days * 86400))} dtk"

        self.card_dur.set_content(mean_val, label="Rata-rata durasi")
        self.lbl_dur_min.setText(f"{min_v} {unit_s}")
        self.lbl_dur_med.setText(f"{med_v} {unit_s}")
        self.lbl_dur_max.setText(f"{max_v} {unit_s}")
        self.lbl_std_dev.setText(std_v)

    # ------------------------------------------------------------------
    # EXPORT DIALOG & EXPORT LOGIC
    # ------------------------------------------------------------------
    def on_export_dialog(self) -> None:
        if not self.bundle:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat berkas XES terlebih dahulu.")
            return

        dlg = ExportDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        choice = dlg.get_selected_option()
        b = self.bundle

        if choice == 1:
            # Ringkasan jawaban CSV
            path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Ringkasan Jawaban CSV", "ringkasan_jawaban_bpic17.csv", "CSV Files (*.csv)"
            )
            if path:
                sum_df = build_summary_dataframe(
                    b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122
                )
                sum_df.to_csv(path, index=False, encoding="utf-8-sig")
                self.has_exported = True
                self.drawer.update_states(
                    has_data=True,
                    has_analysis=True,
                    is_bpic17=self.seen_bpic17,
                    is_synthetic=self.seen_synthetic,
                    exported=True,
                )
                self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")
                QMessageBox.information(self, "Ekspor Berhasil", f"Ringkasan jawaban disimpan ke:\n{path}")

        elif choice == 2:
            # Daftar case terpilih CSV (folder)
            out_dir = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekspor Case Terpilih")
            if out_dir:
                export_all_to_directory(
                    out_dir, b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122
                )
                self.has_exported = True
                self.drawer.update_states(
                    has_data=True,
                    has_analysis=True,
                    is_bpic17=self.seen_bpic17,
                    is_synthetic=self.seen_synthetic,
                    exported=True,
                )
                self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")
                QMessageBox.information(self, "Ekspor Berhasil", f"Daftar case disimpan ke folder:\n{out_dir}")

        elif choice == 3:
            # HTML Report
            path, _ = QFileDialog.getSaveFileName(
                self, "Simpan Laporan HTML", "laporan_analisis_bpic17.html", "HTML Files (*.html)"
            )
            if path:
                sum_df = build_summary_dataframe(
                    b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122
                )
                html_txt = generate_html_report(
                    b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122, sum_df
                )
                with open(path, "w", encoding="utf-8") as f:
                    f.write(html_txt)
                self.has_exported = True
                self.drawer.update_states(
                    has_data=True,
                    has_analysis=True,
                    is_bpic17=self.seen_bpic17,
                    is_synthetic=self.seen_synthetic,
                    exported=True,
                )
                self.btn_checklist_chip.setText(f"Checklist {self.drawer.get_progress_text()}")
                QMessageBox.information(self, "Ekspor Berhasil", f"Laporan HTML disimpan ke:\n{path}")
