/* Page-scoped preparation and review, separate from the publishing ledger. */
let groupReviewPage = 1;
let groupReviewRequest = 0;
let groupReviewRows = [];
let groupReviewBusy = false;
const selectedDrafts = new Set();
let groupReviewClock = '';
let groupTodayPreview = null;

async function openGroupReview(groupId = '') {
  const picker = document.getElementById('group-review-group');
  if (!picker) return;
  if (![...picker.options].some(o => o.value === groupId) && groupId) {
    picker.add(new Option(groupId, groupId));
  }
  picker.value = groupId;
  groupReviewPage = 1;
  await loadGroupReview();
  document.getElementById('group-review-panel').scrollIntoView({behavior:'smooth', block:'start'});
}

async function loadGroupReviewSummary() {
  const [response, pipelineResponse] = await Promise.all([fetch('/api/groups/post-summary'), fetch('/api/output-pipeline/status')]);
  const data = await response.json();
  const pipelineData = await pipelineResponse.json();
  if (!response.ok || !data.success) throw new Error(data.error || 'Không tải được nhóm');
  groupReviewClock = data.server_now || groupReviewClock;
  const picker = document.getElementById('group-review-group');
  const chosen = picker.value;
  picker.innerHTML = '<option value="">Tất cả nhóm đã chọn</option>' + data.groups.map(g =>
    `<option value="${escapeHtml(g.id)}">${escapeHtml(g.name)} · ${g.counts.preparing || 0} chuẩn bị · ${g.counts.draft || 0} Draft</option>`).join('');
  picker.value = chosen;
  await loadGroupReviewPages();
  document.getElementById('group-review-stock').textContent = `${data.stock} video trong kho chờ phân bổ. Chọn nhóm rồi bấm “Lấy từ kho cho hôm nay”. Daily dùng giờ cố định và có thể đặt ngày mai nếu hôm nay đã hết khung giờ.`;
  const pipeline = pipelineData.pipeline || {};
  const systemStatus = document.getElementById('group-review-system-status');
  if (systemStatus) {
    systemStatus.style.color = pipeline.error || !pipeline.alive ? '#fbbf24' : '#94a3b8';
    systemStatus.textContent = `${pipeline.alive ? 'Pipeline output đang chạy' : 'Pipeline output đang dừng'}${pipeline.paused ? ' · Render tạm chờ: ' + (pipeline.reason === 'backlog_limit' ? 'kho đã đủ ' + pipeline.backlog + '/' + pipeline.max_backlog + ' video' : pipeline.reason) : ''}${pipeline.error ? ' · Lỗi: ' + pipeline.error : ''}`;
  }
  document.getElementById('group-review-summary').innerHTML = data.groups.map(g =>
    `<button class="btn btn-outline btn-sm" data-group-id="${escapeHtml(g.id)}" onclick="openGroupReview(this.dataset.groupId)" style="white-space:normal;text-align:left;">${escapeHtml(g.name)}<br><small>${g.daily ? '● Post hàng ngày' : 'Post hàng ngày: tắt'} · ${g.counts.preparing || 0} chuẩn bị · ${g.counts.draft || 0} Draft</small></button>`).join('');
  return data;
}

async function loadGroupReviewPages() {
  const target = document.getElementById('group-review-page-filter');
  if (!target) return;
  const response = await fetch('/api/pages');
  const data = await response.json();
  const chosen = target.value;
  target.innerHTML = '<option value="">Tất cả Page</option>' + (data.pages || []).map(p =>
    `<option value="${escapeHtml(String(p.page_id))}">${escapeHtml(p.page_name || p.page_id)}</option>`).join('');
  target.value = chosen;
}

async function loadGroupReview() {
  if (!document.getElementById('group-review-body')) return;
  const generation = ++groupReviewRequest;
  const group = document.getElementById('group-review-group').value;
  const bucket = document.getElementById('group-review-status').value;
  const pageId = document.getElementById('group-review-page-filter').value;
  try {
    const response = await fetch(`/api/posts/list?view=review&group_id=${encodeURIComponent(group)}&page_id=${encodeURIComponent(pageId)}&bucket=${encodeURIComponent(bucket)}&page=${groupReviewPage}&page_size=30`);
    const data = await response.json();
    if (generation !== groupReviewRequest) return;
    if (!response.ok || !data.success) throw new Error(data.error || 'Không tải được Draft');
    groupReviewRows = data.items;
    groupReviewPage = data.page;
    selectedDrafts.clear();
    document.getElementById('group-review-pagination').textContent = `Trang ${data.page}/${data.pages} · ${data.total} bài · ${data.counts.preparing || 0} chuẩn bị · ${data.counts.draft || 0} Draft`;
    document.getElementById('group-review-prev').disabled = data.page <= 1;
    document.getElementById('group-review-next').disabled = data.page >= data.pages;
    document.getElementById('group-review-body').innerHTML = data.items.map(p => {
      const ready = p.status === 'draft' && p.content_package_status === 'ready' && p.website_status === 'ready';
      const selectable = ['draft','preparing'].includes(p.status) && !p.content_frozen_at && !['meta_upload_video_id','meta_video_id','meta_post_id','post_fb_id','reel_id','outcome_unknown','publish_started_at','claimed_at'].some(k => p[k]);
      const error = p.schedule_error || p.website_error || p.content_package_error || '';
      const link = /^https?:\/\//i.test(p.article_url || '') ? `<a href="${escapeHtml(p.article_url)}" target="_blank" rel="noopener">Bài Website</a>` : 'Website đang chuẩn bị';
      return `<tr data-review-post-id="${escapeHtml(p.id)}">
        <td style="padding:12px;">${selectable ? `<input type="checkbox" data-draft-id="${escapeHtml(p.id)}" onchange="selectGroupDraft(this.dataset.draftId,this.checked)" aria-label="Chọn bài">` : ''}</td>
        <td style="padding:12px;max-width:300px;"><strong>${escapeHtml(p.title || p.media_file)}</strong><div style="font-size:11px;color:#94a3b8;">${escapeHtml(p.media_file)}<br>${escapeHtml(p.group_name || 'Page chọn riêng')}</div><a href="${escapeHtml(p.local_video_url || '')}" target="_blank" rel="noopener">Xem video</a> · ${link}</td>
        <td style="padding:12px;"><strong style="color:#60a5fa;">${escapeHtml(p.page_name || p.page_id)}</strong><div style="font-size:11px;color:#fbbf24;">${escapeHtml(p.token_display_name || p.token_id)}</div></td>
        <td style="padding:12px;font-size:12px;">${escapeHtml(p.scheduled_time || 'Chưa hẹn')}<div style="color:#38bdf8;">${p.requested_publish_mode === 'meta_scheduled' ? 'Meta giữ lịch' : 'App giữ lịch'}</div></td>
        <td style="padding:12px;max-width:260px;"><strong style="color:${ready ? '#4ade80' : '#fbbf24'};">${ready ? 'Draft · sẵn sàng duyệt' : 'Đang chuẩn bị'}</strong><div style="font-size:11px;color:#fca5a5;white-space:normal;">${escapeHtml(error)}</div>${error ? `<button class="btn btn-outline btn-sm" data-post-id="${escapeHtml(p.id)}" onclick="retryGroupWebsite(this.dataset.postId)">Thử lại Website</button>` : ''}</td>
        <td style="padding:12px;"><button class="btn btn-outline btn-sm" data-post-id="${escapeHtml(p.id)}" onclick="openOutputDraft(this.dataset.postId)">Xem / sửa / duyệt</button>${ready ? `<button class="btn btn-primary btn-sm" data-post-id="${escapeHtml(p.id)}" onclick="approveGroupDrafts(this.dataset.postId)" style="margin-top:6px;">Duyệt & lên lịch</button>` : ''}</td>
      </tr>`;
    }).join('') || '<tr><td colspan="6" style="padding:25px;color:#94a3b8;text-align:center;">Chưa có bài cần duyệt trong nhóm này. Bật Post hàng ngày để nhận video mới từ kho.</td></tr>';
    updateGroupDraftSelection();
  } catch (error) {
    if (generation === groupReviewRequest) document.getElementById('group-review-result').textContent = error.message;
  }
}

function selectGroupDraft(id, checked) {
  if (checked) selectedDrafts.add(id); else selectedDrafts.delete(id);
  updateGroupDraftSelection();
}
function selectAllGroupDrafts(checked) {
  document.querySelectorAll('[data-draft-id]').forEach(input => { input.checked = checked; selectGroupDraft(input.dataset.draftId, checked); });
}
function updateGroupDraftSelection() {
  const button = document.getElementById('group-review-approve');
  const ready = groupReviewRows.filter(p => selectedDrafts.has(p.id) && p.status === 'draft' && p.content_package_status === 'ready' && p.website_status === 'ready');
  button.disabled = groupReviewBusy || !ready.length;
  button.textContent = `Duyệt ${ready.length} Draft theo lịch đã lưu`;
  document.getElementById('group-review-today-selected').disabled = groupReviewBusy || !selectedDrafts.size;
  const all = document.getElementById('group-review-select-all');
  const inputs = [...document.querySelectorAll('[data-draft-id]')];
  all.checked = inputs.length > 0 && inputs.every(i => i.checked);
  all.disabled = groupReviewBusy || !inputs.length;
}

async function approveGroupDrafts(singleId = '') {
  if (groupReviewBusy) return;
  const ids = singleId ? [singleId] : groupReviewRows.filter(p => selectedDrafts.has(p.id) && p.status === 'draft' && p.content_package_status === 'ready' && p.website_status === 'ready').map(p => p.id);
  if (!ids.length) return;
  groupReviewBusy = true; updateGroupDraftSelection();
  const feedback = document.getElementById('group-review-result');
  feedback.textContent = `Đang duyệt ${ids.length} bài theo Page, Token và lịch đã lưu…`;
  try {
    const response = await fetch('/api/posts/review-batch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_ids:ids})});
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Chưa duyệt được');
    feedback.textContent = `Đã duyệt ${data.approved}/${ids.length} bài. ` + (data.results || []).filter(r => !r.approved).map(r => r.error).join('\n');
    await Promise.all([loadGroupReview(), loadGroupReviewSummary()]);
  } catch(error) { feedback.textContent = error.message; }
  finally { groupReviewBusy = false; updateGroupDraftSelection(); }
}

function invalidateGroupTodayPreview() {
  groupTodayPreview = null;
  document.getElementById('group-today-apply').disabled = true;
}

async function openGroupToday(scope = 'selected') {
  if (groupReviewBusy) return;
  const groupId = document.getElementById('group-review-group').value;
  if (!groupId) { showToast('Chọn một nhóm Page trước khi lên lịch hôm nay.'); return; }
  if (scope === 'selected' && !selectedDrafts.size) return;
  await loadGroupReviewSummary();
  const modal = document.getElementById('group-today-modal');
  modal.dataset.scope = scope;
  modal.dataset.groupId = groupId;
  const current = new Date(groupReviewClock || Date.now());
  current.setMinutes(current.getMinutes() + 31, 0, 0);
  document.getElementById('group-today-start').value = `${String(current.getHours()).padStart(2,'0')}:${String(current.getMinutes()).padStart(2,'0')}`;
  document.getElementById('group-today-date').textContent = `${groupReviewClock.slice(0,10)} · giờ trên máy chạy app`;
  document.getElementById('group-today-scope').textContent = scope === 'group' ? 'Tất cả bài đang chuẩn bị và Draft của nhóm đã chọn' : scope === 'stock' ? 'Lấy video chưa phân bổ từ kho vào nhóm đã chọn' : `${selectedDrafts.size} bài đã chọn trong nhóm`;
  document.getElementById('group-today-stock-label').style.display = scope === 'stock' ? '' : 'none';
  document.getElementById('group-today-result').textContent = 'Xem trước để kiểm tra ngày, giờ cuối và số bài còn chỗ.';
  invalidateGroupTodayPreview();
  modal.style.display = 'flex';
}

function closeGroupToday() {
  if (groupReviewBusy) return;
  document.getElementById('group-today-modal').style.display = 'none';
  invalidateGroupTodayPreview();
}

function groupTodayOptions() {
  const modal = document.getElementById('group-today-modal');
  return {scope:modal.dataset.scope, group_id:modal.dataset.groupId, post_ids:[...selectedDrafts],
    start_time:document.getElementById('group-today-start').value,
    interval_minutes:Number(document.getElementById('group-today-gap').value),
    publish_mode:document.getElementById('group-today-mode').value,
    approval_mode:document.getElementById('group-today-approval').value,
    stock_count:Number(document.getElementById('group-today-stock').value)};
}

async function previewGroupToday() {
  if (groupReviewBusy) return;
  const body = groupTodayOptions();
  invalidateGroupTodayPreview();
  groupReviewBusy = true;
  const feedback = document.getElementById('group-today-result');
  feedback.textContent = 'Đang kiểm tra lịch hôm nay…';
  try {
    const response = await fetch('/api/posts/schedule-today', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Không xem trước được');
    // Ignore a response if inputs changed while the request was running.
    if (JSON.stringify(body) !== JSON.stringify(groupTodayOptions())) { feedback.textContent='Lựa chọn đã đổi; bấm Xem trước lại.'; return; }
    groupTodayPreview = {body:{...body,start_time:data.start_time}, revision:data.revision};
    feedback.textContent = `${data.count}/${data.requested} bài có lịch ngày ${data.date}.\n${data.first_time || '—'} → ${data.last_time || '—'}\n${data.automatic} bài tự lên lịch khi nội dung/Website sẵn sàng; ${data.count-data.automatic} bài chờ duyệt Draft.\n${data.overflow.length} bài hết chỗ hôm nay; ${data.skipped.length} bài bỏ qua. Bài hết chỗ giữ nguyên lịch cũ.`;
    if (body.scope !== 'selected') feedback.textContent += '\nDaily tạm ngừng phân bổ thêm cho nhóm đến hết hôm nay, tiếp tục ngày mai. Dùng Lấy từ kho nếu cần thêm bài hôm nay.';
    document.getElementById('group-today-apply').disabled = !data.count;
  } catch (error) { feedback.textContent = error.message; }
  finally { groupReviewBusy = false; updateGroupDraftSelection(); }
}

async function applyGroupToday() {
  if (groupReviewBusy || !groupTodayPreview) return;
  groupReviewBusy = true;
  document.getElementById('group-today-apply').disabled = true;
  const feedback = document.getElementById('group-today-result');
  try {
    const response = await fetch('/api/posts/schedule-today', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({...groupTodayPreview.body,revision:groupTodayPreview.revision,apply:true})});
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Không lưu được lịch');
    feedback.textContent = `Đã lưu lịch hôm nay ${data.date} cho ${data.count} bài. Giờ cuối ${data.last_time}. ${data.overflow.length} bài hết chỗ giữ nguyên lịch cũ. Bài đang chuẩn bị tiếp tục làm Website trước khi đăng.`;
    document.getElementById('group-review-result').textContent = feedback.textContent;
    groupTodayPreview = null;
    await Promise.all([loadGroupReview(),loadGroupReviewSummary()]);
  } catch(error) { feedback.textContent = error.message; invalidateGroupTodayPreview(); }
  finally { groupReviewBusy = false; updateGroupDraftSelection(); }
}

async function retryGroupWebsite(postId) {
  try {
    const response = await fetch(`/api/posts/${encodeURIComponent(postId)}/retry-website`, {method:'POST'});
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Chưa thử lại được');
    showToast(data.message || 'Đã xếp hàng kiểm tra Website');
    await loadGroupReview();
  } catch(error) { showToast(error.message); }
}

document.addEventListener('DOMContentLoaded', () => {
  setInterval(() => {
    if (document.getElementById('pane-groups')?.classList.contains('active') && !groupReviewBusy && !selectedDrafts.size &&
        document.getElementById('draft-review-modal')?.style.display !== 'flex' && document.getElementById('group-today-modal')?.style.display !== 'flex') {
      loadGroupReview(); loadGroupReviewSummary().catch(() => {});
    }
  }, 15000);
});
