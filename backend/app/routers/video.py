from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member, assert_org_member
from ..security import decrypt_secret
from ..services.orchestrator import Orchestrator
from ..services.usage import enforce_quota, log_usage, QuotaExceeded
from ..services.idempotency import IdempotencyService
from ..providers.storage import get_storage
from fastapi.responses import StreamingResponse
from ..celery_app import celery
from typing import List, Dict, Optional
from ..providers.tiktok_official import TikTokClient
from ..security import decrypt_secret
from ..config import get_settings
from datetime import datetime, timedelta

router = APIRouter()
orchestrator = Orchestrator()
storage = get_storage()
settings = get_settings()

from ..providers.openrouter_client import OpenRouterClient
from ..providers.falai_client import FalAIClient
from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: str | None = None
    supports_video_generation: bool = False  # Für Video-Generierungs-Modelle
    pricing: Optional[Dict] = None  # Pricing-Informationen von OpenRouter
    cost_per_1k_tokens: Optional[float] = None  # Kosten pro 1K Tokens (vereinfacht)
    cost_per_minute: Optional[float] = None  # Kosten pro Minute Video (für Video-Generierung)
    currency: str = "USD"


class ProviderKeyRequest(BaseModel):
    provider: Optional[str] = "openrouter"  # Provider-Typ
    api_key: Optional[str] = None
    credential_id: Optional[str] = None
    org_id: Optional[str] = None


@router.post("/models", response_model=List[ModelInfo])
async def list_video_models(
    req: ProviderKeyRequest = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Liste verfügbare Video-Generierung Modelle (für Script-Generierung)"""
    api_key = None
    provider = req.provider or "openrouter"  # Verwende provider aus Request
    
    # Hole API-Key aus Credential falls angegeben
    if req.credential_id and req.org_id:
        assert_org_member(db, user, req.org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == req.credential_id,
            models.Credential.organization_id == req.org_id
        ).first()
        if credential:
            api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
            provider = credential.provider or "openrouter"
    
    if not api_key and req.api_key:
        api_key = req.api_key
    
    models_list = []
    
    if provider == "openrouter" or not req.credential_id:
        # OpenRouter Modelle für Script-Generierung
        try:
            client = OpenRouterClient(api_key=api_key)
            all_models = await client.list_models()
            
            # Filtere für Script-Generierung geeignete Modelle (nicht Transcription)
            # Suche nach GPT, Claude, Llama, etc.
            script_models = [
                m for m in all_models
                if any(keyword in m.get("id", "").lower() for keyword in [
                    "gpt", "claude", "llama", "mistral", "gemini", "anthropic", "openai"
                ]) and "whisper" not in m.get("id", "").lower()
            ]
            
            for model in script_models[:50]:  # Limit auf 50
                pricing = model.get("pricing", {})
                prompt_price = pricing.get("prompt", "0") if pricing else "0"
                completion_price = pricing.get("completion", "0") if pricing else "0"
                
                # Berechne durchschnittliche Kosten pro 1K Tokens
                cost_per_1k = None
                try:
                    prompt_cost = float(str(prompt_price).replace("$", "").replace(",", "")) if isinstance(prompt_price, str) else float(prompt_price) if prompt_price else 0
                    completion_cost = float(str(completion_price).replace("$", "").replace(",", "")) if isinstance(completion_price, str) else float(completion_price) if completion_price else 0
                    # Durchschnitt für Input + Output
                    cost_per_1k = (prompt_cost + completion_cost) / 2 if (prompt_cost + completion_cost) > 0 else None
                except (ValueError, TypeError):
                    cost_per_1k = None
                
                models_list.append(ModelInfo(
                    id=model.get("id", ""),
                    name=model.get("name", model.get("id", "")),
                    provider="openrouter",
                    description=model.get("description", ""),
                    pricing=pricing,
                    cost_per_1k_tokens=cost_per_1k,
                    currency="USD"
                ))
        except Exception as e:
            # Fallback: Bekannte Modelle
            known_models = [
                ("openrouter/auto", "OpenRouter Auto (Empfohlen)", "Automatische Modell-Auswahl"),
                ("openai/gpt-4o", "GPT-4o", "OpenAI GPT-4 Optimized"),
                ("openai/gpt-4-turbo", "GPT-4 Turbo", "OpenAI GPT-4 Turbo"),
                ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet", "Anthropic Claude 3.5"),
                ("meta-llama/llama-3.1-70b-instruct", "Llama 3.1 70B", "Meta Llama 3.1"),
            ]
            # Bekannte Preise für Fallback-Modelle (ungefähr)
            known_prices = {
                "openrouter/auto": 0.002,  # Durchschnitt
                "openai/gpt-4o": 0.005,
                "openai/gpt-4-turbo": 0.01,
                "anthropic/claude-3.5-sonnet": 0.003,
                "meta-llama/llama-3.1-70b-instruct": 0.0007,
            }
            for model_id, name, desc in known_models:
                models_list.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider="openrouter",
                    description=desc,
                    pricing=None,
                    cost_per_1k_tokens=known_prices.get(model_id),
                    currency="USD"
                ))
    
    elif provider == "falai":
        # Fal.ai bietet Video-Generierungs-Modelle
        try:
            client = FalAIClient(api_key=api_key)
            falai_models = await client.list_models()
            
            # Filtere nur Video-Generierungs-Modelle (nicht Transcription-Modelle)
            video_models = [
                m for m in falai_models
                if m.get("supports_video_generation", False) and not m.get("supports_transcription", False)
            ]
            
            for model in video_models:
                cost_per_sec = model.get("cost_per_second", 0)
                # Konvertiere zu cost_per_1k_tokens für einheitliche Anzeige (geschätzt: 1 Sekunde Video ≈ 1000 Tokens)
                cost_per_1k = cost_per_sec * 1000 if cost_per_sec > 0 else None
                models_list.append(ModelInfo(
                    id=model.get("id", ""),
                    name=model.get("name", model.get("id", "")),
                    provider="falai",
                    description=model.get("description", ""),
                    pricing={"per_second": f"${cost_per_sec:.4f}", "note": "Kosten pro Sekunde generiertes Video"},
                    cost_per_1k_tokens=cost_per_1k,
                    currency=model.get("currency", "USD")
                ))
        except Exception as e:
            # Fallback: Bekannte Fal.ai Video-Generierungs-Modelle
            known_falai_video_models = [
                ("fal-ai/kling-video/v2.6/pro/text-to-video", "Kling 2.6 Pro (Text-to-Video)", "Hochwertige Text-zu-Video-Generierung - ~$0.05/Sekunde", 50.0),
                ("fal-ai/kling-video/v2.6/text-to-video", "Kling 2.6 (Text-to-Video)", "Text-zu-Video-Generierung - ~$0.03/Sekunde", 30.0),
                ("fal-ai/kling-video/v2.6/pro/image-to-video", "Kling 2.6 Pro (Image-to-Video)", "Bild-zu-Video-Generierung - ~$0.04/Sekunde", 40.0),
                ("fal-ai/stable-video-diffusion", "Stable Video Diffusion", "Stable Diffusion für Video - ~$0.02/Sekunde", 20.0),
            ]
            for model_id, name, desc, cost_per_1k in known_falai_video_models:
                models_list.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider="falai",
                    description=desc,
                    pricing={"per_second": f"${cost_per_1k/1000:.4f}", "note": "Kosten pro Sekunde generiertes Video"},
                    cost_per_1k_tokens=cost_per_1k,
                    currency="USD"
                ))
    
    return models_list


@router.post("/generation-models", response_model=List[ModelInfo])
async def list_video_generation_models(
    req: ProviderKeyRequest = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Liste verfügbare Video-Generierungs-Modelle (Text-to-Video APIs, nicht Script-Generierung)"""
    api_key = None
    provider = req.provider or "falai"  # Standard für Video-Generierung ist Fal.ai
    
    # Hole API-Key aus Credential falls angegeben
    if req.credential_id and req.org_id:
        assert_org_member(db, user, req.org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == req.credential_id,
            models.Credential.organization_id == req.org_id
        ).first()
        if credential:
            api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
            provider = credential.provider or "falai"
    
    if not api_key and req.api_key:
        api_key = req.api_key
    
    models_list = []
    
    if provider == "falai":
        # Fal.ai Video-Generierungs-Modelle (nur Text-to-Video)
        try:
            client = FalAIClient(api_key=api_key)
            falai_models = await client.list_models()
            
            # Filtere nur Text-to-Video Modelle (nicht Transcription, nicht Image-to-Video)
            text_to_video_models = [
                m for m in falai_models
                if m.get("supports_video_generation", False) 
                and m.get("supports_text_to_video", False)  # Nur Text-to-Video
                and not m.get("supports_transcription", False)
            ]
            
            for model in text_to_video_models:
                cost_per_min = model.get("cost_per_minute", 0)
                cost_per_sec = model.get("cost_per_second", 0)
                
                models_list.append(ModelInfo(
                    id=model.get("id", ""),
                    name=model.get("name", model.get("id", "")),
                    provider="falai",
                    description=model.get("description", ""),
                    supports_video_generation=True,
                    pricing={
                        "per_minute": f"${cost_per_min:.2f}" if cost_per_min > 0 else "N/A",
                        "per_second": f"${cost_per_sec:.4f}" if cost_per_sec > 0 else "N/A",
                        "note": "Kosten pro Minute generiertes Video"
                    },
                    cost_per_minute=cost_per_min if cost_per_min > 0 else None,
                    currency=model.get("currency", "USD")
                ))
        except Exception as e:
            # Fallback: Bekannte Fal.ai Text-to-Video Modelle
            known_models = [
                ("fal-ai/kling-video/v2.6/pro/text-to-video", "Kling 2.6 Pro (Text-to-Video)", "Hochwertige Text-zu-Video-Generierung", 16.80),
                ("fal-ai/kling-video/v2.6/text-to-video", "Kling 2.6 (Text-to-Video)", "Text-zu-Video-Generierung - Standard", 5.70),
                ("fal-ai/kling-video/v2.5/text-to-video", "Kling 2.5 (Text-to-Video)", "Text-zu-Video-Generierung - Ältere Version", 4.80),
                ("fal-ai/stable-video-diffusion", "Stable Video Diffusion (Text-to-Video)", "Günstige Text-zu-Video-Generierung", 1.20),
            ]
            for model_id, name, desc, cost_per_min in known_models:
                models_list.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider="falai",
                    description=desc,
                    supports_video_generation=True,
                    pricing={"per_minute": f"${cost_per_min:.2f}", "note": "Kosten pro Minute generiertes Video"},
                    cost_per_minute=cost_per_min,
                    currency="USD"
                ))
    else:
        # Andere Provider können hier hinzugefügt werden
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{provider}' unterstützt derzeit keine Video-Generierung. Bitte verwende 'falai'."
        )
    
    return models_list


@router.post("/generate/{project_id}/{plan_id}", response_model=schemas.VideoGenerateResponse)
async def generate_video_asset(project_id: str, plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id, roles=["owner", "admin", "editor"])
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id, models.Plan.project_id == project_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Prüfe ob Plan ein Script hat
    if not plan.script_content:
        raise HTTPException(
            status_code=400, 
            detail="Plan hat noch kein Script. Bitte zuerst ein Script generieren."
        )
    
    try:
        enforce_quota(db, project.organization_id, metric="video_generation")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    idem = f"gen:{plan.id}"
    # Use IdempotencyService for atomic check-and-create
    job, is_new = IdempotencyService.check_and_create_job(
        db=db,
        organization_id=project.organization_id,
        project_id=project.id,
        job_type="generate_assets",
        idempotency_key=idem,
        payload=str(plan.id),
    )
    
    if not is_new:
        # Job already exists - return existing asset if available
        if job and job.status in ("in_progress", "completed"):
            asset = db.query(models.VideoAsset).filter(models.VideoAsset.plan_id == plan.id).order_by(models.VideoAsset.created_at.desc()).first()
            if asset:
                asset.signed_video_url = storage.signed_url(asset.video_path)
                asset.signed_thumbnail_url = storage.signed_url(asset.thumbnail_path)
                return schemas.VideoGenerateResponse(
                    id=asset.id,
                    status=asset.status,
                    video_path=asset.video_path,
                    thumbnail_path=asset.thumbnail_path,
                    signed_video_url=asset.signed_video_url,
                    signed_thumbnail_url=asset.signed_thumbnail_url,
                    job_id=job.id,
                    message=f"Video bereits vorhanden (Status: {asset.status})"
                )
            return schemas.VideoGenerateResponse(
                status=job.status,
                job_id=job.id,
                message=f"Job läuft bereits (Status: {job.status})"
            )
        return schemas.VideoGenerateResponse(
            status=job.status if job else "pending",
            job_id=job.id if job else None,
            message="Job bereits vorhanden"
        )
    
    # New job created - enqueue task
    log_usage(db, project.organization_id, metric="video_generation")
    celery.send_task("tasks.generate_assets", args=[job.id, project.id, plan.id])
    return schemas.VideoGenerateResponse(
        job_id=job.id,
        status="queued",
        message="Video-Generierung gestartet"
    )


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
    
    # Prüfe Zugriff: Entweder über Projekt oder Organisation
    if asset.project_id:
        project = db.query(models.Project).filter(models.Project.id == asset.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        assert_project_member(db, user, project.id, roles=["owner", "admin", "editor"])
        org_id = project.organization_id
    else:
        # Org-level Asset - prüfe nur Org-Mitgliedschaft
        assert_org_member(db, user, asset.organization_id, roles=["owner", "admin", "editor"])
        org_id = asset.organization_id
    
    if use_stored_token:
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(models.SocialAccount.organization_id == org_id, models.SocialAccount.platform == "tiktok")
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
            resp = await TikTokClient(organization_id=org_id).refresh(refresh_token)
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
    # Use IdempotencyService for atomic check-and-create
    job, is_new = IdempotencyService.check_and_create_job(
        db=db,
        organization_id=org_id,
        project_id=asset.project_id,  # Kann None sein für org-level Assets
        job_type="publish_now",
        idempotency_key=idem,
        payload=asset.id,
    )
    
    if not is_new:
        # Job already exists
        return {"status": job.status if job else "pending", "job_id": job.id if job else None}
    
    # New job created - enqueue task
    log_usage(db, org_id, metric="publish_now")
    celery.send_task("tasks.publish_now", args=[job.id, asset.id, access_token, open_id, use_inbox])
    return {"status": "queued", "job_id": job.id}


@router.get("/assets/{asset_id}/signed")
def get_signed_urls(asset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    # Prüfe Zugriff: Entweder über Projekt oder Organisation
    if asset.project_id:
        assert_project_member(db, user, asset.project_id)
    else:
        # Org-level Asset
        assert_org_member(db, user, asset.organization_id)
    return {
        "video": storage.signed_url(asset.video_path),
        "thumbnail": storage.signed_url(asset.thumbnail_path),
    }


@router.get("/assets/{asset_id}/stream")
def stream_asset(asset_id: str, kind: str = "video", db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Prüfe Zugriff: Entweder über Projekt oder Organisation
    if asset.project_id:
        assert_project_member(db, user, asset.project_id)
    else:
        # Org-level Asset (z.B. YouTube Transcription/Translation)
        assert_org_member(db, user, asset.organization_id)
    
    uri = asset.video_path if kind == "video" else asset.thumbnail_path
    try:
        data = storage.read_bytes_uri(uri)
    except Exception:
        raise HTTPException(status_code=404, detail="File not available")
    media_type = "video/mp4" if kind == "video" else "image/jpeg"
    return StreamingResponse(iter([data]), media_type=media_type)


@router.get("/download/{asset_id}")
def download_video(asset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Download-Route für VideoAssets - unterstützt alle Video-Typen (generiert, übersetzt, transkribiert)"""
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Prüfe Zugriff: Entweder über Projekt oder Organisation
    if asset.project_id:
        assert_project_member(db, user, asset.project_id)
    else:
        # Org-level Asset (z.B. YouTube Transcription/Translation)
        assert_org_member(db, user, asset.organization_id)
    
    try:
        # Lade Video-Daten
        video_data = storage.read_bytes_uri(asset.video_path)
        
        # Bestimme Dateiname basierend auf Asset-Status
        filename = f"video_{asset.id}.mp4"
        if asset.status == "translated":
            filename = f"translated_{asset.translated_language}_{asset.id}.mp4"
        elif asset.status == "transcribed":
            filename = f"transcribed_{asset.id}.mp4"
        
        # Return als Download
        from fastapi.responses import Response
        return Response(
            content=video_data,
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(video_data))
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Laden des Videos: {str(e)}"
        )


@router.get("/assets/project/{project_id}", response_model=List[schemas.VideoAssetOut])
def list_assets(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Liste alle VideoAssets für ein Projekt UND org-level Assets (YouTube Transcription/Translation)"""
    project = assert_project_member(db, user, project_id)
    
    # Hole Projekt-spezifische Assets
    project_assets = (
        db.query(models.VideoAsset)
        .filter(models.VideoAsset.project_id == project.id)
        .all()
    )
    
    # Hole org-level Assets (YouTube Transcription/Translation ohne Projekt)
    org_assets = (
        db.query(models.VideoAsset)
        .filter(
            models.VideoAsset.organization_id == project.organization_id,
            models.VideoAsset.project_id.is_(None)  # Org-level Assets
        )
        .all()
    )
    
    # Kombiniere und sortiere nach created_at
    all_assets = sorted(project_assets + org_assets, key=lambda a: a.created_at or datetime.min, reverse=True)
    
    # Generiere signed URLs
    for asset in all_assets:
        try:
            asset.signed_video_url = storage.signed_url(asset.video_path)
            asset.signed_thumbnail_url = storage.signed_url(asset.thumbnail_path)
        except Exception:
            asset.signed_video_url = None
            asset.signed_thumbnail_url = None
    
    return all_assets


@router.get("/status/{asset_id}")
async def publish_status(asset_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    # Prüfe Zugriff: Entweder über Projekt oder Organisation
    if asset.project_id:
        project = assert_project_member(db, user, asset.project_id)
        org_id = project.organization_id
    else:
        # Org-level Asset
        assert_org_member(db, user, asset.organization_id)
        org_id = asset.organization_id
    tokens = (
        db.query(models.OAuthToken, models.SocialAccount)
        .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
        .filter(models.SocialAccount.organization_id == org_id, models.SocialAccount.platform == "tiktok")
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
    client = TikTokClient(organization_id=org_id)
    # refresh if expiring
    if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
        if refresh:
            resp = await client.refresh(refresh)
            new_access = resp.get("data", {}).get("access_token")
            new_refresh = resp.get("data", {}).get("refresh_token", refresh)
            expires_in = resp.get("data", {}).get("expires_in", 3600)
            if new_access:
                access = new_access
                # FIX: Persist token refresh
                from ..security import encrypt_secret
                token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
                if new_refresh:
                    token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
                token_row.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                db.add(token_row)
                db.commit()
    # try to extract video_id from publish_response
    video_id = None
    if asset.publish_response:
        if "video_id" in asset.publish_response:
            try:
                import json
                import ast
                # FIX: Proper JSON parsing - handle both JSON strings and Python dict strings
                response_str = asset.publish_response
                try:
                    parsed = json.loads(response_str)
                except json.JSONDecodeError:
                    try:
                        parsed = ast.literal_eval(response_str)
                    except (ValueError, SyntaxError):
                        import re
                        match = re.search(r'"video_id"\s*:\s*"([^"]+)"', response_str)
                        if match:
                            video_id = match.group(1)
                            parsed = {}
                        else:
                            parsed = {}
                if parsed:
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
