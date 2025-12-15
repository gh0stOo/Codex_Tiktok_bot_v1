from datetime import datetime, timedelta
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_db,
    create_session,
    validate_refresh,
    revoke_session,
    get_current_session,
    hash_token_value,
)
from ..config import get_settings

router = APIRouter()
settings = get_settings()
PASSWORD_RESET_EXP = timedelta(hours=1)
VERIFICATION_EXP = timedelta(hours=24)


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    verification_token = secrets.token_urlsafe(32)
    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        verification_token=hash_token_value(verification_token),
        verification_sent_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenPair)
def login(payload: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    session, refresh_token = create_session(db, user, request.headers.get("user-agent"), request.client.host if request.client else None)
    token = create_access_token(user.id, session.id)
    return schemas.TokenPair(access_token=token, refresh_token=refresh_token)


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(payload: schemas.RefreshRequest, request: Request, db: Session = Depends(get_db)):
    session = validate_refresh(db, payload.refresh_token)
    user = db.query(models.User).filter(models.User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    revoke_session(db, session)
    new_session, new_refresh = create_session(db, user, request.headers.get("user-agent"), request.client.host if request.client else None)
    access_token = create_access_token(user.id, new_session.id)
    return schemas.TokenPair(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout")
def logout(session_user=Depends(get_current_session), db: Session = Depends(get_db)):
    session, _ = session_user
    revoke_session(db, session)
    return {"detail": "logged out"}


@router.post("/password/reset/request")
def password_reset_request(payload: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"detail": "if the account exists, a reset was requested"}
    token = secrets.token_urlsafe(32)
    reset = models.PasswordReset(
        user_id=user.id,
        token_hash=hash_token_value(token),
        expires_at=datetime.utcnow() + PASSWORD_RESET_EXP,
    )
    db.add(reset)
    db.commit()
    if settings.environment == "development":
        return {"detail": "reset token generated (development)", "reset_token": token}
    return {"detail": "reset requested"}


@router.post("/password/reset/confirm")
def password_reset_confirm(payload: schemas.PasswordResetConfirm, db: Session = Depends(get_db)):
    token_hash = hash_token_value(payload.token)
    reset = (
        db.query(models.PasswordReset)
        .filter(models.PasswordReset.token_hash == token_hash, models.PasswordReset.used_at.is_(None))
        .order_by(models.PasswordReset.created_at.desc())
        .first()
    )
    if not reset or reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    user = db.query(models.User).filter(models.User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    reset.used_at = datetime.utcnow()
    db.add_all([user, reset])
    db.commit()
    return {"detail": "password updated"}


@router.post("/verify/request")
def verify_request(payload: schemas.VerificationRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"detail": "if the account exists, verification was requested"}
    token = secrets.token_urlsafe(32)
    user.verification_token = hash_token_value(token)
    user.verification_sent_at = datetime.utcnow()
    db.add(user)
    db.commit()
    if settings.environment == "development":
        return {"detail": "verification token generated (development)", "verification_token": token}
    return {"detail": "verification requested"}


@router.post("/verify/confirm")
def verify_confirm(payload: schemas.VerificationConfirm, db: Session = Depends(get_db)):
    token_hash = hash_token_value(payload.token)
    user = db.query(models.User).filter(models.User.verification_token == token_hash).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    if user.email_verified:
        return {"detail": "already verified"}
    user.email_verified = True
    user.verification_token = None
    user.verification_sent_at = None
    db.add(user)
    db.commit()
    return {"detail": "email verified"}
