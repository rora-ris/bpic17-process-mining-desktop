"""Analysis engine implementing F02 through F07 and optional enrichment features."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pm4py

from .core import INVALID_RESOURCE_STRINGS, EventLogContext


def is_valid_resource(val: Any) -> bool:
    """Checks if a resource value is non-null, non-empty, and not a placeholder."""
    if val is None or pd.isna(val):
        return False
    s = str(val).strip()
    if s.lower() in INVALID_RESOURCE_STRINGS:
        return False
    return True


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


def analyze_overview(ctx: EventLogContext) -> OverviewResult:
    """F02 — Computes overall event log statistics and case duration table."""
    df = ctx.df
    cs = ctx.case_summary_df

    total_cases = len(cs)
    total_events = len(df)
    unique_acts = int(df["concept:name"].nunique())

    if "org:resource" in df.columns:
        valid_res = df["org:resource"][df["org:resource"].apply(is_valid_resource)]
        unique_res = int(valid_res.nunique())
    else:
        unique_res = 0

    min_ts = df["time:timestamp"].min()
    max_ts = df["time:timestamp"].max()

    dur_days = cs["duration_days"]
    mean_days = float(dur_days.mean()) if total_cases > 0 else 0.0
    mean_hours = float(cs["duration_hours"].mean()) if total_cases > 0 else 0.0
    mean_secs = float(cs["duration_seconds"].mean()) if total_cases > 0 else 0.0
    median_days = float(dur_days.median()) if total_cases > 0 else 0.0
    min_days = float(dur_days.min()) if total_cases > 0 else 0.0
    max_days = float(dur_days.max()) if total_cases > 0 else 0.0
    std_days = float(dur_days.std()) if total_cases > 1 else 0.0

    # Optional enrichment (Section 12): Fast (< 45 days) vs Slow (>= 45 days) cases (Example 11.10)
    fast_mask = dur_days < 45.0
    slow_mask = dur_days >= 45.0
    fast_cnt = int(fast_mask.sum())
    slow_cnt = int(slow_mask.sum())
    fast_pct = (fast_cnt / total_cases * 100.0) if total_cases > 0 else 0.0
    slow_pct = (slow_cnt / total_cases * 100.0) if total_cases > 0 else 0.0
    fast_mean = float(dur_days[fast_mask].mean()) if fast_cnt > 0 else 0.0
    slow_mean = float(dur_days[slow_mask].mean()) if slow_cnt > 0 else 0.0

    return OverviewResult(
        total_cases=total_cases,
        total_events=total_events,
        unique_activities=unique_acts,
        unique_resources=unique_res,
        log_start_time=str(min_ts),
        log_end_time=str(max_ts),
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

    Uses PM4Py trace attribute filtering semantics while preserving full trace
    cycle time computed before any event removal (Section 7.1).
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
    # Use pm4py.filter_trace_attribute_values to retain full traces containing O_Accepted
    filtered_c_df = pm4py.filter_trace_attribute_values(
        df, act_col, ["O_Accepted"], retain=True, case_id_key=case_col
    )
    c_case_ids = filtered_c_df[case_col].unique()
    c_occurrences = df[df[act_col] == "O_Accepted"].groupby(case_col).size()
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
    filtered_d_df = pm4py.filter_trace_attribute_values(
        df, act_col, ["O_Refused"], retain=True, case_id_key=case_col
    )
    d_case_ids = filtered_d_df[case_col].unique()
    d_occurrences = df[df[act_col] == "O_Refused"].groupby(case_col).size()
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
    # Use pm4py.filter_end_activities to select traces whose final event is O_Cancelled
    filtered_e_df = pm4py.filter_end_activities(
        df, ["O_Cancelled"], retain=True, case_id_key=case_col, activity_key=act_col, timestamp_key="time:timestamp"
    )
    # To guarantee exact trace-order endpoint consistency (Section 4 & 7.1: "Event TERAKHIR pada urutan trace"):
    cs_e = cs[cs["last_activity"] == "O_Cancelled"].copy()
    e_occurrences = df[df[act_col] == "O_Cancelled"].groupby(case_col).size()
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

    overlap_cd = len(set(cs_c.index).intersection(set(cs_d.index)))
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
    act_events = df[df[act_col].str.strip().str.lower() == target_lower].copy()

    # Count all lifecycle occurrences per case for comparison (Section 7.2)
    all_lc_counts = act_events.groupby(case_col, sort=False).size()
    cases_two_all_lc = all_lc_counts[all_lc_counts >= min_occurrences].index.tolist()

    has_lc = lc_col in df.columns
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
    )


def analyze_exercise_11_18(
    ctx: EventLogContext,
    target_activity: str = "W_Assess potential fraud",
    min_occurrences: int = 2,
    complete_only: bool = True,
) -> Exercise1118Result:
    """F05 — Analyzes cases where target_activity is completed >= 2 times by the SAME valid resource.

    Explicitly excludes missing/empty/unknown resource values so two blank resources
    are never treated as the same resource (Section 4 & F05).
    """
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

    if res_col not in df.columns:
        return Exercise1118Result(
            target_activity=target_activity,
            min_occurrences=min_occurrences,
            lifecycle_filter=res_1115.lifecycle_filter,
            rule_description="Atribut org:resource tidak tersedia pada dataset.",
            matching_case_count=0,
            total_cases_denominator=total_cases,
            matching_percentage=0.0,
            cases_from_1115_excluded_diff_resource=[],
            excluded_diff_resource_evidence_df=pd.DataFrame(),
            case_resource_summary_df=pd.DataFrame(),
            evidence_events_df=pd.DataFrame(),
        )

    target_lower = target_activity.strip().lower()
    act_events = df[df[act_col].str.strip().str.lower() == target_lower].copy()
    if complete_only and (lc_col in df.columns):
        comp_events = act_events[act_events[lc_col].astype(str).str.strip().str.lower() == "complete"].copy()
    else:
        comp_events = act_events.copy()

    # Filter out empty/missing/placeholder resources explicitly
    valid_res_mask = comp_events[res_col].apply(is_valid_resource)
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
    cases_1115_ids = (
        res_1115.case_summary_df["case_id"].tolist()
        if not res_1115.case_summary_df.empty
        else []
    )
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

    sub = df[df[act_col].isin([first_activity, second_activity])].copy()
    first_ev = sub[sub[act_col] == first_activity]
    second_ev = sub[sub[act_col] == second_activity]

    # Earliest occurrence of first_activity per case, and latest occurrence of second_activity per case
    min_first_idx = first_ev.groupby(case_col, sort=False)["_trace_pos"].min()
    max_second_idx = second_ev.groupby(case_col, sort=False)["_trace_pos"].max()

    common_cases = min_first_idx.index.intersection(max_second_idx.index)
    valid_mask = min_first_idx.loc[common_cases] < max_second_idx.loc[common_cases]

    qualifying_cases = common_cases[valid_mask].tolist()
    reverse_only_cases = common_cases[~valid_mask].tolist()

    # Build detailed pair evidence for each qualifying case
    qual_sub = sub[sub[case_col].isin(qualifying_cases)].copy()

    first_qual = first_ev[first_ev[case_col].isin(qualifying_cases)].groupby(case_col, sort=False).first()
    second_qual = second_ev[second_ev[case_col].isin(qualifying_cases)].groupby(case_col, sort=False).last()

    has_offer = "OfferID" in df.columns
    summary_rows = []
    for cid in qualifying_cases:
        f_row = first_qual.loc[cid]
        s_row = second_qual.loc[cid]
        f_pos = int(f_row["_trace_pos"])
        s_pos = int(s_row["_trace_pos"])
        f_ts = f_row["time:timestamp"]
        s_ts = s_row["time:timestamp"]
        gap_events = s_pos - f_pos - 1
        gap_days = (s_ts - f_ts).total_seconds() / 86400.0
        f_offer = str(f_row["OfferID"]) if (has_offer and pd.notna(f_row.get("OfferID"))) else "-"
        s_offer = str(s_row["OfferID"]) if (has_offer and pd.notna(s_row.get("OfferID"))) else "-"
        last_act = str(cs.loc[cid, "last_activity"]) if cid in cs.index else "-"
        dur_days = float(cs.loc[cid, "duration_days"]) if cid in cs.index else 0.0

        summary_rows.append({
            "case_id": str(cid),
            "cancelled_trace_pos": f_pos,
            "cancelled_timestamp": str(f_ts),
            "cancelled_offer_id": f_offer,
            "accepted_trace_pos": s_pos,
            "accepted_timestamp": str(s_ts),
            "accepted_offer_id": s_offer,
            "intervening_events_count": gap_events,
            "time_between_days": gap_days,
            "trace_end_activity": last_act,
            "case_duration_days": dur_days,
        })

    case_summary_df = pd.DataFrame(summary_rows)

    # Section 7.3 additional check: Offer-ID level analysis (labelled separately)
    same_offer_count = 0
    if has_offer:
        sub_offer = sub.dropna(subset=["OfferID"])
        f_off = sub_offer[sub_offer[act_col] == first_activity].groupby([case_col, "OfferID"])["_trace_pos"].min()
        s_off = sub_offer[sub_offer[act_col] == second_activity].groupby([case_col, "OfferID"])["_trace_pos"].max()
        comm_off = f_off.index.intersection(s_off.index)
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
    )
