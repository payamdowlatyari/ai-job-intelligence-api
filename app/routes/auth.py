"""Auth routes: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import User
from app.schemas import UserRegister, UserLogin, UserRead, TokenResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: UserRegister,
    session: Session = Depends(get_session),
) -> UserRead:
    """Create a new user account."""
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        name=payload.name,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    session.refresh(user)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Authenticate and return a JWT access token."""
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Return the currently authenticated user."""
    return UserRead.model_validate(current_user)


@router.get("/me/token", response_model=TokenResponse)
def get_me_token(current_user: User = Depends(get_current_user)) -> TokenResponse:
    """Return a new access token for the currently authenticated user."""
    token = create_access_token(current_user.id)
    return TokenResponse(access_token=token)