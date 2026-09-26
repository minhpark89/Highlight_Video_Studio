from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's write the complete loadLoHaGroups function that renders directly into the table
new_load_groups_fn = """  async function loadLoHaGroups() {
    const tbody = document.getElementById('loha-groups-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 40px; color: #94a3b8;">
          <i class="bi bi-arrow-repeat spin" style="font-size: 24px; display: inline-block;"></i>
          <div style="margin-top: 8px;">Đang tải danh sách Nhóm Trang & Kho Video...</div>
        </td>
      </tr>
    `;

    try {
      const [resG, resC] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/clips')
      ]);
      const groupsData = await resG.json();
      const groups = Array.isArray(groupsData) ? groupsData : (groupsData.groups || []);
      const clipsData = await resC.json();
      const clips = Array.isArray(clipsData) ? clipsData : (clipsData.clips || []);
      const unpostedClips = clips.filter(c => !c.is_posted);

      if (!groups || groups.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: #64748b;">
              <i class="bi bi-folder-x" style="font-size: 28px; display: block; margin-bottom: 8px;"></i>
              Chưa có Nhóm Trang nào. Hãy bấm nút "+ Tạo nhóm mới" ở góc trên để tạo nhóm!
            </td>
          </tr>
        `;
        return;
      }

      let rows = '';
      groups.forEach((g, idx) => {
        const pageCount = (g.page_ids || []).length;
        const availableCount = unpostedClips.length;
        const folder = g.folder_path || g.folder_binding || 'D:\\\\Highlight_Video_Studio\\\\output';
        const stagger = (g.schedule_config && g.schedule_config.stagger_minutes) ? g.schedule_config.stagger_minutes : 15;
        const times = (g.schedule_config && g.schedule_config.times && g.schedule_config.times.length) ? g.schedule_config.times.join(', ') : '11:30, 19:30';

        rows += `
          <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='rgba(255,255,255,0.02)'" onmouseout="this.style.background='transparent'">
            <td style="padding: 12px 16px; color: #64748b; font-weight: 700;">${idx + 1}</td>
            <td style="padding: 12px 16px;">
              <div style="font-weight: 800; font-size: 14px; color: #fff; display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-collection-fill" style="color: #ec4899;"></i>
                <span>${g.name}</span>
              </div>
              <div style="font-size: 11px; color: #64748b; margin-top: 2px;">ID: ${g.id}</div>
            </td>
            <td style="padding: 12px 16px;">
              <div style="font-family: monospace; font-size: 11.5px; color: #cbd5e1; background: #0f172a; padding: 4px 8px; border-radius: 6px; display: inline-block; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${folder}">
                <i class="bi bi-folder-fill" style="color: #f59e0b;"></i> ${folder}
              </div>
              <div style="font-size: 11px; color: #10b981; margin-top: 3px; font-weight: 600;">
                <i class="bi bi-film"></i> ${availableCount} clip khả dụng
              </div>
            </td>
            <td style="padding: 12px 16px;">
              <span style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;">
                <i class="bi bi-flag-fill"></i> ${pageCount} Page
              </span>
            </td>
            <td style="padding: 12px 16px;">
              <span style="background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); padding: 3px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 700; display: inline-flex; align-items: center; gap: 5px;">
                <i class="bi bi-check-circle-fill"></i> 1 Video : 1 Page
              </span>
            </td>
            <td style="padding: 12px 16px;">
              <div style="font-size: 12px; font-weight: 700; color: #e2e8f0; font-family: monospace;">
                <i class="bi bi-clock-history" style="color: #38bdf8;"></i> ${times}
              </div>
              <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                Giãn cách: <strong>${stagger} phút</strong>
              </div>
            </td>
            <td style="padding: 12px 16px; text-align: right;">
              <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
                <button class="btn btn-primary btn-sm" onclick="runLoHaBatchSchedule('${g.id}', '${g.name}')" style="background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; font-weight: 700; padding: 5px 12px; font-size: 12px;" title="Quét kho video và lên lịch ngay cho nhóm này">
                  <i class="bi bi-send-check-fill"></i> Lên lịch
                </button>
                <button class="btn btn-outline btn-sm" onclick="editGroupModal('${g.id}')" style="padding: 5px 10px; font-size: 12px;" title="Chỉnh sửa cấu hình nhóm">
                  <i class="bi bi-gear-fill"></i> Sửa
                </button>
                <button class="btn btn-outline btn-sm" onclick="deleteGroup('${g.id}', '${g.name}')" style="color: #ef4444; border-color: rgba(239,68,68,0.3); padding: 5px 8px; font-size: 12px;" title="Xóa nhóm">
                  <i class="bi bi-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = rows;
    } catch (e) {
      console.error(e);
      tbody.innerHTML = `<tr><td colspan="7" style="color: #ef4444; padding: 20px; text-align: center;">Lỗi tải danh sách nhóm: ${e.message}</td></tr>`;
    }
  }"""

# Replace existing loadLoHaGroups function in html
pos = html.find('async function loadLoHaGroups()')
pos_end = html.find('async function runLoHaBatchSchedule', pos)
if pos != -1 and pos_end != -1:
    html = html[:pos] + new_load_groups_fn + "\n\n  " + html[pos_end:]
    print("Replaced loadLoHaGroups function successfully!")
else:
    print("Could not find loadLoHaGroups boundary")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html step 2!")
