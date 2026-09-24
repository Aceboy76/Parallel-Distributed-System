from __future__ import annotations
import os
from pathlib import Path

SESSION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SESSION_DIR.parent
SESSION1_DIR = PROJECT_ROOT / 'session1_parallel_compute'
DATA_DIR = SESSION1_DIR / 'Datasets'
RESULTS_DIR = SESSION_DIR / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DB_HOST = os.getenv('CMA_FLOW_DB_HOST', 'localhost')
DB_PORT = int(os.getenv('CMA_FLOW_DB_PORT', '5432'))
DB_NAME = os.getenv('CMA_FLOW_DB_NAME', 'cma_flow_db')
DB_USER = os.getenv('CMA_FLOW_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('CMA_FLOW_DB_PASSWORD', '')

PARTITIONS = 4
TOLERANCE = 1e-6
PASS_SCORE = 40.0
UPSELL_SCORE = 80.0
DEFAULT_BENCHMARK_CALLS = 300
DEFAULT_ROUND_TRIP_ROWS = 50
DEFAULT_STREAM_ROWS = 5000

OUT_CONTRACT = RESULTS_DIR / 'contract_report.json'
OUT_PAYLOAD = RESULTS_DIR / 'payload_sizes.csv'
OUT_LATENCY = RESULTS_DIR / 'latency_benchmark.csv'
OUT_ROUNDTRIP = RESULTS_DIR / 'roundtrip_benchmark.csv'
OUT_STREAMING = RESULTS_DIR / 'streaming_benchmark.csv'
OUT_ADAPTER = RESULTS_DIR / 'adapter_comparison.csv'
OUT_DEADLINE = RESULTS_DIR / 'deadline_demo.json'
OUT_COMPOSE = RESULTS_DIR / 'service_regional_revenue.csv'
OUT_RECON = RESULTS_DIR / 'reconciliation_report.json'
OUT_SUMMARY = RESULTS_DIR / 'session3_summary.json'
OUT_SCHEMA = RESULTS_DIR / 'event_schema.json'

ARTIFACTS = [OUT_CONTRACT, OUT_PAYLOAD, OUT_LATENCY, OUT_ROUNDTRIP, OUT_STREAMING,
             OUT_ADAPTER, OUT_DEADLINE, OUT_COMPOSE, OUT_RECON, OUT_SUMMARY, OUT_SCHEMA]


def banner(title: str):
    print('\n' + '=' * 76)
    print(title)
    print('=' * 76)
