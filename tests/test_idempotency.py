from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_successful_transfer_and_double_entry(client: AsyncClient) -> None:
    account_a = await client.post("/accounts", json={"name": "Checking", "initial_balance_cents": 1000})
    account_b = await client.post("/accounts", json={"name": "Savings", "initial_balance_cents": 200})

    response = await client.post(
        "/transfers",
        json={"from_account_id": account_a.json()["id"], "to_account_id": account_b.json()["id"], "amount_cents": 150},
        headers={"Idempotency-Key": "transfer-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["amount_cents"] == 150
    assert body["status"] == "COMPLETED"

    source = await client.get(f"/accounts/{account_a.json()['id']}")
    destination = await client.get(f"/accounts/{account_b.json()['id']}")
    assert source.json()["balance_cents"] == 850
    assert destination.json()["balance_cents"] == 350


@pytest.mark.asyncio
async def test_insufficient_balance_rejected(client: AsyncClient) -> None:
    account_a = await client.post("/accounts", json={"name": "Low Balance", "initial_balance_cents": 50})
    account_b = await client.post("/accounts", json={"name": "Receiver", "initial_balance_cents": 100})

    response = await client.post(
        "/transfers",
        json={"from_account_id": account_a.json()["id"], "to_account_id": account_b.json()["id"], "amount_cents": 75},
        headers={"Idempotency-Key": "transfer-insufficient"},
    )

    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_concurrent_transfers_do_not_deadlock(client: AsyncClient) -> None:
    account_a = await client.post("/accounts", json={"name": "A", "initial_balance_cents": 1000})
    account_b = await client.post("/accounts", json={"name": "B", "initial_balance_cents": 1000})

    a_id = account_a.json()["id"]
    b_id = account_b.json()["id"]

    async def transfer(sender_id: str, receiver_id: str, amount: int, key: str) -> None:
        response = await client.post(
            "/transfers",
            json={"from_account_id": sender_id, "to_account_id": receiver_id, "amount_cents": amount},
            headers={"Idempotency-Key": key},
        )
        assert response.status_code == 200

    await asyncio.gather(
        transfer(a_id, b_id, 100, "race-1"),
        transfer(b_id, a_id, 50, "race-2"),
    )

    account_a_after = await client.get(f"/accounts/{a_id}")
    account_b_after = await client.get(f"/accounts/{b_id}")
    assert account_a_after.json()["balance_cents"] == 950
    assert account_b_after.json()["balance_cents"] == 1050
