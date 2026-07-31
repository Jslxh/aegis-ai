from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import secrets

from app.auth.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.auth.dependencies import get_current_user, require_role
from app.database.session import get_db
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.refresh_token_repository import RefreshTokenRepository
from app.models.auth import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.services.email_service import send_password_reset_email
from app.observability import emit_security_event
from app.observability.security import (
    LOGIN_SUCCESS,
    LOGIN_FAILURE,
    REGISTER_USER,
    LOGOUT,
    TOKEN_REFRESH,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    payload: UserCreate,
    current_user: dict = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    if repo.find_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    if repo.find_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already exists")

    valid_roles = {"viewer", "operator", "auditor", "security_analyst", "admin"}
    if payload.role not in valid_roles:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role. Must be one of: {', '.join(sorted(valid_roles))}",
        )

    user = repo.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    db.commit()

    emit_security_event(
        REGISTER_USER,
        severity="info",
        outcome="success",
        user_id=user.id,
        username=user.username,
        role=user.role,
    )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.find_by_username(payload.username)

    if not user or not verify_password(payload.password, user.hashed_password):
        emit_security_event(
            LOGIN_FAILURE,
            severity="warning",
            outcome="failure",
            username=payload.username,
            reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        emit_security_event(
            LOGIN_FAILURE,
            severity="warning",
            outcome="failure",
            username=payload.username,
            reason="account_disabled",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    token_hash = hash_token(refresh_token)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).replace(tzinfo=None)

    refresh_repo = RefreshTokenRepository(db)
    refresh_repo.create_token(token_hash, user.id, expires_at)
    db.commit()

    emit_security_event(
        LOGIN_SUCCESS,
        severity="info",
        outcome="success",
        user_id=user.id,
        username=user.username,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_payload = decode_token(payload.refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    token_hash = hash_token(payload.refresh_token)
    refresh_repo = RefreshTokenRepository(db)
    stored = refresh_repo.find_by_hash(token_hash)

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    if stored.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    if stored.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )

    user_repo = UserRepository(db)
    user = user_repo.get(stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Rotate refresh token
    refresh_repo.revoke_token(token_hash)

    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    new_access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)

    new_hash = hash_token(new_refresh)
    new_expires = (datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).replace(tzinfo=None)
    refresh_repo.create_token(new_hash, user.id, new_expires)
    db.commit()

    emit_security_event(
        TOKEN_REFRESH,
        severity="info",
        outcome="success",
        user_id=user.id,
        username=user.username,
    )

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        role=current_user["role"],
        is_active=True,
    )


@router.post("/logout")
def logout(
    payload: RefreshRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    token_hash = hash_token(payload.refresh_token)
    refresh_repo = RefreshTokenRepository(db)
    stored = refresh_repo.find_by_hash(token_hash)

    if stored and stored.user_id == current_user["id"]:
        refresh_repo.revoke_token(token_hash)
        db.commit()

    emit_security_event(
        LOGOUT,
        severity="info",
        outcome="success",
        user_id=current_user["id"],
        username=current_user["username"],
    )

    return {"detail": "Logged out successfully"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.get(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.find_by_username(payload.identity)
    if not user:
        user = repo.find_by_email(payload.identity)

    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        db.commit()

        reset_link = f"http://localhost:5173/reset-password?token={token}"
        send_password_reset_email(user.email, user.username, reset_link)

    return {"detail": "If a matching account exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.find_by_reset_token(payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        user.reset_token = None
        user.reset_token_expires_at = None
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    return {"detail": "Password reset successfully"}
