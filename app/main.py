from fastapi import FastAPI
from app.database import engine, Base
import app.models  # noqa: F401 — registers all ORM models before create_all
from app.routers import departments, students, exam_halls, exams, seating

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Xaminator API",
    description="Automated Exam Seat Arrangement System",
    version="1.0.0",
)

app.include_router(departments.router, prefix="/departments", tags=["Departments"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(exam_halls.router, prefix="/halls", tags=["Exam Halls"])
app.include_router(exams.router, prefix="/exams", tags=["Exams"])
app.include_router(seating.router, tags=["Seat Allocation"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Xaminator API is running"}
