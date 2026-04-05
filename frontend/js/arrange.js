/**
 * arrange.js — Wizard logic for exam seating arrangement
 * Multi-batch, multi-exam, session-based seating.
 */

// ============================================================
// Wizard state
// ============================================================
const wizardState = {
  currentStep: 1,
  studentSelectionMode: 'filter',  // 'filter' | 'upload'

  // Step 1: Batches
  batches: [],           // [{ deptId, deptName, semester, semLabel, count }]
  uploadedStudentIds: [],
  studentCount: 0,

  // Step 2: Session + linked exams
  sessionId: null,
  session: null,
  batchExamLinks: {},    // { batchKey → { examId, examTitle } }

  // Step 3: Halls
  selectedHallIds: [],
  halls: [],
  totalCapacity: 0,
};

let _allExams = [];   // cache for the exam dropdowns in Step 2

// ============================================================
// Boot
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([loadDepartments(), loadExams(), loadHalls()]);
  setupEventListeners();
});

async function loadDepartments() {
  try {
    const depts = await DepartmentAPI.getAll();
    const sel = document.getElementById('filter-dept');
    depts.forEach(d => {
      const o = document.createElement('option');
      o.value = d.id;
      o.textContent = `${d.name} (${d.code})`;
      sel.appendChild(o);
    });
  } catch (err) {
    console.error('loadDepartments:', err);
  }
}

async function loadExams() {
  try {
    // Load ALL scheduled exams for the linker dropdowns
    _allExams = await ExamAPI.getAll({ status: 'scheduled', limit: 500 });
  } catch (err) {
    console.error('loadExams:', err);
    _allExams = [];
  }
}

async function loadHalls() {
  try {
    wizardState.halls = await HallAPI.getAll({ is_active: true });
    renderHallGrid();
  } catch (err) {
    console.error('loadHalls:', err);
    document.getElementById('hall-grid').innerHTML =
      '<p style="color:var(--error);font-size:13px;">Failed to load halls.</p>';
  }
}

function setupEventListeners() {
  // File input → show filename + enable parse button
  const fileInput = document.getElementById('student-list-file');
  if (fileInput) {
    fileInput.addEventListener('change', function () {
      const file = this.files[0];
      const label    = document.getElementById('student-list-label');
      const selected = document.getElementById('student-list-selected');
      const parseBtn = document.getElementById('parse-list-btn');
      if (file) {
        label.classList.add('has-file');
        label.textContent = '✅ File selected';
        selected.textContent = file.name;
        parseBtn.disabled = false;
      } else {
        label.classList.remove('has-file');
        label.innerHTML = '📁 Choose file (CSV or TXT)';
        selected.textContent = '';
        parseBtn.disabled = true;
      }
    });
  }
}

// ============================================================
// Step Navigation
// ============================================================
function goToStep(step) {
  if (step > wizardState.currentStep && !validateStep(wizardState.currentStep)) return;

  // Update stepper UI
  for (let i = 1; i <= 4; i++) {
    document.getElementById(`step-${i}`).style.display = 'none';
    const dot = document.querySelector(`.wizard-step[data-step="${i}"]`);
    dot.classList.remove('active', 'completed');
  }
  for (let i = 1; i < step; i++) {
    document.querySelector(`.wizard-step[data-step="${i}"]`).classList.add('completed');
  }
  document.getElementById(`step-${step}`).style.display = 'block';
  document.querySelector(`.wizard-step[data-step="${step}"]`).classList.add('active');
  wizardState.currentStep = step;

  // Side-effects per step
  if (step === 2) renderBatchExamLinker();
  if (step === 3) initHallStep();
  if (step === 4) updateFinalSummary();
}

function validateStep(step) {
  switch (step) {
    case 1:
      if (wizardState.studentCount === 0) {
        showToast('Add at least one batch with students first.', 'error');
        return false;
      }
      return true;

    case 2:
      if (!wizardState.sessionId) {
        showToast('Save session details first (Session Details tab).', 'error');
        return false;
      }
      if (wizardState.studentSelectionMode === 'filter') {
        const unlinked = wizardState.batches.filter(b => !wizardState.batchExamLinks[_batchKey(b)]);
        if (unlinked.length > 0) {
          const names = unlinked.map(b => `${b.deptName} Sem ${b.semester || 'All'}`).join(', ');
          showToast(`Link an exam to: ${names}`, 'error');
          return false;
        }
      }
      return true;

    case 3:
      if (wizardState.selectedHallIds.length === 0) {
        showToast('Select at least one hall.', 'error');
        return false;
      }
      if (wizardState.totalCapacity < wizardState.studentCount) {
        showToast('Not enough hall capacity for all students.', 'error');
        return false;
      }
      return true;

    default:
      return true;
  }
}

// ============================================================
// Step 1 — Student Selection
// ============================================================
function switchStudentTab(tabId) {
  document.querySelectorAll('#step-1 .option-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === tabId));
  document.querySelectorAll('#step-1 .tab-content').forEach(c =>
    c.classList.toggle('active', c.id === tabId));
  wizardState.studentSelectionMode = tabId === 'filter-tab' ? 'filter' : 'upload';
  tabId === 'filter-tab' ? _recalcBatchTotal() : _recalcUploadTotal();
}

async function addBatch() {
  const deptSel  = document.getElementById('filter-dept');
  const semSel   = document.getElementById('filter-sem');
  const deptId   = deptSel.value  || null;
  const sem      = semSel.value   || null;
  const deptName = deptId ? deptSel.options[deptSel.selectedIndex].text : 'All Departments';
  const semLabel = sem ? `Semester ${sem}` : 'All Semesters';

  // Prevent duplicates
  const dup = wizardState.batches.find(
    b => String(b.deptId) === String(deptId) && String(b.semester) === String(sem)
  );
  if (dup) {
    showToast(`Batch "${deptName} — ${semLabel}" already added.`, 'warning');
    return;
  }

  const btn = document.getElementById('add-batch-btn');
  btn.disabled = true;
  btn.textContent = 'Counting…';

  try {
    const params = {};
    if (deptId) params.department_id = deptId;
    if (sem)    params.semester = sem;
    // is_active defaults to true on the backend
    const result = await StudentAPI.count(params);

    if (!result || result.count === 0) {
      showToast(`No active students found for ${deptName} — ${semLabel}.`, 'warning');
      return;
    }

    wizardState.batches.push({ deptId, deptName, semester: sem, semLabel, count: result.count });
    renderBatchList();
    _recalcBatchTotal();
    showToast(`Added: ${deptName} — ${semLabel} (${result.count} students)`, 'success');
  } catch (err) {
    showToast('Failed to count students: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '+ Add Batch';
  }
}

function removeBatch(index) {
  const b = wizardState.batches[index];
  if (b) delete wizardState.batchExamLinks[_batchKey(b)];
  wizardState.batches.splice(index, 1);
  renderBatchList();
  _recalcBatchTotal();
  if (wizardState.currentStep === 2) renderBatchExamLinker();
}

function clearAllBatches() {
  wizardState.batches.forEach(b => delete wizardState.batchExamLinks[_batchKey(b)]);
  wizardState.batches = [];
  renderBatchList();
  _recalcBatchTotal();
  if (wizardState.currentStep === 2) renderBatchExamLinker();
}

function renderBatchList() {
  const wrapper = document.getElementById('batch-list-wrapper');
  const list    = document.getElementById('batch-list');

  if (wizardState.batches.length === 0) {
    wrapper.style.display = 'none';
    list.innerHTML = '';
    return;
  }

  wrapper.style.display = 'block';
  list.innerHTML = wizardState.batches.map((b, i) => `
    <div class="batch-item">
      <div class="batch-item-info">
        <span class="batch-item-label">${escapeHtml(b.deptName)}</span>
        <span class="batch-item-sem"> — ${escapeHtml(b.semLabel)}</span>
      </div>
      <div class="batch-item-meta">
        <span class="batch-item-count">${b.count} students</span>
        <button type="button" class="batch-remove-btn"
          onclick="removeBatch(${i})" title="Remove batch">✕</button>
      </div>
    </div>
  `).join('');
}

function _recalcBatchTotal() {
  if (wizardState.studentSelectionMode !== 'filter') return;
  const total = wizardState.batches.reduce((s, b) => s + b.count, 0);
  wizardState.studentCount = total;
  const preview = document.getElementById('student-preview');
  if (total > 0) {
    document.getElementById('student-count').textContent = total;
    preview.style.display = 'block';
    document.getElementById('step1-next').disabled = false;
  } else {
    preview.style.display = 'none';
    document.getElementById('step1-next').disabled = true;
  }
}

function _recalcUploadTotal() {
  if (wizardState.studentSelectionMode !== 'upload') return;
  wizardState.studentCount = wizardState.uploadedStudentIds.length;
  document.getElementById('step1-next').disabled = wizardState.studentCount === 0;
}

async function parseStudentListFile() {
  const file = document.getElementById('student-list-file').files[0];
  if (!file) return;

  try {
    const text = await file.text();
    const regNumbers = text
      .split(/[\n\r,;]+/)
      .map(l => l.trim())
      .filter(l => l)
      .map(l => l.toUpperCase());

    if (!regNumbers.length) { showToast('No register numbers found in file.', 'error'); return; }

    // Fetch all students and match
    const allStudents = await StudentAPI.getAll({ limit: 10000 });
    const byReg = {};
    allStudents.forEach(s => { byReg[s.register_number.toUpperCase()] = s; });

    const validIds = [];
    const notFound = [];
    regNumbers.forEach(reg => {
      if (byReg[reg]) validIds.push(byReg[reg].id);
      else notFound.push(reg);
    });

    wizardState.uploadedStudentIds = validIds;
    wizardState.studentCount = validIds.length;
    document.getElementById('upload-student-count').textContent = validIds.length;
    document.getElementById('upload-student-preview').style.display = validIds.length > 0 ? 'block' : 'none';
    document.getElementById('step1-next').disabled = validIds.length === 0;

    if (notFound.length > 0)
      showToast(`Matched ${validIds.length} students. ${notFound.length} register numbers not found.`, 'warning');
    else
      showToast(`All ${validIds.length} students matched.`, 'success');
  } catch (err) {
    showToast('Failed to parse file: ' + err.message, 'error');
  }
}

// ============================================================
// Step 2 — Session + Exam Linking
// ============================================================
function switchExamTab(tabId) {
  document.querySelectorAll('#step-2 .option-tab').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === tabId));
  document.querySelectorAll('#step-2 .tab-content').forEach(c =>
    c.classList.toggle('active', c.id === tabId));
  if (tabId === 'link-exams-tab') renderBatchExamLinker();
}

async function createOrVerifySession() {
  const title = document.getElementById('session-title').value.trim();
  const date  = document.getElementById('session-date').value;
  const start = document.getElementById('session-start').value;
  const end   = document.getElementById('session-end').value;
  const year  = document.getElementById('session-year').value.trim();

  if (!title || !date || !start || !end || !year) {
    showToast('Fill in all session fields before saving.', 'error');
    return;
  }
  if (end <= start) {
    showToast('End time must be after start time.', 'error');
    return;
  }

  const btn = document.getElementById('create-session-btn');
  setButtonLoading(btn, true);

  try {
    const session = await ExamSessionAPI.create({
      title,
      exam_date: date,
      start_time: start,
      end_time: end,
      academic_year: year,
    });

    wizardState.sessionId = session.id;
    wizardState.session   = session;

    document.getElementById('session-preview-title').textContent = session.title;
    document.getElementById('session-preview-date').textContent  =
      `${formatDate(session.exam_date)}  ${formatTime(session.start_time)} – ${formatTime(session.end_time)}`;
    document.getElementById('session-preview').style.display = 'block';

    _checkStep2Complete();
    showToast('Session saved!', 'success');
    // Auto-jump to link tab
    switchExamTab('link-exams-tab');
  } catch (err) {
    showToast('Failed to save session: ' + err.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

/** Unique key for a batch used as dict key in batchExamLinks */
function _batchKey(b) {
  return `${b.deptId ?? 'all'}__${b.semester ?? 'all'}`;
}

/**
 * Render one row per batch with a dropdown to pick their exam.
 * Called whenever Step 2 is entered or batches change.
 */
function renderBatchExamLinker() {
  const container = document.getElementById('batch-exam-linker');
  if (!container) return;

  if (!wizardState.sessionId) {
    container.innerHTML =
      '<p style="font-size:13px;color:var(--gray-400);">Save session details first — then link exams here.</p>';
    return;
  }

  if (wizardState.batches.length === 0) {
    container.innerHTML =
      '<p style="font-size:13px;color:var(--gray-400);">Add batches in Step 1 first.</p>';
    _checkStep2Complete();
    return;
  }

  const examOptions = _allExams
    .map(e => `<option value="${e.id}">${escapeHtml(e.title)}</option>`)
    .join('');

  container.innerHTML = wizardState.batches.map((b, i) => {
    const key    = _batchKey(b);
    const linked = wizardState.batchExamLinks[key];
    return `
      <div class="batch-exam-row" id="batch-exam-row-${i}">
        <div class="batch-exam-label">
          <span class="batch-item-label">${escapeHtml(b.deptName)}</span>
          <span class="batch-item-sem"> — ${escapeHtml(b.semLabel)}</span>
          <span class="batch-item-count" style="margin-left:8px;">${b.count} students</span>
        </div>
        <div class="batch-exam-selector">
          <select id="exam-sel-${i}" onchange="linkBatchExam(${i}, this.value)">
            <option value="">— Select existing exam —</option>
            ${examOptions}
          </select>
          <span class="batch-exam-or">or</span>
          <button type="button" class="btn btn-secondary btn-sm"
            onclick="toggleNewExamForm(${i})">+ New Exam</button>
        </div>
        ${linked ? `<div class="batch-exam-linked">✅ Linked: ${escapeHtml(linked.examTitle)}</div>` : ''}
        <div class="new-exam-form-inline" id="new-exam-form-${i}" style="display:none;">
          <div class="form-row" style="margin-top:12px;">
            <div class="form-group">
              <label>Subject / Title *</label>
              <input id="new-exam-title-${i}" type="text"
                placeholder="e.g. Data Structures End Semester">
            </div>
            <div class="form-group">
              <label>Semester *</label>
              <input id="new-exam-sem-${i}" type="number"
                placeholder="1–12" min="1" max="12"
                value="${b.semester || ''}">
            </div>
          </div>
          <div style="display:flex;gap:8px;margin-top:4px;">
            <button type="button" class="btn btn-primary btn-sm"
              onclick="createAndLinkExam(${i})">Create & Link</button>
            <button type="button" class="btn btn-ghost btn-sm"
              onclick="toggleNewExamForm(${i})">Cancel</button>
          </div>
        </div>
      </div>
      ${i < wizardState.batches.length - 1
        ? '<hr style="border:none;border-top:1px solid var(--gray-100);margin:14px 0;">'
        : ''}
    `;
  }).join('');

  // Restore previously selected values
  wizardState.batches.forEach((b, i) => {
    const linked = wizardState.batchExamLinks[_batchKey(b)];
    const sel = document.getElementById(`exam-sel-${i}`);
    if (sel && linked) sel.value = linked.examId;
  });

  _checkStep2Complete();
}

function linkBatchExam(batchIndex, examIdStr) {
  const b = wizardState.batches[batchIndex];
  if (!b) return;
  const key = _batchKey(b);

  if (!examIdStr) {
    delete wizardState.batchExamLinks[key];
    _checkStep2Complete();
    renderBatchExamLinker();
    return;
  }
  const exam = _allExams.find(e => String(e.id) === examIdStr);
  if (exam) {
    wizardState.batchExamLinks[key] = { examId: exam.id, examTitle: exam.title };
  }
  _checkStep2Complete();
  renderBatchExamLinker();
}

function toggleNewExamForm(batchIndex) {
  const form = document.getElementById(`new-exam-form-${batchIndex}`);
  if (form) form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function createAndLinkExam(batchIndex) {
  const b = wizardState.batches[batchIndex];
  if (!b) return;

  const titleEl = document.getElementById(`new-exam-title-${batchIndex}`);
  const semEl   = document.getElementById(`new-exam-sem-${batchIndex}`);
  const title   = titleEl ? titleEl.value.trim() : '';
  const sem     = semEl ? parseInt(semEl.value) : null;

  if (!title) { showToast('Enter an exam title.', 'error'); return; }
  if (!sem || sem < 1 || sem > 12) { showToast('Enter a valid semester (1–12).', 'error'); return; }
  if (!wizardState.session) { showToast('Save session details first.', 'error'); return; }

  const btn = document.querySelector(`#new-exam-form-${batchIndex} .btn-primary`);
  if (btn) btn.disabled = true;

  try {
    const payload = {
      title,
      exam_date: wizardState.session.exam_date,
      start_time: wizardState.session.start_time,
      end_time: wizardState.session.end_time,
      academic_year: wizardState.session.academic_year,
      semester: sem,
      department_id: b.deptId ? parseInt(b.deptId) : null,
      session_id: wizardState.sessionId,     // ← link to session immediately
    };

    const exam = await ExamAPI.create(payload);

    // Add to cache so other batches can also pick it up
    _allExams.push(exam);

    const key = _batchKey(b);
    wizardState.batchExamLinks[key] = { examId: exam.id, examTitle: exam.title };

    showToast(`Created & linked: "${exam.title}"`, 'success');
    renderBatchExamLinker();
    _checkStep2Complete();
  } catch (err) {
    showToast('Failed to create exam: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

/** Enable Step 2 Next button only when session + all exams linked */
function _checkStep2Complete() {
  const sessionOk = !!wizardState.sessionId;
  let allLinked = true;

  if (wizardState.studentSelectionMode === 'filter') {
    allLinked = wizardState.batches.length > 0 &&
      wizardState.batches.every(b => !!wizardState.batchExamLinks[_batchKey(b)]);
  }
  // In upload mode, no per-batch exam linking needed
  const ok = sessionOk && (wizardState.studentSelectionMode === 'upload' || allLinked);
  document.getElementById('step2-next').disabled = !ok;
}

// ============================================================
// Step 3 — Halls
// ============================================================
function initHallStep() {
  // Default: all active halls selected
  wizardState.halls.forEach(h => {
    const cb = document.getElementById(`hall-${h.id}`);
    if (cb && !cb.dataset.userChanged) cb.checked = true;
  });
  wizardState.selectedHallIds = wizardState.halls.map(h => h.id);
  updateCapacitySummary();
}

function renderHallGrid() {
  const grid = document.getElementById('hall-grid');
  if (!grid) return;

  if (wizardState.halls.length === 0) {
    grid.innerHTML = '<p style="font-size:13px;color:var(--gray-400);">No active halls found. Add halls first.</p>';
    return;
  }

  grid.innerHTML = wizardState.halls.map(h => `
    <label class="hall-checkbox">
      <input type="checkbox" id="hall-${h.id}" value="${h.id}"
        onchange="toggleHall(${h.id}, this)">
      <div class="hall-info">
        <div class="hall-name">${escapeHtml(h.name)}</div>
        <div class="hall-capacity">Capacity: ${h.capacity}</div>
        ${h.block ? `<div class="hall-block">${escapeHtml(h.block)}</div>` : ''}
      </div>
    </label>
  `).join('');
}

function toggleHall(hallId, checkbox) {
  if (checkbox) checkbox.dataset.userChanged = '1';
  if (checkbox && checkbox.checked) {
    if (!wizardState.selectedHallIds.includes(hallId)) wizardState.selectedHallIds.push(hallId);
  } else {
    wizardState.selectedHallIds = wizardState.selectedHallIds.filter(id => id !== hallId);
  }
  updateCapacitySummary();
}

function selectAllHalls() {
  wizardState.halls.forEach(h => {
    const cb = document.getElementById(`hall-${h.id}`);
    if (cb) { cb.checked = true; cb.dataset.userChanged = '1'; }
  });
  wizardState.selectedHallIds = wizardState.halls.map(h => h.id);
  updateCapacitySummary();
}

function deselectAllHalls() {
  wizardState.halls.forEach(h => {
    const cb = document.getElementById(`hall-${h.id}`);
    if (cb) { cb.checked = false; cb.dataset.userChanged = '1'; }
  });
  wizardState.selectedHallIds = [];
  updateCapacitySummary();
}

function updateCapacitySummary() {
  const selected = wizardState.halls.filter(h => wizardState.selectedHallIds.includes(h.id));
  wizardState.totalCapacity = selected.reduce((s, h) => s + h.capacity, 0);

  document.getElementById('summary-students').textContent = wizardState.studentCount;
  document.getElementById('summary-capacity').textContent = wizardState.totalCapacity;

  const statusEl = document.getElementById('summary-status');
  const nextBtn  = document.getElementById('step3-next');

  if (wizardState.selectedHallIds.length === 0) {
    statusEl.textContent = 'No halls selected';
    statusEl.className   = 'capacity-value status-warning';
    nextBtn.disabled = true;
  } else if (wizardState.totalCapacity >= wizardState.studentCount) {
    const extra = wizardState.totalCapacity - wizardState.studentCount;
    statusEl.textContent = `✅ Sufficient (${extra} extra seat${extra !== 1 ? 's' : ''})`;
    statusEl.className   = 'capacity-value status-success';
    nextBtn.disabled = false;
  } else {
    const short = wizardState.studentCount - wizardState.totalCapacity;
    statusEl.textContent = `⚠️ Insufficient (${short} seat${short !== 1 ? 's' : ''} short)`;
    statusEl.className   = 'capacity-value status-error';
    nextBtn.disabled = true;
  }
}

// ============================================================
// Step 4 — Summary + Generate
// ============================================================
function updateFinalSummary() {
  const s = wizardState.session;
  const selectedHalls = wizardState.halls.filter(h => wizardState.selectedHallIds.includes(h.id));

  document.getElementById('final-exam').textContent     = s ? s.title : '—';
  document.getElementById('final-datetime').textContent = s
    ? `${formatDate(s.exam_date)}  ${formatTime(s.start_time)} – ${formatTime(s.end_time)}`
    : '—';
  document.getElementById('final-halls').textContent    = selectedHalls.map(h => h.name).join(', ') || '—';
  document.getElementById('final-capacity').textContent = wizardState.totalCapacity;

  // Students with batch breakdown
  let studentsText = String(wizardState.studentCount);
  if (wizardState.studentSelectionMode === 'filter' && wizardState.batches.length) {
    const lines = wizardState.batches.map(b => {
      const linked = wizardState.batchExamLinks[_batchKey(b)];
      return `${b.deptName}${b.semester ? ' S' + b.semester : ''} (${b.count})${linked ? ' → ' + linked.examTitle : ''}`;
    });
    studentsText = `${wizardState.studentCount} total\n${lines.join('\n')}`;
  }
  document.getElementById('final-students').textContent = studentsText;
}

/**
 * Resolve final batches payload by fetching actual student IDs.
 * Returns [{exam_id, student_ids}].
 */
async function resolveBatches() {
  // Upload mode — no per-batch exam, use null exam_id
  if (wizardState.studentSelectionMode === 'upload') {
    return [{ exam_id: null, student_ids: wizardState.uploadedStudentIds }];
  }

  // Filter mode — fetch student IDs per batch in parallel
  const results = await Promise.all(
    wizardState.batches.map(async b => {
      const key    = _batchKey(b);
      const linked = wizardState.batchExamLinks[key];
      const params = { is_active: true, limit: 10000 };
      if (b.deptId)   params.department_id = b.deptId;
      if (b.semester) params.semester = b.semester;

      const students = await StudentAPI.getAll(params);
      return {
        exam_id:     linked ? linked.examId : null,
        student_ids: students.map(s => s.id),
      };
    })
  );

  return results;
}

async function generateSeating() {
  const btn = document.getElementById('generate-btn');
  try {
    setButtonLoading(btn, true);

    // Resolve actual student ID lists per batch
    const batches = await resolveBatches();

    // Sanity check
    const totalResolved = batches.reduce((s, b) => s + b.student_ids.length, 0);
    if (totalResolved === 0) {
      showToast('No students found to seat. Check your batches.', 'error');
      return;
    }

    const result = await SeatingAPI.generateSession(
      wizardState.sessionId,
      batches,
      wizardState.selectedHallIds,
    );

    document.getElementById('generation-results').style.display = 'block';
    document.getElementById('result-message').textContent =
      `Successfully allocated ${result.total_allocated} students across ${result.halls_used} hall(s).`;
    document.getElementById('step4-back').style.display = 'none';
    btn.style.display = 'none';

    showToast('Seating generated!', 'success');
  } catch (err) {
    showToast('Failed to generate seating: ' + err.message, 'error');
  } finally {
    setButtonLoading(btn, false);
  }
}

function viewSeating() {
  window.location.href = `seating.html?session=${wizardState.sessionId}`;
}

async function exportToExcel() {
  if (!wizardState.sessionId) { showToast('No session to export.', 'error'); return; }
  try {
    const s = wizardState.session;
    const filename = `seating_${(s.title || 'session').replace(/\s+/g, '_')}_${s.exam_date}.xlsx`;
    await SeatingAPI.exportExcelSession(wizardState.sessionId, filename);
    showToast('Excel downloaded.', 'success');
  } catch (err) {
    showToast('Export failed: ' + err.message, 'error');
  }
}

function startOver() {
  // Reset all state
  wizardState.currentStep         = 1;
  wizardState.studentSelectionMode = 'filter';
  wizardState.batches             = [];
  wizardState.uploadedStudentIds  = [];
  wizardState.studentCount        = 0;
  wizardState.sessionId           = null;
  wizardState.session             = null;
  wizardState.batchExamLinks      = {};
  wizardState.selectedHallIds     = [];

  // Reset UI elements
  document.getElementById('filter-dept').value = '';
  document.getElementById('filter-sem').value  = '';
  document.getElementById('batch-list').innerHTML = '';
  document.getElementById('batch-list-wrapper').style.display = 'none';
  document.getElementById('student-preview').style.display = 'none';
  document.getElementById('upload-student-preview').style.display = 'none';
  document.getElementById('step1-next').disabled = true;
  document.getElementById('session-title').value = '';
  document.getElementById('session-date').value  = '';
  document.getElementById('session-start').value = '';
  document.getElementById('session-end').value   = '';
  document.getElementById('session-year').value  = '';
  document.getElementById('session-preview').style.display = 'none';
  document.getElementById('step2-next').disabled = true;
  document.getElementById('generation-results').style.display = 'none';
  document.getElementById('generate-btn').style.display = '';
  document.getElementById('step4-back').style.display   = '';

  // Remove user-changed markers from hall checkboxes
  wizardState.halls.forEach(h => {
    const cb = document.getElementById(`hall-${h.id}`);
    if (cb) { cb.checked = false; delete cb.dataset.userChanged; }
  });

  // Switch tabs back to default
  switchStudentTab('filter-tab');
  goToStep(1);
}

// ============================================================
// Formatters
// ============================================================
function formatDate(dateStr) {
  if (!dateStr) return '—';
  // Handle both 'YYYY-MM-DD' string and date objects
  const d = new Date(String(dateStr).replace(/-/g, '/'));
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(timeStr) {
  if (!timeStr) return '';
  const parts = String(timeStr).split(':');
  const h = parseInt(parts[0]);
  const m = parts[1] || '00';
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${h % 12 || 12}:${m} ${ampm}`;
}
