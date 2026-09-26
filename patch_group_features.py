import os, json, re, shutil
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Thêm nút "Quản lý Nhóm" vào cạnh nút "Tạo Nhóm" trong header pane-pages
# và thêm danh sách các Nhóm (badges/chips) có nút Xoá nhóm trực tiếp như LoHa Page
old_btn_group = """<button class="btn btn-primary" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border:none;" onclick="openAddGroupModal()"><i class="bi bi-folder-plus"></i> Tạo Nhóm</button>"""
new_btn_group = """<button class="btn btn-primary" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border:none;" onclick="openAddGroupModal()"><i class="bi bi-folder-plus"></i> Tạo Nhóm Mới</button>
              <button class="btn btn-secondary" onclick="openManageGroupsModal()"><i class="bi bi-folder-check"></i> Quản lý Nhóm (<span id="btn-group-count">1</span>)</button>"""

if old_btn_group in html:
    html = html.replace(old_btn_group, new_btn_group)
    print("Added 'Quản lý Nhóm' button to header!")

# 2. Xây dựng MODAL Quản lý & Xoá nhóm, và nâng cấp MODAL Tạo nhóm (submitAddGroup + deleteGroup)
modal_manage_groups_html = """
  <!-- MODAL: DANH SÁCH & QUẢN LÝ NHÓM PAGE (CHUẨN LOHAPAGE - CÓ XOÁ & SỬA) -->
  <div id="modal-manage-groups" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 650px; max-width: 95vw; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div class="app-modal-header" style="padding: 16px 20px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 16px; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <i class="bi bi-folder-fill" style="color: #c084fc;"></i>
          Danh Sách Nhóm Fanpage Vệ Tinh (LoHa Page)
        </div>
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeManageGroupsModal()"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="app-modal-body" style="padding: 20px; max-height: 70vh; overflow-y: auto;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
          <span style="font-size: 12px; color: #94a3b8;">Gom trang theo chủ đề để phân bổ 1 Video : 1 Page</span>
          <button class="btn btn-sm btn-primary" onclick="closeManageGroupsModal(); openAddGroupModal();"><i class="bi bi-plus-lg"></i> Thêm Nhóm Mới</button>
        </div>
        <div id="manage-groups-list" style="display: flex; flex-direction: column; gap: 10px;">
          <!-- Render danh sách nhóm động ở đây -->
        </div>
      </div>
      <div style="padding: 14px 20px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeManageGroupsModal()">Đóng</button>
      </div>
    </div>
  </div>
"""

if "id=\"modal-manage-groups\"" not in html:
    pos_b = html.rfind("</body>")
    if pos_b != -1:
        html = html[:pos_b] + modal_manage_groups_html + "\n" + html[pos_b:]
        print("Injected modal-manage-groups into HTML!")

# 3. Thêm các hàm xử lý JS: openManageGroupsModal, deleteGroup, submitAddGroup, renderGroupsInModal
js_group_logic = """
  // ================= QUẢN LÝ NHÓM PAGE (CHUẨN LOHAPAGE: THÊM, XOÁ, HIỂN THỊ) =================
  let cachedGroupsList = [];

  function openAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (!m) return;
    document.getElementById('group-input-name').value = '';
    m.style.display = 'flex';
    
    // Nạp danh sách checkbox các Fanpage
    const box = document.getElementById('group-pages-select-box');
    if (box) {
      if (cachedPagesList.length === 0) {
        box.innerHTML = '<span style="font-size: 11px; color: #64748b;">Chưa có Fanpage nào được đồng bộ!</span>';
      } else {
        box.innerHTML = cachedPagesList.map(p => `
          <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #cbd5e1; cursor: pointer; padding: 4px 6px; border-radius: 4px; background: rgba(255,255,255,0.02);">
            <input type="checkbox" class="group-page-checkbox" value="${p.page_id || p.id}">
            <span><b>${p.page_name || p.name}</b> <small style="color: #64748b;">(${p.page_id || p.id})</small></span>
          </label>
        `).join('');
      }
    }
  }

  function closeAddGroupModal() {
    const m = document.getElementById('modal-add-group');
    if (m) m.style.display = 'none';
  }

  async function submitAddGroup() {
    const nameInput = document.getElementById('group-input-name');
    const folderInput = document.getElementById('group-input-folder');
    const name = nameInput ? nameInput.value.trim() : '';
    const folder = folderInput ? folderInput.value.trim() : 'D:\\\\Highlight_Video_Studio\\\\output';

    if (!name) {
      alert('Vui lòng nhập tên nhóm Fanpage (ví dụ: Nhóm Review, Nhóm Tin Tức...)!');
      return;
    }

    // Lấy các page được tích chọn
    const selectedPageIds = [];
    document.querySelectorAll('.group-page-checkbox:checked').forEach(cb => {
      selectedPageIds.push(cb.value);
    });

    const btn = document.getElementById('btn-submit-group');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Đang lưu...';
    }

    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name,
          page_ids: selectedPageIds,
          folder_binding: folder
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert(`Đã tạo thành công nhóm '${name}' với ${selectedPageIds.length} Fanpage!`);
        closeAddGroupModal();
        await loadTokensAndPages();
      } else {
        alert('Lỗi tạo nhóm: ' + (data.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối khi tạo nhóm: ' + e.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-lg"></i> Lưu cấu hình Nhóm';
      }
    }
  }

  function openManageGroupsModal() {
    const m = document.getElementById('modal-manage-groups');
    if (!m) return;
    m.style.display = 'flex';
    renderGroupsInManageModal();
  }

  function closeManageGroupsModal() {
    const m = document.getElementById('modal-manage-groups');
    if (m) m.style.display = 'none';
  }

  function renderGroupsInManageModal() {
    const listCont = document.getElementById('manage-groups-list');
    if (!listCont) return;

    if (!cachedGroupsList || cachedGroupsList.length === 0) {
      listCont.innerHTML = `
        <div style="text-align: center; color: #64748b; padding: 30px; background: rgba(15, 23, 42, 0.4); border-radius: 8px;">
          <i class="bi bi-folder-x" style="font-size: 2rem; opacity: 0.3; display: block; margin-bottom: 8px;"></i>
          Chưa có nhóm nào được tạo. Hãy bấm 'Thêm Nhóm Mới' ở trên.
        </div>`;
      return;
    }

    listCont.innerHTML = cachedGroupsList.map(g => {
      const gId = g.id || g.group_id;
      const gName = g.name || 'Nhóm Fanpage';
      const pageCount = (g.page_ids || []).length;
      const folder = g.folder_binding || g.folder_path || 'D:\\\\Highlight_Video_Studio\\\\output';

      return `
        <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 14px;">
          <div style="display: flex; align-items: center; gap: 12px; flex: 1;">
            <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(192, 132, 252, 0.2); color: #c084fc; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0;">
              <i class="bi bi-folder2"></i>
            </div>
            <div>
              <div style="font-weight: 700; font-size: 13.5px; color: #f8fafc;">${gName}</div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">${pageCount} Fanpage</span>
                <span style="margin-left: 6px; font-family: monospace; color: #64748b;">${folder}</span>
              </div>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn btn-secondary btn-sm text-danger" onclick="deleteGroup('${gId}', '${gName}')" title="Xóa nhóm này">
              <i class="bi bi-trash"></i> Xóa Nhóm
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  async function deleteGroup(groupId, groupName) {
    if (!confirm(`Bạn có chắc chắn muốn XÓA nhóm '${groupName}' không?\\n\\n(Lưu ý: Xóa nhóm chỉ gỡ phân nhóm, các Fanpage và video hoàn toàn không bị ảnh hưởng).`)) return;
    try {
      const res = await fetch('/api/groups/' + encodeURIComponent(groupId), { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        alert(`Đã xóa nhóm '${groupName}' thành công!`);
        await loadTokensAndPages();
        renderGroupsInManageModal();
      } else {
        alert('Lỗi khi xóa nhóm: ' + (d.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối khi xóa nhóm: ' + e.message);
    }
  }
"""

# Chèn các hàm JS vào trước loadTokensAndPages
pos_lt = html.find("async function loadTokensAndPages()")
if pos_lt != -1:
    html = html[:pos_lt] + js_group_logic + "\n\n  " + html[pos_lt:]
    print("Injected JS group logic successfully!")

# Cập nhật loadTokensAndPages để lưu cachedGroupsList và cập nhật số lượng nhóm trên button
html = html.replace("const groups = dataGrp.groups || [];", 
                    "const groups = dataGrp.groups || [];\n      cachedGroupsList = groups;\n      const grpBtnCount = document.getElementById('btn-group-count'); if (grpBtnCount) grpBtnCount.textContent = groups.length;")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("Saved index.html with full Group Management features!")
