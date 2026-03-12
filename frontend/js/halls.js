/**
 * halls.js — Exam hall management: add, list, deactivate.
 */

document.addEventListener('DOMContentLoaded', async () => {
  await loadHalls();
  setupForm();
});

// ============================================================
// Load & render halls table
// ============================================================
async function loadHalls() {
  const tbody = document.querySelector('#halls-table tbody');
  renderLoadingRow(tbody, 7);
  try {
    const halls = await HallAPI.getAll();
    if (!halls.length) {
      renderEmptyRow(tbody, 7, 'No halls yet. Add your first exam hall.');
      return;
    }
    tbody.innerHTML = halls.map(hall => `
      <tr>
        <td>${escapeHtml(String(hall.id))}</td>
        <td><strong>${escapeHtml(hall.name)}</strong></td>
        <td>${hall.block ? escapeHtml(hall.block) : '—'}</td>
        <td>${hall.floor !== null && hall.floor !== undefined ? `Floor ${escapeHtml(String(hall.floor))}` : '—'}</td>
        <td>${escapeHtml(String(hall.capacity))}</td>
        <td>${statusBadge(hall.is_active ? 'active' : 'inactive')}</td>
        <td>
          ${hall.is_active
            ? `<button class="btn btn-secondary btn-sm"
                       onclick="deactivateHall(${hall.id}, this)">
                 Deactivate
               </button>`
            : '—'}
        </td>
      </tr>`).join('');
  } catch (err) {
    renderEmptyRow(tbody, 7, 'Failed to load halls.');
    showToast('Failed to load halls: ' + err.message, 'error');
  }
}

// ============================================================
// Add Hall form
// ============================================================
function setupForm() {
  const form = document.getElementById('add-hall-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormErrors(form);

    const nameInput     = document.getElementById('hall-name');
    const blockInput    = document.getElementById('hall-block');
    const floorInput    = document.getElementById('hall-floor');
    const capacityInput = document.getElementById('hall-capacity');

    const capacity = parseInt(capacityInput.value);
    const data = {
      name:     nameInput.value.trim(),
      block:    blockInput.value.trim() || null,
      floor:    floorInput.value !== '' ? parseInt(floorInput.value) : null,
      capacity,
    };

    let valid = true;
    if (!data.name) {
      showFieldError(nameInput, 'Hall name is required');
      valid = false;
    }
    if (!capacityInput.value || isNaN(capacity) || capacity <= 0) {
      showFieldError(capacityInput, 'Capacity must be a positive number');
      valid = false;
    }
    if (!valid) return;

    const btn = form.querySelector('button[type="submit"]');
    setButtonLoading(btn, true);
    try {
      await HallAPI.create(data);
      showToast('Exam hall added!', 'success');
      resetForm(form);
      await loadHalls();
    } catch (err) {
      showToast('Failed to add hall: ' + err.message, 'error');
    } finally {
      setButtonLoading(btn, false);
    }
  });
}

// ============================================================
// Deactivate hall
// ============================================================
async function deactivateHall(id, btn) {
  if (!confirm('Deactivate this hall? It will not be used in future seating allocations.')) return;
  setButtonLoading(btn, true);
  try {
    await HallAPI.deactivate(id);
    showToast('Hall deactivated.', 'success');
    await loadHalls();
  } catch (err) {
    showToast('Failed to deactivate: ' + err.message, 'error');
    setButtonLoading(btn, false);
  }
}
