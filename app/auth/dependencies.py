from typing import List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.security import decode_token, has_sufficient_role
from app.database.session import get_db_optional
from app.observability import emit_security_event
from app.observability.security import RBAC_DENIED

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Optional[Session] = Depends(get_db_optional),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )

    from app.database.repositories.user_repository import UserRepository

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    repo = UserRepository(db)
    user = repo.get(int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Optional[Session] = Depends(get_db_optional),
) -> Optional[dict]:
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None


def require_role(required_role: str):
    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if not has_sufficient_role(current_user["role"], required_role):
            emit_security_event(
                RBAC_DENIED,
                severity="warning",
                outcome="denied",
                user_id=current_user.get("id"),
                username=current_user.get("username"),
                role=current_user.get("role"),
                required_role=required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' insufficient. Required: '{required_role}'",
            )
        return current_user
    return role_checker


def optional_require_role(required_role: str):
    """Like require_role, but allows unauthenticated requests (no token = no enforcement).
    Only checks RBAC when a valid token is provided."""
    def role_checker(current_user: Optional[dict] = Depends(optional_current_user)) -> None:
        if current_user is not None and not has_sufficient_role(current_user["role"], required_role):
            emit_security_event(
                RBAC_DENIED,
                severity="warning",
                outcome="denied",
                user_id=current_user.get("id"),
                username=current_user.get("username"),
                role=current_user.get("role"),
                required_role=required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' insufficient. Required: '{required_role}'",
            )
    return role_checker
