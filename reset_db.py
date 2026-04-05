import os
from dotenv import load_dotenv
from sqlalchemy import text
import app.models  # Load all models
from app.database import engine, Base

load_dotenv()

print(f"Connecting to database to drop all tables...")

with engine.connect() as conn:
    # Disable foreign key checks so we can drop tables in any order
    if "sqlite" not in str(engine.url):
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
    # Drop all tables managed by SQLAlchemy
    Base.metadata.drop_all(bind=engine)
    
    # Also drop the alembic_version table to reset migration state
    conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
    
    # Re-enable foreign key checks
    if "sqlite" not in str(engine.url):
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        
    conn.commit()

print("All tables dropped successfully!")
print("Run the following command to recreate the schema:")
print("alembic upgrade head")
