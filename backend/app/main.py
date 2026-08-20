from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import router as auth_router


app = FastAPI(
    title="ClaimBridge API",
    description="Intelligent Insurance Claim Verification and Readiness Assessment System",
    version="1.0.0",
)

#change that i done
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
def root():
    return {
        "message": "ClaimBridge API is running",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ClaimBridge Backend",
    }