from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-tokens in html
pos = html.find('id="pane-tokens"')
pos_end = html.find('</section>', pos)
print("pane-tokens length:", pos_end - pos)

# Replace pane-tokens completely with LoHa Page exact design:
# 1. Box Số Luồng Chạy Song Song (input 10)
# 2. Box Số bài chạy song song trên 1 trang (input 1)
# 3. Thanh Nhóm Token hiện ra ngoài:
#    [ Tất cả (31) ] [ Nhóm AutoPool Chính (31) ] [ BM 1 (5) ]
# 4. Table 1 dòng 1 token

new_pane_tokens = """<section id="pane-tokens" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-key-fill" style="color: #f59e0b;"></i>
                Quản lý Token
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Phép kiểm tra định kỳ không qua proxy của trang — scan sống/die và quản lý nhóm token chuẩn LoHa Page
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="loadTokensOnly()"><i class="bi bi-arrow-repeat"></i> Làm mới</button>
              <button class="btn btn-primary" onclick="openTokenGroupModal()"><i class="bi bi-folder-plus"></i> + Thêm Nhóm Token</button>
              <button class="btn btn-outline" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token</button>
            </div>
          </div>

          <!-- Khối Cấu hình Số Luồng (Chuẩn LoHa Page Top-Left) -->
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
          </div>

          <!-- THANH NHÓM TOKEN (HIỆN NẰM NGAY TRÊN ĐẦU DANH SÁCH NHƯ LOHAPAGE) -->
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
              <span style="display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-collection-fill" style="color: #ec4899;"></i> Chọn Nhóm Token để lọc & phân bổ:
              </span>
              <span style="font-size: 11px; color: #64748b; text-transform: none; font-weight: normal;">Bấm vào nhóm để xem danh sách token của nhóm đó</span>
            </div>
            <div id="loha-token-group-pills" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
              <!-- Render động: [ Tất cả (31) ] [ Nhóm AutoPool Chính (31) ] [ BM 1 (5) ] -->
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
                  <th style="padding: 12px 16px; width: 140px;">Số Trang Gán</th>
                  <th style="padding: 12px 16px;">Nhóm Token</th>
                  <th style="padding: 12px 16px; width: 160px;">Trạng Thái</th>
                  <th style="padding: 12px 16px; text-align: right; width: 140px;">Thao tác</th>
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

html = html[:pos] + new_pane_tokens + html[pos_end+10:]
INDEX_PATH.write_text(html, encoding="utf-8")
print("Replaced pane-tokens successfully!")
