import os
import sys
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.db import Base  # type: ignore
from app import models  # type: ignore


@pytest.fixture(scope="function")
def db():
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
