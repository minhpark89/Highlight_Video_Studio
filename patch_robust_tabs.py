import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Thay thế toàn bộ đoạn gán click của navigation tabs để độc lập và tự kích hoạt display:block
old_nav_code = """  // Navigation tabs
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
  });"""

new_nav_code = """  // Robust Event Delegation Tab Switcher (Chống xung đột click)
  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.nav-btn[data-pane]');
    if (!btn) return;
    e.preventDefault();
    var paneId = btn.getAttribute('data-pane');
    if (paneId && typeof window.switchTab === 'function') {
      window.switchTab(paneId, btn);
    }
  });"""

if old_nav_code in text:
    text = text.replace(old_nav_code, new_nav_code)
    print("Replaced navigation tab click listeners with robust delegation!")
else:
    print("old_nav_code not found verbatim, checking regex...")
    text = re.sub(r'// Navigation tabs\s+document\.querySelectorAll\([\'"]\.nav-btn\[data-pane\][\'"]\)[\s\S]*?\}\);\s*\}\);', new_nav_code, text, count=1)

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Saved index.html.")
