# Check how tokens and groups are rendered, and reformat tokens to table style as well
from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
old_pane_tokens = re.search(r'<section id="pane-tokens"[^>]*>.*?</section>', html, re.DOTALL)

new_pane_tokens = """<section id="pane-tokens" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-key-fill" style="color: #f59e0b;"></i>
                Quản lý Token
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Danh sách Token System User vĩnh viễn (không hết hạn) - Tự động xoay vòng chịu tải cho dàn Fanpage
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="loadTokensOnly()"><i class="bi bi-arrow-repeat"></i> Làm mới</button>
              <button class="btn btn-warning" onclick="openTokenGroupModal()" style="font-weight: 700; color: #0f172a;"><i class="bi bi-diagram-3-fill"></i> Nhóm Token (<span id="stat-token-groups-count">1</span>)</button>
              <button class="btn btn-primary" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token Mới</button>
            </div>
          </div>

          <!-- Bảng Token theo dòng chuẩn LoHa Page -->
          <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--panel-bg);">
            <table class="table" style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
              <thead>
                <tr style="background: rgba(15, 23, 42, 0.85); border-bottom: 2px solid var(--border); color: #94a3b8; font-weight: 700;">
                  <th style="padding: 12px 16px; width: 50px;">#</th>
                  <th style="padding: 12px 16px;">Tên Token</th>
                  <th style="padding: 12px 16px;">Mã Token (Masked)</th>
                  <th style="padding: 12px 16px; width: 140px;">Số Trang Quản Lý</th>
                  <th style="padding: 12px 16px;">Số Luồng Tối Đa</th>
                  <th style="padding: 12px 16px; width: 160px;">Trạng Thái</th>
                  <th style="padding: 12px 16px; text-align: right; width: 160px;">Thao tác</th>
                </tr>
              </thead>
              <tbody id="tokens-table-body">
                <tr>
                  <td colspan="7" style="text-align: center; padding: 40px; color: #64748b;">
                    <i class="bi bi-arrow-repeat spin" style="font-size: 24px; display: inline-block;"></i> Đang nạp danh sách token...
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>"""

if old_pane_tokens:
    html = html[:old_pane_tokens.start()] + new_pane_tokens + html[old_pane_tokens.end():]
    print("Replaced pane-tokens with LoHa Table HTML!")

# Update loadTokensOnly to render into tokens-table-body
old_tokens_fn = re.search(r'async function loadTokensOnly\(\)\s*\{.*?const container = document\.getElementById\(\'tokens-full-list-container\'\);.*?\}\s*\}', html, re.DOTALL)
if not old_tokens_fn:
    # search more broadly
    pos_t = html.find('async function loadTokensOnly()')
    pos_t_end = html.find('async function deleteTokenItem', pos_t)
    if pos_t_end == -1:
        pos_t_end = html.find('function deleteToken', pos_t)

new_tokens_fn = """  async function loadTokensOnly() {
    try {
      const res = await fetch('/api/tokens');
      const data = await res.json();
      const tokens = data.tokens || [];
      
      const tbody = document.getElementById('tokens-table-body');
      if (!tbody) return;

      if (tokens.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #64748b; padding: 40px;">Chưa có Token nào. Hãy bấm "+ Thêm Token Mới" ở trên!</td></tr>';
        return;
      }

      let rows = '';
      tokens.forEach((t, idx) => {
        const masked = t.token_masked || t.masked_token || 'EAAayhOu...';
        const tName = t.name || `AutoPool ${idx + 1}`;
        const pagesCount = t.pages_count || 0;
        const threads = t.max_threads || 10;
        const statusBadge = `<span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; font-size: 11px; padding: 4px 8px; border: 1px solid rgba(16, 185, 129, 0.3);"><i class="bi bi-shield-check"></i> HOẠT ĐỘNG (VĨNH VIỄN)</span>`;

        rows += `
          <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
            <td style="padding: 12px 16px; color: #64748b; font-weight: 700;">${idx + 1}</td>
            <td style="padding: 12px 16px;">
              <div style="font-weight: 800; font-size: 13.5px; color: #fff; display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-key-fill" style="color: #f59e0b;"></i>
                <span>${tName}</span>
              </div>
              <div style="font-size: 11px; color: #64748b;">ID: ${t.id || 'system_user'}</div>
            </td>
            <td style="padding: 12px 16px;">
              <code style="font-family: monospace; font-size: 12px; color: #f59e0b; background: rgba(245, 158, 11, 0.1); padding: 4px 8px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.2);">${masked}</code>
            </td>
            <td style="padding: 12px 16px;">
              <span style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;">
                <i class="bi bi-flag-fill"></i> ${pagesCount} Page
              </span>
            </td>
            <td style="padding: 12px 16px;">
              <span style="color: #e2e8f0; font-weight: 700; font-size: 12px;"><i class="bi bi-cpu" style="color: #38bdf8;"></i> ${threads} luồng</span>
            </td>
            <td style="padding: 12px 16px;">${statusBadge}</td>
            <td style="padding: 12px 16px; text-align: right;">
              <button class="btn btn-outline btn-sm" onclick="deleteTokenItem('${t.id}')" style="color: #ef4444; border-color: rgba(239,68,68,0.3); padding: 4px 8px; font-size: 12px;" title="Xóa Token">
                <i class="bi bi-trash"></i> Xóa
              </button>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = rows;
    } catch (e) {
      console.error(e);
      const tbody = document.getElementById('tokens-table-body');
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="color: #ef4444; padding: 20px; text-align: center;">Lỗi tải danh sách token: ${e.message}</td></tr>`;
    }
  }"""

pos_t_fn = html.find('async function loadTokensOnly()')
pos_t_fn_end = html.find('async function deleteTokenItem', pos_t_fn)
if pos_t_fn != -1 and pos_t_fn_end != -1:
    html = html[:pos_t_fn] + new_tokens_fn + "\n\n  " + html[pos_t_fn_end:]
    print("Replaced loadTokensOnly function successfully!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html step 3!")
