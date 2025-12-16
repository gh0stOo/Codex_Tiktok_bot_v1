import json
import tempfile
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
from ..providers.openrouter_client import OpenRouterClient
from ..providers.storage import get_storage, tenant_prefix
from ..providers.tiktok_official import TikTokClient
from ..providers.video_provider import FFmpegVideoProvider
from ..providers.falai_video_provider import FalAIVideoProvider
from ..services.usage import log_usage
from ..security import decrypt_secret

settings = get_settings()


class ScriptSpec(BaseModel):
    title: str
    script: str
    cta: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    # Visuelle Felder (optional)
    hook: str | None = None
    visual_prompt: str | None = None
    lighting: str | None = None
    composition: str | None = None
    camera_angles: str | None = None
    visual_style: str | None = None


class PolicyEngine:
    banned_terms = ["finance", "investment", "crypto", "medical", "health advice", "gambling"]

    def check(self, text: str) -> None:
        for term in self.banned_terms:
            if term.lower() in text.lower():
                raise ValueError(f"Content violates policy: {term}")


class DeterministicLLM:
    """Deterministic Fallback ohne externe Abhängigkeit."""

    def complete(self, prompt: str) -> dict:
        return {
            "title": "Autopilot Script",
            "script": f"{prompt} - generated",
            "cta": "Follow for more",
            "rationale": "deterministic",
            "confidence": 0.5,
        }


def rule_based_script(project: models.Project, plan: models.Plan | None) -> ScriptSpec:
    slot = f"Slot {plan.slot_index} am {plan.slot_date}" if plan else "Ad-hoc Post"
    return ScriptSpec(
        title=f"{project.name}: {slot}",
        script=f"Warum {project.name} heute relevant ist. {slot}. Kurz und prägnant.",
        cta="Folge für mehr kurze Insights.",
        rationale="Deterministic generator (no external dependency).",
        confidence=0.42,
    )


class Orchestrator:
    def __init__(self):
        self.video = FFmpegVideoProvider(settings.ffmpeg_path)
        self.storage = get_storage()
        self.policy = PolicyEngine()
        self.llm = DeterministicLLM()

    def _repair(self, payload: str | dict) -> ScriptSpec:
        data = payload
        if isinstance(payload, str):
            try:
                data = json.loads(payload)
            except Exception:
                data = {"title": "Auto Script", "script": payload, "cta": "Follow for more", "rationale": "repair", "confidence": 0.5}
        try:
            return ScriptSpec.model_validate(data)
        except ValidationError:
            return ScriptSpec(
                title=data.get("title", "Auto Script"),
                script=data.get("script", str(data)),
                cta=data.get("cta", "Follow for more"),
                rationale=data.get("rationale", "fallback"),
                confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
                hook=data.get("hook"),
                visual_prompt=data.get("visual_prompt"),
                lighting=data.get("lighting"),
                composition=data.get("composition"),
                camera_angles=data.get("camera_angles"),
                visual_style=data.get("visual_style"),
            )

    async def _generate_script(self, db: Session, project: models.Project, plan: models.Plan | None) -> ScriptSpec:
        # Wenn Plan ein Script hat, verwende es direkt
        if plan and plan.script_content:
            return ScriptSpec(
                title=plan.title or f"{project.name}: {plan.topic or 'Video'}",
                script=plan.script_content,
                cta=plan.cta or "Folge für mehr",
                rationale="From plan script_content",
                confidence=0.9,
            )
        
        base_spec = rule_based_script(project, plan)
        
        # FIX: Verwende gespeichertes Modell aus Projekt-Einstellungen
        # Script-Generierung ist FEST auf GPT-4.0 Mini (nicht auswählbar)
        model_id = "openai/gpt-4o-mini"
        provider = "openrouter"
        api_key = None
        
        # Hole API-Key aus Credential falls vorhanden (für OpenRouter)
        # Suche nach OpenRouter Credential in der Organisation
        if project.video_credential_id:
            credential = db.query(models.Credential).filter(
                models.Credential.id == project.video_credential_id,
                models.Credential.organization_id == project.organization_id,
                models.Credential.provider == "openrouter"  # Script-Generierung verwendet OpenRouter
            ).first()
            if credential:
                api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
        
        # Fallback: Suche nach beliebigem OpenRouter Credential in der Organisation
        if not api_key:
            openrouter_credential = db.query(models.Credential).filter(
                models.Credential.organization_id == project.organization_id,
                models.Credential.provider == "openrouter"
            ).first()
            if openrouter_credential:
                api_key = decrypt_secret(openrouter_credential.encrypted_secret, settings.fernet_secret)
        
        # Fallback auf globale Einstellung
        if not api_key:
            api_key = settings.openrouter_api_key
        
        if not api_key:
            # Nur OpenRouter wird für Script-Generierung unterstützt
            return base_spec
        
        # FIX: Detaillierter Prompt mit visuellen Beschreibungen (wie in plans.py)
        plan_context = ""
        if plan:
            plan_context = f"""
KONTEXT:
- Kategorie: {plan.category or 'Faceless TikTok'}
- Thema: {plan.topic or 'Allgemein'}
- Tag: {plan.slot_date}, Video {plan.slot_index} von 3
- Projekt: {project.name}
"""
        else:
            plan_context = f"""
KONTEXT:
- Projekt: {project.name}
- Video: Ad-hoc Generierung
"""
        
        prompt = f"""Du bist ein Experte für virale TikTok-Videos. Erstelle ein authentisches, trendbasiertes Video-Script.
{plan_context}
Ziel: Viral-fähig, aber natürlich und nicht erzwungen

VIRALE HOOK-FORMELN (wähle passend):
1. "Du wusstest nicht, dass..." (Wissens-Hook)
2. "Ich habe X getestet und..." (Test-Hook)
3. "Das wird dein Leben verändern..." (Transformation-Hook)
4. "POV: Du..." (POV-Hook)
5. "Wenn du X machst, passiert Y..." (Konsequenz-Hook)
6. "Die Wahrheit über X..." (Revelation-Hook)

SCRIPT-STRUKTUR:
- Hook (0-3s): Fesselnd, neugierig machend, emotional
- Setup (3-8s): Kontext geben, Problem/Interesse etablieren
- Value (8-45s): Hauptinhalt, Mehrwert, Storytelling
- CTA (45-60s): Natürlicher Aufruf, nicht aufdringlich

VISUELLE BESCHREIBUNG (für Video-Generierung):
- Beleuchtung: Natürlich, weich, oder dramatisch (je nach Thema)
- Komposition: Close-up für Emotion, Medium Shot für Kontext, Wide für Atmosphäre
- Kamerawinkel: Eye-level für Authentizität, Low Angle für Power, Overhead für Tutorials
- Stil: Minimalistisch für Fokus, Vibrant für Energie, Cinematic für Storytelling
- Motive: Relevante visuelle Elemente, die das Thema unterstützen

TREND-INTEGRATION:
- Nutze aktuelle TikTok-Trends (2024/2025): CapCut-Templates, Sound-Trends, Format-Trends
- Aber: Integriere Trends natürlich, nicht erzwungen
- Fokus auf: Storytelling, Emotion, Mehrwert

TONALITÄT:
- Authentisch, nicht verkaufsorientiert
- Freundlich, aber nicht übertrieben
- Informativ, aber unterhaltsam
- Natürliche Sprache, keine Marketing-Floskeln

FORMAT (JSON):
{{
  "hook": "Fesselnder Hook (max 15 Wörter, erste 3 Sekunden)",
  "script": "Vollständiges Script (15-60 Sekunden, natürliche Sprache)",
  "title": "Video-Titel (SEO-optimiert, aber natürlich)",
  "cta": "Call-to-Action (natürlich, nicht aufdringlich)",
  "rationale": "Warum dieses Script viral-fähig ist (kurze Begründung)",
  "confidence": 0.8,
  "visual_prompt": "Detaillierte visuelle Beschreibung für Video-Generierung (Beleuchtung, Komposition, Motive, Stil)",
  "lighting": "Beleuchtungsstil (z.B. 'soft natural', 'dramatic', 'ring light')",
  "composition": "Komposition (z.B. 'close-up', 'medium shot', 'wide angle')",
  "camera_angles": "Kamerawinkel (z.B. 'eye-level', 'low angle', 'overhead')",
  "visual_style": "Visueller Stil (z.B. 'minimalist', 'vibrant', 'cinematic')"
}}

Antworte NUR mit gültigem JSON, keine zusätzlichen Erklärungen."""
        try:
            client = OpenRouterClient(api_key=api_key)
            # FIX: Verwende gespeichertes Modell
            completion = await client.complete(prompt, model_id=model_id)
            candidate = completion.get("script") or completion.get("content") or completion.get("raw")
            return self._repair(candidate)
        except Exception:
            return base_spec

    async def generate_assets(self, db: Session, project: models.Project, plan: models.Plan | None = None) -> models.VideoAsset:
        script_spec = await self._generate_script(db, project, plan)
        # Nur Policy-Check für AI-generierte Scripts, nicht für manuell erstellte/bearbeitete
        # Wenn Plan ein Script hat, wurde es vom User erstellt/bearbeitet und sollte nicht geprüft werden
        if not plan or not plan.script_content:
            # Nur für AI-generierte Scripts Policy-Check durchführen
            self.policy.check(script_spec.script)
            self.policy.check(script_spec.cta)
            
            # FIX: Speichere visuelle Felder im Plan, wenn vorhanden
            if plan:
                if script_spec.hook:
                    plan.hook = script_spec.hook
                if script_spec.visual_prompt:
                    plan.visual_prompt = script_spec.visual_prompt
                if script_spec.lighting:
                    plan.lighting = script_spec.lighting
                if script_spec.composition:
                    plan.composition = script_spec.composition
                if script_spec.camera_angles:
                    plan.camera_angles = script_spec.camera_angles
                if script_spec.visual_style:
                    plan.visual_style = script_spec.visual_style
                # Speichere auch Script, Title, CTA falls noch nicht vorhanden
                if not plan.script_content:
                    plan.script_content = script_spec.script
                if not plan.title:
                    plan.title = script_spec.title
                if not plan.cta:
                    plan.cta = script_spec.cta
                db.add(plan)

        with tempfile.TemporaryDirectory() as tmpdir:
            video_tmp = Path(tmpdir) / "video.mp4"
            thumb_tmp = Path(tmpdir) / "thumb.jpg"
            
            # Video-Generierung: Verwende visual_prompt mit Text-to-Video API (statt FFmpeg)
            # Prüfe ob visual_prompt vorhanden ist und Video-Generierungs-Einstellungen gesetzt sind
            visual_prompt = None
            if plan:
                visual_prompt = plan.visual_prompt
            
            # Falls kein visual_prompt, erstelle einen aus Script und visuellen Feldern
            if not visual_prompt and plan:
                visual_prompt_parts = []
                if plan.script_content:
                    visual_prompt_parts.append(f"Content: {plan.script_content[:200]}")
                if plan.lighting:
                    visual_prompt_parts.append(f"Lighting: {plan.lighting}")
                if plan.composition:
                    visual_prompt_parts.append(f"Composition: {plan.composition}")
                if plan.camera_angles:
                    visual_prompt_parts.append(f"Camera angles: {plan.camera_angles}")
                if plan.visual_style:
                    visual_prompt_parts.append(f"Visual style: {plan.visual_style}")
                if visual_prompt_parts:
                    visual_prompt = ". ".join(visual_prompt_parts)
            
            # Falls immer noch kein visual_prompt, verwende Script als Fallback
            if not visual_prompt:
                visual_prompt = script_spec.script[:500]  # Max 500 Zeichen
            
            # Verwende Video-Generierungs-Einstellungen aus Project
            video_provider_name = project.video_generation_provider or "falai"
            video_model_id = project.video_generation_model_id or "fal-ai/kling-video/v2.6/pro/text-to-video"
            video_credential_id = project.video_generation_credential_id
            
            # Hole API-Key für Video-Generierung
            video_api_key = None
            if video_credential_id:
                credential = db.query(models.Credential).filter(
                    models.Credential.id == video_credential_id,
                    models.Credential.organization_id == project.organization_id,
                    models.Credential.provider == video_provider_name
                ).first()
                if credential:
                    video_api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
            
            # Generiere Video mit Text-to-Video API (falls konfiguriert) oder FFmpeg Fallback
            if video_provider_name == "falai" and video_api_key:
                try:
                    video_provider = FalAIVideoProvider(api_key=video_api_key)
                    result = await video_provider.generate_video(
                        visual_prompt=visual_prompt,
                        output_path=str(video_tmp),
                        model_id=video_model_id,
                        duration=60  # 60 Sekunden für TikTok
                    )
                    video_tmp = Path(result["video_path"])
                    thumb_tmp = Path(result["thumbnail_path"])
                except Exception as e:
                    # Fallback zu FFmpeg bei Fehler
                    self.video.render(script_spec.script, str(video_tmp), str(thumb_tmp))
            else:
                # Fallback zu FFmpeg (sollte nicht mehr verwendet werden, aber für Kompatibilität)
                self.video.render(script_spec.script, str(video_tmp), str(thumb_tmp))

            prefix = tenant_prefix(project.organization_id, project.id, plan.id if plan else "adhoc")
            video_key = f"{prefix}/final.mp4"
            thumb_key = f"{prefix}/thumbnail.jpg"
            video_uri = self.storage.save_file(video_key, str(video_tmp))
            thumb_uri = self.storage.save_file(thumb_key, str(thumb_tmp))
            # log storage usage in MB (rough)
            try:
                size_mb = max(1, int(video_tmp.stat().st_size / (1024 * 1024)))
                log_usage(db, project.organization_id, metric="storage_mb", amount=size_mb)
            except Exception:
                pass

        asset = models.VideoAsset(
            organization_id=project.organization_id,
            project_id=project.id,
            plan_id=plan.id if plan else None,
            status="generated",
            video_path=str(video_uri),
            thumbnail_path=str(thumb_uri),
            transcript="",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    async def publish_now(self, asset: models.VideoAsset, access_token: str, open_id: str, caption: str = "Auto-post", use_inbox: bool = False) -> dict:
        # ensure video is local; if stored remotely, fetch to temp
        video_path = asset.video_path
        local_path = video_path
        tmpdir = None
        try:
            if not Path(video_path).exists():
                from ..providers.storage import get_storage
                storage = get_storage()
                data = storage.read_bytes_uri(video_path)
                tmpdir = tempfile.TemporaryDirectory()
                local_path = str(Path(tmpdir.name) / "upload.mp4")
                Path(local_path).write_bytes(data)
            # FIX: Pass organization_id for rate limiting
            client = TikTokClient(organization_id=asset.organization_id)
            idem = f"pub-{asset.id}"
            if use_inbox:
                result = await client.upload_video_inbox(
                    access_token=access_token,
                    open_id=open_id,
                    video_path=local_path,
                    caption=caption,
                    idempotency_key=idem,
                )
            else:
                result = await client.upload_video(
                    access_token=access_token,
                    open_id=open_id,
                    video_path=local_path,
                    caption=caption,
                    idempotency_key=idem,
                )
            return result
        finally:
            # cleanup temp if used
            if tmpdir:
                try:
                    tmpdir.cleanup()
                except Exception:
                    pass
