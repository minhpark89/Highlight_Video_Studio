(() => {
  let loaded = false;
  window.storageRetentionPayload = () => loaded ? {
    storage_retention: {
      delete_published_reels: document.getElementById('cfg_delete_published_reels').checked,
      delete_completed_sources: document.getElementById('cfg_delete_completed_sources').checked
    }
  } : {};
  async function refresh() {
    const summary = document.getElementById('cfg_storage_summary');
    if (!summary) return;
    try {
      const response = await fetch('/api/storage/status');
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.error || 'Không đọc được trạng thái ổ');
      if (!loaded) {
        for (const key of ['delete_published_reels', 'delete_completed_sources']) {
          const input = document.getElementById('cfg_' + key);
          input.checked = data.settings[key] === true;
          input.disabled = false;
        }
        loaded = true;
      }
      const stats = data.statistics;
      summary.textContent = 'Ổ còn trống ' + (data.free_bytes / 1073741824).toFixed(1) +
        ' GB · Đã dọn ' + stats.published_reels_deleted + ' Reel và ' +
        stats.source_files_deleted + ' file nguồn · Giải phóng ' +
        (stats.freed_bytes / 1073741824).toFixed(2) + ' GB';
    } catch (error) {
      summary.textContent = 'Chưa đọc được trạng thái dọn ổ: ' + error.message;
    }
  }
  document.addEventListener('DOMContentLoaded', () => {
    refresh();
    setInterval(() => {
      if (document.getElementById('pane-settings')?.classList.contains('active')) refresh();
    }, 60000);
  });
})();
