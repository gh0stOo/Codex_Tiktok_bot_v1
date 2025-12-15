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
from ..services.usage import log_usage

settings = get_settings()


class ScriptSpec(BaseModel):
    title: str
    script: str
    cta: str
    rationale: str
    confidence: float = Field(ge=0, le=1)


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
            )

    async def _generate_script(self, project: models.Project, plan: models.Plan | None) -> ScriptSpec:
        base_spec = rule_based_script(project, plan)
        if not settings.openrouter_api_key:
            return base_spec
        prompt = (
            "Erzeuge ein JSON für einen TikTok-Post auf Deutsch. Felder: title, script, cta, rationale, confidence (0-1). "
            f"Projekt: {project.name}. Slot: {plan.slot_index if plan else 'adhoc'}."
        )
        try:
            client = OpenRouterClient()
            completion = await client.complete(prompt)
            candidate = completion.get("script") or completion.get("content") or completion.get("raw")
            return self._repair(candidate)
        except Exception:
            return base_spec

    async def generate_assets(self, db: Session, project: models.Project, plan: models.Plan | None = None) -> models.VideoAsset:
        script_spec = await self._generate_script(project, plan)
        self.policy.check(script_spec.script)
        self.policy.check(script_spec.cta)

        with tempfile.TemporaryDirectory() as tmpdir:
            video_tmp = Path(tmpdir) / "video.mp4"
            thumb_tmp = Path(tmpdir) / "thumb.jpg"
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
        if not Path(video_path).exists():
            from ..providers.storage import get_storage
            storage = get_storage()
            data = storage.read_bytes_uri(video_path)
            tmpdir = tempfile.TemporaryDirectory()
            local_path = str(Path(tmpdir.name) / "upload.mp4")
            Path(local_path).write_bytes(data)
        client = TikTokClient()
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
        # cleanup temp if used
        if local_path != video_path:
            Path(local_path).unlink(missing_ok=True)
        return result
