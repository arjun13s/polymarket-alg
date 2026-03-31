from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from polymarket_ai.storage.models import Base


class Database:
    def __init__(self, url: str) -> None:
        if url.startswith("sqlite:///"):
            db_path = Path(url.replace("sqlite:///", "", 1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(url, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, future=True)

    def create_all(self) -> None:
        Base.metadata.create_all(self._engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
