from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    initial_balance_cents: int = Field(default=0, ge=0)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    balance_cents: int


class TransferRequest(BaseModel):
    from_account_id: UUID
    to_account_id: UUID
    amount_cents: int = Field(..., gt=0)


class TransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transfer_id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount_cents: int
    status: str
    idempotency_key: str


class HealthStatus(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    detail: str


class ReconciliationReport(BaseModel):
    ok: bool
    total_ledger_sum: int
    accounts: list[dict[str, Any]]
    errors: list[str] = []
