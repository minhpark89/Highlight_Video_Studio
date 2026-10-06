/* Verified stock selection and a local render fallback. No upload on selection. */
let recoveryCandidates = [], recoveryOffset = 0, recoveryNext = null, recoveryRenderTimer = null;
function recoverySize(bytes) { return (Number(bytes || 0) / 1048576).toFixed(1) + ' MB'; }
function recoveryCard(item) {
  const info = item.duration ? `${Number(item.duration).toFixed(1)} giây · ${Number(item.width)}×${Number(item.height)} · ${recoverySize(item.size)}` : '';
  return `<label style="display:block;border:1px solid ${item.valid ? '#475569' : '#7f1d1d'};border-radius:8px;padding:10px;margin:8px 0;overflow-wrap:anywhere;">
    <input type="radio" name="recovery-video-choice" value="${escapeHtml(item.filename)}" ${item.valid ? '' : 'disabled'} onchange="chooseRecoveryVideo(this.value)">
    <b>${escapeHtml(item.title || item.filename)}</b><div>${escapeHtml(info)}</div>
    <small>${escapeHtml(item.filename)}</small><div style="color:${item.valid ? '#86efac' : '#fca5a5'};">${item.valid ? 'MP4 đã kiểm tra' + (item.same_file ? ' · File hiện tại; nếu Meta vẫn từ chối, dùng render lại.' : '') : escapeHtml(item.reason)}</div>
    ${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener">Xem video gốc</a>` : ''}</label>`;
}
async function mountRecoveryVideos(body, postId) {
  clearTimeout(recoveryRenderTimer); recoveryCandidates = []; recoveryOffset = 0;
  const container = document.createElement('div'); container.style = 'margin-top:16px;';
  container.innerHTML = `<div style="color:#fbbf24;margin-bottom:8px;">Chọn clip đã kiểm tra trong kho. App chuẩn bị Content, Website có embed video gốc và First Comment đúng clip trước khi đăng.</div>
    <div id="recovery-stock-status" role="status"></div><div id="recovery-stock-list"></div>
    <div style="display:flex;gap:8px;"><button type="button" id="recovery-prev" class="btn btn-outline btn-sm" onclick="loadRecoveryVideos(Math.max(0,recoveryOffset-12))">Trước</button><button type="button" id="recovery-next" class="btn btn-outline btn-sm" onclick="loadRecoveryVideos(recoveryNext)">Xem thêm</button></div>
    <input id="meta-replacement-file" type="hidden"><div id="recovery-selected" style="margin:10px 0;color:#86efac;"></div>
    <video id="recovery-preview" controls preload="metadata" style="display:none;width:100%;max-height:240px;background:#000;"></video>
    <div style="margin-top:12px;"><button type="button" id="recovery-render" class="btn btn-outline btn-sm" onclick="renderRecoveryVideo()">Không có clip phù hợp: render lại từ video gốc</button><div id="recovery-render-status" role="status" style="margin-top:8px;white-space:pre-line;"></div><div id="recovery-rendered-choice"></div></div>
    <label for="meta-replacement-mode">Cách đăng lại sau khi Content sẵn sàng</label><select id="meta-replacement-mode" class="form-control"><option value="app_queue">Đăng lại bằng App ngay</option><option value="meta_scheduled">Meta giữ lịch</option></select>
    <label for="meta-replacement-schedule">Giờ mới (App: có thể để trống; Meta: cần đủ thời gian chuẩn bị và ít nhất 30 phút)</label><input id="meta-replacement-schedule" type="datetime-local" class="form-control">`;
  body.appendChild(container);
  document.getElementById('meta-replace-failed').style.display = '';
  document.getElementById('meta-replace-failed').disabled = true;
  await loadRecoveryVideos(0, postId);
}
function chooseRecoveryVideo(filename) {
  const item = recoveryCandidates.find(row => row.filename === filename && row.valid);
  if (!item) return;
  document.getElementById('meta-replacement-file').value = filename;
  document.getElementById('recovery-selected').textContent = 'Đã chọn: ' + item.title + ' · ' + Number(item.duration).toFixed(1) + ' giây';
  const preview = document.getElementById('recovery-preview');
  preview.src = '/api/posts/' + encodeURIComponent(currentMetaDiagnosisPost) + '/recovery-preview?filename=' + encodeURIComponent(filename);
  preview.style.display = 'block';
  document.getElementById('meta-replace-failed').disabled = false;
  document.querySelectorAll('input[name="recovery-video-choice"]').forEach(input => { input.checked = input.value === filename; });
}
async function loadRecoveryVideos(offset, postId = currentMetaDiagnosisPost) {
  if (offset == null || postId !== currentMetaDiagnosisPost) return;
  const status = document.getElementById('recovery-stock-status'); if (!status) return;
  status.textContent = 'Đang kiểm tra MP4, thời lượng và nguồn của 12 clip...';
  document.getElementById('recovery-next').disabled = true;
  try {
    const response = await fetch('/api/posts/' + encodeURIComponent(postId) + '/recovery-videos?offset=' + offset);
    const data = await response.json(); if (postId !== currentMetaDiagnosisPost || !document.getElementById('recovery-stock-list')) return;
    if (!response.ok || !data.success) throw new Error(data.error || 'Không đọc được kho');
    recoveryOffset = data.offset; recoveryNext = data.next_offset;
    const rendered = recoveryCandidates.filter(row => row.rendered);
    recoveryCandidates = [...data.candidates, ...rendered];
    document.getElementById('recovery-stock-list').innerHTML = data.candidates.map(recoveryCard).join('') || '<div>Kho chưa có MP4 để chọn.</div>';
    status.textContent = `${data.candidates.filter(row => row.valid).length} clip dùng được trong ${data.candidates.length} clip vừa kiểm tra · Kho ${data.total} clip.`;
    document.getElementById('recovery-prev').disabled = offset === 0;
    document.getElementById('recovery-next').disabled = recoveryNext == null;
    const selected = document.getElementById('meta-replacement-file').value;
    document.querySelectorAll('input[name="recovery-video-choice"]').forEach(input => { input.checked = input.value === selected; });
    if (data.render_task) showRecoveryRenderTask(data.render_task, postId);
  } catch (error) { if (postId === currentMetaDiagnosisPost) status.textContent = error.message; }
}
function showRecoveryRenderTask(task, postId) {
  if (postId !== currentMetaDiagnosisPost) return;
  const status = document.getElementById('recovery-render-status'); if (!status) return;
  status.textContent = task.message || task.status;
  const active = ['queued', 'running'].includes(task.status);
  document.getElementById('recovery-render').disabled = active;
  clearTimeout(recoveryRenderTimer);
  if (task.status === 'ready') {
    const candidate = {...task, valid: true, rendered: true};
    recoveryCandidates = [...recoveryCandidates.filter(row => row.filename !== candidate.filename), candidate];
    document.getElementById('recovery-rendered-choice').innerHTML = recoveryCard(candidate);
  }
  if (active) recoveryRenderTimer = setTimeout(() => pollRecoveryRender(postId), 2000);
}
async function pollRecoveryRender(postId) {
  if (postId !== currentMetaDiagnosisPost || document.getElementById('modal-meta-diagnosis').style.display === 'none') return;
  try {
    const response = await fetch('/api/posts/' + encodeURIComponent(postId) + '/render-recovery');
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Chưa đọc được render');
    if (data.task) showRecoveryRenderTask(data.task, postId);
  } catch (error) {
    if (postId !== currentMetaDiagnosisPost) return;
    const status = document.getElementById('recovery-render-status'); if (status) status.textContent = error.message + ' · Đang đọc lại...';
    recoveryRenderTimer = setTimeout(() => pollRecoveryRender(postId), 4000);
  }
}
async function renderRecoveryVideo() {
  if (!currentMetaDiagnosis?.diagnosis?.can_replace_failed_video) return;
  if (!confirm('Render MP4 mới từ video gốc? Bạn sẽ xem trước và chọn clip sau khi render xong.')) return;
  const postId = currentMetaDiagnosisPost;
  const button = document.getElementById('recovery-render'); button.disabled = true;
  try {
    const response = await fetch('/api/posts/' + encodeURIComponent(postId) + '/render-recovery', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({confirm_render:true, video_id:currentMetaDiagnosis.diagnosis.video_id})});
    const data = await response.json(); if (postId !== currentMetaDiagnosisPost) return;
    if (!response.ok || !data.success) throw new Error(data.error || 'Chưa render được');
    showRecoveryRenderTask(data.task, postId);
  } catch (error) {
    if (postId === currentMetaDiagnosisPost) { document.getElementById('recovery-render-status').textContent = error.message; button.disabled = false; }
  }
}
