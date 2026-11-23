"""PySide6 Desktop GUI for BPIC17 Event Log Analysis (FBPM Chapter 11 Exercises)."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStatusBar,
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
from .core import EventLogContext, ValidationReport, get_environment_info, load_and_validate_xes
from .exporter import build_summary_dataframe, export_all_to_directory
from .synthetic import generate_synthetic_xes_file


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
    color: #1e3a8a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: #ffffff;
}
QFrame#MetricCard {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
    padding: 10px;
}
QFrame#MetricCard QLabel {
    background-color: transparent;
}
QFrame#HeaderBanner {
    background-color: #1e3a8a;
    border-radius: 8px;
    padding: 10px 16px;
}
QLabel#BannerTitle {
    background-color: transparent;
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}
QLabel#BannerSubtitle {
    background-color: transparent;
    color: #bfdbfe;
    font-size: 12px;
}
QLabel#CardTitle {
    color: #475569;
    font-size: 11px;
    font-weight: 600;
}
QLabel#CardValue {
    color: #0f172a;
    font-size: 18px;
    font-weight: 700;
}
QLabel#CardSub {
    color: #2563eb;
    font-size: 11px;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:disabled {
    background-color: #94a3b8;
    color: #f1f5f9;
}
QPushButton#SecondaryBtn {
    background-color: #e2e8f0;
    color: #1e293b;
    border: 1px solid #cbd5e1;
}
QPushButton#SecondaryBtn:hover {
    background-color: #cbd5e1;
}
QPushButton#SuccessBtn {
    background-color: #059669;
    color: #ffffff;
}
QPushButton#SuccessBtn:hover {
    background-color: #047857;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 5px 10px;
}
QTabWidget::pane {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #e2e8f0;
    color: #334155;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #1e3a8a;
    color: #ffffff;
}
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    gridline-color: #e2e8f0;
    selection-background-color: #dbeafe;
    selection-color: #1e3a8a;
}
QHeaderView::section {
    background-color: #f1f5f9;
    color: #1e293b;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #cbd5e1;
    border-bottom: 2px solid #cbd5e1;
    font-weight: 700;
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
        self._df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self.highlight_activities = [a.lower() for a in (highlight_activities or [])]
        self.highlight_lifecycle = highlight_lifecycle.lower() if highlight_lifecycle else None
        self.highlight_resource = highlight_resource.lower() if highlight_resource else None

    def set_dataframe(
        self,
        df: pd.DataFrame,
        highlight_activities: Optional[List[str]] = None,
        highlight_lifecycle: Optional[str] = None,
        highlight_resource: Optional[str] = None,
    ) -> None:
        self.beginResetModel()
        self._df = df.copy().reset_index(drop=True) if df is not None else pd.DataFrame()
        self.highlight_activities = [a.lower() for a in (highlight_activities or [])]
        self.highlight_lifecycle = highlight_lifecycle.lower() if highlight_lifecycle else None
        self.highlight_resource = highlight_resource.lower() if highlight_resource else None
        self.endResetModel()

    def get_dataframe(self) -> pd.DataFrame:
        return self._df

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or self._df.empty:
            return None

        row = index.row()
        col = index.column()
        val = self._df.iloc[row, col]

        if role == Qt.DisplayRole:
            if pd.isna(val):
                return "-"
            if isinstance(val, float):
                return f"{val:,.4f}"
            if isinstance(val, int):
                return f"{val:,}"
            return str(val)

        if role == Qt.BackgroundRole and self.highlight_activities:
            act_col = "concept:name" if "concept:name" in self._df.columns else None
            if act_col:
                row_act = str(self._df.loc[row, act_col]).strip().lower()
                if row_act in self.highlight_activities:
                    lc_ok = True
                    if self.highlight_lifecycle and "lifecycle:transition" in self._df.columns:
                        row_lc = str(self._df.loc[row, "lifecycle:transition"]).strip().lower()
                        lc_ok = row_lc == self.highlight_lifecycle
                    res_ok = True
                    if self.highlight_resource and "org:resource" in self._df.columns:
                        row_res = str(self._df.loc[row, "org:resource"]).strip().lower()
                        res_ok = row_res == self.highlight_resource
                    if lc_ok and res_ok:
                        return QColor("#fef08a")  # Bright yellow highlight for matching evidence events
                    return QColor("#e0f2fe")  # Soft blue for same activity with other lifecycle/resource

        if role == Qt.TextAlignmentRole:
            if isinstance(val, (int, float)) and not pd.isna(val):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole or self._df.empty:
            return None
        if orientation == Qt.Horizontal:
            if 0 <= section < len(self._df.columns):
                return str(self._df.columns[section])
        else:
            return str(section + 1)
        return None


class MetricCard(QFrame):
    """Reusable summary metric card widget."""

    def __init__(self, title: str, value: str = "-", subtitle: str = "", border_color: str = "#2563eb"):
        super().__init__()
        self.setObjectName("MetricCard")
        self.setStyleSheet(f"QFrame#MetricCard {{ border-left: 4px solid {border_color}; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("CardTitle")
        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("CardValue")
        self.lbl_value.setWordWrap(True)
        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("CardSub")
        self.lbl_sub.setWordWrap(True)

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_value)
        layout.addWidget(self.lbl_sub)

    def update_card(self, value: str, subtitle: str = "") -> None:
        self.lbl_value.setText(value)
        self.lbl_sub.setText(subtitle)


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
    """Background worker thread so XES import and analysis never freeze the desktop UI (Section 7.1)."""

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
            r1118 = analyze_exercise_11_18(ctx)

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


class MainWindow(QMainWindow):
    """Main Desktop GUI Window for BPIC17 Event Log Analysis."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aplikasi Desktop Analisis Event Log BPIC17 — Bab 11 FBPM (Python & PM4Py)")
        self.resize(1380, 880)
        self.setStyleSheet(APP_STYLESHEET)

        self.bundle: Optional[FullAnalysisBundle] = None
        self.worker: Optional[AnalysisWorker] = None

        self._init_menubar()
        self._init_ui()

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
        act_export = QAction("Ekspor Semua Hasil ke Folder (CSV & HTML)...", self)
        act_export.triggered.connect(self.on_export_all)
        file_menu.addAction(act_export)

        file_menu.addSeparator()
        act_exit = QAction("Keluar", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        help_menu = menubar.addMenu("&Bantuan")
        act_about = QAction("Tentang Aplikasi & Versi Dependency (Reproducibility)", self)
        act_about.triggered.connect(self.on_show_about)
        help_menu.addAction(act_about)

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # Top header banner
        banner = QFrame()
        banner.setObjectName("HeaderBanner")
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(12, 8, 12, 8)

        title_box = QVBoxLayout()
        lbl_title = QLabel("BPIC17 Process Mining Desktop Analyzer — Latihan Bab 11 FBPM")
        lbl_title.setObjectName("BannerTitle")
        self.lbl_active_dataset = QLabel("Dataset Aktif: Belum ada file XES dimuat | Silakan impor file XES atau muat BPIC17 / Log Sintetis")
        self.lbl_active_dataset.setObjectName("BannerSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.lbl_active_dataset)
        b_layout.addLayout(title_box, stretch=1)

        self.btn_top_import = QPushButton("Impor XES...")
        self.btn_top_import.clicked.connect(self.on_browse_xes)
        self.btn_top_bpic = QPushButton("Muat BPIC17 (.xes.gz)")
        self.btn_top_bpic.setObjectName("SuccessBtn")
        self.btn_top_bpic.clicked.connect(self.on_load_default_bpic17)
        self.btn_top_synth = QPushButton("Muat Log Sintetis (Edge Cases)")
        self.btn_top_synth.setObjectName("SecondaryBtn")
        self.btn_top_synth.clicked.connect(self.on_load_synthetic_log)
        self.btn_top_rerun = QPushButton("Re-run Semua Analisis")
        self.btn_top_rerun.setObjectName("SecondaryBtn")
        self.btn_top_rerun.setEnabled(False)
        self.btn_top_rerun.clicked.connect(self.on_rerun_all)

        b_layout.addWidget(self.btn_top_import)
        b_layout.addWidget(self.btn_top_bpic)
        b_layout.addWidget(self.btn_top_synth)
        b_layout.addWidget(self.btn_top_rerun)
        main_layout.addWidget(banner)

        # Main Navigation Tabs (Following Section 6 minimum UI design)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, stretch=1)

        self._build_tab_f01_dataset()
        self._build_tab_f02_overview()
        self._build_tab_f03_ex117()
        self._build_tab_f04_f05_ex1115_1118()
        self._build_tab_f06_ex1122()
        self._build_tab_f07_case_explorer()
        self._build_tab_f07_export()

        # Bottom status bar with progress bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(260)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Siap. Pilih file XES untuk memulai analisis.")

    # ------------------------------------------------------------------
    # TAB 1: F01 — Impor & Validasi Event Log XES
    # ------------------------------------------------------------------
    def _build_tab_f01_dataset(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards_layout = QHBoxLayout()
        self.card_f01_status = MetricCard("Status Impor & Validasi", "Belum Dimuat", "Pilih file .xes / .xes.gz")
        self.card_f01_cases = MetricCard("Jumlah Unique Case (Trace)", "-", "Atribut: case:concept:name", "#059669")
        self.card_f01_events = MetricCard("Jumlah Total Event", "-", "Baris kejadian dalam log", "#7c3aed")
        self.card_f01_attrs = MetricCard("Deteksi Atribut Kunci", "-", "lifecycle:transition & org:resource", "#d97706")
        cards_layout.addWidget(self.card_f01_status)
        cards_layout.addWidget(self.card_f01_cases)
        cards_layout.addWidget(self.card_f01_events)
        cards_layout.addWidget(self.card_f01_attrs)
        layout.addLayout(cards_layout)

        grp_detail = QGroupBox("F01 — Rincian Validasi Atribut XES, Struktur Trace, & Lingkungan Reproduktibilitas")
        g_layout = QVBoxLayout(grp_detail)
        self.txt_f01_validation = QTextBrowser()
        self.txt_f01_validation.setOpenExternalLinks(True)
        env = get_environment_info()
        self.txt_f01_validation.setHtml(
            f"<h3>Selamat Datang di Aplikasi Analisis Event Log BPIC17</h3>"
            f"<p>Gunakan tombol <b>Muat BPIC17 (.xes.gz)</b> di kanan atas untuk memuat dataset utama "
            f"<code>BPI Challenge 2017.xes.gz</code>, atau klik <b>Impor XES...</b> untuk memilih berkas XES lain.</p>"
            f"<p>Anda juga dapat menekan <b>Muat Log Sintetis (Edge Cases)</b> untuk menguji ke-8 skenario uji tepi pada Bagian 8 instruksi proyek.</p>"
            f"<hr><p><b>Versi Lingkungan (Reproducibility):</b> Python {env['Python']} | PM4Py {env['PM4Py']} | "
            f"Pandas {env['Pandas']} | PySide6 {env['PySide6']} | r4pm {env['r4pm (XES accelerator)']}</p>"
        )
        g_layout.addWidget(self.txt_f01_validation)
        layout.addWidget(grp_detail, stretch=1)

        self.tabs.addTab(tab, "1. Dataset & Validasi (F01)")

    # ------------------------------------------------------------------
    # TAB 2: F02 — Event Log Overview & Statistika Dasar
    # ------------------------------------------------------------------
    def _build_tab_f02_overview(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards = QHBoxLayout()
        self.card_f02_cases = MetricCard("Total Unique Case", "-", "Total trace dalam log")
        self.card_f02_events = MetricCard("Total Event & Aktivitas", "-", "Jumlah aktivitas unik", "#7c3aed")
        self.card_f02_meandur = MetricCard("Rata-rata Cycle Time", "-", "Satuan hari, jam, & detik", "#059669")
        self.card_f02_fastslow = MetricCard("Fast (<45 hr) vs Slow (>=45 hr)", "-", "Pengayaan Example 11.10", "#d97706")
        cards.addWidget(self.card_f02_cases)
        cards.addWidget(self.card_f02_events)
        cards.addWidget(self.card_f02_meandur)
        cards.addWidget(self.card_f02_fastslow)
        layout.addLayout(cards)

        self.lbl_f02_timerange = QLabel("Rentang Waktu Event Log: -")
        self.lbl_f02_timerange.setStyleSheet("font-weight: 600; color: #1e3a8a; padding: 4px;")
        layout.addWidget(self.lbl_f02_timerange)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Activity frequency table
        grp_act = QGroupBox("Frekuensi Aktivitas (Event Count, Complete Count, & Case Count)")
        act_layout = QVBoxLayout(grp_act)
        self.model_f02_act = DataFrameTableModel()
        self.table_f02_act = QTableView()
        self.table_f02_act.setModel(self.model_f02_act)
        self.table_f02_act.setAlternatingRowColors(True)
        self.table_f02_act.setSelectionBehavior(QTableView.SelectRows)
        self.table_f02_act.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        act_layout.addWidget(self.table_f02_act)
        splitter.addWidget(grp_act)

        # Right: Case duration table with search & unit precision
        grp_cases = QGroupBox("Daftar Case & Durasi per Case (Klik Ganda untuk Buka di Case Explorer)")
        c_layout = QVBoxLayout(grp_cases)
        search_bar = QHBoxLayout()
        self.txt_f02_search = QLineEdit()
        self.txt_f02_search.setPlaceholderText("Cari Case ID atau nama aktivitas awal/akhir...")
        self.txt_f02_search.textChanged.connect(self._on_filter_f02_cases)
        btn_inspect_f02 = QPushButton("Buka Rincian Case Terpilih di Case Explorer")
        btn_inspect_f02.clicked.connect(self._on_inspect_from_f02)
        search_bar.addWidget(QLabel("Filter Case:"))
        search_bar.addWidget(self.txt_f02_search, stretch=1)
        search_bar.addWidget(btn_inspect_f02)
        c_layout.addLayout(search_bar)

        self.model_f02_cases = DataFrameTableModel()
        self.proxy_f02_cases = QSortFilterProxyModel(self)
        self.proxy_f02_cases.setSourceModel(self.model_f02_cases)
        self.proxy_f02_cases.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_f02_cases.setFilterKeyColumn(-1)

        self.table_f02_cases = QTableView()
        self.table_f02_cases.setModel(self.proxy_f02_cases)
        self.table_f02_cases.setAlternatingRowColors(True)
        self.table_f02_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_f02_cases.setSortingEnabled(True)
        self.table_f02_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_f02_cases.doubleClicked.connect(lambda _: self._on_inspect_from_f02())
        c_layout.addWidget(self.table_f02_cases)
        splitter.addWidget(grp_cases)
        splitter.setSizes([520, 780])

        layout.addWidget(splitter, stretch=1)
        self.tabs.addTab(tab, "2. Overview & Statistika (F02)")

    # ------------------------------------------------------------------
    # TAB 3: F03 — Analisis Exercise 11.7 (A–E)
    # ------------------------------------------------------------------
    def _build_tab_f03_ex117(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards = QHBoxLayout()
        self.card_117a = MetricCard("11.7 A — Total Case", "-", "Unique case keseluruhan log")
        self.card_117b = MetricCard("11.7 B — Mean Cycle Time", "-", "Rata-rata durasi seluruh case", "#0284c7")
        self.card_117c = MetricCard("11.7 C — Successful Cases", "-", "Contains('O_Accepted')", "#059669")
        self.card_117d = MetricCard("11.7 D — Unsuccessful Cases", "-", "Contains('O_Refused')", "#dc2626")
        self.card_117e = MetricCard("11.7 E — Canceled Cases", "-", "Endpoint == 'O_Cancelled'", "#d97706")
        for c in (self.card_117a, self.card_117b, self.card_117c, self.card_117d, self.card_117e):
            cards.addWidget(c)
        layout.addLayout(cards)

        self.lbl_117_rule_note = QLabel(
            "Catatan Semantik Filter 11.7: 11.7 C dan 11.7 D menggunakan aturan 'Contains' (case memuat minimal 1 event O_Accepted / O_Refused, dihitung 1x per case), "
            "sedangkan 11.7 E menggunakan aturan 'Endpoint' (event TERAKHIR pada urutan trace adalah O_Cancelled). Durasi tiap case dihitung dari trace utuh."
        )
        self.lbl_117_rule_note.setWordWrap(True)
        self.lbl_117_rule_note.setStyleSheet("background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 8px; color: #1e3a8a;")
        layout.addWidget(self.lbl_117_rule_note)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("Pilih Kelompok Soal 11.7 untuk Melihat Daftar Case Terpilih:"))
        self.cmb_117_group = QComboBox()
        self.cmb_117_group.addItems([
            "11.7 C — Successful Cases (Contains O_Accepted)",
            "11.7 D — Unsuccessful Cases (Contains O_Refused)",
            "11.7 E — Canceled Cases (Event Terakhir == O_Cancelled)",
            "11.7 A & B — Seluruh Case Aktif",
        ])
        self.cmb_117_group.currentIndexChanged.connect(self._on_117_group_changed)
        ctrl_bar.addWidget(self.cmb_117_group, stretch=1)

        self.txt_117_search = QLineEdit()
        self.txt_117_search.setPlaceholderText("Cari Case ID pada kelompok terpilih...")
        self.txt_117_search.textChanged.connect(self._on_filter_117_table)
        ctrl_bar.addWidget(self.txt_117_search, stretch=1)

        btn_inspect_117 = QPushButton("Buka Rincian Case & Validasi Kategori di Case Explorer")
        btn_inspect_117.clicked.connect(self._on_inspect_from_117)
        ctrl_bar.addWidget(btn_inspect_117)
        layout.addLayout(ctrl_bar)

        self.model_117_cases = DataFrameTableModel()
        self.proxy_117_cases = QSortFilterProxyModel(self)
        self.proxy_117_cases.setSourceModel(self.model_117_cases)
        self.proxy_117_cases.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_117_cases.setFilterKeyColumn(-1)

        self.table_117_cases = QTableView()
        self.table_117_cases.setModel(self.proxy_117_cases)
        self.table_117_cases.setAlternatingRowColors(True)
        self.table_117_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_117_cases.setSortingEnabled(True)
        self.table_117_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_117_cases.doubleClicked.connect(lambda _: self._on_inspect_from_117())
        layout.addWidget(self.table_117_cases, stretch=1)

        self.tabs.addTab(tab, "3. Exercise 11.7 A–E (F03)")

    # ------------------------------------------------------------------
    # TAB 4: F04 & F05 — Exercise 11.15 & 11.18 (Repeated Complete & Same Resource)
    # ------------------------------------------------------------------
    def _build_tab_f04_f05_ex1115_1118(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards = QHBoxLayout()
        self.card_1115_ans = MetricCard("Jawaban Exercise 11.15", "-", "W_Assess potential fraud complete >= 2x", "#2563eb")
        self.card_1115_excl = MetricCard("Bukti Filter Lifecycle Complete", "-", "Case >=2 event semua lifecycle vs complete-only", "#7c3aed")
        self.card_1118_ans = MetricCard("Jawaban Exercise 11.18", "-", "Complete >= 2x oleh Resource Identik", "#059669")
        self.card_1118_diff = MetricCard("Lolos 11.15 tapi Beda Resource", "-", "Selisih case antara 11.15 dan 11.18", "#d97706")
        cards.addWidget(self.card_1115_ans)
        cards.addWidget(self.card_1115_excl)
        cards.addWidget(self.card_1118_ans)
        cards.addWidget(self.card_1118_diff)
        layout.addLayout(cards)

        # Top split: Left = 11.15 table, Right = 11.18 table
        top_splitter = QSplitter(Qt.Horizontal)

        grp_1115 = QGroupBox("F04 — Daftar Case Lolos Exercise 11.15 (Complete >= 2x)")
        l1115 = QVBoxLayout(grp_1115)
        btn_row_15 = QHBoxLayout()
        btn_inspect_15 = QPushButton("Periksa Jejak Case 11.15 di Case Explorer")
        btn_inspect_15.clicked.connect(self._on_inspect_from_1115)
        btn_show_excl = QPushButton("Tampilkan Contoh Case Tereliminasi Filter Complete-Only")
        btn_show_excl.setObjectName("SecondaryBtn")
        btn_show_excl.clicked.connect(self._on_show_excluded_lifecycle_case)
        btn_row_15.addWidget(btn_inspect_15)
        btn_row_15.addWidget(btn_show_excl)
        l1115.addLayout(btn_row_15)

        self.model_1115_cases = DataFrameTableModel()
        self.table_1115_cases = QTableView()
        self.table_1115_cases.setModel(self.model_1115_cases)
        self.table_1115_cases.setAlternatingRowColors(True)
        self.table_1115_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_1115_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_1115_cases.clicked.connect(self._on_select_1115_case)
        self.table_1115_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1115())
        l1115.addWidget(self.table_1115_cases)
        top_splitter.addWidget(grp_1115)

        grp_1118 = QGroupBox("F05 — Daftar Case & Resource Lolos Exercise 11.18 (Complete >= 2x oleh Resource Sama)")
        l1118 = QVBoxLayout(grp_1118)
        btn_row_18 = QHBoxLayout()
        btn_inspect_18 = QPushButton("Periksa Jejak Case 11.18 di Case Explorer")
        btn_inspect_18.setObjectName("SuccessBtn")
        btn_inspect_18.clicked.connect(self._on_inspect_from_1118)
        btn_show_diff_res = QPushButton("Lihat Bukti 10 Case Lolos 11.15 (Resource Berbeda)")
        btn_show_diff_res.setObjectName("SecondaryBtn")
        btn_show_diff_res.clicked.connect(self._on_show_diff_resource_evidence)
        btn_row_18.addWidget(btn_inspect_18)
        btn_row_18.addWidget(btn_show_diff_res)
        l1118.addLayout(btn_row_18)

        self.model_1118_cases = DataFrameTableModel()
        self.table_1118_cases = QTableView()
        self.table_1118_cases.setModel(self.model_1118_cases)
        self.table_1118_cases.setAlternatingRowColors(True)
        self.table_1118_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_1118_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_1118_cases.clicked.connect(self._on_select_1118_case)
        self.table_1118_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1118())
        l1118.addWidget(self.table_1118_cases)
        top_splitter.addWidget(grp_1118)

        # Bottom panel: Evidence events table for selected case / group
        grp_ev = QGroupBox("Bukti Event (Event Evidence) — Menampilkan Timestamp, Aktivitas, Lifecycle Transition, Resource, dan EventID")
        lev = QVBoxLayout(grp_ev)
        self.lbl_15_18_evidence_title = QLabel("Klik salah satu case pada tabel 11.15 atau 11.18 di atas untuk memeriksa bukti event-nya.")
        self.lbl_15_18_evidence_title.setStyleSheet("font-weight: 600; color: #1e3a8a;")
        lev.addWidget(self.lbl_15_18_evidence_title)

        self.model_15_18_evidence = DataFrameTableModel()
        self.table_15_18_evidence = QTableView()
        self.table_15_18_evidence.setModel(self.model_15_18_evidence)
        self.table_15_18_evidence.setAlternatingRowColors(True)
        self.table_15_18_evidence.setSelectionBehavior(QTableView.SelectRows)
        self.table_15_18_evidence.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        lev.addWidget(self.table_15_18_evidence)

        v_split = QSplitter(Qt.Vertical)
        v_split.addWidget(top_splitter)
        v_split.addWidget(grp_ev)
        v_split.setSizes([380, 260])

        layout.addWidget(v_split, stretch=1)
        self.tabs.addTab(tab, "4. Exercise 11.15 & 11.18 (F04–F05)")

    # ------------------------------------------------------------------
    # TAB 5: F06 — Exercise 11.22 (O_Cancelled Eventually Followed By O_Accepted)
    # ------------------------------------------------------------------
    def _build_tab_f06_ex1122(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        cards = QHBoxLayout()
        self.card_1122_ans = MetricCard("Jawaban Exercise 11.22 (Jumlah Case)", "-", "O_Cancelled diikuti O_Accepted (i < j)", "#2563eb")
        self.card_1122_pct = MetricCard("Persentase terhadap Total Case Aktif", "-", "Denominator ditampilkan eksplisit", "#059669")
        self.card_1122_rev = MetricCard("Urutan Terbalik Saja (Tidak Lolos)", "-", "O_Accepted sebelum O_Cancelled tanpa accepted lagi", "#d97706")
        self.card_1122_offer = MetricCard("Analisis Tambahan Level OfferID (Bagian 7.3)", "-", "Pasangan pada OfferID yang sama vs beda OfferID", "#7c3aed")
        cards.addWidget(self.card_1122_ans)
        cards.addWidget(self.card_1122_pct)
        cards.addWidget(self.card_1122_rev)
        cards.addWidget(self.card_1122_offer)
        layout.addLayout(cards)

        ctrl = QHBoxLayout()
        self.txt_1122_search = QLineEdit()
        self.txt_1122_search.setPlaceholderText("Cari Case ID atau Offer ID pada hasil 11.22...")
        self.txt_1122_search.textChanged.connect(self._on_filter_1122_table)
        btn_inspect_22 = QPushButton("Buka Timeline Lengkap Case di Case Explorer")
        btn_inspect_22.clicked.connect(self._on_inspect_from_1122)
        ctrl.addWidget(QLabel("Cari Case 11.22:"))
        ctrl.addWidget(self.txt_1122_search, stretch=1)
        ctrl.addWidget(btn_inspect_22)
        layout.addLayout(ctrl)

        v_split = QSplitter(Qt.Vertical)

        grp_cases = QGroupBox("F06 — Daftar Case & Pasangan Kejadian Pembukti Urutan (O_Cancelled pada Posisi i < O_Accepted pada Posisi j)")
        lc = QVBoxLayout(grp_cases)
        self.model_1122_cases = DataFrameTableModel()
        self.proxy_1122_cases = QSortFilterProxyModel(self)
        self.proxy_1122_cases.setSourceModel(self.model_1122_cases)
        self.proxy_1122_cases.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_1122_cases.setFilterKeyColumn(-1)

        self.table_1122_cases = QTableView()
        self.table_1122_cases.setModel(self.proxy_1122_cases)
        self.table_1122_cases.setAlternatingRowColors(True)
        self.table_1122_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_1122_cases.setSortingEnabled(True)
        self.table_1122_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_1122_cases.clicked.connect(self._on_select_1122_case)
        self.table_1122_cases.doubleClicked.connect(lambda _: self._on_inspect_from_1122())
        lc.addWidget(self.table_1122_cases)
        v_split.addWidget(grp_cases)

        grp_tl = QGroupBox("Timeline Event O_Cancelled & O_Accepted pada Case Terpilih")
        ltl = QVBoxLayout(grp_tl)
        self.lbl_1122_timeline_info = QLabel("Pilih sebuah case pada tabel di atas untuk melihat urutan event O_Cancelled -> O_Accepted beserta OfferID-nya.")
        self.lbl_1122_timeline_info.setStyleSheet("font-weight: 600; color: #1e3a8a;")
        ltl.addWidget(self.lbl_1122_timeline_info)

        self.model_1122_evidence = DataFrameTableModel()
        self.table_1122_evidence = QTableView()
        self.table_1122_evidence.setModel(self.model_1122_evidence)
        self.table_1122_evidence.setAlternatingRowColors(True)
        self.table_1122_evidence.setSelectionBehavior(QTableView.SelectRows)
        self.table_1122_evidence.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        ltl.addWidget(self.table_1122_evidence)
        v_split.addWidget(grp_tl)
        v_split.setSizes([380, 240])

        layout.addWidget(v_split, stretch=1)
        self.tabs.addTab(tab, "5. Exercise 11.22 (F06)")

    # ------------------------------------------------------------------
    # TAB 6: F07 — Case Explorer & Jejak Analisis
    # ------------------------------------------------------------------
    def _build_tab_f07_case_explorer(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Filter Kelompok Analisis:"))
        self.cmb_explorer_filter = QComboBox()
        self.cmb_explorer_filter.addItems([
            "Semua Case Aktif (Overview)",
            "Exercise 11.7 C — Successful Cases (Contains O_Accepted)",
            "Exercise 11.7 D — Unsuccessful Cases (Contains O_Refused)",
            "Exercise 11.7 E — Canceled Cases (Event Terakhir == O_Cancelled)",
            "Exercise 11.15 — W_Assess potential fraud Complete >= 2x",
            "Exercise 11.18 — W_Assess potential fraud Complete >= 2x oleh Resource Sama",
            "Exercise 11.22 — O_Cancelled Diikuti O_Accepted (i < j)",
        ])
        self.cmb_explorer_filter.currentIndexChanged.connect(self._on_explorer_group_changed)
        top_bar.addWidget(self.cmb_explorer_filter, stretch=1)

        top_bar.addWidget(QLabel("Cari Case ID:"))
        self.txt_explorer_search = QLineEdit()
        self.txt_explorer_search.setPlaceholderText("Ketik Case ID (mis. Application_1221917431)...")
        self.txt_explorer_search.textChanged.connect(self._on_explorer_search_changed)
        top_bar.addWidget(self.txt_explorer_search, stretch=1)

        btn_reset_exp = QPushButton("Reset Filter")
        btn_reset_exp.setObjectName("SecondaryBtn")
        btn_reset_exp.clicked.connect(self._on_reset_explorer)
        top_bar.addWidget(btn_reset_exp)
        layout.addLayout(top_bar)

        self.lbl_explorer_rule_banner = QLabel("Aturan Filter Aktif: Menampilkan seluruh case pada event log.")
        self.lbl_explorer_rule_banner.setWordWrap(True)
        self.lbl_explorer_rule_banner.setStyleSheet("background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-weight: 600;")
        layout.addWidget(self.lbl_explorer_rule_banner)

        splitter = QSplitter(Qt.Horizontal)

        grp_left = QGroupBox("Daftar Case Hasil Filter")
        ll = QVBoxLayout(grp_left)
        self.model_explorer_cases = DataFrameTableModel()
        self.proxy_explorer_cases = QSortFilterProxyModel(self)
        self.proxy_explorer_cases.setSourceModel(self.model_explorer_cases)
        self.proxy_explorer_cases.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_explorer_cases.setFilterKeyColumn(-1)

        self.table_explorer_cases = QTableView()
        self.table_explorer_cases.setModel(self.proxy_explorer_cases)
        self.table_explorer_cases.setAlternatingRowColors(True)
        self.table_explorer_cases.setSelectionBehavior(QTableView.SelectRows)
        self.table_explorer_cases.setSortingEnabled(True)
        self.table_explorer_cases.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_explorer_cases.clicked.connect(self._on_explorer_case_clicked)
        ll.addWidget(self.table_explorer_cases)
        splitter.addWidget(grp_left)

        grp_right = QGroupBox("Jejak Trace Lengkap (Urutan Event, Timestamp, Aktivitas, Lifecycle, Resource, & OfferID)")
        lr = QVBoxLayout(grp_right)
        self.lbl_explorer_case_meta = QLabel("Pilih sebuah case di sebelah kiri untuk melihat seluruh urutan event-nya.")
        self.lbl_explorer_case_meta.setWordWrap(True)
        self.lbl_explorer_case_meta.setStyleSheet("color: #1e3a8a; font-weight: 600; padding: 4px;")
        lr.addWidget(self.lbl_explorer_case_meta)

        self.model_explorer_events = DataFrameTableModel()
        self.table_explorer_events = QTableView()
        self.table_explorer_events.setModel(self.model_explorer_events)
        self.table_explorer_events.setAlternatingRowColors(True)
        self.table_explorer_events.setSelectionBehavior(QTableView.SelectRows)
        self.table_explorer_events.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        lr.addWidget(self.table_explorer_events)
        splitter.addWidget(grp_right)
        splitter.setSizes([460, 860])

        layout.addWidget(splitter, stretch=1)
        self.tabs.addTab(tab, "6. Case Explorer & Bukti (F07)")

    # ------------------------------------------------------------------
    # TAB 7: F07 — Ringkasan Jawaban & Ekspor CSV / HTML
    # ------------------------------------------------------------------
    def _build_tab_f07_export(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_row = QHBoxLayout()
        btn_export_dir = QPushButton("Ekspor Semua Hasil Analisis ke Folder (CSV + Laporan HTML)...")
        btn_export_dir.setObjectName("SuccessBtn")
        btn_export_dir.clicked.connect(self.on_export_all)

        btn_export_single_csv = QPushButton("Simpan Tabel Ringkasan Jawaban ke File CSV...")
        btn_export_single_csv.clicked.connect(self.on_export_summary_csv)

        top_row.addWidget(btn_export_dir)
        top_row.addWidget(btn_export_single_csv)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        grp_sum = QGroupBox("Ringkasan Kedelapan Butir Jawaban Wajib (Exercise 11.7 A–E, 11.15, 11.18, dan 11.22)")
        ls = QVBoxLayout(grp_sum)
        self.model_export_summary = DataFrameTableModel()
        self.table_export_summary = QTableView()
        self.table_export_summary.setModel(self.model_export_summary)
        self.table_export_summary.setAlternatingRowColors(True)
        self.table_export_summary.setSelectionBehavior(QTableView.SelectRows)
        self.table_export_summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        ls.addWidget(self.table_export_summary)
        layout.addWidget(grp_sum, stretch=1)

        self.tabs.addTab(tab, "7. Ringkasan & Ekspor (F07)")

    # ==================================================================
    # EVENT HANDLERS & WORKFLOW LOGIC
    # ==================================================================
    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.progress_bar.setVisible(busy)
        if busy:
            self.progress_bar.setRange(0, 0)  # Indeterminate busy indicator
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
            "Berkas 'BPI Challenge 2017.xes.gz' tidak ditemukan di folder kerja saat ini. Silakan pilih manual menggunakan tombol 'Impor XES...'.",
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
        self._set_busy(True, f"Memproses {os.path.basename(file_path)}...")
        self.worker = AnalysisWorker(file_path=file_path, existing_context=existing_context)
        self.worker.progress_changed.connect(self.status_bar.showMessage)
        self.worker.finished_bundle.connect(self._on_analysis_finished)
        self.worker.failed_error.connect(self._on_analysis_failed)
        self.worker.start()

    def _on_analysis_failed(self, err_msg: str) -> None:
        self._set_busy(False, "Gagal memuat/memvalidasi berkas XES.")
        self.card_f01_status.update_card("GAGAL / TIDAK VALID", "Lihat rincian pesan error di bawah")
        self.txt_f01_validation.setHtml(
            f"<h3 style='color:#dc2626;'>Impor atau Validasi XES Gagal</h3>"
            f"<pre style='background:#fef2f2;padding:12px;border:1px solid #fecaca;color:#991b1b;'>{err_msg}</pre>"
        )
        QMessageBox.critical(self, "Kesalahan Impor / Validasi XES", err_msg)

    def _on_analysis_finished(self, bundle: FullAnalysisBundle) -> None:
        self.bundle = bundle
        self._set_busy(
            False,
            f"Berhasil memuat {bundle.report.file_name} ({bundle.report.total_cases:,} case, {bundle.report.total_events:,} event) dalam {bundle.report.load_time_seconds:.2f} detik.",
        )
        self.lbl_active_dataset.setText(
            f"Dataset Aktif: {bundle.report.file_name} ({bundle.report.file_size_mb:.2f} MB) | "
            f"{bundle.report.total_cases:,} Unique Cases | {bundle.report.total_events:,} Events | "
            f"Waktu Baca: {bundle.report.load_time_seconds:.2f} dtk"
        )

        self._populate_f01(bundle)
        self._populate_f02(bundle)
        self._populate_f03(bundle)
        self._populate_f04_f05(bundle)
        self._populate_f06(bundle)
        self._populate_f07(bundle)

    # ------------------------------------------------------------------
    # POPULATE UI TABS FROM BUNDLE
    # ------------------------------------------------------------------
    def _populate_f01(self, b: FullAnalysisBundle) -> None:
        rep = b.report
        self.card_f01_status.update_card("VALID (PM4Py)", f"{rep.file_name} ({rep.file_size_mb:.2f} MB) — {rep.load_time_seconds:.2f} dtk")
        self.card_f01_cases.update_card(f"{rep.total_cases:,} Case", "Atribut case:concept:name tervalidasi")
        self.card_f01_events.update_card(f"{rep.total_events:,} Event", f"Rata-rata {rep.total_events / max(rep.total_cases, 1):.2f} event/case")
        lc_txt = "Ada" if rep.has_lifecycle else "Tidak Ada"
        res_txt = "Ada" if rep.has_resource else "Tidak Ada"
        self.card_f01_attrs.update_card(f"Lifecycle: {lc_txt} | Resource: {res_txt}", f"Transisi: {', '.join(rep.lifecycle_values)}")

        env = get_environment_info()
        warn_html = ""
        if rep.warnings:
            warn_items = "".join(f"<li>{w}</li>" for w in rep.warnings)
            warn_html = f"<div style='background:#fffbeb;border:1px solid #fde68a;padding:8px;border-radius:6px;'><b>Peringatan:</b><ul>{warn_items}</ul></div>"

        self.txt_f01_validation.setHtml(f"""
        <h3>Laporan Validasi Event Log XES (F01)</h3>
        {warn_html}
        <ul>
          <li><b>Lokasi Berkas:</b> <code>{rep.file_path}</code></li>
          <li><b>Ukuran Berkas & Waktu Impor:</b> {rep.file_size_mb:.2f} MB (diimpor melalui <code>pm4py.read_xes</code> dalam {rep.load_time_seconds:.2f} detik)</li>
          <li><b>Jumlah Unique Case (Trace):</b> <b>{rep.total_cases:,}</b> case</li>
          <li><b>Jumlah Total Event:</b> <b>{rep.total_events:,}</b> event</li>
          <li><b>Validasi Atribut Wajib:</b> <code>case:concept:name</code> (OK), <code>concept:name</code> (OK), <code>time:timestamp</code> (OK)</li>
          <li><b>Deteksi <code>lifecycle:transition</code>:</b> {'Tersedia' if rep.has_lifecycle else 'Tidak Tersedia'} — Nilai unik ({len(rep.lifecycle_values)}): <code>{', '.join(rep.lifecycle_values)}</code></li>
          <li><b>Deteksi <code>org:resource</code>:</b> {'Tersedia' if rep.has_resource else 'Tidak Tersedia'} ({b.overview.unique_resources:,} resource valid teridentifikasi)</li>
          <li><b>Deteksi <code>OfferID</code>:</b> {'Tersedia' if rep.has_offer_id else 'Tidak Tersedia'}</li>
          <li><b>Atribut Level Trace ({len(rep.trace_attributes)}):</b> <code>{', '.join(rep.trace_attributes)}</code></li>
          <li><b>Atribut Level Event ({len(rep.event_attributes)}):</b> <code>{', '.join(rep.event_attributes)}</code></li>
        </ul>
        <hr>
        <h4>Aturan Urutan Event & Perhitungan Durasi (Bagian 4 & 7.1)</h4>
        <ul>
          <li><b>Urutan Event dalam Trace:</b> Menggunakan urutan indeks aktual event di dalam XES trace (<code>_trace_pos</code>), sehingga apabila terdapat dua event dengan timestamp identik, urutan kejadian tetap konsisten dan deterministik sesuai representasi log asli.</li>
          <li><b>Perhitungan Cycle Time Case:</b> Dihitung pada level trace utuh (<i>timestamp event terakhir − timestamp event pertama</i>) sebelum pemfilteran event apa pun agar durasi case tidak terdistorsi.</li>
        </ul>
        <p><b>Lingkungan Eksekusi:</b> Python {env['Python']} | PM4Py {env['PM4Py']} | Pandas {env['Pandas']} | PySide6 {env['PySide6']} | r4pm {env['r4pm (XES accelerator)']}</p>
        """)

    def _populate_f02(self, b: FullAnalysisBundle) -> None:
        ov = b.overview
        self.card_f02_cases.update_card(f"{ov.total_cases:,} Case", f"Min: {ov.min_cycle_time_days:.4f} hr | Max: {ov.max_cycle_time_days:.2f} hr")
        self.card_f02_events.update_card(f"{ov.total_events:,} Event", f"{ov.unique_activities} Aktivitas Unik | {ov.unique_resources} Resource")
        self.card_f02_meandur.update_card(
            f"{ov.mean_cycle_time_days:.2f} Hari",
            f"Presisi: {ov.mean_cycle_time_days:.4f} hr ({ov.mean_cycle_time_hours:.2f} jam) | Median: {ov.median_cycle_time_days:.2f} hr",
        )
        self.card_f02_fastslow.update_card(
            f"Fast: {ov.fast_cases_count:,} ({ov.fast_cases_pct:.1f}%)",
            f"Slow (>=45 hr): {ov.slow_cases_count:,} ({ov.slow_cases_pct:.1f}%)",
        )
        self.lbl_f02_timerange.setText(
            f"Rentang Waktu Event Log: {ov.log_start_time}  s/d  {ov.log_end_time}  |  "
            f"Simpangan Baku (Std Dev) Cycle Time: {ov.std_cycle_time_days:.4f} hari"
        )
        self.model_f02_act.set_dataframe(ov.activity_table)
        self.model_f02_cases.set_dataframe(ov.case_table)

    def _populate_f03(self, b: FullAnalysisBundle) -> None:
        r = b.ex117
        self.card_117a.update_card(f"{r.sub_a.case_count:,} Case", "100.00% dari log aktif")
        self.card_117b.update_card(
            f"{r.sub_b.mean_duration_days:.2f} Hari",
            f"Presisi: {r.sub_b.mean_duration_days:.4f} hr ({r.sub_b.mean_duration_hours:.2f} jam)",
        )
        self.card_117c.update_card(
            f"{r.sub_c.case_count:,} Case ({r.sub_c.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_c.mean_duration_days:.2f} hr ({r.sub_c.mean_duration_days:.4f} hr)",
        )
        self.card_117d.update_card(
            f"{r.sub_d.case_count:,} Case ({r.sub_d.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_d.mean_duration_days:.2f} hr ({r.sub_d.mean_duration_days:.4f} hr)",
        )
        self.card_117e.update_card(
            f"{r.sub_e.case_count:,} Case ({r.sub_e.case_percentage:.2f}%)",
            f"Mean Cycle Time: {r.sub_e.mean_duration_days:.2f} hr ({r.sub_e.mean_duration_days:.4f} hr)",
        )
        self.lbl_117_rule_note.setText(
            f"Perbandingan Semantik Filter 11.7: "
            f"(1) 11.7 C [Contains O_Accepted] = {r.sub_c.case_count:,} case (Mean {r.sub_c.mean_duration_days:.2f} hr). "
            f"(2) 11.7 D [Contains O_Refused] = {r.sub_d.case_count:,} case (Mean {r.sub_d.mean_duration_days:.2f} hr). "
            f"Irisan case yang memuat keduanya (O_Accepted & O_Refused) = {r.overlap_c_and_d_count:,} case. "
            f"(3) 11.7 E [Event TERAKHIR == O_Cancelled] = {r.sub_e.case_count:,} case (Mean {r.sub_e.mean_duration_days:.2f} hr). "
            f"(Sebagai perbandingan: terdapat {r.contains_cancelled_anywhere_count:,} case yang memuat O_Cancelled di posisi mana pun, namun {r.contains_cancelled_anywhere_count - r.sub_e.case_count:,} di antaranya masih diikuti aktivitas lain seperti W_Call after offers sehingga bukan berakhir di O_Cancelled)."
        )
        self._on_117_group_changed()

    def _populate_f04_f05(self, b: FullAnalysisBundle) -> None:
        r15 = b.ex1115
        r18 = b.ex1118
        self.card_1115_ans.update_card(
            f"{r15.matching_case_count:,} Case",
            f"Dari {r15.total_cases_denominator:,} case ({r15.matching_percentage:.4f}%)",
        )
        self.card_1115_excl.update_card(
            f"{r15.excluded_by_lifecycle_count:,} Case Tereliminasi",
            f"Semua lifecycle >=2x: {r15.cases_with_two_all_lifecycles:,} case vs Complete >=2x: {r15.matching_case_count:,} case",
        )
        self.card_1118_ans.update_card(
            f"{r18.matching_case_count:,} Case",
            f"Complete >=2x oleh resource identik ({r18.matching_percentage:.4f}%)",
        )
        self.card_1118_diff.update_card(
            f"{len(r18.cases_from_1115_excluded_diff_resource):,} Case",
            "Lolos 11.15 (>=2 complete) tetapi oleh resource berbeda/kosong",
        )

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
            f"Menampilkan seluruh {len(r15.evidence_events_df)} bukti kejadian 'complete' untuk {r15.matching_case_count} case yang lolos Exercise 11.15 (Klik baris case di atas untuk memfilter per case)."
        )

    def _populate_f06(self, b: FullAnalysisBundle) -> None:
        r22 = b.ex1122
        ans_prefix = "Ya, Ada" if r22.matching_case_count > 0 else "Tidak Ada"
        self.card_1122_ans.update_card(
            f"{ans_prefix}: {r22.matching_case_count:,} Case",
            f"Memenuhi posisi i(O_Cancelled) < j(O_Accepted)",
        )
        self.card_1122_pct.update_card(
            f"{r22.matching_percentage:.2f}% ({r22.matching_percentage:.4f}%)",
            f"Denominator: {r22.matching_case_count:,} / {r22.total_cases_denominator:,} case aktif",
        )
        self.card_1122_rev.update_card(
            f"{r22.reverse_only_count:,} Case",
            f"Dari {r22.both_present_any_order_count:,} case yang memuat keduanya, {r22.reverse_only_count:,} hanya O_Accepted -> O_Cancelled",
        )
        self.card_1122_offer.update_card(
            f"Same OfferID: {r22.same_offer_id_matching_count} Case",
            "Penjelasan 7.3: Penawaran lama dibatalkan (O_Cancelled), lalu penawaran baru diterima (O_Accepted)",
        )
        self.model_1122_cases.set_dataframe(r22.case_summary_df)
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

    # ------------------------------------------------------------------
    # INTERACTIVE FILTER & DRILL-DOWN HANDLERS
    # ------------------------------------------------------------------
    def _on_filter_f02_cases(self, text: str) -> None:
        self.proxy_f02_cases.setFilterFixedString(text)

    def _on_117_group_changed(self) -> None:
        if self.bundle is None:
            return
        idx = self.cmb_117_group.currentIndex()
        r = self.bundle.ex117
        if idx == 0:
            self.model_117_cases.set_dataframe(r.sub_c.case_df)
        elif idx == 1:
            self.model_117_cases.set_dataframe(r.sub_d.case_df)
        elif idx == 2:
            self.model_117_cases.set_dataframe(r.sub_e.case_df)
        else:
            self.model_117_cases.set_dataframe(r.sub_a.case_df)

    def _on_filter_117_table(self, text: str) -> None:
        self.proxy_117_cases.setFilterFixedString(text)

    def _on_filter_1122_table(self, text: str) -> None:
        self.proxy_1122_cases.setFilterFixedString(text)

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
            f"Bukti Event 11.15 untuk Case {cid}: menampilkan seluruh event '{self.bundle.ex1115.target_activity}' (baris kuning = lifecycle 'complete' yang dihitung; baris biru = lifecycle lain seperti schedule/start/suspend/resume)."
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
            f"Bukti Event 11.18 untuk Case {cid} (Resource Sama: {rid}): baris kuning menunjukkan >=2 kejadian 'complete' oleh resource {rid}."
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
            f"CONTOH PEMBUKTIAN FILTER COMPLETE-ONLY (Bagian 7.2) — Case {r15.example_excluded_case_id}: Memiliki {len(r15.example_excluded_events_df)} event '{r15.target_activity}' (schedule/start/suspend/resume), namun hanya 1 yang berstatus 'complete' (baris kuning), sehingga TIDAK diloloskan oleh Exercise 11.15."
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
            f"BUKTI PERBEDAAN 11.15 vs 11.18 — Menampilkan {len(r18.cases_from_1115_excluded_diff_resource)} case yang memiliki >=2 'complete' (lolos 11.15), tetapi diselesaikan oleh org:resource yang BERBEDA atau kosong (tidak lolos 11.18)."
        )

    def _on_select_1122_case(self, index: QModelIndex) -> None:
        if self.bundle is None or not index.isValid():
            return
        src_idx = self.proxy_1122_cases.mapToSource(index)
        df_22 = self.model_1122_cases.get_dataframe()
        cid = str(df_22.iloc[src_idx.row()]["case_id"])
        ev = self.bundle.context.get_case_events(cid)
        cols = [c for c in ["_trace_pos", "time:timestamp", "concept:name", "lifecycle:transition", "org:resource", "OfferID", "EventID"] if c in ev.columns]
        self.model_1122_evidence.set_dataframe(
            ev[cols],
            highlight_activities=["O_Cancelled", "O_Accepted"],
        )
        self.lbl_1122_timeline_info.setText(
            f"Trace Lengkap Case {cid} ({len(ev)} event): Baris kuning menandai urutan O_Cancelled yang kemudian diikuti oleh O_Accepted."
        )

    # ------------------------------------------------------------------
    # CASE EXPLORER NAVIGATION (F07)
    # ------------------------------------------------------------------
    def _get_selected_case_id_from_table(self, table: QTableView, proxy: Optional[QSortFilterProxyModel], model: DataFrameTableModel) -> Optional[str]:
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
        cid = self._get_selected_case_id_from_table(self.table_f02_cases, self.proxy_f02_cases, self.model_f02_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=0)

    def _on_inspect_from_117(self) -> None:
        cid = self._get_selected_case_id_from_table(self.table_117_cases, self.proxy_117_cases, self.model_117_cases)
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
        cid = self._get_selected_case_id_from_table(self.table_1122_cases, self.proxy_1122_cases, self.model_1122_cases)
        if cid:
            self.open_case_in_explorer(cid, filter_group_index=6)

    def open_case_in_explorer(self, case_id: str, filter_group_index: int = 0) -> None:
        self.tabs.setCurrentIndex(5)  # Switch to Case Explorer tab
        self.cmb_explorer_filter.setCurrentIndex(filter_group_index)
        self.txt_explorer_search.setText(case_id)
        self._display_case_trace_in_explorer(case_id)

    def _on_reset_explorer(self) -> None:
        self.cmb_explorer_filter.setCurrentIndex(0)
        self.txt_explorer_search.clear()

    def _on_explorer_search_changed(self, text: str) -> None:
        self.proxy_explorer_cases.setFilterFixedString(text)

    def _on_explorer_group_changed(self) -> None:
        if self.bundle is None:
            return
        idx = self.cmb_explorer_filter.currentIndex()
        b = self.bundle
        total = b.overview.total_cases

        if idx == 0:
            df = b.overview.case_table
            rule = f"Semua Case Aktif: {len(df):,} / {total:,} case (100.00%)"
            self._explorer_highlights = ([], None)
        elif idx == 1:
            df = b.ex117.sub_c.case_df
            rule = f"[11.7 C] {b.ex117.sub_c.rule_description} | Lolos: {len(df):,} / {total:,} case ({b.ex117.sub_c.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Accepted"], None)
        elif idx == 2:
            df = b.ex117.sub_d.case_df
            rule = f"[11.7 D] {b.ex117.sub_d.rule_description} | Lolos: {len(df):,} / {total:,} case ({b.ex117.sub_d.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Refused"], None)
        elif idx == 3:
            df = b.ex117.sub_e.case_df
            rule = f"[11.7 E] {b.ex117.sub_e.rule_description} | Lolos: {len(df):,} / {total:,} case ({b.ex117.sub_e.case_percentage:.2f}%)"
            self._explorer_highlights = (["O_Cancelled"], None)
        elif idx == 4:
            df = b.ex1115.case_summary_df
            rule = f"[11.15] {b.ex1115.rule_description} | Lolos: {len(df):,} / {total:,} case ({b.ex1115.matching_percentage:.4f}%)"
            self._explorer_highlights = ([b.ex1115.target_activity], "complete")
        elif idx == 5:
            df = b.ex1118.case_resource_summary_df
            rule = f"[11.18] {b.ex1118.rule_description} | Lolos: {b.ex1118.matching_case_count:,} / {total:,} case ({b.ex1118.matching_percentage:.4f}%)"
            self._explorer_highlights = ([b.ex1118.target_activity], "complete")
        else:
            df = b.ex1122.case_summary_df
            rule = f"[11.22] {b.ex1122.rule_description} | Lolos: {len(df):,} / {total:,} case ({b.ex1122.matching_percentage:.2f}% / {b.ex1122.matching_percentage:.4f}%)"
            self._explorer_highlights = (["O_Cancelled", "O_Accepted"], None)

        self.lbl_explorer_rule_banner.setText(rule)
        self.model_explorer_cases.set_dataframe(df)
        if not df.empty:
            first_cid = str(df.iloc[0]["case_id"])
            self._display_case_trace_in_explorer(first_cid)

    def _on_explorer_case_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        src_idx = self.proxy_explorer_cases.mapToSource(index)
        df = self.model_explorer_cases.get_dataframe()
        if not df.empty and 0 <= src_idx.row() < len(df):
            cid = str(df.iloc[src_idx.row()]["case_id"])
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
                f"Case ID: {case_id}  |  Jumlah Event: {len(ev)}  |  "
                f"Cycle Time: {dur_d:.4f} hari ({dur_h:.2f} jam)  |  "
                f"Event Pertama: {f_act}  |  Event Terakhir: {l_act}"
            )
        else:
            meta_txt = f"Case ID: {case_id} ({len(ev)} event)"

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
            "Tentang Aplikasi & Reproduktibilitas",
            f"<h3>Aplikasi Desktop Analisis Event Log BPIC17</h3>"
            f"<p>Menjawab Latihan Bab 11 <i>Fundamentals of Business Process Management (FBPM)</i> "
            f"(Exercise 11.7 A–E, 11.15, 11.18, dan 11.22) menggunakan Python & PM4Py.</p>"
            f"<p><b>Versi Lingkungan & Dependency Utama:</b></p>"
            f"<ul>"
            f"<li><b>Python:</b> {env['Python']}</li>"
            f"<li><b>PM4Py:</b> {env['PM4Py']}</li>"
            f"<li><b>Pandas:</b> {env['Pandas']}</li>"
            f"<li><b>PySide6 (Qt GUI):</b> {env['PySide6']}</li>"
            f"<li><b>r4pm (XES Parser Accelerator):</b> {env['r4pm (XES accelerator)']}</li>"
            f"</ul>",
        )
