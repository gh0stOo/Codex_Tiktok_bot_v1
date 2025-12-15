from datetime import datetime, timedelta
import hashlib
import secrets
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal
from . import models

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
settings = get_settings()
ACCESS_EXPIRE = timedelta(minutes=settings.access_token_exp_minutes)
REFRESH_EXPIRE = timedelta(days=settings.refresh_token_exp_days)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def hash_token_value(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, session_id: str) -> str:
    payload = {"sub": user_id, "sid": session_id, "exp": datetime.utcnow() + ACCESS_EXPIRE}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def create_session(db: Session, user: models.User, user_agent: str | None, ip_address: str | None) -> tuple[models.Session, str]:
    refresh_token = secrets.token_urlsafe(48)
    refresh_hash = hash_token_value(refresh_token)
    session = models.Session(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.utcnow() + REFRESH_EXPIRE,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, refresh_token


def revoke_session(db: Session, session: models.Session) -> None:
    session.revoked_at = datetime.utcnow()
    db.add(session)
    db.commit()


def validate_refresh(db: Session, refresh_token: str) -> models.Session:
    token_hash = hash_token_value(refresh_token)
    session = db.query(models.Session).filter(models.Session.refresh_token_hash == token_hash).first()
    if not session or session.revoked_at or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    return session


def get_current_session(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> tuple[models.Session, models.User]:
    payload = decode_token(token)
    user_id = payload.get("sub")
    session_id = payload.get("sid")
    if not user_id or not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    session = db.query(models.Session).filter(models.Session.id == session_id, models.Session.user_id == user_id).first()
    if not session or session.revoked_at or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return session, user


def get_current_user(session_user=Depends(get_current_session)) -> models.User:
    _, user = session_user
    return user
