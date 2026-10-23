# Chaos-Proven-Ledger — Problem Statement & System Purpose

## 1. System Overview
The Chaos-Proven-Ledger Delivery Platform is a Kubernetes-based stateful financial ledger service designed to demonstrate delivery automation, database resilience, and disaster recovery under controlled failure conditions. This project serves as a reliability testing laboratory to prove with empirical evidence that a stateful service can detect bad releases, survive database node failures, and recover from catastrophic data loss without sacrificing data integrity.

## 2. Target Problem & Real-World Failures
In distributed production systems, three critical failure modes routinely cause customer impact, financial loss, or data corruption:

1. **Unsafe Releases (The Sneaky Bug)**: Deploying a software release containing hidden bugs that cause HTTP 5xx errors for live traffic before human operators can intervene.
2. **Database Primary Crashes**: Sudden failure or network partition of an active database primary node during concurrent transaction processing, risking lost writes, half-updated balances, or duplicate charges when clients retry.
3. **Catastrophic Data Loss**: Unintended table deletion or bad database migrations that corrupt production state beyond live node recovery.

## 3. Engineering Goals & Demonstrable Outcomes
The platform is designed to achieve three verifiable, evidence-backed outcomes:

* **Outcome 1: SLO-Gated Progressive Rollout**: Automated canary releases (using Argo Rollouts and Traefik) that continuously evaluate 5xx error rates against Service Level Objectives (SLO) via Prometheus, automatically aborting and rolling back buggy deployments before widespread user impact occurs.
* **Outcome 2: Crash-Proof Stateful Resilience**: A 3-instance PostgreSQL cluster (managed by CloudNativePG with synchronous replication `dataDurability: required`) that maintains zero lost acknowledged transfers (RPO = 0) and zero duplicate charges during primary node failover.
* **Outcome 3: Verified Point-In-Time Recovery (PITR)**: Continuous Write-Ahead Log (WAL) archiving to S3-compatible storage (MinIO) paired with automated bootstrap verification to restore state up to the exact second prior to corruption, passing 100% of data integrity checks.

## 4. Scope & Non-Goals
* **In Scope**: Transactional correctness, integer-cent accounting, row locking, idempotency, GitOps delivery, automated canary analysis, operator failover, WAL archiving, and failure experiments under load.
* **Non-Goals**: Building a multi-tenant banking platform, UI frontend development, or public internet exposure without authentication.
