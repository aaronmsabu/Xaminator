/**
 * ui.js — Shared UI utilities: toasts, loaders, DOM helpers, nav state.
 * Load after api.js, before page-specific scripts.
 */

// ============================================================
// Auth Guard
// ============================================================

/**
 * Check if the user is authenticated and redirect to login if not.
 * Call this at the top of every protected page.
 */
function requireAuth() {
  if (typeof AuthAPI !== 'undefined' && !AuthAPI.isAuthenticated()) {
    window.location.href = 'index.html';
    return false;
  }
  return true;
}

/**
 * Logout the user and redirect to login page.
 */
function logout() {
  if (typeof AuthAPI !== 'undefined') {
    AuthAPI.logout();
  }
  window.location.href = 'index.html';
}

// ============================================================
// Toast Notifications
// ============================================================

/**
 * Show a toast notification.
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const icon  = icons[type] || 'ℹ️';

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut .3s forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ============================================================
// Button Loading State
// ============================================================

/**
 * Toggle a button's loading state.
 * @param {HTMLButtonElement} btn
 * @param {boolean} loading
 */
function setButtonLoading(btn, loading) {
  if (loading) {
    btn._origHTML  = btn.innerHTML;
    btn.disabled   = true;
    btn.innerHTML  = `<span class="spinner"></span> Processing…`;
  } else {
    btn.disabled  = false;
    btn.innerHTML = btn._origHTML || btn.innerHTML;
  }
}

// ============================================================
// Table Helpers
// ============================================================

/** Render an "empty state" row spanning all columns. */
function renderEmptyRow(tbody, colSpan, msg = 'No records found.') {
  tbody.innerHTML = `<tr class="empty-row"><td colspan="${colSpan}">${msg}</td></tr>`;
}

/** Render a loading spinner row spanning all columns. */
function renderLoadingRow(tbody, colSpan) {
  tbody.innerHTML = `
    <tr class="loading-row">
      <td colspan="${colSpan}">
        <span class="spinner spinner-dark"></span> Loading…
      </td>
    </tr>`;
}

// ============================================================
// Form Helpers
// ============================================================

/** Remove all inline validation styling from a form. */
function clearFormErrors(form) {
  form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
  form.querySelectorAll('.field-error').forEach(el => el.remove());
}

/** Mark a field invalid and show a message below it. */
function showFieldError(input, message) {
  input.classList.add('error');
  const msg = document.createElement('div');
  msg.className   = 'field-error';
  msg.textContent = message;
  input.parentNode.appendChild(msg);
}

/** Reset form values and clear validation state. */
function resetForm(form) {
  form.reset();
  clearFormErrors(form);
}

// ============================================================
// Sidebar Active State
// ============================================================

/** Highlight the current page's nav link in the sidebar. */
function setActiveNav() {
  const page = location.pathname.split('/').pop().replace('.html', '') || 'index';
  document.querySelectorAll('.nav-links a').forEach(link => {
    const href = link.getAttribute('href').replace('.html', '');
    if (href === page) link.classList.add('active');
  });
}

// ============================================================
// Status/Active Badge
// ============================================================

/**
 * Return a coloured <span class="badge …"> for a given status string.
 * @param {string} status
 */
function statusBadge(status) {
  const map = {
    scheduled: 'badge-info',
    ongoing:   'badge-warning',
    completed: 'badge-success',
    cancelled: 'badge-error',
    active:    'badge-success',
    inactive:  'badge-gray',
    true:      'badge-success',
    false:     'badge-gray',
  };
  const cls = map[String(status)] || 'badge-gray';
  return `<span class="badge ${cls}">${status}</span>`;
}

// ============================================================
// Security Helper
// ============================================================

/** Escape HTML special chars to prevent XSS when inserting user data. */
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Run on every page load
document.addEventListener('DOMContentLoaded', () => {
  setActiveNav();
  
  // Setup logout button if present
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  }
});
