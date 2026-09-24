# CMA-Flow — Session 3: High-Performance Inter-Service Communication

## Implemented components

This folder implements the Session 3 submission requirements:

- `cma.proto` — readable proto3 contract
- `contracts.py` — typed contract mirror and contract verification
- `wire.py` — JSON and protobuf wire codecs
- `test_wire.py` — byte-for-byte verification against `google.protobuf`
- `transport.py` — transport-independent stubs with in-process, HTTP/JSON, HTTP/protobuf, and optional real gRPC transports
- `service_registry.py` — runtime registry for six logical services
- `services.py` — Customer, Config, Entitlement, Transaction, Revenue, and Charge service logic
- `service_host.py` — HTTP server and optional real grpcio generic server
- `adapters.py` — `PaymentProviderAdapter`, `RestPaymentAdapter`, and `GrpcPaymentAdapter`
- `adapter.py` — adapter benchmark and deadline demonstration
- `benchmark.py` — payload, latency, round-trip/N+1, and streaming benchmarks
- `compose.py` / `reconcile.py` — RevenueService composition and three-way reconciliation
- `run_pipeline.py` / `run_session3.py` — end-to-end runners
- `session3_dashboard.py` — GUI entry point
- `grpc_backend.py` — optional real grpcio server helper

## Setup

Use the same Python environment as the previous sessions and install:

```powershell
python -m pip install -r requirements.txt
```

Set PostgreSQL environment variables if your local setup differs from the defaults:

```powershell
$env:CMA_FLOW_DB_HOST="localhost"
$env:CMA_FLOW_DB_PORT="5432"
$env:CMA_FLOW_DB_NAME="cma_flow_db"
$env:CMA_FLOW_DB_USER="postgres"
$env:CMA_FLOW_DB_PASSWORD="your-password"
```

The password is never written to the report.

## Verify the contract and wire format

```powershell
python contracts.py
python test_wire.py
```

`test_wire.py` builds an equivalent dynamic protobuf descriptor and checks that the hand-written encoder is byte-identical for the selected test messages.

## Run the complete pipeline

```powershell
python run_pipeline.py
```

or:

```powershell
python run_session3.py --stage all
```

Stage-specific examples:

```powershell
python run_session3.py --stage contract
python run_session3.py --stage wire
python run_session3.py --stage latency
python run_session3.py --stage roundtrips
python run_session3.py --stage streaming
python run_session3.py --stage adapter
python run_session3.py --stage deadline
python run_session3.py --stage typed-failure
python run_session3.py --stage compose
python run_session3.py --stage reconcile
```

## Run the GUI

```powershell
python session3_dashboard.py
```

## Optional real gRPC

The project includes a real grpcio backend using generic handlers, so generated `*_pb2.py` files are not required.

```powershell
python grpc_backend.py
```

The gRPC endpoint is `127.0.0.1:53211` and uses the same typed contract and protobuf wire encoder as the transport-independent stub.

## Important interpretation notes

- PostgreSQL is the authoritative Session 3 data source.
- The OULAD score is used as the documented revenue reconciliation proxy; it is not a native monetary field in OULAD.
- `RevenueService` composes `TransactionService` and `CustomerService`; the client does not perform regional-revenue arithmetic.
- `RestPaymentAdapter` and `GrpcPaymentAdapter` implement the same `charge()` seam while hiding protocol details from the caller.
- The deadline demonstration distinguishes a caller deadline from server cancellation. A client timeout does not automatically prove that server work was cancelled.
- Session 1 and Session 2 artifacts must exist in their expected sibling folders for the reconciliation gate to compare all three sessions.
- If `psycopg2` is missing, install `psycopg2-binary` before running database-backed stages.
