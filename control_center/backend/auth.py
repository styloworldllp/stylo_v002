# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/auth.py
#
# JWT-based authentication for the Control Center admin UI.
#
# Flow:
#   1. Admin POSTs username + password to /api/auth/login (defined in main.py)
#   2. create_access_token() signs a JWT with the subject ("admin") and an
#      expiry of ACCESS_TOKEN_EXPIRE_MINUTES (default 8 hours)
#   3. All protected routes receive the token via the Authorization: Bearer
#      header and call Depends(get_current_user) which validates the JWT
#
# The bearer_scheme (HTTPBearer) extracts the token from the header.
# get_current_user() decodes and validates it; raises 401 on failure.
#
# Note: credentials are currently hardcoded for the single admin user.
# For multi-admin setups, replace the login endpoint with a DB lookup.
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from config import settings

bearer_scheme = HTTPBearer()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "stylo-admin"  # Override via env: ADMIN_PASSWORD in .env.control


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": subject, "exp": expire}, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        user: str = payload.get("sub")
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
