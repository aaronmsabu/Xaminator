-- ============================================================
-- Xaminator - MySQL Database Schema
-- Automated Exam Seat Arrangement System
-- ============================================================

-- MySQL requires foreign key checks to be enabled (default ON).
-- Run each CREATE TABLE in dependency order (no forward references).

-- ============================================================
-- DEPARTMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id          INT             NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)    NOT NULL,
    code        VARCHAR(20)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_departments_name (name),
    UNIQUE KEY uq_departments_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- STUDENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id              INT             NOT NULL AUTO_INCREMENT,
    register_number VARCHAR(30)     NOT NULL,
    full_name       VARCHAR(150)    NOT NULL,
    email           VARCHAR(255),
    department_id   INT             NOT NULL,
    semester        SMALLINT        NOT NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_students_register_number (register_number),
    UNIQUE KEY uq_students_email (email),
    KEY idx_students_department_id (department_id),
    CONSTRAINT chk_students_semester CHECK (semester BETWEEN 1 AND 12),
    CONSTRAINT fk_students_department
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- EXAM HALLS
-- ============================================================
CREATE TABLE IF NOT EXISTS exam_halls (
    id          INT             NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100)    NOT NULL,
    block       VARCHAR(50),
    floor       SMALLINT,
    capacity    SMALLINT        NOT NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_exam_halls_name (name),
    CONSTRAINT chk_exam_halls_capacity CHECK (capacity > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- EXAMS
-- ============================================================
CREATE TABLE IF NOT EXISTS exams (
    id              INT             NOT NULL AUTO_INCREMENT,
    title           VARCHAR(200)    NOT NULL,
    exam_date       DATE            NOT NULL,
    start_time      TIME            NOT NULL,
    end_time        TIME            NOT NULL,
    academic_year   VARCHAR(20)     NOT NULL,
    semester        SMALLINT        NOT NULL,
    department_id   INT,                             -- NULL = all departments
    status          VARCHAR(20)     NOT NULL DEFAULT 'scheduled',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_exams_exam_date     (exam_date),
    KEY idx_exams_department_id (department_id),
    KEY idx_exams_status        (status),
    CONSTRAINT chk_exams_semester CHECK (semester BETWEEN 1 AND 12),
    CONSTRAINT chk_exams_status  CHECK (status IN ('scheduled','ongoing','completed','cancelled')),
    CONSTRAINT chk_exams_times   CHECK (end_time > start_time),
    CONSTRAINT fk_exams_department
        FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- SEAT ALLOCATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS seat_allocations (
    id          INT             NOT NULL AUTO_INCREMENT,
    exam_id     INT             NOT NULL,
    student_id  INT             NOT NULL,
    hall_id     INT             NOT NULL,
    seat_number VARCHAR(20)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    -- A student can only have one seat per exam
    UNIQUE KEY uq_allocation_exam_student (exam_id, student_id),
    -- Seat numbers must be unique per hall per exam
    UNIQUE KEY uq_allocation_hall_seat    (exam_id, hall_id, seat_number),
    KEY idx_seat_alloc_student_id (student_id),
    KEY idx_seat_alloc_hall_id    (hall_id),
    CONSTRAINT fk_seat_alloc_exam
        FOREIGN KEY (exam_id)    REFERENCES exams(id)       ON DELETE CASCADE,
    CONSTRAINT fk_seat_alloc_student
        FOREIGN KEY (student_id) REFERENCES students(id)    ON DELETE CASCADE,
    CONSTRAINT fk_seat_alloc_hall
        FOREIGN KEY (hall_id)    REFERENCES exam_halls(id)  ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

