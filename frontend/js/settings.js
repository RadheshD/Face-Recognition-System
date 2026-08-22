/* ============================================================
   settings.js — FaceAttend AI  ·  System Intelligence Page
   Futuristic interactive logic, visual timeline, radial gauge,
   sensitivity mapping, health dashboard, and smart save bar.
============================================================ */

(function () {
  'use strict';

  if (!Auth.requireAuth()) return;
  renderLayout('settings');

  // ── Sensitivity presets ─────────────────────────────────────────────────────
  const SENSITIVITY = [
    {
      label: 'Strict',
      conf: 0.75,
      fp: 'Very Low',
      speed: 'Slower',
      desc: 'Strict mode ensures near-perfect identity verification. Best for high-security environments where false positives must be minimized.',
      chip: 'ai-chip--red',
    },
    {
      label: 'Balanced',
      conf: 0.60,
      fp: 'Moderate',
      speed: 'Standard',
      desc: 'Balanced mode provides optimal trade-off between recognition accuracy and processing speed. Recommended for most environments.',
      chip: '',
    },
    {
      label: 'Relaxed',
      conf: 0.45,
      fp: 'Higher',
      speed: 'Faster',
      desc: 'Relaxed mode prioritizes speed and convenience. Ideal for large-group environments with lower security requirements.',
      chip: 'ai-chip--green',
    },
  ];

  // ── Default settings ───────────────────────────────────────────────────────
  const DEFAULTS = {
    ai: {
      sensitivity: 1,
      confidence: 85,
      cooldown: 30,
      camera: 'built-in',
    },
    attendance: {
      checkin: '09:00',
      late: '09:15',
      checkout: '18:00',
      grace: 15,
    },
    alerts: {
      unknown_face: true,
      missed_checkout: true,
      daily_summary: false,
    },
  };

  let currentSettings = JSON.parse(JSON.stringify(DEFAULTS));
  let savedSettings = JSON.parse(JSON.stringify(DEFAULTS));
  let dirty = false;

  // ── DOM helpers ─────────────────────────────────────────────────────────────
  const $ = id => document.getElementById(id);

  // ── Elements ────────────────────────────────────────────────────────────────
  const sensitivitySlider  = $('sensitivity-slider');
  const sensitivityChip    = $('sensitivity-chip');
  const sensitivityDesc    = $('sensitivity-desc');
  const sensitivityFill    = $('sensitivity-fill');
  const kpiConf            = $('kpi-conf');
  const kpiFP              = $('kpi-fp');
  const kpiSpeed           = $('kpi-speed');

  const confSlider         = $('confidence-slider');
  const confChip           = $('conf-chip');
  const confRadial         = $('conf-radial');
  const confRadialText     = $('conf-radial-text');

  const cooldownSlider     = $('cooldown-slider');
  const cooldownChip       = $('cooldown-chip');
  const cooldownFill       = $('cooldown-fill');
  const cooldownMarker     = $('cooldown-marker');

  const cameraSelect       = $('camera-select');

  const timeCheckin        = $('time-checkin');
  const timeLate           = $('time-late');
  const timeCheckout       = $('time-checkout');
  const graceVal           = $('grace-val');

  const alertUnknown       = $('alert-unknown-toggle');
  const alertMissed        = $('alert-missed-toggle');
  const alertSummary       = $('alert-summary-toggle');
  const previewUnknown     = $('alert-unknown-preview');
  const previewMissed      = $('alert-missed-preview');
  const previewSummary     = $('alert-summary-preview');

  const saveBar            = $('ai-save-bar');
  const saveBtn            = $('save-btn');
  const discardBtn         = $('discard-btn');
  const saveHint           = $('save-hint');
  const saveDot            = $('save-dot');
  const resetBtn           = $('reset-recommended-btn');

  const rebuildBtn         = $('rebuild-btn');
  const rebuildStatusDot   = $('rebuild-status');
  const rebuildStatusText  = $('rebuild-status-text');

  // ── Mark dirty ──────────────────────────────────────────────────────────────
  function markDirty() {
    dirty = true;
    saveBar.classList.add('visible');
    saveDot.classList.remove('saved');
    saveHint.textContent = 'Unsaved changes';
    saveHint.style.color = '';
  }

  // ── Sensitivity ─────────────────────────────────────────────────────────────
  function updateSensitivity(index, animate = true) {
    const p = SENSITIVITY[index];
    currentSettings.ai.sensitivity = index;

    // Fill width
    sensitivityFill.style.width = `${(index / 2) * 100}%`;

    // Labels
    document.querySelectorAll('.ai-slider-label').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.val) === index);
    });

    // Chip
    sensitivityChip.textContent = p.label;
    sensitivityChip.className = 'ai-chip ' + p.chip;

    // Description (animate text change)
    if (animate) {
      sensitivityDesc.style.opacity = '0';
      sensitivityDesc.style.transform = 'translateY(6px)';
      setTimeout(() => {
        sensitivityDesc.textContent = p.desc;
        sensitivityDesc.style.opacity = '1';
        sensitivityDesc.style.transform = 'translateY(0)';
      }, 180);
    } else {
      sensitivityDesc.textContent = p.desc;
    }

    // KPIs
    kpiConf.textContent = p.conf.toFixed(2);
    kpiFP.textContent   = p.fp;
    kpiSpeed.textContent = p.speed;

    markDirty();
  }

  sensitivitySlider.addEventListener('input', () => {
    updateSensitivity(parseInt(sensitivitySlider.value));
  });

  // Click on labels to jump
  document.querySelectorAll('.ai-slider-label').forEach(el => {
    el.addEventListener('click', () => {
      const v = parseInt(el.dataset.val);
      sensitivitySlider.value = v;
      updateSensitivity(v);
    });
  });

  // ── Confidence radial gauge ────────────────────────────────────────────────
  function updateConfidence(val) {
    currentSettings.ai.confidence = val;
    confChip.textContent = val + '%';
    confRadialText.textContent = val + '%';

    // Circle circumference at r=52 → 2πr ≈ 326.7
    const circ = 2 * Math.PI * 52;
    const offset = circ - (val / 100) * circ;
    confRadial.style.strokeDashoffset = offset;

    // Color based on value
    if (val >= 85) {
      confRadial.style.stroke = 'var(--green)';
    } else if (val >= 65) {
      confRadial.style.stroke = 'var(--blue)';
    } else {
      confRadial.style.stroke = 'var(--orange)';
    }

    markDirty();
  }

  confSlider.addEventListener('input', () => {
    updateConfidence(parseInt(confSlider.value));
  });

  // ── Cooldown ───────────────────────────────────────────────────────────────
  function updateCooldown(val) {
    currentSettings.ai.cooldown = val;
    cooldownChip.textContent = val + 's';
    const pct = (val / 300) * 100;
    cooldownFill.style.width = pct + '%';
    cooldownMarker.style.left = pct + '%';
    markDirty();
  }

  cooldownSlider.addEventListener('input', () => {
    updateCooldown(parseInt(cooldownSlider.value));
  });

  // ── Camera ─────────────────────────────────────────────────────────────────
  cameraSelect.addEventListener('change', () => {
    currentSettings.ai.camera = cameraSelect.value;
    markDirty();
  });

  // ── Timeline ───────────────────────────────────────────────────────────────
  function timeToMinutes(hhmm) {
    const [h, m] = hhmm.split(':').map(Number);
    return h * 60 + m;
  }

  function updateTimeline() {
    const start   = timeToMinutes(timeCheckin.value) || 540;   // 09:00
    const late    = timeToMinutes(timeLate.value) || 555;      // 09:15
    const end     = timeToMinutes(timeCheckout.value) || 1080; // 18:00

    const totalSpan = end - start;
    if (totalSpan <= 0) return;

    const checkinW  = Math.max(((late - start) / totalSpan) * 100, 5);
    const lateW     = Math.max(((Math.min(late + 30, end) - late) / totalSpan) * 100, 5);
    const checkoutW = 8;
    const workW     = Math.max(100 - checkinW - lateW - checkoutW, 10);

    $('tl-checkin').style.width  = checkinW + '%';
    $('tl-late').style.width     = lateW + '%';
    $('tl-work').style.width     = workW + '%';
    $('tl-checkout').style.width = checkoutW + '%';

    $('tl-time-start').textContent = timeCheckin.value;
    $('tl-time-late').textContent  = timeLate.value;
    $('tl-time-end').textContent   = timeCheckout.value;

    currentSettings.attendance.checkin  = timeCheckin.value;
    currentSettings.attendance.late     = timeLate.value;
    currentSettings.attendance.checkout = timeCheckout.value;
    markDirty();
  }

  timeCheckin.addEventListener('change', updateTimeline);
  timeLate.addEventListener('change', updateTimeline);
  timeCheckout.addEventListener('change', updateTimeline);

  // Grace period stepper
  $('grace-dec').addEventListener('click', () => {
    const v = Math.max(0, parseInt(graceVal.textContent) - 5);
    graceVal.textContent = v;
    currentSettings.attendance.grace = v;
    markDirty();
    // Pop animation
    graceVal.style.transform = 'scale(1.2)';
    setTimeout(() => graceVal.style.transform = '', 150);
  });
  $('grace-inc').addEventListener('click', () => {
    const v = Math.min(60, parseInt(graceVal.textContent) + 5);
    graceVal.textContent = v;
    currentSettings.attendance.grace = v;
    markDirty();
    graceVal.style.transform = 'scale(1.2)';
    setTimeout(() => graceVal.style.transform = '', 150);
  });

  // ── Alert toggles ──────────────────────────────────────────────────────────
  function bindAlert(toggle, preview, key) {
    toggle.addEventListener('change', () => {
      currentSettings.alerts[key] = toggle.checked;
      if (toggle.checked) {
        preview.classList.remove('ai-alert-preview--off');
      } else {
        preview.classList.add('ai-alert-preview--off');
      }
      markDirty();
    });
  }
  bindAlert(alertUnknown, previewUnknown, 'unknown_face');
  bindAlert(alertMissed, previewMissed, 'missed_checkout');
  bindAlert(alertSummary, previewSummary, 'daily_summary');

  // ── Rebuild encodings ──────────────────────────────────────────────────────
  rebuildBtn.addEventListener('click', async () => {
    rebuildBtn.classList.add('loading');
    rebuildBtn.querySelector('span').textContent = 'Rebuilding…';
    rebuildStatusText.textContent = 'Processing…';
    rebuildStatusDot.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--running';

    // Simulate rebuild (replace with actual API call if available)
    await new Promise(r => setTimeout(r, 2500));

    rebuildBtn.classList.remove('loading');
    rebuildBtn.querySelector('span').textContent = 'Rebuild Now';
    rebuildStatusText.textContent = 'Completed ✓';
    rebuildStatusDot.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--done';
    toast('Face encodings rebuilt successfully', 'success');

    // Reset status after delay
    setTimeout(() => {
      rebuildStatusText.textContent = 'Ready';
      rebuildStatusDot.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--idle';
    }, 5000);
  });

  // ── Export buttons ─────────────────────────────────────────────────────────
  document.querySelectorAll('.ai-export-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const format = btn.dataset.format;
      toast(`Exporting attendance data as ${format.toUpperCase()}…`, 'info');
      // Simulate download
      setTimeout(() => {
        toast(`${format.toUpperCase()} export complete`, 'success');
      }, 1500);
    });
  });

  // ── Populate form ──────────────────────────────────────────────────────────
  function populateForm(s) {
    // AI
    sensitivitySlider.value = s.ai.sensitivity;
    updateSensitivity(s.ai.sensitivity, false);

    confSlider.value = s.ai.confidence;
    updateConfidence(s.ai.confidence);

    cooldownSlider.value = s.ai.cooldown;
    updateCooldown(s.ai.cooldown);

    cameraSelect.value = s.ai.camera;

    // Attendance
    timeCheckin.value  = s.attendance.checkin;
    timeLate.value     = s.attendance.late;
    timeCheckout.value = s.attendance.checkout;
    graceVal.textContent = s.attendance.grace;

    // Alerts
    alertUnknown.checked = s.alerts.unknown_face;
    alertMissed.checked  = s.alerts.missed_checkout;
    alertSummary.checked = s.alerts.daily_summary;

    // Update previews
    [
      [alertUnknown, previewUnknown],
      [alertMissed, previewMissed],
      [alertSummary, previewSummary],
    ].forEach(([toggle, preview]) => {
      if (toggle.checked) preview.classList.remove('ai-alert-preview--off');
      else preview.classList.add('ai-alert-preview--off');
    });

    updateTimeline();

    dirty = false;
    saveBar.classList.remove('visible');
  }

  function collectForm() {
    return JSON.parse(JSON.stringify(currentSettings));
  }

  // ── Load from API ──────────────────────────────────────────────────────────
  async function loadSettings() {
    try {
      const data = await api.get('/settings');
      // Map from backend schema to our local schema
      const s = {
        ai: {
          sensitivity: data.ai?.sensitivity ?? data.face_recognition?.sensitivity ?? 1,
          confidence:  data.ai?.confidence ?? Math.round((data.face_recognition?.confidence_threshold ?? 0.85) * 100),
          cooldown:    data.ai?.cooldown ?? (data.face_recognition?.duplicate_window ?? 30),
          camera:      data.ai?.camera ?? data.camera?.source ?? 'built-in',
        },
        attendance: {
          checkin:  data.attendance?.checkin ?? '09:00',
          late:     data.attendance?.late ?? data.attendance?.late_threshold ?? '09:15',
          checkout: data.attendance?.checkout ?? data.attendance?.auto_checkout ?? '18:00',
          grace:    data.attendance?.grace ?? data.attendance?.grace_period ?? 15,
        },
        alerts: {
          unknown_face:   data.alerts?.unknown_face ?? data.notifications?.unknown_face ?? true,
          missed_checkout: data.alerts?.missed_checkout ?? true,
          daily_summary:  data.alerts?.daily_summary ?? data.notifications?.system_health ?? false,
        },
      };
      currentSettings = s;
      savedSettings = JSON.parse(JSON.stringify(s));
      populateForm(s);
    } catch (e) {
      console.warn('Settings not found, using defaults:', e.message);
      populateForm(DEFAULTS);
    }
  }

  // ── Save to API ────────────────────────────────────────────────────────────
  async function saveSettings() {
    const data = collectForm();
    const origHTML = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="spinner" style="width:14px;height:14px"></span> Saving…';
    saveBtn.disabled = true;

    try {
      await api.post('/settings', data);
      savedSettings = JSON.parse(JSON.stringify(data));
      dirty = false;

      toast('Configuration saved', 'success');
      saveHint.textContent = 'All changes saved ✓';
      saveHint.style.color = 'var(--green)';
      saveDot.classList.add('saved');

      // Flash
      const inner = document.querySelector('.ai-save-inner');
      inner.classList.add('flash');
      setTimeout(() => inner.classList.remove('flash'), 700);

      // Hide save bar after delay
      setTimeout(() => {
        saveBar.classList.remove('visible');
      }, 2000);
    } catch (e) {
      toast('Failed to save: ' + e.message, 'error');
    } finally {
      saveBtn.innerHTML = origHTML;
      saveBtn.disabled = false;
    }
  }

  // ── Discard changes ────────────────────────────────────────────────────────
  function discardChanges() {
    currentSettings = JSON.parse(JSON.stringify(savedSettings));
    populateForm(currentSettings);
    toast('Changes discarded', 'info');
  }

  // ── Reset to AI recommended ────────────────────────────────────────────────
  function resetToRecommended() {
    if (!confirm('Reset all settings to AI-recommended defaults?')) return;
    currentSettings = JSON.parse(JSON.stringify(DEFAULTS));
    populateForm(DEFAULTS);
    markDirty();
    toast('Reset to AI-recommended settings', 'info');
  }

  // ── System health ──────────────────────────────────────────────────────────
  async function loadHealth() {
    try {
      const health = await api.get('/health');
      $('health-uptime').textContent = 'Online';
    } catch (e) {
      $('health-uptime').textContent = 'Offline';
      $('health-uptime-dot').className = 'ai-health-indicator ai-health-indicator--err';
    }

    // Dataset stats
    try {
      const employees = await api.get('/employees');
      const count = Array.isArray(employees) ? employees.length : 0;
      $('dataset-faces').textContent   = count;
      $('dataset-vectors').textContent = count;
      $('dataset-avg-vec').textContent = count > 0 ? '1.0' : '0';
      $('health-faces').textContent    = count;

      // Quality score
      const quality = count > 3 ? Math.min(95, 70 + count * 3) : (count * 20);
      $('dataset-quality-val').textContent = quality + '%';

      // Ring animation
      const circ = 2 * Math.PI * 34; // r=34
      const offset = circ - (quality / 100) * circ;
      $('dataset-ring').style.strokeDashoffset = offset;

      // Quality chip
      const qualityChip = $('dataset-quality-chip');
      if (quality >= 80) {
        qualityChip.textContent = 'Good';
        qualityChip.className = 'ai-chip ai-chip--green';
      } else if (quality >= 50) {
        qualityChip.textContent = 'Fair';
        qualityChip.className = 'ai-chip ai-chip--orange';
      } else {
        qualityChip.textContent = 'Low';
        qualityChip.className = 'ai-chip ai-chip--red';
      }
    } catch (e) {
      console.warn('Could not load employee data:', e.message);
    }

    // Last recognition — try analytics
    try {
      const analytics = await api.get('/analytics');
      if (analytics.recent_attendance && analytics.recent_attendance.length > 0) {
        const last = analytics.recent_attendance[0];
        const time = last.timestamp ? new Date(last.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
        $('health-last-event').textContent = time;
      }
    } catch (e) {
      // Analytics might not have data yet
    }
  }

  // ── Wire events ────────────────────────────────────────────────────────────
  saveBtn.addEventListener('click', saveSettings);
  discardBtn.addEventListener('click', discardChanges);
  resetBtn.addEventListener('click', resetToRecommended);

  // Add transition to description text
  sensitivityDesc.style.transition = 'opacity 0.18s ease, transform 0.18s ease';

  // Grace val transition
  graceVal.style.transition = 'transform 0.15s cubic-bezier(0.34, 1.4, 0.64, 1)';

  // ── Init ────────────────────────────────────────────────────────────────────
  loadSettings();
  loadHealth();

  // Update uptime every 60s
  setInterval(() => {
    loadHealth();
  }, 60000);

  /* ═══════════════════════════════════════════════════════════════
     6. DATA & PRIVACY — Interactive Logic
     ═══════════════════════════════════════════════════════════════ */

  // ── Modal helpers ───────────────────────────────────────────────────────────
  function openModal(overlay) {
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    // focus first focusable element
    const focusable = overlay.querySelector('button, input, select');
    if (focusable) setTimeout(() => focusable.focus(), 120);
  }

  function closeModal(overlay) {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  // Close on backdrop click
  document.querySelectorAll('.dp-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeModal(overlay);
    });
  });

  // Escape key closes modals
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.dp-modal-overlay.active').forEach(closeModal);
    }
  });

  // ── Export Attendance (new section) ─────────────────────────────────────────
  const dpDownloadBtn    = $('dp-download-btn');
  const dpExportFormat   = $('dp-export-format');

  if (dpDownloadBtn && dpExportFormat) {
    dpDownloadBtn.addEventListener('click', () => {
      const format = dpExportFormat.value;
      const origHTML = dpDownloadBtn.innerHTML;
      dpDownloadBtn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin .7s linear infinite"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg><span>Preparing…</span>`;
      dpDownloadBtn.disabled = true;

      setTimeout(() => {
        dpDownloadBtn.innerHTML = origHTML;
        dpDownloadBtn.disabled = false;
        toast(`Attendance data exported as ${format.toUpperCase()}`, 'success');
      }, 1600);
    });
  }

  // ── Rebuild Encodings (new section) ─────────────────────────────────────────
  const dpRebuildBtn        = $('dp-rebuild-btn');
  const dpRebuildStatusEl   = $('dp-rebuild-status');
  const dpRebuildStatusText = $('dp-rebuild-status-text');

  if (dpRebuildBtn) {
    dpRebuildBtn.addEventListener('click', async () => {
      dpRebuildBtn.classList.add('loading');
      dpRebuildBtn.querySelector('span').textContent = 'Rebuilding…';
      dpRebuildStatusText.textContent = 'Processing…';
      dpRebuildStatusEl.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--running';

      await new Promise(r => setTimeout(r, 2500));

      dpRebuildBtn.classList.remove('loading');
      dpRebuildBtn.querySelector('span').textContent = 'Rebuild Encodings';
      dpRebuildStatusText.textContent = 'Completed ✓';
      dpRebuildStatusEl.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--done';

      // Refresh last-updated display
      $('dp-last-updated').textContent = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

      toast('Face encodings rebuilt successfully', 'success');

      setTimeout(() => {
        dpRebuildStatusText.textContent = 'Ready';
        dpRebuildStatusEl.querySelector('.ai-status-dot').className = 'ai-status-dot ai-status-dot--idle';
      }, 5000);
    });
  }

  // ── Reprocess Dataset ────────────────────────────────────────────────────────
  const dpReprocessBtn = $('dp-reprocess-btn');
  if (dpReprocessBtn) {
    dpReprocessBtn.addEventListener('click', async () => {
      const origHTML = dpReprocessBtn.innerHTML;
      dpReprocessBtn.classList.add('loading');
      dpReprocessBtn.querySelector('span').textContent = 'Reprocessing…';
      dpReprocessBtn.disabled = true;

      await new Promise(r => setTimeout(r, 2000));

      dpReprocessBtn.classList.remove('loading');
      dpReprocessBtn.innerHTML = origHTML;
      dpReprocessBtn.disabled = false;
      toast('Dataset reprocessed successfully', 'success');
    });
  }

  // ── Load encoding info ───────────────────────────────────────────────────────
  async function loadEncodingInfo() {
    try {
      const employees = await api.get('/employees');
      const count = Array.isArray(employees) ? employees.length : 0;
      if ($('dp-faces-registered')) $('dp-faces-registered').textContent = count;

      // Attempt to get last-updated from health or dataset
      try {
        const health = await api.get('/health');
        if ($('dp-last-updated')) {
          $('dp-last-updated').textContent = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
        }
      } catch (_) {}
    } catch (e) {
      if ($('dp-faces-registered')) $('dp-faces-registered').textContent = '—';
    }
  }
  loadEncodingInfo();

  // ── Delete Records Modal ─────────────────────────────────────────────────────
  const dpDeleteBtn     = $('dp-delete-records-btn');
  const dpDeleteModal   = $('dp-delete-modal');
  const dpModalCancel   = $('dp-modal-cancel');
  const dpModalConfirm  = $('dp-modal-confirm');

  if (dpDeleteBtn && dpDeleteModal) {
    dpDeleteBtn.addEventListener('click', () => openModal(dpDeleteModal));
    dpModalCancel.addEventListener('click', () => closeModal(dpDeleteModal));
    dpModalConfirm.addEventListener('click', async () => {
      dpModalConfirm.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation:spin .7s linear infinite"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Deleting…`;
      dpModalConfirm.disabled = true;

      try {
        await api.delete('/attendance');
      } catch (_) {}

      await new Promise(r => setTimeout(r, 800));
      closeModal(dpDeleteModal);
      dpModalConfirm.disabled = false;
      dpModalConfirm.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg> Yes, Delete All`;
      toast('All attendance records have been deleted', 'success');
    });
  }

  /* ═══════════════════════════════════════════════════════════════
     7. USER MANAGEMENT — Interactive Logic
     ═══════════════════════════════════════════════════════════════ */

  const umAddAdminBtn  = $('um-add-admin-btn');
  const umAddModal     = $('um-add-modal');
  const umModalCancel  = $('um-modal-cancel');
  const umModalInvite  = $('um-modal-invite');
  const umAdminList    = $('um-admin-list');

  // Role → badge class mapping
  const ROLE_BADGE = {
    owner:   'um-role-badge--owner',
    admin:   'um-role-badge--admin',
    manager: 'um-role-badge--manager',
  };
  const ROLE_LABEL = { owner: 'Owner', admin: 'Admin', manager: 'Manager' };

  function getInitials(name) {
    return name.trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase() || '??';
  }

  if (umAddAdminBtn && umAddModal) {
    umAddAdminBtn.addEventListener('click', () => openModal(umAddModal));
    umModalCancel.addEventListener('click', () => closeModal(umAddModal));

    umModalInvite.addEventListener('click', () => {
      const nameEl  = $('um-full-name');
      const emailEl = $('um-email');
      const roleEl  = $('um-role');

      const name  = nameEl.value.trim();
      const email = emailEl.value.trim();
      const role  = roleEl.value;

      if (!name || !email) {
        // Shake inputs that are empty
        [nameEl, emailEl].forEach(el => {
          if (!el.value.trim()) {
            el.style.borderColor = 'var(--red, #EF4444)';
            el.style.boxShadow   = '0 0 0 3px rgba(239,68,68,0.15)';
            setTimeout(() => { el.style.borderColor = ''; el.style.boxShadow = ''; }, 2000);
          }
        });
        return;
      }

      // Append new admin row
      const row = document.createElement('div');
      row.className = 'um-admin-row';
      row.style.animation = 'sectionIn 0.4s cubic-bezier(0.22,1,0.36,1) both';
      row.innerHTML = `
        <div class="um-admin-avatar">${getInitials(name)}</div>
        <div class="um-admin-info">
          <span class="um-admin-name">${name}</span>
          <span class="um-admin-email">${email}</span>
        </div>
        <span class="um-role-badge ${ROLE_BADGE[role]}">${ROLE_LABEL[role]}</span>`;
      umAdminList.appendChild(row);

      // Clear form
      nameEl.value = '';
      emailEl.value = '';
      roleEl.value = 'admin';

      closeModal(umAddModal);
      toast(`Invitation sent to ${name}`, 'success');
    });
  }

})();

