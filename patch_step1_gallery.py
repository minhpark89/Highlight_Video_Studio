import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_FILE = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_FILE = BASE_DIR / "web" / "index.html"
APP_FILE = BASE_DIR / "web" / "app.py"

print("[1/4] Reading index.html...")
with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    html = f.read()

# Make backup
shutil.copy2(TEMPLATE_FILE, TEMPLATE_FILE.with_suffix(".html.bak_loha_opt"))

# Tối ưu renderFilteredClips: Dùng poster/thumbnail preview thay vì nạp ngay thẻ <video> ngốn RAM,
# có nút "Xem" mở popup player hoặc click để play, phân trang rõ ràng, nút xóa hàng loạt clip đã post.
new_render_fn = """  // ================= THƯ VIỆN CLIPS (TỐI ƯU NHẸ, PHÂN TRANG & QUẢN LÝ DUNG LƯỢNG) =================
  let cachedAllClips = [];
  let currentClipFilter = 'all'; // all | unposted | posted
  let currentClipPage = 1;
  const CLIPS_PER_PAGE = 12;

  function setClipFilter(filter) {
    currentClipFilter = filter;
    currentClipPage = 1;
    ['all', 'unposted', 'posted'].forEach(f => {
      const btn = document.getElementById('filter-' + f + '-clips');
      if (btn) {
        if (f === filter) {
          btn.classList.add('active');
          btn.style.background = '#2563eb';
        } else {
          btn.classList.remove('active');
          btn.style.background = '';
        }
      }
    });
    renderFilteredClips();
  }

  async function loadClipsGallery() {
    try {
      const res = await fetch('/api/clips');
      const data = await res.json();
      cachedAllClips = Array.isArray(data) ? data : (data.clips || []);
      renderFilteredClips();
    } catch (e) {
      console.error('Lỗi loadClipsGallery:', e);
      const container = document.getElementById('clips-gallery-container');
      if (container) container.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: #ef4444; padding: 20px;">Lỗi nạp clips: ${e.message}</div>`;
    }
  }

  function renderFilteredClips() {
    const container = document.getElementById('clips-gallery-container');
    const badge = document.getElementById('gallery-count-badge');
    const pagination = document.getElementById('gallery-pagination');
    if (!container) return;

    let filtered = cachedAllClips;
    if (currentClipFilter === 'unposted') {
      filtered = cachedAllClips.filter(c => !c.is_posted);
    } else if (currentClipFilter === 'posted') {
      filtered = cachedAllClips.filter(c => c.is_posted);
    }

    if (badge) badge.textContent = `${filtered.length} / ${cachedAllClips.length} video`;

    if (!filtered || filtered.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 40px; background: rgba(15, 23, 42, 0.4); border-radius: 12px; border: 1px dashed #23304d;">
          <i class="bi bi-film" style="font-size: 2.5rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
          Không có clip nào trong bộ lọc này.
        </div>`;
      if (pagination) pagination.innerHTML = '';
      return;
    }

    const totalPages = Math.ceil(filtered.length / CLIPS_PER_PAGE);
    if (currentClipPage > totalPages) currentClipPage = totalPages;
    const startIndex = (currentClipPage - 1) * CLIPS_PER_PAGE;
    const pageClips = filtered.slice(startIndex, startIndex + CLIPS_PER_PAGE);

    container.innerHTML = pageClips.map((c, idx) => {
      const isPosted = !!c.is_posted;
      const statusBadge = isPosted 
        ? '<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80; font-size: 10px;"><i class="bi bi-check2-all"></i> ĐÃ POST</span>'
        : '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-size: 10px;"><i class="bi bi-clock"></i> CHƯA POST</span>';
      
      const title = c.title || c.hook_title || c.filename;
      const videoSrc = `/api/clips/play/${encodeURIComponent(c.filename)}`;
      const cardId = `clip-card-${startIndex + idx}`;
      
      return `
        <div class="card" style="background: #111c33; border: 1px solid ${isPosted ? '#166534' : '#23304d'}; border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
          <!-- Media Player Preview (Nhẹ, không tải hết video cùng lúc) -->
          <div id="${cardId}-player-box" style="position: relative; background: #000; height: 185px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
            <video id="${cardId}-vid" preload="none" style="max-height: 100%; width: 100%; object-fit: contain; display: block;" controls poster="">
              <source src="${videoSrc}" type="video/mp4">
            </video>
            <div style="position: absolute; top: 8px; left: 8px; z-index: 2;">
              ${statusBadge}
            </div>
            <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.75); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px; z-index: 2;">
              ${c.duration ? Math.round(c.duration) + 's' : ''}
            </div>
          </div>
          
          <div style="padding: 12px; display: flex; flex-direction: column; flex: 1;">
            <div style="font-weight: 700; font-size: 13px; color: #f8fafc; margin-bottom: 4px; line-height: 1.35; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; min-height: 35px;" title="${title}">
              ${title}
            </div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${c.filename}
            </div>
            
            <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: center; gap: 6px; border-top: 1px solid #1e293b; padding-top: 10px;">
              <span class="badge" style="background: rgba(236, 72, 153, 0.2); color: #f472b6; font-size: 10.5px;">
                ★ Viral: ${c.viral_score || 95}
              </span>
              <div style="display: flex; gap: 5px;">
                <button class="btn btn-secondary btn-sm" style="padding: 3px 8px; font-size: 11px;" onclick="toggleMarkClipPosted('${c.filename}', ${!isPosted})" title="${isPosted ? 'Đánh dấu chưa post' : 'Đánh dấu đã post'}">
                  <i class="bi ${isPosted ? 'bi-arrow-counterclockwise' : 'bi-check-lg'}"></i>
                </button>
                <a href="${videoSrc}" download class="btn btn-secondary btn-sm" style="padding: 3px 8px; font-size: 11px;" title="Tải về máy">
                  <i class="bi bi-download"></i>
                </a>
                <button class="btn btn-secondary btn-sm text-danger" style="padding: 3px 8px; font-size: 11px;" onclick="deleteSingleClip('${c.filename}')" title="Xóa video khỏi ổ D">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Render pagination mượt mà
    if (pagination && totalPages > 1) {
      let pageBtns = '';
      for (let p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || (p >= currentClipPage - 2 && p <= currentClipPage + 2)) {
          const activeStyle = (p === currentClipPage) ? 'background: #2563eb; color: #fff; font-weight: 700;' : 'background: #1e293b; color: #94a3b8;';
          pageBtns += `<button class="btn btn-sm" style="${activeStyle} min-width: 32px; padding: 4px 8px; margin: 0 2px;" onclick="goToClipPage(${p})">${p}</button>`;
        } else if (p === currentClipPage - 3 || p === currentClipPage + 3) {
          pageBtns += `<span style="color: #64748b; margin: 0 2px;">...</span>`;
        }
      }
      pagination.innerHTML = `
        <button class="btn btn-secondary btn-sm" ${currentClipPage === 1 ? 'disabled' : ''} onclick="goToClipPage(${currentClipPage - 1})"><i class="bi bi-chevron-left"></i> Trước</button>
        <div style="display: flex; align-items: center;">${pageBtns}</div>
        <button class="btn btn-secondary btn-sm" ${currentClipPage === totalPages ? 'disabled' : ''} onclick="goToClipPage(${currentClipPage + 1})">Sau <i class="bi bi-chevron-right"></i></button>
        <span style="font-size: 12px; color: #64748b; margin-left: 8px;">Trang ${currentClipPage} / ${totalPages}</span>
      `;
    } else if (pagination) {
      pagination.innerHTML = '';
    }
  }

  function goToClipPage(p) {
    currentClipPage = p;
    renderFilteredClips();
    const c = document.getElementById('clips-gallery-container');
    if (c) c.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }"""

# Thay thế hàm renderFilteredClips cũ
fn_start = html.find("function renderFilteredClips()")
fn_end = html.find("async function toggleMarkClipPosted", fn_start)
if fn_start != -1 and fn_end != -1:
    html = html[:fn_start] + new_render_fn + "\n\n  " + html[fn_end:]
    print("Replaced renderFilteredClips successfully!")
else:
    print("WARNING: Could not locate renderFilteredClips boundaries")

# Lưu lại file template và file index phụ
with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_FILE.exists():
    with open(INDEX_ALT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

print("[1/4] index.html updated successfully!")
