from app.db import normalize_database_url


def test_render_postgres_url_uses_psycopg3_dialect() -> None:
    assert normalize_database_url(
        "postgresql://user:password@host:5432/callflow"
    ) == "postgresql+psycopg://user:password@host:5432/callflow"


def test_non_postgres_urls_are_unchanged() -> None:
    assert normalize_database_url("sqlite:///./callflow.db") == "sqlite:///./callflow.db"
