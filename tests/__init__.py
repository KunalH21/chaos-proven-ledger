#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from typing import Any

from sqlalchemy import create_engine, func, select, text

from app.config import settings


def _sync_url() -> str:
    url = settings.DATABASE_URL
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def main() -> int:
    engine = create_engine(_sync_url())

    with engine.begin() as conn:
        ledger_sum = conn.execute(text("SELECT COALESCE(SUM(amount_cents), 0) FROM ledger_entries")).scalar_one()
        account_rows = conn.execute(
            text(
                "SELECT a.id, a.name, a.balance_cents, COALESCE(SUM(le.amount_cents), 0) AS ledger_total "
                "FROM accounts a LEFT JOIN ledger_entries le ON le.account_id = a.id "
                "GROUP BY a.id, a.name, a.balance_cents "
                "ORDER BY a.id"
            )
        ).mappings().all()

        failures: list[str] = []

        if ledger_sum != 0:
            failures.append(f"Ledger sum mismatch: expected 0, got {ledger_sum}")

        for row in account_rows:
            if row["balance_cents"] != row["ledger_total"]:
                failures.append(
                    f"Account {row['id']} balance mismatch: stored={row['balance_cents']} ledger_total={row['ledger_total']}"
                )

        report: dict[str, Any] = {
            "ok": not failures,
            "total_ledger_sum": ledger_sum,
            "accounts": [
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "balance_cents": r["balance_cents"],
                    "ledger_total": r["ledger_total"],
                }
                for r in account_rows
            ],
            "errors": failures,
        }

        print(json.dumps(report, indent=2, sort_keys=True))
        if failures:
            return 1
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # pragma: no cover - CLI safety
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2, sort_keys=True))
        sys.exit(1)
