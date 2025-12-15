import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.services.orchestrator import Orchestrator  # type: ignore


def test_orchestrator_schema_valid():
    orch = Orchestrator()
    completion = orch.llm.complete("test")
    assert {"title", "script", "cta"}.issubset(completion.keys())
