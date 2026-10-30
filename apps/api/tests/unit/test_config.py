import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgres://db.example/deposit360", "postgresql+psycopg://db.example/deposit360"),
        ("postgresql://db.example/deposit360", "postgresql+psycopg://db.example/deposit360"),
        (
            "postgresql+psycopg://db.example/deposit360",
            "postgresql+psycopg://db.example/deposit360",
        ),
        ("sqlite:///./deposit360.db", "sqlite:///./deposit360.db"),
    ],
)
def test_database_url_uses_supported_postgres_driver(database_url: str, expected: str):
    assert Settings(database_url=database_url).database_url == expected


def test_vercel_upload_limit_stays_below_function_payload_limit(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")

    assert Settings(max_upload_size_mb=20).max_upload_size_bytes == 4 * 1024 * 1024
