"""
Shared configuration for MIT 261 Session 1 - CMA-Flow parallel compute.

Every script in this folder imports from here so that the dataset paths,
partition key, metric field, and benchmark settings are defined exactly
once. Changing a value here changes it for the baseline, the parallel
implementation, the benchmark, and the partition analysis together, which
is what keeps the benchmark conditions comparable.

Dataset : OULAD (Open University Learning Analytics Dataset)

Author  : <student name>
Course  : MIT 261 - Parallel and Distributed Systems
Session : 1 - Foundations in In-Memory Cluster Compute

IMPORTANT: run prep_oulad.py once before profile_files.py. It builds
customers_dim.csv, entitlements_dim.csv, and assessment_defs.csv from the
raw OULAD files - the four files below are what prep_oulad.py produces,
not the raw Kaggle download.
"""
import os
import sys
from pathlib import Path

os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
SESSION_DIR = REPO_ROOT
DATA_DIR = SESSION_DIR / "Datasets"
RESULTS_DIR = SESSION_DIR / "results"
DOCS_DIR = REPO_ROOT / "docs"
ARCH_DIR = REPO_ROOT / "architecture"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Input files
# ---------------------------------------------------------------------------
# Role classification follows the Session 1 activity sheet:
#   Event    - transactional or time-stamped records
#   Entity   - master or dimension data
#   Lookup   - small reference tables (do NOT count towards the 3-file minimum)
#
# studentAssessment.csv is the genuine one-to-many child: one row per
# submission, many submissions per student. It plays the role
# "transactions.csv" played in the original template.
#
# customers_dim.csv and entitlements_dim.csv are built by prep_oulad.py from
# studentInfo.csv and studentRegistration.csv respectively, deduplicated to
# one row per id_student (both files are one row per student PER MODULE
# PRESENTATION in their raw form, which is not the grain a many_to_one join
# requires).
FILES = {
    "assessments": {
        "file": "studentAssessment.csv",
        "role": "Event",
    },
    "customers": {
        "file": "customers_dim.csv",
        "role": "Entity",
    },
    "entitlements": {
        "file": "entitlements_dim.csv",
        "role": "Entity",
    },
    "assessment_configs": {
        "file": "assessment_defs.csv",
        "role": "Lookup",
    },
}


def path_for(name: str) -> Path:
    """Absolute path of one of the input files."""
    return DATA_DIR / FILES[name]["file"]


# ---------------------------------------------------------------------------
# Workload definition
# ---------------------------------------------------------------------------
# region lives in customers_dim.csv, not in studentAssessment.csv directly -
# it is pulled in via the join on id_student (see CUSTOMER_KEY below).
# region is chosen over id_student because id_student is close to uniform
# relative to submission volume, which leaves the skew analysis in
# partition_analysis.py with more to observe under region.
PARTITION_KEY = "region"
METRIC_FIELD = "score"
EVENT_TIME_FIELD = "date_submitted"

# Join keys - both single-column, verified against the raw files to resolve
# with zero orphans (see prep_oulad.py and profile_files.py output).
CUSTOMER_KEY = "id_student"
CONFIG_KEY = "id_assessment"


# ---------------------------------------------------------------------------
# Benchmark settings
# ---------------------------------------------------------------------------
PARTITION_SETTINGS = (2, 4, 8)  # bounded parallelism conditions to compare
BENCHMARK_REPEATS = 3           # runs per condition; median is reported
BASELINE_REPEATS = 5

CHOSEN_PARTITIONS = 4            # best setting, used for the final output

# Numeric tolerance for the correctness check. Spark sums each partition
# independently and then combines, so the addition order differs from pandas
# and tiny floating-point residuals are expected and acceptable.
TOLERANCE = 1e-6


# ---------------------------------------------------------------------------
# Spark settings
# ---------------------------------------------------------------------------
SPARK_APP_NAME = "MIT261-Session1-CMA-Flow"
SPARK_MASTER = "local[*]"
SPARK_DRIVER_MEMORY = "2g"
SPARK_SHUFFLE_PARTITIONS = "8"

# Files small enough to broadcast to every worker rather than shuffle.
# customers_dim = 28,785 rows, entitlements_dim = 28,785 rows,
# assessment_defs = 206 rows.
BROADCAST_FILES = ("customers", "entitlements", "assessment_configs")


# ---------------------------------------------------------------------------
# Output artifacts
# ---------------------------------------------------------------------------
OUT_PROFILE = RESULTS_DIR / "file_profile.json"
OUT_JOINED = RESULTS_DIR / "working_dataset.parquet"
OUT_BASELINE = RESULTS_DIR / "baseline_result.csv"
OUT_BENCHMARK = RESULTS_DIR / "session1_benchmark.csv"
OUT_PARTITIONS = RESULTS_DIR / "partition_sizes.csv"
OUT_FINAL = RESULTS_DIR / "regional_score_summary.parquet"
OUT_VALIDATION = RESULTS_DIR / "validation_report.json"


def build_spark():
    """Create the SparkSession used by every parallel script."""
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder
        .appName(SPARK_APP_NAME)
        .master(SPARK_MASTER)
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .config("spark.sql.shuffle.partitions", SPARK_SHUFFLE_PARTITIONS)
        .config("spark.pyspark.python", sys.executable)
        .config("spark.pyspark.driver.python", sys.executable)
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("ERROR")
    return spark

def banner(title: str) -> None:
    """Consistent section heading for console output."""
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)