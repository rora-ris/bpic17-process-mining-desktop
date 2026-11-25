"""PySide6 Desktop GUI for BPIC17 Event Log Analyzer following the official UI guide."""

from __future__ import annotations

import os
import re
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTabWidget,
    QTableView,
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


# ==============================================================================
# OFFICIAL LIGHT MODE DESIGN TOKENS
# ==============================================================================
NAVY = "#0B1F5C"
YELLOW = "#FFC700"
BG_CANVAS = "#F5F7FB"
BG_CARD = "#FFFFFF"
BG_SURFACE_MUTED = "#F8FAFC"
BORDER = "#E2E8F0"
BORDER_INPUT = "#CBD5E1"
TEXT_PRIMARY = "#0F172A"
TEXT_MUTED = "#64748B"
GREEN = "#16A34A"
GREEN_BG = "#DCFCE7"
RED = "#DC2626"
RED_BG = "#FEE2E2"
AMBER_BG = "#FEF3C7"
AMBER_TEXT = "#92400E"
AMBER_BORDER = "#FCD34D"
SELECTION_BG = "#EEF2FF"
SELECTION_TEXT = "#1E3A8A"
BLUE_LINK = "#2563EB"

FONT_FAMILY = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

ISO_TS_REGEX = re.compile(
    r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
)

COLUMN_HEADER_MAP: Dict[str, str] = {
    "case_id": "Case ID",
    "case:concept:name": "Case ID",
    "activity": "Aktivitas",
    "concept:name": "Aktivitas",
    "event_count": "Jumlah Event",
    "complete_event_count": "Event Complete",
    "event_percentage": "Persentase Event",
    "event_pct": "Persentase Event",
    "case_count": "Jumlah Case",
    "case_percentage": "Persentase Case",
    "case_pct": "Persentase Case",
    "start_timestamp": "Waktu Mulai",
    "end_timestamp": "Waktu Selesai",
    "first_activity": "Aktivitas Awal",
    "last_activity": "Aktivitas Akhir",
    "duration_seconds": "Durasi (detik)",
    "duration_hours": "Durasi (jam)",
    "duration_days": "Durasi (hari)",
    "case_duration_days": "Durasi (hari)",
    "minmax_duration_days": "Rentang (hari)",
    "speed_category": "Kategori Kecepatan",
    "trigger_activity": "Aktivitas Pemicu",
    "trigger_count": "Kemunculan",
    "complete_occurrences": "Jumlah Complete",
    "all_lifecycle_occurrences": "Semua Lifecycle",
    "resources_involved": "Resource Terlibat",
    "unique_valid_resources": "Resource Unik",
    "case_total_events": "Total Event Case",
    "resource_id": "Resource ID",
    "org:resource": "Resource",
    "same_resource_completions": "Complete Resource Sama",
    "total_case_completions": "Total Complete Case",
    "evidence_event_ids": "Event ID Bukti",
    "first_complete_time": "Complete Pertama",
    "last_complete_time": "Complete Terakhir",
    "_trace_pos": "Urutan",
    "time:timestamp": "Waktu",
    "lifecycle:transition": "Lifecycle",
    "cancelled_trace_pos": "Posisi Cancelled",
    "cancelled_timestamp": "Waktu O_Cancelled",
    "cancelled_offer_id": "Offer ID Cancelled",
    "accepted_trace_pos": "Posisi Accepted",
    "accepted_timestamp": "Waktu O_Accepted",
    "accepted_offer_id": "Offer ID Accepted",
    "intervening_events_count": "Event Perantara",
    "time_between_days": "Selisih (hari)",
    "trace_end_activity": "Aktivitas Akhir",
    "same_offer_id": "Offer ID Sama",
    "OfferID": "Offer ID",
    "EventID": "Event ID",
    "EventOrigin": "Asal Event",
    "Action": "Aksi",
    "Kode Soal": "Kode",
    "Pertanyaan": "Pertanyaan",
    "Aturan / Filter": "Aturan Filter",
    "Jumlah Case Terpilih": "Case Terpilih",
    "Denominator (Total Case Aktif)": "Denominator",
    "Persentase Case (%)": "Persentase",
    "Mean Cycle Time (Hari)": "Rata-rata (hari)",
    "Mean Cycle Time (Jam)": "Rata-rata (jam)",
    "Median Cycle Time (Hari)": "Median (hari)",
    "Jawaban Utama": "Jawaban Utama",
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


# ==============================================================================
# FORMATTING HELPERS (INDONESIAN LOCALE & GLOBAL PRECISION)
# ==============================================================================
def fmt_int(val: Any) -> str:
    """Formats an integer with Indonesian dot thousand separators (e.g. 31.509)."""
    if val is None or pd.isna(val):
        return "—"
    return f"{int(val):,}".replace(",", ".")


def fmt_num(val: Any, precision: int = 2) -> str:
    """Formats a float with Indonesian dot thousands and comma decimal (e.g. 21,90)."""
    if val is None or pd.isna(val):
        return "—"
    raw = f"{float(val):,.{precision}f}"
    return raw.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_pct(val: Any, precision: int = 2) -> str:
    """Formats percentage using Indonesian comma decimal."""
    if val is None or pd.isna(val):
        return "—"
    return f"{fmt_num(val, precision)}%"


def fmt_duration(days: Any, unit: str = "hari", precision: int = 2) -> str:
    """Converts duration in days to active unit ('hari', 'jam', or 'detik') and formats it."""
    if days is None or pd.isna(days):
        return "—"
    d = float(days)
    if unit == "jam":
        return f"{fmt_num(d * 24.0, precision)} jam"
    if unit == "detik":
        return f"{fmt_num(d * 86400.0, precision)} detik"
    return f"{fmt_num(d, precision)} hari"


def format_case_id_middle(cid: Any, max_len: int = 40) -> str:
    """Preserves full Case ID up to max_len; middle-truncates only very long IDs."""
    s = str(cid) if cid is not None else "—"
    if len(s) <= max_len:
        return s
    keep_left = (max_len - 1) // 2
    keep_right = max_len - 1 - keep_left
    return f"{s[:keep_left]}…{s[-keep_right:]}"


def format_timestamp_compact(val_str: str) -> str:
    """Formats verbose ISO timestamps into 'YYYY-MM-DD HH:MM:SS'."""
    s = val_str.strip()
    m = ISO_TS_REGEX.match(s)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return s


def _make_font(pixel_size: int = 12, bold: bool = False) -> QFont:
    f = QFont("Segoe UI")
    f.setPixelSize(pixel_size)
    if bold:
        f.setWeight(QFont.Bold)
    return f


# ==============================================================================
# GLOBAL STYLESHEET (MINIMUM 12px, ISOLATED SELECTORS, ZERO GRADIENTS/SHADOWS)
# ==============================================================================
APP_STYLESHEET = f"""
QMainWindow, QWidget#RootCanvas {{
    background-color: {BG_CANVAS};
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}
QLabel {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
    color: {TEXT_PRIMARY};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}
QFrame#MainHeader {{
    background-color: {NAVY};
    border: none;
}}
QWidget#TabCanvas {{
    background-color: {BG_CANVAS};
}}
QFrame#KartuAngka {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#KartuAngkaSelected {{
    background-color: {SELECTION_BG};
    border: 1px solid {NAVY};
    border-radius: 8px;
}}
QFrame#ChecklistDrawer {{
    background-color: {BG_CARD};
    border: none;
    border-left: 1px solid {BORDER};
}}
QWidget#DrawerInner {{
    background-color: {BG_CARD};
}}
QFrame#DividerH {{
    background-color: {BORDER};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
QFrame#DividerV {{
    background-color: {BORDER};
    border: none;
    max-width: 1px;
    min-width: 1px;
}}
QTabWidget#BodyStack::pane {{
    border: none;
    border-top: 1px solid {BORDER};
    background-color: {BG_CANVAS};
}}
QTabWidget#BodyStack QTabBar {{
    background-color: {BG_CARD};
}}
QTabWidget#BodyStack QTabBar::tab {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    padding: 12px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 15px;
    font-weight: 600;
}}
QTabWidget#BodyStack QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}
QTabWidget#BodyStack QTabBar::tab:selected {{
    color: {NAVY};
    border-bottom: 2px solid {BLUE_LINK};
    font-weight: 700;
}}
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_INPUT};
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {BG_SURFACE_MUTED};
    border-color: {TEXT_MUTED};
}}
QPushButton:disabled {{
    background-color: {BG_SURFACE_MUTED};
    color: {TEXT_MUTED};
    border-color: {BORDER};
}}
QPushButton#HeaderBtn {{
    background-color: #162F7A;
    color: #FFFFFF;
    border: 1px solid #2A4596;
    border-radius: 6px;
    padding: 7px 13px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#HeaderBtn:hover {{
    background-color: #1E3E9B;
}}
QPushButton#HeaderInfoBtn {{
    background-color: #162F7A;
    color: #FFFFFF;
    border: 1px solid #2A4596;
    border-radius: 13px;
    padding: 0px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#HeaderInfoBtn:hover {{
    background-color: #1E3E9B;
}}
QPushButton#ExportYellowBtn {{
    background-color: {YELLOW};
    color: {NAVY};
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#ExportYellowBtn:hover {{
    background-color: #EAB308;
}}
QPushButton#ExportYellowBtn:disabled {{
    background-color: #E2E8F0;
    color: {TEXT_MUTED};
}}
QPushButton#UnitBtn {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_INPUT};
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#UnitBtn:checked {{
    background-color: {NAVY};
    color: #FFFFFF;
    border-color: {NAVY};
}}
QPushButton#LinkBtn {{
    background: transparent;
    border: none;
    color: {BLUE_LINK};
    padding: 2px 0px;
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}
QPushButton#LinkBtn:hover {{
    text-decoration: underline;
}}
QLineEdit, QComboBox {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_INPUT};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}
QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {NAVY};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QMenu {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_INPUT};
    border-radius: 6px;
    padding: 4px;
    font-size: 13px;
}}
QMenu::item {{
    padding: 7px 16px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {SELECTION_BG};
    color: {SELECTION_TEXT};
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    spacing: 8px;
}}
QTableView {{
    background-color: {BG_CARD};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: {BORDER};
    selection-background-color: {SELECTION_BG};
    selection-color: {SELECTION_TEXT};
    font-size: 13px;
}}
QTableView::item {{
    padding: 4px 8px;
}}
QTableCornerButton::section {{
    background-color: {BG_SURFACE_MUTED};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
}}
QHeaderView::section:horizontal {{
    background-color: {BG_SURFACE_MUTED};
    color: {TEXT_MUTED};
    padding: 8px 8px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    font-size: 12px;
    font-weight: 700;
}}
QHeaderView::section:vertical {{
    background-color: {BG_CARD};
    color: {TEXT_MUTED};
    padding: 0px 6px;
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    font-size: 12px;
}}
QProgressBar {{
    background-color: {BORDER};
    border: none;
    border-radius: 4px;
    max-height: 8px;
    min-height: 8px;
}}
QProgressBar::chunk {{
    background-color: {NAVY};
    border-radius: 4px;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_INPUT};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_INPUT};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QDialog {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
}}
"""


# ==============================================================================
# TABLE MODELS & DELEGATES (ALL LEFT-ALIGNED, GLOBAL PRECISION, HIGH SCALE)
# ==============================================================================
class DataFrameTableModel(QAbstractTableModel):
    """Vectorized Qt TableModel supporting 31.509+ rows smoothly with Indonesian formatting."""

    def __init__(
        self,
        df: Optional[pd.DataFrame] = None,
        highlight_activities: Optional[List[str]] = None,
        highlight_lifecycle: Optional[str] = None,
        highlight_resource: Optional[str] = None,
        precision: int = 2,
        duration_unit: str = "hari",
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._source_df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self._df = self._source_df
        self.highlight_activities = [a.lower() for a in (highlight_activities or [])]
        self.highlight_lifecycle = highlight_lifecycle.lower() if highlight_lifecycle else None
        self.highlight_resource = highlight_resource.lower() if highlight_resource else None
        self._precision = precision
        self._duration_unit = duration_unit
        self._bold_font = _make_font(13, bold=True)
        self._filter_text: str = ""
        self._search_corpus: Optional[pd.Series] = None
        self._sort_col: int = -1
        self._sort_order: Qt.SortOrder = Qt.AscendingOrder
        self._col_names: List[str] = []
        self._col_arrays: List[np.ndarray] = []
        self._highlight_states: Optional[np.ndarray] = None
        self._apply_filter_and_sort()

    def set_format_options(self, precision: int, duration_unit: str = "hari") -> None:
        if precision == self._precision and duration_unit == self._duration_unit:
            return
        self._precision = precision
        self._duration_unit = duration_unit
        if not self._df.empty:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._df) - 1, max(len(self._col_names) - 1, 0))
            self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])
            self.headerDataChanged.emit(Qt.Horizontal, 0, max(len(self._col_names) - 1, 0))

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
                return "—"
            if isinstance(val, (bool, np.bool_)):
                return "Ya" if val else "Tidak"
            if col_name in ("case_id", "case:concept:name"):
                return format_case_id_middle(val, max_len=40)
            if isinstance(val, (float, np.floating)):
                f_val = float(val)
                if "percentage" in col_name or "_pct" in col_name or "(%)" in col_name:
                    return fmt_pct(f_val, self._precision)
                if col_name in ("duration_days", "case_duration_days"):
                    if self._duration_unit == "jam":
                        return fmt_num(f_val * 24.0, self._precision)
                    if self._duration_unit == "detik":
                        return fmt_num(f_val * 86400.0, self._precision)
                if "hours" in col_name or "(Jam)" in col_name:
                    return fmt_num(f_val, self._precision)
                if "seconds" in col_name:
                    return fmt_num(f_val, 0 if self._precision <= 2 else 2)
                return fmt_num(f_val, self._precision)
            if isinstance(val, (int, np.integer)):
                return fmt_int(val)
            s_val = str(val)
            if col_name in TIMESTAMP_COLUMNS:
                return format_timestamp_compact(s_val)
            return s_val

        if role == Qt.ToolTipRole:
            if pd.isna(val):
                return "—"
            return str(val)

        if role == Qt.UserRole:
            # Expose lifecycle string for ActivityLifecycleDelegate in Case Explorer
            if col_name == "concept:name" and "lifecycle:transition" in self._col_names:
                lc_idx = self._col_names.index("lifecycle:transition")
                lc_val = self._col_arrays[lc_idx][row]
                return str(lc_val) if not pd.isna(lc_val) else ""
            return None

        if role == Qt.BackgroundRole:
            hl = self._row_highlight_state(row)
            if hl == 2:
                return QColor(AMBER_BG)
            if hl == 1:
                return QColor(SELECTION_BG)
            return QColor(BG_CARD)

        if role == Qt.ForegroundRole:
            hl = self._row_highlight_state(row)
            if hl == 2:
                return QColor(AMBER_TEXT)
            if hl == 1:
                return QColor(SELECTION_TEXT)
            return QColor(TEXT_PRIMARY)

        if role == Qt.FontRole:
            if self._row_highlight_state(row) == 2:
                return self._bold_font
            if col_name in ("Jawaban Utama", "Kode Soal"):
                return self._bold_font

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if self._df.empty:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._col_names):
                raw_col = self._col_names[section]
                if role == Qt.DisplayRole:
                    if raw_col in ("duration_days", "case_duration_days"):
                        return f"Durasi ({self._duration_unit})"
                    return COLUMN_HEADER_MAP.get(raw_col, raw_col)
                if role == Qt.TextAlignmentRole:
                    return int(Qt.AlignLeft | Qt.AlignVCenter)
                if role == Qt.ToolTipRole:
                    return raw_col
        else:
            if role == Qt.DisplayRole:
                return str(section + 1)
        return None


class Simple3ColTableModel(QAbstractTableModel):
    """Lightweight 3-column table model (Case ID, Event, Lolos di) for Case Explorer left panel."""

    HEADERS = ["Case ID", "Event", "Lolos di"]

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._case_ids: List[str] = []
        self._events: List[int] = []
        self._tags: List[str] = []
        self._view_indices: List[int] = []
        self._filter_text: str = ""

    def set_cases(self, case_ids: List[str], event_counts: List[int], tags: List[str]) -> None:
        self.beginResetModel()
        self._case_ids = case_ids
        self._events = event_counts
        self._tags = tags
        self._apply_filter()
        self.endResetModel()

    def set_filter_text(self, text: str) -> None:
        needle = text.strip().lower()
        if needle == self._filter_text:
            return
        self.beginResetModel()
        self._filter_text = needle
        self._apply_filter()
        self.endResetModel()

    def _apply_filter(self) -> None:
        if not self._filter_text:
            self._view_indices = list(range(len(self._case_ids)))
            return
        needle = self._filter_text
        self._view_indices = [
            i for i, cid in enumerate(self._case_ids)
            if needle in cid.lower() or needle in self._tags[i].lower()
        ]

    def case_id_at(self, row: int) -> Optional[str]:
        if 0 <= row < len(self._view_indices):
            return self._case_ids[self._view_indices[row]]
        return None

    def row_of_case_id(self, case_id: str) -> int:
        for row_idx, src_idx in enumerate(self._view_indices):
            if self._case_ids[src_idx] == case_id:
                return row_idx
        return -1

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._view_indices)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return 3

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._view_indices):
            return None
        src_i = self._view_indices[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return format_case_id_middle(self._case_ids[src_i], max_len=40)
            if col == 1:
                return fmt_int(self._events[src_i])
            return self._tags[src_i] or "—"

        if role == Qt.ToolTipRole:
            if col == 0:
                return self._case_ids[src_i]
            if col == 2:
                return self._tags[src_i] or "Tidak masuk kelompok latihan khusus"
            return fmt_int(self._events[src_i])

        if role == Qt.ForegroundRole:
            return QColor(TEXT_PRIMARY) if col != 2 else QColor(TEXT_MUTED)

        if role == Qt.BackgroundRole:
            return QColor(BG_CARD)

        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and 0 <= section < 3:
            if role == Qt.DisplayRole:
                return self.HEADERS[section]
            if role == Qt.TextAlignmentRole:
                return int(Qt.AlignLeft | Qt.AlignVCenter)
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(section + 1)
        return None


class ActivityLifecycleDelegate(QStyledItemDelegate):
    """Renders concept:name with lifecycle sub-text cleanly inside Case Explorer event table."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        bg_brush = index.data(Qt.BackgroundRole)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor(SELECTION_BG))
        elif isinstance(bg_brush, QColor):
            painter.fillRect(option.rect, bg_brush)

        act_text = str(index.data(Qt.DisplayRole) or "")
        lc_text = str(index.data(Qt.UserRole) or "")
        fg_color = index.data(Qt.ForegroundRole)
        main_col = fg_color if isinstance(fg_color, QColor) else QColor(TEXT_PRIMARY)
        is_amber = isinstance(bg_brush, QColor) and bg_brush.name().upper() == AMBER_BG

        rect = option.rect.adjusted(8, 4, -8, -4)
        f_main = _make_font(13, bold=is_amber)
        painter.setFont(f_main)
        painter.setPen(main_col)
        fm_main = QFontMetrics(f_main)
        act_elided = fm_main.elidedText(act_text, Qt.ElideRight, rect.width())
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), 19),
            Qt.AlignLeft | Qt.AlignVCenter,
            act_elided,
        )

        if lc_text:
            f_sub = _make_font(12, bold=False)
            painter.setFont(f_sub)
            painter.setPen(QColor(AMBER_TEXT if is_amber else TEXT_MUTED))
            painter.drawText(
                QRectF(rect.left(), rect.top() + 19, rect.width(), 17),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"lifecycle: {lc_text}",
            )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(220, 44)


# ==============================================================================
# REUSABLE UI & FLAT DATA VISUALIZATION COMPONENTS
# ==============================================================================
class KartuAngka(QFrame):
    """Flat metric card widget (the only card component on main analytical views)."""

    clicked = Signal()

    def __init__(
        self,
        label_text: str,
        value_text: str = "—",
        sub_text: str = "",
        clickable: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._clickable = clickable
        self._selected = False
        self.setObjectName("KartuAngka")
        if clickable:
            self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        self.lbl_value = QLabel(value_text)
        self.lbl_value.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 28px; font-weight: 700;"
        )
        self.lbl_label = QLabel(label_text)
        self.lbl_label.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;"
        )
        self.lbl_sub = QLabel(sub_text)
        self.lbl_sub.setWordWrap(True)
        self.lbl_sub.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;"
        )
        self.lbl_sub.setVisible(bool(sub_text))

        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_label)
        layout.addWidget(self.lbl_sub)

    def update_card(self, value: str, sub_text: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(sub_text)
        self.lbl_sub.setVisible(bool(sub_text))

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setObjectName("KartuAngkaSelected" if selected else "KartuAngka")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event: Any) -> None:
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class BadgeStatus(QLabel):
    """Static status badge pill (never animated)."""

    def __init__(self, text: str = "Siap", state: str = "neutral", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.set_status(text, state)

    def set_status(self, text: str, state: str = "neutral") -> None:
        self.setText(text)
        if state == "valid":
            bg, fg, brd = GREEN_BG, GREEN, GREEN_BG
        elif state == "error":
            bg, fg, brd = RED_BG, RED, RED_BG
        elif state == "loading":
            bg, fg, brd = SELECTION_BG, NAVY, BORDER
        else:
            bg, fg, brd = BG_SURFACE_MUTED, TEXT_MUTED, BORDER
        self.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border: 1px solid {brd}; "
            f"border-radius: 12px; padding: 3px 10px; font-size: 12px; font-weight: 700;"
        )


class ChipStatus(QLabel):
    """Validation attribute chip (Case ID, concept:name, timestamp, lifecycle, resource)."""

    def __init__(self, attr_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._attr_label = attr_label
        self.set_state("neutral")

    def set_state(self, state: str) -> None:
        if state == "valid":
            self.setText(f"✓ {self._attr_label}")
            self.setStyleSheet(
                f"background-color: {GREEN_BG}; color: {GREEN}; border: 1px solid {GREEN_BG}; "
                f"border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600;"
            )
        elif state == "invalid":
            self.setText(f"✕ {self._attr_label}")
            self.setStyleSheet(
                f"background-color: {RED_BG}; color: {RED}; border: 1px solid {RED_BG}; "
                f"border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600;"
            )
        else:
            self.setText(self._attr_label)
            self.setStyleSheet(
                f"background-color: {BG_CARD}; color: {TEXT_MUTED}; border: 1px solid {BORDER}; "
                f"border-radius: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600;"
            )


class BarListWidget(QWidget):
    """Flat horizontal bar chart drawn directly on BG_CANVAS using NAVY #0B1F5C."""

    def __init__(self, empty_msg: str = "Belum ada data dimuat.", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._items: List[Tuple[str, float, str]] = []
        self._empty_msg = empty_msg
        self._row_h = 32
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_items(self, items: List[Tuple[str, float, str]]) -> None:
        self._items = items
        h = max(len(items) * self._row_h + 4, 68)
        self.setMinimumHeight(h)
        self.setMaximumHeight(h)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        if not self._items:
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(_make_font(13))
            painter.drawText(QRectF(0, 0, w, float(self.height())), Qt.AlignLeft | Qt.AlignVCenter, self._empty_msg)
            return

        max_v = max((max(0.0, it[1]) for it in self._items), default=1.0)
        if max_v <= 0:
            max_v = 1.0

        f_lbl = _make_font(13, bold=False)
        f_val = _make_font(12, bold=False)
        fm_lbl = QFontMetrics(f_lbl)
        fm_val = QFontMetrics(f_val)

        for i, (name, val, val_str) in enumerate(self._items):
            y = float(i * self._row_h)
            val_w = float(fm_val.horizontalAdvance(val_str) + 12)
            lbl_max_w = max(w - val_w - 8.0, 60.0)

            painter.setFont(f_lbl)
            painter.setPen(QColor(TEXT_PRIMARY))
            elided = fm_lbl.elidedText(name, Qt.ElideRight, int(lbl_max_w))
            painter.drawText(QRectF(0.0, y, lbl_max_w, 18.0), Qt.AlignLeft | Qt.AlignVCenter, elided)

            painter.setFont(f_val)
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(QRectF(w - val_w, y, val_w, 18.0), Qt.AlignRight | Qt.AlignVCenter, val_str)

            track_y = y + 20.0
            track_h = 7.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(BORDER)))
            painter.drawRoundedRect(QRectF(0.0, track_y, w, track_h), 4.0, 4.0)

            ratio = min(1.0, max(0.0, val / max_v))
            fill_w = max(ratio * w, 4.0 if val > 0 else 0.0)
            if fill_w > 0:
                painter.setBrush(QBrush(QColor(NAVY)))
                painter.drawRoundedRect(QRectF(0.0, track_y, fill_w, track_h), 4.0, 4.0)


class HistogramDurasiWidget(QWidget):
    """Flat duration distribution histogram with red 45-day threshold line."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._durations_days: Optional[np.ndarray] = None
        self._precision = 2
        self._fast_cnt = 0
        self._fast_pct = 0.0
        self._slow_cnt = 0
        self._slow_pct = 0.0
        self.setMinimumHeight(185)
        self.setMaximumHeight(205)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(
        self,
        durations_days: Optional[np.ndarray],
        fast_cnt: int,
        fast_pct: float,
        slow_cnt: int,
        slow_pct: float,
        precision: int = 2,
    ) -> None:
        self._durations_days = durations_days
        self._fast_cnt = fast_cnt
        self._fast_pct = fast_pct
        self._slow_cnt = slow_cnt
        self._slow_pct = slow_pct
        self._precision = precision
        self.update()

    def set_precision(self, precision: int) -> None:
        self._precision = precision
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())

        if self._durations_days is None or len(self._durations_days) == 0:
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(_make_font(13))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignLeft | Qt.AlignVCenter, "Histogram durasi akan tampil setelah event log dimuat.")
            return

        vals = self._durations_days[np.isfinite(self._durations_days) & (self._durations_days >= 0)]
        if len(vals) == 0:
            return

        p99 = float(np.percentile(vals, 99))
        x_max = max(60.0, min(max(p99 * 1.05, 55.0), 120.0))
        clipped = np.clip(vals, 0.0, x_max)
        bins = 24
        counts, edges = np.histogram(clipped, bins=bins, range=(0.0, x_max))
        max_cnt = max(int(counts.max()), 1)

        pad_left = 4.0
        pad_right = 8.0
        pad_top = 24.0
        pad_bottom = 48.0
        plot_w = max(w - pad_left - pad_right, 40.0)
        plot_h = max(h - pad_top - pad_bottom, 40.0)
        base_y = pad_top + plot_h

        # Subtle baseline
        painter.setPen(QPen(QColor(BORDER), 1.0))
        painter.drawLine(QRectF(pad_left, base_y, plot_w, 0).topLeft(), QRectF(pad_left, base_y, plot_w, 0).topRight())

        # Draw histogram bars
        bar_step = plot_w / bins
        bar_w = max(bar_step - 2.0, 2.0)
        painter.setPen(Qt.NoPen)
        for i in range(bins):
            c = int(counts[i])
            if c <= 0:
                continue
            bh = max((c / max_cnt) * plot_h, 2.0)
            bx = pad_left + i * bar_step + 1.0
            by = base_y - bh
            bin_mid = (edges[i] + edges[i + 1]) / 2.0
            painter.setBrush(QBrush(QColor(NAVY if bin_mid < 45.0 else TEXT_MUTED)))
            painter.drawRect(QRectF(bx, by, bar_w, bh))

        # Red vertical threshold line at 45 days
        x_45 = pad_left + (45.0 / x_max) * plot_w
        pen_red = QPen(QColor(RED), 1.5)
        painter.setPen(pen_red)
        painter.drawLine(QRectF(x_45, pad_top - 4.0, 0, plot_h + 6.0).topLeft(), QRectF(x_45, pad_top - 4.0, 0, plot_h + 6.0).bottomLeft())

        painter.setFont(_make_font(12, bold=True))
        painter.drawText(QRectF(min(x_45 + 5.0, w - 95.0), 2.0, 95.0, 18.0), Qt.AlignLeft | Qt.AlignVCenter, "Batas 45 hari")

        # X-axis tick labels
        painter.setFont(_make_font(12))
        painter.setPen(QColor(TEXT_MUTED))
        tick_y = base_y + 4.0
        ticks = [0, 15, 30, 45, int(round(x_max))]
        for t in ticks:
            tx = pad_left + (t / x_max) * plot_w
            lbl_t = f"{t}+ hari" if t == int(round(x_max)) else f"{t}"
            align = Qt.AlignLeft if t == 0 else (Qt.AlignRight if t == int(round(x_max)) else Qt.AlignCenter)
            rx = tx if t == 0 else (tx - 55.0 if t == int(round(x_max)) else tx - 20.0)
            rw = 36.0 if t == 0 else (55.0 if t == int(round(x_max)) else 40.0)
            painter.drawText(QRectF(rx, tick_y, rw, 18.0), align | Qt.AlignVCenter, lbl_t)

        # Bottom summary line (Fast vs Slow, no dots/pipes)
        summary_y = base_y + 26.0
        painter.setFont(_make_font(12))
        painter.setPen(QColor(TEXT_PRIMARY))
        summary_txt = (
            f"Cepat (kurang dari 45 hari): {fmt_int(self._fast_cnt)} case ({fmt_pct(self._fast_pct, self._precision)}), "
            f"Lambat (45 hari ke atas): {fmt_int(self._slow_cnt)} case ({fmt_pct(self._slow_pct, self._precision)})"
        )
        painter.drawText(QRectF(pad_left, summary_y, plot_w, 18.0), Qt.AlignLeft | Qt.AlignVCenter, summary_txt)


class Perbandingan117Widget(QWidget):
    """Flat side-by-side comparison chart for Exercise 11.7 (case share and mean duration)."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._share_items: List[Tuple[str, float, str]] = []
        self._dur_items: List[Tuple[str, float, str]] = []
        self.setMinimumHeight(148)
        self.setMaximumHeight(156)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(
        self,
        share_items: List[Tuple[str, float, str]],
        dur_items: List[Tuple[str, float, str]],
    ) -> None:
        self._share_items = share_items
        self._dur_items = dur_items
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        if not self._share_items and not self._dur_items:
            return

        gap = 32.0
        half_w = max((w - gap) / 2.0, 120.0)

        def draw_group(x0: float, gw: float, title: str, items: List[Tuple[str, float, str]], fixed_max: Optional[float]) -> None:
            painter.setFont(_make_font(13, bold=True))
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(QRectF(x0, 0.0, gw, 20.0), Qt.AlignLeft | Qt.AlignVCenter, title)

            max_v = fixed_max if fixed_max else max((max(0.0, it[1]) for it in items), default=1.0)
            if max_v <= 0:
                max_v = 1.0

            lbl_w = min(155.0, gw * 0.38)
            val_w = 88.0
            track_x = x0 + lbl_w + 8.0
            track_w = max(gw - lbl_w - val_w - 16.0, 30.0)

            f_lbl = _make_font(12)
            f_val = _make_font(12, bold=True)
            fm_lbl = QFontMetrics(f_lbl)

            for idx, (lbl, val, val_str) in enumerate(items):
                ry = 26.0 + idx * 29.0
                painter.setFont(f_lbl)
                painter.setPen(QColor(TEXT_PRIMARY))
                painter.drawText(
                    QRectF(x0, ry, lbl_w, 22.0),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    fm_lbl.elidedText(lbl, Qt.ElideRight, int(lbl_w)),
                )

                bar_y = ry + 7.0
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(BORDER)))
                painter.drawRoundedRect(QRectF(track_x, bar_y, track_w, 8.0), 4.0, 4.0)

                fill_w = max(min(1.0, val / max_v) * track_w, 4.0 if val > 0 else 0.0)
                if fill_w > 0:
                    painter.setBrush(QBrush(QColor(NAVY)))
                    painter.drawRoundedRect(QRectF(track_x, bar_y, fill_w, 8.0), 4.0, 4.0)

                painter.setFont(f_val)
                painter.setPen(QColor(TEXT_PRIMARY))
                painter.drawText(QRectF(track_x + track_w + 8.0, ry, val_w, 22.0), Qt.AlignRight | Qt.AlignVCenter, val_str)

        draw_group(0.0, half_w, "Proporsi kategori terhadap seluruh case", self._share_items, 100.0)
        draw_group(half_w + gap, half_w, "Rata-rata durasi per kelompok (hari)", self._dur_items, None)


class Corong1115Widget(QWidget):
    """Flat 4-stage funnel chart illustrating lifecycle complete and same-resource filtering."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._stages: List[Tuple[str, int, str]] = []
        self.setMinimumHeight(124)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_stages(self, stages: List[Tuple[str, int, str]]) -> None:
        self._stages = stages
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        if not self._stages:
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(_make_font(13))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignLeft | Qt.AlignVCenter, "Corong penyaringan akan tampil setelah dataset dimuat.")
            return

        painter.setFont(_make_font(13, bold=True))
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(QRectF(0, 0, w, 20.0), Qt.AlignLeft | Qt.AlignVCenter, "Corong penyaringan Exercise 11.15 dan 11.18")

        max_cnt = max((max(1, s[1]) for s in self._stages), default=1)
        log_max = float(np.log10(max_cnt + 1.0))

        lbl_w = min(225.0, w * 0.38)
        val_w = 135.0
        track_x = lbl_w + 10.0
        track_w = max(w - lbl_w - val_w - 18.0, 40.0)

        f_lbl = _make_font(12)
        f_val = _make_font(12, bold=True)
        fm_lbl = QFontMetrics(f_lbl)

        for idx, (label, cnt, detail) in enumerate(self._stages):
            ry = 24.0 + idx * 25.0
            painter.setFont(f_lbl)
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(
                QRectF(0.0, ry, lbl_w, 22.0),
                Qt.AlignLeft | Qt.AlignVCenter,
                fm_lbl.elidedText(label, Qt.ElideRight, int(lbl_w)),
            )

            bar_y = ry + 7.0
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(BORDER)))
            painter.drawRoundedRect(QRectF(track_x, bar_y, track_w, 8.0), 4.0, 4.0)

            if cnt > 0 and log_max > 0:
                ratio = float(np.log10(cnt + 1.0)) / log_max
                fill_w = max(ratio * track_w, 8.0)
                painter.setBrush(QBrush(QColor(NAVY)))
                painter.drawRoundedRect(QRectF(track_x, bar_y, fill_w, 8.0), 4.0, 4.0)

            painter.setFont(f_val)
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(QRectF(track_x + track_w + 8.0, ry, val_w, 22.0), Qt.AlignRight | Qt.AlignVCenter, detail)


class Urutan1122Widget(QWidget):
    """Flat visualization for Exercise 11.22: forward vs reverse order + turnaround gap histogram."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._forward_cnt = 0
        self._reverse_cnt = 0
        self._gaps_days: Optional[np.ndarray] = None
        self._precision = 2
        self.setMinimumHeight(130)
        self.setMaximumHeight(138)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, forward_cnt: int, reverse_cnt: int, gaps_days: Optional[np.ndarray], precision: int = 2) -> None:
        self._forward_cnt = forward_cnt
        self._reverse_cnt = reverse_cnt
        self._gaps_days = gaps_days
        self._precision = precision
        self.update()

    def set_precision(self, precision: int) -> None:
        self._precision = precision
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        if self._forward_cnt == 0 and self._reverse_cnt == 0:
            return

        gap = 32.0
        half_w = max((w - gap) / 2.0, 120.0)

        # Left: Forward vs Reverse order comparison
        painter.setFont(_make_font(13, bold=True))
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(QRectF(0.0, 0.0, half_w, 20.0), Qt.AlignLeft | Qt.AlignVCenter, "Perbandingan arah urutan pada case yang memuat keduanya")

        total_both = max(self._forward_cnt + self._reverse_cnt, 1)
        items = [
            ("Lolos 11.22 (Cancelled lalu Accepted)", self._forward_cnt, NAVY),
            ("Urutan terbalik saja (Accepted lalu Cancelled)", self._reverse_cnt, BORDER_INPUT),
        ]
        for idx, (lbl, cnt, col) in enumerate(items):
            ry = 28.0 + idx * 44.0
            pct = (cnt / total_both) * 100.0
            val_str = f"{fmt_int(cnt)} case ({fmt_pct(pct, self._precision)})"
            painter.setFont(_make_font(12))
            painter.setPen(QColor(TEXT_PRIMARY))
            painter.drawText(QRectF(0.0, ry, half_w * 0.64, 18.0), Qt.AlignLeft | Qt.AlignVCenter, lbl)
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(QRectF(half_w * 0.64, ry, half_w * 0.36, 18.0), Qt.AlignRight | Qt.AlignVCenter, val_str)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(BORDER)))
            painter.drawRoundedRect(QRectF(0.0, ry + 22.0, half_w, 9.0), 4.5, 4.5)
            fill_w = max((cnt / total_both) * half_w, 4.0 if cnt > 0 else 0.0)
            if fill_w > 0:
                painter.setBrush(QBrush(QColor(col)))
                painter.drawRoundedRect(QRectF(0.0, ry + 22.0, fill_w, 9.0), 4.5, 4.5)

        # Right: Gap time distribution between O_Cancelled and O_Accepted
        rx0 = half_w + gap
        painter.setFont(_make_font(13, bold=True))
        painter.setPen(QColor(TEXT_PRIMARY))
        painter.drawText(QRectF(rx0, 0.0, half_w, 20.0), Qt.AlignLeft | Qt.AlignVCenter, "Sebaran jeda waktu O_Cancelled ke O_Accepted (hari)")

        if self._gaps_days is None or len(self._gaps_days) == 0:
            painter.setFont(_make_font(12))
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(QRectF(rx0, 30.0, half_w, 60.0), Qt.AlignLeft | Qt.AlignVCenter, "Tidak ada pasangan yang memenuhi pola.")
            return

        vals = self._gaps_days[np.isfinite(self._gaps_days) & (self._gaps_days >= 0)]
        if len(vals) == 0:
            return
        max_g = max(float(np.percentile(vals, 95)), 10.0)
        bins = 16
        counts, _ = np.histogram(np.clip(vals, 0.0, max_g), bins=bins, range=(0.0, max_g))
        max_c = max(int(counts.max()), 1)
        plot_h = 68.0
        base_y = 26.0 + plot_h
        painter.setPen(QPen(QColor(BORDER), 1.0))
        painter.drawLine(QRectF(rx0, base_y, half_w, 0).topLeft(), QRectF(rx0, base_y, half_w, 0).topRight())

        step = half_w / bins
        bw = max(step - 2.0, 2.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(NAVY)))
        for i in range(bins):
            c = int(counts[i])
            if c <= 0:
                continue
            bh = max((c / max_c) * plot_h, 2.0)
            painter.drawRect(QRectF(rx0 + i * step + 1.0, base_y - bh, bw, bh))

        mean_gap = float(np.mean(vals))
        med_gap = float(np.median(vals))
        painter.setFont(_make_font(12))
        painter.setPen(QColor(TEXT_MUTED))
        painter.drawText(
            QRectF(rx0, base_y + 4.0, half_w, 20.0),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"Rata-rata jeda {fmt_num(mean_gap, self._precision)} hari, median {fmt_num(med_gap, self._precision)} hari",
        )


class StripAlur(QWidget):
    """Chronological trace evidence strip rendered directly on canvas with arrow separators."""

    def __init__(self, show_detail: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._show_detail = show_detail
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.setFixedHeight(62 if show_detail else 46)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent; border: none;")
        self._layout = QHBoxLayout(self._container)
        self._layout.setContentsMargins(0, 2, 0, 2)
        self._layout.setSpacing(6)
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self.set_placeholder("Pilih salah satu case pada tabel untuk melihat ringkasan urutan kejadiannya.")

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def set_placeholder(self, text: str) -> None:
        self._clear()
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
        self._layout.addWidget(lbl)
        self._layout.addStretch(1)

    def set_events(
        self,
        ev_df: pd.DataFrame,
        highlight_activities: Optional[List[str]] = None,
        highlight_lifecycle: Optional[str] = None,
        highlight_resource: Optional[str] = None,
        max_chips: int = 8,
    ) -> None:
        self._clear()
        if ev_df.empty or "concept:name" not in ev_df.columns:
            self.set_placeholder("Tidak ada event pada trace terpilih.")
            return

        hl_acts = {a.lower() for a in (highlight_activities or [])}
        hl_lc = highlight_lifecycle.lower() if highlight_lifecycle else None
        hl_res = highlight_resource.lower() if highlight_resource else None

        rows = list(ev_df.iterrows())
        n = len(rows)

        def is_evidence(r_ser: pd.Series) -> bool:
            act = str(r_ser.get("concept:name", "")).strip().lower()
            if act not in hl_acts:
                return False
            if hl_lc and "lifecycle:transition" in r_ser.index:
                if str(r_ser.get("lifecycle:transition", "")).strip().lower() != hl_lc:
                    return False
            if hl_res and "org:resource" in r_ser.index:
                if str(r_ser.get("org:resource", "")).strip().lower() != hl_res:
                    return False
            return True

        if n <= max_chips:
            chosen = list(range(n))
        else:
            ev_indices = [i for i, (_, r) in enumerate(rows) if is_evidence(r)]
            chosen_set: Set[int] = {0, n - 1}
            for idx in ev_indices:
                if len(chosen_set) < max_chips:
                    chosen_set.add(idx)
            if len(chosen_set) < max_chips:
                for i, (_, r) in enumerate(rows):
                    act_s = str(r.get("concept:name", ""))
                    if act_s.startswith("O_") and len(chosen_set) < max_chips:
                        chosen_set.add(i)
            chosen = sorted(chosen_set)

        for k, pos in enumerate(chosen):
            if k > 0:
                gap = pos - chosen[k - 1] - 1
                arrow_txt = f"→ (+{gap}) →" if gap > 0 else "→"
                arr = QLabel(arrow_txt)
                arr.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;")
                self._layout.addWidget(arr)

            row_ser = rows[pos][1]
            act_name = str(row_ser.get("concept:name", ""))
            lc_val = str(row_ser.get("lifecycle:transition", "")) if "lifecycle:transition" in row_ser.index else ""
            res_val = str(row_ser.get("org:resource", "")) if "org:resource" in row_ser.index else ""
            ts_val = format_timestamp_compact(str(row_ser.get("time:timestamp", "")))[:10]
            pos_num = int(row_ser.get("_trace_pos", pos + 1))

            highlighted = is_evidence(row_ser)
            if self._show_detail:
                sub_parts = [p for p in (lc_val, res_val, ts_val) if p and p != "nan"]
                chip_txt = f"{act_name}\n{', '.join(sub_parts)}"
            else:
                chip_txt = f"{pos_num}. {act_name}"

            chip = QLabel(chip_txt)
            chip.setToolTip(f"Urutan {pos_num}: {act_name} ({lc_val}, {res_val}, {ts_val})")
            if highlighted:
                chip.setStyleSheet(
                    f"background-color: {AMBER_BG}; color: {AMBER_TEXT}; border: 1px solid {AMBER_BORDER}; "
                    f"border-radius: 6px; padding: 4px 9px; font-size: 12px; font-weight: 700;"
                )
            else:
                chip.setStyleSheet(
                    f"background-color: {BG_SURFACE_MUTED}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER}; "
                    f"border-radius: 6px; padding: 4px 9px; font-size: 12px; font-weight: 600;"
                )
            self._layout.addWidget(chip)

        self._layout.addStretch(1)


# ==============================================================================
# SLIDE-OVER CHECKLIST DRAWER & DIALOGS
# ==============================================================================
CHECKLIST_ITEMS: List[Tuple[str, str]] = [
    ("app_opened", "Aplikasi dibuka tanpa modifikasi kode."),
    ("bpic17_loaded", "BPIC17 XES diimpor dan overview tampil."),
    ("ex117_ab", "Latihan 11.7 A dan B dapat dijawab."),
    ("ex117_cde", "Latihan 11.7 C, D, E menampilkan filter, jumlah, dan mean durasi."),
    ("ex1115", "Latihan 11.15 menampilkan case dengan dua complete occurrence."),
    ("ex1118", "Latihan 11.18 menampilkan same-resource evidence."),
    ("ex1122", "Latihan 11.22 menampilkan count, persentase, dan event ordering."),
    ("explorer_export", "Case Explorer dan ekspor CSV berfungsi."),
    ("synthetic_loaded", "Log sintetis untuk pengujian edge cases dapat ditunjukkan."),
    ("team_ready", "Seluruh anggota dapat menjelaskan bagian yang dikerjakan."),
]


class ChecklistDrawer(QFrame):
    """Right-side drawer displaying the 10 Lampiran A demonstration items without numbers."""

    count_changed = Signal(int, int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ChecklistDrawer")
        self.setFixedWidth(320)
        self._boxes: Dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Checklist Demonstrasi")
        title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(f"padding: 0px; color: {TEXT_PRIMARY}; font-size: 14px; font-weight: 700;")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.hide)
        hdr.addWidget(title, stretch=1)
        hdr.addWidget(btn_close)
        layout.addLayout(hdr)

        div = QFrame()
        div.setObjectName("DividerH")
        layout.addWidget(div)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("DrawerInner")
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 4, 0)
        inner_l.setSpacing(10)

        for key, desc in CHECKLIST_ITEMS:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(8)
            cb = QCheckBox()
            cb.stateChanged.connect(self._emit_count)
            lbl = QLabel(desc)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px;")
            row.addWidget(cb, alignment=Qt.AlignTop)
            row.addWidget(lbl, stretch=1)
            inner_l.addLayout(row)
            self._boxes[key] = cb

        inner_l.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        self.mark_done("app_opened", True)

    def mark_done(self, key: str, done: bool = True) -> None:
        cb = self._boxes.get(key)
        if cb is not None:
            cb.setChecked(done)

    def _emit_count(self) -> None:
        done_cnt = sum(1 for cb in self._boxes.values() if cb.isChecked())
        self.count_changed.emit(done_cnt, len(self._boxes))


class AboutDialog(QDialog):
    """Displays reproducibility environment versions (Python, PM4Py, Pandas, PySide6, r4pm)."""

    def __init__(self, active_file_path: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Informasi Aplikasi & Reproduktibilitas")
        self.resize(520, 340)
        env = get_environment_info()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl_title = QLabel("BPIC17 Event Log Analyzer")
        lbl_title.setStyleSheet(f"background: transparent; border: none; font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Aplikasi desktop analisis event log proses pengajuan pinjaman BPIC17 "
            "untuk menjawab Latihan Bab 11 FBPM (11.7 A sampai E, 11.15, 11.18, dan 11.22)."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(lbl_desc)

        div = QFrame()
        div.setObjectName("DividerH")
        layout.addWidget(div)

        rows = [
            ("Python", env["Python"]),
            ("PM4Py", env["PM4Py"]),
            ("Pandas", env["Pandas"]),
            ("PySide6", env["PySide6"]),
            ("r4pm", env["r4pm (XES accelerator)"]),
            ("Berkas aktif", active_file_path or "Belum ada berkas dimuat"),
        ]
        for k, v in rows:
            r = QHBoxLayout()
            lk = QLabel(k)
            lk.setFixedWidth(120)
            lk.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
            lv = QLabel(v)
            lv.setWordWrap(True)
            lv.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px;")
            r.addWidget(lk)
            r.addWidget(lv, stretch=1)
            layout.addLayout(r)

        layout.addStretch(1)
        btn_ok = QPushButton("Tutup")
        btn_ok.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)


class AllActivitiesDialog(QDialog):
    """Modal dialog showing all activities with search filter and Indonesian numeric formatting."""

    def __init__(self, activity_df: pd.DataFrame, precision: int = 2, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Semua Aktivitas Event Log")
        self.resize(780, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        lbl = QLabel(f"Daftar Lengkap Aktivitas ({fmt_int(len(activity_df))} aktivitas)")
        lbl.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};")
        layout.addWidget(lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cari nama aktivitas...")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(lambda: self._model.set_filter_text(self._search.text()))
        self._search.textChanged.connect(lambda _: self._timer.start())
        layout.addWidget(self._search)

        self._model = DataFrameTableModel(activity_df, precision=precision)
        table = QTableView()
        table.setModel(self._model)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        for i, col_w in enumerate([250, 110, 120, 120, 110]):
            if i < len(activity_df.columns):
                table.setColumnWidth(i, col_w)
        layout.addWidget(table, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


class CaseDurationDialog(QDialog):
    """Modal dialog listing all 31.509+ cases and their durations with fast Interactive table."""

    open_case_requested = Signal(str)

    def __init__(
        self,
        case_df: pd.DataFrame,
        precision: int = 2,
        duration_unit: str = "hari",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Daftar Case dan Durasi")
        self.resize(1040, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        lbl = QLabel(f"Daftar Case dan Durasi ({fmt_int(len(case_df))} case)")
        lbl.setStyleSheet(f"background: transparent; border: none; font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};")
        top.addWidget(lbl, stretch=1)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Cari Case ID atau aktivitas...")
        self._search.setFixedWidth(280)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(180)
        self._timer.timeout.connect(lambda: self._model.set_filter_text(self._search.text()))
        self._search.textChanged.connect(lambda _: self._timer.start())
        top.addWidget(self._search)

        btn_open = QPushButton("Buka di Case Explorer")
        btn_open.clicked.connect(self._on_open_selected)
        top.addWidget(btn_open)
        layout.addLayout(top)

        self._model = DataFrameTableModel(case_df, precision=precision, duration_unit=duration_unit)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(32)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)
        widths = {
            "case_id": 180,
            "event_count": 95,
            "start_timestamp": 145,
            "end_timestamp": 145,
            "first_activity": 160,
            "last_activity": 160,
            "duration_seconds": 105,
            "duration_hours": 100,
            "duration_days": 110,
            "minmax_duration_days": 110,
            "speed_category": 140,
        }
        for i, col_name in enumerate(case_df.columns):
            self._table.setColumnWidth(i, widths.get(str(col_name), 120))
        self._table.doubleClicked.connect(lambda _: self._on_open_selected())
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_open_selected(self) -> None:
        idxs = self._table.selectionModel().selectedRows()
        row = idxs[0].row() if idxs else self._table.currentIndex().row()
        df = self._model.get_dataframe()
        if 0 <= row < len(df):
            cid = str(df.iloc[row]["case_id"])
            self.open_case_requested.emit(cid)
            self.accept()


class ExportDialog(QDialog):
    """Summary and export dialog showing the 8 mandatory benchmarks plus CSV/HTML export buttons."""

    def __init__(
        self,
        summary_df: pd.DataFrame,
        precision: int,
        on_export_summary: Callable[[], None],
        on_export_all: Callable[[], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Ringkasan Jawaban & Ekspor Hasil")
        self.resize(1300, 740)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        lbl = QLabel("Ringkasan Kedelapan Jawaban Wajib")
        lbl.setStyleSheet(f"background: transparent; border: none; font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};")
        sub = QLabel("Mencakup Exercise 11.7 A sampai E, 11.15, 11.18, dan 11.22 beserta aturan filter serta denominator aktif.")
        sub.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        title_col.addWidget(lbl)
        title_col.addWidget(sub)
        top.addLayout(title_col, stretch=1)

        btn_csv = QPushButton("Simpan Ringkasan (CSV)")
        btn_csv.clicked.connect(on_export_summary)
        btn_all = QPushButton("Ekspor Semua (CSV dan HTML)")
        btn_all.setObjectName("ExportYellowBtn")
        btn_all.clicked.connect(on_export_all)
        top.addWidget(btn_csv)
        top.addWidget(btn_all)
        layout.addLayout(top)

        self._model = DataFrameTableModel(summary_df, precision=precision)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setWordWrap(True)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.verticalHeader().setDefaultSectionSize(52)
        hh = self._table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setSectionResizeMode(QHeaderView.Interactive)
        hh.setStretchLastSection(True)

        widths = {
            "Kode Soal": 72,
            "Pertanyaan": 165,
            "Aturan / Filter": 230,
            "Jumlah Case Terpilih": 94,
            "Denominator (Total Case Aktif)": 94,
            "Persentase Case (%)": 86,
            "Mean Cycle Time (Hari)": 104,
            "Mean Cycle Time (Jam)": 104,
            "Median Cycle Time (Hari)": 98,
            "Jawaban Utama": 200,
        }
        for i, col_name in enumerate(summary_df.columns):
            self._table.setColumnWidth(i, widths.get(str(col_name), 110))
        self._table.resizeRowsToContents()
        layout.addWidget(self._table, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Tutup")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)


# ==============================================================================
# WORKER THREAD & BUNDLE
# ==============================================================================
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

            self.progress_changed.emit("Menghitung ringkasan event log dan durasi case...")
            ov = analyze_overview(ctx)

            self.progress_changed.emit("Menghitung hasil Exercise 11.7...")
            r117 = analyze_exercise_11_7(ctx)

            self.progress_changed.emit("Menghitung hasil Exercise 11.15...")
            r1115 = analyze_exercise_11_15(ctx)

            self.progress_changed.emit("Menghitung hasil Exercise 11.18...")
            r1118 = analyze_exercise_11_18(ctx)

            self.progress_changed.emit("Menghitung hasil Exercise 11.22...")
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


# ==============================================================================
# MAIN WINDOW (HEADER 64px + 5 TABS + CHECKLIST DRAWER)
# ==============================================================================
class MainWindow(QMainWindow):
    """Main Desktop GUI Window for BPIC17 Event Log Analyzer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BPIC17 Event Log Analyzer")
        self.resize(1400, 880)
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(APP_STYLESHEET)

        self.bundle: Optional[FullAnalysisBundle] = None
        self.worker: Optional[AnalysisWorker] = None
        self._precision: int = 2
        self._duration_unit: str = "hari"
        self._117_active_idx: int = 2  # Default 11.7 C
        self._1518_mode: str = "11.15"
        self._explorer_highlights: Tuple[List[str], Optional[str]] = ([], None)
        self._current_explorer_case_id: Optional[str] = None
        self._explorer_tags_map: Dict[str, str] = {}

        self._init_ui()

    @staticmethod
    def _configure_table(
        table: QTableView,
        row_height: int = 32,
        interactive_columns: bool = False,
        hide_vertical_header: bool = False,
    ) -> None:
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setShowGrid(True)
        table.verticalHeader().setDefaultSectionSize(row_height)
        table.verticalHeader().setVisible(not hide_vertical_header)
        hh = table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        if interactive_columns:
            hh.setSectionResizeMode(QHeaderView.Interactive)
            hh.setDefaultSectionSize(130)
            hh.setMinimumSectionSize(60)
        else:
            hh.setSectionResizeMode(QHeaderView.ResizeToContents)
        hh.setStretchLastSection(True)
        hh.setHighlightSections(False)

    @staticmethod
    def _apply_column_widths(
        table: QTableView,
        df: pd.DataFrame,
        width_map: Dict[str, int],
        default_width: int = 125,
    ) -> None:
        if df.empty:
            return
        for i, col_name in enumerate(df.columns):
            table.setColumnWidth(i, width_map.get(str(col_name), default_width))

    def _init_ui(self) -> None:
        central = QWidget()
        central.setObjectName("RootCanvas")
        self.setCentralWidget(central)

        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # 1. Flat Navy Header (64 px)
        root_v.addWidget(self._build_header())

        # 2. Body Split (5 Tabs + Slide-Over ChecklistDrawer)
        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("BodyStack")
        self.tabs.tabBar().setExpanding(False)
        body_row.addWidget(self.tabs, stretch=1)

        self.drawer = ChecklistDrawer()
        self.drawer.setVisible(False)
        self.drawer.count_changed.connect(self._on_checklist_count_changed)
        body_row.addWidget(self.drawer)

        root_v.addLayout(body_row, stretch=1)

        self._build_tab_data()
        self._build_tab_117()
        self._build_tab_1115_1118()
        self._build_tab_1122()
        self._build_tab_case_explorer()

        self._on_checklist_count_changed(1, len(CHECKLIST_ITEMS))

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("MainHeader")
        header.setFixedHeight(64)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(12)

        lbl_title = QLabel("BPIC17 Analyzer")
        lbl_title.setStyleSheet("background: transparent; border: none; color: #FFFFFF; font-size: 18px; font-weight: 700;")
        hl.addWidget(lbl_title)

        btn_info = QPushButton("ⓘ")
        btn_info.setObjectName("HeaderInfoBtn")
        btn_info.setFixedSize(26, 26)
        btn_info.setCursor(Qt.PointingHandCursor)
        btn_info.setToolTip("Informasi aplikasi dan versi lingkungan")
        btn_info.clicked.connect(self.on_show_about)
        hl.addWidget(btn_info)

        self.lbl_header_file = QLabel("Belum ada berkas dimuat")
        self.lbl_header_file.setStyleSheet("background: transparent; border: none; color: #CBD5E1; font-size: 13px; padding-left: 6px;")
        hl.addWidget(self.lbl_header_file)
        hl.addStretch(1)

        self.btn_checklist = QPushButton("Checklist 1/10")
        self.btn_checklist.setObjectName("HeaderBtn")
        self.btn_checklist.setCursor(Qt.PointingHandCursor)
        self.btn_checklist.clicked.connect(self._toggle_drawer)
        hl.addWidget(self.btn_checklist)

        self.btn_data_menu = QPushButton("Ganti data ▾")
        self.btn_data_menu.setObjectName("HeaderBtn")
        self.btn_data_menu.setCursor(Qt.PointingHandCursor)
        data_menu = QMenu(self)
        act_imp = QAction("Impor Berkas XES...", self)
        act_imp.triggered.connect(self.on_browse_xes)
        act_bpic = QAction("Muat Dataset Utama BPIC17", self)
        act_bpic.triggered.connect(self.on_load_default_bpic17)
        act_syn = QAction("Muat Log Sintetis (Edge Cases)", self)
        act_syn.triggered.connect(self.on_load_synthetic_log)
        self.act_rerun_menu = QAction("Jalankan Ulang Semua Analisis", self)
        self.act_rerun_menu.setEnabled(False)
        self.act_rerun_menu.triggered.connect(self.on_rerun_all)
        data_menu.addAction(act_imp)
        data_menu.addAction(act_bpic)
        data_menu.addAction(act_syn)
        data_menu.addSeparator()
        data_menu.addAction(self.act_rerun_menu)
        self.btn_data_menu.setMenu(data_menu)
        hl.addWidget(self.btn_data_menu)

        self.btn_export = QPushButton("Ekspor")
        self.btn_export.setObjectName("ExportYellowBtn")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.on_open_export_dialog)
        hl.addWidget(self.btn_export)

        return header

    def _toggle_drawer(self) -> None:
        self.drawer.setVisible(not self.drawer.isVisible())

    def _on_checklist_count_changed(self, done: int, total: int) -> None:
        self.btn_checklist.setText(f"Checklist {done}/{total}")

    # ------------------------------------------------------------------
    # TAB 1: DATA (F01 & F02)
    # ------------------------------------------------------------------
    def _build_tab_data(self) -> None:
        tab = QWidget()
        tab.setObjectName("TabCanvas")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(12)

        # Status bar row (single place for load status)
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.badge_data_status = BadgeStatus("Siap", "neutral")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.lbl_data_status_msg = QLabel("Pilih berkas XES melalui menu Ganti data untuk memulai analisis.")
        self.lbl_data_status_msg.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        status_row.addWidget(self.badge_data_status)
        status_row.addWidget(self.progress_bar)
        status_row.addWidget(self.lbl_data_status_msg, stretch=1)

        btn_quick_bpic = QPushButton("Muat BPIC17")
        btn_quick_bpic.setCursor(Qt.PointingHandCursor)
        btn_quick_bpic.clicked.connect(self.on_load_default_bpic17)
        btn_quick_import = QPushButton("Impor XES")
        btn_quick_import.setCursor(Qt.PointingHandCursor)
        btn_quick_import.clicked.connect(self.on_browse_xes)
        status_row.addWidget(btn_quick_bpic)
        status_row.addWidget(btn_quick_import)
        layout.addLayout(status_row)

        # 5 KartuAngka
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        self.card_data_cases = KartuAngka("Case")
        self.card_data_events = KartuAngka("Event")
        self.card_data_acts = KartuAngka("Aktivitas")
        self.card_data_res = KartuAngka("Resource unik")
        self.card_data_mean = KartuAngka("Rata-rata durasi")
        for c in (self.card_data_cases, self.card_data_events, self.card_data_acts, self.card_data_res, self.card_data_mean):
            cards_row.addWidget(c)
        layout.addLayout(cards_row)

        # 5 Attribute Validation Chips
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)
        lbl_chips = QLabel("Validasi atribut:")
        lbl_chips.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
        chips_row.addWidget(lbl_chips)
        self.chip_case_id = ChipStatus("Case ID")
        self.chip_concept = ChipStatus("concept:name")
        self.chip_ts = ChipStatus("timestamp")
        self.chip_lc = ChipStatus("lifecycle")
        self.chip_res = ChipStatus("resource")
        for ch in (self.chip_case_id, self.chip_concept, self.chip_ts, self.chip_lc, self.chip_res):
            chips_row.addWidget(ch)
        chips_row.addStretch(1)
        layout.addLayout(chips_row)

        div_top = QFrame()
        div_top.setObjectName("DividerH")
        layout.addWidget(div_top)

        # Two-column content directly on BG_CANVAS (no card wrappers)
        cols = QHBoxLayout()
        cols.setSpacing(24)

        # Left column: Aktivitas terbanyak + Distribusi lifecycle
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        act_hdr = QHBoxLayout()
        lbl_act_title = QLabel("Aktivitas terbanyak")
        lbl_act_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
        self.btn_all_activities = QPushButton("Lihat semua aktivitas")
        self.btn_all_activities.setObjectName("LinkBtn")
        self.btn_all_activities.setCursor(Qt.PointingHandCursor)
        self.btn_all_activities.setEnabled(False)
        self.btn_all_activities.clicked.connect(self._on_open_all_activities)
        act_hdr.addWidget(lbl_act_title, stretch=1)
        act_hdr.addWidget(self.btn_all_activities)
        left_col.addLayout(act_hdr)

        self.bar_top_activities = BarListWidget("Belum ada aktivitas yang dimuat.")
        left_col.addWidget(self.bar_top_activities)

        div_left = QFrame()
        div_left.setObjectName("DividerH")
        left_col.addWidget(div_left)

        lbl_lc_title = QLabel("Distribusi lifecycle")
        lbl_lc_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
        left_col.addWidget(lbl_lc_title)

        self.bar_lifecycle = BarListWidget("Distribusi lifecycle akan tampil setelah log dimuat.")
        left_col.addWidget(self.bar_lifecycle)
        left_col.addStretch(1)
        cols.addLayout(left_col, stretch=5)

        div_v = QFrame()
        div_v.setObjectName("DividerV")
        cols.addWidget(div_v)

        # Right column: Durasi case + Unit toggle + Global Ketelitian + Histogram
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        dur_hdr = QHBoxLayout()
        dur_hdr.setSpacing(8)
        lbl_dur_title = QLabel("Durasi case")
        lbl_dur_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
        dur_hdr.addWidget(lbl_dur_title, stretch=1)

        self._unit_group = QButtonGroup(self)
        self._unit_group.setExclusive(True)
        for u_key, u_label in [("hari", "Hari"), ("jam", "Jam"), ("detik", "Detik")]:
            ub = QPushButton(u_label)
            ub.setObjectName("UnitBtn")
            ub.setCheckable(True)
            ub.setChecked(u_key == "hari")
            ub.setCursor(Qt.PointingHandCursor)
            ub.clicked.connect(lambda _c, u=u_key: self._on_unit_changed(u))
            self._unit_group.addButton(ub)
            dur_hdr.addWidget(ub)

        lbl_prec = QLabel("Ketelitian")
        lbl_prec.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px; padding-left: 6px;")
        self.cmb_precision = QComboBox()
        self.cmb_precision.addItems(["2 desimal", "4 desimal"])
        self.cmb_precision.currentIndexChanged.connect(self._on_precision_changed)
        dur_hdr.addWidget(lbl_prec)
        dur_hdr.addWidget(self.cmb_precision)

        self.btn_case_durations = QPushButton("Daftar case dan durasi")
        self.btn_case_durations.setObjectName("LinkBtn")
        self.btn_case_durations.setCursor(Qt.PointingHandCursor)
        self.btn_case_durations.setEnabled(False)
        self.btn_case_durations.clicked.connect(self._on_open_case_durations)
        dur_hdr.addWidget(self.btn_case_durations)
        right_col.addLayout(dur_hdr)

        # 5 separate label-value rows (no dot/pipe concatenation)
        self._dur_labels: Dict[str, QLabel] = {}
        for key, label in [
            ("min", "Minimum"),
            ("median", "Median"),
            ("max", "Maksimum"),
            ("std", "Simpangan baku"),
            ("range", "Rentang waktu"),
        ]:
            r_box = QHBoxLayout()
            lk = QLabel(label)
            lk.setFixedWidth(140)
            lk.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
            lv = QLabel("—")
            lv.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 600;")
            r_box.addWidget(lk)
            r_box.addWidget(lv, stretch=1)
            right_col.addLayout(r_box)
            self._dur_labels[key] = lv

        div_r = QFrame()
        div_r.setObjectName("DividerH")
        right_col.addWidget(div_r)

        lbl_hist = QLabel("Sebaran durasi case terhadap batas 45 hari")
        lbl_hist.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        right_col.addWidget(lbl_hist)

        self.histogram_durasi = HistogramDurasiWidget()
        right_col.addWidget(self.histogram_durasi)
        right_col.addStretch(1)

        cols.addLayout(right_col, stretch=6)
        layout.addLayout(cols, stretch=1)

        self.tabs.addTab(tab, "Data")

    # ------------------------------------------------------------------
    # TAB 2: EXERCISE 11.7 (F03)
    # ------------------------------------------------------------------
    def _build_tab_117(self) -> None:
        tab = QWidget()
        tab.setObjectName("TabCanvas")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 5 KartuAngka sejajar
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_117a = KartuAngka("11.7 A Total case", clickable=True)
        self.card_117b = KartuAngka("11.7 B Rata-rata durasi", clickable=True)
        self.card_117c = KartuAngka("11.7 C Berhasil", clickable=True)
        self.card_117d = KartuAngka("11.7 D Tidak berhasil", clickable=True)
        self.card_117e = KartuAngka("11.7 E Dibatalkan", clickable=True)
        self._cards_117 = [self.card_117a, self.card_117b, self.card_117c, self.card_117d, self.card_117e]
        for idx, c in enumerate(self._cards_117):
            c.clicked.connect(lambda i=idx: self._on_select_117_card(i))
            cards.addWidget(c)
        self.card_117c.set_selected(True)
        layout.addLayout(cards)

        # Diagnostic comparison notes
        self.lbl_117_notes = QLabel(
            "Aturan filter: 11.7 C dan 11.7 D menggunakan aturan contains, sedangkan 11.7 E memeriksa event terakhir trace."
        )
        self.lbl_117_notes.setWordWrap(True)
        self.lbl_117_notes.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(self.lbl_117_notes)

        # Visualization: Proporsi & Perbandingan Rata-rata Durasi
        self.viz_117 = Perbandingan117Widget()
        layout.addWidget(self.viz_117)

        div_117 = QFrame()
        div_117.setObjectName("DividerH")
        layout.addWidget(div_117)

        # Controls row
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self.cmb_117_group = QComboBox()
        self.cmb_117_group.addItems([
            "11.7 A Seluruh case aktif",
            "11.7 B Seluruh case aktif (durasi)",
            "11.7 C Berhasil (memuat O_Accepted)",
            "11.7 D Tidak berhasil (memuat O_Refused)",
            "11.7 E Dibatalkan (event terakhir O_Cancelled)",
        ])
        self.cmb_117_group.setCurrentIndex(2)
        self.cmb_117_group.currentIndexChanged.connect(self._on_117_combo_changed)
        ctrl.addWidget(self.cmb_117_group)

        self.txt_117_search = QLineEdit()
        self.txt_117_search.setPlaceholderText("Cari Case ID atau aktivitas...")
        self._timer_117 = QTimer(self)
        self._timer_117.setSingleShot(True)
        self._timer_117.setInterval(180)
        self._timer_117.timeout.connect(lambda: self.model_117_cases.set_filter_text(self.txt_117_search.text()))
        self.txt_117_search.textChanged.connect(lambda _: self._timer_117.start())
        ctrl.addWidget(self.txt_117_search, stretch=1)

        btn_exp_117 = QPushButton("Buka di Case Explorer")
        btn_exp_117.setCursor(Qt.PointingHandCursor)
        btn_exp_117.clicked.connect(self._on_inspect_from_117)
        btn_csv_117 = QPushButton("Ekspor CSV soal ini")
        btn_csv_117.setCursor(Qt.PointingHandCursor)
        btn_csv_117.clicked.connect(self._on_export_117_csv)
        btn_rerun_117 = QPushButton("Jalankan ulang")
        btn_rerun_117.setCursor(Qt.PointingHandCursor)
        btn_rerun_117.clicked.connect(self.on_rerun_all)
        ctrl.addWidget(btn_exp_117)
        ctrl.addWidget(btn_csv_117)
        ctrl.addWidget(btn_rerun_117)
        layout.addLayout(ctrl)

        self.model_117_cases = DataFrameTableModel(precision=self._precision, duration_unit=self._duration_unit)
        self.table_117_cases = QTableView()
        self.table_117_cases.setModel(self.model_117_cases)
        self._configure_table(self.table_117_cases, row_height=32, interactive_columns=True, hide_vertical_header=True)
        self.table_117_cases.setSortingEnabled(True)
        self.table_117_cases.clicked.connect(self._on_select_117_row)
        self.table_117_cases.doubleClicked.connect(lambda _: self._on_inspect_from_117())
        layout.addWidget(self.table_117_cases, stretch=1)

        self.strip_117 = StripAlur(show_detail=False)
        layout.addWidget(self.strip_117)

        self.tabs.addTab(tab, "Exercise 11.7")

    # ------------------------------------------------------------------
    # TAB 3: EXERCISE 11.15 & 11.18 (F04 & F05)
    # ------------------------------------------------------------------
    def _build_tab_1115_1118(self) -> None:
        tab = QWidget()
        tab.setObjectName("TabCanvas")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        self.card_1115 = KartuAngka("11.15 Fraud complete minimal 2 kali", clickable=True)
        self.card_1118 = KartuAngka("11.18 Resource sama minimal 2 kali", clickable=True)
        self.card_1115.set_selected(True)
        self.card_1115.clicked.connect(lambda: self._on_switch_1518_mode("11.15"))
        self.card_1118.clicked.connect(lambda: self._on_switch_1518_mode("11.18"))
        top_row.addWidget(self.card_1115, stretch=3)
        top_row.addWidget(self.card_1118, stretch=3)

        self.funnel_1115 = Corong1115Widget()
        top_row.addWidget(self.funnel_1115, stretch=5)
        layout.addLayout(top_row)

        div_1518 = QFrame()
        div_1518.setObjectName("DividerH")
        layout.addWidget(div_1518)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)

        self.chk_show_excluded_1518 = QCheckBox("Tampilkan case yang tidak lolos")
        self.chk_show_excluded_1518.stateChanged.connect(self._refresh_1518_table)
        ctrl.addWidget(self.chk_show_excluded_1518)

        self.lbl_1518_rule = QLabel("Menampilkan case dengan W_Assess potential fraud berstatus complete minimal 2 kali.")
        self.lbl_1518_rule.setWordWrap(True)
        self.lbl_1518_rule.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        ctrl.addWidget(self.lbl_1518_rule, stretch=1)

        btn_exp_1518 = QPushButton("Buka di Case Explorer")
        btn_exp_1518.setCursor(Qt.PointingHandCursor)
        btn_exp_1518.clicked.connect(self._on_inspect_from_1518)
        btn_csv_1518 = QPushButton("Ekspor CSV soal ini")
        btn_csv_1518.setCursor(Qt.PointingHandCursor)
        btn_csv_1518.clicked.connect(self._on_export_1518_csv)
        btn_rerun_1518 = QPushButton("Jalankan ulang")
        btn_rerun_1518.setCursor(Qt.PointingHandCursor)
        btn_rerun_1518.clicked.connect(self.on_rerun_all)
        ctrl.addWidget(btn_exp_1518)
        ctrl.addWidget(btn_csv_1518)
        ctrl.addWidget(btn_rerun_1518)
        layout.addLayout(ctrl)

        self.model_1518_cases = DataFrameTableModel(precision=self._precision, duration_unit=self._duration_unit)
        self.table_1518_cases = QTableView()
        self.table_1518_cases.setModel(self.model_1518_cases)
        self._configure_table(self.table_1518_cases, row_height=32, interactive_columns=True, hide_vertical_header=True)
        self.table_1518_cases.setSortingEnabled(True)
        self.table_1518_cases.clicked.connect(self._on_select_1518_row)
        self.table_1518_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1518())
        layout.addWidget(self.table_1518_cases, stretch=1)

        lbl_strip_hdr = QLabel("Jejak bukti aktivitas W_Assess potential fraud pada case terpilih")
        lbl_strip_hdr.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 700;")
        layout.addWidget(lbl_strip_hdr)

        self.strip_1518 = StripAlur(show_detail=True)
        layout.addWidget(self.strip_1518)

        self.tabs.addTab(tab, "Exercise 11.15 && 11.18")

    # ------------------------------------------------------------------
    # TAB 4: EXERCISE 11.22 (F06)
    # ------------------------------------------------------------------
    def _build_tab_1122(self) -> None:
        tab = QWidget()
        tab.setObjectName("TabCanvas")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Giant answer row + percentage + status badge + denominator badge
        ans_row = QHBoxLayout()
        ans_row.setSpacing(14)
        self.lbl_22_ans = QLabel("—")
        self.lbl_22_ans.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 38px; font-weight: 700;")
        ans_row.addWidget(self.lbl_22_ans)

        self.lbl_22_pct = QLabel("")
        self.lbl_22_pct.setStyleSheet(f"background: transparent; border: none; color: {NAVY}; font-size: 20px; font-weight: 700;")
        ans_row.addWidget(self.lbl_22_pct)

        self.badge_22_yesno = BadgeStatus("Belum dihitung", "neutral")
        ans_row.addWidget(self.badge_22_yesno)

        self.lbl_22_denom = QLabel("")
        self.lbl_22_denom.setStyleSheet(
            f"background-color: {BG_CARD}; color: {TEXT_MUTED}; border: 1px solid {BORDER}; "
            f"border-radius: 12px; padding: 3px 10px; font-size: 12px; font-weight: 600;"
        )
        self.lbl_22_denom.setVisible(False)
        ans_row.addWidget(self.lbl_22_denom)
        ans_row.addStretch(1)
        layout.addLayout(ans_row)

        self.lbl_22_rule = QLabel(
            "Aturan eventually follows pada level trace: terdapat posisi i lebih kecil dari j sehingga kejadian ke-i adalah O_Cancelled dan kejadian ke-j adalah O_Accepted (tidak harus bersebelahan)."
        )
        self.lbl_22_rule.setWordWrap(True)
        self.lbl_22_rule.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(self.lbl_22_rule)

        # Visualization: Forward vs Reverse & Gap Distribution
        self.viz_1122 = Urutan1122Widget()
        layout.addWidget(self.viz_1122)

        # Separate additional analysis block (OfferID level)
        self.lbl_22_offer_note = QLabel("Analisis tambahan (Level OfferID): belum ada data dimuat.")
        self.lbl_22_offer_note.setWordWrap(True)
        self.lbl_22_offer_note.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 13px;")
        layout.addWidget(self.lbl_22_offer_note)

        div_22 = QFrame()
        div_22.setObjectName("DividerH")
        layout.addWidget(div_22)

        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)
        self.txt_1122_search = QLineEdit()
        self.txt_1122_search.setPlaceholderText("Cari Case ID atau Offer ID...")
        self._timer_1122 = QTimer(self)
        self._timer_1122.setSingleShot(True)
        self._timer_1122.setInterval(180)
        self._timer_1122.timeout.connect(lambda: self.model_1122_cases.set_filter_text(self.txt_1122_search.text()))
        self.txt_1122_search.textChanged.connect(lambda _: self._timer_1122.start())
        ctrl.addWidget(self.txt_1122_search, stretch=1)

        btn_exp_22 = QPushButton("Buka di Case Explorer")
        btn_exp_22.setCursor(Qt.PointingHandCursor)
        btn_exp_22.clicked.connect(self._on_inspect_from_1122)
        btn_csv_22 = QPushButton("Ekspor CSV soal ini")
        btn_csv_22.setCursor(Qt.PointingHandCursor)
        btn_csv_22.clicked.connect(self._on_export_1122_csv)
        btn_rerun_22 = QPushButton("Jalankan ulang")
        btn_rerun_22.setCursor(Qt.PointingHandCursor)
        btn_rerun_22.clicked.connect(self.on_rerun_all)
        ctrl.addWidget(btn_exp_22)
        ctrl.addWidget(btn_csv_22)
        ctrl.addWidget(btn_rerun_22)
        layout.addLayout(ctrl)

        self.model_1122_cases = DataFrameTableModel(precision=self._precision, duration_unit=self._duration_unit)
        self.table_1122_cases = QTableView()
        self.table_1122_cases.setModel(self.model_1122_cases)
        self._configure_table(self.table_1122_cases, row_height=32, interactive_columns=True, hide_vertical_header=True)
        self.table_1122_cases.setSortingEnabled(True)
        self.table_1122_cases.clicked.connect(self._on_select_1122_row)
        self.table_1122_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1122())
        layout.addWidget(self.table_1122_cases, stretch=1)

        self.strip_1122 = StripAlur(show_detail=False)
        layout.addWidget(self.strip_1122)

        self.tabs.addTab(tab, "Exercise 11.22")

    # ------------------------------------------------------------------
    # TAB 5: CASE EXPLORER (F07)
    # ------------------------------------------------------------------
    def _build_tab_case_explorer(self) -> None:
        tab = QWidget()
        tab.setObjectName("TabCanvas")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)

        # Left Panel (430 px): Search, cohort dropdown, Reset, 3-column table
        left_panel = QWidget()
        left_panel.setMinimumWidth(380)
        ll = QVBoxLayout(left_panel)
        ll.setContentsMargins(0, 0, 12, 0)
        ll.setSpacing(10)

        self.txt_explorer_search = QLineEdit()
        self.txt_explorer_search.setPlaceholderText("Cari Case ID...")
        self._timer_exp = QTimer(self)
        self._timer_exp.setSingleShot(True)
        self._timer_exp.setInterval(180)
        self._timer_exp.timeout.connect(lambda: self.model_explorer_cases.set_filter_text(self.txt_explorer_search.text()))
        self.txt_explorer_search.textChanged.connect(lambda _: self._timer_exp.start())
        ll.addWidget(self.txt_explorer_search)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.cmb_explorer_filter = QComboBox()
        self.cmb_explorer_filter.addItems([
            "Semua case",
            "11.7 C Berhasil (O_Accepted)",
            "11.7 D Tidak berhasil (O_Refused)",
            "11.7 E Dibatalkan (O_Cancelled)",
            "11.15 Fraud 2x complete",
            "11.18 Fraud 2x resource sama",
            "11.22 Cancelled lalu Accepted",
        ])
        self.cmb_explorer_filter.currentIndexChanged.connect(self._on_explorer_group_changed)
        btn_reset = QPushButton("Reset")
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.clicked.connect(self._on_reset_explorer)
        filter_row.addWidget(self.cmb_explorer_filter, stretch=1)
        filter_row.addWidget(btn_reset)
        ll.addLayout(filter_row)

        self.lbl_explorer_rule = QLabel("Menampilkan seluruh case pada event log.")
        self.lbl_explorer_rule.setWordWrap(True)
        self.lbl_explorer_rule.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 12px;")
        ll.addWidget(self.lbl_explorer_rule)

        self.model_explorer_cases = Simple3ColTableModel()
        self.table_explorer_cases = QTableView()
        self.table_explorer_cases.setModel(self.model_explorer_cases)
        self._configure_table(self.table_explorer_cases, row_height=32, interactive_columns=True, hide_vertical_header=True)
        self.table_explorer_cases.setColumnWidth(0, 185)
        self.table_explorer_cases.setColumnWidth(1, 70)
        self.table_explorer_cases.setColumnWidth(2, 145)
        self.table_explorer_cases.clicked.connect(self._on_explorer_case_clicked)
        ll.addWidget(self.table_explorer_cases, stretch=1)
        splitter.addWidget(left_panel)

        # Right Panel: Case summary + optional IDs checkbox + StripAlur + Event Table with Delegate
        right_panel = QWidget()
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(12, 0, 0, 0)
        rl.setSpacing(10)

        meta_hdr = QHBoxLayout()
        self.lbl_explorer_case_title = QLabel("Pilih salah satu case di sebelah kiri")
        self.lbl_explorer_case_title.setStyleSheet(f"background: transparent; border: none; color: {TEXT_PRIMARY}; font-size: 15px; font-weight: 700;")
        self.chk_show_ids = QCheckBox("Tampilkan Offer ID, Event ID")
        self.chk_show_ids.stateChanged.connect(self._on_toggle_explorer_ids)
        meta_hdr.addWidget(self.lbl_explorer_case_title, stretch=1)
        meta_hdr.addWidget(self.chk_show_ids)
        rl.addLayout(meta_hdr)

        self.lbl_explorer_case_meta = QLabel("")
        self.lbl_explorer_case_meta.setWordWrap(True)
        self.lbl_explorer_case_meta.setStyleSheet(f"background: transparent; border: none; color: {TEXT_MUTED}; font-size: 13px;")
        rl.addWidget(self.lbl_explorer_case_meta)

        self.strip_explorer = StripAlur(show_detail=False)
        rl.addWidget(self.strip_explorer)

        self.model_explorer_events = DataFrameTableModel(precision=self._precision, duration_unit=self._duration_unit)
        self.table_explorer_events = QTableView()
        self.table_explorer_events.setModel(self.model_explorer_events)
        self._configure_table(self.table_explorer_events, row_height=44, interactive_columns=True, hide_vertical_header=False)
        self._activity_delegate = ActivityLifecycleDelegate(self.table_explorer_events)
        rl.addWidget(self.table_explorer_events, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([430, 920])
        layout.addWidget(splitter, stretch=1)

        self.tabs.addTab(tab, "Case Explorer")

    # ==================================================================
    # LOADING & DATA BINDING
    # ==================================================================
    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)
            self.badge_data_status.set_status("Memuat...", "loading")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
        self.btn_data_menu.setEnabled(not busy)
        self.act_rerun_menu.setEnabled((not busy) and (self.bundle is not None))
        if msg:
            self.lbl_data_status_msg.setText(msg)

    def on_browse_xes(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Impor Berkas Event Log XES",
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
            "Berkas Tidak Ditemukan",
            "Berkas BPI Challenge 2017.xes.gz tidak ditemukan pada folder kerja saat ini. Gunakan menu Impor Berkas XES untuk memilih berkas secara manual.",
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
        self._set_busy(True, f"Memproses berkas {os.path.basename(file_path)}...")
        self.worker = AnalysisWorker(file_path=file_path, existing_context=existing_context)
        self.worker.progress_changed.connect(self.lbl_data_status_msg.setText)
        self.worker.finished_bundle.connect(self._on_analysis_finished)
        self.worker.failed_error.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_analysis_failed(self, err_msg: str) -> None:
        self._set_busy(False, f"Gagal memuat atau memvalidasi berkas XES.")
        self.badge_data_status.set_status("✕ Gagal", "error")
        QMessageBox.critical(self, "Kesalahan Impor XES", err_msg)

    def _on_analysis_finished(self, bundle: FullAnalysisBundle) -> None:
        self.bundle = bundle
        rep = bundle.report
        load_txt = fmt_num(rep.load_time_seconds, 2)
        self._set_busy(False, f"Data dimuat dalam {load_txt} detik.")
        self.badge_data_status.set_status("✓ Valid", "valid")
        self.lbl_header_file.setText(rep.file_name)

        self.btn_all_activities.setEnabled(True)
        self.btn_case_durations.setEnabled(True)

        # Auto-check Lampiran A checklist items
        if "synthetic" in rep.file_name.lower():
            self.drawer.mark_done("synthetic_loaded", True)
        else:
            self.drawer.mark_done("bpic17_loaded", True)
        self.drawer.mark_done("ex117_ab", True)
        self.drawer.mark_done("ex117_cde", True)
        self.drawer.mark_done("ex1115", True)
        self.drawer.mark_done("ex1118", True)
        self.drawer.mark_done("ex1122", True)

        self._build_explorer_tags_map(bundle)
        self._populate_tab_data(bundle)
        self._populate_tab_117(bundle)
        self._populate_tab_1115_1118(bundle)
        self._populate_tab_1122(bundle)
        self._on_explorer_group_changed()

    def _build_explorer_tags_map(self, b: FullAnalysisBundle) -> None:
        all_ids = b.context.case_summary_df["case_id"].astype(str).tolist()
        tags_dict: Dict[str, List[str]] = {cid: [] for cid in all_ids}
        groups = [
            (b.ex117.sub_c.case_df, "11.7 C"),
            (b.ex117.sub_d.case_df, "11.7 D"),
            (b.ex117.sub_e.case_df, "11.7 E"),
            (b.ex1115.case_summary_df, "11.15"),
            (b.ex1118.case_resource_summary_df, "11.18"),
            (b.ex1122.case_summary_df, "11.22"),
        ]
        for df, tag in groups:
            if df is not None and not df.empty and "case_id" in df.columns:
                for cid in df["case_id"].astype(str).unique():
                    if cid in tags_dict:
                        tags_dict[cid].append(tag)
        self._explorer_tags_map = {cid: ", ".join(v) if v else "—" for cid, v in tags_dict.items()}

    # ------------------------------------------------------------------
    # POPULATE TABS & GLOBAL PRECISION/UNIT SYNC
    # ------------------------------------------------------------------
    def _on_precision_changed(self, idx: int) -> None:
        self._precision = 4 if idx == 1 else 2
        for m in (
            self.model_117_cases,
            self.model_1518_cases,
            self.model_1122_cases,
            self.model_explorer_events,
        ):
            m.set_format_options(self._precision, self._duration_unit)
        if self.bundle is not None:
            self._populate_tab_data(self.bundle)
            self._populate_tab_117(self.bundle)
            self._populate_tab_1115_1118(self.bundle)
            self._populate_tab_1122(self.bundle)
            if self._current_explorer_case_id:
                self._display_case_trace_in_explorer(self._current_explorer_case_id)

    def _on_unit_changed(self, unit: str) -> None:
        self._duration_unit = unit
        for m in (
            self.model_117_cases,
            self.model_1518_cases,
            self.model_1122_cases,
            self.model_explorer_events,
        ):
            m.set_format_options(self._precision, self._duration_unit)
        if self.bundle is not None:
            self._populate_tab_data(self.bundle)
            if self._current_explorer_case_id:
                self._display_case_trace_in_explorer(self._current_explorer_case_id)

    def _populate_tab_data(self, b: FullAnalysisBundle) -> None:
        ov = b.overview
        rep = b.report
        p = self._precision
        u = self._duration_unit

        self.card_data_cases.update_card(fmt_int(ov.total_cases))
        self.card_data_events.update_card(fmt_int(ov.total_events))
        self.card_data_acts.update_card(fmt_int(ov.unique_activities))
        self.card_data_res.update_card(fmt_int(ov.unique_resources))
        self.card_data_mean.update_card(fmt_duration(ov.mean_cycle_time_days, u, p))

        self.chip_case_id.set_state("valid" if "case:concept:name" in rep.available_columns else "invalid")
        self.chip_concept.set_state("valid" if "concept:name" in rep.available_columns else "invalid")
        self.chip_ts.set_state("valid" if "time:timestamp" in rep.available_columns else "invalid")
        self.chip_lc.set_state("valid" if rep.has_lifecycle else "invalid")
        self.chip_res.set_state("valid" if rep.has_resource else "invalid")

        self.btn_all_activities.setText(f"Lihat semua {fmt_int(ov.unique_activities)} aktivitas")

        top5 = ov.activity_table.head(5)
        act_items = [
            (str(r["activity"]), float(r["event_count"]), f"{fmt_int(r['event_count'])} ({fmt_pct(r['event_pct'], p)})")
            for _, r in top5.iterrows()
        ]
        self.bar_top_activities.set_items(act_items)

        # Lifecycle distribution computed dynamically from active DataFrame
        df_raw = b.context.df
        if "lifecycle:transition" in df_raw.columns and not df_raw.empty:
            lc_counts = df_raw["lifecycle:transition"].fillna("kosong").astype(str).value_counts()
            total_ev = max(len(df_raw), 1)
            lc_items = [
                (str(name), float(cnt), f"{fmt_int(cnt)} ({fmt_pct(cnt / total_ev * 100.0, p)})")
                for name, cnt in lc_counts.head(7).items()
            ]
            self.bar_lifecycle.set_items(lc_items)
        else:
            self.bar_lifecycle.set_items([])

        self._dur_labels["min"].setText(fmt_duration(ov.min_cycle_time_days, u, p))
        self._dur_labels["median"].setText(fmt_duration(ov.median_cycle_time_days, u, p))
        self._dur_labels["max"].setText(fmt_duration(ov.max_cycle_time_days, u, p))
        self._dur_labels["std"].setText(fmt_duration(ov.std_cycle_time_days, u, p))
        start_s = format_timestamp_compact(str(ov.log_start_time))
        end_s = format_timestamp_compact(str(ov.log_end_time))
        self._dur_labels["range"].setText(f"{start_s} sampai {end_s}")

        durs = b.context.case_summary_df["duration_days"].to_numpy(dtype=float) if not b.context.case_summary_df.empty else np.array([])
        self.histogram_durasi.set_data(
            durs,
            ov.fast_cases_count,
            ov.fast_cases_pct,
            ov.slow_cases_count,
            ov.slow_cases_pct,
            precision=p,
        )

    def _populate_tab_117(self, b: FullAnalysisBundle) -> None:
        r = b.ex117
        p = self._precision
        self.card_117a.update_card(fmt_int(r.sub_a.case_count), "100% dari seluruh log aktif")
        self.card_117b.update_card(
            f"{fmt_num(r.sub_b.mean_duration_days, p)} hari",
            f"Setara {fmt_num(r.sub_b.mean_duration_hours, p)} jam",
        )
        self.card_117c.update_card(
            fmt_int(r.sub_c.case_count),
            f"{fmt_pct(r.sub_c.case_percentage, p)}, rata-rata {fmt_num(r.sub_c.mean_duration_days, p)} hari",
        )
        self.card_117d.update_card(
            fmt_int(r.sub_d.case_count),
            f"{fmt_pct(r.sub_d.case_percentage, p)}, rata-rata {fmt_num(r.sub_d.mean_duration_days, p)} hari",
        )
        self.card_117e.update_card(
            fmt_int(r.sub_e.case_count),
            f"{fmt_pct(r.sub_e.case_percentage, p)}, rata-rata {fmt_num(r.sub_e.mean_duration_days, p)} hari",
        )

        both_pct = (r.overlap_c_and_d_count / max(r.sub_a.case_count, 1)) * 100.0
        cont_only = max(0, r.contains_cancelled_anywhere_count - r.sub_e.case_count)
        self.lbl_117_notes.setText(
            f"{fmt_int(r.overlap_c_and_d_count)} case masuk 11.7 C dan 11.7 D ({fmt_pct(both_pct, p)}). "
            f"Pada 11.7 E, terdapat {fmt_int(r.contains_cancelled_anywhere_count)} case yang memuat O_Cancelled di posisi mana pun, "
            f"namun {fmt_int(cont_only)} di antaranya berlanjut ke aktivitas lain sehingga tidak berakhir di O_Cancelled."
        )

        self.viz_117.set_data(
            share_items=[
                ("11.7 C Berhasil", r.sub_c.case_percentage, fmt_pct(r.sub_c.case_percentage, p)),
                ("11.7 D Tidak berhasil", r.sub_d.case_percentage, fmt_pct(r.sub_d.case_percentage, p)),
                ("11.7 E Dibatalkan", r.sub_e.case_percentage, fmt_pct(r.sub_e.case_percentage, p)),
            ],
            dur_items=[
                ("11.7 B Seluruh case", r.sub_b.mean_duration_days, f"{fmt_num(r.sub_b.mean_duration_days, p)} hari"),
                ("11.7 C Berhasil", r.sub_c.mean_duration_days, f"{fmt_num(r.sub_c.mean_duration_days, p)} hari"),
                ("11.7 D Tidak berhasil", r.sub_d.mean_duration_days, f"{fmt_num(r.sub_d.mean_duration_days, p)} hari"),
                ("11.7 E Dibatalkan", r.sub_e.mean_duration_days, f"{fmt_num(r.sub_e.mean_duration_days, p)} hari"),
            ],
        )

        self._refresh_117_table()

    def _on_select_117_card(self, idx: int) -> None:
        self._117_active_idx = idx
        for i, c in enumerate(self._cards_117):
            c.set_selected(i == idx)
        self.cmb_117_group.blockSignals(True)
        self.cmb_117_group.setCurrentIndex(idx)
        self.cmb_117_group.blockSignals(False)
        self._refresh_117_table()

    def _on_117_combo_changed(self, idx: int) -> None:
        self._on_select_117_card(idx)

    def _refresh_117_table(self) -> None:
        if self.bundle is None:
            return
        r = self.bundle.ex117
        idx = self._117_active_idx
        if idx == 2:
            df, hl = r.sub_c.case_df, ["O_Accepted"]
        elif idx == 3:
            df, hl = r.sub_d.case_df, ["O_Refused"]
        elif idx == 4:
            df, hl = r.sub_e.case_df, ["O_Cancelled"]
        else:
            df, hl = r.sub_a.case_df, []

        self._117_hl = hl
        self.model_117_cases.set_dataframe(df)
        self._apply_column_widths(
            self.table_117_cases,
            df,
            {
                "case_id": 180,
                "event_count": 100,
                "start_timestamp": 150,
                "end_timestamp": 150,
                "first_activity": 175,
                "last_activity": 175,
                "duration_seconds": 115,
                "duration_hours": 110,
                "duration_days": 115,
                "minmax_duration_days": 115,
                "speed_category": 145,
                "trigger_activity": 155,
                "trigger_count": 100,
            },
        )
        if not df.empty:
            self.table_117_cases.selectRow(0)
            cid = str(df.iloc[0]["case_id"])
            ev = self.bundle.context.get_case_events(cid)
            self.strip_117.set_events(ev, highlight_activities=hl)
        else:
            self.strip_117.set_placeholder("Tidak ada case yang lolos filter ini.")

    def _on_select_117_row(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        df = self.model_117_cases.get_dataframe()
        row = index.row()
        if 0 <= row < len(df):
            cid = str(df.iloc[row]["case_id"])
            ev = self.bundle.context.get_case_events(cid)
            self.strip_117.set_events(ev, highlight_activities=getattr(self, "_117_hl", []))

    def _populate_tab_1115_1118(self, b: FullAnalysisBundle) -> None:
        r15 = b.ex1115
        r18 = b.ex1118
        p = self._precision

        self.card_1115.update_card(
            fmt_int(r15.matching_case_count),
            f"{fmt_pct(r15.matching_percentage, p)} dari {fmt_int(r15.total_cases_denominator)} case",
        )
        self.card_1118.update_card(
            fmt_int(r18.matching_case_count),
            f"{fmt_pct(r18.matching_percentage, p)} oleh resource yang sama",
        )

        self.funnel_1115.set_stages([
            ("Seluruh case aktif", r15.total_cases_denominator, f"{fmt_int(r15.total_cases_denominator)} case"),
            ("Semua lifecycle minimal 2 event", r15.cases_with_two_all_lifecycles, f"{fmt_int(r15.cases_with_two_all_lifecycles)} case"),
            ("11.15 Complete minimal 2 kali", r15.matching_case_count, f"{fmt_int(r15.matching_case_count)} case"),
            ("11.18 Resource sama minimal 2 kali", r18.matching_case_count, f"{fmt_int(r18.matching_case_count)} case"),
        ])

        self._refresh_1518_table()

    def _on_switch_1518_mode(self, mode: str) -> None:
        self._1518_mode = mode
        self.card_1115.set_selected(mode == "11.15")
        self.card_1118.set_selected(mode == "11.18")
        self._refresh_1518_table()

    def _refresh_1518_table(self) -> None:
        if self.bundle is None:
            return
        r15 = self.bundle.ex1115
        r18 = self.bundle.ex1118
        show_excl = self.chk_show_excluded_1518.isChecked()

        if self._1518_mode == "11.15":
            if not show_excl:
                df = r15.case_summary_df
                self.lbl_1518_rule.setText(
                    f"Menampilkan {fmt_int(r15.matching_case_count)} case dengan W_Assess potential fraud berstatus complete minimal 2 kali."
                )
            else:
                # Build summary of cases excluded by complete-only filter
                excl_ids = sorted(
                    list(set(self.bundle.context.df.loc[
                        self.bundle.context.df["concept:name"].str.lower() == r15.target_activity.lower(),
                        "case:concept:name",
                    ].unique()) - set(r15.case_summary_df["case_id"].tolist() if not r15.case_summary_df.empty else []))
                )
                act_ev = self.bundle.context.df[
                    self.bundle.context.df["concept:name"].str.lower() == r15.target_activity.lower()
                ]
                all_cnt = act_ev.groupby("case:concept:name", sort=False).size()
                comp_ev = act_ev[act_ev["lifecycle:transition"].astype(str).str.lower() == "complete"] if "lifecycle:transition" in act_ev.columns else act_ev
                comp_cnt = comp_ev.groupby("case:concept:name", sort=False).size()
                rows_excl = []
                for cid in excl_ids:
                    ac = int(all_cnt.get(cid, 0))
                    cc = int(comp_cnt.get(cid, 0))
                    if ac >= 2 and cc < 2:
                        rows_excl.append({
                            "case_id": str(cid),
                            "complete_occurrences": cc,
                            "all_lifecycle_occurrences": ac,
                            "resources_involved": "Tereliminasi (hanya schedule, start, suspend, atau abort)",
                        })
                df = pd.DataFrame(rows_excl)
                self.lbl_1518_rule.setText(
                    f"Menampilkan {fmt_int(len(df))} case yang memiliki minimal 2 event W_Assess potential fraud tetapi kurang dari 2 status complete."
                )
        else:
            if not show_excl:
                df = r18.case_resource_summary_df
                self.lbl_1518_rule.setText(
                    f"Menampilkan {fmt_int(r18.matching_case_count)} case dengan minimal 2 complete oleh org:resource yang sama dan valid."
                )
            else:
                diff_ids = r18.cases_from_1115_excluded_diff_resource
                df = r15.case_summary_df[r15.case_summary_df["case_id"].isin(diff_ids)].copy() if not r15.case_summary_df.empty else pd.DataFrame()
                self.lbl_1518_rule.setText(
                    f"Menampilkan {fmt_int(len(df))} case yang lolos 11.15 tetapi dikerjakan oleh resource berbeda atau kosong."
                )

        self.model_1518_cases.set_dataframe(df)
        self._apply_column_widths(
            self.table_1518_cases,
            df,
            {
                "case_id": 180,
                "complete_occurrences": 130,
                "all_lifecycle_occurrences": 130,
                "resources_involved": 220,
                "unique_valid_resources": 115,
                "first_complete_time": 150,
                "last_complete_time": 150,
                "case_total_events": 120,
                "case_duration_days": 120,
                "resource_id": 130,
                "same_resource_completions": 155,
                "total_case_completions": 145,
                "evidence_event_ids": 220,
            },
        )
        if not df.empty:
            self.table_1518_cases.selectRow(0)
            self._update_1518_strip_for_row(0)
        else:
            self.strip_1518.set_placeholder("Tidak ada case pada kategori ini.")

    def _on_select_1518_row(self, index: QModelIndex) -> None:
        if index.isValid():
            self._update_1518_strip_for_row(index.row())

    def _update_1518_strip_for_row(self, row: int) -> None:
        if self.bundle is None:
            return
        df = self.model_1518_cases.get_dataframe()
        if df.empty or row < 0 or row >= len(df):
            return
        cid = str(df.iloc[row]["case_id"])
        rid = str(df.iloc[row]["resource_id"]) if "resource_id" in df.columns else None
        ev = self.bundle.context.get_case_events(cid)
        fraud_ev = ev[ev["concept:name"].str.lower() == self.bundle.ex1115.target_activity.lower()]
        self.strip_1518.set_events(
            fraud_ev,
            highlight_activities=[self.bundle.ex1115.target_activity],
            highlight_lifecycle="complete",
            highlight_resource=rid,
            max_chips=6,
        )

    def _populate_tab_1122(self, b: FullAnalysisBundle) -> None:
        r22 = b.ex1122
        p = self._precision
        self.lbl_22_ans.setText(f"{fmt_int(r22.matching_case_count)} case")
        self.lbl_22_pct.setText(fmt_pct(r22.matching_percentage, p))
        if r22.matching_case_count > 0:
            self.badge_22_yesno.set_status("Ya, ada", "valid")
        else:
            self.badge_22_yesno.set_status("Tidak ada", "error")
        self.lbl_22_denom.setText(f"dari {fmt_int(r22.total_cases_denominator)} case aktif")
        self.lbl_22_denom.setVisible(True)

        gaps = (
            r22.case_summary_df["time_between_days"].to_numpy(dtype=float)
            if not r22.case_summary_df.empty and "time_between_days" in r22.case_summary_df.columns
            else np.array([])
        )
        self.viz_1122.set_data(r22.matching_case_count, r22.reverse_only_count, gaps, precision=p)

        self.lbl_22_offer_note.setText(
            f"Analisis tambahan (Level OfferID): ditemukan {fmt_int(r22.same_offer_id_matching_count)} case dengan O_Cancelled dan O_Accepted pada OfferID yang sama. "
            f"Seluruh pasangan berasal dari penawaran lama yang dibatalkan lalu penawaran baru dalam aplikasi yang sama disetujui."
        )

        self.model_1122_cases.set_dataframe(r22.case_summary_df)
        self._apply_column_widths(
            self.table_1122_cases,
            r22.case_summary_df,
            {
                "case_id": 180,
                "cancelled_trace_pos": 115,
                "cancelled_timestamp": 150,
                "cancelled_offer_id": 135,
                "accepted_trace_pos": 115,
                "accepted_timestamp": 150,
                "accepted_offer_id": 135,
                "intervening_events_count": 120,
                "time_between_days": 110,
                "trace_end_activity": 170,
                "case_duration_days": 115,
            },
        )
        if not r22.case_summary_df.empty:
            self.table_1122_cases.selectRow(0)
            cid = str(r22.case_summary_df.iloc[0]["case_id"])
            ev = self.bundle.context.get_case_events(cid)
            self.strip_1122.set_events(ev, highlight_activities=["O_Cancelled", "O_Accepted"])
        else:
            self.strip_1122.set_placeholder("Tidak ada case yang lolos pola 11.22.")

    def _on_select_1122_row(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        df = self.model_1122_cases.get_dataframe()
        row = index.row()
        if 0 <= row < len(df):
            cid = str(df.iloc[row]["case_id"])
            ev = self.bundle.context.get_case_events(cid)
            self.strip_1122.set_events(ev, highlight_activities=["O_Cancelled", "O_Accepted"])

    # ------------------------------------------------------------------
    # CASE EXPLORER NAVIGATION & ACTIONS
    # ------------------------------------------------------------------
    def _get_selected_case_id(self, table: QTableView, model: DataFrameTableModel) -> Optional[str]:
        idxs = table.selectionModel().selectedRows()
        row = idxs[0].row() if idxs else table.currentIndex().row()
        df = model.get_dataframe()
        if df.empty or row < 0 or row >= len(df):
            return None
        col = "case_id" if "case_id" in df.columns else "case:concept:name"
        return str(df.iloc[row][col])

    def _on_inspect_from_117(self) -> None:
        cid = self._get_selected_case_id(self.table_117_cases, self.model_117_cases)
        if cid:
            g_map = {0: 0, 1: 0, 2: 1, 3: 2, 4: 3}
            self.open_case_in_explorer(cid, filter_group_index=g_map.get(self._117_active_idx, 0))

    def _on_inspect_from_1518(self) -> None:
        cid = self._get_selected_case_id(self.table_1518_cases, self.model_1518_cases)
        if cid:
            g_idx = 4 if self._1518_mode == "11.15" else 5
            self.open_case_in_explorer(cid, filter_group_index=g_idx)

    def _on_inspect_from_1122(self) -> None:
        cid = self._get_selected_case_id(self.table_1122_cases, self.model_1122_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=6)

    def open_case_in_explorer(self, case_id: str, filter_group_index: int = 0) -> None:
        self.tabs.setCurrentIndex(4)
        self.cmb_explorer_filter.setCurrentIndex(filter_group_index)
        self.txt_explorer_search.setText(case_id)
        self.model_explorer_cases.set_filter_text(case_id)
        row_idx = self.model_explorer_cases.row_of_case_id(case_id)
        if row_idx >= 0:
            self.table_explorer_cases.selectRow(row_idx)
        self._display_case_trace_in_explorer(case_id)
        self.drawer.mark_done("explorer_export", True)

    def _on_reset_explorer(self) -> None:
        self.cmb_explorer_filter.setCurrentIndex(0)
        self.txt_explorer_search.clear()
        self.model_explorer_cases.set_filter_text("")

    def _on_explorer_group_changed(self) -> None:
        if self.bundle is None:
            return
        idx = self.cmb_explorer_filter.currentIndex()
        b = self.bundle
        total = b.overview.total_cases

        if idx == 0:
            df = b.overview.case_table
            rule = f"Semua case aktif ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = ([], None)
        elif idx == 1:
            df = b.ex117.sub_c.case_df
            rule = f"11.7 C Berhasil, memuat O_Accepted ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = (["O_Accepted"], None)
        elif idx == 2:
            df = b.ex117.sub_d.case_df
            rule = f"11.7 D Tidak berhasil, memuat O_Refused ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = (["O_Refused"], None)
        elif idx == 3:
            df = b.ex117.sub_e.case_df
            rule = f"11.7 E Dibatalkan, event terakhir O_Cancelled ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = (["O_Cancelled"], None)
        elif idx == 4:
            df = b.ex1115.case_summary_df
            rule = f"11.15 Fraud complete minimal 2 kali ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = ([b.ex1115.target_activity], "complete")
        elif idx == 5:
            df = b.ex1118.case_resource_summary_df
            rule = f"11.18 Fraud complete oleh resource sama ({fmt_int(b.ex1118.matching_case_count)} dari {fmt_int(total)} case)"
            self._explorer_highlights = ([b.ex1118.target_activity], "complete")
        else:
            df = b.ex1122.case_summary_df
            rule = f"11.22 O_Cancelled lalu O_Accepted ({fmt_int(len(df))} dari {fmt_int(total)} case)"
            self._explorer_highlights = (["O_Cancelled", "O_Accepted"], None)

        self.lbl_explorer_rule.setText(rule)
        if df is not None and not df.empty:
            cids = df["case_id"].astype(str).tolist()
            cs = b.context.case_summary_df
            ev_counts = [int(cs.loc[cid, "event_count"]) if cid in cs.index else 0 for cid in cids]
            tags = [self._explorer_tags_map.get(cid, "—") for cid in cids]
            self.model_explorer_cases.set_cases(cids, ev_counts, tags)
            self.table_explorer_cases.selectRow(0)
            self._display_case_trace_in_explorer(cids[0])
        else:
            self.model_explorer_cases.set_cases([], [], [])
            self.strip_explorer.set_placeholder("Tidak ada case pada kelompok filter ini.")

    def _on_explorer_case_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        cid = self.model_explorer_cases.case_id_at(index.row())
        if cid:
            self._display_case_trace_in_explorer(cid)

    def _on_toggle_explorer_ids(self) -> None:
        if self._current_explorer_case_id:
            self._display_case_trace_in_explorer(self._current_explorer_case_id)

    def _display_case_trace_in_explorer(self, case_id: str) -> None:
        if self.bundle is None:
            return
        self._current_explorer_case_id = case_id
        ctx = self.bundle.context
        ev = ctx.get_case_events(case_id)
        if ev.empty:
            return

        cs = ctx.case_summary_df
        self.lbl_explorer_case_title.setText(f"Case {case_id}")
        if case_id in cs.index:
            row = cs.loc[case_id]
            dur_str = fmt_duration(float(row["duration_days"]), self._duration_unit, self._precision)
            f_act = str(row["first_activity"])
            l_act = str(row["last_activity"])
            tag_s = self._explorer_tags_map.get(case_id, "—")
            meta_txt = (
                f"Jumlah event {fmt_int(len(ev))}, durasi {dur_str}, "
                f"aktivitas awal {f_act}, aktivitas akhir {l_act}, lolos di {tag_s}"
            )
        else:
            meta_txt = f"Jumlah event {fmt_int(len(ev))}"
        self.lbl_explorer_case_meta.setText(meta_txt)

        hl_acts, hl_lc = self._explorer_highlights
        self.strip_explorer.set_events(ev, highlight_activities=hl_acts, highlight_lifecycle=hl_lc, max_chips=6)

        # Event columns: Waktu, Aktivitas (with ActivityLifecycleDelegate), Resource (+ OfferID, EventID if checked)
        cols = [c for c in ["time:timestamp", "concept:name", "org:resource"] if c in ev.columns]
        if self.chk_show_ids.isChecked():
            cols.extend(c for c in ["OfferID", "EventID"] if c in ev.columns)
        # Keep hidden lifecycle:transition inside UserRole via model's _source_df
        extra = ["lifecycle:transition"] if "lifecycle:transition" in ev.columns else []
        sub_df = ev[cols + extra].copy()
        # Hide raw lifecycle column from visible table since delegate displays it under Aktivitas
        self.model_explorer_events.set_dataframe(
            sub_df,
            highlight_activities=hl_acts,
            highlight_lifecycle=hl_lc,
        )
        # Set delegate on Aktivitas column and hide standalone lifecycle column
        for i, cname in enumerate(sub_df.columns):
            if cname == "lifecycle:transition":
                self.table_explorer_events.setColumnHidden(i, True)
            else:
                self.table_explorer_events.setColumnHidden(i, False)
            if cname == "concept:name":
                self.table_explorer_events.setItemDelegateForColumn(i, self._activity_delegate)
                self.table_explorer_events.setColumnWidth(i, 250)
            elif cname == "time:timestamp":
                self.table_explorer_events.setColumnWidth(i, 160)
            elif cname == "org:resource":
                self.table_explorer_events.setColumnWidth(i, 120)
            elif cname in ("OfferID", "EventID"):
                self.table_explorer_events.setColumnWidth(i, 155)

    # ------------------------------------------------------------------
    # DIALOG & EXPORT HANDLERS
    # ------------------------------------------------------------------
    def _on_open_all_activities(self) -> None:
        if self.bundle is None:
            return
        dlg = AllActivitiesDialog(self.bundle.overview.activity_table, precision=self._precision, parent=self)
        dlg.exec()

    def _on_open_case_durations(self) -> None:
        if self.bundle is None:
            return
        dlg = CaseDurationDialog(
            self.bundle.overview.case_table,
            precision=self._precision,
            duration_unit=self._duration_unit,
            parent=self,
        )
        dlg.open_case_requested.connect(lambda cid: self.open_case_in_explorer(cid, filter_group_index=0))
        dlg.exec()

    def on_open_export_dialog(self) -> None:
        if self.bundle is None:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat dan jalankan analisis pada berkas XES terlebih dahulu.")
            return
        b = self.bundle
        sum_df = build_summary_dataframe(b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122)
        dlg = ExportDialog(
            summary_df=sum_df,
            precision=self._precision,
            on_export_summary=self.on_export_summary_csv,
            on_export_all=self.on_export_all,
            parent=self,
        )
        dlg.exec()

    def _export_single_df(self, df: pd.DataFrame, default_name: str) -> None:
        if df is None or df.empty:
            QMessageBox.information(self, "Tidak Ada Data", "Tabel tidak memiliki baris untuk diekspor.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Data ke CSV",
            os.path.join(os.getcwd(), default_name),
            "CSV Files (*.csv)",
        )
        if not path:
            return
        try:
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.drawer.mark_done("explorer_export", True)
            QMessageBox.information(self, "Berhasil Disimpan", f"Berkas CSV berhasil disimpan ke:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Menyimpan CSV", str(exc))

    def _on_export_117_csv(self) -> None:
        if self.bundle is None:
            return
        df = self.model_117_cases.get_dataframe()
        self._export_single_df(df, f"hasil_exercise_11_7_kelompok_{self._117_active_idx}.csv")

    def _on_export_1518_csv(self) -> None:
        if self.bundle is None:
            return
        df = self.model_1518_cases.get_dataframe()
        name = "hasil_exercise_11_15.csv" if self._1518_mode == "11.15" else "hasil_exercise_11_18.csv"
        self._export_single_df(df, name)

    def _on_export_1122_csv(self) -> None:
        if self.bundle is None:
            return
        self._export_single_df(self.model_1122_cases.get_dataframe(), "hasil_exercise_11_22.csv")

    def on_export_all(self) -> None:
        if self.bundle is None:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat dan jalankan analisis pada berkas XES terlebih dahulu.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Pilih Folder Tujuan Ekspor CSV dan HTML", os.getcwd())
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
            self.drawer.mark_done("explorer_export", True)
            file_list = "\n".join(f"{k}: {os.path.basename(v)}" for k, v in files.items())
            QMessageBox.information(
                self,
                "Ekspor Berhasil",
                f"Seluruh hasil analisis dan daftar bukti case berhasil diekspor ke:\n{out_dir}\n\nBerkas yang dibuat:\n{file_list}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Mengekspor", str(exc))

    def on_export_summary_csv(self) -> None:
        if self.bundle is None:
            QMessageBox.warning(self, "Belum Ada Hasil", "Silakan muat dan jalankan analisis pada berkas XES terlebih dahulu.")
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
            b = self.bundle
            df = build_summary_dataframe(b.context, b.overview, b.ex117, b.ex1115, b.ex1118, b.ex1122)
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.drawer.mark_done("explorer_export", True)
            QMessageBox.information(self, "Berhasil Disimpan", f"Ringkasan jawaban berhasil disimpan ke:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Gagal Menyimpan CSV", str(exc))

    def on_show_about(self) -> None:
        active_path = self.bundle.report.file_path if self.bundle is not None else ""
        dlg = AboutDialog(active_file_path=active_path, parent=self)
        dlg.exec()
