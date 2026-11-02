import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router
from .claims import router as claims_router
from .documents import router as documents_router
from .cashless import router as cashless_router


app = FastAPI(
    title="ClaimBridge API",
    description=(
        "Intelligent Insurance Claim Verification "
        "and Readiness Assessment System"
    ),
    version="1.0.0",
)


# =========================================================
# CORS
# =========================================================


allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8002",
    "http://127.0.0.1:8002",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
]

extra_origins = os.getenv("CLAIMBRIDGE_ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend(
        origin.strip() for origin in extra_origins.split(",") if origin.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(auth_router)

app.include_router(claims_router)

app.include_router(documents_router)

app.include_router(cashless_router)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "ClaimBridge API is running",
        "status": "healthy",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ClaimBridge Backend",
    }