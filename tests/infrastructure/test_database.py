from rag.infrastructure.database.client import sqlalchemy_url
from rag.infrastructure.database.models import Base


def test_postgresql_dsn_uses_psycopg_sqlalchemy_dialect() -> None:
    assert sqlalchemy_url("postgresql://user:pass@localhost/rag") == (
        "postgresql+psycopg://user:pass@localhost/rag"
    )


def test_sqlalchemy_metadata_contains_the_fact_tables() -> None:
    assert set(Base.metadata.tables) == {"documents", "chunks"}
