from __future__ import annotations

import random

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings


class FaultInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if settings.FAULTS_ENABLED and request.method == "POST" and request.url.path == "/transfers":
            if random.random() < settings.FAULT_RATE:
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "detail": "Simulated fault injection: canary release failure"},
                )
        return await call_next(request)


def add_fault_injection_middleware(app: FastAPI) -> None:
    app.add_middleware(FaultInjectionMiddleware)
