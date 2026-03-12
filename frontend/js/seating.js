/**
 * seating.js — Generate and display seating arrangements.
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadExamOptions();
  setupGenerateButton();
  setupExamSelect();
  clearSeatingTable();
});

// ============================================================
// Populate exam dropdown
// ============================================================
async function loadExamOptions() {
  const select = document.getElementById('seating-exam');
  try {
    const exams = await ExamAPI.getAll();
    if (!exams.length) {
      const opt = document.createElement('option');
      opt.textContent = 'No exams available';
      opt.disabled    = true;
      select.appendChild(opt);
      return;
    }
    exams.forEach(exam => {
      const opt = document.createElement('option');
      opt.value       = exam.id;
      opt.textContent = `${exam.title} — ${exam.exam_date} (Sem ${exam.semester})`;
      select.appendChild(opt);
    });
  } catch (err) {
    showToast('Failed to load exams: ' + err.message, 'error');
  }
}

// ============================================================
// Auto-load seating when exam changes
// ============================================================
function setupExamSelect() {
  const select = document.getElementById('seating-exam');
  select.addEventListener('change', () => {
    const id = parseInt(select.value);
    if (id) loadSeating(id);
    else clearSeatingTable();
  });
}

// ============================================================
// Generate seating button
// ============================================================
function setupGenerateButton() {
  const btn = document.getElementById('generate-btn');
  btn.addEventListener('click', async () => {
    const examId = parseInt(document.getElementById('seating-exam').value);
    if (!examId) {
      showToast('Please select an exam first.', 'info');
      return;
    }
    if (!confirm('Re-generate seating for this exam? Existing allocations will be replaced.')) return;

    setButtonLoading(btn, true);
    try {
      const result = await SeatingAPI.generate(examId);
      showToast(result.message || 'Seating generated successfully!', 'success');
      await loadSeating(examId);
    } catch (err) {
      showToast('Failed to generate seating: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

// ============================================================
// Load and render seating table
// ============================================================
async function loadSeating(examId) {
  const tbody  = document.querySelector('#seating-table tbody');
  const metaEl = document.getElementById('seating-meta');
  renderLoadingRow(tbody, 6);
  metaEl.textContent = '';

  try {
    const data = await SeatingAPI.getByExam(examId);
    metaEl.textContent = `${data.total_allocated} student${data.total_allocated !== 1 ? 's' : ''} allocated`;

    if (!data.allocations.length) {
      renderEmptyRow(tbody, 6, 'No seating generated yet. Click "Generate Seating" above.');
      return;
    }
    tbody.innerHTML = data.allocations.map((row, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${escapeHtml(row.hall_name)}</td>
        <td><strong>${escapeHtml(row.seat_number)}</strong></td>
        <td>${escapeHtml(row.student_name)}</td>
        <td>${escapeHtml(row.register_number)}</td>
        <td>${escapeHtml(row.department_name)}</td>
      </tr>`).join('');
  } catch (_) {
    renderEmptyRow(tbody, 6, 'No seating data yet for this exam.');
    document.getElementById('seating-meta').textContent = '';
  }
}

// ============================================================
// Clear table when no exam is selected
// ============================================================
function clearSeatingTable() {
  const tbody = document.querySelector('#seating-table tbody');
  document.getElementById('seating-meta').textContent = '';
  renderEmptyRow(tbody, 6, 'Select an exam above to view or generate seating.');
}
