from celery import shared_task
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import anyio
import json
from .db import SessionLocal
from . import models
from .services.orchestrator import Orchestrator
from .providers.tiktok_official import TikTokClient
from .providers.openrouter_client import OpenRouterClient
from .providers.falai_client import FalAIClient
from .providers.voice_translation_client import VoiceTranslationClient
from .providers.storage import get_storage, tenant_prefix
from .security import decrypt_secret, encrypt_secret
from .config import get_settings

settings = get_settings()


def _db() -> Session:
    return SessionLocal()


def _job_run(db: Session, job: models.Job, status: str, message: str | None = None):
    run = models.JobRun(job_id=job.id, status=status, message=message)
    db.add(run)
    db.commit()


@shared_task(bind=True, name="tasks.generate_assets")
def generate_assets_task(self, job_id: str, project_id: str, plan_id: str):
    db = _db()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
        if not job or not project or not plan:
            return "missing entities"
        orchestrator = Orchestrator()
        _job_run(db, job, "in_progress")
        db.commit()
        
        asset = anyio.run(orchestrator.generate_assets, db, project, plan)
        
        # update plan status for visibility in calendar
        plan.status = "assets_generated"
        db.add(plan)
        job.status = "completed"
        db.add(job)
        _job_run(db, job, "completed", message=asset.id)
        db.commit()
        return asset.id
    except Exception as exc:
        if db and job:
            try:
                job.status = "failed"
                db.add(job)
                _job_run(db, job, "failed", message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        # Exponential backoff: 2^retry_count * 30 seconds, max 600 seconds
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 30, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()


@shared_task(bind=True, name="tasks.publish_now")
def publish_now_task(self, job_id: str, asset_id: str, access_token: str, open_id: str, use_inbox: bool = False):
    db = _db()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
        if not job or not asset:
            return "missing entities"
        
        # Prüfe ob TikTok-Account verbunden ist
        # Org-level Assets haben kein project_id
        if asset.project_id:
            project = db.query(models.Project).filter(models.Project.id == asset.project_id).first()
            if not project:
                raise RuntimeError("Project not found")
            org_id = project.organization_id
        else:
            # Org-level Asset
            org_id = asset.organization_id
        
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(models.SocialAccount.organization_id == org_id, models.SocialAccount.platform == "tiktok")
            .first()
        )
        if not tokens:
            raise RuntimeError("TikTok account not connected")
        
        token_row, account = tokens
        
        # Refresh token if needed before publishing
        if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
            refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
            if refresh:
                client = TikTokClient(organization_id=org_id)
                resp = anyio.run(client.refresh, refresh)
                new_access = resp.get("data", {}).get("access_token")
                new_refresh = resp.get("data", {}).get("refresh_token", refresh)
                if new_access:
                    access_token = new_access
                    token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
                    if new_refresh:
                        token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
                    db.add(token_row)
                    db.commit()
        
        # Verwende access_token aus token_row falls nicht übergeben
        if not access_token:
            access_token = decrypt_secret(token_row.access_token, settings.fernet_secret)
        if not open_id:
            open_id = account.open_id
        
        orchestrator = Orchestrator()
        _job_run(db, job, "in_progress")
        db.commit()
        
        result = anyio.run(orchestrator.publish_now, asset, access_token, open_id, use_inbox=use_inbox)
        asset.status = "published"
        asset.publish_response = str(result)
        db.add(asset)
        # keep plan in sync
        if asset.plan_id:
            plan = db.query(models.Plan).filter(models.Plan.id == asset.plan_id).first()
            if plan:
                plan.status = "published"
                db.add(plan)
        job.status = "completed"
        db.add(job)
        _job_run(db, job, "completed", message=str(result))
        db.commit()
        # enqueue status polling
        celery = __import__("app.celery_app", fromlist=["celery"]).celery
        celery.send_task("tasks.poll_publish_status", args=[asset.id])
        return "ok"
    except Exception as exc:
        if db and job:
            try:
                job.status = "failed"
                db.add(job)
                _job_run(db, job, "failed", message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        # Exponential backoff: 2^retry_count * 30 seconds, max 600 seconds
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 30, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()


@shared_task(bind=True, name="tasks.fetch_metrics")
def fetch_metrics_task(self, job_id: str, project_id: str):
    db = _db()
    job = None
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        if not job or not project:
            return "missing entities"
        _job_run(db, job, "in_progress")
        db.commit()
        
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(models.SocialAccount.organization_id == project.organization_id)
            .first()
        )
        if not tokens:
            raise RuntimeError("TikTok account not connected")
        token_row, account = tokens
        access = decrypt_secret(token_row.access_token, settings.fernet_secret)
        refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
        if not access:
            raise RuntimeError("Missing access token")
        client = TikTokClient(organization_id=project.organization_id)
        resp = anyio.run(client.get_metrics, access, account.handle)
        videos = resp.get("data", {}).get("videos", [])
        for v in videos:
            stats = v.get("statistics", {}) or {}
            metric = models.Metric(
                organization_id=project.organization_id,
                project_id=project_id,
                plan_id=None,
                metric="views",
                value=stats.get("view_count", 0),
                open_id=account.handle,
            )
            db.add(metric)
        job.status = "completed"
        db.add(job)
        _job_run(db, job, "completed", message=f"videos={len(videos)}")
        db.commit()
        return "ok"
    except Exception as exc:
        if db and job:
            try:
                job.status = "failed"
                db.add(job)
                _job_run(db, job, "failed", message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        # Exponential backoff: 2^retry_count * 30 seconds, max 600 seconds
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 30, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()


@shared_task(name="tasks.enqueue_due_plans")
def enqueue_due_plans():
    """
    Scheduler-Task: Identifiziert fällige Plan-Slots und erstellt Generation-Jobs.
    Läuft stündlich via Celery Beat.
    """
    db = _db()
    try:
        from datetime import datetime, timedelta, date
        from .services.idempotency import IdempotencyService
        from .celery_app import celery
        
        # Finde Pläne die in den nächsten 24 Stunden fällig sind und noch keine Assets haben
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).date()
        today = now.date()
        
        # Finde alle Projekte mit aktiviertem Autopilot
        projects = db.query(models.Project).filter(models.Project.autopilot_enabled == True).all()
        
        enqueued = 0
        for project in projects:
            # Finde Pläne die heute oder morgen fällig sind, approved sind, aber noch keine Assets haben
            plans = (
                db.query(models.Plan)
                .filter(
                    models.Plan.project_id == project.id,
                    models.Plan.slot_date >= today,
                    models.Plan.slot_date <= tomorrow,
                    models.Plan.approved == True,
                    models.Plan.locked == False,
                )
                .all()
            )
            
            for plan in plans:
                # Prüfe ob bereits Asset existiert
                existing_asset = (
                    db.query(models.VideoAsset)
                    .filter(models.VideoAsset.plan_id == plan.id)
                    .first()
                )
                
                if existing_asset:
                    continue  # Bereits generiert
                
                # Prüfe ob bereits Job existiert
                idem = f"gen:{plan.id}"
                existing_job = (
                    db.query(models.Job)
                    .filter(
                        models.Job.organization_id == project.organization_id,
                        models.Job.idempotency_key == idem,
                        models.Job.type == "generate_assets",
                        models.Job.status.in_(["pending", "in_progress"]),
                    )
                    .first()
                )
                
                if existing_job:
                    continue  # Bereits gequeued
                
                # Erstelle Job
                job, is_new = IdempotencyService.check_and_create_job(
                    db=db,
                    organization_id=project.organization_id,
                    project_id=project.id,
                    job_type="generate_assets",
                    idempotency_key=idem,
                    payload=str(plan.id),
                )
                
                if is_new:
                    celery.send_task("tasks.generate_assets", args=[job.id, project.id, plan.id])
                    enqueued += 1
        
        db.commit()
        return f"enqueued={enqueued}"
    except Exception as exc:
        if db:
            db.rollback()
        # Log error but don't retry (scheduler runs again in 1 hour)
        return f"error: {str(exc)}"
    finally:
        if db:
            db.close()


@shared_task(bind=True, name="tasks.poll_publish_status")
def poll_publish_status(self, asset_id: str):
    db = _db()
    try:
        assets: list[models.VideoAsset]
        if asset_id == "__broadcast__":
            assets = db.query(models.VideoAsset).filter(models.VideoAsset.status.in_(["published", "pending", "processing"])).all()
        else:
            asset = db.query(models.VideoAsset).filter(models.VideoAsset.id == asset_id).first()
            assets = [asset] if asset else []
        if not assets:
            return "missing asset"
        updated = 0
        for asset in assets:
            project = db.query(models.Project).filter(models.Project.id == asset.project_id).first()
            if not project:
                continue
            tokens = (
                db.query(models.OAuthToken, models.SocialAccount)
                .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
                .filter(models.SocialAccount.organization_id == project.organization_id, models.SocialAccount.platform == "tiktok")
                .first()
            )
            if not tokens:
                continue
            token_row, account = tokens
            access = decrypt_secret(token_row.access_token, settings.fernet_secret)
            refresh = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
            if not access:
                continue
            client = TikTokClient(organization_id=project.organization_id)
            # refresh if needed
            if token_row.expires_at and token_row.expires_at < datetime.utcnow() + timedelta(minutes=5):
                if refresh:
                    resp = anyio.run(client.refresh, refresh)
                    new_access = resp.get("data", {}).get("access_token")
                    new_refresh = resp.get("data", {}).get("refresh_token", refresh)
                    expires_in = resp.get("data", {}).get("expires_in", 3600)  # Default 1 hour
                    if new_access:
                        access = new_access
                        token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
                        if new_refresh:
                            token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
                        # FIX: Update expires_at after refresh
                        token_row.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                        db.add(token_row)
                        db.commit()
            video_id = None
            if asset.publish_response:
                try:
                    import json
                    import ast
                    # FIX: Proper JSON parsing - handle both JSON strings and Python dict strings
                    response_str = asset.publish_response
                    # Try JSON first
                    parsed = None
                    try:
                        parsed = json.loads(response_str)
                    except json.JSONDecodeError:
                        # If JSON fails, try eval (for Python dict strings like "{'data': {...}}")
                        try:
                            parsed = ast.literal_eval(response_str)
                        except (ValueError, SyntaxError):
                            # Last resort: try to extract video_id with regex
                            import re
                            match = re.search(r'"video_id"\s*:\s*"([^"]+)"', response_str)
                            if match:
                                video_id = match.group(1)
                                parsed = {}
                            else:
                                parsed = None
                    if parsed:
                        video_id = parsed.get("data", {}).get("video_id") or parsed.get("video_id")
                except Exception:
                    pass
            if not video_id:
                continue
            resp = anyio.run(client.get_video_status, access, account.handle, video_id)
            asset.publish_response = str(resp)
            status_val = resp.get("data", {}).get("status", "unknown")
            asset.status = status_val
            db.add(asset)
            updated += 1
        db.commit()
        return f"updated={updated}"
    except Exception as exc:
        # Exponential backoff: 2^retry_count * 60 seconds, max 600 seconds
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 60, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()


@shared_task(bind=True, name="tasks.refresh_expiring_tokens")
def refresh_expiring_tokens(self):
    """Background job to refresh TikTok tokens that are expiring soon"""
    db = _db()
    try:
        # Find tokens expiring in the next 15 minutes
        expiry_threshold = datetime.utcnow() + timedelta(minutes=15)
        
        tokens = (
            db.query(models.OAuthToken, models.SocialAccount)
            .join(models.SocialAccount, models.OAuthToken.social_account_id == models.SocialAccount.id)
            .filter(
                models.SocialAccount.platform == "tiktok",
                models.OAuthToken.expires_at.isnot(None),
                models.OAuthToken.expires_at <= expiry_threshold,
            )
            .all()
        )
        
        refreshed = 0
        failed = 0
        for token_row, account in tokens:
            try:
                refresh_token = decrypt_secret(token_row.refresh_token, settings.fernet_secret)
                if not refresh_token:
                    failed += 1
                    continue
                
                # FIX: Pass organization_id for rate limiting
                client = TikTokClient(organization_id=account.organization_id)
                resp = anyio.run(client.refresh, refresh_token)
                new_access = resp.get("data", {}).get("access_token")
                new_refresh = resp.get("data", {}).get("refresh_token", refresh_token)
                
                if new_access:
                    token_row.access_token = encrypt_secret(new_access, settings.fernet_secret)
                    if new_refresh:
                        token_row.refresh_token = encrypt_secret(new_refresh, settings.fernet_secret)
                    # Update expires_at if provided
                    expires_in = resp.get("data", {}).get("expires_in", 3600)
                    if expires_in:
                        token_row.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    db.add(token_row)
                    refreshed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                # Log error but continue with other tokens
                continue
        
        db.commit()
        return f"refreshed={refreshed}, failed={failed}"
    except Exception as exc:
        if db:
            db.rollback()
        raise self.retry(exc=exc, countdown=300, max_retries=2)
    finally:
        if db:
            db.close()


@shared_task(bind=True, name="tasks.youtube_transcribe")
def youtube_transcribe_task(self, job_id: str, payload_json: str):
    """Transkribiere YouTube Video im Hintergrund und speichere in VideoAsset"""
    import yt_dlp
    import tempfile
    from pathlib import Path
    
    db = _db()
    job = None
    storage = get_storage()
    
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return "missing job"
        
        payload = json.loads(payload_json)
        url = payload.get("url")
        provider = payload.get("provider")
        model_id = payload.get("model_id")
        target_language = payload.get("target_language", "auto")
        api_key = payload.get("api_key")
        
        org_id = job.organization_id
        
        _job_run(db, job, "in_progress", message=f"Starte Transcription von {url}")
        db.commit()
        
        # 1. YouTube Video herunterladen und Audio extrahieren
        _job_run(db, job, "in_progress", message="Lade YouTube-Video herunter und extrahiere Audio")
        db.commit()
        
        temp_dir = tempfile.TemporaryDirectory()
        audio_path = Path(temp_dir.name) / "audio.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': str(audio_path.with_suffix('')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file = Path(ydl.prepare_filename(info_dict)).with_suffix('.mp3')
                if not downloaded_file.exists():
                    mp3_files = list(Path(temp_dir.name).glob('*.mp3'))
                    if mp3_files:
                        downloaded_file = mp3_files[0]
                    else:
                        raise RuntimeError("Audio-Datei konnte nicht gefunden werden.")
                audio_path = downloaded_file
        except Exception as e:
            raise RuntimeError(f"Fehler beim Herunterladen/Extrahieren des Audios: {e}")
        
        # 2. Transkribieren mit ausgewähltem Provider/Modell
        _job_run(db, job, "in_progress", message="Transkribiere Audio")
        db.commit()
        
        transcript_text = ""
        if provider == "openrouter":
            # OpenRouter unterstützt keine direkte Audio-Transkription
            raise RuntimeError("OpenRouter unterstützt derzeit keine direkte Audio-Transkription.")
        elif provider == "falai":
            client = FalAIClient(api_key=api_key)
            # Fal.ai erwartet eine öffentlich zugängliche URL
            # Für jetzt: Upload Audio zu temporärem Storage oder verwende lokalen Pfad
            # In Produktion: Upload zu S3 oder temporärer Storage
            try:
                # Upload Audio zu Storage
                prefix = tenant_prefix(org_id, None, f"youtube_transcribe_{job.id}")
                audio_key = f"{prefix}/audio.mp3"
                audio_uri = storage.save_file(audio_key, str(audio_path))
                
                # Verwende signed URL für Fal.ai
                audio_url = storage.signed_url(audio_uri)
                
                # Transkribiere
                result = anyio.run(client.transcribe, audio_url, model_id, target_language)
                transcript_text = result.get("text", "") or result.get("transcription", "")
            except Exception as e:
                raise RuntimeError(f"Fehler bei Fal.ai Transcription: {e}")
        else:
            raise RuntimeError(f"Unbekannter Transkriptions-Provider: {provider}")
        
        # 3. Video herunterladen (für VideoAsset)
        _job_run(db, job, "in_progress", message="Lade Video für Library")
        db.commit()
        
        video_path = Path(temp_dir.name) / "video.mp4"
        ydl_video_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': str(video_path.with_suffix('')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_video_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_video = Path(ydl.prepare_filename(info_dict))
                if not downloaded_video.exists():
                    mp4_files = list(Path(temp_dir.name).glob('*.mp4'))
                    if mp4_files:
                        downloaded_video = mp4_files[0]
                    else:
                        raise RuntimeError("Video-Datei konnte nicht gefunden werden.")
                video_path = downloaded_video
        except Exception as e:
            raise RuntimeError(f"Fehler beim Herunterladen des Videos: {e}")
        
        # 4. Video auf Server speichern
        _job_run(db, job, "in_progress", message="Speichere Video auf Server")
        db.commit()
        
        prefix = tenant_prefix(org_id, None, f"youtube_transcribe_{job.id}")
        video_key = f"{prefix}/video.mp4"
        thumb_key = f"{prefix}/thumbnail.jpg"
        
        video_uri = storage.save_file(video_key, str(video_path))
        
        # Generiere Thumbnail
        try:
            from ..config import get_settings
            settings = get_settings()
            ffmpeg_path = settings.ffmpeg_path
            if ffmpeg_path:
                import subprocess
                thumb_path = Path(temp_dir.name) / "thumbnail.jpg"
                cmd = [
                    ffmpeg_path,
                    "-i", str(video_path),
                    "-frames:v", "1",
                    "-y",
                    str(thumb_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True, timeout=10)
                thumb_uri = storage.save_file(thumb_key, str(thumb_path))
            else:
                thumb_uri = video_uri  # Fallback
        except Exception:
            thumb_uri = video_uri  # Fallback
        
        # 5. VideoAsset erstellen und in Library speichern
        asset = models.VideoAsset(
            organization_id=org_id,
            project_id=None,  # Transcription hat kein Projekt
            plan_id=None,
            status="transcribed",
            video_path=str(video_uri),
            thumbnail_path=str(thumb_uri),
            transcript=transcript_text,
            original_language=target_language if target_language != "auto" else None
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # 6. Job abschließen
        job.status = "completed"
        job.payload = str(asset.id)  # Speichere Asset ID im Job Payload
        _job_run(db, job, "completed", message=f"Transcription abgeschlossen. Asset ID: {asset.id}")
        db.commit()
        
        # Log Storage Usage
        try:
            size_mb = max(1, int(video_path.stat().st_size / (1024 * 1024)))
            from .services.usage import log_usage
            log_usage(db, org_id, metric="storage_mb", amount=size_mb)
        except Exception:
            pass
        
        return f"Transcription abgeschlossen: {asset.id}"
    
    except Exception as exc:
        if db and job:
            try:
                job.status = "failed"
                db.add(job)
                _job_run(db, job, "failed", message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 30, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()
        if 'temp_dir' in locals() and temp_dir:
            temp_dir.cleanup()


@shared_task(bind=True, name="tasks.youtube_translate")
def youtube_translate_task(self, job_id: str, payload_json: str):
    """Übersetze YouTube Video mit Voice Cloning im Hintergrund"""
    import yt_dlp
    import tempfile
    from pathlib import Path
    import httpx
    import asyncio
    
    db = _db()
    job = None
    storage = get_storage()
    
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return "missing job"
        
        payload = json.loads(payload_json)
        url = payload.get("url")
        target_language = payload.get("target_language")
        source_language = payload.get("source_language")
        voice_cloning_provider = payload.get("voice_cloning_provider")
        voice_cloning_model_id = payload.get("voice_cloning_model_id")
        api_key = payload.get("api_key")
        credential_id = payload.get("credential_id")
        
        org_id = job.organization_id
        
        _job_run(db, job, "in_progress", message=f"Starte Video-Übersetzung von {url}")
        db.commit()
        
        # 1. YouTube Video herunterladen
        _job_run(db, job, "in_progress", message="Lade YouTube-Video herunter")
        db.commit()
        
        temp_dir = tempfile.TemporaryDirectory()
        video_path = Path(temp_dir.name) / "video.mp4"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(video_path.with_suffix('')),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file = Path(ydl.prepare_filename(info_dict))
                if not downloaded_file.exists():
                    mp4_files = list(Path(temp_dir.name).glob('*.mp4'))
                    if mp4_files:
                        downloaded_file = mp4_files[0]
                    else:
                        raise RuntimeError("Video-Datei konnte nicht gefunden werden.")
                video_path = downloaded_file
        except Exception as e:
            raise RuntimeError(f"Fehler beim Herunterladen des Videos: {e}")
        
        # 2. Video auf temporären Server hochladen (für Voice Cloning API)
        # Oder verwende direkten Upload zu Voice Cloning Provider
        _job_run(db, job, "in_progress", message="Bereite Video für Voice Cloning vor")
        db.commit()
        
        # 3. Voice Cloning Provider aufrufen
        _job_run(db, job, "in_progress", message=f"Starte Voice Cloning mit {voice_cloning_provider}")
        db.commit()
        
        # Erstelle Voice Translation Client
        client = VoiceTranslationClient(api_key=api_key, provider=voice_cloning_provider)
        
        # Lade Video zu temporärer URL hoch (falls Provider URL benötigt)
        # Für jetzt: Verwende lokalen Pfad (Provider muss File-Upload unterstützen)
        # In Produktion: Upload zu S3 oder temporärer Storage
        
        # Übersetze Video
        async def translate():
            return await client.translate_video(
                video_url=str(video_path),  # In Produktion: öffentliche URL
                target_language=target_language,
                source_language=source_language,
                model_id=voice_cloning_model_id
            )
        
        result = anyio.run(translate)
        
        if not result.get("video_url"):
            raise RuntimeError("Keine Video-URL von Voice Cloning Provider erhalten")
        
        # 4. Übersetztes Video herunterladen
        _job_run(db, job, "in_progress", message="Lade übersetztes Video herunter")
        db.commit()
        
        translated_video_path = Path(temp_dir.name) / "translated_video.mp4"
        
        async def download_video():
            async with httpx.AsyncClient(timeout=300.0) as http_client:
                response = await http_client.get(result["video_url"])
                response.raise_for_status()
                with open(translated_video_path, "wb") as f:
                    f.write(response.content)
        
        anyio.run(download_video)
        
        # 5. Video auf Server speichern
        _job_run(db, job, "in_progress", message="Speichere übersetztes Video auf Server")
        db.commit()
        
        prefix = tenant_prefix(org_id, None, f"youtube_translate_{job.id}")
        video_key = f"{prefix}/translated_video.mp4"
        thumb_key = f"{prefix}/thumbnail.jpg"
        
        video_uri = storage.save_file(video_key, str(translated_video_path))
        
        # Generiere Thumbnail
        try:
            from ..config import get_settings
            settings = get_settings()
            ffmpeg_path = settings.ffmpeg_path
            if ffmpeg_path:
                import subprocess
                thumb_path = Path(temp_dir.name) / "thumbnail.jpg"
                cmd = [
                    ffmpeg_path,
                    "-i", str(translated_video_path),
                    "-frames:v", "1",
                    "-y",
                    str(thumb_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True, timeout=10)
                thumb_uri = storage.save_file(thumb_key, str(thumb_path))
            else:
                thumb_uri = video_uri  # Fallback
        except Exception:
            thumb_uri = video_uri  # Fallback
        
        # 6. VideoAsset erstellen und in Library speichern
        asset = models.VideoAsset(
            organization_id=org_id,
            project_id=None,  # YouTube-Übersetzung hat kein Projekt
            plan_id=None,
            status="translated",
            video_path=str(video_uri),
            thumbnail_path=str(thumb_uri),
            transcript="",  # Kann später mit Transcription gefüllt werden
            original_language=source_language or "auto",
            translated_language=target_language,
            voice_clone_model_id=voice_cloning_model_id,
            translation_provider=voice_cloning_provider
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # 7. Job abschließen
        job.status = "completed"
        job.payload = str(asset.id)  # Speichere Asset ID im Job Payload
        _job_run(db, job, "completed", message=f"Video-Übersetzung abgeschlossen. Asset ID: {asset.id}")
        db.commit()
        
        # Log Storage Usage
        try:
            size_mb = max(1, int(translated_video_path.stat().st_size / (1024 * 1024)))
            from .services.usage import log_usage
            log_usage(db, org_id, metric="storage_mb", amount=size_mb)
        except Exception:
            pass
        
        return f"Video-Übersetzung abgeschlossen: {asset.id}"
    
    except Exception as exc:
        if db and job:
            try:
                job.status = "failed"
                db.add(job)
                _job_run(db, job, "failed", message=str(exc))
                db.commit()
            except Exception:
                db.rollback()
        retry_count = self.request.retries
        countdown = min(2 ** retry_count * 30, 600)
        raise self.retry(exc=exc, countdown=countdown, max_retries=3)
    finally:
        if db:
            db.close()
        if 'temp_dir' in locals() and temp_dir:
            temp_dir.cleanup()
