# Full script to rebuild LoHa Page tables for Groups and Tokens, fix sidebar names, and fix groups response parsing
from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Update Sidebar menu item names (clean, no hardcoded counts)
html = re.sub(r'<span>Quản lý \d+ Fanpage</span>', '<span>Quản lý Page</span>', html)
html = re.sub(r'<span>Quản lý Token \(\d+ Token\)</span>', '<span>Quản lý Token</span>', html)
html = html.replace('<span>Quản lý 100 Fanpage</span>', '<span>Quản lý Page</span>')
html = html.replace('<span>Quản lý Token (31 Token)</span>', '<span>Quản lý Token</span>')

# 2. Reformat TAB "Nhóm Trang" (pane-groups) into LoHa Page Table Style (1 row per group)
old_pane_groups = re.search(r'<section id="pane-groups"[^>]*>.*?</section>', html, re.DOTALL)
new_pane_groups = """<section id="pane-groups" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-collection-play-fill" style="color: #ec4899;"></i>
                Quản lý Nhóm Trang
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Cấu hình nhóm Fanpage, thư mục video nguồn, khung giờ và quét lên lịch tự động chuẩn LoHa Page
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
                  <th style="padding: 12px 16px; width: 50px;">#</th>
                  <th style="padding: 12px 16px;">Tên Nhóm</th>
                  <th style="padding: 12px 16px;">Thư mục video nguồn</th>
                  <th style="padding: 12px 16px; width: 120px;">Số Trang</th>
                  <th style="padding: 12px 16px;">Cơ chế đăng</th>
                  <th style="padding: 12px 16px;">Giờ lên lịch & Giãn cách</th>
                  <th style="padding: 12px 16px; text-align: right; width: 260px;">Thao tác</th>
                </tr>
              </thead>
              <tbody id="loha-groups-table-body">
                <tr>
                  <td colspan="7" style="text-align: center; padding: 40px; color: #64748b;">
                    <i class="bi bi-arrow-repeat spin" style="font-size: 24px; display: inline-block;"></i> Đang nạp danh sách nhóm...
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>"""

if old_pane_groups:
    html = html[:old_pane_groups.start()] + new_pane_groups + html[old_pane_groups.end():]
    print("Replaced pane-groups with LoHa Table HTML!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html step 1")
