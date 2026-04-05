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
  const headers = { ...options.headers };
  
  // Only set Content-Type for non-FormData requests
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  
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
function _put(path, body = {}) { return _request(path, { method: 'PUT',  body: JSON.stringify(body) }); }
function _del(path)              { return _request(path, { method: 'DELETE' }); }

/**
 * Upload a file via multipart/form-data
 */
async function _uploadFile(path, file, additionalParams = {}) {
  const formData = new FormData();
  formData.append('file', file);
  
  // Build query string for additional params
  const qs = new URLSearchParams(
    Object.entries(additionalParams).filter(([, v]) => v !== null && v !== undefined && v !== '')
  ).toString();
  const fullPath = qs ? `${path}?${qs}` : path;
  
  return _request(fullPath, { 
    method: 'POST', 
    body: formData,
    // Don't set Content-Type - browser will set it with boundary for FormData
  });
}

/**
 * Download a file (returns a Blob)
 */
async function _downloadFile(path) {
  const url = `${BASE_URL}${path}`;
  const token = getAuthToken();
  
  const response = await fetch(url, {
    method: 'GET',
    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
  });
  
  if (!response.ok) {
    throw new Error(`Download failed: ${response.status} ${response.statusText}`);
  }
  
  return response.blob();
}

/**
 * Trigger a file download in the browser
 */
function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}

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
  count:    (params = {}) => _get('/students/count', params),
  
  // Bulk operations
  downloadTemplate: async () => {
    const blob = await _downloadFile('/students/template.csv');
    downloadBlob(blob, 'students_template.csv');
  },
  bulkUpload: (file, onDuplicate = 'skip') => _uploadFile('/students/bulk', file, { on_duplicate: onDuplicate }),
};

// ============================================================
// Exam Hall API
// ============================================================
const HallAPI = {
  getAll:      (params = {}) => _get('/halls', params),
  getById:     (id)   => _get(`/halls/${id}`),
  create:      (data) => _post('/halls', data),
  deactivate:  (id)   => _patch(`/halls/${id}/deactivate`),
  activate:    (id)   => _patch(`/halls/${id}/activate`),
  
  // Bulk operations
  downloadTemplate: async () => {
    const blob = await _downloadFile('/halls/template.csv');
    downloadBlob(blob, 'halls_template.csv');
  },
  bulkUpload: (file) => _uploadFile('/halls/bulk', file),
  
  // Per-exam availability
  getExamAvailability: (examId) => _get(`/halls/exam/${examId}/availability`),
  setExamHallAvailability: (examId, hallId, isAvailable) => 
    _put(`/halls/exam/${examId}/availability/${hallId}?is_available=${isAvailable}`),
  setExamHallsAvailabilityBulk: (examId, hallIds) => 
    _post(`/halls/exam/${examId}/availability/bulk`, hallIds),
};

// ============================================================
// Exam API
// ============================================================
const ExamAPI = {
  getAll:        (params = {})     => _get('/exams', params),
  getById:       (id)              => _get(`/exams/${id}`),
  create:        (data)            => _post('/exams', data),
  updateStatus:  (id, status)      => _patch(`/exams/${id}/status`, { status }),
  
  // Bulk operations
  downloadTemplate: async () => {
    const blob = await _downloadFile('/exams/template.csv');
    downloadBlob(blob, 'exams_template.csv');
  },
  bulkUpload: (file) => _uploadFile('/exams/bulk', file),
};

// ============================================================
// Exam Session API
// ============================================================
const ExamSessionAPI = {
  getAll:  (params = {}) => _get('/sessions', params),
  getById: (id)          => _get(`/sessions/${id}`),
  create:  (data)        => _post('/sessions', data),
};

// ============================================================
// Seating API
// ============================================================
const SeatingAPI = {
  /**
   * Generate seating for a full session (multi-batch).
   * @param {number} sessionId
   * @param {Array<{exam_id: number, student_ids: number[]}>} batches
   * @param {number[]} hallIds
   */
  generateSession: (sessionId, batches, hallIds) =>
    _post('/generate-seating/session', {
      session_id: sessionId,
      batches,
      hall_ids: hallIds,
    }),

  /** Legacy: single-exam generate */
  generate: (examId, studentIds = null) => _post('/generate-seating', {
    exam_id: examId,
    ...(studentIds && studentIds.length > 0 ? { student_ids: studentIds } : {}),
  }),

  getBySession: (sessionId) => _get(`/seating/session/${sessionId}`),
  getByExam:    (examId)    => _get(`/seating/${examId}`),

  exportExcelSession: async (sessionId, filename) => {
    const blob = await _downloadFile(`/seating/session/${sessionId}/export/excel`);
    downloadBlob(blob, filename || `seating_session_${sessionId}.xlsx`);
  },
  exportExcel: async (examId, filename) => {
    const blob = await _downloadFile(`/seating/${examId}/export/excel`);
    downloadBlob(blob, filename || `seating_${examId}.xlsx`);
  },
};
