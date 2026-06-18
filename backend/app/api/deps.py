from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.revoked_token import RevokedToken
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
    )


def _authenticate_token(token: str, db: Session) -> User:
    credentials_error = _credentials_error()
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub", "0"))
        jti = str(payload.get("jti", ""))
    except (InvalidTokenError, ValueError):
        raise credentials_error

    if jti and db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_error
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return _authenticate_token(token, db)


def get_current_user_from_header_or_query(
    request: Request,
    token_header: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User:
    token = token_header or request.query_params.get("token")
    if not token:
        raise _credentials_error()
    return _authenticate_token(token, db)
