from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.schemas import Credentials, TokenRead, UserRead
from app.security import Db, create_access_token, dummy_hash, password_hash

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: Credentials, db: Db):
    user = User(
        email=str(payload.email).lower(),
        password_hash=password_hash.hash(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenRead)
def login(payload: Credentials, db: Db):
    user = db.scalar(
        select(User).where(User.email == str(payload.email).lower())
    )
    stored_hash = user.password_hash if user is not None else dummy_hash
    valid = password_hash.verify(payload.password, stored_hash)
    if user is None or not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenRead(access_token=create_access_token(user.id))