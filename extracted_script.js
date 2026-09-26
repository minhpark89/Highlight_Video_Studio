
/* --- SCRIPT 0 --- */

  // Global robust tab switcher
  window.switchTab = function(paneId, btnEl) {
    try {
      console.log('[Tab] Switching to:', paneId);
      // Remove active from all nav-btn
      var btns = document.querySelectorAll('.nav-btn');
      for (var i = 0; i < btns.length; i++) {
        btns[i].classList.remove('active');
      }
      // Remove active from all panes & force display
      var panes = document.querySelectorAll('.pane');
      for (var j = 0; j < panes.length; j++) {
        panes[j].classList.remove('active');
        panes[j].style.setProperty('display', 'none', 'important');
      }

      // Activate clicked button or matching button
      if (btnEl) {
        btnEl.classList.add('active');
      } else {
        var mBtn = document.querySelector('.nav-btn[data-pane="' + paneId + '"]');
        if (mBtn) mBtn.classList.add('active');
      }

      // Activate target pane & force display block
      var target = document.getElementById(paneId);
      if (target) {
        target.classList.add('active');
        target.style.setProperty('display', 'block', 'important');
      }

      // Safely call tab lazy loaders
      try {
        if (paneId === 'pane-jobs' && typeof loadJobsTable === 'function') loadJobsTable();
      } catch (e) { console.warn(e); }
      try {
        if (paneId === 'pane-research' && typeof loadSavedResearchVideos === 'function') loadSavedResearchVideos();
      } catch (e) { console.warn(e); }
      try {
        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
      } catch (e) { console.warn(e); }
      try {
        if (paneId === 'pane-pages') { if (typeof loadTokensAndPages === 'function') loadTokensAndPages(); if (typeof loadScheduleRulesConfig === 'function') loadScheduleRulesConfig();
      loadTokensAndPages(); }
        if (paneId === 'pane-schedule' && typeof loadScheduleRulesConfig === 'function') loadScheduleRulesConfig();
      loadTokensAndPages();
      } catch (e) { console.warn(e); }
      try {
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();
      } catch (e) { console.warn(e); }
    } catch (err) {
      console.error('[switchTab error]', err);
    }
  };

  // Navigation tabs
  document.querySelectorAll('.nav-btn[data-pane]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const targetPane = document.getElementById(btn.getAttribute('data-pane'));
      if (targetPane) targetPane.classList.add('active');
      if (btn.getAttribute('data-pane') === 'pane-jobs') loadJobsTable();
      if (btn.getAttribute('data-pane') === 'pane-research') loadSavedResearchVideos();
      
        if (btn.getAttribute('data-pane') === 'pane-gallery') loadClipsGallery();
        if (btn.getAttribute('data-pane') === 'pane-pages') loadTokensAndPages();
        if (btn.getAttribute('data-pane') === 'pane-website') loadWebsiteConfig();
    });
  });
  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (text) document.getElementById('youtube_url').value = text;
    } catch (e) {
      alert('Vui lòng dán thủ công bằng Ctrl+V!');
    }
  }
  function resetJobForm() {
    document.getElementById('createJobForm').reset();
  }
  // Create Job submission
  document.getElementById('createJobForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitJob');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Đang khởi tạo job...';
    let hookDur = document.getElementById('hook_duration').value;
    if (hookDur === 'custom') {
      hookDur = parseInt(document.getElementById('custom_hook_val').value) || 6;
    } else {
      hookDur = parseInt(hookDur) || 6;
    }
    const payload = {
      youtube_url: document.getElementById('youtube_url').value.trim(),
      hook_duration: hookDur,
      clip_length: document.getElementById('clip_length').value,
      num_clips: parseInt(document.getElementById('num_clips').value),
      aspect_ratio: document.getElementById('aspect_ratio').value,
      reframe_mode: document.getElementById('reframe_mode').value,
      subtitle_style: document.getElementById('subtitle_style').value,
      highlight_criteria: document.getElementById('highlight_criteria').value
    };
    try {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        if (data.count && data.count > 1) {
          alert(`Đã khởi tạo thành công ${data.count} Jobs chạy song song đa luồng!`);
          pollJobProgress(data.job_ids[0]);
        } else {
          alert('Đã khởi tạo Job thành công: ' + data.job_id);
          pollJobProgress(data.job_id);
        }
        loadJobsTable();
      } else {
        alert('Lỗi: ' + (data.error || 'Không thể tạo job'));
      }
    } catch (err) {
      alert('Lỗi kết nối tới server: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-play-circle-fill"></i> <span>Bắt đầu trích xuất Highlight</span>';
    }
  });
  let pollInterval = null;
  function pollJobProgress(jobId) {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
      try {
        const res = await fetch('/api/jobs/' + jobId);
        if (!res.ok) return;
        const job = await res.json();
        // Update UI step visualizer
        updatePipelineSteps(job.step || 1, job.status);
        document.getElementById('current-job-title').textContent = job.video_title || job.youtube_url;
        document.getElementById('current-job-progress').textContent = `[${job.status.toUpperCase()}] ${job.progress_msg || ''}`;
        if (job.status === 'completed' || job.status === 'error') {
          clearInterval(pollInterval);
          loadJobsTable();
          loadClipsGallery();
          if (job.status === 'error') {
            showJobErrorPopup(job);
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 2500);
  }
  function updatePipelineSteps(currentStep, status) {
    for (let i = 1; i <= 5; i++) {
      const el = document.getElementById('step-' + i);
      const icon = el.querySelector('.step-status');
      if (status === 'completed') {
        el.className = 'pipeline-step-item done';
        icon.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
      } else if (status === 'error' && i === currentStep) {
        el.className = 'pipeline-step-item error';
        icon.innerHTML = '<i class="bi bi-x-circle-fill text-danger"></i>';
      } else if (i < currentStep) {
        el.className = 'pipeline-step-item done';
        icon.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
      } else if (i === currentStep) {
        el.className = 'pipeline-step-item active';
        icon.innerHTML = '<i class="bi bi-arrow-repeat text-warning spin"></i>';
      } else {
        el.className = 'pipeline-step-item';
        icon.innerHTML = '<i class="bi bi-dash-circle text-muted"></i>';
      }
    }
  }
  async function loadJobsTable() {
    try {
      const res = await fetch('/api/jobs');
      const jobs = await res.json();
      document.getElementById('topbar-jobs-count').textContent = jobs.length;
      const failedCount = jobs.filter(j => j.status === 'error').length;
      const retryBtn = document.getElementById('btn-retry-failed');
      const failedBadge = document.getElementById('failed-jobs-count');
      if (retryBtn && failedBadge) {
        failedBadge.textContent = failedCount;
        retryBtn.style.display = failedCount > 0 ? 'inline-block' : 'none';
      }
      const tbody = document.getElementById('jobs-table-body');
      if (!jobs || jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Chưa có job nào trong hệ thống.</td></tr>';
        return;
      }
      tbody.innerHTML = jobs.map(j => {
        let badgeClass = 'badge-queued';
        if (j.status === 'running') badgeClass = 'badge-running';
        if (j.status === 'transcribing') badgeClass = 'badge-transcribing';
        if (j.status === 'cutting') badgeClass = 'badge-cutting';
        if (j.status === 'completed') badgeClass = 'badge-done';
        if (j.status === 'error') badgeClass = 'badge-error';
        return `
          <tr>
            <td><code style="color: #f472b6;">${j.id.substring(0, 8)}</code></td>
            <td>
              <div style="font-weight: 700; max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                ${j.video_title || j.youtube_url}
              </div>
              <div style="font-size: 11px; color: var(--text-dim);">${j.duration ? Math.round(j.duration) + 's' : 'Đang tải...'}</div>
            </td>
            <td>
              <span class="badge" style="background: #1e293b;">${j.aspect_ratio || '9:16'}</span>
              <span class="badge" style="background: #1e293b;">${j.reframe_mode || 'Face Center'}</span>
            </td>
            <td><strong>${j.clips ? j.clips.length : 0}</strong> / ${j.num_clips || 3}</td>
            <td><span class="badge ${badgeClass}">${j.status.toUpperCase()}</span></td>
            <td style="font-size: 11.5px; color: var(--text-muted);">${j.created_at || ''}</td>
            <td style="text-align: right;">
              <button class="btn btn-secondary btn-sm" onclick="showJobDetail('${j.id}')" title="Xem chi tiết job"><i class="bi bi-eye"></i></button>
              ${j.status === 'error' ? `<button class="btn btn-warning btn-sm me-1" onclick="retrySingleJob('${j.id}')" title="Chạy lại job này"><i class="bi bi-arrow-repeat"></i></button>` : ''}<button class="btn btn-secondary btn-sm text-danger" onclick="deleteJob('${j.id}')"><i class="bi bi-trash"></i></button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
    }
  }
  async function loadClipsGallery() {
    try {
      const res = await fetch('/api/clips');
      const clips = await res.json();
      const container = document.getElementById('clips-gallery-container');
      if (!clips || clips.length === 0) {
        container.innerHTML = `
          <div class="col-12" style="text-align: center; color: var(--text-dim); padding: 40px;">
            <i class="bi bi-film" style="font-size: 3rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
            Chưa có clip highlight nào được render hoàn thành. Hãy tạo job mới ở tab "Cắt Highlight"!
          </div>`;
        return;
      }
      container.innerHTML = clips.map(c => `
        <div class="col-4">
          <div class="clip-card">
            <video class="clip-video-preview" controls preload="metadata">
              <source src="/api/clips/play/${encodeURIComponent(c.filename)}" type="video/mp4">
            </video>
            <div class="clip-body">
              <div class="clip-title">${c.hook_title || c.filename}</div>
              <div style="font-size: 11.5px; color: var(--text-dim); margin-bottom: 6px;">
                ${c.summary || 'AI Highlight Clip'}
              </div>
              <div class="clip-meta">
                <span class="badge" style="background: rgba(236, 72, 153, 0.2); color: #f472b6;">
                  ⭐ Viral: ${c.viral_score || 95}/100
                </span>
                <span style="font-size: 11px; color: var(--text-muted);">
                  ${c.duration ? Math.round(c.duration) + 's' : ''}
                </span>
                <a href="/api/clips/play/${encodeURIComponent(c.filename)}" download class="btn btn-primary btn-sm">
                  <i class="bi bi-download"></i> Tải về
                </a>
              </div>
            </div>
          </div>
        </div>
      `).join('');
    } catch (e) {
      console.error(e);
    }
  }
  async function deleteJob(id) {
    if (!confirm('Xóa job này?')) return;
    await fetch('/api/jobs/' + id, { method: 'DELETE' });
    loadJobsTable();
  }
  // Initial load
  loadJobsTable();
  loadClipsGallery();
  
  // ================= RESEARCH VIDEO PERSISTENCE & HISTORY =================
  function renderResearchCards(results) {
    const container = document.getElementById('research-results-container');
    if (!container) return;
    container.innerHTML = results.map((v, idx) => {
      const isTop = idx < 3;
      const topBadge = isTop ? `<span class="badge" style="background: linear-gradient(135deg, #ef4444, #f59e0b); color: #fff; font-weight: 700; position: absolute; top: 10px; left: 10px; z-index: 2; box-shadow: 0 2px 8px rgba(0,0,0,0.5);"><i class="bi bi-fire"></i> TOP ${idx + 1} VIRAL</span>` : '';
      return `
        <div class="col-4" style="margin-bottom: 20px;">
          <div class="clip-card" style="height: 100%; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; position: relative;">
            ${topBadge}
            <!-- Multi-select Checkbox -->
            <div style="position: absolute; top: 10px; right: 10px; z-index: 3; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 4px 6px; display: flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
              <input type="checkbox" class="video-select-check" data-url="${v.url}" data-title="${escapeHtml(v.title)}" onchange="updateSelectedCount()" style="width: 17px; height: 17px; accent-color: #ec4899; cursor: pointer;">
              <span style="font-size: 11px; font-weight: 700; color: #fff; user-select: none;">Chọn</span>
            </div>
            <div style="position: relative; width: 100%; aspect-ratio: 16/9; background: #000; overflow: hidden;">
              <img src="${v.thumbnail || ''}" alt="${escapeHtml(v.title)}" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
              <span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                ${v.duration_str || 'N/A'}
              </span>
              <span style="position: absolute; bottom: 8px; left: 8px; background: rgba(15, 23, 42, 0.85); color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.3);">
                <i class="bi bi-eye-fill"></i> ${v.view_count_str || 'N/A'}
              </span>
            </div>
            <div style="padding: 14px; display: flex; flex-direction: column; flex: 1; justify-content: space-between;">
              <div>
                <div style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 38px;" title="${escapeHtml(v.title)}">
                  ${escapeHtml(v.title)}
                </div>
                <div style="font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-bottom: 12px;">
                  <i class="bi bi-person-circle" style="color: var(--accent);"></i>
                  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(v.uploader || 'YouTube Creator')}</span>
                </div>
              </div>
              <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 12px;">
                <button class="btn btn-primary" style="width: 100%; font-weight: 700; justify-content: center; font-size: 12.5px; background: linear-gradient(135deg, #3b82f6, #6366f1); border: none;" onclick="copyVideoUrl('${v.url}', this)">
                  <i class="bi bi-clipboard-check"></i> <span>Sao chép Link YouTube</span>
                </button>
                <div style="display: flex; gap: 8px;">
                  <button class="btn btn-secondary btn-sm" style="flex: 1; justify-content: center; font-size: 11.5px; color: #a855f7; border-color: rgba(168, 85, 247, 0.3);" onclick="sendToRender('${v.url}')" title="Tự động chuyển tab và dán link vào ô render">
                    <i class="bi bi-lightning-charge"></i> Ném vào Render
                  </button>
                  <button class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 0 10px; justify-content: center; background: #1e293b; border-color: #38bdf8; color: #38bdf8;" onclick="openVideoPlayerModal('${v.url}', '${escapeHtml(v.title)}', '${v.id}')" title="Xem video trực tiếp trên web">
                    <i class="bi bi-play-circle-fill"></i> <span style="margin-left: 4px;">Xem trực tiếp</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderResearchResults(results) {
    const container = document.getElementById('research-results-container');
    const titleEl = document.getElementById('research-results-title');
    const batchBar = document.getElementById('research-batch-bar');

    if (!results || results.length === 0) {
      if (titleEl) titleEl.textContent = 'Danh sách video cào được (0)';
      if (batchBar) batchBar.style.display = 'none';
      if (container) {
        container.innerHTML = `
          <div class="col-12" style="text-align: center; color: var(--text-dim); padding: 50px 20px;">
            <i class="bi bi-binoculars" style="font-size: 3.2rem; opacity: 0.3; display: block; margin-bottom: 12px;"></i>
            <div style="font-size: 14px; font-weight: 600;">Chưa có kết quả research nào</div>
            <div style="font-size: 12px; margin-top: 4px;">Nhập từ khóa, link kênh hoặc chọn chủ đề gợi ý phía trên rồi bấm "Cào Link"!</div>
          </div>
        `;
      }
      return;
    }

    if (titleEl) titleEl.textContent = `Danh sách video viral cào được (${results.length})`;
    if (batchBar) batchBar.style.display = 'flex';
    const checkAll = document.getElementById('check-all-videos');
    if (checkAll) checkAll.checked = false;
    updateSelectedCount();

    renderResearchCards(results);
  }

  async function loadSavedResearchVideos() {
    try {
      const res = await fetch('/api/research/saved');
      const data = await res.json();
      if (data && data.success && Array.isArray(data.results) && data.results.length > 0) {
        renderResearchResults(data.results);
      }
    } catch (e) {
      console.warn('Lỗi tải lịch sử cào:', e);
    }
  }

  async function clearResearchHistory() {
    if (!confirm('Bạn có chắc muốn xóa sạch toàn bộ lịch sử cào video?')) return;
    try {
      await fetch('/api/research/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'clear_all' })
      });
      renderResearchResults([]);
      showToast('Đã xóa sạch lịch sử cào link!');
    } catch (e) {
      alert('Lỗi: ' + e.message);
    }
  }

  

  // ================= JOB RETRY FUNCTIONS =================
  async function retryFailedJobs() {
    const btn = document.getElementById('btn-retry-failed');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang chạy lại...';
    }
    try {
      const res = await fetch('/api/jobs/retry_failed', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Đã đưa ${data.retried || 0} job lỗi vào lại hàng đợi xử lý!`);
        loadJobsTable();
      } else {
        alert('Lỗi chạy lại jobs: ' + (data.error || 'Không xác định'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function retrySingleJob(jobId) {
    if (!confirm(`Chạy lại job [${jobId.substring(0, 8)}]?`)) return;
    try {
      const res = await fetch(`/api/jobs/${jobId}/retry`, { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Đã đưa job ${jobId.substring(0, 8)} vào lại hàng đợi!`);
        loadJobsTable();
      } else {
        alert('Lỗi chạy lại job: ' + (data.error || 'Không xác định'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }
// ================= RESEARCH NGUỒN LINK VIRAL =================
  function fillResearchQuery(q) {
    document.getElementById('research_query').value = q;
    performResearch();
  }
  async function performResearch() {
    const query = document.getElementById('research_query').value.trim();
    if (!query) {
      alert('Vui lòng nhập từ khóa hoặc link kênh/playlist YouTube!');
      document.getElementById('research_query').focus();
      return;
    }
    const platform = document.getElementById('research_platform').value;
    const filterType = document.getElementById('research_filter').value;
    const btnSubmit = document.getElementById('btn-research-submit');
    const loading = document.getElementById('research-loading');
    const container = document.getElementById('research-results-container');
    const titleEl = document.getElementById('research-results-title');
    btnSubmit.disabled = true;
    loading.style.display = 'inline-flex';
    container.innerHTML = `
      <div class="col-12" style="text-align: center; color: var(--text-dim); padding: 50px 20px;">
        <span class="spinner-border text-primary" style="width: 3rem; height: 3rem; margin-bottom: 16px;"></span>
        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">Đang quét & lọc video nhiều view, đang viral từ YouTube...</div>
        <div style="font-size: 12px; margin-top: 6px; color: var(--text-muted);">Sắp xếp theo số lượt xem cao nhất để lấy nguồn chất lượng</div>
      </div>
    `;
    try {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          platform: platform,
          filter_type: filterType,
          max_results: parseInt(document.getElementById('research_max_results') ? document.getElementById('research_max_results').value : 50) || 50
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Lỗi khi cào link');
      }
      const results = data.results || [];
      titleEl.textContent = `Danh sách video viral cào được (${results.length})`;
      if (results.length === 0) {
        container.innerHTML = `
          <div class="col-12" style="text-align: center; color: var(--text-dim); padding: 40px;">
            <i class="bi bi-exclamation-circle" style="font-size: 3rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
            Không tìm thấy video nào phù hợp với từ khóa này. Hãy thử từ khóa khác!
          </div>
        `;
        return;
      }
      // Show batch bar
      const batchBar = document.getElementById('research-batch-bar');
      if (batchBar) batchBar.style.display = 'flex';
      const checkAll = document.getElementById('check-all-videos');
      if (checkAll) checkAll.checked = false;
      updateSelectedCount();
      container.innerHTML = results.map((v, idx) => {
        const isTop = idx < 3;
        const topBadge = isTop ? `<span class="badge" style="background: linear-gradient(135deg, #ef4444, #f59e0b); color: #fff; font-weight: 700; position: absolute; top: 10px; left: 10px; z-index: 2; box-shadow: 0 2px 8px rgba(0,0,0,0.5);"><i class="bi bi-fire"></i> TOP ${idx + 1} VIRAL</span>` : '';
        return `
          <div class="col-4" style="margin-bottom: 20px;">
            <div class="clip-card" style="height: 100%; display: flex; flex-direction: column; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; position: relative;">
              ${topBadge}
              <!-- Multi-select Checkbox -->
              <div style="position: absolute; top: 10px; right: 10px; z-index: 3; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; padding: 4px 6px; display: flex; align-items: center; gap: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.5);">
                <input type="checkbox" class="video-select-check" data-url="${v.url}" data-title="${escapeHtml(v.title)}" onchange="updateSelectedCount()" style="width: 17px; height: 17px; accent-color: #ec4899; cursor: pointer;">
                <span style="font-size: 11px; font-weight: 700; color: #fff; user-select: none;">Chọn</span>
              </div>
              <div style="position: relative; width: 100%; aspect-ratio: 16/9; background: #000; overflow: hidden;">
                <img src="${v.thumbnail || ''}" alt="${escapeHtml(v.title)}" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                <span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: 600;">
                  ${v.duration_str || 'N/A'}
                </span>
                <span style="position: absolute; bottom: 8px; left: 8px; background: rgba(15, 23, 42, 0.85); color: #38bdf8; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.3);">
                  <i class="bi bi-eye-fill"></i> ${v.view_count_str || 'N/A'}
                </span>
              </div>
              <div style="padding: 14px; display: flex; flex-direction: column; flex: 1; justify-content: space-between;">
                <div>
                  <div style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); line-height: 1.4; margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 38px;" title="${escapeHtml(v.title)}">
                    ${escapeHtml(v.title)}
                  </div>
                  <div style="font-size: 12px; color: var(--text-muted); display: flex; align-items: center; gap: 6px; margin-bottom: 12px;">
                    <i class="bi bi-person-circle" style="color: var(--accent);"></i>
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(v.uploader || 'YouTube Creator')}</span>
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 12px;">
                  <!-- LỰA CHỌN 1 (CHÍNH): SAO CHÉP LINK ĐỂ TỰ NÉM VÀO PHẦN CẮT -->
                  <button class="btn btn-primary" style="width: 100%; font-weight: 700; justify-content: center; font-size: 12.5px; background: linear-gradient(135deg, #3b82f6, #6366f1); border: none;" onclick="copyVideoUrl('${v.url}', this)">
                    <i class="bi bi-clipboard-check"></i> <span>Sao chép Link YouTube</span>
                  </button>
                  <div style="display: flex; gap: 8px;">
                    <!-- LỰA CHỌN 2 (PHỤ): 1-CLICK TỰ NÉM VÀO RENDER -->
                    <button class="btn btn-secondary btn-sm" style="flex: 1; justify-content: center; font-size: 11.5px; color: #a855f7; border-color: rgba(168, 85, 247, 0.3);" onclick="sendToRender('${v.url}')" title="Lựa chọn 2: Tự động chuyển tab và dán link vào ô render">
                      <i class="bi bi-lightning-charge"></i> Ném vào Render
                    </button>
                    <!-- XEM GỐC TRÊN YOUTUBE -->
                                          <!-- XEM TRỰC TIẾP TRÊN WEB HOẶC MỞ TAB -->
                      <button class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 0 10px; justify-content: center; background: #1e293b; border-color: #38bdf8; color: #38bdf8;" onclick="openVideoPlayerModal('${v.url}', '${escapeHtml(v.title)}', '${v.id}')" title="Xem video trực tiếp trên web">
                        <i class="bi bi-play-circle-fill"></i> <span style="margin-left: 4px;">Xem trực tiếp</span>
                      </button>
                      
                  </div>
                </div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `
        <div class="col-12" style="text-align: center; color: #f87171; padding: 40px;">
          <i class="bi bi-exclamation-triangle" style="font-size: 3rem; display: block; margin-bottom: 10px;"></i>
          Đã xảy ra lỗi: ${escapeHtml(err.message)}
        </div>
      `;
    } finally {
      btnSubmit.disabled = false;
      loading.style.display = 'none';
    }
  }
  function copyVideoUrl(url, btn) {
    navigator.clipboard.writeText(url).then(() => {
      const originalText = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check2-circle"></i> <span style="color: #4ade80;">Đã sao chép!</span>';
      btn.style.background = '#1e293b';
      showToast('Đã sao chép link YouTube! Bạn có thể dán (Ctrl+V) vào tab "Cắt Highlight".');
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.style.background = 'linear-gradient(135deg, #3b82f6, #6366f1)';
      }, 2000);
    }).catch(() => {
      prompt('Sao chép link này:', url);
    });
  }
  function sendToRender(url) {
    // Chuyển sang tab Cắt Highlight
    const studioBtn = document.querySelector('.nav-btn[data-pane="pane-studio"]');
    if (studioBtn) studioBtn.click();
    // Điền URL
    const urlInput = document.getElementById('youtube_url');
    if (urlInput) {
      urlInput.value = url;
      urlInput.focus();
      urlInput.style.transition = 'box-shadow 0.3s, border-color 0.3s';
      urlInput.style.borderColor = '#8b5cf6';
      urlInput.style.boxShadow = '0 0 15px rgba(139, 92, 246, 0.5)';
      setTimeout(() => {
        urlInput.style.borderColor = '';
        urlInput.style.boxShadow = '';
      }, 2500);
    }
    showToast('Đã điền link vào ô Cắt Highlight!');
  }
  function showToast(msg) {
    let toast = document.getElementById('saas-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'saas-toast';
      toast.style.position = 'fixed';
      toast.style.bottom = '24px';
      toast.style.right = '24px';
      toast.style.background = '#0f172a';
      toast.style.color = '#fff';
      toast.style.padding = '12px 20px';
      toast.style.borderRadius = '8px';
      toast.style.border = '1px solid #3b82f6';
      toast.style.boxShadow = '0 8px 24px rgba(0,0,0,0.4)';
      toast.style.zIndex = '9999';
      toast.style.fontSize = '13px';
      toast.style.fontWeight = '600';
      toast.style.display = 'flex';
      toast.style.alignItems = 'center';
      toast.style.gap = '8px';
      toast.style.transition = 'all 0.3s ease';
      document.body.appendChild(toast);
    }
    toast.innerHTML = `<i class="bi bi-info-circle-fill text-primary"></i> ${msg}`;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
    }, 3200);
  }
  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }
  // ================= BATCH SELECTION FOR RESEARCH =================
  function toggleSelectAllVideos(checked) {
    const checkboxes = document.querySelectorAll('.video-select-check');
    checkboxes.forEach(cb => cb.checked = checked);
    updateSelectedCount();
  }
  function updateSelectedCount() {
    const checkboxes = document.querySelectorAll('.video-select-check:checked');
    const count = checkboxes.length;
    const total = document.querySelectorAll('.video-select-check').length;
    
    const countEl = document.getElementById('selected-count');
    const copyBtnCount = document.getElementById('copy-btn-count');
    const btnCopy = document.getElementById('btn-copy-selected');
    const btnSend = document.getElementById('btn-send-selected');
    const checkAll = document.getElementById('check-all-videos');
    if (countEl) countEl.textContent = count;
    if (copyBtnCount) copyBtnCount.textContent = count;
    if (btnCopy) btnCopy.disabled = (count === 0);
    if (btnSend) btnSend.disabled = (count === 0);
    if (checkAll && total > 0) {
      checkAll.checked = (count === total);
    }
  }
  function copySelectedUrls() {
    const checkboxes = document.querySelectorAll('.video-select-check:checked');
    if (checkboxes.length === 0) {
      alert('Vui lòng tick chọn ít nhất 1 video!');
      return;
    }
    const urls = Array.from(checkboxes).map(cb => cb.getAttribute('data-url')).filter(Boolean);
    const textToCopy = urls.join('\n');
    navigator.clipboard.writeText(textToCopy).then(() => {
      showToast(`Đã sao chép thành công ${urls.length} link YouTube vào bộ nhớ tạm!`);
    }).catch(() => {
      prompt(`Sao chép ${urls.length} link dưới đây:`, textToCopy);
    });
  }
  function sendSelectedToStudio() {
    const checkboxes = document.querySelectorAll('.video-select-check:checked');
    if (checkboxes.length === 0) {
      alert('Vui lòng tick chọn ít nhất 1 video!');
      return;
    }
    const allUrls = Array.from(checkboxes).map(cb => cb.getAttribute('data-url')).filter(Boolean);
    const count = allUrls.length;
    // Switch to Studio tab
    const studioBtn = document.querySelector('.nav-btn[data-pane="pane-studio"]');
    if (studioBtn) studioBtn.click();
    const urlInput = document.getElementById('youtube_url');
    if (urlInput) {
      urlInput.value = allUrls.join('\n');
      urlInput.focus();
      urlInput.style.borderColor = '#8b5cf6';
      urlInput.style.boxShadow = '0 0 15px rgba(139, 92, 246, 0.4)';
    }
    showToast(`Đã nạp thành công ${count} video vào Studio! Bạn có thể nhấn 'Bắt đầu' để chạy song song.`);
  }
  // ================= HARDWARE AUTO-DETECT & SETTINGS =================
  async function loadSystemHardwareInfo() {
    try {
      const res = await fetch('/api/system/info');
      if (!res.ok) return;
      const data = await res.json();
      if (!data.success) return;
      const hw = data.hardware || {};
      const cfg = data.config || {};
      // 1. Sidebar status
      const workerEl = document.getElementById('worker-node-text');
      if (workerEl) {
        workerEl.innerHTML = `⚡ Worker: <strong>${escapeHtml(hw.hostname || 'Local PC')}</strong>`;
      }
      const gpuEl = document.getElementById('gpu-info-text');
      if (gpuEl) {
        gpuEl.innerHTML = `🎮 GPU: <strong>${escapeHtml(hw.gpu || 'Auto')}</strong>`;
      }
      // 2. Topbar LLM info
      const topbarLlm = document.getElementById('topbar-llm');
      if (topbarLlm && cfg.llm && cfg.llm.model) {
        topbarLlm.textContent = cfg.llm.model;
      }
      // 3. Settings Pane Hardware Box
      const hwHost = document.getElementById('hw-hostname');
      if (hwHost) hwHost.textContent = hw.hostname || 'Unknown';
      const hwCpu = document.getElementById('hw-cpu');
      if (hwCpu) hwCpu.textContent = hw.cpu || 'Unknown CPU';
      const hwGpu = document.getElementById('hw-gpu');
      if (hwGpu) hwGpu.textContent = hw.gpu || 'CPU Only';
      const hwRecEnc = document.getElementById('hw-rec-encoder');
      if (hwRecEnc) {
        hwRecEnc.textContent = hw.recommended_encoder === 'h264_nvenc' ? 'NVIDIA NVENC (Tăng tốc GPU phần cứng)' : 'CPU (libx264)';
      }
      // 4. Auto-sync encoder select in Settings
      const cfgEncoder = document.getElementById('cfg_encoder');
      if (cfgEncoder) {
        const preferredEncoder = (cfg.video_pipeline && cfg.video_pipeline.encoder && cfg.video_pipeline.encoder !== 'auto') 
          ? cfg.video_pipeline.encoder 
          : hw.recommended_encoder;
        cfgEncoder.value = preferredEncoder || 'h264_nvenc';
      }
      // 5. LLM base & model
      if (cfg.llm) {
        const baseInput = document.getElementById('cfg_llm_base');
        if (baseInput && cfg.llm.api_base) baseInput.value = cfg.llm.api_base;
        const modelSelect = document.getElementById('cfg_llm_model');
        if (modelSelect && cfg.llm.model) modelSelect.value = cfg.llm.model;
      }
    } catch (e) {
      console.warn('Could not load hardware info:', e);
    }
  }
  // Hook into window.onload / DOMContentLoaded
  document.addEventListener('DOMContentLoaded', () => {
    loadSystemHardwareInfo();
    checkYouTubeStatus();
    loadScheduleRulesConfig();
      loadTokensAndPages();
  });
  // ================= VIDEO PLAYER MODAL =================
  let currentModalVideo = { url: '', title: '', id: '' };
  function openVideoPlayerModal(url, title, videoId) {
    if (!videoId && url) {
      const m = url.match(/(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})/);
      videoId = m ? m[1] : '';
    }
    currentModalVideo = { url, title, id: videoId };
    document.getElementById('player-modal-title').textContent = title || 'Trình xem video trực tiếp';
    const iframe = document.getElementById('youtube-embed-frame');
    
    if (videoId) {
      iframe.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    } else {
      iframe.src = url;
    }
    const modal = document.getElementById('modal-video-player');
    modal.style.display = 'flex';
  }
  function closeVideoPlayerModal() {
    const modal = document.getElementById('modal-video-player');
    modal.style.display = 'none';
    const iframe = document.getElementById('youtube-embed-frame');
    iframe.src = '';
  }
  function copyModalVideoUrl() {
    if (!currentModalVideo.url) return;
    navigator.clipboard.writeText(currentModalVideo.url).then(() => {
      showToast('Đã sao chép link video vào clipboard!');
    }).catch(() => {
      prompt('Link video:', currentModalVideo.url);
    });
  }
  function sendModalUrlToRender() {
    if (!currentModalVideo.url) return;
    closeVideoPlayerModal();
    sendToRender(currentModalVideo.url);
  }
  function openContentWriterFromPlayer() {
    closeVideoPlayerModal();
    openContentWriterModal(currentModalVideo.title, '', '', 1, currentModalVideo.url);
  }
  // ================= AI CONTENT WRITER & FIRST COMMENT =================
  let currentWriterContext = { title: '', summary: '', job_id: '', clip_index: 1, video_url: '' };
  function openContentWriterModal(title, summary, jobId, clipIndex, videoUrl, clipFilename) {
    let filename = clipFilename || '';
    if (!filename && jobId) {
      filename = `${jobId}_clip_${clipIndex || 1}.mp4`;
    }
    currentWriterContext = {
      title: title || '',
      summary: summary || '',
      job_id: jobId || '',
      clip_index: clipIndex || 1,
      video_url: videoUrl || '',
      filename: filename
    };
    // Nạp video preview nội bộ vào modal
    const videoElem = document.getElementById('ai-writer-video-elem');
    const videoSrc = document.getElementById('ai-writer-video-src');
    const clipNameEl = document.getElementById('ai-writer-clip-name');
    const clipTitleEl = document.getElementById('ai-writer-clip-title');
    if (filename) {
      document.getElementById('ai-writer-video-box').style.display = 'flex';
      videoSrc.src = `/api/clips/play/${encodeURIComponent(filename)}`;
      videoElem.load();
      if (clipNameEl) clipNameEl.textContent = filename;
      if (clipTitleEl) clipTitleEl.textContent = title || filename;
    } else {
      document.getElementById('ai-writer-video-box').style.display = 'none';
    }
    document.getElementById('ai-writer-title').value = title || '';
    document.getElementById('out-viral-title').value = '';
    document.getElementById('out-fb-post').value = '';
    document.getElementById('out-first-comment').value = '';
    document.getElementById('out-hashtags').innerHTML = '';
    document.getElementById('thumb-preview-img').style.display = 'none';
    document.getElementById('thumb-placeholder').style.display = 'block';
    document.getElementById('btn-download-thumb').style.display = 'none';
    const modal = document.getElementById('modal-content-writer');
    modal.style.display = 'flex';
    // Tự động trigger nếu có title
    if (title) {
      triggerAiContentGen();
    }
  }
  function closeContentWriterModal() {
    document.getElementById('modal-content-writer').style.display = 'none';
  }
  async function triggerAiContentGen() {
    const title = document.getElementById('ai-writer-title').value.trim();
    if (!title) {
      alert('Vui lòng nhập tiêu đề video!');
      return;
    }
    const loading = document.getElementById('ai-writer-loading');
    const results = document.getElementById('ai-writer-results');
    const btn = document.getElementById('btn-trigger-ai-write');
    loading.style.display = 'block';
    results.style.opacity = '0.4';
    btn.disabled = true;
    try {
      const resp = await fetch('/api/content/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title,
          summary: currentWriterContext.summary,
          hook: currentWriterContext.title,
          video_url: currentWriterContext.video_url
        })
      });
      const data = await resp.json();
      if (data.success && data.data) {
        const d = data.data;
        document.getElementById('out-viral-title').value = d.viral_title || '';
        document.getElementById('out-fb-post').value = d.facebook_post || '';
        document.getElementById('out-first-comment').value = d.first_comment || '';
        
        // Render tags
        const tagsContainer = document.getElementById('out-hashtags');
        tagsContainer.innerHTML = '';
        (d.hashtags || []).forEach(t => {
          const badge = document.createElement('span');
          badge.className = 'badge';
          badge.style.background = '#1e293b';
          badge.style.color = '#38bdf8';
          badge.style.border = '1px solid #334155';
          badge.style.fontSize = '11px';
          badge.style.padding = '4px 8px';
          badge.textContent = t;
          tagsContainer.appendChild(badge);
        });
        showToast('AI đã tạo bài viết và First Comment thành công!');
      } else {
        alert('Lỗi tạo nội dung: ' + (data.error || 'Vui lòng thử lại'));
      }
    } catch (e) {
      alert('Không thể kết nối API AI: ' + e.message);
    } finally {
      loading.style.display = 'none';
      results.style.opacity = '1';
      btn.disabled = false;
    }
  }
  async function renderThumbnailAction() {
    const btn = document.getElementById('btn-render-thumb');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang render...';
    btn.disabled = true;
    const bannerText = document.getElementById('out-viral-title').value || document.getElementById('ai-writer-title').value || 'VIRAL MOMENT';
    try {
      const resp = await fetch('/api/content/thumbnail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: currentWriterContext.job_id,
          clip_index: currentWriterContext.clip_index,
          banner_text: bannerText
        })
      });
      const data = await resp.json();
      if (data.success && data.thumbnail_url) {
        const img = document.getElementById('thumb-preview-img');
        const placeholder = document.getElementById('thumb-placeholder');
        const downloadBtn = document.getElementById('btn-download-thumb');
        img.src = data.thumbnail_url + '?t=' + Date.now();
        img.style.display = 'block';
        placeholder.style.display = 'none';
        downloadBtn.href = data.thumbnail_url;
        downloadBtn.style.display = 'flex';
        showToast('Đã tạo ảnh thumbnail phong cách Longform thành công!');
      } else {
        alert('Chưa có file video hoàn chỉnh trên máy để render thumbnail: ' + (data.error || ''));
      }
    } catch (e) {
      alert('Lỗi render thumbnail: ' + e.message);
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  }
  function copyBoxText(elementId, btn) {
    const el = document.getElementById(elementId);
    if (!el || !el.value) return;
    navigator.clipboard.writeText(el.value).then(() => {
      const orig = btn.innerHTML;
      btn.innerHTML = '<i class="bi bi-check2"></i> Đã copy';
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
      showToast('Đã sao chép nội dung vào bộ nhớ tạm!');
    }).catch(() => {
      prompt('Copy nội dung:', el.value);
    });
  }
  // Tự động kiểm tra 9router active khi khởi động
  async function checkActive9Router() {
    try {
      const r = await fetch('/api/llm/detect');
      const d = await r.json();
      if (d.success && d.active_llm) {
        console.log('[9router Auto-Detect] Active endpoint:', d.active_llm.api_base);
      }
    } catch (e) {
      console.warn('[9router Check failed]:', e);
    }
  }
  window.addEventListener('DOMContentLoaded', checkActive9Router);
  // ================= MODAL & TAB HANDLERS =================
  function openAddTokenModal() {
    const m = document.getElementById('modal-add-token');
    if (m) m.style.display = 'flex';
  }
  function closeAddTokenModal() {
    const m = document.getElementById('modal-add-token');
    if (m) m.style.display = 'none';
  }
  function openAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (m) m.style.display = 'flex';
  }
  function closeAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (m) m.style.display = 'none';
  }
  // Xem chi tiết Job trong hàng đợi khi ấn icon con mắt
  async function showJobDetail(jobId) {
    const modal = document.getElementById('jobDetailModal');
    const titleEl = document.getElementById('job-detail-modal-title');
    const subEl = document.getElementById('job-detail-modal-sub');
    const bodyEl = document.getElementById('job-detail-modal-body');
    if (!modal) return;
    titleEl.textContent = 'Chi tiết Job: ' + jobId.substring(0, 8);
    subEl.textContent = 'Đang tải dữ liệu tiến độ...';
    bodyEl.innerHTML = '<div style="text-align:center; padding: 30px;"><span class="spinner-border text-primary"></span><div style="margin-top:10px; color:#94a3b8;">Đang nạp chi tiết job từ máy chủ...</div></div>';
    modal.style.display = 'flex';
    try {
      const res = await fetch('/api/jobs/' + jobId);
      if (!res.ok) throw new Error('Không tìm thấy thông tin job');
      const j = await res.json();
      titleEl.textContent = 'Chi tiết Job: ' + (j.id ? j.id.substring(0, 8) : jobId);
      subEl.textContent = j.created_at || '';
      let statusBadge = `<span class="badge badge-queued">${(j.status||'queued').toUpperCase()}</span>`;
      if (j.status === 'completed') statusBadge = `<span class="badge badge-done">HOÀN THÀNH</span>`;
      if (j.status === 'error') statusBadge = `<span class="badge badge-error">LỖI</span>`;
      if (j.status === 'running') statusBadge = `<span class="badge badge-running">ĐANG CHẠY</span>`;
      bodyEl.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Nguồn Video</div>
            <div style="font-size: 14px; font-weight: 700; color: #fff; margin-top: 4px;">${j.video_title || 'Chưa có tiêu đề'}</div>
            <div style="font-size: 12px; color: #38bdf8; word-break: break-all; margin-top: 2px;"><a href="${j.youtube_url}" target="_blank" style="color:#38bdf8;">${j.youtube_url}</a></div>
          </div>
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
            <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 12px;">
              <div style="font-size: 11px; color: #94a3b8;">Trạng thái</div>
              <div style="margin-top: 4px;">${statusBadge}</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 12px;">
              <div style="font-size: 11px; color: #94a3b8;">Tiến độ bước</div>
              <div style="font-size: 14px; font-weight: 700; color: #f59e0b; margin-top: 4px;">Bước ${j.step || 1} / 5</div>
            </div>
            <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 12px;">
              <div style="font-size: 11px; color: #94a3b8;">Số clips trích xuất</div>
              <div style="font-size: 14px; font-weight: 700; color: #34d399; margin-top: 4px;">${(j.clips||[]).length} / ${j.num_clips||3}</div>
            </div>
          </div>
          <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Thông điệp tiến độ</div>
            <div style="font-size: 13px; color: #cbd5e1; margin-top: 6px; font-family: monospace;">${j.progress_msg || 'Không có thông báo tiến độ mới.'}</div>
          </div>
          ${j.error ? `
          <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 14px;">
            <div style="font-size: 11px; color: #ef4444; font-weight: 700; text-transform: uppercase;">Chi tiết lỗi</div>
            <div style="font-size: 12.5px; color: #fca5a5; margin-top: 6px; font-family: monospace; white-space: pre-wrap;">${j.error}</div>
          </div>` : ''}
          ${(j.clips && j.clips.length > 0) ? `
          <div>
            <div style="font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 8px; text-transform: uppercase;">Danh sách Clips trích xuất:</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${j.clips.map(c => `
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 10px 14px;">
                  <div>
                    <div style="font-size: 13px; font-weight: 700; color: #fff;">${c.hook_title || c.filename}</div>
                    <div style="font-size: 11px; color: #94a3b8;">Thời lượng: ${Math.round(c.duration||0)}s | Điểm viral: ${c.viral_score||95}/100</div>
                  </div>
                  <a href="/api/clips/play/${encodeURIComponent(c.filename)}" download class="btn btn-primary btn-sm"><i class="bi bi-download"></i> Tải clip</a>
                </div>
              `).join('')}
            </div>
          </div>` : ''}
        </div>
      `;
    } catch (e) {
      bodyEl.innerHTML = `<div class="alert alert-danger" style="margin:0;">Lỗi: ${e.message}</div>`;
    }
  }
  function closeJobDetailModal() {
    const modal = document.getElementById('jobDetailModal');
    if (modal) modal.style.display = 'none';
  }
  // ================= TOKEN & PAGE MANAGEMENT =================
  let cachedPagesList = [];
  let globalTokensCatalog = [];
  function openAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (!m) return;
    m.style.display = 'flex';
    
    // Render list of pages into group-pages-select-box
    const box = document.getElementById('group-pages-select-box');
    if (box) {
      if (cachedPagesList.length === 0) {
        box.innerHTML = '<span style="font-size: 11px; color: #64748b;">Chưa có Fanpage nào được đồng bộ. Hãy thêm Access Token trước!</span>';
      } else {
        box.innerHTML = cachedPagesList.map(p => `
          <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #cbd5e1; cursor: pointer; padding: 4px 6px; border-radius: 4px; background: rgba(255,255,255,0.02);">
            <input type="checkbox" class="group-page-checkbox" value="${p.page_id || p.id}">
            <span><b>${p.page_name || p.name}</b> <small style="color: #64748b;">(${p.page_id || p.id})</small></span>
          </label>
        `).join('');
      }
    }
  }
  function closeAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (m) m.style.display = 'none';
  }
  async function loadTokensAndPages() {
    try {
      const [resTok, resPages, resGrp] = await Promise.all([
        fetch('/api/tokens'),
        fetch('/api/pages'),
        fetch('/api/groups')
      ]);
      const dataTok = await resTok.json();
      const dataPages = await resPages.json();
      const dataGrp = await resGrp.json();
      const tokens = dataTok.tokens || [];
      globalTokensCatalog = tokens;
      const pages = dataPages.pages || [];
      const groups = dataGrp.groups || [];
      cachedPagesList = pages;
      // Update counters
      if (document.getElementById('stat-total-tokens')) document.getElementById('stat-total-tokens').textContent = tokens.length;
      if (document.getElementById('stat-total-pages')) document.getElementById('stat-total-pages').textContent = pages.length;
      if (document.getElementById('stat-total-groups')) document.getElementById('stat-total-groups').textContent = groups.length;
      if (document.getElementById('badge-page-count')) document.getElementById('badge-page-count').textContent = pages.length + ' Trang';
      // Render Tokens
      const tokCont = document.getElementById('tokens-list-container');
      if (tokCont) {
        if (tokens.length === 0) {
          tokCont.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">Chưa có Token nào trong kho. Bấm nút "+ Thêm Token Mới" bên trên.</div>';
        } else {
          tokCont.innerHTML = tokens.map(t => {
            const masked = t.token_masked || t.masked_token || '***';
            const statusBadge = t.status === 'ACTIVE' 
              ? '<span class="badge badge-done" style="font-size: 9.5px;">ACTIVE</span>' 
              : `<span class="badge badge-error" style="font-size: 9.5px;" title="${t.error_msg || ''}">ERROR</span>`;
            return `
              <div style="display: flex; justify-content: space-between; align-items: center; background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 10px 14px;">
                <div>
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="font-weight: 700; font-size: 13px; color: #f59e0b;">${t.name}</span>
                    <span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-size: 10px;">${t.kind || 'SYS'}</span>
                    ${statusBadge}
                  </div>
                  <div style="font-size: 11px; color: #64748b; font-family: monospace; margin-top: 2px;">${masked} · ${t.pages_count || 0} Pages</div>
                </div>
                <button class="btn btn-secondary btn-sm text-danger" onclick="deleteToken('${t.id}')" title="Xóa token"><i class="bi bi-trash"></i></button>
              </div>
            `;
          }).join('');
        }
      }
      // Render Pages
      const pagesTbody = document.getElementById('pages-tbody');
      if (pagesTbody) {
        if (pages.length === 0) {
          pagesTbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 30px; color: #64748b;">Chưa có Fanpage nào được đồng bộ. Hãy thêm System User Token để tự động nạp Fanpage!</td></tr>';
        } else {
          pagesTbody.innerHTML = pages.map(p => {
            const pId = p.page_id || p.id;
            const pName = p.page_name || p.name || 'Fanpage';
            const avatarHtml = p.avatar 
              ? `<img src="${p.avatar}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover;">`
              : `<div style="width: 28px; height: 28px; border-radius: 50%; background: #2563eb; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #fff; font-size: 11px;">${pName[0]}</div>`;
            const tokenOptions = tokens.map(t => {
              const selected = (p.token_id === t.id) ? 'selected' : '';
              return `<option value="${t.id}" ${selected}>🔑 ${t.name}</option>`;
            }).join('');
            const tokenSelectHtml = `
              <select onchange="assignTokenToPage('${pId}', this.value)" style="background: #1e293b; color: #f59e0b; border: 1px solid #334155; border-radius: 6px; padding: 3px 6px; font-size: 11px;">
                <option value="">-- Chưa gán Token --</option>
                ${tokenOptions}
              </select>
            `;
            return `
              <tr style="border-bottom: 1px solid #1e293b;">
                <td style="padding: 8px 6px;">${avatarHtml}</td>
                <td style="padding: 8px 6px; font-weight: 600; color: #fff;">${pName}</td>
                <td style="padding: 8px 6px; font-family: monospace; font-size: 11.5px; color: #94a3b8;">${pId}</td>
                <td style="padding: 8px 6px;">${tokenSelectHtml}</td>
                <td style="padding: 8px 6px; text-align: right; font-weight: 700; color: #38bdf8;">${p.total_posted || p.published_count || 0}</td>
              </tr>
            `;
          }).join('');
        }
      }
      // Render Groups
      const grpCont = document.getElementById('groups-list-container');
      if (grpCont) {
        if (groups.length === 0) {
          grpCont.innerHTML = '<div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">Chưa tạo nhóm trang nào. Bấm nút "+ Tạo Nhóm Page" bên trên.</div>';
        } else {
          grpCont.innerHTML = groups.map(g => `
            <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="font-weight: 700; font-size: 13px; color: #c084fc;">${g.name}</div>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="badge" style="background: rgba(192, 132, 252, 0.2); color: #c084fc; font-size: 10px;">${(g.page_ids||[]).length} Pages</span>
                  <button class="btn btn-secondary btn-sm text-danger" style="padding: 2px 6px; font-size: 11px;" onclick="deleteGroup('${g.id}')" title="Xóa nhóm"><i class="bi bi-trash"></i></button>
                </div>
              </div>
              <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Thư mục: <code style="color: #94a3b8;">${g.folder_binding || g.folder_path || 'Mặc định output'}</code></div>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      console.warn('Lỗi loadTokensAndPages:', e);
    }
  }
  async function submitAddToken() {
    const nameInput = document.getElementById('token-input-name');
    const kindSelect = document.getElementById('token-input-kind');
    const strTextarea = document.getElementById('token-input-str');
    const btnSubmit = document.getElementById('btn-submit-token');
    const name = nameInput ? nameInput.value.trim() : '';
    const kind = kindSelect ? kindSelect.value : 'SYS';
    const tokens_input = strTextarea ? strTextarea.value.trim() : '';
    if (!tokens_input) {
      alert('Vui lòng nhập hoặc dán ít nhất 1 mã Access Token!');
      return;
    }
    const originalBtnHtml = btnSubmit ? btnSubmit.innerHTML : '';
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang đồng bộ Meta...';
    }
    try {
      const res = await fetch('/api/tokens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, tokens_input, kind })
      });
      const d = await res.json();
      if (res.ok && d.success) {
        const count = d.count || 1;
        const pagesSynced = d.synced_pages || 0;
        alert(`Đã lưu thành công ${count} token và đồng bộ ${pagesSynced} Fanpages từ Meta!`);
        closeAddTokenModal();
        if (strTextarea) strTextarea.value = '';
        if (nameInput) nameInput.value = '';
        await loadTokensAndPages();
      } else {
        alert('Lỗi lưu token: ' + (d.error || 'Không thể đồng bộ'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = originalBtnHtml;
      }
    }
  }
  async function deleteToken(id) {
    if (!confirm('Xóa token này khỏi kho? Các Page thuộc token này vẫn được giữ lại.')) return;
    try {
      const res = await fetch('/api/tokens/' + id, { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        await loadTokensAndPages();
      } else {
        alert('Không thể xóa token: ' + (d.error || 'Lỗi server'));
      }
    } catch (e) {
      alert('Lỗi xóa token: ' + e.message);
    }
  }
  async function submitAddGroup() {
    const nameEl = document.getElementById('group-input-name');
    const folderEl = document.getElementById('group-input-folder');
    const btnSubmit = document.getElementById('btn-submit-group');
    const name = nameEl ? nameEl.value.trim() : '';
    const folder = folderEl ? folderEl.value.trim() : '';
    if (!name) {
      alert('Vui lòng nhập Tên nhóm Fanpage!');
      return;
    }
    // Collect selected page IDs
    const checkedBoxes = document.querySelectorAll('.group-page-checkbox:checked');
    const page_ids = Array.from(checkedBoxes).map(cb => cb.value);
    const origBtnHtml = btnSubmit ? btnSubmit.innerHTML : '';
    if (btnSubmit) {
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang lưu...';
    }
    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, folder_binding: folder, page_ids })
      });
      const d = await res.json();
      if (res.ok && d.success) {
        alert(`Đã tạo nhóm "${name}" thành công với ${page_ids.length} Fanpages!`);
        closeAddGroupModal();
        if (nameEl) nameEl.value = '';
        await loadTokensAndPages();
      } else {
        alert('Lỗi tạo nhóm: ' + (d.error || 'Không thể tạo nhóm'));
      }
    } catch (e) {
      alert('Lỗi kết nối tạo nhóm: ' + e.message);
    } finally {
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = origBtnHtml;
      }
    }
  }
  // Support legacy or alternative naming
  const submitSaveGroup = submitAddGroup;
  async function deleteGroup(id) {
    if (!confirm('Xóa nhóm Fanpage này? (Các Fanpage bên trong không bị ảnh hưởng)')) return;
    try {
      const res = await fetch('/api/groups/' + id, { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        await loadTokensAndPages();
      } else {
        alert('Không thể xóa nhóm: ' + (d.error || 'Lỗi server'));
      }
    } catch (e) {
      alert('Lỗi xóa nhóm: ' + e.message);
    }
  }
  // ================= WEBSITE ARTICLE CMS CONFIG =================
  async 
  // ================= QUY TẮC LÊN LỊCH & PHÂN BỔ (LOHA CONTROLLER) =================
  // LOHA SCHEDULE RULES MODAL & BANNER SYNC
  function openScheduleRulesModal() {
    const m = document.getElementById('modal-schedule-rules');
    if (m) {
      m.style.display = 'flex';
      loadScheduleRulesConfig();
      loadTokensAndPages();
    }
  }

  function closeScheduleRulesModal() {
    const m = document.getElementById('modal-schedule-rules');
    if (m) m.style.display = 'none';
  }

  async function checkYouTubeStatus() {
    try {
      const resp = await fetch('/api/system/youtube_status');
      const data = await resp.json();
      const pill = document.getElementById('topbar-yt-status');
      const icon = document.getElementById('topbar-yt-icon');
      const text = document.getElementById('topbar-yt-text');
      const badge = document.getElementById('topbar-yt-badge');

      if (data && data.logged_in) {
        if (pill) {
          pill.style.background = 'rgba(34, 197, 94, 0.15)';
          pill.style.borderColor = 'rgba(34, 197, 94, 0.4)';
          pill.title = 'YouTube Profile: ĐÃ ĐĂNG NHẬP (' + data.count + ' cookie auth). Bấm để mở Chrome quản trị';
        }
        if (icon) {
          icon.className = 'bi bi-check-circle-fill';
          icon.style.color = '#4ade80';
        }
        if (text) {
          text.style.color = '#86efac';
          text.innerText = 'YouTube: Sẵn sàng';
        }
        if (badge) {
          badge.style.background = 'rgba(34, 197, 94, 0.3)';
          badge.style.color = '#86efac';
          badge.innerText = 'Đã Login';
        }
      } else {
        if (pill) {
          pill.style.background = 'rgba(239, 68, 68, 0.15)';
          pill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
          pill.title = 'Chưa phát hiện phiên đăng nhập YouTube. Bấm để mở Chrome đăng nhập profile';
        }
        if (icon) {
          icon.className = 'bi bi-browser-chrome';
          icon.style.color = '#f87171';
        }
        if (text) {
          text.style.color = '#fca5a5';
          text.innerText = 'YouTube: Chưa Login';
        }
        if (badge) {
          badge.style.background = 'rgba(239, 68, 68, 0.3)';
          badge.style.color = '#fca5a5';
          badge.innerText = 'Chưa Đăng Nhập';
        }
      }
    } catch (err) {
      console.warn('Lỗi kiểm tra trạng thái YouTube:', err);
    }
  }

  async function loadScheduleRulesConfig() {
    try {
      const resp = await fetch('/api/schedule/rules');
      const data = await resp.json();
      if (data.status === 'ok' && data.rules) {
        const r = data.rules;
        const slotsArr = (r.slots && r.slots.length > 0) ? r.slots : ['08:00', '11:30', '20:30'];
        if (document.getElementById('sched-slots')) document.getElementById('sched-slots').value = slotsArr.join(', ');
        if (document.getElementById('sched-stagger-min')) document.getElementById('sched-stagger-min').value = r.stagger_min || 5;
        if (document.getElementById('sched-stagger-max')) document.getElementById('sched-stagger-max').value = r.stagger_max || 15;
        if (document.getElementById('sched-max-posts')) document.getElementById('sched-max-posts').value = r.max_posts_per_page_day || 4;
        if (document.getElementById('sched-auto-comment')) document.getElementById('sched-auto-comment').checked = (r.auto_comment !== false);
        if (document.getElementById('sched-include-web')) document.getElementById('sched-include-web').checked = (r.include_website_link !== false);
        if (document.getElementById('sched-folder-mode')) {
          document.getElementById('sched-folder-mode').value = r.folder_binding_mode || 'round_robin';
        }

        // Cập nhật LoHa Gradient Banner text
        const bannerSlots = document.getElementById('loha-banner-slots');
        if (bannerSlots) {
          bannerSlots.innerText = slotsArr.join(' · ');
        }
        const bannerHours = document.getElementById('loha-banner-hours');
        if (bannerHours && slotsArr.length > 0) {
          bannerHours.innerText = slotsArr[0] + ' – ' + slotsArr[slotsArr.length - 1];
        }
        const bannerStagger = document.getElementById('loha-banner-stagger');
        if (bannerStagger) {
          bannerStagger.innerText = (r.stagger_min || 5) + ' – ' + (r.stagger_max || 15) + ' phút';
        }
      }

      // Populate group select in distribution card
      const grpResp = await fetch('/api/pages/groups');
      const grpData = await grpResp.json();
      const selectGrp = document.getElementById('dist-select-group');
      if (selectGrp) {
        selectGrp.innerHTML = '<option value="">-- Chọn Nhóm Fanpage --</option>';
        (grpData.groups || []).forEach(g => {
          selectGrp.innerHTML += `<option value="${g.id}">${g.name} (${(g.page_ids || []).length} Pages)</option>`;
        });
      }

      // Set default start time
      const dtInput = document.getElementById('dist-start-time');
      if (dtInput && !dtInput.value) {
        const now = new Date();
        now.setMinutes(now.getMinutes() + 20);
        dtInput.value = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      }
    } catch (err) {
      console.warn('Lỗi load schedule rules:', err);
    }
  }

  async function saveScheduleRulesConfig() {
    const rawSlots = document.getElementById('sched-slots') ? document.getElementById('sched-slots').value : '';
    const slots = rawSlots.split(',').map(s => s.trim()).filter(s => s);
    const body = {
      slots: slots.length ? slots : ['08:00', '11:30', '20:30'],
      stagger_min: parseInt(document.getElementById('sched-stagger-min')?.value || 5, 10),
      stagger_max: parseInt(document.getElementById('sched-stagger-max')?.value || 15, 10),
      max_posts_per_page_day: parseInt(document.getElementById('sched-max-posts')?.value || 4, 10),
      auto_comment: document.getElementById('sched-auto-comment') ? document.getElementById('sched-auto-comment').checked : true,
      include_website_link: document.getElementById('sched-include-web') ? document.getElementById('sched-include-web').checked : true,
      folder_binding_mode: document.getElementById('sched-folder-mode')?.value || 'round_robin'
    };

    const saveBtn = document.getElementById('btn-save-sched-rules');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Đang lưu...';
    }

    try {
      const resp = await fetch('/api/schedule/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      if (data.status === 'ok') {
        showToast('Đã lưu quy tắc lên lịch LoHa thành công!');
        closeScheduleRulesModal();
        // Refresh banner
        loadScheduleRulesConfig();
      loadTokensAndPages();
      } else {
        alert('Lỗi khi lưu quy tắc lên lịch: ' + (data.message || ''));
      }
    } catch (err) {
      alert('Lỗi kết nối: ' + err.message);
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-check2-circle"></i> Lưu Quy Tắc Lên Lịch';
      }
    }
  }

  async function executeBatchDistribute() {
    const grpId = document.getElementById('dist-select-group').value;
    const startTime = document.getElementById('dist-start-time').value;
    const stagger = parseInt(document.getElementById('dist-stagger').value || 15, 10);
    const banner = document.getElementById('dist-result-banner');
    const btn = document.getElementById('btn-batch-distribute');

    if (!grpId) {
      alert('Vui lòng chọn 1 Nhóm Fanpage để phân bổ!');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang phân bổ video từ kho...';

    try {
      // Lấy danh sách clip hiện có trong output
      const clipResp = await fetch('/api/clips');
      const clipData = await clipResp.json();
      const clips = clipData.clips || [];
      const filenames = clips.map(c => c.filename);

      if (!filenames.length) {
        alert('Kho Clips hiện chưa có video nào hoàn thành để phân bổ!');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-play-circle-fill"></i> Bắt đầu Tự động Phân bổ & Lên lịch';
        return;
      }

      const resp = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: grpId,
          clip_filenames: filenames,
          start_time: startTime,
          stagger_minutes: stagger,
          auto_first_comment: true
        })
      });

      const res = await resp.json();
      if (res.success) {
        banner.style.display = 'block';
        banner.style.background = 'rgba(34, 197, 94, 0.15)';
        banner.style.border = '1px solid #22c55e';
        banner.style.color = '#4ade80';
        banner.innerHTML = `<strong><i class="bi bi-check-circle-fill"></i> Thành công!</strong> Đã tự động tạo và lên lịch cho ${res.posts_count || res.count || 0} bài đăng phân bổ đều cho các Page.`;
        showToast('Đã phân bổ và lên lịch thành công!');
      } else {
        banner.style.display = 'block';
        banner.style.background = 'rgba(239, 68, 68, 0.15)';
        banner.style.border = '1px solid #ef4444';
        banner.style.color = '#f87171';
        banner.innerHTML = `<strong><i class="bi bi-exclamation-triangle-fill"></i> Lỗi:</strong> ${res.error || 'Không thể phân bổ video'}`;
      }
    } catch (err) {
      banner.style.display = 'block';
      banner.style.background = 'rgba(239, 68, 68, 0.15)';
      banner.style.border = '1px solid #ef4444';
      banner.style.color = '#f87171';
      banner.innerHTML = `<strong><i class="bi bi-x-circle-fill"></i> Lỗi kết nối:</strong> ${err.message}`;
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-play-circle-fill"></i> Bắt đầu Tự động Phân bổ & Lên lịch';
    }
  }


  async function loadWebsiteConfig() {
    try {
      const res = await fetch('/api/website-config');
      if (!res.ok) return;
      const d = await res.json();
      if (d.success && d.config) {
        if (document.getElementById('cfg_web_base')) document.getElementById('cfg_web_base').value = d.config.base_url || '';
        if (document.getElementById('cfg_web_user')) document.getElementById('cfg_web_user').value = d.config.username || '';
        if (document.getElementById('cfg_web_status')) {
          if (d.config.has_password) {
            document.getElementById('cfg_web_status').innerHTML = '<span style="color:#22c55e;"><i class="bi bi-check-circle-fill"></i> Đã lưu mật khẩu an toàn (DPAPI). Để trống ô mật khẩu nếu không đổi.</span>';
          } else {
            document.getElementById('cfg_web_status').innerHTML = '<span style="color:#f59e0b;"><i class="bi bi-exclamation-triangle"></i> Chưa lưu mật khẩu website.</span>';
          }
        }
      }
    } catch (e) {
      console.warn('Lỗi loadWebsiteConfig:', e);
    }
  }
  async function saveWebsiteConfig(e) {
    e.preventDefault();
    const msgEl = document.getElementById('website-save-msg');
    msgEl.textContent = 'Đang lưu...';
    msgEl.style.color = '#38bdf8';
    const base_url = document.getElementById('cfg_web_base').value.trim();
    const username = document.getElementById('cfg_web_user').value.trim();
    const password = document.getElementById('cfg_web_password').value;
    try {
      const res = await fetch('/api/website-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url, username, password })
      });
      const d = await res.json();
      if (res.ok && d.success) {
        msgEl.textContent = '✓ Đã lưu cấu hình website bài viết an toàn!';
        msgEl.style.color = '#22c55e';
        document.getElementById('cfg_web_password').value = '';
        loadWebsiteConfig();
        setTimeout(() => { msgEl.textContent = ''; }, 4000);
      } else {
        msgEl.textContent = 'Lỗi: ' + (d.error || 'Không thể lưu');
        msgEl.style.color = '#ef4444';
      }
    } catch (err) {
      msgEl.textContent = 'Lỗi kết nối: ' + err.message;
      msgEl.style.color = '#ef4444';
    }
  }
  async function testWebsiteConnection() {
    const msgEl = document.getElementById('website-save-msg');
    msgEl.textContent = 'Đang kiểm tra kết nối tới Website...';
    msgEl.style.color = '#f59e0b';
    try {
      const res = await fetch('/api/website-config/test', { method: 'POST' });
      const d = await res.json();
      if (d.success) {
        msgEl.textContent = '✓ Kết nối Website thành công: ' + (d.message || 'OK');
        msgEl.style.color = '#22c55e';
      } else {
        msgEl.textContent = '❌ Lỗi kết nối: ' + (d.error || 'Thất bại');
        msgEl.style.color = '#ef4444';
      }
    } catch (e) {
      msgEl.textContent = 'Lỗi: ' + e.message;
      msgEl.style.color = '#ef4444';
    }
  }
  // ================= PUBLISHER & SCHEDULER CONTROLLER (LOHA ARCHITECTURE) =================
  let currentPublishContext = {
    filename: '',
    title: '',
    caption: '',
    first_comment: ''
  };
  let globalPagesCatalog = [];
  let globalGroupsCatalog = [];
  function openDirectPublishModal(filename, title) {
    currentPublishContext = {
      filename: filename,
      title: title || 'Clip Highlight',
      caption: title || '',
      first_comment: ''
    };
    initAndShowPublishModal();
  }
  function openPublishModalFromWriter() {
    const title = document.getElementById('out-viral-title').value.trim() || document.getElementById('ai-writer-title').value.trim();
    const fbPost = document.getElementById('out-fb-post').value.trim();
    const comment = document.getElementById('out-first-comment').value.trim();
    const filename = currentWriterContext.filename;
    if (!filename) {
      alert('Không tìm thấy video clip cần đăng!');
      return;
    }
    currentPublishContext = {
      filename: filename,
      title: title,
      caption: fbPost || title,
      first_comment: comment
    };
    initAndShowPublishModal();
  }
  async function initAndShowPublishModal() {
    document.getElementById('pub-clip-title').textContent = currentPublishContext.title || 'Clip Highlight';
    document.getElementById('pub-clip-filename').textContent = currentPublishContext.filename;
    document.getElementById('pub-caption').value = currentPublishContext.caption || '';
    document.getElementById('pub-first-comment').value = currentPublishContext.first_comment || '';
    // Set default schedule time to Now + 20 minutes
    const now = new Date();
    now.setMinutes(now.getMinutes() + 20);
    const localIso = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    const dtInput = document.getElementById('pub-schedule-datetime');
    if (dtInput) dtInput.value = localIso;
    // Reset radio
    const radios = document.getElementsByName('pub_mode');
    for (let r of radios) {
      if (r.value === 'now') r.checked = true;
    }
    toggleScheduleOptions();
    const banner = document.getElementById('pub-status-banner');
    if (banner) banner.style.display = 'none';
    // Fetch pages & groups
    try {
      const res = await fetch('/api/pages');
      const data = await res.json();
      if (data.success) {
        globalPagesCatalog = data.pages || [];
        globalGroupsCatalog = data.groups || [];
        // Fill single page select
        const pSel = document.getElementById('pub-select-single-page');
        pSel.innerHTML = '<option value="">-- Chọn 1 Fanpage cụ thể --</option>' + 
          globalPagesCatalog.map(p => `<option value="${p.page_id}">${p.page_name} (ID: ${p.page_id})</option>`).join('');
        // Fill group select
        const gSel = document.getElementById('pub-select-group');
        gSel.innerHTML = '<option value="">-- Chọn nhóm trang vệ tinh --</option>' + 
          globalGroupsCatalog.map(g => `<option value="${g.id}">${g.name} (${(g.page_ids || []).length} Pages)</option>`).join('');
        onPubGroupChanged();
      }
    } catch (e) {
      console.error('Error loading pages for publish modal:', e);
    }
    document.getElementById('modal-publish-reel').style.display = 'flex';
  }
  function closePublishModal() {
    document.getElementById('modal-publish-reel').style.display = 'none';
  }
  function toggleScheduleOptions() {
    const mode = document.querySelector('input[name="pub_mode"]:checked')?.value;
    const box = document.getElementById('pub-schedule-box');
    const btn = document.getElementById('btn-execute-publish');
    if (box) {
      box.style.display = (mode === 'schedule') ? 'block' : 'none';
    }
    if (btn) {
      if (mode === 'schedule') {
        btn.innerHTML = '<i class="bi bi-calendar-check"></i> Xác nhận Lên Lịch (Schedule)';
        btn.style.background = 'linear-gradient(135deg, #8b5cf6, #ec4899)';
      } else {
        btn.innerHTML = '<i class="bi bi-send-check"></i> Đăng Ngay (Publish Now)';
        btn.style.background = 'linear-gradient(135deg, #0ea5e9, #2563eb)';
      }
    }
  }
  function onPubGroupChanged() {
    const gVal = document.getElementById('pub-select-group').value;
    const summary = document.getElementById('pub-pages-target-summary');
    if (gVal) {
      const grp = globalGroupsCatalog.find(g => g.id === gVal);
      if (grp) {
        const count = (grp.page_ids || []).length;
        summary.innerHTML = `<i class="bi bi-collection-fill text-warning"></i> Đã chọn nhóm <strong>${grp.name}</strong> (${count} Fanpage). Video sẽ được tự động đăng lần lượt lên tất cả các trang!`;
        return;
      }
    }
    const pVal = document.getElementById('pub-select-single-page').value;
    if (pVal) {
      const p = globalPagesCatalog.find(item => item.page_id === pVal);
      summary.innerHTML = `<i class="bi bi-flag-fill text-info"></i> Đã chọn Fanpage: <strong>${p ? p.page_name : pVal}</strong>.`;
    } else {
      summary.innerHTML = `<i class="bi bi-info-circle"></i> Vui lòng chọn Nhóm trang hoặc 1 Fanpage cụ thể.`;
    }
  }
  document.getElementById('pub-select-single-page')?.addEventListener('change', () => {
    if (document.getElementById('pub-select-single-page').value) {
      document.getElementById('pub-select-group').value = '';
    }
    onPubGroupChanged();
  });
  async function insertWebsiteLinkToFirstComment() {
    try {
      const res = await fetch('/api/website-config');
      const d = await res.json();
      const siteUrl = d.site_url || 'https://';
      const commentInput = document.getElementById('pub-first-comment');
      const current = commentInput.value.trim();
      const linkText = `Xem chi tiết và cập nhật thêm tại: ${siteUrl}`;
      if (!current) {
        commentInput.value = linkText;
      } else if (!current.includes(siteUrl)) {
        commentInput.value = current + ' - ' + linkText;
      }
      showToast('Đã chèn Link website vào First Comment!');
    } catch (e) {
      showToast('Chưa lấy được cấu hình website');
    }
  }
  async function executePublishReel() {
    const filename = currentPublishContext.filename;
    const caption = document.getElementById('pub-caption').value.trim();
    const firstComment = document.getElementById('pub-first-comment').value.trim();
    const groupId = document.getElementById('pub-select-group').value;
    const singlePageId = document.getElementById('pub-select-single-page').value;
    const mode = document.querySelector('input[name="pub_mode"]:checked')?.value;
    const scheduleDt = document.getElementById('pub-schedule-datetime').value;
    const stagger = parseInt(document.getElementById('pub-schedule-stagger').value || '15', 10);
    if (!groupId && !singlePageId) {
      alert('Vui lòng chọn ít nhất 1 Fanpage hoặc 1 Nhóm Trang để xuất bản!');
      return;
    }
    const btn = document.getElementById('btn-execute-publish');
    const banner = document.getElementById('pub-status-banner');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang xử lý Meta API...';
    banner.style.display = 'block';
    banner.style.background = '#1e293b';
    banner.style.color = '#38bdf8';
    banner.innerHTML = '<i class="bi bi-hourglass-split"></i> Đang kết nối Meta Graph API v22.0 để tải video và xuất bản...';
    const payload = {
      filename: filename,
      caption: caption,
      first_comment: firstComment,
      group_id: groupId || null,
      page_id: singlePageId || null,
      schedule_time: (mode === 'schedule') ? scheduleDt : null,
      stagger_minutes: stagger
    };
    try {
      const resp = await fetch('/api/publish/reel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (data.success) {
        banner.style.background = 'rgba(34, 197, 94, 0.2)';
        banner.style.border = '1px solid #22c55e';
        banner.style.color = '#4ade80';
        const sCount = data.success_count || 1;
        const actionStr = (mode === 'schedule') ? 'Lên lịch thành công' : 'Đã xuất bản trực tiếp';
        banner.innerHTML = `<strong><i class="bi bi-check-circle-fill"></i> ${actionStr}!</strong> Đã xử lý cho ${sCount} Fanpage. Facebook Video ID: ${data.results?.[0]?.video_id || 'OK'}.`;
        showToast(`${actionStr} cho ${sCount} Trang!`);
        btn.innerHTML = '<i class="bi bi-check-lg"></i> Hoàn tất!';
        
        // Cập nhật lại số liệu
        loadTokensAndPages();
        setTimeout(() => {
          btn.disabled = false;
          toggleScheduleOptions();
        }, 3000);
      } else {
        banner.style.background = 'rgba(239, 68, 68, 0.2)';
        banner.style.border = '1px solid #ef4444';
        banner.style.color = '#f87171';
        banner.innerHTML = `<strong><i class="bi bi-exclamation-triangle-fill"></i> Lỗi:</strong> ${data.error || 'Không thể đăng Reel lên Facebook'}`;
        btn.disabled = false;
        toggleScheduleOptions();
      }
    } catch (err) {
      banner.style.background = 'rgba(239, 68, 68, 0.2)';
      banner.style.border = '1px solid #ef4444';
      banner.style.color = '#f87171';
      banner.innerHTML = `<strong><i class="bi bi-x-circle-fill"></i> Lỗi kết nối:</strong> ${err.message}`;
      btn.disabled = false;
      toggleScheduleOptions();
    }
  }
  let lastFailedJobId = null;
  function showJobErrorPopup(job) {
    lastFailedJobId = job.id;
    document.getElementById('job-error-modal-title').textContent = `Lỗi Job [${job.id}]`;
    document.getElementById('job-error-modal-video').innerHTML = `<b>Video:</b> ${escapeHtml(job.video_title || job.youtube_url)} (Bước ${job.step || '?'})`;
    document.getElementById('job-error-modal-msg').textContent = job.error_msg || job.progress_msg || 'Không rõ nguyên nhân lỗi cụ thể';
    document.getElementById('jobErrorPopupModal').style.display = 'flex';
  }
  function closeJobErrorPopup() {
    document.getElementById('jobErrorPopupModal').style.display = 'none';
  }
  function showJobDetailFromError() {
    closeJobErrorPopup();
    if (lastFailedJobId) {
      showJobDetail(lastFailedJobId);
    }
  }

  // Toggle Custom Hook Input
  function toggleCustomHook(val) {
    const box = document.getElementById('custom-hook-box');
    if (box) box.style.display = (val === 'custom') ? 'block' : 'none';
  }

  // Poll Queue Status
  async function updateQueueStatus() {
    try {
      const res = await fetch('/api/queue/status');
      if (!res.ok) return;
      const data = await res.json();
      if (document.getElementById('q-stat-queued')) document.getElementById('q-stat-queued').textContent = data.queued || 0;
      if (document.getElementById('q-stat-running')) document.getElementById('q-stat-running').textContent = data.running || 0;
      if (document.getElementById('q-stat-completed')) document.getElementById('q-stat-completed').textContent = data.completed || 0;
      
      const btnPause = document.getElementById('btn-queue-pause');
      const dot = document.getElementById('queue-status-dot');
      if (data.is_paused) {
        if (btnPause) {
          btnPause.innerHTML = '<i class="bi bi-play-fill"></i> Tiếp tục chạy';
          btnPause.className = 'btn btn-primary btn-sm';
        }
        if (dot) dot.className = 'status-dot err';
      } else {
        if (btnPause) {
          btnPause.innerHTML = '<i class="bi bi-pause-fill"></i> Tạm dừng';
          btnPause.className = 'btn btn-secondary btn-sm';
        }
        if (dot) dot.className = (data.running > 0) ? 'status-dot ok' : 'status-dot';
      }
    } catch(e){}
  }
  setInterval(updateQueueStatus, 3000);

  async function toggleQueuePause() {
    const btn = document.getElementById('btn-queue-pause');
    const isCurrentlyPaused = btn && btn.textContent.includes('Tiếp tục');
    const endpoint = isCurrentlyPaused ? '/api/queue/resume' : '/api/queue/pause';
    try {
      const res = await fetch(endpoint, { method: 'POST' });
      const d = await res.json();
      alert(d.message || 'Thành công');
      updateQueueStatus();
    } catch (e) {
      alert('Lỗi: ' + e.message);
    }
  }

  async function clearRenderQueue() {
    if (!confirm('Boss có chắc chắn muốn HỦY TẤT CẢ các video đang chờ trong hàng đợi không?')) return;
    try {
      const res = await fetch('/api/queue/clear', { method: 'POST' });
      const d = await res.json();
      alert(d.message || 'Đã hủy');
      updateQueueStatus();
      loadJobsTable();
    } catch(e) {
      alert('Lỗi: ' + e.message);
    }
  }

  // Assign Token to Page directly from table
  async function assignTokenToPage(pageId, tokenId) {
    try {
      const res = await fetch('/api/pages/assign_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page_id: pageId, token_id: tokenId })
      });
      const d = await res.json();
      if (res.ok && d.success) {
        loadTokensAndPages();
      } else {
        alert(d.error || 'Lỗi gán token');
      }
    } catch(e) {
      alert('Lỗi: ' + e.message);
    }
  }


  // ================= TỰ ĐỘNG CHIA TOKEN CHO FANPAGE (LOHAPAGE MODEL) =================
  // [TDZ fix] globalTokensCatalog moved to top

  function openTokenAllocModal() {
    const m = document.getElementById('modal-token-alloc');
    if (!m) return;
    
    // Nạp số lượng
    const tokCount = (globalTokensCatalog && globalTokensCatalog.length > 0) 
      ? globalTokensCatalog.length 
      : (parseInt(document.getElementById('stat-total-tokens')?.textContent || '0') || 0);
    const pageCount = (cachedPagesList && cachedPagesList.length > 0)
      ? cachedPagesList.length
      : (parseInt(document.getElementById('stat-total-pages')?.textContent || '0') || 0);
      
    document.getElementById('alloc-tokens-count').textContent = tokCount;
    document.getElementById('alloc-pages-count').textContent = pageCount;
    
    const banner = document.getElementById('alloc-status-banner');
    if (banner) banner.style.display = 'none';
    
    toggleAllocMode();
    m.style.display = 'flex';
  }

  function closeTokenAllocModal() {
    const m = document.getElementById('modal-token-alloc');
    if (m) m.style.display = 'none';
  }

  function toggleAllocMode() {
    const mode = document.querySelector('input[name="alloc_mode"]:checked')?.value || 'fixed_ratio';
    const ratioBox = document.getElementById('alloc-ratio-box');
    if (ratioBox) {
      ratioBox.style.display = (mode === 'fixed_ratio') ? 'block' : 'none';
    }
    calculateAllocPreview();
  }

  function calculateAllocPreview() {
    const previewEl = document.getElementById('alloc-preview-text');
    if (!previewEl) return;
    
    const mode = document.querySelector('input[name="alloc_mode"]:checked')?.value || 'fixed_ratio';
    const pagesCount = cachedPagesList.length || parseInt(document.getElementById('alloc-pages-count')?.textContent || '0') || 0;
    const tokensCount = globalTokensCatalog.length || parseInt(document.getElementById('alloc-tokens-count')?.textContent || '0') || 0;
    
    if (tokensCount === 0) {
      previewEl.innerHTML = '<span style="color: #ef4444;"><i class="bi bi-exclamation-triangle"></i> Kho chưa có Token nào! Vui lòng thêm token trước.</span>';
      return;
    }
    
    if (mode === 'fixed_ratio') {
      const perToken = parseInt(document.getElementById('alloc-pages-per-token')?.value || '5', 10) || 5;
      const neededTokens = Math.ceil(pagesCount / perToken);
      let statusColor = '#38bdf8';
      let extraNote = '';
      if (neededTokens > tokensCount) {
        statusColor = '#f59e0b';
        extraNote = ` (⚠️ Bạn có ${tokensCount} tokens, sẽ thiếu ${neededTokens - tokensCount} tokens cho tỷ lệ này. Hệ thống sẽ tự động gán xoay vòng các token khả dụng!)`;
      }
      previewEl.innerHTML = `💡 Với <strong>${pagesCount} Fanpage</strong> và cài đặt <strong>1 Token = ${perToken} Page</strong>:<br>` +
        `• Cần khoảng <strong style="color: ${statusColor};">${neededTokens} Token</strong> quản trị.<br>` +
        `• Khi hoàn tất, mỗi token sẽ đảm nhiệm tối đa ${perToken} page.${extraNote}`;
    } else {
      const avg = (pagesCount / tokensCount).toFixed(1);
      previewEl.innerHTML = `🔄 <strong>Chế độ xoay vòng đều (Round-Robin):</strong><br>` +
        `• Toàn bộ <strong>${pagesCount} Fanpage</strong> sẽ được chia đều lần lượt qua <strong>${tokensCount} Token</strong>.<br>` +
        `• Trung bình mỗi token sẽ phụ trách khoảng <strong>~${avg} Fanpage</strong>, tải trọng phân bổ 100% cân bằng!`;
    }
  }

  async function executeTokenAllocation() {
    const btn = document.getElementById('btn-confirm-alloc');
    const banner = document.getElementById('alloc-status-banner');
    const mode = document.querySelector('input[name="alloc_mode"]:checked')?.value || 'fixed_ratio';
    const scope = document.getElementById('alloc-scope-select')?.value || 'all';
    const perToken = parseInt(document.getElementById('alloc-pages-per-token')?.value || '5', 10) || 5;
    
    // Đảm bảo có token list và pages list
    let tokens = globalTokensCatalog;
    let pages = cachedPagesList;
    if (!tokens || tokens.length === 0 || !pages || pages.length === 0) {
      try {
        const [rT, rP] = await Promise.all([fetch('/api/tokens'), fetch('/api/pages')]);
        const dT = await rT.json();
        const dP = await rP.json();
        tokens = dT.tokens || [];
        pages = dP.pages || [];
        globalTokensCatalog = tokens;
        cachedPagesList = pages;
      } catch (e) {
        alert('Lỗi tải dữ liệu: ' + e.message);
        return;
      }
    }
    
    if (tokens.length === 0) {
      alert('Không tìm thấy token nào trong kho!');
      return;
    }
    
    // Lọc pages cần gán
    let targetPages = pages;
    if (scope === 'unassigned') {
      targetPages = pages.filter(p => !p.token_id);
    }
    
    if (targetPages.length === 0) {
      alert('Không có Fanpage nào cần phân bổ token trong phạm vi đã chọn!');
      return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Đang phân bổ...';
    banner.style.display = 'block';
    banner.style.background = '#1e293b';
    banner.style.color = '#38bdf8';
    banner.innerHTML = `<i class="bi bi-hourglass-split"></i> Đang gán token cho ${targetPages.length} Fanpage...`;
    
    // Thuật toán phân bổ
    // Group target pages theo token_id
    let tokenMap = {}; // token_id -> array of page_ids
    tokens.forEach(t => { tokenMap[t.id] = []; });
    
    if (mode === 'fixed_ratio') {
      // 1 token = perToken pages
      let tokenIdx = 0;
      targetPages.forEach((p, idx) => {
        // Chọn token hiện tại
        const tId = tokens[tokenIdx % tokens.length].id;
        tokenMap[tId].push(p.page_id || p.id);
        if ((idx + 1) % perToken === 0) {
          tokenIdx++;
        }
      });
    } else {
      // Round-robin
      targetPages.forEach((p, idx) => {
        const tId = tokens[idx % tokens.length].id;
        tokenMap[tId].push(p.page_id || p.id);
      });
    }
    
    // Gửi batch_assign_token qua backend
    try {
      let totalAssigned = 0;
      for (const [tId, pIds] of Object.entries(tokenMap)) {
        if (pIds.length > 0) {
          const resp = await fetch('/api/pages/batch_assign_token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token_id: tId, page_ids: pIds })
          });
          const resJson = await resp.json();
          if (resp.ok && resJson.success) {
            totalAssigned += (resJson.count || pIds.length);
          }
        }
      }
      
      banner.style.background = 'rgba(34, 197, 94, 0.2)';
      banner.style.border = '1px solid #22c55e';
      banner.style.color = '#4ade80';
      banner.innerHTML = `<strong><i class="bi bi-check-circle-fill"></i> Thành công!</strong> Đã tự động phân bổ và gán token cho <strong>${totalAssigned} Fanpage</strong> theo cấu hình!`;
      showToast(`Đã phân bổ token thành công cho ${totalAssigned} Fanpage!`);
      
      await loadTokensAndPages();
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check2-circle"></i> Xác nhận Phân bổ Token';
        closeTokenAllocModal();
      }, 1800);
    } catch (e) {
      banner.style.background = 'rgba(239, 68, 68, 0.2)';
      banner.style.border = '1px solid #ef4444';
      banner.style.color = '#f87171';
      banner.innerHTML = `<strong><i class="bi bi-x-circle-fill"></i> Lỗi:</strong> ${e.message}`;
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check2-circle"></i> Thử lại';
    }
  }


  async function openLocalChrome(platform) {
    const statusDiv = document.getElementById('chrome-launch-status');
    if (statusDiv) statusDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Đang khởi chạy Google Chrome với Profile Local của app...';
    try {
      const res = await fetch('/api/system/open_chrome', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform: platform || 'youtube' })
      });
      const data = await res.json();
      if (data.success) {
        if (statusDiv) statusDiv.innerHTML = '<span style="color:#22c55e;"><i class="bi bi-check-circle-fill"></i> ' + (data.message || 'Đã mở cửa sổ Chrome thành công!') + '</span>';
        alert('Đã mở Chrome (Profile Local của App)!\n\nBạn hãy đăng nhập tài khoản trên cửa sổ Chrome vừa xuất hiện. Sau khi đăng nhập xong, có thể đóng Chrome để app tự động dùng cookie fallback.');
      } else {
        if (statusDiv) statusDiv.innerHTML = '<span style="color:#ef4444;"><i class="bi bi-x-circle-fill"></i> Lỗi: ' + (data.error || 'Không thể mở Chrome') + '</span>';
        alert('Lỗi mở Chrome: ' + (data.error || 'Không tìm thấy file chrome.exe'));
      }
    } catch (e) {
      if (statusDiv) statusDiv.innerHTML = '<span style="color:#ef4444;"><i class="bi bi-x-circle-fill"></i> Lỗi kết nối: ' + e.message + '</span>';
      alert('Lỗi kết nối tới máy chủ khi mở Chrome: ' + e.message);
    }
  }
