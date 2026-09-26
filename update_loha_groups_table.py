# Reformat pane-groups and pane-tokens into LoHa Page table style (1 row per item)
from pathlib import Path

index_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = index_path.read_text(encoding="utf-8")

# Let's inspect pane-groups HTML
old_pane_groups = """      <!-- ========================================== -->
      <!-- TAB 1: NHÓM TRANG & LÊN LỊCH TỰ ĐỘNG (LOHA STYLE) -->
      <!-- ========================================== -->
      <section id="pane-groups" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-collection-play-fill" style="color: #ec4899;"></i>
                Nhóm Trang & Phân Bổ Tự Động (1 Video : 1 Page)
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Quét kho video D:\\Highlight_Video_Studio\\output, tự động chia đều độc nhất cho từng Page trong nhóm, không trùng lặp
              </div>
            </div>
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-outline" onclick="loadLoHaGroups()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới nhóm
              </button>
              <button class="btn btn-primary" onclick="openAddGroupModal()">
                <i class="bi bi-plus-circle"></i> + Tạo nhóm mới
              </button>
            </div>
          </div>

          <!-- Danh sách thẻ Nhóm Trang chuẩn LoHa Page -->
          <div id="loha-groups-container" style="display: flex; flex-direction: column; gap: 16px;">
            <!-- Render động bằng loadLoHaGroups() -->
          </div>
        </div>
      </section>"""

new_pane_groups = """      <!-- ========================================== -->
      <!-- TAB 1: NHÓM TRANG (CHUẨN LOHA PAGE - 1 DÒNG 1 NHÓM) -->
      <!-- ========================================== -->
      <section id="pane-groups" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-collection-play-fill" style="color: #ec4899;"></i>
                Quản lý Nhóm Trang
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Cấu hình phân nhóm Fanpage, thư mục video nguồn, khung giờ và lên lịch đăng tự động chuẩn LoHa Page
              </div>
            </div>
            <div style="display: flex; gap: 10px;">
              <button class="btn btn-outline" onclick="loadLoHaGroups()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới
              </button>
              <button class="btn btn-primary" onclick="openAddGroupModal()" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; font-weight: 700;">
                <i class="bi bi-plus-circle"></i> + Tạo nhóm mới
              </button>
            </div>
          </div>

          <!-- Bảng Nhóm Trang theo dòng chuẩn LoHa Page -->
          <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--panel-bg);">
            <table class="table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
              <thead>
                <tr style="background: rgba(15, 23, 42, 0.85); border-bottom: 2px solid var(--border); color: #94a3b8; font-weight: 700;">
                  <th style="padding: 12px 16px; width: 60px;">#</th>
                  <th style="padding: 12px 16px;">Tên Nhóm</th>
                  <th style="padding: 12px 16px;">Thư mục video nguồn</th>
                  <th style="padding: 12px 16px; width: 140px;">Số Trang</th>
                  <th style="padding: 12px 16px;">Cơ chế đăng</th>
                  <th style="padding: 12px 16px;">Giờ lên lịch</th>
                  <th style="padding: 12px 16px; text-align: right; width: 220px;">Thao tác</th>
                </tr>
              </thead>
              <tbody id="loha-groups-table-body">
                <tr>
                  <td colspan="7" style="text-align: center; padding: 40px; color: #64748b;">
                    <i class="bi bi-arrow-repeat spin" style="font-size: 24px; display: inline-block;"></i> Đang tải danh sách nhóm...
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>"""

if old_pane_groups in html:
    html = html.replace(old_pane_groups, new_pane_groups, 1)
    print("Replaced pane-groups with LoHa table style!")
else:
    print("WARNING: old_pane_groups not exact match")

index_path.write_text(html, encoding="utf-8")
