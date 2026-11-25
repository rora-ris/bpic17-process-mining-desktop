"""Generator for synthetic XES event logs covering all 8 mandatory edge-case test scenarios (Section 8)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pandas as pd


def build_synthetic_edge_case_dataframe() -> pd.DataFrame:
    """Builds a synthetic event log DataFrame specifically designed to test all 8 edge-case scenarios in Section 8.

    Cases included (10 cases total):
    1. CASE_01_DOUBLE_ACCEPTED:
       - Contains O_Accepted TWICE (day 0 -> day 10).
       - Expected: 11.7 C counts this case ONCE (not twice); cycle time = 10.0 days.
    2. CASE_02_CANCELLED_MIDDLE_THEN_OTHER:
       - Contains O_Cancelled in the middle (day 2), followed by W_Call after offers at the end (day 6).
       - Expected: 11.7 E does NOT count this as canceled (last event is not O_Cancelled).
    3. CASE_03_BOTH_REFUSED_AND_ACCEPTED:
       - Contains O_Refused (day 2) AND O_Accepted (day 8).
       - Expected: Passes BOTH 11.7 C and 11.7 D (contains filters are not forced to be mutually exclusive).
    4. CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE:
       - W_Assess potential fraud has 'schedule' twice, 'start' once, and 'complete' only ONCE (day 0 -> day 4).
       - Expected: Does NOT pass 11.15 (nor 11.18).
    5. CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE:
       - W_Assess potential fraud has 'complete' TWICE, by User_A and User_B (day 0 -> day 5).
       - Expected: Passes 11.15, does NOT pass 11.18.
    6. CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE:
       - W_Assess potential fraud has 'complete' TWICE, both by User_X (day 0 -> day 7).
       - Expected: Passes BOTH 11.15 and 11.18.
    7. CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE:
       - W_Assess potential fraud has 'complete' TWICE, both with empty/blank resource "" (day 0 -> day 3).
       - Expected: Passes 11.15, does NOT pass 11.18 (empty resource must not be treated as identical resource).
    8. CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED:
       - O_Cancelled at event 2, followed by W_Validate application at event 3, then O_Accepted at event 4 (day 0 -> day 12).
       - Expected: Passes 11.22 (even though O_Cancelled and O_Accepted are not adjacent) and passes 11.7 C.
    9. CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER:
       - O_Accepted at event 2 (day 2), followed by O_Cancelled at event 3 (day 9, last event).
       - Expected: Does NOT pass 11.22; passes 11.7 C (contains O_Accepted) and 11.7 E (ends with O_Cancelled).
    10. CASE_10_PURE_CANCELLED_AT_END:
       - Starts with A_Create Application (day 0), ends with O_Cancelled (day 5).
       - Expected: Passes 11.7 E (cycle time = 5.0 days).
    """
    base = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    def ts(days: float) -> datetime:
        return base + timedelta(days=days)

    rows: List[Dict[str, object]] = [
        # 1. CASE_01_DOUBLE_ACCEPTED (duration = 10 days)
        {"case:concept:name": "CASE_01_DOUBLE_ACCEPTED", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E01_1", "OfferID": "Off_1A"},
        {"case:concept:name": "CASE_01_DOUBLE_ACCEPTED", "concept:name": "O_Accepted", "lifecycle:transition": "complete", "org:resource": "User_2", "time:timestamp": ts(4), "EventID": "E01_2", "OfferID": "Off_1A"},
        {"case:concept:name": "CASE_01_DOUBLE_ACCEPTED", "concept:name": "O_Accepted", "lifecycle:transition": "complete", "org:resource": "User_2", "time:timestamp": ts(10), "EventID": "E01_3", "OfferID": "Off_1B"},

        # 2. CASE_02_CANCELLED_MIDDLE_THEN_OTHER (duration = 6 days)
        {"case:concept:name": "CASE_02_CANCELLED_MIDDLE_THEN_OTHER", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E02_1", "OfferID": "Off_2A"},
        {"case:concept:name": "CASE_02_CANCELLED_MIDDLE_THEN_OTHER", "concept:name": "O_Cancelled", "lifecycle:transition": "complete", "org:resource": "User_3", "time:timestamp": ts(2), "EventID": "E02_2", "OfferID": "Off_2A"},
        {"case:concept:name": "CASE_02_CANCELLED_MIDDLE_THEN_OTHER", "concept:name": "W_Call after offers", "lifecycle:transition": "complete", "org:resource": "User_3", "time:timestamp": ts(6), "EventID": "E02_3", "OfferID": "Off_2A"},

        # 3. CASE_03_BOTH_REFUSED_AND_ACCEPTED (duration = 8 days)
        {"case:concept:name": "CASE_03_BOTH_REFUSED_AND_ACCEPTED", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E03_1", "OfferID": "Off_3A"},
        {"case:concept:name": "CASE_03_BOTH_REFUSED_AND_ACCEPTED", "concept:name": "O_Refused", "lifecycle:transition": "complete", "org:resource": "User_4", "time:timestamp": ts(2), "EventID": "E03_2", "OfferID": "Off_3A"},
        {"case:concept:name": "CASE_03_BOTH_REFUSED_AND_ACCEPTED", "concept:name": "O_Accepted", "lifecycle:transition": "complete", "org:resource": "User_4", "time:timestamp": ts(8), "EventID": "E03_3", "OfferID": "Off_3B"},

        # 4. CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE (duration = 4 days)
        {"case:concept:name": "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E04_1", "OfferID": ""},
        {"case:concept:name": "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "schedule", "org:resource": "User_10", "time:timestamp": ts(1), "EventID": "E04_2", "OfferID": ""},
        {"case:concept:name": "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "schedule", "org:resource": "User_10", "time:timestamp": ts(2), "EventID": "E04_3", "OfferID": ""},
        {"case:concept:name": "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "start", "org:resource": "User_10", "time:timestamp": ts(3), "EventID": "E04_4", "OfferID": ""},
        {"case:concept:name": "CASE_04_FRAUD_SCHEDULED_TWICE_COMPLETE_ONCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "User_10", "time:timestamp": ts(4), "EventID": "E04_5", "OfferID": ""},

        # 5. CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE (duration = 5 days)
        {"case:concept:name": "CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E05_1", "OfferID": ""},
        {"case:concept:name": "CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "User_A", "time:timestamp": ts(2), "EventID": "E05_2", "OfferID": ""},
        {"case:concept:name": "CASE_05_FRAUD_TWO_COMPLETE_DIFF_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "User_B", "time:timestamp": ts(5), "EventID": "E05_3", "OfferID": ""},

        # 6. CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE (duration = 7 days)
        {"case:concept:name": "CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E06_1", "OfferID": ""},
        {"case:concept:name": "CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "User_X", "time:timestamp": ts(3), "EventID": "E06_2", "OfferID": ""},
        {"case:concept:name": "CASE_06_FRAUD_TWO_COMPLETE_SAME_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "User_X", "time:timestamp": ts(7), "EventID": "E06_3", "OfferID": ""},

        # 7. CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE (duration = 3 days)
        {"case:concept:name": "CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E07_1", "OfferID": ""},
        {"case:concept:name": "CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "", "time:timestamp": ts(1), "EventID": "E07_2", "OfferID": ""},
        {"case:concept:name": "CASE_07_FRAUD_TWO_COMPLETE_EMPTY_RESOURCE", "concept:name": "W_Assess potential fraud", "lifecycle:transition": "complete", "org:resource": "", "time:timestamp": ts(3), "EventID": "E07_3", "OfferID": ""},

        # 8. CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED (duration = 12 days)
        {"case:concept:name": "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E08_1", "OfferID": "Off_8A"},
        {"case:concept:name": "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED", "concept:name": "O_Cancelled", "lifecycle:transition": "complete", "org:resource": "User_5", "time:timestamp": ts(3), "EventID": "E08_2", "OfferID": "Off_8A"},
        {"case:concept:name": "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED", "concept:name": "W_Validate application", "lifecycle:transition": "complete", "org:resource": "User_6", "time:timestamp": ts(7), "EventID": "E08_3", "OfferID": ""},
        {"case:concept:name": "CASE_08_CANCELLED_THEN_OTHER_THEN_ACCEPTED", "concept:name": "O_Accepted", "lifecycle:transition": "complete", "org:resource": "User_6", "time:timestamp": ts(12), "EventID": "E08_4", "OfferID": "Off_8B"},

        # 9. CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER (duration = 9 days)
        {"case:concept:name": "CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E09_1", "OfferID": "Off_9A"},
        {"case:concept:name": "CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER", "concept:name": "O_Accepted", "lifecycle:transition": "complete", "org:resource": "User_7", "time:timestamp": ts(2), "EventID": "E09_2", "OfferID": "Off_9A"},
        {"case:concept:name": "CASE_09_ACCEPTED_BEFORE_CANCELLED_NO_ACCEPTED_AFTER", "concept:name": "O_Cancelled", "lifecycle:transition": "complete", "org:resource": "User_7", "time:timestamp": ts(9), "EventID": "E09_3", "OfferID": "Off_9B"},

        # 10. CASE_10_PURE_CANCELLED_AT_END (duration = 5 days)
        {"case:concept:name": "CASE_10_PURE_CANCELLED_AT_END", "concept:name": "A_Create Application", "lifecycle:transition": "complete", "org:resource": "User_1", "time:timestamp": ts(0), "EventID": "E10_1", "OfferID": "Off_10A"},
        {"case:concept:name": "CASE_10_PURE_CANCELLED_AT_END", "concept:name": "O_Cancelled", "lifecycle:transition": "complete", "org:resource": "User_8", "time:timestamp": ts(5), "EventID": "E10_2", "OfferID": "Off_10A"},
    ]
    return pd.DataFrame(rows)


def generate_synthetic_xes_file(output_path: str) -> str:
    """Exports the synthetic edge-case event log to an XES file using PM4Py."""
    import pm4py

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df = build_synthetic_edge_case_dataframe()
    pm4py.write_xes(df, output_path, case_id_key="case:concept:name")
    return output_path
