# Xaminator API Specification

Base URL: `/api/v1`

---

## Department APIs

| Method | Endpoint                   | Description             |
|--------|----------------------------|-------------------------|
| POST   | `/departments`             | Create a new department |
| GET    | `/departments`             | List all departments    |
| GET    | `/departments/{id}`        | Get department by ID    |

### POST /departments
**Request body:**
```json
{ "name": "Computer Science", "code": "CSE" }
```
**Response:** `201 Created` — department object

---

## Student APIs

| Method | Endpoint             | Description                 |
|--------|----------------------|-----------------------------|
| POST   | `/students`          | Register a new student      |
| GET    | `/students`          | List students (filterable)  |
| GET    | `/students/{id}`     | Get student by ID           |
| PATCH  | `/students/{id}`     | Update student details      |
| DELETE | `/students/{id}`     | Remove a student            |

### POST /students
**Request body:**
```json
{
  "register_number": "CSE2024001",
  "full_name": "John Doe",
  "email": "john@college.edu",
  "department_id": 1,
  "semester": 4
}
```
**Validation:**
- `register_number`: 5–20 uppercase alphanumeric characters, unique
- `semester`: 1–12
- `email`: valid email format (optional)

### GET /students
**Query params:** `department_id`, `semester`, `is_active`

---

## Exam Hall APIs

| Method | Endpoint                        | Description             |
|--------|---------------------------------|-------------------------|
| POST   | `/halls`                        | Add a new exam hall     |
| GET    | `/halls`                        | List all exam halls     |
| GET    | `/halls/{id}`                   | Get hall by ID          |
| PATCH  | `/halls/{id}/deactivate`        | Deactivate a hall       |

### POST /halls
**Request body:**
```json
{ "name": "Hall A", "block": "Main Block", "floor": 1, "capacity": 40 }
```
**Validation:** `capacity` > 0

---

## Exam APIs

| Method | Endpoint                   | Description               |
|--------|----------------------------|---------------------------|
| POST   | `/exams`                   | Schedule a new exam       |
| GET    | `/exams`                   | List exams (filterable)   |
| GET    | `/exams/{id}`              | Get exam by ID            |
| PATCH  | `/exams/{id}/status`       | Update exam status        |

### POST /exams
**Request body:**
```json
{
  "title": "Data Structures End Semester",
  "exam_date": "2026-04-15",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "academic_year": "2025-26",
  "semester": 4,
  "department_id": 1
}
```
**Validation:**
- `end_time` must be after `start_time`
- `semester`: 1–12
- `department_id`: nullable (null = all departments sit)

### GET /exams
**Query params:** `status`, `department_id`

### PATCH /exams/{id}/status
Allowed values: `scheduled` | `ongoing` | `completed` | `cancelled`

---

## Seat Allocation APIs

| Method | Endpoint                   | Description                                 |
|--------|----------------------------|---------------------------------------------|
| POST   | `/generate-seating`        | Generate seating arrangement for an exam    |
| GET    | `/seating/{exam_id}`       | Get full seating chart for an exam          |

### POST /generate-seating
**Request body:**
```json
{ "exam_id": 1 }
```
**Algorithm constraints:**
- Hall capacity must not be exceeded
- Students from the same department are interleaved (round-robin) across seats
- Seat numbers are sequential per hall
- Existing allocations for the exam are replaced

**Response:** `201 Created`
```json
{ "message": "Seating generated successfully. 120 students allocated." }
```

### GET /seating/{exam_id}
**Response:**
```json
{
  "exam_id": 1,
  "total_allocated": 120,
  "allocations": [
    {
      "id": 1,
      "seat_number": "1",
      "hall_name": "Hall A",
      "student_name": "John Doe",
      "register_number": "CSE2024001",
      "department_name": "Computer Science"
    }
  ]
}
```

---

## Error Responses

| Status | Meaning                            |
|--------|------------------------------------|
| 400    | Validation error / business rule   |
| 404    | Resource not found                 |
| 422    | Unprocessable entity (Pydantic)    |
| 500    | Internal server error              |
