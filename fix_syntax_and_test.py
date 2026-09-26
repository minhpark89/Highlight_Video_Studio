import re

path = "D:/Highlight_Video_Studio/web/templates/index.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the broken "async \n // ===" with proper functions
old_broken = """  // ================= WEBSITE ARTICLE CMS CONFIG =================
  async 
  // ================= QUY TẮC LÊN LỊCH & PHÂN BỔ (LOHA CONTROLLER) ================="""

new_fixed = """  // ================= WEBSITE ARTICLE CMS CONFIG =================
  async function loadWebsiteConfig() {
    try {
      const res = await fetch('/api/website-config');
      const data = await res.json();
      if (data.success && data.config) {
        if (document.getElementById('cfg_web_base')) document.getElementById('cfg_web_base').value = data.config.base_url || '';
        if (document.getElementById('cfg_web_user')) document.getElementById('cfg_web_user').value = data.config.username || '';
        if (document.getElementById('cfg_web_pass') && data.config.has_password) {
          document.getElementById('cfg_web_pass').placeholder = '•••••••• (Đã lưu mật khẩu)';
        }
      }
    } catch (e) {
      console.warn('Lỗi loadWebsiteConfig:', e);
    }
  }

  async function saveWebsiteConfig(e) {
    if (e && e.preventDefault) e.preventDefault();
    const base_url = document.getElementById('cfg_web_base')?.value?.trim() || '';
    const username = document.getElementById('cfg_web_user')?.value?.trim() || '';
    const password = document.getElementById('cfg_web_pass')?.value || '';
    try {
      const res = await fetch('/api/website-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_url, username, password })
      });
      const data = await res.json();
      if (data.success) {
        alert('Đã lưu cấu hình Website CMS thành công!');
        loadWebsiteConfig();
      } else {
        alert('Lỗi: ' + (data.error || 'Không thể lưu cấu hình'));
      }
    } catch (err) {
      alert('Lỗi kết nối khi lưu website config: ' + err.message);
    }
  }

  // ================= QUY TẮC LÊN LỊCH & PHÂN BỔ (LOHA CONTROLLER) ================="""

if old_broken in content:
    content = content.replace(old_broken, new_fixed)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: Fixed broken async in templates/index.html")
else:
    # try normalized search
    print("Not found exact string, searching with regex...")
    pattern = r"//\s*={5,}\s*WEBSITE ARTICLE CMS CONFIG\s*={5,}\s*async\s*//\s*={5,}\s*QUY TẮC"
    m = re.search(pattern, content)
    if m:
        content = content[:m.start()] + new_fixed + content[m.end():]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("SUCCESS regex replace in templates/index.html")
    else:
        print("Could not find pattern in templates/index.html!")

# Also check web/index.html just in case
path2 = "D:/Highlight_Video_Studio/web/index.html"
with open(path2, "r", encoding="utf-8") as f:
    c2 = f.read()
if old_broken in c2:
    c2 = c2.replace(old_broken, new_fixed)
    with open(path2, "w", encoding="utf-8") as f:
        f.write(c2)
    print("SUCCESS: Fixed broken async in web/index.html")
