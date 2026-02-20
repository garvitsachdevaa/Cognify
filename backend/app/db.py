"""
Database connection and session utilities.
Uses SQLAlchemy 2.0 (sync) with psycopg3 driver.
Dialect: postgresql+psycopg://
"""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # auto-reconnect on stale connections
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Run the initial SQL migration on startup if tables don't exist."""
    sql_path = Path(__file__).parent.parent / "migrations" / "001_init.sql"
    if not sql_path.exists():
        print("[DB] Migration file not found, skipping.")
        return

    with engine.connect() as conn:
        sql = sql_path.read_text()
        conn.execute(text(sql))
        conn.commit()
    print("[DB] Migrations applied.")
