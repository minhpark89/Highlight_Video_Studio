from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-posts top action buttons
pos_posts = html.find('id="pane-posts"')
pos_table = html.find('<table', pos_posts)

# Look for:
# <button class="btn btn-outline" onclick="loadPostsTable()">
#   <i class="bi bi-arrow-clockwise"></i> Làm mới bài đăng
# </button>

old_btn_span = """              <button class="btn btn-danger" onclick="triggerPurgePostedClips()" style="background: #ef4444; color: #fff; font-weight: 700; border: none; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);">
                <i class="bi bi-trash3-fill"></i> Dọn sạch clip đã dùng (Ổ D)
              </button>
              <button class="btn btn-outline" onclick="loadPostsTable()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới bài đăng
              </button>"""

new_btn_span = """              <button class="btn btn-warning" onclick="clearScheduledPosts()" style="background: #f59e0b; color: #0f172a; font-weight: 700; border: none;">
                <i class="bi bi-x-circle-fill"></i> Hủy các bài đang hẹn lịch
              </button>
              <button class="btn btn-outline" onclick="clearAllPosts()" style="color: #ef4444; border-color: #ef4444;" title="Xóa toàn bộ hàng đợi bài đăng">
                <i class="bi bi-trash"></i> Xóa sạch hàng đợi
              </button>
              <button class="btn btn-danger" onclick="triggerPurgePostedClips()" style="background: #ef4444; color: #fff; font-weight: 700; border: none; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);">
                <i class="bi bi-trash3-fill"></i> Dọn sạch clip đã dùng (Ổ D)
              </button>
              <button class="btn btn-outline" onclick="loadPostsTable()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới
              </button>"""

if old_btn_span in html:
    html = html.replace(old_btn_span, new_btn_span, 1)
    print("Replaced pane-posts buttons with Clear Scheduled Posts actions!")
else:
    print("Could not find old_btn_span in pane-posts!")

# Now let's add JavaScript functions: clearScheduledPosts and clearAllPosts
new_js_funcs = """
  async function clearScheduledPosts() {
    if (!confirm('Xác nhận: HỦY TOÀN BỘ các bài viết đang ở trạng thái Đang hẹn lịch?\\n\\nThao tác này sẽ làm sạch danh sách hẹn để bạn chọn nhóm Page và phân bổ lịch lại từ đầu!')) {
      return;
    }
    try {
      const res = await fetch('/api/posts/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'scheduled' })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message || 'Đã hủy toàn bộ bài đang hẹn lịch!');
        loadPostsTable();
      } else {
        alert('Lỗi: ' + (data.message || 'Không thể hủy bài viết.'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }

  async function clearAllPosts() {
    if (!confirm('Cảnh báo: Bạn có chắc chắn muốn XÓA SẠCH toàn bộ danh sách bài đăng không?')) {
      return;
    }
    try {
      const res = await fetch('/api/posts/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'all' })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message || 'Đã làm sạch toàn bộ hàng đợi bài đăng!');
        loadPostsTable();
      } else {
        alert('Lỗi: ' + (data.message || 'Không thể xóa bài viết.'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }
"""

pos_load_posts = html.find('async function loadPostsTable()')
if pos_load_posts != -1 and 'async function clearScheduledPosts()' not in html:
    html = html[:pos_load_posts] + new_js_funcs + "\n" + html[pos_load_posts:]
    print("Added clearScheduledPosts and clearAllPosts JS functions!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html successfully!")
