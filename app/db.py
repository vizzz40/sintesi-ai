from collections.abc import Iterator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _normalize(url: str) -> str:
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


settings = get_settings()
database_url = _normalize(settings.database_url)
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, connect_args=connect_args)


def init_db() -> None:
    # Drop the old schema if it is still around; the data is only a cache.
    insp = inspect(engine)
    if insp.has_table("topics"):
        columns = {c["name"] for c in insp.get_columns("topics")}
        if "subreddit" in columns:
            SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
