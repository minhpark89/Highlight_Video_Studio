with open("D:/Highlight_Video_Studio/web/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Gallery HTML Pane
old_gallery_pane = """      <!-- PANE 3: THƯ VIỆN CLIPS -->
      <section id="pane-gallery" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div class="panel-title" style="margin-bottom: 0;">
              <span class="pticon"><i class="bi bi-film"></i></span>
              <span>Thư viện Highlight Clips (Đã render hoàn tất)</span>
            </div>
            <button class="btn btn-secondary btn-sm" onclick="loadClipsGallery()">
              <i class="bi bi-arrow-clockwise"></i> Làm mới
            </button>
          </div>
          <div class="row" id="clips-gallery-container">
            <div class="col-12" style="text-align: center; color: var(--text-dim); padding: 40px;">
              <i class="bi bi-film" style="font-size: 3rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
              Chưa có clip highlight nào được render hoàn thành. Hãy tạo job mới ở tab "Cắt Highlight"!
            </div>
          </div>
        </div>
      </section>"""

new_gallery_pane = """      <!-- PANE 3: THƯ VIỆN CLIPS -->
      <section id="pane-gallery" class="pane">
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

if old_gallery_pane in html:
    html = html.replace(old_gallery_pane, new_gallery_pane)
    print("Replaced Gallery HTML Pane successfully!")
else:
    print("WARNING: Could not find exact old_gallery_pane")

# 2. Update loadClipsGallery JS function
old_fn_start = html.find("async function loadClipsGallery()")
if old_fn_start == -1:
    old_fn_start = html.find("function loadClipsGallery()")
old_fn_end = html.find("async function deleteJob(id)", old_fn_start)

new_gallery_js = """  // ================= THƯ VIỆN CLIPS (PAGINATION, FILTER, POSTED & DELETE) =================
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

    container.innerHTML = pageClips.map(c => {
      const isPosted = !!c.is_posted;
      const statusBadge = isPosted 
        ? '<span class="badge" style="background: rgba(34, 197, 94, 0.2); color: #4ade80; font-size: 10px;"><i class="bi bi-check2-all"></i> ĐÃ POST</span>'
        : '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-size: 10px;"><i class="bi bi-clock"></i> CHƯA POST</span>';
      
      const title = c.title || c.hook_title || c.filename;
      return `
        <div class="card" style="background: #111c33; border: 1px solid ${isPosted ? '#166534' : '#23304d'}; border-radius: 10px; overflow: hidden; display: flex; flex-direction: column;">
          <div style="position: relative; background: #000; height: 180px; display: flex; align-items: center; justify-content: center;">
            <video preload="metadata" style="max-height: 100%; width: 100%; object-fit: contain;" controls>
              <source src="/api/clips/play/${encodeURIComponent(c.filename)}" type="video/mp4">
            </video>
            <div style="position: absolute; top: 8px; left: 8px;">
              ${statusBadge}
            </div>
            <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 10px;">
              ${c.duration ? Math.round(c.duration) + 's' : ''}
            </div>
          </div>
          <div style="padding: 12px; display: flex; flex-direction: column; flex: 1;">
            <div style="font-weight: 700; font-size: 13px; color: #f8fafc; margin-bottom: 4px; line-height: 1.3; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;" title="${title}">
              ${title}
            </div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${c.filename}
            </div>
            <div style="margin-top: auto; display: flex; justify-content: space-between; align-items: center; gap: 6px; border-top: 1px solid #1e293b; padding-top: 10px;">
              <span class="badge" style="background: rgba(236, 72, 153, 0.2); color: #f472b6; font-size: 10.5px;">
                ⭐ Viral: ${c.viral_score || 95}
              </span>
              <div style="display: flex; gap: 4px;">
                <button class="btn btn-secondary btn-sm" style="padding: 3px 8px; font-size: 11px;" onclick="toggleMarkClipPosted('${c.filename}', ${!isPosted})" title="${isPosted ? 'Đánh dấu chưa post' : 'Đánh dấu đã post'}">
                  <i class="bi ${isPosted ? 'bi-arrow-counterclockwise' : 'bi-check-lg'}"></i>
                </button>
                <a href="/api/clips/play/${encodeURIComponent(c.filename)}" download class="btn btn-secondary btn-sm" style="padding: 3px 8px; font-size: 11px;" title="Tải về">
                  <i class="bi bi-download"></i>
                </a>
                <button class="btn btn-secondary btn-sm text-danger" style="padding: 3px 8px; font-size: 11px;" onclick="deleteSingleClip('${c.filename}')" title="Xóa video này">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Render pagination
    if (pagination && totalPages > 1) {
      let pageBtns = '';
      for (let p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || (p >= currentClipPage - 2 && p <= currentClipPage + 2)) {
          const activeStyle = (p === currentClipPage) ? 'background: #2563eb; color: #fff; font-weight: 700;' : 'background: #1e293b; color: #94a3b8;';
          pageBtns += `<button class="btn btn-sm" style="${activeStyle} min-width: 32px; padding: 4px 8px;" onclick="goToClipPage(${p})">${p}</button>`;
        } else if (p === currentClipPage - 3 || p === currentClipPage + 3) {
          pageBtns += `<span style="color: #64748b;">...</span>`;
        }
      }
      pagination.innerHTML = `
        <button class="btn btn-secondary btn-sm" ${currentClipPage === 1 ? 'disabled' : ''} onclick="goToClipPage(${currentClipPage - 1})"><i class="bi bi-chevron-left"></i> Trước</button>
        ${pageBtns}
        <button class="btn btn-secondary btn-sm" ${currentClipPage === totalPages ? 'disabled' : ''} onclick="goToClipPage(${currentClipPage + 1})">Sau <i class="bi bi-chevron-right"></i></button>
      `;
    } else if (pagination) {
      pagination.innerHTML = '';
    }
  }

  function goToClipPage(p) {
    currentClipPage = p;
    renderFilteredClips();
  }

  async function toggleMarkClipPosted(filename, markPosted) {
    try {
      if (markPosted) {
        await fetch('/api/clips/mark_posted', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename })
        });
      }
      // Reload
      await loadClipsGallery();
    } catch (e) {
      alert('Lỗi cập nhật trạng thái: ' + e.message);
    }
  }

  async function deleteSingleClip(filename) {
    if (!confirm(`Xóa video "${filename}" khỏi bộ nhớ ổ cứng?`)) return;
    try {
      const res = await fetch('/api/clips/' + encodeURIComponent(filename), { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        await loadClipsGallery();
      } else {
        alert('Lỗi xóa clip: ' + (d.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối khi xóa clip: ' + e.message);
    }
  }

  async function deleteBatchPostedClips() {
    const postedClips = cachedAllClips.filter(c => c.is_posted);
    if (postedClips.length === 0) {
      alert('Không có video nào được đánh dấu "Đã đăng" để xóa!');
      return;
    }
    if (!confirm(`Bạn có chắc chắn muốn xóa ${postedClips.length} video đã đăng để giải phóng ổ cứng?`)) return;
    let deletedCount = 0;
    for (const c of postedClips) {
      try {
        await fetch('/api/clips/' + encodeURIComponent(c.filename), { method: 'DELETE' });
        deletedCount++;
      } catch (err) {}
    }
    alert(`Đã xóa thành công ${deletedCount} video đã đăng!`);
    await loadClipsGallery();
  }
"""

if old_fn_start != -1 and old_fn_end != -1:
    html = html[:old_fn_start] + new_gallery_js + "\n  " + html[old_fn_end:]
    with open("D:/Highlight_Video_Studio/web/templates/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Successfully updated Gallery logic in web/templates/index.html!")
    
    # Also update web/index.html
    with open("D:/Highlight_Video_Studio/web/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Successfully updated web/index.html too!")
else:
    print("Failed to locate old_fn_start or old_fn_end:", old_fn_start, old_fn_end)
