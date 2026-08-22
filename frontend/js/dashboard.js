Auth.requireAuth();
renderLayout('dashboard');

// ── Live date display ─────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  
  const elDayLabel = document.getElementById('dc-day-label');
  const elDayNumber = document.getElementById('dc-day-number');
  const elMonthYear = document.getElementById('dc-month-year');
  
  if (elDayLabel && elDayNumber && elMonthYear) {
    elDayLabel.textContent = now.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
    elDayNumber.textContent = now.getDate();
    elMonthYear.textContent = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }

  // Legacy fallback
  const formatted = now.toLocaleDateString('en-US', {
    weekday: 'short', year: 'numeric', month: 'long', day: 'numeric'
  });
  const elHeader = document.getElementById('live-date');
  if (elHeader) elHeader.textContent = formatted;
  const elHero = document.getElementById('live-date-hero');
  if (elHero) elHero.textContent = formatted;
}
updateClock();

// ── Track previous row IDs for new-item animation ────────────────────────────
let _prevAttendanceIds = new Set();

// ── Activity Feed renderer ────────────────────────────────────────────────────
/**
 * Renders a single attendance record as an activity feed item.
 */
function renderActivityItem(r, isNew) {
  const isCheckIn  = r.event_type === 'CHECK_IN';
  const isUnknown  = !r.employee_name || r.employee_name === 'Unknown';

  let iconClass, iconEmoji;
  if (isUnknown) {
    iconClass = 'activity-icon-unknown';
    iconEmoji = '⚠️';
  } else if (isCheckIn) {
    iconClass = 'activity-icon-checkin';
    iconEmoji = '↑';
  } else {
    iconClass = 'activity-icon-checkout';
    iconEmoji = '↓';
  }

  // SVG arrow icons for check-in and check-out (⚠ for unknown)
  const iconSvg = isUnknown
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`
    : isCheckIn
      ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 11 12 6 7 11"/><line x1="12" y1="18" x2="12" y2="6"/></svg>`
      : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 13 12 18 7 13"/><line x1="12" y1="6" x2="12" y2="18"/></svg>`;

  const conf = r.confidence;
  let confBadge = '';
  if (conf !== null && conf !== undefined) {
    const pct = Math.round(conf);
    const cls  = pct >= 80 ? 'badge-green' : pct >= 55 ? 'badge-orange' : 'badge-red';
    confBadge = `<span class="badge ${cls}">${pct}%</span>`;
  }

  const eventBadge = isUnknown
    ? `<span class="badge badge-orange">Unknown</span>`
    : isCheckIn
      ? `<span class="badge badge-green">Check In</span>`
      : `<span class="badge badge-red">Check Out</span>`;

  const cameraIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>`;

  return `
    <div class="activity-item${isNew ? ' item-new' : ''}">
      <div class="activity-icon ${iconClass}">${iconSvg}</div>
      <div class="activity-body">
        <div class="activity-header-row">
          <span class="activity-name">${r.employee_name || 'Unknown Face'}</span>
          <span class="activity-time">${formatTime(r.timestamp)}</span>
        </div>
        <div class="activity-meta">
          ${eventBadge}
          ${confBadge}
          ${r.employee_code ? `<span class="activity-code">${r.employee_code}</span>` : ''}
          <span class="activity-camera">${cameraIcon} ${r.camera_name || 'API'}</span>
        </div>
      </div>
    </div>`;
}

// ── Dashboard data loader ─────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const [summary, today] = await Promise.all([
      api.get('/analytics/dashboard-summary'),
      api.get('/attendance/today'),
    ]);

    // ─── Animated stat counters ──────────────────────────────────────────────
    animateCounter(document.getElementById('s-employees'), summary.total_employees ?? 0);
    animateCounter(document.getElementById('s-cameras'),   summary.total_cameras   ?? 0);
    animateCounter(document.getElementById('s-checkins'),  summary.today_checkins  ?? 0);

    const accVal = summary.avg_confidence ? Math.round(summary.avg_confidence) : null;
    const accEl  = document.getElementById('s-accuracy');
    if (accVal !== null) {
      animateCounter(accEl, accVal, '%');
    } else {
      accEl.textContent = 'N/A';
    }

    // Sub-labels
    document.getElementById('s-active-emp').textContent  = `${summary.active_employees} active`;
    document.getElementById('s-active-cam').textContent  = `${summary.active_cameras} active`;
    document.getElementById('s-checkouts').textContent   = `${summary.today_checkouts} check-outs`;

    // Update camera system status based on active cameras count
    const sysCamEl = document.getElementById('sys-cam-status');
    if (sysCamEl) {
      const activeCams = summary.active_cameras ?? 0;
      sysCamEl.textContent = activeCams > 0 ? 'Active' : 'No Feed';
      sysCamEl.className   = activeCams > 0 ? 'sys-status-value' : 'sys-status-value warning';
    }

    // ─── Activity Feed ────────────────────────────────────────────────────────
    const feedEl = document.getElementById('activity-feed');
    // Also keep legacy tbody updated (attendace.js on other pages uses it via API)
    const tbody  = document.getElementById('recent-table');

    if (!today.length) {
      _prevAttendanceIds = new Set();
      if (feedEl) {
        feedEl.innerHTML = `
          <div class="empty-state">
            <span class="empty-icon">📋</span>
            <p>No attendance records for today yet.</p>
          </div>`;
      }
      return;
    }

    const records = today.slice(0, 50);
    const newIds  = new Set(records.map(r => r.id));

    // Find newly added entries
    const addedIds = new Set();
    if (_prevAttendanceIds.size > 0) {
      for (const id of newIds) {
        if (!_prevAttendanceIds.has(id)) addedIds.add(id);
      }
    }

    // Render activity feed
    if (feedEl) {
      feedEl.innerHTML = records
        .map(r => renderActivityItem(r, addedIds.has(r.id)))
        .join('');
    }

    // Keep hidden legacy tbody in sync (rows only, for any other code that reads it)
    if (tbody) {
      tbody.innerHTML = records.map(r => `
        <tr class="${addedIds.has(r.id) ? 'row-new' : ''}">
          <td>${r.employee_name || '—'}</td>
          <td><code>${r.employee_code || '—'}</code></td>
          <td>${eventBadge(r.event_type)}</td>
          <td>${formatTime(r.timestamp)}</td>
          <td>${confidenceBadge(r.confidence)}</td>
          <td style="color:var(--text-3);font-size:0.8rem">${r.camera_name || 'API'}</td>
        </tr>`).join('');
    }

    // ─── Toast for each new check-in ─────────────────────────────────────────
    if (_prevAttendanceIds.size > 0) {
      for (const r of records) {
        if (addedIds.has(r.id)) {
          const name  = r.employee_name || 'Employee';
          const event = r.event_type === 'CHECK_IN' ? 'checked in' : 'checked out';
          toast(`✔ ${name} ${event}`, 'success', 3500);
        }
      }
    }

    _prevAttendanceIds = newIds;

  } catch (err) {
    toast(err.message, 'error');
  }
}

loadDashboard();
setInterval(loadDashboard, 30000);
