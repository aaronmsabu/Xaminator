import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./xaminator.db",  # SQLite for local development
)

# Configure engine based on database type
connect_args = {}
engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific settings
    connect_args = {"check_same_thread": False}
else:
    # MySQL/PostgreSQL settings
    engine_kwargs = {
        "pool_pre_ping": True,    # Detects stale connections before use
        "pool_recycle": 3600,     # Recycle connections every hour
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
