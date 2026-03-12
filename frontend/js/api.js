/**
 * api.js — Centralized API communication layer for Xaminator.
 *
 * All HTTP calls go through this file. Import order in HTML:
 *   <script src="js/api.js"></script>  ← load first
 */

const BASE_URL = 'http://localhost:8000';

// ============================================================
// Core fetch wrapper
// ============================================================

/**
 * Make an HTTP request and return parsed JSON.
 * Throws a descriptive Error on non-2xx responses.
 */
async function _request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };

  let response;
  try {
    response = await fetch(url, config);
  } catch (networkErr) {
    throw new Error('Network error — is the backend running on port 8000?');
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = body.detail || body.message || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  // 204 No Content
  if (response.status === 204) return null;
  return response.json();
}

function _get(path, params = {}) {
  const qs = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== '')
  ).toString();
  return _request(qs ? `${path}?${qs}` : path, { method: 'GET' });
}

function _post(path, body)       { return _request(path, { method: 'POST',   body: JSON.stringify(body) }); }
function _patch(path, body = {}) { return _request(path, { method: 'PATCH',  body: JSON.stringify(body) }); }
function _del(path)              { return _request(path, { method: 'DELETE' }); }

// ============================================================
// Department API
// ============================================================
const DepartmentAPI = {
  getAll:   ()     => _get('/departments'),
  getById:  (id)   => _get(`/departments/${id}`),
  create:   (data) => _post('/departments', data),
};

// ============================================================
// Student API
// ============================================================
const StudentAPI = {
  getAll:   (params = {}) => _get('/students', params),
  getById:  (id)          => _get(`/students/${id}`),
  create:   (data)        => _post('/students', data),
  update:   (id, data)    => _patch(`/students/${id}`, data),
  delete:   (id)          => _del(`/students/${id}`),
};

// ============================================================
// Exam Hall API
// ============================================================
const HallAPI = {
  getAll:      ()     => _get('/halls'),
  getById:     (id)   => _get(`/halls/${id}`),
  create:      (data) => _post('/halls', data),
  deactivate:  (id)   => _patch(`/halls/${id}/deactivate`),
};

// ============================================================
// Exam API
// ============================================================
const ExamAPI = {
  getAll:        (params = {})     => _get('/exams', params),
  getById:       (id)              => _get(`/exams/${id}`),
  create:        (data)            => _post('/exams', data),
  updateStatus:  (id, status)      => _patch(`/exams/${id}/status`, { status }),
};

// ============================================================
// Seating API
// ============================================================
const SeatingAPI = {
  generate:   (examId) => _post('/generate-seating', { exam_id: examId }),
  getByExam:  (examId) => _get(`/seating/${examId}`),
};
