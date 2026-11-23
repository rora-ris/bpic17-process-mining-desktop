"""Core models, XES importer, and validator using PM4Py."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

os.environ.setdefault("PM4PY_SHOW_CONSOLE_MESSAGE", "0")

import pandas as pd
import pm4py

REQUIRED_COLUMNS = ["case:concept:name", "concept:name", "time:timestamp"]
OPTIONAL_KEY_COLUMNS = ["lifecycle:transition", "org:resource", "OfferID", "EventID", "EventOrigin", "Action"]
INVALID_RESOURCE_STRINGS = {"", "nan", "none", "null", "unknown", "undefined", "n/a", "-"}


@dataclass
class ValidationReport:
    """Represents validation results of an imported XES event log."""
    is_valid: bool
    file_path: str
    file_name: str
    file_size_mb: float
    load_time_seconds: float
    total_cases: int
    total_events: int
    available_columns: List[str]
    trace_attributes: List[str]
    event_attributes: List[str]
    has_lifecycle: bool
    has_resource: bool
    has_offer_id: bool
    lifecycle_values: List[str]
    missing_required: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class EventLogContext:
    """Holds the active PM4Py event log DataFrame and precomputed case-level metadata."""

    def __init__(self, df: pd.DataFrame, report: ValidationReport):
        self.df = df
        self.report = report

        # Precompute case-level summary table (preserving trace context)
        self.case_summary_df = self._build_case_summary(df)
        self.activity_freq_df = self._build_activity_frequency(df)

    @staticmethod
    def _build_case_summary(df: pd.DataFrame) -> pd.DataFrame:
        """Computes case-level timestamps, event counts, start/end activities, and cycle times.
        
        Follows Section 4 & 7.1:
        - Cycle time = timestamp of last event minus timestamp of first event in the trace.
        - Also computes (max - min) duration to ensure full consistency.
        - Never removes events before computing case duration.
        """
        case_col = "case:concept:name"
        act_col = "concept:name"
        ts_col = "time:timestamp"

        grp = df.groupby(case_col, sort=False)

        first_ts = grp[ts_col].first()
        last_ts = grp[ts_col].last()
        min_ts = grp[ts_col].min()
        max_ts = grp[ts_col].max()
        event_count = grp.size()
        first_act = grp[act_col].first()
        last_act = grp[act_col].last()

        duration_sec = (last_ts - first_ts).dt.total_seconds()
        duration_days = duration_sec / 86400.0
        duration_hours = duration_sec / 3600.0

        minmax_sec = (max_ts - min_ts).dt.total_seconds()
        minmax_days = minmax_sec / 86400.0

        summary = pd.DataFrame({
            "case_id": first_ts.index.astype(str),
            "event_count": event_count.to_numpy(),
            "start_timestamp": first_ts.array,
            "end_timestamp": last_ts.array,
            "first_activity": first_act.to_numpy(),
            "last_activity": last_act.to_numpy(),
            "duration_seconds": duration_sec.to_numpy(),
            "duration_hours": duration_hours.to_numpy(),
            "duration_days": duration_days.to_numpy(),
            "minmax_duration_days": minmax_days.to_numpy(),
        })
        summary["speed_category"] = summary["duration_days"].apply(
            lambda d: "Fast (< 45 hari)" if d < 45.0 else "Slow (>= 45 hari)"
        )
        summary.index = summary["case_id"]
        return summary

    @staticmethod
    def _build_activity_frequency(df: pd.DataFrame) -> pd.DataFrame:
        """Computes activity frequency at both event level and unique case level."""
        case_col = "case:concept:name"
        act_col = "concept:name"
        total_cases = df[case_col].nunique()
        total_events = len(df)

        event_counts = df[act_col].value_counts()
        case_counts = df.groupby(act_col, sort=False)[case_col].nunique()

        has_lc = "lifecycle:transition" in df.columns
        if has_lc:
            comp_df = df[df["lifecycle:transition"].astype(str).str.lower() == "complete"]
            comp_event_counts = comp_df[act_col].value_counts()
        else:
            comp_event_counts = event_counts

        rows = []
        for act, ev_cnt in event_counts.items():
            c_cnt = int(case_counts.get(act, 0))
            comp_cnt = int(comp_event_counts.get(act, 0))
            rows.append({
                "activity": str(act),
                "event_count": int(ev_cnt),
                "complete_event_count": comp_cnt,
                "event_pct": (ev_cnt / total_events * 100.0) if total_events > 0 else 0.0,
                "case_count": c_cnt,
                "case_pct": (c_cnt / total_cases * 100.0) if total_cases > 0 else 0.0,
            })
        return pd.DataFrame(rows)

    def get_case_events(self, case_id: str) -> pd.DataFrame:
        """Returns all events belonging to a specific case ID in exact trace order."""
        sub = self.df[self.df["case:concept:name"].astype(str) == str(case_id)].copy()
        if "_trace_pos" in sub.columns:
            sub = sub.sort_values("_trace_pos", kind="mergesort")
        return sub


def get_environment_info() -> Dict[str, str]:
    """Returns Python, PM4Py, Pandas, and PySide6 versions for reproducibility (Section 7.1)."""
    info = {
        "Python": sys.version.split()[0],
        "PM4Py": getattr(pm4py, "__version__", "unknown"),
        "Pandas": getattr(pd, "__version__", "unknown"),
    }
    try:
        import PySide6
        info["PySide6"] = getattr(PySide6, "__version__", "unknown")
    except ImportError:
        info["PySide6"] = "not installed"
    try:
        import r4pm
        info["r4pm (XES accelerator)"] = getattr(r4pm, "__version__", "installed")
    except ImportError:
        info["r4pm (XES accelerator)"] = "not installed"
    return info


def load_and_validate_xes(
    file_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[Optional[EventLogContext], ValidationReport]:
    """Loads an XES (.xes or .xes.gz) file via PM4Py and validates required attributes (F01)."""
    t0 = time.time()
    if progress_callback:
        progress_callback(f"Memeriksa berkas: {os.path.basename(file_path)}...")

    if not os.path.exists(file_path):
        report = ValidationReport(
            is_valid=False,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size_mb=0.0,
            load_time_seconds=0.0,
            total_cases=0,
            total_events=0,
            available_columns=[],
            trace_attributes=[],
            event_attributes=[],
            has_lifecycle=False,
            has_resource=False,
            has_offer_id=False,
            lifecycle_values=[],
            error_message=f"Berkas tidak ditemukan: {file_path}",
        )
        return None, report

    file_size_mb = os.path.getsize(file_path) / (1024.0 * 1024.0)

    try:
        if progress_callback:
            progress_callback(f"Mengimpor event log XES dengan PM4Py ({file_size_mb:.2f} MB)...")

        raw_log = pm4py.read_xes(file_path)
        if not isinstance(raw_log, pd.DataFrame):
            df = pm4py.convert_to_dataframe(raw_log)
        else:
            df = raw_log.copy()

    except Exception as exc:
        elapsed = time.time() - t0
        report = ValidationReport(
            is_valid=False,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size_mb=file_size_mb,
            load_time_seconds=elapsed,
            total_cases=0,
            total_events=0,
            available_columns=[],
            trace_attributes=[],
            event_attributes=[],
            has_lifecycle=False,
            has_resource=False,
            has_offer_id=False,
            lifecycle_values=[],
            error_message=f"Gagal membaca berkas XES (file rusak atau format tidak valid): {exc}",
        )
        return None, report

    if progress_callback:
        progress_callback("Memvalidasi atribut wajib dan struktur trace...")

    cols = list(df.columns)
    missing_req = [c for c in REQUIRED_COLUMNS if c not in cols]
    if missing_req:
        elapsed = time.time() - t0
        report = ValidationReport(
            is_valid=False,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size_mb=file_size_mb,
            load_time_seconds=elapsed,
            total_cases=0,
            total_events=len(df),
            available_columns=cols,
            trace_attributes=[c for c in cols if c.startswith("case:")],
            event_attributes=[c for c in cols if not c.startswith("case:")],
            has_lifecycle="lifecycle:transition" in cols,
            has_resource="org:resource" in cols,
            has_offer_id="OfferID" in cols,
            lifecycle_values=[],
            missing_required=missing_req,
            error_message=f"Atribut wajib XES tidak ditemukan: {', '.join(missing_req)}",
        )
        return None, report

    if len(df) == 0:
        elapsed = time.time() - t0
        report = ValidationReport(
            is_valid=False,
            file_path=file_path,
            file_name=os.path.basename(file_path),
            file_size_mb=file_size_mb,
            load_time_seconds=elapsed,
            total_cases=0,
            total_events=0,
            available_columns=cols,
            trace_attributes=[c for c in cols if c.startswith("case:")],
            event_attributes=[c for c in cols if not c.startswith("case:")],
            has_lifecycle="lifecycle:transition" in cols,
            has_resource="org:resource" in cols,
            has_offer_id="OfferID" in cols,
            lifecycle_values=[],
            error_message="Event log kosong (tidak memiliki event/trace).",
        )
        return None, report

    # Normalize types and preserve original XML sequence order
    df["case:concept:name"] = df["case:concept:name"].astype(str)
    df["concept:name"] = df["concept:name"].astype(str)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)
    df["_event_idx"] = range(len(df))
    df["_trace_pos"] = df.groupby("case:concept:name", sort=False).cumcount() + 1

    has_lc = "lifecycle:transition" in cols
    has_res = "org:resource" in cols
    has_offer = "OfferID" in cols

    warnings: List[str] = []
    lc_values: List[str] = []
    if has_lc:
        lc_values = sorted(df["lifecycle:transition"].dropna().astype(str).unique().tolist())
    else:
        warnings.append(
            "Atribut 'lifecycle:transition' tidak tersedia di file XES ini; semua event akan dianggap sebagai 'complete'."
        )

    if not has_res:
        warnings.append(
            "Atribut 'org:resource' tidak tersedia di file XES ini; analisis same-resource (Exercise 11.18) tidak akan menemukan resource yang valid."
        )

    total_cases = int(df["case:concept:name"].nunique())
    total_events = int(len(df))

    if progress_callback:
        progress_callback("Menghitung metrik dasar dan durasi per case...")

    elapsed = time.time() - t0
    report = ValidationReport(
        is_valid=True,
        file_path=file_path,
        file_name=os.path.basename(file_path),
        file_size_mb=file_size_mb,
        load_time_seconds=elapsed,
        total_cases=total_cases,
        total_events=total_events,
        available_columns=cols,
        trace_attributes=[c for c in cols if c.startswith("case:")],
        event_attributes=[c for c in cols if not c.startswith("case:")],
        has_lifecycle=has_lc,
        has_resource=has_res,
        has_offer_id=has_offer,
        lifecycle_values=lc_values,
        warnings=warnings,
    )

    context = EventLogContext(df=df, report=report)
    return context, report
