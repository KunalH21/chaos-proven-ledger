# chaos-ledger

A small, production-style financial ledger API built to demonstrate stateful system resilience, transactional correctness, and platform automation under chaos conditions. The app is intentionally simple to operate, but the design focuses on the engineering story behind it: safe releases, database correctness, controlled failure testing, and operational evidence.

This repository is the application piece of a larger platform story. The Kubernetes, GitOps, PostgreSQL HA, rollout automation, and chaos tooling live outside this codebase and are intentionally not the focus here.

## What this project is

`chaos-ledger` is a money-transfer service that enforces a few strict invariants:

- Double-entry accounting using integer cents only
- Deterministic lock ordering to avoid deadlocks during concurrent transfers
- Idempotent transfer processing with PostgreSQL-backed `Idempotency-Key` tracking
- Simple health probes for liveness and readiness
- Prometheus metrics for deployment and canary analysis

The service is designed to prove that a bad release can be detected early, that stateful systems can survive failure, and that the underlying data remains internally consistent.

## Why this project exists

This project is a portfolio/engineering demo for DevOps and Platform Engineering work. It combines:

- application correctness
- database safety
- operational observability
- chaos-triggered failure simulation
- release validation concepts

The core idea is not to build a full banking system. The goal is to demonstrate a stateful platform that can be safely operated in a real Kubernetes environment with automated validation, rollback capability, and evidence of correctness.

## Architecture summary

At a high level:

- FastAPI exposes the ledger API
- PostgreSQL stores accounts, transfers, and ledger entries
- SQLAlchemy handles async database access
- Alembic manages schema migrations
- Prometheus metrics provide observability
- a simple reconciliation script validates accounting invariants

This repo intentionally stays focused on the application contract and data correctness while leaving the infrastructure layer to platform engineering workflows such as Kubernetes manifests, GitOps, and automated rollout controls.

## Repository layout

```text
chaos-ledger/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── db.py
│       ├── main.py
│       ├── middleware.py
│       ├── models.py
│       ├── schemas.py
│       └── services.py
├── scripts/
│   └── reconcile.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_idempotency.py
│   └── test_transfers.py
├── README.md
└── .gitignore
```

## Quick start

### 1) Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -U pip
pip install -e .[dev]
```

### 3) Start PostgreSQL

Use any PostgreSQL instance you prefer. The default connection string is:

```bash
postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_db
```

You can run a local containerized database with:

```bash
docker run --name chaos-ledger-db \
  -e POSTGRES_USER=ledger \
  -e POSTGRES_PASSWORD=ledger \
  -e POSTGRES_DB=ledger_db \
  -p 5432:5432 \
  -d postgres:16
```

### 4) Set environment variables

```bash
export DATABASE_URL="postgresql+asyncpg://ledger:ledger@localhost:5432/ledger_db"
export FAULTS_ENABLED="false"
export FAULT_RATE="0.3"
```

### 5) Run database migrations

```bash
alembic upgrade head
```

### 6) Start the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7) Run tests

```bash
pytest -q
```

## Core API behavior

### Root endpoint

```http
GET /
```

Returns basic metadata about the app.

### Health checks

```http
GET /health/live
GET /health/ready
```

- `/health/live` returns immediately with `{"status": "alive"}`
- `/health/ready` runs a lightweight DB connectivity check

### Account creation

```http
POST /accounts
```

Example body:

```json
{
  "name": "Primary Checking",
  "initial_balance_cents": 1000
}
```

### Transfer creation

```http
POST /transfers
Idempotency-Key: <unique-client-key>
```

Example body:

```json
{
  "from_account_id": "<uuid>",
  "to_account_id": "<uuid>",
  "amount_cents": 250
}
```

Behavior:

- rejects transfers with amount <= 0
- rejects sending to the same account
- locks account rows in deterministic order
- validates funds before mutating balances
- creates two ledger entries: one debit and one credit
- stores idempotency results in PostgreSQL
- returns 409 when the same idempotency key is reused with a different payload

### Metrics endpoint

```http
GET /metrics
```

Exposes Prometheus metrics for request counts, status codes, and request latency.

## Invariants and accounting rules

This project intentionally enforces three principles:

### 1) Double-entry accounting
Every transfer must create:

- one negative entry for the sender
- one positive entry for the receiver

The total sum across all ledger entries must remain zero.

### 2) Deterministic row locking
When two transfers touch the same pair of accounts, the app always locks the lower account ID first, then the higher one. This prevents deadlocks in concurrent transaction paths.

### 3) Idempotency at the API boundary
An idempotency key is required for transfer requests. If the same key is used with the same payload, the service returns the original response. If the same key is used with different data, the service rejects the request with HTTP 409.

## File-by-file overview

### `pyproject.toml`
Purpose: Python packaging and dependency management.

Why it matters:
- tells Python how to install the app and its test dependencies
- defines FastAPI, SQLAlchemy, Alembic, pydantic-settings, and pytest tooling
- keeps the project easy to run locally and in CI

### `alembic.ini`
Purpose: Alembic runner configuration.

Why it matters:
- points the migration tool at the database connection
- keeps schema changes versioned and reproducible

### `alembic/env.py`
Purpose: Bootstraps Alembic with the app’s SQLAlchemy metadata.

Why it matters:
- connects the migration system to the app models
- makes schema evolution consistent with application code

### `alembic/versions/001_initial_schema.py`
Purpose: Creates the initial tables.

Why it matters:
- establishes the foundation for accounts, transfers, ledger entries, and idempotency records
- provides the basic state model needed for correctness and auditing

### `src/app/config.py`
Purpose: Reads runtime configuration from environment variables.

Why it matters:
- centralizes database connection and chaos-testing configuration
- keeps deployments portable across local and Kubernetes environments

### `src/app/db.py`
Purpose: SQLAlchemy async engine and session setup.

Why it matters:
- allows the API to use async database access cleanly
- keeps database management separate from business logic

### `src/app/models.py`
Purpose: Domain model definitions for accounts and ledger state.

Why it matters:
- expresses the actual data model in code
- makes the accounting rules explicit in the ORM layer

### `src/app/schemas.py`
Purpose: DTOs for API validation and document generation.

Why it matters:
- keeps the API contract clear
- validates request payloads before business logic executes

### `src/app/services.py`
Purpose: Handles transfer execution and accounting invariants.

Why it matters:
- contains the real business logic
- enforces debit/credit balance rules and idempotency checks
- is the heart of the application correctness story

### `src/app/middleware.py`
Purpose: Fault injection for canary/chaos behavior testing.

Why it matters:
- makes it easy to simulate a bad release or broken deployment
- supports platform validation exercises without changing the infrastructure layer

### `src/app/main.py`
Purpose: FastAPI application entrypoint.

Why it matters:
- wires together endpoints, database dependencies, startup logic, and metrics
- gives us a single, simple application interface

### `scripts/reconcile.py`
Purpose: Independent audit script for ledger integrity checks.

Why it matters:
- provides a second line of validation outside the app code
- verifies that the ledger state matches the expected invariants
- useful during chaos testing, production verification, or incident review

### `tests/`
Purpose: Application validation for health, transfers, and idempotency.

Why it matters:
- keeps correctness measurable
- verifies the ledger behaves as expected under normal and concurrent conditions

## Operational notes

This repo is intentionally written to be simple and understandable. The application is not a full-scale banking product, but it reflects the critical engineering patterns used in stateful production systems:

- correct accounting semantics
- safe concurrency behavior
- strict data validation
- idempotent external APIs
- transparent monitoring
- reproducible migrations

For a real platform implementation, the next layer would be Kubernetes manifests, GitOps pipelines, database HA configuration, secret management, monitoring dashboards, and rollout automation. This repo is the application foundation that those platform controls can sit on top of.

## Recommended next steps

If you want to extend this project as a portfolio demo, the next logical additions are:

- Kubernetes deployment manifests
- Helm or Kustomize packaging
- Argo Rollouts canary strategy
- PostgreSQL HA setup with backups and WAL archiving
- Grafana dashboards
- GitHub Actions CI for linting and pytest
- a small Terraform or Pulumi environment for infrastructure provisioning

## Summary

`chaos-ledger` is a deliberately compact application that models a money transfer system under strict correctness constraints. Its real value is not in the breadth of features—it is in the evidence it gives you about how to run stateful systems safely in modern platform environments.

The app demonstrates:

- correct financial accounting
- safe concurrent behavior
- idempotent APIs
- operational observability
- platform-friendly failure simulation

That is the story this repository is designed to tell.
