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
