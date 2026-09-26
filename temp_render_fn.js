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

  function goToClipPage