/**
 * exams.js — Exam management: create, list.
 */

let _examDepartments = [];

document.addEventListener('DOMContentLoaded', async () => {
  await loadDepartments();
  await loadExams();
  setupForm();
});

// ============================================================
// Departments (for dropdown + display)
// ============================================================
async function loadDepartments() {
  try {
    _examDepartments = await DepartmentAPI.getAll();
    const select = document.getElementById('exam-dept');
    _examDepartments.forEach(d => {
      const opt = document.createElement('option');
      opt.value       = d.id;
      opt.textContent = `${d.name} (${d.code})`;
      select.appendChild(opt);
    });
  } catch (err) {
    showToast('Failed to load departments', 'error');
  }
}

function deptLabel(deptId) {
  if (!deptId) return 'All Departments';
  const d = _examDepartments.find(d => d.id === deptId);
  return d ? escapeHtml(d.name) : String(deptId);
}

// ============================================================
// Load & render exams table
// ============================================================
async function loadExams() {
  const tbody = document.querySelector('#exams-table tbody');
  renderLoadingRow(tbody, 7);
  try {
    const exams = await ExamAPI.getAll();
    if (!exams.length) {
      renderEmptyRow(tbody, 7, 'No exams created yet.');
      return;
    }
    tbody.innerHTML = exams.map(exam => `
      <tr>
        <td>${escapeHtml(String(exam.id))}</td>
        <td><strong>${escapeHtml(exam.title)}</strong></td>
        <td>${escapeHtml(exam.exam_date)}</td>
        <td>${escapeHtml(exam.start_time.slice(0,5))} – ${escapeHtml(exam.end_time.slice(0,5))}</td>
        <td>${deptLabel(exam.department_id)}</td>
        <td>Sem&nbsp;${escapeHtml(String(exam.semester))}</td>
        <td>${statusBadge(exam.status)}</td>
      </tr>`).join('');
  } catch (err) {
    renderEmptyRow(tbody, 7, 'Failed to load exams.');
    showToast('Failed to load exams: ' + err.message, 'error');
  }
}

// ============================================================
// Create Exam form
// ============================================================
function setupForm() {
  const form = document.getElementById('add-exam-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);

    const titleInput = document.getElementById('exam-title');
    const dateInput  = document.getElementById('exam-date');
    const startInput = document.getElementById('exam-start');
    const endInput   = document.getElementById('exam-end');
    const yearInput  = document.getElementById('exam-year');
    const semInput   = document.getElementById('exam-sem');
    const deptInput  = document.getElementById('exam-dept');

    const data = {
      title:         titleInput.value.trim(),
      exam_date:     dateInput.value,
      start_time:    startInput.value ? startInput.value + ':00' : '',
      end_time:      endInput.value   ? endInput.value   + ':00' : '',
      academic_year: yearInput.value.trim(),
      semester:      parseInt(semInput.value),
      department_id: deptInput.value ? parseInt(deptInput.value) : null,
    };

    let valid = true;
    if (!data.title)         { showFieldError(titleInput, 'Title is required');         valid = false; }
    if (!data.exam_date)     { showFieldError(dateInput,  'Date is required');           valid = false; }
    if (!startInput.value)   { showFieldError(startInput, 'Start time is required');    valid = false; }
    if (!endInput.value)     { showFieldError(endInput,   'End time is required');      valid = false; }
    if (!data.academic_year) { showFieldError(yearInput,  'Academic year is required'); valid = false; }
    if (!data.semester || data.semester < 1 || data.semester > 12) {
      showFieldError(semInput, 'Semester must be between 1 and 12');
      valid = false;
    }
    if (startInput.value && endInput.value && startInput.value >= endInput.value) {
      showFieldError(endInput, 'End time must be after start time');
      valid = false;
    }
    if (!valid) return;

    const btn = form.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    try {
      await ExamAPI.create(data);
      showToast('Exam created!', 'success');
      resetForm(form);
      await loadExams();
    } catch (err) {
      showToast('Failed to create exam: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}
