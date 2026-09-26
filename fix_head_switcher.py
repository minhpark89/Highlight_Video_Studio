import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Đảm bảo switchTab được định nghĩa ở đầu trang trong thẻ <script> riêng biệt
# để không bao giờ bị ảnh hưởng bởi bất kỳ lỗi cú pháp nào ở các hàm bên dưới.
head_tab_script = """<script>
  // Robust Head Switcher: Chạy độc lập, không phụ thuộc script khác
  window.switchTab = function(paneId, btnEl) {
    try {
      console.log('[Tab Direct] Switching to:', paneId);
      document.querySelectorAll('.nav-btn').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.pane').forEach(function(p) {
        p.classList.remove('active');
        p.style.display = 'none';
      });

      if (btnEl) {
        btnEl.classList.add('active');
      } else {
        var mBtn = document.querySelector('.nav-btn[data-pane="' + paneId + '"]');
        if (mBtn) mBtn.classList.add('active');
      }

      var target = document.getElementById(paneId);
      if (target) {
        target.classList.add('active');
        target.style.display = 'block';
      }

      // Lazy loaders
      try {
        if (paneId === 'pane-jobs' && typeof loadJobsTable === 'function') loadJobsTable();
        if (paneId === 'pane-research' && typeof loadSavedResearchVideos === 'function') loadSavedResearchVideos();
        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
        if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();
        if (paneId === 'pane-pages' && typeof loadTokensAndPages === 'function') loadTokensAndPages();
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();
      } catch (err) {
        console.warn('Lazy loader warning:', err);
      }
    } catch (e) {
      console.error('[switchTab error]', e);
    }
  };

  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.nav-btn[data-pane]').forEach(function(btn) {
      btn.onclick = function(e) {
        e.preventDefault();
        var pId = this.getAttribute('data-pane');
        window.switchTab(pId, this);
      };
    });
  });
</script>"""

if "Robust Head Switcher" not in text:
    # Chèn ngay sau thẻ <head> hoặc trước thẻ <div class="app-layout">
    pos_body = text.find("<body")
    pos_body_end = text.find(">", pos_body) + 1
    text = text[:pos_body_end] + "\n" + head_tab_script + "\n" + text[pos_body_end:]
    print("Injected Robust Head Switcher into top of body!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Saved index.html with top-level switcher!")
