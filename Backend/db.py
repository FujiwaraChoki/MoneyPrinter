import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from dotenv import load_dotenv
from utils import ENV_FILE


load_dotenv(ENV_FILE)


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    return "sqlite:///moneyprinter.db"


DATABASE_URL = _database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def init_db() -> None:
    from models import Artifact, GenerationEvent, GenerationJob, Project, Script  # noqa: F401

    Base.metadata.create_all(bind=engine)
