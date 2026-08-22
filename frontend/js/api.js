/* ============================================================
   api.js — Centralised API client + shared UI helpers
   All pages include this file before their own JS.
============================================================ */

const API_BASE = '/api';

// ── Auth helpers ──────────────────────────────────────────────────────────────

const Auth = {
  getToken: () => localStorage.getItem('fa_token'),
  setToken: (t) => localStorage.setItem('fa_token', t),
  clear: () => { localStorage.removeItem('fa_token'); localStorage.removeItem('fa_user'); },
  isLoggedIn: () => !!localStorage.getItem('fa_token'),
  requireAuth: () => {
    if (!Auth.isLoggedIn()) {
      window.location.href = '/login.html';
      return false;
    }
    return true;
  },
};

// ── HTTP helper ───────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    Auth.clear();
    window.location.href = '/login.html';
    throw new Error('Session expired');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

const api = {
  get: (path) => apiFetch(path, { method: 'GET' }),
  post: (path, body) => apiFetch(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path, body) => apiFetch(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path) => apiFetch(path, { method: 'DELETE' }),
};

// ── Toast notifications ───────────────────────────────────────────────────────

function ensureToastContainer() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}

function toast(message, type = 'info', duration = 3500) {
  const icons = {
    success: '✔',
    error: '✕',
    info: 'ℹ',
  };
  const container = ensureToastContainer();
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  // Set CSS variable so the progress bar duration matches the toast duration
  el.style.setProperty('--toast-duration', `${duration}ms`);
  el.innerHTML = `<span class="toast-icon">${icons[type] || '·'}</span><span class="toast-msg">${message}</span>`;
  container.appendChild(el);

  // Auto-dismiss with slide-out animation
  setTimeout(() => {
    el.classList.add('dismissing');
    setTimeout(() => el.remove(), 300);
  }, duration);
}


// ── Floating nav renderer (replaces sidebar) ─────────────────────────────────

function renderLayout(activePage) {
  // SVG-based nav icons — 18px, softly rounded strokes
  const navItems = [
    {
      href: '/dashboard.html',
      label: 'Dashboard',
      id: 'dashboard',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
    },
    {
      href: '/employees.html',
      label: 'Employees',
      id: 'employees',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
    },
    {
      href: '/cameras.html',
      label: 'Cameras',
      id: 'cameras',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
    },
    {
      href: '/attendance.html',
      label: 'Attendance',
      id: 'attendance',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    },
    {
      href: '/analytics.html',
      label: 'Analytics',
      id: 'analytics',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    },
    {
      href: '/settings.html',
      label: 'Settings',
      id: 'settings',
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`,
    },
  ];

  // ── 1. Hide the old sidebar element (still in HTML, now unused) ───────────
  const sidebarEl = document.getElementById('sidebar');
  if (sidebarEl) sidebarEl.style.display = 'none';

  // ── 2. Inject floating brand wordmark (top-left, non-interactive overlay) ─
  if (!document.getElementById('float-brand')) {
    const brand = document.createElement('div');
    brand.id = 'float-brand';
    brand.className = 'floatbrand';
    brand.innerHTML = `
      <div class="fb-icon">FA</div>
      <div class="fb-text">Face<span>Attend</span></div>`;
    document.body.appendChild(brand);
  }

  // ── 3. Build floating nav item HTML ───────────────────────────────────────
  const navItemsHtml = navItems.map((n, i) => {
    const isActive = n.id === activePage;
    const sep = (i < navItems.length - 1)
      ? '<span class="floatnav-sep" aria-hidden="true"></span>'
      : '';
    return `
      <a href="${n.href}"
         class="fn-item${isActive ? ' active' : ''}"
         id="fn-${n.id}"
         aria-current="${isActive ? 'page' : 'false'}"
         data-page="${n.id}">
        <span class="fn-indicator" aria-hidden="true"></span>
        <span class="fn-glow"      aria-hidden="true"></span>
        <span class="fn-icon">${n.icon}</span>
        <span class="fn-label">${n.label}</span>
      </a>${sep}`;
  }).join('');

  // ── 4. Inject (or update) the floating nav element ────────────────────────
  let nav = document.getElementById('float-nav');
  if (!nav) {
    nav = document.createElement('nav');
    nav.id = 'float-nav';
    nav.className = 'floatnav';
    nav.setAttribute('role', 'navigation');
    nav.setAttribute('aria-label', 'Main navigation');
    document.body.appendChild(nav);
  }
  nav.innerHTML = navItemsHtml;

  // ── 5. Dock magnification effect ─────────────────────────────────────────
  initDockMagnification(nav);

  // ── 6. Press feedback on click (no delay — navigate instantly) ─────────────
  nav.querySelectorAll('.fn-item').forEach(link => {
    link.addEventListener('mousedown', () => link.classList.add('fn-press'));
    link.addEventListener('mouseup', () => link.classList.remove('fn-press'));
  });

  // ── 7. Admin logout (button lives in each page's static header HTML) ──────
  const logoutBtn = document.getElementById('admin-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      Auth.clear();
      window.location.href = '/login.html';
    });
  }


}

// ── Dock Magnification (Mac-style proximity scaling) ─────────────────────────
//
// Scales ONLY the .fn-icon inside each item — label stays fixed.
// This keeps the pill layout stable while giving a smooth dock-like feel.
//
// Gaussian formula:  scale(d) = 1 + AMP * exp( −d² / 2σ² )
//
// d = 0   (cursor on icon center):  scale = 1.25  (subtle, not aggressive)
// d = σ   (~80px away):             scale ≈ 1.15
// d = 2σ  (~160px away):            scale ≈ 1.04
// d = 3σ  (~240px away):            scale ≈ 1.00

function initDockMagnification(navEl) {
  // Skip on touch-only devices — no cursor to track
  if (window.matchMedia('(hover: none) and (pointer: coarse)').matches) return;

  const items = [...navEl.querySelectorAll('.fn-item')];
  const SIGMA = 80;    // px — narrower spread so only adjacent icons enlarge
  const MAX_AMP = 0.25;  // max increment → 1.25× on the icon directly under cursor
  let lastX = null;
  let pressed = null;

  // Scale each item's icon based on Gaussian proximity to cursorX
  function applyScale(cursorX) {
    items.forEach(item => {
      if (item === pressed) return;
      const icon = item.querySelector('.fn-icon');
      if (!icon) return;
      const rect = item.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const dist = Math.abs(cursorX - cx);
      const amp = Math.exp(-(dist * dist) / (2 * SIGMA * SIGMA));
      const scale = 1 + MAX_AMP * amp;
      icon.style.transform = `scale(${scale.toFixed(4)})`;
    });
  }

  // Reset all icons to natural size (CSS transition handles the ease-out)
  function resetScale() {
    items.forEach(item => {
      const icon = item.querySelector('.fn-icon');
      if (icon) icon.style.transform = '';
    });
    lastX = null;
  }

  // Live cursor tracking across the pill
  navEl.addEventListener('mousemove', e => {
    lastX = e.clientX;
    applyScale(lastX);
  });

  navEl.addEventListener('mouseleave', resetScale);

  // Press (mousedown) — tactile squeeze on the whole item via CSS class
  items.forEach(item => {
    item.addEventListener('mousedown', () => {
      pressed = item;
      item.classList.add('fn-press');
    });

    const release = () => {
      if (!pressed) return;
      pressed.classList.remove('fn-press');
      pressed = null;
      if (lastX !== null) requestAnimationFrame(() => applyScale(lastX));
    };

    item.addEventListener('mouseup', release);
    item.addEventListener('mouseleave', release);
  });
}

// ── Utility helpers ───────────────────────────────────────────────────────────

function formatDateTime(iso) {
  if (!iso) return '—';
  if (iso && iso.indexOf('Z') === -1 && iso.indexOf('+') === -1) iso += 'Z';
  return new Date(iso).toLocaleString();
}

function formatDate(iso) {
  if (!iso) return '—';
  if (iso && iso.indexOf('Z') === -1 && iso.indexOf('+') === -1) iso += 'Z';
  return new Date(iso).toLocaleDateString();
}

function formatTime(iso) {
  if (!iso) return '—';
  if (iso && iso.indexOf('Z') === -1 && iso.indexOf('+') === -1) iso += 'Z';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function confidenceBadge(conf) {
  if (!conf && conf !== 0) return '<span class="badge badge-gray">—</span>';
  const pct = Math.round(conf);
  const cls = pct >= 80 ? 'badge-green' : pct >= 55 ? 'badge-orange' : 'badge-red';
  return `<span class="badge ${cls}">${pct}%</span>`;
}

function eventBadge(type) {
  return type === 'CHECK_IN'
    ? '<span class="badge badge-green">Check In</span>'
    : '<span class="badge badge-red">Check Out</span>';
}

function statusBadge(status) {
  const cfg = {
    active: ['badge-green', 'Active'],
    inactive: ['badge-gray', 'Inactive'],
    error: ['badge-red', 'Error'],
  };
  const [cls, label] = cfg[status] || ['badge-gray', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

// Cam dot shorthand
function camDot(status) {
  const cls = status === 'active' ? 'active' : status === 'error' ? 'error' : 'inactive';
  const label = status === 'active' ? 'Active' : status === 'error' ? 'Error' : 'Inactive';
  return `<span class="cam-status-dot ${cls}">${label}</span>`;
}

function showSpinner(btnEl, text = 'Processing…') {
  btnEl._origText = btnEl.innerHTML;
  btnEl.innerHTML = `<span class="spinner"></span> ${text}`;
  btnEl.disabled = true;
}

function hideSpinner(btnEl) {
  btnEl.innerHTML = btnEl._origText || btnEl.innerHTML;
  btnEl.disabled = false;
}

// ── Animated Counter ──────────────────────────────────────────────────────────
/**
 * Animates a numeric value from its current displayed value to `target`.
 * @param {HTMLElement} el  - The element whose textContent to animate
 * @param {number}      target - The destination number
 * @param {string}      suffix - Optional suffix (e.g. '%')
 * @param {number}      duration - Animation duration in ms (default 700)
 */
function animateCounter(el, target, suffix = '', duration = 700) {
  if (!el) return;
  // Parse current displayed value (strip non-numeric except '.')
  const rawCurrent = parseFloat(el.textContent.replace(/[^0-9.]/g, '')) || 0;
  if (rawCurrent === target) {
    el.textContent = target + suffix;
    return;
  }
  const startTime = performance.now();
  const diff = target - rawCurrent;

  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(rawCurrent + diff * eased);
    el.textContent = current + suffix;
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target + suffix;
  }

  requestAnimationFrame(step);
}

// ── Face Detection Indicator ──────────────────────────────────────────────────
/**
 * Shows or hides the face-detect indicator element.
 * @param {string|HTMLElement} elOrId - Element or its ID
 * @param {boolean} visible
 */
function setFaceDetectIndicator(elOrId, visible) {
  const el = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
  if (!el) return;
  if (visible) {
    el.classList.add('visible');
  } else {
    el.classList.remove('visible');
  }
}

// ── Modal close helper ────────────────────────────────────────────────────────
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// ── Webcam helpers ────────────────────────────────────────────────────────────

const Webcam = {
  stream: null,

  async start(videoEl) {
    this.stop(); // guarantee prior streams are cleaned up safely
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
      });
      this.videoEl = videoEl;
      videoEl.srcObject = this.stream;

      await Promise.race([
        new Promise((resolve) => {
          if (videoEl.readyState >= 1) resolve();
          videoEl.onloadedmetadata = () => resolve();
          videoEl.onloadeddata = () => resolve();
          videoEl.oncanplay = () => resolve();
        }),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Webcam readiness timeout')), 5000))
      ]);

      await videoEl.play();
      console.log('Webcam started:', videoEl.videoWidth, 'x', videoEl.videoHeight);
      return true;
    } catch (e) {
      console.error('Webcam start error:', e);
      toast('Webcam access error: ' + e.message, 'error');
      return false;
    }
  },

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    if (this.videoEl) {
      this.videoEl.pause();
      this.videoEl.srcObject = null;
      this.videoEl = null;
    }
  },

  captureBase64(videoEl, quality = 0.85) {
    if (videoEl.readyState < 2 || !videoEl.videoWidth) {
      console.warn('Webcam not ready for capture');
      return null;
    }
    const canvas = document.createElement('canvas');
    canvas.width = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoEl, 0, 0);
    return canvas.toDataURL('image/jpeg', quality);
  },
};
