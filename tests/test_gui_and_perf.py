"""Additional unit tests for analyzer edge cases, interleaved traces, and headless PySide6 GUI integration."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.analyzer import (
    analyze_exercise_11_7,
    analyze_exercise_11_15,
    analyze_exercise_11_18,
    analyze_exercise_11_22,
    analyze_overview,
)
from src.core import load_and_validate_xes
from src.exporter import export_all_to_directory, get_export_target_dataframe
from src.gui import (
    AboutDialog,
    ActivityListDialog,
    CaseDurationDialog,
    ExportDialog,
    FastSlowDialog,
    FullAnalysisBundle,
    MainWindow,
    _compute_case_category_tags,
)
from src.synthetic import generate_synthetic_xes_file


def _write_xes(path: str, xml_content: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml_content.strip())
    return path


def test_11_15_and_11_18_with_empty_optional_columns(tmp_path):
    """When lifecycle:transition and org:resource columns exist but are 100% empty:
    - has_lifecycle is False -> all events are treated as complete in 11.15.
    - has_resource is False -> 11.18 returns 0 cases and populates cases_from_1115_excluded_diff_resource.
    """
    xes_path = _write_xes(
        str(tmp_path / "empty_opt_cols.xes"),
        """<?xml version="1.0" encoding="UTF-8"?>
<log xes.version="1.0">
  <trace>
    <string key="concept:name" value="C_EMPTY_OPTS"/>
    <event>
      <string key="concept:name" value="W_Assess potential fraud"/>
      <string key="lifecycle:transition" value=""/>
      <string key="org:resource" value=""/>
      <date key="time:timestamp" value="2026-01-01T08:00:00.000+00:00"/>
    </event>
    <event>
      <string key="concept:name" value="W_Assess potential fraud"/>
      <string key="lifecycle:transition" value="nan"/>
      <string key="org:resource" value="null"/>
      <date key="time:timestamp" value="2026-01-02T08:00:00.000+00:00"/>
    </event>
  </trace>
</log>""",
    )
    ctx, rep = load_and_validate_xes(xes_path)
    assert rep.is_valid and ctx is not None
    assert not rep.has_lifecycle
    assert not rep.has_resource

    r15 = analyze_exercise_11_15(ctx)
    assert r15.matching_case_count == 1
    assert r15.case_summary_df.iloc[0]["case_id"] == "C_EMPTY_OPTS"

    r18 = analyze_exercise_11_18(ctx, res_1115=r15)
    assert r18.matching_case_count == 0
    assert r18.cases_from_1115_excluded_diff_resource == ["C_EMPTY_OPTS"]


def test_non_contiguous_traces_fallback_consistency(tmp_path):
    """Verifies that non-contiguous / interleaved trace rows fallback produces identical results."""
    xes_path = str(tmp_path / "syn.xes")
    generate_synthetic_xes_file(xes_path)
    ctx_contig, rep_contig = load_and_validate_xes(xes_path)
    assert rep_contig.is_valid and ctx_contig is not None

    # Interleave cases round-robin by _trace_pos while strictly preserving per-case event order
    df_interleaved = ctx_contig.df.sort_values(
        ["_trace_pos", "case:concept:name"], kind="mergesort"
    ).reset_index(drop=True)
    from src.core import EventLogContext

    ctx_interleaved = EventLogContext(df=df_interleaved, report=rep_contig)

    ov1 = analyze_overview(ctx_contig)
    ov2 = analyze_overview(ctx_interleaved)
    assert ov1.total_cases == ov2.total_cases == 10
    assert pytest.approx(ov1.mean_cycle_time_days, rel=1e-6) == ov2.mean_cycle_time_days

    r117_1 = analyze_exercise_11_7(ctx_contig)
    r117_2 = analyze_exercise_11_7(ctx_interleaved)
    assert r117_1.sub_c.case_count == r117_2.sub_c.case_count
    assert r117_1.sub_d.case_count == r117_2.sub_d.case_count
    assert r117_1.sub_e.case_count == r117_2.sub_e.case_count

    r1115_1 = analyze_exercise_11_15(ctx_contig)
    r1115_2 = analyze_exercise_11_15(ctx_interleaved)
    assert r1115_1.matching_case_count == r1115_2.matching_case_count

    r1118_1 = analyze_exercise_11_18(ctx_contig, res_1115=r1115_1)
    r1118_2 = analyze_exercise_11_18(ctx_interleaved, res_1115=r1115_2)
    assert r1118_1.matching_case_count == r1118_2.matching_case_count

    r1122_1 = analyze_exercise_11_22(ctx_contig)
    r1122_2 = analyze_exercise_11_22(ctx_interleaved)
    assert r1122_1.matching_case_count == r1122_2.matching_case_count
    assert r1122_1.reverse_only_count == r1122_2.reverse_only_count
    assert set(r1122_1.excluded_case_ids) == set(r1122_2.excluded_case_ids)

    ev1 = ctx_contig.get_case_events("CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED")
    ev2 = ctx_interleaved.get_case_events("CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED")
    assert ev1["concept:name"].tolist() == ev2["concept:name"].tolist()


def test_11_22_vectorized_details_and_excluded_ids(tmp_path):
    """Checks 11.22 vectorized output columns, gap counts, and excluded reverse-only IDs."""
    xes_path = str(tmp_path / "syn22.xes")
    generate_synthetic_xes_file(xes_path)
    ctx, rep = load_and_validate_xes(xes_path)
    assert rep.is_valid and ctx is not None

    r22 = analyze_exercise_11_22(ctx)
    assert r22.matching_case_count == 1
    assert r22.reverse_only_count == 1
    assert r22.excluded_case_ids == ["CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER"]
    row = r22.case_summary_df.iloc[0]
    assert row["case_id"] == "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED"
    assert int(row["cancelled_trace_pos"]) == 2
    assert int(row["accepted_trace_pos"]) == 4
    assert int(row["intervening_events_count"]) == 1
    assert pytest.approx(float(row["time_between_days"]), rel=1e-5) == 9.0
    assert r22.same_offer_id_matching_count == 0


def test_gui_mainwindow_integration_and_export(tmp_path):
    """Headless PySide6 integration test exercising all 5 tabs, dialogs, drawer, and exports."""
    app = QApplication.instance() or QApplication(sys.argv)
    xes_path = str(tmp_path / "synthetic_edge_cases.xes")
    generate_synthetic_xes_file(xes_path)
    ctx, rep = load_and_validate_xes(xes_path)
    assert rep.is_valid and ctx is not None

    ov = analyze_overview(ctx)
    r117 = analyze_exercise_11_7(ctx)
    r1115 = analyze_exercise_11_15(ctx)
    r1118 = analyze_exercise_11_18(ctx, res_1115=r1115)
    r1122 = analyze_exercise_11_22(ctx)
    tags = _compute_case_category_tags(ov, r117, r1115, r1118, r1122)

    bundle = FullAnalysisBundle(
        context=ctx,
        report=rep,
        overview=ov,
        ex117=r117,
        ex1115=r1115,
        ex1118=r1118,
        ex1122=r1122,
        case_category_tags=tags,
    )

    win = MainWindow()
    try:
        win._on_analysis_finished(bundle)
        app.processEvents()

        # Tab Data assertions
        assert win.card_cases.lbl_val.text() == "10"
        assert win.card_events.lbl_val.text() == "32"
        assert win.card_dur.lbl_val.text() == "6,90 hari"

        # Toggle units & precision
        win._set_f02_unit("jam")
        assert "jam" in win.card_dur.lbl_val.text()
        win._set_f02_unit("detik")
        assert "dtk" in win.card_dur.lbl_val.text()
        win._set_f02_unit("hari")
        win.cmb_prec.setCurrentIndex(1)
        assert "6,9000 hari" in win.card_dur.lbl_val.text()

        # Tab 11.7 sub-questions (full rows without truncation)
        for sub_code, expected_rows in (("11.7 A", 10), ("11.7 B", 10), ("11.7 C", 4), ("11.7 D", 1), ("11.7 E", 2)):
            win._select_117_sub(sub_code)
            assert win.table_117.model().rowCount() == expected_rows

        # Tab 11.15 & 11.18 + excluded toggle
        win._select_1518_sub("11.15")
        assert win.table_1518.model().rowCount() == 3
        win.chk_show_excluded_1518.setChecked(True)
        assert win.table_1518.model().rowCount() == 1
        win._select_1518_sub("11.18")
        assert win.table_1518.model().rowCount() == 2  # diff resource + empty resource
        win.chk_show_excluded_1518.setChecked(False)
        assert win.table_1518.model().rowCount() == 1

        # Tab 11.22
        assert win.table_22.model().rowCount() == 1
        assert "Ya, 1 case" in win.lbl_22_ans.text()

        # Case Explorer group filter, search, detail toggle, reset
        win.cmb_exp_group.setCurrentIndex(6)  # 11.22
        assert win.table_exp_cases.model().rowCount() == 1
        win.chk_exp_detail.setChecked(True)
        assert win.table_exp_events.model().columnCount() == 5
        win.exp_search.setText("CASE_08")
        win._apply_explorer_filter()
        assert win.table_exp_cases.model().rowCount() == 1
        win._on_explorer_reset()
        assert win.table_exp_cases.model().rowCount() == 10

        # ChecklistDrawer manual item 10 updates header button immediately (7/10 -> 8/10 since BPIC17 & export not yet done)
        assert "7/10" in win.btn_checklist_chip.text()
        win.drawer.checkboxes[9].setChecked(True)
        assert "8/10" in win.btn_checklist_chip.text()

        # Dialog instantiation checks
        dlg_dur = CaseDurationDialog(ov.case_table, win)
        assert dlg_dur.table.model().rowCount() == 10
        dlg_dur._on_search("CASE_06")
        assert dlg_dur.table.model().rowCount() == 1
        dlg_act = ActivityListDialog(ov.activity_table, win)
        assert dlg_act is not None
        dlg_fs = FastSlowDialog(ov, win)
        assert dlg_fs is not None
        dlg_ab = AboutDialog(win)
        assert dlg_ab is not None

        # Full directory export check
        out_dir = str(tmp_path / "exported")
        files = export_all_to_directory(out_dir, ctx, ov, r117, r1115, r1118, r1122)
        assert len(files) == 11
        for fp in files.values():
            assert os.path.exists(fp)
    finally:
        win.close()


def test_export_dialog_options_and_target_lookup(tmp_path):
    """Verifies ExportDialog option switching, target selection, and single-target CSV lookup."""
    app = QApplication.instance() or QApplication(sys.argv)
    dlg = ExportDialog()
    try:
        # Default selection is Option 1
        assert dlg.get_selected_option() == 1
        assert dlg.btn_save.text() == "Simpan CSV..."
        assert "&" not in dlg.r3.text()

        # Clicking option 2 row switches to Option 2 (bundle folder by default)
        QTest.mouseClick(dlg.row_2, Qt.LeftButton)
        app.processEvents()
        assert dlg.get_selected_option() == 2
        assert dlg.get_selected_case_target() == "all_bundle"
        assert dlg.btn_save.text() == "Pilih Folder..."

        # Selecting a specific CSV target updates button label to Simpan CSV...
        idx_1118 = dlg.cmb_case_target.findData("11_18_cases")
        assert idx_1118 > 0
        dlg.cmb_case_target.setCurrentIndex(idx_1118)
        app.processEvents()
        assert dlg.get_selected_case_target() == "11_18_cases"
        assert dlg.btn_save.text() == "Simpan CSV..."

        # Switching back to Option 1, then changing combobox auto-selects Option 2
        QTest.mouseClick(dlg.row_1, Qt.LeftButton)
        app.processEvents()
        assert dlg.get_selected_option() == 1
        assert dlg.btn_save.text() == "Simpan CSV..."

        idx_1122 = dlg.cmb_case_target.findData("11_22_cases")
        assert idx_1122 > 0
        dlg.cmb_case_target.setCurrentIndex(idx_1122)
        app.processEvents()
        assert dlg.get_selected_option() == 2
        assert dlg.get_selected_case_target() == "11_22_cases"

        # Clicking option 3 row switches to Option 3 (HTML)
        QTest.mouseClick(dlg.row_3, Qt.LeftButton)
        app.processEvents()
        assert dlg.get_selected_option() == 3
        assert dlg.btn_save.text() == "Simpan HTML..."
    finally:
        dlg.close()

    # Single-target CSV lookup verification across all 11 supported keys
    xes_path = str(tmp_path / "synthetic_export_targets.xes")
    generate_synthetic_xes_file(xes_path)
    ctx, rep = load_and_validate_xes(xes_path)
    assert rep.is_valid and ctx is not None

    ov = analyze_overview(ctx)
    r117 = analyze_exercise_11_7(ctx)
    r1115 = analyze_exercise_11_15(ctx)
    r1118 = analyze_exercise_11_18(ctx, res_1115=r1115)
    r1122 = analyze_exercise_11_22(ctx)

    expected_keys = [
        "summary",
        "overview_activities",
        "11_7_all",
        "11_7_c",
        "11_7_d",
        "11_7_e",
        "11_15_cases",
        "11_15_events",
        "11_18_cases",
        "11_18_events",
        "11_22_cases",
    ]
    for key in expected_keys:
        df, default_name, title = get_export_target_dataframe(
            key, ctx, ov, r117, r1115, r1118, r1122
        )
        assert isinstance(df, pd.DataFrame)
        assert default_name.endswith(".csv")
        assert len(title) > 0

    with pytest.raises(ValueError):
        get_export_target_dataframe("unknown_key", ctx, ov, r117, r1115, r1118, r1122)
