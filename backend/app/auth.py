from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from pwdlib import PasswordHash

from .database import get_db
from .models import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

password_hash = PasswordHash.recommended()


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str = "Coordinator"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login_user(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == login_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Password is not configured"
        )

    if not password_hash.verify(
        login_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "message": "Login successful",
        "user_id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role
    }


@router.post("/register")
def register_user(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_password = password_hash.hash(user_data.password)

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        role=user_data.role,
        password_hash=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role
    }