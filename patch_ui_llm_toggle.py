from pathlib import Path
import re

tmpl_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
web_path = Path(r"D:\Highlight_Video_Studio\web\index.html")
text = tmpl_path.read_text(encoding="utf-8")

# Let's inspect modal-schedule-config
pos = text.find('id="modal-schedule-config"')
end = text.find('function executeBatchSchedule', pos)
old_modal_chunk = text[pos:end]
print("Found modal chunk. Length:", len(old_modal_chunk))

# We want to add the Toggle AI LLM Curiosity Comment right below the language box
old_lang_box = """      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Ngôn ngữ First Comment & Bài viết:</label>
        <div style="background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-size: 12.5px; color: #10b981; font-weight: 700;">
          <i class="bi bi-translate"></i> 100% Tiếng Anh Chuẩn Quốc Tế (Full English Hook + Uncut Video Link)
        </div>
      </div>"""

new_lang_and_llm_box = """      <div style="margin-bottom: 16px;">
        <label style="display: block; font-size: 12px; font-weight: 700; color: #94a3b8; margin-bottom: 6px;">Ngôn ngữ First Comment & Bài viết:</label>
        <div style="background: #0b1120; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-size: 12.5px; color: #10b981; font-weight: 700;">
          <i class="bi bi-translate"></i> 100% Tiếng Anh Chuẩn Quốc Tế (Full English Hook + Uncut Video Link)
        </div>
      </div>

      <!-- ĐIỂM 1: CÀI ĐẶT BẬT/TẮT AI LLM VIẾT FIRST COMMENT CURIOSITY GAP -->
      <div style="margin-bottom: 16px; background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 8px; padding: 12px 14px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <label for="sched-conf-use-llm" style="cursor: pointer; margin: 0; font-size: 13px; font-weight: 700; color: #c084fc; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-robot"></i> Dùng AI LLM Viết First Comment Gây Tò Mò
          </label>
          <input type="checkbox" id="sched-conf-use-llm" checked style="width: 18px; height: 18px; accent-color: #a855f7; cursor: pointer;">
        </div>
        <div style="font-size: 11.5px; color: #94a3b8; margin-top: 6px; line-height: 1.4;">
          • <strong>Bật:</strong> Gọi router <em>Gemini-3-Flash</em> tự động sáng tạo hook gây tò mò (Curiosity Gap) theo đúng nội dung clip.<br>
          • <strong>Tắt hoặc lỗi mạng:</strong> Tự động fallback về comment mẫu chuẩn cố định kéo về Web CMS.
        </div>
      </div>"""

if old_lang_box in text:
    text = text.replace(old_lang_box, new_lang_and_llm_box)
    print("Successfully added LLM Curiosity Comment toggle into modal-schedule-config!")
else:
    print("Could not find old_lang_box exact text!")

# Update executeBatchSchedule to send use_llm_comment
old_exec_js = """    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          posts_per_page: postsPerPage,
          auto_first_comment: true,
          english_mode: true
        })
      });"""

new_exec_js = """    const useLlm = document.getElementById('sched-conf-use-llm') ? document.getElementById('sched-conf-use-llm').checked : true;

    try {
      const res = await fetch('/api/distribute/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          group_id: groupId,
          posts_per_page: postsPerPage,
          auto_first_comment: true,
          use_llm_comment: useLlm,
          english_mode: true
        })
      });"""

if old_exec_js in text:
    text = text.replace(old_exec_js, new_exec_js)
    print("Successfully updated executeBatchSchedule with use_llm_comment param!")
else:
    print("Could not find old_exec_js exact text!")

tmpl_path.write_text(text, encoding="utf-8")
web_path.write_text(text, encoding="utf-8")
print("Saved both templates/index.html and web/index.html!")
