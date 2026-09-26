with open("D:/Highlight_Video_Studio/web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re

# Tìm section pane-gallery
pane_pattern = re.compile(r'<section\s+id=["\']pane-gallery["\'].*?</section>', re.DOTALL)
m = pane_pattern.search(html)

new_pane = """<section id="pane-gallery" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <div class="panel-title" style="margin-bottom: 0;">
              <span class="pticon"><i class="bi bi-film"></i></span>
              <span>Thư viện Highlight Clips</span>
              <span id="gallery-count-badge" class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 11px; margin-left: 8px;">0 video</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <div class="btn-group" role="group">
                <button type="button" class="btn btn-secondary btn-sm active" id="filter-all-clips" onclick="setClipFilter('all')">Tất cả</button>
                <button type="button" class="btn btn-secondary btn-sm" id="filter-unposted-clips" onclick="setClipFilter('unposted')">Chưa đăng</button>
                <button type="button" class="btn btn-secondary btn-sm" id="filter-posted-clips" onclick="setClipFilter('posted')">Đã đăng</button>
              </div>
              <button class="btn btn-danger btn-sm" onclick="deleteBatchPostedClips()" title="Xóa các clip đã đăng để giải phóng dung lượng">
                <i class="bi bi-trash"></i> Xóa clip đã đăng
              </button>
              <button class="btn btn-secondary btn-sm" onclick="loadClipsGallery()">
                <i class="bi bi-arrow-clockwise"></i> Làm mới
              </button>
            </div>
          </div>
          
          <div id="clips-gallery-container" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
            <div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 40px;">
              <i class="bi bi-film" style="font-size: 3rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
              Đang tải danh sách clips...
            </div>
          </div>
          
          <!-- Phân trang Pagination -->
          <div id="gallery-pagination" style="display: flex; justify-content: center; align-items: center; gap: 12px; margin-top: 20px;"></div>
        </div>
      </section>"""

if m:
    html = html[:m.start()] + new_pane + html[m.end():]
    with open("D:/Highlight_Video_Studio/web/templates/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open("D:/Highlight_Video_Studio/web/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Replaced pane-gallery HTML successfully!")
else:
    print("Not found pane-gallery!")
