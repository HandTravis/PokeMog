"""
auth_routes.py — Authentication routes for PokéRanker.

Endpoints:
    POST /api/auth/register  — create a new account
    POST /api/auth/login     — get a JWT token
    GET  /api/auth/me        — get the current user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str


class RegisterResponse(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.

    Returns the new user and a JWT token so the user is logged
    in immediately after registering — no separate login step needed.
    """
    # Check if email is already taken
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )

    # Hash the password — never store plaintext
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)

    return RegisterResponse(
        user=UserOut(id=str(user.id), email=user.email),
        access_token=token,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Log in with email and password, receive a JWT token.

    Uses OAuth2PasswordRequestForm which expects form fields
    `username` and `password` — we treat `username` as the email.
    This is the standard OAuth2 token endpoint shape that FastAPI
    and most API clients expect.
    """
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Use the same error for wrong email and wrong password —
    # never tell an attacker which one was incorrect
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """
    Return the currently authenticated user's profile.

    This route requires a valid Bearer token — FastAPI automatically
    returns 401 if the token is missing or invalid via get_current_user.
    """
    return UserOut(id=str(current_user.id), email=current_user.email)