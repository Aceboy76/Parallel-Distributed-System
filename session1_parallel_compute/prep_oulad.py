"""
prep_oulad.py - one-time data preparation step, run BEFORE profile_files.py.

The Session 1 guide's pipeline (profile_files.py onward) expects four
ready-made files with the roles Event / Entity / Entity / Lookup, sized so
that Entity and Lookup can be broadcast. Raw OULAD does not ship those
files directly, so this script builds them once from the source CSVs and
writes them to DATA_DIR. Every downstream script (profile_files.py through
render_diagrams.py) reads only the files this script produces - it never
touches studentInfo.csv or studentRegistration.csv directly.

Why this step is separate from load_and_join.py: the guide's join step
assumes each Entity file is already one row per customer_id (a precondition
for validate="many_to_one"). studentInfo.csv and studentRegistration.csv are
one row per (student, module presentation), so they must be deduplicated to
student-grain BEFORE the join, not during it. Doing the dedup inside
load_and_join.py would hide a real data decision inside what should be a
mechanical join step.

Output files (role -> file):
    Event    -> studentAssessment.csv     (used as-is; already submission-grain)
    Entity   -> customers_dim.csv         (deduped studentInfo.csv)
    Entity   -> entitlements_dim.csv      (deduped studentRegistration.csv)
    Lookup   -> assessment_defs.csv       (assessments.csv, renamed columns only)

Run:
    python prep_oulad.py
"""
import json
import sys

import pandas as pd

import config as cfg


# ---------------------------------------------------------------------------
def build_customers_dim(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    One row per id_student. studentInfo.csv is one row per (student, module
    presentation); a student's demographic fields are consistent across
    every presentation EXCEPT age_band, which is why age_band is dropped
    rather than silently deduped to a possibly-wrong value.
    """
    per_student_nunique = raw.groupby("id_student").nunique(dropna=False)
    unstable = [
        c for c in ["gender", "region", "highest_education", "imd_band",
                    "age_band", "disability"]
        if (per_student_nunique[c] > 1).any()
    ]

    keep_cols = ["id_student", "gender", "region", "highest_education",
                 "imd_band", "disability"]
    dim = (
        raw.sort_values(["id_student", "code_presentation"])
        .drop_duplicates(subset="id_student", keep="first")
        [keep_cols]
        .reset_index(drop=True)
    )

    report = {
        "source_rows": int(len(raw)),
        "output_rows": int(len(dim)),
        "distinct_id_student": int(raw["id_student"].nunique()),
        "dedup_rule": "first row per id_student, sorted by code_presentation",
        "fields_dropped_as_unstable_across_presentations": unstable,
        "fields_confirmed_stable": [c for c in keep_cols[1:] if c not in unstable],
    }
    return dim, report


# ---------------------------------------------------------------------------
def build_entitlements_dim(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    One row per id_student. date_registration and date_unregistration
    genuinely differ across a student's module presentations (registering
    for a second course is a later event than the first), so "first row" is
    a real modelling choice, not a data-quality artefact. It is documented
    here rather than assumed.
    """
    per_student_nunique = raw.groupby("id_student").nunique(dropna=False)
    varies_by_presentation = [
        c for c in ["date_registration", "date_unregistration"]
        if (per_student_nunique[c] > 1).any()
    ]

    dim = (
        raw.sort_values(["id_student", "code_presentation"])
        .drop_duplicates(subset="id_student", keep="first")
        [["id_student", "date_registration", "date_unregistration"]]
        .reset_index(drop=True)
    )

    report = {
        "source_rows": int(len(raw)),
        "output_rows": int(len(dim)),
        "distinct_id_student": int(raw["id_student"].nunique()),
        "dedup_rule": "first row per id_student, sorted by code_presentation",
        "fields_that_vary_by_presentation": varies_by_presentation,
        "limitation": (
            "date_registration/date_unregistration reflect only the "
            "student's FIRST module presentation. A student's later "
            "registrations are not represented in this Entity file."
        ) if varies_by_presentation else "",
    }
    return dim, report


# ---------------------------------------------------------------------------
def build_assessment_defs(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    assessments.csv is already one row per id_assessment - no dedup needed.
    Columns are renamed only to keep the Lookup file self-contained (it
    drops code_module/code_presentation, which are not used as join keys
    anywhere in the corrected schema).
    """
    is_unique = raw["id_assessment"].is_unique
    dim = raw[["id_assessment", "assessment_type", "date", "weight"]].copy()
    report = {
        "source_rows": int(len(raw)),
        "output_rows": int(len(dim)),
        "id_assessment_is_unique": bool(is_unique),
        "dedup_rule": "none required; already one row per id_assessment",
    }
    return dim, report


# ---------------------------------------------------------------------------
def main() -> int:
    cfg.banner("OULAD PREP - BUILDING CUSTOMERS_DIM / ENTITLEMENTS_DIM / ASSESSMENT_DEFS")

    student_info = pd.read_csv(cfg.DATA_DIR / "studentInfo.csv")
    student_registration = pd.read_csv(cfg.DATA_DIR / "studentRegistration.csv")
    assessments = pd.read_csv(cfg.DATA_DIR / "assessments.csv")

    customers_dim, cust_report = build_customers_dim(student_info)
    entitlements_dim, ent_report = build_entitlements_dim(student_registration)
    assessment_defs, defs_report = build_assessment_defs(assessments)

    for label, df, report in [
        ("customers_dim.csv", customers_dim, cust_report),
        ("entitlements_dim.csv", entitlements_dim, ent_report),
        ("assessment_defs.csv", assessment_defs, defs_report),
    ]:
        print(f"\n {label}")
        for k, v in report.items():
            print(f"   {k}: {v}")

    # Both Entity files must land on the SAME set of id_student values, or
    # the later join in load_and_join.py will silently drop or duplicate
    # rows rather than raising - check it here, before anything downstream
    # relies on it.
    same_population = set(customers_dim["id_student"]) == set(entitlements_dim["id_student"])
    print(f"\n customers_dim and entitlements_dim cover identical students: {same_population}")
    if not same_population:
        print(" WARNING: populations differ. Investigate before running profile_files.py.")

    customers_dim.to_csv(cfg.DATA_DIR / "customers_dim.csv", index=False)
    entitlements_dim.to_csv(cfg.DATA_DIR / "entitlements_dim.csv", index=False)
    assessment_defs.to_csv(cfg.DATA_DIR / "assessment_defs.csv", index=False)

    prep_report = {
        "customers_dim": cust_report,
        "entitlements_dim": ent_report,
        "assessment_defs": defs_report,
        "same_student_population": same_population,
        "note": (
            "studentAssessment.csv is used as-is for the Event role; it is "
            "already one row per submission and needs no preparation."
        ),
    }
    out = cfg.RESULTS_DIR / "prep_report.json"
    out.write_text(json.dumps(prep_report, indent=2))
    print(f"\nWrote customers_dim.csv, entitlements_dim.csv, assessment_defs.csv to {cfg.DATA_DIR}")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
