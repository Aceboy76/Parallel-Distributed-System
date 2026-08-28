"""
partition_strategy.py - Session 1, Part 5.

Produces every row of the "Partitioning Strategy and Workload Definition"
table, and shows the evidence for rejecting the alternative keys.

The point of this script is that the partition key should be a *derived*
choice, not an asserted one. It evaluates every candidate key in the joined
dataset against three tests and reports which ones fail and why:

    1. Cardinality - too few distinct values and you cannot fill the workers;
                      too many and per-partition work becomes trivial relative
                      to scheduling overhead.
    2. Variance    - a perfectly uniform key produces perfectly even partitions
                      and leaves the Part 10 skew analysis with nothing to say.
    3. Join survival- the key must exist in the joined frame, which means it
                      must come through the join rather than being dropped or
                      aggregated away.

Adapted from the guide's synthetic-dataset version: NEVER_PARTITION lists the
real identifier/measure columns for this schema (id_assessment, id_student,
score) instead of the synthetic dataset's id/amount/parameters_json.

Run:
    python partition_strategy.py
"""
import json
import sys

import pandas as pd

import config as cfg
from load_and_join import build_working_dataset, load_frames


# Columns that are identifiers of the event itself, or free-form values, and
# are therefore never sensible partition keys.
NEVER_PARTITION = {"id_assessment", "id_student", cfg.METRIC_FIELD}

# A workable partition key needs enough distinct values to fill the workers
# but not so many that each partition holds a handful of rows.
MIN_DISTINCT = 2
MAX_DISTINCT_RATIO = 0.5  # distinct values must be < 50% of row count


# ---------------------------------------------------------------------------
def owning_file(column: str, frames: dict[str, pd.DataFrame]) -> str:
    """Which input file a column originally came from."""
    owners = [name for name, df in frames.items() if column in df.columns]
    if not owners:
        return "derived in join"
    return " + ".join(owners)


def evaluate(working: pd.DataFrame,
             frames: dict[str, pd.DataFrame]) -> list[dict]:
    """Score every column in the joined frame as a partition-key candidate."""
    rows = len(working)
    candidates = []
    for col in working.columns:
        counts = working[col].value_counts()
        distinct = int(counts.size)
        rejects = []

        if col in NEVER_PARTITION:
            rejects.append("identifier or measure, not a grouping attribute")
        if distinct < MIN_DISTINCT:
            rejects.append(f"only {distinct} distinct value")
        if distinct > rows * MAX_DISTINCT_RATIO:
            rejects.append(f"{distinct:,} distinct values is near-unique")

        skew = round(counts.max() / counts.min(), 2) if distinct else 0.0
        if not rejects and skew == 1.0:
            rejects.append("perfectly uniform - no skew to analyse")

        candidates.append({
            "column": col,
            "source_file": owning_file(col, frames),
            "distinct": distinct,
            "min": int(counts.min()) if distinct else 0,
            "median": int(counts.median()) if distinct else 0,
            "max": int(counts.max()) if distinct else 0,
            "skew_ratio": skew,
            "viable": not rejects,
            "rejected_because": "; ".join(rejects),
        })
    return candidates


# ---------------------------------------------------------------------------
def survives_join(key: str, frames: dict[str, pd.DataFrame],
                   working: pd.DataFrame) -> dict:
    """
    Confirm the chosen key is present after the join and trace where it
    entered from.
    """
    present = key in working.columns
    origin = owning_file(key, frames)
    nulls = int(working[key].isna().sum()) if present else None
    return {
        "key": key,
        "present_after_join": present,
        "entered_from": origin,
        "nulls_after_join": nulls,
        "verdict": ("survives the join intact" if present and nulls == 0
                    else "DOES NOT survive the join"),
    }


# ---------------------------------------------------------------------------
def main() -> int:
    cfg.banner("SESSION 1 - PARTITIONING STRATEGY (Part 5)")
    frames = load_frames()
    working, join_report = build_working_dataset(frames, verbose=False)
    print(f" joined dataset: {len(working):,} rows x "
          f"{len(working.columns)} columns")

    # ---------------- candidate evaluation ----------------
    cfg.banner("CANDIDATE PARTITION KEYS")
    candidates = evaluate(working, frames)
    header = (f"  {'column':<22}{'distinct':>10}{'min':>10}{'median':>10}"
              f"{'max':>10}{'skew':>12}  verdict")
    print(header)
    print("  " + "-" * (len(header) + 20))
    for c in sorted(candidates, key=lambda x: (not x["viable"], -x["skew_ratio"])):
        verdict = "VIABLE" if c["viable"] else c["rejected_because"]
        print(f"  {c['column']:<22}{c['distinct']:>10,}{c['min']:>10,}"
              f"{c['median']:>10,}{c['max']:>10,}{c['skew_ratio']:>12,.2f}"
              f"  {verdict}")
    viable = [c for c in candidates if c["viable"]]
    print(f"\n  {len(viable)} viable candidate(s) of {len(candidates)} columns")

    # ---------------- the chosen key ----------------
    chosen = next(c for c in candidates if c["column"] == cfg.PARTITION_KEY)
    survival = survives_join(cfg.PARTITION_KEY, frames, working)
    cfg.banner(f"CHOSEN KEY: {cfg.PARTITION_KEY}")
    print(f"  entity that owns the key    : {survival['entered_from']}")
    print(f"  distinct key values         : {chosen['distinct']}")
    print(f"  survives the join           : {survival['verdict']}")
    print(f"  nulls after join            : {survival['nulls_after_join']}")
    print(f"  predicted records/partition : min={chosen['min']:,} "
          f"median={chosen['median']:,} max={chosen['max']:,}")
    print(f"  predicted skew ratio        : {chosen['skew_ratio']} : 1")

    # ---------------- the rejected alternative ----------------
    alt = next(c for c in candidates if c["column"] == cfg.CUSTOMER_KEY)
    cfg.banner(f"REJECTED ALTERNATIVE: {cfg.CUSTOMER_KEY}")
    print(f"  distinct values  : {alt['distinct']:,}")
    print(f"  records per key  : min={alt['min']} median={alt['median']} "
          f"max={alt['max']}")
    print(f"  skew ratio       : {alt['skew_ratio']} : 1")
    print(f"  rejected because : {alt['rejected_because']}")

    # ---------------- workload definition ----------------
    cfg.banner("WORKLOAD DEFINITION")
    workload = (f"Compute submission count, total {cfg.METRIC_FIELD}, and "
                f"mean {cfg.METRIC_FIELD} per {cfg.PARTITION_KEY} across the "
                f"joined {len(working):,}-row dataset.")
    print(f"  {workload}")
    schema = {
        cfg.PARTITION_KEY: "string",
        "txn_count": "int64",
        "score_total": "double",
        "score_mean": "double",
    }
    print("\n  expected output schema:")
    for col, dtype in schema.items():
        print(f"    {col:<16} {dtype}")
    print("\n  independence check: regional aggregates require no data from")
    print("  any other region, so each partition can be computed alone and")
    print("  the partial results combined afterwards.")

    # ---------------- persist ----------------
    out = cfg.RESULTS_DIR / "partition_strategy.json"
    out.write_text(json.dumps({
        "chosen_key": cfg.PARTITION_KEY,
        "owned_by": survival["entered_from"],
        "join_survival": survival,
        "prediction": {
            "distinct": chosen["distinct"],
            "min": chosen["min"],
            "median": chosen["median"],
            "max": chosen["max"],
            "skew_ratio": chosen["skew_ratio"],
        },
        "rejected_alternative": alt,
        "all_candidates": candidates,
        "workload": workload,
        "output_schema": schema,
        "join": join_report,
    }, indent=2))
    print(f"\nWrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
