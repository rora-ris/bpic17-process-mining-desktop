"""Core models, XES importer, and validator using PM4Py."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from typing import Any, Callable, Dict, List, Optional, Tuple

os.environ.setdefault("PM4PY_SHOW_CONSOLE_MESSAGE", "0")

import numpy as np
import pandas as pd


def _pkg_version(pkg_name: str, module_name: Optional[str] = None, fallback: str = "unknown") -> str:
    """Returns package version without importing heavy modules eagerly."""
    mod = sys.modules.get(module_name or pkg_name)
    if mod is not None and hasattr(mod, "__version__"):
        return str(getattr(mod, "__version__"))
    try:
        return importlib_metadata.version(pkg_name)
    except importlib_metadata.PackageNotFoundError:
        return fallback


def _ensure_stripped_str(s: pd.Series) -> pd.Series:
    """Returns stripped string Series, avoiding full-column copy if already clean strings."""
    uniq = s.unique()
    if all(type(v) is str and v == v.strip() for v in uniq):
        return s
    return s.map({v: str(v).strip() for v in uniq})

REQUIRED_COLUMNS = ["case:concept:name", "concept:name", "time:timestamp"]
OPTIONAL_KEY_COLUMNS = ["lifecycle:transition", "org:resource", "OfferID", "EventID", "EventOrigin", "Action"]
INVALID_RESOURCE_STRINGS = {"", "nan", "none", "null", "unknown", "undefined", "n/a", "-"}


def is_valid_resource(val: Any) -> bool:
    """Checks if a resource value is non-null, non-empty, and not a placeholder."""
    if val is None or pd.isna(val):
        return False
    s = str(val).strip()
    if s.lower() in INVALID_RESOURCE_STRINGS:
        return False
    return True


def is_valid_activity(val: Any) -> bool:
    """Checks if an activity name is non-null, non-empty, and not a placeholder."""
    if val is None or pd.isna(val):
        return False
    s = str(val).strip()
    if s.lower() in {"", "nan", "none", "null", "undefined"}:
        return False
    return True


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
        self._case_indices: Optional[Dict[str, np.ndarray]] = None

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

        # Cycle time calculation:
        # For chronological traces, (last_ts - first_ts) is equal to (max_ts - min_ts).
        # For traces with non-chronological events (e.g., last_ts < first_ts),
        # minmax_sec guarantees non-negative, accurate span of the case.
        raw_duration_sec = (last_ts - first_ts).dt.total_seconds().fillna(0.0).to_numpy()
        minmax_sec = (max_ts - min_ts).dt.total_seconds().fillna(0.0).to_numpy()

        duration_sec = np.where(raw_duration_sec < 0, minmax_sec, raw_duration_sec)
        duration_days = duration_sec / 86400.0
        duration_hours = duration_sec / 3600.0

        minmax_days = minmax_sec / 86400.0

        summary = pd.DataFrame({
            "case_id": first_ts.index.astype(str),
            "event_count": event_count.to_numpy(),
            "start_timestamp": first_ts.array,
            "end_timestamp": last_ts.array,
            "first_activity": first_act.to_numpy(),
            "last_activity": last_act.to_numpy(),
            "duration_seconds": duration_sec,
            "duration_hours": duration_hours,
            "duration_days": duration_days,
            "minmax_duration_days": minmax_days,
        })
        summary["speed_category"] = np.where(
            np.isfinite(duration_days) & (duration_days < 45.0),
            "Fast (< 45 hari)",
            "Slow (>= 45 hari)",
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
            comp_vals = [
                v for v in df["lifecycle:transition"].dropna().unique()
                if str(v).lower() == "complete"
            ]
            comp_df = df[df["lifecycle:transition"].isin(comp_vals)]
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
        if self._case_indices is None:
            self._case_indices = {
                str(k): idx
                for k, idx in self.df.groupby("case:concept:name", sort=False).indices.items()
            }
        idx = self._case_indices.get(str(case_id))
        if idx is None or len(idx) == 0:
            return self.df.iloc[0:0].copy()
        sub = self.df.iloc[idx].copy()
        if "_trace_pos" in sub.columns:
            sub = sub.sort_values("_trace_pos", kind="mergesort")
        return sub


def get_environment_info() -> Dict[str, str]:
    """Returns Python, PM4Py, Pandas, and PySide6 versions for reproducibility (Section 7.1)."""
    return {
        "Python": sys.version.split()[0],
        "PM4Py": _pkg_version("pm4py"),
        "Pandas": _pkg_version("pandas"),
        "PySide6": _pkg_version("PySide6", fallback="not installed"),
        "r4pm (XES accelerator)": _pkg_version("r4pm", fallback="not installed"),
    }


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

        import pm4py

        raw_log = pm4py.read_xes(file_path)
        if not isinstance(raw_log, pd.DataFrame):
            df = pm4py.convert_to_dataframe(raw_log)
        else:
            df = raw_log

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
            has_lifecycle=False,
            has_resource=False,
            has_offer_id=False,
            lifecycle_values=[],
            error_message="Event log kosong (tidak memiliki event/trace).",
        )
        return None, report

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

    # Validate that mandatory columns have no empty / NaN / placeholder values
    for req_col in REQUIRED_COLUMNS:
        col_series = df[req_col]
        if pd.api.types.is_datetime64_any_dtype(col_series):
            invalid_count = int(col_series.isna().sum())
        else:
            na_mask = col_series.isna()
            non_na = col_series[~na_mask]
            bad_vals = {
                v for v in non_na.unique()
                if str(v).strip().lower() in {"", "nan", "none", "null"}
            }
            invalid_count = (
                int(na_mask.sum() + non_na.isin(bad_vals).sum())
                if bad_vals
                else int(na_mask.sum())
            )
        if invalid_count > 0:
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
                missing_required=[],
                error_message=f"Kolom wajib XES '{req_col}' memuat {invalid_count} baris bernilai kosong/NaN/tidak valid.",
            )
            return None, report

    # Safe datetime parsing with error wrapping and NaT check
    try:
        ts_series = df["time:timestamp"]
        if pd.api.types.is_datetime64_any_dtype(ts_series):
            if ts_series.dt.tz is None:
                df["time:timestamp"] = ts_series.dt.tz_localize("UTC")
            else:
                df["time:timestamp"] = ts_series.dt.tz_convert("UTC")
        else:
            df["time:timestamp"] = pd.to_datetime(ts_series, utc=True, errors="coerce")
        nat_count = int(df["time:timestamp"].isna().sum())
        if nat_count > 0:
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
                missing_required=[],
                error_message=f"Gagal mem-parse timestamp pada kolom 'time:timestamp': ditemukan {nat_count} nilai tidak valid atau NaT.",
            )
            return None, report
    except Exception as exc:
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
            missing_required=[],
            error_message=f"Gagal mem-parse kolom 'time:timestamp': {exc}",
        )
        return None, report

    # Normalize types and preserve original XML sequence order
    df["case:concept:name"] = _ensure_stripped_str(df["case:concept:name"])
    df["concept:name"] = _ensure_stripped_str(df["concept:name"])
    df["_event_idx"] = np.arange(len(df))
    df["_trace_pos"] = df.groupby("case:concept:name", sort=False).cumcount() + 1

    warnings: List[str] = []

    # Detect non-chronological events within traces
    ts_diffs = df.groupby("case:concept:name", sort=False)["time:timestamp"].diff()
    non_chrono_mask = ts_diffs.dt.total_seconds() < 0
    if non_chrono_mask.any():
        non_chrono_cases = int(df.loc[non_chrono_mask, "case:concept:name"].nunique())
        warnings.append(
            f"Ditemukan {non_chrono_cases} trace dengan urutan event yang tidak berurutan secara kronologis "
            f"(timestamp mundur); durasi per case diamankan menggunakan rentang (max - min) timestamp."
        )

    # Validate optional columns: lifecycle:transition
    has_lc = False
    lc_values: List[str] = []
    if "lifecycle:transition" in cols:
        lc_vals_raw = df["lifecycle:transition"].dropna().unique()
        lc_clean = {
            str(v).strip()
            for v in lc_vals_raw
            if str(v).strip().lower() not in {"", "nan", "none", "null", "undefined"}
        }
        if lc_clean:
            has_lc = True
            lc_values = sorted(lc_clean)
        else:
            warnings.append(
                "Kolom 'lifecycle:transition' ada di berkas XES tetapi 100% nilainya kosong/tidak valid; semua event akan dianggap sebagai 'complete'."
            )
    else:
        warnings.append(
            "Atribut 'lifecycle:transition' tidak tersedia di file XES ini; semua event akan dianggap sebagai 'complete'."
        )

    # Validate optional columns: org:resource
    has_res = False
    if "org:resource" in cols:
        has_res = any(is_valid_resource(v) for v in df["org:resource"].dropna().unique())
        if not has_res:
            warnings.append(
                "Kolom 'org:resource' ada di berkas XES tetapi 100% nilainya kosong/tidak valid; analisis same-resource (Exercise 11.18) tidak akan menemukan resource yang valid."
            )
    else:
        warnings.append(
            "Atribut 'org:resource' tidak tersedia di file XES ini; analisis same-resource (Exercise 11.18) tidak akan menemukan resource yang valid."
        )

    has_offer = "OfferID" in cols

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
