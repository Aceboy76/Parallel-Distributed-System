"""
parallel_compute.py - Session 1, Parts 7 and 9.

Partitioned parallel implementation in PySpark local mode, plus the
correctness check against the sequential baseline.

Two design decisions are worth stating explicitly.

Broadcast joins. customers_dim (28,785 rows), entitlements_dim (28,785
rows), and assessment_defs (206 rows) are all small enough to replicate to
every worker. Broadcasting them removes the shuffle that a join would
otherwise force across all 173,912 studentAssessment rows. Confirm with the
physical plan: it should show BroadcastHashJoin and no SortMergeJoin.

Bounded parallelism. repartition(n, key) is called with an explicit n rather
than relying on the default. local[*] uses whatever cores are available,
which is not a documented, tuned, or reproducible setting.

Adapted from the guide's synthetic-dataset version: no column renaming is
needed on read, because customers_dim.csv, entitlements_dim.csv, and
assessment_defs.csv already use their real key names (id_student,
id_assessment) rather than a generic "id" that needs aligning.

Importable:
    from parallel_compute import build_joined, compute_parallel, validate

Run:
    python parallel_compute.py
"""
import json
import sys
import time

import pandas as pd

import config as cfg


# ---------------------------------------------------------------------------
def load_spark_frames(spark):
    """Read each input file into a Spark DataFrame."""
    def read(name):
        return (
            spark.read
            .option("header", True)
            .option("inferSchema", True)
            .csv(str(cfg.path_for(name)))
        )

    events = read("assessments")          # studentAssessment.csv
    customers = read("customers")         # customers_dim.csv
    configs = read("assessment_configs")  # assessment_defs.csv
    entitlements = read("entitlements")   # entitlements_dim.csv
    return events, customers, configs, entitlements


# ---------------------------------------------------------------------------
def build_joined(spark, verbose: bool = True):
    """Join the four files in Spark, broadcasting the small ones."""
    from pyspark.sql import functions as F

    events, customers, configs, entitlements = load_spark_frames(spark)

    rows_before = events.count()
    input_partitions = events.rdd.getNumPartitions()

    joined = (
        events
        .join(F.broadcast(customers), on=cfg.CUSTOMER_KEY, how="inner")
        .join(F.broadcast(configs), on=cfg.CONFIG_KEY, how="inner")
        .join(F.broadcast(entitlements), on=cfg.CUSTOMER_KEY, how="inner")
    )
    joined.cache()
    rows_after = joined.count()

    # Inspect the physical plan to confirm the join strategy.
    plan = joined._jdf.queryExecution().executedPlan().toString()
    broadcast_nodes = plan.count("BroadcastHashJoin")
    sortmerge_nodes = plan.count("SortMergeJoin")

    report = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "delta": rows_after - rows_before,
        "input_partitions": input_partitions,
        "broadcast_hash_joins": broadcast_nodes,
        "sort_merge_joins": sortmerge_nodes,
    }

    if verbose:
        cfg.banner("SPARK JOIN")
        print(f"  rows before join   : {rows_before:,}")
        print(f"  rows after join    : {rows_after:,}")
        print(f"  difference         : {report['delta']}")
        print(f"  input partitions   : {input_partitions}")
        print(f"  BroadcastHashJoin  : {broadcast_nodes}")
        print(f"  SortMergeJoin      : {sortmerge_nodes}")
        if sortmerge_nodes == 0:
            print("  -> no shuffle from the join; all small files broadcast")
        else:
            print("  -> a shuffle join is present and will dominate runtime")

    assert rows_after == rows_before, "Spark join changed the row count"
    return joined, report


# ---------------------------------------------------------------------------
def compute_parallel(joined, partitions: int):
    """
    Repartition with an explicit bound, then aggregate.

    repartition() is what makes the parallelism bounded and documented rather
    than whatever the framework happens to choose.
    """
    from pyspark.sql import functions as F

    partitioned = joined.repartition(partitions, cfg.PARTITION_KEY)
    result = (
        partitioned
        .groupBy(cfg.PARTITION_KEY)
        .agg(
            F.count(cfg.METRIC_FIELD).alias("txn_count"),
            F.sum(cfg.METRIC_FIELD).alias("score_total"),
            F.avg(cfg.METRIC_FIELD).alias("score_mean"),
        )
    )
    return partitioned, result


# ---------------------------------------------------------------------------
def validate(parallel_pd: pd.DataFrame,
             baseline_pd: pd.DataFrame,
             verbose: bool = True) -> dict:
    """
    Compare parallel output against the sequential baseline.

    Row counts are checked before values. With multi-file joins an incorrect
    join duplicates records without raising an error and still produces
    plausible-looking averages, so a values-only check can pass on data that
    is wrong.
    """
    parallel_pd = parallel_pd.sort_values(cfg.PARTITION_KEY).reset_index(drop=True)
    baseline_pd = baseline_pd.sort_values(cfg.PARTITION_KEY).reset_index(drop=True)

    group_match = len(parallel_pd) == len(baseline_pd)

    merged = parallel_pd.merge(
        baseline_pd, on=cfg.PARTITION_KEY, suffixes=("_par", "_base")
    )
    count_diff = int((merged["txn_count_par"] - merged["txn_count_base"]).abs().max())
    total_diff = float((merged["score_total_par"] -
                         merged["score_total_base"]).abs().max())
    mean_diff = float((merged["score_mean_par"] -
                        merged["score_mean_base"]).abs().max())

    passed = group_match and count_diff == 0 and mean_diff < cfg.TOLERANCE

    report = {
        "parallel_groups": int(len(parallel_pd)),
        "baseline_groups": int(len(baseline_pd)),
        "group_count_match": group_match,
        "max_txn_count_difference": count_diff,
        "max_score_total_difference": total_diff,
        "max_score_mean_difference": mean_diff,
        "tolerance": cfg.TOLERANCE,
        "passed": bool(passed),
    }

    if verbose:
        cfg.banner("CORRECTNESS VALIDATION")
        print(f"  parallel groups          : {report['parallel_groups']}")
        print(f"  baseline groups          : {report['baseline_groups']}")
        print(f"  max txn_count difference : {count_diff}")
        print(f"  max score_total diff     : {total_diff:.6e}")
        print(f"  max score_mean diff      : {mean_diff:.6e}")
        print(f"  tolerance                : {cfg.TOLERANCE:.0e}")
        print(f"\n  {'PASSED' if passed else 'FAILED'}")
        if passed and mean_diff > 0:
            print("  Residual is floating-point summation order: Spark sums each")
            print("  partition independently, then combines. Both are correct to")
            print("  double precision.")

    if not passed:
        raise AssertionError(
            "Correctness check FAILED. Investigate in this order: join keys "
            "and their uniqueness, join type, rows dropped by an inner join, "
            "data types across files, nulls, duplicates, then aggregation "
            "logic. In a multi-file workload the fault is far more often in "
            "the join than in the aggregation."
        )
    return report


# ---------------------------------------------------------------------------
def main() -> int:
    cfg.banner("SESSION 1 - PARALLEL COMPUTE")
    spark = cfg.build_spark()
    try:
        joined, join_report = build_joined(spark)

        cfg.banner(f"PARALLEL AGGREGATION - {cfg.CHOSEN_PARTITIONS} PARTITIONS")
        start = time.perf_counter()
        partitioned, result = compute_parallel(joined, cfg.CHOSEN_PARTITIONS)
        groups = result.count()  # materialise for timing
        elapsed = time.perf_counter() - start
        print(f"  configured partitions : {partitioned.rdd.getNumPartitions()}")
        print(f"  result groups         : {groups}")
        print(f"  execution time        : {elapsed:.4f} s")
        result.orderBy("score_total", ascending=False).show(13, truncate=False)

        # ---------------- correctness ----------------
        parallel_pd = result.toPandas()
        if cfg.OUT_BASELINE.exists():
            baseline_pd = pd.read_csv(cfg.OUT_BASELINE)
        else:
            print("\n  baseline file not found; computing it now")
            from sequential_baseline import run_baseline
            baseline_pd, _ = run_baseline(verbose=False)

        validation = validate(parallel_pd, baseline_pd)

        # ---------------- persist Session 1 output ----------------
        final = parallel_pd.sort_values(cfg.PARTITION_KEY).reset_index(drop=True)
        final.to_parquet(cfg.OUT_FINAL, index=False)
        print(f"\nWrote {cfg.OUT_FINAL} ({len(final)} rows)")

        cfg.OUT_VALIDATION.write_text(json.dumps(
            {"join": join_report,
             "aggregation": {"partitions": cfg.CHOSEN_PARTITIONS,
                              "groups": groups,
                              "seconds": round(elapsed, 4)},
             "validation": validation},
            indent=2))
        print(f"Wrote {cfg.OUT_VALIDATION}")
    finally:
        spark.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
