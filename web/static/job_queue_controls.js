/* Bounded Jobs rendering and durable render preferences. */
(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const esc = value => String(value == null ? '' : value).replace(/[&<>"']/g,
    c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const jobs = {
    page: 1, pages: 1, serial: 0, request: null, searching: null,
    reset() { this.page = 1; return this.load(); },
    search() { clearTimeout(this.searching); this.searching = setTimeout(() => this.reset(), 300); },
    turn(delta) { this.page = Math.max(1, Math.min(this.pages, this.page + delta)); return this.load(); },
    async load(automatic = false) {
      if (!el('jobs-table-body') || (automatic && this.request)) return;
      if (this.request) this.request.abort();
      const controller = new AbortController();
      this.request = controller;
      const serial = ++this.serial;
      const params = new URLSearchParams({page: this.page,
        page_size: el('jobs-page-size').value,
        status: el('jobs-status-filter').value, q: el('jobs-search').value.trim()});
      try {
        const response = await fetch('/api/jobs?' + params, {signal: controller.signal});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Không tải được Jobs');
        if (serial !== this.serial) return;
        this.page = data.page; this.pages = data.pages;
        const counts = data.counts;
        el('topbar-jobs-count').textContent = data.total;
        el('failed-jobs-count').textContent = counts.error;
        el('btn-retry-failed').style.display = counts.error ? 'inline-block' : 'none';
        el('jobs-counts').textContent = 'Lỗi: ' + counts.error + ' · Đang chờ: ' +
          counts.queued + ' · Đang chạy: ' + counts.running + ' · Hoàn tất: ' + counts.completed;
        const labels = {all:'Tất cả', error:'Lỗi (error)', queued:'Đang chờ (queued)',
          running:'Đang chạy (running)', completed:'Hoàn tất (completed)'};
        Object.entries(labels).forEach(([key, label]) => {
          el('jobs-status-filter').querySelector('option[value="' + key + '"]').textContent =
            label + ' (' + (key === 'all' ? data.total : counts[key]) + ')';
        });
        el('jobs-page-summary').textContent = 'Trang ' + data.page + ' / ' + data.pages +
          ' · ' + data.filtered_total + ' Jobs phù hợp / ' + data.total + ' tổng';
        el('jobs-prev').disabled = data.page <= 1;
        el('jobs-next').disabled = data.page >= data.pages;
        el('jobs-load-error').textContent = '';
        const badges = {running:'badge-running', transcribing:'badge-transcribing',
          cutting:'badge-cutting', completed:'badge-done', error:'badge-error'};
        const html = data.items.map(j => {
          const state = j.status || 'queued';
          const message = state === 'error' ? (j.error || j.progress_msg) :
            (['running','transcribing','cutting'].includes(state) ? j.progress_msg : '');
          const button = (action, icon, title) => '<button class="btn btn-secondary btn-sm" data-job-action="' +
            action + '" data-job-id="' + esc(j.id) + '" title="' + title +
            '"><i class="bi bi-' + icon + '"></i></button>';
          return '<tr><td><code style="color:#f472b6;" title="' + esc(j.id) + '">' + esc(j.id) +
            '</code></td><td><div style="font-weight:700;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
            esc(j.video_title || j.youtube_url) + '</div><div style="font-size:11px;color:var(--text-dim);">' +
            (j.duration ? Math.round(j.duration) + 's' : 'Đang tải...') + '</div></td><td>' +
            esc(j.aspect_ratio || '9:16') + '<br>' + esc(j.reframe_mode || 'Face Center') +
            '</td><td><strong>' + j.clip_count + '</strong> / ' + (j.num_clips || 3) +
            '</td><td><span class="badge ' + (badges[state] || 'badge-queued') + '">' + esc(state.toUpperCase()) +
            '</span><div title="' + esc(message) + '" style="max-width:260px;font-size:11px;color:' +
            (state === 'error' ? '#f87171' : 'var(--text-muted)') +
            ';display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">' +
            esc(message) + '</div></td><td style="font-size:11px;">' + esc(j.created_at) +
            '</td><td style="text-align:right;white-space:nowrap;">' + button('detail','eye','Xem chi tiết job') +
            (state === 'error' ? button('retry','arrow-repeat','Chạy lại job này') : '') +
            button('delete','trash','Xóa job') + '</td></tr>';
        }).join('') || '<tr><td colspan="7" style="text-align:center;padding:24px;">Không có Jobs phù hợp.</td></tr>';
        if (el('jobs-table-body').innerHTML !== html) el('jobs-table-body').innerHTML = html;
      } catch (error) {
        if (error.name !== 'AbortError' && serial === this.serial)
          el('jobs-load-error').textContent = error.message + '. Bấm Làm mới để thử lại.';
      } finally {
        if (serial === this.serial) this.request = null;
      }
    }
  };
  window.highlightJobs = jobs;

  const render = {
    dirty: false, saving: false, request: null, revision: 0,
    edit(dirty = false) {
      if (dirty) { this.dirty = true; this.revision++; }
      const manual = el('queue-concurrency-mode').value === 'manual';
      el('queue-concurrency-manual').disabled = !manual || this.saving;
      if (!this.saving) el('queue-concurrency-help').textContent = this.dirty ?
        'Chưa lưu — bấm Áp dụng để giữ lựa chọn này sau khi mở lại app.' :
        (manual ? 'Đã lưu số luồng thủ công. Giảm mức áp dụng cho job mới.' : 'Auto dùng cấu hình phần cứng đã kiểm tra.');
    },
    sync(data) {
      if (this.dirty || this.saving) return;
      el('queue-concurrency-mode').value = data.concurrency_mode || data.mode || 'auto';
      el('queue-concurrency-manual').value = data.max_concurrent || data.concurrency || 1;
      this.edit();
    },
    async refresh() {
      if (this.request) return this.request;
      const revision = this.revision;
      this.request = (async () => {
        try {
          const response = await fetch('/api/queue/status');
          if (!response.ok) return;
          const data = await response.json();
          el('q-stat-queued').textContent = data.queued;
          el('q-stat-running').textContent = data.running;
          el('q-stat-completed').textContent = data.completed;
          el('topbar-jobs-count').textContent = data.total;
          el('q-stat-running').parentElement.innerHTML = 'Đang render: <strong id="q-stat-running">' +
            data.running + '</strong> / ' + data.max_concurrent;
          if (revision === this.revision) this.sync(data);
          const pause = el('btn-queue-pause');
          pause.innerHTML = data.is_paused ? '<i class="bi bi-play-fill"></i> Tiếp tục chạy' :
            '<i class="bi bi-pause-fill"></i> Tạm dừng';
          pause.className = data.is_paused ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
          el('queue-status-dot').className = data.is_paused ? 'status-dot err' :
            (data.running ? 'status-dot ok' : 'status-dot');
        } catch (error) { console.warn('Queue status:', error.message); }
        finally { this.request = null; }
      })();
      return this.request;
    },
    async save() {
      if (this.saving) return;
      const mode = el('queue-concurrency-mode').value;
      const manual = Number(el('queue-concurrency-manual').value);
      if (mode === 'manual' && (!Number.isInteger(manual) || manual < 1 || manual > 4)) {
        el('queue-concurrency-help').textContent = 'Chọn số nguyên từ 1 đến 4.';
        return;
      }
      this.saving = true; this.revision++;
      el('queue-concurrency-save').disabled = true;
      el('queue-concurrency-mode').disabled = true;
      el('queue-concurrency-manual').disabled = true;
      el('queue-concurrency-help').textContent = 'Đang lưu...';
      try {
        const response = await fetch(el('queue-concurrency-controls').dataset.endpoint, {method:'POST',
          headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode, manual_concurrency:manual})});
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'Không lưu được số luồng');
        this.dirty = false; this.saving = false;
        this.sync(data);
        el('queue-concurrency-help').textContent = 'Đã lưu: ' + data.concurrency +
          ' luồng (' + (data.mode === 'manual' ? 'thủ công' : 'Auto') + ').';
      } catch (error) {
        this.dirty = true;
        el('queue-concurrency-help').textContent = error.message + ' — lựa chọn chưa được lưu.';
      } finally {
        this.saving = false;
        el('queue-concurrency-save').disabled = false;
        el('queue-concurrency-mode').disabled = false;
        el('queue-concurrency-manual').disabled = el('queue-concurrency-mode').value !== 'manual';
      }
    }
  };
  window.highlightRenderQueue = render;
  el('jobs-table-body').addEventListener('click', event => {
    const button = event.target.closest('[data-job-action]');
    if (!button) return;
    const id = button.dataset.jobId;
    if (button.dataset.jobAction === 'detail') window.showJobDetail(id);
    if (button.dataset.jobAction === 'retry') window.retrySingleJob(id);
    if (button.dataset.jobAction === 'delete') window.deleteJob(id);
  });
  render.refresh();
  setInterval(() => {
    if (document.hidden) return;
    render.refresh();
    if (el('pane-jobs').classList.contains('active') && !document.querySelector('.app-modal-overlay.active'))
      jobs.load(true);
  }, 5000);
})();
