let recoveryOperationTimer = null;

async function submitSelectedRecovery() {
  if (metaFinishBusy) return;
  const postId = currentMetaDiagnosisPost;
  const filename = document.getElementById('meta-replacement-file')?.value;
  const mode = document.getElementById('meta-replacement-mode')?.value || 'app_queue';
  const schedule = document.getElementById('meta-replacement-schedule')?.value || null;
  if (!filename || (mode === 'meta_scheduled' && !schedule)) {
    recoveryFeedback('Chọn MP4 đã kiểm tra và giờ đăng nếu chọn Meta giữ lịch.', true);
    return;
  }
  setRecoveryBusy(true);
  recoveryFeedback('Đang gửi yêu cầu dùng MP4 đã chọn…');
  let accepted = false;
  try {
    const response = await fetch('/api/posts/' + encodeURIComponent(postId) + '/replace-failed-video', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({confirm_replace_failed_video: true, background: false,
        video_id: currentMetaDiagnosis.diagnosis.video_id, filename, mode, schedule_time: schedule})
    });
    const result = await response.json();
    if (!recoveryIsVisible(postId)) return;
    if (!response.ok || !result.success) throw new Error(result.error || 'Chưa nhận được yêu cầu');
    accepted = acceptRecoveryResult(result, postId);
    if (!accepted && result.post_id) trackReplacementPost(result.post_id, postId);
  } catch (error) {
    if (recoveryIsVisible(postId)) recoveryFeedback(error.message, true);
  } finally {
    if (!accepted && recoveryIsVisible(postId)) setRecoveryBusy(false);
  }
}

function recoveryIsVisible(postId) {
  return postId === currentMetaDiagnosisPost
    && document.getElementById('modal-meta-diagnosis')?.style.display !== 'none';
}

function recoveryFeedback(message, error = false) {
  const element = document.getElementById('meta-recovery-result');
  if (!element) return;
  element.textContent = message;
  element.style.color = error ? '#fca5a5' : '#cbd5e1';
}

function setRecoveryBusy(busy) {
  metaFinishBusy = busy;
  for (const id of ['recovery-auto', 'meta-replace-failed', 'recovery-render']) {
    const button = document.getElementById(id);
    const replaced = currentMetaDiagnosis?.diagnosis?.can_replace_failed_video === false;
    if (button) button.disabled = busy || replaced || (id === 'meta-replace-failed'
      && !document.getElementById('meta-replacement-file')?.value);
  }
}

async function recoveryJson(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {signal: controller.signal});
    const result = await response.json();
    if (!response.ok || result.success === false) throw new Error(result.error || 'Không đọc được trạng thái');
    return result;
  } finally {
    clearTimeout(timeout);
  }
}

async function trackRecoveryOperation(postId, operation = null) {
  clearTimeout(recoveryOperationTimer);
  if (!recoveryIsVisible(postId)) return;
  try {
    if (!operation) {
      const data = await recoveryJson('/api/posts/' + encodeURIComponent(postId) + '/recovery-operation');
      operation = data.operation;
    }
    if (!operation || !recoveryIsVisible(postId)) return;
    const pending = ['queued', 'running', 'waiting_worker'].includes(operation.status);
    setRecoveryBusy(pending);
    recoveryFeedback(operation.message, operation.status === 'error');
    if (pending) {
      recoveryOperationTimer = setTimeout(() => trackRecoveryOperation(postId), 1500);
      return;
    }
    const result = operation.result || {};
    if (result.render_started) showRecoveryRenderTask(result.task, postId);
    if (result.post_id) {
      trackReplacementPost(result.post_id, postId);
    }
    loadPostsTable({quiet: true});
  } catch (error) {
    if (!recoveryIsVisible(postId)) return;
    recoveryFeedback('Chưa đọc được tiến độ: ' + error.message + '. Đang kết nối lại.', true);
    recoveryOperationTimer = setTimeout(() => trackRecoveryOperation(postId), 4000);
  }
}

function acceptRecoveryResult(result, postId) {
  if (!result.accepted) return false;
  trackRecoveryOperation(postId, result.operation);
  return true;
}

async function trackReplacementPost(replacementId, originalId) {
  clearTimeout(recoveryOperationTimer);
  if (!recoveryIsVisible(originalId)) return;
  if (currentMetaDiagnosis?.diagnosis) currentMetaDiagnosis.diagnosis.can_replace_failed_video = false;
  setRecoveryBusy(false);
  try {
    const data = await recoveryJson('/api/posts/' + encodeURIComponent(replacementId));
    if (!recoveryIsVisible(originalId)) return;
    const post = data.post;
    const labels = {
      preparing: 'Đang chuẩn bị Content, Website và First Comment.',
      scheduled: 'MP4 và Content đã sẵn sàng; đang chờ lượt đăng.',
      meta_handoff: 'Đang giao lịch cho Meta.',
      publishing: 'Đang gửi video lên Meta.',
      processing: 'Meta đang xử lý video; app đang xác minh kết quả.',
      meta_scheduled: 'Meta đã xác nhận giữ lịch.',
      published: 'Meta đã xác nhận đăng thành công.'
    };
    const reason = post.queue_readiness?.blocked_reason || post.content_package_error || post.error || '';
    const failed = ['failed', 'error'].includes(post.status);
    const message = (failed ? 'Chưa đăng được bài.' : labels[post.status] || post.status)
      + (reason ? '\n' + reason : '');
    recoveryFeedback(message, failed || !!post.queue_readiness?.blocked_reason);
    if (['failed', 'error', 'published', 'meta_scheduled', 'cancelled'].includes(post.status)) {
      loadPostsTable({quiet: true});
      loadDashboard();
      return;
    }
    recoveryOperationTimer = setTimeout(() => trackReplacementPost(replacementId, originalId), 2500);
  } catch (error) {
    if (!recoveryIsVisible(originalId)) return;
    recoveryFeedback('Chưa đọc được kết quả đăng: ' + error.message + '. Đang kết nối lại.', true);
    recoveryOperationTimer = setTimeout(() => trackReplacementPost(replacementId, originalId), 4000);
  }
}
