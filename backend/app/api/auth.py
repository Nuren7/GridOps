from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.models import User
from app.schemas.auth import (
    AuthResponse,
    Credentials,
    RegistrationResponse,
    TokenResponse,
)
from app.security import password_hash

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=RegistrationResponse)
async def register(
    credentials: Credentials,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RegistrationResponse:
    result = await session.execute(
        select(User).where(User.username == credentials.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Användarnamnet är upptaget",
        )

    session.add(
        User(
            username=credentials.username,
            hashed_password=password_hash.hash(credentials.password),
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Användarnamnet är upptaget",
        ) from None

    return RegistrationResponse(registered=True, username=credentials.username)


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: Credentials,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthResponse:
    result = await session.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    if user is None or not password_hash.verify(
        credentials.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Felaktigt användarnamn eller lösenord.",
        )
    return AuthResponse(authenticated=True, username=user.username)


@router.post("/token", response_model=TokenResponse)
async def issue_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    result = await session.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    if user is None or not password_hash.verify(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    token = jwt.encode(
        {"sub": user.username, "role": user.role, "exp": expires_at},
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return TokenResponse(access_token=token)
