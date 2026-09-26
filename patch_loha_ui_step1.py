import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

print("[1/3] Reading index.html...")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Backup
shutil.copy2(TEMPLATE_PATH, TEMPLATE_PATH.with_suffix(".html.bak_before_loha_ui"))

# GIAO DIỆN CHUẨN LOHAPAGE CHO PANE-PAGES:
# 1. Header thống kê & các nút thao tác chính
# 2. Bộ lọc (Tìm kiếm, Chọn nhóm page, Trạng thái token, Chế độ xem Thẻ Card / Bảng)
# 3. Danh sách Fanpage dạng THẺ NGANG (Avatar tròn viết tắt, Tên page, ID, Badge số bài, Token gán, Trạng thái Hoạt động)
# 4. Modal Popup Quy tắc Lên lịch LoHa (Khung giờ slot vàng, Stagger/Jitter lệch phút, Thư mục nguồn video, Tự động First Comment web)
loha_pane_pages_html = """      <!-- PANE: QUẢN LÝ PAGE & LÊN LỊCH THEO CHUẨN LOHAPAGE -->
      <section id="pane-pages" class="pane">
        <div class="panel">
          <!-- Header chính -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-facebook" style="color: #1877f2;"></i>
                Quản lý Trang Facebook & Lên lịch (LoHa Style)
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Hệ thống thẻ card vệ tinh, phân bổ 1 Video : 1 Page, xoay vòng Token System User & Hẹn giờ thông minh
              </div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <button class="btn btn-secondary" onclick="loadTokensAndPages()"><i class="bi bi-arrow-repeat"></i> Làm mới</button>
              <button class="btn btn-primary" onclick="openAddTokenModal()"><i class="bi bi-key-fill"></i> Nạp Token</button>
              <button class="btn btn-primary" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border:none;" onclick="openAddGroupModal()"><i class="bi bi-folder-plus"></i> Tạo Nhóm</button>
              <button class="btn btn-warning" onclick="openScheduleRulesModal()" style="font-weight: 700; color: #0f172a;"><i class="bi bi-sliders2-vertical"></i> Quy tắc Lên lịch</button>
              <button class="btn btn-success" onclick="openDistributeModal()" style="font-weight: 700;"><i class="bi bi-send-check-fill"></i> 1-Click Phân bổ</button>
            </div>
          </div>

          <!-- Thống kê Header Badges theo LoHa -->
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 20px;">
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Tổng Fanpage</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="stat-total-pages" style="font-size: 24px; font-weight: 800; color: #38bdf8;">0</span>
                <span style="font-size: 11px; color: #64748b;">trang vệ tinh</span>
              </div>
            </div>
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Kho Token Vĩnh Viễn</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="stat-total-tokens" style="font-size: 24px; font-weight: 800; color: #f59e0b;">0</span>
                <span style="font-size: 11px; color: #10b981;">SYS User</span>
              </div>
            </div>
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Nhóm Trang Phân Bổ</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="stat-total-groups" style="font-size: 24px; font-weight: 800; color: #c084fc;">0</span>
                <span style="font-size: 11px; color: #64748b;">nhóm chủ đề</span>
              </div>
            </div>
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Bài Đăng / Lên lịch</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="stat-total-published" style="font-size: 24px; font-weight: 800; color: #22c55e;">0</span>
                <span style="font-size: 11px; color: #64748b;">Reels + First Comment</span>
              </div>
            </div>
          </div>

          <!-- Banner Quy tắc Lên lịch hiện hành -->
          <div class="card" style="background: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-radius: 10px; padding: 12px 18px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <span class="badge" style="background: rgba(37, 99, 235, 0.2); color: #60a5fa; font-weight: 700; font-size: 11.5px; padding: 6px 10px;"><i class="bi bi-clock-history"></i> QUY TẮC HIỆN HÀNH</span>
              <div style="font-size: 12.5px; color: #e2e8f0;">
                Khung giờ vàng: <strong id="rule-display-slots" style="color: #38bdf8;">08:00, 11:30, 17:30, 20:30</strong> · Giãn cách (Stagger): <strong id="rule-display-stagger" style="color: #f59e0b;">15 phút</strong> · Chế độ: <strong style="color: #34d399;">1 Video : 1 Page</strong>
              </div>
            </div>
            <button class="btn btn-sm btn-secondary" onclick="openScheduleRulesModal()"><i class="bi bi-pencil-square"></i> Cấu hình</button>
          </div>

          <!-- Thanh tìm kiếm & Bộ lọc LoHa -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; gap: 10px; align-items: center; flex: 1; min-width: 320px;">
              <div style="position: relative; flex: 1;">
                <input type="text" id="page-search-input" class="form-control form-control-sm" placeholder="Tìm theo tên trang hoặc dán Page ID..." oninput="filterPagesList()" style="background: #0b1329; border-color: #23304d; padding-left: 32px; font-size: 13px;">
                <i class="bi bi-search" style="position: absolute; left: 10px; top: 7px; color: #64748b;"></i>
              </div>
              <select id="page-filter-group" class="form-select form-select-sm" onchange="filterPagesList()" style="width: 180px; background: #0b1329; border-color: #23304d; font-size: 12.5px;">
                <option value="all">Tất cả nhóm</option>
              </select>
              <select id="page-filter-status" class="form-select form-select-sm" onchange="filterPagesList()" style="width: 150px; background: #0b1329; border-color: #23304d; font-size: 12.5px;">
                <option value="all">Tất cả trạng thái</option>
                <option value="active">Đang hoạt động</option>
                <option value="notoken">Chưa có Token</option>
              </select>
            </div>
            <div style="display: flex; gap: 6px; align-items: center;">
              <span id="page-filtered-count-badge" class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 11px;">130 trang</span>
              <div class="btn-group" role="group">
                <button type="button" class="btn btn-secondary btn-sm active" id="view-mode-card" onclick="setPageViewMode('card')" title="Xem dạng thẻ LoHa"><i class="bi bi-grid-fill"></i> Thẻ Card</button>
                <button type="button" class="btn btn-secondary btn-sm" id="view-mode-table" onclick="setPageViewMode('table')" title="Xem dạng bảng Excel"><i class="bi bi-table"></i> Bảng</button>
              </div>
            </div>
          </div>

          <!-- Khu vực hiển thị danh sách Pages dạng Thẻ Card Ngang (LoHa Style) -->
          <div id="pages-cards-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px;">
            <div style="grid-column: 1 / -1; text-align: center; color: #64748b; padding: 40px;">
              <span class="spinner-border spinner-border-sm text-primary"></span> Đang nạp danh sách Fanpage Facebook...
            </div>
          </div>

          <!-- Bảng dự phòng cho chế độ Table -->
          <div id="pages-table-wrapper" style="display: none; background: #111c33; border: 1px solid #23304d; border-radius: 10px; overflow: hidden; margin-top: 10px;">
            <div class="table-responsive">
              <table class="table" style="margin-bottom: 0;">
                <thead>
                  <tr>
                    <th>Fanpage</th>
                    <th>ID Trang</th>
                    <th>Token Phụ Trách</th>
                    <th>Nhóm</th>
                    <th>Bài Đã Đăng</th>
                    <th>Trạng Thái</th>
                    <th style="text-align: right;">Thao tác</th>
                  </tr>
                </thead>
                <tbody id="pages-tbody"></tbody>
              </table>
            </div>
          </div>

          <!-- Phân trang Pages -->
          <div id="pages-pagination" style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 24px;"></div>
        </div>
      </section>"""

# Tìm và thay thế khối section pane-pages cũ
m_pane = re.search(r'(<section[^>]*id=["\']pane-pages["\'][\s\S]*?</section>)', html)
if m_pane:
    html = html[:m_pane.start()] + loha_pane_pages_html + html[m_pane.end():]
    print("Replaced pane-pages with LoHa Style Cards & Toolbar successfully!")
else:
    print("WARNING: Could not find section pane-pages in index.html")

# 2. POPUP QUY TẮC LÊN LỊCH & PHÂN BỔ CHUẨN LOHAPAGE (MODAL)
loha_schedule_modal_html = """
  <!-- MODAL: QUY TẮC LÊN LỊCH & ĐĂNG BÀI (CHUẨN LOHAPAGE) -->
  <div id="modal-schedule-rules" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 620px; max-width: 95vw; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div class="app-modal-header" style="padding: 16px 20px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 16px; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <i class="bi bi-calendar2-range-fill" style="color: #f59e0b;"></i>
          Cấu hình Quy tắc Lên lịch LoHa Page
        </div>
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeScheduleRulesModal()"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="app-modal-body" style="padding: 20px; max-height: 80vh; overflow-y: auto;">
        
        <!-- Khung giờ đăng cố định (Slots) -->
        <div style="margin-bottom: 18px;">
          <label style="font-size: 12.5px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            1. Khung giờ đăng cố định trong ngày (Golden Hours):
          </label>
          <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <input type="text" id="loha-slot-input" class="form-control form-control-sm" placeholder="08:00, 11:30, 17:30, 20:30" value="08:00, 11:30, 17:30, 20:30" style="background: #0b1329; border-color: #23304d; font-family: monospace;">
          </div>
          <div style="font-size: 11px; color: #64748b;">Nhập các khung giờ cách nhau bởi dấu phẩy (Ví dụ: 08:00, 11:30, 17:30, 20:30).</div>
        </div>

        <!-- Độ giãn cách (Stagger / Jitter) -->
        <div style="margin-bottom: 18px;">
          <label style="font-size: 12.5px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            2. Độ giãn cách ngẫu nhiên giữa các Fanpage (Stagger / Jitter):
          </label>
          <select id="loha-stagger-select" class="form-select form-select-sm" style="background: #0b1329; border-color: #23304d;">
            <option value="5">Giãn cách 5 phút (Tối ưu cho dàn 5-10 page)</option>
            <option value="10">Giãn cách 10 phút</option>
            <option value="15" selected>Giãn cách 15 phút (Khuyên dùng - Chống checkpoint Meta)</option>
            <option value="20">Giãn cách 20 phút</option>
            <option value="30">Giãn cách 30 phút</option>
          </select>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Tự động làm lệch giờ giữa các page trong cùng 1 nhóm để bảo vệ tài khoản.</div>
        </div>

        <!-- Chế độ phân bổ -->
        <div style="margin-bottom: 18px;">
          <label style="font-size: 12.5px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            3. Chế độ phân bổ nội dung video:
          </label>
          <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #6ee7b7;">
            <i class="bi bi-check-circle-fill"></i> <strong>1 Video : 1 Page độc nhất:</strong> Mỗi Fanpage nhận 1 video riêng biệt, không trùng lặp nội dung.
          </div>
        </div>

        <!-- Thư mục nguồn video -->
        <div style="margin-bottom: 18px;">
          <label style="font-size: 12.5px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            4. Thư mục nguồn Video (Folder Binding):
          </label>
          <input type="text" id="loha-folder-source" class="form-control form-control-sm" value="D:\\Highlight_Video_Studio\\output" readonly style="background: #0b1329; border-color: #23304d; font-family: monospace; color: #94a3b8;">
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Tự động lấy kho 288+ clip đã render hoàn chỉnh từ studio.</div>
        </div>

        <!-- Tự động First Comment kèm link Web -->
        <div style="margin-bottom: 14px;">
          <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;">
            <input type="checkbox" id="loha-auto-first-comment" checked style="width: 16px; height: 16px; accent-color: #2563eb;">
            <span style="font-size: 12.5px; font-weight: 700; color: #cbd5e1;">Tự động chèn First Comment kèm link bài viết Web (Video dài không link ngoài)</span>
          </label>
          <div style="font-size: 11px; color: #64748b; margin-left: 24px;">Kéo tương tác & traffic về website bài viết chính thức.</div>
        </div>

      </div>
      <div style="padding: 14px 20px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end; gap: 8px;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeScheduleRulesModal()">Đóng</button>
        <button type="button" class="btn btn-primary btn-sm" onclick="saveLoHaScheduleRules()"><i class="bi bi-save"></i> Lưu Quy Tắc</button>
      </div>
    </div>
  </div>

  <!-- MODAL: 1-CLICK PHÂN BỔ NHÓM PAGE (CHUẨN LOHAPAGE) -->
  <div id="modal-distribute-loha" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 560px; max-width: 95vw; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div class="app-modal-header" style="padding: 16px 20px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 16px; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <i class="bi bi-send-check-fill" style="color: #22c55e;"></i>
          1-Click Phân Bổ Kho Video & Lên Lịch
        </div>
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeDistributeModal()"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="app-modal-body" style="padding: 20px;">
        <div style="margin-bottom: 16px;">
          <label style="font-size: 12px; font-weight: 700; color: #94a3b8;">1. Chọn Nhóm Fanpage vệ tinh:</label>
          <select id="modal-dist-group" class="form-select form-select-sm" style="background: #0b1329; border-color: #23304d;"></select>
        </div>
        <div style="margin-bottom: 16px;">
          <label style="font-size: 12px; font-weight: 700; color: #94a3b8;">2. Thời gian bắt đầu lên lịch:</label>
          <input type="datetime-local" id="modal-dist-starttime" class="form-control form-control-sm" style="background: #0b1329; border-color: #23304d;">
        </div>
        <div style="margin-bottom: 16px;">
          <label style="font-size: 12px; font-weight: 700; color: #94a3b8;">3. Giãn cách giữa các Page:</label>
          <select id="modal-dist-stagger" class="form-select form-select-sm" style="background: #0b1329; border-color: #23304d;">
            <option value="5">Giãn cách 5 phút</option>
            <option value="10">Giãn cách 10 phút</option>
            <option value="15" selected>Giãn cách 15 phút (Khuyên dùng)</option>
            <option value="20">Giãn cách 20 phút</option>
          </select>
        </div>
        <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 12px; font-size: 12px; color: #7dd3fc;">
          <i class="bi bi-info-circle-fill"></i> Hệ thống sẽ tự động quét kho clip <strong>chưa đăng</strong>, bốc mỗi page đúng 1 video độc nhất (1:1) và lên lịch kèm link web First Comment.
        </div>
      </div>
      <div style="padding: 14px 20px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end; gap: 8px;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeDistributeModal()">Hủy</button>
        <button type="button" class="btn btn-success btn-sm" id="btn-submit-distribute" onclick="executeBatchDistribute()"><i class="bi bi-lightning-charge-fill"></i> Bắt đầu Lên Lịch</button>
      </div>
    </div>
  </div>
"""

# Chèn modal mới nếu chưa có
if "id=\"modal-distribute-loha\"" not in html:
    # thay thế modal-schedule-rules cũ
    m_rules = re.search(r'(<div[^>]*id=["\']modal-schedule-rules["\'][\s\S]*?</div>\s*</div>\s*</div>)', html)
    if m_rules:
        html = html[:m_rules.start()] + loha_schedule_modal_html + html[m_rules.end():]
        print("Replaced modal-schedule-rules with LoHa style modals successfully!")
    else:
        # Chèn trước thẻ đóng body
        pos_body = html.rfind("</body>")
        if pos_body != -1:
            html = html[:pos_body] + loha_schedule_modal_html + "\n" + html[pos_body:]
            print("Appended LoHa modals before </body>!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("[1/3] HTML markup updated successfully!")
