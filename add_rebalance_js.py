from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's add the function rebalanceTokenPageAllocation() and update the ratio badge
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

pos_load_tok = html.find('async function loadTokensOnly()')
if 'function rebalanceTokenPageAllocation' not in html and pos_load_tok != -1:
    html = html[:pos_load_tok] + rebalance_js + "\n\n  " + html[pos_load_tok:]
    print("Added rebalanceTokenPageAllocation to templates/index.html!")

Path(r"D:\Highlight_Video_Studio\web\templates\index.html").write_text(html, encoding="utf-8")
