let schedulerStatusRequest = null;

async function refreshSchedulerView() {
  if (schedulerStatusRequest) return schedulerStatusRequest;
  schedulerStatusRequest = readSchedulerView();
  try {
    await schedulerStatusRequest;
  } finally {
    schedulerStatusRequest = null;
  }
}

async function readSchedulerView() {
  const status = document.getElementById('scheduler-status-text');
  const banner = document.getElementById('scheduler-overdue-banner');
  if (!status) return;
  try {
    const response = await fetch('/api/scheduler/status');
    const state = await response.json();
    if (!response.ok || state.success === false) throw new Error(state.error || 'Không đọc được worker');
    schedulerCycleActive = !!state.cycle_active;
    postsOverdue.clear();
    for (const post of state.overdue_posts || []) {
      if (post.status === 'scheduled') postsOverdue.set(post.id, Math.max(0, Math.round(post.late_seconds / 60)));
    }
    const alive = state.thread_alive && state.last_cycle_ok !== false;
    const label = state.waiting_for_lease ? 'Đang chờ worker' : (alive ? 'Hoạt động' : 'Cần kiểm tra');
    status.textContent = `${label} · chu kỳ cuối ${state.last_cycle_at?.slice(11, 19) || '--:--:--'}`;
    status.style.color = alive ? '#10b981' : '#fbbf24';
    if (!banner) return;
    const blocked = (state.overdue_posts || []).filter(post => post.blocked_reason);
    const ready = Number(state.actionable_count ?? state.overdue_count ?? 0);
    const messages = [];
    if (blocked.length) {
      messages.push(`<b>${state.blocked_count || blocked.length} bài cần xử lý</b>: `
        + escapeHtml(blocked[0].blocked_reason));
      if (blocked.some(post => post.action === 'tokens')) {
        messages.push('<button class="btn btn-outline btn-sm" onclick="switchTab(\'pane-tokens\')">Mở Token</button>');
      }
    }
    if (ready) {
      messages.push(`<b>${ready} bài đến hạn</b> · `
        + (schedulerCycleActive ? 'worker đang xử lý.' : 'sẵn sàng chạy.'));
      messages.push('<button class="btn btn-outline btn-sm" onclick="runDuePostsNow()">Chạy bài đến hạn</button>');
    }
    if (state.last_error) messages.push(escapeHtml(state.last_error));
    banner.innerHTML = messages.join(' ');
    banner.style.display = messages.length ? 'block' : 'none';
  } catch (error) {
    status.textContent = 'Không đọc được worker: ' + error.message;
    status.style.color = '#ef4444';
  }
}

async function requestDuePosts() {
  const button = document.getElementById('run-due-btn');
  if (button) button.disabled = true;
  try {
    const response = await fetch('/api/scheduler/run-due', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({background: true})
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'Chưa chạy được bài đến hạn');
    showToast(result.message || 'Đã nhận yêu cầu chạy bài đến hạn.', 'info');
  } catch (error) {
    showToast(error.message, 'error');
    const banner = document.getElementById('scheduler-overdue-banner');
    banner.textContent = error.message;
    banner.style.display = 'block';
  } finally {
    if (button) button.disabled = false;
    refreshSchedulerStatus();
    loadPostsTable({quiet: true});
  }
}
