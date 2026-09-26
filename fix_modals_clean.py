import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1. TÌM VÀ SỬA TRIỆT ĐỂ ẢNH 1:
# Trong openAddGroupModal(): Thay thế hoàn toàn cách render danh sách page trong modal-add-group
# Đảm bảo: Dòng ngang flexbox chuẩn, Checkbox bên trái cùng -> Avatar tròn Facebook CDN -> Tên Page (đậm) + ID -> Badge Nhóm & Trạng thái token bên phải.
old_box_pattern = r'const box = document\.getElementById\([\'"]group-pages-select-box[\'"]\);[\s\S]*?box\.innerHTML = cachedPagesList\.map[\s\S]*?\}\)\.join\([\'"][\'"]\);'

new_box_code = """const box = document.getElementById('group-pages-select-box');
    if (box) {
      if (!cachedPagesList || cachedPagesList.length === 0) {
        box.innerHTML = '<span style="font-size: 12px; color: #64748b; padding: 10px; display: block; text-align: center;">Chưa có Fanpage nào được nạp!</span>';
      } else {
        box.innerHTML = cachedPagesList.map(p => {
          const pName = p.page_name || p.name || 'Fanpage Facebook';
          const pId = String(p.page_id || p.id || 'N/A');
          const avatarUrl = p.avatar || `https://graph.facebook.com/${pId}/picture?type=normal`;
          const initials = pName.trim().substring(0, 2).toUpperCase();
          const colors = ['#2563eb', '#7c3aed', '#db2777', '#059669', '#d97706', '#0284c7'];
          const avatarBg = colors[Math.abs(pName.split('').reduce((a,c)=>a+c.charCodeAt(0), 0)) % colors.length];
          const hasToken = !!(p.page_token || p.has_token);

          return `
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 12px; border-radius: 8px; background: #0f172a; border: 1px solid #1e293b; margin-bottom: 6px;">
              <div style="display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;">
                <input type="checkbox" class="group-page-checkbox" value="${pId}" style="width: 18px; height: 18px; accent-color: #8b5cf6; cursor: pointer; flex-shrink: 0;">
                <div style="width: 36px; height: 36px; border-radius: 50%; overflow: hidden; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1.5px solid #334155;">
                  <img src="${avatarUrl}" alt="${pName}" style="width: 100%; height: 100%; object-fit: cover;" referrerpolicy="no-referrer" onerror="this.onerror=null; this.parentElement.innerHTML='<span style=\\'color:#fff; font-weight:800; font-size:13px;\\'>${initials}</span>';">
                </div>
                <div style="min-width: 0; overflow: hidden;">
                  <div style="font-weight: 700; font-size: 13px; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${pName}">${pName}</div>
                  <div style="font-size: 11px; color: #64748b; font-family: monospace;">ID: ${pId}</div>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
                <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc; font-size: 10.5px; border: 1px solid rgba(192, 132, 252, 0.25);">${p.group_name || 'BM 1'}</span>
                ${hasToken ? '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 10.5px;"><i class="bi bi-shield-check"></i> Vĩnh viễn</span>' : '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 10.5px;">Thiếu token</span>'}
              </div>
            </div>
          `;
        }).join('');
      }
    }"""

# Thay thế bằng regex
text, n_subs = re.subn(old_box_pattern, new_box_code, text, count=1)
print(f"Replaced group-pages-select-box in openAddGroupModal: {n_subs} match")

# 2. TÌM VÀ SỬA TRIỆT ĐỂ ẢNH 2:
# modal-publish-reel bị vỡ layout, lệch khỏi khung nhìn và có nút thừa "Chèn link Web cấu hình"
# Tìm modal có id="modal-publish-reel" và viết lại style chuẩn fixed center, max-height 90vh
p_pub = text.find('id="modal-publish-reel"')
if p_pub != -1:
    p_end = text.find('</form>\n    </div>\n  </div>', p_pub)
    if p_end == -1:
        p_end = text.find('</div>\n    </div>\n  </div>', p_pub)
    
    clean_publish_modal = """id="modal-publish-reel" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 99999; align-items: center; justify-content: center; backdrop-filter: blur(5px); padding: 20px;">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 680px; max-width: 95vw; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.7);">
      <div class="app-modal-header" style="padding: 16px 22px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; flex-shrink: 0;">
        <h3 style="font-size: 16px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 8px; color: #38bdf8;">
          <i class="bi bi-send-check-fill"></i> Xuất bản & Lên lịch Reels (Meta Graph API)
        </h3>
        <button class="app-modal-close" onclick="closePublishModal()" style="background: none; border: none; color: #94a3b8; font-size: 22px; cursor: pointer; line-height: 1;">&times;</button>
      </div>
      <div class="app-modal-body" style="padding: 22px; overflow-y: auto; flex: 1;">
        <!-- Video File info -->
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <i class="bi bi-file-earmark-play-fill" style="color: #38bdf8; font-size: 1.5rem;"></i>
            <div>
              <div id="pub-clip-title" style="font-size: 13.5px; font-weight: 700; color: #f1f5f9;">Clip Highlight</div>
              <div id="pub-clip-filename" style="font-size: 11px; color: #64748b; font-family: monospace;">output_clip.mp4</div>
            </div>
          </div>
          <span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e; font-size: 11px; padding: 4px 8px; border-radius: 4px;">SẴN SÀNG ĐĂNG</span>
        </div>

        <!-- Target Destination (Page hoặc Nhóm) -->
        <div style="margin-bottom: 16px;">
          <label class="form-label" style="font-size: 12px; font-weight: 700; color: #cbd5e1;">1. Chọn Fanpage hoặc Nhóm vệ tinh (LoHa Model):</label>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 8px;">
            <div>
              <label style="font-size: 11px; color: #94a3b8;">Chọn theo Nhóm Page:</label>
              <select id="pub-select-group" class="form-select form-select-sm" style="background: #0f172a; border-color: #334155; font-size: 12.5px;" onchange="onPubGroupChanged()">
                <option value="">-- Chọn nhóm trang vệ tinh --</option>
              </select>
            </div>
            <div>
              <label style="font-size: 11px; color: #94a3b8;">Hoặc chọn Trang đơn lẻ:</label>
              <select id="pub-select-single-page" class="form-select form-select-sm" style="background: #0f172a; border-color: #334155; font-size: 12.5px;">
                <option value="">-- Chọn 1 Fanpage cụ thể --</option>
              </select>
            </div>
          </div>
          <div id="pub-pages-target-summary" style="font-size: 11.5px; color: #38bdf8; background: #070d1e; padding: 8px 12px; border-radius: 6px; border: 1px dashed #1e293b;">
            <i class="bi bi-info-circle"></i> Vui lòng chọn nhóm hoặc 1 Fanpage để tiến hành đăng.
          </div>
        </div>

        <!-- Nội dung status (Caption) -->
        <div style="margin-bottom: 16px;">
          <label class="form-label" style="font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">2. Tiêu đề & Nội dung Facebook Reel:</label>
          <textarea id="pub-caption" class="form-control" rows="3" style="font-size: 12.5px; line-height: 1.4; background: #0f172a; border-color: #334155;" placeholder="Nội dung status đính kèm clip Reel..."></textarea>
        </div>

        <!-- First Comment tự động từ Website bài viết (Không cần nút cấu hình thừa) -->
        <div style="margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <label class="form-label" style="font-size: 12px; font-weight: 700; color: #f59e0b; margin-bottom: 0;">
              <i class="bi bi-chat-left-text-fill"></i> 3. First Comment tự động (Kèm Link website bài viết):
            </label>
            <span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e; font-size: 10.5px;">
              <i class="bi bi-magic"></i> Auto tạo bài web & sinh link
            </span>
          </div>
          <textarea id="pub-first-comment" class="form-control" rows="2" style="font-size: 12px; line-height: 1.4; background: #0f172a; border-color: #334155;" placeholder="Bình luận đầu tiên tạo tò mò kèm link website bài viết full..."></textarea>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Hệ thống tự động post video dài lên web, lấy link bài viết và ảnh hook ghim vào bình luận đầu tiên.</div>
        </div>

        <!-- Chế độ Đăng Ngay hoặc Lên Lịch -->
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; margin-bottom: 10px;">
          <div style="display: flex; gap: 20px; align-items: center; margin-bottom: 12px;">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px; font-weight: 700; color: #cbd5e1;">
              <input type="radio" name="pub_mode" value="schedule" checked onchange="toggleScheduleOptions()" style="accent-color: #ec4899;">
              <i class="bi bi-clock-history text-warning"></i> Hẹn giờ lên lịch (Meta Scheduled)
            </label>
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 13px; font-weight: 700; color: #cbd5e1;">
              <input type="radio" name="pub_mode" value="now" onchange="toggleScheduleOptions()" style="accent-color: #38bdf8;">
              <i class="bi bi-send-fill text-primary"></i> Đăng ngay lập tức
            </label>
          </div>
          <div id="pub-schedule-box" style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 11px; color: #94a3b8; font-weight: 600;">Thời gian bắt đầu đăng:</label>
              <input type="datetime-local" id="pub-schedule-time" class="form-control form-control-sm" style="background: #0b1329; border-color: #334155; font-size: 12px;">
            </div>
            <div>
              <label style="font-size: 11px; color: #94a3b8; font-weight: 600;">Giãn cách giữa các Page (Stagger):</label>
              <select id="pub-stagger-select" class="form-select form-select-sm" style="background: #0b1329; border-color: #334155; font-size: 12px;">
                <option value="5">Giãn cách 5 phút</option>
                <option value="10">Giãn cách 10 phút</option>
                <option value="15" selected>Giãn cách 15 phút (Khuyên dùng)</option>
                <option value="20">Giãn cách 20 phút</option>
              </select>
            </div>
          </div>
        </div>
      </div>
      <div class="app-modal-footer" style="padding: 14px 22px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end; gap: 10px; flex-shrink: 0;">
        <button type="button" class="btn btn-secondary" onclick="closePublishModal()">Hủy bỏ</button>
        <button type="button" class="btn btn-primary" id="btn-execute-publish" onclick="executePublishReel()" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; font-weight: 700; padding: 8px 24px;">
          <i class="bi bi-calendar-check"></i> Xác nhận Lên Lịch (Schedule)
        </button>
      </div>
    </div>
  </div>"""

    if p_end != -1:
        text = text[:p_pub] + clean_publish_modal + text[p_end+len('</div>\n    </div>\n  </div>'):]
        print("Replaced modal-publish-reel with perfectly centered layout and removed redundant web button!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Saved index.html successfully!")
