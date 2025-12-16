from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict
import httpx
import asyncio
from sqlalchemy.orm import Session
from ..services.orchestrator import Orchestrator
from ..services.usage import enforce_quota, log_usage, QuotaExceeded
from ..services.idempotency import IdempotencyService
from ..auth import get_current_user, get_db
from ..authorization import assert_org_member
from ..security import decrypt_secret
from ..config import get_settings
from ..providers.openrouter_client import OpenRouterClient
from ..providers.falai_client import FalAIClient
from ..providers.voice_translation_client import VoiceTranslationClient
from .. import models
from ..celery_app import celery

router = APIRouter()
orch = Orchestrator()
settings = get_settings()


class ProviderKeyRequest(BaseModel):
    provider: str  # "openrouter" oder "falai"
    api_key: Optional[str] = None  # Optional, wenn credential_id verwendet wird
    credential_id: Optional[str] = None  # Optional: ID eines gespeicherten Credentials
    org_id: Optional[str] = None  # Erforderlich, wenn credential_id verwendet wird


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    cost_per_minute: Optional[float] = None
    currency: str = "USD"
    supported_languages: List[str]
    description: Optional[str] = None
    pricing: Optional[Dict] = None


class TranscribeRequest(BaseModel):
    url: str
    target_language: str = "auto"
    provider: str  # "openrouter" oder "falai"
    api_key: Optional[str] = None  # Optional, wenn credential_id verwendet wird
    model_id: str
    credential_id: Optional[str] = None  # Optional: ID eines gespeicherten Credentials
    org_id: Optional[str] = None  # Erforderlich, wenn credential_id verwendet wird


class TranslateRequest(BaseModel):
    url: str
    target_language: str  # z.B. "de", "en", "es"
    source_language: Optional[str] = None  # Optional, wird automatisch erkannt wenn None
    voice_cloning_provider: str  # "rask" | "heygen" | "elevenlabs" | "falai"
    voice_cloning_model_id: Optional[str] = None  # Optional: spezifisches Modell
    credential_id: Optional[str] = None  # Optional: ID eines gespeicherten Credentials
    org_id: Optional[str] = None  # Erforderlich, wenn credential_id verwendet wird


# Whisper unterstützt alle Sprachen (99 Sprachen)
WHISPER_LANGUAGES = [
    "auto", "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "zh"
]


async def get_openrouter_models(api_key: str) -> List[ModelInfo]:
    """Hole alle Transcription-fähigen Modelle von OpenRouter"""
    try:
        client = OpenRouterClient(api_key=api_key)
        models = await client.list_models()
        
        transcription_models = []
        for model in models:
            model_id = model.get("id", "")
            name = model.get("name", model_id)
            model_id_lower = model_id.lower()
            
            # Filtere nach Transcription-fähigen Modellen (Whisper, etc.)
            # OpenRouter hat verschiedene Whisper-Modelle und andere Audio-Modelle
            # Prüfe auch Modell-Modalities für Audio-Support
            modalities = model.get("modalities", [])
            has_audio_support = "audio" in modalities or "audio_input" in modalities
            
            is_transcription_model = (
                any(keyword in model_id_lower for keyword in [
                    "whisper", "transcribe", "asr", "speech", "audio", "stt",
                    "whisper-1", "whisper-large", "whisper-medium", "whisper-small"
                ]) or has_audio_support
            )
            
            if is_transcription_model:
                pricing = model.get("pricing", {})
                
                # Berechne Kosten pro Minute
                # OpenRouter Pricing ist typischerweise pro Token, aber für Audio-Modelle
                # gibt es oft direkte Preise pro Minute
                prompt_price = pricing.get("prompt", "0") if pricing else "0"
                completion_price = pricing.get("completion", "0") if pricing else "0"
                
                # Versuche Preise zu parsen (können Strings wie "$0.0001" sein)
                try:
                    prompt_cost = float(prompt_price.replace("$", "").replace(",", "")) if isinstance(prompt_price, str) else float(prompt_price)
                    # Für Transcription: geschätzte Kosten pro Minute
                    # Typischerweise ~$0.006 pro Minute für Whisper
                    cost_per_minute = prompt_cost * 1000 if prompt_cost > 0 else 0.006
                except (ValueError, TypeError):
                    cost_per_minute = 0.006  # Fallback
                
                transcription_models.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider="openrouter",
                    cost_per_minute=cost_per_minute,
                    currency="USD",
                    supported_languages=WHISPER_LANGUAGES,  # Whisper unterstützt alle Sprachen
                    description=model.get("description", ""),
                    pricing=pricing
                ))
        
        # Falls keine gefunden, füge bekannte Whisper-Modelle hinzu
        if not transcription_models:
            # Bekannte OpenRouter Whisper-Modelle
            known_whisper_models = [
                ("openai/whisper-1", "OpenAI Whisper", 0.006),
                ("fal-ai/whisper", "Fal.ai Whisper", 0.005),
            ]
            for model_id, model_name, cost in known_whisper_models:
                transcription_models.append(ModelInfo(
                    id=model_id,
                    name=model_name,
                    provider="openrouter",
                    cost_per_minute=cost,
                    currency="USD",
                    supported_languages=WHISPER_LANGUAGES,
                    description="Whisper-basiertes Transcription-Modell"
                ))
        
        return transcription_models
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Ungültiger API-Key. Bitte prüfe deinen OpenRouter API-Key."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fehler beim Abrufen der OpenRouter-Modelle: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fehler beim Abrufen der OpenRouter-Modelle: {str(e)}"
        )


async def get_falai_models(api_key: str) -> List[ModelInfo]:
    """Hole alle Transcription-Modelle von Fal.ai"""
    try:
        client = FalAIClient(api_key=api_key)
        models = await client.list_models()
        
        transcription_models = []
        for model in models:
            transcription_models.append(ModelInfo(
                id=model.get("id", ""),
                name=model.get("name", ""),
                provider="falai",
                cost_per_minute=model.get("cost_per_minute", 0.005),
                currency=model.get("currency", "USD"),
                supported_languages=model.get("supported_languages", WHISPER_LANGUAGES),
                description=model.get("description", "")
            ))
        
        return transcription_models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fehler beim Abrufen der Fal.ai-Modelle: {str(e)}"
        )


@router.post("/models", response_model=List[ModelInfo])
async def list_models(req: ProviderKeyRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Liste alle verfügbaren Transcription-Modelle basierend auf API-Key oder Credential"""
    api_key = req.api_key
    
    # FIX: Unterstütze Credentials für Model-Liste
    if req.credential_id and req.org_id:
        assert_org_member(db, user, req.org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == req.credential_id,
            models.Credential.organization_id == req.org_id,
            models.Credential.provider == req.provider
        ).first()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential nicht gefunden"
            )
        api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Fehler beim Entschlüsseln des Credentials"
            )
    elif not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-Key oder Credential-ID ist erforderlich"
        )
    
    if req.provider == "openrouter":
        return await get_openrouter_models(api_key)
    elif req.provider == "falai":
        return await get_falai_models(api_key)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unbekannter Provider: {req.provider}. Unterstützt: openrouter, falai"
        )


@router.post("/transcribe")
async def transcribe(req: TranscribeRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Transkribiere YouTube Video mit ausgewähltem Provider und Modell"""
    # Hole API-Key entweder aus Request oder aus Credentials
    api_key = req.api_key
    
    if req.credential_id and req.org_id:
        # Verwende gespeichertes Credential
        assert_org_member(db, user, req.org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == req.credential_id,
            models.Credential.organization_id == req.org_id,
            models.Credential.provider == req.provider
        ).first()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential nicht gefunden"
            )
        api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Fehler beim Entschlüsseln des Credentials"
            )
    elif not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-Key oder Credential-ID ist erforderlich"
        )
    
    # Wenn org_id nicht vorhanden, verwende erste Organisation des Users
    org_id = req.org_id
    if not org_id and user.organizations:
        org_id = user.organizations[0].id
    elif not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation ist erforderlich für Transcription-Jobs"
        )
    
    assert_org_member(db, user, org_id)
    
    # Validierung
    if req.provider == "openrouter":
        client = OpenRouterClient(api_key=api_key)
        try:
            available_models = await client.list_models()
            model_exists = any(m.get("id") == req.model_id for m in available_models)
            if not model_exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Modell '{req.model_id}' nicht gefunden"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fehler beim Validieren des Modells: {str(e)}"
            )
    elif req.provider == "falai":
        client = FalAIClient(api_key=api_key)
        # Validierung für Fal.ai
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unbekannter Provider: {req.provider}"
        )
    
    # Quota prüfen
    try:
        enforce_quota(db, org_id, metric="youtube_transcription")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    
    # Erstelle Job für Transcription
    import json
    payload_data = {
        "url": req.url,
        "provider": req.provider,
        "model_id": req.model_id,
        "target_language": req.target_language,
        "api_key": api_key,  # Wird verschlüsselt gespeichert
        "credential_id": req.credential_id
    }
    
    idem = f"transcribe:{req.url}:{req.provider}:{req.model_id}"
    job, is_new = IdempotencyService.check_and_create_job(
        db=db,
        organization_id=org_id,
        project_id=None,  # Transcription hat kein Projekt
        job_type="youtube_transcribe",
        idempotency_key=idem,
        payload=json.dumps(payload_data),
    )
    
    if not is_new:
        # Job existiert bereits
        return {
            "status": job.status,
            "job_id": job.id,
            "provider": req.provider,
            "model_id": req.model_id,
            "url": req.url,
            "message": f"Transcription-Job bereits vorhanden (Status: {job.status})"
        }
    
    # Neuer Job - enqueue task
    log_usage(db, org_id, metric="youtube_transcription")
    celery.send_task("tasks.youtube_transcribe", args=[job.id, json.dumps(payload_data)])
    
    # Berechne geschätzte Kosten basierend auf Modell
    estimated_duration_minutes = 5.0  # Schätzung
    # Hole Kosten aus Modell-Info falls verfügbar
    estimated_cost = estimated_duration_minutes * 0.006  # Fallback
    
    return {
        "status": "queued",
        "job_id": job.id,
        "provider": req.provider,
        "model_id": req.model_id,
        "url": req.url,
        "target_language": req.target_language,
        "estimated_duration_minutes": estimated_duration_minutes,
        "estimated_cost": round(estimated_cost, 4),
        "currency": "USD",
        "message": f"Transcription gestartet mit {req.provider}/{req.model_id}"
    }


@router.post("/translate")
async def translate_video(req: TranslateRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Übersetze YouTube Video mit Voice Cloning (originale Stimme beibehalten)"""
    import json
    
    # Hole API-Key aus Credential
    api_key = None
    org_id = req.org_id
    
    if not org_id and user.organizations:
        org_id = user.organizations[0].id
    
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation nicht gefunden. Bitte erstelle eine Organisation."
        )
    
    if req.credential_id:
        assert_org_member(db, user, org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == req.credential_id,
            models.Credential.organization_id == org_id,
            models.Credential.provider == req.voice_cloning_provider
        ).first()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential nicht gefunden"
            )
        api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Fehler beim Entschlüsseln des Credentials"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential-ID ist erforderlich für Video-Übersetzung"
        )
    
    # Validiere Provider
    if req.voice_cloning_provider not in ["rask", "heygen", "elevenlabs", "falai"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unbekannter Voice Cloning Provider: {req.voice_cloning_provider}. Unterstützt: rask, heygen, elevenlabs, falai"
        )
    
    # Quota prüfen
    try:
        enforce_quota(db, org_id, metric="youtube_translation")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    
    # Erstelle Job für Übersetzung
    payload_data = {
        "url": req.url,
        "target_language": req.target_language,
        "source_language": req.source_language,
        "voice_cloning_provider": req.voice_cloning_provider,
        "voice_cloning_model_id": req.voice_cloning_model_id,
        "credential_id": req.credential_id,
        "api_key": api_key  # Wird verschlüsselt gespeichert
    }
    
    idem = f"translate:{req.url}:{req.voice_cloning_provider}:{req.target_language}"
    job, is_new = IdempotencyService.check_and_create_job(
        db=db,
        organization_id=org_id,
        project_id=None,  # Übersetzung hat kein Projekt
        job_type="youtube_translate",
        idempotency_key=idem,
        payload=json.dumps(payload_data),
    )
    
    if not is_new:
        # Job existiert bereits
        return {
            "status": job.status,
            "job_id": job.id,
            "provider": req.voice_cloning_provider,
            "url": req.url,
            "target_language": req.target_language,
            "message": f"Übersetzungs-Job bereits vorhanden (Status: {job.status})"
        }
    
    # Starte Celery Task
    celery.send_task("tasks.youtube_translate", args=[job.id, json.dumps(payload_data)])
    log_usage(db, org_id, metric="youtube_translation")
    
    return {
        "status": "queued",
        "job_id": job.id,
        "provider": req.voice_cloning_provider,
        "url": req.url,
        "target_language": req.target_language,
        "source_language": req.source_language,
        "message": f"Video-Übersetzung gestartet mit {req.voice_cloning_provider}"
    }


@router.get("/voice-models")
async def list_voice_models(
    provider: str,
    credential_id: Optional[str] = None,
    org_id: Optional[str] = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Liste verfügbare Voice Cloning Modelle für einen Provider"""
    api_key = None
    
    if credential_id and org_id:
        assert_org_member(db, user, org_id)
        credential = db.query(models.Credential).filter(
            models.Credential.id == credential_id,
            models.Credential.organization_id == org_id,
            models.Credential.provider == provider
        ).first()
        if credential:
            api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API-Key oder Credential-ID ist erforderlich"
        )
    
    if provider not in ["rask", "heygen", "elevenlabs", "falai"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unbekannter Provider: {provider}"
        )
    
    try:
        client = VoiceTranslationClient(api_key=api_key, provider=provider)
        models = await client.list_models()
        return models
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fehler beim Abrufen der Voice Cloning Modelle: {str(e)}"
        )
