from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# 1. Update loadPostsTable to render direct Facebook Reel Link
# Let's find where statusBadge is rendered in loadPostsTable
pos_badge = text.find("if (p.status === 'published' || p.status === 'success') {")
print("pos_badge:", pos_badge)

old_badge = """        if (p.status === 'published' || p.status === 'success') {
          statusBadge = '<span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-check-circle"></i> Đã đăng</span>';
        } else if (p.status === 'failed') {"""

new_badge = """        if (p.status === 'published' || p.status === 'success') {
          const reelUrl = p.post_fb_id ? `https://www.facebook.com/reel/${p.post_fb_id}` : (p.fb_url || '');
          statusBadge = `
            <div>
              <span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                <i class="bi bi-check-circle-fill"></i> Đã đăng
              </span>
              ${reelUrl ? `
                <div style="margin-top: 5px;">
                  <a href="${reelUrl}" target="_blank" style="color: #38bdf8; font-size: 11px; text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; background: rgba(56, 189, 248, 0.15); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.35);">
                    <i class="bi bi-box-arrow-up-right"></i> Xem Reel Facebook
                  </a>
                </div>
              ` : ''}
            </div>
          `;
        } else if (p.status === 'failed') {"""

if old_badge in text:
    text = text.replace(old_badge, new_badge)
    print("Updated statusBadge with direct Facebook Reel Link!")
else:
    print("Could not find exact old_badge")

html_tmpl.write_text(text, encoding="utf-8")
