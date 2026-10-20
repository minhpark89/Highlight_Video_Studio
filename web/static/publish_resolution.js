/* Recovery controls for interrupted publication and independent Meta checks. */
function mountPublishResolution(body, data) {
  const panel = document.createElement('section');
  panel.id = 'publish-resolution';
  panel.style.cssText = 'margin-top:16px;padding:14px;border:1px solid #475569;border-radius:10px;';
  const result = document.createElement('div');
  result.setAttribute('role', 'status');
  result.style.cssText = 'margin-top:10px;white-space:pre-line;';
  const buttons = [];
  const makeButton = (label, action) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline btn-sm';
    button.style.margin = '6px 8px 6px 0';
    button.textContent = label;
    button.addEventListener('click', action);
    panel.appendChild(button);
    buttons.push(button);
    return button;
  };
  const request = async (payload) => {
    for (const button of buttons) button.disabled = true;
    result.textContent = 'Đang đối soát…';
    try {
      const response = await fetch(`/api/posts/${encodeURIComponent(data.post_id)}/resolve-unknown`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const reply = await response.json();
      if (!response.ok || !reply.success) throw new Error(reply.error || 'Chưa hoàn tất đối soát');
      result.textContent = reply.message;
      if (reply.status) {
        await loadPostsTable({quiet: true});
        await openMetaDiagnosis(data.post_id);
        showToast(reply.message, 'info');
      }
      return reply;
    } catch (error) {
      result.textContent = error.message;
      return null;
    } finally {
      for (const button of buttons) button.disabled = false;
      const retry = panel.querySelector('[data-return-draft]');
      if (retry) retry.disabled = !panel.querySelector('[data-confirm-absent]').checked;
    }
  };
  makeButton('Mở Quản lý Token', () => {
    document.getElementById('modal-meta-diagnosis').style.display = 'none';
    switchTab('pane-tokens');
  });
  const pageLink = document.createElement('a');
  pageLink.href = `https://www.facebook.com/${encodeURIComponent(data.page_id || '')}`;
  pageLink.target = '_blank';
  pageLink.rel = 'noopener';
  pageLink.textContent = 'Mở Page trên Facebook';
  pageLink.style.color = '#38bdf8';
  panel.appendChild(pageLink);
  if (data.diagnosis?.video_id) {
    const summary = document.createElement('p');
    summary.textContent = data.reconcile_error || (data.next_check_at
      ? `App tự kiểm tra. Lượt tiếp theo từ ${new Date(data.next_check_at * 1000).toLocaleString('vi-VN')}.`
      : 'App tự kiểm tra video hiện có và phục hồi khi Meta cho phép.');
    panel.appendChild(summary);
    makeButton('Ưu tiên kiểm tra Meta ngay', async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        const response = await fetch('/api/scheduler/check-meta', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({post_ids: [data.post_id]})
        });
        const reply = await response.json();
        if (!response.ok || !reply.success) throw new Error(reply.error || 'Không gửi được yêu cầu');
        result.textContent = reply.message;
      } catch (error) {
        result.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  }
  if (data.diagnosis?.needs_operator_resolution) {
    const input = document.createElement('input');
    input.className = 'form-control';
    input.id = 'unknown-video-id';
    input.placeholder = 'ID hoặc liên kết video đã đăng trên đúng Page';
    input.setAttribute('aria-label', 'ID hoặc liên kết video đã đăng');
    panel.appendChild(input);
    makeButton('Tìm video trùng nội dung', async () => {
      const reply = await request({action: 'search'});
      if (!reply) return;
      const candidates = reply.candidates || [];
      for (const video of candidates) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline btn-sm';
        button.textContent = `Chọn ${video.video_id} · ${video.created_time || ''}`;
        button.addEventListener('click', () => {
          input.value = video.video_id;
        });
        result.appendChild(document.createElement('br'));
        result.appendChild(button);
      }
      if (!candidates.length) result.textContent += '\nChưa tìm thấy video phù hợp. Kiểm tra trực tiếp Page trước khi quyết định.';
    });
    makeButton('Gắn video và tiếp tục đối soát', () => request({action: 'link_existing', video_id: input.value}));
    const label = document.createElement('label');
    label.style.cssText = 'display:flex;align-items:flex-start;gap:9px;margin-top:12px;line-height:1.6;';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.style.cssText = 'width:16px;height:16px;flex:0 0 16px;margin:4px 0 0;';
    checkbox.dataset.confirmAbsent = 'true';
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(' Tôi đã kiểm tra video, bài đăng và lịch chờ trên đúng Page và xác nhận chưa có bài này. Nếu xác nhận nhầm, lần đăng sau có thể bị trùng.'));
    panel.appendChild(label);
    const retry = makeButton('Chuyển về Draft sau đối soát', () => request({action: 'return_to_draft', confirmed_absent: checkbox.checked}));
    retry.dataset.returnDraft = 'true';
    retry.disabled = true;
    checkbox.addEventListener('change', () => {
      retry.disabled = !checkbox.checked;
    });
  }
  panel.appendChild(result);
  body.appendChild(panel);
}
