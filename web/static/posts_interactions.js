/* Keep controls stable while paginated rows refresh. */
function renderPostFilters(counts) {
  const container = document.getElementById('posts-schedule-summary');
  if (!container) return;
  const existing = new Map([...container.children].map(button => [button.dataset.bucket, button]));
  for (const [key, label, count] of counts) {
    let button = existing.get(key);
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-outline btn-sm';
      button.dataset.bucket = key;
      button.addEventListener('click', () => filterPostsSchedule(key));
      container.appendChild(button);
    }
    const text = `${label} ${count}`;
    if (button.textContent !== text) button.textContent = text;
    const selected = postsScheduleFilter === key;
    button.setAttribute('aria-pressed', String(selected));
    button.classList.toggle('posts-filter-selected', selected);
  }
}

function showPostsLoading(loading, error = '') {
  const table = document.getElementById('posts-table-body');
  if (!table) return;
  table.setAttribute('aria-busy', String(loading));
  let feedback = document.getElementById('posts-load-feedback');
  if (!feedback) {
    feedback = document.createElement('div');
    feedback.id = 'posts-load-feedback';
    feedback.setAttribute('role', 'status');
    const label = document.getElementById('posts-page-label');
    label.parentElement.insertBefore(feedback, label.nextSibling);
  }
  feedback.textContent = error || (loading ? 'Đang tải…' : '');
  feedback.classList.toggle('posts-load-error', !!error);
}

function scheduledReadinessBadge(post) {
  const state = post.queue_readiness;
  if (!state?.blocked_reason) return '';
  const title = state.blocked_code?.startsWith('token_') ? 'Cần kiểm tra Token' : 'Chưa thể đăng';
  const action = state.action === 'tokens'
    ? '<button type="button" class="btn btn-outline btn-sm" onclick="switchTab(\'pane-tokens\')">Mở Token</button>'
    : '';
  return `<div class="posts-blocked"><b>${title}</b><div>${escapeHtml(state.blocked_reason)}</div>${action}</div>`;
}

function patchPostRow(current, replacement) {
  for (let index = 0; index < replacement.cells.length; index++) {
    const cell = current.cells[index];
    const updated = replacement.cells[index];
    if (!cell || cell.innerHTML === updated.innerHTML) continue;
    const opened = [...cell.querySelectorAll('details')].map(details => details.open);
    cell.innerHTML = updated.innerHTML;
    [...cell.querySelectorAll('details')].forEach((details, number) => {
      if (opened[number]) details.open = true;
    });
  }
}

function supersededPostBadge(post) {
  const replacement = post.replacement_post;
  const label = post.video_recovery_stock_claim ? 'Clip kho đã dùng cho bài khác' : 'Bài cũ đã được thay thế';
  if (!replacement) return `<span>${label}</span><div>Chưa đọc được bài thay thế; bấm Làm mới.</div>`;
  const statuses = {published: 'Đã đăng', success: 'Đã đăng', scheduled: 'App giữ lịch', preparing: 'Đang chuẩn bị',
    processing: 'Meta đang xử lý', meta_scheduled: 'Meta giữ lịch', failed: 'Cần xử lý lỗi'};
  return `<div class="posts-blocked"><b>${label}</b><div>${escapeHtml(replacement.page_name || '')}</div>`
    + `<div>Bài thay thế: ${escapeHtml(statuses[replacement.status] || replacement.status || '')}</div>`
    + `<button class="btn btn-outline btn-sm" data-replacement-post="${escapeHtml(replacement.id)}">`
    + 'Xem bài thay thế</button></div>';
}

document.addEventListener('click', event => {
  const button = event.target.closest('[data-replacement-post]');
  if (button) openMetaDiagnosis(button.dataset.replacementPost);
});

function mediaQualityBadge(post) {
  if (!post.media_quality_error) return '';
  return '<div class="posts-blocked"><b>Video cần sửa</b>'
    + `<div>${escapeHtml(post.media_quality_error)}</div></div>`;
}

function tokenIdentityLabel(token) {
  if (token.identity_verified) return 'Meta đã xác minh';
  return token.owner_name ? 'Tên Meta đã biết · cần xác minh lại' : 'Chưa xác minh tên với Meta';
}
