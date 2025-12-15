from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from ..services.orchestrator import Orchestrator
from ..auth import get_current_user

router = APIRouter()
orch = Orchestrator()


class TranscribeRequest(BaseModel):
    url: str
    target_language: str = "en"


@router.post("/transcribe")
def transcribe(req: TranscribeRequest, user=Depends(get_current_user)):
    # Real integration pending: reject instead of returning mock to avoid fake data in prod path.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Transcription provider not configured. Configure ASR + translation credentials to enable.",
    )
