Auth.requireAuth();
renderLayout('attendance');

// ══════════════════════════════════════════════════════════════════════════════
//  GEOFENCING — runs BEFORE any face recognition or webcam logic.
//  Face recognition pipeline (startWebcam / autoScan) is NOT modified.
// ══════════════════════════════════════════════════════════════════════════════

/** Switch the geofence gate to a named state panel. */
function _gfShow(stateId) {
  ['gf-checking', 'gf-verified', 'gf-blocked', 'gf-denied'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === stateId) ? 'flex' : 'none';
  });
}

// ── Session cache — skip re-verification for 4 hours in the same browser session ──
const _GF_KEY = 'fa_geo_ok';
const _GF_TTL = 4 * 60 * 60 * 1000; // 4 hours in ms

function _gfSessionValid() {
  try {
    const raw = sessionStorage.getItem(_GF_KEY);
    if (!raw) return false;
    const { ts } = JSON.parse(raw);
    return (Date.now() - ts) < _GF_TTL;
  } catch { return false; }
}

function _gfWriteSession(distanceMeters) {
  try {
    sessionStorage.setItem(_GF_KEY, JSON.stringify({ ts: Date.now(), dist: distanceMeters }));
  } catch { /* ignore quota errors */ }
}

function _gfRevealAttendance(distanceMeters) {
  const gate    = document.getElementById('geofence-gate');
  const content = document.getElementById('attendance-content');
  if (gate)    gate.style.display    = 'none';
  if (content) content.style.display = 'block';

  // Persistent badge in header
  const headerRight = document.querySelector('.header-right');
  if (headerRight && !document.getElementById('geo-badge')) {
    const badge = document.createElement('div');
    badge.id = 'geo-badge';
    badge.className = 'geo-badge';
    badge.title = `Location verified — ${Math.round(distanceMeters)} m from office`;
    badge.innerHTML = `
      <span class="geo-badge-dot"></span>
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
      </svg>
      <span>Location Verified</span>`;
    headerRight.insertBefore(badge, headerRight.firstChild);
  }
  loadToday();
}

/** Request GPS from the browser then validate with backend. */
async function runGeofenceCheck() {
  // ── Fast path: already verified this session ─────────────────────────────
  if (_gfSessionValid()) {
    // Skip gate entirely — just reveal attendance directly
    const gate    = document.getElementById('geofence-gate');
    const content = document.getElementById('attendance-content');
    if (gate)    gate.style.display    = 'none';
    if (content) content.style.display = 'block';
    // Show badge using stored distance
    try {
      const { dist } = JSON.parse(sessionStorage.getItem(_GF_KEY));
      _gfRevealAttendance(dist);
    } catch { loadToday(); }
    return;
  }

  // First visit — show spinner and request GPS
  _gfShow('gf-checking');

  if (!navigator.geolocation) {
    _gfShow('gf-denied');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const { latitude, longitude, accuracy } = pos.coords;
      try {
        const result = await api.post('/verify-location', { latitude, longitude, accuracy });

        if (result.location_verified) {
          // ── Verified ───────────────────────────────────────────────────────
          const okMsg = document.getElementById('gf-ok-msg');
          if (okMsg) {
            okMsg.textContent =
              `✅ You are ${Math.round(result.distance_meters)} m from the office ` +
              `(within ${result.allowed_radius} m).`;
          }
          _gfShow('gf-verified');

          // Save to session so revisits skip the gate (valid 4 hrs)
          _gfWriteSession(result.distance_meters);

          // Let user read the ✅ screen for 2.8 s, then reveal attendance
          setTimeout(() => _gfRevealAttendance(result.distance_meters), 2800);

        } else {
          // ── Blocked ────────────────────────────────────────────────────────
          const blockedMsg = document.getElementById('gf-blocked-msg');
          if (blockedMsg) blockedMsg.textContent = result.message;
          _gfShow('gf-blocked');
        }
      } catch (err) {
        console.error('Geofence API error:', err);
        _gfShow('gf-blocked');
        const blockedMsg = document.getElementById('gf-blocked-msg');
        if (blockedMsg) blockedMsg.textContent = 'Location verification failed. Please try again.';
      }
    },
    (err) => {
      // GPS unavailable or permission denied
      console.warn('Geolocation error:', err.message);
      if (err.code === err.PERMISSION_DENIED) {
        _gfShow('gf-denied');
      } else {
        const blockedMsg = document.getElementById('gf-blocked-msg');
        if (blockedMsg) blockedMsg.textContent = 'Unable to determine your location. Please check GPS settings.';
        _gfShow('gf-blocked');
      }
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
  );
}

// Kick off geofence check immediately on page load
runGeofenceCheck();

// ══════════════════════════════════════════════════════════════════════════════
//  ORIGINAL ATTENDANCE LOGIC — untouched below this line
// ══════════════════════════════════════════════════════════════════════════════

let webcamActive = false;
let scanInterval = null;
const recentlyMarked = {}; // employee_id -> timestamp


async function startWebcam() {
  const video       = document.getElementById('att-video');
  const canvas      = document.getElementById('att-canvas');
  const status      = document.getElementById('att-cam-status');
  const startBtn    = document.getElementById('start-cam-btn');
  const scanIndicator = document.getElementById('scan-indicator');
  const scanRing    = document.getElementById('scan-ring');

  if (webcamActive) {
    webcamActive = false;
    if (scanInterval) { clearInterval(scanInterval); scanInterval = null; }
    
    Webcam.stop();
    startBtn.textContent = '▶ Start';
    if (scanIndicator) scanIndicator.style.display = 'none';
    if (scanRing) scanRing.classList.remove('active');

    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width || 5000, canvas.height || 5000);
        canvas.width = 0; 
        canvas.height = 0;
    }
    
    if (video) {
        video.pause();
        video.srcObject = null;
    }

    status.textContent = 'Camera stopped';
    return;
  }

  status.textContent = 'Coordinating with backend…';
  try {
    const cameras = await api.get('/cameras');
    const usbCam = cameras.find(c => c.stream_url === '0' && c.status === 'active');
    if (usbCam) {
      console.log(`Pausing backend processor for camera ${usbCam.id} to release hardware lock…`);
      await api.post(`/cameras/${usbCam.id}/stop`);
      await new Promise(r => setTimeout(r, 800));
    }
  } catch (err) {
    console.warn('Could not coordinate with backend:', err);
  }

  status.textContent = 'Requesting camera access…';
  const ok = await Webcam.start(video);
  if (ok) {
    webcamActive = true;
    startBtn.textContent = '■ Stop';
    if (scanIndicator) scanIndicator.style.display = 'flex';
    if (scanRing)      scanRing.classList.add('active');
    status.textContent = `Camera live (${video.videoWidth}×${video.videoHeight}) — position face to scan`;
    scanInterval = setInterval(autoScan, 1500);
  } else {
    status.textContent = 'Camera error — see notification for details.';
  }
}

let isScanning = false;
async function autoScan() {
  if (!webcamActive || isScanning) return;

  const video    = document.getElementById('att-video');
  const resultEl = document.getElementById('att-result');
  const inner    = document.getElementById('att-result-inner');

  isScanning = true;
  try {
    const b64 = Webcam.captureBase64(video);
    if (!b64) { isScanning = false; return; }

    const data = await api.post('/attendance/mark', { image_base64: b64 });

    drawOverlay(data.results);

    // ── Visual-only: toggle face-detect indicator (no recognition logic) ──
    const hasFaces = data.results && data.results.length > 0;
    setFaceDetectIndicator('face-detect-indicator', hasFaces);
    if (hasFaces) {
      clearTimeout(window._faceDetectHideTimer);
      window._faceDetectHideTimer = setTimeout(() => {
        setFaceDetectIndicator('face-detect-indicator', false);
      }, 2000);
    }

    // Clear old cooldowns (60 seconds)
    const now = Date.now();
    for (let id in recentlyMarked) {
      if (now - recentlyMarked[id] > 60000) delete recentlyMarked[id];
    }

    if (!data.results || data.results.length === 0) { isScanning = false; return; }

    let htmlChunks  = [];
    let markedSomeone = false;

    data.results.forEach(res => {
      if (res.success && res.employee_id) {
        if (recentlyMarked[res.employee_id]) return;
        recentlyMarked[res.employee_id] = now;
        markedSomeone = true;
        toast(`✔ Attendance recorded — ${res.employee_name} ${res.event_type === 'CHECK_IN' ? 'checked in' : 'checked out'}`, 'success');
      } else if (!res.success && res.message.includes('Face not recognised')) {
        if (recentlyMarked['unknown'] && now - recentlyMarked['unknown'] < 5000) return;
        recentlyMarked['unknown'] = now;
        toast(res.message, 'error');
      }

      const isSuccess = res.success;
      const isCheckIn = res.event_type === 'CHECK_IN';
      const cardClass = isSuccess ? (isCheckIn ? 'success' : 'error') : '';
      const icon      = isSuccess ? (isCheckIn ? '↑' : '↓') : '!';
      const iconBg    = isSuccess ? (isCheckIn ? 'var(--green)' : 'var(--red)') : 'var(--orange)';

      let confHtml = '';
      if (res.confidence) {
        confHtml = `
          <div style="margin-top:10px">
            <div style="display:flex;justify-content:space-between;font-size:0.73rem;color:var(--text-3);margin-bottom:3px">
              <span>Confidence</span><span>${Math.round(res.confidence)}%</span>
            </div>
            <div class="conf-bar">
              <div class="conf-fill" style="width:${res.confidence}%;background:${iconBg}"></div>
            </div>
          </div>`;
      }

      htmlChunks.push(`
        <div class="result-card ${isSuccess ? (isCheckIn ? 'success' : 'error') : ''}" style="margin-bottom:10px">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <div style="width:32px;height:32px;border-radius:50%;background:${iconBg};display:flex;align-items:center;justify-content:center;color:white;font-weight:700;flex-shrink:0">
              ${icon}
            </div>
            <div>
              <div style="font-weight:600;font-size:0.95rem;color:var(--text)">${res.employee_name || 'Unknown'}</div>
              <div style="font-size:0.75rem;color:var(--text-3)">${res.employee_code || ''}</div>
            </div>
          </div>
          <div style="font-size:0.82rem;color:var(--text-2)">${res.message}</div>
          ${confHtml}
        </div>
      `);
    });

    if (htmlChunks.length > 0) {
      inner.innerHTML = htmlChunks.join('');
      resultEl.style.display = 'block';
      if (markedSomeone) loadToday();
    }
  } catch(e) {
    if (e.message && e.message !== 'Failed to fetch') console.error(e);
  }
  isScanning = false;
}

function drawOverlay(results) {
  const video  = document.getElementById('att-video');
  const canvas = document.getElementById('att-canvas');
  if (!canvas || !video) return;

  // If the camera was stopped while this request was in-flight, just clear and bail
  if (!webcamActive) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width || 5000, canvas.height || 5000);
    canvas.width = 0;
    canvas.height = 0;
    return;
  }

  const ctx = canvas.getContext('2d');
  canvas.width  = video.clientWidth;
  canvas.height = video.clientHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!results || results.length === 0) return;

  const internalW = 640;
  const scale     = canvas.width / internalW;

  results.forEach(res => {
    if (!res.box_2d) return;
    const [top, right, bottom, left] = res.box_2d;

    const color = res.is_live ? '#16A34A' : '#DC2626';
    const label = res.is_live ? (res.employee_name || 'Unknown') : 'Spoof Detected';

    ctx.strokeStyle = color;
    ctx.lineWidth   = 2.5;
    ctx.strokeRect(left * scale, top * scale, (right - left) * scale, (bottom - top) * scale);

    ctx.fillStyle = color;
    ctx.font = 'bold 13px Inter, sans-serif';
    const textWidth = ctx.measureText(label).width;
    ctx.fillRect(left * scale, (top * scale) - 22, textWidth + 10, 22);

    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, (left * scale) + 5, (top * scale) - 6);
  });
}

async function loadToday() {
  try {
    const records = await api.get('/attendance/today');
    document.getElementById('att-count').textContent = `${records.length} records today`;
    const tbody = document.getElementById('att-table');
    if (!records.length) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><span class="empty-icon">📋</span><p>No records today yet.</p></div></td></tr>`;
      return;
    }
    tbody.innerHTML = records.map(r => `
      <tr>
        <td>${r.employee_name || '—'}</td>
        <td>${eventBadge(r.event_type)}</td>
        <td style="color:var(--text-2)">${formatTime(r.timestamp)}</td>
        <td>${confidenceBadge(r.confidence)}</td>
        <td>${r.is_live
          ? '<span class="badge badge-green">Live</span>'
          : '<span class="badge badge-red">Spoof?</span>'}</td>
      </tr>`).join('');
  } catch(e) { toast(e.message, 'error'); }
}

loadToday();
setInterval(loadToday, 20000);
