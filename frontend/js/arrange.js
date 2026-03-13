/**
 * arrange.js — Wizard logic for exam seating arrangement
 */

// Wizard state
const wizardState = {
  currentStep: 1,
  studentSelectionMode: 'filter', // 'filter' or 'upload'
  filterDept: null,
  filterSem: null,
  uploadedStudentIds: [],
  studentCount: 0,
  selectedExamId: null,
  selectedExam: null,
  selectedHallIds: [],
  halls: [],
  totalCapacity: 0,
};

// ============================================================
// Initialization
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([
    loadDepartments(),
    loadExams(),
    loadHalls(),
  ]);
  
  // Set up event listeners
  setupEventListeners();
});

async function loadDepartments() {
  try {
    const depts = await DepartmentAPI.getAll();
    const select = document.getElementById('filter-dept');
    depts.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = `${d.name} (${d.code})`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Failed to load departments:', err);
  }
}

async function loadExams() {
  try {
    const exams = await ExamAPI.getAll({ status: 'scheduled' });
    const select = document.getElementById('select-exam');
    exams.forEach(e => {
      const opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = `${e.title} — ${formatDate(e.date)}`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('Failed to load exams:', err);
  }
}

async function loadHalls() {
  try {
    const halls = await HallAPI.getAll({ is_active: true });
    wizardState.halls = halls;
    renderHallGrid();
  } catch (err) {
    console.error('Failed to load halls:', err);
    document.getElementById('hall-grid').innerHTML = '<p class="error">Failed to load halls</p>';
  }
}

function setupEventListeners() {
  // Filter changes
  document.getElementById('filter-dept').addEventListener('change', resetStudentCount);
  document.getElementById('filter-sem').addEventListener('change', resetStudentCount);
  
  // Student list file input
  document.getElementById('student-list-file').addEventListener('change', function(e) {
    const file = e.target.files[0];
    const label = document.getElementById('student-list-label');
    const selected = document.getElementById('student-list-selected');
    const parseBtn = document.getElementById('parse-list-btn');
    
    if (file) {
      label.classList.add('has-file');
      label.textContent = '✅ File selected';
      selected.textContent = file.name;
      parseBtn.disabled = false;
    } else {
      label.classList.remove('has-file');
      label.innerHTML = '📁 Choose file (CSV, Excel, or TXT)';
      selected.textContent = '';
      parseBtn.disabled = true;
    }
  });
  
  // Exam selection
  document.getElementById('select-exam').addEventListener('change', function() {
    const examId = this.value;
    if (examId) {
      selectExam(parseInt(examId));
    } else {
      wizardState.selectedExamId = null;
      wizardState.selectedExam = null;
      document.getElementById('exam-preview').style.display = 'none';
      document.getElementById('step2-next').disabled = true;
    }
  });
  
  // New exam form
  document.getElementById('new-exam-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    await createNewExam();
  });
}

// ============================================================
// Step Navigation
// ============================================================

function goToStep(step) {
  // Validate current step before moving forward
  if (step > wizardState.currentStep) {
    if (!validateStep(wizardState.currentStep)) {
      return;
    }
  }
  
  // Hide all steps
  for (let i = 1; i <= 4; i++) {
    document.getElementById(`step-${i}`).style.display = 'none';
    document.querySelector(`.wizard-step[data-step="${i}"]`).classList.remove('active', 'completed');
  }
  
  // Mark completed steps
  for (let i = 1; i < step; i++) {
    document.querySelector(`.wizard-step[data-step="${i}"]`).classList.add('completed');
  }
  
  // Show current step
  document.getElementById(`step-${step}`).style.display = 'block';
  document.querySelector(`.wizard-step[data-step="${step}"]`).classList.add('active');
  
  wizardState.currentStep = step;
  
  // Load step-specific data
  if (step === 3) {
    loadHallAvailability();
  } else if (step === 4) {
    updateFinalSummary();
  }
}

function validateStep(step) {
  switch (step) {
    case 1:
      if (wizardState.studentCount === 0) {
        showToast('Please select students first', 'error');
        return false;
      }
      return true;
    case 2:
      if (!wizardState.selectedExamId) {
        showToast('Please select or create an exam', 'error');
        return false;
      }
      return true;
    case 3:
      if (wizardState.selectedHallIds.length === 0) {
        showToast('Please select at least one hall', 'error');
        return false;
      }
      if (wizardState.totalCapacity < wizardState.studentCount) {
        showToast('Not enough hall capacity for all students', 'error');
        return false;
      }
      return true;
    default:
      return true;
  }
}

// ============================================================
// Step 1: Students
// ============================================================

function switchStudentTab(tabId) {
  // Update tab buttons
  document.querySelectorAll('#step-1 .option-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  
  // Update tab content
  document.querySelectorAll('#step-1 .tab-content').forEach(content => {
    content.classList.toggle('active', content.id === tabId);
  });
  
  // Update mode
  wizardState.studentSelectionMode = tabId === 'filter-tab' ? 'filter' : 'upload';
  resetStudentCount();
}

function resetStudentCount() {
  wizardState.studentCount = 0;
  wizardState.uploadedStudentIds = [];
  document.getElementById('student-preview').style.display = 'none';
  document.getElementById('step1-next').disabled = true;
}

async function countFilteredStudents() {
  const deptId = document.getElementById('filter-dept').value;
  const sem = document.getElementById('filter-sem').value;
  
  try {
    const result = await StudentAPI.count({
      department_id: deptId || undefined,
      semester: sem || undefined,
    });
    
    wizardState.filterDept = deptId || null;
    wizardState.filterSem = sem || null;
    wizardState.studentCount = result.count;
    
    document.getElementById('student-count').textContent = result.count;
    document.getElementById('student-preview').style.display = 'block';
    document.getElementById('step1-next').disabled = result.count === 0;
    
    if (result.count === 0) {
      showToast('No students found with the selected filters', 'warning');
    } else {
      showToast(`Found ${result.count} students`, 'success');
    }
  } catch (err) {
    showToast('Failed to count students: ' + err.message, 'error');
  }
}

async function parseStudentListFile() {
  const fileInput = document.getElementById('student-list-file');
  const file = fileInput.files[0];
  if (!file) return;
  
  try {
    const text = await file.text();
    let regNumbers = [];
    
    // Parse as newline or comma separated
    const lines = text.split(/[\n\r,]+/).map(l => l.trim()).filter(l => l);
    regNumbers = lines.map(l => l.toUpperCase());
    
    if (regNumbers.length === 0) {
      showToast('No register numbers found in file', 'error');
      return;
    }
    
    // Validate that these students exist
    const allStudents = await StudentAPI.getAll();
    const validIds = [];
    const notFound = [];
    
    regNumbers.forEach(reg => {
      const student = allStudents.find(s => s.register_number.toUpperCase() === reg);
      if (student) {
        validIds.push(student.id);
      } else {
        notFound.push(reg);
      }
    });
    
    wizardState.uploadedStudentIds = validIds;
    wizardState.studentCount = validIds.length;
    
    document.getElementById('student-count').textContent = validIds.length;
    document.getElementById('student-preview').style.display = 'block';
    document.getElementById('step1-next').disabled = validIds.length === 0;
    
    if (notFound.length > 0) {
      showToast(`Found ${validIds.length} students. ${notFound.length} register numbers not found.`, 'warning');
    } else {
      showToast(`Found all ${validIds.length} students`, 'success');
    }
  } catch (err) {
    showToast('Failed to parse file: ' + err.message, 'error');
  }
}

// ============================================================
// Step 2: Exam
// ============================================================

function switchExamTab(tabId) {
  // Update tab buttons
  document.querySelectorAll('#step-2 .option-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  
  // Update tab content
  document.querySelectorAll('#step-2 .tab-content').forEach(content => {
    content.classList.toggle('active', content.id === tabId);
  });
}

async function selectExam(examId) {
  try {
    const exam = await ExamAPI.getById(examId);
    wizardState.selectedExamId = examId;
    wizardState.selectedExam = exam;
    
    document.getElementById('selected-exam-title').textContent = exam.title;
    document.getElementById('exam-preview').style.display = 'block';
    document.getElementById('step2-next').disabled = false;
    
    showToast('Exam selected', 'success');
  } catch (err) {
    showToast('Failed to load exam details: ' + err.message, 'error');
  }
}

async function createNewExam() {
  const title = document.getElementById('new-exam-title').value.trim();
  const date = document.getElementById('new-exam-date').value;
  const start = document.getElementById('new-exam-start').value;
  const end = document.getElementById('new-exam-end').value;
  const year = document.getElementById('new-exam-year').value.trim();
  const sem = document.getElementById('new-exam-sem').value;
  
  if (!title || !date || !start || !end || !year || !sem) {
    showToast('Please fill in all required fields', 'error');
    return;
  }
  
  try {
    const exam = await ExamAPI.create({
      title,
      date,
      start_time: start,
      end_time: end,
      academic_year: year,
      semester: parseInt(sem),
    });
    
    wizardState.selectedExamId = exam.id;
    wizardState.selectedExam = exam;
    
    // Add to dropdown
    const select = document.getElementById('select-exam');
    const opt = document.createElement('option');
    opt.value = exam.id;
    opt.textContent = `${exam.title} — ${formatDate(exam.date)}`;
    select.appendChild(opt);
    select.value = exam.id;
    
    document.getElementById('selected-exam-title').textContent = exam.title;
    document.getElementById('exam-preview').style.display = 'block';
    document.getElementById('step2-next').disabled = false;
    
    // Switch to existing tab to show selection
    switchExamTab('existing-exam-tab');
    
    showToast('Exam created successfully', 'success');
  } catch (err) {
    showToast('Failed to create exam: ' + err.message, 'error');
  }
}

// ============================================================
// Step 3: Halls
// ============================================================

async function loadHallAvailability() {
  if (!wizardState.selectedExamId) return;
  
  try {
    const availability = await HallAPI.getExamAvailability(wizardState.selectedExamId);
    
    // Update hall selection based on availability
    wizardState.selectedHallIds = [];
    wizardState.halls.forEach(hall => {
      const avail = availability.find(a => a.hall_id === hall.id);
      const isAvailable = avail ? avail.is_available : true; // Default to available
      
      const checkbox = document.getElementById(`hall-${hall.id}`);
      if (checkbox) {
        checkbox.checked = isAvailable;
        if (isAvailable) {
          wizardState.selectedHallIds.push(hall.id);
        }
      }
    });
    
    updateCapacitySummary();
  } catch (err) {
    console.error('Failed to load hall availability:', err);
  }
}

function renderHallGrid() {
  const grid = document.getElementById('hall-grid');
  
  if (wizardState.halls.length === 0) {
    grid.innerHTML = '<p class="text-muted">No active halls found. Please add halls first.</p>';
    return;
  }
  
  grid.innerHTML = wizardState.halls.map(hall => `
    <label class="hall-checkbox">
      <input type="checkbox" id="hall-${hall.id}" value="${hall.id}" onchange="toggleHall(${hall.id})">
      <div class="hall-info">
        <div class="hall-name">${escapeHtml(hall.name)}</div>
        <div class="hall-capacity">Capacity: ${hall.capacity}</div>
        ${hall.block ? `<div class="hall-block">${escapeHtml(hall.block)}</div>` : ''}
      </div>
    </label>
  `).join('');
}

function toggleHall(hallId) {
  const checkbox = document.getElementById(`hall-${hallId}`);
  if (checkbox.checked) {
    if (!wizardState.selectedHallIds.includes(hallId)) {
      wizardState.selectedHallIds.push(hallId);
    }
  } else {
    wizardState.selectedHallIds = wizardState.selectedHallIds.filter(id => id !== hallId);
  }
  updateCapacitySummary();
}

function selectAllHalls() {
  wizardState.halls.forEach(hall => {
    const checkbox = document.getElementById(`hall-${hall.id}`);
    if (checkbox) {
      checkbox.checked = true;
    }
  });
  wizardState.selectedHallIds = wizardState.halls.map(h => h.id);
  updateCapacitySummary();
}

function deselectAllHalls() {
  wizardState.halls.forEach(hall => {
    const checkbox = document.getElementById(`hall-${hall.id}`);
    if (checkbox) {
      checkbox.checked = false;
    }
  });
  wizardState.selectedHallIds = [];
  updateCapacitySummary();
}

function updateCapacitySummary() {
  const selectedHalls = wizardState.halls.filter(h => wizardState.selectedHallIds.includes(h.id));
  wizardState.totalCapacity = selectedHalls.reduce((sum, h) => sum + h.capacity, 0);
  
  document.getElementById('summary-students').textContent = wizardState.studentCount;
  document.getElementById('summary-capacity').textContent = wizardState.totalCapacity;
  
  const statusEl = document.getElementById('summary-status');
  const nextBtn = document.getElementById('step3-next');
  
  if (wizardState.selectedHallIds.length === 0) {
    statusEl.textContent = 'No halls selected';
    statusEl.className = 'capacity-value status-warning';
    nextBtn.disabled = true;
  } else if (wizardState.totalCapacity >= wizardState.studentCount) {
    statusEl.textContent = `✅ Sufficient (${wizardState.totalCapacity - wizardState.studentCount} extra seats)`;
    statusEl.className = 'capacity-value status-success';
    nextBtn.disabled = false;
  } else {
    statusEl.textContent = `⚠️ Insufficient (${wizardState.studentCount - wizardState.totalCapacity} seats short)`;
    statusEl.className = 'capacity-value status-error';
    nextBtn.disabled = true;
  }
}

// ============================================================
// Step 4: Generate
// ============================================================

function updateFinalSummary() {
  const exam = wizardState.selectedExam;
  const selectedHalls = wizardState.halls.filter(h => wizardState.selectedHallIds.includes(h.id));
  
  document.getElementById('final-exam').textContent = exam ? exam.title : '—';
  document.getElementById('final-datetime').textContent = exam 
    ? `${formatDate(exam.date)} ${formatTime(exam.start_time)} - ${formatTime(exam.end_time)}`
    : '—';
  document.getElementById('final-students').textContent = wizardState.studentCount;
  document.getElementById('final-halls').textContent = selectedHalls.map(h => h.name).join(', ') || '—';
  document.getElementById('final-capacity').textContent = wizardState.totalCapacity;
}

async function generateSeating() {
  const btn = document.getElementById('generate-btn');
  
  try {
    setButtonLoading(btn, true);
    
    // First, save hall availability for this exam
    await HallAPI.setExamHallsAvailabilityBulk(
      wizardState.selectedExamId,
      wizardState.selectedHallIds
    );
    
    // Generate seating
    const result = await SeatingAPI.generate(wizardState.selectedExamId);
    
    // Show success
    document.getElementById('generation-results').style.display = 'block';
    document.getElementById('result-message').textContent = 
      `Successfully allocated ${result.total_allocated} students across ${result.halls_used} halls.`;
    document.getElementById('step4-back').style.display = 'none';
    btn.style.display = 'none';
    
    showToast('Seating generated successfully!', 'success');
  } catch (err) {
    showToast('Failed to generate seating: ' + err.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

function viewSeating() {
  window.location.href = `seating.html?exam=${wizardState.selectedExamId}`;
}

async function exportToExcel() {
  try {
    const exam = wizardState.selectedExam;
    const filename = `seating_${exam.title.replace(/\s+/g, '_')}_${exam.date}.xlsx`;
    await SeatingAPI.exportExcel(wizardState.selectedExamId, filename);
    showToast('Excel file downloaded', 'success');
  } catch (err) {
    showToast('Failed to export: ' + err.message, 'error');
  }
}

function startOver() {
  // Reset state
  wizardState.currentStep = 1;
  wizardState.studentCount = 0;
  wizardState.selectedExamId = null;
  wizardState.selectedExam = null;
  wizardState.selectedHallIds = [];
  wizardState.uploadedStudentIds = [];
  
  // Reset UI
  document.getElementById('filter-dept').value = '';
  document.getElementById('filter-sem').value = '';
  document.getElementById('student-preview').style.display = 'none';
  document.getElementById('step1-next').disabled = true;
  document.getElementById('select-exam').value = '';
  document.getElementById('exam-preview').style.display = 'none';
  document.getElementById('step2-next').disabled = true;
  document.getElementById('generation-results').style.display = 'none';
  document.getElementById('generate-btn').style.display = '';
  document.getElementById('step4-back').style.display = '';
  
  // Reset form
  document.getElementById('new-exam-form').reset();
  
  // Go to step 1
  goToStep(1);
}

// ============================================================
// Utilities
// ============================================================

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(timeStr) {
  if (!timeStr) return '';
  const [h, m] = timeStr.split(':');
  const hour = parseInt(h);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  return `${hour12}:${m} ${ampm}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[m]));
}
