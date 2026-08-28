"""
CMA-Flow - PostgreSQL Dataset Importer

Put this file in:
    session1_parallel_compute/database/import_data.py

Project structure:
    session1_parallel_compute/
    ├── database/
    │   └── import_data.py
    └── Datasets/
        ├── assessments.csv
        ├── assessment_defs.csv
        ├── courses.csv
        ├── customers_dim.csv
        ├── entitlements_dim.csv
        ├── oulad_monetization.csv
        ├── studentAssessment.csv
        ├── studentInfo.csv
        ├── studentRegistration.csv
        ├── studentVle.csv
        └── vle.csv

Install:
    pip install pandas psycopg2-binary

Run:
    python database/import_data.py
"""

from __future__ import annotations
from tkinter import ttk, messagebox, filedialog, simpledialog

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "database"))
import db  # noqa: E402

import csv
import getpass
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2 import sql


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "Datasets"


# ---------------------------------------------------------
# PostgreSQL settings
# Change these if necessary.
# The password is requested securely when the program starts.
# ---------------------------------------------------------

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "cma_flow_db"
DB_USER = "postgres"


# ---------------------------------------------------------
# Table-name mapping
# ---------------------------------------------------------

TABLE_NAMES = {
    "assessments.csv": "assessments",
    "assessment_defs.csv": "assessment_defs",
    "courses.csv": "courses",
    "customers_dim.csv": "customers",
    "entitlements_dim.csv": "entitlements",
    "oulad_monetization.csv": "oulad_monetization",
    "studentAssessment.csv": "student_assessment",
    "studentInfo.csv": "student_info",
    "studentRegistration.csv": "student_registration",
    "studentVle.csv": "student_vle",
    "vle.csv": "vle",
}


# ---------------------------------------------------------
# PostgreSQL identifier helpers
# ---------------------------------------------------------

def clean_identifier(name: str) -> str:
    """Convert a CSV column name into a PostgreSQL-safe name."""
    name = str(name).strip().lower()
    name = re.sub(r"[^a-zA-Z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")

    if not name:
        name = "column"

    if name[0].isdigit():
        name = "_" + name

    return name


def unique_columns(columns):
    """Clean column names and make duplicates unique."""
    result = []
    used = {}

    for col in columns:
        base = clean_identifier(col)

        if base not in used:
            used[base] = 1
            result.append(base)
        else:
            used[base] += 1
            result.append(f"{base}_{used[base]}")

    return result


# ---------------------------------------------------------
# Data type detection
# ---------------------------------------------------------

def postgres_type(series: pd.Series) -> str:
    """
    Infer a reasonable PostgreSQL type from a pandas series.

    We intentionally use TEXT for object/string columns because
    OULAD contains mixed identifiers and categorical values.
    """

    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"

    if pd.api.types.is_integer_dtype(dtype):
        return "BIGINT"

    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE PRECISION"

    # Try numeric inference for object columns.
    # Only choose numeric when every non-null value can be converted.
    non_null = series.dropna()

    if len(non_null) > 0:
        numeric = pd.to_numeric(non_null, errors="coerce")

        if numeric.notna().all():
            if (numeric % 1 == 0).all():
                return "BIGINT"
            return "DOUBLE PRECISION"

    return "TEXT"


# ---------------------------------------------------------
# Database creation
# ---------------------------------------------------------

def create_database_if_needed(password: str):
    """
    Create cma_flow_db if it does not already exist.

    PostgreSQL cannot create a database while connected to that
    same database, so this connects to the default 'postgres' DB.
    """

    conn = None

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            user=DB_USER,
            password=password,
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DB_NAME,),
            )

            exists = cur.fetchone() is not None

            if exists:
                print(f"[OK] Database '{DB_NAME}' already exists.")
            else:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(DB_NAME)
                    )
                )
                print(f"[OK] Created database '{DB_NAME}'.")

    except psycopg2.Error as exc:
        print("\n[ERROR] Could not create/check the PostgreSQL database.")
        print(exc)
        raise

    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------
# Create table
# ---------------------------------------------------------

def create_table(conn, table_name: str, dataframe: pd.DataFrame):
    columns = []

    for column in dataframe.columns:
        columns.append(
            sql.SQL("{} {}").format(
                sql.Identifier(column),
                sql.SQL(postgres_type(dataframe[column])),
            )
        )

    statement = sql.SQL(
        "CREATE TABLE IF NOT EXISTS {} ({})"
    ).format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(columns),
    )

    with conn.cursor() as cur:
        cur.execute(statement)

    conn.commit()


# ---------------------------------------------------------
# Truncate table
# ---------------------------------------------------------

def clear_table(conn, table_name: str):
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE TABLE {}").format(
                sql.Identifier(table_name)
            )
        )

    conn.commit()


# ---------------------------------------------------------
# Insert CSV using PostgreSQL COPY
# ---------------------------------------------------------

def import_csv(conn, csv_path: Path, table_name: str):
    print()
    print("=" * 72)
    print(f"IMPORTING: {csv_path.name}")
    print(f"TABLE:     {table_name}")
    print("=" * 72)

    sample = pd.read_csv(csv_path, nrows=1000, low_memory=False)
    sample.columns = unique_columns(sample.columns)

    print(f"Columns: {len(sample.columns)}")
    print("Creating table...")

    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
        )
    conn.commit()

    create_table(conn, table_name, sample)

    # NEW: remember the PG type chosen for each column so we can format
    # values to match it (avoids "-159.0" being sent to a BIGINT column).
    column_types = {col: postgres_type(sample[col]) for col in sample.columns}

    columns_sql = sql.SQL(", ").join(
        sql.Identifier(column) for column in sample.columns
    )

    copy_sql = sql.SQL(
        "COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER FALSE, NULL '\\N')"
    ).format(sql.Identifier(table_name), columns_sql)

    total_rows = 0
    chunk_size = 10000

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
        chunk.columns = unique_columns(chunk.columns)
        pg_types = [column_types[col] for col in chunk.columns]

        buffer = StringIO()
        writer = csv.writer(
            buffer,
            delimiter=",",
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )

        for row in chunk.itertuples(index=False, name=None):
            cleaned = []
            for value, pg_type in zip(row, pg_types):
                if pd.isna(value):
                    cleaned.append(r"\N")
                elif pg_type == "BIGINT":
                    # value may arrive as a float (e.g. -159.0) because
                    # pandas upcasts int columns containing NaN to float64.
                    cleaned.append(str(int(round(float(value)))))
                else:
                    cleaned.append(str(value))
            writer.writerow(cleaned)

        buffer.seek(0)

        with conn.cursor() as cur:
            cur.copy_expert(copy_sql.as_string(conn), buffer)

        conn.commit()
        total_rows += len(chunk)
        print(f"  Imported {total_rows:,} rows...", end="\r")

    print(f"  Imported {total_rows:,} rows.        ")
    return total_rows

# ---------------------------------------------------------
# Show imported tables
# ---------------------------------------------------------

def show_database_summary(conn):
    print()
    print("=" * 72)
    print("DATABASE SUMMARY")
    print("=" * 72)

    for table_name in TABLE_NAMES.values():
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}").format(
                    sql.Identifier(table_name)
                )
            )
            count = cur.fetchone()[0]

        print(f"{table_name:<25} {count:>12,} rows")

    print("=" * 72)


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    print("=" * 72)
    print("CMA-FLOW SESSION 1")
    print("POSTGRESQL DATA IMPORTER")
    print("=" * 72)

    print(f"\nProject folder : {PROJECT_ROOT}")
    print(f"Dataset folder : {DATASET_DIR}")
    print(f"Database       : {DB_NAME}")
    print(f"Host           : {DB_HOST}:{DB_PORT}")
    print(f"User           : {DB_USER}")

    if not DATASET_DIR.exists():
        print("\n[ERROR] Datasets folder was not found:")
        print(DATASET_DIR)
        return

    password = getpass.getpass("\nPostgreSQL password: ")

    # Check/create database.
    create_database_if_needed(password)

    print("\nConnecting to CMA-Flow database...")

    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=password,
    )

    print("[OK] Connected to PostgreSQL.")

    try:
        imported = 0

        for filename, table_name in TABLE_NAMES.items():
            csv_path = DATASET_DIR / filename

            if not csv_path.exists():
                print(f"\n[WARNING] Missing file: {csv_path}")
                continue

            import_csv(conn, csv_path, table_name)
            imported += 1

        show_database_summary(conn)

        print()
        print(f"[SUCCESS] Imported {imported} dataset(s).")
        print()
        print("Your PostgreSQL database is now ready for the GUI.")
        print()
        print("Example query:")
        print("  SELECT * FROM student_assessment LIMIT 10;")
        print()
        print("Example row count:")
        print("  SELECT COUNT(*) FROM student_assessment;")

    except Exception as exc:
        conn.rollback()
        print("\n[ERROR] Import failed:")
        print(exc)
        raise

    finally:
        conn.close()
        print("\n[OK] PostgreSQL connection closed.")


if __name__ == "__main__":
    main()
