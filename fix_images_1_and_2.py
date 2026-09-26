import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1. FIX ẢNH 1: Khi mở popup "Cấu hình Nhóm Page" (openAddGroupModal),
# danh sách Fanpage phải có ĐẦY ĐỦ: Checkbox bên trái, Avatar tròn thật, Tên trang đậm, ID trang, Nhóm hiện tại, Trạng thái token.
old_group_checkbox_render = """box.innerHTML = cachedPagesList.map(p => `
          <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #cbd5e1; cursor: pointer; padding: 4px 6px; border-radius: 4px; background: rgba(255,255,255,0.02);">
            <input type="checkbox" class="group-page-checkbox" value="${p.page_id || p.id}">
            <span><b>${p.page_name || p.name}</b> <small style="color: #64748b;">(${p.page_id || p.id})</small></span>
          </label>
        `).join('');"""

new_group_checkbox_render = """box.innerHTML = cachedPagesList.map(p => {
          const pName = p.page_name || p.name || 'Fanpage Facebook';
          const pId = p.page_id || p.id || 'N/A';
          const avatarUrl = p.avatar || `https://graph.facebook.com/${pId}/picture?type=normal`;
          const initials = pName.trim().substring(0, 2).toUpperCase();
          const colors = ['#2563eb', '#7c3aed', '#db2777', '#059669', '#d97706', '#0284c7'];
          const avatarBg = colors[Math.abs(pName.split('').reduce((a,c)=>a+c.charCodeAt(0), 0)) % colors.length];
          const hasToken = !!(p.page_token || p.has_token);

          return `
            <label style="display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 12px; color: #cbd5e1; cursor: pointer; padding: 8px 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; margin-bottom: 4px; transition: background 0.15s;">
              <div style="display: flex; align-items: center; gap: 10px; flex: 1; overflow: hidden;">
                <input type="checkbox" class="group-page-checkbox" value="${pId}" style="width: 17px; height: 17px; accent-color: #8b5cf6; cursor: pointer; flex-shrink: 0;">
                <div style="width: 32px; height: 32px; border-radius: 50%; overflow: hidden; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                  <img src="${avatarUrl}" alt="${pName}" style="width: 100%; height: 100%; object-fit: cover;" referrerpolicy="no-referrer" onerror="this.onerror=null; this.parentElement.innerHTML='<span style=\\'color:#fff; font-weight:800; font-size:12px;\\'>${initials}</span>';">
                </div>
                <div style="overflow: hidden;">
                  <div style="font-weight: 700; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${pName}</div>
                  <div style="font-size: 10.5px; color: #64748b; font-family: monospace;">ID: ${pId}</div>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc; font-size: 10px;">${p.group_name || 'BM 1'}</span>
                ${hasToken ? '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 10px;">Vĩnh viễn</span>' : '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 10px;">Thiếu token</span>'}
              </div>
            </label>
          `;
        }).join('');"""

# Thay thế render trong modal add group
if old_group_checkbox_render in text:
    text = text.replace(old_group_checkbox_render, new_group_checkbox_render)
    print("Fixed Image 1: Added Avatars, Names, Badges to Group Selection List!")

# Tăng chiều cao của group-pages-select-box để cuộn rộng rãi
text = text.replace('id="group-pages-select-box" style="max-height: 160px;', 'id="group-pages-select-box" style="max-height: 280px;')

# 2. FIX ẢNH 2: Vùng modal bị che mất nửa trên và phần chèn link web thừa
# Trong modal-publish-reel:
# - Gỡ bỏ nút và hướng dẫn "Chèn link Web cấu hình" (hệ thống đã auto viết bài web + sinh first comment)
# - Đặt modal ở giữa màn hình chuẩn (z-index 99999, display flex, align-items center, justify-content center)
# - Giới hạn max-height 90vh, overflow-y auto để toàn bộ nội dung hiện 100% không bị che

# Tìm modal-publish-reel hoặc modal-content-writer liên quan đến ảnh 2
pos_sec2 = text.find('First Comment tự động (Kèm Link website kéo traffic)')
if pos_sec2 != -1:
    print("Found First Comment block in modal publish reel at:", pos_sec2)
    # Loại bỏ nút thừa "Chèn link Web cấu hình"
    btn_link_web = """<button class="btn btn-outline-secondary btn-sm" style="font-size: 10.5px; padding: 1px 6px;" onclick="insertWebsiteLinkToFirstComment()">
              <i class="bi bi-link-45deg"></i> Chèn link Web cấu hình
            </button>"""
    if btn_link_web in text:
        text = text.replace(btn_link_web, '<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e; font-size: 11px;"><i class="bi bi-magic"></i> Auto sinh từ Website Bài Viết</span>')
        print("Removed redundant 'Chèn link Web' button, replaced with Auto badge!")

# Đảm bảo CSS của modal-publish-reel luôn căn giữa và hiển thị đầy đủ
old_pub_modal_box = '<div id="modal-publish-reel" class="app-modal-overlay" style="display: none;">'
new_pub_modal_box = '<div id="modal-publish-reel" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 99999; align-items: center; justify-content: center; backdrop-filter: blur(5px); overflow-y: auto; padding: 20px;">'
if old_pub_modal_box in text:
    text = text.replace(old_pub_modal_box, new_pub_modal_box)
    print("Fixed modal-publish-reel overlay centering & full visibility!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Step 1 & 2 applied to index.html successfully!")
