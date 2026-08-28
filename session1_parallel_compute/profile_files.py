"""
profile_files.py - Session 1, Parts 2 and 3.

Profiles every input file individually, detects candidate primary keys by
testing column uniqueness, verifies referential integrity across files, and
evaluates the four dataset eligibility conditions from the activity sheet.

Adapted from the guide's synthetic-dataset version in two places:
  - There is no generic "id" column on the parent files. customers_dim.csv
    and entitlements_dim.csv are keyed directly on id_student; assessment_defs.csv
    is keyed directly on id_assessment. Integrity checks join on those names,
    not on a renamed "id".
  - EVENT_TIME_FIELD (date_submitted) is an integer day-offset from the
    module start date, not a timestamp string, so it is NOT parsed with
    pd.to_datetime. Its span is measured directly in days.

Writes results/file_profile.json for use by the other scripts and by the
submission document.

Run:
    python profile_files.py
"""
import json
import sys

import pandas as pd

import config as cfg


# ---------------------------------------------------------------------------
def profile_one(name: str) -> tuple[pd.DataFrame, dict]:
    """Profile a single input file and return the frame plus its profile."""
    path = cfg.path_for(name)
    df = pd.read_csv(path)

    # A column is a candidate primary key if every value is unique and
    # non-null. Several columns can qualify; the semantically correct one is
    # chosen by hand in the file inventory.
    candidate_pks = [
        c for c in df.columns
        if df[c].notna().all() and df[c].is_unique
    ]

    # Columns with a single distinct value carry no information and are worth
    # flagging, because they silently break downstream analytics.
    constant_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]

    prof = {
        "file": path.name,
        "role": cfg.FILES[name]["role"],
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": df.columns.tolist(),
        "size_kb": round(path.stat().st_size / 1024, 1),
        "candidate_primary_keys": candidate_pks,
        "constant_columns": constant_cols,
        "null_counts": {c: int(df[c].isna().sum()) for c in df.columns},
        "distinct_counts": {c: int(df[c].nunique(dropna=True)) for c in df.columns},
    }
    return df, prof


# ---------------------------------------------------------------------------
def check_integrity(frames: dict[str, pd.DataFrame]) -> dict:
    """
    Confirm that every foreign key resolves to a parent row.

    Unlike the synthetic-dataset version, parent keys are the real column
    names (id_student, id_assessment) rather than a generic "id" - so no
    renaming is needed before the isin() checks.
    """
    events = frames["assessments"]          # studentAssessment.csv
    cust = frames["customers"]               # customers_dim.csv
    ent = frames["entitlements"]             # entitlements_dim.csv
    configs = frames["assessment_configs"]   # assessment_defs.csv

    checks = {
        "assessments.id_student -> customers_dim.id_student":
            bool(events[cfg.CUSTOMER_KEY].isin(set(cust[cfg.CUSTOMER_KEY])).all()),
        "assessments.id_assessment -> assessment_defs.id_assessment":
            bool(events[cfg.CONFIG_KEY].isin(set(configs[cfg.CONFIG_KEY])).all()),
        "entitlements_dim.id_student -> customers_dim.id_student":
            bool(ent[cfg.CUSTOMER_KEY].isin(set(cust[cfg.CUSTOMER_KEY])).all()),
    }
    orphans = {
        "assessments_without_customer":
            int((~events[cfg.CUSTOMER_KEY].isin(set(cust[cfg.CUSTOMER_KEY]))).sum()),
        "assessments_without_assessment_def":
            int((~events[cfg.CONFIG_KEY].isin(set(configs[cfg.CONFIG_KEY]))).sum()),
    }
    return {"foreign_keys_resolve": checks, "orphan_counts": orphans}


# ---------------------------------------------------------------------------
def check_eligibility(frames: dict[str, pd.DataFrame], prof: dict) -> dict:
    """Evaluate the four Part 2 eligibility conditions."""
    # Condition 1 - at least three qualifying (non-Lookup) files.
    qualifying = [n for n, p in prof.items() if p["role"] in ("Event", "Entity")]

    # Condition 2 - at least one genuine one-to-many association. A child
    # whose foreign key is unique is a 1:1 extension, not a 1..* relation.
    events = frames["assessments"]
    ent = frames["entitlements"]
    one_to_many = []
    if not events[cfg.CUSTOMER_KEY].is_unique:
        per_parent = events[cfg.CUSTOMER_KEY].value_counts()
        one_to_many.append({
            "parent": "customers",
            "child": "assessments",
            "key": cfg.CUSTOMER_KEY,
            "children_min": int(per_parent.min()),
            "children_median": int(per_parent.median()),
            "children_max": int(per_parent.max()),
        })
    entitlement_is_1to1 = bool(ent[cfg.CUSTOMER_KEY].is_unique)

    # Condition 3 - a usable event-time field. date_submitted is an integer
    # day-offset from the module start, not a timestamp string - measure the
    # span directly rather than parsing it as a date.
    day_offset = events[cfg.EVENT_TIME_FIELD]
    span_days = int(day_offset.max() - day_offset.min())

    # Condition 4 - transactional volume.
    event_rows = sum(p["rows"] for p in prof.values() if p["role"] == "Event")

    return {
        "condition_1_three_related_files": {
            "met": len(qualifying) >= 3,
            "qualifying_files": qualifying,
            "lookup_files_excluded":
                [n for n, p in prof.items() if p["role"] == "Lookup"],
        },
        "condition_2_one_to_many": {
            "met": len(one_to_many) >= 1,
            "associations": one_to_many,
            "entitlements_is_one_to_one": entitlement_is_1to1,
        },
        "condition_3_timestamp": {
            "met": True,
            "field": f"assessments.{cfg.EVENT_TIME_FIELD}",
            "field_type": "integer day-offset from module start (not a calendar timestamp)",
            "min": int(day_offset.min()),
            "max": int(day_offset.max()),
            "span_days": span_days,
            "note": ("Negative values occur - a small number of assessments "
                     "are submitted before the module's official start day "
                     "(banked or early submissions)."),
        },
        "condition_4_volume": {
            "met": event_rows >= 50_000,
            "event_rows": event_rows,
        },
    }


# ---------------------------------------------------------------------------
def main() -> int:
    cfg.banner("SESSION 1 - FILE PROFILING")
    frames, prof = {}, {}
    for name in cfg.FILES:
        df, p = profile_one(name)
        frames[name], prof[name] = df, p
        print(f"\nFILE: {p['file']:<28} role={p['role']:<7} "
              f"rows={p['rows']:>6} cols={p['columns']} "
              f"size={p['size_kb']} KB")
        print(f"    columns: {', '.join(p['column_names'])}")
        print(f"    candidate primary keys: {p['candidate_primary_keys']}")
        if p["constant_columns"]:
            print(f"    WARNING constant columns (no variance): "
                  f"{p['constant_columns']}")

    cfg.banner("REFERENTIAL INTEGRITY")
    integrity = check_integrity(frames)
    for label, ok in integrity["foreign_keys_resolve"].items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"  orphan records: {integrity['orphan_counts']}")

    cfg.banner("DATASET ELIGIBILITY (Part 2)")
    elig = check_eligibility(frames, prof)
    for key, result in elig.items():
        print(f"  {'MET ' if result['met'] else 'NOT MET'}  {key}")
    for assoc in elig["condition_2_one_to_many"]["associations"]:
        print(f"      {assoc['parent']} 1..* {assoc['child']} on {assoc['key']}: "
              f"min={assoc['children_min']} "
              f"median={assoc['children_median']} "
              f"max={assoc['children_max']}")
    if elig["condition_2_one_to_many"]["entitlements_is_one_to_one"]:
        print("      NOTE entitlements_dim.id_student is unique -> 1:1 extension "
              "of Customer, not a second 1..* association")

    report = {"profiles": prof, "integrity": integrity, "eligibility": elig}
    cfg.OUT_PROFILE.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {cfg.OUT_PROFILE}")

    all_met = all(v["met"] for v in elig.values())
    all_fk = all(integrity["foreign_keys_resolve"].values())
    if not (all_met and all_fk):
        print("\nDATASET NOT ELIGIBLE - select a different dataset.")
        return 1

    print("\nAll eligibility conditions met. Proceed to load_and_join.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
