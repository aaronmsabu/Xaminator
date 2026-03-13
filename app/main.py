import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
import app.models  # noqa: F401 — registers all ORM models before create_all
from app.models.user import User
from app.auth import get_password_hash
from app.routers import departments, students, exam_halls, exams, seating, auth


def init_default_admin():
    """
    Create a default admin user if no users exist.
    This ensures the first admin can log in and create other users.
    """
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
            admin = User(
                username="admin",
                email="admin@xaminator.local",
                hashed_password=get_password_hash(default_password),
                full_name="System Administrator",
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"Created default admin user (username: admin, password: {default_password})")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: Create tables (for development) and init admin
    # In production, use Alembic migrations instead:
    #   alembic upgrade head
    # Set AUTO_CREATE_TABLES=false in production to disable this
    if os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true":
        Base.metadata.create_all(bind=engine)
    
    init_default_admin()
    yield
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="Xaminator API",
    description="Automated Exam Seat Arrangement System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
# In production, set CORS_ORIGINS env var to your frontend domain(s)
# Example: CORS_ORIGINS=https://xaminator.example.com,https://admin.example.com
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

# For development, allow all origins if CORS_ALLOW_ALL is set
if os.getenv("CORS_ALLOW_ALL", "false").lower() == "true":
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if cors_origins != ["*"] else False,  # Can't use credentials with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes (login/register) - no prefix needed
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(departments.router, prefix="/departments", tags=["Departments"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(exam_halls.router, prefix="/halls", tags=["Exam Halls"])
app.include_router(exams.router, prefix="/exams", tags=["Exams"])
app.include_router(seating.router, tags=["Seat Allocation"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Xaminator API is running"}
