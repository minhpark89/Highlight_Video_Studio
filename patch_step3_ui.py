import os, json, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_FILE = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_FILE = BASE_DIR / "web" / "index.html"

print("[3/4] Updating UI in index.html for Purge & Web Article flow...")
with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Thêm nút "Dọn dẹp clip đã dùng (Giải phóng ổ D)" ở thanh công cụ Gallery
gallery_toolbar_target = """<button class="btn btn-danger btn-sm" onclick="deleteBatchPostedClips()" title="Xóa các clip đã đăng để giải phóng dung lượng">
                <i class="bi bi-trash"></i> Xóa clip đã đăng
              </button>"""

new_gallery_toolbar = """<button class="btn btn-danger btn-sm" onclick="purgePostedClips()" title="Xóa vĩnh viễn tất cả video đã đăng/đã phân bổ để giải phóng ổ D và tránh trùng lặp">
                <i class="bi bi-trash3-fill"></i> Dọn sạch clip đã dùng
              </button>"""

if gallery_toolbar_target in html:
    html = html.replace(gallery_toolbar_target, new_gallery_toolbar)
    print("Replaced gallery toolbar button!")
else:
    print("Notice: gallery_toolbar_target not found verbatim, checking alternatives...")

# 2. Thêm function purgePostedClips vào JS
js_addon = """
  // ================= DỌN DẸP Ổ D & TRÁNH TRÙNG LẶP =================
  async function purgePostedClips() {
    if (!confirm('Hành động này sẽ XÓA TOÀN BỘ các file video đã đăng/đã lên lịch khỏi ổ D để giải phóng dung lượng và chống đăng trùng.\\n\\nBạn có chắc chắn muốn dọn sạch không?')) return;
    try {
      const res = await fetch('/api/clips/purge_posted', { method: 'POST' });
      const d = await res.json();
      if (d.success) {
        alert(d.message || `Đã dọn dẹp thành công!`);
        await loadClipsGallery();
      } else {
        alert('Lỗi khi dọn dẹp: ' + (d.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối dọn dẹp ổ D: ' + e.message);
    }
  }

  // ================= LUỒNG TẠO BÀI VIẾT WEB & FIRST COMMENT GÂY TÒ MÒ =================
  async function testCreateWebsiteArticleWithHook(title, summary, videoPath, hookImg) {
    try {
      const payload = {
        title: title || 'Diễn Biến Kịch Tính Không Thể Bỏ Lỡ',
        summary: summary || 'Toàn cảnh sự việc vừa diễn ra gây chấn động cộng đồng mạng.',
        video_path: videoPath || '/api/clips/play/sample.mp4',
        hook_image: hookImg || '',
        dry_run: false
      };
      const res = await fetch('/api/website/publish_draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const d = await res.json();
      if (d.success) {
        return d;
      } else {
        console.error('Lỗi tạo bài viết web:', d.error);
        return null;
      }
    } catch (e) {
      console.error('Lỗi kết nối web CMS:', e);
      return null;
    }
  }
"""

if "function purgePostedClips()" not in html:
    pos = html.find("async function deleteBatchPostedClips()")
    if pos != -1:
        html = html[:pos] + js_addon + "\n\n  " + html[pos:]
        print("Injected purgePostedClips & testCreateWebsiteArticleWithHook into JS!")
    else:
        # Chèn trước thẻ đóng script cuối
        end_script = html.rfind("</script>")
        if end_script != -1:
            html = html[:end_script] + js_addon + "\n" + html[end_script:]
            print("Injected into bottom script block!")

with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_FILE.exists():
    with open(INDEX_ALT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

print("[3/4] UI patch completed!")
