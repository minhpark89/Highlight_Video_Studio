import os, json
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"
APP_PATH = BASE_DIR / "web" / "app.py"

print("[1/2] Adding Quick Assign Dropdowns for Group and Token directly on each page row...")

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# MODAL GÁN NHÓM HOẶC GÁN TOKEN TIỆN LỢI CHO TỪNG PAGE (POPUP SELECT DROPDOWN)
modal_assign_popup_html = """
  <!-- MODAL: GÁN NHANH NHÓM & TOKEN CHO FANPAGE (SELECT DROPDOWN CHUẨN LOHAPAGE) -->
  <div id="modal-quick-assign" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 500px; max-width: 95vw; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div class="app-modal-header" style="padding: 16px 20px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 15px; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <i class="bi bi-gear-fill" style="color: #38bdf8;"></i>
          Thiết Lập Fanpage: <span id="assign-page-name-title" style="color: #60a5fa;">Fanpage</span>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeQuickAssignModal()"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="app-modal-body" style="padding: 20px;">
        <input type="hidden" id="assign-target-page-id">
        
        <!-- Chọn Nhóm Page -->
        <div style="margin-bottom: 16px;">
          <label style="font-size: 12px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            1. Chọn Nhóm Fanpage (Chủ đề):
          </label>
          <select id="assign-select-group" class="form-select form-select-sm" style="background: #0b1329; border-color: #23304d; font-size: 13px;">
            <!-- Populated dynamically -->
          </select>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Gom trang vào nhóm để tự động phân bổ 1 Video : 1 Page khi lên lịch.</div>
        </div>

        <!-- Chọn Token Phụ Trách -->
        <div style="margin-bottom: 16px;">
          <label style="font-size: 12px; font-weight: 700; color: #cbd5e1; display: block; margin-bottom: 6px;">
            2. Chọn Token phụ trách đăng bài:
          </label>
          <select id="assign-select-token" class="form-select form-select-sm" style="background: #0b1329; border-color: #23304d; font-size: 13px;">
            <!-- Populated dynamically with 31 tokens -->
          </select>
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Chọn 1 trong 31 Token AutoPool hoặc để tự động xoay vòng.</div>
        </div>

      </div>
      <div style="padding: 14px 20px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end; gap: 8px;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeQuickAssignModal()">Hủy</button>
        <button type="button" class="btn btn-primary btn-sm" id="btn-save-quick-assign" onclick="saveQuickAssign()"><i class="bi bi-check-lg"></i> Lưu Thiết Lập</button>
      </div>
    </div>
  </div>
"""

if "id=\"modal-quick-assign\"" not in html:
    pos_body = html.rfind("</body>")
    if pos_body != -1:
        html = html[:pos_body] + modal_assign_popup_html + "\n" + html[pos_body:]
        print("Injected modal-quick-assign into HTML!")

# Cập nhật nút trên từng dòng page: Đổi thành nút "Cấu hình / Đổi Nhóm & Token"
old_action_btn = """<button class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 5px 10px;" onclick="openAssignSingleTokenModal('${pId}')" title="Gán hoặc đổi Token cho trang này">
                <i class="bi bi-key"></i> Đổi Token
              </button>"""

new_action_btn = """<button class="btn btn-secondary btn-sm" style="font-size: 11.5px; padding: 5px 10px; background: #1e293b; border-color: #3b82f6; color: #60a5fa;" onclick="openQuickAssignModal('${pId}', '${escapeHtml(pName)}')" title="Chọn Nhóm & Token cho trang này">
                <i class="bi bi-sliders"></i> Đổi Nhóm & Token
              </button>"""

if old_action_btn in html:
    html = html.replace(old_action_btn, new_action_btn)
    print("Updated page row button to 'Đổi Nhóm & Token'!")

# Thêm JS functions cho modal này
quick_assign_js = """
  // ================= MODAL CHỌN NHÓM & TOKEN TRỰC TIẾP (CHUẨN LOHAPAGE) =================
  function openQuickAssignModal(pageId, pageName) {
    const m = document.getElementById('modal-quick-assign');
    if (!m) return;
    
    document.getElementById('assign-target-page-id').value = pageId;
    document.getElementById('assign-page-name-title').textContent = pageName || pageId;

    // 1. Populate Dropdown Nhóm
    const selGroup = document.getElementById('assign-select-group');
    if (selGroup) {
      let grpOptions = '<option value="">-- Chưa phân nhóm --</option>';
      (cachedGroupsList || []).forEach(g => {
        grpOptions += `<option value="${g.id || g.name}">${g.name} (${(g.page_ids||[]).length} Page)</option>`;
      });
      selGroup.innerHTML = grpOptions;

      // Tìm nhóm hiện tại của page
      const pageObj = cachedPagesList.find(p => String(p.page_id || p.id) === String(pageId));
      if (pageObj) {
        if (pageObj.group_id) selGroup.value = pageObj.group_id;
        else if (pageObj.group_name) {
          const matchedG = (cachedGroupsList || []).find(g => g.name === pageObj.group_name);
          if (matchedG) selGroup.value = matchedG.id || matchedG.name;
        }
      }
    }

    // 2. Populate Dropdown 31 Token
    const selToken = document.getElementById('assign-select-token');
    if (selToken) {
      let tokOptions = '<option value="">-- Tự động xoay vòng (AutoPool) --</option>';
      (globalTokensCatalog || []).forEach((t, idx) => {
        const masked = t.token_masked || t.masked_token || 'EAAayhOu...';
        tokOptions += `<option value="${t.id}">#${idx+1} ${t.name} (${masked})</option>`;
      });
      selToken.innerHTML = tokOptions;

      const pageObj = cachedPagesList.find(p => String(p.page_id || p.id) === String(pageId));
      if (pageObj && pageObj.token_id) {
        selToken.value = pageObj.token_id;
      }
    }

    m.style.display = 'flex';
  }

  function closeQuickAssignModal() {
    const m = document.getElementById('modal-quick-assign');
    if (m) m.style.display = 'none';
  }

  async function saveQuickAssign() {
    const pageId = document.getElementById('assign-target-page-id').value;
    const groupId = document.getElementById('assign-select-group').value;
    const tokenId = document.getElementById('assign-select-token').value;
    const btn = document.getElementById('btn-save-quick-assign');

    if (!pageId) return;
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang lưu...';
    }

    try {
      const res = await fetch('/api/pages/update_binding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          page_id: pageId,
          group_id: groupId,
          token_id: tokenId
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(data.message || 'Đã cập nhật Nhóm & Token thành công!');
        closeQuickAssignModal();
        await loadTokensAndPages();
      } else {
        alert('Lỗi: ' + (data.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối lưu cấu hình: ' + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-lg"></i> Lưu Thiết Lập';
      }
    }
  }
"""

if "function openQuickAssignModal" not in html:
    pos_sub = html.find("function openAssignSingleTokenModal")
    if pos_sub != -1:
        html = html[:pos_sub] + quick_assign_js + "\n\n  " + html[pos_sub:]
        print("Injected quick_assign_js into HTML script!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("[1/2] index.html successfully updated with Quick Assign Modal!")
