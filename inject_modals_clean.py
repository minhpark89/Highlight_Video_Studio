from pathlib import Path

modal_html = """
<!-- MODAL CHỈNH SỬA NHÓM TRANG (CHUẨN LOHAPAGE) -->
<div id="modal-edit-group" class="modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 9999; justify-content: center; align-items: center; padding: 20px;">
  <div class="modal-content" style="background: #111c33; border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 650px; max-height: 90vh; overflow-y: auto; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 14px; margin-bottom: 20px;">
      <h3 style="margin: 0; font-size: 18px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 8px;">
        <i class="bi bi-gear-fill" style="color: #ec4899;"></i> Chỉnh sửa Cấu hình Nhóm Trang
      </h3>
      <button onclick="closeEditGroupModal()" style="background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer;">&times;</button>
    </div>

    <form id="form-edit-group" onsubmit="saveEditGroup(event)">
      <input type="hidden" id="edit-group-id">
      
      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Tên Nhóm Trang:</label>
        <input type="text" id="edit-group-name" required style="width: 100%; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; color: #fff; font-size: 13px;">
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Thư mục Video nguồn cho nhóm:</label>
        <input type="text" id="edit-group-folder" required style="width: 100%; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; color: #fff; font-family: monospace; font-size: 13px;">
        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Ví dụ: D:\\Highlight_Video_Studio\\output</div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
        <div>
          <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Khung giờ đăng trong ngày:</label>
          <input type="text" id="edit-group-times" value="07:00, 11:30, 17:00, 20:00" placeholder="07:00, 11:30, 17:00, 20:00" style="width: 100%; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; color: #fff; font-family: monospace; font-size: 13px;">
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Cách nhau bằng dấu phẩy (,)</div>
        </div>
        <div>
          <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Giãn cách giữa các Page (Phút):</label>
          <input type="number" id="edit-group-stagger" min="1" max="120" value="15" style="width: 100%; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; color: #fff; font-size: 13px;">
          <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Tránh đăng đồng thời gây spam</div>
        </div>
      </div>

      <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <label style="font-size: 12px; font-weight: 700; color: #94a3b8; margin: 0;">Danh sách Fanpage trong nhóm (<span id="edit-group-page-count">0</span>):</label>
          <div style="display: flex; gap: 8px;">
            <button type="button" class="btn btn-sm btn-outline" onclick="selectAllEditPages(true)" style="padding: 2px 8px; font-size: 11px;">Chọn tất cả</button>
            <button type="button" class="btn btn-sm btn-outline" onclick="selectAllEditPages(false)" style="padding: 2px 8px; font-size: 11px;">Bỏ chọn</button>
          </div>
        </div>
        <div id="edit-group-pages-list" style="max-height: 200px; overflow-y: auto; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
          <!-- Checkbox render động -->
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border); padding-top: 16px;">
        <button type="button" class="btn btn-outline" onclick="closeEditGroupModal()">Hủy</button>
        <button type="submit" class="btn btn-primary" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; font-weight: 700;">
          <i class="bi bi-check-lg"></i> Lưu thay đổi
        </button>
      </div>
    </form>
  </div>
</div>

<!-- MODAL XÁC NHẬN LÊN LỊCH THEO NHÓM (CHỌN SỐ BÀI / NGÀY / TRANG) -->
<div id="modal-schedule-config" class="modal-overlay" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.75); z-index: 9999; justify-content: center; align-items: center; padding: 20px;">
  <div class="modal-content" style="background: #111c33; border: 1px solid var(--border); border-radius: 12px; width: 100%; max-width: 550px; padding: 24px; box-shadow: 0 10px 40px rgba(0,0,0,0.8);">
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 14px; margin-bottom: 20px;">
      <h3 style="margin: 0; font-size: 18px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 8px;">
        <i class="bi bi-calendar2-week-fill" style="color: #38bdf8;"></i> Lên lịch Phân bổ Clip cho Nhóm
      </h3>
      <button onclick="closeScheduleConfigModal()" style="background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer;">&times;</button>
    </div>

    <div>
      <input type="hidden" id="sched-conf-group-id">
      <div style="font-size: 14px; color: #e2e8f0; margin-bottom: 16px;">
        Nhóm áp dụng: <strong id="sched-conf-group-name" style="color: #ec4899;"></strong>
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Số bài muốn lên cho MỖI FANPAGE:</label>
        <select id="sched-conf-posts-per-page" style="width: 100%; background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; color: #fff; font-size: 13px; font-weight: 700;">
          <option value="1">1 bài / ngày / page (Lên lịch 1 khung giờ tiếp theo)</option>
          <option value="2">2 bài / ngày / page (Trải đều 2 khung giờ)</option>
          <option value="4" selected>4 bài / ngày / page (Phủ kín 4 khung giờ: Sáng, Trưa, Chiều, Tối)</option>
        </select>
        <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
          Theo quy tắc 1 Video : 1 Page, hệ thống sẽ bốc số lượng video độc nhất từ kho tương ứng.
        </div>
      </div>

      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Ngôn ngữ First Comment & Bài viết:</label>
        <div style="background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-size: 12.5px; color: #10b981; font-weight: 700;">
          <i class="bi bi-translate"></i> 100% Tiếng Anh Chuẩn Quốc Tế (Full English Hook + Uncut Video Link)
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid var(--border); padding-top: 16px;">
        <button type="button" class="btn btn-outline" onclick="closeScheduleConfigModal()">Hủy</button>
        <button type="button" class="btn btn-primary" onclick="executeBatchSchedule()" style="background: linear-gradient(135deg, #38bdf8, #8b5cf6); border: none; font-weight: 700;">
          <i class="bi bi-send-check-fill"></i> Xác nhận & Quét Lên Lịch
        </button>
      </div>
    </div>
  </div>
</div>
"""

for p in [Path(r"D:\Highlight_Video_Studio\web\templates\index.html"), Path(r"D:\Highlight_Video_Studio\web\index.html")]:
    txt = p.read_text(encoding="utf-8")
    if 'id="modal-edit-group"' in txt:
        # replace existing modal
        pos_m = txt.find('<div id="modal-edit-group"')
        pos_end_m = txt.find('</div>\n</div>\n</div>', pos_m)
        if pos_end_m == -1: pos_end_m = txt.find('<!-- MODAL XÁC NHẬN LÊN LỊCH', pos_m)
    else:
        # insert before </body>
        pos_b = txt.rfind('</body>')
        txt = txt[:pos_b] + modal_html + "\n" + txt[pos_b:]
        p.write_text(txt, encoding="utf-8")
        print(f"Injected modal_html into {p.name}!")

print("Checking both files:")
for p in [Path(r"D:\Highlight_Video_Studio\web\templates\index.html"), Path(r"D:\Highlight_Video_Studio\web\index.html")]:
    txt = p.read_text(encoding="utf-8")
    print(f"{p.name}: has modal-edit-group? {'id=\"modal-edit-group\"' in txt}, has edit-group-id? {'id=\"edit-group-id\"' in txt}")
