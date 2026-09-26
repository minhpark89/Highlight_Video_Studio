from pathlib import Path
import re

app_py = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_py.read_text(encoding="utf-8")

# Let's inspect api_save_group in app.py
# Fix: group_id = data.get("id") or data.get("group_id")
old_save_group = """@app.route("/api/groups", methods=["POST"])
def api_save_group():
    data = request.json or {}
    group_id = data.get("id")
    name = data.get("name", "").strip()"""

new_save_group = """@app.route("/api/groups", methods=["POST"])
def api_save_group():
    data = request.json or {}
    group_id = data.get("id") or data.get("group_id")
    name = data.get("name", "").strip()"""

if old_save_group in text:
    text = text.replace(old_save_group, new_save_group)
    print("Fixed group_id key in api_save_group!")
else:
    print("Could not find exact old_save_group, inspecting...")
    pos = text.find('def api_save_group')
    print(text[pos:pos+300])

# Also check api_distribute_batch:
# It should NEVER mark clips into posted_clips.json when merely scheduling!
# Clips should ONLY be marked into posted_clips.json when they are ACTUALLY PUBLISHED by the publisher worker!
old_mark_in_batch = """    # Đánh dấu các clip này vào posted_clips.json để không bao giờ phân bổ trùng lặp
    try:
        posted_list = list(posted_set)
        for c in assigned_clips:
            if c not in posted_list:
                posted_list.append(c)
        posted_file.write_text(json.dumps(posted_list, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as ex:
        print("[Error saving posted_clips]", ex)"""

new_mark_in_batch = """    # Lưu ý: Không ghi vào posted_clips.json ở đây!
    # Clip chỉ được đánh dấu đã đăng khi Publisher Worker đăng thành công lên Facebook Reels thực tế."""

if old_mark_in_batch in text:
    text = text.replace(old_mark_in_batch, new_mark_in_batch)
    print("Removed premature marking of clips into posted_clips.json during scheduling!")
else:
    print("Could not find exact old_mark_in_batch, searching...")

app_py.write_text(text, encoding="utf-8")
print("Saved app.py updates!")
