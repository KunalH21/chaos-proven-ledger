from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_idempotency_key_exact_replay(client: AsyncClient) -> None:
    account_a = await client.post("/accounts", json={"name": "Sender", "initial_balance_cents": 1000})
    account_b = await client.post("/accounts", json={"name": "Receiver", "initial_balance_cents": 0})

    payload = {"from_account_id": account_a.json()["id"], "to_account_id": account_b.json()["id"], "amount_cents": 200}
    headers = {"Idempotency-Key": "same-key"}

    first = await client.post("/transfers", json=payload, headers=headers)
    second = await client.post("/transfers", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


@pytest.mark.asyncio
async def test_idempotency_key_conflict_on_payload_mismatch(client: AsyncClient) -> None:
    account_a = await client.post("/accounts", json={"name": "A", "initial_balance_cents": 1000})
    account_b = await client.post("/accounts", json={"name": "B", "initial_balance_cents": 0})

    first = await client.post(
        "/transfers",
        json={"from_account_id": account_a.json()["id"], "to_account_id": account_b.json()["id"], "amount_cents": 100},
        headers={"Idempotency-Key": "conflict-key"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/transfers",
        json={"from_account_id": account_a.json()["id"], "to_account_id": account_b.json()["id"], "amount_cents": 250},
        headers={"Idempotency-Key": "conflict-key"},
    )

    assert second.status_code == 409
    assert "different request payload" in second.json()["detail"]
