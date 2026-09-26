import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Tìm và xoá đoạn form bị trôi dạt ("Cơ chế phát video từ kho", "Curiosity Hook"...)
# Đoạn form này nằm ở cuối file, bị lộ ra ngoài thẻ pane
pos = text.find("Cơ chế phát video từ kho")
if pos != -1:
    print("Found leaked form at pos:", pos)
    # Tìm vùng bắt đầu của thẻ rác này
    start_tag = text.rfind("<div", 0, pos - 150)
    # Tìm thẻ đóng cuối cùng trước thẻ script hoặc modal tiếp theo
    end_tag = text.find("</section>", pos)
    if end_tag == -1:
        end_tag = text.find("<script", pos)
    if end_tag == -1:
        end_tag = text.find("<div id=", pos)
    
    # Tìm chính xác thẻ đóng div của khối này
    div_close = text.find("</div>\n        </div>", pos)
    if div_close != -1:
        end_tag = div_close + len("</div>\n        </div>")

    print(f"Removing rogue block from {start_tag} to {end_tag}")
    text = text[:start_tag] + text[end_tag:]
    print("Rogue form removed successfully!")

# 2. Thêm Tab 'Quản lý Token' riêng biệt trên Navbar (như LoHa Page)
nav_token_btn = """        <button class="nav-btn" data-pane="pane-tokens" onclick="switchTab('pane-tokens', this)">
          <span class="nav-icon"><i class="bi bi-key-fill"></i></span>
          <span>Quản lý Token</span>
        </button>"""

if 'data-pane="pane-tokens"' not in text:
    target_nav = '<button class="nav-btn" data-pane="pane-pages"'
    text = text.replace(target_nav, nav_token_btn + "\n" + target_nav)
    print("Added 'Quản lý Token' tab to navbar!")

# 3. Thêm Section 'pane-tokens' hiển thị toàn bộ 31 Token dạng thẻ ngang chuẩn LoHa Page
pane_tokens_html = """
      <!-- PANE: QUẢN LÝ TOKEN RIÊNG BIỆT (CHUẨN LOHAPAGE) -->
      <section id="pane-tokens" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-key-fill" style="color: #f59e0b;"></i>
                Quản lý Token Hệ Thống (LoHa System Tokens)
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Danh sách Token System User vĩnh viễn (không hết hạn) - Tự động xoay vòng chịu tải cho dàn Fanpage
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="loadTokensOnly()"><i class="bi bi-arrow-repeat"></i> Làm mới</button>
              <button class="btn btn-primary" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token Mới</button>
            </div>
          </div>

          <!-- Banner Thông số Token -->
          <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 20px;">
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Tổng Token Hệ Thống</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span id="tab-token-total-count" style="font-size: 24px; font-weight: 800; color: #f59e0b;">31</span>
                <span style="font-size: 11px; color: #10b981;">Đang hoạt động</span>
              </div>
            </div>
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Fanpage Được Phụ Trách</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span style="font-size: 24px; font-weight: 800; color: #38bdf8;">100</span>
                <span style="font-size: 11px; color: #64748b;">Trang vệ tinh</span>
              </div>
            </div>
            <div class="card" style="padding: 14px 16px; background: #111c33; border: 1px solid #23304d; border-radius: 10px;">
              <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase;">Cơ Chế Phân Phối</div>
              <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 4px;">
                <span style="font-size: 18px; font-weight: 800; color: #34d399;">Xoay Vòng Thông Minh</span>
              </div>
            </div>
          </div>

          <!-- Danh sách 31 Token dạng 1 dòng 1 Token -->
          <div id="tokens-full-list-container" style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 50px;">
            <div style="text-align: center; color: #64748b; padding: 40px;">
              <span class="spinner-border spinner-border-sm text-primary"></span> Đang nạp danh sách 31 Token...
            </div>
          </div>
        </div>
      </section>
"""

if 'id="pane-tokens"' not in text:
    pos_pages_sec = text.find('<section id="pane-pages"')
    if pos_pages_sec != -1:
        text = text[:pos_pages_sec] + pane_tokens_html + "\n" + text[pos_pages_sec:]
        print("Injected pane-tokens section before pane-pages!")

# 4. Thêm JS hàm loadTokensOnly và hỗ trợ switchTab pane-tokens
token_js_code = """
  // ================= TAB QUẢN LÝ TOKEN RIÊNG BIỆT (CHUẨN LOHAPAGE) =================
  async function loadTokensOnly() {
    try {
      const res = await fetch('/api/tokens');
      const data = await res.json();
      const tokens = data.tokens || [];
      
      const countEl = document.getElementById('tab-token-total-count');
      if (countEl) countEl.textContent = tokens.length;
      
      const container = document.getElementById('tokens-full-list-container');
      if (!container) return;

      if (tokens.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #64748b; padding: 40px;">Chưa có Token nào. Hãy bấm "+ Thêm Token Mới" ở trên!</div>';
        return;
      }

      container.innerHTML = tokens.map((t, idx) => {
        const masked = t.token_masked || t.masked_token || 'EAAayhOu...';
        const tName = t.name || `AutoPool ${idx + 1}`;
        const pagesCount = t.pages_count || 0;
        const statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 11px; padding: 4px 8px; border: 1px solid rgba(16, 185, 129, 0.3);"><i class="bi bi-shield-check"></i> HOẠT ĐỘNG (VĨNH VIỄN)</span>`;

        return `
          <div style="background: #111c33; border: 1px solid #23304d; border-radius: 10px; padding: 12px 18px; display: flex; align-items: center; justify-content: space-between; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px; min-width: 220px;">
              <div style="width: 40px; height: 40px; border-radius: 8px; background: rgba(245, 158, 11, 0.15); color: #f59e0b; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 800; flex-shrink: 0;">
                #${idx + 1}
              </div>
              <div>
                <div style="font-weight: 700; font-size: 14px; color: #f8fafc;">${tName}</div>
                <div style="font-size: 11.5px; color: #64748b; font-family: monospace; margin-top: 2px;">${masked}</div>
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 11px; padding: 5px 10px;">
                <i class="bi bi-shield-lock-fill"></i> System User
              </span>
              <span class="badge" style="background: rgba(192, 132, 252, 0.15); color: #c084fc; font-size: 11px; padding: 5px 10px;">
                <i class="bi bi-diagram-3-fill"></i> AutoPool Nhóm Token
              </span>
            </div>

            <div>${statusBadge}</div>

            <div>
              <button class="btn btn-secondary btn-sm text-danger" onclick="deleteSingleToken('${t.id}', '${tName}')" title="Xóa Token này">
                <i class="bi bi-trash"></i> Xóa
              </button>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.error('Lỗi loadTokensOnly:', e);
    }
  }

  async function deleteSingleToken(tokenId, tokenName) {
    if (!confirm(`Bạn có chắc chắn muốn xóa Token '${tokenName}' khỏi kho?`)) return;
    try {
      const res = await fetch('/api/tokens/' + encodeURIComponent(tokenId), { method: 'DELETE' });
      const d = await res.json();
      if (d.success) {
        alert(`Đã xóa token '${tokenName}' thành công!`);
        await loadTokensOnly();
        await loadTokensAndPages();
      } else {
        alert('Lỗi xóa token: ' + (d.error || 'Server error'));
      }
    } catch (e) {
      alert('Lỗi kết nối khi xóa token: ' + e.message);
    }
  }
"""

if "function loadTokensOnly()" not in text:
    pos_top = text.find("async function loadTokensAndPages()")
    if pos_top != -1:
        text = text[:pos_top] + token_js_code + "\n\n  " + text[pos_top:]
        print("Injected token_js_code successfully!")

# Hook loadTokensOnly vào switchTab
if "paneId === 'pane-tokens'" not in text:
    target_switch = "if (paneId === 'pane-pages')"
    text = text.replace(target_switch, "if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();\n      " + target_switch)
    print("Hooked loadTokensOnly into switchTab!")

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("index.html fully updated!")
