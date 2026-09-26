from pathlib import Path

content = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

old_str = """      let html = '';
      posts.forEach((p, index) => {
        let statusBadge = '';
        if (p.status === 'published' || p.status === 'success') {
          statusBadge = '<span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-check-circle"></i> Đã đăng</span>';
        } else if (p.status === 'failed') {
          statusBadge = '<span style="background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-x-circle"></i> Lỗi</span>';
        } else {
          statusBadge = '<span style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-clock-history"></i> Đang hẹn lịch</span>';
        }"""

new_str = """      let html = '';
      posts.forEach((p, index) => {
        let statusBadge = '';
        if (p.status === 'published' || p.status === 'success') {
          const reelUrl = p.post_fb_id ? `https://www.facebook.com/reel/${p.post_fb_id}` : (p.fb_url || '');
          statusBadge = `
            <div>
              <span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                <i class="bi bi-check-circle-fill"></i> Đã đăng
              </span>
              ${reelUrl ? `
                <div style="margin-top: 5px;">
                  <a href="${reelUrl}" target="_blank" style="color: #38bdf8; font-size: 11px; text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; background: rgba(56, 189, 248, 0.15); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.35);">
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
              <div style="font-size: 11px; color: #f87171; margin-top: 4px;" title="${p.error || ''}">${p.error ? (p.error.length > 25 ? p.error.substring(0, 25) + '...' : p.error) : ''}</div>
            </div>
          `;
        } else {
          statusBadge = '<span style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-clock-history"></i> Đang hẹn lịch</span>';
        }"""

if old_str in content:
    content = content.replace(old_str, new_str, 1)
    Path(r"D:\Highlight_Video_Studio\web\templates\index.html").write_text(content, encoding="utf-8")
    print("Injected Facebook Reel Link into loadPostsTable successfully!")
else:
    print("Could not find exact old_str in templates/index.html")
