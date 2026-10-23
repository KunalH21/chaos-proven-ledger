# Financial Guarantees & System Invariants

## 1. Executive Summary
An **invariant** is a property of the system that must remain true at all times, regardless of concurrent traffic, network partitions, application crashes, or database node failovers. If an invariant is violated, the ledger is considered corrupted.

## 2. System Invariants

### Invariant 1: Double-Entry Balance Conservation (Zero Balance Drift)
* **Definition**: Money is never created or destroyed. Every transaction must be represented as two balanced ledger entries: a signed debit from the source account and an equal signed credit to the destination account.
* **Implementation Rule**: All amounts are represented strictly as **integer cents** (never floating-point numbers) to prevent rounding errors.

### Invariant 2: Exactly-Once Business Processing (Idempotency)
* **Definition**: Repeating a request with the same `Idempotency-Key` header must return the exact result of the original transaction without applying duplicate mutations to account balances.
* **Conflict Handling**: Reusing an existing `Idempotency-Key` with a different request payload (e.g., changing amount or destination) must be rejected with HTTP 409 Conflict.

### Invariant 3: Non-Negative Balances & Deadlock-Free Lock Ordering
* **Definition**: Account balances must not drop below zero unless overdrafts are explicitly permitted.
* **Concurrency Guarantee**: To prevent database deadlocks when concurrent requests lock competing accounts (e.g., Account A $\rightarrow$ Account B while Account B $\rightarrow$ Account A), the transfer service must **sort account IDs deterministically** (e.g., locking `min(account_a, account_b)` first) before acquiring row-level SELECT FOR UPDATE locks inside the database transaction.

## 3. Automated Reconciliation & Verification Strategy
Invariants are verified via a standalone Python reconciliation tool executed after load tests and failover experiments. The reconciliation script independently asserts:
1. Each account balance equals the exact sum of its `ledger_entries`.
2. Every `transfer` record possesses exactly one debit entry and one credit entry netting to zero.
3. Total system debits equal total system credits across the entire database.
