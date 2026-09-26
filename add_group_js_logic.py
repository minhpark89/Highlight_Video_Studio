from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's add the JavaScript logic for:
# 1. editGroupModal(groupId)
# 2. closeEditGroupModal()
# 3. selectAllEditPages(val)
# 4. saveEditGroup(e)
# 5. runLoHaBatchSchedule(groupId, groupName) -> opens modal-schedule-config
# 6. closeScheduleConfigModal()
# 7. executeBatchSchedule() -> calls POST /api/distribute/batch with posts_per_page!

group_js_logic = """
  // ==================== LOHA PAGE: QUẢN LÝ & SỬA NHÓM TRANG ====================
  let allPagesCached = [];

  async function editGroupModal(groupId) {
    try {
      const [resG, resP] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/pages')
      ]);
      const dataG = await resG.json();
      const groups = Array.isArray(dataG) ? dataG : (dataG.groups || []);
      const g = groups.find(x => x.id === groupId);
      if (!g) {
        alert('Không tìm thấy thông tin nhóm!');
        return;
      }

      const dataP = await resP.json();
      allPagesCached = Array.isArray(dataP) ? dataP : (dataP.pages || []);

      document.getElementById('edit-group-id').value = g.id;
      document.getElementById('edit-group-name').value = g.name || '';
      document.getElementById('edit-group-folder').value = g.folder_path || g.folder_binding || 'D:\\\\Highlight_Video_Studio\\\\output';

      const sched = g.schedule_config || {};
      const times = sched.times && sched.times.length ? sched.times.join(', ') : '07:00, 11:30, 17:00, 20:00';
      const stagger = sched.stagger_minutes || 15;

      document.getElementById('edit-group-times').value = times;
      document.getElementById('edit-group-stagger').value = stagger;

      // Render Fanpage selection checkboxes
      const container = document.getElementById('edit-group-pages-list');
      const assignedIds = new Set(g.page_ids || []);
      document.getElementById('edit-group-page-count').innerText = assignedIds.size;

      let html = '';
      allPagesCached.forEach(p => {
        const isChecked = assignedIds.has(p.page_id);
        html += `
          <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #e2e8f0; cursor: pointer; padding: 4px; border-radius: 4px; background: rgba(255,255,255,0.02);">
            <input type="checkbox" class="edit-page-chk" value="${p.page_id}" ${isChecked ? 'checked' : ''} onchange="updateEditPageCount()">
            <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${p.page_name || p.page_id}</span>
          </label>
        `;
      });
      container.innerHTML = html;

      document.getElementById('modal-edit-group').style.display = 'flex';
    } catch (e) {
      alert('Lỗi tải dữ liệu nhóm: ' + e.message);
    }
  }

  function updateEditPageCount() {
    const chks = document.querySelectorAll('.edit-page-chk:checked');
    document.getElementById('edit-group-page-count').innerText = chks.length;
  }

  function selectAllEditPages(val) {
    document.querySelectorAll('.edit-page-chk').forEach(c => c.checked = val);
    updateEditPageCount();
  }

  function closeEditGroupModal() {
    document.getElementById('modal-edit-group').style.display = 'none';
  }

  async function saveEditGroup(e) {
    e.preventDefault();
    const gid = document.getElementById('edit-group-id').value;
    const name = document.getElementById('edit-group-name').value.trim();
    const folder = document.getElementById('edit-group-folder').value.trim();
    const timesRaw = document.getElementById('edit-group-times').value.split(',').map(s => s.trim()).filter(Boolean);
    const stagger = parseInt(document.getElementById('edit-group-stagger').value) || 15;

    const selectedPages = Array.from(document.querySelectorAll('.edit-page-chk:checked')).map(c => c.value);

    try {
      const res = await fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: gid,
          name: name,
          folder_binding: folder,
          page_ids: selectedPages,
          schedule_config: {
            times: timesRaw,
            stagger_minutes: stagger
          }
        })
      });
      const data = await res.json();
      if (data.success) {
        alert('Đã cập nhật cấu hình nhóm thành công!');
        closeEditGroupModal();
        loadLoHaGroups();
      } else {
        alert('Lỗi: ' + (data.error || 'Không thể lưu nhóm'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }

  // ==================== LÊN LỊCH THEO NHÓM (CHỌN SỐ BÀI / KHUNG GIỜ) ====================
  function runLoHaBatchSchedule(groupId, groupName) {
    document.getElementById('sched-conf-group-id').value = groupId;
    document.getElementById('sched-conf-group-name').innerText = groupName;
    document.getElementById('modal-schedule-config').style.display = 'flex';
  }

  function closeScheduleConfigModal() {
    document.getElementById('modal-schedule-config').style.display = 'none';
  }

  async function executeBatchSchedule() {
    const groupId = document.getElementById('sched-conf-group-id').value;
    const postsPerPage = parseInt(document.getElementById('sched-conf-posts-per-page').value) || 1;

    closeScheduleConfigModal();

    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          posts_per_page: postsPerPage,
          auto_first_comment: true,
          english_mode: true
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(`Đã lên lịch thành công ${data.scheduled_count} bài viết!\\n- Mỗi page: ${postsPerPage} bài\\n- 100% First Comment Tiếng Anh\\n- Kiểm tra chi tiết tại tab Quản lý Bài Đăng.`);
        switchTab('pane-posts');
        loadPostsTable();
      } else {
        alert('Lỗi lên lịch: ' + (data.error || data.message || 'Không thể lên lịch'));
      }
    } catch (e) {
      alert('Lỗi kết nối máy chủ: ' + e.message);
    }
  }
"""

pos_load_groups = html.find('async function loadLoHaGroups()')
if 'function editGroupModal' not in html and pos_load_groups != -1:
    html = html[:pos_load_groups] + group_js_logic + "\n\n  " + html[pos_load_groups:]
    print("Added group_js_logic to templates/index.html!")

Path(r"D:\Highlight_Video_Studio\web\templates\index.html").write_text(html, encoding="utf-8")
