
import re

html_path = r'D:\Highlight_Video_Studio\web\templates\index.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Current logic:
# function sendSelectedToStudio() {
#   const checkboxes = document.querySelectorAll('.video-select-check:checked');
#   if (checkboxes.length === 0) {
#     alert('Vui lòng tick chọn ít nhất 1 video!');
#     return;
#   }
#   const firstUrl = checkboxes[0].getAttribute('data-url');
#   const count = checkboxes.length;
#
#   sendToRender(firstUrl);
#   ...

# We want:
# If user selects multiple videos and clicks "Ném vào Cắt Highlight",
# it should create jobs for ALL selected videos!
# And in backend: jobs run concurrently or queue up cleanly.

new_func = '''async function sendSelectedToStudio() {
    const checkboxes = document.querySelectorAll('.video-select-check:checked');
    if (checkboxes.length === 0) {
      alert('Vui lòng tick chọn ít nhất 1 video!');
      return;
    }
    const urls = Array.from(checkboxes).map(cb => cb.getAttribute('data-url')).filter(Boolean);
    const count = urls.length;

    if (count === 1) {
      sendToRender(urls[0]);
      return;
    }

    if (!confirm(`Bạn có muốn ném toàn bộ ${count} video đã chọn vào hàng đợi Render không?`)) {
      return;
    }

    const clip_length = document.getElementById('clip_length')?.value || 'auto';
    const num_clips = parseInt(document.getElementById('num_clips')?.value || '3');
    const aspect_ratio = document.getElementById('aspect_ratio')?.value || '9:16';
    const reframe_mode = document.getElementById('reframe_mode')?.value || 'face_center';
    const subtitle_style = document.getElementById('subtitle_style')?.value || 'hormozi_yellow';
    const highlight_criteria = document.getElementById('highlight_criteria')?.value || 'hook_viral';

    let successCount = 0;
    showToast(`Đang khởi tạo ${count} jobs render vào hàng đợi...`);

    for (const url of urls) {
      try {
        const payload = {
          youtube_url: url,
          clip_length,
          num_clips,
          aspect_ratio,
          reframe_mode,
          subtitle_style,
          highlight_criteria
        };
        const res = await fetch('/api/jobs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) successCount++;
      } catch (err) {
        console.error('Lỗi tạo job:', err);
      }
    }

    showToast(`Đã thêm thành công ${successCount}/${count} video vào Hàng đợi Jobs!`);
    loadJobsTable();
    switchTab('jobs');
  }'''

pattern = re.compile(r'function sendSelectedToStudio\(\)\s*\{[\s\S]*?showToast\([^\)]*\);\s*\}\s*\}', re.MULTILINE)
if pattern.search(html):
    html = pattern.sub(new_func, html)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("BATCH_RENDER_UPGRADED_SUCCESS")
else:
    print("PATTERN_NOT_MATCHED")
