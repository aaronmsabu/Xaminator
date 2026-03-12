/**
 * students.js — Student CRUD: add, list, search, delete.
 */

let _allStudents   = [];
let _departments   = [];

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartments();
  await loadStudents();
  setupForm();
  setupSearch();
});

// ============================================================
// Departments (needed for dropdown + display names)
// ============================================================
async function loadDepartments() {
  try {
    _departments = await DepartmentAPI.getAll();
    const select = document.getElementById('student-dept');
    _departments.forEach(d => {
      const opt = document.createElement('option');
      opt.value       = d.id;
      opt.textContent = `${d.name} (${d.code})`;
      select.appendChild(opt);
    });
  } catch (err) {
    showToast('Failed to load departments: ' + err.message, 'error');
  }
}

function deptName(deptId) {
  const d = _departments.find(d => d.id === deptId);
  return d ? escapeHtml(d.name) : String(deptId);
}

// ============================================================
// Load & render students table
// ============================================================
async function loadStudents() {
  const tbody = document.querySelector('#students-table tbody');
  renderLoadingRow(tbody, 7);
  try {
    _allStudents = await StudentAPI.getAll();
    renderStudentTable(_allStudents);
  } catch (err) {
    renderEmptyRow(tbody, 7, 'Failed to load students.');
    showToast('Failed to load students: ' + err.message, 'error');
  }
}

function renderStudentTable(students) {
  const tbody = document.querySelector('#students-table tbody');
  if (!students.length) {
    renderEmptyRow(tbody, 7, 'No students found.');
    return;
  }
  tbody.innerHTML = students.map(s => `
    <tr>
      <td>${escapeHtml(String(s.id))}</td>
      <td><strong>${escapeHtml(s.register_number)}</strong></td>
      <td>${escapeHtml(s.full_name)}</td>
      <td>${s.email ? escapeHtml(s.email) : '—'}</td>
      <td>${deptName(s.department_id)}</td>
      <td>Sem&nbsp;${escapeHtml(String(s.semester))}</td>
      <td>
        <button class="btn btn-danger btn-sm"
                onclick="deleteStudent(${s.id}, this)"
                aria-label="Delete student ${escapeHtml(s.register_number)}">
          🗑 Delete
        </button>
      </td>
    </tr>`).join('');
}

// ============================================================
// Add Student form
// ============================================================
function setupForm() {
  const form = document.getElementById('add-student-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);

    const regInput  = document.getElementById('student-reg');
    const nameInput = document.getElementById('student-name');
    const deptInput = document.getElementById('student-dept');
    const semInput  = document.getElementById('student-sem');
    const emailInput = document.getElementById('student-email');

    const data = {
      register_number: regInput.value.trim().toUpperCase(),
      full_name:       nameInput.value.trim(),
      email:           emailInput.value.trim() || null,
      department_id:   parseInt(deptInput.value),
      semester:        parseInt(semInput.value),
    };

    // Client-side validation (mirrors backend Pydantic rules)
    let valid = true;
    if (!data.register_number || !/^[A-Z0-9]{5,20}$/.test(data.register_number)) {
      showFieldError(regInput, 'Register number must be 5–20 uppercase alphanumeric characters');
      valid = false;
    }
    if (!data.full_name) {
      showFieldError(nameInput, 'Full name is required');
      valid = false;
    }
    if (!deptInput.value) {
      showFieldError(deptInput, 'Please select a department');
      valid = false;
    }
    if (!data.semester || data.semester < 1 || data.semester > 12) {
      showFieldError(semInput, 'Semester must be between 1 and 12');
      valid = false;
    }
    if (!valid) return;

    const btn = form.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    try {
      await StudentAPI.create(data);
      showToast('Student added successfully!', 'success');
      resetForm(form);
      await loadStudents();
    } catch (err) {
      showToast('Failed to add student: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

// ============================================================
// Delete student
// ============================================================
async function deleteStudent(id, btn) {
  if (!confirm('Delete this student? This cannot be undone.')) return;
  setButtonLoading(btn, true);
  try {
    await StudentAPI.delete(id);
    showToast('Student deleted.', 'success');
    await loadStudents();
  } catch (err) {
    showToast('Failed to delete: ' + err.message, 'error');
    setButtonLoading(btn, false);
  }
}

// ============================================================
// Search / filter (client-side)
// ============================================================
function setupSearch() {
  const input = document.getElementById('student-search');
  input.addEventListener('input', () => {
    const q = input.value.trim().toUpperCase();
    if (!q) { renderStudentTable(_allStudents); return; }
    const filtered = _allStudents.filter(s =>
      s.register_number.toUpperCase().includes(q) ||
      s.full_name.toUpperCase().includes(q)
    );
    renderStudentTable(filtered);
  });

  // Clear search on Escape
  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') { input.value = ''; renderStudentTable(_allStudents); }
  });
}
