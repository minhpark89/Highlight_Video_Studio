from pathlib import Path

html = Path(r"D:\Highlight_Video_Studio\web\templates\index.html").read_text(encoding="utf-8")

# Let's inspect line 5040 to 5080 in templates/index.html
old_code_snippet = """  async function runLoHaBatchSchedule(groupId, groupName) {
    if (!confirm(`Xác nhận quét kho video (D:\\Highlight_Video_Studio\\output) và phân bổ độc nhất (1 Video : 1 Page) cho nhóm '${groupName}'?`)) {
      return;
    }

    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          stagger_minutes: 15,
          auto_first_comment: true,
          delete_after_schedule: false
        })
      });

      const data = await res.json();
      if (!res.ok) {
        alert('Lỗi: ' + (data.error || 'Không thể phân bổ'));
        return;
      }

      alert(`✅ Thành công!\\n\\n${data.message}\\nTổng số bài đã lên lịch: ${data.scheduled_count} bài!\\n\\nHệ thống sẽ chuyển bạn sang tab 'Quản lý Bài Đăng' để theo dõi.`);
      
      // Chuyển sang tab quản lý bài đăng
      switchTab('pane-posts');
    } catch (err) {
      alert('Lỗi kết nối server: ' + err.message);
    }
  }"""

if old_code_snippet in html:
    # Delete the old overriding function so the modal version at line 4900 is used!
    html = html.replace(old_code_snippet, "// Old runLoHaBatchSchedule removed to use modal-schedule-config")
    Path(r"D:\Highlight_Video_Studio\web\templates\index.html").write_text(html, encoding="utf-8")
    print("Removed duplicate old runLoHaBatchSchedule from templates/index.html!")
else:
    print("Could not find exact old_code_snippet, inspecting...")
