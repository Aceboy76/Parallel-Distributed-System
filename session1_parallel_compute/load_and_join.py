"""
load_and_join.py - Session 1, Part 4.

Assembles the working dataset from the four input files along a documented
join path, and reconciles the row count before and after.

Join path (all inner, all many-to-one):

    assessments  (studentAssessment.csv - Event)
      |> customers_dim        on id_student
      |> assessment_defs      on id_assessment
      |> entitlements_dim     on id_student

Every merge passes validate="many_to_one". That argument is the cheapest
defence against a silent join error: if the parent key is not unique, pandas
raises instead of quietly multiplying rows. Without it a duplicated key
inflates the row count, every downstream measurement is wrong, and nothing
reports a failure.

Adapted from the guide's synthetic-dataset version: no column renaming or
suffixing is needed here, because customers_dim.csv, entitlements_dim.csv,
and assessment_defs.csv already use their real key names (id_student,
id_assessment) and share no other column names with each other or with
studentAssessment.csv.

Importable:
    from load_and_join import load_frames, build_working_dataset

Run:
    python load_and_join.py
"""
import sys
import time

import pandas as pd

import config as cfg


# ---------------------------------------------------------------------------
def load_frames() -> dict[str, pd.DataFrame]:
    """Read every input file into a DataFrame."""
    return {name: pd.read_csv(cfg.path_for(name)) for name in cfg.FILES}


# ---------------------------------------------------------------------------
def build_working_dataset(
    frames: dict[str, pd.DataFrame] | None = None,
    verbose: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Join the four files into the working dataset.

    Returns the joined frame and a reconciliation report. Raises AssertionError
    if the join changed the row count, which would mean duplication or loss.
    """
    if frames is None:
        frames = load_frames()

    events = frames["assessments"]            # studentAssessment.csv
    customers = frames["customers"]            # customers_dim.csv
    configs = frames["assessment_configs"]      # assessment_defs.csv
    entitlements = frames["entitlements"]       # entitlements_dim.csv

    rows_before = len(events)

    start = time.perf_counter()
    working = (
        events
        .merge(customers,
               on=cfg.CUSTOMER_KEY, how="inner", validate="many_to_one")
        .merge(configs,
               on=cfg.CONFIG_KEY, how="inner", validate="many_to_one")
        .merge(entitlements,
               on=cfg.CUSTOMER_KEY, how="inner", validate="many_to_one")
    )
    join_seconds = time.perf_counter() - start

    rows_after = len(working)

    report = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "delta": rows_after - rows_before,
        "columns_after": len(working.columns),
        "join_seconds": round(join_seconds, 4),
        "join_path": ("assessments |> customers_dim |> assessment_defs "
                      "|> entitlements_dim"),
    }

    if verbose:
        cfg.banner("JOIN PATH RECONCILIATION")
        print(f" join path        : {report['join_path']}")
        print(f" rows before join  : {rows_before:,}")
        print(f" rows after join   : {rows_after:,}")
        print(f" difference        : {report['delta']}")
        print(f" columns after     : {report['columns_after']}")
        print(f" join time         : {report['join_seconds']} s")

    # An inner join on a many-to-one relationship must not increase the row
    # count. An increase means a parent key is not unique. A decrease means
    # unmatched keys were dropped - confirm that is intended before ignoring.
    assert rows_after == rows_before, (
        f"Join changed the row count: {rows_before} -> {rows_after}. "
        "Check key uniqueness on the parent side and unmatched foreign keys."
    )

    return working, report


# ---------------------------------------------------------------------------
def main() -> int:
    cfg.banner("SESSION 1 - LOAD AND JOIN")
    frames = load_frames()
    for name, df in frames.items():
        print(f"  loaded {name:<22} {len(df):>6,} rows")

    working, report = build_working_dataset(frames)

    print("\n working dataset columns:")
    for col in working.columns:
        print(f"  - {col}")

    # Persist so the baseline and validation steps use identical input.
    working.to_parquet(cfg.OUT_JOINED, index=False)
    print(f"\nWrote {cfg.OUT_JOINED} ({len(working):,} rows)")

    # Quick distribution preview of the partition key.
    counts = working[cfg.PARTITION_KEY].value_counts()
    cfg.banner(f"PARTITION KEY PREVIEW - {cfg.PARTITION_KEY}")
    print(f"  distinct values  : {counts.size}")
    print(f"  records per key  : min={counts.min()} "
          f"median={int(counts.median())} max={counts.max()}")
    print(f"  skew ratio       : {counts.max() / counts.min():.2f} : 1")
    print(f"\n  heaviest 5:\n{counts.head(5).to_string()}")
    print(f"\n  lightest 5:\n{counts.tail(5).to_string()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
