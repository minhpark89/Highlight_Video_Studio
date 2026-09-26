from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect where statusBadge is created in loadPostsTable:
pos = text.find("async function loadPostsTable")
pos_end = text.find("tbody.innerHTML = html;", pos)
if pos_end == -1: pos_end = text.find("tbody.innerHTML = rows;", pos)

old_badge_chunk = """        let statusBadge = '';
        if (p.status === 'published' || p.status === 'success') {
          statusBadge = '<span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-check-circle"></i> Đã đăng</span>';
        } else if (p.status === 'failed') {
          statusBadge = '<span style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-x-circle"></i> Lỗi</span>';
        } else {
          statusBadge = '<span style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-clock-history"></i> Đang hẹn lịch</span>';
        }"""

new_badge_chunk = """        let statusBadge = '';
        if (p.status === 'published' || p.status === 'success') {
          statusBadge = `
            <div>
              <span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                <i class="bi bi-check-circle-fill"></i> Đã đăng
              </span>
              ${p.post_fb_id ? `
                <div style="margin-top: 6px;">
                  <a href="https://www.facebook.com/reel/${p.post_fb_id}" target="_blank" style="color: #38bdf8; font-size: 11px; text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; background: rgba(56, 189, 248, 0.15); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.35);">
                    <i class="bi bi-box-arrow-up-right"></i> Xem Reel Facebook
                  </a>
                </div>
              ` : ''}
            </div>
          `;
        } else if (p.status === 'failed') {
          statusBadge = `
            <div>
              <span style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-x-circle-fill"></i> Lỗi</span>
              <div style="font-size: 11px; color: #f87171; margin-top: 4px;" title="${p.error || ''}">${p.error ? (p.error.length > 30 ? p.error.substring(0, 30) + '...' : p.error) : ''}</div>
            </div>
          `;
        } else {
          statusBadge = '<span style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-clock-history"></i> Đang hẹn lịch</span>';
        }"""

if old_badge_chunk in text:
    text = text.replace(old_badge_chunk, new_badge_chunk)
    print("Replaced statusBadge successfully in templates/index.html!")
else:
    print("Could not find exact old_badge_chunk, checking...")

html_tmpl.write_text(text, encoding="utf-8")
