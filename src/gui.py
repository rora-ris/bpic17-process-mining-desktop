"""PySide6 Desktop GUI for ProcessMine Studio — Loan Application Process Mining (BPIC17)."""

from __future__ import annotations

import os
import re
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QRectF,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
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
from .core import EventLogContext, ValidationReport, get_environment_info, load_and_validate_xes
from .exporter import build_summary_dataframe, export_all_to_directory
from .synthetic import generate_synthetic_xes_file


COLUMN_HEADER_MAP: Dict[str, str] = {
    "case_id": "Case ID",
    "case:concept:name": "Case ID",
    "activity": "Activity",
    "concept:name": "Activity",
    "event_count": "Events",
    "complete_event_count": "Complete",
    "event_percentage": "% Events",
    "event_pct": "% Events",
    "case_count": "Cases",
    "case_percentage": "% Cases",
    "case_pct": "% Cases",
    "start_timestamp": "Start Time",
    "end_timestamp": "End Time",
    "first_activity": "First Activity",
    "last_activity": "Last Activity",
    "duration_seconds": "Duration (s)",
    "duration_hours": "Duration (hr)",
    "duration_days": "Cycle Time (d)",
    "case_duration_days": "Cycle Time (d)",
    "minmax_duration_days": "Span (d)",
    "speed_category": "SLA Tier",
    "trigger_activity": "Trigger",
    "trigger_count": "Hits",
    "complete_occurrences": "Complete",
    "all_lifecycle_occurrences": "All Lifecycle",
    "resources_involved": "Resources Involved",
    "unique_valid_resources": "Unique Res",
    "case_total_events": "Total Events",
    "resource_id": "Resource ID",
    "org:resource": "Resource",
    "same_resource_completions": "Same-Res Complete",
    "total_case_completions": "Case Complete",
    "evidence_event_ids": "Evidence Event IDs",
    "first_complete_time": "First Complete",
    "last_complete_time": "Last Complete",
    "_trace_pos": "#",
    "time:timestamp": "Timestamp",
    "lifecycle:transition": "Lifecycle",
    "cancelled_trace_pos": "Cancel Pos (i)",
    "cancelled_timestamp": "O_Cancelled Time",
    "cancelled_offer_id": "Cancelled OfferID",
    "accepted_trace_pos": "Accept Pos (j)",
    "accepted_timestamp": "O_Accepted Time",
    "accepted_offer_id": "Accepted OfferID",
    "intervening_events_count": "Gap Events",
    "time_between_days": "Gap (d)",
    "trace_end_activity": "Trace End",
    "same_offer_id": "Same OfferID?",
    "OfferID": "Offer ID",
    "EventID": "Event ID",
    "EventOrigin": "Origin",
    "Action": "Action",
    "Kode Soal": "Kode",
    "Pertanyaan": "Metrik / Pertanyaan",
    "Aturan / Filter": "Aturan Filter",
    "Jumlah Case Terpilih": "Case",
    "Denominator (Total Case Aktif)": "Total",
    "Persentase Case (%)": "Persen",
    "Mean Cycle Time (Hari)": "Mean (hr)",
    "Mean Cycle Time (Jam)": "Mean (jam)",
    "Median Cycle Time (Hari)": "Median (hr)",
    "Jawaban Utama": "Hasil Utama",
}

TIMESTAMP_COLUMNS = {
    "start_timestamp",
    "end_timestamp",
    "time:timestamp",
    "first_complete_time",
    "last_complete_time",
    "cancelled_timestamp",
    "accepted_timestamp",
}

ISO_TS_REGEX = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)


def format_timestamp_compact(val_str: str) -> str:
    """Formats verbose ISO timestamps into compact 'YYYY-MM-DD HH:MM:SS'."""
    s = val_str.strip()
    m = ISO_TS_REGEX.match(s)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return s


def activity_color_hex(name: str) -> str:
    """Returns semantic color hex based on BPIC17 activity prefix (A_, O_, W_)."""
    s = str(name).strip()
    if s.startswith("O_"):
        return "#059669"
    if s.startswith("W_"):
        return "#4f46e5"
    if s.startswith("A_"):
        return "#2563eb"
    return "#475569"


APP_STYLESHEET = """
QMainWindow, QWidget#RootCanvas {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #334155;
}
QMenuBar::item {
    padding: 5px 10px;
    border-radius: 5px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px 6px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: #eff6ff;
    color: #1d4ed8;
}

/* Dark Slate Left Sidebar */
QFrame#Sidebar {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}
QLabel#BrandBadge {
    background-color: #4f46e5;
    color: #ffffff;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
}
QLabel#BrandTitle {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 700;
}
QLabel#BrandSub {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 500;
}
QLabel#NavSection {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.9px;
    padding: 8px 10px 2px 10px;
}
QPushButton#NavBtn {
    text-align: left;
    background-color: transparent;
    color: #cbd5e1;
    border: none;
    border-left: 3px solid transparent;
    border-radius: 6px;
    padding: 9px 12px;
    font-size: 12.5px;
    font-weight: 600;
}
QPushButton#NavBtn:hover {
    background-color: #1e293b;
    color: #ffffff;
}
QPushButton#NavBtn:checked {
    background-color: #1e293b;
    color: #ffffff;
    border-left: 3px solid #3b82f6;
    font-weight: 700;
}
QFrame#SidebarCard {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
}
QLabel#SidebarStatusTitle {
    color: #f1f5f9;
    font-size: 12px;
    font-weight: 700;
}
QLabel#SidebarStatusMeta {
    color: #94a3b8;
    font-size: 11px;
}
QPushButton#SidebarPrimaryBtn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #047857;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#SidebarPrimaryBtn:hover {
    background-color: #047857;
}
QPushButton#SidebarPrimaryBtn:disabled {
    background-color: #334155;
    color: #64748b;
    border-color: #334155;
}
QPushButton#SidebarGhostBtn {
    background-color: transparent;
    color: #cbd5e1;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11.5px;
    font-weight: 600;
}
QPushButton#SidebarGhostBtn:hover {
    background-color: #334155;
    color: #ffffff;
}
QPushButton#SidebarGhostBtn:disabled {
    color: #475569;
    border-color: #1e293b;
}

/* Top Workspace Context Bar */
QFrame#TopBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QLabel#PageTitle {
    color: #0f172a;
    font-size: 17px;
    font-weight: 700;
}
QLabel#PageRefPill {
    background-color: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#PageSub {
    color: #64748b;
    font-size: 12px;
}
QLabel#DatasetPill {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 11.5px;
    font-weight: 600;
}

/* Cards */
QFrame#SectionCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QLabel#SectionTitle {
    color: #0f172a;
    font-size: 13px;
    font-weight: 700;
}
QLabel#SectionSub {
    color: #64748b;
    font-size: 11.5px;
    font-weight: 500;
}
QFrame#SectionDivider {
    background-color: #f1f5f9;
    max-height: 1px;
    min-height: 1px;
}
QFrame#ToolbarCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}

/* Metric KPI Cards */
QFrame#MetricCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame#MetricCard QLabel {
    background-color: transparent;
}
QLabel#CardTitle {
    color: #64748b;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.4px;
}
QLabel#CardValue {
    color: #0f172a;
    font-size: 20px;
    font-weight: 800;
}
QLabel#CardSub {
    color: #475569;
    font-size: 11.5px;
    font-weight: 500;
}

/* Standard Buttons */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    border-radius: 6px;
    padding: 6px 13px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #cbd5e1;
}
QPushButton#SecondaryBtn {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#SecondaryBtn:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
    color: #0f172a;
}
QPushButton#SuccessBtn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #047857;
}
QPushButton#SuccessBtn:hover {
    background-color: #047857;
}

/* Inputs */
QLineEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #0f172a;
    font-size: 12px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}

/* Tables */
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e3a8a;
    font-size: 12px;
}
QTableView::item {
    padding: 3px 6px;
}
QTableCornerButton::section {
    background-color: #f8fafc;
    border: none;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
}
QHeaderView::section:horizontal {
    background-color: #f8fafc;
    color: #475569;
    padding: 7px 8px;
    border: none;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #cbd5e1;
    font-weight: 700;
    font-size: 11.5px;
}
QHeaderView::section:vertical {
    background-color: #ffffff;
    color: #94a3b8;
    padding: 0 6px;
    border: none;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #f1f5f9;
    font-size: 11px;
    font-weight: 600;
}
QTextBrowser {
    background-color: #ffffff;
    border: none;
    padding: 2px;
}
QSplitter::handle {
    background-color: #e2e8f0;
    border-radius: 2px;
}
QSplitter::handle:horizontal {
    width: 4px;
    margin: 2px 3px;
}
QSplitter::handle:vertical {
    height: 4px;
    margin: 3px 2px;
}
QSplitter::handle:hover {
    background-color: #3b82f6;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
    color: #475569;
    font-weight: 600;
    font-size: 11.5px;
    padding: 2px 8px;
}
"""


class DataFrameTableModel(QAbstractTableModel):
    """High-performance Qt TableModel backed by a pandas DataFrame (supports 31,509+ rows smoothly)."""

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        highlight_activities: Optional[List[str]] = None,
        highlight_lifecycle: Optional[str] = None,
        highlight_resource: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._source_df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self._df = self._source_df
        self.highlight_activities = [a.lower() for a in (highlight_activities or [])]
        self.highlight_lifecycle = highlight_lifecycle.lower() if highlight_lifecycle else None
        self.highlight_resource = highlight_resource.lower() if highlight_resource else None
        self._bold_font = QFont("Segoe UI", 9, QFont.Bold)
        self._filter_text: str = ""
        self._search_corpus: Optional[pd.Series] = None
        self._sort_col: int = -1
        self._sort_order: Qt.SortOrder = Qt.AscendingOrder
        self._col_names: List[str] = []
        self._col_arrays: List[np.ndarray] = []
        self._highlight_states: Optional[np.ndarray] = None
        self._apply_filter_and_sort()

    def set_dataframe(
        self,
        df: pd.DataFrame,
        highlight_activities: Optional[List[str]] = None,
        highlight_lifecycle: Optional[str] = None,
        highlight_resource: Optional[str] = None,
    ) -> None:
        self.beginResetModel()
        self._source_df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self.highlight_activities = [a.lower() for a in (highlight_activities or [])]
        self.highlight_lifecycle = highlight_lifecycle.lower() if highlight_lifecycle else None
        self.highlight_resource = highlight_resource.lower() if highlight_resource else None
        self._search_corpus = None
        self._sort_col = -1
        self._apply_filter_and_sort()
        self.endResetModel()

    def set_filter_text(self, text: str) -> None:
        needle = text.strip().lower()
        if needle == self._filter_text:
            return
        self.beginResetModel()
        self._filter_text = needle
        self._apply_filter_and_sort()
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if self._source_df.empty or column < 0 or column >= len(self._source_df.columns):
            return
        self.beginResetModel()
        self._sort_col = column
        self._sort_order = order
        self._apply_filter_and_sort()
        self.endResetModel()

    def _apply_filter_and_sort(self) -> None:
        if self._source_df.empty:
            self._df = self._source_df
            self._rebuild_cache()
            return

        if self._filter_text:
            if self._search_corpus is None:
                parts = [self._source_df[c].astype(str).str.lower() for c in self._source_df.columns]
                corpus = parts[0]
                for p in parts[1:]:
                    corpus = corpus.str.cat(p, sep="\t")
                self._search_corpus = corpus
            mask = self._search_corpus.str.contains(self._filter_text, regex=False, na=False)
            view = self._source_df.loc[mask]
        else:
            view = self._source_df

        if 0 <= self._sort_col < len(view.columns):
            col_key = view.columns[self._sort_col]
            asc = self._sort_order == Qt.AscendingOrder
            try:
                view = view.sort_values(by=col_key, ascending=asc, kind="mergesort", na_position="last")
            except TypeError:
                view = view.sort_values(
                    by=col_key,
                    ascending=asc,
                    kind="mergesort",
                    na_position="last",
                    key=lambda s: s.astype(str),
                )

        if view is self._source_df:
            self._df = view
        else:
            self._df = view.reset_index(drop=True)
        self._rebuild_cache()

    def _rebuild_cache(self) -> None:
        self._col_names = [str(c) for c in self._df.columns]
        self._col_arrays = [self._df[c].to_numpy() for c in self._df.columns]
        if not self.highlight_activities or self._df.empty or "concept:name" not in self._df.columns:
            self._highlight_states = None
            return

        act_arr = self._df["concept:name"].to_numpy()
        act_match = np.array(
            [str(v).strip().lower() in self.highlight_activities for v in act_arr],
            dtype=bool,
        )
        if not act_match.any():
            self._highlight_states = np.zeros(len(self._df), dtype=np.int8)
            return

        exact_mask = act_match.copy()
        if self.highlight_lifecycle and "lifecycle:transition" in self._df.columns:
            lc_arr = self._df["lifecycle:transition"].to_numpy()
            exact_mask &= np.array(
                [str(v).strip().lower() == self.highlight_lifecycle for v in lc_arr],
                dtype=bool,
            )
        if self.highlight_resource and "org:resource" in self._df.columns:
            res_arr = self._df["org:resource"].to_numpy()
            exact_mask &= np.array(
                [str(v).strip().lower() == self.highlight_resource for v in res_arr],
                dtype=bool,
            )

        states = np.zeros(len(self._df), dtype=np.int8)
        states[act_match] = 1
        states[exact_mask] = 2
        self._highlight_states = states

    def get_dataframe(self) -> pd.DataFrame:
        return self._df

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._col_names)

    def _row_highlight_state(self, row: int) -> int:
        """Returns 2 for exact target match (amber), 1 for partial activity match (soft blue), 0 otherwise."""
        if self._highlight_states is None:
            return 0
        return int(self._highlight_states[row])

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or self._df.empty:
            return None

        row = index.row()
        col = index.column()
        col_name = self._col_names[col]
        val = self._col_arrays[col][row]

        if role == Qt.DisplayRole:
            if pd.isna(val):
                return "-"
            if isinstance(val, (bool, np.bool_)):
                return "Ya" if val else "Tidak"
            if isinstance(val, (float, np.floating)):
                f_val = float(val)
                if "percentage" in col_name or "_pct" in col_name or "(%)" in col_name:
                    return f"{f_val:,.2f}%" if abs(f_val) >= 1.0 or f_val == 0 else f"{f_val:,.4f}%"
                if "hours" in col_name or "(Jam)" in col_name:
                    return f"{f_val:,.2f}"
                if "seconds" in col_name:
                    return f"{f_val:,.1f}"
                return f"{f_val:,.4f}"
            if isinstance(val, (int, np.integer)):
                return f"{int(val):,}"
            s_val = str(val)
            if col_name in TIMESTAMP_COLUMNS:
                return format_timestamp_compact(s_val)
            return s_val

        if role == Qt.ToolTipRole:
            if pd.isna(val):
                return "-"
            return f"{COLUMN_HEADER_MAP.get(col_name, col_name)}: {val}"

        if role == Qt.BackgroundRole:
            hl = self._row_highlight_state(row)
            if hl == 2:
                return QColor("#fef3c7")
            if hl == 1:
                return QColor("#eff6ff")
            if col_name == "Jawaban Utama":
                return QColor("#ecfdf5")
            if col_name == "Kode Soal":
                return QColor("#f8fafc")

        if role == Qt.ForegroundRole:
            hl = self._row_highlight_state(row)
            if hl == 2:
                return QColor("#92400e")
            if hl == 1:
                return QColor("#1e40af")
            if col_name == "Jawaban Utama":
                return QColor("#065f46")
            if col_name in ("Kode Soal", "case_id", "case:concept:name"):
                return QColor("#1e3a8a")
            if col_name in ("concept:name", "activity") and not pd.isna(val):
                return QColor(activity_color_hex(str(val)))
            if col_name == "lifecycle:transition" and not pd.isna(val):
                lc_v = str(val).strip().lower()
                if lc_v == "complete":
                    return QColor("#047857")
                if lc_v in ("ate_abort", "withdraw"):
                    return QColor("#b91c1c")
                if lc_v in ("schedule", "start"):
                    return QColor("#2563eb")
            return QColor("#0f172a")

        if role == Qt.FontRole:
            if self._row_highlight_state(row) == 2:
                return self._bold_font
            if col_name in ("Jawaban Utama", "Kode Soal", "case_id"):
                return self._bold_font

        if role == Qt.TextAlignmentRole:
            if col_name in (
                "Kode Soal",
                "_trace_pos",
                "cancelled_trace_pos",
                "accepted_trace_pos",
                "intervening_events_count",
                "same_offer_id",
            ):
                return int(Qt.AlignCenter)
            if isinstance(val, (int, float, np.integer, np.floating)) and not isinstance(val, (bool, np.bool_)) and not pd.isna(val):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if self._df.empty:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._col_names):
                raw_col = self._col_names[section]
                if role == Qt.DisplayRole:
                    return COLUMN_HEADER_MAP.get(raw_col, raw_col)
                if role == Qt.ToolTipRole:
                    return f"Attribute: {raw_col}"
        else:
            if role == Qt.DisplayRole:
                return str(section + 1)
        return None


class MetricCard(QFrame):
    """Minimalist KPI card with a clean 3px accent strip and clear typography."""

    def __init__(self, title: str, value: str = "-", subtitle: str = "", border_color: str = "#2563eb"):
        super().__init__()
        self.setObjectName("MetricCard")
        self._accent = border_color
        self.setStyleSheet(
            f"QFrame#MetricCard {{ "
            f"background-color: #ffffff; "
            f"border: 1px solid #e2e8f0; "
            f"border-left: 3px solid {border_color}; "
            f"border-radius: 10px; "
            f"}}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setObjectName("CardTitle")
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("CardValue")
        self.lbl_value.setWordWrap(True)
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("CardSub")
        self.lbl_sub.setStyleSheet(f"color: {border_color}; font-size: 11.5px; font-weight: 600;")
        self.lbl_sub.setWordWrap(True)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_sub)

    def update_card(self, value: str, subtitle: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)


class SectionCard(QFrame):
    """Clean white card container replacing legacy QGroupBox borders."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        header_right: Optional[QWidget] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 11, 14, 12)
        root.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("SectionTitle")
        title_col.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel(subtitle)
        self.lbl_subtitle.setObjectName("SectionSub")
        self.lbl_subtitle.setVisible(bool(subtitle))
        title_col.addWidget(self.lbl_subtitle)

        hdr.addLayout(title_col, stretch=1)
        if header_right is not None:
            hdr.addWidget(header_right)
        root.addLayout(hdr)

        divider = QFrame()
        divider.setObjectName("SectionDivider")
        root.addWidget(divider)

        self.body_layout = QVBoxLayout()
        self.body_layout.setContentsMargins(0, 2, 0, 0)
        self.body_layout.setSpacing(8)
        root.addLayout(self.body_layout, stretch=1)

    def set_subtitle(self, subtitle: str) -> None:
        self.lbl_subtitle.setText(subtitle)
        self.lbl_subtitle.setVisible(bool(subtitle))


class SegmentedRatioBarWidget(QWidget):
    """Custom QPainter horizontal stacked proportion bar with crisp legend items."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._segments: List[Tuple[str, float, str, str]] = []
        self.setMinimumHeight(46)
        self.setMaximumHeight(54)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_segments(self, segments: List[Tuple[str, float, str, str]]) -> None:
        self._segments = segments
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        bar_x = 2.0
        bar_y = 4.0
        bar_w = max(w - 4.0, 20.0)
        bar_h = 12.0

        # Track background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#f1f5f9")))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 6.0, 6.0)

        if not self._segments:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 8.5))
            painter.drawText(QRectF(bar_x, 22.0, bar_w, 20.0), Qt.AlignLeft | Qt.AlignVCenter, "Load a dataset to view distribution.")
            return

        total_pct = sum(max(0.0, s[1]) for s in self._segments)
        norm = total_pct if total_pct > 0 else 100.0

        # Draw proportional segments clipped inside rounded bar
        cur_x = bar_x
        visible_segs = [s for s in self._segments if s[1] > 0]
        for idx, (label, pct, color_hex, detail) in enumerate(visible_segs):
            seg_w = (max(0.0, pct) / norm) * bar_w
            if idx == len(visible_segs) - 1:
                seg_w = max(0.0, bar_x + bar_w - cur_x)
            else:
                seg_w = max(seg_w, 3.0)
            painter.setBrush(QBrush(QColor(color_hex)))
            if idx == 0 and len(visible_segs) == 1:
                painter.drawRoundedRect(QRectF(cur_x, bar_y, seg_w, bar_h), 6.0, 6.0)
            elif idx == 0:
                painter.drawRoundedRect(QRectF(cur_x, bar_y, seg_w + 5.0, bar_h), 6.0, 6.0)
                painter.drawRect(QRectF(cur_x + seg_w - 2.0, bar_y, 2.0, bar_h))
            elif idx == len(visible_segs) - 1:
                painter.drawRoundedRect(QRectF(cur_x - 5.0, bar_y, seg_w + 5.0, bar_h), 6.0, 6.0)
                painter.drawRect(QRectF(cur_x, bar_y, 4.0, bar_h))
            else:
                painter.drawRect(QRectF(cur_x, bar_y, seg_w, bar_h))
            # 1.5px white separator between segments
            if idx < len(visible_segs) - 1:
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawRect(QRectF(cur_x + seg_w - 1.5, bar_y, 1.5, bar_h))
            cur_x += seg_w

        # Draw legend items beneath bar
        legend_y = 24.0
        lx = 2.0
        font_lbl = QFont("Segoe UI", 8.5, QFont.DemiBold)
        font_det = QFont("Segoe UI", 8.5)
        fm_lbl = QFontMetrics(font_lbl)
        fm_det = QFontMetrics(font_det)

        for label, pct, color_hex, detail in self._segments:
            txt_head = f"{label}: "
            txt_tail = f"{detail}"
            need_w = 14.0 + fm_lbl.horizontalAdvance(txt_head) + fm_det.horizontalAdvance(txt_tail) + 16.0
            if lx + need_w > w and lx > 10.0:
                break
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.drawEllipse(QRectF(lx, legend_y + 4.5, 8.0, 8.0))
            lx += 13.0

            painter.setFont(font_lbl)
            painter.setPen(QColor("#334155"))
            w_h = fm_lbl.horizontalAdvance(txt_head)
            painter.drawText(QRectF(lx, legend_y, w_h + 2, 18.0), Qt.AlignLeft | Qt.AlignVCenter, txt_head)
            lx += w_h

            painter.setFont(font_det)
            painter.setPen(QColor("#64748b"))
            w_t = fm_det.horizontalAdvance(txt_tail)
            painter.drawText(QRectF(lx, legend_y, w_t + 2, 18.0), Qt.AlignLeft | Qt.AlignVCenter, txt_tail)
            lx += w_t + 16.0


class HorizontalBarChartWidget(QWidget):
    """Custom QPainter horizontal bar chart for activity volumes or cycle time comparisons."""

    def __init__(self, row_height: int = 24, label_width: int = 160, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: List[Tuple[str, float, str, str]] = []
        self._max_val: Optional[float] = None
        self._row_height = row_height
        self._label_width = label_width
        self.setMinimumHeight(row_height * 4 + 8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_bars(self, items: List[Tuple[str, float, str, str]], max_val: Optional[float] = None) -> None:
        self._items = items
        self._max_val = max_val
        h = max(len(items) * self._row_height + 8, self._row_height * 3)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = float(self.width())
        if not self._items:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 8.5))
            painter.drawText(QRectF(4, 4, w - 8, float(self.height()) - 8), Qt.AlignCenter, "No chart data loaded yet.")
            return

        max_v = self._max_val if self._max_val and self._max_val > 0 else max((max(0.0, it[1]) for it in self._items), default=1.0)
        if max_v <= 0:
            max_v = 1.0

        val_col_w = 104.0
        lbl_w = min(float(self._label_width), w * 0.42)
        track_x = lbl_w + 8.0
        track_w = max(w - track_x - val_col_w - 8.0, 40.0)

        font_lbl = QFont("Segoe UI", 8.5, QFont.DemiBold)
        font_val = QFont("Segoe UI", 8.5, QFont.Bold)
        fm_lbl = QFontMetrics(font_lbl)

        for idx, (label, val, fmt_val, color_hex) in enumerate(self._items):
            y = 4.0 + idx * self._row_height
            # Label (elided if long)
            painter.setFont(font_lbl)
            painter.setPen(QColor("#334155"))
            elided = fm_lbl.elidedText(label, Qt.ElideRight, int(lbl_w))
            painter.drawText(QRectF(2.0, y, lbl_w, float(self._row_height)), Qt.AlignLeft | Qt.AlignVCenter, elided)

            # Track bar
            bar_h = 10.0
            bar_y = y + (self._row_height - bar_h) / 2.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#f1f5f9")))
            painter.drawRoundedRect(QRectF(track_x, bar_y, track_w, bar_h), 5.0, 5.0)

            # Value bar
            ratio = min(1.0, max(0.0, val / max_v))
            fill_w = max(ratio * track_w, 4.0 if val > 0 else 0.0)
            if fill_w > 0:
                painter.setBrush(QBrush(QColor(color_hex)))
                painter.drawRoundedRect(QRectF(track_x, bar_y, fill_w, bar_h), 5.0, 5.0)

            # Right formatted value
            painter.setFont(font_val)
            painter.setPen(QColor("#0f172a"))
            painter.drawText(
                QRectF(track_x + track_w + 8.0, y, val_col_w - 4.0, float(self._row_height)),
                Qt.AlignRight | Qt.AlignVCenter,
                fmt_val,
            )


class TraceFlowStripWidget(QFrame):
    """Visual horizontal milestone strip showing key steps in a selected trace."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setFixedHeight(38)
        self.setStyleSheet(
            "QFrame { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }"
        )
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(10, 5, 10, 5)
        self._layout.setSpacing(5)
        self.set_placeholder("Select a case to preview its milestone trace sequence.")

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def set_placeholder(self, text: str) -> None:
        self._clear()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #64748b; font-size: 11.5px; border: none; background: transparent;")
        self._layout.addWidget(lbl)
        self._layout.addStretch(1)

    def set_events(self, ev_df: pd.DataFrame, highlight_activities: Optional[List[str]] = None) -> None:
        self._clear()
        if ev_df.empty or "concept:name" not in ev_df.columns:
            self.set_placeholder("No trace events available.")
            return

        hl_set = {a.lower() for a in (highlight_activities or [])}
        rows = list(ev_df.iterrows())
        chosen_idx: List[int] = [0]
        # Prefer highlighted evidence events first, then key offer milestones (max 5 pills total)
        for i in range(1, len(rows) - 1):
            act = str(rows[i][1]["concept:name"])
            if act.lower() in hl_set and len(chosen_idx) < 4:
                chosen_idx.append(i)
        if len(chosen_idx) < 4:
            for i in range(1, len(rows) - 1):
                act = str(rows[i][1]["concept:name"])
                if act.startswith("O_") and i not in chosen_idx and len(chosen_idx) < 4:
                    chosen_idx.append(i)
        if len(rows) > 1:
            chosen_idx.append(len(rows) - 1)
        chosen_idx = sorted(set(chosen_idx))

        for k, pos in enumerate(chosen_idx):
            if k > 0:
                gap = pos - chosen_idx[k - 1] - 1
                arrow_txt = f"→ +{gap} →" if gap > 0 else "→"
                arr = QLabel(arrow_txt)
                arr.setStyleSheet("color: #94a3b8; font-size: 10.5px; font-weight: 700; border: none; background: transparent;")
                self._layout.addWidget(arr)

            row_data = rows[pos][1]
            act_name = str(row_data["concept:name"])
            short_act = act_name if len(act_name) <= 17 else f"{act_name[:15]}…"
            is_hl = act_name.lower() in hl_set
            c_hex = activity_color_hex(act_name)
            pill = QLabel(f"#{int(row_data.get('_trace_pos', pos + 1))} {short_act}")
            pill.setToolTip(f"Pos #{int(row_data.get('_trace_pos', pos + 1))}: {act_name}")
            if is_hl:
                pill.setStyleSheet(
                    "background-color: #fef3c7; color: #92400e; border: 1px solid #f59e0b; "
                    "border-radius: 5px; padding: 2px 7px; font-size: 11px; font-weight: 700;"
                )
            else:
                pill.setStyleSheet(
                    f"background-color: #ffffff; color: {c_hex}; border: 1px solid #cbd5e1; "
                    f"border-radius: 5px; padding: 2px 7px; font-size: 11px; font-weight: 600;"
                )
            self._layout.addWidget(pill)

        self._layout.addStretch(1)


@dataclass
class FullAnalysisBundle:
    """Holds all computed outputs from a background worker run."""
    context: EventLogContext
    report: ValidationReport
    overview: OverviewResult
    ex117: Exercise117Result
    ex1115: Exercise1115Result
    ex1118: Exercise1118Result
    ex1122: Exercise1122Result


class AnalysisWorker(QThread):
    """Background worker thread so XES import and analysis never freeze the desktop UI."""

    progress_changed = Signal(str)
    finished_bundle = Signal(object)
    failed_error = Signal(str)

    def __init__(self, file_path: str, existing_context: Optional[EventLogContext] = None):
        super().__init__()
        self.file_path = file_path
        self.existing_context = existing_context

    def run(self) -> None:
        try:
            if self.existing_context is None:
                ctx, report = load_and_validate_xes(
                    self.file_path, progress_callback=self.progress_changed.emit
                )
                if not report.is_valid or ctx is None:
                    self.failed_error.emit(report.error_message or "Gagal memvalidasi berkas XES.")
                    return
            else:
                ctx = self.existing_context
                report = ctx.report

            self.progress_changed.emit("Menjalankan F02: Event Log Overview & Statistika Dasar...")
            ov = analyze_overview(ctx)

            self.progress_changed.emit("Menjalankan F03: Analisis Exercise 11.7 (A–E)...")
            r117 = analyze_exercise_11_7(ctx)

            self.progress_changed.emit("Menjalankan F04: Analisis Exercise 11.15 (Repeated Complete)...")
            r1115 = analyze_exercise_11_15(ctx)

            self.progress_changed.emit("Menjalankan F05: Analisis Exercise 11.18 (Same Resource)...")
            r1118 = analyze_exercise_11_18(ctx, res_1115=r1115)

            self.progress_changed.emit("Menjalankan F06: Analisis Exercise 11.22 (Eventually Follows)...")
            r1122 = analyze_exercise_11_22(ctx)

            bundle = FullAnalysisBundle(
                context=ctx,
                report=report,
                overview=ov,
                ex117=r117,
                ex1115=r1115,
                ex1118=r1118,
                ex1122=r1122,
            )
            self.progress_changed.emit("Analisis selesai.")
            self.finished_bundle.emit(bundle)
        except Exception as exc:
            tb = traceback.format_exc()
            self.failed_error.emit(f"Terjadi kesalahan saat memproses event log:\n{exc}\n\n{tb}")


PAGE_METADATA: List[Tuple[str, str, str]] = [
    ("Data Source & Schema", "Schema • F01", "Impor event log XES, validasi atribut wajib, serta pemeriksaan struktur trace."),
    ("Process Overview", "Overview • F02", "Distribusi volume aktivitas (A_, O_, W_), performa SLA, dan durasi per aplikasi."),
    ("Outcomes & Cycle Time", "Ref: 11.7 A–E", "Perbandingan aplikasi berhasil (O_Accepted), ditolak (O_Refused), dan dibatalkan di akhir trace."),
    ("Fraud Rework & Audit", "Ref: 11.15 & 11.18", "Deteksi pengulangan W_Assess potential fraud berstatus complete dan audit kepatuhan resource."),
    ("Offer Re-Acceptance", "Ref: 11.22", "Pelacakan pola sekuensial O_Cancelled yang diikuti O_Accepted (level trace & OfferID)."),
    ("Trace Explorer", "Trace Audit • F07", "Inspeksi urutan event per case dengan visualisasi alur milestone dan sorotan bukti."),
    ("Summary & Export", "Export • 8 KPIs", "Konsolidasi seluruh metrik utama dan ekspor paket laporan CSV & HTML."),
]


class MainWindow(QMainWindow):
    """Main Desktop GUI Window for ProcessMine Studio (BPIC17 Loan Process Analytics)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProcessMine Studio — Loan Application Process Mining (BPIC17)")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 760)
        self.setStyleSheet(APP_STYLESHEET)

        self.bundle: Optional[FullAnalysisBundle] = None
        self.worker: Optional[AnalysisWorker] = None
        self._nav_buttons: List[QPushButton] = []

        self._init_menubar()
        self._init_ui()
        self.switch_page(0)

    @staticmethod
    def _configure_table(
        table: QTableView,
        stretch_last: bool = True,
        word_wrap: bool = False,
        row_height: int = 28,
        interactive_columns: bool = False,
    ) -> None:
        """Applies consistent modern table styling, smooth scrolling, and column sizing."""
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setWordWrap(word_wrap)
        table.setShowGrid(True)
        vh = table.verticalHeader()
        vh.setDefaultSectionSize(row_height)
        vh.setMinimumSectionSize(24)
        hh = table.horizontalHeader()
        if interactive_columns:
            hh.setSectionResizeMode(QHeaderView.Interactive)
            hh.setDefaultSectionSize(125)
            hh.setMinimumSectionSize(60)
        else:
            hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(stretch_last)
        hh.setHighlightSections(False)

    @staticmethod
    def _apply_column_widths(
        table: QTableView,
        df: pd.DataFrame,
        width_map: Dict[str, int],
        default_width: int = 120,
    ) -> None:
        if df.empty:
            return
        for i, col_name in enumerate(df.columns):
            table.setColumnWidth(i, width_map.get(str(col_name), default_width))

    def _init_menubar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&Berkas")
        act_open = QAction("Impor File XES (.xes / .xes.gz)...", self)
        act_open.triggered.connect(self.on_browse_xes)
        file_menu.addAction(act_open)

        act_bpic = QAction("Muat Dataset Utama BPIC17 (BPI Challenge 2017.xes.gz)", self)
        act_bpic.triggered.connect(self.on_load_default_bpic17)
        file_menu.addAction(act_bpic)

        act_syn = QAction("Muat Log Sintetis Pengujian Edge Cases (10 Case)", self)
        act_syn.triggered.connect(self.on_load_synthetic_log)
        file_menu.addAction(act_syn)

        file_menu.addSeparator()
        act_export = QAction("Ekspor Semua Hasil ke Folder (CSV && HTML)...", self)
        act_export.triggered.connect(self.on_export_all)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_exit = QAction("Keluar", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        help_menu = menubar.addMenu("&Bantuan")
        act_about = QAction("Tentang Aplikasi && Versi Dependency (Reproducibility)", self)
        act_about.triggered.connect(self.on_show_about)
        help_menu.addAction(act_about)

    def _init_ui(self) -> None:
        central = QWidget()
        central.setObjectName("RootCanvas")
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Dark Slate Navigation Sidebar
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        # 2. Right Workspace Container (Top Bar + Stacked Pages)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        top_bar = self._build_topbar()
        right_layout.addWidget(top_bar)

        content_wrap = QWidget()
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(18, 14, 18, 12)
        content_layout.setSpacing(10)

        self.pages = QStackedWidget()
        content_layout.addWidget(self.pages, stretch=1)
        right_layout.addWidget(content_wrap, stretch=1)

        root_layout.addWidget(right_panel, stretch=1)

        # Build the 7 functional workspace pages
        self._build_page_f01_dataset()
        self._build_page_f02_overview()
        self._build_page_f03_ex117()
        self._build_page_f04_f05_ex1115_1118()
        self._build_page_f06_ex1122()
        self._build_page_f07_case_explorer()
        self._build_page_f07_export()

        # Bottom Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(240)
        self.progress_bar.setMaximumHeight(14)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready. Select BPIC17 dataset or import an XES file to begin.")

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(228)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 14)
        sb_layout.setSpacing(4)

        # Brand Header
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        badge = QLabel("PM")
        badge.setObjectName("BrandBadge")
        badge.setFixedSize(34, 34)
        badge.setAlignment(Qt.AlignCenter)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        lbl_brand = QLabel("ProcessMine")
        lbl_brand.setObjectName("BrandTitle")
        lbl_sub = QLabel("Loan Process Analytics")
        lbl_sub.setObjectName("BrandSub")
        brand_text.addWidget(lbl_brand)
        brand_text.addWidget(lbl_sub)

        brand_row.addWidget(badge)
        brand_row.addLayout(brand_text, stretch=1)
        sb_layout.addLayout(brand_row)
        sb_layout.addSpacing(12)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        def add_section(text: str) -> None:
            lbl = QLabel(text)
            lbl.setObjectName("NavSection")
            sb_layout.addWidget(lbl)

        def add_nav(idx: int, label: str) -> None:
            btn = QPushButton(label)
            btn.setObjectName("NavBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked, i=idx: self.switch_page(i))
            self._nav_group.addButton(btn, idx)
            self._nav_buttons.append(btn)
            sb_layout.addWidget(btn)

        add_section("WORKSPACE")
        add_nav(0, "Data Source && Schema")
        add_nav(1, "Process Overview")

        add_section("PROCESS ANALYTICS")
        add_nav(2, "Outcomes && Cycle Time")
        add_nav(3, "Fraud Rework && Audit")
        add_nav(4, "Offer Re-Acceptance")
        add_nav(5, "Trace Explorer")

        add_section("REPORTING")
        add_nav(6, "Summary && Export")

        sb_layout.addStretch(1)

        # Bottom Quick-Load Dataset Card
        ds_card = QFrame()
        ds_card.setObjectName("SidebarCard")
        ds_layout = QVBoxLayout(ds_card)
        ds_layout.setContentsMargins(10, 10, 10, 10)
        ds_layout.setSpacing(6)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self._lbl_sidebar_dot = QLabel("●")
        self._lbl_sidebar_dot.setStyleSheet("color: #f59e0b; font-size: 11px;")
        self._lbl_sidebar_ds_name = QLabel("No dataset loaded")
        self._lbl_sidebar_ds_name.setObjectName("SidebarStatusTitle")
        self._lbl_sidebar_ds_name.setWordWrap(True)
        status_row.addWidget(self._lbl_sidebar_dot)
        status_row.addWidget(self._lbl_sidebar_ds_name, stretch=1)
        ds_layout.addLayout(status_row)

        self._lbl_sidebar_ds_meta = QLabel("Load BPIC17 or synthetic log")
        self._lbl_sidebar_ds_meta.setObjectName("SidebarStatusMeta")
        ds_layout.addWidget(self._lbl_sidebar_ds_meta)

        self.btn_top_bpic = QPushButton("Load BPIC17 Dataset")
        self.btn_top_bpic.setObjectName("SidebarPrimaryBtn")
        self.btn_top_bpic.setCursor(Qt.PointingHandCursor)
        self.btn_top_bpic.clicked.connect(self.on_load_default_bpic17)
        ds_layout.addWidget(self.btn_top_bpic)

        self.btn_top_synth = QPushButton("Load Synthetic Test Log")
        self.btn_top_synth.setObjectName("SidebarGhostBtn")
        self.btn_top_synth.setCursor(Qt.PointingHandCursor)
        self.btn_top_synth.clicked.connect(self.on_load_synthetic_log)
        ds_layout.addWidget(self.btn_top_synth)

        sb_layout.addWidget(ds_card)
        return sidebar

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(64)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(18, 8, 18, 8)
        tb_layout.setSpacing(10)

        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.lbl_page_title = QLabel("Data Source & Schema")
        self.lbl_page_title.setObjectName("PageTitle")
        self.lbl_page_ref = QLabel("Schema • F01")
        self.lbl_page_ref.setObjectName("PageRefPill")
        title_row.addWidget(self.lbl_page_title)
        title_row.addWidget(self.lbl_page_ref)
        title_row.addStretch(1)

        self.lbl_page_subtitle = QLabel("")
        self.lbl_page_subtitle.setObjectName("PageSub")
        left_col.addLayout(title_row)
        left_col.addWidget(self.lbl_page_subtitle)
        tb_layout.addLayout(left_col, stretch=1)

        self.lbl_active_dataset = QLabel("Idle • No XES Loaded")
        self.lbl_active_dataset.setObjectName("DatasetPill")
        tb_layout.addWidget(self.lbl_active_dataset)

        self.btn_top_rerun = QPushButton("Re-run")
        self.btn_top_rerun.setObjectName("SecondaryBtn")
        self.btn_top_rerun.setEnabled(False)
        self.btn_top_rerun.setCursor(Qt.PointingHandCursor)
        self.btn_top_rerun.clicked.connect(self.on_rerun_all)
        tb_layout.addWidget(self.btn_top_rerun)

        self.btn_top_import = QPushButton("Import XES...")
        self.btn_top_import.setCursor(Qt.PointingHandCursor)
        self.btn_top_import.clicked.connect(self.on_browse_xes)
        tb_layout.addWidget(self.btn_top_import)

        self.btn_top_export = QPushButton("Export")
        self.btn_top_export.setObjectName("SecondaryBtn")
        self.btn_top_export.setCursor(Qt.PointingHandCursor)
        self.btn_top_export.clicked.connect(self.on_export_all)
        tb_layout.addWidget(self.btn_top_export)

        return topbar

    def switch_page(self, index: int) -> None:
        """Switches the active workspace page and updates sidebar & top-bar context."""
        if not (0 <= index < self.pages.count()):
            return
        self.pages.setCurrentIndex(index)
        if 0 <= index < len(self._nav_buttons):
            self._nav_buttons[index].setChecked(True)
        title, ref_tag, subtitle = PAGE_METADATA[index]
        self.lbl_page_title.setText(title)
        self.lbl_page_ref.setText(ref_tag)
        self.lbl_page_subtitle.setText(subtitle)
        if index == 6:
            QTimer.singleShot(0, self._resize_summary_table_columns)

    # ------------------------------------------------------------------
    # PAGE 0: F01 — Data Source & Schema Validation
    # ------------------------------------------------------------------
    def _build_page_f01_dataset(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)
        self.card_f01_status = MetricCard("Ingestion Status", "Idle", "Select .xes / .xes.gz file", "#2563eb")
        self.card_f01_cases = MetricCard("Unique Cases (Traces)", "-", "Attribute: case:concept:name", "#059669")
        self.card_f01_events = MetricCard("Total Process Events", "-", "Event rows in active log", "#4f46e5")
        self.card_f01_attrs = MetricCard("Schema Readiness", "-", "lifecycle:transition & org:resource", "#d97706")
        for c in (self.card_f01_status, self.card_f01_cases, self.card_f01_events, self.card_f01_attrs):
            cards_layout.addWidget(c)
        layout.addLayout(cards_layout)

        card_detail = SectionCard(
            "Event Log Schema & Validation Diagnostics",
            "Validates mandatory XES attributes, trace order determinism, and runtime reproducibility",
        )
        self.txt_f01_validation = QTextBrowser()
        self.txt_f01_validation.setOpenExternalLinks(True)
        env = get_environment_info()
        self.txt_f01_validation.setHtml(f"""
        <div style="font-family:'Segoe UI',sans-serif;color:#0f172a;padding:6px;line-height:1.6;">
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px 18px;margin-bottom:14px;">
            <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:4px;">Welcome to ProcessMine Studio</div>
            <div style="color:#475569;font-size:13px;">
              Load a loan application event log from the sidebar or top bar to inspect trace schemas, analyze process outcomes, audit fraud rework, and export reproducible evidence.
            </div>
          </div>
          <table width="100%" cellspacing="10" cellpadding="0">
            <tr>
              <td width="33%" valign="top" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;">
                <div style="font-size:11px;font-weight:700;color:#059669;">STEP 1 • LOAD DATASET</div>
                <div style="font-weight:700;margin:4px 0;">BPI Challenge 2017</div>
                <div style="color:#64748b;font-size:12px;">Click <b>Load BPIC17 Dataset</b> in the left sidebar to analyze <code>BPI Challenge 2017.xes.gz</code> (31,509 traces).</div>
              </td>
              <td width="33%" valign="top" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;">
                <div style="font-size:11px;font-weight:700;color:#2563eb;">STEP 2 • CUSTOM XES</div>
                <div style="font-weight:700;margin:4px 0;">Import Any XES Log</div>
                <div style="color:#64748b;font-size:12px;">Click <b>Import XES...</b> in the top bar to validate and mine any <code>.xes</code> or <code>.xes.gz</code> event log.</div>
              </td>
              <td width="33%" valign="top" style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;">
                <div style="font-size:11px;font-weight:700;color:#4f46e5;">STEP 3 • EDGE-CASE SUITE</div>
                <div style="font-weight:700;margin:4px 0;">Synthetic Validation Log</div>
                <div style="color:#64748b;font-size:12px;">Click <b>Load Synthetic Test Log</b> to inspect the 10-case verification suite covering all 8 edge scenarios.</div>
              </td>
            </tr>
          </table>
          <div style="margin-top:14px;padding:10px 14px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:12px;color:#475569;">
            <b>Runtime Environment:</b> Python <code>{env['Python']}</code> &bull; PM4Py <code>{env['PM4Py']}</code> &bull;
            Pandas <code>{env['Pandas']}</code> &bull; PySide6 <code>{env['PySide6']}</code> &bull; r4pm <code>{env['r4pm (XES accelerator)']}</code>
          </div>
        </div>
        """)
        card_detail.body_layout.addWidget(self.txt_f01_validation)
        layout.addWidget(card_detail, stretch=1)
        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 1: F02 — Process Overview & Activity Volumes
    # ------------------------------------------------------------------
    def _build_page_f02_overview(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_f02_cases = MetricCard("Total Applications (Cases)", "-", "Unique traces in log", "#2563eb")
        self.card_f02_events = MetricCard("Total Process Events", "-", "Unique activities & resources", "#4f46e5")
        self.card_f02_meandur = MetricCard("Mean Cycle Time", "-", "Days, hours & median", "#059669")
        self.card_f02_fastslow = MetricCard("SLA Performance (< 45d)", "-", "Fast vs Slow benchmark", "#d97706")
        for c in (self.card_f02_cases, self.card_f02_events, self.card_f02_meandur, self.card_f02_fastslow):
            cards.addWidget(c)
        layout.addLayout(cards)

        # Compact SLA distribution strip with time range pill
        self.lbl_f02_timerange = QLabel("Time Span: -")
        self.lbl_f02_timerange.setStyleSheet(
            "background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 5px; "
            "font-size: 11px; font-weight: 600; color: #334155; padding: 3px 9px;"
        )
        sla_card = SectionCard(
            "Case Speed Distribution (< 45d Fast vs >= 45d Slow)",
            header_right=self.lbl_f02_timerange,
        )
        sla_card.setMaximumHeight(112)
        self.chart_f02_sla = SegmentedRatioBarWidget()
        sla_card.body_layout.addWidget(self.chart_f02_sla)
        layout.addWidget(sla_card)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Activity Chart + Activity Frequency Table
        card_act = SectionCard("Activity Volume & Frequency", "Color-coded by stage: A_ Application (Blue) • O_ Offer (Green) • W_ Workflow (Indigo)")
        self.chart_f02_activities = HorizontalBarChartWidget(row_height=22, label_width=155)
        card_act.body_layout.addWidget(self.chart_f02_activities)

        self.model_f02_act = DataFrameTableModel()
        self.table_f02_act = QTableView()
        self.table_f02_act.setModel(self.model_f02_act)
        self._configure_table(self.table_f02_act, stretch_last=True, row_height=28)
        card_act.body_layout.addWidget(self.table_f02_act, stretch=1)
        splitter.addWidget(card_act)

        # Right: Application Case Explorer
        search_bar_widget = QWidget()
        sb = QHBoxLayout(search_bar_widget)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(6)
        self.txt_f02_search = QLineEdit()
        self.txt_f02_search.setPlaceholderText("Filter Case ID or activity...")
        self.txt_f02_search.setMinimumWidth(220)
        self.txt_f02_search.textChanged.connect(self._on_filter_f02_cases)
        btn_inspect_f02 = QPushButton("Inspect Trace")
        btn_inspect_f02.setCursor(Qt.PointingHandCursor)
        btn_inspect_f02.clicked.connect(self._on_inspect_from_f02)
        sb.addWidget(self.txt_f02_search)
        sb.addWidget(btn_inspect_f02)

        card_cases = SectionCard(
            "Application Case Explorer",
            "Double-click any case row to open its full event sequence",
            header_right=search_bar_widget,
        )
        self.model_f02_cases = DataFrameTableModel()

        self.table_f02_cases = QTableView()
        self.table_f02_cases.setModel(self.model_f02_cases)
        self._configure_table(self.table_f02_cases, stretch_last=True, interactive_columns=True)
        # Sembunyikan vertical header agar tidak menampilkan nomor baris acak saat disortir
        self.table_f02_cases.verticalHeader().setVisible(False)
        self.table_f02_cases.setSortingEnabled(True)
        self.table_f02_cases.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table_f02_cases.doubleClicked.connect(lambda _: self._on_inspect_from_f02())
        card_cases.body_layout.addWidget(self.table_f02_cases, stretch=1)
        splitter.addWidget(card_cases)
        splitter.setSizes([540, 640])

        layout.addWidget(splitter, stretch=1)
        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 2: F03 — Outcomes & Cycle Time (Ref: 11.7 A–E)
    # ------------------------------------------------------------------
    def _build_page_f03_ex117(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_117a = MetricCard("Total & Mean Cycle Time (11.7 A/B)", "-", "All active cases", "#2563eb")
        self.card_117c = MetricCard("Accepted Cases (11.7 C)", "-", "Contains('O_Accepted')", "#059669")
        self.card_117d = MetricCard("Refused Cases (11.7 D)", "-", "Contains('O_Refused')", "#dc2626")
        self.card_117e = MetricCard("Cancelled Endpoint (11.7 E)", "-", "Last Event == 'O_Cancelled'", "#d97706")
        for c in (self.card_117a, self.card_117c, self.card_117d, self.card_117e):
            cards.addWidget(c)
        layout.addLayout(cards)

        # Side-by-side compact visual comparison row
        viz_row = QHBoxLayout()
        viz_row.setSpacing(10)

        card_mix = SectionCard("Outcome Distribution (Contains vs Endpoint)")
        card_mix.setMaximumHeight(168)
        self.chart_117_mix = SegmentedRatioBarWidget()
        card_mix.body_layout.addWidget(self.chart_117_mix)
        self.lbl_117_rule_note = QLabel("Load dataset to compare Contains vs Endpoint semantics.")
        self.lbl_117_rule_note.setWordWrap(True)
        self.lbl_117_rule_note.setStyleSheet("color: #475569; font-size: 11.5px; padding-top: 2px;")
        card_mix.body_layout.addWidget(self.lbl_117_rule_note)
        viz_row.addWidget(card_mix, stretch=6)

        card_dur = SectionCard("Mean Cycle Time Comparison (Days)")
        card_dur.setMaximumHeight(168)
        self.chart_117_dur = HorizontalBarChartWidget(row_height=24, label_width=135)
        card_dur.body_layout.addWidget(self.chart_117_dur)
        viz_row.addWidget(card_dur, stretch=5)
        layout.addLayout(viz_row)

        # Cohort table card with inline controls
        ctrl_widget = QWidget()
        ctrl_bar = QHBoxLayout(ctrl_widget)
        ctrl_bar.setContentsMargins(0, 0, 0, 0)
        ctrl_bar.setSpacing(6)
        self.cmb_117_group = QComboBox()
        self.cmb_117_group.addItems([
            "11.7 C — Accepted Cases (Contains O_Accepted)",
            "11.7 D — Refused Cases (Contains O_Refused)",
            "11.7 E — Cancelled Cases (Last Event == O_Cancelled)",
            "11.7 A & B — All Active Applications",
        ])
        self.cmb_117_group.setMinimumWidth(310)
        self.cmb_117_group.currentIndexChanged.connect(self._on_117_group_changed)
        self.txt_117_search = QLineEdit()
        self.txt_117_search.setPlaceholderText("Search Case ID or activity...")
        self.txt_117_search.setMinimumWidth(190)
        self.txt_117_search.textChanged.connect(self._on_filter_117_table)
        btn_inspect_117 = QPushButton("Inspect Trace")
        btn_inspect_117.setCursor(Qt.PointingHandCursor)
        btn_inspect_117.clicked.connect(self._on_inspect_from_117)
        ctrl_bar.addWidget(self.cmb_117_group)
        ctrl_bar.addWidget(self.txt_117_search)
        ctrl_bar.addWidget(btn_inspect_117)

        card_cohort = SectionCard(
            "Filtered Case Cohort",
            "Full trace cycle time preserved prior to cohort filtering",
            header_right=ctrl_widget,
        )
        self.model_117_cases = DataFrameTableModel()

        self.table_117_cases = QTableView()
        self.table_117_cases.setModel(self.model_117_cases)
        self._configure_table(self.table_117_cases, stretch_last=True, interactive_columns=True)
        self.table_117_cases.setSortingEnabled(True)
        self.table_117_cases.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table_117_cases.doubleClicked.connect(lambda _: self._on_inspect_from_117())
        card_cohort.body_layout.addWidget(self.table_117_cases, stretch=1)
        layout.addWidget(card_cohort, stretch=1)

        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 3: F04 & F05 — Fraud Rework & Audit (Ref: 11.15 & 11.18)
    # ------------------------------------------------------------------
    def _build_page_f04_f05_ex1115_1118(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_1115_ans = MetricCard("Fraud Rework Complete (11.15)", "-", "W_Assess potential fraud >= 2x", "#2563eb")
        self.card_1115_excl = MetricCard("Excluded Non-Complete", "-", "All lifecycle >=2x vs complete >=2x", "#4f46e5")
        self.card_1118_ans = MetricCard("Same-Resource Repeat (11.18)", "-", "Identical valid org:resource >= 2x", "#059669")
        self.card_1118_diff = MetricCard("Multi-Resource Repeat", "-", "Passed 11.15 with distinct/empty resources", "#d97706")
        for c in (self.card_1115_ans, self.card_1115_excl, self.card_1118_ans, self.card_1118_diff):
            cards.addWidget(c)
        layout.addLayout(cards)

        # Compact audit funnel bar
        funnel_card = SectionCard("Lifecycle & Resource Audit Funnel (W_Assess potential fraud >= 2x)")
        funnel_card.setMaximumHeight(105)
        self.chart_15_18_funnel = SegmentedRatioBarWidget()
        funnel_card.body_layout.addWidget(self.chart_15_18_funnel)
        layout.addWidget(funnel_card)

        top_splitter = QSplitter(Qt.Horizontal)

        # Left: 11.15
        ctrl_15_w = QWidget()
        row_15 = QHBoxLayout(ctrl_15_w)
        row_15.setContentsMargins(0, 0, 0, 0)
        row_15.setSpacing(6)
        btn_show_excl = QPushButton("Non-Complete Proof")
        btn_show_excl.setObjectName("SecondaryBtn")
        btn_show_excl.setCursor(Qt.PointingHandCursor)
        btn_show_excl.clicked.connect(self._on_show_excluded_lifecycle_case)
        btn_inspect_15 = QPushButton("Inspect Trace")
        btn_inspect_15.setCursor(Qt.PointingHandCursor)
        btn_inspect_15.clicked.connect(self._on_inspect_from_1115)
        row_15.addWidget(btn_show_excl)
        row_15.addWidget(btn_inspect_15)

        card_1115 = SectionCard("Repeated Fraud Complete (11.15)", "Click a row to load event evidence below", header_right=ctrl_15_w)
        self.model_1115_cases = DataFrameTableModel()
        self.table_1115_cases = QTableView()
        self.table_1115_cases.setModel(self.model_1115_cases)
        self._configure_table(self.table_1115_cases, stretch_last=True, row_height=28)
        self.table_1115_cases.clicked.connect(self._on_select_1115_case)
        self.table_1115_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1115())
        card_1115.body_layout.addWidget(self.table_1115_cases)
        top_splitter.addWidget(card_1115)

        # Right: 11.18
        ctrl_18_w = QWidget()
        row_18 = QHBoxLayout(ctrl_18_w)
        row_18.setContentsMargins(0, 0, 0, 0)
        row_18.setSpacing(6)
        btn_show_diff_res = QPushButton("Diff-Resource Proof")
        btn_show_diff_res.setObjectName("SecondaryBtn")
        btn_show_diff_res.setCursor(Qt.PointingHandCursor)
        btn_show_diff_res.clicked.connect(self._on_show_diff_resource_evidence)
        btn_inspect_18 = QPushButton("Inspect Trace")
        btn_inspect_18.setObjectName("SuccessBtn")
        btn_inspect_18.setCursor(Qt.PointingHandCursor)
        btn_inspect_18.clicked.connect(self._on_inspect_from_1118)
        row_18.addWidget(btn_show_diff_res)
        row_18.addWidget(btn_inspect_18)

        card_1118 = SectionCard("Same-Resource Compliance Audit (11.18)", "Validates repeated completion by identical resource", header_right=ctrl_18_w)
        self.model_1118_cases = DataFrameTableModel()
        self.table_1118_cases = QTableView()
        self.table_1118_cases.setModel(self.model_1118_cases)
        self._configure_table(self.table_1118_cases, stretch_last=True, row_height=28)
        self.table_1118_cases.clicked.connect(self._on_select_1118_case)
        self.table_1118_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1118())
        card_1118.body_layout.addWidget(self.table_1118_cases)
        top_splitter.addWidget(card_1118)
        top_splitter.setSizes([600, 580])

        # Bottom: Event Evidence
        card_ev = SectionCard("Event-Level Audit Evidence", "Amber = qualifying 'complete' events • Blue = other lifecycle transitions")
        self.lbl_15_18_evidence_title = QLabel("Click any case above to inspect its W_Assess potential fraud lifecycle events.")
        self.lbl_15_18_evidence_title.setWordWrap(True)
        self.lbl_15_18_evidence_title.setStyleSheet(
            "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 600; color: #1e3a8a;"
        )
        card_ev.body_layout.addWidget(self.lbl_15_18_evidence_title)

        self.model_15_18_evidence = DataFrameTableModel()
        self.table_15_18_evidence = QTableView()
        self.table_15_18_evidence.setModel(self.model_15_18_evidence)
        self._configure_table(self.table_15_18_evidence, stretch_last=True, row_height=28)
        card_ev.body_layout.addWidget(self.table_15_18_evidence)

        v_split = QSplitter(Qt.Vertical)
        v_split.addWidget(top_splitter)
        v_split.addWidget(card_ev)
        v_split.setSizes([310, 250])

        layout.addWidget(v_split, stretch=1)
        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 4: F06 — Offer Re-Acceptance (Ref: 11.22)
    # ------------------------------------------------------------------
    def _build_page_f06_ex1122(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_1122_ans = MetricCard("Cancelled → Accepted (11.22)", "-", "O_Cancelled before O_Accepted (i < j)", "#2563eb")
        self.card_1122_pct = MetricCard("Share of Active Cases", "-", "Explicit denominator ratio", "#059669")
        self.card_1122_rev = MetricCard("Reverse Order Only", "-", "O_Accepted before O_Cancelled only", "#d97706")
        self.card_1122_offer = MetricCard("Same-OfferID Matches", "-", "Re-acceptance within identical OfferID", "#4f46e5")
        for c in (self.card_1122_ans, self.card_1122_pct, self.card_1122_rev, self.card_1122_offer):
            cards.addWidget(c)
        layout.addLayout(cards)

        v_split = QSplitter(Qt.Vertical)

        ctrl_22_w = QWidget()
        ctrl_22 = QHBoxLayout(ctrl_22_w)
        ctrl_22.setContentsMargins(0, 0, 0, 0)
        ctrl_22.setSpacing(6)
        self.txt_1122_search = QLineEdit()
        self.txt_1122_search.setPlaceholderText("Search Case ID or OfferID...")
        self.txt_1122_search.setMinimumWidth(240)
        self.txt_1122_search.textChanged.connect(self._on_filter_1122_table)
        btn_inspect_22 = QPushButton("Inspect Full Trace")
        btn_inspect_22.setCursor(Qt.PointingHandCursor)
        btn_inspect_22.clicked.connect(self._on_inspect_from_1122)
        ctrl_22.addWidget(self.txt_1122_search)
        ctrl_22.addWidget(btn_inspect_22)

        card_cases = SectionCard(
            "Sequential Pattern Matches (O_Cancelled at pos i < O_Accepted at pos j)",
            "Select a case row to inspect its offer transition timeline below",
            header_right=ctrl_22_w,
        )
        self.model_1122_cases = DataFrameTableModel()

        self.table_1122_cases = QTableView()
        self.table_1122_cases.setModel(self.model_1122_cases)
        self._configure_table(self.table_1122_cases, stretch_last=True, interactive_columns=True)
        self.table_1122_cases.setSortingEnabled(True)
        self.table_1122_cases.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table_1122_cases.clicked.connect(self._on_select_1122_case)
        self.table_1122_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1122())
        card_cases.body_layout.addWidget(self.table_1122_cases)
        v_split.addWidget(card_cases)

        card_tl = SectionCard("Selected Case Offer Timeline", "Highlights O_Cancelled and O_Accepted events in trace order")
        self.lbl_1122_timeline_info = QLabel("Click a matching case above to view its O_Cancelled → O_Accepted event sequence and OfferIDs.")
        self.lbl_1122_timeline_info.setWordWrap(True)
        self.lbl_1122_timeline_info.setStyleSheet(
            "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 600; color: #1e3a8a;"
        )
        card_tl.body_layout.addWidget(self.lbl_1122_timeline_info)

        self.model_1122_evidence = DataFrameTableModel()
        self.table_1122_evidence = QTableView()
        self.table_1122_evidence.setModel(self.model_1122_evidence)
        self._configure_table(self.table_1122_evidence, stretch_last=True, row_height=28)
        card_tl.body_layout.addWidget(self.table_1122_evidence)
        v_split.addWidget(card_tl)
        v_split.setSizes([350, 260])

        layout.addWidget(v_split, stretch=1)
        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 5: F07 — Trace Explorer (Case & Event Inspector)
    # ------------------------------------------------------------------
    def _build_page_f07_case_explorer(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Toolbar card
        toolbar = QFrame()
        toolbar.setObjectName("ToolbarCard")
        tb_v = QVBoxLayout(toolbar)
        tb_v.setContentsMargins(14, 10, 14, 10)
        tb_v.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        lbl_fk = QLabel("Cohort Filter:")
        lbl_fk.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px;")
        top_bar.addWidget(lbl_fk)
        self.cmb_explorer_filter = QComboBox()
        self.cmb_explorer_filter.addItems([
            "All Active Applications (Overview)",
            "11.7 C — Accepted Cases (Contains O_Accepted)",
            "11.7 D — Refused Cases (Contains O_Refused)",
            "11.7 E — Cancelled Cases (Last Event == O_Cancelled)",
            "11.15 — Fraud Rework Complete >= 2x",
            "11.18 — Fraud Rework Complete >= 2x (Same Resource)",
            "11.22 — O_Cancelled Followed By O_Accepted (i < j)",
        ])
        self.cmb_explorer_filter.currentIndexChanged.connect(self._on_explorer_group_changed)
        top_bar.addWidget(self.cmb_explorer_filter, stretch=1)

        lbl_cc = QLabel("Case ID:")
        lbl_cc.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px;")
        top_bar.addWidget(lbl_cc)
        self.txt_explorer_search = QLineEdit()
        self.txt_explorer_search.setPlaceholderText("Search Case ID (e.g. Application_1221917431)...")
        self.txt_explorer_search.textChanged.connect(self._on_explorer_search_changed)
        top_bar.addWidget(self.txt_explorer_search, stretch=1)

        btn_reset_exp = QPushButton("Reset")
        btn_reset_exp.setObjectName("SecondaryBtn")
        btn_reset_exp.setCursor(Qt.PointingHandCursor)
        btn_reset_exp.clicked.connect(self._on_reset_explorer)
        top_bar.addWidget(btn_reset_exp)
        tb_v.addLayout(top_bar)

        self.lbl_explorer_rule_banner = QLabel("Active Filter: Displaying all cases in the active event log.")
        self.lbl_explorer_rule_banner.setWordWrap(True)
        self.lbl_explorer_rule_banner.setStyleSheet(
            "background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: 600; color: #1e3a8a;"
        )
        tb_v.addWidget(self.lbl_explorer_rule_banner)
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        card_left = SectionCard("Matching Cases")
        card_left.setMinimumWidth(290)
        self.model_explorer_cases = DataFrameTableModel()

        self.table_explorer_cases = QTableView()
        self.table_explorer_cases.setModel(self.model_explorer_cases)
        self._configure_table(self.table_explorer_cases, stretch_last=True, interactive_columns=True)
        self.table_explorer_cases.setSortingEnabled(True)
        self.table_explorer_cases.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.table_explorer_cases.clicked.connect(self._on_explorer_case_clicked)
        card_left.body_layout.addWidget(self.table_explorer_cases)
        splitter.addWidget(card_left)

        card_right = SectionCard("Full Trace Sequence", "Exact XES trace ordering (_trace_pos) with automatic evidence row highlights")
        self.lbl_explorer_case_meta = QLabel("Select a case on the left to inspect its full event sequence.")
        self.lbl_explorer_case_meta.setWordWrap(True)
        self.lbl_explorer_case_meta.setStyleSheet(
            "background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; color: #0f172a; font-size: 12px; font-weight: 600; padding: 6px 10px;"
        )
        card_right.body_layout.addWidget(self.lbl_explorer_case_meta)

        self.trace_flow_strip = TraceFlowStripWidget()
        card_right.body_layout.addWidget(self.trace_flow_strip)

        self.model_explorer_events = DataFrameTableModel()
        self.table_explorer_events = QTableView()
        self.table_explorer_events.setModel(self.model_explorer_events)
        self._configure_table(self.table_explorer_events, stretch_last=True, row_height=28)
        card_right.body_layout.addWidget(self.table_explorer_events, stretch=1)
        splitter.addWidget(card_right)
        splitter.setSizes([410, 770])

        layout.addWidget(splitter, stretch=1)
        self.pages.addWidget(page)

    # ------------------------------------------------------------------
    # PAGE 6: F07 — Summary & Export
    # ------------------------------------------------------------------
    def _build_page_f07_export(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        action_card = QFrame()
        action_card.setObjectName("ToolbarCard")
        ac_layout = QHBoxLayout(action_card)
        ac_layout.setContentsMargins(14, 10, 14, 10)
        ac_layout.setSpacing(10)

        hint_col = QVBoxLayout()
        hint_col.setSpacing(2)
        lbl_h1 = QLabel("Export Analytical Deliverables")
        lbl_h1.setStyleSheet("font-size: 13px; font-weight: 700; color: #0f172a;")
        lbl_h2 = QLabel("Generates 10 structured CSV datasets (summaries, case cohorts, event evidence) plus a standalone HTML report.")
        lbl_h2.setStyleSheet("font-size: 12px; color: #64748b;")
        hint_col.addWidget(lbl_h1)
        hint_col.addWidget(lbl_h2)
        ac_layout.addLayout(hint_col, stretch=1)

        btn_export_single_csv = QPushButton("Export Summary CSV...")
        btn_export_single_csv.setObjectName("SecondaryBtn")
        btn_export_single_csv.setCursor(Qt.PointingHandCursor)
        btn_export_single_csv.clicked.connect(self.on_export_summary_csv)
        ac_layout.addWidget(btn_export_single_csv)

        btn_export_dir = QPushButton("Export Full Package (10 CSV + HTML)...")
        btn_export_dir.setObjectName("SuccessBtn")
        btn_export_dir.setCursor(Qt.PointingHandCursor)
        btn_export_dir.clicked.connect(self.on_export_all)
        ac_layout.addWidget(btn_export_dir)
        layout.addWidget(action_card)

        card_sum = SectionCard(
            "Consolidated Process Mining Metrics (8 Mandatory Benchmarks)",
            "All 10 columns fit within the viewport with automatic multi-line wrapping",
        )
        self.model_export_summary = DataFrameTableModel()
        self.table_export_summary = QTableView()
        self.table_export_summary.setModel(self.model_export_summary)
        self.table_export_summary.setStyleSheet("QTableView { font-size: 11.5px; } QTableView::item { padding: 2px 5px; }")
        self._configure_table(self.table_export_summary, stretch_last=True, word_wrap=True, row_height=46)
        card_sum.body_layout.addWidget(self.table_export_summary)
        layout.addWidget(card_sum, stretch=1)

        self.pages.addWidget(page)

    def _resize_summary_table_columns(self) -> None:
        """Calibrates Tab 7 column widths so all 10 columns fit cleanly without header clipping."""
        df = self.model_export_summary.get_dataframe()
        if df.empty:
            return
        hh = self.table_export_summary.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)

        col_widths = {
            "Kode Soal": 56,
            "Pertanyaan": 156,
            "Aturan / Filter": 256,
            "Jumlah Case Terpilih": 56,
            "Denominator (Total Case Aktif)": 58,
            "Persentase Case (%)": 62,
            "Mean Cycle Time (Hari)": 70,
            "Mean Cycle Time (Jam)": 74,
            "Median Cycle Time (Hari)": 76,
            "Jawaban Utama": 260,
        }
        for i, col_name in enumerate(df.columns):
            w = col_widths.get(str(col_name), 100)
            self.table_export_summary.setColumnWidth(i, w)
        self.table_export_summary.resizeRowsToContents()

    # ==================================================================
    # EVENT HANDLERS & WORKFLOW LOGIC
    # ==================================================================
    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        self.btn_top_import.setEnabled(not busy)
        self.btn_top_bpic.setEnabled(not busy)
        self.btn_top_synth.setEnabled(not busy)
        self.btn_top_rerun.setEnabled((not busy) and (self.bundle is not None))
        if msg:
            self.status_bar.showMessage(msg)

    def on_browse_xes(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Berkas Event Log XES",
            os.getcwd(),
            "XES Event Log Files (*.xes *.xes.gz);;All Files (*)",
        )
        if file_path:
            self.start_analysis(file_path)

    def on_load_default_bpic17(self) -> None:
        candidates = [
            os.path.join(os.getcwd(), "BPI Challenge 2017.xes.gz"),
            os.path.join(os.getcwd(), "BPI Challenge 2017.xes"),
        ]
        for c in candidates:
            if os.path.exists(c):
                self.start_analysis(c)
                return
        QMessageBox.warning(
            self,
            "Berkas BPIC17 Tidak Ditemukan",
            "Berkas 'BPI Challenge 2017.xes.gz' tidak ditemukan di folder kerja saat ini. Silakan pilih manual menggunakan tombol 'Import XES...'.",
        )

    def on_load_synthetic_log(self) -> None:
        syn_path = os.path.join(os.getcwd(), "data", "synthetic_edge_cases.xes")
        try:
            generate_synthetic_xes_file(syn_path)
            self.start_analysis(syn_path)
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Membuat Log Sintetis", str(exc))

    def on_rerun_all(self) -> None:
        if self.bundle is None:
            return
        self.start_analysis(self.bundle.report.file_path, existing_context=self.bundle.context)

    def start_analysis(self, file_path: str, existing_context: Optional[EventLogContext] = None) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self._set_busy(True, f"Processing {os.path.basename(file_path)}...")
        self.worker = AnalysisWorker(file_path=file_path, existing_context=existing_context)
        self.worker.progress_changed.connect(self.status_bar.showMessage)
        self.worker.finished_bundle.connect(self._on_analysis_finished)
        self.worker.failed_error.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_analysis_failed(self, err_msg: str) -> None:
        self._set_busy(False, "Failed to load/validate XES file.")
        self._lbl_sidebar_dot.setStyleSheet("color: #ef4444; font-size: 11px;")
        self._lbl_sidebar_ds_name.setText("Validation Failed")
        self.card_f01_status.update_card("INVALID / ERROR", "See diagnostic details below")
        self.txt_f01_validation.setHtml(
            f"<h3 style='color:#dc2626;'>XES Import or Validation Error</h3>"
            f"<pre style='background:#fef2f2;padding:12px;border:1px solid #fecaca;color:#991b1b;border-radius:6px;'>{err_msg}</pre>"
        )
        QMessageBox.critical(self, "Kesalahan Impor / Validasi XES", err_msg)

    def _on_analysis_finished(self, bundle: FullAnalysisBundle) -> None:
        self.bundle = bundle
        rep = bundle.report
        self._set_busy(
            False,
            f"Loaded {rep.file_name} ({rep.total_cases:,} cases, {rep.total_events:,} events) in {rep.load_time_seconds:.2f}s.",
        )

        # Update sidebar card & topbar pill
        self._lbl_sidebar_dot.setStyleSheet("color: #10b981; font-size: 11px;")
        self._lbl_sidebar_ds_name.setText(rep.file_name)
        ev_label = f"{rep.total_events / 1_000_000:.2f}M" if rep.total_events >= 1_000_000 else f"{rep.total_events:,}"
        self._lbl_sidebar_ds_meta.setText(f"{rep.total_cases:,} cases • {ev_label} events")
        self.lbl_active_dataset.setText(
            f"{rep.file_name} • {rep.file_size_mb:.2f} MB • {rep.load_time_seconds:.2f}s"
        )

        self._populate_f01(bundle)
        self._populate_f02(bundle)
        self._populate_f03(bundle)
        self._populate_f04_f05(bundle)
        self._populate_f06(bundle)
        self._populate_f07(bundle)

    # ------------------------------------------------------------------
    # POPULATE PAGES FROM BUNDLE
    # ------------------------------------------------------------------
    def _populate_f01(self, b: FullAnalysisBundle) -> None:
        rep = b.report
        self.card_f01_status.update_card("VALID (PM4Py)", f"{rep.file_name} ({rep.file_size_mb:.2f} MB) • {rep.load_time_seconds:.2f}s")
        self.card_f01_cases.update_card(f"{rep.total_cases:,} Cases", "case:concept:name verified")
        self.card_f01_events.update_card(f"{rep.total_events:,} Events", f"Avg {rep.total_events / max(rep.total_cases, 1):.2f} events/case")
        lc_txt = "Yes" if rep.has_lifecycle else "No"
        res_txt = "Yes" if rep.has_resource else "No"
        self.card_f01_attrs.update_card(
            f"{len(rep.lifecycle_values)} Transitions • {b.overview.unique_resources:,} Res",
            f"Lifecycle: {lc_txt} | Resource: {res_txt} | OfferID: {'Yes' if rep.has_offer_id else 'No'}",
        )

        env = get_environment_info()
        warn_html = ""
        if rep.warnings:
            warn_items = "".join(f"<li>{w}</li>" for w in rep.warnings)
            warn_html = (
                f"<div style='background:#fffbeb;border:1px solid #fde68a;padding:10px;border-radius:6px;margin-bottom:12px;'>"
                f"<b>Warnings:</b><ul>{warn_items}</ul></div>"
            )

        trace_pills = " ".join(
            f"<span style='display:inline-block;background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;border-radius:4px;padding:2px 7px;margin:2px;font-family:Consolas,monospace;font-size:12px;'>{a}</span>"
            for a in rep.trace_attributes
        )
        event_pills = " ".join(
            f"<span style='display:inline-block;background:#f8fafc;color:#0f172a;border:1px solid #cbd5e1;border-radius:4px;padding:2px 7px;margin:2px;font-family:Consolas,monospace;font-size:12px;'>{a}</span>"
            for a in rep.event_attributes
        )
        lc_pills = " ".join(
            f"<span style='display:inline-block;background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;border-radius:4px;padding:2px 7px;margin:2px;font-family:Consolas,monospace;font-size:12px;font-weight:600;'>{v}</span>"
            for v in rep.lifecycle_values
        )

        self.txt_f01_validation.setHtml(f"""
        <div style="font-family:'Segoe UI',sans-serif;color:#0f172a;padding:4px;line-height:1.55;">
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #059669;border-radius:6px;padding:10px 14px;margin-bottom:12px;">
            <span style="background:#d1fae5;color:#065f46;font-weight:700;padding:2px 8px;border-radius:4px;font-size:11px;">SCHEMA VERIFIED</span>
            <span style="margin-left:8px;font-weight:700;color:#0f172a;font-size:14px;">{rep.file_name}</span>
            <span style="margin-left:10px;color:#64748b;font-size:12px;">Path: <code>{rep.file_path}</code></span>
          </div>
          {warn_html}
          <table width="100%" cellspacing="0" cellpadding="7" style="border-collapse:collapse;border:1px solid #e2e8f0;margin-bottom:12px;font-size:12.5px;">
            <tr style="background:#f8fafc;color:#475569;font-weight:700;">
              <th align="left" width="26%" style="border-bottom:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">Validation Check</th>
              <th align="left" width="22%" style="border-bottom:1px solid #e2e8f0;border-right:1px solid #e2e8f0;">Detected Value</th>
              <th align="left" width="52%" style="border-bottom:1px solid #e2e8f0;">Technical Details</th>
            </tr>
            <tr>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;"><b>Ingestion &amp; Size</b></td>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;color:#1d4ed8;font-weight:700;">{rep.file_size_mb:.2f} MB ({rep.load_time_seconds:.2f}s)</td>
              <td style="border-bottom:1px solid #f1f5f9;">Parsed via <code>pm4py.read_xes</code> on background <code>QThread</code> worker</td>
            </tr>
            <tr style="background:#f8fafc;">
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;"><b>Log Volume</b></td>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;color:#059669;font-weight:700;">{rep.total_cases:,} Cases &bull; {rep.total_events:,} Events</td>
              <td style="border-bottom:1px solid #f1f5f9;">Mandatory keys <code>case:concept:name</code>, <code>concept:name</code>, <code>time:timestamp</code> 100% present</td>
            </tr>
            <tr>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;"><b>Lifecycle Transitions</b></td>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;color:#059669;font-weight:700;">{len(rep.lifecycle_values)} States</td>
              <td style="border-bottom:1px solid #f1f5f9;">{lc_pills}</td>
            </tr>
            <tr style="background:#f8fafc;">
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;"><b>Resources &amp; OfferID</b></td>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;color:#4f46e5;font-weight:700;">{b.overview.unique_resources:,} Valid Resources</td>
              <td style="border-bottom:1px solid #f1f5f9;"><code>org:resource</code>: {'Present' if rep.has_resource else 'Missing'} &bull; <code>OfferID</code>: {'Present (used in 11.22)' if rep.has_offer_id else 'Missing'}</td>
            </tr>
            <tr>
              <td style="border-bottom:1px solid #f1f5f9;border-right:1px solid #f1f5f9;"><b>Trace Attributes ({len(rep.trace_attributes)})</b></td>
              <td colspan="2" style="border-bottom:1px solid #f1f5f9;">{trace_pills}</td>
            </tr>
            <tr style="background:#f8fafc;">
              <td style="border-right:1px solid #f1f5f9;"><b>Event Attributes ({len(rep.event_attributes)})</b></td>
              <td colspan="2">{event_pills}</td>
            </tr>
          </table>
          <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:9px 13px;margin-bottom:8px;font-size:12px;">
            <b>Trace Semantics:</b> Event sequence follows exact XES trace index (<code>_trace_pos</code>); case cycle time is computed on full unpruned traces (<code>last_timestamp - first_timestamp</code>).
          </div>
          <div style="font-size:11.5px;color:#64748b;">
            <b>Reproducibility:</b> Python <code>{env['Python']}</code> &bull; PM4Py <code>{env['PM4Py']}</code> &bull; Pandas <code>{env['Pandas']}</code> &bull; PySide6 <code>{env['PySide6']}</code> &bull; r4pm <code>{env['r4pm (XES accelerator)']}</code>
          </div>
        </div>
        """)

    def _populate_f02(self, b: FullAnalysisBundle) -> None:
        ov = b.overview
        self.card_f02_cases.update_card(f"{ov.total_cases:,} Cases", f"Min: {ov.min_cycle_time_days:.4f}d | Max: {ov.max_cycle_time_days:.2f}d")
        self.card_f02_events.update_card(f"{ov.total_events:,} Events", f"{ov.unique_activities} Activities • {ov.unique_resources} Resources")
        self.card_f02_meandur.update_card(
            f"{ov.mean_cycle_time_days:.2f} Days",
            f"Exact: {ov.mean_cycle_time_days:.4f}d ({ov.mean_cycle_time_hours:.2f} hr) • Median: {ov.median_cycle_time_days:.2f}d",
        )
        self.card_f02_fastslow.update_card(
            f"Fast: {ov.fast_cases_count:,} ({ov.fast_cases_pct:.1f}%)",
            f"Slow (>=45d): {ov.slow_cases_count:,} ({ov.slow_cases_pct:.1f}%)",
        )
        self.lbl_f02_timerange.setText(
            f"{format_timestamp_compact(str(ov.log_start_time))} → {format_timestamp_compact(str(ov.log_end_time))} UTC  •  Std Dev: {ov.std_cycle_time_days:.2f}d"
        )

        self.chart_f02_sla.set_segments([
            ("Fast (< 45d)", ov.fast_cases_pct, "#10b981", f"{ov.fast_cases_count:,} cases ({ov.fast_cases_pct:.1f}%)"),
            ("Slow (>= 45d)", ov.slow_cases_pct, "#f59e0b", f"{ov.slow_cases_count:,} cases ({ov.slow_cases_pct:.1f}%)"),
        ])

        top_acts = ov.activity_table.head(6)
        bar_items = [
            (
                str(r["activity"]),
                float(r["event_count"]),
                f"{int(r['event_count']):,} ({float(r['event_pct']):.1f}%)",
                activity_color_hex(str(r["activity"])),
            )
            for _, r in top_acts.iterrows()
        ]
        self.chart_f02_activities.set_bars(bar_items)

        self.model_f02_act.set_dataframe(ov.activity_table)
        self.model_f02_cases.set_dataframe(ov.case_table)
        self._apply_column_widths(
            self.table_f02_cases,
            ov.case_table,
            {
                "case_id": 172,
                "event_count": 72,
                "start_timestamp": 140,
                "end_timestamp": 140,
                "first_activity": 160,
                "last_activity": 160,
                "duration_seconds": 100,
                "duration_hours": 95,
                "duration_days": 110,
                "minmax_duration_days": 105,
                "speed_category": 125,
            },
        )

    def _populate_f03(self, b: FullAnalysisBundle) -> None:
        r = b.ex117
        self.card_117a.update_card(
            f"{r.sub_b.mean_duration_days:.2f} Days",
            f"{r.sub_a.case_count:,} Cases (100%) • {r.sub_b.mean_duration_hours:.2f} hr",
        )
        self.card_117c.update_card(
            f"{r.sub_c.case_count:,} ({r.sub_c.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_c.mean_duration_days:.2f}d ({r.sub_c.mean_duration_days:.4f}d)",
        )
        self.card_117d.update_card(
            f"{r.sub_d.case_count:,} ({r.sub_d.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_d.mean_duration_days:.2f}d ({r.sub_d.mean_duration_days:.4f}d)",
        )
        self.card_117e.update_card(
            f"{r.sub_e.case_count:,} ({r.sub_e.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_e.mean_duration_days:.2f}d ({r.sub_e.mean_duration_days:.4f}d)",
        )

        other_pct = max(0.0, 100.0 - (r.sub_c.case_percentage + r.sub_d.case_percentage + r.sub_e.case_percentage))
        other_cnt = max(0, r.sub_a.case_count - r.sub_c.case_count - r.sub_d.case_count - r.sub_e.case_count)
        self.chart_117_mix.set_segments([
            ("Accepted (11.7 C)", r.sub_c.case_percentage, "#059669", f"{r.sub_c.case_count:,} ({r.sub_c.case_percentage:.1f}%)"),
            ("Cancelled End (11.7 E)", r.sub_e.case_percentage, "#f59e0b", f"{r.sub_e.case_count:,} ({r.sub_e.case_percentage:.1f}%)"),
            ("Refused (11.7 D)", r.sub_d.case_percentage, "#dc2626", f"{r.sub_d.case_count:,} ({r.sub_d.case_percentage:.1f}%)"),
            ("Other", other_pct, "#cbd5e1", f"{other_cnt:,}"),
        ])

        self.lbl_117_rule_note.setText(
            f"Overlap Accepted ∩ Refused = {r.overlap_c_and_d_count:,} cases  •  "
            f"Contains O_Cancelled anywhere = {r.contains_cancelled_anywhere_count:,} cases "
            f"({r.contains_cancelled_anywhere_count - r.sub_e.case_count:,} continued to later events)."
        )

        self.chart_117_dur.set_bars([
            ("Refused (11.7 D)", r.sub_d.mean_duration_days, f"{r.sub_d.mean_duration_days:.2f} d", "#dc2626"),
            ("Accepted (11.7 C)", r.sub_c.mean_duration_days, f"{r.sub_c.mean_duration_days:.2f} d", "#059669"),
            ("All Cases (11.7 B)", r.sub_b.mean_duration_days, f"{r.sub_b.mean_duration_days:.2f} d", "#2563eb"),
            ("Cancelled End (11.7 E)", r.sub_e.mean_duration_days, f"{r.sub_e.mean_duration_days:.2f} d", "#d97706"),
        ])

        self._on_117_group_changed()

    def _populate_f04_f05(self, b: FullAnalysisBundle) -> None:
        r15 = b.ex1115
        r18 = b.ex1118
        self.card_1115_ans.update_card(
            f"{r15.matching_case_count:,} Cases",
            f"Out of {r15.total_cases_denominator:,} ({r15.matching_percentage:.4f}%)",
        )
        self.card_1115_excl.update_card(
            f"{r15.excluded_by_lifecycle_count:,} Excluded",
            f"All lifecycle >=2x: {r15.cases_with_two_all_lifecycles:,} vs Complete >=2x: {r15.matching_case_count:,}",
        )
        self.card_1118_ans.update_card(
            f"{r18.matching_case_count:,} Cases",
            f"Same valid resource >=2x ({r18.matching_percentage:.4f}%)",
        )
        self.card_1118_diff.update_card(
            f"{len(r18.cases_from_1115_excluded_diff_resource):,} Cases",
            "Passed 11.15 with different/empty resources",
        )

        total_all_lc = max(r15.cases_with_two_all_lifecycles, 1)
        excl_pct = (r15.excluded_by_lifecycle_count / total_all_lc) * 100.0
        diff_cnt = len(r18.cases_from_1115_excluded_diff_resource)
        diff_pct = (diff_cnt / total_all_lc) * 100.0
        same_pct = (r18.matching_case_count / total_all_lc) * 100.0
        self.chart_15_18_funnel.set_segments([
            ("Same-Res Complete (11.18)", same_pct, "#059669", f"{r18.matching_case_count:,}"),
            ("Diff-Res Complete (11.15 only)", diff_pct, "#2563eb", f"{diff_cnt:,}"),
            ("Excluded Non-Complete", excl_pct, "#cbd5e1", f"{r15.excluded_by_lifecycle_count:,} (of {r15.cases_with_two_all_lifecycles:,} all-lifecycle >=2x)"),
        ])

        self.model_1115_cases.set_dataframe(r15.case_summary_df)
        self.model_1118_cases.set_dataframe(r18.case_resource_summary_df)

        cols_ev = [
            c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "EventID", "Action"]
            if c in r15.evidence_events_df.columns
        ]
        self.model_15_18_evidence.set_dataframe(
            r15.evidence_events_df[cols_ev] if cols_ev else r15.evidence_events_df,
            highlight_activities=[r15.target_activity],
            highlight_lifecycle="complete",
        )
        self.lbl_15_18_evidence_title.setText(
            f"Showing all {len(r15.evidence_events_df)} 'complete' evidence events for the {r15.matching_case_count} qualifying 11.15 cases (click a row above to drill down)."
        )

    def _populate_f06(self, b: FullAnalysisBundle) -> None:
        r22 = b.ex1122
        ans_prefix = "Yes" if r22.matching_case_count > 0 else "None"
        self.card_1122_ans.update_card(
            f"{ans_prefix}: {r22.matching_case_count:,} Cases",
            "Satisfies trace order i(O_Cancelled) < j(O_Accepted)",
        )
        self.card_1122_pct.update_card(
            f"{r22.matching_percentage:.2f}% ({r22.matching_percentage:.4f}%)",
            f"Denominator: {r22.matching_case_count:,} / {r22.total_cases_denominator:,} active cases",
        )
        self.card_1122_rev.update_card(
            f"{r22.reverse_only_count:,} Cases",
            f"Out of {r22.both_present_any_order_count:,} with both events, only Accepted → Cancelled",
        )
        self.card_1122_offer.update_card(
            f"Same OfferID: {r22.same_offer_id_matching_count} Cases",
            "Prior offer cancelled, new offer accepted",
        )
        self.model_1122_cases.set_dataframe(r22.case_summary_df)
        self._apply_column_widths(
            self.table_1122_cases,
            r22.case_summary_df,
            {
                "case_id": 172,
                "cancelled_trace_pos": 115,
                "cancelled_timestamp": 140,
                "cancelled_offer_id": 125,
                "accepted_trace_pos": 115,
                "accepted_timestamp": 140,
                "accepted_offer_id": 125,
                "intervening_events_count": 120,
                "time_between_days": 120,
                "trace_end_activity": 165,
                "case_duration_days": 115,
            },
        )
        cols_ev = [
            c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "OfferID", "EventID"]
            if c in r22.evidence_events_df.columns
        ]
        self.model_1122_evidence.set_dataframe(
            r22.evidence_events_df[cols_ev].head(100) if cols_ev else r22.evidence_events_df.head(100),
            highlight_activities=["O_Cancelled", "O_Accepted"],
        )

    def _populate_f07(self, b: FullAnalysisBundle) -> None:
        self._on_explorer_group_changed()
        sum_df = build_summary_dataframe(
            b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122
        )
        self.model_export_summary.set_dataframe(sum_df)
        QTimer.singleShot(0, self._resize_summary_table_columns)

    # ------------------------------------------------------------------
    # INTERACTIVE FILTER & DRILL-DOWN HANDLERS
    # ------------------------------------------------------------------
    def _on_filter_f02_cases(self, text: str) -> None:
        self.model_f02_cases.set_filter_text(text)

    def _on_117_group_changed(self) -> None:
        if self.bundle is None:
            return
        idx = self.cmb_117_group.currentIndex()
        r = self.bundle.ex117
        if idx == 0:
            df = r.sub_c.case_df
        elif idx == 1:
            df = r.sub_d.case_df
        elif idx == 2:
            df = r.sub_e.case_df
        else:
            df = r.sub_a.case_df
        self.model_117_cases.set_dataframe(df)
        self._apply_column_widths(
            self.table_117_cases,
            df,
            {
                "case_id": 172,
                "event_count": 85,
                "start_timestamp": 140,
                "end_timestamp": 140,
                "first_activity": 165,
                "last_activity": 165,
                "duration_seconds": 105,
                "duration_hours": 100,
                "duration_days": 115,
                "minmax_duration_days": 115,
                "speed_category": 130,
                "trigger_activity": 145,
                "trigger_count": 95,
            },
        )

    def _on_filter_117_table(self, text: str) -> None:
        self.model_117_cases.set_filter_text(text)

    def _on_filter_1122_table(self, text: str) -> None:
        self.model_1122_cases.set_filter_text(text)

    def _on_select_1115_case(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        df_15 = self.model_1115_cases.get_dataframe()
        cid = str(df_15.iloc[index.row()]["case_id"])
        case_ev = self.bundle.context.get_case_events(cid)
        fraud_ev = case_ev[case_ev["concept:name"].str.lower() == self.bundle.ex1115.target_activity.lower()]
        cols = [c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "EventID"] if c in fraud_ev.columns]
        self.model_15_18_evidence.set_dataframe(
            fraud_ev[cols],
            highlight_activities=[self.bundle.ex1115.target_activity],
            highlight_lifecycle="complete",
        )
        self.lbl_15_18_evidence_title.setText(
            f"11.15 Audit — Case {cid}: showing all '{self.bundle.ex1115.target_activity}' events (Amber = 'complete', Blue = other lifecycle states)."
        )

    def _on_select_1118_case(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        df_18 = self.model_1118_cases.get_dataframe()
        cid = str(df_18.iloc[index.row()]["case_id"])
        rid = str(df_18.iloc[index.row()]["resource_id"])
        case_ev = self.bundle.context.get_case_events(cid)
        fraud_ev = case_ev[case_ev["concept:name"].str.lower() == self.bundle.ex1118.target_activity.lower()]
        cols = [c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "EventID"] if c in fraud_ev.columns]
        self.model_15_18_evidence.set_dataframe(
            fraud_ev[cols],
            highlight_activities=[self.bundle.ex1118.target_activity],
            highlight_lifecycle="complete",
            highlight_resource=rid,
        )
        self.lbl_15_18_evidence_title.setText(
            f"11.18 Audit — Case {cid} (Same Resource: {rid}): amber rows confirm >=2 'complete' executions by {rid}."
        )

    def _on_show_excluded_lifecycle_case(self) -> None:
        if self.bundle is None:
            return
        r15 = self.bundle.ex1115
        if r15.example_excluded_case_id is None or r15.example_excluded_events_df.empty:
            QMessageBox.information(self, "Info", "Tidak ada case yang tereliminasi oleh filter lifecycle complete pada dataset ini.")
            return
        cols = [c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "EventID"] if c in r15.example_excluded_events_df.columns]
        self.model_15_18_evidence.set_dataframe(
            r15.example_excluded_events_df[cols],
            highlight_activities=[r15.target_activity],
            highlight_lifecycle="complete",
        )
        self.lbl_15_18_evidence_title.setText(
            f"Excluded Case Example — {r15.example_excluded_case_id}: {len(r15.example_excluded_events_df)} total '{r15.target_activity}' events, but only 1 'complete' (amber) → excluded by 11.15."
        )

    def _on_show_diff_resource_evidence(self) -> None:
        if self.bundle is None:
            return
        r18 = self.bundle.ex1118
        if r18.excluded_diff_resource_evidence_df.empty:
            QMessageBox.information(self, "Info", "Tidak ada selisih case antara 11.15 dan 11.18.")
            return
        cols = [c for c in ["case:concept:name", "_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "EventID"] if c in r18.excluded_diff_resource_evidence_df.columns]
        self.model_15_18_evidence.set_dataframe(
            r18.excluded_diff_resource_evidence_df[cols],
            highlight_activities=[r18.target_activity],
            highlight_lifecycle="complete",
        )
        self.lbl_15_18_evidence_title.setText(
            f"11.15 vs 11.18 Delta — {len(r18.cases_from_1115_excluded_diff_resource)} cases with >=2 'complete' executions across different/missing resources (excluded from 11.18)."
        )

    def _on_select_1122_case(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        df_22 = self.model_1122_cases.get_dataframe()
        row = index.row()
        if df_22.empty or row < 0 or row >= len(df_22):
            return
        cid = str(df_22.iloc[row]["case_id"])
        ev = self.bundle.context.get_case_events(cid)
        cols = [c for c in ["_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "OfferID", "EventID"] if c in ev.columns]
        self.model_1122_evidence.set_dataframe(
            ev[cols],
            highlight_activities=["O_Cancelled", "O_Accepted"],
        )
        self.lbl_1122_timeline_info.setText(
            f"Full Trace for {cid} ({len(ev)} events): amber rows highlight O_Cancelled followed by O_Accepted."
        )

    # ------------------------------------------------------------------
    # CASE EXPLORER NAVIGATION (F07)
    # ------------------------------------------------------------------
    def _get_selected_case_id_from_table(
        self, table: QTableView, proxy: Optional[Any], model: DataFrameTableModel
    ) -> Optional[str]:
        idxs = table.selectionModel().selectedRows()
        if not idxs:
            curr = table.currentIndex()
            if not curr.isValid():
                return None
            row_idx = proxy.mapToSource(curr).row() if proxy else curr.row()
        else:
            row_idx = proxy.mapToSource(idxs[0]).row() if proxy else idxs[0].row()

        df = model.get_dataframe()
        if df.empty or row_idx < 0 or row_idx >= len(df):
            return None
        col = "case_id" if "case_id" in df.columns else "case:concept:name"
        return str(df.iloc[row_idx][col])

    def _on_inspect_from_f02(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_f02_cases, None, self.model_f02_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=0)

    def _on_inspect_from_117(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_117_cases, None, self.model_117_cases)
        if cid:
            g_map = {0: 1, 1: 2, 2: 3, 3: 0}
            self.open_case_in_explorer(cid, filter_group_index=g_map.get(self.cmb_117_group.currentIndex(), 0))

    def _on_inspect_from_1115(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_1115_cases, None, self.model_1115_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=4)

    def _on_inspect_from_1118(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_1118_cases, None, self.model_1118_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=5)

    def _on_inspect_from_1122(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_1122_cases, None, self.model_1122_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=6)

    def open_case_in_explorer(self, case_id: str, filter_group_index: int = 0) -> None:
        self.switch_page(5)
        self.cmb_explorer_filter.setCurrentIndex(filter_group_index)
        self.txt_explorer_search.setText(case_id)
        self._display_case_trace_in_explorer(case_id)

    def _on_reset_explorer(self) -> None:
        self.cmb_explorer_filter.setCurrentIndex(0)
        self.txt_explorer_search.clear()

    def _on_explorer_search_changed(self, text: str) -> None:
        self.model_explorer_cases.set_filter_text(text)

    def _on_explorer_group_changed(self) -> None:
        if self.bundle is None:
            return
        idx = self.cmb_explorer_filter.currentIndex()
        b = self.bundle
        total = b.overview.total_cases

        if idx == 0:
            df = b.overview.case_table
            rule = f"All Active Applications: {len(df):,} / {total:,} cases (100.00%)"
            self._explorer_highlights = ([], None)
        elif idx == 1:
            df = b.ex117.sub_c.case_df
            rule = f"[11.7 C] Contains('O_Accepted') • Matched: {len(df):,} / {total:,} cases ({b.ex117.sub_c.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Accepted"], None)
        elif idx == 2:
            df = b.ex117.sub_d.case_df
            rule = f"[11.7 D] Contains('O_Refused') • Matched: {len(df):,} / {total:,} cases ({b.ex117.sub_d.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Refused"], None)
        elif idx == 3:
            df = b.ex117.sub_e.case_df
            rule = f"[11.7 E] Endpoint == 'O_Cancelled' • Matched: {len(df):,} / {total:,} cases ({b.ex117.sub_e.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Cancelled"], None)
        elif idx == 4:
            df = b.ex1115.case_summary_df
            rule = f"[11.15] W_Assess potential fraud Complete >= 2x • Matched: {len(df):,} / {total:,} cases ({b.ex1115.matching_percentage:.4f}%)"
            self._explorer_highlights = ([b.ex1115.target_activity], "complete")
        elif idx == 5:
            df = b.ex1118.case_resource_summary_df
            rule = f"[11.18] Same-Resource Complete >= 2x • Matched: {b.ex1118.matching_case_count:,} / {total:,} cases ({b.ex1118.matching_percentage:.4f}%)"
            self._explorer_highlights = ([b.ex1118.target_activity], "complete")
        else:
            df = b.ex1122.case_summary_df
            rule = f"[11.22] O_Cancelled → O_Accepted (i < j) • Matched: {len(df):,} / {total:,} cases ({b.ex1122.matching_percentage:.2f}%)"
            self._explorer_highlights = (["O_Cancelled", "O_Accepted"], None)

        self.lbl_explorer_rule_banner.setText(rule)
        self.model_explorer_cases.set_dataframe(df)
        self._apply_column_widths(
            self.table_explorer_cases,
            df,
            {
                "case_id": 172,
                "event_count": 85,
                "duration_days": 115,
                "case_duration_days": 115,
                "speed_category": 130,
                "first_activity": 160,
                "last_activity": 160,
                "duration_hours": 100,
                "duration_seconds": 105,
                "start_timestamp": 140,
                "end_timestamp": 140,
                "minmax_duration_days": 115,
                "resource_id": 110,
                "same_resource_completions": 135,
                "total_case_completions": 125,
                "complete_occurrences": 110,
                "all_lifecycle_occurrences": 120,
                "resources_involved": 160,
            },
        )
        if not df.empty:
            first_cid = str(df.iloc[0]["case_id"])
            self._display_case_trace_in_explorer(first_cid)

    def _on_explorer_case_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        df = self.model_explorer_cases.get_dataframe()
        row = index.row()
        if not df.empty and 0 <= row < len(df):
            cid = str(df.iloc[row]["case_id"])
            self._display_case_trace_in_explorer(cid)

    def _display_case_trace_in_explorer(self, case_id: str) -> None:
        if self.bundle is None:
            return
        ctx = self.bundle.context
        ev = ctx.get_case_events(case_id)
        if ev.empty:
            return

        cs = ctx.case_summary_df
        if case_id in cs.index:
            row = cs.loc[case_id]
            dur_d = float(row["duration_days"])
            dur_h = float(row["duration_hours"])
            f_act = str(row["first_activity"])
            l_act = str(row["last_activity"])
            meta_txt = (
                f"Case ID: {case_id}  •  Events: {len(ev)}  •  "
                f"Cycle Time: {dur_d:.4f} days ({dur_h:.2f} hr)  •  "
                f"Start: {f_act}  →  End: {l_act}"
            )
        else:
            meta_txt = f"Case ID: {case_id} ({len(ev)} events)"

        self.lbl_explorer_case_meta.setText(meta_txt)

        preferred_cols = [
            "_trace_pos",
            "time:timestamp",
            "concept:name",
            "lifecycle:transition",
            "org:resource",
            "OfferID",
            "EventID",
            "EventOrigin",
            "Action",
        ]
        cols = [c for c in preferred_cols if c in ev.columns]
        extra_cols = [c for c in ev.columns if c not in cols and c not in ("_event_idx", "case:concept:name")]
        final_cols = cols + extra_cols

        hl_acts, hl_lc = getattr(self, "_explorer_highlights", ([], None))
        self.trace_flow_strip.set_events(ev, highlight_activities=hl_acts)
        self.model_explorer_events.set_dataframe(
            ev[final_cols],
            highlight_activities=hl_acts,
            highlight_lifecycle=hl_lc,
        )

    # ------------------------------------------------------------------
    # EXPORT & ABOUT HANDLERS
    # ------------------------------------------------------------------
    def on_export_all(self) -> None:
        if self.bundle is None:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat dan jalankan analisis pada file XES terlebih dahulu.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekspor CSV & HTML", os.getcwd())
        if not out_dir:
            return
        try:
            files = export_all_to_directory(
                out_dir,
                self.bundle.context,
                self.bundle.overview,
                self.bundle.ex117,
                self.bundle.ex1115,
                self.bundle.ex1118,
                self.bundle.ex1122,
            )
            file_list = "\n".join(f"• {k}: {os.path.basename(v)}" for k, v in files.items())
            QMessageBox.information(
                self,
                "Ekspor Berhasil",
                f"Seluruh hasil analisis dan daftar bukti case berhasil diekspor ke:\n{out_dir}\n\nBerkas yang dibuat:\n{file_list}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Mengekspor", str(exc))

    def on_export_summary_csv(self) -> None:
        if self.bundle is None:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat dan jalankan analisis pada file XES terlebih dahulu.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Ringkasan Jawaban ke CSV",
            os.path.join(os.getcwd(), "ringkasan_jawaban_bpic17.csv"),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            df = self.model_export_summary.get_dataframe()
            df.to_csv(path, index=False, encoding="utf-8-sig")
            QMessageBox.information(self, "Berhasil Disimpan", f"Ringkasan jawaban berhasil disimpan ke:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Menyimpan CSV", str(exc))

    def on_show_about(self) -> None:
        env = get_environment_info()
        QMessageBox.information(
            self,
            "Tentang ProcessMine Studio & Reproduktibilitas",
            f"<h3>ProcessMine Studio — Loan Application Process Mining</h3>"
            f"<p>Workbench analitik berbasis Python &amp; PM4Py untuk eksplorasi event log BPIC17 "
            f"(termasuk pemetaan standar Exercise 11.7 A–E, 11.15, 11.18, dan 11.22).</p>"
            f"<p><b>Versi Lingkungan &amp; Dependency Utama:</b></p>"
            f"<ul>"
            f"<li><b>Python:</b> {env['Python']}</li>"
            f"<li><b>PM4Py:</b> {env['PM4Py']}</li>"
            f"<li><b>Pandas:</b> {env['Pandas']}</li>"
            f"<li><b>PySide6 (Qt GUI):</b> {env['PySide6']}</li>"
            f"<li><b>r4pm (XES Parser Accelerator):</b> {env['r4pm (XES accelerator)']}</li>"
            f"</ul>",
        )
