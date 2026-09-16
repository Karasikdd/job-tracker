from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash("dummy-password-for-login-check")
bearer = HTTPBearer(auto_error=False)
Db = Annotated[Session, Depends(get_db)]


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=30)},
        settings.secret_key,
        algorithm="HS256",
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
    db: Db,
) -> User:
    error = HTTPException(
        status_code=401,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise ValueError("Invalid subject")
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise error
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]