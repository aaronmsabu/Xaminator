/**
 * dashboard.js — Load stats, department management, recent exams.
 */

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadRecentExams();
  loadDepartmentList();
  setupDeptForm();
});

// ============================================================
// Stats
// ============================================================
async function loadStats() {
  try {
    const [students, halls, exams] = await Promise.all([
      StudentAPI.getAll(),
      HallAPI.getAll(),
      ExamAPI.getAll(),
    ]);
    document.getElementById('stat-students').textContent  = students.length;
    document.getElementById('stat-halls').textContent     = halls.filter(h => h.is_active).length;
    document.getElementById('stat-exams').textContent     = exams.length;
    document.getElementById('stat-scheduled').textContent = exams.filter(e => e.status === 'scheduled').length;
  } catch (err) {
    showToast('Failed to load stats: ' + err.message, 'error');
  }
}

// ============================================================
// Recent Exams table (last 5)
// ============================================================
async function loadRecentExams() {
  const tbody = document.querySelector('#recent-exams-table tbody');
  renderLoadingRow(tbody, 5);
  try {
    const exams = await ExamAPI.getAll();
    if (!exams.length) {
      renderEmptyRow(tbody, 5, 'No exams scheduled yet.');
      return;
    }
    const recent = [...exams].reverse().slice(0, 5);
    tbody.innerHTML = recent.map(e => `
      <tr>
        <td>${escapeHtml(String(e.id))}</td>
        <td>${escapeHtml(e.title)}</td>
        <td>${escapeHtml(e.exam_date)}</td>
        <td>${escapeHtml(e.academic_year)}</td>
        <td>${statusBadge(e.status)}</td>
      </tr>`).join('');
  } catch (err) {
    renderEmptyRow(tbody, 5, 'Failed to load exams.');
  }
}

// ============================================================
// Department list
// ============================================================
async function loadDepartmentList() {
  const el = document.getElementById('dept-list');
  try {
    const depts = await DepartmentAPI.getAll();
    if (!depts.length) {
      el.innerHTML = '<p class="text-muted">No departments yet.</p>';
      return;
    }
    el.innerHTML = depts.map(d => `
      <div class="dept-item">
        <span><span class="dept-code">${escapeHtml(d.code)}</span> &nbsp;${escapeHtml(d.name)}</span>
      </div>`).join('');
  } catch (_) {
    el.innerHTML = '<p class="text-muted">Failed to load departments.</p>';
  }
}

// ============================================================
// Add Department form
// ============================================================
function setupDeptForm() {
  const form = document.getElementById('add-dept-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);

    const nameInput = document.getElementById('dept-name');
    const codeInput = document.getElementById('dept-code');
    const name = nameInput.value.trim();
    const code = codeInput.value.trim().toUpperCase();

    let valid = true;
    if (!name) { showFieldError(nameInput, 'Department name is required'); valid = false; }
    if (!code) { showFieldError(codeInput, 'Code is required');            valid = false; }
    if (!valid) return;

    const btn = form.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    try {
      await DepartmentAPI.create({ name, code });
      showToast('Department added!', 'success');
      resetForm(form);
      await loadDepartmentList();
    } catch (err) {
      showToast('Failed to add department: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}
