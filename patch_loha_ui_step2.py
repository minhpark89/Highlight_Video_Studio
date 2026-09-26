import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

print("[2/3] Patching JavaScript in index.html for LoHa Page Card UI & Modals...")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

loha_js_code = """
  // ================= QUẢN LÝ FANPAGE & TOKEN CHUẨN LOHAPAGE =================
  let cachedPagesList = [];
  let globalTokensCatalog = [];
  let currentPageFilterGroup = 'all';
  let currentPageFilterStatus = 'all';
  let currentPageSearchText = '';
  let currentPageViewMode = 'card'; // card | table
  let currentPagesPage = 1;
  const PAGES_PER_PAGE = 12;

  function setPageViewMode(mode) {
    currentPageViewMode = mode;
    document.getElementById('view-mode-card').classList.toggle('active', mode === 'card');
    document.getElementById('view-mode-table').classList.toggle('active', mode === 'table');
    document.getElementById('pages-cards-container').style.display = (mode === 'card') ? 'grid' : 'none';
    document.getElementById('pages-table-wrapper').style.display = (mode === 'table') ? 'block' : 'none';
    renderFilteredPages();
  }

  function filterPagesList() {
    currentPageSearchText = (document.getElementById('page-search-input')?.value || '').trim().toLowerCase();
    currentPageFilterGroup = document.getElementById('page-filter-group')?.value || 'all';
    currentPageFilterStatus = document.getElementById('page-filter-status')?.value || 'all';
    currentPagesPage = 1;
    renderFilteredPages();
  }

  function renderFilteredPages() {
    const cardsContainer = document.getElementById('pages-cards-container');
    const tbody = document.getElementById('pages-tbody');
    const badge = document.getElementById('page-filtered-count-badge');
    const pagination = document.getElementById('pages-pagination');

    let filtered = cachedPagesList.filter(p => {
      const pName = (p.page_name || p.name || '').toLowerCase();
      const pId = String(p.page_id || p.id || '');
      // Match search
      if (currentPageSearchText && !pName.includes(currentPageSearchText) && !pId.includes(currentPageSearchText)) {
        return false;
      }
      // Match group
      if (currentPageFilterGroup !== 'all') {
        const pGroups = p.groups || [];
        if (!pGroups.includes(currentPageFilterGroup) && p.group_id !== currentPageFilterGroup) return false;
      }
      // Match status
      if (currentPageFilterStatus === 'active' && !p.page_token && !p.has_token) return false;
      if (currentPageFilterStatus === 'notoken' && (p.page_token || p.has_token)) return false;
      return true;
    });

    if (badge) badge.textContent = `${filtered.length} / ${cachedPagesList.length} trang`;

    if (filtered.length === 0) {
      if (cardsContainer) {
        cardsContainer.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; color: var(--text-dim); padding: 40px; background: rgba(15, 23, 42, 0.4); border-radius: 12px; border: 1px dashed #23304d;">
            <i class="bi bi-folder-x" style="font-size: 2.5rem; opacity: 0.3; display: block; margin-bottom: 10px;"></i>
            Không tìm thấy Fanpage nào phù hợp với bộ lọc hiện tại.
          </div>`;
      }
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #64748b; padding: 20px;">Không có dữ liệu trang.</td></tr>`;
      if (pagination) pagination.innerHTML = '';
      return;
    }

    const totalPages = Math.ceil(filtered.length / PAGES_PER_PAGE);
    if (currentPagesPage > totalPages) currentPagesPage = totalPages;
    const startIndex = (currentPagesPage - 1) * PAGES_PER_PAGE;
    const pageItems = filtered.slice(startIndex, startIndex + PAGES_PER_PAGE);

    // 1. Render Thẻ Ngang (LoHa Style Cards)
    if (cardsContainer) {
      cardsContainer.innerHTML = pageItems.map(p => {
        const pName = p.page_name || p.name || 'Fanpage Facebook';
        const pId = p.page_id || p.id || 'N/A';
        const totalPosts = p.total_posted || 0;
        const hasToken = !!(p.page_token || p.has_token);
        const tokenName = p.token_name || 'System User';
        const grpName = p.group_name || (p.groups && p.groups[0]) || 'Chưa nhóm';

        // Avatar viết tắt màu ngẫu nhiên theo chữ cái đầu
        const initials = pName.trim().substring(0, 2).toUpperCase();
        const colors = ['#2563eb', '#7c3aed', '#db2777', '#059669', '#d97706', '#0284c7'];
        const avatarBg = colors[Math.abs(pName.split('').reduce((a,c)=>a+c.charCodeAt(0), 0)) % colors.length];

        const tokenBadge = hasToken 
          ? `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 10px;"><i class="bi bi-shield-check"></i> VĨNH VIỄN</span>`
          : `<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 10px;"><i class="bi bi-shield-x"></i> THIẾU TOKEN</span>`;

        return `
          <div class="card" style="background: #111c33; border: 1px solid ${hasToken ? '#23304d' : 'rgba(239, 68, 68, 0.4)'}; border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 10px; transition: transform 0.2s, border-color 0.2s; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
            <div style="display: flex; align-items: center; gap: 12px;">
              <div style="width: 44px; height: 44px; border-radius: 50%; background: ${avatarBg}; color: #fff; font-weight: 800; font-size: 15px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; box-shadow: 0 2px 6px rgba(0,0,0,0.4);">
                ${initials}
              </div>
              <div style="flex: 1; overflow: hidden;">
                <div style="font-weight: 700; font-size: 13.5px; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${pName}">
                  ${pName}
                </div>
                <div style="font-size: 11px; color: #64748b; font-family: monospace; display: flex; align-items: center; gap: 4px; margin-top: 2px;">
                  <span>ID: ${pId}</span>
                  <i class="bi bi-copy" style="cursor: pointer; opacity: 0.7;" onclick="navigator.clipboard.writeText('${pId}')" title="Copy ID"></i>
                </div>
              </div>
              <div>${tokenBadge}</div>
            </div>

            <!-- Dải thông tin Badges LoHa -->
            <div style="display: flex; gap: 6px; flex-wrap: wrap; border-top: 1px solid #1e293b; padding-top: 8px; font-size: 11px;">
              <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">
                <i class="bi bi-film"></i> ${totalPosts} bài đăng
              </span>
              <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc;">
                <i class="bi bi-folder2-open"></i> ${grpName}
              </span>
              <span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">
                <i class="bi bi-key"></i> ${tokenName}
              </span>
            </div>

            <!-- Nút hành động nhanh -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto; padding-top: 4px;">
              <a href="https://facebook.com/${pId}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 3px 8px;" title="Mở trang trên Facebook">
                <i class="bi bi-box-arrow-up-right"></i> Xem Page
              </a>
              <div style="display: flex; gap: 4px;">
                <button class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 3px 8px;" onclick="openAssignSingleTokenModal('${pId}')" title="Gán Token riêng">
                  <i class="bi bi-key"></i> Đổi Token
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    // 2. Render Table dự phòng
    if (tbody) {
      tbody.innerHTML = pageItems.map(p => {
        const pName = p.page_name || p.name || 'Fanpage Facebook';
        const pId = p.page_id || p.id || 'N/A';
        const totalPosts = p.total_posted || 0;
        const hasToken = !!(p.page_token || p.has_token);
        const tokenName = p.token_name || 'System User';
        const grpName = p.group_name || (p.groups && p.groups[0]) || 'Mặc định';

        return `
          <tr>
            <td><strong>${pName}</strong></td>
            <td><code>${pId}</code></td>
            <td><span class="badge" style="background:#1e293b; color:#f59e0b;">${tokenName}</span></td>
            <td><span class="badge" style="background:#1e293b; color:#c084fc;">${grpName}</span></td>
            <td><strong>${totalPosts}</strong> bài</td>
            <td>${hasToken ? '<span class="badge badge-done">Hoạt động</span>' : '<span class="badge badge-error">Thiếu token</span>'}</td>
            <td style="text-align: right;">
              <a href="https://facebook.com/${pId}" target="_blank" class="btn btn-secondary btn-sm" style="padding: 2px 6px; font-size: 11px;"><i class="bi bi-box-arrow-up-right"></i></a>
            </td>
          </tr>
        `;
      }).join('');
    }

    // 3. Phân trang Pagination
    if (pagination && totalPages > 1) {
      let pageBtns = '';
      for (let p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || (p >= currentPagesPage - 2 && p <= currentPagesPage + 2)) {
          const activeStyle = (p === currentPagesPage) ? 'background: #2563eb; color: #fff; font-weight: 700;' : 'background: #1e293b; color: #94a3b8;';
          pageBtns += `<button class="btn btn-sm" style="${activeStyle} min-width: 32px; padding: 4px 8px; margin: 0 2px;" onclick="goToPagesPage(${p})">${p}</button>`;
        } else if (p === currentPagesPage - 3 || p === currentPagesPage + 3) {
          pageBtns += `<span style="color: #64748b; margin: 0 2px;">...</span>`;
        }
      }
      pagination.innerHTML = `
        <button class="btn btn-secondary btn-sm" ${currentPagesPage === 1 ? 'disabled' : ''} onclick="goToPagesPage(${currentPagesPage - 1})"><i class="bi bi-chevron-left"></i> Trước</button>
        <div style="display: flex; align-items: center;">${pageBtns}</div>
        <button class="btn btn-secondary btn-sm" ${currentPagesPage === totalPages ? 'disabled' : ''} onclick="goToPagesPage(${currentPagesPage + 1})">Sau <i class="bi bi-chevron-right"></i></button>
        <span style="font-size: 12px; color: #64748b; margin-left: 8px;">Trang ${currentPagesPage} / ${totalPages}</span>
      `;
    } else if (pagination) {
      pagination.innerHTML = '';
    }
  }

  function goToPagesPage(p) {
    currentPagesPage = p;
    renderFilteredPages();
    const c = document.getElementById('pages-cards-container');
    if (c) c.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Cập nhật loadTokensAndPages để nạp danh sách chuẩn
  async function loadTokensAndPages() {
    try {
      const [resTok, resPages, resGrp, resRules] = await Promise.all([
        fetch('/api/tokens'),
        fetch('/api/pages'),
        fetch('/api/groups'),
        fetch('/api/schedule/rules')
      ]);
      const dataTok = await resTok.json();
      const dataPages = await resPages.json();
      const dataGrp = await resGrp.json();
      const rules = await resRules.json();

      const tokens = dataTok.tokens || [];
      globalTokensCatalog = tokens;
      const pages = dataPages.pages || [];
      const groups = dataGrp.groups || [];
      cachedPagesList = pages;

      // Update counters & metrics
      if (document.getElementById('stat-total-tokens')) document.getElementById('stat-total-tokens').textContent = tokens.length;
      if (document.getElementById('stat-total-pages')) document.getElementById('stat-total-pages').textContent = pages.length;
      if (document.getElementById('stat-total-groups')) document.getElementById('stat-total-groups').textContent = groups.length;
      
      const totalPub = pages.reduce((acc, p) => acc + (p.total_posted || 0), 0);
      if (document.getElementById('stat-total-published')) document.getElementById('stat-total-published').textContent = totalPub;

      // Update rules banner
      if (rules && rules.slots) {
        if (document.getElementById('rule-display-slots')) document.getElementById('rule-display-slots').textContent = rules.slots.join(', ');
        if (document.getElementById('rule-display-stagger')) document.getElementById('rule-display-stagger').textContent = `${rules.stagger_min || 15} phút`;
      }

      // Populate filter dropdown
      const filterGrp = document.getElementById('page-filter-group');
      if (filterGrp) {
        filterGrp.innerHTML = '<option value="all">Tất cả nhóm</option>' + groups.map(g => `
          <option value="${g.id || g.name}">${g.name} (${(g.page_ids||[]).length})</option>
        `).join('');
      }

      // Render cards
      renderFilteredPages();
    } catch (e) {
      console.error('Lỗi nạp tokens and pages:', e);
    }
  }

  // ================= MODAL QUY TẮC LÊN LỊCH & 1-CLICK PHÂN BỔ =================
  function openScheduleRulesModal() {
    const m = document.getElementById('modal-schedule-rules');
    if (m) m.style.display = 'flex';
    fetch('/api/schedule/rules').then(r => r.json()).then(rules => {
      if (rules && rules.slots) {
        document.getElementById('loha-slot-input').value = rules.slots.join(', ');
        document.getElementById('loha-stagger-select').value = String(rules.stagger_min || 15);
      }
    }).catch(e => console.warn(e));
  }

  function closeScheduleRulesModal() {
    const m = document.getElementById('modal-schedule-rules');
    if (m) m.style.display = 'none';
  }

  async function saveLoHaScheduleRules() {
    try {
      const rawSlots = document.getElementById('loha-slot-input').value;
      const slots = rawSlots.split(',').map(s => s.trim()).filter(s => s);
      const stagger = parseInt(document.getElementById('loha-stagger-select').value) || 15;
      const autoComment = document.getElementById('loha-auto-first-comment').checked;

      const payload = {
        slots: slots,
        stagger_min: stagger,
        stagger_max: stagger,
        auto_comment: autoComment,
        include_website_link: true,
        folder_binding_mode: "1_video_1_page"
      };

      const res = await fetch('/api/schedule/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const d = await res.json();
      if (res.ok) {
        alert('Đã lưu quy tắc lên lịch LoHa Page thành công!');
        closeScheduleRulesModal();
        loadTokensAndPages();
      } else {
        alert('Lỗi: ' + (d.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối lưu quy tắc: ' + e.message);
    }
  }

  function openDistributeModal() {
    const m = document.getElementById('modal-distribute-loha');
    if (!m) return;
    m.style.display = 'flex';

    // Populate nhóm page
    fetch('/api/groups').then(r => r.json()).then(d => {
      const sel = document.getElementById('modal-dist-group');
      const grps = d.groups || [];
      if (sel) {
        if (grps.length === 0) {
          sel.innerHTML = '<option value="">Chưa có Nhóm Page nào (Hãy tạo nhóm trước)</option>';
        } else {
          sel.innerHTML = grps.map(g => `<option value="${g.id}">${g.name} (${(g.page_ids||[]).length} Page)</option>`).join('');
        }
      }
    });

    // Default start time: 20 phút tới
    const now = new Date(Date.now() + 20 * 60 * 1000);
    const tzOffset = now.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(now - tzOffset)).toISOString().slice(0, 16);
    const timeInput = document.getElementById('modal-dist-starttime');
    if (timeInput) timeInput.value = localISOTime;
  }

  function closeDistributeModal() {
    const m = document.getElementById('modal-distribute-loha');
    if (m) m.style.display = 'none';
  }

  async function executeBatchDistribute() {
    const groupId = document.getElementById('modal-dist-group')?.value;
    const startTime = document.getElementById('modal-dist-starttime')?.value;
    const stagger = parseInt(document.getElementById('modal-dist-stagger')?.value) || 15;
    const btn = document.getElementById('btn-submit-distribute');

    if (!groupId) {
      alert('Vui lòng chọn hoặc tạo ít nhất 1 Nhóm Page!');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang phân bổ...';
    }

    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          start_time: startTime,
          stagger_minutes: stagger,
          auto_first_comment: true,
          delete_after_schedule: false
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(data.message || `Đã phân bổ thành công ${data.scheduled_count} video 1:1 cho nhóm!`);
        closeDistributeModal();
        loadTokensAndPages();
        if (typeof loadJobsTable === 'function') loadJobsTable();
      } else {
        alert('Lỗi phân bổ: ' + (data.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối phân bổ: ' + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lightning-charge-fill"></i> Bắt đầu Lên Lịch';
      }
    }
  }

  function openAssignSingleTokenModal(pageId) {
    const token = prompt(`Nhập mã Token riêng cho Page ${pageId} (hoặc để trống để dùng System User Token):`);
    if (token === null) return;
    fetch('/api/pages/assign_token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_id: pageId, token: token.trim() })
    }).then(r => r.json()).then(d => {
      if (d.success) {
        alert('Đã cập nhật Token cho Page thành công!');
        loadTokensAndPages();
      } else {
        alert('Lỗi: ' + (d.error || 'Server error'));
      }
    }).catch(e => alert(e.message));
  }
"""

# Tìm hàm loadTokensAndPages cũ để thay thế
fn_start = html.find("async function loadTokensAndPages()")
if fn_start != -1:
    # Tìm kết thúc khối quản lý token & pages cũ
    fn_end = html.find("// ================= QUY TẮC LÊN LỊCH & PHÂN BỔ (LOHA CONTROLLER) =================", fn_start)
    if fn_end == -1:
        fn_end = html.find("async function checkYouTubeStatus()", fn_start)

    html = html[:fn_start] + loha_js_code + "\n\n  " + html[fn_end:]
    print("Replaced loadTokensAndPages with LoHa Card & Modal Logic successfully!")
else:
    print("WARNING: Could not find async function loadTokensAndPages() in index.html")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("[2/3] index.html JS patch completed!")
