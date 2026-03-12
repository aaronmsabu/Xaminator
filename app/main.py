from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
import app.models  # noqa: F401 — registers all ORM models before create_all
from app.routers import departments, students, exam_halls, exams, seating

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Xaminator API",
    description="Automated Exam Seat Arrangement System",
    version="1.0.0",
)

# Allow the frontend (any origin during development) to reach the API.
# In production, restrict allow_origins to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(departments.router, prefix="/departments", tags=["Departments"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(exam_halls.router, prefix="/halls", tags=["Exam Halls"])
app.include_router(exams.router, prefix="/exams", tags=["Exams"])
app.include_router(seating.router, tags=["Seat Allocation"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Xaminator API is running"}
