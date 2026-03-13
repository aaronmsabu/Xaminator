# Xaminator

Automated Exam Seat Arrangement System for college exam cells. Xaminator automates the process of distributing students across exam halls with an anti-cheating interleaving strategy.

## Features

- **Department Management**: Create and manage academic departments
- **Student Registration**: Register students with department and semester information
- **Exam Hall Management**: Configure exam halls with capacity and block/floor details
- **Exam Scheduling**: Schedule exams with date, time, and semester
- **Automated Seating Generation**: Generate seating arrangements with:
  - Department-based interleaving to minimize cheating opportunities
  - Random shuffling within departments for per-run variation
  - Automatic capacity validation
  - Idempotent regeneration (safe to re-run)
- **JWT-based Authentication**: Secure API endpoints with token-based auth

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.x, FastAPI, Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | MySQL (via PyMySQL) |
| Authentication | JWT (python-jose), bcrypt |
| Frontend | Vanilla HTML5/CSS3/JavaScript |
| Testing | pytest |

## Quick Start

### Prerequisites

- Python 3.9+
- MySQL 8.0+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Xaminator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and secret key
   ```

5. **Create the database**
   ```sql
   CREATE DATABASE xaminator_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

6. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

   The API will be available at `http://localhost:8000`.

7. **Access the frontend**
   
   Open `frontend/index.html` in a browser, or serve it with a local server:
   ```bash
   cd frontend
   python -m http.server 5500
   ```
   Then open `http://localhost:5500`

### Default Credentials

On first run, a default admin user is created:
- **Username**: `admin`
- **Password**: `admin123` (configurable via `DEFAULT_ADMIN_PASSWORD` env var)

**Important**: Change the default password in production!

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | `mysql+pymysql://root:password@localhost/xaminator_db` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Auto-generated (insecure for dev) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity duration | `60` |
| `DEFAULT_ADMIN_PASSWORD` | Initial admin password | `admin123` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:3000,...` |
| `CORS_ALLOW_ALL` | Allow all origins (dev only) | `false` |

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## Project Structure

```
Xaminator/
├── app/
│   ├── main.py           # FastAPI app, middleware, routes
│   ├── database.py       # SQLAlchemy engine & session
│   ├── auth.py           # JWT authentication utilities
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic DTOs
│   ├── routers/          # HTTP route handlers
│   └── services/         # Business logic (seating algorithm)
├── frontend/
│   ├── *.html            # Admin panel pages
│   ├── css/styles.css    # Global stylesheet
│   └── js/               # API client & page scripts
├── tests/                # Pytest test suite
├── requirements.txt
├── .env.example
└── README.md
```

## Seating Algorithm

The seating generation uses a department-interleaving strategy:

1. Students are grouped by department
2. Each group is shuffled randomly
3. Students are distributed in round-robin order across departments
4. This ensures adjacent seats belong to different departments, reducing cheating opportunities

## Security Notes

- All API endpoints (except `/auth/login`) require JWT authentication
- Passwords are hashed using bcrypt
- CORS is configured to specific origins in production
- Set a strong `SECRET_KEY` in production (minimum 32 characters)

## License

MIT
