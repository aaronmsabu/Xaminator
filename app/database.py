import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost/xaminator_db",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # Detects stale connections before use
    pool_recycle=3600,     # Recycle connections every hour; prevents "MySQL has gone away"
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
