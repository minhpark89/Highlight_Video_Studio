# Add frontend JavaScript for pane-groups and pane-posts in index.html
import re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"

html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Update Head lazy loaders so switchTab automatically loads data for new tabs
old_lazy = """        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
        if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();
        if (paneId === 'pane-pages' && typeof loadTokensAndPages === 'function') loadTokensAndPages();
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();"""

new_lazy = """        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
        if (paneId === 'pane-groups' && typeof loadLoHaGroups === 'function') loadLoHaGroups();
        if (paneId === 'pane-pages' && typeof loadTokensAndPages === 'function') loadTokensAndPages();
        if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();
        if (paneId === 'pane-posts' && typeof loadPostsTable === 'function') loadPostsTable();
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();"""

if old_lazy in html:
    html = html.replace(old_lazy, new_lazy, 1)
    print("Updated head lazy loader successfully!")

# 2. Add client-side functions for loha groups and posts:
# - loadLoHaGroups()
# - runLoHaBatchSchedule(groupId, groupName)
# - loadPostsTable()
# - triggerPurgePostedClips()
# - deletePost(postId)

loha_scripts = """
  // =========================================================================
  // LOHA PAGE PIPELINE: NHÓM TRANG & LÊN LỊCH TỰ ĐỘNG + QUẢN LÝ BÀI ĐĂNG
  // =========================================================================

  async function loadLoHaGroups() {
    const container = document.getElementById('loha-groups-container');
    if (!container) return;
    
    container.innerHTML = `
      <div style="text-align: center; padding: 40px; color: #94a3b8;">
        <i class="bi bi-arrow-repeat spin" style="font-size: 28px; display: inline-block;"></i>
        <div style="margin-top: 8px;">Đang tải danh sách Nhóm Trang & Kho Video...</div>
      </div>
    `;

    try {
      const [resG, resC] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/clips')
      ]);
      const groups = await resG.json();
      const clipsData = await resC.json();
      const clips = clipsData.clips || [];
      const unpostedClips = clips.filter(c => !c.is_posted);

      if (!groups || groups.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; padding: 40px; background: rgba(15,23,42,0.4); border: 1px dashed var(--border); border-radius: var(--radius-md);">
            <i class="bi bi-folder-x" style="font-size: 32px; color: #64748b;"></i>
            <div style="font-size: 15px; font-weight: 700; margin-top: 10px;">Chưa có Nhóm Trang nào</div>
            <div style="color: #94a3b8; font-size: 12px; margin-top: 4px;">Hãy bấm nút "+ Tạo nhóm mới" ở góc trên để tạo nhóm quản lý cho dàn Fanpage.</div>
          </div>
        `;
        return;
      }

      let html = '';
      groups.forEach((g, idx) => {
        const pageCount = (g.page_ids || []).length;
        const availableCount = unpostedClips.length;
        const folder = g.folder_path || 'D:\\\\Highlight_Video_Studio\\\\output';

        html += `
          <div style="background: var(--panel-bg); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 18px 22px; box-shadow: 0 4px 16px rgba(0,0,0,0.25);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 14px;">
              <div>
                <div style="display: flex; align-items: center; gap: 10px;">
                  <span style="background: rgba(236, 72, 153, 0.15); border: 1px solid rgba(236, 72, 153, 0.4); color: #ec4899; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 800;">
                    NHÓM #${idx + 1}
                  </span>
                  <h3 style="margin: 0; font-size: 17px; font-weight: 800; color: #fff;">${g.name}</h3>
                  <span style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;">
                    <i class="bi bi-flag-fill"></i> ${pageCount} Fanpage
                  </span>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #94a3b8; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
                  <span><i class="bi bi-folder-fill" style="color: #f59e0b;"></i> Thư mục nguồn: <code style="background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #cbd5e1;">${folder}</code></span>
                  <span><i class="bi bi-film" style="color: #ec4899;"></i> Video khả dụng trong kho: <strong style="color: #10b981;">${availableCount} clip</strong></span>
                </div>
              </div>
              <div style="display: flex; gap: 8px;">
                <button class="btn btn-outline btn-sm" onclick="editGroupModal('${g.id}')">
                  <i class="bi bi-pencil-square"></i> Đổi tên / Sửa
                </button>
                <button class="btn btn-outline btn-sm" style="color: #ef4444; border-color: rgba(239,68,68,0.3);" onclick="deleteGroup('${g.id}', '${g.name}')">
                  <i class="bi bi-trash"></i> Xóa
                </button>
              </div>
            </div>

            <!-- Khối cấu hình phân bổ tự động chuẩn LoHa -->
            <div style="margin-top: 16px; padding: 14px 18px; background: rgba(15, 23, 42, 0.6); border: 1px solid #1e293b; border-radius: 10px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 14px;">
              <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap;">
                <div>
                  <div style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Cơ chế phân bổ:</div>
                  <div style="font-size: 13px; font-weight: 700; color: #10b981; margin-top: 3px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-check-circle-fill"></i> Mỗi video cho 1 page (Độc nhất 1:1)
                  </div>
                </div>

                <div style="border-left: 1px solid #334155; padding-left: 18px;">
                  <div style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">Giãn cách (Stagger):</div>
                  <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-top: 3px;">
                    15 phút / Page
                  </div>
                </div>

                <div style="border-left: 1px solid #334155; padding-left: 18px;">
                  <div style="font-size: 11px; color: #94a3b8; font-weight: 700; text-transform: uppercase;">First Comment & Web:</div>
                  <div style="font-size: 13px; font-weight: 700; color: #f59e0b; margin-top: 3px; display: flex; align-items: center; gap: 6px;">
                    <i class="bi bi-link-45deg"></i> Tự động kèm Link Web + Video dài
                  </div>
                </div>
              </div>

              <!-- Nút bấm hành động 1-Click Lên Lịch LoHa -->
              <div>
                <button class="btn btn-primary" onclick="runLoHaBatchSchedule('${g.id}', '${g.name}')" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; font-weight: 800; padding: 10px 22px; font-size: 13.5px; box-shadow: 0 4px 18px rgba(236,72,153,0.4);">
                  <i class="bi bi-send-check-fill"></i> 🚀 Quét kho & Lên lịch cho ${pageCount} Page
                </button>
              </div>
            </div>
          </div>
        `;
      });

      container.innerHTML = html;
    } catch (e) {
      console.error(e);
      container.innerHTML = `<div style="color: #ef4444; padding: 20px;">Lỗi tải danh sách nhóm: ${e.message}</div>`;
    }
  }

  async function runLoHaBatchSchedule(groupId, groupName) {
    if (!confirm(`Xác nhận quét kho video (D:\\Highlight_Video_Studio\\output) và phân bổ độc nhất (1 Video : 1 Page) cho nhóm '${groupName}'?`)) {
      return;
    }

    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          stagger_minutes: 15,
          auto_first_comment: true,
          delete_after_schedule: false
        })
      });

      const data = await res.json();
      if (!res.ok) {
        alert('Lỗi: ' + (data.error || 'Không thể phân bổ'));
        return;
      }

      alert(`✅ Thành công!\\n\\n${data.message}\\nTổng số bài đã lên lịch: ${data.scheduled_count} bài!\\n\\nHệ thống sẽ chuyển bạn sang tab 'Quản lý Bài Đăng' để theo dõi.`);
      
      // Chuyển sang tab quản lý bài đăng
      switchTab('pane-posts');
    } catch (err) {
      alert('Lỗi kết nối server: ' + err.message);
    }
  }

  async function loadPostsTable() {
    const tbody = document.getElementById('posts-table-body');
    if (!tbody) return;

    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 30px; color: #94a3b8;">
          <i class="bi bi-arrow-repeat spin" style="font-size: 24px; display: inline-block;"></i>
          <div style="margin-top: 8px;">Đang tải danh sách bài đăng...</div>
        </td>
      </tr>
    `;

    try {
      const res = await fetch('/api/posts');
      const posts = await res.json();

      if (!posts || posts.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align: center; padding: 40px; color: #64748b;">
              <i class="bi bi-inbox" style="font-size: 32px; display: block; margin-bottom: 8px;"></i>
              Chưa có bài đăng nào trong hàng đợi. Vào tab "Nhóm Trang" để lên lịch ngay!
            </td>
          </tr>
        `;
        return;
      }

      let html = '';
      posts.forEach((p, index) => {
        let statusBadge = '';
        if (p.status === 'published' || p.status === 'success') {
          statusBadge = '<span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-check-circle"></i> Đã đăng</span>';
        } else if (p.status === 'failed') {
          statusBadge = '<span style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-x-circle"></i> Lỗi</span>';
        } else {
          statusBadge = '<span style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-clock-history"></i> Đang hẹn lịch</span>';
        }

        const commentSnippet = p.first_comment ? (p.first_comment.length > 50 ? p.first_comment.substring(0, 50) + '...' : p.first_comment) : '<span style="color: #64748b;">(Không có)</span>';

        html += `
          <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
            <td style="padding: 12px 14px; color: #64748b; font-weight: 600;">${index + 1}</td>
            <td style="padding: 12px 14px;">
              <div style="font-weight: 700; color: #f8fafc; font-size: 13.5px;">${p.title || 'Reel Highlight'}</div>
              <div style="font-size: 11.5px; color: #94a3b8; font-family: monospace; margin-top: 2px;"><i class="bi bi-film"></i> ${p.media_file}</div>
            </td>
            <td style="padding: 12px 14px;">
              <div style="font-weight: 700; color: #60a5fa; display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-facebook" style="color: #1877f2;"></i> ${p.page_name || p.page_id}
              </div>
              <div style="font-size: 11px; color: #64748b;">ID: ${p.page_id}</div>
            </td>
            <td style="padding: 12px 14px;">
              <span style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); padding: 2px 8px; border-radius: 6px; font-size: 11.5px; font-weight: 700;">
                <i class="bi bi-key-fill"></i> ${p.token_name || 'System User'}
              </span>
            </td>
            <td style="padding: 12px 14px; max-width: 250px;">
              <div style="font-size: 11.5px; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.first_comment || ''}">
                <i class="bi bi-chat-quote-fill" style="color: #06b6d4;"></i> ${commentSnippet}
              </div>
            </td>
            <td style="padding: 12px 14px;">${statusBadge}</td>
            <td style="padding: 12px 14px; font-size: 12px; color: #e2e8f0; font-family: monospace;">
              <i class="bi bi-calendar3"></i> ${p.scheduled_time || 'Chưa hẹn'}
            </td>
            <td style="padding: 12px 14px; text-align: right;">
              <button class="btn btn-outline btn-sm" onclick="deletePostItem('${p.id}')" style="color: #ef4444; border-color: rgba(239,68,68,0.3); padding: 4px 8px;" title="Xóa khỏi hàng đợi">
                <i class="bi bi-trash"></i>
              </button>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = html;
    } catch (e) {
      console.error(e);
      tbody.innerHTML = `<tr><td colspan="8" style="color: #ef4444; padding: 20px; text-align: center;">Lỗi tải bài đăng: ${e.message}</td></tr>`;
    }
  }

  async function deletePostItem(postId) {
    if (!confirm('Xóa bài đăng này khỏi hàng đợi?')) return;
    try {
      const res = await fetch(`/api/posts/${postId}`, { method: 'DELETE' });
      if (res.ok) {
        loadPostsTable();
      }
    } catch (err) {
      alert('Lỗi: ' + err.message);
    }
  }

  async function triggerPurgePostedClips() {
    if (!confirm('Hành động này sẽ XÓA SẠCH các file MP4 trên ổ D của những video đã được lên lịch/đăng để chống đầy bộ nhớ. Bạn có chắc chắn muốn dọn dẹp?')) {
      return;
    }

    try {
      const res = await fetch('/api/clips/purge_posted', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        const mb = (data.freed_bytes / (1024 * 1024)).toFixed(1);
        alert(`🧹 Đã dọn dẹp thành công!\\n\\nSố file đã xóa: ${data.deleted_count} video\\nDung lượng ổ D giải phóng: ${mb} MB`);
        loadPostsTable();
        if (typeof loadClipsGallery === 'function') loadClipsGallery();
      } else {
        alert('Thông báo: ' + (data.message || 'Không có file cần xóa'));
      }
    } catch (e) {
      alert('Lỗi kết nối: ' + e.message);
    }
  }
"""

# Append loha_scripts to the main script before </script>
pos_script_end = html.rfind('</script>')
if pos_script_end != -1:
    html = html[:pos_script_end] + "\n" + loha_scripts + "\n" + html[pos_script_end:]
    print("Appended loha_scripts successfully!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved updated index.html!")
