from pathlib import Path

from alembic.config import Config

from alembic import command
from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def upgrade_database() -> None:
    api_dir = Path(__file__).resolve().parents[2]
    migration_config = Config(str(api_dir / "alembic.ini"))
    migration_config.set_main_option("script_location", str(api_dir / "alembic"))
    migration_config.set_main_option(
        "sqlalchemy.url", get_settings().database_url.replace("%", "%%")
    )
    with engine.connect() as connection:
        migration_config.attributes["connection"] = connection
        command.upgrade(migration_config, "head")
