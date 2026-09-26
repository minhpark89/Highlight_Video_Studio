import os, json, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"
APP_PATH = BASE_DIR / "web" / "app.py"

print("[1/4] Checking and adding Token Group Backend...")

# Đọc app.py để thêm chức năng Nhóm Token
with open(APP_PATH, "r", encoding="utf-8") as f:
    app_code = f.read()

token_group_backend = """
# ================= QUẢN LÝ NHÓM TOKEN (LOHA TOKEN GROUPS) =================
TOKEN_GROUPS_FILE = BASE_DIR / "token_groups.json"

def load_token_groups():
    if not TOKEN_GROUPS_FILE.exists():
        # Mặc định tạo Nhóm AutoPool 31 Token
        default_groups = [{
            "id": "tgrp_autopool",
            "name": "Nhóm AutoPool Chính (31 Token)",
            "strategy": "least_recently_used", # round_robin | least_recently_used | random
            "token_ids": [t.get("id") for t in token_vault.list_tokens(mask=False)],
            "note": "Xoay vòng 31 token chống quá tải Meta",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]
        with open(TOKEN_GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_groups, f, indent=2, ensure_ascii=False)
        return default_groups
    try:
        with open(TOKEN_GROUPS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_token_groups(groups):
    with open(TOKEN_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)

@app.route("/api/token-groups", methods=["GET"])
def api_list_token_groups():
    return jsonify({"success": True, "groups": load_token_groups()})

@app.route("/api/token-groups", methods=["POST"])
def api_save_token_group():
    data = request.json or {}
    gid = data.get("id") or f"tgrp_{int(time.time())}"
    name = data.get("name", "").strip()
    token_ids = data.get("token_ids", [])
    strategy = data.get("strategy", "least_recently_used")
    note = data.get("note", "").strip()

    if not name:
        return jsonify({"error": "Tên nhóm token không được rỗng"}), 400

    groups = load_token_groups()
    existing = next((g for g in groups if g.get("id") == gid), None)
    if existing:
        existing["name"] = name
        existing["token_ids"] = token_ids
        existing["strategy"] = strategy
        existing["note"] = note
        existing["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        groups.append({
            "id": gid,
            "name": name,
            "strategy": strategy,
            "token_ids": token_ids,
            "note": note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    save_token_groups(groups)
    return jsonify({"success": True, "message": f"Đã lưu Nhóm Token '{name}' thành công!"})

@app.route("/api/token-groups/<gid>", methods=["DELETE"])
def api_delete_token_group(gid):
    groups = load_token_groups()
    new_groups = [g for g in groups if g.get("id") != gid]
    save_token_groups(new_groups)
    return jsonify({"success": True, "message": "Đã xóa nhóm token!"})
"""

if "def load_token_groups" not in app_code:
    pos_rt = app_code.find("@app.route(\"/api/tokens\"")
    app_code = app_code[:pos_rt] + token_group_backend + "\n\n" + app_code[pos_rt:]
    with open(APP_PATH, "w", encoding="utf-8") as f:
        f.write(app_code)
    print("Injected Token Group routes into app.py!")

# 2. Sửa index.html:
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# [A] SỬA ẢNH 1: Khi mở modal-add-group, render danh sách Fanpage ĐẦY ĐỦ AVATAR THẬT, TÊN, ID, NHÓM, TOKEN
# Đảm bảo box có avatar tròn load từ p.avatar với referrerpolicy="no-referrer"
# và checkbox nằm bên trái cùng, text căn lề chuẩn
page_item_render_template = """box.innerHTML = cachedPagesList.map(p => {
          const pName = p.page_name || p.name || 'Fanpage Facebook';
          const pId = p.page_id || p.id || 'N/A';
          const avatarUrl = p.avatar || `https://graph.facebook.com/${pId}/picture?type=normal`;
          const initials = pName.trim().substring(0, 2).toUpperCase();
          const colors = ['#2563eb', '#7c3aed', '#db2777', '#059669', '#d97706', '#0284c7'];
          const avatarBg = colors[Math.abs(pName.split('').reduce((a,c)=>a+c.charCodeAt(0), 0)) % colors.length];
          const hasToken = !!(p.page_token || p.has_token);

          return `
            <label style="display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 12px; color: #cbd5e1; cursor: pointer; padding: 10px 14px; border-radius: 8px; background: #0b1329; border: 1px solid #1e293b; margin-bottom: 6px; transition: all 0.2s;">
              <div style="display: flex; align-items: center; gap: 12px; flex: 1; overflow: hidden;">
                <input type="checkbox" class="group-page-checkbox" value="${pId}" style="width: 18px; height: 18px; accent-color: #ec4899; cursor: pointer; flex-shrink: 0;">
                <div style="width: 36px; height: 36px; border-radius: 50%; overflow: hidden; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1.5px solid #334155;">
                  <img src="${avatarUrl}" alt="${pName}" style="width: 100%; height: 100%; object-fit: cover;" referrerpolicy="no-referrer" onerror="this.onerror=null; this.parentElement.innerHTML='<span style=\\'color:#fff; font-weight:800; font-size:13px;\\'>${initials}</span>';">
                </div>
                <div style="overflow: hidden;">
                  <div style="font-weight: 700; font-size: 13px; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${pName}</div>
                  <div style="font-size: 11px; color: #64748b; font-family: monospace;">ID: ${pId}</div>
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
                <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc; font-size: 10.5px;">${p.group_name || 'BM 1'}</span>
                ${hasToken ? '<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 10.5px;">Vĩnh viễn</span>' : '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #f87171; font-size: 10.5px;">Thiếu token</span>'}
              </div>
            </label>
          `;
        }).join('');"""

# Thay thế đoạn render checkbox trong openAddGroupModal
m_start = html.find("function openAddGroupModal()")
if m_start != -1:
    m_box = html.find("box.innerHTML = cachedPagesList.map", m_start)
    m_end = html.find("}).join('');", m_box)
    if m_box != -1 and m_end != -1:
        html = html[:m_box] + page_item_render_template + html[m_end + len("}).join('');"):]
        print("Updated openAddGroupModal page list rendering!")

# [B] SỬA ẢNH 2: Modal Lên Lịch / Phân Bổ bị che nửa trên và thừa nút chèn link
# Xoá modal-publish-reel cũ bị hỏng layout nếu có
html = re.sub(r'<div id="modal-publish-reel"[\s\S]*?</form>\s*</div>\s*</div>', '', html)

# Thêm MODAL NHÓM TOKEN (LoHa Token Groups Manager)
token_group_modal_html = """
  <!-- MODAL: TẠO & QUẢN LÝ NHÓM TOKEN (CHUẨN LOHAPAGE) -->
  <div id="modal-token-group" class="app-modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.8); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="app-modal-box" style="background: #111c33; border: 1px solid #23304d; border-radius: 14px; width: 620px; max-width: 95vw; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
      <div class="app-modal-header" style="padding: 16px 20px; background: #0b1329; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center;">
        <div style="font-size: 16px; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
          <i class="bi bi-diagram-3-fill" style="color: #f59e0b;"></i>
          Quản Lý Nhóm Token (LoHa Token Pool)
        </div>
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeTokenGroupModal()"><i class="bi bi-x-lg"></i></button>
      </div>
      <div class="app-modal-body" style="padding: 20px; max-height: 75vh; overflow-y: auto;">
        
        <!-- Form thêm nhóm token -->
        <div style="background: #0f172a; border: 1px solid #23304d; border-radius: 10px; padding: 16px; margin-bottom: 20px;">
          <div style="font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
            <i class="bi bi-plus-circle-fill"></i> Tạo Nhóm Token Mới
          </div>
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="font-size: 12px; font-weight: 600; color: #cbd5e1;">Tên nhóm token:</label>
            <input type="text" id="tgrp-input-name" class="form-control form-control-sm" placeholder="Ví dụ: Nhóm Token BM Chính, Dàn Token Phụ..." style="background: #0b1329; border-color: #334155;">
          </div>
          <div style="margin-bottom: 12px;">
            <label class="form-label" style="font-size: 12px; font-weight: 600; color: #cbd5e1;">Chiến lược xoay vòng:</label>
            <select id="tgrp-input-strategy" class="form-select form-select-sm" style="background: #0b1329; border-color: #334155;">
              <option value="least_recently_used" selected>Ít dùng gần đây nhất (Khuyên dùng - Tránh limit FB)</option>
              <option value="round_robin">Xoay vòng đều (Round Robin)</option>
              <option value="random">Ngẫu nhiên (Random)</option>
            </select>
          </div>
          <div style="margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <label class="form-label" style="font-size: 12px; font-weight: 600; color: #cbd5e1; margin-bottom:0;">Chọn các Token thuộc nhóm:</label>
              <button type="button" class="btn btn-link btn-sm" style="padding:0; font-size:11px; color:#38bdf8;" onclick="toggleAllTokenGroupChecks()">Chọn tất cả 31 Token</button>
            </div>
            <div id="tgrp-tokens-select-box" style="max-height: 180px; overflow-y: auto; background: #0b1329; border: 1px solid #23304d; border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 6px;">
              <!-- Render checkbox 31 tokens -->
            </div>
          </div>
          <button type="button" class="btn btn-warning btn-sm" style="font-weight: 700; color: #0f172a; width: 100%;" onclick="submitCreateTokenGroup()">
            <i class="bi bi-save2"></i> Lưu Nhóm Token Mới
          </button>
        </div>

        <!-- Danh sách các Nhóm Token hiện có -->
        <div style="font-size: 13px; font-weight: 700; color: #cbd5e1; margin-bottom: 10px;">
          Danh Sách Nhóm Token Hiện Hữu:
        </div>
        <div id="tgrp-existing-list" style="display: flex; flex-direction: column; gap: 8px;">
          <!-- Render existing token groups -->
        </div>

      </div>
      <div style="padding: 12px 20px; background: #0b1329; border-top: 1px solid #1e293b; display: flex; justify-content: flex-end;">
        <button type="button" class="btn btn-secondary btn-sm" onclick="closeTokenGroupModal()">Đóng</button>
      </div>
    </div>
  </div>
"""

if "id=\"modal-token-group\"" not in html:
    pos_b = html.rfind("</body>")
    html = html[:pos_b] + token_group_modal_html + "\n" + html[pos_b:]
    print("Injected modal-token-group into HTML!")

# Thêm nút "Nhóm Token" vào tab Quản lý Token & Quản lý Page
token_group_btn = """<button class="btn btn-warning" onclick="openTokenGroupModal()" style="font-weight: 700; color: #0f172a;"><i class="bi bi-diagram-3-fill"></i> Nhóm Token (<span id="stat-token-groups-count">1</span>)</button>"""

if "openTokenGroupModal" not in html:
    html = html.replace('<button class="btn btn-primary" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token Mới</button>',
                        token_group_btn + '\n              <button class="btn btn-primary" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token Mới</button>')
    print("Added 'Nhóm Token' button to pane-tokens!")

# JS functions cho Nhóm Token
token_group_js = """
  // ================= QUẢN LÝ NHÓM TOKEN (LOHA TOKEN POOL CONTROLLER) =================
  let cachedTokenGroups = [];

  async function openTokenGroupModal() {
    const m = document.getElementById('modal-token-group');
    if (!m) return;
    document.getElementById('tgrp-input-name').value = '';
    
    // Render list of 31 tokens into checkbox box
    const box = document.getElementById('tgrp-tokens-select-box');
    if (box) {
      box.innerHTML = (globalTokensCatalog || []).map((t, idx) => `
        <label style="display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 11.5px; color: #cbd5e1; cursor: pointer; padding: 4px 8px; border-radius: 4px; background: #0f172a;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" class="tgrp-token-check" value="${t.id}" style="width: 15px; height: 15px; accent-color: #f59e0b;">
            <span><b>#${idx+1} ${t.name}</b> <small style="color: #64748b;">(${t.token_masked || 'EAAayhOu...'})</small></span>
          </div>
          <span class="badge" style="background: rgba(16,185,129,0.15); color: #34d399; font-size: 9.5px;">ACTIVE</span>
        </label>
      `).join('');
    }

    await loadTokenGroupsList();
    m.style.display = 'flex';
  }

  function closeTokenGroupModal() {
    const m = document.getElementById('modal-token-group');
    if (m) m.style.display = 'none';
  }

  function toggleAllTokenGroupChecks() {
    const checks = document.querySelectorAll('.tgrp-token-check');
    const allChecked = Array.from(checks).every(c => c.checked);
    checks.forEach(c => c.checked = !allChecked);
  }

  async function loadTokenGroupsList() {
    try {
      const res = await fetch('/api/token-groups');
      const data = await res.json();
      cachedTokenGroups = data.groups || [];

      const countEl = document.getElementById('stat-token-groups-count');
      if (countEl) countEl.textContent = cachedTokenGroups.length;

      const listCont = document.getElementById('tgrp-existing-list');
      if (listCont) {
        if (cachedTokenGroups.length === 0) {
          listCont.innerHTML = '<div style="color: #64748b; font-size: 12px; text-align: center; padding: 15px;">Chưa có nhóm token nào.</div>';
          return;
        }
        listCont.innerHTML = cachedTokenGroups.map(g => `
          <div style="background: #0b1329; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; gap: 12px;">
            <div>
              <div style="font-weight: 700; font-size: 13px; color: #f59e0b;">${g.name}</div>
              <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">${(g.token_ids||[]).length} Token</span>
                <span style="margin-left: 6px;">Chiến lược: <strong>${g.strategy || 'least_recently_used'}</strong></span>
              </div>
            </div>
            <button class="btn btn-secondary btn-sm text-danger" onclick="deleteTokenGroup('${g.id}', '${g.name}')" style="font-size: 11px; padding: 3px 8px;">
              <i class="bi bi-trash"></i> Xóa
            </button>
          </div>
        `).join('');
      }
    } catch (e) {
      console.warn('Lỗi nạp token groups:', e);
    }
  }

  async function submitCreateTokenGroup() {
    const name = document.getElementById('tgrp-input-name')?.value.trim();
    const strategy = document.getElementById('tgrp-input-strategy')?.value || 'least_recently_used';
    if (!name) {
      alert('Vui lòng nhập tên nhóm token!');
      return;
    }
    const tokenIds = [];
    document.querySelectorAll('.tgrp-token-check:checked').forEach(c => tokenIds.push(c.value));
    if (tokenIds.length === 0) {
      alert('Vui lòng chọn ít nhất 1 Token vào nhóm!');
      return;
    }
    try {
      const res = await fetch('/api/token-groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, strategy, token_ids: tokenIds })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        showToast(`Đã tạo thành công Nhóm Token '${name}'!`);
        document.getElementById('tgrp-input-name').value = '';
        await loadTokenGroupsList();
      } else {
        alert('Lỗi: ' + (data.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối tạo nhóm token: ' + e.message);
    }
  }

  async function deleteTokenGroup(gid, gname) {
    if (!confirm(`Xóa nhóm token '${gname}'?`)) return;
    try {
      const res = await fetch('/api/token-groups/' + gid, { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        showToast('Đã xóa nhóm token thành công!');
        await loadTokenGroupsList();
      }
    } catch (e) {
      alert(e.message);
    }
  }
"""

if "function openTokenGroupModal" not in html:
    pos_tok = html.find("async function loadTokensOnly()")
    if pos_tok != -1:
        html = html[:pos_tok] + token_group_js + "\n\n  " + html[pos_tok:]
        print("Injected token_group_js into HTML!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

print("index.html successfully updated with Token Groups & clean modal layout!")
