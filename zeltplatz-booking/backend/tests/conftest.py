from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATA = Path(__file__).resolve().parent / ".testdata"
TEST_DATA.mkdir(exist_ok=True)
db_file = TEST_DATA / "booking.db"
if db_file.exists():
    db_file.unlink()

os.environ["DATA_DIR"] = str(TEST_DATA)
os.environ["DEV_MODE"] = "1"
os.environ["API_TOKEN"] = ""

from app.config import get_settings  # noqa: E402
from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_db():
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
