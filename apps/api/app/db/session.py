from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_database_url = get_settings().database_url
_is_sqlite = _database_url.startswith("sqlite")
_engine_options: dict[str, object] = {"echo": get_settings().database_echo}
if _is_sqlite:
    _engine_options["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _database_url:
        _engine_options["poolclass"] = StaticPool

engine = create_engine(_database_url, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if _is_sqlite:

    @event.listens_for(Engine, "connect")
    def _enable_sqlite_foreign_keys(connection: object, _record: object) -> None:
        cursor = connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
