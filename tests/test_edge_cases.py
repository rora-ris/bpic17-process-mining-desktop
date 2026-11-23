"""Unit tests verifying all 8 mandatory edge-case scenarios from Section 8 using PM4Py."""

from __future__ import annotations

import os
import tempfile
import pytest

from src.analyzer import (
    analyze_exercise_11_7,
    analyze_exercise_11_15,
    analyze_exercise_11_18,
    analyze_exercise_11_22,
    analyze_overview,
)
from src.core import load_and_validate_xes
from src.synthetic import generate_synthetic_xes_file


@pytest.fixture(scope="module")
def synthetic_context():
    """Generates the synthetic XES log file and loads it through PM4Py."""
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    xes_path = os.path.join(out_dir, "synthetic_edge_cases.xes")
    generate_synthetic_xes_file(xes_path)
    ctx, report = load_and_validate_xes(xes_path)
    assert report.is_valid, f"Synthetic XES should be valid: {report.error_message}"
    assert ctx is not None
    return ctx


def test_f01_and_f02_overview_on_synthetic(synthetic_context):
    """Tests F01 validation and F02 overview metrics on the 10-case synthetic dataset."""
    ov = analyze_overview(synthetic_context)
    assert ov.total_cases == 10
    assert ov.total_events == 32
    # Sum of durations across the 10 cases: 10 + 6 + 8 + 4 + 5 + 7 + 3 + 12 + 9 + 5 = 69.0 days
    # Mean duration = 69.0 / 10 = 6.9 days
    assert pytest.approx(ov.mean_cycle_time_days, rel=1e-5) == 6.9


def test_scenario_1_double_accepted_counted_once(synthetic_context):
    """Skenario 1: Satu case memiliki O_Accepted dua kali -> 11.7 C menghitung case satu kali, bukan dua."""
    r117 = analyze_exercise_11_7(synthetic_context)
    c_ids = r117.sub_c.case_df["case_id"].tolist()
    assert c_ids.count("CASE_01_DOUBLE_ACCEPTED") == 1
    # Cycle time of CASE_01_DOUBLE_ACCEPTED must be full trace duration (10.0 days)
    dur = float(r117.sub_c.case_df.loc["CASE_01_DOUBLE_ACCEPTED", "duration_days"])
    assert pytest.approx(dur, rel=1e-5) == 10.0


def test_scenario_2_cancelled_in_middle_not_counted_in_11_7_e(synthetic_context):
    """Skenario 2: Case memiliki O_Cancelled di tengah dan event lain sesudahnya -> 11.7 E tidak menganggapnya canceled."""
    r117 = analyze_exercise_11_7(synthetic_context)
    e_ids = r117.sub_e.case_df["case_id"].tolist()
    assert "CASE_02_CANCELLED_MIDDLE_THEN_OTHER" not in e_ids
    assert "CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER" in e_ids
    assert "CASE_10_PURE_CANCELLED_AT_END" in e_ids
    assert r117.sub_e.case_count == 2


def test_scenario_3_both_refused_and_accepted_not_exclusive(synthetic_context):
    """Skenario 3: Case memiliki O_Refused dan O_Accepted -> lolos kedua filter contains (11.7 C dan 11.7 D)."""
    r117 = analyze_exercise_11_7(synthetic_context)
    c_ids = set(r117.sub_c.case_df["case_id"].tolist())
    d_ids = set(r117.sub_d.case_df["case_id"].tolist())
    assert "CASE_03_BOTH_REFUSED_AND_ACCEPTED" in c_ids
    assert "CASE_03_BOTH_REFUSED_AND_ACCEPTED" in d_ids
    assert r117.overlap_c_and_d_count == 1


def test_scenario_4_fraud_scheduled_twice_complete_once_excluded(synthetic_context):
    """Skenario 4: W_Assess Potential Fraud dijadwalkan dua kali tetapi complete hanya sekali -> 11.15 tidak meloloskan case tersebut."""
    r1115 = analyze_exercise_11_15(synthetic_context)
    passed_1115 = set(r1115.case_summary_df["case_id"].tolist())
    assert "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE" not in passed_1115
    assert r1115.excluded_by_lifecycle_count >= 1


def test_scenario_5_two_complete_different_resources(synthetic_context):
    """Skenario 5: Dua complete, tetapi resource berbeda -> Lolos 11.15, tidak lolos 11.18."""
    r1115 = analyze_exercise_11_15(synthetic_context)
    r1118 = analyze_exercise_11_18(synthetic_context)
    passed_1115 = set(r1115.case_summary_df["case_id"].tolist())
    passed_1118 = set(r1118.case_resource_summary_df["case_id"].tolist())
    assert "CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE" in passed_1115
    assert "CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE" not in passed_1118


def test_scenario_6_two_complete_same_resource_and_empty_resource_handling(synthetic_context):
    """Skenario 6 & F05: Dua complete oleh resource sama -> Lolos 11.15 dan 11.18; resource kosong tidak dianggap resource sama."""
    r1115 = analyze_exercise_11_15(synthetic_context)
    r1118 = analyze_exercise_11_18(synthetic_context)
    passed_1115 = set(r1115.case_summary_df["case_id"].tolist())
    passed_1118 = set(r1118.case_resource_summary_df["case_id"].tolist())

    # CASE_06 has 2 complete by User_X -> passes both 11.15 and 11.18
    assert "CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE" in passed_1115
    assert "CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE" in passed_1118
    assert r1118.matching_case_count == 1

    # CASE_07 has 2 complete with empty resource "" -> passes 11.15, must NOT pass 11.18
    assert "CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE" in passed_1115
    assert "CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE" not in passed_1118


def test_scenario_7_and_8_eventually_follows_11_22(synthetic_context):
    """Skenario 7 & 8:
    - O_Cancelled diikuti aktivitas lain lalu O_Accepted -> Lolos 11.22 meskipun tidak bertetangga.
    - O_Accepted mendahului O_Cancelled tanpa accepted sesudahnya -> Tidak lolos 11.22.
    """
    r1122 = analyze_exercise_11_22(synthetic_context)
    passed_1122 = set(r1122.case_summary_df["case_id"].tolist())

    assert "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED" in passed_1122
    assert "CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER" not in passed_1122
    assert r1122.matching_case_count == 1
    assert r1122.total_cases_denominator == 10
    assert pytest.approx(r1122.matching_percentage, rel=1e-5) == 10.0


def test_invalid_or_missing_file_handling():
    """Tests F01 clear error reporting when a file is missing or corrupted."""
    ctx, report = load_and_validate_xes("non_existent_file_12345.xes")
    assert ctx is None
    assert not report.is_valid
    assert report.error_message is not None

    with tempfile.NamedTemporaryFile(suffix=".xes", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("<corrupted><xml>not closed")
        tmp_path = tmp.name

    try:
        ctx2, report2 = load_and_validate_xes(tmp_path)
        assert ctx2 is None
        assert not report2.is_valid
        assert report2.error_message is not None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
