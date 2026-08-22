Auth.requireAuth();
renderLayout('cameras');

let allCameras = [];

async function loadCameras() {
  try {
    allCameras = await api.get('/cameras/');
    const active = allCameras.filter(c => c.status === 'active').length;
    document.getElementById('c-total').textContent = allCameras.length;
    document.getElementById('c-active').textContent = active;
    document.getElementById('c-inactive').textContent = allCameras.length - active;
    renderTable();
  } catch (e) { toast(e.message, 'error'); }
}

function renderTable() {
  const tbody = document.getElementById('cam-table');
  if (!allCameras.length) {
    tbody.innerHTML = `<tr><td colspan="8">
      <div class="empty-state"><span class="empty-icon">📷</span><p>No cameras added yet.</p></div>
    </td></tr>`;
    return;
  }
  tbody.innerHTML = allCameras.map(c => `
    <tr>
      <td>${c.name}</td>
      <td style="color:var(--text-2)">${c.location || '<span style="color:var(--text-3)">—</span>'}</td>
      <td><span class="badge badge-purple">${c.camera_type.toUpperCase()}</span></td>
      <td><code style="font-size:0.73rem;word-break:break-all">${c.stream_url}</code></td>
      <td>${camDot(c.status)}</td>
      <td>${c.is_enabled
        ? '<span class="badge badge-green">Enabled</span>'
        : '<span class="badge badge-gray">Disabled</span>'}</td>
      <td style="color:var(--text-3);font-size:0.8rem">${c.last_heartbeat ? formatTime(c.last_heartbeat) : 'Never'}</td>
      <td>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <button class="btn btn-success btn-sm" onclick="startCamera(${c.id})">Start</button>
          <button class="btn btn-danger btn-sm"  onclick="stopCamera(${c.id})">Stop</button>
          <button class="btn btn-outline btn-sm" onclick="editCamera(${c.id})">Edit</button>
          <button class="btn btn-danger btn-sm"  onclick="deleteCamera(${c.id}, '${c.name}')">Del</button>
        </div>
      </td>
    </tr>`).join('');
}

function openAddCamera() {
  ['cam-id','cam-name','cam-location','cam-url'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('cam-type').value = 'rtsp';
  document.getElementById('cam-modal-title').textContent = 'Add Camera';
  document.getElementById('cam-modal').classList.add('open');
}

function editCamera(id) {
  const c = allCameras.find(x => x.id === id);
  if (!c) return;
  document.getElementById('cam-id').value = c.id;
  document.getElementById('cam-name').value = c.name;
  document.getElementById('cam-location').value = c.location || '';
  document.getElementById('cam-type').value = c.camera_type;
  document.getElementById('cam-url').value = c.stream_url;
  document.getElementById('cam-modal-title').textContent = 'Edit Camera';
  document.getElementById('cam-modal').classList.add('open');
}

async function saveCamera() {
  const btn = document.getElementById('save-cam-btn');
  const id  = document.getElementById('cam-id').value;
  const payload = {
    name:        document.getElementById('cam-name').value.trim(),
    location:    document.getElementById('cam-location').value.trim() || null,
    stream_url:  document.getElementById('cam-url').value.trim(),
    camera_type: document.getElementById('cam-type').value,
  };
  if (!payload.name || !payload.stream_url) { toast('Name and Stream URL required', 'error'); return; }
  showSpinner(btn, 'Saving…');
  try {
    if (id) await api.put(`/cameras/${id}`, { name: payload.name, location: payload.location, stream_url: payload.stream_url });
    else    await api.post('/cameras/', payload);
    toast(id ? 'Camera updated' : 'Camera added', 'success');
    closeModal('cam-modal');
    loadCameras();
  } catch(e) { toast(e.message, 'error'); }
  hideSpinner(btn);
}

async function startCamera(id) {
  try {
    const r = await api.post(`/cameras/${id}/start`);
    toast(r.message, 'success');
    setTimeout(loadCameras, 1000);
  } catch(e) { toast(e.message, 'error'); }
}

async function stopCamera(id) {
  try {
    await api.post(`/cameras/${id}/stop`);
    toast('Camera stopped', 'info');
    setTimeout(loadCameras, 1000);
  } catch(e) { toast(e.message, 'error'); }
}

async function deleteCamera(id, name) {
  if (!confirm(`Delete camera "${name}"?`)) return;
  try {
    await api.delete(`/cameras/${id}`);
    toast('Camera deleted', 'success');
    loadCameras();
  } catch(e) { toast(e.message, 'error'); }
}

function closeModal(id) { document.getElementById(id).classList.remove('open'); }

loadCameras();
setInterval(loadCameras, 15000);
