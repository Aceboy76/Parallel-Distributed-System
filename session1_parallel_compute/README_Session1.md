# CMA-Flow — Session 1: Foundations in In-Memory Cluster Compute

**Course:** MIT 261 – Parallel and Distributed Systems
**Project:** CMA-Flow
**Session:** 1 – Foundations in In-Memory Cluster Compute
**Dataset:** OULAD (Open University Learning Analytics Dataset), reframed as a customer-monetization workload

## Overview

Session 1 implements and evaluates a small parallel data-processing workload using **Python, pandas, PySpark, and Spark local mode**.

The session establishes the foundation for the CMA-Flow capstone by:

- preparing the raw OULAD files into the Event/Entity/Entity/Lookup shape the pipeline requires;
- profiling and validating the input dataset;
- building and reconciling the join path;
- selecting a partition key from measured data characteristics;
- producing a sequential pandas baseline;
- implementing the same workload in PySpark;
- validating the Spark result against the baseline;
- benchmarking different Spark partition counts;
- measuring skew at both the key and physical Spark-partition levels; and
- generating the entity-model and architecture diagrams.

The implementation follows a **single-source-of-truth configuration** in `config.py`, so dataset paths, keys, metrics, partition settings, and other shared settings are defined centrally.

---

## Business Framing: OULAD as a Monetization Proxy

CMA-Flow's business narrative is customer monetization — customers, entitlements, priced transactions, and revenue. OULAD does not contain a monetization table directly, so this project maps the *shape* of a monetization workload onto the *substance* of OULAD's learning-analytics data:

| Monetization concept | OULAD equivalent |
|---|---|
| Customer | Student (`studentInfo.csv`, deduplicated to `customers_dim.csv`) |
| Entitlement (access/subscription) | Module registration (`studentRegistration.csv`, deduplicated to `entitlements_dim.csv`) |
| Priced transaction / usage event | Assessment submission (`studentAssessment.csv`) |
| Transaction config / pricing tier | Assessment definition (`assessments.csv` → `assessment_defs.csv`) |
| Revenue (proxy metric) | Assessment `score` |

`docs/oulad_monetization_flow.png` documents the underlying business logic this framing is built on: a student enrolls and effectively "pays" via `studied_credits`; their engagement and assessment activity (`student_vle`, `student_assessment`) feeds a classification model predicting `final_result`; a **Distinction** or **Pass** outcome secures revenue (with an upsell opportunity on Distinction); a **Fail** generates a repeat/resit fee (additional revenue); a predicted **Withdrawn** triggers an early-intervention/tutor-outreach step that either converts the student back to Pass (revenue saved) or the student withdraws (revenue lost); successful outcomes feed back into re-enrollment for the next module presentation.

This is why `score` — not a literal currency field — is used as `METRIC_FIELD`: it is the measurable signal this narrative's revenue outcomes are actually contingent on. This substitution is stated explicitly here so the metric's meaning is never ambiguous in the rest of this document.

`docs/oulad_erd.png` shows the full raw OULAD schema for reference; Session 1 uses only four of its tables (`studentInfo`, `studentRegistration`, `studentAssessment`, `assessments`) after the preparation step below.

---

## Dataset

Raw OULAD does not ship files in the Event/Entity/Entity/Lookup shape this pipeline needs, and two of the raw tables are at the wrong grain to serve as parent entities in a `many_to_one` join (`studentInfo.csv` and `studentRegistration.csv` are one row per **student per module presentation**, not one row per student). `prep_oulad.py` is therefore a required one-time step, run before `profile_files.py`, that builds the three derived files below from the raw source data.

| File | Role | Rows | Built from |
|---|---|---:|---|
| `studentAssessment.csv` | Event | 173,912 | used as-is (already submission-grain) |
| `customers_dim.csv` | Entity | 28,785 | `studentInfo.csv`, deduplicated to one row per `id_student` |
| `entitlements_dim.csv` | Entity | 28,785 | `studentRegistration.csv`, deduplicated to one row per `id_student` |
| `assessment_defs.csv` | Lookup | 206 | `assessments.csv`, columns renamed for a self-contained lookup |

The lookup table is intentionally excluded from the three-file Event/Entity minimum used for dataset eligibility.

Two dedup decisions in `prep_oulad.py` are documented rather than silently assumed:

- `age_band` is **dropped** from `customers_dim.csv` — it is the one demographic field that actually differs across a student's module presentations (72 students affected), so a "first row wins" rule would have picked an arbitrary value for them. Every other retained field (`gender`, `region`, `highest_education`, `imd_band`, `disability`) was confirmed stable per student before being kept.
- `date_registration`/`date_unregistration` in `entitlements_dim.csv` reflect only each student's **first** module presentation — these genuinely vary by presentation for roughly 2,800–2,900 students, so this is a real modelling limitation, not a data-quality bug.

The main join path reconciles:

**173,912 rows before join → 173,912 rows after join** (Δ = 0)

The resulting working dataset contains **15 columns** (5 from `studentAssessment` + 4 from `customers_dim` + 4 from `assessment_defs` + 2 unique from `entitlements_dim`).

---

## Project Structure

```text
session1_parallel_compute/
│
├── Datasets/
│   ├── studentInfo.csv              (raw)
│   ├── studentRegistration.csv      (raw)
│   ├── assessments.csv              (raw)
│   ├── studentAssessment.csv        (raw, used as-is for the Event role)
│   ├── customers_dim.csv            (built by prep_oulad.py)
│   ├── entitlements_dim.csv         (built by prep_oulad.py)
│   └── assessment_defs.csv          (built by prep_oulad.py)
│
├── results/
│   ├── prep_report.json
│   ├── file_profile.json
│   ├── working_dataset.parquet
│   ├── partition_strategy.json
│   ├── baseline_result.csv
│   ├── regional_score_summary.parquet
│   ├── validation_report.json
│   ├── session1_benchmark.csv
│   └── partition_sizes.csv
│
├── docs/
│   ├── entity-model-session1.png
│   ├── oulad_erd.png
│   └── oulad_monetization_flow.png
│
├── architecture/
│   └── architecture-session1.png
│
├── config.py
├── prep_oulad.py
├── profile_files.py
├── load_and_join.py
├── partition_strategy.py
├── sequential_baseline.py
├── parallel_compute.py
├── benchmark.py
├── partition_analysis.py
├── render_diagrams.py
└── README_Session1.md
```

---

## Requirements

### Software

- Python 3.10+
- JDK 17 or 21 (Spark 4.2.0 deprecates Java 25 builds prior to 25.0.3 — if your system Java is a very new release, install JDK 17 alongside it and set `JAVA_HOME` for this project rather than replacing your system default)
- PySpark 4.2.0
- pandas
- PyArrow
- Graphviz

### Python packages

Install the required packages with:

```bash
pip install pandas pyspark pyarrow
```

Install into the **same Python interpreter** that will run the scripts — on systems with multiple Python installs, `pip install X` and `python script.py` can silently resolve to different interpreters. If a script reports `ModuleNotFoundError` despite installation, reinstall explicitly against that interpreter:

```bash
<path-to-python.exe> -m pip install pandas pyspark pyarrow
```

### Windows-specific note: PySpark worker resolution

On Windows, letting Spark resolve a bare `python` command for its worker processes can hit the Microsoft Store "App Execution Alias" stub instead of the real interpreter, which fails RDD-level operations (`.map()`, `.glom()`, etc. — used in `partition_analysis.py`) with a socket timeout, even though DataFrame-only operations work fine. `config.py`'s `build_spark()` avoids this by pointing Spark explicitly at `sys.executable` (the exact interpreter running the script) via `spark.pyspark.python` / `spark.pyspark.driver.python`, so no environment variable needs to be set manually.

### Graphviz

Graphviz is required by `render_diagrams.py` because the diagrams are rendered through the `dot` executable.

Verify the installation with:

```bash
dot -V
```

A successful installation should print the installed Graphviz version.

---

## Configuration

All shared settings are defined in:

```text
config.py
```

Important configuration includes:

- dataset location (`DATA_DIR`);
- input file names and roles (`FILES`);
- customer join key (`CUSTOMER_KEY = "id_student"`);
- configuration join key (`CONFIG_KEY = "id_assessment"`);
- selected partition key (`PARTITION_KEY = "region"`);
- metric field (`METRIC_FIELD = "score"`);
- Spark settings;
- partition-count settings;
- benchmark repeat counts; and
- output locations.

The design intentionally keeps these values in one place so that changing a configuration value does not require duplicating it across multiple scripts.

---

# Session 1 Pipeline

Run the scripts in the following order.

## Part 1 — Data Preparation (one-time, before profiling)

```bash
python prep_oulad.py
```

Builds `customers_dim.csv`, `entitlements_dim.csv`, and `assessment_defs.csv` from the raw OULAD files, deduplicating the two student-per-presentation files down to one row per `id_student`. Confirms both Entity files cover an identical student population (28,785 students) before anything downstream relies on that.

Output:

```text
results/prep_report.json
```

---

## Part 2–3 — Dataset Profiling

```bash
python profile_files.py
```

This profiles every input file and checks:

- row counts;
- columns;
- data types;
- candidate primary keys;
- referential integrity; and
- dataset eligibility.

Measured results:

- **Condition 1 (≥3 qualifying files):** MET — 3 Event/Entity files (`assessments`, `customers`, `entitlements`)
- **Condition 2 (genuine one-to-many):** MET — `customers` 1..* `assessments` on `id_student`, min 1 / median 7 / max 28 submissions per student. `entitlements_dim.id_student` is unique, so Entitlement is a 1:1 extension of Customer, not a second one-to-many association.
- **Condition 3 (usable event-time field):** MET — `date_submitted` is an integer day-offset from the module start (−11 to 608 days), not a calendar timestamp; a small number of negative values reflect early or banked submissions.
- **Condition 4 (volume ≥ 50,000):** MET — 173,912 event rows.
- **Referential integrity:** 0 orphans across all three foreign-key checks.

Note for the file inventory: `studentAssessment.csv` has **no candidate primary key** — neither `id_student` nor `id_assessment` alone is unique, since the file is the many-to-many junction between students and assessments, and it has no surrogate submission-id column.

Output:

```text
results/file_profile.json
```

---

## Part 4 — Load and Join

```bash
python load_and_join.py
```

This builds the working dataset using the explicit join path and verifies row-count reconciliation.

Join path (all inner, all many-to-one):

```text
studentAssessment
  |> customers_dim        on id_student
  |> assessment_defs      on id_assessment
  |> entitlements_dim     on id_student
```

Expected reconciliation:

```text
173,912 rows before join
173,912 rows after join
15 columns after join
```

No column renaming or suffixing is needed — `customers_dim.csv`, `entitlements_dim.csv`, and `assessment_defs.csv` already use their real key names (`id_student`, `id_assessment`) and share no other column names with each other.

Output:

```text
results/working_dataset.parquet
```

Entity-relationship diagram (Part 4 deliverable): `docs/entity-model-session1.png`, generated by `render_diagrams.py`.

---

## Part 5 — Partition Strategy

```bash
python partition_strategy.py
```

This evaluates candidate partition keys using measured cardinality and distribution.

The selected partition key is:

```text
region
```

There are:

```text
13 distinct region values
```

The measured records-per-region distribution is:

```text
minimum: 7,341
median:  13,049
maximum: 18,263
```

Key-level skew:

```text
2.49 : 1
```

`id_student` was **not** rejected for being uniform — it is actually skewed 28:1 (min 1, median 7, max 28 submissions per student). It was rejected because it is an **event identifier, not a business grouping attribute** — with 23,369 distinct values relative to a 173,912-row dataset, partitioning on it would produce far too many, far-too-small partitions to be a sensible workload dimension.

Also of note: `date_registration` and `date_submitted` showed far higher skew (2,937.5:1 and 2,747.0:1 respectively) than `region`. These were not chosen despite the more dramatic skew, because they are per-record date artifacts rather than a business dimension anyone would query revenue by — the same trade-off the course's own worked example makes between a business-meaningful key and a maximally skewed one.

Output:

```text
results/partition_strategy.json
```

---

## Part 6 — Sequential Baseline

```bash
python sequential_baseline.py
```

The baseline uses pandas and performs the same joined workload and aggregation as the Spark implementation: submission count, total score, and mean score per `region`.

The baseline provides:

1. a correctness reference; and
2. the denominator for the performance comparison.

Output:

```text
results/baseline_result.csv
```

A representative run reports:

```text
median: ~0.008–0.03 s (varies by machine)
groups: 13
total score across 13 regions: 13,169,342.00
```

Exact timings vary meaningfully by hardware — this pipeline was verified across two different machines with medians ranging from 0.0080 s to 0.0312 s, while every non-timing figure (group count, per-region totals, grand total) matched exactly across both. Report the median from your own run, not the figures above.

---

## Parts 7 and 9 — Parallel Compute and Correctness

```bash
python parallel_compute.py
```

The Spark implementation:

1. reads the source files;
2. performs broadcast joins for the small customer, entitlement, and assessment-definition tables;
3. explicitly repartitions by `region`;
4. performs the regional aggregation;
5. inspects the physical plan; and
6. compares the result against the pandas baseline.

The expected physical plan uses:

```text
BroadcastHashJoin  (6 nodes — 2 per join × 3 joins)
```

and avoids:

```text
SortMergeJoin  (0 nodes)
```

The configured parallelism for the main implementation is:

```text
4 partitions
```

Output:

```text
results/regional_score_summary.parquet
results/validation_report.json
```

The result should contain:

```text
13 groups
```

and the validation should pass with an **exact** match (0.0 difference) on `txn_count`, `score_total`, and `score_mean` against the pandas baseline — confirmed on both machines this pipeline was verified against.

---

## Part 8 — Benchmark

```bash
python benchmark.py
```

The benchmark compares:

- sequential pandas;
- Spark with 2 partitions;
- Spark with 4 partitions;
- Spark with 8 partitions.

A representative run produced:

| Condition | Partitions | Median |
|---|---:|---:|
| Sequential baseline | — | 0.0081–0.0312 s |
| Parallel A | 2 | 0.48–0.56 s |
| Parallel B | 4 | 0.47–0.50 s |
| Parallel C | 8 | 0.59–0.69 s |

The 4-partition Spark configuration was the fastest Spark setting in every run of this pipeline.

However, even the fastest Spark configuration was substantially slower than the pandas baseline — by roughly 15× to 62× depending on hardware. The result demonstrates that parallelism is not automatically beneficial for a relatively small, in-memory workload. The group-count invariant (13 groups on every condition, including the baseline) was verified before any timing was reported, ruling out a fast-but-wrong result.

Output:

```text
results/session1_benchmark.csv
```

### Important timing note

`parallel_compute.py` reports a single cold Spark execution, while `benchmark.py` reports repeated warm-session timings using the median. These measurements answer different questions and should not be treated as contradictory.

---

## Part 10 — Partition Analysis

```bash
python partition_analysis.py
```

This measures skew at two levels:

### Key level

Records per distinct `region` value. This is the level predicted by the entity model.

```text
skew ratio = 2.49 : 1  (fixed, independent of partition count)
```

### Physical Spark partition level

Records per actual Spark partition after repartitioning. This is the level that affects task workload and execution time.

```text
n=2:  skew ≈ 1.83 : 1
n=4:  skew ≈ 2.91 : 1
n=8:  skew ≈ 6.00 : 1
```

The analysis demonstrates that key-level skew and physical-partition skew are **not the same thing**, and — counter to intuition — physical skew **worsens** as partition count increases. With only 13 regions, each additional partition holds fewer regions, so an unlucky pairing of two heavy regions into one hash bucket is no longer diluted by the others. At 8 partitions, the heaviest bucket held roughly 2× the even share, which directly explains why 8 partitions was the *worst* setting in Part 8: more parallelism was theoretically available, but the straggler partition bounded the job regardless.

Output:

```text
results/partition_sizes.csv
```

---

## Part 11 — Architecture Diagrams

```bash
python render_diagrams.py
```

This requires Graphviz. Paths are read from `config.py`'s `DOCS_DIR`/`ARCH_DIR`, keeping this script consistent with the single-source-of-truth principle every other script in the pipeline follows.

It generates:

```text
docs/entity-model-session1.png
architecture/architecture-session1.png
```

The diagrams document:

- the Customer–Assessment(Transaction)–Entitlement–AssessmentDef(Config) entity relationships, using the real OULAD-derived table and column names;
- key and foreign-key relationships, including the corrected reasoning for why `id_student` is rejected as a partition key (identifier role, not uniformity);
- partition-key semantics with the actual measured 2.49:1 skew;
- the full source-to-ingestion-to-compute flow, including the `prep_oulad.py` step absent from the original template;
- broadcast joins;
- bounded Spark parallelism;
- validation; and
- Session 1 outputs.

`docs/oulad_erd.png` and `docs/oulad_monetization_flow.png` are supplementary, hand-authored diagrams (not generated by `render_diagrams.py`) documenting the raw OULAD schema and the monetization business narrative respectively — see the Business Framing section above.

---

# Complete Execution Order

From the `session1_parallel_compute` directory:

```bash
python prep_oulad.py
python profile_files.py
python load_and_join.py
python partition_strategy.py
python sequential_baseline.py
python parallel_compute.py
python benchmark.py
python partition_analysis.py
python render_diagrams.py
```

The order matters in two places. `prep_oulad.py` must run before `profile_files.py`, or `customers_dim.csv`/`entitlements_dim.csv`/`assessment_defs.csv` will not exist yet. `sequential_baseline.py` should run before `parallel_compute.py`, since the latter compares against the saved baseline; if it has not been generated, `parallel_compute.py` computes it automatically, but the dedicated Part 6 timing will not have been produced separately.

---

# Key Findings

## 1. Parallelism was slower for this workload

The pandas baseline completed in roughly **0.008–0.03 s** depending on machine. The fastest Spark condition (4 partitions) took roughly **0.47–0.50 s**.

Therefore, the Spark implementation was roughly **15× to 62× slower** than the sequential baseline, depending on hardware.

This is not treated as a failure. It is a measured result demonstrating the overhead of Spark for a workload — 173,912 rows — that is small enough to fit comfortably in memory. The overhead includes JVM startup, task scheduling, serialization, Spark execution overhead, and the Python/JVM boundary.

## 2. Four Spark partitions were the best tested setting

The benchmark tested 2, 4, and 8 partitions. Four partitions were fastest on every machine this pipeline was run on; eight partitions was consistently the *worst* — a result directly explained by Part 10's finding that physical-partition skew worsens as partition count increases with only 13 distinct region values.

## 3. `region` is the selected partition key

`region` was selected because it provides a meaningful, business-relevant distribution across the dataset: 13 distinct values, skew 2.49:1. `id_student` was rejected — not because it is uniform (it is not; it is skewed 28:1) but because it is an event identifier with too many distinct values (23,369) relative to the dataset size to serve as a partitioning dimension. Two date-based columns showed far higher skew than `region` but were rejected as artifacts rather than meaningful business dimensions.

## 4. Key-level skew does not completely describe Spark workload skew

Hash partitioning can combine multiple region keys into the same physical partition. With only 13 keys, this effect is pronounced: physical skew climbed from 1.83:1 (2 partitions) to 6.00:1 (8 partitions) even though the underlying key-level skew never changed. This matters because the slowest task determines elapsed execution time — which is exactly why more partitions did not mean better performance in Part 8.

## 5. Broadcast joins avoid unnecessary large-table shuffles

The customer, entitlement, and assessment-definition tables are small relative to the 173,912 assessment-submission rows. The Spark implementation therefore uses broadcast joins. The physical plan shows 6 `BroadcastHashJoin` nodes and 0 `SortMergeJoin` nodes, confirming no shuffle is introduced by the join itself — differences between partition-count conditions in Part 8 are scheduling overhead, not shuffle cost.

---

# Outputs Checklist

Before considering Session 1 complete, verify that these outputs exist:

```text
[ ] results/prep_report.json
[ ] results/file_profile.json
[ ] results/working_dataset.parquet
[ ] results/partition_strategy.json
[ ] results/baseline_result.csv
[ ] results/regional_score_summary.parquet
[ ] results/validation_report.json
[ ] results/session1_benchmark.csv
[ ] results/partition_sizes.csv
[ ] docs/entity-model-session1.png
[ ] architecture/architecture-session1.png
```

---

# Concepts Demonstrated

Session 1 demonstrates the following parallel and distributed systems concepts:

- **Broadcast join**
- **Bounded parallelism**
- **Caching**
- **Candidate key detection**
- **Cardinality**
- **Controlled experiment**
- **Data skew**
- **Determinism**
- **Hash partitioning**
- **Invariant checking**
- **Lazy evaluation**
- **Median-based benchmarking**
- **Physical plan inspection**
- **Referential integrity**
- **Reconciliation**
- **Shuffle**
- **Split-apply-combine**
- **Straggler effect**
- **Tolerance-based comparison**
- **Warm-up effects**
- **Single source of truth**
- **Diagrams as code**
- **Data preparation as an explicit, documented step** (dedup rules, dropped-field justification)

---

# Reproducibility

The pipeline is designed to be reproducible by:

- centralizing configuration;
- documenting every data-preparation decision (deduplication rules, dropped fields) rather than making them implicitly;
- explicitly setting partition counts;
- using deterministic aggregations;
- repeating benchmark runs;
- reporting medians;
- persisting the baseline result;
- validating Spark results against the baseline;
- pointing Spark at the exact running Python interpreter (`sys.executable`) rather than relying on PATH resolution, which is what makes the pipeline portable across the Windows/Linux environments it was verified on; and
- writing machine-readable output files.

Every non-timing result in this document (row counts, group counts, skew ratios, correctness deltas) was verified identical across two different machines running this pipeline. Only wall-clock timings varied, as expected.

---

# Session 1 Conclusion

Session 1 establishes a complete in-memory parallel-compute pipeline from raw-data preparation, through dataset profiling, Spark execution, benchmarking, skew analysis, correctness validation, and architecture documentation — applied to OULAD reframed as a customer-monetization workload.

The central performance finding is that **Spark parallelism did not outperform pandas for this 173,912-row workload**. The experiment nevertheless demonstrates the mechanics and trade-offs of partitioned parallel computation, including broadcast joins, bounded parallelism, correctness validation, benchmark design, and — notably — physical partition skew that *worsens* with more partitions when the partition key has relatively few distinct values (13 regions).

The result should therefore be interpreted as a **valid negative performance result**, not as evidence that parallel processing is inherently slower. The workload is simply below the scale, and the partition key has too little cardinality, for Spark's distributed execution overhead to be justified.