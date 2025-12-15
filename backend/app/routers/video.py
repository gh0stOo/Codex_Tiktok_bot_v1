from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member
from ..services.orchestrator import Orchestrator
from ..services.usage import enforce_quota, log_usage, QuotaExceeded
from ..providers.storage import get_storage
from fastapi.responses import StreamingResponse
from ..celery_app import celery
from typing import List
from ..providers.tiktok_official import TikTokClient
from ..security import decrypt_secret
from ..config import get_settings
from datetime import datetime, timedelta

router = APIRouter()
orchestrator = Orchestrator()
storage = get_storage()


@router.post("/generate/{project_id}/{plan_id}", response_model=schemas.VideoAssetOut)
async def generate_assets(project_id: str, plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id, roles=["owner", "admin", "editor"])
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id, models.Plan.project_id == project_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    try:
        enforce_quota(db, project.organization_id, metric="video_generation")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    idem = f"gen:{plan.id}"
    existing = (
        db.query(models.Job)
        .filter(models.Job.organization_id == project.organization_id, models.Job.idempotency_key == idem, models.Job.type == "generate_assets")
        .order_by(models.Job.created_at.desc())
        .first()
    )
    if existing and existing.status in ("in_progress", "completed"):
        # return current asset if exists
        asset = db.query(models.VideoAsset).filter(models.VideoAsset.plan_id == plan.id).order_by(models.VideoAsset.created_at.desc()).first()
        if asset:
            asset.signed_video_url = storage.signed_url(asset.video_path)
            asset.signed_thumbnail_url = storage.signed_url(asset.thumbnail_path)
            return asset
        return {"status": existing.status}
    job = models.Job(
        organization_id=project.organization_id,
        project_id=project.id,
        type="generate_assets",
        status="pending",
        payload=str(plan.id),
        idempotency_key=idem,
    )
    db.add(job)
    db.commit()
    log_usage(db, project.organization_id, metric="video_generation")
    celery.send_task("tasks.generate_assets", args=[job.id, project.id, plan.id])
    return {"job_id": job.id, "status": "queued"}


@router.post("/publish/{asset_id}")
async def publish_now(
    asset_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    access_token: str | None = Body(None, embed=True),
    open_id: str | None = Body(None, embed=True),
    use_stored_token: bool = Body(True, embed=True),
    use_inbox: bool = Body(False, embed=True),
):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    project = db.query(models.Project).filter(models.Project.id == asset.project_id).first()
    assert_project_member(db, user, project.id, roles=["owner", "admin", "editor"])
    if use_stored_token:
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(models.SocialAccount.organization_id == project.organization_id, models.SocialAccount.platform == "tiktok")
            .first()
        )
        if not tokens:
            raise HTTPException(status_code=503, detail="TikTok account not connected")
        token_row, account = tokens
        from ..security import decrypt_secret
        from ..config import get_settings
        from datetime import datetime, timedelta
        from ..providers.tiktok_official import TikTokClient

        settings = get_settings()
        access_token = decrypt_secret(token_row.access_token, settings.fernet_secret)
        refresh_token = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
        if not access_token:
            raise HTTPException(status_code=400, detail="Missing access token")
        # refresh if needed
        if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
            if not refresh_token:
                raise HTTPException(status_code=400, detail="Token expired and no refresh token")
            resp = await TikTokClient().refresh(refresh_token)
            new_access = resp.get("data", {}).get("access_token")
            new_refresh = resp.get("data", {}).get("refresh_token", refresh_token)
            if new_access:
                from ..security import encrypt_secret

                token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
                token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
                db.add(token_row)
                db.commit()
                access_token = new_access
            open_id = account.handle
        else:
            open_id = account.handle
    if not access_token or not open_id:
        raise HTTPException(status_code=400, detail="access_token/open_id required")
    if asset.plan_id:
        plan = db.query(models.Plan).filter(models.Plan.id == asset.plan_id).first()
        if plan and not plan.approved:
            raise HTTPException(status_code=400, detail="Plan not approved")
        if plan and plan.locked and plan.status != "published":
            raise HTTPException(status_code=423, detail="Plan locked")
    idem = f"pub:{asset.id}"
    existing = (
        db.query(models.Job)
        .filter(models.Job.organization_id == project.organization_id, models.Job.idempotency_key == idem, models.Job.type == "publish_now")
        .order_by(models.Job.created_at.desc())
        .first()
    )
    if existing and existing.status in ("in_progress", "completed"):
        return {"status": existing.status, "job_id": existing.id}
    job = models.Job(
        organization_id=project.organization_id,
        project_id=project.id,
        type="publish_now",
        status="pending",
        payload=asset.id,
        idempotency_key=idem,
    )
    db.add(job)
    db.commit()
    log_usage(db, project.organization_id, metric="publish_now")
    celery.send_task("tasks.publish_now", args=[job.id, asset.id, access_token, open_id, use_inbox])
    return {"status": "queued", "job_id": job.id}


@router.get("/assets/{asset_id}/signed")
def get_signed_urls(asset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    project = assert_project_member(db, user, asset.project_id)
    return {
        "video": storage.signed_url(asset.video_path),
        "thumbnail": storage.signed_url(asset.thumbnail_path),
    }


@router.get("/assets/{asset_id}/stream")
def stream_asset(asset_id: str, kind: str = "video", db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    project = assert_project_member(db, user, asset.project_id)
    uri = asset.video_path if kind == "video" else asset.thumbnail_path
    try:
        data = storage.read_bytes_uri(uri)
    except Exception:
        raise HTTPException(status_code=404, detail="File not available")
    media_type = "video/mp4" if kind == "video" else "image/jpeg"
    return StreamingResponse(iter([data]), media_type=media_type)


@router.get("/assets/project/{project_id}", response_model=List[schemas.VideoAssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    assets = (
        db.query(models.VideoAsset)
        .filter(models.VideoAsset.project_id == project.id)
        .order_by(models.VideoAsset.created_at.desc())
        .all()
    )
    for asset in assets:
        try:
            asset.signed_video_url = storage.signed_url(asset.video_path)
            asset.signed_thumbnail_url = storage.signed_url(asset.thumbnail_path)
        except Exception:
            asset.signed_video_url = None
            asset.signed_thumbnail_url = None
    return assets


@router.get("/status/{asset_id}")
async def publish_status(asset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    project = assert_project_member(db, user, asset.project_id)
    tokens = (
        db.query(models.OAuthToken, models.SocialAccount)
        .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
        .filter(models.SocialAccount.organization_id == project.organization_id, models.SocialAccount.platform == "tiktok")
        .first()
    )
    if not tokens:
        raise HTTPException(status_code=503, detail="TikTok account not connected")
    token_row, account = tokens
    settings = get_settings()
    access = decrypt_secret(token_row.access_token, settings.fernet_secret)
    refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
    if not access:
        raise HTTPException(status_code=400, detail="Missing access token")
    client = TikTokClient()
    # refresh if expiring
    if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
        if refresh:
            resp = await client.refresh(refresh)
            new_access = resp.get("data", {}).get("access_token")
            if new_access:
                access = new_access
    # try to extract video_id from publish_response
    video_id = None
    if asset.publish_response:
        if "video_id" in asset.publish_response:
            try:
                import json

                parsed = json.loads(asset.publish_response.replace("'", '"'))
                video_id = parsed.get("data", {}).get("video_id") or parsed.get("video_id")
            except Exception:
                pass
    if not video_id:
        raise HTTPException(status_code=400, detail="No video_id stored")
    resp = await client.get_video_status(access, account.handle, video_id)
    asset.publish_response = str(resp)
    status = resp.get("data", {}).get("status", "unknown")
    asset.status = status
    db.add(asset)
    db.commit()
    return {"status": status, "raw": resp}
