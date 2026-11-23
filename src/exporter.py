"""Export utilities for CSV summary tables, case lists, evidence logs, and HTML reports (F07)."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .analyzer import (
    Exercise117Result,
    Exercise1115Result,
    Exercise1118Result,
    Exercise1122Result,
    OverviewResult,
)
from .core import EventLogContext, get_environment_info


def build_summary_dataframe(
    ctx: EventLogContext,
    ov: OverviewResult,
    r117: Exercise117Result,
    r1115: Exercise1115Result,
    r1118: Exercise1118Result,
    r1122: Exercise1122Result,
) -> pd.DataFrame:
    """Builds a comprehensive summary DataFrame of all 8 mandatory answers (11.7 A-E, 11.15, 11.18, 11.22)."""
    rows = [
        {
            "Kode Soal": "11.7 A",
            "Pertanyaan": "Berapa jumlah keseluruhan case?",
            "Aturan / Filter": r117.sub_a.rule_description,
            "Jumlah Case Terpilih": r117.sub_a.case_count,
            "Denominator (Total Case Aktif)": r117.sub_a.total_cases_denominator,
            "Persentase Case (%)": round(r117.sub_a.case_percentage, 4),
            "Mean Cycle Time (Hari)": round(r117.sub_a.mean_duration_days, 4),
            "Mean Cycle Time (Jam)": round(r117.sub_a.mean_duration_hours, 2),
            "Median Cycle Time (Hari)": round(r117.sub_a.median_duration_days, 4),
            "Jawaban Utama": f"{r117.sub_a.case_count:,} case",
        },
        {
            "Kode Soal": "11.7 B",
            "Pertanyaan": "Berapa rata-rata cycle time seluruh case?",
            "Aturan / Filter": r117.sub_b.rule_description,
            "Jumlah Case Terpilih": r117.sub_b.case_count,
            "Denominator (Total Case Aktif)": r117.sub_b.total_cases_denominator,
            "Persentase Case (%)": round(r117.sub_b.case_percentage, 4),
            "Mean Cycle Time (Hari)": round(r117.sub_b.mean_duration_days, 4),
            "Mean Cycle Time (Jam)": round(r117.sub_b.mean_duration_hours, 2),
            "Median Cycle Time (Hari)": round(r117.sub_b.median_duration_days, 4),
            "Jawaban Utama": f"{r117.sub_b.mean_duration_days:.2f} hari ({r117.sub_b.mean_duration_days:.4f} hari)",
        },
        {
            "Kode Soal": "11.7 C",
            "Pertanyaan": "Berapa successful cases dan rata-rata cycle time-nya?",
            "Aturan / Filter": r117.sub_c.rule_description,
            "Jumlah Case Terpilih": r117.sub_c.case_count,
            "Denominator (Total Case Aktif)": r117.sub_c.total_cases_denominator,
            "Persentase Case (%)": round(r117.sub_c.case_percentage, 4),
            "Mean Cycle Time (Hari)": round(r117.sub_c.mean_duration_days, 4),
            "Mean Cycle Time (Jam)": round(r117.sub_c.mean_duration_hours, 2),
            "Median Cycle Time (Hari)": round(r117.sub_c.median_duration_days, 4),
            "Jawaban Utama": f"{r117.sub_c.case_count:,} case ({r117.sub_c.case_percentage:.2f}%), Mean = {r117.sub_c.mean_duration_days:.2f} hari",
        },
        {
            "Kode Soal": "11.7 D",
            "Pertanyaan": "Berapa unsuccessful cases dan rata-rata cycle time-nya?",
            "Aturan / Filter": r117.sub_d.rule_description,
            "Jumlah Case Terpilih": r117.sub_d.case_count,
            "Denominator (Total Case Aktif)": r117.sub_d.total_cases_denominator,
            "Persentase Case (%)": round(r117.sub_d.case_percentage, 4),
            "Mean Cycle Time (Hari)": round(r117.sub_d.mean_duration_days, 4),
            "Mean Cycle Time (Jam)": round(r117.sub_d.mean_duration_hours, 2),
            "Median Cycle Time (Hari)": round(r117.sub_d.median_duration_days, 4),
            "Jawaban Utama": f"{r117.sub_d.case_count:,} case ({r117.sub_d.case_percentage:.2f}%), Mean = {r117.sub_d.mean_duration_days:.2f} hari",
        },
        {
            "Kode Soal": "11.7 E",
            "Pertanyaan": "Berapa canceled cases dan rata-rata cycle time-nya?",
            "Aturan / Filter": r117.sub_e.rule_description,
            "Jumlah Case Terpilih": r117.sub_e.case_count,
            "Denominator (Total Case Aktif)": r117.sub_e.total_cases_denominator,
            "Persentase Case (%)": round(r117.sub_e.case_percentage, 4),
            "Mean Cycle Time (Hari)": round(r117.sub_e.mean_duration_days, 4),
            "Mean Cycle Time (Jam)": round(r117.sub_e.mean_duration_hours, 2),
            "Median Cycle Time (Hari)": round(r117.sub_e.median_duration_days, 4),
            "Jawaban Utama": f"{r117.sub_e.case_count:,} case ({r117.sub_e.case_percentage:.2f}%), Mean = {r117.sub_e.mean_duration_days:.2f} hari",
        },
        {
            "Kode Soal": "11.15",
            "Pertanyaan": "Berapa case dengan W_Assess Potential Fraud selesai minimal 2x?",
            "Aturan / Filter": r1115.rule_description,
            "Jumlah Case Terpilih": r1115.matching_case_count,
            "Denominator (Total Case Aktif)": r1115.total_cases_denominator,
            "Persentase Case (%)": round(r1115.matching_percentage, 4),
            "Mean Cycle Time (Hari)": round(float(r1115.case_summary_df["case_duration_days"].mean()), 4) if not r1115.case_summary_df.empty else 0.0,
            "Mean Cycle Time (Jam)": round(float(r1115.case_summary_df["case_duration_days"].mean() * 24.0), 2) if not r1115.case_summary_df.empty else 0.0,
            "Median Cycle Time (Hari)": round(float(r1115.case_summary_df["case_duration_days"].median()), 4) if not r1115.case_summary_df.empty else 0.0,
            "Jawaban Utama": f"{r1115.matching_case_count:,} case ({r1115.matching_percentage:.4f}%)",
        },
        {
            "Kode Soal": "11.18",
            "Pertanyaan": "Berapa case dengan W_Assess Potential Fraud selesai minimal 2x oleh resource yang sama?",
            "Aturan / Filter": r1118.rule_description,
            "Jumlah Case Terpilih": r1118.matching_case_count,
            "Denominator (Total Case Aktif)": r1118.total_cases_denominator,
            "Persentase Case (%)": round(r1118.matching_percentage, 4),
            "Mean Cycle Time (Hari)": round(float(r1118.case_resource_summary_df["case_duration_days"].mean()), 4) if not r1118.case_resource_summary_df.empty else 0.0,
            "Mean Cycle Time (Jam)": round(float(r1118.case_resource_summary_df["case_duration_days"].mean() * 24.0), 2) if not r1118.case_resource_summary_df.empty else 0.0,
            "Median Cycle Time (Hari)": round(float(r1118.case_resource_summary_df["case_duration_days"].median()), 4) if not r1118.case_resource_summary_df.empty else 0.0,
            "Jawaban Utama": f"{r1118.matching_case_count:,} case ({r1118.matching_percentage:.4f}%)",
        },
        {
            "Kode Soal": "11.22",
            "Pertanyaan": "Adakah O_Cancelled yang kemudian diikuti O_Accepted? Berapa persentase case-nya?",
            "Aturan / Filter": r1122.rule_description,
            "Jumlah Case Terpilih": r1122.matching_case_count,
            "Denominator (Total Case Aktif)": r1122.total_cases_denominator,
            "Persentase Case (%)": round(r1122.matching_percentage, 4),
            "Mean Cycle Time (Hari)": round(float(r1122.case_summary_df["case_duration_days"].mean()), 4) if not r1122.case_summary_df.empty else 0.0,
            "Mean Cycle Time (Jam)": round(float(r1122.case_summary_df["case_duration_days"].mean() * 24.0), 2) if not r1122.case_summary_df.empty else 0.0,
            "Median Cycle Time (Hari)": round(float(r1122.case_summary_df["case_duration_days"].median()), 4) if not r1122.case_summary_df.empty else 0.0,
            "Jawaban Utama": (
                f"Ya, ada {r1122.matching_case_count:,} dari {r1122.total_cases_denominator:,} case "
                f"({r1122.matching_percentage:.2f}% / {r1122.matching_percentage:.4f}%)"
                if r1122.matching_case_count > 0
                else f"Tidak ada (0 dari {r1122.total_cases_denominator:,} case, 0.00%)"
            ),
        },
    ]
    return pd.DataFrame(rows)


def export_all_to_directory(
    output_dir: str,
    ctx: EventLogContext,
    ov: OverviewResult,
    r117: Exercise117Result,
    r1115: Exercise1115Result,
    r1118: Exercise1118Result,
    r1122: Exercise1122Result,
) -> Dict[str, str]:
    """Exports all summary answers, selected case lists, and HTML report into output_dir (F07)."""
    os.makedirs(output_dir, exist_ok=True)
    exported_files: Dict[str, str] = {}

    summary_df = build_summary_dataframe(ctx, ov, r117, r1115, r1118, r1122)
    p_sum = os.path.join(output_dir, "01_ringkasan_jawaban_latihan.csv")
    summary_df.to_csv(p_sum, index=False, encoding="utf-8-sig")
    exported_files["Ringkasan Jawaban (CSV)"] = p_sum

    p_act = os.path.join(output_dir, "02_overview_frekuensi_aktivitas.csv")
    ov.activity_table.to_csv(p_act, index=False, encoding="utf-8-sig")
    exported_files["Frekuensi Aktivitas (CSV)"] = p_act

    p_117c = os.path.join(output_dir, "03_cases_11_7_C_successful_O_Accepted.csv")
    r117.sub_c.case_df.to_csv(p_117c, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.7 C (CSV)"] = p_117c

    p_117d = os.path.join(output_dir, "04_cases_11_7_D_unsuccessful_O_Refused.csv")
    r117.sub_d.case_df.to_csv(p_117d, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.7 D (CSV)"] = p_117d

    p_117e = os.path.join(output_dir, "05_cases_11_7_E_canceled_endpoint_O_Cancelled.csv")
    r117.sub_e.case_df.to_csv(p_117e, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.7 E (CSV)"] = p_117e

    p_1115 = os.path.join(output_dir, "06_cases_11_15_repeated_complete_fraud.csv")
    r1115.case_summary_df.to_csv(p_1115, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.15 (CSV)"] = p_1115

    p_1115_ev = os.path.join(output_dir, "07_evidence_events_11_15.csv")
    r1115.evidence_events_df.to_csv(p_1115_ev, index=False, encoding="utf-8-sig")
    exported_files["Bukti Event 11.15 (CSV)"] = p_1115_ev

    p_1118 = os.path.join(output_dir, "08_cases_11_18_same_resource_fraud.csv")
    r1118.case_resource_summary_df.to_csv(p_1118, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.18 (CSV)"] = p_1118

    p_1118_ev = os.path.join(output_dir, "09_evidence_events_11_18.csv")
    r1118.evidence_events_df.to_csv(p_1118_ev, index=False, encoding="utf-8-sig")
    exported_files["Bukti Event 11.18 (CSV)"] = p_1118_ev

    p_1122 = os.path.join(output_dir, "10_cases_11_22_cancelled_followed_by_accepted.csv")
    r1122.case_summary_df.to_csv(p_1122, index=False, encoding="utf-8-sig")
    exported_files["Daftar Case 11.22 (CSV)"] = p_1122

    p_html = os.path.join(output_dir, "11_laporan_analisis_bpic17.html")
    html_content = generate_html_report(ctx, ov, r117, r1115, r1118, r1122, summary_df)
    with open(p_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    exported_files["Laporan Ringkas (HTML)"] = p_html

    return exported_files


def generate_html_report(
    ctx: EventLogContext,
    ov: OverviewResult,
    r117: Exercise117Result,
    r1115: Exercise1115Result,
    r1118: Exercise1118Result,
    r1122: Exercise1122Result,
    summary_df: pd.DataFrame,
) -> str:
    """Generates a self-contained HTML analytical report with parameters, results, and evidence tables."""
    env = get_environment_info()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sum_table_html = summary_df.to_html(index=False, classes="table", border=0)
    t1115_html = (
        r1115.case_summary_df.to_html(index=False, classes="table", border=0)
        if not r1115.case_summary_df.empty
        else "<p>Tidak ada case yang lolos filter 11.15.</p>"
    )
    t1118_html = (
        r1118.case_resource_summary_df.to_html(index=False, classes="table", border=0)
        if not r1118.case_resource_summary_df.empty
        else "<p>Tidak ada case yang lolos filter 11.18.</p>"
    )
    t1122_html = (
        r1122.case_summary_df.head(25).to_html(index=False, classes="table", border=0)
        if not r1122.case_summary_df.empty
        else "<p>Tidak ada case yang lolos filter 11.22.</p>"
    )

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Laporan Analisis Event Log BPIC17 — Bab 11 FBPM</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; color: #0f172a; margin: 24px; line-height: 1.5; }}
  h1 {{ color: #1e3a8a; border-bottom: 2px solid #cbd5e1; padding-bottom: 8px; }}
  h2 {{ color: #1e40af; margin-top: 28px; }}
  .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }}
  .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
  .table th {{ background: #1e3a8a; color: #ffffff; text-align: left; padding: 8px 10px; }}
  .table td {{ border-bottom: 1px solid #e2e8f0; padding: 7px 10px; }}
  .table tr:nth-child(even) {{ background: #f1f5f9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; background: #dbeafe; color: #1e40af; font-weight: 600; font-size: 12px; }}
</style>
</head>
<body>
  <h1>Laporan Analisis Event Log BPIC17 (Latihan Bab 11 FBPM)</h1>
  <div class="card">
    <p><strong>Berkas Dataset:</strong> {ctx.report.file_name} ({ctx.report.file_size_mb:.2f} MB) |
       <strong>Total Case:</strong> {ov.total_cases:,} |
       <strong>Total Event:</strong> {ov.total_events:,} |
       <strong>Waktu Ekspor:</strong> {now_str}</p>
    <p><strong>Lingkungan Reproduktibilitas:</strong> Python {env.get('Python')}, PM4Py {env.get('PM4Py')}, Pandas {env.get('Pandas')}, PySide6 {env.get('PySide6')}</p>
  </div>

  <h2>1. Ringkasan Jawaban Wajib (Exercise 11.7 A–E, 11.15, 11.18, 11.22)</h2>
  <div class="card">
    {sum_table_html}
  </div>

  <h2>2. Bukti Case Exercise 11.15 (W_Assess potential fraud &ge; 2x complete)</h2>
  <div class="card">
    <p><span class="badge">Aturan Filter</span> {r1115.rule_description}</p>
    <p>Jumlah case dengan &ge; 2 event semua lifecycle: <strong>{r1115.cases_with_two_all_lifecycles}</strong> case |
       Jumlah case dengan &ge; 2 event <code>complete</code>: <strong>{r1115.matching_case_count}</strong> case (tereliminasi oleh filter lifecycle complete: {r1115.excluded_by_lifecycle_count} case).</p>
    {t1115_html}
  </div>

  <h2>3. Bukti Case Exercise 11.18 (W_Assess potential fraud &ge; 2x complete oleh Resource Sama)</h2>
  <div class="card">
    <p><span class="badge">Aturan Filter</span> {r1118.rule_description}</p>
    <p>Case lolos 11.15 namun dilakukan oleh resource berbeda: <strong>{len(r1118.cases_from_1115_excluded_diff_resource)}</strong> case ({', '.join(r1118.cases_from_1115_excluded_diff_resource)}).</p>
    {t1118_html}
  </div>

  <h2>4. Bukti Case Exercise 11.22 (O_Cancelled diikuti O_Accepted — 25 Sampel Pertama)</h2>
  <div class="card">
    <p><span class="badge">Aturan Filter</span> {r1122.rule_description}</p>
    <p>Total Case Cocok: <strong>{r1122.matching_case_count:,}</strong> dari <strong>{r1122.total_cases_denominator:,}</strong> case (<strong>{r1122.matching_percentage:.2f}%</strong> / {r1122.matching_percentage:.4f}%).</p>
    {t1122_html}
  </div>
</body>
</html>
"""
