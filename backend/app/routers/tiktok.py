from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..auth import get_current_user, get_db
from ..config import get_settings
from ..providers.tiktok_official import TikTokClient
from ..security import encrypt_secret, decrypt_secret
from .. import models
from ..authorization import assert_org_member
import secrets

router = APIRouter()
settings = get_settings()


@router.get("/oauth/start")
def oauth_start(org_id: str = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id, roles=["owner", "admin"])
    try:
        client = TikTokClient(organization_id=org_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    nonce = secrets.token_urlsafe(12)
    state = f"{org_id}:{nonce}"
    return {"redirect_url": client.oauth_authorize_url(state=state), "state": state}


@router.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    # state carries org_id to enforce tenant ownership
    if ":" not in state:
        raise HTTPException(status_code=400, detail="Invalid state")
    org_id, _nonce = state.split(":", 1)
    assert_org_member(db, user, org_id, roles=["owner", "admin"])
    client = TikTokClient(organization_id=org_id)
    token_data = await client.exchange_code(code)
    access = token_data.get("data", {}).get("access_token")
    refresh = token_data.get("data", {}).get("refresh_token")
    open_id = token_data.get("data", {}).get("open_id")
    expires_in = token_data.get("data", {}).get("expires_in")
    if not access or not refresh or not open_id:
        raise HTTPException(status_code=400, detail="TikTok token response invalid")

    social = (
        db.query(models.SocialAccount)
        .filter(models.SocialAccount.organization_id == org_id, models.SocialAccount.platform == "tiktok")
        .first()
    )
    if not social:
        social = models.SocialAccount(organization_id=org_id, platform="tiktok", handle=open_id)
        db.add(social)
        db.flush()
    else:
        social.handle = open_id
    enc_access = encrypt_secret(access, settings.fernet_secret)
    enc_refresh = encrypt_secret(refresh, settings.fernet_secret)

    existing_token = (
        db.query(models.OAuthToken).filter(models.OAuthToken.social_account_id == social.id).order_by(models.OAuthToken.created_at.desc()).first()
    )
    if existing_token:
        existing_token.access_token = enc_access
        existing_token.refresh_token = enc_refresh
        existing_token.expires_at = None
        token_row = existing_token
    else:
        token_row = models.OAuthToken(
            social_account_id=social.id,
            access_token=enc_access,
            refresh_token=enc_refresh,
            expires_at=None,
        )
        db.add(token_row)
    db.commit()
    return {"status": "ok", "open_id": open_id}


@router.post("/refresh")
async def refresh_token(org_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assert_org_member(db, user, org_id)
    tokens = (
        db.query(models.OAuthToken, models.SocialAccount)
        .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
        .filter(models.SocialAccount.organization_id == org_id, models.SocialAccount.platform == "tiktok")
        .first()
    )
    if not tokens:
        raise HTTPException(status_code=404, detail="No TikTok account linked")
    token_row, account = tokens
    refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
    if not refresh:
        raise HTTPException(status_code=400, detail="No refresh token available")
    client = TikTokClient(organization_id=org_id)
    resp = await client.refresh(refresh)
    new_access = resp.get("data", {}).get("access_token")
    new_refresh = resp.get("data", {}).get("refresh_token", refresh)
    if not new_access:
        raise HTTPException(status_code=400, detail="Refresh failed")
    token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
    token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
    db.add(token_row)
    db.commit()
    return {"status": "refreshed"}
