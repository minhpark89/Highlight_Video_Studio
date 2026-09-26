from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

pos_t = html.find('id="pane-tokens"')
pos_end_t = html.find('</section>', pos_t)

print("Found pane-tokens:", pos_t, pos_end_t)

# New LoHa style pane-tokens:
# Top: Token Pool / Groups bar (Tất cả (31) | Nhóm AutoPool Chính (31) | BM 1 (5)...)
# Settings: Số luồng chạy song song (10 luồng)
# Table: 1 row per token (Check, #, Tên token, Trạng thái, Số page gán, Hành động)
new_pane_tokens = """<section id="pane-tokens" class="pane">
        <div class="panel">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h2 style="font-size: 20px; font-weight: 800; margin: 0; display: flex; align-items: center; gap: 10px;">
                <i class="bi bi-key-fill" style="color: #f59e0b;"></i>
                Quản lý Token & Nhóm Token
              </h2>
              <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                Cấu hình số luồng chạy song song, phân chia Nhóm Token (Token Pool) và giám sát trạng thái System User vĩnh viễn
              </div>
            </div>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-secondary" onclick="loadTokensOnly()"><i class="bi bi-arrow-repeat"></i> Làm mới</button>
              <button class="btn btn-primary" onclick="openAddTokenGroupModal()"><i class="bi bi-plus-circle"></i> + Tạo Nhóm Token</button>
              <button class="btn btn-outline" onclick="openAddTokenModal()"><i class="bi bi-plus-lg"></i> Thêm Token</button>
            </div>
          </div>

          <!-- Khối Cấu hình Số Luồng Chạy Song Song (Chuẩn LoHa Page) -->
          <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 14px 18px; margin-bottom: 18px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px;">
            <div style="display: flex; align-items: center; gap: 14px;">
              <div style="width: 38px; height: 38px; border-radius: 8px; background: rgba(139, 92, 246, 0.15); color: #a78bfa; display: flex; align-items: center; justify-content: center; font-size: 18px;">
                <i class="bi bi-cpu-fill"></i>
              </div>
              <div>
                <div style="font-size: 13.5px; font-weight: 700; color: #f8fafc;">Số Luồng Chạy Song Song</div>
                <div style="font-size: 11.5px; color: #94a3b8; margin-top: 2px;">
                  Mỗi luồng dùng 1 Token ra chạy 1 trang. Nhiều luồng = Đăng nhanh hơn khi có nhiều trang cùng chờ bài.
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
              <span style="font-size: 12px; color: #94a3b8;">Số luồng tối đa:</span>
              <input type="number" id="cfg-token-threads" min="1" max="50" value="10" style="width: 70px; background: #0f172a; border: 1px solid #334155; color: #f8fafc; padding: 6px 10px; border-radius: 6px; font-weight: 700; text-align: center;">
              <button class="btn btn-outline btn-sm" onclick="saveTokenThreadsConfig()" style="font-size: 12px; font-weight: 700;">
                <i class="bi bi-check-lg"></i> Lưu cấu hình
              </button>
            </div>
          </div>

          <!-- KHỐI DANH SÁCH NHÓM TOKEN (HIỆN RA NGOÀI MẶT TIỀN NHƯ LOHAPAGE) -->
          <div style="margin-bottom: 18px;">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
              <i class="bi bi-diagram-3-fill" style="color: #ec4899;"></i> Danh Sách Nhóm Token (Token Pools):
            </div>
            <!-- Thanh Tabs Chọn Nhóm Token ngang như LoHa -->
            <div id="token-groups-pills-bar" style="display: flex; gap: 10px; flex-wrap: wrap;">
              <!-- Render động bằng loadTokenGroupsPills() -->
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

html = html[:pos_t] + new_pane_tokens + html[pos_end_t+10:]
INDEX_PATH.write_text(html, encoding="utf-8")
print("Updated pane-tokens HTML with Token Groups bar!")
