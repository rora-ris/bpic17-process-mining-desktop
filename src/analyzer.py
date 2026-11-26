"""Analysis engine implementing F02 through F07 and optional enrichment features."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .core import INVALID_RESOURCE_STRINGS, EventLogContext, is_valid_activity, is_valid_resource


def format_duration_human(days: float) -> str:
    """Formats duration in days into an adaptive human-readable string with units."""
    if pd.isna(days) or days < 0:
        return "0.0000 hari (0.0 dtk)"
    sec = days * 86400.0
    if sec < 60.0:
        return f"{sec:.2f} detik ({days:.6f} hari)"
    if sec < 3600.0:
        mins = sec / 60.0
        return f"{mins:.2f} menit ({days:.5f} hari)"
    if sec < 86400.0:
        hrs = sec / 3600.0
        return f"{hrs:.2f} jam ({days:.4f} hari)"
    hrs = sec / 3600.0
    return f"{days:.2f} hari ({days:.4f} hari / {hrs:.1f} jam)"


@dataclass
class OverviewResult:
    """F02 — Event Log Overview and descriptive statistics."""
    total_cases: int
    total_events: int
    unique_activities: int
    unique_resources: int
    log_start_time: str
    log_end_time: str
    mean_cycle_time_days: float
    mean_cycle_time_hours: float
    mean_cycle_time_seconds: float
    median_cycle_time_days: float
    min_cycle_time_days: float
    max_cycle_time_days: float
    std_cycle_time_days: float
    fast_cases_count: int
    fast_cases_pct: float
    fast_cases_mean_days: float
    slow_cases_count: int
    slow_cases_pct: float
    slow_cases_mean_days: float
    activity_table: pd.DataFrame
    case_table: pd.DataFrame
    lifecycle_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class SubQuestion117:
    """Stores result for a single sub-question (A, B, C, D, or E) of Exercise 11.7."""
    code: str
    title: str
    rule_description: str
    filter_type: str
    case_count: int
    total_cases_denominator: int
    case_percentage: float
    mean_duration_days: float
    mean_duration_hours: float
    mean_duration_seconds: float
    median_duration_days: float
    min_duration_days: float
    max_duration_days: float
    case_df: pd.DataFrame


@dataclass
class Exercise117Result:
    """F03 — Complete results for Exercise 11.7 (A-E) plus diagnostic notes."""
    sub_a: SubQuestion117
    sub_b: SubQuestion117
    sub_c: SubQuestion117
    sub_d: SubQuestion117
    sub_e: SubQuestion117
    overlap_c_and_d_count: int
    contains_cancelled_anywhere_count: int
    contains_cancelled_anywhere_mean_days: float
    overlap_c_and_d_case_ids: List[str] = field(default_factory=list)


@dataclass
class Exercise1115Result:
    """F04 — Results for Exercise 11.15 (Repeated complete activity >= 2x)."""
    target_activity: str
    min_occurrences: int
    lifecycle_filter: str
    rule_description: str
    matching_case_count: int
    total_cases_denominator: int
    matching_percentage: float
    cases_with_at_least_one_complete: int
    cases_with_two_all_lifecycles: int
    excluded_by_lifecycle_count: int
    example_excluded_case_id: Optional[str]
    example_excluded_events_df: pd.DataFrame
    case_summary_df: pd.DataFrame
    evidence_events_df: pd.DataFrame
    excluded_case_ids: List[str] = field(default_factory=list)
    excluded_summary_df: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class Exercise1118Result:
    """F05 — Results for Exercise 11.18 (Repeated complete >= 2x by same resource)."""
    target_activity: str
    min_occurrences: int
    lifecycle_filter: str
    rule_description: str
    matching_case_count: int
    total_cases_denominator: int
    matching_percentage: float
    cases_from_1115_excluded_diff_resource: List[str]
    excluded_diff_resource_evidence_df: pd.DataFrame
    case_resource_summary_df: pd.DataFrame
    evidence_events_df: pd.DataFrame


@dataclass
class Exercise1122Result:
    """F06 — Results for Exercise 11.22 (O_Cancelled eventually followed by O_Accepted)."""
    first_activity: str
    second_activity: str
    rule_description: str
    matching_case_count: int
    total_cases_denominator: int
    matching_percentage: float
    both_present_any_order_count: int
    reverse_only_count: int
    same_offer_id_matching_count: int
    case_summary_df: pd.DataFrame
    evidence_events_df: pd.DataFrame
    excluded_case_ids: List[str] = field(default_factory=list)


def analyze_overview(ctx: EventLogContext) -> OverviewResult:
    """F02 — Computes overall event log statistics and case duration table."""
    df = ctx.df
    cs = ctx.case_summary_df

    total_cases = len(cs)
    total_events = len(df)

    # Filter valid activities consistently with valid resources
    unique_acts = sum(1 for v in df["concept:name"].dropna().unique() if is_valid_activity(v))

    if "org:resource" in df.columns:
        unique_res = sum(1 for v in df["org:resource"].dropna().unique() if is_valid_resource(v))
    else:
        unique_res = 0

    min_ts = df["time:timestamp"].min() if not df.empty else None
    max_ts = df["time:timestamp"].max() if not df.empty else None

    # Handle duration series safely against NaN
    dur_days = cs["duration_days"].fillna(0.0) if not cs.empty else pd.Series(dtype=float)
    dur_hours = cs["duration_hours"].fillna(0.0) if not cs.empty else pd.Series(dtype=float)
    dur_secs = cs["duration_seconds"].fillna(0.0) if not cs.empty else pd.Series(dtype=float)

    mean_days = float(dur_days.mean()) if total_cases > 0 else 0.0
    mean_hours = float(dur_hours.mean()) if total_cases > 0 else 0.0
    mean_secs = float(dur_secs.mean()) if total_cases > 0 else 0.0
    median_days = float(dur_days.median()) if total_cases > 0 else 0.0
    min_days = float(dur_days.min()) if total_cases > 0 else 0.0
    max_days = float(dur_days.max()) if total_cases > 0 else 0.0
    std_days = float(dur_days.std(ddof=1)) if total_cases > 1 else 0.0
    if pd.isna(std_days):
        std_days = 0.0

    # Optional enrichment (Section 12): Fast (< 45 days) vs Slow (>= 45 days) cases (Example 11.10)
    # Complementary boolean mask ensures fast_cnt + slow_cnt == total_cases (100.0%)
    fast_mask = dur_days < 45.0
    slow_mask = ~fast_mask
    fast_cnt = int(fast_mask.sum())
    slow_cnt = int(slow_mask.sum())
    fast_pct = (fast_cnt / total_cases * 100.0) if total_cases > 0 else 0.0
    slow_pct = (slow_cnt / total_cases * 100.0) if total_cases > 0 else 0.0
    fast_mean = float(dur_days[fast_mask].mean()) if fast_cnt > 0 else 0.0
    slow_mean = float(dur_days[slow_mask].mean()) if slow_cnt > 0 else 0.0
    if pd.isna(fast_mean):
        fast_mean = 0.0
    if pd.isna(slow_mean):
        slow_mean = 0.0

    lc_counts: Dict[str, int] = {}
    if ctx.report.has_lifecycle and "lifecycle:transition" in df.columns and not df.empty:
        vc = df["lifecycle:transition"].value_counts(dropna=True)
        agg: Dict[str, int] = {}
        for k, v in vc.items():
            clean_k = str(k).strip().lower()
            if clean_k not in {"", "nan", "none", "null", "undefined"}:
                agg[clean_k] = agg.get(clean_k, 0) + int(v)
        lc_counts = dict(sorted(agg.items(), key=lambda kv: kv[1], reverse=True))

    return OverviewResult(
        total_cases=total_cases,
        total_events=total_events,
        unique_activities=unique_acts,
        unique_resources=unique_res,
        log_start_time=str(min_ts) if min_ts is not None else "-",
        log_end_time=str(max_ts) if max_ts is not None else "-",
        mean_cycle_time_days=mean_days,
        mean_cycle_time_hours=mean_hours,
        mean_cycle_time_seconds=mean_secs,
        median_cycle_time_days=median_days,
        min_cycle_time_days=min_days,
        max_cycle_time_days=max_days,
        std_cycle_time_days=std_days,
        fast_cases_count=fast_cnt,
        fast_cases_pct=fast_pct,
        fast_cases_mean_days=fast_mean,
        slow_cases_count=slow_cnt,
        slow_cases_pct=slow_pct,
        slow_cases_mean_days=slow_mean,
        activity_table=ctx.activity_freq_df,
        case_table=cs,
        lifecycle_counts=lc_counts,
    )


def _make_subquestion_117(
    code: str,
    title: str,
    rule_description: str,
    filter_type: str,
    case_df: pd.DataFrame,
    total_cases: int,
) -> SubQuestion117:
    cnt = len(case_df)
    pct = (cnt / total_cases * 100.0) if total_cases > 0 else 0.0
    if cnt > 0:
        mean_d = float(case_df["duration_days"].mean())
        mean_h = float(case_df["duration_hours"].mean())
        mean_s = float(case_df["duration_seconds"].mean())
        med_d = float(case_df["duration_days"].median())
        min_d = float(case_df["duration_days"].min())
        max_d = float(case_df["duration_days"].max())
    else:
        mean_d = mean_h = mean_s = med_d = min_d = max_d = 0.0

    return SubQuestion117(
        code=code,
        title=title,
        rule_description=rule_description,
        filter_type=filter_type,
        case_count=cnt,
        total_cases_denominator=total_cases,
        case_percentage=pct,
        mean_duration_days=mean_d,
        mean_duration_hours=mean_h,
        mean_duration_seconds=mean_s,
        median_duration_days=med_d,
        min_duration_days=min_d,
        max_duration_days=max_d,
        case_df=case_df,
    )


def analyze_exercise_11_7(ctx: EventLogContext) -> Exercise117Result:
    """F03 — Computes answers and case evidence for Exercise 11.7 (A-E).

    Operates on the PM4Py-parsed event log DataFrame using case-level trace filtering
    semantics while preserving full trace cycle time computed before any event removal (Section 7.1).
    """
    df = ctx.df
    cs = ctx.case_summary_df
    total_cases = len(cs)
    case_col = "case:concept:name"
    act_col = "concept:name"

    # 11.7 A & B: All unique cases in active log
    sub_a = _make_subquestion_117(
        code="11.7 A",
        title="Jumlah Keseluruhan Case",
        rule_description="Hitung seluruh unique case/trace dari keseluruhan event log aktif.",
        filter_type="All Cases (Unique case:concept:name)",
        case_df=cs,
        total_cases=total_cases,
    )
    sub_b = _make_subquestion_117(
        code="11.7 B",
        title="Rata-rata Cycle Time Seluruh Case",
        rule_description="Durasi tiap case = timestamp event terakhir dikurangi event pertama pada trace; dihitung rata-ratanya dalam satuan hari.",
        filter_type="All Cases Cycle Time (Last Timestamp - First Timestamp)",
        case_df=cs,
        total_cases=total_cases,
    )

    # 11.7 C: Successful cases -> Case CONTAINS at least one event O_Accepted
    c_mask = df[act_col] == "O_Accepted"
    c_case_ids = df.loc[c_mask, case_col].unique()
    c_occurrences = df.loc[c_mask].groupby(case_col, sort=False).size()
    cs_c = cs.loc[cs.index.intersection(c_case_ids)].copy()
    cs_c["trigger_activity"] = "O_Accepted"
    cs_c["trigger_count"] = cs_c["case_id"].map(c_occurrences).fillna(0).astype(int)

    sub_c = _make_subquestion_117(
        code="11.7 C",
        title="Successful Cases & Rata-rata Cycle Time",
        rule_description="Contains Filter: Case memuat setidaknya satu event 'O_Accepted' (dihitung 1x per case meskipun O_Accepted muncul >1x).",
        filter_type="Contains('O_Accepted')",
        case_df=cs_c,
        total_cases=total_cases,
    )

    # 11.7 D: Unsuccessful cases -> Case CONTAINS at least one event O_Refused
    d_mask = df[act_col] == "O_Refused"
    d_case_ids = df.loc[d_mask, case_col].unique()
    d_occurrences = df.loc[d_mask].groupby(case_col, sort=False).size()
    cs_d = cs.loc[cs.index.intersection(d_case_ids)].copy()
    cs_d["trigger_activity"] = "O_Refused"
    cs_d["trigger_count"] = cs_d["case_id"].map(d_occurrences).fillna(0).astype(int)

    sub_d = _make_subquestion_117(
        code="11.7 D",
        title="Unsuccessful Cases & Rata-rata Cycle Time",
        rule_description="Contains Filter: Case memuat setidaknya satu event 'O_Refused' (tidak dipaksa saling eksklusif dengan 11.7 C).",
        filter_type="Contains('O_Refused')",
        case_df=cs_d,
        total_cases=total_cases,
    )

    # 11.7 E: Canceled cases -> LAST event in trace is O_Cancelled
    cs_e = cs[cs["last_activity"] == "O_Cancelled"].copy()
    e_occurrences = df.loc[df[act_col] == "O_Cancelled"].groupby(case_col, sort=False).size()
    cs_e["trigger_activity"] = "O_Cancelled (Endpoint)"
    cs_e["trigger_count"] = cs_e["case_id"].map(e_occurrences).fillna(0).astype(int)

    sub_e = _make_subquestion_117(
        code="11.7 E",
        title="Canceled Cases & Rata-rata Cycle Time",
        rule_description="Endpoint Filter: Event TERAKHIR pada urutan trace adalah 'O_Cancelled' (case dengan O_Cancelled di tengah trace tetapi diikuti event lain tidak lolos).",
        filter_type="EndsWith('O_Cancelled')",
        case_df=cs_e,
        total_cases=total_cases,
    )

    overlap_ids = sorted(list(set(cs_c.index).intersection(set(cs_d.index))))
    overlap_cd = len(overlap_ids)
    contains_canc_ids = df.loc[df[act_col] == "O_Cancelled", case_col].unique()
    cs_contains_canc = cs.loc[cs.index.intersection(contains_canc_ids)]
    contains_canc_mean = float(cs_contains_canc["duration_days"].mean()) if len(cs_contains_canc) > 0 else 0.0

    return Exercise117Result(
        sub_a=sub_a,
        sub_b=sub_b,
        sub_c=sub_c,
        sub_d=sub_d,
        sub_e=sub_e,
        overlap_c_and_d_count=overlap_cd,
        contains_cancelled_anywhere_count=len(cs_contains_canc),
        contains_cancelled_anywhere_mean_days=contains_canc_mean,
        overlap_c_and_d_case_ids=[str(x) for x in overlap_ids],
    )


def analyze_exercise_11_15(
    ctx: EventLogContext,
    target_activity: str = "W_Assess potential fraud",
    min_occurrences: int = 2,
    complete_only: bool = True,
) -> Exercise1115Result:
    """F04 — Analyzes cases where target_activity (W_Assess potential fraud) is completed >= 2 times.

    Matches activity name case-insensitively so 'W_Assess Potential Fraud' (PDF prompt)
    and 'W_Assess potential fraud' (BPIC17 XES concept:name) both match seamlessly.
    """
    df = ctx.df
    cs = ctx.case_summary_df
    total_cases = len(cs)
    case_col = "case:concept:name"
    act_col = "concept:name"
    lc_col = "lifecycle:transition"
    res_col = "org:resource"

    target_lower = target_activity.strip().lower()
    matching_acts = [
        v for v in df[act_col].dropna().unique()
        if str(v).strip().lower() == target_lower
    ]
    act_events = df[df[act_col].isin(matching_acts)].copy()

    # Count all lifecycle occurrences per case for comparison (Section 7.2)
    all_lc_counts = act_events.groupby(case_col, sort=False).size()
    cases_two_all_lc = all_lc_counts[all_lc_counts >= min_occurrences].index.tolist()

    has_lc = ctx.report.has_lifecycle and (lc_col in df.columns)
    if complete_only and has_lc:
        comp_events = act_events[act_events[lc_col].astype(str).str.strip().str.lower() == "complete"].copy()
        lc_label = "lifecycle:transition == 'complete'"
    else:
        comp_events = act_events.copy()
        lc_label = "Semua lifecycle (atau atribut lifecycle tidak ada)"

    comp_counts = comp_events.groupby(case_col, sort=False).size()
    cases_at_least_one = int((comp_counts >= 1).sum())
    qualifying_counts = comp_counts[comp_counts >= min_occurrences]
    qualifying_case_ids = qualifying_counts.index.tolist()

    # Find cases excluded by complete-only filter (had >=2 events across all lifecycles, but <2 complete)
    excluded_ids = sorted(list(set(cases_two_all_lc) - set(qualifying_case_ids)))
    example_excl_id = excluded_ids[0] if excluded_ids else None
    if example_excl_id is not None:
        example_excl_df = act_events[act_events[case_col] == example_excl_id].copy()
    else:
        example_excl_df = pd.DataFrame()

    if excluded_ids:
        excluded_summary_df = pd.DataFrame({
            "case_id": [str(cid) for cid in excluded_ids],
            "complete_occurrences": [int(comp_counts.get(cid, 0)) for cid in excluded_ids],
            "all_lifecycle_occurrences": [int(all_lc_counts.get(cid, 0)) for cid in excluded_ids],
        })
    else:
        excluded_summary_df = pd.DataFrame(columns=["case_id", "complete_occurrences", "all_lifecycle_occurrences"])

    # Build summary table per qualifying case
    summary_rows = []
    for cid in qualifying_case_ids:
        c_comp = comp_events[comp_events[case_col] == cid]
        c_all = act_events[act_events[case_col] == cid]
        resources_list = (
            c_comp[res_col].dropna().astype(str).tolist()
            if res_col in c_comp.columns
            else []
        )
        unique_valid_res = [r for r in dict.fromkeys(resources_list) if is_valid_resource(r)]
        dur_days = float(cs.loc[cid, "duration_days"]) if cid in cs.index else 0.0
        total_ev_in_case = int(cs.loc[cid, "event_count"]) if cid in cs.index else 0
        summary_rows.append({
            "case_id": cid,
            "complete_occurrences": int(len(c_comp)),
            "all_lifecycle_occurrences": int(len(c_all)),
            "resources_involved": ", ".join(resources_list) if resources_list else "-",
            "unique_valid_resources": len(unique_valid_res),
            "first_complete_time": str(c_comp["time:timestamp"].iloc[0]),
            "last_complete_time": str(c_comp["time:timestamp"].iloc[-1]),
            "case_total_events": total_ev_in_case,
            "case_duration_days": dur_days,
        })

    case_summary_df = pd.DataFrame(summary_rows)
    evidence_df = comp_events[comp_events[case_col].isin(qualifying_case_ids)].copy()

    rule_desc = (
        f"Pilih case dengan aktivitas '{target_activity}' berstatus {lc_label} "
        f"sebanyak minimal {min_occurrences} kali dalam satu trace."
    )
    pct = (len(qualifying_case_ids) / total_cases * 100.0) if total_cases > 0 else 0.0

    return Exercise1115Result(
        target_activity=target_activity,
        min_occurrences=min_occurrences,
        lifecycle_filter=lc_label,
        rule_description=rule_desc,
        matching_case_count=len(qualifying_case_ids),
        total_cases_denominator=total_cases,
        matching_percentage=pct,
        cases_with_at_least_one_complete=cases_at_least_one,
        cases_with_two_all_lifecycles=len(cases_two_all_lc),
        excluded_by_lifecycle_count=len(excluded_ids),
        example_excluded_case_id=example_excl_id,
        example_excluded_events_df=example_excl_df,
        case_summary_df=case_summary_df,
        evidence_events_df=evidence_df,
        excluded_case_ids=[str(x) for x in excluded_ids],
        excluded_summary_df=excluded_summary_df,
    )


def analyze_exercise_11_18(
    ctx: EventLogContext,
    target_activity: str = "W_Assess potential fraud",
    min_occurrences: int = 2,
    complete_only: bool = True,
    res_1115: Optional[Exercise1115Result] = None,
) -> Exercise1118Result:
    """F05 — Analyzes cases where target_activity is completed >= 2 times by the SAME valid resource.

    Explicitly excludes missing/empty/unknown resource values so two blank resources
    are never treated as the same resource (Section 4 & F05).
    """
    if res_1115 is None:
        res_1115 = analyze_exercise_11_15(
            ctx, target_activity=target_activity, min_occurrences=min_occurrences, complete_only=complete_only
        )
    df = ctx.df
    cs = ctx.case_summary_df
    total_cases = len(cs)
    case_col = "case:concept:name"
    act_col = "concept:name"
    lc_col = "lifecycle:transition"
    res_col = "org:resource"

    cases_1115_ids = (
        res_1115.case_summary_df["case_id"].astype(str).tolist()
        if not res_1115.case_summary_df.empty
        else []
    )

    if not ctx.report.has_resource or res_col not in df.columns:
        diff_res_cases = sorted(cases_1115_ids)
        diff_ev_df = (
            res_1115.evidence_events_df[res_1115.evidence_events_df[case_col].isin(diff_res_cases)].copy()
            if (diff_res_cases and not res_1115.evidence_events_df.empty)
            else pd.DataFrame()
        )
        return Exercise1118Result(
            target_activity=target_activity,
            min_occurrences=min_occurrences,
            lifecycle_filter=res_1115.lifecycle_filter,
            rule_description="Atribut org:resource tidak tersedia atau seluruhnya kosong/tidak valid pada dataset.",
            matching_case_count=0,
            total_cases_denominator=total_cases,
            matching_percentage=0.0,
            cases_from_1115_excluded_diff_resource=diff_res_cases,
            excluded_diff_resource_evidence_df=diff_ev_df,
            case_resource_summary_df=pd.DataFrame(),
            evidence_events_df=pd.DataFrame(),
        )

    target_lower = target_activity.strip().lower()
    matching_acts = [
        v for v in df[act_col].dropna().unique()
        if str(v).strip().lower() == target_lower
    ]
    act_events = df[df[act_col].isin(matching_acts)].copy()
    has_lc = ctx.report.has_lifecycle and (lc_col in df.columns)
    if complete_only and has_lc:
        comp_events = act_events[act_events[lc_col].astype(str).str.strip().str.lower() == "complete"].copy()
    else:
        comp_events = act_events.copy()

    # Filter out empty/missing/placeholder resources explicitly
    if comp_events.empty:
        valid_comp_events = comp_events.copy()
        valid_comp_events["_clean_resource"] = pd.Series(dtype=str)
    else:
        valid_res_mask = comp_events[res_col].apply(is_valid_resource).astype(bool)
        valid_comp_events = comp_events[valid_res_mask].copy()
        valid_comp_events["_clean_resource"] = valid_comp_events[res_col].astype(str).str.strip()

    # Group by (case_id, resource)
    pair_counts = valid_comp_events.groupby([case_col, "_clean_resource"], sort=False).size()
    qualifying_pairs = pair_counts[pair_counts >= min_occurrences]

    qualifying_case_ids = qualifying_pairs.index.get_level_values(0).unique().tolist()

    summary_rows = []
    evidence_indices = []
    for (cid, rid), cnt in qualifying_pairs.items():
        pair_ev = valid_comp_events[
            (valid_comp_events[case_col] == cid) & (valid_comp_events["_clean_resource"] == rid)
        ]
        evidence_indices.extend(pair_ev.index.tolist())
        total_comp_in_case = int((comp_events[case_col] == cid).sum())
        dur_days = float(cs.loc[cid, "duration_days"]) if cid in cs.index else 0.0
        event_ids = (
            ", ".join(pair_ev["EventID"].dropna().astype(str).tolist())
            if "EventID" in pair_ev.columns
            else "-"
        )
        summary_rows.append({
            "case_id": str(cid),
            "resource_id": str(rid),
            "same_resource_completions": int(cnt),
            "total_case_completions": total_comp_in_case,
            "first_complete_time": str(pair_ev["time:timestamp"].iloc[0]),
            "last_complete_time": str(pair_ev["time:timestamp"].iloc[-1]),
            "evidence_event_ids": event_ids,
            "case_duration_days": dur_days,
        })

    case_resource_summary_df = pd.DataFrame(summary_rows)
    evidence_df = valid_comp_events.loc[sorted(list(set(evidence_indices)))].drop(columns=["_clean_resource"], errors="ignore")

    # Identify cases that passed 11.15 (>=2 complete) but failed 11.18 (different resources or empty resources)
    diff_res_cases = sorted(list(set(cases_1115_ids) - set(qualifying_case_ids)))
    diff_res_evidence_df = comp_events[comp_events[case_col].isin(diff_res_cases)].copy()

    rule_desc = (
        f"Pilih case dengan aktivitas '{target_activity}' berstatus {res_1115.lifecycle_filter} "
        f"yang diselesaikan minimal {min_occurrences} kali oleh org:resource yang SAMA (resource kosong/tidak valid diabaikan)."
    )
    pct = (len(qualifying_case_ids) / total_cases * 100.0) if total_cases > 0 else 0.0

    return Exercise1118Result(
        target_activity=target_activity,
        min_occurrences=min_occurrences,
        lifecycle_filter=res_1115.lifecycle_filter,
        rule_description=rule_desc,
        matching_case_count=len(qualifying_case_ids),
        total_cases_denominator=total_cases,
        matching_percentage=pct,
        cases_from_1115_excluded_diff_resource=diff_res_cases,
        excluded_diff_resource_evidence_df=diff_res_evidence_df,
        case_resource_summary_df=case_resource_summary_df,
        evidence_events_df=evidence_df,
    )


def analyze_exercise_11_22(
    ctx: EventLogContext,
    first_activity: str = "O_Cancelled",
    second_activity: str = "O_Accepted",
) -> Exercise1122Result:
    """F06 — Analyzes cases where first_activity (O_Cancelled) is eventually followed by second_activity (O_Accepted).

    Definition (Section 3, 4, 7.3):
    There exists a pair of positions i < j in the trace such that event i is O_Cancelled
    and event j is O_Accepted (not necessarily adjacent).
    Condition: earliest_trace_pos(O_Cancelled) < latest_trace_pos(O_Accepted).
    """
    df = ctx.df
    cs = ctx.case_summary_df
    total_cases = len(cs)
    case_col = "case:concept:name"
    act_col = "concept:name"

    sub = df[df[act_col].isin([first_activity, second_activity])]
    first_ev = sub[sub[act_col] == first_activity]
    second_ev = sub[sub[act_col] == second_activity]

    # Earliest occurrence of first_activity per case, and latest occurrence of second_activity per case
    first_qual_all = first_ev.groupby(case_col, sort=False).first()
    second_qual_all = second_ev.groupby(case_col, sort=False).last()

    common_cases = first_qual_all.index.intersection(second_qual_all.index)
    if len(common_cases) > 0:
        valid_mask = first_qual_all.loc[common_cases, "_trace_pos"] < second_qual_all.loc[common_cases, "_trace_pos"]
        qualifying_cases = common_cases[valid_mask].tolist()
        reverse_only_cases = common_cases[~valid_mask].tolist()
    else:
        qualifying_cases = []
        reverse_only_cases = []

    has_offer = "OfferID" in df.columns
    if qualifying_cases:
        qual_sub = sub[sub[case_col].isin(qualifying_cases)].copy()
        f_df = first_qual_all.loc[qualifying_cases]
        s_df = second_qual_all.loc[qualifying_cases]
        c_df = cs.reindex(qualifying_cases)

        f_pos = f_df["_trace_pos"].to_numpy(dtype=np.int64)
        s_pos = s_df["_trace_pos"].to_numpy(dtype=np.int64)
        f_ts_series = f_df["time:timestamp"].reset_index(drop=True)
        s_ts_series = s_df["time:timestamp"].reset_index(drop=True)
        gap_events = (s_pos - f_pos - 1).astype(np.int64)
        gap_days = (s_ts_series - f_ts_series).dt.total_seconds().to_numpy() / 86400.0

        if has_offer:
            f_offer = f_df["OfferID"].where(f_df["OfferID"].notna(), "-").astype(str).to_numpy()
            s_offer = s_df["OfferID"].where(s_df["OfferID"].notna(), "-").astype(str).to_numpy()
        else:
            f_offer = np.full(len(qualifying_cases), "-", dtype=object)
            s_offer = np.full(len(qualifying_cases), "-", dtype=object)

        last_acts = c_df["last_activity"].fillna("-").astype(str).to_numpy()
        dur_days = c_df["duration_days"].fillna(0.0).to_numpy(dtype=float)

        case_summary_df = pd.DataFrame({
            "case_id": [str(cid) for cid in qualifying_cases],
            "cancelled_trace_pos": f_pos,
            "cancelled_timestamp": f_ts_series.astype(str).to_numpy(),
            "cancelled_offer_id": f_offer,
            "accepted_trace_pos": s_pos,
            "accepted_timestamp": s_ts_series.astype(str).to_numpy(),
            "accepted_offer_id": s_offer,
            "intervening_events_count": gap_events,
            "time_between_days": gap_days,
            "trace_end_activity": last_acts,
            "case_duration_days": dur_days,
        })
    else:
        qual_sub = sub.iloc[0:0].copy()
        case_summary_df = pd.DataFrame(columns=[
            "case_id",
            "cancelled_trace_pos",
            "cancelled_timestamp",
            "cancelled_offer_id",
            "accepted_trace_pos",
            "accepted_timestamp",
            "accepted_offer_id",
            "intervening_events_count",
            "time_between_days",
            "trace_end_activity",
            "case_duration_days",
        ])

    # Section 7.3 additional check: Offer-ID level analysis (labelled separately)
    same_offer_count = 0
    if has_offer and not sub.empty:
        sub_offer = sub.dropna(subset=["OfferID"])
        sub_offer = sub_offer[sub_offer["OfferID"].astype(str).str.strip() != ""]
        if not sub_offer.empty:
            f_off = sub_offer[sub_offer[act_col] == first_activity].groupby([case_col, "OfferID"], sort=False)["_trace_pos"].min()
            s_off = sub_offer[sub_offer[act_col] == second_activity].groupby([case_col, "OfferID"], sort=False)["_trace_pos"].max()
            comm_off = f_off.index.intersection(s_off.index)
            if len(comm_off) > 0:
                valid_off = comm_off[f_off.loc[comm_off] < s_off.loc[comm_off]]
                same_offer_count = int(valid_off.get_level_values(0).nunique())

    pct = (len(qualifying_cases) / total_cases * 100.0) if total_cases > 0 else 0.0
    rule_desc = (
        f"Eventually Follows Filter (Level Trace/Case): Terdapat pasangan posisi i < j dalam satu trace "
        f"di mana event ke-i adalah '{first_activity}' dan event ke-j adalah '{second_activity}' "
        f"(kedua event tidak harus bersebelahan). Persentase = (Jumlah Case Cocok / {total_cases}) × 100%."
    )

    return Exercise1122Result(
        first_activity=first_activity,
        second_activity=second_activity,
        rule_description=rule_desc,
        matching_case_count=len(qualifying_cases),
        total_cases_denominator=total_cases,
        matching_percentage=pct,
        both_present_any_order_count=len(common_cases),
        reverse_only_count=len(reverse_only_cases),
        same_offer_id_matching_count=same_offer_count,
        case_summary_df=case_summary_df,
        evidence_events_df=qual_sub,
        excluded_case_ids=[str(x) for x in reverse_only_cases],
    )
