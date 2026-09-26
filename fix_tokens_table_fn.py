from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Update loadTokensOnly to render directly into #tokens-table-body
old_loadtokens = """  async function loadTokensOnly() {
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
  }"""

new_loadtokens = """  async function loadTokensOnly() {
    try {
      const res = await fetch('/api/tokens');
      const data = await res.json();
      const tokens = data.tokens || [];
      
      const countEl = document.getElementById('tab-token-total-count');
      if (countEl) countEl.textContent = tokens.length;
      
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
              <button class="btn btn-outline btn-sm" onclick="deleteSingleToken('${t.id}', '${tName}')" style="color: #ef4444; border-color: rgba(239,68,68,0.3); padding: 4px 8px; font-size: 12px;" title="Xóa Token">
                <i class="bi bi-trash"></i> Xóa
              </button>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = rows;
    } catch (e) {
      console.error('Lỗi loadTokensOnly:', e);
      const tbody = document.getElementById('tokens-table-body');
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="color: #ef4444; padding: 20px; text-align: center;">Lỗi tải token: ${e.message}</td></tr>`;
    }
  }"""

if old_loadtokens in html:
    html = html.replace(old_loadtokens, new_loadtokens, 1)
    print("Replaced old_loadtokens with table row renderer!")
else:
    print("WARNING: Exact match for old_loadtokens not found")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html!")
