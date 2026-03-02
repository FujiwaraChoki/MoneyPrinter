import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from db import Base  # noqa: E402
import models  # noqa: F401,E402


@pytest.fixture
def session_factory(tmp_path: Path):
    database_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{database_file}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    yield session_factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def session(session_factory):
    with session_factory() as db_session:
        yield db_session
