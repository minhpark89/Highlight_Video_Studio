from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# 1. Look for loha-token-threads block in pane-tokens
pos_tokens = text.find('id="pane-tokens"')
pos_table = text.find('<table', pos_tokens)

old_controls_block = text[text.find('<!-- Khối Cấu hình', pos_tokens):pos_table].strip()
print("=== OLD CONTROLS BLOCK ===")
print(old_controls_block)

new_controls_block = """<!-- Khối Cấu hình Luồng & Tỷ lệ Phân bổ Token/Page (Chuẩn LoHa Page) -->
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 14px; display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 16px;">
            <!-- Box 1: Số luồng song song -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; border-right: 1px solid #1e293b; padding-right: 14px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #a78bfa; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-cpu-fill"></i> Số Luồng Song Song
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                  Mỗi luồng dùng 1 Token chạy 1 page
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <input type="number" id="loha-token-threads" min="1" max="50" value="10" style="width: 55px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 5px; border-radius: 6px; font-weight: 700; text-align: center;">
                <span style="font-size: 11px; color: #94a3b8;">luồng</span>
              </div>
            </div>

            <!-- Box 2: TỶ LỆ PHÂN BỔ: SỐ PAGE ỨNG VỚI 1 TOKEN -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; border-right: 1px solid #1e293b; padding-right: 14px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #10b981; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-diagram-3-fill"></i> Số Page Gán Cho 1 Token
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                  Đang gán: <strong id="token-ratio-status" style="color: #38bdf8;">~3-4 Page/Token</strong> (100 Page / 31 Token)
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <input type="number" id="pages-per-token-input" min="1" max="50" value="4" style="width: 50px; background: #0f172a; border: 1px solid #334155; color: #10b981; padding: 5px; border-radius: 6px; font-weight: 700; text-align: center;">
                <button class="btn btn-sm btn-primary" onclick="rebalanceTokenPageAllocation()" style="padding: 4px 8px; font-size: 11px; font-weight: 700; background: #10b981; border: none;" title="Chia đều lại toàn bộ Page cho dàn Token">
                  <i class="bi bi-shuffle"></i> Gán Lại
                </button>
              </div>
            </div>

            <!-- Box 3: Số bài chạy song song trên 1 trang -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-layers-fill"></i> Bài/trang cùng lúc
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                  Mặc định 1 (đăng lần lượt chống spam)
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <input type="number" id="loha-posts-per-page" min="1" max="10" value="1" style="width: 50px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 5px; border-radius: 6px; font-weight: 700; text-align: center;">
                <span style="font-size: 11px; color: #94a3b8;">bài</span>
              </div>
            </div>
          </div>"""

text = text.replace(old_controls_block, new_controls_block)

# 2. Add Facebook link for published posts in loadPostsTable
old_badge = """        if (p.status === 'published' || p.status === 'success') {
          statusBadge = '<span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px;"><i class="bi bi-check-circle"></i> Đã đăng</span>';
        } else if (p.status === 'failed') {"""

new_badge = """        if (p.status === 'published' || p.status === 'success') {
          const reelUrl = p.post_fb_id ? `https://www.facebook.com/reel/${p.post_fb_id}` : (p.fb_url || '');
          statusBadge = `
            <div>
              <span style="background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.4); padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                <i class="bi bi-check-circle-fill"></i> Đã đăng
              </span>
              ${reelUrl ? `
                <div style="margin-top: 5px;">
                  <a href="${reelUrl}" target="_blank" style="color: #38bdf8; font-size: 11.5px; text-decoration: none; font-weight: 800; display: inline-flex; align-items: center; gap: 4px; background: rgba(56, 189, 248, 0.15); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.35);">
                    <i class="bi bi-box-arrow-up-right"></i> Xem Reel Facebook
                  </a>
                </div>
              ` : ''}
            </div>
          `;
        } else if (p.status === 'failed') {"""

text = text.replace(old_badge, new_badge)

# 3. Add JS rebalanceTokenPageAllocation
rebalance_js = """
  async function rebalanceTokenPageAllocation() {
    const inputVal = parseInt(document.getElementById('pages-per-token-input').value) || 4;
    if (!confirm(`Xác nhận: Tự động phân bổ lại toàn bộ 100 Fanpage vào dàn Token trong Vault với tỷ lệ tối đa ${inputVal} Page / 1 Token?`)) {
      return;
    }

    try {
      const [resT, resP] = await Promise.all([
        fetch('/api/tokens'),
        fetch('/api/pages')
      ]);
      const dataT = await resT.json();
      const dataP = await resP.json();

      const tokens = dataT.tokens || [];
      const pages = dataP.pages || [];

      if (tokens.length === 0) {
        alert('Không có token nào trong Vault để phân bổ!');
        return;
      }

      // Xoay vòng round-robin gán đều các page cho từng token theo inputVal
      const assignments = [];
      pages.forEach((p, idx) => {
        const tokenObj = tokens[Math.floor(idx / inputVal) % tokens.length];
        assignments.push({
          page_id: p.page_id,
          token_id: tokenObj.id,
          token_name: tokenObj.name
        });
      });

      const resAssign = await fetch('/api/pages/batch_assign_token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments: assignments })
      });

      const dataRes = await resAssign.json();
      if (dataRes.success) {
        alert(`✅ Đã phân bổ lại thành công!\\n- Tổng: ${pages.length} Fanpage\\n- Dàn: ${tokens.length} Token\\n- Tỷ lệ: ~${(pages.length / tokens.length).toFixed(1)} Page/Token (Tối đa ${inputVal} Page/Token).`);
        loadTokensOnly();
        if (typeof loadTokensAndPages === 'function') loadTokensAndPages();
      } else {
        alert('Lỗi: ' + (dataRes.error || 'Không thể phân bổ'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }
"""

if "function rebalanceTokenPageAllocation" not in text:
    pos_insert = text.find("async function loadTokensOnly()")
    text = text[:pos_insert] + rebalance_js + "\n\n  " + text[pos_insert:]

# Save both templates/index.html and web/index.html
html_tmpl.write_text(text, encoding="utf-8")
Path(r"D:\Highlight_Video_Studio\web\index.html").write_text(text, encoding="utf-8")
print("Saved both templates/index.html and web/index.html!")
