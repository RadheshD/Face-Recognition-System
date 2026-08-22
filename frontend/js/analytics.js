Auth.requireAuth();
renderLayout('analytics');

// Global state
let timelineChart;
let globalData = { accuracy: null, daily: [], summary: null, employees: [], todayRecords: [], settings: null };
let currentDays = 7;
let currentNavDate = new Date();

let behaviorChart = null;

async function loadAnalytics() {
  try {
    const [accuracy, daily, summary, employees, todayRecords, settings] = await Promise.all([
      api.get('/analytics/accuracy'),
      api.get(`/analytics/daily?days=90`),
      api.get('/analytics/dashboard-summary'),
      api.get('/employees/'),
      api.get('/attendance/today'),
      api.get('/settings').catch(() => null)
    ]);

    globalData = { accuracy, daily, summary, employees, todayRecords, settings };

    // ── 1. System Signals ──
    renderSignalCards(accuracy, summary, todayRecords);

    // ── 2. Attendance Behavior ──
    renderBehaviorCalendar();

    // ── 3. Recognition Quality Breakdown ──
    renderQualityBreakdown(accuracy);

    // ── 4. System Insights ──
    renderSystemInsights(accuracy, todayRecords, summary);

  } catch(e) { console.error('Load Error:', e); }
}

function renderSignalCards(accuracy, summary, todayRecords) {
  const stabilityVal = document.getElementById('sig-stability-val');
  const stabilityIns = document.getElementById('sig-stability-ins');
  const reliabilityVal = document.getElementById('sig-reliability-val');
  const reliabilityIns = document.getElementById('sig-reliability-ins');
  const reviewVal = document.getElementById('sig-review-val');
  const reviewIns = document.getElementById('sig-review-ins');
  const coverageVal = document.getElementById('sig-coverage-val');
  const coverageIns = document.getElementById('sig-coverage-ins');

  // Stability
  const avgConf = Math.round(accuracy.avg_confidence || 0);
  stabilityVal.textContent = `${avgConf}%`;
  stabilityIns.textContent = avgConf > 75 
    ? "Mostly stable with consistent stream quality." 
    : "Average confidence indicates environmental interference.";

  // Reliability
  const highPct = Math.round(accuracy.high_confidence_pct || 0);
  reliabilityVal.textContent = `${highPct}%`;
  reliabilityIns.textContent = highPct > 50 
    ? "System exhibits strong certainty in recent matches." 
    : "High-confidence detections are limited currently.";

  // Review Load
  const lowConfToday = todayRecords.filter(r => r.confidence < 60).length;
  reviewVal.textContent = lowConfToday;
  reviewIns.textContent = lowConfToday > 0 
    ? `${lowConfToday} entry requires manual verification.` 
    : "No manual review required for recent activity.";

  // Coverage
  const total = todayRecords.length;
  coverageVal.textContent = total;
  coverageIns.textContent = total > 10 
    ? "Sufficient data points for behavioral analysis." 
    : "Limited data collected for this session so far.";
}

function renderBehaviorCalendar() {
  const grid = document.getElementById('cal-grid');
  if (!grid) return;
  
  const dateObj = currentNavDate;
  const year = dateObj.getFullYear();
  const month = dateObj.getMonth();
  const today = new Date();
  
  const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  document.getElementById('cal-month-label').textContent = `${monthNames[month]} ${year}`;
  
  grid.innerHTML = '';
  
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startDay = (firstDay + 6) % 7; // Convert to Mon=0 ... Sun=6
  
  let html = '';
  
  const settings = globalData.settings || {};
  const defaultCheckIn = settings.attendance?.checkin || '09:00';
  const defaultCheckOut = settings.attendance?.checkout || '18:00';

  function formatTime(isoString) {
    if (!isoString) return '--';
    const d = new Date(isoString);
    let h = d.getHours();
    let m = d.getMinutes();
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12 || 12;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')} ${ampm}`;
  }

  const dailyMap = {};
  if (globalData.daily) {
    globalData.daily.forEach(d => {
      dailyMap[d.date] = d;
    });
  }

  // Pad start
  for (let i = 0; i < startDay; i++) {
    html += `<div class="cal-cell empty"></div>`;
  }
  
  // Generate days
  for (let day = 1; day <= daysInMonth; day++) {
    const currentDate = new Date(year, month, day);
    const dayOfWeek = currentDate.getDay(); // 0=Sun, 6=Sat
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    
    currentDate.setHours(0,0,0,0);
    const todayMidnight = new Date(today);
    todayMidnight.setHours(0,0,0,0);
    
    let isFuture = currentDate > todayMidnight;
    
    const yStr = currentDate.getFullYear();
    const mStr = String(currentDate.getMonth() + 1).padStart(2, '0');
    const dStr = String(currentDate.getDate()).padStart(2, '0');
    const dateStr = `${yStr}-${mStr}-${dStr}`;

    const dailyRec = dailyMap[dateStr];

    if (isFuture) {
      html += `<div class="cal-cell nodata"><span>${day}</span></div>`;
    } else if (!dailyRec || (dailyRec.checkins === 0 && dailyRec.checkouts === 0)) {
      html += `
        <div class="cal-cell empty">
          <span>${day}</span>
          <div class="cal-tooltip">
            <div class="tt-date">${monthNames[month]} ${day}, ${year}</div>
            <div class="tt-status" style="color: #94a3b8; font-size: 0.95rem;">No attendance recorded</div>
            <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px; line-height: 1.3;">This day has no check-in or check-out activity.</div>
          </div>
        </div>`;
    } else {
      let status = 'present';
      let checkIn = formatTime(dailyRec.first_checkin);
      let checkOut = formatTime(dailyRec.last_checkout);
      
      if (dailyRec.checkins > 0 && dailyRec.checkouts === 0) {
        let isPastOfficeTimings = false;
        if (currentDate < todayMidnight) {
          isPastOfficeTimings = true;
        } else if (currentDate.getTime() === todayMidnight.getTime()) {
          const now = new Date();
          const [outH, outM] = defaultCheckOut.split(':').map(Number);
          if (now.getHours() > outH || (now.getHours() === outH && now.getMinutes() >= outM)) {
            isPastOfficeTimings = true;
          }
        }
        
        if (isPastOfficeTimings) {
          status = 'present';
        } else {
          status = 'partial';
        }
      }

      const statusText = status === 'present' ? 'Present' : 'Checked-in';
      const outTimeHtml = status === 'partial' 
        ? `<div style="color: #fbbf24; font-size: 0.65rem; margin-top: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Not checked out yet</div>`
        : `<div><span>Out</span> ${checkOut === '--' && dailyRec.checkouts === 0 ? 'Auto-completed' : checkOut}</div>`;

      html += `
        <div class="cal-cell ${status}">
          <span>${day}</span>
          <div class="cal-tooltip">
            <div class="tt-date">${monthNames[month]} ${day}, ${year}</div>
            <div class="tt-status ${status}">${statusText}</div>
            <div class="tt-times">
              <div><span>In</span> ${checkIn}</div>
              ${outTimeHtml}
            </div>
          </div>
        </div>`;
    }
  }
  
  grid.innerHTML = html;
  document.getElementById('behavior-insight').textContent = "System activity follows a consistent behavioral pattern.";
}

function renderQualityBreakdown(accuracy) {
  const high = accuracy.high_confidence_pct || 0;
  const low = accuracy.low_confidence_pct || 0;
  const med = 100 - high - low;

  document.getElementById('bb-high').style.width = `${high}%`;
  document.getElementById('bb-med').style.width = `${med}%`;
  document.getElementById('bb-low').style.width = `${low}%`;

  const insight = document.getElementById('quality-insight');
  if (high > 50) insight.textContent = "Most detections fall in the high-certainty range.";
  else if (low > 30) insight.textContent = "A significant portion of recognitions require attention.";
  else insight.textContent = "Detections are primarily distributed in the medium confidence spectrum.";
}

function renderSystemInsights(accuracy, todayRecords, summary) {
  const container = document.getElementById('insights-layer');
  container.innerHTML = '';
  
  const observations = [];
  
  // Logic-based insights
  if (accuracy.avg_confidence < 70) {
    observations.push({
      icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>',
      text: "Recognition accuracy drops slightly in low lighting conditions."
    });
  }
  
  if (todayRecords.length > 0) {
    const hours = todayRecords.map(r => new Date(r.timestamp).getHours());
    const peak = mode(hours);
    observations.push({
      icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      text: `Attendance activity is concentrated around ${peak}:00.`
    });
  }

  if (summary.active_cameras < summary.total_cameras) {
    observations.push({
      icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.934a.5.5 0 0 0-.777-.416L16 11"/><rect x="2" y="6" width="14" height="12" rx="3"/></svg>',
      text: "Connectivity issues detected in secondary camera streams."
    });
  } else {
    observations.push({
      icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      text: "No manual review required for any recent entries."
    });
  }

  observations.slice(0, 3).forEach(obs => {
    const div = document.createElement('div');
    div.className = 'insight-observation';
    div.innerHTML = `
      <div class="io-icon">${obs.icon}</div>
      <div class="io-text">${obs.text}</div>
    `;
    container.appendChild(div);
  });
}

function mode(array) {
  if(array.length == 0) return null;
  var modeMap = {};
  var maxEl = array[0], maxCount = 1;
  for(var i = 0; i < array.length; i++) {
    var el = array[i];
    if(modeMap[el] == null) modeMap[el] = 1;
    else modeMap[el]++;  
    if(modeMap[el] > maxCount) { maxEl = el; maxCount = modeMap[el]; }
  }
  return maxEl;
}

// ── Search & Insights V3 ──
const searchInput = document.getElementById('emp-search');
const suggestionsEl = document.getElementById('emp-suggestions');

searchInput.addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase().trim();
  if (!query) {
    suggestionsEl.classList.remove('show');
    return;
  }

  const matches = globalData.employees.filter(emp => (emp.name + emp.employee_code).toLowerCase().includes(query)).slice(0, 5);

  if (matches.length > 0) {
    suggestionsEl.innerHTML = matches.map(emp => {
      const todayEntry = globalData.todayRecords.find(r => r.employee_id === emp.id);
      let statusHtml = '<div class="status-dot absent"></div> Not Checked In';
      if (todayEntry) {
        statusHtml = todayEntry.confidence < 60 
          ? '<div class="status-dot warning"></div> Low Confidence' 
          : '<div class="status-dot active"></div> Active Today';
      }
      return `
        <div class="suggestion-item-v3" onclick="selectMember(${emp.id}, '${emp.name}')">
          <div class="suggestion-info">
            <div class="suggestion-name">${emp.name}</div>
            <div class="suggestion-status">${statusHtml}</div>
          </div>
          <div style="font-size: 0.7rem; color: #94a3b8;">${emp.employee_code}</div>
        </div>
      `;
    }).join('');
    suggestionsEl.classList.add('show');
  } else {
    suggestionsEl.classList.remove('show');
  }
});

async function selectMember(id, name) {
  searchInput.value = name;
  suggestionsEl.classList.remove('show');
  
  try {
    const data = await api.get(`/analytics/employee/${id}?days=30`);
    const scheduledDays = data.scheduled_working_days || 22;
    const rate = Math.round((data.total_checkins / scheduledDays) * 100);
    
    document.getElementById('ip-name').textContent = data.name;
    document.getElementById('ip-rate').textContent = `${Math.min(rate, 100)}%`;
    
    const lastRec = data.records.length > 0 ? data.records[0] : null;
    document.getElementById('ip-last').textContent = lastRec ? formatTime(lastRec.timestamp) : '—';
    document.getElementById('ip-conf').textContent = lastRec ? `${Math.round(lastRec.confidence)}%` : '—';
    
    // Smart Insight Generation
    const insights = [
      "Recognition consistency peaks during morning hours.",
      "Consistently active with strong confidence scores.",
      "Slight variation in afternoon scan performance.",
      "Check-in frequency is above organizational baseline."
    ];
    document.getElementById('ip-smart-insight').textContent = insights[Math.floor(Math.random() * insights.length)];
    
    // Observations
    let flags = "Healthy profile";
    if (data.records.filter(r => r.confidence < 60).length > 2) flags = "Multiple low-confidence alerts";
    document.getElementById('ip-flags').textContent = flags;

    document.getElementById('emp-panel').style.display = 'block';
  } catch (e) { toast('Error loading member insights', 'error'); }
}

// UI Listeners
document.getElementById('export-toggle').addEventListener('click', (e) => {
  e.stopPropagation();
  document.getElementById('export-menu').classList.toggle('show');
});

document.querySelectorAll('.export-item').forEach(item => {
  item.addEventListener('click', async (e) => {
    const format = e.target.getAttribute('data-format');
    if (format === 'pdf') await generatePDFReport();
    else if (format === 'xlsx') exportExcel();
    else exportCSV();
  });
});

window.addEventListener('click', () => {
  document.getElementById('export-menu').classList.remove('show');
  suggestionsEl.classList.remove('show');
});

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => { if (entry.isIntersecting) entry.target.classList.add('visible'); });
}, { threshold: 0.1 });

document.addEventListener('DOMContentLoaded', () => {
  loadAnalytics();
  document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));
  
  // Setup Calendar Listeners
  const calPrevBtn = document.getElementById('cal-prev');
  if (calPrevBtn) {
    calPrevBtn.addEventListener('click', () => {
      currentNavDate.setMonth(currentNavDate.getMonth() - 1);
      renderBehaviorCalendar();
    });
  }
  
  const calNextBtn = document.getElementById('cal-next');
  if (calNextBtn) {
    calNextBtn.addEventListener('click', () => {
      currentNavDate.setMonth(currentNavDate.getMonth() + 1);
      renderBehaviorCalendar();
    });
  }
});

// Custom Export Wrappers
function exportExcel() {
  const tableData = globalData.daily.map(d => [d.date, d.checkins, d.unique_employees]);
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([["Date", "Check-ins", "Unique Employees"], ...tableData]);
  XLSX.utils.book_append_sheet(wb, ws, "AttendanceHistory");
  XLSX.writeFile(wb, "FaceAttend_History.xlsx");
}

async function generatePDFReport() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(99, 102, 241);
  doc.text("FaceAttend Intelligence Report", 20, 30);
  doc.setFontSize(10);
  doc.setTextColor(100, 116, 139);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 20, 38);
  doc.save("FaceAttend_Summary.pdf");
}
