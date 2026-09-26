import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Cập nhật CSS cho container: 1 dòng 1 page (flex-direction: column hoặc 1fr)
old_grid_style = 'id="pages-cards-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px;"'
new_grid_style = 'id="pages-cards-container" style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 30px;"'

if old_grid_style in html:
    html = html.replace(old_grid_style, new_grid_style)
    print("Updated pages-cards-container to 1 row per page!")

# 2. Cập nhật thẻ card: 1 dòng ngang trải dài (full row), tải avatar thật từ URL avatar, không bị che options
old_card_template_marker = 'cardsContainer.innerHTML = pageItems.map(p => {'
# Tìm đoạn render card
start_idx = html.find('cardsContainer.innerHTML = pageItems.map(p => {')
end_idx = html.find('}).join(\'\');', start_idx)

if start_idx != -1 and end_idx != -1:
    new_card_code = """cardsContainer.innerHTML = pageItems.map(p => {
        const pName = p.page_name || p.name || 'Fanpage Facebook';
        const pId = p.page_id || p.id || 'N/A';
        const totalPosts = p.total_posted || 0;
        const hasToken = !!(p.page_token || p.has_token);
        const tokenName = p.token_name || 'System User';
        const grpName = p.group_name || (p.groups && p.groups[0]) || 'BM 1 (Dàn 100 Page)';
        const avatarUrl = p.avatar || `https://graph.facebook.com/${pId}/picture?type=normal`;

        // Avatar tròn: load ảnh thật từ Facebook CDN, nếu lỗi mới fallback sang chữ viết tắt
        const initials = pName.trim().substring(0, 2).toUpperCase();
        const colors = ['#2563eb', '#7c3aed', '#db2777', '#059669', '#d97706', '#0284c7'];
        const avatarBg = colors[Math.abs(pName.split('').reduce((a,c)=>a+c.charCodeAt(0), 0)) % colors.length];

        const tokenBadge = hasToken 
          ? `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 11px; padding: 4px 8px; border: 1px solid rgba(16, 185, 129, 0.3);"><i class="bi bi-shield-check"></i> VĨNH VIỄN</span>`
          : `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 11px; padding: 4px 8px; border: 1px solid rgba(239, 68, 68, 0.3);"><i class="bi bi-shield-x"></i> THIẾU TOKEN</span>`;

        return `
          <div class="page-row-card" style="background: #111c33; border: 1px solid ${hasToken ? '#23304d' : 'rgba(239, 68, 68, 0.4)'}; border-radius: 10px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.25);">
            <!-- Cột 1: Avatar thật + Tên + ID (1 dòng) -->
            <div style="display: flex; align-items: center; gap: 14px; min-width: 280px; flex: 1.2;">
              <div style="width: 44px; height: 44px; border-radius: 50%; overflow: hidden; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 2px solid #1e293b;">
                <img src="${avatarUrl}" alt="${pName}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.onerror=null; this.parentElement.innerHTML='<span style=\\'color:#fff; font-weight:800; font-size:14px;\\'>${initials}</span>';">
              </div>
              <div style="overflow: hidden;">
                <div style="font-weight: 700; font-size: 14px; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${pName}">
                  ${pName}
                </div>
                <div style="font-size: 11.5px; color: #64748b; font-family: monospace; display: flex; align-items: center; gap: 6px; margin-top: 2px;">
                  <span>ID: ${pId}</span>
                  <i class="bi bi-copy" style="cursor: pointer; opacity: 0.7;" onclick="navigator.clipboard.writeText('${pId}')" title="Copy ID"></i>
                </div>
              </div>
            </div>

            <!-- Cột 2: Badges Nhóm + Token + Số bài -->
            <div style="display: flex; align-items: center; gap: 8px; flex: 1.5; justify-content: center; flex-wrap: wrap;">
              <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc; border: 1px solid rgba(192, 132, 252, 0.3); font-size: 11px; padding: 5px 9px;">
                <i class="bi bi-folder2-open"></i> ${grpName}
              </span>
              <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 11px; padding: 5px 9px;">
                <i class="bi bi-key-fill"></i> ${tokenName}
              </span>
              <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); font-size: 11px; padding: 5px 9px;">
                <i class="bi bi-film"></i> ${totalPosts} bài đăng
              </span>
            </div>

            <!-- Cột 3: Trạng thái Token -->
            <div style="flex: 0.6; text-align: center;">
              ${tokenBadge}
            </div>

            <!-- Cột 4: Nút Thao tác (Không bị che, nổi bật ở cuối dòng) -->
            <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
              <a href="https://facebook.com/${pId}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 5px 10px;" title="Mở trang trên Facebook">
                <i class="bi bi-box-arrow-up-right"></i> Xem Page
              </a>
              <button class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 5px 10px;" onclick="openAssignSingleTokenModal('${pId}')" title="Gán hoặc đổi Token cho trang này">
                <i class="bi bi-key"></i> Đổi Token
              </button>
            </div>
          </div>
        `;
      """
    html = html[:start_idx] + new_card_code + html[end_idx:]
    print("Replaced card template with horizontal 1-line-1-page design!")

# Đảm bảo phân trang ở dưới có margin-bottom đủ lớn để không bao giờ bị thanh footer che khuất
html = html.replace('id="pages-pagination" style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 24px;"',
                    'id="pages-pagination" style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 24px; margin-bottom: 50px; padding-bottom: 20px;"')

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("Saved updated index.html successfully!")
