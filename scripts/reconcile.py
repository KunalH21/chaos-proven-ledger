from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import AsyncSessionLocal, get_db, init_db
from .middleware import add_fault_injection_middleware
from .models import Account, IdempotencyRecord, Transfer
from .schemas import AccountCreate, AccountRead, HealthStatus, TransferRequest, TransferResponse
from .services import execute_transfer

app = FastAPI(title="chaos-ledger", version="0.1.0")
Instrumentator().instrument(app).expose(app, endpoint="/metrics")
add_fault_injection_middleware(app)


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "chaos-ledger", "version": "0.1.0", "status": "ok"}


@app.get("/health/live", response_model=HealthStatus)
async def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", response_model=HealthStatus)
async def ready() -> dict[str, str] | JSONResponse:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "not_ready"})


@app.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db)) -> Account:
    record = Account(name=account.name, balance_cents=account.initial_balance_cents)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@app.get("/accounts/{account_id}", response_model=AccountRead)
async def get_account(account_id: UUID, db: AsyncSession = Depends(get_db)) -> Account:
    account = await db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@app.post("/transfers", response_model=TransferResponse)
async def create_transfer(
    payload: TransferRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> TransferResponse:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    response = await execute_transfer(
        db,
        payload.from_account_id,
        payload.to_account_id,
        payload.amount_cents,
        idempotency_key,
    )
    return TransferResponse.model_validate(response)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
