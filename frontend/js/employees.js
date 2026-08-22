Auth.requireAuth();
renderLayout('employees');

let allEmployees = [];
let faceTargetId = null;

async function loadEmployees() {
  try {
    allEmployees = await api.get('/employees/');
    document.getElementById('emp-count').textContent = `${allEmployees.length} employees`;
    renderTable(allEmployees);
  } catch (e) { toast(e.message, 'error'); }
}

function renderTable(list) {
  const tbody = document.getElementById('emp-table');
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="8">
      <div class="empty-state"><span class="empty-icon">👥</span><p>No employees yet. Add one to get started.</p></div>
    </td></tr>`;
    return;
  }
  tbody.innerHTML = list.map((e, i) => `
    <tr>
      <td style="color:var(--text-3);font-size:0.8rem">${i + 1}</td>
      <td><code>${e.employee_code}</code></td>
      <td>${e.name}</td>
      <td style="color:var(--text-2)">${e.department || '<span style="color:var(--text-3)">—</span>'}</td>
      <td>${e.face_registered
        ? `<span class="badge badge-green">✓ Enrolled</span>`
        : `<span class="badge badge-red">✗ Not set</span>`}</td>
      <td>${e.is_active
        ? '<span class="badge badge-blue">Active</span>'
        : '<span class="badge badge-gray">Inactive</span>'}</td>
      <td style="color:var(--text-2)">${formatDate(e.created_at)}</td>
      <td>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <button class="btn btn-outline btn-sm" onclick="editEmployee(${e.id})">Edit</button>
          <button class="btn btn-primary btn-sm" onclick="openFaceModal(${e.id}, '${e.name}')">Face</button>
          <button class="btn btn-danger btn-sm" onclick="deleteEmployee(${e.id}, '${e.name}')">Delete</button>
        </div>
      </td>
    </tr>`).join('');
}

document.getElementById('search-emp').addEventListener('input', (e) => {
  const q = e.target.value.toLowerCase();
  renderTable(allEmployees.filter(emp =>
    emp.name.toLowerCase().includes(q) || emp.employee_code.toLowerCase().includes(q)
  ));
});

// ── Add / Edit ────────────────────────────────────────────────────────────────
document.getElementById('add-emp-btn').addEventListener('click', () => {
  document.getElementById('emp-id').value = '';
  document.getElementById('emp-code').value = '';
  document.getElementById('emp-name').value = '';
  document.getElementById('emp-email').value = '';
  document.getElementById('emp-dept').value = '';
  document.getElementById('emp-position').value = '';
  document.getElementById('emp-modal-title').textContent = 'Add Employee';
  document.getElementById('emp-code').disabled = false;
  document.getElementById('emp-modal').classList.add('open');
});

function editEmployee(id) {
  const emp = allEmployees.find(e => e.id === id);
  if (!emp) return;
  document.getElementById('emp-id').value = emp.id;
  document.getElementById('emp-code').value = emp.employee_code;
  document.getElementById('emp-name').value = emp.name;
  document.getElementById('emp-email').value = emp.email || '';
  document.getElementById('emp-dept').value = emp.department || '';
  document.getElementById('emp-position').value = emp.position || '';
  document.getElementById('emp-modal-title').textContent = 'Edit Employee';
  document.getElementById('emp-code').disabled = true;
  document.getElementById('emp-modal').classList.add('open');
}

async function saveEmployee() {
  const btn  = document.getElementById('save-emp-btn');
  const id   = document.getElementById('emp-id').value;
  const code = document.getElementById('emp-code').value.trim();
  const name = document.getElementById('emp-name').value.trim();
  if (!name) { toast('Name is required', 'error'); return; }
  showSpinner(btn, 'Saving…');
  try {
    if (id) {
      await api.put(`/employees/${id}`, {
        name,
        email:      document.getElementById('emp-email').value.trim() || null,
        department: document.getElementById('emp-dept').value.trim() || null,
        position:   document.getElementById('emp-position').value.trim() || null,
      });
      toast('Employee updated', 'success');
    } else {
      if (!code) { hideSpinner(btn); toast('Employee ID required', 'error'); return; }
      await api.post('/employees/', {
        employee_code: code, name,
        email:      document.getElementById('emp-email').value.trim() || null,
        department: document.getElementById('emp-dept').value.trim() || null,
        position:   document.getElementById('emp-position').value.trim() || null,
      });
      toast('Employee created', 'success');
    }
    closeModal('emp-modal');
    loadEmployees();
  } catch (e) { toast(e.message, 'error'); }
  hideSpinner(btn);
}

async function deleteEmployee(id, name) {
  if (!confirm(`Delete employee "${name}"? This cannot be undone.`)) return;
  try {
    await api.delete(`/employees/${id}`);
    toast('Employee deleted', 'success');
    loadEmployees();
  } catch (e) { toast(e.message, 'error'); }
}

// ── Face registration ─────────────────────────────────────────────────────────
function openFaceModal(empId, empName) {
  faceTargetId = empId;
  document.querySelector('#face-modal .modal-title').textContent = `Register Face — ${empName}`;
  document.getElementById('face-result').style.display = 'none';
  document.getElementById('face-modal').classList.add('open');
  const video = document.getElementById('face-video');
  document.getElementById('face-status').textContent = 'Starting camera…';
  Webcam.start(video).then(ok => {
    if (ok) document.getElementById('face-status').textContent = 'Camera ready — look at the camera';
  });
}

function closeFaceModal() {
  Webcam.stop();
  document.getElementById('face-modal').classList.remove('open');
}

async function captureFace() {
  const btn      = document.getElementById('capture-btn');
  const video    = document.getElementById('face-video');
  const resultEl = document.getElementById('face-result');
  showSpinner(btn, 'Registering…');
  try {
    const b64 = Webcam.captureBase64(video);
    if (!b64) {
      toast('Camera not ready — try again.', 'error');
      hideSpinner(btn);
      return;
    }

    const data = await api.post('/employees/register-face', {
      employee_id:  faceTargetId,
      image_base64: b64,
    });

    if (data.success) {
      resultEl.innerHTML = `<div class="badge badge-green" style="padding:8px 16px;font-size:0.84rem">✓ ${data.message}</div>`;
      resultEl.style.display = 'block';
      toast('Face registered successfully!', 'success');
      loadEmployees();
    } else {
      resultEl.innerHTML = `<div class="badge badge-red" style="padding:8px 16px;font-size:0.84rem">✕ ${data.message}</div>`;
      resultEl.style.display = 'block';
      toast(data.message, 'error');
    }
  } catch (e) {
    toast(e.message, 'error');
  }
  hideSpinner(btn);
}


function closeModal(id) { document.getElementById(id).classList.remove('open'); }

loadEmployees();
