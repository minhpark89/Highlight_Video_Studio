from pathlib import Path
import re

html_tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
text = html_tmpl.read_text(encoding="utf-8")

# Let's inspect pane-tokens in templates/index.html:
pos_tokens = text.find('id="pane-tokens"')
pos_table = text.find('<table', pos_tokens)

old_controls_block = """          <!-- Khối Cấu hình Số Luồng (Chuẩn LoHa Page Top-Left) -->
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <!-- Box 1: Số luồng song song -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; border-right: 1px solid #1e293b; padding-right: 16px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #a78bfa; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-cpu-fill"></i> Số Luồng Chạy Song Song
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                  Mỗi luồng dùng 1 Token ra chạy 1 trang (Đăng nhanh hơn khi có nhiều trang cùng chờ bài).
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <input type="number" id="loha-token-threads" min="1" max="50" value="10" style="width: 60px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 5px 8px; border-radius: 6px; font-weight: 700; text-align: center;">
                <span style="font-size: 12px; color: #94a3b8;">luồng</span>
              </div>
            </div>

            <!-- Box 2: Số bài chạy song song trên 1 trang -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-layers-fill"></i> Số bài chạy song song trên 1 trang
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                  Mặc định 1 (đăng lần lượt từng bài lên mỗi page, chống spam).
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <input type="number" id="loha-posts-per-page" min="1" max="10" value="1" style="width: 60px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 5px 8px; border-radius: 6px; font-weight: 700; text-align: center;">
                <span style="font-size: 12px; color: #94a3b8;">bài/trang</span>
              </div>
            </div>
          </div>"""

# Replace with 3-box Grid:
# Box 1: Số luồng song song (10 luồng)
# Box 2: Tỷ lệ phân bổ: Số Page gán cho 1 Token (mặc định 3-4 page/token, có nút Tái phân bổ lại)
# Box 3: Số bài song song trên 1 trang (1 bài/trang)
new_controls_block = """          <!-- Khối Cấu hình Luồng & Tỷ lệ Phân bổ Token/Page (Chuẩn LoHa Page) -->
          <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 14px; display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 16px;">
            <!-- Box 1: Số luồng song song -->
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; border-right: 1px solid #1e293b; padding-right: 14px;">
              <div>
                <div style="font-size: 13px; font-weight: 700; color: #a78bfa; display: flex; align-items: center; gap: 6px;">
                  <i class="bi bi-cpu-fill"></i> Số Luồng Chạy Song Song
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
                  Hiện tại: <strong id="token-ratio-status" style="color: #38bdf8;">~3-4 Page/Token</strong> (100 Page / 31 Token)
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 6px;">
                <input type="number" id="pages-per-token-input" min="1" max="100" value="4" style="width: 55px; background: #0f172a; border: 1px solid #334155; color: #10b981; padding: 5px; border-radius: 6px; font-weight: 700; text-align: center;">
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
                <input type="number" id="loha-posts-per-page" min="1" max="10" value="1" style="width: 55px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 5px; border-radius: 6px; font-weight: 700; text-align: center;">
                <span style="font-size: 11px; color: #94a3b8;">bài</span>
              </div>
            </div>
          </div>"""

if old_controls_block in text:
    text = text.replace(old_controls_block, new_controls_block)
    print("Replaced pane-tokens controls block with 3-box allocation control!")
else:
    print("Could not find exact old_controls_block in templates/index.html")

html_tmpl.write_text(text, encoding="utf-8")
