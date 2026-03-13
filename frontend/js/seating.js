/**
 * seating.js — Generate and display seating arrangements.
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadExamOptions();
  setupGenerateButton();
  setupExportButton();
  setupExamSelect();
  clearSeatingTable();
  
  // Check for exam parameter in URL
  const urlParams = new URLSearchParams(window.location.search);
  const examId = urlParams.get('exam');
  if (examId) {
    const select = document.getElementById('seating-exam');
    select.value = examId;
    loadSeating(parseInt(examId));
  }
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
  const exportBtn = document.getElementById('export-btn');
  
  select.addEventListener('change', () => {
    const id = parseInt(select.value);
    if (id) {
      loadSeating(id);
      exportBtn.disabled = false;
    } else {
      clearSeatingTable();
      exportBtn.disabled = true;
    }
  });
}

// ============================================================
// Export to Excel button
// ============================================================
function setupExportButton() {
  const btn = document.getElementById('export-btn');
  btn.addEventListener('click', async () => {
    const examId = parseInt(document.getElementById('seating-exam').value);
    if (!examId) {
      showToast('Please select an exam first.', 'info');
      return;
    }
    
    setButtonLoading(btn, true);
    try {
      // Get exam title for filename
      const select = document.getElementById('seating-exam');
      const selectedOption = select.options[select.selectedIndex];
      const examTitle = selectedOption.textContent.split('—')[0].trim().replace(/\s+/g, '_');
      const filename = `seating_${examTitle}.xlsx`;
      
      await SeatingAPI.exportExcel(examId, filename);
      showToast('Excel file downloaded!', 'success');
    } catch (err) {
      showToast('Failed to export: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
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
  const exportBtn = document.getElementById('export-btn');
  renderLoadingRow(tbody, 6);
  metaEl.textContent = '';

  try {
    const data = await SeatingAPI.getByExam(examId);
    metaEl.textContent = `${data.total_allocated} student${data.total_allocated !== 1 ? 's' : ''} allocated`;

    if (!data.allocations.length) {
      renderEmptyRow(tbody, 6, 'No seating generated yet. Click "Generate Seating" above.');
      exportBtn.disabled = true;
      return;
    }
    
    exportBtn.disabled = false;
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
    exportBtn.disabled = true;
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
