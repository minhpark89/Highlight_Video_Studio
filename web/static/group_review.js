/* Page-scoped preparation and review, separate from the publishing ledger. */
let groupReviewPage = 1;
let groupReviewRequest = 0;
let groupReviewRows = [];
let groupReviewBusy = false;
const selectedDrafts = new Set();

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
  const response = await fetch('/api/groups/post-summary');
  const data = await response.json();
  if (!response.ok || !data.success) throw new Error(data.error || 'Không tải được nhóm');
  const picker = document.getElementById('group-review-group');
  const chosen = picker.value;
  picker.innerHTML = '<option value="">Tất cả nhóm đã chọn</option>' + data.groups.map(g =>
    `<option value="${escapeHtml(g.id)}">${escapeHtml(g.name)} · ${g.counts.preparing || 0} chuẩn bị · ${g.counts.draft || 0} Draft</option>`).join('');
  picker.value = chosen;
  await loadGroupReviewPages();
  document.getElementById('group-review-stock').textContent = `${data.stock} video trong kho chờ phân bổ. Bật Post hàng ngày ở nhóm cần dùng; app gắn Page, Token và giờ trước khi đưa vào danh sách duyệt.`;
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
      const error = p.website_error || p.content_package_error || '';
      const link = /^https?:\/\//i.test(p.article_url || '') ? `<a href="${escapeHtml(p.article_url)}" target="_blank" rel="noopener">Bài Website</a>` : 'Website đang chuẩn bị';
      return `<tr data-review-post-id="${escapeHtml(p.id)}">
        <td style="padding:12px;">${ready ? `<input type="checkbox" data-draft-id="${escapeHtml(p.id)}" onchange="selectGroupDraft(this.dataset.draftId,this.checked)" aria-label="Chọn Draft">` : ''}</td>
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
  button.disabled = groupReviewBusy || !selectedDrafts.size;
  button.textContent = `Duyệt & lên lịch ${selectedDrafts.size} bài đã chọn`;
  const all = document.getElementById('group-review-select-all');
  const inputs = [...document.querySelectorAll('[data-draft-id]')];
  all.checked = inputs.length > 0 && inputs.every(i => i.checked);
  all.disabled = groupReviewBusy || !inputs.length;
}

async function approveGroupDrafts(singleId = '') {
  if (groupReviewBusy) return;
  const ids = singleId ? [singleId] : [...selectedDrafts];
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
        document.getElementById('draft-review-modal')?.style.display !== 'flex') {
      loadGroupReview(); loadGroupReviewSummary().catch(() => {});
    }
  }, 15000);
});
