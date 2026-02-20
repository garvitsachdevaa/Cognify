"""
Auth router — register and login (simple, no OAuth).
Passwords hashed with bcrypt directly.
Returns user_id on success — swap for JWT in production.
"""

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import crud
from app.db import get_db

router = APIRouter()


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())



class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    if crud.get_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = _hash_password(body.password)
    user = crud.create_user(db, body.name, body.email, hashed)
    return {
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "message": "Account created successfully",
    }


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return user_id."""
    user = crud.get_user_by_email(db, body.email)
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "user_id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }
