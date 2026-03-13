/**
 * api.js — Centralized API communication layer for Xaminator.
 *
 * All HTTP calls go through this file. Import order in HTML:
 *   <script src="js/api.js"></script>  ← load first
 */

const BASE_URL = 'http://localhost:8000';

// ============================================================
// Token management
// ============================================================

function getAuthToken() {
  return sessionStorage.getItem('xaminator_token');
}

function setAuthToken(token) {
  sessionStorage.setItem('xaminator_token', token);
  sessionStorage.setItem('xaminator_auth', '1'); // Keep for backwards compat
}

function clearAuthToken() {
  sessionStorage.removeItem('xaminator_token');
  sessionStorage.removeItem('xaminator_auth');
}

function isAuthenticated() {
  return !!getAuthToken();
}

// ============================================================
// Core fetch wrapper
// ============================================================

/**
 * Make an HTTP request and return parsed JSON.
 * Throws a descriptive Error on non-2xx responses.
 */
async function _request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  
  // Add auth token if available and not explicitly skipped
  if (!options.skipAuth) {
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const config = {
    headers,
    ...options,
  };
  delete config.skipAuth;

  let response;
  try {
    response = await fetch(url, config);
  } catch (networkErr) {
    throw new Error('Network error — is the backend running on port 8000?');
  }

  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    clearAuthToken();
    // Only redirect if we're not on the login page
    if (!window.location.pathname.includes('index.html') && window.location.pathname !== '/') {
      window.location.href = 'index.html';
    }
    throw new Error('Session expired. Please log in again.');
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

function _post(path, body, options = {}) { 
  return _request(path, { method: 'POST', body: JSON.stringify(body), ...options }); 
}
function _patch(path, body = {}) { return _request(path, { method: 'PATCH',  body: JSON.stringify(body) }); }
function _del(path)              { return _request(path, { method: 'DELETE' }); }

// ============================================================
// Auth API
// ============================================================
const AuthAPI = {
  login: async (username, password) => {
    const response = await _post('/auth/login', { username, password }, { skipAuth: true });
    if (response && response.access_token) {
      setAuthToken(response.access_token);
    }
    return response;
  },
  logout: () => {
    clearAuthToken();
  },
  getCurrentUser: () => _get('/auth/me'),
  isAuthenticated,
};

// ============================================================
// Department API
// ============================================================
const DepartmentAPI = {
  getAll:   (params = {}) => _get('/departments', params),
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
  getAll:      (params = {}) => _get('/halls', params),
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
