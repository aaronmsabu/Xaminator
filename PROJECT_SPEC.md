Project: Xaminator

Xaminator is an automated exam seat arrangement system for colleges.

Problem:
Exam cells currently generate seating arrangements manually which is time consuming and error prone.

Goal:
Automatically allocate seats to students across exam halls while respecting constraints.

Users:
- Exam Cell Admin
- Invigilators
- Students (view seat allocation)

Tech Stack:
Backend: FastAPI
Database: PostgreSQL
ORM: SQLAlchemy
NoSQL: MongoDB
Frontend: HTML, CSS, JavaScript

Core Features:
- Manage students
- Manage departments
- Manage exam halls
- Create exams
- Generate seating arrangement
- View seating allocation
- Export seating reports

Seat Allocation Constraints:
- Hall capacity must not be exceeded
- Seat numbers must be unique
- Students from the same department should be distributed across halls
- Seat allocation should be randomized to reduce cheating

System Modules:
1. Student Management
2. Exam Hall Management
3. Exam Scheduling
4. Seat Allocation Engine
5. Seating Visualization
6. Reporting