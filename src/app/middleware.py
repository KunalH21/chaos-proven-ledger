from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Account, IdempotencyRecord, LedgerEntry, Transfer, TransferStatus


def _canonicalize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = _canonicalize_payload(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _get_account_or_404(db: AsyncSession, account_id: UUID) -> Account:
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account


async def execute_transfer(
    db: AsyncSession,
    from_id: UUID | str,
    to_id: UUID | str,
    amount_cents: int,
    idempotency_key: str,
) -> dict[str, Any]:
    from_uuid = UUID(str(from_id))
    to_uuid = UUID(str(to_id))

    if amount_cents <= 0:
        raise HTTPException(status_code=400, detail="amount_cents must be greater than 0")
    if from_uuid == to_uuid:
        raise HTTPException(status_code=400, detail="from_account_id and to_account_id must be different")

    payload = {
        "from_account_id": str(from_uuid),
        "to_account_id": str(to_uuid),
        "amount_cents": amount_cents,
    }
    request_hash = _hash_payload(payload)

    existing = await db.get(IdempotencyRecord, idempotency_key)
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key was already used with a different request payload",
            )
        return json.loads(existing.response_body)

    first_id, second_id = sorted((from_uuid, to_uuid))

    first_account = await db.scalar(
        select(Account).where(Account.id == first_id).with_for_update()
    )
    second_account = await db.scalar(
        select(Account).where(Account.id == second_id).with_for_update()
    )

    if first_account is None or second_account is None:
        missing = [str(account_id) for account_id in [first_id, second_id] if account_id not in {a.id for a in [first_account, second_account] if a is not None}]
        raise HTTPException(status_code=404, detail=f"Account not found: {missing}")

    from_account = first_account if first_account.id == from_uuid else second_account
    to_account = second_account if second_account.id == to_uuid else first_account

    if from_account.balance_cents < amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds for transfer")

    from_account.balance_cents -= amount_cents
    to_account.balance_cents += amount_cents

    transfer = Transfer(
        from_account_id=from_uuid,
        to_account_id=to_uuid,
        amount_cents=amount_cents,
        status=TransferStatus.COMPLETED,
        idempotency_key=idempotency_key,
    )
    db.add(transfer)
    await db.flush()

    db.add_all(
        [
            LedgerEntry(transfer_id=transfer.id, account_id=from_uuid, amount_cents=-amount_cents),
            LedgerEntry(transfer_id=transfer.id, account_id=to_uuid, amount_cents=amount_cents),
        ]
    )

    response_payload = {
        "transfer_id": str(transfer.id),
        "from_account_id": str(from_uuid),
        "to_account_id": str(to_uuid),
        "amount_cents": amount_cents,
        "status": transfer.status.value,
        "idempotency_key": idempotency_key,
    }

    idempotency_record = IdempotencyRecord(
        key=idempotency_key,
        request_hash=request_hash,
        response_code=200,
        response_body=json.dumps(response_payload, separators=(",", ":")),
    )
    db.add(idempotency_record)

    await db.commit()
    await db.refresh(transfer)

    return response_payload
