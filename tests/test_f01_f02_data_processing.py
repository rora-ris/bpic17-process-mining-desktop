"""Unit tests for F01 (Import & Validation Hardening) and F02 (Overview & Statistics Consistency).

Covers all hardening, edge cases, and robustness requirements for Anggota 1:
1. Empty XES file (0 trace/event) -> report.is_valid is False with clear error.
2. Missing required columns -> report.is_valid is False.
3. Required columns containing null / empty / NaN / "nan" -> report.is_valid is False.
4. Unparseable timestamp / NaT -> safe handling, report.is_valid is False, no crash.
5. Non-chronological timestamps within trace -> report.warnings logged, duration_seconds is non-negative and uses max-min.
6. Optional columns 100% empty or invalid -> detected, warnings added, flags set to False.
7. Single-event case / zero duration -> duration is 0.0, classified as Fast (< 45 hari).
8. Boundary test: exactly 45.0 days (Slow) vs 44.99 days (Fast).
9. Full OverviewResult statistics consistency (fast + slow == total, 100%, unique activities & resources).
"""

from __future__ import annotations

import os
import tempfile
import pytest
import pandas as pd
import pm4py

from src.core import (
    EventLogContext,
    ValidationReport,
    is_valid_activity,
    is_valid_resource,
    load_and_validate_xes,
)
from src.analyzer import (
    OverviewResult,
    analyze_overview,
    format_duration_human,
)


def _write_xes(tmp_path: str, xml_content: str) -> str:
    """Helper to write raw XES XML content to disk."""
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(xml_content.strip())
    return tmp_path


# =====================================================================
# 1. EMPTY XES FILE
# =====================================================================
def test_f01_empty_xes_file(tmp_path):
    """Test XES with 0 traces / 0 events returns is_valid=False with clear error."""
    xes_file = str(tmp_path / "empty_log.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert ctx is None
    assert not report.is_valid
    assert "Event log kosong" in (report.error_message or "")


# =====================================================================
# 2. MISSING REQUIRED COLUMNS
# =====================================================================
def test_f01_missing_required_column(tmp_path):
    """Test XES missing concept:name or time:timestamp returns is_valid=False."""
    xes_file = str(tmp_path / "missing_attr.xes")
    # Log with case:concept:name and concept:name, but missing time:timestamp
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_1"/>
    <event>
      <string key="concept:name" value="Activity_A"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert ctx is None
    assert not report.is_valid
    assert "time:timestamp" in (report.error_message or "")
    assert "time:timestamp" in report.missing_required


# =====================================================================
# 3. REQUIRED COLUMNS CONTAINING NULL / EMPTY / "nan"
# =====================================================================
def test_f01_required_column_contains_empty_or_nan(tmp_path):
    """Test XES where concept:name contains empty string or 'nan' is caught by validation."""
    xes_file = str(tmp_path / "empty_activity.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_1"/>
    <event>
      <string key="concept:name" value=""/>
      <date key="time:timestamp" value="2026-01-01T10:00:00.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert ctx is None
    assert not report.is_valid
    assert "concept:name" in (report.error_message or "")
    assert "kosong/NaN/tidak valid" in (report.error_message or "")


def test_f01_case_id_contains_nan_string(tmp_path):
    """Test XES where case:concept:name is 'nan' is caught by validation."""
    xes_file = str(tmp_path / "nan_case.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="nan"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2026-01-01T10:00:00.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert ctx is None
    assert not report.is_valid
    assert "case:concept:name" in (report.error_message or "")


# =====================================================================
# 4. UNPARSEABLE TIMESTAMP / NaT (NO CRASH)
# =====================================================================
def test_f01_unparseable_timestamp_handling(tmp_path):
    """Test unparseable timestamp returns is_valid=False with clear error without raising unhandled exception."""
    xes_file = str(tmp_path / "corrupt_timestamp.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_1"/>
    <event>
      <string key="concept:name" value="Action_A"/>
      <string key="time:timestamp" value="NOT_A_VALID_DATE_99999"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert ctx is None
    assert not report.is_valid
    assert ("timestamp" in (report.error_message or "").lower() or "nat" in (report.error_message or "").lower())


# =====================================================================
# 5. NON-CHRONOLOGICAL TIMESTAMPS (WARNING & DURATION SAFETY)
# =====================================================================
def test_f01_non_chronological_trace_warning_and_duration_safety(tmp_path):
    """Test that backwards event timestamps trigger a warning and duration is safely computed as (max - min)."""
    xes_file = str(tmp_path / "non_chrono.xes")
    # Event 1 is on 2026-01-10, Event 2 is on 2026-01-02.
    # Raw (last - first) = -8 days. Safe duration = (max - min) = 8 days.
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_BACKWARDS"/>
    <event>
      <string key="concept:name" value="Event_First_In_Trace"/>
      <date key="time:timestamp" value="2026-01-10T12:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="Event_Second_In_Trace"/>
      <date key="time:timestamp" value="2026-01-02T12:00:00.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert report.is_valid
    assert ctx is not None
    # Verify warning was recorded
    assert any("kronologis" in w for w in report.warnings)

    # Verify duration calculation is non-negative and equals 8.0 days
    cs = ctx.case_summary_df
    assert "CASE_BACKWARDS" in cs.index
    row = cs.loc["CASE_BACKWARDS"]
    assert row["duration_seconds"] == 8.0 * 86400.0
    assert row["duration_days"] == 8.0
    assert row["duration_seconds"] >= 0.0


# =====================================================================
# 6. OPTIONAL COLUMNS 100% EMPTY OR INVALID
# =====================================================================
def test_f01_optional_columns_empty_detection(tmp_path):
    """Test that columns present with 100% empty/placeholder values are detected as not valid."""
    xes_file = str(tmp_path / "empty_optional.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_1"/>
    <event>
      <string key="concept:name" value="Activity_A"/>
      <date key="time:timestamp" value="2026-01-01T10:00:00.000+00:00"/>
      <string key="org:resource" value=""/>
      <string key="lifecycle:transition" value="nan"/>
    </event>
    <event>
      <string key="concept:name" value="Activity_B"/>
      <date key="time:timestamp" value="2026-01-02T10:00:00.000+00:00"/>
      <string key="org:resource" value="none"/>
      <string key="lifecycle:transition" value=""/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert report.is_valid
    assert ctx is not None
    assert not report.has_resource
    assert not report.has_lifecycle
    assert any("org:resource" in w for w in report.warnings)
    assert any("lifecycle:transition" in w for w in report.warnings)


# =====================================================================
# 7. DURATION 0 SECONDS (SINGLE EVENT / IDENTICAL TIMESTAMPS)
# =====================================================================
def test_f02_duration_zero_seconds(tmp_path):
    """Test case with 1 event has 0.0 duration and is categorized as Fast (< 45 hari)."""
    xes_file = str(tmp_path / "single_event.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_SINGLE"/>
    <event>
      <string key="concept:name" value="Single_Event"/>
      <date key="time:timestamp" value="2026-01-01T10:00:00.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert report.is_valid
    assert ctx is not None

    cs = ctx.case_summary_df
    row = cs.loc["CASE_SINGLE"]
    assert row["duration_seconds"] == 0.0
    assert row["duration_days"] == 0.0
    assert row["speed_category"] == "Fast (< 45 hari)"

    ov = analyze_overview(ctx)
    assert ov.mean_cycle_time_days == 0.0
    assert ov.mean_cycle_time_seconds == 0.0
    assert ov.fast_cases_count == 1
    assert ov.slow_cases_count == 0
    assert ov.fast_cases_pct == 100.0


# =====================================================================
# 8. FAST VS SLOW EXACT BOUNDARY (45.0 DAYS VS 44.99 DAYS)
# =====================================================================
def test_f02_fast_vs_slow_boundary(tmp_path):
    """Test exact threshold: 45.0 days is Slow (>=45) while 44.99 days is Fast (<45)."""
    xes_file = str(tmp_path / "boundary.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="CASE_EXACT_45_DAYS"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2026-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="End"/>
      <date key="time:timestamp" value="2026-02-15T00:00:00.000+00:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="CASE_44_POINT_99_DAYS"/>
    <event>
      <string key="concept:name" value="Start"/>
      <date key="time:timestamp" value="2026-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="End"/>
      <date key="time:timestamp" value="2026-02-14T23:45:36.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert report.is_valid
    assert ctx is not None

    cs = ctx.case_summary_df
    dur_slow = cs.loc["CASE_EXACT_45_DAYS", "duration_days"]
    dur_fast = cs.loc["CASE_44_POINT_99_DAYS", "duration_days"]

    assert pytest.approx(dur_slow, rel=1e-5) == 45.0
    assert pytest.approx(dur_fast, rel=1e-4) == 44.99

    assert cs.loc["CASE_EXACT_45_DAYS", "speed_category"] == "Slow (>= 45 hari)"
    assert cs.loc["CASE_44_POINT_99_DAYS", "speed_category"] == "Fast (< 45 hari)"

    ov = analyze_overview(ctx)
    assert ov.total_cases == 2
    assert ov.fast_cases_count == 1
    assert ov.slow_cases_count == 1
    assert ov.fast_cases_count + ov.slow_cases_count == ov.total_cases
    assert pytest.approx(ov.fast_cases_pct, rel=1e-5) == 50.0
    assert pytest.approx(ov.slow_cases_pct, rel=1e-5) == 50.0
    assert pytest.approx(ov.fast_cases_pct + ov.slow_cases_pct, rel=1e-5) == 100.0


# =====================================================================
# 9. OVERVIEWRESULT DESCRIPTIVE METRICS CONSISTENCY
# =====================================================================
def test_f02_overview_descriptive_metrics_full_suite(tmp_path):
    """Test median, min, max, std, unique_activities, and unique_resources on multi-case log."""
    xes_file = str(tmp_path / "metrics_test.xes")
    _write_xes(xes_file, """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="C1"/>
    <event>
      <string key="concept:name" value="Act_A"/>
      <string key="org:resource" value="User_1"/>
      <date key="time:timestamp" value="2026-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="Act_B"/>
      <string key="org:resource" value="User_2"/>
      <date key="time:timestamp" value="2026-01-03T00:00:00.000+00:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="C2"/>
    <event>
      <string key="concept:name" value="Act_B"/>
      <string key="org:resource" value="User_2"/>
      <date key="time:timestamp" value="2026-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="Act_C"/>
      <string key="org:resource" value="User_3"/>
      <date key="time:timestamp" value="2026-01-07T00:00:00.000+00:00"/>
    </event>
  </trace>
  <trace>
    <string key="concept:name" value="C3"/>
    <event>
      <string key="concept:name" value="Act_A"/>
      <string key="org:resource" value="User_1"/>
      <date key="time:timestamp" value="2026-01-01T00:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="Act_C"/>
      <string key="org:resource" value="none"/>
      <date key="time:timestamp" value="2026-01-11T00:00:00.000+00:00"/>
    </event>
  </trace>
</log>
""")
    ctx, report = load_and_validate_xes(xes_file)
    assert report.is_valid
    ov = analyze_overview(ctx)

    # Durations: C1 = 2 days, C2 = 6 days, C3 = 10 days
    # Mean = (2 + 6 + 10) / 3 = 6.0 days
    # Median = 6.0 days
    # Min = 2.0 days, Max = 10.0 days
    # Std = sample std([2, 6, 10]) = 4.0 days
    assert ov.total_cases == 3
    assert ov.total_events == 6
    assert pytest.approx(ov.mean_cycle_time_days, rel=1e-5) == 6.0
    assert pytest.approx(ov.median_cycle_time_days, rel=1e-5) == 6.0
    assert pytest.approx(ov.min_cycle_time_days, rel=1e-5) == 2.0
    assert pytest.approx(ov.max_cycle_time_days, rel=1e-5) == 10.0
    assert pytest.approx(ov.std_cycle_time_days, rel=1e-5) == 4.0

    # Unique valid activities: Act_A, Act_B, Act_C = 3
    assert ov.unique_activities == 3

    # Unique valid resources: User_1, User_2, User_3 = 3 ('none' is excluded)
    assert ov.unique_resources == 3

    # Human duration formatter tests
    assert "detik" in format_duration_human(0.0005)
    assert "jam" in format_duration_human(0.5)
    assert "hari" in format_duration_human(2.5)
