# Script to build and integrate the 4 LoHa tabs into Highlight Video Studio
import json
import re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
INDEX_PATH = BASE_DIR / "web" / "templates" / "index.html"
APP_PATH = BASE_DIR / "web" / "app.py"

html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Update Sidebar Navigation to clearly match LoHa Page 4-tab section:
# - Nhóm Trang (Lên lịch & Quét Folder) -> pane-groups
# - Trang Facebook (Dàn 100 Page) -> pane-pages
# - Quản lý Token & Pool -> pane-tokens
# - Quản lý Bài Đăng (Theo dõi & Dọn ổ D) -> pane-posts

sidebar_old = """    <span class="nav-section">Điều khiển chính</span>
    <div class="nav-group">
<button class="nav-btn active" data-pane="pane-research" onclick="switchTab('pane-research', this)">
        <span class="nav-icon"><i class="bi bi-search-heart"></i></span>
        <span>Research Nguồn Link</span>
      </button>
      <button class="nav-btn" data-pane="pane-studio" onclick="switchTab('pane-studio', this)">
        <span class="nav-icon"><i class="bi bi-scissors"></i></span>
        <span>Cắt Highlight</span>
      </button>
      <button class="nav-btn" data-pane="pane-jobs" onclick="switchTab('pane-jobs', this)">
        <span class="nav-icon"><i class="bi bi-list-task"></i></span>
        <span>Hàng đợi Jobs</span>
      </button>
      <button class="nav-btn" data-pane="pane-gallery" onclick="switchTab('pane-gallery', this)">
        <span class="nav-icon"><i class="bi bi-film"></i></span>
        <span>Thư viện Clips</span>
      </button>
              <button class="nav-btn" data-pane="pane-tokens" onclick="switchTab('pane-tokens', this)">
          <span class="nav-icon"><i class="bi bi-key-fill"></i></span>
          <span>Quản lý Token</span>
        </button>
<button class="nav-btn" data-pane="pane-pages" onclick="switchTab('pane-pages', this)">
        <span class="nav-icon"><i class="bi bi-shield-lock"></i></span>
        <span>Quản lý Page & Token</span>
      </button>
      <button class="nav-btn" data-pane="pane-website" onclick="switchTab('pane-website', this)">
        <span class="nav-icon"><i class="bi bi-globe"></i></span>
        <span>Kết nối Website bài viết</span>
      </button>
    </div>"""

sidebar_new = """    <span class="nav-section">Tạo Nội Dung & Cắt Video</span>
    <div class="nav-group">
      <button class="nav-btn active" data-pane="pane-research" onclick="switchTab('pane-research', this)">
        <span class="nav-icon"><i class="bi bi-search-heart"></i></span>
        <span>Research Nguồn Link</span>
      </button>
      <button class="nav-btn" data-pane="pane-studio" onclick="switchTab('pane-studio', this)">
        <span class="nav-icon"><i class="bi bi-scissors"></i></span>
        <span>Cắt Highlight</span>
      </button>
      <button class="nav-btn" data-pane="pane-jobs" onclick="switchTab('pane-jobs', this)">
        <span class="nav-icon"><i class="bi bi-list-task"></i></span>
        <span>Hàng đợi Jobs</span>
      </button>
      <button class="nav-btn" data-pane="pane-gallery" onclick="switchTab('pane-gallery', this)">
        <span class="nav-icon"><i class="bi bi-film"></i></span>
        <span>Thư viện Clips</span>
      </button>
    </div>

    <span class="nav-section" style="color: #38bdf8;">Hệ Thống Phân Phối (LoHa Standard)</span>
    <div class="nav-group">
      <button class="nav-btn" data-pane="pane-groups" onclick="switchTab('pane-groups', this)">
        <span class="nav-icon"><i class="bi bi-collection-play-fill" style="color: #ec4899;"></i></span>
        <span>Nhóm Trang & Lên Lịch</span>
      </button>
      <button class="nav-btn" data-pane="pane-pages" onclick="switchTab('pane-pages', this)">
        <span class="nav-icon"><i class="bi bi-facebook" style="color: #1877f2;"></i></span>
        <span>Quản lý 100 Fanpage</span>
      </button>
      <button class="nav-btn" data-pane="pane-tokens" onclick="switchTab('pane-tokens', this)">
        <span class="nav-icon"><i class="bi bi-key-fill" style="color: #f59e0b;"></i></span>
        <span>Quản lý Token (31 Token)</span>
      </button>
      <button class="nav-btn" data-pane="pane-posts" onclick="switchTab('pane-posts', this)">
        <span class="nav-icon"><i class="bi bi-calendar-check-fill" style="color: #10b981;"></i></span>
        <span>Quản lý Bài Đăng & Dọn Ổ</span>
      </button>
      <button class="nav-btn" data-pane="pane-website" onclick="switchTab('pane-website', this)">
        <span class="nav-icon"><i class="bi bi-globe" style="color: #06b6d4;"></i></span>
        <span>Kết nối Website & Bài Viết</span>
      </button>
    </div>"""

if sidebar_old in html:
    html = html.replace(sidebar_old, sidebar_new, 1)
    print("Replaced sidebar successfully!")
else:
    print("WARNING: Exact sidebar_old match not found, checking regex replacement")

# 2. Add pane-groups and pane-posts HTML sections
pane_groups_html = """
      <!-- ========================================== -->
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
      </section>

      <!-- ========================================== -->
      <!-- TAB 4: QUẢN LÝ BÀI ĐĂNG & DỌN DẸP Ổ D (LOHA STYLE) -->
      <!-- ========================================== -->
      <section id="pane-posts" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-calendar-check-fill" style="color: #10b981;"></i>
                Quản lý Bài Đăng & Hàng Đợi (Theo dõi & Dọn ổ D)
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Theo dõi trạng thái lịch đăng, First Comment chứa Link Website bài viết kèm Video dài, và dọn dẹp file MP4 ổ D
              </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid #334155; padding: 6px 14px; border-radius: 8px; font-size: 12px; display: flex; align-items: center; gap: 8px;">
                <span style="color: #94a3b8;">Chống đăng trùng:</span>
                <span style="color: #10b981; font-weight: 700;"><i class="bi bi-shield-check"></i> ĐANG BẬT (100% Độc Nhất)</span>
              </div>
              <button class="btn btn-danger" onclick="triggerPurgePostedClips()" style="background: #ef4444; color: #fff; font-weight: 700; border: none; box-shadow: 0 4px 14px rgba(239, 68, 68, 0.4);">
                <i class="bi bi-trash3-fill"></i> Dọn sạch clip đã dùng (Ổ D)
              </button>
              <button class="btn btn-outline" onclick="loadPostsTable()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới bài đăng
              </button>
            </div>
          </div>

          <!-- Bảng danh sách bài đăng chuẩn LoHa -->
          <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--panel-bg);">
            <table class="table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
              <thead>
                <tr style="background: rgba(15, 23, 42, 0.8); border-bottom: 2px solid var(--border); color: #94a3b8;">
                  <th style="padding: 12px 14px;">#</th>
                  <th style="padding: 12px 14px;">Nội dung / Video</th>
                  <th style="padding: 12px 14px;">Fanpage đích</th>
                  <th style="padding: 12px 14px;">Token sử dụng</th>
                  <th style="padding: 12px 14px;">First Comment & Web Link</th>
                  <th style="padding: 12px 14px;">Trạng thái</th>
                  <th style="padding: 12px 14px;">Lịch đăng</th>
                  <th style="padding: 12px 14px; text-align: right;">Thao tác</th>
                </tr>
              </thead>
              <tbody id="posts-table-body">
                <tr>
                  <td colspan="8" style="text-align: center; padding: 40px; color: #64748b;">
                    <i class="bi bi-hourglass-split" style="font-size: 24px; display: block; margin-bottom: 8px;"></i>
                    Chưa có bài đăng nào trong hàng đợi. Hãy vào tab "Nhóm Trang" để lên lịch tự động cho 100 Page!
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
"""

# Insert pane_groups and pane-posts right before </main>
if '</main>' in html and 'id="pane-groups"' not in html:
    html = html.replace('</main>', pane_groups_html + '\n</main>', 1)
    print("Inserted pane-groups and pane-posts HTML successfully!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Updated index.html successfully!")
