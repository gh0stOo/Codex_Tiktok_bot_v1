from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import anyio
from .. import models, schemas
from ..auth import get_current_user, get_db
from ..authorization import assert_project_member, assert_plan_member
from ..services.orchestrator import Orchestrator
from ..providers.openrouter_client import OpenRouterClient
from ..security import decrypt_secret
from ..config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/generate/{project_id}", response_model=list[schemas.PlanOut])
def generate_calendar(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    start_date = date.today()
    created = []
    for day in range(30):
        for slot in range(1, 4):
            existing = (
                db.query(models.Plan)
                .filter(
                    models.Plan.project_id == project_id,
                    models.Plan.slot_date == start_date + timedelta(days=day),
                    models.Plan.slot_index == slot,
                )
                .first()
            )
            if existing:
                continue
            plan = models.Plan(
                organization_id=project.organization_id,
                project_id=project_id,
                slot_date=start_date + timedelta(days=day),
                slot_index=slot,
                status="scheduled",
            )
            db.add(plan)
            created.append(plan)
    db.commit()
    return db.query(models.Plan).filter(models.Plan.project_id == project_id).all()


@router.get("/calendar/{project_id}", response_model=list[schemas.CalendarSlot])
def get_calendar(project_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    project = assert_project_member(db, user, project_id)
    plans = db.query(models.Plan).filter(models.Plan.project_id == project_id).order_by(models.Plan.slot_date, models.Plan.slot_index).all()
    by_date = {}
    for plan in plans:
        by_date.setdefault(plan.slot_date, []).append(plan)
    # FIX: Sortiere nach Datum (aufsteigend) und Slots innerhalb eines Tages nach slot_index
    sorted_items = sorted(by_date.items())
    result = []
    for date_key, slots in sorted_items:
        # Sortiere Slots innerhalb eines Tages nach slot_index
        sorted_slots = sorted(slots, key=lambda s: s.slot_index)
        result.append(schemas.CalendarSlot(date=date_key, slots=sorted_slots))
    return result


@router.post("/approve/{plan_id}")
def approve_plan(plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan = assert_plan_member(db, user, plan_id, roles=["owner", "admin", "editor"])
    plan.approved = True
    db.commit()
    return {"status": "approved"}


@router.post("/lock/{plan_id}")
def lock_plan(plan_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    plan = assert_plan_member(db, user, plan_id, roles=["owner", "admin"])
    plan.locked = True
    db.commit()
    return {"status": "locked"}


@router.post("/content-plan/{project_id}", response_model=List[schemas.PlanOut])
async def generate_content_plan(
    project_id: str,
    req: schemas.ContentPlanRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Generiere Content-Plan mit Themen für 30 Tage (3 Videos pro Tag)"""
    project = assert_project_member(db, user, project_id)
    
    # Hole OpenRouter API-Key aus Credentials
    credential = db.query(models.Credential).filter(
        models.Credential.organization_id == project.organization_id,
        models.Credential.provider == "openrouter"
    ).first()
    
    if not credential:
        raise HTTPException(status_code=400, detail="OpenRouter API-Key nicht gefunden. Bitte im Credentials-Tab hinzufügen.")
    
    api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
    if not api_key:
        raise HTTPException(status_code=500, detail="Fehler beim Entschlüsseln des API-Keys")
    
    # Generiere Content-Plan mit KI
    client = OpenRouterClient(api_key=api_key)
    
    prompt = f"""Du bist ein Experte für virale TikTok-Content-Strategie. Erstelle einen 30-Tage Content-Plan.

KONTEXT:
- Kategorie: {req.category}
- Hauptthema: {req.topic}
- Ziel: 30 Tage, 3 Videos pro Tag (90 Videos total)

STRATEGIE:
- Jeder Tag hat 3 verschiedene Themen/Aspekte
- Themen sollten abwechslungsreich sein und das Hauptthema aus verschiedenen Perspektiven beleuchten
- Integriere aktuelle TikTok-Trends (2024/2025) natürlich
- Mix aus: Educational, Entertainment, Storytelling, Trends
- Vermeide: Repetitive Themen, erzwungene Trends, zu generische Inhalte

VIRALE ELEMENTE (verteilt über 30 Tage):
- Hook-Variationen: Wissens-Hooks, Test-Hooks, POV-Hooks, Transformation-Hooks
- Format-Variationen: Tutorials, Storytimes, Reactions, Comparisons, Challenges
- Emotionale Variationen: Inspirierend, Unterhaltsam, Informativ, Überraschend

FORMAT (JSON-Array):
[
  {{
    "day": 1,
    "topics": [
      "Thema 1 (mit kurzer Beschreibung warum viral-fähig)",
      "Thema 2 (mit kurzer Beschreibung warum viral-fähig)",
      "Thema 3 (mit kurzer Beschreibung warum viral-fähig)"
    ]
  }},
  ...
]

Antworte NUR mit einem gültigen JSON-Array, keine zusätzlichen Erklärungen."""
    
    if req.feedback:
        prompt += f"\n\nFeedback für Anpassungen: {req.feedback}"
    
    try:
        # Begrenze max_tokens auf 4000 für Content-Plan (reicht für JSON-Array mit 30 Tagen)
        response = await client.complete(prompt, max_tokens=4000)
        content = response.get("script", "")
        
        # Parse JSON (vereinfacht - in Produktion besser validieren)
        import json
        import re
        # Extrahiere JSON aus der Antwort
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if not json_match:
            raise ValueError("Kein gültiges JSON in der Antwort gefunden")
        
        plan_data = json.loads(json_match.group())
        
        # Erstelle/Update Plans in der Datenbank
        start_date = date.today()
        created_plans = []
        
        for day_data in plan_data:
            day_num = day_data.get("day", 1)
            topics = day_data.get("topics", [])
            
            for slot_idx, topic in enumerate(topics[:3], start=1):  # Max 3 Videos pro Tag
                slot_date = start_date + timedelta(days=day_num - 1)
                
                # Prüfe ob Plan existiert
                existing = db.query(models.Plan).filter(
                    models.Plan.project_id == project_id,
                    models.Plan.slot_date == slot_date,
                    models.Plan.slot_index == slot_idx
                ).first()
                
                if existing:
                    # Update bestehenden Plan
                    existing.category = req.category
                    existing.topic = topic
                    existing.status = "scheduled"
                    created_plans.append(existing)
                else:
                    # Erstelle neuen Plan
                    plan = models.Plan(
                        organization_id=project.organization_id,
                        project_id=project_id,
                        slot_date=slot_date,
                        slot_index=slot_idx,
                        status="scheduled",
                        category=req.category,
                        topic=topic
                    )
                    db.add(plan)
                    created_plans.append(plan)
        
        db.commit()
        for plan in created_plans:
            db.refresh(plan)
        
        return created_plans
        
    except RuntimeError as e:
        # RuntimeError von OpenRouterClient (API-Fehler)
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        # JSON-Parsing-Fehler
        raise HTTPException(status_code=500, detail=f"Fehler beim Parsen der KI-Antwort: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei Content-Plan-Generierung: {str(e)}")


@router.post("/generate-script/{plan_id}", response_model=schemas.PlanOut)
async def generate_script(
    plan_id: str,
    req: schemas.ScriptGenerateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Generiere/Regeneriere Script für einen Plan"""
    plan = assert_plan_member(db, user, plan_id, roles=["owner", "admin", "editor"])
    
    if not plan.topic:
        raise HTTPException(status_code=400, detail="Plan hat kein Thema. Bitte zuerst Content-Plan generieren.")
    
    # Hole OpenRouter API-Key
    credential = db.query(models.Credential).filter(
        models.Credential.organization_id == plan.organization_id,
        models.Credential.provider == "openrouter"
    ).first()
    
    if not credential:
        raise HTTPException(status_code=400, detail="OpenRouter API-Key nicht gefunden.")
    
    api_key = decrypt_secret(credential.encrypted_secret, settings.fernet_secret)
    if not api_key:
        raise HTTPException(status_code=500, detail="Fehler beim Entschlüsseln des API-Keys")
    
    client = OpenRouterClient(api_key=api_key)
    
    prompt = f"""Du bist ein Experte für virale TikTok-Videos. Erstelle ein authentisches, trendbasiertes Video-Script.

KONTEXT:
- Kategorie: {plan.category or 'Faceless TikTok'}
- Thema: {plan.topic}
- Tag: {plan.slot_date}, Video {plan.slot_index} von 3
- Ziel: Viral-fähig, aber natürlich und nicht erzwungen

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
  "visual_prompt": "Detaillierte visuelle Beschreibung für Video-Generierung (Beleuchtung, Komposition, Motive, Stil)",
  "lighting": "Beleuchtungsstil (z.B. 'soft natural', 'dramatic', 'ring light')",
  "composition": "Komposition (z.B. 'close-up', 'medium shot', 'wide angle')",
  "camera_angles": "Kamerawinkel (z.B. 'eye-level', 'low angle', 'overhead')",
  "visual_style": "Visueller Stil (z.B. 'minimalist', 'vibrant', 'cinematic')",
  "trend_elements": "Welche aktuellen Trends werden integriert (optional)",
  "viral_potential": "Warum könnte dieses Video viral gehen (kurze Begründung)"
}}

Antworte NUR mit gültigem JSON, keine zusätzlichen Erklärungen."""
    
    if req.feedback:
        prompt += f"\n\nFeedback/Anpassungen: {req.feedback}"
    
    try:
        # Begrenze max_tokens auf 2000 für Script-Generierung (reicht für ein Video-Script)
        response = await client.complete(prompt, max_tokens=2000)
        content = response.get("script", "")
        
        # Parse JSON
        import json
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            raise ValueError("Kein gültiges JSON in der Antwort gefunden")
        
        script_data = json.loads(json_match.group())
        
        # Update Plan mit Script
        plan.hook = script_data.get("hook", "")
        plan.script_content = script_data.get("script", "")
        plan.title = script_data.get("title", "")
        plan.cta = script_data.get("cta", "")
        plan.status = "script_ready"
        
        db.commit()
        db.refresh(plan)
        
        return plan
        
    except RuntimeError as e:
        # RuntimeError von OpenRouterClient (API-Fehler)
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        # JSON-Parsing-Fehler
        raise HTTPException(status_code=500, detail=f"Fehler beim Parsen der KI-Antwort: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei Script-Generierung: {str(e)}")


@router.get("/day/{project_id}/{day_date}", response_model=List[schemas.PlanOut])
def get_day_plans(
    project_id: str,
    day_date: date,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Hole alle Plans für einen bestimmten Tag"""
    project = assert_project_member(db, user, project_id)
    plans = db.query(models.Plan).filter(
        models.Plan.project_id == project_id,
        models.Plan.slot_date == day_date
    ).order_by(models.Plan.slot_index).all()
    return plans
