import pytest

from app import demo_seed
from app.core.config import Settings


def test_production_demo_seed_requires_private_password(monkeypatch):
    monkeypatch.setattr(
        demo_seed,
        "get_settings",
        lambda: Settings(app_env="production"),
    )

    with pytest.raises(RuntimeError, match="Set DEMO_PASSWORD"):
        demo_seed.seed_demo_data()
